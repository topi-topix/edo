// 類型の庭(Stage 5)— **どの類型が何をどこへ**だけ。EDO-0323。
//
// 意匠は庭方 2026-09-21 の設計。正典は `docs/typology-builder.md` §4.5、実装できる密度の全文は
// 掲示板 EDO-0317 の申し送り §5。⛔ **意匠を実装側で作り変えない**(規則17)。覆さない線は五つ:
//   ① 前庭は空ける(参道の帯に駒0)② 塊は必ず奇数 ③ 常緑:落葉 = 7:3
//   ④ 池は類型では掘らない(代わりに chisen へ**池代地**)⑤ 地形(高さ・アルファマップ)を書かない
//
// ⛔ 置き方の算術(退避・芯々・据え・乱れ)はここに書かない — `EdoBuildNiwa.cs` の持ち場(規則21)。
// ⛔ 本数を4型へ固定で配らない — **周長と面長からの従属値**(28区画は面積で100倍・周長で12倍の開きがある)。
// ⛔ 庭域へ一様乱数で撒かない — 置くのは**帯と塊**だけ(§5-4 ①)。

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    /// <summary>1区画の草木の駒の上限(庭方 §5-0「予算」)。超えたら**低木から減らす** —
    /// ⛔ 高木の骨格で帳尻を合わせない。</summary>
    const int NIWA_BUDGET = 400;

    // ───────────────────────── 層ごとの部材(在庫。⛔ パスの literal を書かない・規則12) ─────────────────────────

    /// <summary>屋敷林の帯。⭐ **常緑7:落葉3** — 並びの数でその比を持たせる(⛔ 落葉に寄せると冬に骨組みが消える)。
    /// 常緑 = 林のクロマツ(`Own.Matsu`)と常緑広葉樹 / 落葉 = エノキ・ムクノキ・ケヤキの Small。</summary>
    static string[] _linEv, _linDe, _linPal;
    /// <summary>屋敷林の**常緑**(林のクロマツ `Own.Matsu` と常緑広葉樹)。</summary>
    static string[] LinEv
    {
        get
        {
            if (_linEv == null) _linEv = new[]
            {
                EdoAssets.Own.Matsu("Mid", 1), EdoAssets.Own.Matsu("Mid", 2), EdoAssets.Own.Matsu("Mid", 3),
                EdoAssets.Own.Matsu("Big", 1), EdoAssets.Own.Jouryoku("Big", 1),
                EdoAssets.Own.Jouryoku("Big", 2), EdoAssets.Own.Jouryoku("Mid", 3),
            };
            return _linEv;
        }
    }
    /// <summary>屋敷林の**落葉**(エノキ・ムクノキ・ケヤキ)。⛔ 紅葉色ではない(季節は秋でもない)。</summary>
    static string[] LinDe
    {
        get
        {
            if (_linDe == null) _linDe = new[]
            {
                EdoAssets.Own.Enoki("Small", 1), EdoAssets.Own.Mukunoki("Small", 2),
                EdoAssets.Own.Keyaki("Small", 3),
            };
            return _linDe;
        }
    }
    static string[] LinPal
    {
        get { if (_linPal == null) _linPal = LinEv.Concat(LinDe).ToArray(); return _linPal; }
    }

    /// <summary>屋敷林の個体の採り方。⭐ **庭全体で常緑:落葉 = 7:3**(覆さない線③)に着地させる。
    /// 屋敷林は常緑と落葉の両方を持つ唯一の層なので、他の層(松・中木・低木=常緑 / モミジ=落葉)の
    /// **これから据える本数**を勘定に入れて、この帯だけで比の帳尻を合わせる。
    /// ⛔ 落葉を 0.6 より濃くしない(屋敷林が雑木林に化ける)。</summary>
    static Func<string, string> LinMix(System.Random rnd, float deShare)
    {
        int ev = 0, de = 0;
        return last =>
        {
            bool takeDe = (de + 1f) / (ev + de + 1f) <= deShare;
            var pal = takeDe ? LinDe : LinEv;
            string path = pal[rnd.Next(pal.Length)];
            for (int t = 0; t < 32 && path == last && pal.Length > 1; t++) path = pal[rnd.Next(pal.Length)];   // ⛔ 塊の中で同一個体を2本続けない(4回では確率で残る)
            if (takeDe) de++; else ev++;
            return path;
        };
    }

    /// <summary>帯の落葉の割り。⭐ **0.30 固定**(庭方 2026-09-22 の直し③)。
    /// ⛔ 他の層の予定本数から帳尻を合わせない — 帯の取れ高が区画ごとに 0/9〜9/15 本と振れるので、
    ///    従属させると帯の落葉が 0〜60% へ跳ね、検査の 20〜35% に入らない区画が出る。固定にすると
    ///    庭方の検算で実測 25〜32% に収まり、帯が0本の区画もモミジ層(直し②)で届く。</summary>
    static float DeShare(int band)
    {
        if (band <= 0) return 0f;
        return 0.30f;
    }

    /// <summary>庭のクロマツ(主木)。⭐ 在庫の `JG.Pine` は独立して枝を張った**庭の松**で、
    /// `Own.Matsu`(林の松)とは樹形が別。丈は素の 5.6m 前後 = 庭方の「丈5〜7」の帯。</summary>
    static string[] _matsuPal;
    static string[] MatsuPal
    {
        get
        {
            if (_matsuPal == null) _matsuPal = new[]
            {
                EdoAssets.JG.Pine("Big", 1), EdoAssets.JG.Pine("Big", 2), EdoAssets.JG.Pine("Big", 3),
                EdoAssets.JG.Pine("Mid", 1), EdoAssets.JG.Pine("Mid", 2), EdoAssets.JG.Pine("Mid", 3),
            };
            return _matsuPal;
        }
    }
    static string[] _chubokuPal;
    /// <summary>常緑中木 + イロハモミジ。⛔ モミジは別の層として数えるので、ここは常緑だけ。</summary>
    static string[] ChubokuPal
    {
        get
        {
            if (_chubokuPal == null) _chubokuPal = new[]
            {
                EdoAssets.Own.Jouryoku("Mid", 1), EdoAssets.Own.Jouryoku("Mid", 2),
                EdoAssets.Own.Jouryoku("Mid", 3), EdoAssets.Own.Jouryoku("Small", 1),
            };
            return _chubokuPal;
        }
    }
    static string[] _momijiPal;
    static string[] MomijiPal
    {
        get
        {
            if (_momijiPal == null) _momijiPal = new[]
            {
                EdoAssets.Own.Momiji("Small", 1), EdoAssets.Own.Momiji("Small", 2),
                EdoAssets.Own.Momiji("Mid", 3),
            };
            return _momijiPal;
        }
    }
    static string[] _teibokuPal;
    static string[] TeibokuPal
    {
        get
        {
            if (_teibokuPal == null) _teibokuPal = new[]
            {
                EdoAssets.Own.Teiboku("H16", 1), EdoAssets.Own.Teiboku("H16", 2),
                EdoAssets.Own.Teiboku("H20", 3), EdoAssets.Own.Teiboku("H12", 2),
            };
            return _teibokuPal;
        }
    }
    static string[] _karikomiPal;
    static string[] KarikomiPal
    {
        get
        {
            if (_karikomiPal == null) _karikomiPal = new[]
            { EdoAssets.JG.Boxwood(1), EdoAssets.JG.Boxwood(2), EdoAssets.JG.Boxwood(3) };
            return _karikomiPal;
        }
    }
    static string[] _ishiPal;
    /// <summary>景石。⭐ 丈 1.000 に正規化してあるので **localScale = 総丈**。⛔ 1種で並べない。</summary>
    static string[] IshiPal
    {
        get
        {
            if (_ishiPal == null) _ishiPal = new[]
            { EdoAssets.Own.Ishigumi(0), EdoAssets.Own.Ishigumi(1), EdoAssets.Own.Ishigumi(2),
              EdoAssets.Own.Ishigumi(3), EdoAssets.Own.Ishigumi(4) };
            return _ishiPal;
        }
    }
    static string[] _tobiPal;
    /// <summary>飛石。⭐ 長軸 1.000 に正規化。⛔ 個体2(沢飛石・厚0.95)は陸に使わない。</summary>
    static string[] TobiPal
    {
        get
        {
            if (_tobiPal == null) _tobiPal = new[] { EdoAssets.Own.Tobiishi(0), EdoAssets.Own.Tobiishi(1) };
            return _tobiPal;
        }
    }
    static string[] _shidaPal;
    static string[] ShidaPal
    {
        get
        {
            if (_shidaPal == null) _shidaPal = new[] { EdoAssets.JG.Fern(1), EdoAssets.JG.Fern(2) };
            return _shidaPal;
        }
    }

    // ───────────────────────── 小道具 ─────────────────────────

    static int Rng(System.Random r, int lo, int hi) { return r.Next(lo, hi + 1); }
    /// <summary>奇数で引く(⛔ 偶数の塊を作らない)。</summary>
    static int Odd(System.Random r, int lo, int hi)
    {
        int v = Rng(r, lo, hi); if ((v & 1) == 0) v = (v + 1 <= hi) ? v + 1 : v - 1;
        return Mathf.Max(1, v);
    }
    static float Rf(System.Random r, float lo, float hi) { return Mathf.Lerp(lo, hi, (float)r.NextDouble()); }

    /// <summary>層の本数を**奇数の塊**へ割る(7/5/3/1)。⛔ 偶数を作らない(§5-0「塊」)。</summary>
    static List<int> OddSplit(int total, System.Random rnd)
    {
        var L = new List<int>();
        while (total > 0)
        {
            int c = total >= 7 ? 7 : (total >= 5 ? 5 : (total >= 3 ? 3 : 1));
            if (c >= 5 && rnd.NextDouble() < 0.5) c -= 2;
            if (c > total) c = 1;
            L.Add(c); total -= c;
        }
        return L;
    }

    static float MaxCrown(string[] pal)
    {
        float m = 0f; foreach (var p in pal) m = Mathf.Max(m, EdoBuild.CrownR(p)); return m;
    }

    /// <summary>候補の池から、その半径が本当に空いている点を1つ取り出す。
    /// ⭐ **池から外すのは据わった点だけ**(検分④)。⛔ 空いていなかった点まで捨てない —
    /// 捨てると候補が**成否に関わらず**枯れて、後ろの層(小さい駒なら置けた層)が丸ごと 0 になる
    /// (2026-09-22 実測: 6区画でモミジ以降が単調に 0)。</summary>
    static Vector2? TakeSite(List<Vector2> pool, System.Random rnd, EdoBuild.NiwaField f,
                             float r, EdoBuild.NiwaSet o)
    {
        var tried = new HashSet<int>();
        for (int t = 0; t < 40 && tried.Count < pool.Count; t++)
        {
            int k = rnd.Next(pool.Count);
            if (!tried.Add(k)) continue;
            var p = pool[k];
            if (!f.Free(p, r, o)) continue;
            pool.RemoveAt(k);                      // ⭐ 据わる点だけを外す
            return p;
        }
        return null;
    }

    /// <summary>層をひと組据える。⭐ **意図した数と据わった数の差を必ず控える**(§5-2 ①・規則19)。
    /// ⭐ 候補の池は**層ごとに引き直す**(検分④)— 呼び手が `new List&lt;Vector2&gt;(main)` を渡すこと。</summary>
    static void Layer(Transform grp, string name, EdoBuild.NiwaField f, List<Vector2> pool, string[] pal,
                      int want, System.Random rnd, EdoBuild.NiwaSet o,
                      List<string> want_, List<string> got_)
    {
        int cap = Mathf.Max(0, NIWA_BUDGET - f.Komas.Count);
        int n = Mathf.Min(want, cap);
        int made = 0;
        if (n > 0 && pal.Length > 0)
        {
            float rr = MaxCrown(pal) * o.ScaleHi;
            foreach (int c in OddSplit(n, rnd))
            {
                var site = TakeSite(pool, rnd, f, rr, o);
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, name, f, site.Value, pal, c, rnd, o, name).Count;
            }
        }
        want_.Add(name + " " + want); got_.Add(name + " " + made);
    }

    /// <summary>**主景の帯** — 座敷面の中点 + 法線 3.0m を起点に、幅 = 面長 + 左右各 4.0m・奥行 25m の
    /// 帯と庭域 G の交わり(検分⑨)。⛔ 半角35°の扇で採らない — 扇はどの区画でも同じ 382m² にしかならず、
    /// **面長に従属しない**(設計と §4.5 は「面長×奥行25」と書いている)。</summary>
    static List<Vector2> MainBand(EdoBuild.NiwaField f, Vector2 apex, Vector2 n, float faceLen, float depth)
    {
        var perp = new Vector2(-n.y, n.x);
        float halfW = faceLen * 0.5f + 4.0f;
        var L = new List<Vector2>();
        foreach (var p in f.Cells)
        {
            var d = p - apex;
            float along = Vector2.Dot(d, n);
            if (along < 0f || along > depth) continue;
            if (Mathf.Abs(Vector2.Dot(d, perp)) > halfW) continue;
            L.Add(p);
        }
        return L;
    }

    /// <summary>門の**通り抜け**(柱間)[m] — 参道の帯(白洲)の幅を引くための代用値(検分③)。
    /// ⛔ 門構えの全幅ではない(長屋門の両翼は長屋)。⛔ 部材の名から推し量らず、
    /// <see cref="GatePath"/> に実在する綴りだけで引く(表に無い型は「他 = 1間」へ落とす)。
    /// <list type="bullet">
    /// <item>長屋門 2間 = 3.64m(`nagayamon`)</item>
    /// <item>高麗門・薬医門・棟門 1.5間 = 2.73m(`hmon` / `yakuimon` / `munemon` /
    ///   `kmon` — 在庫の `Eg.Kmon` も薬医門・<see cref="EdoAssets"/> の注記)</item>
    /// <item>他(冠木門 `kabukimon`・小門 `komon`・山門 `sanmon`)1間 = 1.82m</item>
    /// </list></summary>
    static float GateThrough(string gate)
    {
        switch (gate)
        {
            case "nagayamon": return 2f * ES;
            case "hmon": case "yakuimon": case "munemon": case "kmon": return 1.5f * ES;
            default: return 1f * ES;
        }
    }

    static float Perimeter(Vector2[] poly)
    {
        float p = 0f;
        for (int i = 0; i < poly.Length; i++) p += Vector2.Distance(poly[i], poly[(i + 1) % poly.Length]);
        return p;
    }

    // ───────────────────────── Stage 5 ─────────────────────────

    /// <summary>庭を建てる。<paramref name="gateC"/> / <paramref name="gateHalf"/> は Stage 1 で
    /// **実測した門構えの開口**(⛔ 当て推量の GateWidth ではない)。参道の帯はここから引く。</summary>
    static string Niwa(Spec s, Transform root, Vector2[] poly, Edge front, float pad,
                       Vector2 gateC, float gateHalf)
    {
        string g = s.garden;
        if (string.IsNullOrEmpty(g)) return "  庭: 表に garden の欄が無い(町屋・寺社・公有地)— 建てない";
        if (g == "none") return "  庭: garden=none — 建てない(御家人の小屋敷)";

        var log = new List<string>();
        var grp = Group("Niwa", root);
        var rnd = new System.Random(EdoBuild.Seed(s.id + ":niwa"));
        var f = new EdoBuild.NiwaField(poly);

        // ── 5a 庭の地 — 棟の**軒込み外形**と囲いの**壁体**を実メッシュで撒く(⛔ 外接箱で退けない) ──
        var tate = root.Find("Tatemono");
        var mune = new List<Transform>();
        if (tate != null) foreach (Transform t in tate)
            { if (t.GetComponentsInChildren<Renderer>().Length == 0) continue; f.Eaves.AddBody(t, 400, true); mune.Add(t); }
        foreach (var nm in new[] { "Kakoi", "Mon" })
        {
            var q = root.Find(nm); if (q == null) continue;
            foreach (Transform t in q) f.Walls.AddBody(t, 160, false);
        }
        if (mune.Count == 0)
            return "  ⛔ 庭: 棟が1つも建っていないので庭域(軒からの距離)が解けない — 庭は建てない";

        // 参道の帯(白洲): 門の中心 → 棟の門側の面の最近点。片側 = 実測の開口/2 + 1.5(§5-0 c)
        var omoya = mune[0].gameObject;                       // 最初に据わった棟
        var rbO = EdoBuild.RB(omoya);
        var cO = new Vector2(rbO.center.x, rbO.center.z);
        // ⭐ 帯の幅は**門の通り抜けの実開口**から。⛔ 門構え全体の幅を開口と呼ばない —
        //    長屋門は両翼が長屋(壁体)なので、全幅で白洲を引くと小さい区画は庭域が丸ごと消える。
        var alongF = (front.b - front.a).normalized;
        GameObject monGo = null;
        var monGrp = root.Find("Mon");
        if (monGrp != null) foreach (Transform t in monGrp)
            if (t.name.StartsWith("Mon_")) { monGo = t.gameObject; break; }
        float cproj; float opening = EdoBuild.NiwaGateOpening(monGo, alongF, out cproj);
        string openHow;
        if (!float.IsNaN(opening))
        {
            gateC = front.a + alongF * (cproj - Vector2.Dot(front.a, alongF));   // 開口の芯へ寄せる
            openHow = string.Format("実測の通り抜け {0:F1}m", opening);
        }
        else
        {
            // ⛔ 門構えの**全幅**で代用しない(検分③)。長屋門は両翼が長屋なので、全幅で引くと
            //    白洲が片側 18.5m = 幅 37m になり、庭域を削って前庭の松の置き場まで潰す。
            //    代用するのは**門の格ごとの通り抜け**(柱間)。28区画すべてで門扉が閉じた駒なので
            //    空きの連なりが出ず、いまは全区画がこの道を通る。
            opening = GateThrough(s.gate);
            openHow = string.Format("⚠ 通り抜けが測れず 門の格({0})の柱間 {1:F2}m で代用", s.gate ?? "無指定", opening);
        }
        // ⭐ 片側の上限 6.0m(実測できた場合も含む)— 武家屋敷の玄関前の白洲は 5〜10間【B】
        float half = Mathf.Min(opening * 0.5f + 1.5f, 6.0f);
        Vector2 sandoB = cO;
        {
            float best = float.MaxValue;
            foreach (var w in EdoBuild.Body(omoya.transform, 400, false))
            {
                var q = new Vector2(w.x, w.z); float d = Vector2.Distance(q, gateC);
                if (d < best) { best = d; sandoB = q; }
            }
        }
        f.AddBand(gateC, sandoB, half);
        // ⭐ small は**前後貫通** — 裏門の帯も白洲扱いで空ける(§5-1 small)
        if (g == "small")
        {
            // ⛔ 区画の**頂点**を裏口に採らない(軸から外れた隅へ帯が曲がる)。門から棟へ引いた軸を
            //    そのまま奥へ延ばし、区画から出る所を歩いて探す。
            var away = (cO - gateC).sqrMagnitude > 0.01f ? (cO - gateC).normalized : Vector2.up;
            Vector2 hit = cO;
            for (float t = 0f; t < 400f; t += 2f)
            {
                var q = cO + away * t;
                if (!EdoGeom.PIP(poly, q)) break;
                hit = q;
            }
            if (Vector2.Distance(hit, cO) > 4f) f.AddBand(cO, hit, half * 0.8f);
        }

        f.Solve(1.2f);
        if (f.Cells.Count == 0)
            return string.Format("  ⚠ 庭({0}): 庭域が 0 — 棟と囲いと参道の帯で敷地が埋まっている(庭は建てない)", g);

        // 座敷面 — 棟の4面のうち庭域の点が最多の面。同数なら門から遠い面(§5-0 b)
        var tr = omoya.transform;
        var axes = new List<Vector2>
        {
            new Vector2(tr.right.x, tr.right.z).normalized, new Vector2(-tr.right.x, -tr.right.z).normalized,
            new Vector2(tr.forward.x, tr.forward.z).normalized, new Vector2(-tr.forward.x, -tr.forward.z).normalized,
        };
        Vector2 zashikiN = axes[0], zashikiApex = cO, zashikiMid = cO; float zashikiLen = 10f; int bestN = -1;
        foreach (var n in axes)
        {
            if (n.sqrMagnitude < 0.5f) continue;
            float hw = EdoBuild.ProjSpan(omoya, n) * 0.5f;
            var mid = cO + n * hw;
            var apex = mid + n * 3.0f;
            float faceLen = EdoBuild.ProjSpan(omoya, new Vector2(-n.y, n.x));
            int c = MainBand(f, apex, n, faceLen, 25f).Count;
            bool better = c > bestN || (c == bestN && Vector2.Distance(apex, gateC) > Vector2.Distance(zashikiApex, gateC));
            if (!better) continue;
            bestN = c; zashikiN = n; zashikiApex = apex; zashikiMid = mid; zashikiLen = faceLen;
        }
        var main = MainBand(f, zashikiApex, zashikiN, zashikiLen, 25f);
        float per = Perimeter(poly);
        var want = new List<string>(); var got = new List<string>();
        log.Add(string.Format("  庭({0}): 庭域 {1:F0}m²({2}点)/ 周長 {3:F0}m / 座敷面 面長 {4:F1}m"
                            + "・主景の帯(幅 面長+左右4.0 × 奥行25)の候補 {5}点 = {6:F0}m²"
                            + " / 参道の帯 片側 {7:F1}m({8} ÷2 + 1.5・上限6.0)",
                              g, f.Area, f.Cells.Count, per, zashikiLen, main.Count,
                              main.Count * f.Cell * f.Cell, half, openHow));

        // 勝手側(門と反対の半面)の候補点
        var kdir = (cO - gateC).sqrMagnitude > 0.01f ? (cO - gateC).normalized : zashikiN;
        var katte = f.Cells.Where(p => Vector2.Dot(p - cO, kdir) > 0f).ToList();

        switch (g)
        {
            case "chisen": NiwaChisen(s, grp, f, poly, front, rnd, main, katte, per, zashikiLen, zashikiMid, zashikiN, gateC, half, want, got, log, 1.0f); break;
            case "small":  NiwaChisen(s, grp, f, poly, front, rnd, main, katte, per, zashikiLen, zashikiMid, zashikiN, gateC, half, want, got, log, 0.55f); break;
            case "tsubo":  NiwaTsubo(s, grp, f, poly, front, rnd, main, per, zashikiMid, zashikiN, want, got, log); break;
            case "ura":    NiwaUra(s, grp, f, mune, rnd, katte, kdir, cO, want, got, log); break;
            default:       return "  ⚠ 庭: 表の garden=" + g + " は庭方の設計に無い型 — 建てない(表を検め直す)";
        }

        log.Add(NiwaInspect(f, g, want, got));
        return string.Join("\n", log.ToArray());
    }

    // ───────────────────────── chisen / small ─────────────────────────

    /// <summary>池泉(大名上屋敷)と中規模(中屋敷)。<paramref name="k"/> = 1.0 なら chisen、
    /// 0.55 なら small(⛔ small は**池代地を持たない**)。本数はすべて周長と面長からの従属値。</summary>
    static void NiwaChisen(Spec s, Transform grp, EdoBuild.NiwaField f, Vector2[] poly, Edge front,
                           System.Random rnd, List<Vector2> main, List<Vector2> katte,
                           float per, float faceLen, Vector2 zashikiMid, Vector2 zashikiN,
                           Vector2 gateC, float bandHalf,
                           List<string> want, List<string> got, List<string> log, float k)
    {
        bool chisen = k > 0.9f;
        var tree = EdoBuild.NiwaSet.Tree;        // 高木(囲いから幹で 1.2)
        var chu = EdoBuild.NiwaSet.Chuboku;      // 中木(囲いから幹で 0.8)
        var shrub = EdoBuild.NiwaSet.Shrub;
        var kusa = EdoBuild.NiwaSet.Kusa;        // 下草 — 飛石は下草を踏める(検分①)

        // ⭐ **主景の本数を先に引く。**屋敷林は常緑と落葉の両方を持つ唯一の層なので、
        //    他の層の予定を知らないと庭全体の 常緑:落葉 = 7:3(覆さない線③)に着地できない。
        // ⛔ small を chisen の 0.55 倍で割り出さない — 庭方は small の本数を**別に書いている**
        //    (§5-1 small)。倍率で出すと中木 4〜7(書いてあるのは 5〜9)のように黙ってずれる。
        int nMatsu  = chisen ? Odd(rnd, 5, 9)   : Odd(rnd, 3, 5);
        int nChu    = chisen ? Rng(rnd, 7, 13)  : Rng(rnd, 5, 9);
        int nMomiji = chisen ? Rng(rnd, 3, 5)   : Rng(rnd, 2, 3);
        int nTei    = chisen ? Rng(rnd, 15, 30) : Rng(rnd, 10, 20);
        int nKari   = chisen ? Rng(rnd, 3, 5)   : Rng(rnd, 2, 3);      // 刈込の塊(組)
        int nIshi   = chisen ? Rng(rnd, 3, 5)   : Rng(rnd, 2, 3);      // 景石(組)
        int nTobi   = chisen ? Rng(rnd, 12, 24) : Rng(rnd, 10, 18);    // 飛石1条の石数
        int nToro   = chisen ? Rng(rnd, 1, 2)   : 1;
        int nShida  = chisen ? Rng(rnd, 20, 40) : Rng(rnd, 12, 25);

        // ── ④ 層の本数を庭域 A に従属させる(庭方 2026-09-22 の裁定1)⭐ **引いた後に抑える** —
        //    Odd/Rng を引かずに差し替えると後段の層の乱数が丸ごとずれ、検分で見た数が再現しなくなる。
        // ⛔ 当てない3層: モミジ(常緑本数からの従属値なので二重に絞らない)/ 下草(裸地を埋める役目・
        //    被覆率の分子にも入らない)/ 屋敷林(基準は周長で、保険で掛けても実害が無い)。
        nMatsu = f.Area < 1200f ? 1 : (f.Area < 3000f ? Mathf.Min(nMatsu, 3) : nMatsu);
        nChu   = Mathf.Min(nChu,  Mathf.FloorToInt(f.Area / 400f));
        nTei   = Mathf.Min(nTei,  Mathf.FloorToInt(f.Area / 150f));
        nKari  = Mathf.Min(nKari, Mathf.Max(1, Mathf.FloorToInt(f.Area / 1200f)));
        //        ⚠ 刈込は**組数だけ**を抑える。組の中の本数(3〜5)は減らさない(裁定1)。

        // ── ③ 池代地を**先に**囲う(木を置いてからでは動かせない・§5-1 chisen ③)──
        if (chisen)
        {
            // ⭐ 母集合は**座敷面の側の半面ぜんたい**(検分⑤)。⛔ 主景の帯で切らない —
            //    帯(660m²級)を さらに 軒≥12・区画辺≥8 で削ると連結域が数升になり、
            //    22,333坪の屋敷に径2〜3mの水たまりが出来る(2026-09-22 実測・下草は1株も入らなかった)。
            var zashikiSide = f.Cells.Where(p => Vector2.Dot(p - zashikiMid, zashikiN) > 0f).ToList();
            var cand = zashikiSide.Where(p => f.Eaves.Dist(p, 13f) >= 12f && EdoGeom.DistToPolyEdge(poly, p) >= 8f).ToList();
            var blob = EdoBuild.NiwaBlob(f, cand, 6);
            float longD = 0f; Vector2 c = Vector2.zero;
            if (blob.Count >= 6)
            {
                foreach (var p in blob) c += p; c /= blob.Count;
                float mnx = blob.Min(p => p.x), mxx = blob.Max(p => p.x);
                float mnz = blob.Min(p => p.y), mxz = blob.Max(p => p.y);
                longD = (Mathf.Min(mxx - mnx, mxz - mnz) + f.Cell) * 0.55f;      // 長径 = 短辺 × 0.55
            }
            if (longD >= 12f)
            {
                f.Voids.Add(EdoBuild.NiwaVoidPoly(c, longD * 0.5f, rnd));
                log.Add(string.Format("    池代地: 座敷面の側の {0:F0}m² の連結域の重心に 長径 {1:F1}m の不定形の空地を確保"
                                    + "(⛔ 類型では掘らない — 後から木を動かさずに掘れるように空けるだけ)",
                                      blob.Count * f.Cell * f.Cell, longD));
            }
            else log.Add(string.Format("    ⚠ 池代地: 取らなかった — 座敷面の側で 軒から12m・区画辺から8m を満たす"
                                     + "連結域の長径が {0:F1}m(12m 未満・池として小さすぎる)", longD));
        }

        // ── ① 屋敷林の帯。⭐ 基準は**囲いの内側の面**(検分②)──
        {
            // ⛔ 区画の線から 2.5〜7.0 で採らない — 長屋・長屋塀は内へ5〜6m の占めを持つので
            //    帯がその上に乗って丸ごと落ちる(実測 555→285本・61%落ち)。
            //    寄せは**壁の実メッシュから** chisen/small 1.5〜8.0m。
            float lo = 1.5f, hi = 8.0f;
            int sites = Mathf.Max(1, Mathf.RoundToInt(per / (chisen ? 28f : 32f)));
            int capTrees = chisen ? 140 : 70;
            bool fromWall; int blind;
            var pts = EdoBuild.NiwaWallBandSites(f, lo, hi, sites, rnd,
                          p => EdoGeom.DistToEdge(p, front.a, front.b) < hi + 1.5f, out fromWall, out blind);
            int plan = Mathf.Min(capTrees, pts.Count * (chisen ? 4 : 3));
            float deShare = DeShare(plan);          // ⭐ 0.30 固定(直し③)
            var mix = LinMix(rnd, deShare);
            int made = 0, tried = 0;
            foreach (var p in pts)
            {
                if (made >= capTrees || f.Komas.Count >= NIWA_BUDGET) break;
                int n = chisen ? Odd(rnd, 3, 5) : 3;
                tried += n;
                made += EdoBuild.NiwaClump(grp, "Yashikirin", f, p, LinPal, n, rnd, tree, "屋敷林", mix).Count;
            }
            want.Add("屋敷林 " + tried); got.Add("屋敷林 " + made);
            log.Add(string.Format("    屋敷林: 周長 {0:F0}m ÷ {1} = {2}箇所の塊 → {3}/{4}本"
                                + "(囲いの実メッシュから {5:F1}〜{6:F1}m{7}・上限 {8}・落葉の割り {9:P0} = 庭全体を 7:3 にする値)",
                                  per, chisen ? 28 : 32, pts.Count, made, tried, lo, hi,
                                  fromWall ? (blind > 0 ? string.Format("・うち {0}箇所は囲いが無く区画の線から", blind) : "")
                                           : "・⚠ 囲いが1枚も無いので区画の線から", capTrees, deShare));
        }

        // ── ② 主景(座敷面の前の帯)⭐ 池は**層ごとに main から引き直す**(検分④)──
        Layer(grp, "主木の松", f, new List<Vector2>(main), MatsuPal, nMatsu, rnd, tree, want, got);
        Layer(grp, "常緑中木", f, new List<Vector2>(main), ChubokuPal, nChu, rnd, chu, want, got);
        Layer(grp, "モミジ", f, new List<Vector2>(main), MomijiPal, nMomiji, rnd, chu, want, got);
        Layer(grp, "照葉低木", f, new List<Vector2>(main), TeibokuPal, nTei, rnd, shrub, want, got);

        // 刈込の塊(3〜5組)
        {
            int kumi = nKari;
            int made = 0;
            var pool = new List<Vector2>(main);
            float rr = MaxCrown(KarikomiPal) * shrub.ScaleHi;
            for (int i = 0; i < kumi; i++)
            {
                var site = TakeSite(pool, rnd, f, rr, shrub);
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "Karikomi", f, site.Value, KarikomiPal, Odd(rnd, 3, 5), rnd, shrub, "刈込").Count;
            }
            want.Add("刈込 " + kumi + "組"); got.Add("刈込 " + made + "本");
        }
        // 景石(1組 = 三石。丈 1.0 正規化なので localScale = 総丈・沈め = 総丈÷3 の1/3埋め)
        NiwaIshigumi(grp, f, new List<Vector2>(main), rnd, nIshi, want, got);
        // 飛石1条 — 座敷面の中点の外 2.0m から庭へ下りる(⭐ 芯々は石の実寸から・検分①)
        NiwaTobiishi(grp, f, rnd, zashikiMid + zashikiN * 2.0f, zashikiN, nTobi, want, got, log);
        // 灯籠
        NiwaToro(grp, f, new List<Vector2>(main), rnd, nToro, want, got);
        // 井戸(chisen は勝手まわりに1口・small は2口)
        NiwaIdo(grp, f, katte, rnd, chisen ? 1 : 2, want, got, log);
        // ④ 勝手まわりは裸地・木0〜2本
        Layer(grp, "勝手の木", f, new List<Vector2>(katte), ChubokuPal, Rng(rnd, 0, 2), rnd, chu, want, got);
        // ⑤ 前庭は白洲。門の内側の左右に松1〜2本ずつ**必ず非対称**
        NiwaMaeniwa(grp, f, rnd, gateC, bandHalf, front, want, got);
        // 5e 下草(⛔ 予算を超えたら低木から減る — ここが最後)
        Layer(grp, "下草", f, new List<Vector2>(f.Cells), ShidaPal, nShida, rnd, kusa, want, got);
        // 池代地の中は下草だけ(⛔ 木・石を入れない)。
        // ⭐ 輪郭の内ぜんたいではなく**汀の内側 1.5m の環**に置く — 中央は空ける(水になる所・検分⑤)
        if (f.Voids.Count > 0)
        {
            var ring = f.Cells.Where(p => f.InVoid(p)
                                       && EdoGeom.DistToPolyEdge(f.Voids[0], p) <= 1.5f).ToList();
            int n = Mathf.Min(Rng(rnd, 5, 11), Mathf.Max(0, NIWA_BUDGET - f.Komas.Count));
            int made = 0;
            var o = kusa; o.EdgeK = 0.9f;
            foreach (int c in OddSplit(n, rnd))
            {
                Vector2? site = null;
                for (int t = 0; t < 20 && ring.Count > 0; t++)
                {
                    int q = rnd.Next(ring.Count); var p = ring[q]; ring.RemoveAt(q);
                    if (f.Free(p, 0.6f, o, true)) { site = p; break; }
                }
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "IkeShita", f, site.Value, ShidaPal, c, rnd, o, "池代地の下草").Count;
            }
            want.Add("池代地の下草 " + n + "(汀の内 1.5m の環)"); got.Add("池代地の下草 " + made);
        }
    }

    // ───────────────────────── tsubo ─────────────────────────

    /// <summary>坪庭(大身旗本)。⭐ 本義は**棟と棟の間のポケット**(軒から1.0〜6.0 の最大連結成分)。
    /// ⛔ 坪庭に灯籠・刈込を入れない。⚠ 連結成分が48m²未満なら**坪庭を無理に作らない**。</summary>
    static void NiwaTsubo(Spec s, Transform grp, EdoBuild.NiwaField f, Vector2[] poly, Edge front,
                          System.Random rnd, List<Vector2> main, float per,
                          Vector2 zashikiMid, Vector2 zashikiN,
                          List<string> want, List<string> got, List<string> log)
    {
        var tree = EdoBuild.NiwaSet.Tree; var chu = EdoBuild.NiwaSet.Chuboku;
        var shrub = EdoBuild.NiwaSet.Shrub; var kusa = EdoBuild.NiwaSet.Kusa;
        // ⭐ 外周の帯の落葉の割りを出すのに要る(7:3・覆さない線③)。
        // ⛔ **高木+中木だけ**を足す — 低木(坪庭の低木・照葉低木)は全て常緑で、検査の母集団に入らない。
        int plannedEv = 0;
        int nPocketChu = 0;                                // ⭐ モミジの本数(直し②)に要るので外へ出す
        var pocket = EdoBuild.NiwaPocket(f, 1.0f, 6.0f, 12);
        if (pocket.Count >= 12)
        {
            float pocketA = pocket.Count * f.Cell * f.Cell;
            log.Add(string.Format("    坪庭: 棟と棟の間のポケット {0:F0}m²({1}点)", pocketA, pocket.Count));
            nPocketChu = Rng(rnd, 1, 3);                   // ⛔ 引く順を変えない(この後に nPocketTei)
            int nPocketTei = Rng(rnd, 5, 9);
            // ④ 裁定1 ⭐ 坪庭の2層の基準は**ポケット面積**(庭域 A ではない)。引いた後に抑える
            nPocketChu = Mathf.Min(nPocketChu, Mathf.FloorToInt(pocketA / 250f));
            nPocketTei = Mathf.Min(nPocketTei, Mathf.FloorToInt(pocketA / 150f));
            plannedEv += nPocketChu;                       // ⛔ nPocketTei(低木)は足さない
            Layer(grp, "坪庭の中木", f, new List<Vector2>(pocket), ChubokuPal, nPocketChu, rnd, chu, want, got);
            Layer(grp, "坪庭の低木", f, new List<Vector2>(pocket), TeibokuPal, nPocketTei, rnd, shrub, want, got);
            Layer(grp, "坪庭の下草", f, new List<Vector2>(pocket), ShidaPal, Rng(rnd, 8, 15), rnd, kusa, want, got);
            NiwaIshigumi(grp, f, new List<Vector2>(pocket), rnd, 1, want, got);
            // ⭐ 坪庭の飛石は**ポケットの重心**から。起点は座敷面が無い側なので庭域の重心を採る
            var pc = Vector2.zero; foreach (var p in pocket) pc += p; pc /= pocket.Count;
            NiwaTobiishi(grp, f, rnd, pc, zashikiN, Rng(rnd, 5, 9), want, got, log, "坪庭の飛石");
        }
        else log.Add("    ⚠ 坪庭: 軒から1.0〜6.0m の連結成分が 48m² に満たない — 坪庭は作らない(無理に作らない・§5-1)");

        // 小平庭(座敷面の前)⭐ 池は層ごとに main から引き直す(検分④)
        int nMatsu = Odd(rnd, 2, 3), nChu = Rng(rnd, 3, 5), nTei = Rng(rnd, 6, 12);
        // ── ④ 裁定1: 庭域 A に従属させる ⭐ **引いた後に抑える**(乱数の流れを崩さない)
        nMatsu = f.Area < 1200f ? 1 : (f.Area < 3000f ? Mathf.Min(nMatsu, 3) : nMatsu);
        nChu   = Mathf.Min(nChu, Mathf.FloorToInt(f.Area / 400f));
        nTei   = Mathf.Min(nTei, Mathf.FloorToInt(f.Area / 150f));
        // ── ② 小平庭にモミジ一株(江戸の定石・庭方承認)。⭐ 落葉の供給を外周の帯だけに頼らない —
        //    帯の取れ高が 0/9〜9/15 本と振れるので、tsubo は帯が落ちると 100:0 になっていた。
        // ⛔ モミジに A 従属の上限を当てない(裁定1) — 既に常緑の本数からの従属値で、二重に絞ることになる
        int nMomiji = Mathf.Max(1, Mathf.RoundToInt(0.379f * (nPocketChu + nMatsu + nChu)));
        plannedEv += nMatsu + nChu;                        // ⛔ nTei(低木)は足さない
        Layer(grp, "主木の松", f, new List<Vector2>(main), MatsuPal, nMatsu, rnd, tree, want, got);
        Layer(grp, "常緑中木", f, new List<Vector2>(main), ChubokuPal, nChu, rnd, chu, want, got);
        Layer(grp, "モミジ", f, new List<Vector2>(main), MomijiPal, nMomiji, rnd, chu, want, got);
        {
            int kumi = Rng(rnd, 1, 2); int made = 0;
            kumi = Mathf.Min(kumi, Mathf.Max(1, Mathf.FloorToInt(f.Area / 1200f)));   // ④ 組数だけ(裁定1)
            var pool = new List<Vector2>(main);
            float rr = MaxCrown(KarikomiPal) * shrub.ScaleHi;
            for (int i = 0; i < kumi; i++)
            {
                var site = TakeSite(pool, rnd, f, rr, shrub);
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "Karikomi", f, site.Value, KarikomiPal, 3, rnd, shrub, "刈込").Count;
            }
            want.Add("刈込 " + kumi + "組"); got.Add("刈込 " + made + "本");
        }
        Layer(grp, "照葉低木", f, new List<Vector2>(main), TeibokuPal, nTei, rnd, shrub, want, got);
        NiwaIshigumi(grp, f, new List<Vector2>(main), rnd, Rng(rnd, 1, 2), want, got);
        NiwaTobiishi(grp, f, rnd, zashikiMid + zashikiN * 2.0f, zashikiN, Rng(rnd, 8, 14), want, got, log);
        NiwaToro(grp, f, new List<Vector2>(main), rnd, Rng(rnd, 0, 1), want, got);

        // 外周の帯(⛔ 表の辺は除く)— ⭐ 基準は**囲いの内側の面**・周長÷40 箇所 × 3本・上限30本(検分②)
        {
            float lo = 1.5f, hi = 6.0f;
            int sites = Mathf.Max(1, Mathf.RoundToInt(per / 40f));
            bool fromWall; int blind;
            var pts = EdoBuild.NiwaWallBandSites(f, lo, hi, sites, rnd,
                          p => EdoGeom.DistToEdge(p, front.a, front.b) < hi + 1.5f, out fromWall, out blind);
            // ④ 裁定1: 帯は Min(30, 箇所×3, ⌊A/250⌋)。⭐ plan を loop の上限にも使う —
            //    ⛔ 前は plan が DeShare へ渡るだけで、本数は定数 30 で縛っていた(⌊A/250⌋ が効かない)
            int plan = Mathf.Min(30, pts.Count * 3, Mathf.FloorToInt(f.Area / 250f));
            var mix = LinMix(rnd, DeShare(plan));           // ⭐ 0.30 固定(直し③)
            int made = 0, tried = 0;
            foreach (var p in pts)
            {
                if (made >= plan || f.Komas.Count >= NIWA_BUDGET) break;
                tried += 3;
                made += EdoBuild.NiwaClump(grp, "Gaishu", f, p, LinPal, 3, rnd, tree, "外周の帯", mix).Count;
            }
            want.Add("外周の帯 " + tried); got.Add("外周の帯 " + made);
            log.Add(string.Format("    外周の帯: 周長 {0:F0}m ÷ 40 = {1}箇所 → {2}/{3}本"
                                + "(囲いの実メッシュから {4:F1}〜{5:F1}m{6}・上限 {7} = Min(30, 箇所×3, ⌊A/250⌋))",
                                  per, pts.Count, made, tried, lo, hi,
                                  fromWall ? (blind > 0 ? string.Format("・うち {0}箇所は囲いが無く区画の線から", blind) : "")
                                           : "・⚠ 囲いが1枚も無いので区画の線から", plan));
        }
        Layer(grp, "下草", f, new List<Vector2>(f.Cells), ShidaPal, Rng(rnd, 10, 20), rnd, kusa, want, got);
    }

    // ───────────────────────── ura ─────────────────────────

    /// <summary>裏庭(中級旗本)。⭐ **実用の庭。作庭しない庭として作る。**
    /// ⛔ 灯籠・刈込・景石・池を置かない(1つでも入れると茶庭になる)。駒の合計 ≤25。</summary>
    static void NiwaUra(Spec s, Transform grp, EdoBuild.NiwaField f, List<Transform> mune,
                        System.Random rnd, List<Vector2> katte, Vector2 kdir, Vector2 cO,
                        List<string> want, List<string> got, List<string> log)
    {
        const int URA_CAP = 25;
        var chu = EdoBuild.NiwaSet.Chuboku; var shrub = EdoBuild.NiwaSet.Shrub;
        var kusa = EdoBuild.NiwaSet.Kusa;

        // 棟と土蔵の実メッシュを別々に持つ(⛔ 「軒からの距離」ではなく**その棟からの距離**で決める)
        var occOmoya = new EdoBuild.NiwaOcc(); occOmoya.AddBody(mune[0], 300, false);
        Transform kura = mune.FirstOrDefault(t => t.name.IndexOf("Kura", StringComparison.OrdinalIgnoreCase) >= 0);
        EdoBuild.NiwaOcc occKura = null;
        if (kura != null) { occKura = new EdoBuild.NiwaOcc(); occKura.AddBody(kura, 300, false); }

        // 井戸1口 — 棟の勝手側の面から2.5〜4.0 / 土蔵の扉の面から3.0〜6.0
        Vector2? idoAt = null;
        {
            var cand = katte.Where(p =>
            {
                float d1 = occOmoya.Dist(p, 6f);
                if (d1 < 2.5f || d1 > 4.0f) return false;
                if (occKura == null) return true;
                float d2 = occKura.Dist(p, 8f);
                return d2 >= 3.0f && d2 <= 6.0f;
            }).ToList();
            if (cand.Count == 0)
                cand = katte.Where(p => { float d1 = occOmoya.Dist(p, 8f); return d1 >= 2.5f && d1 <= 5.5f; }).ToList();
            var o = EdoBuild.NiwaSet.Stone;
            string ido = EdoAssets.Own.SannoIdoIgeta(909, 450);
            float r = EdoBuild.CrownR(ido);
            var site = TakeSite(cand, rnd, f, r, o);
            want.Add("井戸 1");
            if (site != null && f.Put(grp, ido, site.Value, Rf(rnd, 0f, 360f), 1f, 0f, "Ido", "井戸", o) != null)
            { idoAt = site; got.Add("井戸 1"); }
            else got.Add("井戸 0");
            log.Add("    ⚠ 井戸の駒は山王社のために起こした井桁の井戸(`Own.SannoIdoIgeta`)を当てている —"
                  + " 類型の井戸の部材は未造(部材方へ・EDO-0318)");
        }

        // 飛石1条(勝手口 → 井戸 → 土蔵の扉)。⭐ これが**唯一の石**
        {
            var way = new List<Vector2>();
            float hw = EdoBuild.ProjSpan(mune[0].gameObject, kdir) * 0.5f;
            way.Add(cO + kdir * (hw + 1.0f));                               // 勝手口
            if (idoAt != null) way.Add(idoAt.Value);
            if (kura != null)
            {
                // ⛔ 土蔵の**中心**を終点にしない — 飛石が蔵の中へ入って一枚も置けなくなる。
                //    扉の前(蔵の実メッシュから 1.2m 手前)まで、井戸の側から歩いて詰める。
                var rb = EdoBuild.RB(kura.gameObject);
                var kc = new Vector2(rb.center.x, rb.center.z);
                var from = way[way.Count - 1];
                var end = kc;
                for (float t = 0f; t <= 1f; t += 0.05f)
                {
                    var q = Vector2.Lerp(kc, from, t);
                    if (occKura.Dist(q, 3f) >= 1.2f) { end = q; break; }
                }
                if (Vector2.Distance(end, from) > 1.0f) way.Add(end);
            }
            // ⭐ 芯々は**石の実寸**から(検分①)。経路は勝手口→井戸→蔵の扉で機能が決めているので、
            //    石数は経路長 ÷ 芯々 の従属値になる。⚠ 意匠の「6〜12石」と噛み合わない経路は
            //    12枚で打ち切り、要る枚数と一緒に刷る(⛔ 芯々を伸ばして辻褄を合わせない)。
            float total = 0f;
            for (int i = 1; i < way.Count; i++) total += Vector2.Distance(way[i - 1], way[i]);
            float pitch = EdoBuild.NiwaStepPitch(0.45f, rnd);
            int need = Mathf.Max(1, Mathf.RoundToInt(total / pitch) + 1);
            int n = Mathf.Min(need, 12);
            want.Add("飛石 " + n);
            int made = way.Count >= 2
                ? EdoBuild.NiwaStepPath(grp, "Tobiishi", f, way, TobiPal, n, rnd, 0.45f,
                                        EdoBuild.NiwaSet.Path("飛石"), "飛石", pitch).Count : 0;
            got.Add("飛石 " + made);
            log.Add(string.Format("    飛石: 勝手口→井戸→蔵の扉 {0:F1}m ÷ 芯々 {1:F2}m(石の長軸 0.45×1.05〜1.25)"
                                + " = {2}枚要る → {3}枚置いた{4}",
                                  total, pitch, need, made,
                                  need > 12 ? "(⚠ 意匠の上限 12枚で打ち切り — 経路長と『6〜12石』が噛み合っていない)" : ""));
        }

        // 常緑中木1〜2(区画の隅)
        {
            var corners = new List<Vector2>();
            foreach (var p in f.Cells)
                if (EdoGeom.DistToPolyEdge(f.Poly, p) <= 4.0f) corners.Add(p);
            corners.Sort((a, b) => EdoGeom.DistToPolyEdge(f.Poly, a).CompareTo(EdoGeom.DistToPolyEdge(f.Poly, b)));
            Layer(grp, "隅の中木", f, corners, ChubokuPal, Rng(rnd, 1, 2), rnd, chu, want, got);
        }
        // 実のなる木0〜1(ウメ)⚠ 夏姿に花が付いていないか — 生成器(build_tree.py)に花の形は無い
        Layer(grp, "実のなる木", f, new List<Vector2>(katte),
              new[] { EdoAssets.Own.Ume("Small", 1), EdoAssets.Own.Ume("Small", 2) },
              Rng(rnd, 0, 1), rnd, chu, want, got);
        // 照葉低木3〜6を塀際に不等間隔
        {
            var hei = f.Cells.Where(p => f.Walls.Dist(p, 4f) <= 2.5f).ToList();
            Layer(grp, "塀際の低木", f, hei, TeibokuPal, Rng(rnd, 3, 6), rnd, shrub, want, got);
        }
        // 下草5〜10(⛔ 合計 25 駒を超えない)
        {
            int room = Mathf.Max(0, URA_CAP - f.Komas.Count);
            Layer(grp, "下草", f, new List<Vector2>(f.Cells), ShidaPal,
                  Mathf.Min(Rng(rnd, 5, 10), room), rnd, kusa, want, got);
        }
        if (f.Komas.Count > URA_CAP)
            log.Add(string.Format("    ⚠ 裏庭の駒が {0}(上限 {1})— 意匠の「実用の庭」を越えている", f.Komas.Count, URA_CAP));
    }

    // ───────────────────────── 点景 ─────────────────────────

    /// <summary>景石(1組 = 三石)。⭐ 丈 1.000 に正規化した部材なので **localScale = 総丈**、
    /// 沈めは **総丈÷3**(1/3埋め・庭方 §5-0「据え」)。</summary>
    static void NiwaIshigumi(Transform grp, EdoBuild.NiwaField f, List<Vector2> pool, System.Random rnd,
                             int kumi, List<string> want, List<string> got)
    {
        var o = EdoBuild.NiwaSet.Stone;
        o.ScaleLo = 0.75f; o.ScaleHi = 1.35f; o.SinkByScale = 1f / 3f;   // 露出 0.5〜0.9m
        int made = 0;
        for (int i = 0; i < kumi; i++)
        {
            var site = TakeSite(pool, rnd, f, 1.2f, o);
            if (site == null) break;
            made += EdoBuild.NiwaClump(grp, "Ishigumi", f, site.Value, IshiPal, 3, rnd, o, "景石").Count;
        }
        want.Add("景石 " + kumi + "組"); got.Add("景石 " + made + "石");
    }

    /// <summary>飛石1条 — **座敷面の中点の外 2.0m** から庭へ下りる筋(検分①)。
    /// ⛔ 庭域の点を2つ拾って結ばない — それだと芯々が経路長の従属値になり、
    /// 芯々 1.5〜3m の飛び飛びの石になって**一条に見えない**(2026-09-22 実測 356→98枚・9区画で0)。
    /// ⭐ 順は **芯々を石の実寸から決める → 経路長 =(n−1)×芯々 → 出だしの向きを測って決める →
    /// 折れ2箇所で経路を引く**。</summary>
    static void NiwaTobiishi(Transform grp, EdoBuild.NiwaField f, System.Random rnd,
                             Vector2 start, Vector2 aim, int n, List<string> want, List<string> got,
                             List<string> log, string label = "飛石")
    {
        want.Add(label + " " + n);
        var o = EdoBuild.NiwaSet.Path(label);
        float pitch = EdoBuild.NiwaStepPitch(0.45f, rnd);
        float total = Mathf.Max(0.5f, (n - 1) * pitch);
        float r = 0.45f * 0.5f;                       // 石の長軸 0.45 の外接円
        var dir = EdoBuild.NiwaStepAim(f, start, aim, 70f, total, pitch, r, o);
        var way = EdoBuild.NiwaStepWay(start, dir, total, rnd);
        int made = EdoBuild.NiwaStepPath(grp, "Tobiishi", f, way, TobiPal, n, rnd, 0.45f, o, label, pitch).Count;
        got.Add(label + " " + made);
        log.Add(string.Format("    {0}: 芯々 {1:F2}m(石の長軸 0.45×1.05〜1.25)× {2}枚 = 経路 {3:F1}m"
                            + "(座敷面の中点の外2.0m から・折れ2箇所)→ {4}枚",
                              label, pitch, n, total, made));
    }

    /// <summary>灯籠(雪見)。⚠ edogoyomi の駒なので **ES を掛ける**。⛔ 春日灯籠は使わない。</summary>
    static void NiwaToro(Transform grp, EdoBuild.NiwaField f, List<Vector2> pool, System.Random rnd,
                         int n, List<string> want, List<string> got)
    {
        var o = EdoBuild.NiwaSet.Stone;
        int made = 0;
        for (int i = 0; i < n; i++)
        {
            float r = EdoBuild.CrownR(EdoAssets.Own.Toro) * ES;
            var site = TakeSite(pool, rnd, f, r, o);
            if (site == null) break;
            if (f.Put(grp, EdoAssets.Own.Toro, site.Value, Rf(rnd, 0f, 360f), ES, 0f, "Toro_" + i, "灯籠", o) != null) made++;
        }
        want.Add("灯籠 " + n); got.Add("灯籠 " + made);
    }

    /// <summary>井戸。⚠ 類型の井戸の部材は未造で、山王社の井桁の井戸を当てている(部材方へ・EDO-0318)。</summary>
    static void NiwaIdo(Transform grp, EdoBuild.NiwaField f, List<Vector2> katte, System.Random rnd,
                        int n, List<string> want, List<string> got, List<string> log)
    {
        var o = EdoBuild.NiwaSet.Stone;
        string ido = EdoAssets.Own.SannoIdoIgeta(909, 450);
        float r = EdoBuild.CrownR(ido);
        var pool = new List<Vector2>(katte);
        int made = 0;
        for (int i = 0; i < n; i++)
        {
            var site = TakeSite(pool, rnd, f, r, o);
            if (site == null) break;
            if (f.Put(grp, ido, site.Value, Rf(rnd, 0f, 360f), 1f, 0f, "Ido_" + i, "井戸", o) != null) made++;
        }
        want.Add("井戸 " + n); got.Add("井戸 " + made);
        if (made > 0) log.Add("    ⚠ 井戸の駒は山王社の井桁の井戸(`Own.SannoIdoIgeta`)の流用 — 類型の井戸は未造(EDO-0318)");
    }

    /// <summary>前庭。⛔ **帯の中には置かない**(白洲)。門の内側の左右に松を**必ず非対称**に。</summary>
    static void NiwaMaeniwa(Transform grp, EdoBuild.NiwaField f, System.Random rnd, Vector2 gateC,
                            float bandHalf, Edge front, List<string> want, List<string> got)
    {
        var tree = EdoBuild.NiwaSet.Tree;
        var along = (front.b - front.a).normalized;
        int left = Rng(rnd, 1, 2), right = left == 1 ? 2 : 1;       // ⛔ 左右を同数にしない
        int made = 0;
        float rr = MaxCrown(MatsuPal) * tree.ScaleHi;
        for (int side = 0; side < 2; side++)
        {
            int n = side == 0 ? left : right;
            var dir = side == 0 ? along : -along;
            var cand = f.Cells.Where(p =>
            {
                var d = p - gateC;
                return Vector2.Dot(d, dir) > bandHalf && d.magnitude < bandHalf + 22f;
            }).OrderBy(p => Vector2.Distance(p, gateC)).ToList();
            for (int i = 0; i < n; i++)
            {
                var site = TakeSite(cand, rnd, f, rr, tree);
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "Maeniwa", f, site.Value, MatsuPal, 1, rnd, tree, "前庭の松").Count;
            }
        }
        want.Add(string.Format("前庭の松 {0}(左{1}右{2}・非対称)", left + right, left, right));
        got.Add("前庭の松 " + made);
    }

    // ───────────────────────── 検査(0件でも刷る・規則19) ─────────────────────────

    /// <summary>庭方 §5-2 の5項目。⛔ 「置けた本数」だけを刷らない — 意図との差・帯の侵入・
    /// 実測の離れ・偶数の塊・樹冠の被覆率まで出して、はじめて検査になる。</summary>
    static string NiwaInspect(EdoBuild.NiwaField f, string g, List<string> want, List<string> got)
    {
        // ④ 偶数の塊 — ⭐ **塊ごとに**据わった本数を数える(NiwaClump が振った札 clump で)。
        //    ⚠ 意図が奇数でも、置けなかった駒があれば据わった本数は偶数になりうる — 数えるのは据わった数。
        //    塊でない駒(clump=0: 井戸・灯籠・飛石の列)は数えない。
        var perClump = new Dictionary<int, int>();
        foreach (var k in f.Komas)
        {
            if (k.clump <= 0) continue;
            int c; perClump.TryGetValue(k.clump, out c); perClump[k.clump] = c + 1;
        }
        int evenClump = 0; foreach (var kv in perClump) if ((kv.Value & 1) == 0) evenClump++;
        // 同一個体が2本続いた箇所 — ⭐ **同じ塊の中で**据えた順に隣り合う2本(設計 §5-1「個体を混ぜ、
        // 同一個体を2本続けない」は塊の規則)。⛔ 層を通しで見ない — 離れた別の塊の境目は「続いた」でない
        int twin = 0;
        int runClump = 0; var runPath = "";
        foreach (var k in f.Komas)
        {
            if (k.clump <= 0) { runClump = 0; runPath = ""; continue; }
            if (k.clump != runClump) { runClump = k.clump; runPath = ""; }
            if (k.path == runPath) twin++;                 // ⛔ 同じ個体が2本続いた = 乱れ④の欠け
            runPath = k.path;
        }

        float cov = f.Coverage();
        // ⭐ 裁定2(2026-09-22): union で測り直したので**旧式の目安 15〜30% 等は当てない**。
        //    判定は不合格線のふたつだけ — 50%超=林 / 5%未満=禿げ。目安の据え直しは庭方の次巡。
        // ⚠ 5%未満の線は ura に当てていない(従前どおり)— 裏庭は裸地が既定で、当てると全 ura が
        //    新たに赤になる。裁定2 の文面はここに触れていないので**現行の挙動を変えない**方を採った。
        float covLo = g == "tsubo" ? 0.15f : (g == "ura" ? 0.05f : 0.10f);   // 刷らないが引数に残す
        float covHi = g == "tsubo" ? 0.30f : (g == "ura" ? 0.15f : 0.25f);
        bool covBad = cov > 0.50f || (g != "ura" && cov < 0.05f);
        string covMark = cov > 0.50f ? "⛔ 林(50%超)" : (g != "ura" && cov < 0.05f ? "⛔ 禿げ(5%未満)"
                       : "参考(union の新式・旧式の目安は当てない)");
        // ⭐ 常緑:落葉の**分母は高木+中木だけ**(検分⑦)。照葉低木・刈込・坪庭の低木・下草は全て常緑なので、
        //    分母に入れると 7:3 は原理的に届かず、帯が落ちた区画が 100:0 になる。
        int raku = 0, jou = 0;
        foreach (var k in f.Komas)
        {
            if (!k.tall) continue;                        // ⛔ 低木・刈込・下草・石は数えない
            bool de = k.path.Contains("Enoki") || k.path.Contains("Mukunoki") || k.path.Contains("Keyaki")
                   || k.path.Contains("Momiji") || k.path.Contains("Ume");
            if (de) raku++; else jou++;
        }
        int tall = jou + raku;
        float deRatio = tall > 0 ? (float)raku / tall : 0f;
        // 許容(検分⑦): chisen/small/tsubo は落葉 20〜35% / ura は 0〜15%(実のなる木だけ)
        float deLo = g == "ura" ? 0.00f : 0.20f, deHi = g == "ura" ? 0.15f : 0.35f;
        // ⭐ **分母が5本未満の区画には当てない**(庭方 2026-09-22 の直し①)— 裏庭は木が1〜2本しか
        //    立たないので、取り得る比は 0% か 50% だけ。7:3 は原理的に届かず永久に赤になる。
        //    ⛔ 意匠の欠陥ではなく検査の当て方の誤り(規則19「検査の文言と実装の集合を突き合わせる」)。
        bool deThin = tall < 5;
        bool deOk = deThin || (deRatio >= deLo && deRatio <= deHi);
        string deMark = tall == 0 ? "(高木・中木が0本)"
                      : (deThin ? "(分母 " + tall + " 本・5本未満なので当てない)" : (deOk ? "⭕" : "⚠ 許容の外"));
        // ⛔ 据えてから落とした駒は**欠陥ではない**(軒へ食い込む木を落とすのは設計どおりの始末)ので
        //    合否には入れない。ただし件数と最悪値は必ず刷る(規則19「0件を合格と読ませない」)。
        string mark = (f.InBand == 0 && evenClump == 0 && twin == 0 && !covBad && deOk) ? "⭕" : "⛔";
        return string.Format(
            "    {0} 庭の検査({16}): 駒 {1}(予算 {2})/ 参道の帯に入った駒 {3}(許容0)/ 偶数の塊 {4}(塊 {15} 個中・据わった本数で数える)/ 同一個体が続いた箇所 {5}(塊の中で)\n"
          + "      離れの実測: 囲いから **幹の芯**で 最小 {6:F2}m(負は是 — 塀越しに枝が張るのは庭として正しい)"
          + " / 軒から **樹冠の外接円**で 最小 {7:F2}m(層ごとの下限 0.2〜0.4m・割った駒は据えてから落とす→次行)\n"
          + "      樹冠の投影の被覆率 {8:P0} {9}(union・下草/飛石/景石/灯籠/井戸を除く全層・不合格は 50%超{20})"
          + " / 常緑:落葉 = {10:P0}:{11:P0} {21}(高木+中木 {22}本が分母・この型の落葉の許容 {23:P0}〜{24:P0})\n"
          + "      置けなかった駒 {12}(退避で拒んだ)/ 据えてから落とした駒: 軒へ食い込み {17}・区画の線を越え {25}(うち内へ寄せて据わった駒 {30}・寄せても駄目で落とした数がこの {25})・急斜面で据わらず {26}(最悪 {27:F2}m)"
          + " / 起伏が大きく間引かずに据え直した駒 {28} / 幹の芯が測れなかった駒 {29}\n"
          + "      意図: {13}\n      実際: {14}",
            mark, f.Komas.Count, NIWA_BUDGET, f.InBand, evenClump, twin,
            float.IsNaN(f.MinWall) ? 0f : f.MinWall, float.IsNaN(f.MinEave) ? 0f : f.MinEave,
            cov, covMark, 1f - deRatio, deRatio, f.Refused,
            string.Join(" / ", want.ToArray()), string.Join(" / ", got.ToArray()), perClump.Count,
            g, f.DropEave, covLo, covHi, g == "ura" ? "" : "と 5%未満", deMark, tall, deLo, deHi,
            f.DropEdge, f.DropSteep, f.WorstSteep, f.Reseat, f.TrunkNaN, f.Nudged);
    }
}
