// 部材を依存の順に解き、変えた所から後だけ流し直す (EdoBuild の partial・2026-09-26・EDO-0455)
//
// ⭐ **何が足りなかったか**: 邸の建て直しは Stage を**一通り**流す(`BuildAll`)か、役が「どれを流し直すか」を
//    その都度考えて一本ずつ流すかの二択だった。前者は石段だけ直しても整地から流れ直し(数分〜十数分)、後者は
//    役が依存を読み違えると下流が古いまま残る(例: 石段を直して土留めを流し忘れる・縁の皮を張り直し忘れる)。
//
// ⭕ <see cref="EdoBuild.Jun"/> は Stage の**依存(何の上に据わるか)**を宣言として持ち、変えた Stage から
//    **下流の閉包だけ**を宣言の順に流す。上流(整地など)は流さない。
//    ・依存は「その Stage が**読む**物を作る Stage」。駒を据える床(石段・土留め)、読む地形を書く Stage(整地)
//    ・依存を宣言していない Stage でも、**足元の地形が動いたら**引き込む — 流さない Stage の駒の下の地形を流す前に
//      測っておき、流した後に 1mm 超動いていれば、その Stage と下流を流す(宣言の漏れを測って拾う・規則21)
//    ・順は宣言の順(= 一括の順)。一括もこの宣言から流す(順を二か所に書かない)
//
// ⛔ 変えた所を推し量らない — 呼び手(役・メニュー)が「どの Stage の入力を変えたか」を名乗る。C# の直しは
//    機械に見えないので、名乗るのが正しい。名乗りが広すぎても狭すぎても、足元の実測が狭すぎの側を拾う。
//
// 当たる先: 山王社の建て直し(EdoSannoShaRebuild の Stage0〜9)。同じ型 = Stage を一括で流す邸ビルダー
//   (EdoDoiBuilder.RunAll・EdoOkabeYashikiBuilder.RunAll・EdoShiomizakaRebuild.RunAll)。
//   類型ビルダーは区画ごとに建てるので当たらない。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**解く順。** Stage を依存つきで宣言し、変えた Stage から下流だけを流す。</summary>
    public sealed class Jun
    {
        sealed class Step
        {
            public string Key, Label;
            public string[] After;
            public Func<string> Run;
            /// <summary>この Stage の駒が据わる所(足元の地形を測る)。null = 地形に据わる駒を持たない。</summary>
            public Func<Transform> Ground;
        }

        readonly string name;
        readonly List<Step> steps = new List<Step>();
        /// <summary>足元の地形が「動いた」とみなす閾[m]。⛔ 設計値ではない — 高さの丸めの幅。</summary>
        public const float GROUND_EPS = 0.001f;

        public Jun(string name) { this.name = name; }

        /// <summary>Stage を一つ宣言する。<paramref name="after"/> はこの Stage が読む物を作る Stage の key
        /// (宣言済みのものだけ = 順は宣言の順)。<paramref name="ground"/> はこの Stage の駒の群(足元を測る)。</summary>
        public Jun Add(string key, string label, Func<string> run, string[] after = null, Func<Transform> ground = null)
        {
            if (Find(key) != null) throw new ArgumentException("解く順: key が重なる " + key);
            foreach (var a in after ?? new string[0])
                if (Find(a) == null) throw new ArgumentException("解く順: " + key + " の上流 " + a + " が先に宣言されていない");
            steps.Add(new Step { Key = key, Label = label, Run = run, After = after ?? new string[0], Ground = ground });
            return this;
        }

        Step Find(string key) { foreach (var s in steps) if (s.Key == key) return s; return null; }

        /// <summary>key の Stage と、それを(推移的に)上流に持つ Stage の集合。</summary>
        HashSet<string> Closure(IEnumerable<string> keys)
        {
            var set = new HashSet<string>();
            foreach (var k in keys)
            {
                if (Find(k) == null) throw new ArgumentException("解く順: " + name + " に Stage " + k + " は無い(" + Keys() + ")");
                set.Add(k);
            }
            foreach (var s in steps)   // 宣言の順 = 上流が先 ⇒ 一巡で閉じる
                if (!set.Contains(s.Key)) foreach (var a in s.After) if (set.Contains(a)) { set.Add(s.Key); break; }
            return set;
        }

        public string Keys() { var ks = new List<string>(); foreach (var s in steps) ks.Add(s.Key); return string.Join("・", ks.ToArray()); }

        /// <summary>流す前の見積り(流さない)。変えた Stage から流れる Stage と、流れない Stage を返す。</summary>
        public string Plan(params string[] changed)
        {
            var set = Closure(changed);
            var run = new List<string>(); var skip = new List<string>();
            foreach (var s in steps) (set.Contains(s.Key) ? run : skip).Add(s.Label);
            return name + " の流し直し(見積り・" + string.Join("・", changed) + " を変えた): 流す " + string.Join(" → ", run.ToArray()) +
                   " / 流さない " + (skip.Count > 0 ? string.Join("・", skip.ToArray()) : "無し") +
                   "\n  ⚠ 流さない Stage も、流した後に足元の地形が動いていれば引き込む(RunFrom)";
        }

        /// <summary>全部を宣言の順に流す(一括)。</summary>
        public string RunAll() { var ks = new List<string>(); foreach (var s in steps) ks.Add(s.Key); return RunFrom(ks.ToArray()); }

        /// <summary>**変えた Stage から下流だけ流す。**上流は流さない。流さない Stage の足元の地形を先に測り、
        /// 流した Stage の後で動いていれば、その Stage と下流を引き込む。戻り値の頭の1行が要約
        /// (流した・流さなかった・引き込んだ・所要)。</summary>
        public string RunFrom(params string[] changed)
        {
            var sw = Stopwatch.StartNew();
            var plan = Closure(changed);
            var why = new Dictionary<string, string>();
            foreach (var k in changed) why[k] = "変えた";
            foreach (var s in steps) if (plan.Contains(s.Key) && !why.ContainsKey(s.Key)) why[s.Key] = "上流を流す";

            // 流さない Stage の足元を先に測る
            var watch = new Dictionary<string, JunAshimoto>();
            foreach (var s in steps)
                if (!plan.Contains(s.Key) && s.Ground != null)
                {
                    var gp = JunAshimoto.Take(s.Ground());
                    if (gp != null) watch[s.Key] = gp;
                }

            var body = new StringBuilder(); var ran = new List<string>(); var pulled = new List<string>(); var late = new List<string>();
            for (int i = 0; i < steps.Count; i++)
            {
                var s = steps[i];
                if (!plan.Contains(s.Key)) continue;
                var t0 = sw.Elapsed.TotalSeconds;
                string r;
                try { r = s.Run(); }
                catch (Exception e)
                {
                    body.AppendLine("⛔ " + s.Label + " で止まった: " + e.Message);
                    return Head(ran, pulled, late, sw, "⛔ " + s.Label + " で止まった") + "\n" + body;
                }
                ran.Add(s.Label);
                body.AppendLine("── " + s.Label + "(" + why[s.Key] + "・" + (sw.Elapsed.TotalSeconds - t0).ToString("F1") + " 秒)");
                body.AppendLine(r);

                // 流した後、流さない Stage の足元が動いたか
                foreach (var kv in new List<KeyValuePair<string, JunAshimoto>>(watch))
                {
                    float d = kv.Value.MaxMove();
                    if (d <= GROUND_EPS) continue;
                    watch.Remove(kv.Key);
                    int at = steps.IndexOf(Find(kv.Key));
                    if (at < i)
                    {   // 宣言の順で先の Stage — 一括でも流し直さない所。引き込めないので刷るだけ
                        late.Add(Find(kv.Key).Label + "(" + s.Label + " が足元を " + d.ToString("F3") + "m 動かした)");
                        continue;
                    }
                    foreach (var k in Closure(new[] { kv.Key }))
                        if (plan.Add(k)) why[k] = k == kv.Key ? s.Label + " が足元を " + d.ToString("F3") + "m 動かした" : "上流を流す";
                    pulled.Add(Find(kv.Key).Label);
                }
            }
            return Head(ran, pulled, late, sw, null) + "\n" + body;
        }

        string Head(List<string> ran, List<string> pulled, List<string> late, Stopwatch sw, string stop)
        {
            var skip = new List<string>(); foreach (var s in steps) if (!ran.Contains(s.Label)) skip.Add(s.Label);
            return (stop ?? (late.Count > 0 ? "⚠" : "⭕")) + " " + name + " 流した " + ran.Count + "/" + steps.Count + "(" + string.Join(" → ", ran.ToArray()) + ")" +
                   " / 流さなかった " + (skip.Count > 0 ? string.Join("・", skip.ToArray()) : "無し") +
                   (pulled.Count > 0 ? " / 足元が動いて引き込んだ " + string.Join("・", pulled.ToArray()) : "") +
                   (late.Count > 0 ? " / ⚠ 先の Stage の足元が動いた(流し直していない): " + string.Join("・", late.ToArray()) : "") +
                   " / " + sw.Elapsed.TotalSeconds.ToString("F1") + " 秒";
        }
    }

    /// <summary>駒の群の下の地形の高さを覚えておき、後で動いた量を測る(<see cref="Jun"/> の引き込みの物差し)。
    /// 範囲は駒ごとの外接の XZ を 1 格子ぶん広げた矩形の和(⛔ 群全体の外接でまとめない — 散った群で敷地全部を読む)。</summary>
    sealed class JunAshimoto
    {
        readonly Terrain t;
        readonly List<RectInt> rects = new List<RectInt>();
        readonly List<float[,]> before = new List<float[,]>();

        public static JunAshimoto Take(Transform grp)
        {
            if (grp == null) return null;
            var t = T(); if (t == null) return null;
            var td = t.terrainData; int res = td.heightmapResolution; var org = t.transform.position;
            float cx = td.size.x / (res - 1), cz = td.size.z / (res - 1);
            var gp = new JunAshimoto(t);
            foreach (var r in grp.GetComponentsInChildren<Renderer>(false))
            {
                var b = r.bounds;
                int i0 = Mathf.Clamp(Mathf.FloorToInt((b.min.x - org.x) / cx) - 1, 0, res - 1);
                int i1 = Mathf.Clamp(Mathf.CeilToInt((b.max.x - org.x) / cx) + 1, 0, res - 1);
                int j0 = Mathf.Clamp(Mathf.FloorToInt((b.min.z - org.z) / cz) - 1, 0, res - 1);
                int j1 = Mathf.Clamp(Mathf.CeilToInt((b.max.z - org.z) / cz) + 1, 0, res - 1);
                if (i1 < i0 || j1 < j0) continue;
                var rc = new RectInt(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
                bool inside = false;
                foreach (var q in gp.rects) if (q.xMin <= rc.xMin && q.yMin <= rc.yMin && q.xMax >= rc.xMax && q.yMax >= rc.yMax) { inside = true; break; }
                if (inside) continue;
                gp.rects.Add(rc); gp.before.Add(td.GetHeights(rc.x, rc.y, rc.width, rc.height));
            }
            return gp.rects.Count > 0 ? gp : null;
        }

        JunAshimoto(Terrain t) { this.t = t; }

        /// <summary>覚えた時から動いた高さの最大[m]。</summary>
        public float MaxMove()
        {
            var td = t.terrainData; float m = 0f;
            for (int k = 0; k < rects.Count; k++)
            {
                var rc = rects[k]; var now = td.GetHeights(rc.x, rc.y, rc.width, rc.height); var was = before[k];
                for (int y = 0; y < rc.height; y++) for (int x = 0; x < rc.width; x++)
                    m = Mathf.Max(m, Mathf.Abs(now[y, x] - was[y, x]));
            }
            return m * td.size.y;
        }
    }
}
