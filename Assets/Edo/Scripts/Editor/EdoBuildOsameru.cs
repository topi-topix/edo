// 寄せて測るを収まるまで回す (EdoBuild の partial・2026-09-26・EDO-0454)
//
// ⭐ **何が足りなかったか**: 据え付けは「寄せる(Abut)→ 据える(SeatOnGround)」を組にして使うが、横へ寄せると
//    足元の地形が変わり、据え直すと当たりがまた開く(実測 0.062m・docs/oki-kata.md §2)。それを邸ビルダーは
//    `for (pass < 2)` `for (pass < 4)` の決め打ちで回し、収まったかは**最後に測って log に刷るだけ**だった。
//    収まらなければ役が log を読んで、寄せ直す命令を書き、Unity で流して、また読む — その往復が建て直しの
//    考える時間の 1/3 を食っていた(docs/Hikitsugi/infra_sokudo_2026-09-26.md「実測」)。
//
// ⭕ <see cref="EdoBuild.Converge"/> は取り合い(<see cref="EdoBuild.Tori"/>)の並びを**収まるまで**回し、
//    **合否と理由**を返す。役は結果を読んで判断しなくてよい(⭕ なら次へ・⛔ なら理由の取り合いだけを見る)。
//
//    ・解く順は渡した順(固定側 → 可動側。docs/oki-kata.md §2 の4手)。最後は高さの取り合いにする(埋没・浮きは許容0)
//    ・帯の中の取り合いは動かさない(動かすほど他の取り合いを開く)
//    ・巡ごとに全部測り、**一番よかった姿**を覚えておく。引き合って縮まなくなったら、そこへ戻して止める
//    ・硬い制約(許容0)が帯の外なら ⛔ + 理由。柔らかい制約(狙い)は ⚠ 狙い未達で、合否は落とさない(§4a)
//
// ⛔ 事後に寄せる関数ではない(§2 の4手④)— 置く段で、置き方の関数を束ねて回すだけ。建った後の欠陥を隠さない:
//    収まらなければ ⛔ で返し、呼び手は建てない(退ける)か、理由を刷って止まる。
//
// 当たる先: 類型ビルダーの番所→門(EdoTypologyBuilder Stage 1・2b)。同じ型 = 「寄せる → 据える」を決め打ちの巡で
//   回している所すべて — 山王の井戸(EdoSannoShaRebuild.Stage8_Ido の pass<2 ×3)・野面の乱積みの戻し
//   (EdoBuildNozura の pass<2/3/4)・石段と門の間の土留め・袖。
using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**取り合い一つ。**「残り」(0 が狙い・単位 m)を測る手と、一手寄せる手の組。
    /// 残りが帯 [<see cref="Lo"/>, <see cref="Hi"/>] に入れば納まり。⭐ 作るのは下の工場(<see cref="Abut"/> ほか)で、
    /// 自前の手は <see cref="Custom"/> で渡す。</summary>
    public sealed class Tori
    {
        public readonly string Name;
        public readonly GameObject Mover;
        /// <summary>true = 許容0(帯の外なら ⛔)/ false = 狙い(帯の外でも ⚠ で建てる)。docs/oki-kata.md §4a。</summary>
        public readonly bool Hard;
        public readonly float Lo, Hi;
        readonly Func<float> measure;
        readonly Func<float> apply;

        Tori(string name, GameObject mover, bool hard, float lo, float hi, Func<float> measure, Func<float> apply)
        { Name = name; Mover = mover; Hard = hard; Lo = lo; Hi = hi; this.measure = measure; this.apply = apply; }

        /// <summary>残り[m]。測れなければ NaN(⛔ 0 で埋めない)。</summary>
        public float Measure() { try { return measure(); } catch (Exception) { return float.NaN; } }
        /// <summary>一手寄せる。返り値 = 動かした量[m](向き合わなければ NaN)。</summary>
        public float Apply() { try { return apply(); } catch (Exception) { return float.NaN; } }
        /// <summary>帯の外へ出ている量[m](帯の中なら 0・測れなければ +∞)。</summary>
        public float Excess(float r)
        {
            if (float.IsNaN(r)) return float.PositiveInfinity;
            return r < Lo ? Lo - r : r > Hi ? r - Hi : 0f;
        }

        /// <summary>**駒どうしの突き付け。**<paramref name="mover"/> を <paramref name="dir"/>(mover → other)へ動かし、
        /// 触れている箇所の隙(<see cref="EdoBuild.Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>)を
        /// <paramref name="gap"/> ± <paramref name="tol"/> へ。残り = 隙 − gap(正 = 開き・負 = めり込み)。</summary>
        public static Tori Abut(GameObject mover, GameObject other, Vector3 dir, float gap = 0f, float tol = 0.005f,
                                bool hard = true, float cell = 0.25f, int maxSamples = 4000, bool withRoof = true)
        {
            return new Tori(mover.name + "→" + other.name, mover, hard, -tol, tol,
                () => { Vector3 a; int n; return EdoBuild.Contact(mover, other, dir, out a, out n, 0.01f, cell, maxSamples, withRoof) - gap; },
                () => { Vector3 a; int n; return EdoBuild.Abut(mover, other, dir, gap, out a, out n, cell, maxSamples, withRoof); });
        }

        /// <summary>**地面に据える。**残り = 触れている箇所の隙 + <paramref name="sink"/>(正 = 浮き・負 = 埋没)。
        /// <see cref="EdoBuild.SeatOnGround"/> で寄せる。</summary>
        public static Tori Ground(GameObject mover, float sink = 0f, float tol = 0.01f, bool hard = true, int maxSamples = 4000)
        {
            return new Tori(mover.name + " 接地", mover, hard, -tol, tol,
                () => { Vector3 a; int n; return EdoBuild.Contact(mover, out a, out n, 0.01f, maxSamples) + sink; },
                () => EdoBuild.SeatOnGround(mover, sink, maxSamples));
        }

        /// <summary>**浮いていれば床へ下ろす**(<see cref="EdoBuild.SettleOnBed"/>)。座は上限なので、埋まり(根入れ)は帯の中。
        /// 残り = 床との隙(正 = 浮き)。</summary>
        public static Tori OnBed(GameObject mover, Func<float, float, float> bedAt, float tol = 0.01f, bool hard = true,
                                 int maxSamples = 4000)
        {
            return new Tori(mover.name + " 床", mover, hard, float.NegativeInfinity, tol,
                () => { Vector3 a; int n; return EdoBuild.ContactOn(mover, bedAt, out a, out n, 0.01f, maxSamples); },
                () => { float b; return -EdoBuild.SettleOnBed(mover, bedAt, out b, maxSamples); });
        }

        /// <summary>**受けの上に載せる**(材で絞った鉛直の当たり・<see cref="EdoBuild.RestOn"/>)。残り = 隙 − gap。</summary>
        public static Tori Rest(GameObject mover, string moverMat, GameObject bed, string bedMat, float gap = 0f,
                                float tol = 0.005f, bool hard = true)
        {
            return new Tori(mover.name + "／" + bed.name, mover, hard, -tol, tol,
                () => { Vector3 a; int n; return EdoBuild.RestGap(mover, moverMat, bed, bedMat, out a, out n) - gap; },
                () => { Vector3 a; int n; return EdoBuild.RestOn(mover, moverMat, bed, bedMat, gap, out a, out n); });
        }

        /// <summary>自前の取り合い。<paramref name="measure"/> は残り(帯 [lo, hi] で納まり・NaN = 測れない)、
        /// <paramref name="apply"/> は一手寄せて動かした量を返す(NaN = 向き合わない)。
        /// ⛔ apply の中で測らずに決め打ちの量を動かさない(規則21)。</summary>
        public static Tori Custom(string name, GameObject mover, bool hard, float lo, float hi,
                                  Func<float> measure, Func<float> apply)
        { return new Tori(name, mover, hard, lo, hi, measure, apply); }
    }

    /// <summary><see cref="Converge"/> の結果。<see cref="Ok"/> と <see cref="Reason"/> だけ読めば次の手が決まる。</summary>
    public sealed class Osamari
    {
        /// <summary>硬い制約が全部帯の中なら true(柔らかい制約の未達では落とさない)。</summary>
        public bool Ok;
        /// <summary>⛔ のとき、どの取り合いがなぜ納まらないか。⭕ で狙い未達があればその名。</summary>
        public string Reason = "";
        /// <summary>回した巡の数(寄せ直しが要らなければ 0)。</summary>
        public int Rounds;
        public string[] Names; public bool[] Hard;
        /// <summary>取り合いごとの残り: 回す前 / 納めた後(NaN = 測れない)。</summary>
        public float[] Before, After;
        /// <summary>残りの絶対値の最悪[m]とその取り合い(⭕ でも必ず刷る・規則19)。</summary>
        public float Worst; public string WorstName = "";
        /// <summary>全部の取り合いを測った回数(=往復の代わりに関数の中で回した分)。</summary>
        public int Measures;

        /// <summary>log へ一行。例: 「⭕ 納まった 2巡 — 番所_0→門 +0.000(前 +0.062)・番所_0 接地 +0.000(前 −0.031)|最悪 …」</summary>
        public string Summary()
        {
            var sb = new StringBuilder();
            sb.Append(Ok ? (Reason.Length > 0 ? "⚠ 納まった(狙い未達)" : "⭕ 納まった") : "⛔ 納まらない");
            sb.Append(' ').Append(Rounds).Append("巡 — ");
            for (int i = 0; i < Names.Length; i++)
            {
                if (i > 0) sb.Append("・");
                sb.Append(Names[i]).Append(' ').Append(F(After[i])).Append("(前 ").Append(F(Before[i])).Append(')');
                if (!Hard[i]) sb.Append("[狙い]");
            }
            sb.Append("|最悪 ").Append(WorstName).Append(' ').Append(float.IsInfinity(Worst) ? "測れない" : Worst.ToString("F3") + "m");
            if (Reason.Length > 0) sb.Append("|").Append(Reason);
            return sb.ToString();
        }
        static string F(float v) { return float.IsNaN(v) ? "測れない" : v.ToString("+0.000;-0.000"); }
    }

    /// <summary>**寄せて測るを収まるまで回す。**<paramref name="toris"/> を渡した順に寄せ(帯の中の物は動かさない)、
    /// 巡ごとに全部を測り直す。全部が帯に入れば止める。引き合って最悪が <paramref name="stall"/> 以上縮まない巡が
    /// 続いたら、**それまでで一番よかった姿**へ戻して止める。返り値 = 合否・理由・取り合いごとの前後の残り・最悪値。
    ///
    /// <para>⭐ 順は「固定側 → 可動側」、**最後に高さ**(埋没・浮きは許容0なので、最後の一手を据えにする)。
    /// ⛔ 収まらなかった ⛔ を呼び手が黙って飲まない ── 退けるか(<see cref="PlaceBest"/> の硬い制約へ渡す)、
    /// 理由を刷って止まる。⛔ 帯を広げて ⭕ にしない(許容は検査と同じ数)。</para>
    ///
    /// <para>⚠ 一手ごとの寄せは各工場の関数(Abut・SeatOnGround ほか)が**実測の量だけ**動かすので、
    /// 多くは 1〜2 巡で閉じる。巡の上限は、斜面で寄せと据えが引き合うときの保険。</para></summary>
    public static Osamari Converge(IList<Tori> toris, int maxRounds = 6, float stall = 0.001f)
    {
        int n = toris.Count;
        var res = new Osamari { Names = new string[n], Hard = new bool[n], Before = new float[n], After = new float[n] };
        for (int i = 0; i < n; i++) { res.Names[i] = toris[i].Name; res.Hard[i] = toris[i].Hard; }

        var movers = new List<Transform>();
        foreach (var t in toris) if (t.Mover != null && !movers.Contains(t.Mover.transform)) movers.Add(t.Mover.transform);
        Func<Pose[]> snap = () =>
        {
            var p = new Pose[movers.Count];
            for (int i = 0; i < p.Length; i++) p[i] = new Pose(movers[i].position, movers[i].rotation);
            return p;
        };
        Action<Pose[]> restore = p => { for (int i = 0; i < p.Length; i++) movers[i].SetPositionAndRotation(p[i].position, p[i].rotation); };

        var r = new float[n];
        Func<float> measureAll = () =>
        {
            res.Measures++;
            float worst = 0f;                                   // 硬い制約の帯の外の最悪(+∞ = 測れない)
            for (int i = 0; i < n; i++)
            {
                r[i] = toris[i].Measure();
                if (toris[i].Hard) worst = Mathf.Max(worst, toris[i].Excess(r[i]));
            }
            return worst;
        };
        Func<float> softShort = () =>
        {
            float s = 0f;
            for (int i = 0; i < n; i++) if (!toris[i].Hard) { float e = toris[i].Excess(r[i]); s += float.IsInfinity(e) ? 1e6f : e; }
            return s;
        };
        Func<bool> allIn = () => { for (int i = 0; i < n; i++) if (toris[i].Excess(r[i]) > 0f) return false; return true; };

        float score = measureAll();
        Array.Copy(r, res.Before, n);
        float bestScore = score, bestSoft = softShort(); var best = snap(); int bestRound = 0;
        string noFace = null;
        int flat = 0;

        for (int round = 1; round <= maxRounds && !allIn(); round++)
        {
            res.Rounds = round;
            noFace = null;
            for (int i = 0; i < n; i++)
            {
                if (toris[i].Excess(toris[i].Measure()) <= 0f) continue;   // 帯の中は動かさない(動かすほど他が開く)
                if (float.IsNaN(toris[i].Apply()) && noFace == null) noFace = toris[i].Name;
            }
            float prev = score;
            score = measureAll();
            float soft = softShort();
            if (score < bestScore - 1e-6f || (Mathf.Abs(score - bestScore) <= 1e-6f && soft < bestSoft - 1e-6f))
            { bestScore = score; bestSoft = soft; best = snap(); bestRound = round; }
            if (noFace != null) break;                           // 向き合わない取り合いは巡を重ねても同じ
            flat = (prev - score < stall) ? flat + 1 : 0;
            if (flat >= 2) break;                                // 引き合って縮まない
        }

        if (score > bestScore + 1e-6f || (Mathf.Abs(score - bestScore) <= 1e-6f && softShort() > bestSoft + 1e-6f))
        { restore(best); measureAll(); }
        Array.Copy(r, res.After, n);

        // 合否と理由
        var hardOut = new List<string>(); var softOut = new List<string>();
        res.Worst = 0f;
        for (int i = 0; i < n; i++)
        {
            float a = res.After[i];
            float mag = float.IsNaN(a) ? float.PositiveInfinity : Mathf.Abs(a);
            if (mag > res.Worst || res.WorstName.Length == 0) { res.Worst = mag; res.WorstName = toris[i].Name; }
            if (toris[i].Excess(a) <= 0f) continue;
            string why = float.IsNaN(a) ? toris[i].Name + " が測れない"
                       : string.Format("{0} {1:+0.000;-0.000}m(帯 {2}〜{3})", toris[i].Name, a,
                                       float.IsNegativeInfinity(toris[i].Lo) ? "−∞" : toris[i].Lo.ToString("+0.000;-0.000"),
                                       toris[i].Hi.ToString("+0.000;-0.000"));
            (toris[i].Hard ? hardOut : softOut).Add(why);
        }
        res.Ok = hardOut.Count == 0;
        var reason = new StringBuilder();
        if (!res.Ok)
        {
            reason.Append(string.Join("・", hardOut.ToArray()));
            if (noFace != null) reason.Append("|").Append(noFace).Append(" が向き合わない(寄せる向きに相手が無い)");
            else if (res.Rounds >= maxRounds) reason.Append("|巡の上限 ").Append(maxRounds).Append(" で閉じない");
            else reason.Append("|取り合いどうしが引き合って縮まない(").Append(bestRound).Append("巡目の姿へ戻した)");
        }
        if (softOut.Count > 0) { if (reason.Length > 0) reason.Append("|"); reason.Append("狙い未達 ").Append(string.Join("・", softOut.ToArray())); }
        res.Reason = reason.ToString();
        return res;
    }

    /// <summary>一つの駒を「相手へ突き付け → 地面に据える」で納める近道(番所→門・袖塀→番所 の型)。</summary>
    public static Osamari AbutAndSeat(GameObject mover, GameObject other, Vector3 dir, float gap = 0f, float sink = 0f,
                                      int maxSamples = 4000, int maxRounds = 6)
    {
        return Converge(new[] { Tori.Abut(mover, other, dir, gap, 0.005f, true, 0.25f, maxSamples),
                                Tori.Ground(mover, sink, 0.01f, true, maxSamples) }, maxRounds);
    }
}
