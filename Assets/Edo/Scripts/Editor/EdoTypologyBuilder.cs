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
// ⭕ NagayaRun / DobeiRun は EdoBuild(EdoBuildRun.cs)にある。2026-09-21 の EDO-0299 ④ で
//    EdoNishiTameikeBuilder ごと引き取った。⚠ 塀の走り方向の割り付けはまだ bounds 中心合わせ(EDO-0302)。

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static partial class EdoTypologyBuilder   // 庭(Stage 5)は EdoTypologyBuilder.Niwa.cs
{
    const float ES = 1.818f;          // edogoyomi の倍率(江戸間1間)
    const float KEN = 1.818f;
    const float SETBACK = 6.0f;       // 囲いの内側から主屋までの引き(m)
    // 前庭の奥行の**狙い**(門の芯から棟の軒まで・向きを問わない半径)。⛔ 関門ではない — 取れない筆では
    // 試した中で門から最も遠い場所に建てる(施主 2026-09-23)。区画ごとの値は表の maeniwa_ken。4間 = 7.27m【U: 小旗本の門→玄関の間合いの
    // 当方の推定・史料値ではない】。地形のスプラットが白洲を描ける広さ(EdoGardenSurfacePaint.SANDO_MIN_TEXELS)
    // がこれを上回るときはそちらを採る(EDO-0372)。
    const float MAENIWA_MIN = 4f * 1.818f;
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
        // 附属の種別(EDO-0304 案A・2026-09-21 考証方)。⛔ 棟数は推定しない — 在る/無いの 0/1 だけ。
        public int umaya, komeKura, sakujiKoya, hikeshiKura, kagoKura, monooki;
        public bool baba;
        public int maguchiKen, depthKen;
        public bool twoSided, jishinban, inari;
        public bool kuri, yagura, shoro, sanmon, graveyard;
        // ⭐ 本堂(坊・社家は主屋)の間数 [桁行, 梁間]。EDO-0354 まで**ビルダーが名を読みもしない欄**だった。
        public int hallW, hallD;
        // ⭐ 辺ごとの囲い(EDO-0468)。`enclosure_dir` = { "N": "nagaya", "S": "none", … } ── 辺の外向きに最も近い
        //    4 方位の値が `enclosure` に勝つ。書いていない方位は `enclosure` のまま。史料で辺ごとに違う区画だけに書く
        //    (観理院: 名所図会で東と北に長屋・南は施主裁定で練塀 EDO-0500)。
        public Dictionary<string, string> encDir;
        // ⭐ 主屋の型(EDO-0327)。goten / omote_oku / ganko / ujigata / tanoji。
        //    ⛔ 2026-09-21 まで Plan() は rank でしか分岐せず、defaults の omoya は**足しても
        //    建つ姿が変わらない**欄だった(typology_check の inert_defaults が毎朝刷っていた)。
        public string omoya;
        // ⭐ 区画にだけ在って、ビルダーが名を読みもしなかった三つ(EDO-0327・規則19)。
        //    ⛔ 使い道が決まらない欄でも**黙って捨てない** — 読んで log に刷る。
        public string hoshiba;               // 干場の種別 konya 紺屋 / kappa 合羽(4区画)
        public int tacchu;                   // 塔頭(子院)の数(澄泉寺=3)
        public bool tokinokane;              // 時の鐘(成満寺=江戸の二番鐘)
        // 前庭の奥行の狙い[間](EDO-0372)。0 ならビルダーの既定(4間と白洲が描ける広さの大きい方)。
        //    狭い筆で狙いが強すぎる・広い筆でもっと空けたいときは、コードでなくこの欄を書き換える。
        public int maeniwaKen;
        // 寺社の棟を絵図から採った(EDO-0477・山王御宮絵図の観理院)。true なら棟数の目安(4 + 500坪ごとに1)で足さない。
        //    ⛔ 絵図に在る棟だけ建つ ── 南の空きを埋めるために推定の蔵・物置を足さない(規則7)。
        public bool muneZu;
        public bool kyakuden, gomado;        // 絵図に在る客殿・護摩堂(mune_zu の筆だけ読む)
        public bool kodachi;                 // 絵図で棟の無い空きに木の点(境内の庭に明地の木立を入れる)
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
    /// <summary>整数の配列(`main_hall_ken` = [桁行, 梁間] など)。無い・短いときは null。</summary>
    static int[] IA(Dictionary<string, object> d, string k)
    {
        object v; if (!d.TryGetValue(k, out v)) return null;
        var l = v as List<object>; if (l == null) return null;
        var r = new int[l.Count];
        for (int i = 0; i < r.Length; i++)
        {
            double o; if (!double.TryParse(l[i].ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out o)) return null;
            r[i] = (int)o;
        }
        return r;
    }
    static bool Bo(Dictionary<string, object> d, string k, bool dflt)
    {
        object v; if (!d.TryGetValue(k, out v) || v == null) return dflt;
        bool o; if (bool.TryParse(v.ToString(), out o)) return o; return dflt;
    }

    static Dictionary<string, object> _defs;

    /// <summary>この区画の類型に当たる <c>defaults</c> の塊。⭐ 鍵は型ごとに違う —
    /// buke は <c>rank_yashiki</c>(daimyo_kami)→ 無ければ <c>rank</c>(hatamoto_mid)、
    /// jisha は <c>kind</c>、machiya と kouyuu は入れ子が無いので塊そのもの。
    /// ⛔ 格が表に無いときは **null を返す** — 別の格の既定を借りると、書いていない物が建つ。</summary>
    static Dictionary<string, object> DefaultsFor(Dictionary<string, object> d)
    {
        if (_defs == null) return null;
        string type = S(d, "type"); if (type == null) return null;
        object br; if (!_defs.TryGetValue(type, out br)) return null;
        var branch = br as Dictionary<string, object>; if (branch == null) return null;
        string[] keys;
        if (type == "buke") keys = new[] { S(d, "rank") + "_" + S(d, "yashiki"), S(d, "rank") };
        else if (type == "jisha") keys = new[] { S(d, "kind") };
        else return branch;
        foreach (var k in keys)
        {
            object v; if (k == null || !branch.TryGetValue(k, out v)) continue;
            var dd = v as Dictionary<string, object>; if (dd != null) return dd;
        }
        return null;
    }

    /// <summary>区画に**書いていない**欄だけ既定で埋める(表の `_` の約束「区画の欄が null のとき
    /// ビルダーがここから採る」の実装)。⛔ 2026-09-21 まで LoadTable は parcels しか読んでおらず、
    /// この約束は**一度も効いていなかった** — defaults へ欄を足しても建つ姿は変わらなかった(EDO-0304)。
    /// ⛔ 区画に書いてある値を既定で上書きしない。`_` で始まる覚書の欄と、既定側の典拠 `src` は差さない。</summary>
    static void Fill(Dictionary<string, object> d, Dictionary<string, object> def)
    {
        if (def == null) return;
        foreach (var kv in def)
        {
            if (string.IsNullOrEmpty(kv.Key) || kv.Key[0] == '_' || kv.Key == "src") continue;
            object cur; if (d.TryGetValue(kv.Key, out cur) && cur != null) continue;
            d[kv.Key] = kv.Value;
        }
    }

    public static void LoadTable()
    {
        _table = new Dictionary<string, Spec>();
        if (!File.Exists(TablePath)) { Debug.LogError("類型表が無い: " + TablePath); return; }
        var root = EdoMiniJson.Parse(File.ReadAllText(TablePath)) as Dictionary<string, object>;
        if (root == null) { Debug.LogError("類型表が読めない: " + TablePath); return; }
        object df; _defs = root.TryGetValue("defaults", out df) ? df as Dictionary<string, object> : null;
        if (_defs == null) Debug.LogWarning("類型表に defaults が無い — 区画に書いた欄だけで建てる");
        object ps; if (!root.TryGetValue("parcels", out ps)) { Debug.LogError("類型表に parcels が無い"); return; }
        var dict = ps as Dictionary<string, object>;
        foreach (var kv in dict)
        {
            var d = kv.Value as Dictionary<string, object>; if (d == null) continue;
            Fill(d, DefaultsFor(d));                 // ⭐ 既定を差してから読む(区画の値が勝つ)
            YuragiFields(kv.Key, d);                 // ⭐ 揺らぎ(EDO-0476)── 史料値でない欄を表の幅の中で区画ごとに(EdoTypologyBuilder.Yuragi.cs)
            var s = new Spec
            {
                id = kv.Key, raw = d,
                type = S(d, "type"), built = S(d, "built"), note = S(d, "note"), source = S(d, "source"),
                rank = S(d, "rank"), yashiki = S(d, "yashiki"), kind = S(d, "kind"),
                gate = S(d, "gate"), bansho = S(d, "bansho"), enclosure = S(d, "enclosure"),
                garden = S(d, "garden"), surface = S(d, "surface"), fence = S(d, "fence"),
                building = S(d, "building"), front = S(d, "front"),
                kura = I(d, "kura", 0), units = I(d, "units", 1), koku = I(d, "koku", 0),
                umaya = I(d, "umaya", 0), komeKura = I(d, "kome_kura", 0),
                sakujiKoya = I(d, "sakuji_koya", 0), hikeshiKura = I(d, "hikeshi_kura", 0),
                kagoKura = I(d, "kago_kura", 0), monooki = I(d, "monooki", 0),
                baba = Bo(d, "baba", false),
                houses = I(d, "houses", 0), maguchiKen = I(d, "maguchi_ken", 5), depthKen = I(d, "depth_ken", 18),
                twoSided = Bo(d, "two_sided", false), jishinban = Bo(d, "jishinban", false),
                inari = Bo(d, "inari", false),
                kuri = Bo(d, "kuri", true), yagura = Bo(d, "yagura", false),
                shoro = Bo(d, "shoro", false), sanmon = Bo(d, "sanmon", false),
                graveyard = Bo(d, "graveyard", false),
                omoya = S(d, "omoya"), hoshiba = S(d, "hoshiba"),
                tacchu = I(d, "tacchu", 0), tokinokane = Bo(d, "tokinokane", false),
                maeniwaKen = I(d, "maeniwa_ken", 0), muneZu = Bo(d, "mune_zu", false),
                kyakuden = Bo(d, "kyakuden", false), gomado = Bo(d, "gomado", false), kodachi = Bo(d, "kodachi", false),
            };
            var hall = IA(d, "main_hall_ken");
            if (hall != null && hall.Length >= 2) { s.hallW = hall[0]; s.hallD = hall[1]; }
            var ed = d.TryGetValue("enclosure_dir", out var edo) ? edo as Dictionary<string, object> : null;
            if (ed != null) s.encDir = ed.Where(q => q.Value is string).ToDictionary(q => q.Key, q => (string)q.Value);
            // ⭐ 町屋の門(EDO-0503 考証方): 表の gate が空なら、裏長屋のある町は**路地木戸**(komon)・無い町は**門を置かない**。
            //    ⛔ 2026-10-01 まで空の gate が GatePath の既定=冠木門(武家・寺社の門)へ落ち、表店の列の真ん中に立っていた。
            if (s.type == "machiya" && string.IsNullOrEmpty(s.gate))
                s.gate = I(d, "ura_nagaya", -1) == 0 ? "none" : "komon";
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
        var gpath = PickGatePath(s, edges);
        float need = GateWidth(s, gpath) * 1.25f;
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
                if (fitAligned.Count > 0) return fitAligned[0];
                // ⛔ 門構えが載りきらない辺には建てない(硬い)。方位は狙い(柔らかい)── 載る接道辺があればそちらへ移して ⚠ を刷る。
                //   載らない辺に建てると袋小路の奥で両翼が隣の区画の塀と食い違い、門の脇が閉じなかった(三べ坂 阿部・内藤 EDO-0491)
                var fitAny = roads.Where(e => e.len >= need).OrderByDescending(e => e.len).ToList();
                if (fitAny.Count > 0)
                {
                    warn = string.Format("表に書いた方位 {0} の接道辺(最長 辺{1} {2:F1}m)に門構え {3}(約{4:F0}m・余裕込み {5:F0}m)が載らない"
                                       + " — 載る接道辺 辺{6} {7:F1}m へ移した(方位は狙い・柔らかい)", s.front, aligned[0].i, aligned[0].len,
                                       s.gate, GateWidth(s, gpath), need, fitAny[0].i, fitAny[0].len);
                    return fitAny[0];
                }
                warn = string.Format("⛔ 接道辺のどこにも門構え {0}(約{1:F0}m・余裕込み {2:F0}m)が載らない — 門の型を口に合う物へ下げる(類型表の gate)",
                                     s.gate, GateWidth(s, gpath), need);
                return aligned[0];
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
    /// <summary>表店の**店先が掛かる区画の線の上の区間**(EDO-0503)。店の向き(+Z = 店先)の側で最も近い辺を採り、
    /// 足あとの凸包をその辺へ射影した [最小, 最大] を返す。辺が採れなければ null(束ねる従来の平場になる)。</summary>
    static EdoBuild.MonPad ShopFront(Vector2[] poly, Transform t, Vector2[] hull)
    {
        var f3 = t.forward; var f = new Vector2(f3.x, f3.z); if (f.sqrMagnitude < 1e-6f) return null; f.Normalize();
        Vector2 fp = hull[0]; foreach (var q in hull) if (Vector2.Dot(q, f) > Vector2.Dot(fp, f)) fp = q;
        int best = -1; float bd = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 p0 = poly[i], p1 = poly[(i + 1) % poly.Length], d = p1 - p0; if (d.sqrMagnitude < 1e-6f) continue;
            var n = new Vector2(d.y, -d.x).normalized; if (Mathf.Abs(Vector2.Dot(n, f)) < 0.7f) continue;   // 店先に向き合う辺だけ
            float e = EdoGeom.DistToEdge(fp, p0, p1); if (!float.IsNaN(e) && e < bd) { bd = e; best = i; }
        }
        if (best < 0 || bd > 1.5f) return null;
        Vector2 a0 = poly[best], a1 = poly[(best + 1) % poly.Length], dd = a1 - a0; float L2 = dd.sqrMagnitude;
        float t0 = float.MaxValue, t1 = float.MinValue;
        foreach (var q in hull) { float tt = Vector2.Dot(q - a0, dd) / L2; t0 = Mathf.Min(t0, tt); t1 = Mathf.Max(t1, tt); }
        t0 = Mathf.Clamp01(t0); t1 = Mathf.Clamp01(t1); if (t1 - t0 < 1e-4f) return null;
        return new EdoBuild.MonPad { foot = hull, a = a0 + dd * t0, b = a0 + dd * t1 };
    }

    static bool Seat(GameObject go, List<string> log)
    {
        try { EdoBuild.SeatOnGround(go, 0f, VERTS); return true; }
        catch (Exception ex) { log.Add("    ⛔ " + go.name + " を据えられない: " + ex.Message); return false; }
    }
    /// <summary>門構えの駒を据える(<see cref="EdoBuild.SeatGamae"/> ── 札の contact の部材で当てる)。</summary>
    static bool SeatGamae(GameObject go, List<string> log)
    {
        try { EdoBuild.SeatGamae(go, VERTS); return true; }
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
    /// <summary>門の語 → 部材の道(札の試験 EdoPartSpecTests が読む)。</summary>
    public static string GatePathOf(string g) { return GatePath(g); }
    static string GatePath(string g)
    {
        switch (g)
        {
            case "kmon": return EdoAssets.Eg.Kmon;
            case "nagayamon": return EdoAssets.Eg.Nagayamon;
            case "hmon": return EdoAssets.Eg.Hmon;
            case "kabukimon": return EdoAssets.Eg.Kabukimon;
            // ⭐ 格の梯子(部材方 EDO-0318 ①②・2026-09-21 結線)。棟門 3.60 < 薬医門 4.41 < 山門 5.12(棟天端)。
            //    ⛔ 2026-09-21 までこの3つは全部 Eg.Kabukimon(冠木門)へ落ちていて**格が3段違って**いた。
            case "munemon": return EdoAssets.Own.Munamon(2.727f);   // 棟門(門口1.5間)
            case "yakuimon": return EdoAssets.Own.Yakuimon;         // 薬医門(社家)
            case "sanmon": return EdoAssets.Own.Sanmon;             // 山門=四脚門(寺)
            case "komon": return EdoAssets.Eg.KidoOpen;
            default: return EdoAssets.Eg.Kabukimon;
        }
    }

    /// <summary>門構えの幅の目安[m](表門の辺を選ぶため)= 門の札の脇の面の間 × 倍率(EDO-0491)。
    /// ⛔ 2026-09-29 まで型ごとの数の表(長屋門 23・薬医門 5.06 …)と倍率の表(GateScale)を持っていた ── 札と二重になるので廃した。
    /// 札の無い門は 6m(その門は Stage 1 で退けられて建たない)。</summary>
    static float GateWidth(Spec s, string path)
    {
        var sp = EdoPartSpec.Get(path);
        if (sp == null || sp.jambL == null || sp.jambR == null) return 6f;
        float w = (sp.jambR.x - sp.jambL.x) * sp.unitScale;
        // ⭐ 番所も門構えの幅に入れる(札の脇の面の間)── 門だけで測ると内藤の前辺 28.9m に門+番所2 27.9m が「載る」と出た(EDO-0491)
        var bs = EdoPartSpec.Get(EdoAssets.Eg.Bansho);
        if (bs != null && bs.jambL != null && bs.jambR != null)
            w += BanshoCount(s.bansho) * Mathf.Abs(bs.jambR.x - bs.jambL.x) * bs.unitScale;
        return w;
    }
    /// <summary>門の語の駒の候補(大きい順)。⭐ 冠木門は在庫の袖付き(幅 8.0m)と袖無し(2間・部材方 2026-09-30)の二つ ──
    /// 型は類型表の語のまま、接道辺に載る方を採る(施主裁定A 2026-09-30「袖の無い冠木門を新しく部材として起こす」・三べ坂 w1 の接道 6.9m)。</summary>
    static string[] GateChoices(string g)
    {
        if (g == "kabukimon" || string.IsNullOrEmpty(g)) return new[] { EdoAssets.Eg.Kabukimon, EdoAssets.Own.KabukimonNoSode };
        return new[] { GatePath(g) };
    }
    /// <summary>接道辺のどれかに門構え(×1.25)が載る最も大きい候補。どれも載らなければ最も大きい物(FrontEdge が ⛔ を刷る)。</summary>
    static string PickGatePath(Spec s, List<Edge> edges)
    {
        var ch = GateChoices(s.gate);
        var roads = edges.Where(e => e.kind == EdgeKind.Road).ToList(); if (roads.Count == 0) roads = edges;
        float longest = roads.Count > 0 ? roads.Max(e => e.len) : 0f;
        foreach (var p in ch) if (longest >= GateWidth(s, p) * 1.25f) return p;
        return ch[0];
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

    /// <summary>シーンのルートを名前で引く。⭐ **寝ているルートも拾う** —
    /// 撤去は SetActive(false) の決まり(規則1)なので、GameObject.Find だけでは見落とす。</summary>
    static GameObject FindRoot(string name)
    {
        var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        foreach (var r in sc.GetRootGameObjects()) if (r.name == name) return r;
        return null;
    }

    /// <summary>建て終えた類型ルートを **1軒1プレハブ** へ切り出す(EDO-0296)。
    ///
    /// <para>なぜ: LFS は1コミットで書き換わったファイルを丸ごと保存するので、全部が
    /// `Akasaka.unity` に生で載っていると、どの1区画を直しても**シーン全量**が保存量に乗る。
    /// 79区画を類型で建てると、その全部が1枚のシーンへ直に書き込まれる。屋敷・町・寺社の
    /// 手組みルート83本は既に `EdoYashikiPrefab` で1軒1ファイルに割ってあり、
    /// **類型ルートだけがその仕組みに載っていなかった**。</para>
    ///
    /// <para>⚠ 切り出しはビルダーの側でやる。`EdoYashikiPrefabAutoSave`(保存時の自動書き戻し)は
    /// **既にプレハブ資産がある**ルートしか書き戻さないので、新しく生えたルートは何度保存しても
    /// 生のまま残る。⛔ 逆に「大きい新ルートは全部プレハブにする」を保存側へ入れてはいけない —
    /// 手組み資産や検分用の仮ルートまで勝手に焼き付く(規則1)。</para></summary>
    static string Externalize(Transform root)
    {
        var f = EdoYashikiPrefab.One(root.gameObject).Split('\t');
        if (f.Length >= 3 && f[2] == "OK")
            return string.Format("  プレハブ: {0}/{1}.prefab へ切り出した(駒 {2})— シーンに残るのは参照だけ",
                                 EdoYashikiPrefab.Dir, f[0], f[1]);
        return "  ⛔ プレハブへの切り出しに失敗(シーンに生で残る): " + string.Join(" ", f);
    }

    /// <summary>棟の足あとの外へ平らに取る幅[m](犬走り・雨落ち)。【確度 U】一般類型 ── 史料の値が取れたら表の欄へ上げる。</summary>
    const float ZOSEI_MARGIN = 1.0f;

    public static string BuildParcel(string id, bool force)
    {
        Spec s; if (!Table.TryGetValue(id, out s)) return "⛔ 類型表に無い区画: " + id;
        if (s.Hand) return "— " + id + " は図を起こして建てた敷地(built:hand)。触らない: " + s.note;

        string gname = "Edo_Typo_" + id;
        // ⛔ GameObject.Find は**活きている**ルートしか拾わない。撤去は SetActive(false) の決まり
        //    (規則1)なので、寝ているルートを見落とすと同名の2本目が生え、プレハブ資産がどちらの
        //    姿で焼かれたか分からなくなる(EDO-0296)。シーンのルートを直に舐めて拾う。
        var old = FindRoot(gname);
        if (old != null && !force) return "— " + gname + " は既にある(force で建て直す)";
        // ⭐ 古い井戸が抜いた地形の穴を塞ぐ(置き場が変わると穴が地面に残る・EDO-0490)。シーンに無ければ資産から読む
        FillIdoHoles(old != null ? old
            : AssetDatabase.LoadAssetAtPath<GameObject>(EdoYashikiPrefab.Dir + "/" + gname + ".prefab"));
        if (old != null) UnityEngine.Object.DestroyImmediate(old);
        var root = Group(gname, null);

        var poly = EdoParcels.Get(id);
        if (poly == null || poly.Length < 3) return "⛔ 区画の形が無い: " + id;
        // ⭐ 造成は毎回**造成前の地盤**から起こす(2026-09-27・EDO-0477 P1)── 区画の中を base_dem へ戻してから置く。
        //   置き場の選びも前の巡の平場に引きずられない(二度建てても同じ姿)。⛔ 区画の外(道・隣)は触らない。
        string restoreNote;
        EdoBuild.GradePads(poly, new List<Vector2[]>(), 0f, out restoreNote);
        // ⭐ 区画に接する道のうち、指図で造成すると決めた道(欄の zosei)を均す(冪等・区画の中は触らない・2026-09-30 EDO-0495)
        string michiNote = EdoBuild.GradeMichiNear(poly);
        float spread, pad;
        try { pad = Pad(id, out spread); }
        catch (Exception ex) { return "⛔ " + id + ": 面の高さが測れない — " + ex.Message; }
        var edges = Edges(id);
        string frontWarn; var front = FrontEdge(s, edges, out frontWarn);

        var log = new List<string>();
        if (!string.IsNullOrEmpty(michiNote)) log.Add("  " + michiNote);
        log.Add(string.Format("{0}: 面 y={1:F2}(区画内の自然地形の中央値 / 起伏 {2:F2}m。棟の下は Stage 4z で平場を採る)", id, pad, spread));
        if (frontWarn != null) log.Add("  ⚠ " + frontWarn);
        log.Add(string.Format("  辺 {0}: 接道 {1} / 隣と共有 {2}(うち当方持ち {3})", edges.Count,
            edges.Count(e => e.kind == EdgeKind.Road), edges.Count(e => e.kind == EdgeKind.Shared),
            edges.Count(e => e.kind == EdgeKind.Shared && e.mine)));

        EdoBuild.NaturalMode = true;   // 地形追従(造成しない)

        // ── Stage 1: 門構え(**固定側を先に置く** — 置き方の4手①) ──
        // ⭐ 2026-09-29(EDO-0491・施主「ベストプラクティスに基づいた開発に」): 門構えの位置は**部材の札**から一度で解く
        //    (EdoBuild.PlaceGamae ── 横・奥行・番所・区画の線・塀の口)。据え(高さ)だけ地形を実測する。
        //    ⛔ 2026-09-29 まで門構えを段ごとに別の物差しで生メッシュから推し量っていた(帯 0.3〜0.6H の頂点で横と口・
        //    材の名で屋根を落とした全部で区画の線 = 薬医門の軒の木組みを壁体と数えて 2.08m 下げた・建った塀の面の中央値で奥行)。
        //    さらに塀の口は門が動く前に決まり、下げても塀は追わなかった ── 十坊の表門の脇に 1.9m の隙。→ docs/oki-kata.md §8
        var monGrp = Group("Mon", root);
        var gamae = new List<GameObject>();                  // 門構え(門・番所)
        float psi = Mathf.Atan2(front.outward.x, front.outward.y) * Mathf.Rad2Deg;
        var along = (front.b - front.a).normalized;
        float gateHalf = -1f; Vector2 gateC = front.mid;     // 塀の口(囲い・町屋の列が読む)
        Vector2 passageC = front.mid;                        // 門の通り口の芯(参道・庭・本堂の軸が読む)── 番所が片方だけだと口の芯とずれる
        // ⭐ 町屋の通りの側の囲いは**表店の壁そのもの**(EDO-0325)。辺を選ぶのは Stage 3m と同じ関数なので、列の載る辺と必ず一致する。
        var machiyaFronts = MachiyaFrontEdges(s, edges, front);
        string frontKind = machiyaFronts.Contains(front) ? "none" : EnclosureFor(s, front, true);
        string faceHow, biteHow; float nagayaTuck;
        float faceOut = EdoBuild.FenceOuterFace(frontKind, out faceHow);
        float bite = EdoBuild.FenceBite(frontKind, out nagayaTuck, out biteHow);
        EdoBuild.Gamae gm = null;
        GameObject mon = null;
        var bansho = new List<GameObject>();
        if ((s.type != "kouyuu" || s.building == "hikeshi") && s.gate != "none")
        {
            var gp = PickGatePath(s, edges); var gs = EdoPartSpec.Get(gp);
            if (gp != GatePath(s.gate)) log.Add("  門 " + s.gate + ": 在庫の駒は接道辺に載らない ── 同じ型の小さい駒 " + System.IO.Path.GetFileNameWithoutExtension(gp) + " を採った");
            if (gs == null)
                log.Add("  ⛔ 門 " + s.gate + " の部材に札が無い(" + gp + ")── 推し量りで置かずに退けた(硬い)。Edo/部材/取り合いの札を焼く か Blender の write_spec");
            else if (float.IsNaN(faceOut) || float.IsNaN(bite))
                log.Add("  ⛔ 前辺の囲い " + frontKind + " の駒に札が無い ── 門構えを退けた(硬い)。" + faceHow + " " + biteHow);
            else
            {
                mon = EdoBuild.Place(gp, new Vector3(gateC.x, pad, gateC.y), psi, Vector3.one * gs.unitScale, monGrp, "Mon_" + s.gate);
                int nb = BanshoCount(s.bansho);
                for (int k = 0; k < nb; k++)
                {
                    var bs = EdoBuild.Place(EdoAssets.Eg.Bansho, new Vector3(gateC.x, pad, gateC.y), psi, Vector3.one * ES, monGrp, "Bansho_" + k);
                    if (bs != null) bansho.Add(bs);
                }
                // ⭐ 置き場 = 表の辺の上で道がいちばん平らな所(柔らかい・EdoBuild.FlattestStation)── 門の敷居は水平なので、道の傾きぶん下手が浮く
                float sr, srMid; var station = EdoBuild.FlattestStation(front.a, front.b, GateWidth(s, gp) * 0.5f, out sr, out srMid);
                if (Vector2.Distance(station, front.mid) > 0.25f)
                    log.Add(string.Format("  ⚠ 門構えを辺の中央から {0:F1}m 寄せた ── 幅の中の道の高さの差 {1:F2}m → {2:F2}m(道がいちばん平らな所・柔らかい)",
                                          Vector2.Distance(station, front.mid), srMid, sr));
                else log.Add(string.Format("  門構えの置き場: 辺の中央(幅の中の道の高さの差 {0:F2}m)", sr));
                try { gm = EdoBuild.PlaceGamae(mon, bansho, front.a, front.b, front.outward, station, poly, faceOut, bite, EdoBuild.FenceDepth(frontKind)); }
                catch (Exception ex)
                {
                    log.Add("  ⛔ 門構えを札で置けない: " + ex.Message + " ── 退けた(硬い)");
                    foreach (var b in bansho) UnityEngine.Object.DestroyImmediate(b);
                    UnityEngine.Object.DestroyImmediate(mon); mon = null; bansho.Clear();
                }
            }
        }
        if (mon != null)
        {
            SeatGamae(mon, log); foreach (var bs in bansho) SeatGamae(bs, log);   // 据えは高さだけ(平面は札で決まっている)
            gamae.Add(mon); gamae.AddRange(bansho);
            gateC = gm.gapC; gateHalf = gm.gapHalf; passageC = gm.passageC;
            log.Add(string.Format("  門: {0}(辺{1}・外向き {2:F0}°)— 札で置いた: 通り口 {3:F2}m・門構えの幅 {4:F2}m・塀の口 {5:F2}m"
                                  + "(番所 {6})・正面と塀の外の面の差 {7:+0.000;-0.000}m(柔らかい)",
                                  s.gate, front.i, psi, gm.passageHalf * 2f, gm.jHi - gm.jLo, gm.gapHalf * 2f, bansho.Count, gm.faceResid));
            log.Add("    塀の口: " + faceHow + " / " + biteHow);
            foreach (var nt in gm.notes) log.Add("    " + nt);
        }

        // ── Stage 2: 囲い(**可動側** — 開口は門構えの実測 — 置き方の4手②) ──
        var encl = Group("Kakoi", root);
        var kakoiNotes = new List<string>();
        // ⭐ 囲いは造成の後でもう一度建てる(施主の規則「造成の後で全部据え直す」)ので、一手にまとめる。
        Action buildKakoi = () =>
        {
            for (int c = encl.childCount - 1; c >= 0; c--) UnityEngine.Object.DestroyImmediate(encl.GetChild(c).gameObject);
            // ⭐ 生垣・林縁帯の株は区画の外へ出さない(硬い・EDO-0495)── 塀と同じ輪郭で退ける
            EdoBuild.PlantInside = poly;
            kakoiNotes.Clear();
            // ⭐ 長屋の辺を先に建てる(EDO-0500)── 隅の隣が当方の塀なら、長屋は端数を埋めず「足」を返す。塀の辺は
            //    長屋の外面の線で折り、足(外面の線に沿って鎖の端まで)を塀の鎖に足して**同じ塀**で回す。
            //    ⛔ 2026-10-01 まで: 練塀は区画の隅まで行き、長屋との間を低い板塀で埋めた ── 丈が合わず練塀の端が 1.5m 出た(施主指摘)。
            Func<Edge, string> kindOf0 = x => machiyaFronts.Contains(x) ? "表店" : EnclosureFor(s, x, x == front);
            Func<Edge, bool> fenced = x => x != null && !(x.kind == EdgeKind.Shared && !x.mine) && !machiyaFronts.Contains(x)
                                            && kindOf0(x) != "nagaya" && kindOf0(x) != "none";
            Func<Edge, bool> nagOf = x => x != null && !(x.kind == EdgeKind.Shared && !x.mine) && !machiyaFronts.Contains(x) && kindOf0(x) == "nagaya";
            var legs = new List<EdoBuild.NagayaLeg>();
            var kados = new List<EdoBuild.NagayaKado>();   // 長屋どうしの出隅は隅長屋で納める(EDO-0500)
            foreach (var e in edges)
            {
                if (e.kind == EdgeKind.Shared && !e.mine) continue;
                if (machiyaFronts.Contains(e) || kindOf0(e) != "nagaya") continue;
                bool isFront = (e == front);
                var ePrev = edges.FirstOrDefault(x => x != e && (x.b - e.a).sqrMagnitude < 1e-4f);
                var eNext = edges.FirstOrDefault(x => x != e && (x.a - e.b).sqrMagnitude < 1e-4f);
                EdoBuild.NagayaRun(encl, e.a, e.b, e.outward, pad, isFront ? gateC : Vector2.zero, isFront ? gateHalf : -1f,
                                   "nagaya_" + e.i, poly, nagayaTuck,          // 門へ差す量は長屋の駒の札から(EDO-0491)
                                   fenced(ePrev), fenced(eNext), legs, nagOf(ePrev), nagOf(eNext), kados,
                                   ePrev != null ? ePrev.outward : Vector2.zero, eNext != null ? eNext.outward : Vector2.zero);
            }
            foreach (var nt in EdoBuild.NagayaKadoPlace(encl, kados, "nagaya")) kakoiNotes.Add(nt);
            // 塀の辺: 足のある隅で、辺の端を長屋の外面の線(足の芯)との交点へ移し、足の辺を継ぎ足す
            var fe = new List<Edge>(); var legKind = new Dictionary<Edge, string>();
            foreach (var e in edges) fe.Add(e);
            float lhOut, lhIn;
            foreach (var lg in legs)
            {
                int k = fe.FindIndex(x => !(x.kind == EdgeKind.Shared && !x.mine) && kindOf0(x) != "nagaya" && kindOf0(x) != "none"
                                          && ((x.a - lg.corner).sqrMagnitude < 1e-4f || (x.b - lg.corner).sqrMagnitude < 1e-4f));
                if (k < 0) continue;
                var fx = fe[k]; string fk = kindOf0(fx);
                EdoBuild.FenceFaceOffsets(fk, out lhOut, out lhIn);
                bool endAtB = (fx.b - lg.corner).sqrMagnitude < 1e-4f;
                var fd = endAtB ? (fx.a - fx.b).normalized : (fx.b - fx.a).normalized;   // 隅から辺の奥へ
                float dn = Vector2.Dot(fd, lg.outward);
                if (Mathf.Abs(dn) < 0.2f) { kakoiNotes.Add("辺" + fx.i + " ⚠ 長屋の辺とほぼ平行で折れない ── 足を回さない"); continue; }
                float off = lg.inset + lhOut;                                   // 足の芯 = 長屋の外面から塀の外の半厚だけ内
                var P1 = lg.corner + fd * (-off / dn);
                var rd = (lg.chainEnd - lg.corner).normalized; float tEnd = Vector2.Dot(lg.chainEnd - lg.corner, rd);
                var P2 = lg.corner - lg.outward * off + rd * Mathf.Max(tEnd + 0.05f, Vector2.Dot(P1 - lg.corner, rd) + 0.30f);   // 妻へ 0.05 差す
                var nf = new Edge { i = fx.i, a = endAtB ? fx.a : P1, b = endAtB ? P1 : fx.b, outward = fx.outward, kind = fx.kind, neighbour = fx.neighbour, mine = fx.mine };
                nf.len = (nf.b - nf.a).magnitude; nf.mid = (nf.a + nf.b) * 0.5f;
                var leg = new Edge { i = 100 + fx.i, a = endAtB ? P1 : P2, b = endAtB ? P2 : P1, outward = lg.outward, kind = fx.kind, neighbour = fx.neighbour, mine = true };
                leg.len = (leg.b - leg.a).magnitude; leg.mid = (leg.a + leg.b) * 0.5f;
                fe[k] = nf; fe.Insert(endAtB ? k + 1 : k, leg); legKind[leg] = fk;
                legKind[nf] = fk;                                               // 移した辺は向きでなく元の辺の種別を引き継ぐ
                kakoiNotes.Add(string.Format("辺{0} 隅で長屋の外面(線から {1:F2}m 内)へ折り、長屋の妻まで {2:F2}m 回す(足 辺{3})", fx.i, lg.inset, leg.len, leg.i));
            }
            Func<Edge, string> kindOf = x => legKind.ContainsKey(x) ? legKind[x] : kindOf0(x);
            // ⭐ 練塀は段塀で建てる(2026-09-29 EDO-0477 施主裁定1=B)── 続いた練塀の辺を一つの鎖にして区切りを引く
            //    (段を区画の角から離すため・角を挟んで座を揃えるため)。当たる先: 類型の全区画の練塀。
            var danOf = new Dictionary<Edge, KeyValuePair<float, List<EdoBuild.DanSec>>>();
            {
                Func<Edge, bool> isDan = x => !(x.kind == EdgeKind.Shared && !x.mine) && !machiyaFronts.Contains(x) && kindOf(x) == "dobei";
                var done = new HashSet<Edge>();
                foreach (var e0 in fe)
                {
                    if (done.Contains(e0) || !isDan(e0)) continue;
                    var head = e0; int guard = 0;
                    while (guard++ < fe.Count)
                    {
                        var pv = fe.FirstOrDefault(x => x != head && isDan(x) && (x.b - head.a).sqrMagnitude < 1e-4f);
                        if (pv == null || pv == e0) break;
                        head = pv;
                    }
                    var chain = new List<Edge> { head }; done.Add(head);
                    while (true)
                    {
                        var last = chain[chain.Count - 1];
                        var nx = fe.FirstOrDefault(x => !done.Contains(x) && isDan(x) && (x.a - last.b).sqrMagnitude < 1e-4f);
                        if (nx == null) break;
                        chain.Add(nx); done.Add(nx);
                    }
                    var pts = new List<Vector2> { chain[0].a }; foreach (var x in chain) pts.Add(x.b);
                    // ⭐ 門の口を鎖の道のりで渡す ── 門は水平な区間の真ん中に立ち、左右 3間 は区切らない(EDO-0514 案A)。⛔ 渡さないと門が平らな区間の片寄りに立った(樹下の表門)
                    var gaps = new List<Vector2>();
                    {
                        float cg = 0f;
                        foreach (var x in chain)
                        {
                            bool xFront = edges.Contains(x) ? x == front : (front != null && x.i == front.i);
                            if (xFront && gateHalf > 0f)
                            {
                                float gt = Vector2.Dot(gateC - x.a, (x.b - x.a).normalized);
                                if (gt + gateHalf > 0f && gt - gateHalf < x.len) gaps.Add(new Vector2(cg + gt - gateHalf, cg + gt + gateHalf));
                            }
                            cg += x.len;
                        }
                    }
                    string dn; var plan = EdoBuild.DanPlan(pts, out dn, gaps);
                    float c0 = 0f;
                    foreach (var x in chain) { danOf[x] = new KeyValuePair<float, List<EdoBuild.DanSec>>(c0, plan); c0 += x.len; }
                    kakoiNotes.Add("辺" + string.Join("・", chain.Select(x => x.i.ToString()).ToArray()) + " " + dn);
                }
            }
            foreach (var e in fe)
            {
                if (e.kind == EdgeKind.Shared && !e.mine) continue;         // 隣が持つ辺は建てない
                if (machiyaFronts.Contains(e))
                {
                    // ⭐ 表店の辺は店の列が通りを受ける ── 辺そのものは囲わない。通りから裏手へ抜ける隙だけを、
                    //    囲いを建て終えた後で EdoBuild.SukimaGates が塞ぐ(下・EDO-0503 施主 2026-10-03)。
                    kakoiNotes.Add("辺" + e.i + " 囲わない — 表店の列が通りを受ける");
                    continue;
                }
                bool isFront = edges.Contains(e) ? e == front : (front != null && e.i == front.i);
                var gc = isFront ? gateC : Vector2.zero;
                var gh = isFront ? gateHalf : -1f;
                string kind = kindOf(e);
                if (kind == "nagaya") continue;                              // 長屋は先に建てた
                string pre = kind + "_" + e.i;
                {
                    // ⭐ 種別を run へ**渡す**(EDO-0324)。⛔ 2026-09-21 まで種別は捨てられていて、
                    //    ita / dobei / ita+ikegaki / ishigaki+hei / yarai / boji / kui が全部おなじ板塀で建っていた。
                    // ⭐ 崖の面の区間は囲わない(施主の規則「崖の線は面の縁だけ囲う・崖の中腹に塀なし」・2026-09-28 EDO-0477)。崖の裾は囲う。
                    float cliffLen;
                    bool dan = kind == "dobei" && danOf.ContainsKey(e);
                    var spans = EdoBuild.CliffFreeSpans(e.a, e.b, e.outward, 2.0f, out cliffLen, dan);
                    if (cliffLen < 1f) spans = new List<float[]> { new[] { 0f, e.len } };
                    var ed = (e.b - e.a).normalized;
                    if (cliffLen >= 1f) kakoiNotes.Add(string.Format("辺{0} 崖の面 {1:F0}m を囲わない(塀が崖を登る{2})", e.i, cliffLen, dan ? "" : "・内の半分が崖の面に掛かる所"));
                    // ⭐ 区画の角は頂点の先へ延ばして口を閉じる(EdoBuild.CornerReach・EDO-0477 P2 隅)
                    float reA, reB; CornerReaches(fe, e, kind, out reA, out reB);
                    for (int si = 0; si < spans.Count; si++)
                    {
                        var sa = e.a + ed * (spans[si][0] - (spans[si][0] < 1e-3f ? reA : 0f));
                        var sb2 = e.a + ed * (spans[si][1] + (spans[si][1] > e.len - 1e-3f ? reB : 0f));
                        float gt = Vector2.Dot(gc - e.a, ed);
                        bool gateHere = gh > 0f && gt >= spans[si][0] && gt <= spans[si][1];
                        string note;
                        // 段塀の区切りを、この区間の始点(角の延ばしを含む)からの道のりへ写す
                        List<EdoBuild.DanSec> ds = null;
                        if (dan)
                        {
                            var dp = danOf[e]; float org = dp.Key + spans[si][0] - (spans[si][0] < 1e-3f ? reA : 0f);
                            ds = dp.Value.Select(x => new EdoBuild.DanSec { a = x.a - org, b = x.b - org, W = x.W }).ToList();
                        }
                        EdoBuild.FenceRun(encl, sa, sb2, e.outward, kind, pad, gateHere ? gc : Vector2.zero, gateHere ? gh : -1f,
                                          spans.Count == 1 ? pre : pre + "s" + si, out note, ds);
                        if (!string.IsNullOrEmpty(note)) kakoiNotes.Add("辺" + e.i + " " + note);
                    }
                }
            }
            // ⭐ 通りから裏手(敷地の内側)へ抜ける隙だけを竪格子の柵で塞ぐ(EDO-0503・施主 2026-10-03「建物と隣の構造物の間に
            //    すき間があり、さらに裏手に敷地の内側に入るようになっているときにふさぐ」)。相手は左右・後ろの棟、区画の端では
            //    隣の区画の建物・塀・石垣・区画の線。⛔ 2026-10-03 まで表店の辺の端の空きの幅で決め、行き止まりにも柵を立てた。
            //    店はまだ無い一巡目は塞がない(造成の後の二巡目で、据えた駒の実メッシュから測る)。
            {
                var tat0 = root.Find("Tatemono");
                bool anyShop = tat0 != null && tat0.Cast<Transform>().Any(t => t.name.StartsWith("Omotedana", StringComparison.Ordinal));
                // ⛔ 2026-10-03 施主裁定A: 隙の柵は機械が探して建てない(区画ごとに数か所ずつ出て、指摘しきれない)。町木戸(Michi)は別で残す。
                const bool SUKIMA_FENCE = false;
                if (SUKIMA_FENCE && anyShop && machiyaFronts.Count > 0)
                {
                    var fr = machiyaFronts.Select(x => new[] { x.a, x.b, x.outward }).ToList();
                    string sn; var gs = EdoBuild.SukimaGates(poly, fr, root, out sn);
                    kakoiNotes.Add(sn);
                    for (int gi = 0; gi < gs.Count; gi++)
                    {
                        string hn;
                        EdoBuild.FenceRunFlush(encl, gs[gi].a, gs[gi].b, gs[gi].outward, "tategoshi", pad, "sukima_" + gi, 0f, out hn);
                        if (!string.IsNullOrEmpty(hn)) kakoiNotes.Add("隙の口" + gi + "(" + gs[gi].between + ") " + hn);
                    }
                }
            }
        };
        try { buildKakoi(); } finally { EdoBuild.PlantInside = null; }
        log.Add("  囲い: " + string.Join(" / ", edges.Where(e => e.mine).Select(
            e => e.i + "=" + (machiyaFronts.Contains(e) ? "表店" : EnclosureFor(s, e, e == front))).ToArray()));
        foreach (var nt in kakoiNotes) log.Add("    " + nt);   // ⛔ 代用を黙って飲まない(規則7・19)

        // ── Stage 2b(廃止・2026-09-29 EDO-0491)── 門構えの奥行と区画の線は Stage 1 の EdoBuild.PlaceGamae が札で解く。
        //    ⛔ 建った塀の面の中央値(FenceFace)へ帯の頂点で寄せ、材の名で屋根を落とした全部で線を越えたら下げる(TuckInside)、を廃した
        //    ── 口が決まった後で門だけ動き、塀が追わなかった(十坊の表門の脇 1.9m)。

        // ── Stage 3〜4: 主屋・付属 ／ 町屋は Stage 3m(表店の列)──
        // ⭐ 町屋を Omoya へ通さない(EDO-0325)。Omoya は「区画の内側の空いた所へ棟を散らす」段で、
        //    通りに面して軒を接して建つ町屋とは置き方が別の物。→ EdoTypologyBuilder.Machiya.cs
        if (s.type == "machiya") log.Add(Machiya(s, root, poly, front, edges, pad, gateC, gateHalf));
        else log.Add(Omoya(s, root, poly, front, pad, passageC));   // 本堂・前庭の軸は通り口の芯(EDO-0491)

        // ── Stage 4z: 造成(平場を採る・2026-09-27 EDO-0477 P1)──
        // ⭐ 棟の足あと(壁体の実メッシュの凸包)ごとに造成前の地盤の中央値を平場に採り、法面(盛土 1:1.5・切土 1:1.0)で
        //    地山へ擦り付ける。区画の縁で地山へ戻す(区画の外へ出さない)。⛔ 2026-09-27 まで類型は造成を一切せず、
        //    斜面の棟は足元の地形なりに傾いた地面へ SeatOnGround で置かれ、下手が浮いた(規則3 の「面は自然の平場」が効いていなかった)。
        // ⭐ 造成の後で**全部据え直す**(施主の規則)── 棟・門・番所を据え直し、囲いは建て直す。庭と植栽はこの後の段なので造成の上に建つ。
        {
            var tat = root.Find("Tatemono");
            var pads = new List<Vector2[]>(); var bldg = new List<GameObject>();
            var faced = new List<EdoBuild.MonPad>();             // 表店の店先の区間(EDO-0503 ── 軒ごとに道の高さへ段を付ける)
            if (tat != null)
                foreach (Transform b in tat)
                {
                    var ws = EdoBuild.Body(b, 2000, false);     // 壁体(屋根・軒を外す ── 軒の下まで平らにしない)
                    if (ws.Count < 3) continue;
                    var xz = ws.Select(w => new Vector2(w.x, w.z)).ToArray();
                    var hull = EdoGeom.HullXZ(xz).Select(k => xz[k]).ToArray();
                    pads.Add(hull);
                    bldg.Add(b.gameObject);
                    faced.Add(b.name.StartsWith("Omotedana", StringComparison.Ordinal) ? ShopFront(poly, b, hull) : null);
                }
            // ⭐ 町屋の稲荷(群 Yashiro)も平場を採り、浮けば布石で受ける(EDO-0503)── ⛔ 2026-10-02 まで造成の外で、
            //    石垣の際の斜面に据えた小祠が 1.55m 浮いた(門前1・普請検査)。
            var yaG = root.Find("Yashiro");
            if (yaG != null)
                foreach (Transform b in yaG)
                {
                    var ws = EdoBuild.Body(b, 2000, false);
                    if (ws.Count < 3) continue;
                    var xz = ws.Select(w => new Vector2(w.x, w.z)).ToArray();
                    pads.Add(EdoGeom.HullXZ(xz).Select(k => xz[k]).ToArray());
                    bldg.Add(b.gameObject); faced.Add(null);
                }
            // ⭐ 門構え(門+番所)の足元も平場にする ── 札の foot を世界へ写した凸包。⛔ 2026-09-30 まで造成は棟の下だけで、
            //   門は坂なりの地面へ「いちばん高く触れる点」で据わり、下り側の柱が浮いた(45 区画中 40・最大 7.24m・EDO-0491)
            // ⭐ 門構えの平場は別扱いで渡す(2026-09-30)── 高さ = 区画の線の上の区間の地盤(道の高さ)・その区間は縁の帯を外す(EdoBuild.MonPad)
            int gamaePad = -1; EdoBuild.MonPad monPad = null;
            if (mon != null)
            {
                var gf = new List<Vector2>();
                foreach (var g in gamae) { var sp = EdoBuild.SpecOf(g); if (sp != null && sp.foot != null) gf.AddRange(EdoPartSpec.FootWorld(sp, g.transform)); }
                if (gf.Count >= 3)
                {
                    var ga = gf.ToArray(); var ed = front.b - front.a; float L2 = ed.sqrMagnitude, t0 = float.MaxValue, t1 = float.MinValue;
                    foreach (var q in ga) { float t = Vector2.Dot(q - front.a, ed) / L2; t0 = Mathf.Min(t0, t); t1 = Mathf.Max(t1, t); }
                    t0 = Mathf.Clamp01(t0); t1 = Mathf.Clamp01(t1);
                    monPad = new EdoBuild.MonPad { foot = EdoGeom.HullXZ(ga).Select(k => ga[k]).ToArray(), a = front.a + ed * t0, b = front.a + ed * t1 };
                    gamaePad = pads.Count;
                }
            }
            if (pads.Count > 0 || monPad != null)
            {
                string zn;
                var hb = EdoBuild.GradePads(poly, pads, ZOSEI_MARGIN, out zn, mon: monPad,
                                            faced: faced.Any(f => f != null) ? faced : null);
                log.Add("  " + zn);
                for (int k = 0; k < bldg.Count; k++)
                {
                    Seat(bldg[k], log);
                    // ⭐ 棟の**下端**(当たり)が平場からどれだけ浮き・埋まるかを全棟で測る(docs/oki-kata.md §0a ── 当たりだけを測る)。
                    //    ⛔ UnderfloorGap は軒・庇の下(接する想定の無い所)まで拾い、棟の高さを「浮き」と返した(2026-09-27 観理院 3〜6m)。
                    var rt = EdoBuild.RootToBed(bldg[k], GroundBed, 0.1f);
                    log.Add(string.Format("    平場 {0}: y={1:F2}(足あとの下の地盤の起伏 {2:F2}m)・下端の浮き {3:F3}m / 埋まり {4:F3}m{5}{6}", bldg[k].name, hb[k].y, hb[k].relief,
                                          float.IsNaN(rt.hi) ? 0f : Mathf.Max(0f, rt.hi), float.IsNaN(rt.lo) ? 0f : Mathf.Max(0f, -rt.lo),
                                          (rt.hi > GROUND_TOL || rt.lo < -GROUND_TOL) ? " ⚠(線 ±0.01)" : "",
                                          hb[k].squeezed > 0 ? string.Format("・⚠ 縁に近く平らに取れない節点 {0}", hb[k].squeezed) : ""));
                }
                // ── Stage 4y(崖の縁の石垣)は建てない(2026-09-29 EDO-0477 施主「石垣をなくして」)── 造成(GradePads)は区画の縁で
                //    地山へ戻すので、縁に崖はできない。縁の外が高い所は元の斜面を残して木で覆い、塀は線の上に段塀で建てる。
                //    ⛔ 2026-09-28 の型は塀の真下を平場まで削って石垣を積み、観理院の西に 4.5m の崖を自分で作った。
                // ⭐ 造成の後で棟を据え直して測る(EDO-0472)。⛔ 2026-09-28 まで棟は削りの前にだけ据えて測り、
                //    削りで足元が下がった棟(十坊 智乗院の物置 0.79m)を黙って残した。棟は地面の ±0.01 の内(docs/oki-kata.md §4)
                //    ── 埋めて消さない(埋没に数わる)。浮けば ⛔ で刷り、置き場か平場を直す。
                // ⭐ 浮いた棟は**布石の基壇で受ける**(EdoBuild.BuildingKidan・門構えと同じ型・EDO-0503)── 造成は区画の縁で地山へ戻し、
                //    道は造成しないので、店先を区画の線に置く表店は縁の下りで下手が浮く(⛔ 2026-10-02 まで門前2 で 15/15 棟・最大 1.13m)。
                //    一続きの御殿(子が複数の複合)は棟ごとに測る別の輪なので除く。
                var kiso = root.Find("Kiso"); if (kiso != null) UnityEngine.Object.DestroyImmediate(kiso.gameObject);
                Transform kisoG = null; int kisoN = 0; float kisoWorst = 0f;
                for (int k = 0; k < bldg.Count; k++)
                {
                    Seat(bldg[k], log);
                    var rt2 = EdoBuild.RootToBed(bldg[k], EdoBuild.Ground, 0.1f);
                    // ⭐ 据えは間引いた頂点の当たりなので、間引きが拾わなかった高い所へ下端が埋まる(門前2 で 0.099m)── 全部の下端で測って上げる
                    if (!float.IsNaN(rt2.lo) && rt2.lo < -GROUND_TOL)
                    {
                        bldg[k].transform.position -= new Vector3(0f, rt2.lo, 0f);
                        rt2 = EdoBuild.RootToBed(bldg[k], EdoBuild.Ground, 0.1f);
                    }
                    if (float.IsNaN(rt2.hi) || rt2.hi <= GROUND_TOL) continue;
                    // ⭐ 浮きと埋まりの幅が許容の帯(±GROUND_TOL)に収まるなら、帯の真ん中へ下げて据える(硬い ±0.01 の内)。
                    //    ⛔ 2026-10-02 まで下端を 0 に揃えて止め、新町 rb の表店が 0.012m 浮いたまま ⛔ になった
                    //    (最も低い当たりを 0 にすると、高い当たりの側に帯の幅ぶんの浮きが残る)。
                    if (EdoBuild.RecentreInBand(bldg[k], ref rt2, EdoBuild.Ground, GROUND_TOL)) continue;
                    if (!(bldg[k].name == "Goten" && bldg[k].transform.childCount > 1))
                    {
                        if (kisoG == null) kisoG = Group("Kiso", root);
                        string kn; var ks = EdoBuild.BuildingKidan(bldg[k], kisoG, EdoBuild.Ground, out kn);
                        if (ks.Count > 0)
                        {
                            kisoN++; kisoWorst = Mathf.Max(kisoWorst, rt2.hi);
                            var bed = EdoBuild.GroundOrBed(new EdoBuild.BedIndex(ks));
                            rt2 = EdoBuild.RootToBed(bldg[k], bed, 0.1f);
                            if (float.IsNaN(rt2.hi) || rt2.hi <= GROUND_TOL) continue;
                            if (EdoBuild.RecentreInBand(bldg[k], ref rt2, bed, GROUND_TOL, 0.08f)) continue;   // 石の天端へは 0.08m まで埋めてよい(石の面の凹凸が 0.06m 超ある ── chos_0 の裏長屋で幅 0.064m・埋めて隠すが基本)
                        }
                        else if (kn != null) log.Add("    ⚠ " + kn);
                    }
                    log.Add(string.Format("    ⛔ 棟 {0}: 造成と石垣の前の削りの後で下端が {1:F3}m 浮く(線 ±0.01)── 置き場か平場を直す", bldg[k].name, rt2.hi));
                }
                if (kisoN > 0) log.Add(string.Format("    布石の基壇: 浮いた棟 {0} を受けた(見え最大 {1:F2}m・EdoBuild.BuildingKidan)", kisoN, kisoWorst));
                var ya = root.Find("Yashiro");                  // 町屋の稲荷(Stage 3m で建つ・棟の群の外)
                if (ya != null) foreach (Transform y in ya) Seat(y.gameObject, log);
                if (mon != null)
                {
                    SeatGamae(mon, log);
                    foreach (var bs in bansho) SeatGamae(bs, log);   // 平面は札で決まっている ── 据え直すのは高さだけ(EDO-0491)
                    if (gamaePad >= 0)
                        log.Add(string.Format("    平場 門構え: y={0:F2}(足元の下の地盤の起伏 {1:F2}m){2}", hb[gamaePad].y, hb[gamaePad].relief,
                                              hb[gamaePad].squeezed > 0 ? string.Format("・⚠ 縁に近く平らに取れない節点 {0}", hb[gamaePad].squeezed) : ""));
                    // ⭐ 下手の浮きは布石の基壇で受ける(EdoBuild.GamaeKidan・段塀の布石と同じ型)── 道は造成しないので、道の傾きと
                    //    区画の線をまたぐ格子(2m)で足元が下がる所が残る。浮きは布石の天端と地面の高い方で測る(硬い ±0.01)。
                    var kidan = new List<GameObject>();
                    foreach (var g in gamae)
                    {
                        string kn; kidan.AddRange(EdoBuild.GamaeKidan(g, monGrp, EdoBuild.Ground, out kn));
                        if (kn != null) log.Add("    " + kn);
                    }
                    foreach (var g in gamae)
                    {
                        // 床 = 地面 + **その駒の**布石(⛔ 隣の駒の布石は部材どうし ── 数えない §4)
                        var own = kidan.Where(k => k.name.StartsWith(g.name + "_kidan_")).ToList();
                        var monBed = own.Count > 0 ? EdoBuild.GroundOrBed(new EdoBuild.BedIndex(own)) : EdoBuild.Ground;
                        var rg = EdoBuild.RootToBed(g, monBed, 0.1f, EdoBuild.GamaeContact(g));
                        if (float.IsNaN(rg.hi) || rg.hi <= GROUND_TOL) continue;
                        log.Add(string.Format("    ⛔ 門構え {0}: 造成の後で下端が {1:F3}m 浮く(線 ±0.01・硬い)── 所 ({2:F2}, {3:F2}) 床 {4:F3}", g.name, rg.hi, rg.hiAt.x, rg.hiAt.z, rg.hiAt.y));
                    }
                }
                // ⭐ 生垣の株は棟・門構えに芯を掛けない(EDO-0475)── 造成の後の建て直しでだけ効く(一巡目は棟がまだ無い)
                EdoBuild.PlantAvoid = bldg.Where(g => g != null).Select(g => EdoBuild.RB(g))
                                          .Concat(gamae.Where(g => g != null).Select(g => EdoBuild.RB(g))).ToList();
                try { buildKakoi(); } finally { EdoBuild.PlantAvoid = null; EdoBuild.PlantInside = null; }
                // ⭐ 表店の裏を区画の線まで切った筆は、線の内に石積みの土留めを据える(EdoBuild.DodomeAlongEdge・EDO-0503)。
                //    表店の辺は除く(店先は道の高さ)。外の地山が内より 0.10m を超えて高い区間だけ。
                if (faced.Any(f => f != null))
                {
                    int dn = 0; float dw = 0f;
                    foreach (var e in edges)
                    {
                        if (machiyaFronts.Contains(e)) continue;
                        if (kisoG == null) kisoG = Group("Kiso", root);
                        float w1; dn += EdoBuild.DodomeAlongEdge(e.a, e.b, e.outward, kisoG, "Dodome" + e.i, 0.10f, out w1, poly).Count;
                        dw = Mathf.Max(dw, w1);
                    }
                    if (dn > 0) log.Add(string.Format("    土留め: 裏を切った縁に石積み {0} 区間(内外の差 最大 {1:F2}m・EdoBuild.DodomeAlongEdge)", dn, dw));
                }
                log.Add("    造成の後で棟 " + bldg.Count + "・門構え・囲いを据え直した");
                // ⭐ 建て直した囲いの注記も刷る(⛔ 2026-09-28 まで一巡目の注記だけが載り、石垣の上の塀の座・寄せが記録に出なかった・規則19)
                foreach (var nt in kakoiNotes) log.Add("      " + nt);
            }
        }

        // ── Stage 5: 植栽(EDO-0323)── ⭐ 参道の帯は**Stage 1 で実測した門構えの開口**から引く
        //    (⛔ 当て推量の GateWidth ではない)。庭の意匠は庭方の設計・EdoTypologyBuilder.Niwa.cs。
        log.Add(Niwa(s, root, poly, front, pad, passageC, gateHalf));   // 参道の起点は通り口の芯(EDO-0491)
        // ⭐ 置いた地表の印(白洲・叩き土・林床)をその場で地形へ塗る。⛔ 2026-09-29 まで塗りは別のメニューで、建て直すたびに
        //    塗り忘れ、観理院の参道と本堂の前の白洲が芝のまま(白砂利の乗り 0.00)だった(施主指摘・EDO-0489)。
        log.Add("  地表の塗り:\n" + EdoGardenSurfacePaint.Paint(root).TrimEnd().Replace("\n", "\n    "));

        // ── Stage 6: 検査(0件でも刷る・規則19) ──
        if (gm != null) log.Add(GamaeJointReport(encl, gm, front, frontKind));
        log.Add(Inspect(id, root, poly));

        // ── Stage 7: 1軒1プレハブへ切り出す(EDO-0296) ──
        log.Add(Externalize(root));
        return string.Join("\n", log.ToArray());
    }


    /// <summary>この辺を何で囲うか。⛔ 2026-09-21 まで公有地は `fence` の欄を読まずに `yarai` を直書きしていて、
    /// 表に書いた yarai 1 / boji 3 / kui 1 / ita 1 / none 4 のうち**建つ姿に効いていたのは 0 件**だった(EDO-0324)。
    /// 返す語は <see cref="EdoBuild.FenceRun"/> の種別(none は囲わない)。</summary>
    static string EnclosureFor(Spec s, Edge e, bool isFront)
    {
        if (s.type == "kouyuu") return s.fence ?? "yarai";   // ⭐ 表の欄が勝つ(既定は表の defaults.kouyuu.fence)
        if (s.encDir != null && s.encDir.Count > 0)
        {
            // 辺の外向きに最も近い 8 方位の鍵が先・無ければ 4 方位(N=+Z から時計回り)。
            // ⭐ 8 方位は 4 方位で隣との境と水際が同じ向きに丸まる区画のため(十坊の宝仙院 水際 232°・隣境 313° がともに W・EDO-0472)
            float deg = Mathf.Repeat(Mathf.Atan2(e.outward.x, e.outward.y) * Mathf.Rad2Deg, 360f);
            string d8 = new[] { "N", "NE", "E", "SE", "S", "SW", "W", "NW" }[Mathf.RoundToInt(deg / 45f) % 8];
            if (d8.Length == 2 && s.encDir.TryGetValue(d8, out var k8)) return k8;
            string d4 = new[] { "N", "E", "S", "W" }[Mathf.RoundToInt(deg / 90f) % 4];
            if (s.encDir.TryGetValue(d4, out var k4)) return k4;
        }
        if (s.enclosure == "nagaya") return "nagaya";
        if (s.enclosure == "nagaya_front+ita") return isFront ? "nagaya" : "ita";
        return s.enclosure ?? "ita";
    }

    // ───────────────────────── Stage 3〜5 ─────────────────────────
    /// <summary>主屋・付属・庭木。区画の内側へ SETBACK 引いた所に、型ごとの棟を置く。</summary>
    static string Omoya(Spec s, Transform root, Vector2[] poly, Edge front, float pad, Vector2 gateC)
    {
        if (s.type == "kouyuu" && s.building != "hikeshi")
            // ⭐ 干場の種別(`hoshiba`)は読むが**建てない** — 竿・張り板・渋紙の駒が在庫に無い
            //    (`docs/asset-index.tsv` に物干しの類は 0 点)。⛔ 黙って捨てず、何を建てなかったかを刷る(規則19)。
            return "  主屋: 無し(明地・干場は地表と柵だけ)" + (s.hoshiba == null ? "" :
                string.Format("・⚠ {0}干場だが竿と張り板の部材が無く未建(地表 {1} と柵だけ)",
                              s.hoshiba == "konya" ? "紺屋" : s.hoshiba == "kappa" ? "合羽" : s.hoshiba,
                              s.surface ?? "dirt"));
        // ⭐ 寺社の境内は別の置き方(EDO-0354)— 棟ごとの実外形で本堂を軸へ・墓地と鐘楼を縁の帯へ。
        //    Spot() の格子点+半径では、狭い境内(成満寺 248 坪)で 4 棟のうち 2 棟が入らなかった。
        if (s.type == "jisha") return JishaOmoya(s, root, poly, front, pad, gateC) + YuNote(s);
        var g = Group("Tatemono", root);
        var c = Inner(poly, SETBACK);
        if (c.Count == 0) return "  ⛔ 主屋: 区画が狭く、囲いの内側に置ける場所が無い";
        // ⛔ 候補点は格子の走査順のままにしない。2026-09-19、633坪の区画で 16.6×20.6m の主屋が
        //    「区画に収まらず未建」になった — 走査順の先頭8点が区画の隅に固まっていて、
        //    20.6m の余地がある奥へ一度も試されなかった。
        // ⭐ 奥ほど先に試す: 辺から遠い点を優先し、同じくらいなら門から遠い方(表門→前庭→主屋)。
        var gate = front.mid;
        // ⭐ 揺らぎ(EDO-0476)── 点数に区画の種で決まる 0〜okiba_m[m] を足す。同じ形の区画でも同じ点から試さない
        c.Sort((p, q) => (EdoGeom.DistToPolyEdge(poly, q) + 0.15f * Vector2.Distance(q, gate) + YuOkiba(s, q))
                .CompareTo(EdoGeom.DistToPolyEdge(poly, p) + 0.15f * Vector2.Distance(p, gate) + YuOkiba(s, p)));
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
        var made = new List<GameObject>();            // 棟どうしの当たりを測るための実体
        var tried = new HashSet<Vector2>();
        int n = 0, dropped = 0, unseated = 0;
        // ⭐ 御殿複合(EDO-0318 ⑥)— 中軸に玄関→表向→中奥→奥向を渡廊下でつないだ**一体の駒**を輪の前に建てる。
        //    以後の付属(蔵・厩・作事小屋)は、この駒の**棟ごとの外形**を避けて置く(⛔ 複合ぜんたいの外接箱で
        //    避けない — 雁行の振りで箱の中は空き地だらけになり、付属が一つも入らなくなる)。
        string gotenNote = "";
        if (s.type == "buke" && OmoyaOf(s) == "goten")
        {
            var inward = -front.outward;
            float target = EdoBuild.GotenTargetArea(poly, root);
            var gg = EdoBuild.GotenComplex(g, "Goten", poly, gateC, inward, pad, target, SETBACK, VERTS, out gotenNote);
            if (gg != null)
                foreach (Transform part in gg.transform)
                {
                    var prb = EdoBuild.RB(part.gameObject);
                    if (prb.size.y < 0.01f) continue;
                    prb.Expand(MIN_BLDG_GAP * 2f); placed.Add(prb);
                    made.Add(part.gameObject);
                }
            gotenNote = "\n" + gotenNote;
        }
        // ⭐ 前庭(EDO-0372)— 門の芯から MAENIWA 以内に棟(軒込み)を建てない。参道の白洲は門の芯 → 主屋の
        //    最近点に引くので、ここで空けておかないと主屋が門の真裏に建ち、白洲が長さ 1.5m 未満で消える
        //    (2026-09-23 sanbezaka_w1)。⛔ 庭の段(Stage 5)や塗る側で繕わない — 建てる時点で空ける。
        //    御殿複合と寺社は各自の置き方で門から引いている(GotenComplex / JishaOmoya)ので、ここは Spot の棟だけ。
        Vector2 sandoC = gateC; string sandoHow;
        float sandoHalf = SandoAxis(s, root, front, ref sandoC, out sandoHow);
        float splat = EdoGardenSurfacePaint.SplatCell();
        float maeniwa = MAENIWA_MIN;
        if (s.maeniwaKen > 0) maeniwa = s.maeniwaKen * 1.818f;   // ⭐ 表の欄が勝つ(欄の上書きで直す・規則4)
        else if (!float.IsNaN(splat))      // 帯の面積 = 奥行 × 幅 ≥ 要る texel 数 × texel の面積(1.15 は区画の縁で切られる分の余裕)
            maeniwa = Mathf.Max(maeniwa, 1.15f * EdoGardenSurfacePaint.SANDO_MIN_TEXELS * splat * splat / (2f * sandoHalf));
        float worstPair = float.NaN;
        // ⭐ 置き場は EdoBuild.PlaceBest で選ぶ — **硬い制約で退け、柔らかい制約で選ぶ**(docs/oki-kata.md §4a)。
        //    ⛔ 前庭のような狙いを「届かなければ退ける」関門として書かない(施主 2026-09-23)。
        var tally = new EdoBuild.SeiyakuTally();
        int pi = -1;
        foreach (var item in plan)
        {
            pi++;
            string key = item.Key;
            string nm = "B" + n + "_" + Path.GetFileNameWithoutExtension(key);
            float yaw = psi + YuYaw(s, key, nm);   // ⭐ 揺らぎ(EDO-0476)── 付属の向きだけ。主屋級は門へ向けたまま
            Func<Vector2, GameObject> place = spot =>
            {
                var q = EdoBuild.Place(key, new Vector3(spot.x, pad, spot.y), yaw, Vector3.one, g, nm);
                if (q == null) return null;
                // ⛔ ピボットの座・底ではなく**接地箇所**で据える(規則21)
                try { EdoBuild.SeatOnGround(q, 0f, VERTS); }
                catch (Exception) { unseated++; UnityEngine.Object.DestroyImmediate(q); return null; }
                return q;
            };
            var hards = new List<EdoBuild.Hard>
            {
                // 壁体が区画の外へ出ない(軒は別勘定・2026-09-21 施主裁定A)
                new EdoBuild.Hard("区域侵犯", q => OutsideBy(poly, q.transform, false) <= 0f),
                // ⛔ 外接箱の膨らましだけで離れを決めない — **既に建った棟と触れている箇所**を測る(規則21)
                // ⭐ 棟が棟の中へ入るのは**突き抜けて見える**ので退ける(2026-09-27 施主: 部材どうしのめり込みは数えないが、
                //    直すのは「見た目に違和感が出るとき(突き抜けて見える)」── 棟どうしの重なりはいつもそれに当たる・docs/oki-kata.md §4)
                new EdoBuild.Hard("棟どうしの突き抜け", q =>
                {
                    foreach (var prev in made)
                    {
                        var d3 = PairDir(q, prev);
                        if (d3.sqrMagnitude < 1e-4f) return false;
                        Vector3 pat; int pn;
                        float gp = EdoBuild.Contact(q, prev, d3.normalized, out pat, out pn, 0.01f, 0.5f, 800);
                        if (!float.IsNaN(gp) && gp < 0f) return false;
                    }
                    return true;
                }),
            };
            var softs = new List<EdoBuild.Soft>
            {
                // 前庭(EDO-0372)— 門の芯から棟の軒までの離れ。参道の白洲はここに塗る
                new EdoBuild.Soft("前庭の奥行 m", maeniwa, q => EdoBuild.GateClearance(q, sandoC, true)),
            };
            // ⭐ 試す数は 24 — PlaceBest は狙いを満たした所で止まるので、多く試すのは狙いに届かないときだけ
            var go = EdoBuild.PlaceBest(Candidates(poly, c, placed, item.Value, tried), 24, place, hards, softs, tally);
            // ⭐ 揺らぎで差し替えた駒が入らなければ**元の駒で**もう一度(EDO-0476)── 揺らぎで棟を失わない
            //    (2026-09-30 実測: 堀口邸 田の字の 1 棟が House B に替わって区画に入らず、主屋が 0 棟になった)
            string orig = go == null ? YuOrig(s, s.units > 1 ? pi % Mathf.Max(1, plan.Count / s.units) : pi) : null;
            if (orig != null && orig != key)
            {
                YuSay(s.id, string.Format("{0} は入らず元の {1} で建てた", Path.GetFileNameWithoutExtension(key), Path.GetFileNameWithoutExtension(orig)));
                key = orig; nm = "B" + n + "_" + Path.GetFileNameWithoutExtension(key); yaw = psi;
                go = EdoBuild.PlaceBest(Candidates(poly, c, placed, item.Value, new HashSet<Vector2>()), 24, place, hards, softs, tally);
            }
            if (go == null) { dropped++; continue; }
            float worst = float.NaN;
            foreach (var prev in made)
            {
                var d3 = PairDir(go, prev);
                if (d3.sqrMagnitude < 1e-4f) continue;
                Vector3 pat; int pn;
                float gp = EdoBuild.Contact(go, prev, d3.normalized, out pat, out pn, 0.01f, 0.5f, 800);
                if (!float.IsNaN(gp) && (float.IsNaN(worst) || gp < worst)) worst = gp;
            }
            if (!float.IsNaN(worst) && (float.IsNaN(worstPair) || worst < worstPair)) worstPair = worst;
            var rb = EdoBuild.RB(go); rb.Expand(MIN_BLDG_GAP * 2f); placed.Add(rb);  // Expand は片側 1/2
            made.Add(go);
            n++;
        }
        // ⭐ **何を建てるつもりだったか**を毎回刷る(規則19)。棟数だけだと、表に足した種別が
        //    部材の取り違えや置き場所不足で丸ごと落ちても「N棟」の数字が減るだけで気づけない。
        var kinds = new List<string>();
        foreach (var it in plan)
        {
            string nm = Path.GetFileNameWithoutExtension(it.Key);
            int k = kinds.FindIndex(x => x.StartsWith(nm + "×"));
            if (k < 0) kinds.Add(nm + "×1");
            else kinds[k] = nm + "×" + (int.Parse(kinds[k].Substring(nm.Length + 1)) + 1);
        }
        string tch = s.tacchu > 0 ? string.Format("・塔頭{0}寺(⚠ 子院の部材が無く小屋で代用)", s.tacchu) : "";
        string tkn = s.tokinokane ? "・時の鐘(⚠ 鐘楼は建つが時の鐘としての作り分けは未実装)" : "";
        string bab = s.baba ? "・⚠ 馬場は未建(地表+垣根の run は EdoBuild の持ち場・EDO-0304)" : "";
        string yag = s.yagura ? "・⚠ 隅矢倉は在庫に部材が無いため未建(部材方の宿題)" : "";
        string un  = s.units > 1 ? string.Format("・{0}戸割り", s.units) : "";
        string dr  = dropped > 0 ? string.Format("・⚠ {0}棟は区画に収まらず未建", dropped) : "";
        if (unseated > 0) dr += string.Format("・⛔ {0}棟は接地箇所が測れず未建(部材のメッシュを検める)", unseated);
        // 制約ごとの勘定 — 狙い(柔らかい)と許容0(硬い)を分けて毎回刷る(規則19・docs/oki-kata.md §4a)
        dr += tally.Summary() + (s.maeniwaKen > 0 ? "(前庭の狙いは表の maeniwa_ken)" : "");
        if (!float.IsNaN(worstPair)) dr += string.Format("・棟どうしの当たりの最小 {0:F2}m{1}", worstPair,
            worstPair < MIN_BLDG_GAP ? "(⚠ 目安 " + MIN_BLDG_GAP.ToString("F1") + "m 未満)" : "");
        // ⭐ 型は **omoya** を刷る(rank ではない)— どの型で建てたかが log に出ていないと、
        //    表の欄が効いたかどうかを建てた姿からしか確かめられない(EDO-0327・規則19)。
        return string.Format("  主屋と付属: {0}/{1}棟(型={2}{3}){4}{5}{6}{7}{8}\n    仕様: {9}{10}",
            n, plan.Count,
            s.type == "buke" ? OmoyaOf(s) : (s.kind ?? s.type),
            un, dr, yag, bab, tch, tkn,
            string.Join(" ", kinds.ToArray()), gotenNote) + YuNote(s);
    }

    /// <summary>二つの駒を**互いへ押し付ける向き**(a から b・水平)。⛔ 駒の基準点(ピボット)から基準点へ
    /// 向けない — 基準点は部材ごとに端・角・中心とばらばらで、長い駒(御殿複合 80m 超)では向きが軸に沿って
    /// −11.9m の嘘のめり込みが出た(2026-09-22・規則21)。**外形の中心どうし**で向ける。</summary>
    static Vector3 PairDir(GameObject a, GameObject b)
    {
        var d = EdoBuild.RB(b).center - EdoBuild.RB(a).center; d.y = 0f;
        return d;
    }

    /// <summary>この区画の主屋の型。⭐ **表の `omoya` が勝ち**、書いていないときだけ格帯から採る
    /// (割り当ては docs/typology-builder.md §4 の表と同じ)。⛔ 格帯を先に見ない — 区画に書いた
    /// 史料値が既定に負ける(表の約束は「区画の欄が null のときビルダーが既定から採る」)。</summary>
    static string OmoyaOf(Spec s)
    {
        if (!string.IsNullOrEmpty(s.omoya)) return s.omoya;
        switch (s.rank)
        {
            case "daimyo":         return s.yashiki == "naka" ? "omote_oku" : "goten";
            case "hatamoto_large": return "ganko";
            case "hatamoto_mid":   return "ujigata";
            default:               return "tanoji";
        }
    }

    /// <summary>型ごとに「何を何棟」。⛔ 在庫の代用が多い — 専用部材は部材方の宿題。</summary>
    static List<KeyValuePair<string, float>> Plan(Spec s)
    {
        var L = new List<KeyValuePair<string, float>>();
        // ⭐ 揺らぎ(EDO-0476)── 主屋級の駒は表の `yuragi.buke.koma` の同じ格の駒へ区画の種で差し替える(YuKoma)
        Action<string, float, int> add = (p, r, k) => { for (int i = 0; i < k; i++) L.Add(new KeyValuePair<string, float>(YuKoma(s, p, L.Count), r)); };
        if (s.type == "buke")
        {
            // ⭐ 主屋の型は**表の `omoya` が勝つ**(区画 > defaults > 格帯。EDO-0327)。
            //    型の中身は docs/typology-builder.md §4 の表 — 御殿複合 / 表・奥の2核 / 雁行複合 /
            //    U字 / 田の字。⚠ 部材は VK の3点しかないので**型ごとに姿は変わらない** —
            //    変わるのは棟の組み合わせだけで、御殿複合の3核は EDO-0318 ⑥ の持ち場。
            switch (OmoyaOf(s))
            {
                case "goten":        // 御殿複合(玄関→表向→中奥→奥向)— ⭐ 棟は Omoya() が GotenComplex で
                    break;           //    一体の駒として先に建てる。⛔ ここへ VK を足さない(御殿の脇に民家が散る)
                case "omote_oku":    // 表・奥の2核(中屋敷)
                    add(EdoAssets.VK.BigHouse, 13f, 1); add(EdoAssets.VK.House, 10f, 1);
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                case "ganko":        // 雁行複合
                    add(EdoAssets.VK.BigHouse, 13f, 1); add(EdoAssets.VK.House, 9f, 1);
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                case "ujigata":      // U字主屋
                    add(EdoAssets.VK.House, 10f, 1); add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                default:             // tanoji 田の字(御家人 30坪)
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
            }
            add(EdoAssets.Eg.Kura, 6f, Mathf.Clamp(s.kura, 0, 4));
            // ── 附属の種別(EDO-0304 案A・施主裁定 2026-09-21)────────────────────────
            // ⭐ 濃さは**棟数**でなく**種別**で戻す。石高帯から列数を引く鎖は史料で切れている
            //    (1〜10万石の棟数は U・密度の主キーは坪数と警備要求)ので、数は一切推定しない。
            // ⛔ 既定で持たせてよいのは大名だけ。旗本以下が 0 なのは「判らない」ではなく
            //    **不在の側に確度A**([鈴木1985] 建家図8例の周囲は土蔵・物置・雪隠のみ)。
            add(EdoAssets.Own.Typ.Umaya, 6f, Mathf.Clamp(s.umaya, 0, 2));
            add(EdoAssets.Own.Typ.SakujiKoya, 5f, Mathf.Clamp(s.sakujiKoya + s.monooki, 0, 2));
            // ⚠ **蔵は3種別で部材が2点しかない。**土蔵=在庫の汎用蔵 / 米蔵・火消道具蔵・御駕籠蔵=
            //    部材方が起こした米蔵。中の道具が違うだけで外見の作り分けは無い(部材方の宿題)。
            //    ⛔ ここで数を足して濃さを繕わない — 見分けが付かない蔵が増えるだけ(在庫方 09-21)。
            add(EdoAssets.Own.Typ.Komegura, 6f,
                Mathf.Clamp(s.komeKura + s.hikeshiKura + s.kagoKura, 0, 3));
            // ⚠ 馬場(s.baba)はまだ建てない — 建物でなく地表+垣根で、垣根の run は EdoBuild の
            //    持ち場(規則21)。既定は全格 false なので今日は誰にも効かない(EDO-0304 の残り)。
        }
        // ⛔ jisha はここに書かない(2026-09-22・EDO-0354)。本堂・庫裏・蔵・鐘楼・墓地・塔頭は
        //    Omoya() が JishaOmoya(EdoTypologyBuilder.Jisha.cs)へ渡す — 棟ごとの実外形で置く。
        // ⛔ 町屋はここに書かない(2026-09-21・EDO-0325)。表店は**接道辺の run** で建てる
        //    (EdoTypologyBuilder.Machiya.cs の Stage 3m → EdoBuild.MachiyaRun)。
        //    ここに在った分岐は `houses/6` を 2〜14 に丸めた棟数を積み、Spot() が区画の**内側の格子点へ
        //    ばらばらに散らして**いた — 町屋は通りに面して軒を接して建つ物なので姿が根本から違った。
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

    /// <summary><see cref="Spot"/> を次々に引く候補の列(引いた点は <paramref name="tried"/> へ入れる)。
    /// <see cref="EdoBuild.PlaceBest"/> へ渡す。</summary>
    static IEnumerable<Vector2> Candidates(Vector2[] poly, List<Vector2> cand, List<Bounds> placed, float r,
                                           HashSet<Vector2> tried)
    {
        while (true)
        {
            var sp = Spot(poly, cand, placed, r, tried);
            if (sp == null) yield break;
            tried.Add(sp.Value);
            yield return sp.Value;
        }
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
            //    置いた後の OutsideBy(壁体の実頂点)。
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

    /// <summary>駒が区画の外へ出た量[m]。⭐ **壁体と軒を分けて測る。**
    /// <paramref name="withRoof"/>=false なら屋根・軒・垂木を外した**壁体**の頂点だけ(=区域侵犯の本体)、
    /// true なら軒も含む(=軒の張り出し)。⛔ 外接箱の隅で測らない — 斜めの辺に沿う塀は回っているだけで隅が外へ出る。
    /// ⚠ 軒が境界を越えるのは**許容**(2026-09-21 施主裁定A)。判定は壁体だけで出し、軒は別の列に刷る(規則19)。</summary>
    static float OutsideBy(Vector2[] poly, Transform t, bool withRoof)
    {
        // ⭐ withRoof=false は EdoBuild.BodyExRoof を使う(EDO-0358・2026-09-22)。名前で
        //    屋根を落とせない一枚メッシュの駒(庫裏・墓地・鐘楼・山門)は Body(false) が Body(true) と
        //    同数のままだった — 軒込みの外形が壁体として数えられ、軒の越境が許容されず(裁定A)
        //    区域侵犯として誤って赤くなる。→ EdoBuild.cs「BodyExRoof」の注記。
        var pts = withRoof ? EdoBuild.Body(t, 600, true) : EdoBuild.BodyExRoof(t, 600);
        return OutsideBy(poly, pts);
    }

    /// <summary>門構え(門・番所)の区域侵犯 = **札の足元**(<see cref="EdoPartSpec.Spec.foot"/>)が区画の外へ出た量[m](硬い・許容0)。
    /// ⭐ 門は地面に立つ所で線を守る。軒は越えてよい(裁定A)。札の無い駒は NaN(⛔ 測れないのを 0 と読まない)。</summary>
    static float SpecOutsideBy(Vector2[] poly, Transform t)
    {
        var sp = EdoBuild.SpecOf(t.gameObject);
        if (sp == null || sp.foot == null || sp.foot.Count < 3) return float.NaN;
        float over = 0f;
        foreach (var q in EdoPartSpec.FootWorld(sp, t))
            if (!EdoGeom.PIP(poly, q)) over = Mathf.Max(over, EdoGeom.DistToPolyEdge(poly, q));
        return over;
    }

    /// <summary>道の上の物(群 "Michi" — 町木戸)が**区画の内へ**入り込んだ量[m](硬い・許容0)。
    /// 足元は札の foot で測る。相手はこの区画と、名前の末尾の区画(<c>MachiKido_&lt;隣の区画&gt;</c>)。
    /// 親柱の外面は角へ突き付けるので境界上 0.02m までは入り込みに数えない。札の無い駒は NaN(⛔)。EDO-0503。</summary>
    static float MichiInsideBy(Vector2[] poly, Transform t)
    {
        var sp = EdoBuild.SpecOf(t.gameObject);
        if (sp == null || sp.foot == null || sp.foot.Count < 3) return float.NaN;
        var polys = new List<Vector2[]> { poly };
        int us = t.name.IndexOf('_');
        var other = us > 0 ? EdoParcels.Get(t.name.Substring(us + 1)) : null;
        if (other != null && other.Length >= 3) polys.Add(other);
        float into = 0f;
        foreach (var q in EdoPartSpec.FootWorld(sp, t))
            foreach (var pg in polys)
                if (EdoGeom.PIP(pg, q)) into = Mathf.Max(into, EdoGeom.DistToPolyEdge(pg, q) - 0.02f);
        return Mathf.Max(0f, into);
    }

    static float OutsideBy(Vector2[] poly, List<Vector3> pts)
    {
        float over = 0f;
        foreach (var w in pts)
        {
            var q = new Vector2(w.x, w.z);
            if (!EdoGeom.PIP(poly, q)) over = Mathf.Max(over, EdoGeom.DistToPolyEdge(poly, q));
        }
        return over;
    }

    /// <summary>**門構えと塀の取り合い**(Stage 6 の列・硬い ── 隙 &gt; 0.01m は ⛔・測れない NaN も ⛔・EDO-0491)。
    /// 口の両脇で、塀の端の駒と、その側の脇の面を持つ門構えの駒(番所があれば番所)を、実メッシュの水平断面で測る
    /// (<see cref="EdoBuild.GamaeFenceGap"/>)。⛔ 2026-09-29 まで門と塀の間の隙を測る列が無く、施主の目で初めて捕まった。</summary>
    /// <summary>生垣・林縁の株の名(`<種別>_<辺>ike_…` / `<種別>_<辺>rin_…`・EdoBuildRun の FenceRun が付ける)。</summary>
    static readonly System.Text.RegularExpressions.Regex PlantRowName = new System.Text.RegularExpressions.Regex(@"_\d+(ike|rin)_");

    static string GamaeJointReport(Transform encl, EdoBuild.Gamae gm, Edge front, string frontKind)
    {
        if (EdoBuild.FenceEndPiece(frontKind) == null) return "  門構えと塀の取り合い: — 前辺の囲い " + frontKind + " は口に端の駒が無い(測らない)";
        var parts = new List<string>(); int ng = 0;
        foreach (int side in new[] { -1, 1 })
        {
            float edge = side < 0 ? gm.gapLo : gm.gapHi;
            var who = side < 0 ? gm.loPiece : gm.hiPiece;
            // ⭐ 塀の線 = 相手の札の正面(front)を通り口の向き(along)へ延ばした線。⛔ 区画の線で測らない ── 長屋の前辺は
            //   道の余地だけ区画の線から奥に建つ区画があり(溜池北0 で 2.7m)、端が全部落ちて嘘の ⛔ が出た(EDO-0491)
            var whoSpec = EdoBuild.SpecOf(who);
            if (whoSpec == null) { ng++; parts.Add((side < 0 ? "−側" : "+側") + " ⛔ 相手 " + who.name + " に札が無い"); continue; }
            var fw = EdoPartSpec.FrontWorld(whoSpec, who.transform);
            var nrm = new Vector2(-gm.along.y, gm.along.x);
            // 口の縁に端を着けた駒 = 塀の線の近く(2.5m)で、走りの射影の端が口の縁にいちばん近い物(生垣・林縁の株は除く)。
            // ⭐ 端がそろう駒(表と裏の板・端から 0.3m 以内)はまとめて一組として測る(EdoBuild.GamaeFenceGap)
            var cand = new List<KeyValuePair<float, GameObject>>();
            foreach (Transform t in encl)
            {
                // ⛔ 名の部分一致で外さない ── 囲いの種別 `ita+ikegaki` の板まで落ちて「端が無い」の嘘の ⛔ が出た(EDO-0491)。
                //   株の名は EdoBuildRun の `prefix + "ike"` / `prefix + "rin"`(辺の番号の直後)だけを外す
                if (PlantRowName.IsMatch(t.name)) continue;
                var rb = EdoBuild.RB(t.gameObject);
                if (rb.size.y < 0.05f) continue;
                // ⭐ 線からの離れは外形の**いちばん近い角**で測る ── 芯で測ると、外の面を線に置く長屋(奥行 4m 余)の芯が
                //   2.5m より奥へ入り、長屋の端が全部落ちて「端が無い」の嘘の ⛔ が出た(EDO-0491)
                float mn = float.MaxValue, mx = float.MinValue, dLo = float.MaxValue, dHi = float.MinValue;
                foreach (var c in new[] { new Vector2(rb.min.x, rb.min.z), new Vector2(rb.min.x, rb.max.z), new Vector2(rb.max.x, rb.min.z), new Vector2(rb.max.x, rb.max.z) })
                {
                    float q = Vector2.Dot(c, gm.along); mn = Mathf.Min(mn, q); mx = Mathf.Max(mx, q);
                    float d = Vector2.Dot(c - fw, nrm); dLo = Mathf.Min(dLo, d); dHi = Mathf.Max(dHi, d);
                }
                float near = (dLo <= 0f && dHi >= 0f) ? 0f : Mathf.Min(Mathf.Abs(dLo), Mathf.Abs(dHi));
                if (near > 2.5f) continue;
                bool onSide = side < 0 ? (mn < edge - 0.1f) : (mx > edge + 0.1f);
                if (!onSide) continue;
                cand.Add(new KeyValuePair<float, GameObject>(Mathf.Abs((side < 0 ? mx : mn) - edge), t.gameObject));
            }
            string nm = side < 0 ? "−側" : "+側";
            if (cand.Count == 0 || cand.Min(c => c.Key) > 3.5f) { ng++; parts.Add(nm + " ⛔ 口の脇に塀の端が無い"); continue; }
            float bestD = cand.Min(c => c.Key);
            var ends = cand.Where(c => c.Key <= bestD + 0.3f).Select(c => c.Value).ToList();
            string how;
            float gap = EdoBuild.GamaeFenceGap(ends, who, gm.along * (side < 0 ? 1f : -1f), out how);
            bool bad = float.IsNaN(gap) || gap > 0.01f;
            if (bad) ng++;
            parts.Add(string.Format("{0} {1} {2}↔{3} {4}({5})", nm, bad ? "⛔" : "⭕", string.Join("+", ends.Select(e => e.name).ToArray()), who.name,
                                    float.IsNaN(gap) ? "測れない" : string.Format("{0:+0.000;-0.000}m", gap), how));
        }
        return string.Format("  門構えと塀の取り合い(硬い・隙 ≤ 0.01m・負 = 埋め): {0} ── {1}", ng == 0 ? "⭕" : "⛔ " + ng + " 件", string.Join(" / ", parts.ToArray()));
    }

    // ───────────────────────── Stage 6: 検査 ─────────────────────────
    /// <summary>境界侵犯・埋没・浮きを、建てたその場で測って刷る(0件でも刷る・規則19)。
    /// ⛔ これは「機械で見える型」だけ。部材どうしの隙は建てて見る輪の持ち場。</summary>
    /// <summary>Stage 6 — 建てた姿を測る。⛔ **数えるのは「据えた駒」ひとつずつ**(群の直下の子)で、
    /// 部材の中のメッシュ一枚ずつではない。⛔ 2026-09-19、屋根や壁の一枚一枚を数えていて
    /// 「浮き 1103 / 1388」という**嘘の赤**が出た(屋根は地面から離れているのが正しい姿)。
    /// 測る物: ①区域侵犯=駒の底面が区画の外へ出た量 ②埋没=触れている所が地面より 0.01m 下
    /// ③浮き=触れている所が地面より 0.01m 上(2026-09-27 施主 ── 地面との間だけ ±0.01m・docs/oki-kata.md §4。
    /// 旧の埋 1.0 / 浮 0.7 は根拠の無い目安で廃止)。⭐ **根入れで据える物は埋没を数えない** ── 囲い(塀・長屋は代を地中へ
    /// 埋めて据える・§0a「基本は根入れ」)と庭(木の根元・景石の 1/3 埋め)は浮きだけを数える。
    /// ⭐ 部材どうしのめり込みは欠陥に数えない(同日 施主・§4)── 棟どうしの当たりは見張りとして刷るだけ。⭐ 塀は境界線の**上に**立つので囲いだけ 0.6m の遊びを持つ
    /// (建物と門は遊び 0 — 規則4「境界侵犯は許容0」)。⛔ 0 件は「この型では捕まらなかった」
    /// であって合格ではない(規則19)。最悪値を必ず刷り、緩い条件で 0 が出ていないか見えるようにする。</summary>
    /// <summary>地面に置く物の接地の許容[m](浮き +0.01・埋まり −0.01 ── 2026-09-27 施主・docs/oki-kata.md §4)。
    /// ⛔ 地面との間だけの線。部材どうしの隙は 1mm 未満を 0(別の線)。</summary>
    const float GROUND_TOL = 0.01f;
    /// <summary>塀の下端の浮きの線[m] = 地面の線と同じ(2026-09-27 に 0.05 から改めた・§4「類型の塀の下 0.05 はこの線へそろえる」)。</summary>
    const float KAKOI_UKI_TOL = GROUND_TOL;
    /// <summary>庭の駒のうち**剛体の据え物**(`NiwaSet.Stone` で据える物)の名の頭。検査で下端の全部を測る。
    /// ⚠ 据える側(Niwa / Keidai の Put の名)と揃える ── 新しい据え物を足したらここにも足す。</summary>
    static readonly string[] SUE_MONO = { "Ido", "Toro", "Kenntou", "Chozu", "Ishigumi", "Tobiishi" };
    static bool IsSueMono(string name)
    {
        foreach (var h in SUE_MONO) if (name.StartsWith(h, System.StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>門構えの駒の床 = 地面 + **その駒の**基壇の布石(縁と目地は 5cm 跨ぐ)。</summary>
    /// ⛔ 他の駒の布石も床に入れない ── 長屋門の布石が番所の足元の下へ入る所で「番所の埋没 0.666m」と数えた(西溜池2・2026-09-30)。
    static System.Func<float, float, float> MonBedFor(string piece)
    {
        EdoBuild.BedIndex bi; if (_bedMon == null || !_bedMon.TryGetValue(piece, out bi)) return EdoBuild.Ground;
        return EdoBuild.GroundOrBed(bi);
    }
    static Dictionary<string, EdoBuild.BedIndex> _bedMon;
    /// <summary>当たりの相手 = 見えている地表(live terrain)。<see cref="EdoBuild.RootToBed"/> に渡す。</summary>
    static float GroundBed(float x, float z)
    {
        float g = EdoBuild.Ground(x, z);
        if (_bedX != null) { float b = _bedX.AtNear(x, z, 0.05f); if (!float.IsNaN(b) && b > g) return b; }   // 縁と目地は 5cm 跨いで受ける
        return g;
    }
    /// <summary><see cref="GroundBed"/> と同じ床だが、**石垣の天端の継ぎ目の穴**(その点に天端の面が無く、0.35m 以内に有る所)は
    /// NaN を返す ── 塀は穴を跨いで石に載るので、穴の下の地面を床に数えない(<see cref="EdoBuild.RootToBed"/> は NaN を飛ばす)。
    /// ⛔ 穴で地面を返すと、背の地山が低い所(観理院の西の北寄り 12.9)で塀の「浮き」を 1.1m と測り、一続きごと沈めた(2026-09-28)。</summary>
    /// <summary>水平に据える塀(石垣の端への差し込み・継ぎ)の座 = 足あと(線から内へ塀の厚み)の下の床の最も低い所(石の上は石の天端)。低い所で浮かせない。</summary>
    static float TuckBase(Vector2 p0, Vector2 p1, Vector2 inw, EdoBuild.BedIndex stone = null)
    {
        float g = float.MaxValue; var d = p1 - p0; float L = d.magnitude; if (L < 1e-3f) return EdoBuild.Ground(p0.x, p0.y);
        for (float u = 0f; u <= L + 1e-3f; u += 0.1f)
            for (float l = 0f; l <= RIM_WALL_HALF * 2f + 1e-3f; l += RIM_WALL_HALF)
            {
                var q = p0 + d / L * Mathf.Min(u, L) + inw * l; float h = EdoBuild.Ground(q.x, q.y);
                float st = stone != null ? stone.At(q.x, q.y) : float.NaN;     // 石の上は石の天端(地面の高い方)
                if (!float.IsNaN(st)) h = float.IsNaN(h) ? st : Mathf.Max(h, st);
                if (!float.IsNaN(h)) g = Mathf.Min(g, h);
            }
        return g == float.MaxValue ? EdoBuild.Ground(p0.x, p0.y) : g;
    }

    /// <summary>点 <paramref name="p"/> から内へ、石垣の天端の面(<paramref name="bed"/>)が始まる離れ[m](最大 <paramref name="maxIn"/>)。</summary>
    static float RimStoneBack(EdoBuild.BedIndex bed, Vector2 p, Vector2 inw, float maxIn)
    {
        if (bed == null) return 0f;
        for (float l = 0f; l <= maxIn + 1e-3f; l += 0.05f) { var q = p + inw * l; if (!float.IsNaN(bed.At(q.x, q.y))) return l; }
        return maxIn;
    }

    static float GroundBedSpan(float x, float z)
    {
        float g = EdoBuild.Ground(x, z);
        if (_bedX == null) return g;
        // ⭐ 床の縁ちょうどの標本(塀の足跡の端が布石の天端の端に重なる)は、5cm 以内の床の**最も高い所**を採る ── 段の継ぎ目では
        //    隣の低い区間の布石(天端が地中)だけを拾い、自分の布石を見落として段塀を地面からの「浮き」と数えた
        //    (観理院 86 駒・最悪 0.96m・2026-09-29 EDO-0477)。
        const float E = 0.05f;
        float b = float.NaN;
        foreach (var o in new[] { Vector2.zero, new Vector2(E, 0f), new Vector2(-E, 0f), new Vector2(0f, E), new Vector2(0f, -E),
                                  new Vector2(E, E), new Vector2(-E, E), new Vector2(E, -E), new Vector2(-E, -E) })
        {
            float nb = _bedX.At(x + o.x, z + o.y);
            if (!float.IsNaN(nb) && (float.IsNaN(b) || nb > b)) b = nb;
        }
        if (!float.IsNaN(b)) return Mathf.Max(g, b);
        const float R = 0.35f;
        foreach (var o in new[] { new Vector2(R, 0f), new Vector2(-R, 0f), new Vector2(0f, R), new Vector2(0f, -R) })
        {
            float nb = _bedX.At(x + o.x, z + o.y);
            if (!float.IsNaN(nb) && nb > g + 0.05f) return float.NaN;
        }
        return g;
    }
    /// <summary>囲いの駒の当たりの相手。布石("_ishi")は**自分が床**なので地面だけで測る ── 床の索引で測ると自分の天端を床に採り、
    /// 地中へ埋めた底を「浮き」と数えた(観理院の段塀の布石 86/86 駒・最悪 0.96m・2026-09-29 EDO-0477)。</summary>
    static System.Func<float, float, float> KakoiBedFor(Transform t)
    {
        if (t.name.EndsWith("_ishi")) return EdoBuild.Ground;
        return GroundBedSpan;
    }
    /// <summary>床に数える受けの駒(崖の縁の石垣の天端)の索引。<see cref="Inspect"/> が区画の Ishigaki 群から作る ── 塀は石垣の天端に載る。</summary>
    static EdoBuild.BedIndex _bedX;

    public static string Inspect(string id, Transform root, Vector2[] poly)
    {
        int n = 0, outside = 0, sunk = 0, floated = 0, multi = 0, eaveOut = 0, kakoiUki = 0, kakoiN = 0;
        string worstFloatName = "", worstSunkName = "", worstOutName = "";
        float worstOut = 0f, worstSunk = 0f, worstFloat = 0f, worstRelief = 0f, worstEave = 0f, worstKakoiUki = 0f;
        var ishiG = root.Find("Ishigaki");
        // ⭐ 床 = 石垣の駒 + 段塀の布石(囲いの "_ishi" の駒)── 塀は布石の天端に載る(2026-09-29 EDO-0477)。
        //    ⛔ 布石を床に入れないと、布石に載った塀を地面からの「浮き」と数えた(観理院の段塀 88/202 駒・最悪 0.945m)。
        var beds = new List<GameObject>();
        if (ishiG != null) beds.AddRange(ishiG.Cast<Transform>().Select(t => t.gameObject));
        var kakG = root.Find("Kakoi");
        if (kakG != null) beds.AddRange(kakG.Cast<Transform>().Where(t => t.name.EndsWith("_ishi")).Select(t => t.gameObject));
        // ⭐ 門構えの基壇の布石("_kidan_")も床 ── 門・番所は布石の天端に載る(EDO-0491)
        var monG = root.Find("Mon");
        var monKidan = monG == null ? new List<GameObject>() : monG.Cast<Transform>().Where(t => t.name.Contains("_kidan_")).Select(t => t.gameObject).ToList();
        beds.AddRange(monKidan);
        var kisoQ = root.Find("Kiso");                  // 棟の基壇の布石(EdoBuild.BuildingKidan・EDO-0503)も床
        if (kisoQ != null) beds.AddRange(kisoQ.Cast<Transform>().Select(t => t.gameObject));
        _bedMon = monKidan.GroupBy(k => k.name.Substring(0, k.name.IndexOf("_kidan_")))
                          .ToDictionary(gr => gr.Key, gr => new EdoBuild.BedIndex(gr.ToList()));
        _bedX = beds.Count > 0 ? new EdoBuild.BedIndex(beds) : null;
        foreach (Transform grp in root)
        {
            // ⛔ 2026-09-22 まで「Mon」もここに入っていて、辺に載らない門を折り込んでも残る
            //    0.37〜0.58m の壁体侵犯を見逃していた(EDO-0359)。塀は境界線の**上**に乗って建つので
            //    遊びを持つが、門は遊び 0(規則4・関数冒頭の注記どおり)。
            float tol = grp.name == "Kakoi" ? 0.6f : 0f;  // 塀だけ境界線の上に立つ
            foreach (Transform t in grp)                   // 群の直下 = 据えた駒ひとつ
            {
                var rs = t.GetComponentsInChildren<Renderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds;
                for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
                n++;
                // ⛔ AABB の隅で測らない — 斜めの辺に沿う塀は、回っているだけで隅が外へ出る。
                //    実メッシュの底面(回転込み)で測る(規則5)。
                // 区域侵犯は**壁体**で数える(軒は別勘定 — 軒の許容は裁定待ち)
                // ⭐ 木は**幹の芯**で数える(樹冠は区画の線を越えて張り出してよい ── 施主の規則 2026-09-23・EDO-0477 P5)。
                //    幹の取れない駒(石・灯籠)は従来どおり壁体で。
                Vector3 foot3; Vector2 foot;
                float outD = grp.name == "Niwa" && EdoBuild.TrunkFootWorld(t.gameObject, out foot3)
                    ? (EdoGeom.PIP(poly, foot = new Vector2(foot3.x, foot3.z)) ? 0f : EdoGeom.DistToPolyEdge(poly, foot))
                    : grp.name == "Michi" ? MichiInsideBy(poly, t)   // 道の上の物(町木戸)は逆に**区画の内へ**入った量で(EDO-0503)
                    : grp.name == "Mon" && !t.name.Contains("_kidan_") ? SpecOutsideBy(poly, t)   // 門構えは札の足元で(軒は越えてよい・EDO-0491)。基壇の布石は壁体で
                    : OutsideBy(poly, t, false);
                float tolT = (grp.name == "Mon" || grp.name == "Kiso") && t.name.Contains("_kidan_") ? EdoBuild.KIDAN_BULGE : tol;   // 基壇の布石は表の面のふくらみだけ
                if (float.IsNaN(outD) || outD > tolT) { outside++; if (!float.IsNaN(outD) && outD > worstOut) { worstOut = outD; worstOutName = grp.name + "/" + t.name; } }   // 札の無い門構えは測れない = ⛔(黙って通さない)
                float eaveD = grp.name == "Michi" ? 0f : OutsideBy(poly, t, true);   // 道の上の物は区画の外が正しい
                if (eaveD > tol) { eaveOut++; worstEave = Mathf.Max(worstEave, eaveD); }
                // ⛔ 「底(bounds.min.y) − 中心の真下の地形」で測らない(2026-09-20 施主指摘)。
                //    接地は底とは限らず(斜面では上手側の頂点が先に着く)、複数あり得る。
                //    測るのは **接地箇所の隙間** と **接地の数**(EdoBuild.Contact)。
                Vector3 at; int nc;
                float dy = EdoBuild.Contact(t.gameObject, out at, out nc, 0.01f, VERTS);
                if (float.IsNaN(dy)) continue;
                // ⭐ 赤になりかけた駒だけ、間引かずに測り直す。⛔ 頂点の多い駒(屋敷林の木)は 800 点の
                //    一様な間引きが根元の頂点を落とし、+0.97m の「浮き」が全頂点では −0.29m だった
                //    (2026-09-22 todablock。EDO-0323 の指摘)。全区画を精密に測ると 79 区画が終わらないので、
                //    ここだけ。測り直した値が本当の値 — 間引きの値で ⛔ を出さない(規則19)。
                bool kidanPiece = (grp.name == "Mon" || grp.name == "Kiso") && t.name.Contains("_kidan_");       // 門構えの基壇の布石(根入れ)
                bool rooted = grp.name == "Kakoi" || grp.name == "Niwa" || grp.name == "Ishigaki" || grp.name == "Michi" || kidanPiece;   // 石垣は根入れ 0.22 と見付の余りを地中へ   // 根入れで据える物(埋没を数えない)
                if ((!rooted && dy < -GROUND_TOL) || dy > GROUND_TOL)
                    dy = EdoBuild.Contact(t.gameObject, out at, out nc, 0.01f, 60000);
                // ⭐ 棟(御殿の複合を除く)は**下端の全部**を測る(§0a)── Contact(上の測り直しも)は最寄りの 1 点なので、斜面で下手が浮いても 0 を返す。
                //    浮きと埋まりの大きい方を代表にする(複合の棟ごとと同じ作法)。
                // ⭐ 門構え(門・番所)も下端の全部を測る ── 床は地面と基壇の布石(EDO-0491)。⛔ 2026-09-30 まで Contact(最寄りの 1 点)で、
                //    坂の上手の 1 点が着いた門の下手の浮き(最大 7.24m)を 0 と刷っていた。布石は地面だけで測り、浮きだけを採る。
                if (grp.name == "Mon")
                {
                    // ⭐ 門構えの床は地面と自分の基壇の布石だけ(建てる時の検めと同じ)── ⛔ 脇の塀の布石・石垣は床に入れない:
                    //    塀の口の食い込みで門の足元の下へ入る布石の天端を「門の埋没 0.508m」と数えた(寿家・2026-09-30。部材どうしは数えない §4)
                    var rt = EdoBuild.RootToBed(t.gameObject, kidanPiece ? (System.Func<float, float, float>)EdoBuild.Ground : MonBedFor(t.name), 0.1f,
                                                kidanPiece ? null : EdoBuild.GamaeContact(t.gameObject));
                    if (!float.IsNaN(rt.hi)) dy = kidanPiece ? Mathf.Max(dy, rt.hi) : (rt.hi > -rt.lo ? rt.hi : rt.lo);
                }
                if (grp.name == "Kiso")
                {   // 棟の基壇の布石は下端の全部を地面で測る(浮きだけ・埋まりは根入れ)── ⛔ Contact の最寄り 1 点だと坂の下手の浮きを 0 と刷った(EDO-0503)
                    var rk = EdoBuild.RootToBed(t.gameObject, EdoBuild.Ground, 0.05f);
                    if (!float.IsNaN(rk.hi)) dy = Mathf.Max(dy, rk.hi);
                }
                if (grp.name == "Yashiro")
                {   // 稲荷(小祠・鳥居)も下端の全部で浮きを測る ── ⛔ Contact の最寄り 1 点で、斜面で 1.55m 浮いた小祠を 0 と刷った(EDO-0503)
                    var ry = EdoBuild.RootToBed(t.gameObject, GroundBed, 0.1f);
                    if (!float.IsNaN(ry.hi) && ry.hi > dy) dy = ry.hi;
                }
                if (grp.name == "Tatemono" && t.name != "Goten")
                {
                    // 浮きは床(地面と布石)で・埋まりは地面だけで測る ── 布石が棟の下端へ食うのは部材どうし(数えない §4・EdoBuild.KIDAN_BITE)
                    var rt = EdoBuild.RootToBed(t.gameObject, GroundBed, 0.1f);
                    var rg = _bedX != null ? EdoBuild.RootToBed(t.gameObject, EdoBuild.Ground, 0.1f) : rt;
                    float lo = float.IsNaN(rg.lo) ? 0f : rg.lo;
                    if (!float.IsNaN(rt.hi)) dy = rt.hi > -lo ? rt.hi : lo;
                }
                // ⭐ 庭の**剛体の据え物**(井戸・灯籠・献灯・手水鉢・景石・飛石)も下端の全部を測る ── 坂で上手の 1 点が着いて
                //    下手が浮いても Contact は 0 を返す(2026-09-29 EDO-0472: 十坊 8・9 の井戸が 0.75m 浮いて ⭕ だった)。
                //    埋まりは根入れなので数えない(浮きだけを採る)。木・下草は根で据える物なので測らない。
                if (grp.name == "Niwa" && IsSueMono(t.name))
                {
                    var rt = EdoBuild.RootToBed(t.gameObject, GroundBed, 0.05f);
                    if (!float.IsNaN(rt.hi) && rt.hi > dy) dy = rt.hi;
                }
                // ⭐ 石垣の天端に載る塀は床(石の天端)で測る ── Contact は地形だけを見るので、天端の上の塀を地形からの「浮き」と数えた
                //    (観理院の西 0.79m・2026-09-28)。塀は根入れで据えるので浮きだけを採る(埋まりは数えない)。
                //    塀は全部、足跡の下端の当たり(RootToBed・石の継ぎ目の穴は跨ぐ)で測る ── 「塀の下端の浮き」と同じ測り。
                if (grp.name == "Kakoi")
                {
                    var rt = EdoBuild.RootToBed(t.gameObject, KakoiBedFor(t), 0.05f);
                    if (!float.IsNaN(rt.hi)) dy = rt.hi;
                }
                // ⭐ **一続きの複合は棟ごとに測る。**⛔ 複合ぜんたいの Contact は**子の最小**を返すので、
                //    塚に載った 1 棟が 0.00m を返すと、他の 6 棟が 2.1m 浮いていても「⭕ 0.00m」になる。
                //    2026-09-22 の戸田・阿部・松平がこれで、数値の関門は全部通ったのに
                //    検証レンダでは建物の下を光が抜けていた(EDO-0318 ⑥・規則19「0 件は合格ではない」)。
                if (t.name == "Goten" && t.childCount > 1)
                {
                    float lo = dy, hi = dy;
                    foreach (Transform part in t)
                    {
                        if (part.GetComponentsInChildren<Renderer>().Length == 0) continue;
                        Vector3 pat2; int pn2;
                        float pd = EdoBuild.Contact(part.gameObject, out pat2, out pn2, 0.01f, VERTS);
                        if (!float.IsNaN(pd) && (pd < -GROUND_TOL || pd > GROUND_TOL))
                            pd = EdoBuild.Contact(part.gameObject, out pat2, out pn2, 0.01f, 60000);
                        if (float.IsNaN(pd)) continue;
                        if (pd < lo) lo = pd;
                        if (pd > hi) hi = pd;
                    }
                    dy = hi > -lo ? hi : lo;            // 浮きと埋没の**大きい方**を複合の代表にする
                }
                if (!rooted && dy < -GROUND_TOL) { sunk++; if (-dy > worstSunk) { worstSunk = -dy; worstSunkName = grp.name + "/" + t.name; } }
                if (dy > GROUND_TOL) { floated++; if (dy > worstFloat) { worstFloat = dy; worstFloatName = grp.name + "/" + t.name; } }
                if (nc > 1) multi++;
                // ⭐ 塀は**下端のいちばん浮いた所**を数える(2026-09-27・EDO-0477 P2)。⛔ Contact は最寄りの 1 点
                //    (= 上手の端)なので、斜面で下手が浮いた塀を 0 と返していた(観理院 35/133 駒・最大 1.74m・EDO-0466)。
                //    浮きは許容0(規則4)── 遊び KAKOI_UKI_TOL は格子の読み違いの幅だけ。
                if (grp.name == "Kakoi")
                {
                    kakoiN++;
                    // ⭐ 塀の**下端**(当たり)だけを測る(RootToBed ── §0a)。⛔ UnderfloorGap は笠(瓦の庇)の下まで拾い、
                    //    塀の高さ 2.9m を「浮き」と返した(2026-09-27 観理院 199/199 駒)。
                    float uk = EdoBuild.RootToBed(t.gameObject, KakoiBedFor(t), 0.05f).hi;
                    if (!float.IsNaN(uk) && uk > KAKOI_UKI_TOL) { kakoiUki++; worstKakoiUki = Mathf.Max(worstKakoiUki, uk); }
                }
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
        // ⛔ 外接箱の隙で測らない(回った棟で 0 に見える)。**棟どうしの触れている箇所**を測る
        //    (負 = めり込み。2026-09-27 施主: 部材どうしのめり込みは欠陥に数えない ── 見張りとして刷り、直すのはレンダで
        //    違和感が見えたとき(docs/oki-kata.md §4)。棟の置き場の選び(PlaceBest)は突き抜けを避けるので、ここで負が出たら見る)。
        float minGap = float.MaxValue;
        var tate = root.Find("Tatemono");
        if (tate != null)
        {
            var gs = new List<GameObject>();
            var own = new List<Transform>();            // 各駒がどの根に属するか(複合の内側どうしは測らない)
            foreach (Transform t in tate)
            {
                if (t.GetComponentsInChildren<Renderer>().Length == 0) continue;
                // ⭐ 御殿複合は**棟ごとに**測る。複合ぜんたいは 80m を超える長い駒で、基準点も外形も端に寄る —
                //    一つの駒として測ると隣の蔵との向きが軸に沿って −11.9m の嘘が出た(2026-09-22)。
                if (t.name == "Goten") foreach (Transform part in t) { gs.Add(part.gameObject); own.Add(t); }
                else { gs.Add(t.gameObject); own.Add(t); }
            }
            for (int i = 0; i < gs.Count; i++)
                for (int j = i + 1; j < gs.Count; j++)
                {
                    // 複合の内側(渡廊下と棟)は軒がかぶるのが設計 — 取り合いは GotenComplex が屋根を外して測って刷る
                    if (own[i] == own[j]) continue;
                    var d3 = PairDir(gs[i], gs[j]);
                    if (d3.sqrMagnitude < 1e-4f) { minGap = Mathf.Min(minGap, -9f); continue; }
                    Vector3 at2; int n2;
                    float g = EdoBuild.Contact(gs[i], gs[j], d3.normalized, out at2, out n2, 0.01f, 0.5f, 800);
                    if (!float.IsNaN(g)) minGap = Mathf.Min(minGap, g);
                }
        }
        string gap = minGap == float.MaxValue ? "" :
            string.Format(" / 棟どうしの当たりの最小 {0:F2}m{1}", minGap,
                minGap < 0f ? "(⚠ めり込み・数えない ── レンダで見る)" : (minGap < MIN_BLDG_GAP ? "(⚠ 目安 " + MIN_BLDG_GAP.ToString("F1") + "m 未満)" : ""));
        string mark = (outside + sunk + floated + kakoiUki) == 0 ? "⭕" : "⛔";
        gap += string.Format(" / 塀の下端の浮き {0}/{1}駒(最悪 {2:F3}m・線 {3:F2})", kakoiUki, kakoiN, worstKakoiUki, KAKOI_UKI_TOL);
        return string.Format("  {0} 検査: 駒 {1} — 壁体が区画の外 {2}(最悪 {3:F2}m{15}) / 軒が区画の外 {11}(最悪 {12:F2}m・許容・裁定A) / "
                           + "触れている所の埋没 {4}(最悪 {5:F3}m{13}・囲いと庭は根入れで数えない) / 浮き {6}(最悪 {7:F3}m{14}・線 ±0.01) / "
                           + "触れている所が複数 {8}駒 / 足元の起伏 最悪 {9:F2}m{10}",
                             mark, n, outside, worstOut, sunk, worstSunk,
                             floated, worstFloat, multi, worstRelief, gap, eaveOut, worstEave,
                             worstSunkName == "" ? "" : " " + worstSunkName, worstFloatName == "" ? "" : " " + worstFloatName,
                             worstOutName == "" ? "" : " " + worstOutName);
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
