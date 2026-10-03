// 制約の二種 — 硬い制約(関門)と柔らかい制約(狙い)を、置く側の共通の層で使い分ける(EDO-0372・施主 2026-09-23)。
//
// ⭐ 正典は docs/oki-kata.md §4a。ここはその実装だけ。
//
//   硬い制約(Hard)= 許容0。破る置き場は**退ける**。どの置き場でも破るなら、その駒は**建てない**(⛔ で刷る)。
//                    区域侵犯・めり込み・埋没/浮き・接地が測れない、など docs/oki-kata.md §4 の物だけ。
//   柔らかい制約(Soft)= 狙い。満たす置き場があればそこへ。どこも満たさなければ、**試した中で最も近い所へ建てる**
//                    (⛔ 狙いのために駒を落とさない・建て直しを回さない)。届かなかった分は ⚠ で刷り、
//                    検査では「不合格」でなく「狙い未達」の列に数える。前庭の奥行・棟どうしの離れの目安など。
//
// ⛔ 柔らかい制約を関門として書かない(if (測った値 < 狙い) 退ける、を邸ビルダーに書かない)。
//    2026-09-23 に前庭 7.6m を関門で入れかけ、施主に「縛りがキツすぎて検査違反と作り直しが繰り返される」と止められた。
// ⛔ 硬い制約を狙いへ落とさない — 許容0 の物を「最も近い所」で妥協すると欠陥が建つ(規則4)。

