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

    /// <summary>帯の落葉の割り = 庭全体を 7:3 にするために、この帯が負う落葉の比。
    /// <paramref name="plannedEv"/> / <paramref name="plannedDe"/> は他の層の予定本数。</summary>
    static float DeShare(int band, int plannedEv, int plannedDe)
    {
        if (band <= 0) return 0f;
        float need = 0.30f * (band + plannedEv + plannedDe) - plannedDe;
        return Mathf.Clamp(need / band, 0f, 0.60f);
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

    /// <summary>候補の池から、その半径が本当に空いている点を1つ取り出す(取った点は池から外す)。</summary>
    static Vector2? TakeSite(List<Vector2> pool, System.Random rnd, EdoBuild.NiwaField f,
                             float r, EdoBuild.NiwaSet o)
    {
        for (int t = 0; t < 40 && pool.Count > 0; t++)
        {
            int k = rnd.Next(pool.Count);
            var p = pool[k]; pool.RemoveAt(k);
            if (f.Free(p, r, o)) return p;
        }
        return null;
    }

    /// <summary>層をひと組据える。⭐ **意図した数と据わった数の差を必ず控える**(§5-2 ①・規則19)。</summary>
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

    /// <summary>扇(半角35°・半径25m)の中の庭域の格子点(§5-0 b「座敷面」)。</summary>
    static List<Vector2> Fan(EdoBuild.NiwaField f, Vector2 apex, Vector2 n, float halfDeg, float radius)
    {
        var L = new List<Vector2>();
        foreach (var p in f.Cells)
        {
            var d = p - apex; float m = d.magnitude;
            if (m < 0.01f || m > radius) continue;
            if (Vector2.Angle(d, n) > halfDeg) continue;
            L.Add(p);
        }
        return L;
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
            opening = gateHalf > 0f ? gateHalf * 2f : 6.0f;
            openHow = string.Format("⚠ 通り抜けが測れず門構えの幅 {0:F1}m で代用", opening);
        }
        float half = opening * 0.5f + 1.5f;
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
        Vector2 zashikiN = axes[0], zashikiApex = cO; float zashikiLen = 10f; int bestN = -1;
        foreach (var n in axes)
        {
            if (n.sqrMagnitude < 0.5f) continue;
            float hw = EdoBuild.ProjSpan(omoya, n) * 0.5f;
            var mid = cO + n * hw;
            var apex = mid + n * 3.0f;
            int c = Fan(f, apex, n, 35f, 25f).Count;
            bool better = c > bestN || (c == bestN && Vector2.Distance(apex, gateC) > Vector2.Distance(zashikiApex, gateC));
            if (!better) continue;
            bestN = c; zashikiN = n; zashikiApex = apex;
            zashikiLen = EdoBuild.ProjSpan(omoya, new Vector2(-n.y, n.x));
        }
        var main = Fan(f, zashikiApex, zashikiN, 35f, 25f);
        float per = Perimeter(poly);
        var want = new List<string>(); var got = new List<string>();
        log.Add(string.Format("  庭({0}): 庭域 {1:F0}m²({2}点)/ 周長 {3:F0}m / 座敷面 面長 {4:F1}m・主景の候補 {5}点"
                            + " / 参道の帯 片側 {6:F1}m({7} ÷2 + 1.5)",
                              g, f.Area, f.Cells.Count, per, zashikiLen, main.Count, half, openHow));

        // 勝手側(門と反対の半面)の候補点
        var kdir = (cO - gateC).sqrMagnitude > 0.01f ? (cO - gateC).normalized : zashikiN;
        var katte = f.Cells.Where(p => Vector2.Dot(p - cO, kdir) > 0f).ToList();

        switch (g)
        {
            case "chisen": NiwaChisen(s, grp, f, poly, front, rnd, main, katte, per, zashikiLen, gateC, half, want, got, log, 1.0f); break;
            case "small":  NiwaChisen(s, grp, f, poly, front, rnd, main, katte, per, zashikiLen, gateC, half, want, got, log, 0.55f); break;
            case "tsubo":  NiwaTsubo(s, grp, f, poly, front, rnd, main, per, want, got, log); break;
            case "ura":    NiwaUra(s, grp, f, mune, rnd, katte, kdir, cO, want, got, log); break;
            default:       return "  ⚠ 庭: 表の garden=" + g + " は庭方の設計に無い型 — 建てない(表を検め直す)";
        }

        log.Add(NiwaInspect(f, want, got));
        return string.Join("\n", log.ToArray());
    }

    // ───────────────────────── chisen / small ─────────────────────────

    /// <summary>池泉(大名上屋敷)と中規模(中屋敷)。<paramref name="k"/> = 1.0 なら chisen、
    /// 0.55 なら small(⛔ small は**池代地を持たない**)。本数はすべて周長と面長からの従属値。</summary>
    static void NiwaChisen(Spec s, Transform grp, EdoBuild.NiwaField f, Vector2[] poly, Edge front,
                           System.Random rnd, List<Vector2> main, List<Vector2> katte,
                           float per, float faceLen, Vector2 gateC, float bandHalf,
                           List<string> want, List<string> got, List<string> log, float k)
    {
        bool chisen = k > 0.9f;
        var tree = EdoBuild.NiwaSet.Tree;
        var shrub = EdoBuild.NiwaSet.Shrub;

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

        // ── ③ 池代地を**先に**囲う(木を置いてからでは動かせない・§5-1 chisen ③)──
        if (chisen)
        {
            var cand = main.Where(p => f.Eaves.Dist(p, 13f) >= 12f && EdoGeom.DistToPolyEdge(poly, p) >= 8f).ToList();
            var blob = EdoBuild.NiwaBlob(f, cand, 6);
            if (blob.Count >= 6)
            {
                var c = Vector2.zero; foreach (var p in blob) c += p; c /= blob.Count;
                float mnx = blob.Min(p => p.x), mxx = blob.Max(p => p.x);
                float mnz = blob.Min(p => p.y), mxz = blob.Max(p => p.y);
                float shortSide = Mathf.Min(mxx - mnx, mxz - mnz) + f.Cell;
                float longR = shortSide * 0.55f * 0.5f;
                f.Voids.Add(EdoBuild.NiwaVoidPoly(c, longR, rnd));
                log.Add(string.Format("    池代地: {0:F0}m² の連結域の重心に 長径 {1:F1}m の不定形の空地を確保"
                                    + "(⛔ 類型では掘らない — 後から木を動かさずに掘れるように空けるだけ)",
                                      blob.Count * f.Cell * f.Cell, longR * 2f));
            }
            else log.Add("    ⚠ 池代地: 軒から12m・区画辺から8m を満たす連結域が無い(棟と囲いで埋まっている)— 空地は取らない");
        }

        // ── ① 屋敷林の帯(囲いの内側)。塊 3〜5本・表門の辺には置かない ──
        {
            float rr = MaxCrown(LinPal) * tree.ScaleHi;
            // ⚠ 帯の寄せは設計では 2.5〜7.0。樹冠が区画の線を越えると Stage6 が**壁体の区域侵犯**として
            //    数えるので(検査は木と軒を見分けない)、寄せの下限を樹冠半径まで押し込む。
            float insetLo = Mathf.Max(chisen ? 2.5f : 2.5f, rr + 0.3f), insetHi = Mathf.Max(7.0f, rr + 1.2f);
            int sites = Mathf.Max(1, Mathf.RoundToInt(per / (chisen ? 40f : 45f)));
            int capTrees = chisen ? 80 : 40;
            var pts = EdoBuild.NiwaBandSites(poly, insetLo, insetHi, sites, rnd,
                          p => EdoGeom.DistToEdge(p, front.a, front.b) < insetHi + 1.5f);
            int plan = Mathf.Min(capTrees, pts.Count * (chisen ? 4 : 3));
            float deShare = DeShare(plan, nMatsu + nChu + nTei, nMomiji);
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
                                + "(内側 {5:F1}〜{6:F1}m・上限 {7}・落葉の割り {8:P0} = 庭全体を 7:3 にする値)",
                                  per, chisen ? 40 : 45, pts.Count, made, tried, insetLo, insetHi, capTrees, deShare));
        }

        // ── ② 主景(座敷面の前の扇)──
        var pool = new List<Vector2>(main);
        Layer(grp, "主木の松", f, pool, MatsuPal, nMatsu, rnd, tree, want, got);
        Layer(grp, "常緑中木", f, pool, ChubokuPal, nChu, rnd, tree, want, got);
        Layer(grp, "モミジ", f, pool, MomijiPal, nMomiji, rnd, tree, want, got);
        Layer(grp, "照葉低木", f, pool, TeibokuPal, nTei, rnd, shrub, want, got);

        // 刈込の塊(3〜5組)
        {
            int kumi = nKari;
            int made = 0;
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
        NiwaIshigumi(grp, f, pool, rnd, nIshi, want, got);
        // 飛石1条 — 座敷の前から庭を横切る
        NiwaTobiishi(grp, f, pool, rnd, nTobi, want, got);
        // 灯籠
        NiwaToro(grp, f, pool, rnd, nToro, want, got);
        // 井戸(chisen は勝手まわりに1口・small は2口)
        NiwaIdo(grp, f, katte, rnd, chisen ? 1 : 2, want, got, log);
        // ④ 勝手まわりは裸地・木0〜2本
        {
            var kp = new List<Vector2>(katte);
            Layer(grp, "勝手の木", f, kp, ChubokuPal, Rng(rnd, 0, 2), rnd, tree, want, got);
        }
        // ⑤ 前庭は白洲。門の内側の左右に松1〜2本ずつ**必ず非対称**
        NiwaMaeniwa(grp, f, rnd, gateC, bandHalf, front, want, got);
        // 5e 下草(⛔ 予算を超えたら低木から減る — ここが最後)
        var fern = new List<Vector2>(f.Cells);
        Layer(grp, "下草", f, fern, ShidaPal, nShida, rnd, shrub, want, got);
        // 池代地の中は下草だけ(⛔ 木・石を入れない)
        if (f.Voids.Count > 0)
        {
            var inside = f.Cells.Where(p => f.InVoid(p)).ToList();
            int n = Mathf.Min(Rng(rnd, 5, 11), Mathf.Max(0, NIWA_BUDGET - f.Komas.Count));
            int made = 0;
            var o = EdoBuild.NiwaSet.Shrub; o.EdgeK = 0.9f;
            foreach (int c in OddSplit(n, rnd))
            {
                Vector2? site = null;
                for (int t = 0; t < 20 && inside.Count > 0; t++)
                {
                    int q = rnd.Next(inside.Count); var p = inside[q]; inside.RemoveAt(q);
                    if (f.Free(p, 0.6f, o, true)) { site = p; break; }
                }
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "IkeShita", f, site.Value, ShidaPal, c, rnd, o, "池代地の下草").Count;
            }
            want.Add("池代地の下草 " + n); got.Add("池代地の下草 " + made);
        }
    }

    // ───────────────────────── tsubo ─────────────────────────

    /// <summary>坪庭(大身旗本)。⭐ 本義は**棟と棟の間のポケット**(軒から1.0〜6.0 の最大連結成分)。
    /// ⛔ 坪庭に灯籠・刈込を入れない。⚠ 連結成分が48m²未満なら**坪庭を無理に作らない**。</summary>
    static void NiwaTsubo(Spec s, Transform grp, EdoBuild.NiwaField f, Vector2[] poly, Edge front,
                          System.Random rnd, List<Vector2> main, float per,
                          List<string> want, List<string> got, List<string> log)
    {
        var tree = EdoBuild.NiwaSet.Tree; var shrub = EdoBuild.NiwaSet.Shrub;
        int plannedEv = 0;                     // ⭐ 外周の帯の落葉の割りを出すのに要る(7:3・覆さない線③)
        var pocket = EdoBuild.NiwaPocket(f, 1.0f, 6.0f, 12);
        if (pocket.Count >= 12)
        {
            var pp = new List<Vector2>(pocket);
            log.Add(string.Format("    坪庭: 棟と棟の間のポケット {0:F0}m²({1}点)", pocket.Count * f.Cell * f.Cell, pocket.Count));
            int nPocketChu = Rng(rnd, 1, 3), nPocketTei = Rng(rnd, 5, 9);
            plannedEv += nPocketChu + nPocketTei;
            Layer(grp, "坪庭の中木", f, pp, ChubokuPal, nPocketChu, rnd, tree, want, got);
            Layer(grp, "坪庭の低木", f, pp, TeibokuPal, nPocketTei, rnd, shrub, want, got);
            Layer(grp, "坪庭の下草", f, pp, ShidaPal, Rng(rnd, 8, 15), rnd, shrub, want, got);
            NiwaIshigumi(grp, f, pp, rnd, 1, want, got);
            NiwaTobiishi(grp, f, pp, rnd, Rng(rnd, 5, 9), want, got);
        }
        else log.Add("    ⚠ 坪庭: 軒から1.0〜6.0m の連結成分が 48m² に満たない — 坪庭は作らない(無理に作らない・§5-1)");

        // 小平庭(座敷面の前)
        var pool = new List<Vector2>(main);
        int nMatsu = Odd(rnd, 2, 3), nChu = Rng(rnd, 3, 5), nTei = Rng(rnd, 6, 12);
        plannedEv += nMatsu + nChu + nTei;
        Layer(grp, "主木の松", f, pool, MatsuPal, nMatsu, rnd, tree, want, got);
        Layer(grp, "常緑中木", f, pool, ChubokuPal, nChu, rnd, tree, want, got);
        {
            int kumi = Rng(rnd, 1, 2); int made = 0;
            float rr = MaxCrown(KarikomiPal) * shrub.ScaleHi;
            for (int i = 0; i < kumi; i++)
            {
                var site = TakeSite(pool, rnd, f, rr, shrub);
                if (site == null) break;
                made += EdoBuild.NiwaClump(grp, "Karikomi", f, site.Value, KarikomiPal, 3, rnd, shrub, "刈込").Count;
            }
            want.Add("刈込 " + kumi + "組"); got.Add("刈込 " + made + "本");
        }
        Layer(grp, "照葉低木", f, pool, TeibokuPal, nTei, rnd, shrub, want, got);
        NiwaIshigumi(grp, f, pool, rnd, Rng(rnd, 1, 2), want, got);
        NiwaTobiishi(grp, f, pool, rnd, Rng(rnd, 8, 14), want, got);
        NiwaToro(grp, f, pool, rnd, Rng(rnd, 0, 1), want, got);

        // 外周の帯(⛔ 表の辺は除く)— 周長÷50 箇所 × 3本・上限18本
        {
            float rr = MaxCrown(LinPal) * tree.ScaleHi;
            float insetLo = Mathf.Max(2.0f, rr + 0.3f), insetHi = Mathf.Max(5.0f, rr + 1.0f);
            int sites = Mathf.Max(1, Mathf.RoundToInt(per / 50f));
            var pts = EdoBuild.NiwaBandSites(poly, insetLo, insetHi, sites, rnd,
                          p => EdoGeom.DistToEdge(p, front.a, front.b) < insetHi + 1.5f);
            int plan = Mathf.Min(18, pts.Count * 3);
            var mix = LinMix(rnd, DeShare(plan, plannedEv, 0));
            int made = 0, tried = 0;
            foreach (var p in pts)
            {
                if (made >= 18 || f.Komas.Count >= NIWA_BUDGET) break;
                tried += 3;
                made += EdoBuild.NiwaClump(grp, "Gaishu", f, p, LinPal, 3, rnd, tree, "外周の帯", mix).Count;
            }
            want.Add("外周の帯 " + tried); got.Add("外周の帯 " + made);
        }
        var fern = new List<Vector2>(f.Cells);
        Layer(grp, "下草", f, fern, ShidaPal, Rng(rnd, 10, 20), rnd, shrub, want, got);
    }

    // ───────────────────────── ura ─────────────────────────

    /// <summary>裏庭(中級旗本)。⭐ **実用の庭。作庭しない庭として作る。**
    /// ⛔ 灯籠・刈込・景石・池を置かない(1つでも入れると茶庭になる)。駒の合計 ≤25。</summary>
    static void NiwaUra(Spec s, Transform grp, EdoBuild.NiwaField f, List<Transform> mune,
                        System.Random rnd, List<Vector2> katte, Vector2 kdir, Vector2 cO,
                        List<string> want, List<string> got, List<string> log)
    {
        const int URA_CAP = 25;
        var tree = EdoBuild.NiwaSet.Tree; var shrub = EdoBuild.NiwaSet.Shrub;

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
            if (site != null && f.Put(grp, ido, site.Value, Rf(rnd, 0f, 360f), 1f, 0f, "Ido", "井戸") != null)
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
            int n = Rng(rnd, 6, 12);
            want.Add("飛石 " + n);
            int made = way.Count >= 2
                ? EdoBuild.NiwaStepPath(grp, "Tobiishi", f, way, TobiPal, n, rnd, 0.45f, EdoBuild.NiwaSet.Stone, "飛石").Count : 0;
            got.Add("飛石 " + made);
        }

        // 常緑中木1〜2(区画の隅)
        {
            var corners = new List<Vector2>();
            foreach (var p in f.Cells)
                if (EdoGeom.DistToPolyEdge(f.Poly, p) <= 4.0f) corners.Add(p);
            corners.Sort((a, b) => EdoGeom.DistToPolyEdge(f.Poly, a).CompareTo(EdoGeom.DistToPolyEdge(f.Poly, b)));
            Layer(grp, "隅の中木", f, corners, ChubokuPal, Rng(rnd, 1, 2), rnd, tree, want, got);
        }
        // 実のなる木0〜1(ウメ)⚠ 夏姿に花が付いていないか — 生成器(build_tree.py)に花の形は無い
        {
            var pool = new List<Vector2>(katte);
            Layer(grp, "実のなる木", f, pool, new[] { EdoAssets.Own.Ume("Small", 1), EdoAssets.Own.Ume("Small", 2) },
                  Rng(rnd, 0, 1), rnd, tree, want, got);
        }
        // 照葉低木3〜6を塀際に不等間隔
        {
            var hei = f.Cells.Where(p => f.Walls.Dist(p, 4f) <= 2.5f).ToList();
            Layer(grp, "塀際の低木", f, hei, TeibokuPal, Rng(rnd, 3, 6), rnd, shrub, want, got);
        }
        // 下草5〜10(⛔ 合計 25 駒を超えない)
        {
            int room = Mathf.Max(0, URA_CAP - f.Komas.Count);
            var pool = new List<Vector2>(f.Cells);
            Layer(grp, "下草", f, pool, ShidaPal, Mathf.Min(Rng(rnd, 5, 10), room), rnd, shrub, want, got);
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

    /// <summary>飛石1条。座敷の前から庭へ下りる筋を、庭域の点を2つ拾って引く。</summary>
    static void NiwaTobiishi(Transform grp, EdoBuild.NiwaField f, List<Vector2> pool, System.Random rnd,
                             int n, List<string> want, List<string> got)
    {
        want.Add("飛石 " + n);
        if (pool.Count < 2) { got.Add("飛石 0"); return; }
        var a = pool[rnd.Next(pool.Count)];
        var far = pool.OrderByDescending(p => Vector2.Distance(p, a)).Take(Mathf.Max(1, pool.Count / 4)).ToList();
        var b = far[rnd.Next(far.Count)];
        var mid = Vector2.Lerp(a, b, 0.5f) + new Vector2(-(b - a).y, (b - a).x).normalized
                * ((float)rnd.NextDouble() - 0.5f) * Vector2.Distance(a, b) * 0.25f;   // ⛔ 一直線に引かない
        var way = new List<Vector2> { a, mid, b };
        int made = EdoBuild.NiwaStepPath(grp, "Tobiishi", f, way, TobiPal, n, rnd, 0.45f, EdoBuild.NiwaSet.Stone, "飛石").Count;
        got.Add("飛石 " + made);
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
            if (f.Put(grp, EdoAssets.Own.Toro, site.Value, Rf(rnd, 0f, 360f), ES, 0f, "Toro_" + i, "灯籠") != null) made++;
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
            if (f.Put(grp, ido, site.Value, Rf(rnd, 0f, 360f), 1f, 0f, "Ido_" + i, "井戸") != null) made++;
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
    static string NiwaInspect(EdoBuild.NiwaField f, List<string> want, List<string> got)
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
        // 設計 §5-2 ⑤: 目安 15〜30% / **50% 超 = 林・5% 未満 = 禿げ**(この2つだけが不合格)。
        // 目安の外でも 5〜50% なら許容 — ただし「⭕」とは刷らず、外れていることは見せる(規則19)
        string covMark = cov > 0.50f ? "⚠ 林" : (cov < 0.05f ? "⚠ 禿げ"
                       : (cov >= 0.15f && cov <= 0.30f ? "⭕" : "(目安の外・許容)"));
        // 常緑:落葉 — 落葉3種とモミジを落葉に数える
        int raku = 0, jou = 0;
        foreach (var k in f.Komas)
        {
            if (k.layer == "下草" || k.layer == "池代地の下草" || k.layer == "坪庭の下草"
                || k.layer == "景石" || k.layer == "飛石" || k.layer == "灯籠" || k.layer == "井戸") continue;
            bool de = k.path.Contains("Enoki") || k.path.Contains("Mukunoki") || k.path.Contains("Keyaki")
                   || k.path.Contains("Momiji") || k.path.Contains("Ume");
            if (de) raku++; else jou++;
        }
        float ratio = (jou + raku) > 0 ? (float)jou / (jou + raku) : 0f;
        string mark = (f.InBand == 0 && evenClump == 0 && twin == 0 && cov >= 0.05f && cov <= 0.50f) ? "⭕" : "⛔";
        return string.Format(
            "    {0} 庭の検査: 駒 {1}(予算 {2})/ 参道の帯に入った駒 {3}(許容0)/ 偶数の塊 {4}(塊 {15} 個中・据わった本数で数える)/ 同一個体が続いた箇所 {5}(塊の中で)\n"
          + "      離れの実測: 囲いから 最小 {6:F2}m / 軒から 最小 {7:F2}m(⛔ 中心点ではなく実バウンズの縁で測った値)\n"
          + "      樹冠の投影の被覆率 {8:P0} {9}(目安 15〜30%)/ 常緑:落葉 = {10:P0}:{11:P0}(目安 70:30)/ 置けなかった駒 {12}\n"
          + "      意図: {13}\n      実際: {14}",
            mark, f.Komas.Count, NIWA_BUDGET, f.InBand, evenClump, twin,
            float.IsNaN(f.MinWall) ? 0f : f.MinWall, float.IsNaN(f.MinEave) ? 0f : f.MinEave,
            cov, covMark, ratio, 1f - ratio, f.Refused,
            string.Join(" / ", want.ToArray()), string.Join(" / ", got.ToArray()), perClump.Count);
    }
}
