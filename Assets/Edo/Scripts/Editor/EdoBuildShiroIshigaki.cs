// EdoBuild — 城の石垣の直線 run を区画の辺に沿って据える(外周の基壇・2026-10-04・EDO-0533 土井 boundaryPlinth)。
//  スキル unity-modular-stonewall の作法: 天端は区間ごとに一直線(丸い数字のまま)・段は区間の継ぎ目でだけ・ピッチ 1.80 / 重ね 0.20
//  (駒の割りと据えは PlaceCrestWall ── 見え面を低い側へ・天端の前の縁を線へ・走りの端と天端は実メッシュ)。
//  ⭐ この関数が足すのは「区画の辺に沿う」ことだけ: ① 区間を辺の s で受け、② 駒の実メッシュ(根入れの足まで)が区画の線を越えない
//  最小の控えを**据えて測って**解き(InsetRunToPoly)、③ 控えた線どうしの交点で隣の辺の区間と出隅・入隅を閉じる。
//  ⛔ 区画の線を天端の前の縁と決め打ちしない ── 城の石垣は法(1:0.25)で、丈 4.0 の駒の足は天端の縁より 1m 外へ出る。
//  ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図の区間(辺・s・天端・口)を渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>城の石垣の直線 run の一区間(区画の辺 <c>edge</c> の走り s0〜s1・天端 <c>crest</c>・口 <c>gaps</c> は辺の s の [s0, s1])。</summary>
    public class CastleSec
    {
        public string name; public int edge; public float s0, s1, crest;
        public List<Vector2> gaps = new List<Vector2>();
        /// <summary>境の外の地面の上限 = 天端 − この値(NaN = 今の地面のまま)。境の外が隣の邸の地で、隣が境に沿って犬走りと溝を切って下げる取り決めの区間
        /// (土井の北の境 ── 普請方の設計 2026-10-07)。外の今の地面が天端より高くても、下げた後の地面で見付を組み、埋まった駒を退けない。</summary>
        public float outsideCap = float.NaN;
        /// <summary>駒の倍率(既定 1 ── 土井)。岡部の外周の基壇は run ごとの倍率 s(壁高 4.0s)。</summary>
        public float scale = 1f;
        /// <summary>基準線(根石の外面を載せる線)の、区画の線から内への離れ[m](既定 0 = 区画の線)。前に溝を持つ区間は溝の内の縁
        /// (岡部 const.kidan.datumAt「線から溝の全幅 +0.01」)。駒の全頂点がこの線を越えない最小の控えを測る【硬】。</summary>
        public float datumIn = 0f;
        /// <summary>控え(天端の前の縁の線)を一つにする組の名(既定 null = 辺ごと)。岡部は run ごと ── 法肩は辺で一直線が狙い【柔】だが、
        /// 倍率と基準線が run で違い、辺の最大で揃えると根石が基準線の内へ外れる(許容 −0.05)⇒ 長屋の妻の継ぎ目で外す。</summary>
        public string insetKey;
        /// <summary>天端の勾配(辺の走り s 1m あたり・既定 0 = 水平)── <c>crest</c> は s0 の天端・s の天端 = <see cref="CrestAt"/>。≠ 0 の区間は
        /// 坂なりの駒(<see cref="PlaceCastleRun"/> の slopePathOf)で据える(岡部 const.heiLine.kidanCrest「台の石垣の天端は塀の座の線そのもの」・2026-10-13 第122巡)。</summary>
        public float grade;
        /// <summary>走り s の天端(crest + grade·(s − s0))。</summary>
        public float CrestAt(float s) { return crest + grade * (s - s0); }
        public bool Sloped { get { return Mathf.Abs(grade) > 5e-5f; } }
    }

    /// <summary><see cref="PlaceCastleRun"/> の答え。</summary>
    public class CastleRun
    {
        public List<GameObject> pieces = new List<GameObject>();
        /// <summary>辺 → 天端の前の縁の、区画の線から内への距離[m](実測の控え)。</summary>
        public Dictionary<int, float> inset = new Dictionary<int, float>();
        /// <summary>控えの組(<see cref="CastleSec.insetKey"/>・無ければ "e辺")→ 控え[m]。</summary>
        public Dictionary<string, float> insetOf = new Dictionary<string, float>();
        /// <summary>控えの組 → 根石の外面 − 基準線[m](据えた後の実測・+ = 外へ越える)。</summary>
        public Dictionary<string, float> datumResid = new Dictionary<string, float>();
        /// <summary>区間の名 → 据えた駒(区間の割りの名ではなく呼び手の区間の名)。</summary>
        public Dictionary<string, List<GameObject>> bySec = new Dictionary<string, List<GameObject>>();
        public List<RunEnd> ends = new List<RunEnd>();
        public Dictionary<string, List<GameObject>> segs = new Dictionary<string, List<GameObject>>();
        public float worstFloat = float.NegativeInfinity, worstOutside;
        public int buried;
        /// <summary>駒ひとつだけ内へ寄せた量の最大[m](法の足が線を越える丈の高い駒・天端の前の縁の段【柔】)。</summary>
        public float worstStepIn;
    }

    /// <summary>浅い折れ(&lt; 30°)の頂点で、両脇の天端の差をこれ以下なら**段の継ぎ目と読まない**[m](第126巡 2026-10-13 岡部 P35)── 坂なりの区間は芯線の折れ点が
    /// 区画の頂点から離れ(P35 は 1.45m)、頂点の端の天端が 0.04 食い違う。1e-3 で段と読むと、高い方を頂点の先へ・低い方を 1.4m 奥へ延ばし、③a が区画の外へ出た
    /// 両方の端の駒を引き戻して、根石の端が頂点の 0.27m 手前で止まり、出隅に幅 0.5m の口が開いた(見え面から土の柱)。段の丈は 0.5 以上(0.9 刻み)なので 0.10 で分ける。
    /// 当たる先: PlaceCastleRun を通る外周の基壇の浅い出隅・入隅(岡部 北の辺の坂なりの頂点・土井)。</summary>
    public const float CORNER_STEP_MIN = 0.10f;
    /// <summary>区間の端が区画の頂点に在るとみなす離れ[m] ── 指図の s は 0.01 で丸めてある(辺13 の長さ 77.26 と実の 77.264)。</summary>
    public const float VTX_TOL = 0.02f;

    /// <summary>区画の辺 e の外向き(内外判定で決める ── 重心で決めると凹みのある区画で裏返る)。</summary>
    public static Vector2 PolyEdgeOut(Vector2[] poly, int e)
    {
        int n = poly.Length; Vector2 a = poly[e % n], b = poly[(e + 1) % n];
        Vector2 d = (b - a).normalized, nn = new Vector2(-d.y, d.x), mid = (a + b) * 0.5f;
        float probe = Mathf.Min(0.5f, (b - a).magnitude * 0.2f);
        return EdoGeom.PIP(poly, mid + nn * probe) ? -nn : nn;
    }

    /// <summary>**城の石垣の直線 run を区画の辺に沿って据える**(外周の基壇・腰石垣)。
    /// <para>手順(置き方の4手): ① 区間を区画の線そのものへ <see cref="PlaceCrestWall"/> で仮に据え、辺ごとに駒の実メッシュ
    /// (根入れの足を含む全頂点)が区画の外へ出ない最小の控えを <see cref="InsetRunToPoly"/> で測る ② 据え直す ── 線 = 区画の線を
    /// 控えだけ内へ、隣の辺の区間と頂点で続く端は**控えた線どうしの交点**まで(出隅は <see cref="PlaceRunCorners"/> が受ける端の組になる)
    /// ③ もう一度区画の線を検め、まだ越える駒があれば辺ごとに引いて ★ を刷る。</para>
    /// <para>硬い(許容0): 区域(壁体の全頂点が区画の内・<paramref name="tol"/>)・天端 = 区間の crest(実測の最上点)・全体が地表の下の駒は置かない。
    /// 柔らかい: 見付(露出)の狙いは呼び手が刷る(この関数は天端と足元の地表を測るだけ)。段は区間の継ぎ目でだけ(区間を渡す呼び手が決める)。
    /// 天端が同じで口の無い隣り合う区間は一本に束ねる(天端一直線)。</para>
    /// <para>⭐ <paramref name="stepLap"/> ≥ 0(段の継ぎ目の掛け・2026-10-05 EDO-0533): 同じ辺で天端が下がる継ぎ目では、**高い区間の天端の面を継ぎ目の面より
    /// <paramref name="stepLap"/> 先まで届かせる** ── 仮に据えた駒の天端の面(天端 −0.005 より上の頂点)が継ぎ目の s に届かない分を測り、その分 + stepLap だけ
    /// 高い区間の端を低い区間の側へ延ばす(延ばした駒は低い区間の天端の上に立ち、段の小口が掛けの分だけ低い側へ出る)。
    /// 天端の上に載る棟の足が継ぎ目の面まで来るとき、足の端が下の段の天端の上に浮かないため(土井 E13 の表長屋 ── 札の foot が ±L/2 に伸びた第10巡)。
    /// 負(既定)なら延ばさない(従来どおり)。</para>
    /// 当たる先: 区画の線に沿って建つ城の石垣の基壇・腰石垣の全て(土井 boundaryPlinth。岡部 PlaceIshigaki(外周の基壇)は
    /// ピボットを線に置く旧い据えのまま ── 移し替えは別票)。</summary>
    public static CastleRun PlaceCastleRun(IList<CastleSec> secs, Vector2[] poly, Func<float, float, float> groundAt, Transform parent,
                                           System.Text.StringBuilder log, float maxInset = 2.5f, float tol = 0.001f, float stepLap = -1f, float kadoMinTurn = 40f,
                                           ICollection<int> kadoSkip = null, Func<float, float, float, string> slopePathOf = null)
    {
        var res = new CastleRun();
        if (secs == null || secs.Count == 0 || poly == null) return res;
        int n = poly.Length;
        // 天端が同じ・口の無い継ぎ目の区間を束ねる(辺ごと・s の順)
        var list = new List<CastleSec>(secs);
        list.Sort((x, y) => x.edge != y.edge ? x.edge.CompareTo(y.edge) : x.s0.CompareTo(y.s0));
        var merged = new List<CastleSec>(); var members = new Dictionary<CastleSec, List<string>>();
        foreach (var s in list)
        {
            var last = merged.Count > 0 ? merged[merged.Count - 1] : null;
            if (last != null && last.edge == s.edge && Mathf.Abs(last.s1 - s.s0) < 1e-3f && Mathf.Abs(last.CrestAt(s.s0) - s.crest) < 1e-3f && Mathf.Abs(last.grade - s.grade) < 1e-5f && float.IsNaN(last.outsideCap) == float.IsNaN(s.outsideCap)
                && Mathf.Abs(last.scale - s.scale) < 1e-4f && Mathf.Abs(last.datumIn - s.datumIn) < 1e-4f && last.insetKey == s.insetKey)
            {
                last.s1 = s.s1; last.gaps.AddRange(s.gaps); members[last].Add(s.name); continue;
            }
            var c = new CastleSec { name = s.name, edge = s.edge, s0 = s.s0, s1 = s.s1, crest = s.crest, gaps = new List<Vector2>(s.gaps), outsideCap = s.outsideCap, scale = s.scale, datumIn = s.datumIn, insetKey = s.insetKey, grade = s.grade };
            merged.Add(c); members[c] = new List<string> { s.name };
        }
        // 口で区間を割る ── 口の脇に残る駒一枚(2.00)に満たない切れ端は、口の反対の端を隣の区間へ延ばす(天端が同じか高い隣だけ ──
        //   延ばした駒は隣の駒の見え面の裏・天端の下に入って隠れる)。⛔ PlaceCrestWall の「短い区間は両側へはみ出す」に任せると、
        //   駒が口の中へ 0.56m 出た(土井 E13_N09 の通用門・2026-10-04)。
        var wallOf = new Dictionary<CastleSec, string>();
        {
            var split = new List<CastleSec>();
            foreach (var c in merged)
            {
                if (c.gaps.Count == 0) { split.Add(c); wallOf[c] = c.name; continue; }
                var cuts = new List<Vector2> { new Vector2(c.s0, c.s1) };
                foreach (var g in c.gaps)
                {
                    var nx = new List<Vector2>();
                    foreach (var q in cuts) { if (g.y <= q.x || g.x >= q.y) { nx.Add(q); continue; } if (g.x > q.x) nx.Add(new Vector2(q.x, g.x)); if (g.y < q.y) nx.Add(new Vector2(g.y, q.y)); }
                    cuts = nx;
                }
                for (int i = 0; i < cuts.Count; i++)
                {
                    float a0 = cuts[i].x, a1 = cuts[i].y;
                    if (a1 - a0 < 2.0f)
                    {
                        bool gapLo = c.gaps.Exists(g => Mathf.Abs(g.y - a0) < 1e-3f), gapHi = c.gaps.Exists(g => Mathf.Abs(g.x - a1) < 1e-3f);
                        var nbHi = merged.Find(x => x.edge == c.edge && Mathf.Abs(x.s0 - c.s1) < 1e-3f);
                        var nbLo = merged.Find(x => x.edge == c.edge && Mathf.Abs(x.s1 - c.s0) < 1e-3f);
                        if (gapLo && !gapHi && Mathf.Abs(a1 - c.s1) < 1e-3f && nbHi != null && nbHi.crest >= c.crest - 1e-3f) a1 = a0 + 2.0f;
                        else if (gapHi && !gapLo && Mathf.Abs(a0 - c.s0) < 1e-3f && nbLo != null && nbLo.crest >= c.crest - 1e-3f) a0 = a1 - 2.0f;
                        if (a1 - a0 >= 2.0f - 1e-3f && (a1 - a0) > cuts[i].y - cuts[i].x + 1e-3f)
                            log?.AppendLine("  城の石垣 " + c.name + ": 口の脇の切れ端 " + (cuts[i].y - cuts[i].x).ToString("F2") + "m ⇒ 口の縁から駒一枚を据え、反対の端を隣の高い区間の裏へ延ばした");
                    }
                    var sub = new CastleSec { name = c.name, edge = c.edge, s0 = a0, s1 = a1, crest = c.CrestAt(a0), gaps = new List<Vector2>(), outsideCap = c.outsideCap, scale = c.scale, datumIn = c.datumIn, insetKey = c.insetKey, grade = c.grade };
                    split.Add(sub); members[sub] = members[c]; wallOf[sub] = c.name + "_k" + i;
                }
            }
            merged = split;
        }
        Func<int, Vector2> A = e => poly[e % n];
        Func<int, Vector2> Dir = e => (poly[(e + 1) % n] - poly[e % n]).normalized;
        Func<int, float> Len = e => (poly[(e + 1) % n] - poly[e % n]).magnitude;
        float area = 0f; for (int i = 0; i < n; i++) area += poly[i].x * poly[(i + 1) % n].y - poly[(i + 1) % n].x * poly[i].y;
        // 頂点 v(辺 v−1 → 辺 v)の折れ[°]。+ = 出隅(区画の巡りと同じ向きへ折れる)
        Func<int, float> Turn = v =>
        {
            Vector2 d1 = Dir((v - 1 + n) % n), d2 = Dir(v % n);
            float a = Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg;
            return area >= 0f ? a : -a;
        };
        Func<CastleSec, string> KeyOf = x => x.insetKey ?? ("e" + x.edge);
        // 駒の足(天端の縁から外への出)と控え(内への奥行)── 仮に据えた駒の実メッシュで測る(辺ごと)
        var foot = new Dictionary<int, float>(); var back = new Dictionary<int, float>();
        // 相手の無い出隅の端の切り詰め[m]: 端の小口(走りに直角)の四隅が隣の辺の内に入る最小。
        //   L − s ≥ −t·cot φ を t ∈ {控え − 足, 控え + 奥行} で満たす(φ = 頂点の折れ・出隅だけ)
        Func<int, int, float, float> freeTrim = (e, v, de) =>
        {
            float phi = Turn(v); if (phi <= 1f) return 0f;
            float f = foot.ContainsKey(e) ? foot[e] : 1.0f, bk = back.ContainsKey(e) ? back[e] : 2.4f;
            float cot = 1f / Mathf.Tan(phi * Mathf.Deg2Rad), trim = 0f;
            foreach (float t in new[] { de - f, de + bk }) trim = Mathf.Max(trim, -t * cot);
            return trim + 0.01f;
        };

        // 段の継ぎ目の掛け(stepLap ≥ 0)── 区間 → 延ばす長さ[m](低い区間の側の端だけ)
        var lapLo = new Dictionary<CastleSec, float>(); var lapHi = new Dictionary<CastleSec, float>();
        Func<CastleSec, bool, CastleSec> lowerNb = (s, hi) => merged.Find(x => x != s && x.edge == s.edge && (hi ? Mathf.Abs(x.s0 - s.s1) < 1e-3f : Mathf.Abs(x.s1 - s.s0) < 1e-3f) && x.crest < s.crest - 1e-3f);
        // 天端の面の端(走りの s)── 駒の実メッシュの天端 −0.005 より上の頂点の、走りへの射影の最小・最大
        Func<List<GameObject>, CastleSec, Vector2> crestSpan = (gos, s) =>
        {
            float lo = float.MaxValue, hi = float.MinValue; Vector2 dd = (poly[(s.edge + 1) % n] - poly[s.edge % n]).normalized; Vector2 a0 = poly[s.edge % n];
            foreach (var go in gos) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= s.crest - 0.005f) { float t = Vector2.Dot(new Vector2(v.x, v.z) - a0, dd); lo = Mathf.Min(lo, t); hi = Mathf.Max(hi, t); } }
            return new Vector2(lo, hi);
        };

        // 一巡目(区画の線そのもの)と二巡目(控えた線)── 同じ組み立てを inset を変えて呼ぶ
        Func<Dictionary<string, float>, bool, List<GameObject>> build = (ins, final) =>
        {
            var made = new List<GameObject>();
            if (final) { res.ends.Clear(); res.segs.Clear(); res.bySec.Clear(); res.worstFloat = float.NegativeInfinity; res.buried = 0; }
            foreach (var s in merged)
            {
                int e = s.edge; Vector2 d = Dir(e), o = PolyEdgeOut(poly, e);
                float de = ins.ContainsKey(KeyOf(s)) ? ins[KeyOf(s)] : 0f;
                Vector2 a = A(e) + d * s.s0 - o * de, b = A(e) + d * s.s1 - o * de;
                // 頂点で隣の辺の区間へ続く端は、控えた線どうしの交点へ(出隅・入隅を閉じる)
                Func<CastleSec, Vector2, Vector2> meet = (nb, p) =>
                {
                    int e2 = nb.edge; Vector2 d2 = Dir(e2), o2 = PolyEdgeOut(poly, e2); float de2 = ins.ContainsKey(KeyOf(nb)) ? ins[KeyOf(nb)] : 0f;
                    Vector2 q0 = A(e2) - o2 * de2;   // 線2 上の点
                    float den = d.x * d2.y - d.y * d2.x; if (Mathf.Abs(den) < 1e-4f) return p;
                    Vector2 w = q0 - (A(e) - o * de);
                    float t = (w.x * d2.y - w.y * d2.x) / den;
                    return A(e) - o * de + d * t;
                };
                // ⭐ 頂点の端の納め(const.kidan.corner・普請方の設計 2026-10-11 EDO-0502 第108巡):
                //   ・折れ < 30° で控え c が違う辺 ⇒ 控えた線どうしの交点で閉じない(ほぼ平行で交点が数 m 先へ飛ぶ)── 頂点を通る二等分の面で突き付ける
                //   ・出隅の折れ < kadoMinTurn(既定 40°・隅の駒を置かない折れ)⇒ 端を頂点の走り(s = 辺の端)へ ── 根石の外面が頂点で交わり、
                //     二つの躯体で隅を覆う(③a が駒の実長まで走りに沿って引き、根石の端を頂点で止める)。交点で閉じると根石の端が頂点の手前
                //     c·tan(φ/2) で止まり、足元に口が開いた。
                //   ・それ以外(入隅・隅の駒を受ける出隅)は従来どおり交点。当たる先: PlaceCastleRun を通る全ての外周の基壇(土井・岡部)。
                Func<CastleSec, bool, Vector2> bisect = (nb, hi) =>
                {
                    Vector2 V = hi ? A(e) + d * Len(e) : A(e); Vector2 dn = hi ? Dir(nb.edge) : Dir(nb.edge);
                    Vector2 nbd = (d + dn); if (nbd.sqrMagnitude < 1e-8f) nbd = d; nbd.Normalize();
                    float t = Vector2.Dot(V - A(e) + o * de, nbd) / Mathf.Max(1e-4f, Vector2.Dot(d, nbd));
                    return A(e) - o * de + d * t;
                };
                Func<CastleSec, bool, Vector2, Vector2> joinPt = (nb, hi, p) =>
                {
                    float tv = Turn(hi ? (e + 1) % n : e);
                    float de2 = ins.ContainsKey(KeyOf(nb)) ? ins[KeyOf(nb)] : 0f;
                    if (Mathf.Abs(tv) < 30f && Mathf.Abs(de2 - de) > 1e-3f) return bisect(nb, hi);
                    //   ⭐ kadoSkip の頂点(隅の駒を受けられない出隅 ── 両脇の天端か倍率が違う・2026-10-11 EDO-0502 第109巡)も同じく頂点の走りへ。
                    //     交点で閉じると隅の駒が来ないまま根石の端が頂点の手前で止まる。当たる先: PlaceCastleRun の呼び手が隅の駒を据える邸(岡部 P0)。
                    if (tv > 1f && (tv < kadoMinTurn || (kadoSkip != null && kadoSkip.Contains(hi ? (e + 1) % n : e)))) return hi ? A(e) + d * Len(e) - o * de : A(e) - o * de;
                    return meet(nb, p);
                };
                // 頂点で天端の違う区間が浅い折れ(< 30°)で続く = 折れのある段の継ぎ目: 高い方は交点から stepLap(無ければ 0.03)だけ先へ、
                //   低い方は交点から奥へ 1.4m 延ばして高い方の面の裏へ食い込ませる(隅の駒は置かない ── PlaceRunKado・普請方の設計 2026-10-07 土井 辺14/15)
                float stepCornerLap = stepLap >= 0f ? stepLap : 0.03f;
                //   天端は継ぎ目の所で比べる(坂なりの区間は crest = s0 の天端 ── 2026-10-13)
                Func<CastleSec, float> cornerExt = x => { if (x == null) return 0f; bool after = x.edge == (e + 1) % n; float cx = after ? x.crest : x.CrestAt(x.s1), cs = after ? s.CrestAt(s.s1) : s.crest; if (Mathf.Abs(cx - cs) < 1e-3f) return 0f; return cx < cs ? stepCornerLap : -1.4f; };
                if (s.s1 >= Len(e) - VTX_TOL)
                {
                    var nx = merged.Find(x => x.edge == (e + 1) % n && x.s0 <= VTX_TOL);
                    if (nx != null && Mathf.Abs(Turn((e + 1) % n)) < 30f && Mathf.Abs(nx.crest - s.CrestAt(s.s1)) > CORNER_STEP_MIN) { b = joinPt(nx, true, b); float ce = cornerExt(nx); b += d * (ce > 0f ? ce : 1.4f); if (final) log?.AppendLine("  城の石垣 " + s.name + ": 頂点" + ((e + 1) % n) + " の折れのある段の継ぎ目 ── 尻を交点から " + (ce > 0f ? ce : 1.4f).ToString("F2") + "m 先へ(" + (ce > 0f ? "高い方の天端を届かせる" : "低い方を高い方の面の裏へ") + ")"); }
                    else if (nx != null) b = joinPt(nx, true, b);
                    else { float tr = freeTrim(e, (e + 1) % n, de); b -= d * tr; if (final && tr > 0.011f) log?.AppendLine("  城の石垣 " + s.name + ": 相手の無い出隅の端を " + tr.ToString("F2") + "m 詰めた(小口が隣の辺の線を越えない)"); }
                }
                if (s.s0 <= VTX_TOL)
                {
                    var pv = merged.Find(x => (x.edge + 1) % n == e && x.s1 >= Len(x.edge) - VTX_TOL);
                    if (pv != null && Mathf.Abs(Turn(e)) < 30f && Mathf.Abs(pv.CrestAt(pv.s1) - s.crest) > CORNER_STEP_MIN) { a = joinPt(pv, false, a); float ce = cornerExt(pv); a -= d * (ce > 0f ? ce : 1.4f); if (final) log?.AppendLine("  城の石垣 " + s.name + ": 頂点" + e + " の折れのある段の継ぎ目 ── 頭を交点から " + (ce > 0f ? ce : 1.4f).ToString("F2") + "m 手前へ(" + (ce > 0f ? "高い方の天端を届かせる" : "低い方を高い方の面の裏へ") + ")"); }
                    else if (pv != null) a = joinPt(pv, false, a);
                    else { float tr = freeTrim(e, e, de); a += d * tr; if (final && tr > 0.011f) log?.AppendLine("  城の石垣 " + s.name + ": 相手の無い出隅の端を " + tr.ToString("F2") + "m 詰めた(小口が隣の辺の線を越えない)"); }
                }
                { float lp; if (lapLo.TryGetValue(s, out lp)) a -= d * lp; if (lapHi.TryGetValue(s, out lp)) b += d * lp; }
                var gaps = new List<Vector2>();
                foreach (var g in s.gaps)
                {
                    Vector2 g0 = A(e) + d * g.x - o * de, g1 = A(e) + d * g.y - o * de;
                    gaps.Add(new Vector2(Vector2.Dot(g0 - a, d), Vector2.Dot(g1 - a, d)));
                }
                float ssc = s.scale > 0f ? s.scale : 1f;
                //   坂なりの区間(grade ≠ 0)は天端を据えた端の s で引く(交点・突き付けで端が動く ⇒ 端の天端は線の上の値)── 駒は slopePathOf の坂なりの駒
                bool slp = s.Sloped && slopePathOf != null;
                float tA = slp ? s.CrestAt(Vector2.Dot(a - A(e), d)) : s.crest, tB = slp ? s.CrestAt(Vector2.Dot(b - A(e), d)) : s.crest;
                if (s.Sloped && slopePathOf == null && final) log?.AppendLine("  ★ 城の石垣 " + s.name + ": 坂なりの区間(勾配 " + (s.grade * 100f).ToString("F2") + "%)に坂の駒の引き手が無い ── 天端 s0 の水平で据えた");
                var cw = new CrestWall { name = wallOf[s], nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { tA, tB }, gaps = gaps,
                                         pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f * ssc, pitchMax = 1.8f * ssc,
                                         lowHint = (p, q) => o, lowForce = true, scale = ssc, pathOfSlope = slp ? slopePathOf : null };
                float wf; int bs;
                var segOut = new Dictionary<string, List<GameObject>>();
                // 境の外が隣の造成で下がる区間: 線の外の点の地面を 天端 − outsideCap で頭打ちにして組む。
                //   内の点も天端で頭打ち ── 内は長屋の床の下で、背の基壇の切り(S3 丙)が後から天端まで下げる。今の高い地面で測ると
                //   駒が全部埋まったと見なされ退けられ、切った後に基壇の抜けが残った(土井 辺15 の 3 か所・第37・38巡)
                Func<float, float, float> gS = groundAt;
                if (!float.IsNaN(s.outsideCap))
                {
                    //   外と内の境は石垣の面の線(区画の線から de 控えた線)── 区画の線で割ると、控えた面の前の測り点(面 + 0.3)が内に入って
                    //   天端で頭打ちになり、駒が埋まったと退けられた(第39巡 辺15 の抜けが残った)
                    Vector2 a0e = A(e) - o * de; float capY = s.crest - s.outsideCap, capIn = s.crest;
                    gS = (x, z) => { float g = groundAt(x, z); if (float.IsNaN(g)) return g; return Vector2.Dot(new Vector2(x, z) - a0e, o) > 1e-3f ? Mathf.Min(g, capY) : Mathf.Min(g, capIn); };
                }
                var got = PlaceCrestWall(cw, gS, parent, final ? res.ends : null, segOut, final ? log : new System.Text.StringBuilder(), out wf, out bs);
                made.AddRange(got);
                if (final)
                {
                    foreach (var kv in segOut) res.segs[kv.Key] = kv.Value;
                    foreach (var nm in members[s]) if (!res.bySec.ContainsKey(nm)) res.bySec[nm] = new List<GameObject>();
                    // 束ねた区間の駒を元の区間の名へ振り分ける(駒の芯の s で)
                    foreach (var go in got)
                    {
                        var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - A(e), d);
                        string pick = members[s][0];
                        foreach (var x in secs) if (x.edge == e && members[s].Contains(x.name) && sc >= x.s0 - 1e-3f && sc <= x.s1 + 1e-3f) { pick = x.name; break; }
                        res.bySec[pick].Add(go);
                    }
                    if (wf > res.worstFloat) res.worstFloat = wf; res.buried += bs;
                }
            }
            return made;
        };

        // ① 仮に据えて辺ごとの控えを測る
        var probe = build(new Dictionary<string, float>(), false);
        var byKey = new Dictionary<string, List<GameObject>>(); var keyEdge = new Dictionary<string, int>(); var keyDatum = new Dictionary<string, float>();
        var keyS = new Dictionary<string, Vector2>();   // 組の走りの [最小, 最大](辺の s)
        foreach (var s in merged) { string k = KeyOf(s); keyEdge[k] = s.edge; keyDatum[k] = Mathf.Max(keyDatum.ContainsKey(k) ? keyDatum[k] : 0f, s.datumIn);
                                    keyS[k] = keyS.ContainsKey(k) ? new Vector2(Mathf.Min(keyS[k].x, s.s0), Mathf.Max(keyS[k].y, s.s1)) : new Vector2(s.s0, s.s1); }
        foreach (var go in probe)
        {
            string key = null; foreach (var s in merged) if (go.name.StartsWith(wallOf[s] + "_", StringComparison.Ordinal)) key = KeyOf(s);
            if (key == null) continue; List<GameObject> l; if (!byKey.TryGetValue(key, out l)) byKey[key] = l = new List<GameObject>(); l.Add(go);
        }
        foreach (var kv in byKey)
        {
            int ke = keyEdge[kv.Key]; Vector2 o = PolyEdgeOut(poly, ke); float f = 0f, bk = 0f;
            foreach (var go in kv.Value) foreach (var v in Body(go.transform, 999999))
            { float t = Vector2.Dot(new Vector2(v.x, v.z) - A(ke), o); f = Mathf.Max(f, t); bk = Mathf.Max(bk, -t); }
            foot[ke] = Mathf.Max(foot.ContainsKey(ke) ? foot[ke] : 0f, f); back[ke] = Mathf.Max(back.ContainsKey(ke) ? back[ke] : 0f, bk);
            // 控えは辺の中ほどの駒で測る ── 頂点の端の駒は隣の辺に掛かり、走りに直角へ引いても収まらない(出隅は②で詰める)
            //   組が辺の一部(run ごと)なら組の走りの中ほど(端から 3m・短い組は全部)
            Vector2 ks = keyS[kv.Key]; float m0 = Mathf.Max(3.0f, ks.x + 3.0f), m1 = Mathf.Min(Len(ke) - 3.0f, ks.y - 3.0f);
            var mid = kv.Value.FindAll(go =>
            {
                var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - A(ke), Dir(ke));
                return sc > m0 && sc < m1;
            });
            // ⭐ 中ほどの駒が無い短い組は、区画の多角形でなく**辺の線への出**で控えを取る(const.kidan.corner.cFrom【硬】「端の駒の都合で組ごと控えない」)。
            //   ⛔ 端の駒ごと多角形へ押すと、隣の辺を跨ぐ端の駒の都合で組の c が 0.5→1.22(岡部 S_Hei_04)・0.25→0.685(S_Hei_01c)に膨れ、
            //   根石の外面が基準線から 0.16〜0.72 内へ外れた(第107巡)。端の駒は ③a が走りに沿って引く。
            bool noMid = mid.Count == 0; if (noMid) mid = kv.Value;
            float before = 0f; float dpush = noMid ? float.NaN : InsetRunToPoly(mid, poly, -o, maxInset, out before, 0.005f, tol);
            float ins0 = float.IsNaN(dpush) ? maxInset : dpush;
            if (float.IsNaN(dpush))
            {   // 区画の多角形では収まらない(短い組で、頂点の端の駒しか無い)⇒ 辺の線への出だけで控えを取り、端は ③a が走りに沿って引く
                float mx = float.MinValue;
                foreach (var go in mid) foreach (var v in Body(go.transform, 999999)) { var q = new Vector2(v.x, v.z) - A(ke); float sv = Vector2.Dot(q, Dir(ke)); if (sv < 0.3f || sv > Len(ke) - 0.3f) continue; mx = Mathf.Max(mx, Vector2.Dot(q, o)); }
                if (mx != float.MinValue) { ins0 = Mathf.Max(0f, Mathf.Ceil((mx - tol) / 0.005f) * 0.005f); dpush = 0f; foreach (var go in mid) go.transform.position -= new Vector3(o.x, 0f, o.y) * ins0; }
                log?.AppendLine((noMid ? "  城の石垣 " + kv.Key + ": 中ほどの駒が無い短い組" : "  ⚠ 城の石垣 " + kv.Key + ": 区画の多角形では " + maxInset.ToString("F1") + "m 控えても収まらない") + " ⇒ 辺の線への出で控え " + ins0.ToString("F3") + "(端は走りに沿って引く)");
            }
            // ⭐ 基準線が区画の線の内(溝の内の縁)なら、根石の外面(全頂点)をその線まで ── 押した後の駒で外への最大を測り、越えた分だけ控えを足す【硬】
            float dIn = keyDatum[kv.Key], extra = 0f;
            if (dIn > 1e-4f && !float.IsNaN(dpush))
            {
                float mx = float.MinValue; foreach (var go in mid) foreach (var v in Body(go.transform, 999999)) mx = Mathf.Max(mx, Vector2.Dot(new Vector2(v.x, v.z) - A(ke), o));
                if (mx != float.MinValue && mx + dIn > tol) extra = Mathf.Ceil((mx + dIn - tol) / 0.005f) * 0.005f;
            }
            res.insetOf[kv.Key] = ins0 + extra;
            res.inset[ke] = Mathf.Max(res.inset.ContainsKey(ke) ? res.inset[ke] : 0f, ins0 + extra);
            log?.AppendLine("  城の石垣 " + (kv.Key.StartsWith("e") ? "辺" + ke : kv.Key + "(辺" + ke + ")") + ": 区画の線に置くと足が " + before.ToString("F3") + "m 外(足の出 " + f.ToString("F2") + "・控えの奥行 " + bk.ToString("F2") + ")"
                          + (dIn > 1e-4f ? "・基準線 = 線の内 " + dIn.ToString("F2") : "") + " ⇒ 天端の前の縁を " + res.insetOf[kv.Key].ToString("F3") + "m 内へ控える(実測)");
        }
        if (stepLap >= 0f)
            foreach (var s in merged)
            {
                bool hiStep = lowerNb(s, true) != null, loStep = lowerNb(s, false) != null;
                // 隣の無い端(頂点でも口の縁でもなく、同じ辺で触れる区間が無い)も天端の面を端より 0.05 先まで届かせる ── 載る棟の隅の底が端の線に乗ると
                //   測りが隣の低い物を拾う(土井 E14_N1 の外の東の隅 (-462.39, 1174.40) が練塀 E14_Hei_Kado の側で +0.82・第41巡 ── PlaceCastleBack の FREE_LAP と同じ)
                Func<bool, bool> freeEnd = hi =>
                {
                    float se = hi ? s.s1 : s.s0;
                    if (hi ? se >= Len(s.edge) - VTX_TOL : se <= VTX_TOL) return false;
                    if (merged.Exists(x => x != s && x.edge == s.edge && (hi ? Mathf.Abs(x.s0 - se) < 0.05f : Mathf.Abs(x.s1 - se) < 0.05f))) return false;
                    foreach (var sc in secs) if (sc.edge == s.edge) foreach (var g in sc.gaps) if (Mathf.Abs(hi ? g.x - se : g.y - se) < 0.05f) return false;
                    return true;
                };
                bool hiFree = !hiStep && freeEnd(true), loFree = !loStep && freeEnd(false);
                if (!hiStep && !loStep && !hiFree && !loFree) continue;
                var mine = probe.FindAll(go => go != null && go.name.StartsWith(wallOf[s] + "_", StringComparison.Ordinal));
                var sp = crestSpan(mine, s); if (sp.x > sp.y) continue;
                const float FREE_LAP = 0.05f;
                if (hiStep) lapHi[s] = Mathf.Max(0f, s.s1 - sp.y) + stepLap; else if (hiFree) { lapHi[s] = Mathf.Max(0f, s.s1 - sp.y) + FREE_LAP; log?.AppendLine("  城の石垣 " + s.name + ": 隣の無い端(s=" + s.s1.ToString("F2") + ")へ天端の面を " + lapHi[s].ToString("F3") + "m 延ばした"); }
                if (loStep) lapLo[s] = Mathf.Max(0f, sp.x - s.s0) + stepLap; else if (loFree) { lapLo[s] = Mathf.Max(0f, sp.x - s.s0) + FREE_LAP; log?.AppendLine("  城の石垣 " + s.name + ": 隣の無い端(s=" + s.s0.ToString("F2") + ")へ天端の面を " + lapLo[s].ToString("F3") + "m 延ばした"); }
            }
        foreach (var go in probe) if (go != null) UnityEngine.Object.DestroyImmediate(go);
        // ② 控えた線で据え直す
        res.pieces = build(res.insetOf, true);
        // 段の継ぎ目の掛けの検め(硬い ── 高い区間の天端の面が継ぎ目の面を越える)
        if (stepLap >= 0f)
            foreach (var s in merged)
            {
                if (!lapLo.ContainsKey(s) && !lapHi.ContainsKey(s)) continue;
                var mine = new List<GameObject>(); foreach (var nm in members[s]) if (res.bySec.ContainsKey(nm)) mine.AddRange(res.bySec[nm]);
                var sp = crestSpan(mine, s);
                if (lapHi.ContainsKey(s) && lowerNb(s, true) != null) log?.AppendLine("  " + (sp.y >= s.s1 - 1e-3f ? "⭕" : "★") + " 城の石垣 " + s.name + ": 段の継ぎ目(s=" + s.s1.ToString("F2") + "・下の天端 " + lowerNb(s, true).crest.ToString("F2") + ")へ天端の面を " + lapHi[s].ToString("F3") + "m 延ばした ⇒ 天端の面の端 s=" + sp.y.ToString("F3") + "(継ぎ目を " + (sp.y - s.s1).ToString("+0.000;-0.000") + "m 越える)");
                if (lapLo.ContainsKey(s) && lowerNb(s, false) != null) log?.AppendLine("  " + (sp.x <= s.s0 + 1e-3f ? "⭕" : "★") + " 城の石垣 " + s.name + ": 段の継ぎ目(s=" + s.s0.ToString("F2") + "・下の天端 " + lowerNb(s, false).crest.ToString("F2") + ")へ天端の面を " + lapLo[s].ToString("F3") + "m 延ばした ⇒ 天端の面の端 s=" + sp.x.ToString("F3") + "(継ぎ目を " + (s.s0 - sp.x).ToString("+0.000;-0.000") + "m 越える)");
            }
        // ③a 頂点の端の駒は、走りに沿って区画の内へ引く(駒の実長は送りの 2.00 より長く、端の駒が区間の端から出る)。
        //   ⭐ 相手の居る端(控えた線どうしの交点で閉じた端)も、端の駒が区画の外なら引く(2026-10-11 EDO-0502 第107巡): 入隅・鋭い出隅では
        //   天端の交点まで来た端の駒の法の足が隣の辺の線を越える。⛔ ③ で組ごと内へ控えると根石の外面が基準線から 0.16〜0.72 内へ外れた(許容 −0.05)。
        //   端から内へ、外へ出ている駒を順に(3 駒まで)引く。中の駒は触らない。当たる先: 区画の頂点で止まる城の石垣の区間すべて(土井・岡部の外周の基壇)。
        foreach (var s in merged)
        {
            int e = s.edge; Vector2 d = Dir(e);
            bool atHi = s.s1 >= Len(e) - VTX_TOL, atLo = s.s0 <= VTX_TOL;
            if (!atHi && !atLo) continue;
            var mine = new List<GameObject>(); foreach (var nm in members[s]) mine.AddRange(res.bySec[nm]);
            mine.RemoveAll(g => g == null);
            // 引く上限 = 駒の実長(走りへの射影の幅)── const.kidan.corner.deku「最大で駒1つの実長まで引く」
            Func<GameObject, float> lenOf = g => { float lo = float.MaxValue, hi = float.MinValue; foreach (var v in Body(g.transform, 999999)) { float t = v.x * d.x + v.z * d.y; lo = Mathf.Min(lo, t); hi = Mathf.Max(hi, t); } return hi > lo ? hi - lo : 2.0f * (s.scale > 0f ? s.scale : 1f); };
            var ends2 = new List<bool>(); if (atHi) ends2.Add(true); if (atLo) ends2.Add(false);
            foreach (bool isHi in ends2)
            {
                var order = new List<GameObject>(mine);
                order.Sort((g1, g2) => { float a1 = Vector2.Dot(new Vector2(RB(g1).center.x, RB(g1).center.z), d), a2 = Vector2.Dot(new Vector2(RB(g2).center.x, RB(g2).center.z), d); return isHi ? a2.CompareTo(a1) : a1.CompareTo(a2); });
                for (int k = 0; k < Mathf.Min(3, order.Count); k++)
                {
                    var endP = order[k]; float pullMax = lenOf(endP);
                    float before; float pl = PullAlongInside(new List<GameObject> { endP }, poly, isHi ? -d : d, pullMax, out before, 0f, 0.005f, tol);
                    if (before <= tol) break;
                    //   ⭐ 坂なりの区間は引いた先の天端の線の高さへ(第126巡 2026-10-13 岡部 P22: 12% の下りの端の駒を 0.8 引いて高さを据え置き、天端が線より 0.098 低く、
                    //   隅の練塀の足との隙 0.059)── 引いた s の変化 × 勾配(天端は線の上の値【硬】)
                    if (s.Sloped && !float.IsNaN(pl) && pl > 1e-4f) endP.transform.position += Vector3.up * (s.grade * (isHi ? -pl : pl));
                    log?.AppendLine("  城の石垣 " + endP.name + ": 頂点の端の駒が " + before.ToString("F3") + "m 区画の外 ⇒ 走りに沿って " + (float.IsNaN(pl) ? pullMax.ToString("F1") + "m 引いても収まらない ★" : pl.ToString("F3") + "m 引いた(隣の駒と重なる)"));
                }
            }
        }
        // ③ 区画の線の検め(硬い)── まだ越える辺は引いて ★
        var byEdge2 = new Dictionary<string, List<GameObject>>();
        foreach (var s in merged) foreach (var nm in members[s]) foreach (var go in res.bySec[nm])
        { List<GameObject> l; if (!byEdge2.TryGetValue(KeyOf(s), out l)) byEdge2[KeyOf(s)] = l = new List<GameObject>(); if (!l.Contains(go)) l.Add(go); }
        foreach (var kv in byEdge2)
        {
            int ke = keyEdge[kv.Key]; string lab = kv.Key.StartsWith("e") ? "辺" + ke : kv.Key + "(辺" + ke + ")";
            // ⛔ 組ごと内へ控えない(const.kidan.corner.cFrom【硬】)── 越える駒は ③a で引けなかった端の駒だけのはず ⇒ 測るだけで、越える駒を退ける(★)。
            float before; float dpush = InsetRunToPoly(kv.Value, poly, -PolyEdgeOut(poly, ke), 0f, out before, 0.005f, tol);
            if (before > tol)
            {
                if (float.IsNaN(dpush))
                {   // 硬い(区域 許容0)⇒ まだ外へ出る駒は退ける(建てない)── 退けた後の外を測り直す
                    var gone = new List<string>(); float rest = 0f; var stepIn = new List<string>();
                    foreach (var go in kv.Value)
                    {
                        if (go == null) continue; var vs = Body(go.transform, 999999); float o = 0f;
                        foreach (var v in vs) { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(poly, q)) o = Mathf.Max(o, EdoGeom.DistToPolyEdge(poly, q)); }
                        if (o <= tol) continue;
                        // ⭐ 駒ひとつだけ内へ(その駒の根石が区画の線に着く最小)── 足元が低く丈の高い駒は法の足が線を越える(岡部 S_Hei_02 の頭の 4 駒 0.017〜0.164・第108巡)。
                        //   組ごとは控えない【硬】⇒ その駒の天端の前の縁だけが内へ段になる(法肩の一直線は【柔】⇒ ⚠ と量)。退けると隅に口が開く(許容0)。
                        float b1; float dp1 = InsetRunToPoly(new List<GameObject> { go }, poly, -PolyEdgeOut(poly, ke), 0.75f, out b1, 0.005f, tol);
                        if (!float.IsNaN(dp1)) { stepIn.Add(go.name + " " + dp1.ToString("F3")); res.worstStepIn = Mathf.Max(res.worstStepIn, dp1); continue; }
                        gone.Add(go.name + " " + o.ToString("F3")); res.pieces.Remove(go); foreach (var l in res.bySec.Values) l.Remove(go); foreach (var l in res.segs.Values) l.Remove(go);
                        UnityEngine.Object.DestroyImmediate(go);
                    }
                    kv.Value.RemoveAll(g => g == null);
                    if (stepIn.Count > 0) log?.AppendLine("  ⚠ 城の石垣 " + lab + ": 法の足が区画の線を越える駒 " + stepIn.Count + " を一つずつ内へ(天端の前の縁が段になる【柔】): " + string.Join(" / ", stepIn.ToArray()));
                    if (gone.Count > 0) log?.AppendLine("  ★ 城の石垣 " + lab + ": 据え直しても " + before.ToString("F3") + "m 区画の外(組ごとは控えない)⇒ 外へ出る駒を退けた(硬い・区域)" + gone.Count + ": " + string.Join(" / ", gone.ToArray()));
                    res.worstOutside = Mathf.Max(res.worstOutside, rest);
                }
                else
                {
                    log?.AppendLine("  ⚠ 城の石垣 " + lab + ": 据え直しで " + before.ToString("F3") + "m 外(隅の交点の端の駒)⇒ さらに " + dpush.ToString("F3") + "m 引いた");
                    res.inset[ke] += dpush; res.insetOf[kv.Key] += dpush;
                    for (int i = 0; i < res.ends.Count; i++)
                    {
                        var en = res.ends[i]; bool mine = false;
                        foreach (var go in kv.Value) if (res.segs.ContainsKey(en.key) && res.segs[en.key].Contains(go)) mine = true;
                        if (mine) { en.p -= PolyEdgeOut(poly, ke) * dpush; res.ends[i] = en; }
                    }
                }
            }
            // 根石の外面 − 基準線(辺の中ほどの駒・+ = 越える)── 硬い検めの値を呼び手へ返す
            {
                Vector2 o = PolyEdgeOut(poly, ke); float dIn = keyDatum[kv.Key], mx = float.MinValue;
                foreach (var go in kv.Value)
                {
                    if (go == null) continue; var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - A(ke), Dir(ke));
                    if (sc < 0.5f || sc > Len(ke) - 0.5f) continue;   // 頂点の端の駒は隣の辺へ回る(③a が区画で検める)
                    foreach (var v in Body(go.transform, 999999)) mx = Mathf.Max(mx, Vector2.Dot(new Vector2(v.x, v.z) - A(ke), o) + dIn);
                }
                if (mx != float.MinValue) res.datumResid[kv.Key] = mx;
            }
        }
        return res;
    }

    /// <summary>**硬い(許容0)・区域**: 駒の組 <paramref name="gos"/> を走り <paramref name="along"/> に沿って一緒に引き、実メッシュが
    /// 区画の多角形の外へ出ない最小の量に納める(区画の頂点の端で、走りに直角な小口が隣の辺を跨ぐ駒 ── 出隅の折れが 90° を超えると
    /// 線から内へ控えた駒ほど隣の辺の外へ出る)。<paramref name="bandH"/> &gt; 0 なら壁体の最低点から bandH までの全頂点(腰)で測る
    /// (一体で焼いた長屋は軒を材で分けられない ── 軒は越えてよい・施主裁定A)、0 なら全頂点(石垣・練塀・布石)。
    /// 返り値 = 引いた量[m](0 = 元から内・<paramref name="maxPull"/> で収まらなければ動かさず NaN)。<paramref name="before"/> = 引く前の外への出。
    /// ⛔ 伸縮しない(長屋・石垣の駒は長さが決まっている)── 引いた分は隣の駒と重なる(埋めて隠す・docs/oki-kata.md §4)。
    /// 当たる先: 区画の出隅の頂点で止まる直線の run の端の駒(土井 辺12/13・13/14 の表長屋・基壇・練塀。岡部 PlaceOmoteNagaya の
    /// 「隅から走りに沿って 0.02m ずつ引く」は同じ型を邸ビルダーの中で回している)。</summary>
    /// <para>⭐ <paramref name="mats"/>: 測る頂点を材の名で絞る(<see cref="BodyOfMat"/>)── 溝の駒は縁石の外へ地際の土の板(区画の線の外 0.40・記録)を張るので、
    /// 全頂点では決して収まらない。石("rocks"・"Gravel")だけで測る(EDO-0502 第129巡 岡部 D_N40_Mae の頭の駒が P40 で辺39 の線の外 0.007)。</para>
    public static float PullAlongInside(IList<GameObject> gos, Vector2[] poly, Vector2 along, float maxPull, out float before,
                                        float bandH = 0f, float step = 0.005f, float tol = 0.001f, string[] mats = null)
    {
        before = 0f;
        var pts = new List<Vector3>();
        foreach (var go in gos) if (go != null)
        {
            if (mats != null) { foreach (var mt in mats) pts.AddRange(BodyOfMat(go.transform, mt)); continue; }
            pts.AddRange(bandH > 0f ? LowBandPoints(go.transform, bandH) : Body(go.transform, 999999, true));
        }
        if (pts.Count == 0) return float.NaN;
        before = OutsideBy(pts, poly, Vector2.zero);
        if (before <= tol) return 0f;
        along = along.normalized;
        for (float d = step; d <= maxPull + 1e-4f; d += step)
        {
            if (OutsideBy(pts, poly, along * d) > tol) continue;
            foreach (var go in gos) if (go != null) go.transform.position += new Vector3(along.x, 0f, along.y) * d;
            return d;
        }
        return float.NaN;
    }

    /// <summary>据えた城の石垣の区間の**天端(実測の最上点)**と**見付**(天端 − 見え面の足元の前の地表)の [最小, 最大] を測る。
    /// 見え面の足元 = 天端の前の縁から法(駒の実メッシュの、外向きへの地表の高さでの出)の分だけ前。<paramref name="step"/> 刻みで区間を歩く。
    /// 返す: (天端の最小, 天端の最大, 見付の最小, 見付の最大)。駒が無ければ NaN。</summary>
    public static Vector4 CastleCrestExposure(IList<GameObject> pieces, Vector2 outward, Func<float, float, float> groundAt, float step = 0.5f)
    {
        var v = new Vector4(float.NaN, float.NaN, float.NaN, float.NaN);
        if (pieces == null || pieces.Count == 0) return v;
        outward = outward.normalized; Vector2 along = new Vector2(-outward.y, outward.x);
        float tMin = float.MaxValue, tMax = float.MinValue, eMin = float.MaxValue, eMax = float.MinValue;
        foreach (var go in pieces)
        {
            if (go == null) continue;
            var vs = Body(go.transform, 999999); if (vs.Count == 0) continue;
            float top = float.MinValue; foreach (var p in vs) top = Mathf.Max(top, p.y);
            tMin = Mathf.Min(tMin, top); tMax = Mathf.Max(tMax, top);
            float lo = float.MaxValue, hi = float.MinValue, edge = float.MinValue; Vector2 o0 = new Vector2(go.transform.position.x, go.transform.position.z);
            foreach (var p in vs)
            {
                var q = new Vector2(p.x, p.z) - o0; float s = Vector2.Dot(q, along); lo = Mathf.Min(lo, s); hi = Mathf.Max(hi, s);
                if (p.y >= top - 0.15f) edge = Mathf.Max(edge, Vector2.Dot(q, outward));
            }
            for (float s = lo + 0.1f; s <= hi - 0.1f + 1e-4f; s += step)
            {
                // 見え面の足元: 天端の縁から外へ x 出た所の地表で見付 e、法の出 = その高さの駒の外向きの最大
                float x = 0.3f, e = float.NaN;
                for (int it = 0; it < 3; it++)
                {
                    Vector2 g = o0 + along * s + outward * (edge + x); float gy = groundAt(g.x, g.y); if (float.IsNaN(gy)) break;
                    e = top - gy; float reach = float.MinValue;
                    foreach (var p in vs)
                    {
                        if (Mathf.Abs(p.y - gy) > 0.15f) continue; var q = new Vector2(p.x, p.z) - o0;
                        if (Mathf.Abs(Vector2.Dot(q, along) - s) > 0.6f) continue;
                        reach = Mathf.Max(reach, Vector2.Dot(q, outward));
                    }
                    if (reach == float.MinValue) break;
                    x = reach - edge + 0.05f;
                }
                if (float.IsNaN(e)) continue;
                eMin = Mathf.Min(eMin, e); eMax = Mathf.Max(eMax, e);
            }
        }
        if (tMin == float.MaxValue) return v;
        return new Vector4(tMin, tMax, eMin == float.MaxValue ? float.NaN : eMin, eMax == float.MinValue ? float.NaN : eMax);
    }

    /// <summary><see cref="PlaceCastleBack"/> の一区間 = 基壇に載る一棟(長屋・門)の背。</summary>
    public class BackSec
    {
        public string name; public GameObject body; public float crest;
        /// <summary>走りの座標: 辺の始点 origin・走り along・区画の内向き inward(世界 xz・単位)。</summary>
        public Vector2 origin, along, inward;
        /// <summary>口(along の s の [s0, s1])── 棟の通り口。背の基壇もここで切る。</summary>
        public List<Vector2> gaps = new List<Vector2>();
        /// <summary>高い側の端を次の区間の線との交点まで延ばす(区画の出隅の内 = 背の面の入隅)。</summary>
        public bool joinNext;
    }

    /// <summary><see cref="PlaceCastleBack"/> の答え。</summary>
    public class CastleBack
    {
        public List<GameObject> pieces = new List<GameObject>();
        /// <summary>区間の名 → 見え面の駒(背の面)。</summary>
        public Dictionary<string, List<GameObject>> face = new Dictionary<string, List<GameObject>>();
        /// <summary>区間の名 → 外の基壇との間を埋めた駒(長屋の下・見えない)。</summary>
        public Dictionary<string, List<GameObject>> fill = new Dictionary<string, List<GameObject>>();
        /// <summary>区間の名 → (背の面の t, 天端の前の縁の t)(origin から inward への距離・実測の札の背の面から)。</summary>
        public Dictionary<string, Vector2> line = new Dictionary<string, Vector2>();
        /// <summary>区間の名 → 外の基壇の背 と 背の基壇の背 の間の残りの隙[m](天端の高さで・0 = 一つの台)。</summary>
        public Dictionary<string, float> slot = new Dictionary<string, float>();
        public int buried;
    }

    /// <summary>**基壇を棟の背まで通し、背の面も城の石垣で立てる**(2026-10-04・EDO-0533 土井 boundaryPlinth.back)。
    /// <para>手順(置き方の4手): ① 固定側 = 据わった棟。背の面は棟の札の back(局所 −Z の壁体の背)を世界へ写して測る ── ⛔ 外接箱・ピボットで決めない。
    /// ② 天端の前の縁の線 = 背の面から内へ <paramref name="inu"/>(犬走り)。走りの端 = 棟の札の躯体の端(<see cref="SpecBodySpanAlong"/>)、
    /// joinNext の端は次の区間の線との交点(入隅)。天端が同じで線が続く棟は一本に束ねる(天端一直線・段は棟の継ぎ目でだけ)。
    /// ③ <see cref="PlaceCrestWall"/> で見え面を内へ(lowForce)据える ── 天端 = 区間の crest(実測の最上点)。口は棟の通り口で切り、
    /// 口の脇に駒一枚(2.00)に満たない切れ端が残るなら口の縁から一枚を据えて反対の端を隣の区間の裏へ延ばす(隣の天端が同じか高いときだけ)。
    /// ④ 外の基壇の駒の背(<paramref name="outer"/>・局所 +X の鉛直な背)と背の駒の背の間に天端の高さで隙が残れば、背の駒の背の面を
    /// 天端の前の縁にした列を足して埋める(長屋の下 ── 妻の小口と口の脇で地表が見えない一つの台にする)。</para>
    /// <para>硬い(許容0): 天端 = crest・全体が地表の下の駒は置かない(PlaceCrestWall)・札の無い棟は据えない(★)。
    /// 柔らかい: 見付の狙いは呼び手が刷る(<see cref="CastleCrestExposure"/>)。</para>
    /// <para>⭐ <paramref name="stepLap"/> ≥ 0(段の継ぎ目の掛け・2026-10-05 EDO-0533 ── <see cref="PlaceCastleRun"/> の stepLap と同じ作法): 同じ辺で隣の区間の天端が
    /// 低い端では、**高い区間の天端の面を継ぎ目(棟の躯体の端)より <paramref name="stepLap"/> 先まで届かせる** ── 仮に据えた見え面の駒の天端の面(天端 −0.005 より上の頂点)が
    /// 端に届かない分を測り、その分 + stepLap だけ端を低い区間の側へ延ばす(延ばした駒は低い区間の天端の上に立ち、段の小口が掛けの分だけ低い側へ出る)。
    /// 棟の足の端が下の段の天端・地表の上に浮かないため(土井 E13 の表長屋・通用門 E13_N09 ── 第10〜12巡 背の下端 − 下の石の天端 +0.3〜1.5)。
    /// 隣の判定は「同じ辺で端の s を覆うか接する(±0.05)、天端の低い区間」── 口の脇の切れ端を高い区間の裏へ延ばした区間も含む。負(既定)なら延ばさない(従来どおり)。</para>
    /// 当たる先: 外周の基壇に載る表長屋・門の背が内の地表より高い所(土井 boundaryPlinth.back。岡部の表長屋・家臣長屋の背は未適用)。
    /// ⟶ 返す: <see cref="CastleBack"/>(駒・区間ごとの見え面と埋めの駒・線・隙)</summary>
    public static CastleBack PlaceCastleBack(IList<BackSec> secs, float inu, IList<GameObject> outer, Func<float, float, float> groundAt, Transform parent,
                                             System.Text.StringBuilder log, string prefix = "IGB_", float stepLap = -1f)
    {
        var res = new CastleBack();
        if (secs == null || secs.Count == 0) return res;
        var wls = new List<BackWall>();
        foreach (var s in secs)
        {
            var sp = SpecOf(s.body);
            if (sp == null) { log?.AppendLine("  ★ 背の基壇 " + s.name + ": 棟の札が無い ── 背の面が測れず据えない"); continue; }
            var bw = s.body.transform.TransformPoint(new Vector3(0f, 0f, sp.back));
            float tBack = Vector2.Dot(new Vector2(bw.x, bw.z) - s.origin, s.inward);
            var span = SpecBodySpanAlong(s.body, s.origin, s.along);
            if (float.IsNaN(span.x)) { log?.AppendLine("  ★ 背の基壇 " + s.name + ": 札に躯体の端(jamb)が無い ── 据えない"); continue; }
            res.line[s.name] = new Vector2(tBack, tBack + inu);
            var last = wls.Count > 0 ? wls[wls.Count - 1] : null;
            if (last != null && Vector2.Dot(last.along, s.along) > 0.9999f && (last.origin - s.origin).sqrMagnitude < 1e-4f
                && Mathf.Abs(last.t - (tBack + inu)) < 0.005f && Mathf.Abs(last.crest - s.crest) < 1e-3f && Mathf.Abs(last.s1 - span.x) < 0.05f)
            { last.s1 = span.y; last.gaps.AddRange(s.gaps); last.members.Add(s); last.joinNext = s.joinNext; continue; }
            wls.Add(new BackWall { origin = s.origin, along = s.along, inward = s.inward, t = tBack + inu, crest = s.crest, s0 = span.x, s1 = span.y,
                                   gaps = new List<Vector2>(s.gaps), members = new List<BackSec> { s }, joinNext = s.joinNext });
        }
        // 入隅: 天端の前の縁の線どうしの交点へ
        for (int i = 0; i + 1 < wls.Count; i++)
        {
            var A = wls[i]; var B = wls[i + 1]; if (!A.joinNext) continue;
            Vector2 pA = A.origin + A.inward * A.t, pB = B.origin + B.inward * B.t;
            float den = A.along.x * B.along.y - A.along.y * B.along.x; if (Mathf.Abs(den) < 1e-4f) continue;
            Vector2 w = pB - pA; float tA = (w.x * B.along.y - w.y * B.along.x) / den;
            Vector2 X = pA + A.along * tA;
            float sB = Vector2.Dot(X - B.origin, B.along);
            // 交点を越えて相手の天端の奥行(駒の天端 1.4 + 犬走り)まで延ばす ── 越えた分は相手の棟の下に入って隠れ、相手の犬走りの帯を天端で塞ぐ。
            //   ⛔ 棟の端まで延ばさない(端の駒の法の足が隣の辺の線を越える)。
            float over = inu + 1.4f;
            float a1 = Mathf.Min(A.s1, tA + over), b0 = Mathf.Max(B.s0, sB - over);
            log?.AppendLine("  背の基壇 " + A.members[A.members.Count - 1].name + "|" + B.members[0].name + ": 入隅 ── 天端の前の縁の線の交点(s " + tA.ToString("F2") + " / " + sB.ToString("F2") + ")から相手の天端の奥行 "
                            + over.ToString("F2") + "m まで延ばした(高い側の端 s " + A.s1.ToString("F2") + "→" + a1.ToString("F2") + " / 低い側の端 s " + B.s0.ToString("F2") + "→" + b0.ToString("F2") + ")");
            A.s1 = a1; B.s0 = b0;
        }
        // 口で割り、切れ端は口の縁から一枚 ── 反対の端を隣(線が続き天端が同じか高い)の裏へ
        var subs = new List<BackWall>();
        for (int i = 0; i < wls.Count; i++)
        {
            var w = wls[i];
            var cuts = new List<Vector2> { new Vector2(w.s0, w.s1) };
            foreach (var g in w.gaps)
            {
                var nx = new List<Vector2>();
                foreach (var q in cuts) { if (g.y <= q.x || g.x >= q.y) { nx.Add(q); continue; } if (g.x > q.x) nx.Add(new Vector2(q.x, g.x)); if (g.y < q.y) nx.Add(new Vector2(g.y, q.y)); }
                cuts = nx;
            }
            for (int k = 0; k < cuts.Count; k++)
            {
                float a0 = cuts[k].x, a1 = cuts[k].y;
                if (a1 - a0 < 0.3f) continue;
                if (a1 - a0 < 2.0f && w.gaps.Count > 0)
                {
                    bool gapLo = w.gaps.Exists(g => Mathf.Abs(g.y - a0) < 1e-3f), gapHi = w.gaps.Exists(g => Mathf.Abs(g.x - a1) < 1e-3f);
                    BackWall nbHi = i + 1 < wls.Count && Mathf.Abs(wls[i + 1].s0 - w.s1) < 0.05f && Mathf.Abs(wls[i + 1].t - w.t) < 0.005f ? wls[i + 1] : null;
                    BackWall nbLo = i > 0 && Mathf.Abs(wls[i - 1].s1 - w.s0) < 0.05f && Mathf.Abs(wls[i - 1].t - w.t) < 0.005f ? wls[i - 1] : null;
                    float L0 = a1 - a0;
                    if (gapLo && !gapHi && Mathf.Abs(a1 - w.s1) < 1e-3f && nbHi != null && nbHi.crest >= w.crest - 1e-3f) a1 = a0 + 2.0f;
                    else if (gapHi && !gapLo && Mathf.Abs(a0 - w.s0) < 1e-3f && nbLo != null && nbLo.crest >= w.crest - 1e-3f) a0 = a1 - 2.0f;
                    if (a1 - a0 > L0 + 1e-3f) log?.AppendLine("  背の基壇 " + w.members[0].name + ": 口の脇の切れ端 " + L0.ToString("F2") + "m ⇒ 口の縁から一枚・反対の端を隣の高い区間の裏へ延ばした");
                    else log?.AppendLine("  ⚠ 背の基壇 " + w.members[0].name + ": 口の脇の切れ端 " + L0.ToString("F2") + "m ── 隣が低く裏へ延ばせない(駒一枚 2.00 が両側へはみ出す)");
                }
                subs.Add(new BackWall { origin = w.origin, along = w.along, inward = w.inward, t = w.t, crest = w.crest, s0 = a0, s1 = a1, members = w.members, gaps = new List<Vector2>(), key = "_k" + k });
            }
        }
        // 段の継ぎ目の掛け(stepLap ≥ 0)── 天端の低い隣へ向く端を、仮に据えた見え面の天端の面の届かない分 + stepLap だけ延ばす
        var lapLog = new List<KeyValuePair<BackWall, Vector2>>();   // (区間, (延ばした低い側の端の s・高い側の端の s) ── NaN = 延ばさない)
        if (stepLap >= 0f)
        {
            Func<BackWall, BackWall, bool> sameLine = (x, y) => Vector2.Dot(x.along, y.along) > 0.9999f && (x.origin - y.origin).sqrMagnitude < 1e-4f;
            // 端 s の低い側の隣: 同じ辺で s を覆うか接し、天端が低い
            Func<BackWall, bool, BackWall> lowerAt = (w, hiEnd) =>
            {
                float se = hiEnd ? w.s1 : w.s0;
                return subs.Find(x => x != w && sameLine(x, w) && x.crest < w.crest - 1e-3f
                                      && (hiEnd ? (x.s0 <= se + 0.05f && x.s1 > se + 0.05f) : (x.s1 >= se - 0.05f && x.s0 < se - 0.05f)));
            };
            Func<List<GameObject>, BackWall, Vector2> crestSpan = (gos, w) =>
            {
                float lo = float.MaxValue, hi = float.MinValue;
                foreach (var go in gos) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= w.crest - 0.005f) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); lo = Mathf.Min(lo, sv); hi = Mathf.Max(hi, sv); } }
                return new Vector2(lo, hi);
            };
            var newS = new Dictionary<BackWall, Vector2>();
            foreach (var w in subs)
            {
                var nbLo = lowerAt(w, false); var nbHi = lowerAt(w, true);
                // 隣の無い端(同じ辺で端に触れる区間が一つも無い)も、天端の面を元の端(棟の躯体の端)まで届かせる ── 掛けは足さない。
                //   土井 E14_N1 の東の端は隣が別の辺の表門(天端 22.7)で、天端の面が端に届かず棟の隅が 1.5m 浮いた(第37・38巡)
                bool freeLo = nbLo == null && !subs.Exists(x => x != w && sameLine(x, w) && x.s1 >= w.s0 - 0.05f && x.s0 < w.s0 - 0.05f);
                bool freeHi = nbHi == null && !subs.Exists(x => x != w && sameLine(x, w) && x.s0 <= w.s1 + 0.05f && x.s1 > w.s1 + 0.05f);
                if (nbLo == null && nbHi == null && !freeLo && !freeHi) continue;
                Vector2 a = w.origin + w.along * w.s0 + w.inward * w.t, b = w.origin + w.along * w.s1 + w.inward * w.t;
                var inw = w.inward;
                var pcw = new CrestWall { name = prefix + "Probe_" + w.members[0].name + w.key, nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { w.crest, w.crest }, gaps = new List<Vector2>(),
                                          pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, lowHint = (p, q) => inw, lowForce = true };
                float pwf; int pbs;
                var probe = PlaceCrestWall(pcw, groundAt, parent, null, null, new System.Text.StringBuilder(), out pwf, out pbs);
                var sp = crestSpan(probe, w);
                foreach (var go in probe) if (go != null) UnityEngine.Object.DestroyImmediate(go);
                if (sp.x > sp.y) continue;
                // 隣の無い端の届かせ先 = 棟の底(最下点 + 0.05 以内)の頂点の走りの端 ── 札の躯体の端(jamb)より土台の木口が外へ出る(土井 E14_N1 の東の隅・第39巡)
                float fLo = w.s0, fHi = w.s1;
                if (freeLo || freeHi)
                    foreach (var m in w.members)
                    {
                        var bv = Body(m.body.transform, 999999); float ymin = float.MaxValue; foreach (var v in bv) ymin = Mathf.Min(ymin, v.y);
                        foreach (var v in bv) { if (v.y > ymin + 0.05f) continue; float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); if (sv < w.s0 + 1f) fLo = Mathf.Min(fLo, sv); if (sv > w.s1 - 1f) fHi = Mathf.Max(fHi, sv); }
                    }
                //   掛け FREE_LAP: 底の頂点が天端の面のちょうど端の線に乗ると、測りが隣の低い石を拾う(土井 E14_N1 の背の東の隅 (-461.00, 1171.63)・第40巡)
                const float FREE_LAP = 0.05f;
                float s0n = nbLo != null ? w.s0 - (Mathf.Max(0f, sp.x - w.s0) + stepLap) : freeLo ? w.s0 - (Mathf.Max(0f, sp.x - fLo) + FREE_LAP) : w.s0;
                float s1n = nbHi != null ? w.s1 + (Mathf.Max(0f, w.s1 - sp.y) + stepLap) : freeHi ? w.s1 + (Mathf.Max(0f, fHi - sp.y) + FREE_LAP) : w.s1;
                if (nbLo == null && nbHi == null && Mathf.Abs(s0n - w.s0) < 1e-3f && Mathf.Abs(s1n - w.s1) < 1e-3f) continue;
                if (nbLo == null && nbHi == null) log?.AppendLine("  背の基壇 " + w.members[0].name + w.key + ": 隣の無い端へ天端の面を届かせた(s " + w.s0.ToString("F2") + "→" + s0n.ToString("F2") + " / " + w.s1.ToString("F2") + "→" + s1n.ToString("F2") + ")");
                newS[w] = new Vector2(s0n, s1n);
                lapLog.Add(new KeyValuePair<BackWall, Vector2>(w, new Vector2(nbLo != null ? w.s0 : float.NaN, nbHi != null ? w.s1 : float.NaN)));
            }
            foreach (var kv in newS) { kv.Key.s0 = kv.Value.x; kv.Key.s1 = kv.Value.y; }
        }
        foreach (var w in subs)
        {
            string nm0 = w.members[0].name;
            Func<float, string, List<GameObject>> row = (t, tag) =>
            {
                Vector2 a = w.origin + w.along * w.s0 + w.inward * t, b = w.origin + w.along * w.s1 + w.inward * t;
                var inw = w.inward;
                var cw = new CrestWall { name = prefix + tag + nm0 + w.key, nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { w.crest, w.crest }, gaps = new List<Vector2>(),
                                         pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, lowHint = (p, q) => inw, lowForce = true };
                float wf; int bs;
                var got = PlaceCrestWall(cw, groundAt, parent, null, null, log ?? new System.Text.StringBuilder(), out wf, out bs);
                res.buried += bs; res.pieces.AddRange(got);
                return got;
            };
            var faceP = row(w.t, "");
            // 区間の名へ振り分け(駒の芯の s)
            Action<List<GameObject>, Dictionary<string, List<GameObject>>> assign = (gos, dict) =>
            {
                foreach (var m in w.members) if (!dict.ContainsKey(m.name)) dict[m.name] = new List<GameObject>();
                foreach (var go in gos)
                {
                    var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - w.origin, w.along);
                    var pick = w.members[0]; float best = float.MaxValue;
                    foreach (var m in w.members)
                    {
                        var sp = SpecBodySpanAlong(m.body, w.origin, w.along);
                        float d = sc < sp.x ? sp.x - sc : (sc > sp.y ? sc - sp.y : 0f); if (d < best) { best = d; pick = m; }
                    }
                    dict[pick.name].Add(go);
                }
            };
            assign(faceP, res.face);
            // ④ 外の基壇の背との隙を埋める
            Func<List<GameObject>, float> backOf = gos => { float mn = float.MaxValue; foreach (var go in gos) foreach (var v in Body(go.transform, 999999)) mn = Mathf.Min(mn, Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.inward)); return mn; };
            float tOuter = float.MinValue;
            if (outer != null)
                foreach (var go in outer)
                {
                    if (go == null) continue;
                    var r = go.transform.right; if (Vector2.Dot(new Vector2(r.x, r.z).normalized, w.inward) < 0.99f) continue;   // 外の駒(見え面 = 局所 −X が外)
                    foreach (var v in Body(go.transform, 999999))
                    {
                        float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); if (sv < w.s0 - 0.01f || sv > w.s1 + 0.01f) continue;
                        float tv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.inward); if (tv > w.t) continue;
                        tOuter = Mathf.Max(tOuter, tv);
                    }
                }
            float tb = faceP.Count > 0 ? backOf(faceP) : w.t;
            var fillAll = new List<GameObject>();
            for (int k = 0; k < 3 && tOuter > float.MinValue && tb - tOuter > 0.01f; k++)
            {
                var f = row(tb, "F" + k + "_");
                if (f.Count == 0) break;
                fillAll.AddRange(f); tb = Mathf.Min(tb, backOf(f));
            }
            assign(fillAll, res.fill);
            float slot = tOuter > float.MinValue ? Mathf.Max(0f, tb - tOuter) : float.NaN;
            foreach (var m in w.members) res.slot[m.name] = res.slot.ContainsKey(m.name) && !float.IsNaN(res.slot[m.name]) ? Mathf.Max(res.slot[m.name], slot) : slot;
            log?.AppendLine("  背の基壇 " + nm0 + w.key + ": s " + w.s0.ToString("F2") + "〜" + w.s1.ToString("F2") + "・天端 " + w.crest.ToString("F2") + "・見え面 " + faceP.Count + " 駒・埋め " + fillAll.Count + " 駒・外の基壇の背との隙 "
                            + (float.IsNaN(slot) ? "外の駒なし" : slot.ToString("F3")) + "m");
            // 段の継ぎ目の掛けの検め(硬い ── 見え面の天端の面が元の端を stepLap 越える)
            foreach (var kv in lapLog)
            {
                if (kv.Key != w) continue;
                float lo = float.MaxValue, hi = float.MinValue;
                foreach (var go in faceP) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= w.crest - 0.005f) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); lo = Mathf.Min(lo, sv); hi = Mathf.Max(hi, sv); } }
                if (!float.IsNaN(kv.Value.x)) log?.AppendLine("  " + (lo <= kv.Value.x + 1e-3f ? "⭕" : "★") + " 背の基壇 " + nm0 + w.key + ": 低い側の段の継ぎ目(s=" + kv.Value.x.ToString("F2") + ")へ天端の面を延ばした ⇒ 天端の面の端 s=" + lo.ToString("F3") + "(継ぎ目を " + (kv.Value.x - lo).ToString("+0.000;-0.000") + "m 越える・掛け " + stepLap.ToString("F2") + ")");
                if (!float.IsNaN(kv.Value.y)) log?.AppendLine("  " + (hi >= kv.Value.y - 1e-3f ? "⭕" : "★") + " 背の基壇 " + nm0 + w.key + ": 高い側の端の隣が低い段の継ぎ目(s=" + kv.Value.y.ToString("F2") + ")へ天端の面を延ばした ⇒ 天端の面の端 s=" + hi.ToString("F3") + "(継ぎ目を " + (hi - kv.Value.y).ToString("+0.000;-0.000") + "m 越える)");
            }
        }
        return res;
    }

    class BackWall
    {
        public Vector2 origin, along, inward; public float t, crest, s0, s1; public bool joinNext; public string key = "";
        public List<Vector2> gaps = new List<Vector2>(); public List<BackSec> members = new List<BackSec>();
    }

    /// <summary>据えた棟の**背の下端 − 下の石垣の天端**[m](浮き = 正・めり込み = 負)。背の面から棟の内へ <paramref name="band"/> の帯の躯体を
    /// 走りの 0.25m 刻みの筋に割り、筋ごとの最下点と、その点を含む石垣の駒(<paramref name="stones"/> ── 背の基壇・埋め・外の基壇・隣の辺の基壇の全て)
    /// の天端(実測の最上点)の差を取る。口 <paramref name="skipS"/> の中は除く。返す: 絶対値の最悪(符号付き)。<paramref name="bare"/> = 下に石の無い筋の数。
    /// 当たる先: <see cref="PlaceCastleBack"/> の検め(土井の表長屋・門)。</summary>
    public static float BackBedGap(GameObject body, IList<GameObject> stones, Vector2 origin, Vector2 along, Vector2 inward, float tBack, IList<Vector2> skipS, out int bare, float band = 0.3f,
                                   IList<GameObject> others = null)
    {
        // 他の棟の躯体の中(札の jamb × back〜front)に入る頂点は見えない ── 出隅の内で棟どうしが重なる所(土井 辺12/13)
        Func<Vector3, bool> hidden = v =>
        {
            if (others == null) return false;
            foreach (var o in others)
            {
                if (o == null || o == body) continue; var sp = SpecOf(o); if (sp == null || sp.jambL == null || sp.jambR == null) continue;
                var l = o.transform.InverseTransformPoint(v);
                if (l.x > Mathf.Min(sp.jambL.x, sp.jambR.x) + 0.01f && l.x < Mathf.Max(sp.jambL.x, sp.jambR.x) - 0.01f && l.z > sp.back + 0.01f && l.z < sp.front - 0.01f) return true;
            }
            return false;
        };
        bare = 0;
        if (body == null || stones == null || stones.Count == 0) return float.NaN;
        var bins = new Dictionary<int, Vector3>();
        var vs = Body(body.transform, 999999);
        Func<float, bool> inGap = sv => { if (skipS != null) foreach (var g in skipS) if (sv > g.x - 0.05f && sv < g.y + 0.05f) return true; return false; };
        float lo = float.MaxValue;
        foreach (var v in vs)
        {
            var q0 = new Vector2(v.x, v.z); float t = Vector2.Dot(q0 - origin, inward);
            if (t <= tBack + 0.01f && t >= tBack - band && !inGap(Vector2.Dot(q0 - origin, along))) lo = Mathf.Min(lo, v.y);
        }
        foreach (var v in vs)
        {
            if (v.y > lo + 0.3f) continue;   // 土台の帯だけ(二階の壁・軒の頂点を筋の最下点に拾わない)
            var q = new Vector2(v.x, v.z); float t = Vector2.Dot(q - origin, inward); if (t > tBack + 0.01f || t < tBack - band) continue;
            float s = Vector2.Dot(q - origin, along); bool skip = false;
            if (skipS != null) foreach (var g in skipS) if (s > g.x - 0.05f && s < g.y + 0.05f) skip = true;
            if (skip) continue;
            int k = Mathf.FloorToInt(s / 0.25f); Vector3 cur;
            if (!bins.TryGetValue(k, out cur) || v.y < cur.y) bins[k] = v;
        }
        if (bins.Count == 0) return float.NaN;
        // 駒の箱は走りの座標(s, t)で取る ── 世界の外接箱は斜めの辺で走りの端より膨らみ、継ぎ目の頂点が高い隣の天端を拾って偽のめり込みになる
        var boxes = new List<Vector4>(); var tops = new List<float>();
        foreach (var go in stones)
        {
            if (go == null) continue; float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue, top = float.MinValue;
            foreach (var v in Body(go.transform, 999999)) { var q = new Vector2(v.x, v.z) - origin; float sv = Vector2.Dot(q, along), tv = Vector2.Dot(q, inward); s0 = Mathf.Min(s0, sv); s1 = Mathf.Max(s1, sv); t0 = Mathf.Min(t0, tv); t1 = Mathf.Max(t1, tv); top = Mathf.Max(top, v.y); }
            if (top == float.MinValue) continue; boxes.Add(new Vector4(s0, s1, t0, t1)); tops.Add(top);
        }
        float worst = float.NaN;
        foreach (var kv in bins)
        {
            var at = new Vector2(kv.Value.x, kv.Value.z) - origin; float sa = Vector2.Dot(at, along), ta = Vector2.Dot(at, inward), crest = float.MinValue;
            for (int i = 0; i < boxes.Count; i++) { var b = boxes[i]; if (sa < b.x + 0.01f || sa > b.y - 0.01f || ta < b.z - 0.01f || ta > b.w + 0.01f) continue; crest = Mathf.Max(crest, tops[i]); }
            if (crest == float.MinValue)   // 継ぎ目の上の頂点: 端で接する駒のうち低い方(自分の区間の駒)
            {
                float lowTop = float.MaxValue;
                for (int i = 0; i < boxes.Count; i++) { var b = boxes[i]; if (sa < b.x - 0.01f || sa > b.y + 0.01f || ta < b.z - 0.01f || ta > b.w + 0.01f) continue; lowTop = Mathf.Min(lowTop, tops[i]); }
                if (lowTop != float.MaxValue) crest = lowTop;
            }
            if (crest == float.MinValue) { if (!hidden(kv.Value)) bare++; continue; }
            float g = kv.Value.y - crest; if (float.IsNaN(worst) || Mathf.Abs(g) > Mathf.Abs(worst)) worst = g;
        }
        return worst;
    }

    /// <summary>**浅い出隅の台の石の口を裏の駒で塞ぐ**(第126巡 2026-10-13 岡部 const.heiLine.faceFront【硬】「出隅で台の石が抜ける所を作らない」)。
    /// 隅の駒を置かない出隅(折れ 1° 〜 <paramref name="kadoMinTurn"/>)では両脇の根石の外面が頂点で交わるだけで、法の見え面は高さとともに内へ引くので、
    /// 二つの駒の小口の間に上へ開く V の口(天端で 2·c·sin(φ/2))が残り、裏の土が見えた(岡部 P35 22° で幅 0.3)。
    /// 口の裏に、その辺の直線の駒(見付に合う丈 <see cref="CastleWallOfExpose"/>・両脇と同じ倍率)を**内への二等分の向き**に据える:
    /// ① 走りの芯を頂点へ ② 天端 = 両脇の頂点の天端の低い方(実測の最上点)③ 全頂点が両脇の辺の線の内へ入るまで二等分の向きへ引く(区域【硬】・実測)。
    /// 見え面は両脇の駒の見え面の裏に隠れ、口からだけ見える。硬い(区域・天端を越えない)。当たる先: PlaceCastleRun を通る外周の基壇の 40° 未満の出隅(岡部 北の辺・土井)。</summary>
    /// <summary>最後の <see cref="FillConvexCornerSlits"/> が「留めの版が要る」と刷った出隅(頂点・折れ・切り角・倍率・両脇の天端)── 部材方への待ち(第148巡)。</summary>
    public static readonly List<string> MiterBaseWait = new List<string>();
    public static string FillConvexCornerSlits(IList<CastleSec> secs, Vector2[] poly, Transform parent, Func<float, float, float> groundAt, float kadoMinTurn = 40f, IList<GameObject> pieces = null)
    {
        MiterBaseWait.Clear(); TomeBaseLog.Clear();
        int n = poly.Length; float area = 0f; for (int i = 0; i < n; i++) area += poly[i].x * poly[(i + 1) % n].y - poly[(i + 1) % n].x * poly[i].y;
        var sb = new System.Text.StringBuilder(); int made = 0;
        for (int v = 0; v < n; v++)
        {
            int e0 = (v - 1 + n) % n; Vector2 V = poly[v]; float L0 = (poly[v] - poly[e0]).magnitude;
            Vector2 d1 = (poly[v] - poly[e0]).normalized, d2 = (poly[(v + 1) % n] - poly[v]).normalized;
            float tv = Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg; if (area < 0f) tv = -tv;
            if (tv <= 1f || tv >= kadoMinTurn) continue;
            CastleSec sA = null, sB = null; foreach (var x in secs) { if (x.edge == e0 && x.s1 >= L0 - VTX_TOL) sA = x; if (x.edge == v && x.s0 <= VTX_TOL) sB = x; }
            if (sA == null || sB == null) continue;
            Vector2 oA = PolyEdgeOut(poly, e0), oB = PolyEdgeOut(poly, v); Vector2 nb = -(oA + oB).normalized;   // 内への二等分
            //   ⭐ 第150巡(oki-kata §2a【硬】直角でない出隅は最初から留める): 両脇の端の駒を角の二等分の面で切った版(Own.IshigakiChokuTome)へ差し替える ── 両方据われば口は閉じ、裏の駒は置かない
            if (pieces != null)
            {
                string why; int nT = SwapEndsToTome(pieces, parent, poly, v, e0, tv, sA, sB, out why);
                TomeBaseLog.Add("P" + v + " " + why);
                if (nT == 2) { sb.Append(" P" + v + "(留め)"); continue; }
            }
            float crestTop = Mathf.Min(sA.CrestAt(sA.s1), sB.CrestAt(sB.s0)); float sc = sB.scale > 0f ? sB.scale : 1f;
            float gV = groundAt(V.x + (oA.x + oB.x) * 0.15f, V.y + (oA.y + oB.y) * 0.15f); if (float.IsNaN(gV)) gV = groundAt(V.x, V.y);
            float expose = (crestTop - gV) / sc + 0.6f;   // 根入れ 0.6(名の丈で)
            string path = CastleWallOfExpose(expose);
            //   局所の +X = 内(見え面は局所 −X)・走り = 局所 Z(Castle Wall の札)── right = nb ⇒ forward = (−nb.y, nb.x)
            Vector2 fw = new Vector2(-nb.y, nb.x); float ry = Mathf.Atan2(fw.x, fw.y) * Mathf.Rad2Deg;
            var go = Place(path, new Vector3(V.x, crestTop, V.y), ry, new Vector3(sc, sc, sc), parent, "IG_Slit_P" + v);
            Physics.SyncTransforms();
            float topY = float.MinValue, zLo = float.MaxValue, zHi = float.MinValue, xOut = float.MinValue, yBot = float.MaxValue;
            for (int it = 0; it < 3; it++)
            {
                var vs = Body(go.transform, 999999); topY = float.MinValue; zLo = float.MaxValue; zHi = float.MinValue; xOut = float.MinValue; yBot = float.MaxValue;
                foreach (var w in vs) { var q = new Vector2(w.x, w.z) - V; topY = Mathf.Max(topY, w.y); yBot = Mathf.Min(yBot, w.y); float z = Vector2.Dot(q, fw); zLo = Mathf.Min(zLo, z); zHi = Mathf.Max(zHi, z); xOut = Mathf.Max(xOut, Mathf.Max(Vector2.Dot(q, oA), Vector2.Dot(q, oB))); }
                var p = go.transform.position;
                //   ① 走りの芯を頂点へ ② 天端を crestTop へ ③ 全頂点が両脇の線の 0.01 内(二等分の向きに引く: 辺の外向きとの角 φ/2 ⇒ 引く量 = 越え / cos(φ/2))
                float pull = (xOut + 0.01f) / Mathf.Max(0.2f, Vector2.Dot(-nb, oA));
                p += new Vector3(-fw.x, 0f, -fw.y) * (0.5f * (zLo + zHi)) + new Vector3(nb.x, 0f, nb.y) * Mathf.Max(0f, pull) + Vector3.up * (crestTop - topY);
                go.transform.position = p; Physics.SyncTransforms();
                if (Mathf.Abs(0.5f * (zLo + zHi)) < 1e-3f && pull <= 1e-3f && Mathf.Abs(crestTop - topY) < 1e-3f) break;
            }
            made++;
            float back = Vector2.Dot(new Vector2(go.transform.position.x, go.transform.position.z) - V, nb);
            sb.Append(" P" + v + "(折れ " + tv.ToString("F0") + "°・天端 " + crestTop.ToString("F2") + "・線の外 " + (xOut > 0f ? "+" : "") + xOut.ToString("F3") + "・底 " + yBot.ToString("F2") + " / 外の地表 " + gV.ToString("F2")
                      + (yBot > gV - 0.05f ? " ⚠ 底が外の地表に届かない" : "") + ")");
            //   ⭐ 第148巡(oki-kata §2a【硬】直角でない出隅は最初から留める・施主の写真 r147_kado_P41): 口の裏の駒は留めの代わりでない ── 両脇の台の石の端は
            //   角の二等分の面で切った版(端を斜めに切った Castle Wall・倍率 s・天端の違う側は高い方の切り口が見える)で据えるべき所。版が無いので待ちへ(建て方はこの口の駒のまま)
            MiterBaseWait.Add("P" + v + " 折れ " + tv.ToString("F1") + "°・端の切り角 " + (tv * 0.5f).ToString("F1") + "°・倍率 " + sc.ToString("0.##") + "・天端 " + sA.CrestAt(sA.s1).ToString("F2") + "/" + sB.CrestAt(sB.s0).ToString("F2"));
        }
        return "浅い出隅の口を裏の駒で塞いだ " + made + " 基:" + sb + (TomeBaseLog.Count > 0 ? "\n  留めの版: " + string.Join("\n    ", TomeBaseLog.ToArray()) : "") + (MiterBaseWait.Count > 0 ? "\n  ★ 留めの版が要る(台の石の端を角の二等分の面で切った Castle Wall ── 部材方へ・oki-kata §2a): " + string.Join(" / ", MiterBaseWait.ToArray()) : "");
    }

    /// <summary>最後の <see cref="FillConvexCornerSlits"/> の留めの版の差し替えの行(頂点ごと)。</summary>
    public static readonly List<string> TomeBaseLog = new List<string>();
    /// <summary>台の石垣の端の駒の名(資産のパス)から丈・勾配・走りを読む(`JC.CastleWall` = 丈 4・平ら・2.0 / `Ishigaki_Choku_H<丈>[_G<U|D><勾配>][_L<cm>]`)。読めなければ偽。</summary>
    static bool ParseChokuPiece(string path, out float h, out float g, out float len)
    {
        h = 4f; g = 0f; len = 2f;
        if (string.IsNullOrEmpty(path)) return false;
        if (path == EdoAssets.JC.CastleWall) return true;
        var m = System.Text.RegularExpressions.Regex.Match(System.IO.Path.GetFileNameWithoutExtension(path), @"^Ishigaki_Choku_H(\d{4})(?:_G([UD])(\d{4}))?(?:_L(\d+))?$");
        if (!m.Success) return false;
        h = int.Parse(m.Groups[1].Value) / 100f;
        if (m.Groups[2].Success) g = (m.Groups[2].Value == "D" ? -1f : 1f) * int.Parse(m.Groups[3].Value) / 10000f;
        if (m.Groups[4].Success) len = int.Parse(m.Groups[4].Value) / 100f;
        return true;
    }
    /// <summary>**浅い出隅の両脇の台の石の端の駒を留めの版へ差し替える**(第150巡・札の tomeCrestFrontCorner / crestOnMiter の据え)。
    /// ① 端の駒 = 区間の辺に沿う(局所 +Z が辺と平行)駒のうち、端(局所 Z = 0 か −len)が頂点の走りの位置に最も近い物(据わった実物から ── 名と倍率と勾配はその駒の物)
    /// ② 版 = <see cref="EdoAssets.Own.IshigakiChokuTomeNearest"/>(勾配 ±0.0005・折れ ±0.2°)③ 両脇の天端の前の縁の線(局所 X = −1.40 の線を据わった駒で世界へ)の交点 Q
    /// ④ 版を元の駒の yaw・倍率で、札の tomeCrestFrontCorner を Q へ・y = 元の駒の Q での天端 − crestOnMiter·s。
    /// 硬い: 端の駒が見つからない・版が無い側は差し替えない(呼び手が口の裏の駒で塞ぎ ★ 待ちへ)。返す: 差し替えた数(0〜2)。</summary>
    static int SwapEndsToTome(IList<GameObject> pieces, Transform parent, Vector2[] poly, int v, int e0, float turn, CastleSec sA, CastleSec sB, out string why)
    {
        int n = poly.Length; Vector2 V = poly[v];
        Vector2 dA = (poly[v] - poly[e0]).normalized, dB = (poly[(v + 1) % n] - poly[v]).normalized;
        var ends = new GameObject[2]; var pEnd = new bool[2]; var hs = new float[2]; var gs = new float[2]; var ls = new float[2]; var paths = new string[2];
        for (int side = 0; side < 2; side++)
        {
            Vector2 d = side == 0 ? dA : dB; float best = float.MaxValue;
            foreach (var go in pieces)
            {
                if (go == null || go.name.StartsWith("IG_Slit_")) continue;
                string ap = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go); float h, g, len;
                if (!ParseChokuPiece(ap, out h, out g, out len)) continue;
                var f = new Vector2(go.transform.forward.x, go.transform.forward.z).normalized;
                if (Mathf.Abs(Vector2.Dot(f, d)) < 0.995f) continue;
                for (int e = 0; e < 2; e++)
                {
                    var w = go.transform.TransformPoint(new Vector3(-2.4f, 0f, e == 0 ? 0f : -len)); var q = new Vector2(w.x, w.z) - V;
                    float along = Mathf.Abs(Vector2.Dot(q, d)), across = Mathf.Abs(d.x * q.y - d.y * q.x);
                    if (across > 1.0f || along > 1.0f) continue;   // 足元の前の角(局所 X = −2.40)が頂点の近く
                    // 端は頂点の側の端(前の辺は走りの終わり・次の辺は始まり)── 走りの向きで判ずる
                    var other = go.transform.TransformPoint(new Vector3(-2.4f, 0f, e == 0 ? -len : 0f));
                    float sEnd = Vector2.Dot(new Vector2(w.x, w.z) - V, d), sOther = Vector2.Dot(new Vector2(other.x, other.z) - V, d);
                    if (side == 0 ? sOther > sEnd : sOther < sEnd) continue;
                    if (along < best) { best = along; ends[side] = go; pEnd[side] = e == 0; hs[side] = h; gs[side] = g; ls[side] = len; paths[side] = ap; }
                }
            }
        }
        why = "";
        if (ends[0] == null || ends[1] == null) { why = "★ 端の駒が見つからない(" + (ends[0] == null ? "前の辺" : "") + (ends[1] == null ? " 次の辺" : "") + ")── 口の裏の駒で塞ぐ"; return 0; }
        // ③ 天端の前の縁の線の交点
        Func<GameObject, float, Vector2[]> crestLine = (go, len) =>
        {
            var a = go.transform.TransformPoint(new Vector3(-1.4f, 0f, 0f)); var b = go.transform.TransformPoint(new Vector3(-1.4f, 0f, -len));
            return new[] { new Vector2(a.x, a.z), new Vector2(b.x, b.z) };
        };
        var LA = crestLine(ends[0], ls[0]); var LB = crestLine(ends[1], ls[1]);
        Vector2 r = LA[1] - LA[0], u = LB[1] - LB[0]; float den = r.x * u.y - r.y * u.x;
        if (Mathf.Abs(den) < 1e-6f) { why = "★ 天端の前の縁の線が平行 ── 口の裏の駒で塞ぐ"; return 0; }
        float tt = ((LB[0].x - LA[0].x) * u.y - (LB[0].y - LA[0].y) * u.x) / den; Vector2 Q = LA[0] + r * tt;
        var tomes = new string[2]; var gOff = new float[2]; var tOff = new float[2];
        for (int side = 0; side < 2; side++) tomes[side] = EdoAssets.Own.IshigakiChokuTomeNearest(gs[side], turn, pEnd[side], hs[side], ls[side], out gOff[side], out tOff[side]);
        if (tomes[0] == null || tomes[1] == null)
        {
            why = "★ 版が無い: " + (tomes[0] == null ? System.IO.Path.GetFileName(EdoAssets.Own.IshigakiChokuTome(gs[0], turn, pEnd[0], hs[0], ls[0])) + " " : "")
                + (tomes[1] == null ? System.IO.Path.GetFileName(EdoAssets.Own.IshigakiChokuTome(gs[1], turn, pEnd[1], hs[1], ls[1])) : "") + "(端の駒 " + ends[0].name + " / " + ends[1].name + ")── 口の裏の駒で塞ぐ";
            return 0;
        }
        //   ④ 据え: 二通りを据えて測る【硬】
        //   (a) 札の据え ── tomeCrestFrontCorner を両脇の天端の前の縁の線の交点 Q へ・y = 元の駒の Q での天端 − crestOnMiter·s(継ぎ目は天端の角で閉じる)
        //   (b) 元の駒の position・yaw・倍率のまま(版は元の駒と同じ枠 ── 足元の前の角を枠の端に残す)
        //   (a) を採るのは両脇とも ① 全頂点が区画の線の内(0.01)② 同じ走りの隣の駒が版の奥の端を跨ぐ(口が開かない)③ 同じ走りのほかの駒が版の先(足元の角)を越えない(突き抜けない)とき。
        //   どれかを破れば両脇とも (b)。(a) が破れるのは両脇の控え c が倍率と違う角・一つずつ内へ引いた端の駒(第150巡の試し: P14 は Q が 8.4m 先・P19 2.2・P35 隣と 0.27 の口・P41 隣が 0.15 越える)。
        Vector2 mn = (dA + dB).normalized;   // 二つの切り口の面の法線(走りの平均)
        Vector2 oEA = PolyEdgeOut(poly, e0), oEB = PolyEdgeOut(poly, v);
        var made = new GameObject[2]; var footW = new Vector2[2]; var crestW = new Vector2[2]; var posB = new Vector3[2]; var posA = new Vector3[2];
        var others = new List<GameObject>[2];
        for (int side = 0; side < 2; side++)
        {
            var old = ends[side]; Vector2 d = side == 0 ? dA : dB;
            others[side] = new List<GameObject>();
            foreach (var g in pieces)
            {
                if (g == null || g == old || g == ends[1 - side] || g.name.StartsWith("IG_Slit_")) continue;
                var fg = new Vector2(g.transform.forward.x, g.transform.forward.z).normalized; if (Mathf.Abs(Vector2.Dot(fg, d)) < 0.9999f) continue;
                var q = new Vector2(g.transform.position.x - old.transform.position.x, g.transform.position.z - old.transform.position.z);
                if (Mathf.Abs(d.x * q.y - d.y * q.x) > 1.0f || Mathf.Abs(Vector2.Dot(q, d)) > 6f) continue; others[side].Add(g);
            }
            var spec = UnityEditor.AssetDatabase.LoadAssetAtPath<TextAsset>(EdoAssets.PartSpecs.Dir + System.IO.Path.GetFileNameWithoutExtension(tomes[side]) + ".json");
            Vector3 cfc = new Vector3(-1.4f, hs[side], 0f); float com = hs[side];
            if (spec != null)
            {
                var j = JsonUtility.FromJson<TomeSpecJ>(spec.text);
                if (j != null && j.tomeCrestFrontCorner != null) { cfc = new Vector3(j.tomeCrestFrontCorner.x, j.tomeCrestFrontCorner.y, j.tomeCrestFrontCorner.z); com = j.crestOnMiter; }
            }
            float s = old.transform.lossyScale.x;
            float zq = old.transform.InverseTransformPoint(new Vector3(Q.x, old.transform.position.y, Q.y)).z;
            var wc = old.transform.TransformPoint(cfc);
            var pa = old.transform.position + new Vector3(Q.x - wc.x, 0f, Q.y - wc.z); pa.y = old.transform.position.y + s * (hs[side] + gs[side] * zq) - com * s;
            posA[side] = pa; posB[side] = old.transform.position;
            var rot = old.transform.rotation; string nm = old.name; var par = old.transform.parent;
            var go = Place(tomes[side], pa, rot.eulerAngles.y, old.transform.localScale, par, nm + "_Tome"); go.transform.rotation = rot;
            for (int i = 0; i < pieces.Count; i++) if (pieces[i] == old) pieces[i] = go;
            UnityEngine.Object.DestroyImmediate(old); made[side] = go;
        }
        Physics.SyncTransforms();
        var superseded = new List<GameObject>();
        Func<string> check = () =>
        {
            superseded.Clear();
            for (int side = 0; side < 2; side++)
            {
                Vector2 d = side == 0 ? dA : dB; float sg = side == 0 ? 1f : -1f;   // 角へ向かう走り
                float tMin = float.MaxValue, tMax = float.MinValue, outW = float.MinValue;
                foreach (var w in Body(made[side].transform, 999999))
                {
                    var q = new Vector2(w.x, w.z) - V; float a = Vector2.Dot(q, d) * sg; tMin = Mathf.Min(tMin, a); tMax = Mathf.Max(tMax, a);
                    if (!EdoGeom.PIP(poly, new Vector2(w.x, w.z))) outW = Mathf.Max(outW, Mathf.Min(Mathf.Max(Vector2.Dot(q, oEA), Vector2.Dot(q, oEB)), 99f));
                }
                if (outW > 0.01f) return (side == 0 ? "前" : "次") + "の辺の版が区画の外 " + outW.ToString("F3");
                bool covered = others[side].Count == 0; float over = float.MinValue; var bTome = RB(made[side]);
                foreach (var g in others[side])
                {
                    var bg = RB(g); if (bg.max.y < bTome.min.y + 0.1f || bg.min.y > bTome.max.y - 0.1f) continue;   // 下へ継いだ段・上の駒は同じ段でない
                    float aMin = float.MaxValue, aMax = float.MinValue;
                    foreach (var w in Body(g.transform, 999999)) { float a = Vector2.Dot(new Vector2(w.x, w.z) - V, d) * sg; aMin = Mathf.Min(aMin, a); aMax = Mathf.Max(aMax, a); }
                    //   版の奥の端より全て先(角の側)に在る駒は版に替わられた残り ── この据えを採るなら退ける(留めの面を越えて隣の辺へ突き抜ける)
                    if (aMin > tMin + 0.01f && aMax > tMax - 0.01f) { superseded.Add(g); continue; }
                    if (aMin < tMin + 0.01f && aMax > tMin - 0.01f) covered = true;
                    over = Mathf.Max(over, aMax - tMax);
                }
                if (!covered) return (side == 0 ? "前" : "次") + "の辺の版の奥に口(隣の駒が届かない)";
                if (over > 0.02f) return (side == 0 ? "前" : "次") + "の辺の隣の駒が版の先を " + over.ToString("F3") + " 越える";
            }
            return null;
        };
        Func<int, Vector2> footOf = side =>
        {
            var f = made[side].transform.TransformPoint(new Vector3(-2.4f, 0f, pEnd[side] ? 0f : -ls[side])); return new Vector2(f.x, f.z);
        };
        //   走りに沿って k[m] 動かす(坂なりの駒は天端の線に乗るよう y も勾配で)
        Func<int, Vector3, float, Vector3> slideAlong = (side, basePos, k) =>
        {
            Vector2 d = side == 0 ? dA : dB; var fw = made[side].transform.forward; float run = k * Vector2.Dot(d, new Vector2(fw.x, fw.z).normalized);
            return basePos + new Vector3(d.x * k, gs[side] * run, d.y * k);
        };
        string fail = null, how = null; var tried = new List<string>();
        //   (a) 札の据え(Q)
        made[0].transform.position = posA[0]; made[1].transform.position = posA[1]; Physics.SyncTransforms();
        fail = check(); if (fail == null) how = "札の据え(Q へ寄せ " + (new Vector2(posA[0].x - posB[0].x, posA[0].z - posB[0].z)).magnitude.ToString("F3") + "/" + (new Vector2(posA[1].x - posB[1].x, posA[1].z - posB[1].z)).magnitude.ToString("F3") + ")";
        else tried.Add("Q: " + fail);
        if (how == null)
        {
            //   (c) 元の位置から片側だけ(前の辺 → 次の辺 → 半分ずつ)走りに沿って寄せ、足元の前の角で継ぎ目を閉じる
            made[0].transform.position = posB[0]; made[1].transform.position = posB[1]; Physics.SyncTransforms();
            float d0 = Vector2.Dot(footOf(0) - footOf(1), mn);
            float kA = -d0 / Mathf.Max(1e-3f, Vector2.Dot(dA, mn)), kB = d0 / Mathf.Max(1e-3f, Vector2.Dot(dB, mn));
            var opts = new[] { new Vector2(kA, 0f), new Vector2(0f, kB), new Vector2(kA * 0.5f, kB * 0.5f) }; var lab = new[] { "前の辺だけ", "次の辺だけ", "半分ずつ" };
            for (int o = 0; o < opts.Length && how == null; o++)
            {
                if (Mathf.Abs(d0) <= 0.02f) break;
                made[0].transform.position = slideAlong(0, posB[0], opts[o].x); made[1].transform.position = slideAlong(1, posB[1], opts[o].y); Physics.SyncTransforms();
                var f = check(); if (f == null) how = lab[o] + "寄せ(" + opts[o].x.ToString("+0.000;-0.000") + "/" + opts[o].y.ToString("+0.000;-0.000") + ")"; else tried.Add(lab[o] + ": " + f);
            }
        }
        if (how == null) { superseded.Clear(); made[0].transform.position = posB[0]; made[1].transform.position = posB[1]; Physics.SyncTransforms(); how = "元の駒の位置(" + string.Join(" / ", tried.ToArray()) + ")"; }
        fail = null;
        string retired = "";
        if (superseded.Count > 0)
        {
            foreach (var g in superseded) { if (g == null) continue; retired += " " + g.name; pieces.Remove(g); UnityEngine.Object.DestroyImmediate(g); }
            Physics.SyncTransforms();
        }
        for (int side = 0; side < 2; side++)
        {
            var go = made[side]; float zEnd = pEnd[side] ? 0f : -ls[side];
            var f = go.transform.TransformPoint(new Vector3(-2.4f, 0f, zEnd)); footW[side] = new Vector2(f.x, f.z);
            var c = go.transform.TransformPoint(new Vector3(-1.4f, 0f, zEnd + (pEnd[side] ? -1f : 1f) * Mathf.Tan(turn * 0.5f * Mathf.Deg2Rad))); crestW[side] = new Vector2(c.x, c.z);
        }
        //   継ぎ目の離れ(+ = 前の辺の切り口が次の辺の切り口より先 = 重なり・− = 口)── 足元の前の角と天端の前の縁の角の両方で
        float dFoot = Vector2.Dot(footW[0] - footW[1], mn), dCrest = Vector2.Dot(crestW[0] - crestW[1], mn);
        float worst = Mathf.Abs(dFoot) > Mathf.Abs(dCrest) ? dFoot : dCrest;
        var sbw = new System.Text.StringBuilder((Mathf.Abs(worst) <= 0.02f ? "⭕" : worst < 0f ? "★" : "⚠") + " 折れ " + turn.ToString("F1") + "°・" + how + (retired.Length > 0 ? "・版の先の残りを退けた:" + retired : "") + "・継ぎ目 足元 " + dFoot.ToString("+0.000;-0.000") + " / 天端 " + dCrest.ToString("+0.000;-0.000")
            + (worst < -0.02f ? "(口 ── 裏の駒も据える)" : worst > 0.02f ? "(重なり)" : ""));
        for (int side = 0; side < 2; side++)
            sbw.Append(" / " + made[side].name + " ← " + System.IO.Path.GetFileNameWithoutExtension(tomes[side]) + "(勾配の外れ " + gOff[side].ToString("+0.0000;-0.0000") + "・折れ " + tOff[side].ToString("+0.0;-0.0") + "°)");
        why = sbw.ToString(); return worst < -0.02f ? 1 : 2;
    }
    [Serializable] class TomeV3J { public float x, y, z; }
    [Serializable] class TomeSpecJ { public TomeV3J tomeCrestFrontCorner; public float crestOnMiter; }
}
