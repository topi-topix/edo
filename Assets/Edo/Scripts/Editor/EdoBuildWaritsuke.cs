// EdoBuild — 外周の割付の型と石の倍率(2026-10-17・EDO-0502 岡部 const.nagayaKata / const.ishigakiScale・施主裁定「①案A、②このまま、③伸ばす」)。
//  ・外周の道のり u(据えた表長屋の札の外面の線・外隅 Q で続ける)と、表長屋の駒ごとの割付の位相 φ(PerimeterArcOf / ApplyNagayaKata)
//  ・一続きに見える石垣の石の倍率を一つに揃える(StoneScale / UnifyStoneScale / ChainByEnds)
//  ・外周の棟の系統差(座 − 造成前の地盤の中央値)を棟ごとに数える(SeatEnvelopeReport・掲示板 EDO-0592)
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図を読んで渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    // ================================================================ 表長屋の割付の型(海鼠の目地の位相)

    /// <summary>表長屋の割付の型(指図 const.nagayaKata)。<see cref="p"/> = 海鼠の目地の周期[m](1.5間/7)。NaN なら型を使わない(従前の版のまま)。</summary>
    public class NagayaKata
    {
        public float p = float.NaN; public string src;
        public bool On { get { return !float.IsNaN(p) && p > 0.05f; } }
    }

    /// <summary>const.nagayaKata.rule の文から海鼠の目地の周期を読む ──「海鼠の模様の周期 = 1.5間/7(0.3896)」の分数(間 × <paramref name="ken"/> ÷ 分母)を先に、
    /// 無ければ括弧の小数。読めなければ p = NaN(呼び手が ★ を刷る ── 欄の書式が変わって黙って退くのを防ぐ)。
    /// ⭐ 小数の 0.3896 でなく分数で引く: 生成器 build_nagaya_omote.py の KATA_P = 1.5·1.818/7 = 0.389571 と同じ値にする(周長 600m で 0.045m の差になる)。</summary>
    public static NagayaKata ReadNagayaKata(string rule, float ken = 1.818f)
    {
        var k = new NagayaKata(); if (string.IsNullOrEmpty(rule)) return k;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var m = System.Text.RegularExpressions.Regex.Match(rule, @"周期\s*[=＝]\s*([0-9.]+)\s*間\s*/\s*([0-9]+)");
        if (m.Success) { k.p = float.Parse(m.Groups[1].Value, inv) * ken / float.Parse(m.Groups[2].Value, inv); k.src = m.Value; return k; }
        m = System.Text.RegularExpressions.Regex.Match(rule, @"周期[^(（]*[(（]\s*([0-9.]+)");
        if (m.Success) { k.p = float.Parse(m.Groups[1].Value, inv); k.src = m.Value; }
        return k;
    }

    /// <summary>外周の道のり u の線(閉じた折れ線)。頂点 v の外隅 <see cref="Q"/>[v] = 辺 v−1 の終わりの棟と辺 v の始めの棟の**札の外面の線の交点**
    /// (棟の無い辺は区画の線)。u(Q[0]) = 0 から辺の走りの向き(P[e] → P[e+1])に増える。辺 e の上の点 x の u = uQ[e] + (x − Q[e])·d[e]。</summary>
    public class PerimArc
    {
        public Vector2[] Q, d; public float[] uQ; public string[] via;
        public float U(int edge, Vector2 x) { return uQ[edge] + Vector2.Dot(x - Q[edge], d[edge]); }
    }

    /// <summary>**外周の道のり u の線を、据えた駒の外面から作る**(規則5 ── 区画の線でもピボットでもない)。
    /// 辺ごとの外面の線 = その辺で頂点に接する棟の札の front(<see cref="SpecFrontLine"/>)── 頂点 v の外隅は、辺 v−1 で最も s1 の大きい棟と
    /// 辺 v で最も s0 の小さい棟の外面の線の交点(<see cref="FaceLineCorner"/>)。棟の無い側は区画の線そのもの。二線が平行(折れ 0)なら頂点を辺 v の線へ下ろした点。
    /// 同じ辺の中の棟は外面が平行なので u は控えの違いに依らない(走りの射影)。⟶ 当たる先: 外周を長屋で巡る邸すべて(岡部・類型の外周の長屋・松江松平・土井)。</summary>
    public static PerimArc PerimeterArcOf(Vector2[] P, IList<PerimPiece> pcs)
    {
        int n = P.Length; var arc = new PerimArc { Q = new Vector2[n], d = new Vector2[n], uQ = new float[n], via = new string[n] };
        for (int e = 0; e < n; e++) arc.d[e] = (P[(e + 1) % n] - P[e]).normalized;
        for (int v = 0; v < n; v++)
        {
            int ep = (v - 1 + n) % n;
            PerimPiece A = null, B = null;
            foreach (var x in pcs)
            {
                if (x == null || x.go == null) continue;
                if (x.edge == ep && (A == null || x.s1 > A.s1)) A = x;
                if (x.edge == v && (B == null || x.s0 < B.s0)) B = x;
            }
            Vector2 pa = P[ep], da = arc.d[ep], oa = Vector2.zero, pb = P[v], db = arc.d[v], ob = Vector2.zero;
            bool fa = A != null && SpecFrontLine(A.go, out pa, out da, out oa), fb = B != null && SpecFrontLine(B.go, out pb, out db, out ob);
            if (!fa) { pa = P[ep]; da = arc.d[ep]; }
            if (!fb) { pb = P[v]; db = arc.d[v]; }
            Vector2 q = FaceLineCorner(pa, da, Vector2.zero, 0f, pb, db, Vector2.zero, 0f);
            //   浅い折れで二棟の控えが違うと交点が頂点から遠くへ飛ぶ(折れ 0.5°・控えの差 0.25 で 29m)── 交点が頂点から 2·(控えの大きい方) + 0.5 より離れれば、
            //   外面は角で控えの差だけ段になる(MiterPerimeterCorners の「頂点を通る」と同じ)⇒ 頂点を辺 v の外面の線へ下ろした点で u を続ける
            float cMax = Mathf.Max(Mathf.Abs(Cross2(da.normalized, P[v] - pa)), Mathf.Abs(Cross2(db.normalized, P[v] - pb)));
            if (!float.IsNaN(q.x) && (q - P[v]).magnitude > 2f * cMax + 0.5f) q = new Vector2(float.NaN, float.NaN);
            if (float.IsNaN(q.x)) { Vector2 dn = db.normalized; q = pb + dn * Vector2.Dot(P[v] - pb, dn); arc.via[v] = "平行・浅い折れ(頂点を下ろした点)"; }
            else arc.via[v] = (fa ? "棟" : "線") + "×" + (fb ? "棟" : "線");
            arc.Q[v] = q;
        }
        arc.uQ[0] = 0f;
        for (int v = 1; v < n; v++) arc.uQ[v] = arc.uQ[v - 1] + Vector2.Dot(arc.Q[v] - arc.Q[v - 1], arc.d[v - 1]);
        return arc;
    }

    static float Cross2(Vector2 a, Vector2 b) { return a.x * b.y - a.y * b.x; }

    /// <summary>駒の局所 −X の躯体の端(札 jambL の外面の点)の外周の道のり u0 と向き dir(局所 +X が u の増える向きなら +1)から、
    /// 割付の位相 φ = (−dir·u0) mod p[m](生成器の --kata ── 局所 −X の躯体の端から最初の目地の格子点まで)を出す。
    /// 格子は u ≡ 0 (mod p)── −X 端から x 進んだ点の u は u0 + dir·x なので、u0 + dir·φ ≡ 0。札が無ければ NaN。</summary>
    public static float KataPhase(PerimArc arc, int edge, GameObject go, float p, out float u0, out int dir)
    {
        u0 = float.NaN; dir = 0;
        Vector2 jL = MiterJambPoint(go, false); if (float.IsNaN(jL.x)) return float.NaN;
        Vector2 xd = (EdoPartSpec.W(go.transform, 1f, 0f) - EdoPartSpec.W(go.transform, 0f, 0f)).normalized;
        dir = Vector2.Dot(xd, arc.d[edge]) >= 0f ? 1 : -1;
        u0 = arc.U(edge, jL);
        float ph = (-dir * u0) % p; if (ph < 0f) ph += p;
        return ph;
    }

    /// <summary>名の位相の綴り(cm の整数・生成器の <c>_w%d</c> = round(φ·100))。周期の端(φ が p に 0.005 より近い)は 0 へ回す(格子点が −X 端に在る)。</summary>
    public static int KataPhaseCm(float ph, float p)
    {
        int c = Mathf.RoundToInt(ph * 100f);
        if (c * 0.01f > p - 0.005f) c = 0;
        return c;
    }

    /// <summary>**外周の表長屋を割付の型の版へ差し替える**(指図 const.nagayaKata【硬】・施主裁定 2026-10-17「③伸ばす」)。
    /// <para>手順: ① 据えた駒の外面から外周の道のり u の線を作る(<see cref="PerimeterArcOf"/>・外隅 Q で続ける)
    /// ② 駒ごとに局所 −X の躯体の端の u0 と向き dir から位相 φ(<see cref="KataPhase"/>)③ 今の版の名の末尾に <c>_w&lt;φcm&gt;</c>
    /// (生成器 <c>Tools/Blender/build_nagaya_omote.py --kata &lt;φ&gt;</c> の名の決め)を付けた版を引き、あれば差し替える ──
    /// 高さ = 旧い駒の躯体の底・走りと外面 = 旧い駒の −X の躯体の端の外面の点(札 jambL × front)へ新しい駒の同じ点を着ける(⛔ ピボットで据えない)。
    /// 札の躯体の長さが旧い駒と 0.005 より違えば差し替えない(継ぎ目に口かめり込み)。④ 無ければ待ちへ「要る版: 名・躯体の長さ・φ・留めの角・焼き方」(据えたまま)。</para>
    /// <para>型の外: 門の版(名に <c>_mon</c>・門長屋)・剪断の留め(<c>_m&lt;θ&gt;x&lt;θ&gt;</c>・生成器が --kata と併せない)── 今の版のまま(行に刷る)。
    /// 硬い: 版の名の位相 = 外周の u から出した φ(違う版を据えない)・躯体の長さの一致 ±0.005。柔らかい: 無し(版が無ければ待ち)。</para>
    /// 当たる先: 外周を表長屋で巡る邸すべて(岡部 N12〜N18・N39〜N41 の 24 駒。類型の外周の長屋・松江松平・土井も、型の欄を持てば同じ呼び出し)。</summary>
    public static string ApplyNagayaKata(Vector2[] P, List<PerimPiece> pcs, NagayaKata kata, List<string> wait)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        if (kata == null || !kata.On) return "割付の型: 型の欄が無い・周期が読めない ── 従前の版のまま";
        var live = pcs.FindAll(x => x != null && x.go != null && x.go.activeInHierarchy);
        var arc = PerimeterArcOf(P, live);
        string root = System.IO.Directory.GetParent(Application.dataPath).FullName;
        int swapped = 0, already = 0, waiting = 0, outOfKata = 0; var sb = new System.Text.StringBuilder();
        foreach (var x in live)
        {
            string path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(x.go) ?? "";
            string dirP = System.IO.Path.GetDirectoryName(path)?.Replace('\\', '/') ?? "", stem = System.IO.Path.GetFileNameWithoutExtension(path);
            if (stem.Contains("_mon") || !float.IsNaN(x.gateS)) { outOfKata++; sb.Append("  " + x.label + ": 門の版(型の外)── " + stem + " のまま\n"); continue; }
            if (System.Text.RegularExpressions.Regex.IsMatch(stem, @"_kutai_m-?\d+x-?\d+")) { outOfKata++; sb.Append("  ⚠ " + x.label + ": 剪断の留めの版 " + stem + " は型にできない(生成器が --kata と併せない)── 切る留め(_mc)の版が要る\n"); continue; }
            string bas = System.Text.RegularExpressions.Regex.Replace(stem, @"_w\d+$", "");
            float u0; int dir; float ph = KataPhase(arc, x.edge, x.go, kata.p, out u0, out dir);
            if (float.IsNaN(ph)) { waiting++; wait.Add("割付の型 " + x.label + ": 札が無く躯体の端が測れない(" + stem + ")── 型の版を引けない"); continue; }
            int pc = KataPhaseCm(ph, kata.p);
            string want = bas + "_w" + pc, wantPath = dirP + "/" + want + ".fbx";
            var oldSp = EdoPartSpec.Get(path); float Lold = SpecBodyLen(oldSp);
            var mc = System.Text.RegularExpressions.Regex.Match(bas, @"_mc(-?\d+)x(-?\d+)");
            string ang = mc.Success ? "留め −X " + (int.Parse(mc.Groups[1].Value) / 10f).ToString("0.#", inv) + "° / +X " + (int.Parse(mc.Groups[2].Value) / 10f).ToString("0.#", inv) + "°" : "留めなし";
            string row = x.label + ": u0 " + u0.ToString("F3", inv) + "・向き " + (dir > 0 ? "+" : "−") + "・φ " + ph.ToString("F4", inv) + " → " + want;
            if (stem == want) { already++; sb.Append("  ⭕ " + row + "(型の版のまま)\n"); continue; }
            bool have = System.IO.File.Exists(System.IO.Path.Combine(root, wantPath)) && UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(wantPath) != null;
            if (!have)
            {
                waiting++;
                var mL = System.Text.RegularExpressions.Regex.Match(bas, @"Nagaya_Omote_([0-9.]+)"); var mF = System.Text.RegularExpressions.Regex.Match(bas, @"_(\d)f");
                string hint = "blender --background --python Tools/Blender/build_nagaya_omote.py -- " + (mL.Success ? mL.Groups[1].Value : "<長さ>") + " --body"
                            + (mF.Success ? " --floors " + mF.Groups[1].Value : "")
                            + (mc.Success ? " --miter-cut " + (int.Parse(mc.Groups[1].Value) / 10f).ToString("0.#", inv) + " " + (int.Parse(mc.Groups[2].Value) / 10f).ToString("0.#", inv) : "")
                            + " --kata " + (pc * 0.01f).ToString("0.00", inv) + " --render";
                wait.Add("割付の型 " + x.label + ": 要る版 " + want + "(躯体 " + (float.IsNaN(Lold) ? "?" : Lold.ToString("F3", inv)) + "m・φ " + (pc * 0.01f).ToString("0.00", inv) + "・" + ang + ")── " + hint + " ⇒ 今の版のまま");
                sb.Append("  ⏳ " + row + "(焼いていない)\n");
                continue;
            }
            var nsp = EdoPartSpec.Get(wantPath); float Lnew = SpecBodyLen(nsp);
            if (float.IsNaN(Lnew) || float.IsNaN(Lold) || Mathf.Abs(Lnew - Lold) > 0.005f)
            {
                waiting++;
                wait.Add("割付の型 " + x.label + ": 版 " + want + " の札の躯体 " + (float.IsNaN(Lnew) ? "?" : Lnew.ToString("F3", inv)) + " が今の版 " + (float.IsNaN(Lold) ? "?" : Lold.ToString("F3", inv)) + " と違う ── 継ぎ目が開く・据えたまま");
                sb.Append("  ✗ " + row + "(躯体の長さが違う)\n");
                continue;
            }
            // 差し替え: 高さ = 躯体の底・走りと外面 = −X の躯体の端の外面の点(実の札)
            Vector2 jOld = MiterJambPoint(x.go, false);
            float yOld = float.MaxValue; foreach (var q in BodyExRoof(x.go.transform, 999999)) yOld = Mathf.Min(yOld, q.y);
            var ng = Place(wantPath, x.go.transform.position, x.go.transform.eulerAngles.y, Vector3.one, x.go.transform.parent, x.go.name + "__kata");
            if (ng == null) { waiting++; wait.Add("割付の型 " + x.label + ": 版 " + want + " を据えられない"); continue; }
            ng.transform.rotation = x.go.transform.rotation;
            float yNew = float.MaxValue; foreach (var q in BodyExRoof(ng.transform, 999999)) yNew = Mathf.Min(yNew, q.y);
            Vector2 jNew = MiterJambPoint(ng, false);
            ng.transform.position += new Vector3(jOld.x - jNew.x, (yOld < float.MaxValue && yNew < float.MaxValue) ? yOld - yNew : 0f, jOld.y - jNew.y);
            string nm = x.go.name; UnityEngine.Object.DestroyImmediate(x.go); ng.name = nm; x.go = ng; swapped++;
            sb.Append("  ⭕ " + row + "(差し替えた)\n");
        }
        return "割付の型(海鼠の周期 " + kata.p.ToString("F5", inv) + "m・u の線 = 据えた棟の外面・外隅 Q で続ける): 差し替え " + swapped + "・型の版のまま " + already
             + "・待ち " + waiting + "・型の外 " + outOfKata + "\n" + sb;
    }

    // ================================================================ 石垣の石の倍率を一つに

    /// <summary>石の倍率の決め(指図 const.ishigakiScale「一続きに見える石垣は石の倍率を一つ(0.25 = 一段 1.0m)に揃える」【硬】)。
    /// <see cref="s"/> が NaN なら揃えない(呼び手の従前の決め)。高さは倍率で吸わず、丈違いの版(<see cref="PathOfH"/>)と根入れで吸う ──
    /// 要る丈の版・隅の駒が焼いていなければ <see cref="wantStraight"/>・<see cref="RunKadoWanted"/> から待ちの表(<see cref="Report"/>)へ。</summary>
    public class StoneScale
    {
        public float s = float.NaN; public string src;
        /// <summary>丈違いの直線の版を引く上限(名の丈 H・素の m)。0.25 なら 16.0 = 実寸 4.0m = 4 段(普請方 N12/N13 の最大 4 段)。</summary>
        public float hNameMax = 16f;
        /// <summary>焼いていない直線の版の名 → 要る見え[m](実寸)の最大。</summary>
        public readonly Dictionary<string, float> wantStraight = new Dictionary<string, float>();
        /// <summary>倍率を揃えた所(誰の・前の値 → 揃えた値)。</summary>
        public readonly List<string> changed = new List<string>();
        public bool On { get { return !float.IsNaN(s) && s > 0f; } }

        /// <summary>呼び手が決めた倍率 <paramref name="want"/> を、揃えるなら <see cref="s"/> へ(違えば <see cref="changed"/> に刷る)。揃えないならそのまま。</summary>
        public float Pick(float want, string who)
        {
            if (!On) return want;
            if (Mathf.Abs(want - s) > 1e-4f) changed.Add(who + " " + want.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + "→" + s.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture));
            return s;
        }

        /// <summary>城の石垣の直線の駒(<see cref="CrestWall.pathOfH"/> ── 名の丈 hName = 見え ÷ 倍率)。素の丈 4.0 までは素の Castle Wall、越えれば焼いてある
        /// 丈違いの版(<see cref="EdoAssets.Own.IshigakiChoku"/>・0.5 刻み・<see cref="hNameMax"/> まで)の hName 以上で最小。どれも足りなければ
        /// 段数の版(名の丈 4.0 × ⌈hName / 4.0⌉ = 実寸で一段 4.0·s ごと)を <see cref="wantStraight"/> へ足し、焼いてある最大を返す(底が浮けば PlaceCrestWall が ★)。</summary>
        public string PathOfH(float hName)
        {
            if (hName <= 4.01f) return EdoAssets.JC.CastleWall;
            string root = System.IO.Directory.GetParent(Application.dataPath).FullName, last = null;
            for (float h = 4.5f; h <= hNameMax + 1e-3f; h += 0.5f)
            {
                string p = EdoAssets.Own.IshigakiChoku(h);
                if (!System.IO.File.Exists(System.IO.Path.Combine(root, p))) continue;
                last = p; if (h >= hName - 0.01f) return p;
            }
            int nDan = Mathf.CeilToInt(hName / 4f - 1e-3f);
            string want = System.IO.Path.GetFileNameWithoutExtension(EdoAssets.Own.IshigakiChoku(4f * nDan));
            float ex = hName * (On ? s : 1f), q; wantStraight[want] = wantStraight.TryGetValue(want, out q) ? Mathf.Max(q, ex) : ex;
            return last ?? EdoAssets.JC.CastleWall;
        }

        /// <summary>頭の一行 + 待ちの表の行(要る直線の版・要る隅の駒 <c>_S&lt;倍率&gt;</c>)。揃えないなら null。</summary>
        public List<string> Report(out string head)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture; var rows = new List<string>();
            if (!On) { head = null; return rows; }
            head = "石の倍率を一つに(const.ishigakiScale【硬】): " + s.ToString("0.##", inv) + "(一段 " + (4f * s).ToString("0.##", inv) + "m)── 揃えた " + changed.Count + " 所"
                 + (changed.Count > 0 ? "(" + string.Join("・", changed.ToArray()) + ")" : "");
            var ks = new List<string>(wantStraight.Keys); ks.Sort();
            foreach (var k in ks)
            {
                var mh = System.Text.RegularExpressions.Regex.Match(k, @"H(\d{4})");
                string hArg = mh.Success ? (int.Parse(mh.Groups[1].Value) / 100f).ToString("0.##", inv) : "<丈>";
                rows.Add("石の倍率 " + s.ToString("0.##", inv) + ": 要る丈の版 " + k + "(見え " + wantStraight[k].ToString("F2", inv) + "m を倍率 " + s.ToString("0.##", inv) + " で受ける・名の丈 " + hArg + " = 実寸 "
                       + (mh.Success ? (int.Parse(mh.Groups[1].Value) / 100f * s).ToString("0.##", inv) : "?") + "m)── blender --background --python Tools/Blender/build_kado.py -- --straight --h " + hArg + " --render ⇒ 今は焼いてある最大の丈で据えた(底が浮く所は ★)");
            }
            string tag = "_S" + Mathf.RoundToInt(s * 100f).ToString("000");
            var kk = new List<string>(); foreach (var k in RunKadoWanted) if (k != null && k.Contains(tag)) kk.Add(k); kk.Sort();
            foreach (var k in kk) rows.Add("石の倍率 " + s.ToString("0.##", inv) + ": 要る隅の駒 " + System.IO.Path.GetFileNameWithoutExtension(k) + " ⇒ 隅は建てない(頂点で突き付け)");
            return rows;
        }
    }

    /// <summary>const.ishigakiScale.rule の文から揃える倍率を読む(「倍率を一つ(0.25 = 一段 1.0m)」)。読めなければ s = NaN(呼び手が ★ を刷る)。</summary>
    public static StoneScale ReadStoneScale(string rule)
    {
        var ss = new StoneScale(); if (string.IsNullOrEmpty(rule)) return ss;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var m = System.Text.RegularExpressions.Regex.Match(rule, @"倍率を一つ\s*[(（]\s*([0-9.]+)");
        if (!m.Success) m = System.Text.RegularExpressions.Regex.Match(rule, @"([0-9.]+)\s*[=＝]\s*一段");
        if (m.Success) { float v; if (float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, inv, out v) && v > 0f) { ss.s = v; ss.src = m.Value; } }
        return ss;
    }

    /// <summary>城の石垣の区間の倍率を一つに揃える(<paramref name="ss"/> が揃えないなら何もしない)。揃えた区間は組(insetKey)ごとに <see cref="StoneScale.changed"/> へ。
    /// 当たる先: <see cref="PlaceCastleRun"/> に区間を渡す邸のうち、倍率の欄を持つ物(岡部の外周の台)。</summary>
    public static void UnifyStoneScale(IList<CastleSec> secs, StoneScale ss)
    {
        if (ss == null || !ss.On || secs == null) return;
        var seen = new HashSet<string>();
        foreach (var x in secs)
        {
            if (Mathf.Abs(x.scale - ss.s) <= 1e-4f) continue;
            string key = (x.insetKey ?? x.name) + "@" + x.scale.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture);
            if (seen.Add(key)) ss.Pick(x.scale, x.insetKey ?? x.name);
            x.scale = ss.s;
        }
    }

    /// <summary>端どうしで接する物を一続きに束ねる項(<see cref="ChainByEnds"/>)。a, b = 走りの両端(世界 xz)・scale = 倍率・hasBase = 台を持つか。</summary>
    public class ChainItem { public string name; public Vector2 a, b; public float scale; public bool hasBase; }

    /// <summary>**端と端が <paramref name="tol"/> 以内で接する物どうしを一続きに束ねる**(同じ辺の継ぎ目・段の継ぎ目・出隅・入隅を問わず ── 和集合)。
    /// ⟶ 名 → 一続きの番号。<paramref name="chainMaxScale"/> = 一続きの倍率の最大・<paramref name="chainHasBase"/> = 一続きのどれかが台を持つか。
    /// 当たる先: 外周の長屋の台(岡部 N12〜N18・N39〜N41 ── 台の途切れ 0【硬】・第152巡)。倍率を揃える(<see cref="StoneScale"/>)が効く邸では最大は使わない。</summary>
    public static Dictionary<string, int> ChainByEnds(IList<ChainItem> items, float tol, out Dictionary<int, float> chainMaxScale, out Dictionary<int, bool> chainHasBase)
    {
        int n = items.Count; var par = new int[n]; for (int i = 0; i < n; i++) par[i] = i;
        Func<int, int> find = null; find = x => par[x] == x ? x : (par[x] = find(par[x]));
        for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++)
        {
            var A = items[i]; var B = items[j];
            float dmin = Mathf.Min(Mathf.Min((A.a - B.a).magnitude, (A.a - B.b).magnitude), Mathf.Min((A.b - B.a).magnitude, (A.b - B.b).magnitude));
            if (dmin <= tol) par[find(i)] = find(j);
        }
        var map = new Dictionary<string, int>(); chainMaxScale = new Dictionary<int, float>(); chainHasBase = new Dictionary<int, bool>();
        for (int i = 0; i < n; i++)
        {
            int c = find(i); map[items[i].name] = c;
            float q; chainMaxScale[c] = chainMaxScale.TryGetValue(c, out q) ? Mathf.Max(q, items[i].scale) : items[i].scale;
            bool b0; chainHasBase[c] = (chainHasBase.TryGetValue(c, out b0) && b0) || items[i].hasBase;
        }
        return map;
    }

    // ================================================================ 棟ごとの系統差(規則3・掲示板 EDO-0592)

    /// <summary>系統差を数える一棟。go = 据えた駒(札の foot の外形の中を測る)・seatAt = 世界 xz の点の座(欄の座 ── 坂なりの棟は点ごと)。</summary>
    public class EnvItem { public string name; public GameObject go; public Func<Vector2, float> seatAt; }

    /// <summary>**棟ごとの系統差**(CLAUDE.md 規則3 ──「棟ごとの系統差(足元の地形の中央値と面の差)は ±0.25 以内」・掲示板 EDO-0592)。
    /// 据えた駒の札の外形(foot・局所 x,z の凸包)の中を <paramref name="step"/> の格子で測り、点ごとの 座 − 造成前の地盤(<paramref name="nat"/> ── 規則13 base_dem)の**中央値**を出す。
    /// 硬い(許容 ±<paramref name="tol"/>): 外れて <paramref name="exceptions"/>(指図 planes[].devEnvelopeExceptions・const.nagayaCornerSeat.devEnvelopeExceptions の名)に名の無い棟は ★
    /// (報告に赤・建ては止めない ── 直すのは面と座の欄)。名のある棟は「例外」と刷る。札の無い駒・未建の棟は「測れない」。⟶ 刷る文。<paramref name="bad"/> = ★ の数。
    /// 当たる先: 外周の長屋の run を持つ邸すべて(岡部 N12〜N18・N39〜N41。類型の外周の長屋・松江松平・土井も同じ関数で数えられる)。</summary>
    public static string SeatEnvelopeReport(IList<EnvItem> items, Func<float, float, float> nat, ICollection<string> exceptions, out int bad, float tol = 0.25f, float step = 0.5f)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; bad = 0;
        var sb = new System.Text.StringBuilder(); int nOk = 0, nExc = 0, nNo = 0; var oks = new List<string>();
        foreach (var it in items)
        {
            if (it.go == null || !it.go.activeInHierarchy) { nNo++; sb.Append("  " + it.name + ": 未建 ── 測れない\n"); continue; }
            var sp = EdoPartSpec.Get(UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(it.go) ?? "");
            if (sp == null || sp.foot == null || sp.foot.Count < 3) { nNo++; sb.Append("  " + it.name + ": 札の foot が無い ── 測れない\n"); continue; }
            var poly = new Vector2[sp.foot.Count]; for (int i = 0; i < poly.Length; i++) poly[i] = EdoPartSpec.W(it.go.transform, sp.foot[i].x, sp.foot[i].y);
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var q in poly) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
            var ds = new List<float>();
            for (float x = x0; x <= x1 + 1e-4f; x += step) for (float z = z0; z <= z1 + 1e-4f; z += step)
            {
                var p = new Vector2(x, z); if (!EdoGeom.PIP(poly, p)) continue;
                float g = nat(x, z), y = it.seatAt(p); if (float.IsNaN(g) || float.IsNaN(y)) continue; ds.Add(y - g);
            }
            if (ds.Count == 0) { nNo++; sb.Append("  " + it.name + ": 外形の中に地盤の点が無い ── 測れない\n"); continue; }
            ds.Sort(); float med = ds.Count % 2 == 1 ? ds[ds.Count / 2] : 0.5f * (ds[ds.Count / 2 - 1] + ds[ds.Count / 2]);
            float lo = ds[0], hi = ds[ds.Count - 1];
            string v = it.name + " " + med.ToString("+0.00;-0.00", inv);
            if (Mathf.Abs(med) <= tol + 1e-4f) { nOk++; oks.Add(v); continue; }
            if (exceptions != null && exceptions.Contains(it.name)) { nExc++; sb.Append("  例外 " + v + "(devEnvelopeExceptions に名がある・ばらつき " + lo.ToString("+0.00;-0.00", inv) + "〜" + hi.ToString("+0.00;-0.00", inv) + ")\n"); continue; }
            bad++; sb.Append("  ★ " + v + " が ±" + tol.ToString("0.00", inv) + " を外れる(devEnvelopeExceptions に名が無い・ばらつき " + lo.ToString("+0.00;-0.00", inv) + "〜" + hi.ToString("+0.00;-0.00", inv) + "・点 " + ds.Count + ")── 面と座の欄を直すか施主の言葉つきで例外へ\n");
        }
        return "棟の系統差(座 − 造成前の地盤 base_dem の中央値・±" + tol.ToString("0.00", inv) + "【硬・建ては止めない】): ⭕ " + nOk + "・例外 " + nExc + "・★ " + bad + "・測れない " + nNo
             + (oks.Count > 0 ? "\n  ⭕ " + string.Join(" / ", oks.ToArray()) : "") + "\n" + sb;
    }
}