using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>硬い制約。<c>ok(駒)</c> が false の置き場は退ける。</summary>
    public sealed class Hard
    {
        public readonly string Name; public readonly Func<GameObject, bool> Ok;
        public Hard(string name, Func<GameObject, bool> ok) { Name = name; Ok = ok; }
    }

    /// <summary>柔らかい制約。<c>measure(駒)</c> が <c>Target</c> 以上なら満たす(大きいほど良い物だけを書く)。</summary>
    public sealed class Soft
    {
        public readonly string Name; public readonly float Target; public readonly Func<GameObject, float> Measure;
        public Soft(string name, float target, Func<GameObject, float> measure) { Name = name; Target = target; Measure = measure; }
    }

    /// <summary>制約ごとの勘定。邸ビルダーの log へそのまま刷る(規則19)。</summary>
    public sealed class SeiyakuTally
    {
        public readonly Dictionary<string, int> HardRejected = new Dictionary<string, int>();
        public readonly Dictionary<string, int> SoftTried = new Dictionary<string, int>();
        public readonly Dictionary<string, int> SoftShort = new Dictionary<string, int>();
        /// <summary>柔らかい制約ごとの、建った駒の最悪値(狙いとの比較のため)。</summary>
        public readonly Dictionary<string, float> SoftWorst = new Dictionary<string, float>();
        public readonly Dictionary<string, float> SoftTarget = new Dictionary<string, float>();
        public int Dropped;

        internal static void Inc(Dictionary<string, int> d, string k) { int v; d.TryGetValue(k, out v); d[k] = v + 1; }

        public string Summary()
        {
            var sb = new StringBuilder();
            foreach (var kv in SoftTarget)
            {
                float w; bool has = SoftWorst.TryGetValue(kv.Key, out w);
                int shortN; SoftShort.TryGetValue(kv.Key, out shortN);
                sb.AppendFormat("・{0}(狙い {1:F1}・建った最小 {2}){3}", kv.Key, kv.Value,
                    has ? w.ToString("F1") : "—",
                    shortN > 0 ? string.Format(" ⚠ {0}棟は狙いに届かず、試した中で最も近い所に建てた", shortN) : "");
            }
            foreach (var kv in HardRejected)
                sb.AppendFormat("・{0} で退けた置き場 {1}", kv.Key, kv.Value);
            if (Dropped > 0) sb.AppendFormat("・⛔ {0}棟は硬い制約を満たす置き場が無く建てない", Dropped);
            return sb.ToString();
        }
    }

    /// <summary>置き場の候補を順に試し、**硬い制約で退け・柔らかい制約で選ぶ**。
    /// <paramref name="place"/> は置き場へ駒を置いて据える(据わらなければ null — 硬い制約「接地」として数える)。
    /// 硬い制約を全部通り、柔らかい制約も全部満たす最初の置き場で止まる。満たす所が無ければ、硬い制約を通った中で
    /// **狙いへの不足の合計が最も小さい置き場**へ置き直す(<paramref name="place"/> は同じ入力で同じ結果を返すこと)。
    /// どこも硬い制約を通らなければ null。</summary>
    public static GameObject PlaceBest(IEnumerable<Vector2> spots, int maxTries, Func<Vector2, GameObject> place,
                                       IList<Hard> hards, IList<Soft> softs, SeiyakuTally tally)
    {
        return PlaceBest<Vector2>(spots, maxTries, place, hards, softs, tally);
    }

    /// <summary><see cref="PlaceBest(IEnumerable{Vector2},int,Func{Vector2,GameObject},IList{Hard},IList{Soft},SeiyakuTally)"/> の
    /// 置き場が**位置だけでない**版(位置+向きなど)。作法は同じ ── 硬い制約で退け、柔らかい制約で選ぶ。
    /// 当たる先: 類型の寺社の棟(EdoTypologyBuilder.Jisha ── 置き場 = 位置と向き・2026-09-27 EDO-0477 P4)。</summary>
    public static GameObject PlaceBest<T>(IEnumerable<T> spots, int maxTries, Func<T, GameObject> place,
                                          IList<Hard> hards, IList<Soft> softs, SeiyakuTally tally)
    {
        foreach (var sf in softs) tally.SoftTarget[sf.Name] = sf.Target;
        bool hasBest = false; T best = default(T); float bestShort = float.PositiveInfinity;
        int tries = 0;
        foreach (var spot in spots)
        {
            if (tries++ >= maxTries) break;
            var go = place(spot);
            if (go == null) { SeiyakuTally.Inc(tally.HardRejected, "接地"); continue; }
            string broke = null;
            foreach (var h in hards) if (!h.Ok(go)) { broke = h.Name; break; }
            if (broke != null) { SeiyakuTally.Inc(tally.HardRejected, broke); UnityEngine.Object.DestroyImmediate(go); continue; }
            float shortSum = 0f;
            foreach (var sf in softs)
            {
                float m = sf.Measure(go);
                if (m < sf.Target) { shortSum += sf.Target - m; SeiyakuTally.Inc(tally.SoftTried, sf.Name); }
            }
            if (shortSum <= 0f) { Record(go, softs, tally); return go; }
            if (shortSum < bestShort) { bestShort = shortSum; best = spot; hasBest = true; }
            UnityEngine.Object.DestroyImmediate(go);
        }
        if (hasBest)
        {
            var go = place(best);
            if (go != null)
            {
                bool okAll = true;
                foreach (var h in hards) if (!h.Ok(go)) { okAll = false; break; }
                if (okAll) { Record(go, softs, tally); return go; }
                UnityEngine.Object.DestroyImmediate(go);   // 同じ入力で違う結果 = place が決定的でない(呼び手の欠陥)
                Debug.LogWarning("[EdoBuild.PlaceBest] 控えの置き場が置き直しで硬い制約を破った — place が決定的でない");
            }
        }
        tally.Dropped++;
        return null;
    }

    static void Record(GameObject go, IList<Soft> softs, SeiyakuTally tally)
    {
        foreach (var sf in softs)
        {
            float m = sf.Measure(go);
            float w;
            if (!tally.SoftWorst.TryGetValue(sf.Name, out w) || m < w) tally.SoftWorst[sf.Name] = m;
            if (m < sf.Target) SeiyakuTally.Inc(tally.SoftShort, sf.Name);
        }
    }
}
