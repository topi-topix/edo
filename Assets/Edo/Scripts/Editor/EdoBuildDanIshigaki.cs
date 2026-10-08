// EdoBuild — 段の土留め(石垣・野面)を天端の折れ線へ据える(2026-10-03・EDO-0502 岡部 terraceWalls)。
//  スキル unity-modular-stonewall の作法: 天端は run ごとに一直線(丸い数字のまま)・駒は伸縮しない(端数は重なり・高さは埋まり)・
//  ピッチは閉形式(城の石垣 1.80 / 重ね 0.20、野面は 1間で突き付け)・ほとんど見えない折れは一本の run(横 0.10m 以内)・開口は縁を起点に割る。
//  置き方の4手(docs/oki-kata.md §2): 駒を置く → 見え面(法の面)を低い側へ向け、天端の前の縁を線へ寄せる(FaceWallToLine・実メッシュ)
//  → 走りの端は実メッシュの射影で区間の端へ → 天端は実メッシュの最上点を天端の値へ。⛔ ピボットで決めない。
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図・算出物を読んで渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>天端の折れ線一本ぶんの土留め(<see cref="PlaceCrestWall"/> の入力)。</summary>
    public class CrestWall
    {
        public string name;
        /// <summary>天端の前の縁の線(世界 xz)。</summary>
        public List<Vector2> nodes = new List<Vector2>();
        /// <summary>節点ごとの天端の高さ(一本の天端なら全部同じ)。区間の天端 = 両端の高い方(区間は一直線の天端・段は節点で)。</summary>
        public List<float> nodeTops = new List<float>();
        /// <summary>口(石段・坂の切れ目)── 折れ線の道のり s の [s0, s1]。</summary>
        public List<Vector2> gaps = new List<Vector2>();
        /// <summary>見付(見え面の前の地表から天端まで)→ 駒のパス。城の石垣は丈が一つなので常に同じ駒を返す。</summary>
        public Func<float, string> pathOfH;
        /// <summary>駒の走りが局所 X か(野面 = true)/ 局所 Z か(城の石垣 Castle Wall = false)。</summary>
        public bool runAlongX;
        /// <summary>駒の走りの長さ・送りの上限[m](城の石垣 2.00 / 1.80、野面 1.818 / 1.818)。</summary>
        public float runLen = 2.0f, pitchMax = 1.8f;
        /// <summary>低い側が地表で決まらない区間の手掛かり(区間の中点 → 低い側の向き。無ければ zero)。</summary>
        public Func<Vector2, Vector2, Vector2> lowHint;
        /// <summary>true なら低い側を地表で測らず <see cref="lowHint"/> に従う(口の返し ── 見え面は口の内と決まっている。
        /// 地表で測ると返しの裏(本体の石垣の法の下)の方が低く出て裏返る・EDO-0502 第8巡)。</summary>
        public bool lowForce;
    }

    /// <summary>**見付に合う丈の城の石垣の直線の駒**(2026-10-03・EDO-0502)。見付 ≤ 4.00(+0.01)なら素の <c>JC.CastleWall</c>、
    /// 越えれば焼いてある丈違いの駒(<c>EdoAssets.Own.IshigakiChoku</c>・4.5〜8.0 を 0.5 刻み)のうち見付以上の最小。
    /// 据えは素と同じ(<see cref="PlaceCrestWall"/> が天端を実測の最上点へ合わせるので y = 天端 − 丈)。
    /// 条件: 柔らかい ── 焼いた丈が見付に届かなければ最も高い駒で建てて、底の浮きは PlaceCrestWall の ★ が刷る。
    /// 当たる先: 城の石垣の段の土留めで見付が 4m を超える所(岡部 TW_Kado_Shumen 見付 4.11〜4.50)。山王 Stage3 は専用版で未適用。</summary>
    public static string CastleWallOfExpose(float expose)
    {
        if (expose <= 4.01f) return EdoAssets.JC.CastleWall;
        string root = System.IO.Directory.GetParent(Application.dataPath).FullName, last = null;
        for (float h = 4.5f; h <= 8.01f; h += 0.5f)
        {
            string p = EdoAssets.Own.IshigakiChoku(h);
            if (!System.IO.File.Exists(System.IO.Path.Combine(root, p))) continue;
            last = p; if (h >= expose - 0.01f) return p;
        }
        return last ?? EdoAssets.JC.CastleWall;
    }

    /// <summary>**段の土留めを天端の折れ線へ据える**(城の石垣・野面の乱積み)。
    /// <para>硬い(許容0): ① 駒の天端 = 区間の天端(実測の最上点・誤差 0.001)② 全体が地表の下に来る駒は置かない(<see cref="CrestAboveGround"/>)
    /// ③ 駒の底が見え面の前の地表より上(浮き > 0.01m)なら ★ で刷る(丈を伸ばさない・二段築か地盤かは呼び手=設計の話)。
    /// 柔らかい: 見付に合う丈の駒(野面)── 焼いた丈の中で見付以上の最小、無ければ最大を ⚠。</para>
    /// <para>返り値 = 据えた駒。<paramref name="endsOut"/> へ区間の端(出隅の隅の駒を据える <see cref="PlaceRunCorners"/> 用)、
    /// <paramref name="segOut"/> へ区間ごとの駒を足す。<paramref name="worstFloat"/> = 駒の底の浮きの最悪[m]。</para>
    /// 当たる先: 各邸の段の土留め・腰石垣・袖石垣・法尻の野面石(岡部 terraceWalls 9 本。山王 Stage3 は同じ考えの専用版)。</summary>
    public static List<GameObject> PlaceCrestWall(CrestWall w, Func<float, float, float> groundAt, Transform parent,
                                                  List<RunEnd> endsOut, IDictionary<string, List<GameObject>> segOut,
                                                  System.Text.StringBuilder log, out float worstFloat, out int buriedSkip)
    {
        worstFloat = float.NegativeInfinity; buriedSkip = 0;
        var made = new List<GameObject>();
        if (w.nodes.Count < 2) return made;
        // ① ほとんど見えない折れは一本の run(横 0.10m 以内・天端が同じ所だけ束ねる ── スキル R3)
        var keep = new List<int> { 0 };
        {
            int i0 = 0, last = 1;
            Func<int, int, bool> straight = (from, to) =>
            {
                Vector2 A = w.nodes[from], B = w.nodes[to]; Vector2 d = (B - A).normalized, n = new Vector2(d.y, -d.x);
                for (int j = from + 1; j <= to; j++)
                {
                    if (Mathf.Abs(w.nodeTops[j] - w.nodeTops[from]) > 1e-3f) return false;
                    if (j < to && Mathf.Abs(Vector2.Dot(w.nodes[j] - A, n)) > 0.10f) return false;
                }
                return true;
            };
            for (int k = 2; k < w.nodes.Count; k++)
            {
                if (straight(i0, k)) { last = k; continue; }
                keep.Add(last); i0 = last; last = k;
            }
            keep.Add(w.nodes.Count - 1);
        }
        // 道のり(元の折れ線の s)
        var arc = new float[w.nodes.Count]; for (int k = 1; k < w.nodes.Count; k++) arc[k] = arc[k - 1] + Vector2.Distance(w.nodes[k - 1], w.nodes[k]);

        for (int q = 0; q + 1 < keep.Count; q++)
        {
            int ia = keep[q], ib = keep[q + 1];
            Vector2 a = w.nodes[ia], b = w.nodes[ib];
            float len = Vector2.Distance(a, b); if (len < 0.3f) continue;
            Vector2 dir = (b - a) / len, nrm = new Vector2(dir.y, -dir.x);
            float crest = Mathf.Max(w.nodeTops[ia], w.nodeTops[ib]);
            float sA = arc[ia], sB = arc[ib], scale = len / Mathf.Max(1e-4f, sB - sA);   // 束ねた区間は弦の長さへ写す
            // 低い側(描かれた地表を線の両側で ── 駒の奥行 + 0.6 離す)
            int vn, vx;
            Vector2 lowN = LowSide(a, b, groundAt, 3.0f, 0.05f, null, out vn, out vx);
            if (w.lowForce && w.lowHint != null) { Vector2 h0 = w.lowHint(a, b); if (h0 != Vector2.zero) lowN = Vector2.Dot(h0, nrm) >= 0f ? nrm : -nrm; }
            if (lowN == Vector2.zero || vn == vx)
            {
                Vector2 h = w.lowHint != null ? w.lowHint(a, b) : Vector2.zero;
                if (h != Vector2.zero) lowN = Vector2.Dot(h, nrm) >= 0f ? nrm : -nrm;
                if (lowN == Vector2.zero) { log.AppendLine("  ★ " + w.name + "#" + q + ": 低い側が決まらない ── 据えない"); continue; }
            }
            // 口で割る
            var cuts = new List<Vector2> { new Vector2(0f, len) };
            foreach (var g in w.gaps)
            {
                float g0 = (g.x - sA) * scale, g1 = (g.y - sA) * scale;
                var nx = new List<Vector2>();
                foreach (var c in cuts)
                {
                    if (g1 <= c.x || g0 >= c.y) { nx.Add(c); continue; }
                    if (g0 > c.x) nx.Add(new Vector2(c.x, g0));
                    if (g1 < c.y) nx.Add(new Vector2(g1, c.y));
                }
                cuts = nx;
            }
            int ci = -1;
            foreach (var c in cuts)
            {
                ci++;
                float L = c.y - c.x; if (L < 0.3f) continue;
                string key = w.name + "#" + q + "_" + ci;
                var mine = new List<GameObject>(); if (segOut != null) segOut[key] = mine;
                Vector2 ea = a + dir * c.x, eb = a + dir * c.y;
                if (endsOut != null)
                {
                    endsOut.Add(new RunEnd { key = key, run = w.name, node = c.x < 1e-3f ? ia : -1, p = ea, outw = lowN, away = dir });
                    endsOut.Add(new RunEnd { key = key, run = w.name, node = c.y > len - 1e-3f ? ib : -1, p = eb, outw = lowN, away = -dir });
                }
                float W = w.runLen;
                int N = (L <= W) ? 1 : Mathf.CeilToInt((L - W) / w.pitchMax - 1e-4f) + 1;
                float pitch = (N > 1) ? (L - W) / (N - 1) : 0f;
                for (int i = 0; i < N; i++)
                {
                    float t = c.x + pitch * i;                         // 駒の走りの低い端
                    if (N == 1 && L < W) t = c.x + (L - W) * 0.5f;     // 駒より短い区間は両側へ等しくはみ出す(重なりを採る)
                    Vector2 mid = a + dir * (t + W * 0.5f);
                    // 見付 = 天端 − 見え面の前の地表の最低(駒の走りの 3 点)
                    float gMin = float.MaxValue;
                    for (int s3 = 0; s3 < 3; s3++)
                    {
                        Vector2 p = a + dir * Mathf.Clamp(t + W * (0.1f + 0.4f * s3), c.x, c.y) + lowN * 0.3f;
                        float gy = groundAt(p.x, p.y); if (!float.IsNaN(gy)) gMin = Mathf.Min(gMin, gy);
                    }
                    float expose = gMin == float.MaxValue ? 0f : crest - gMin;
                    string path = w.pathOfH(expose);
                    if (path == null) continue;
                    float psi = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg - (w.runAlongX ? 90f : 0f);
                    GameObject go = null; float bot = 0f;
                    // ⭐ 見付は**見え面の足元の前**の地表で測り直す(2026-10-04 EDO-0502 第9巡): 上の 3 点は天端の前の縁から 0.3m ── 法の駒
                    //   (城の石垣 1:0.25)では足元が天端の縁より 1m 前にあり、0.3m は駒の下(法の途中の設計の地盤)を測って見付を 0.5m 少なく読み、
                    //   丈 4.0 の駒が足元の面から 0.5m 浮いた(TW_Kado_Shumen の口の脇・皮が底の石の歯形へ盛り上がって土の歯が並んだ)。
                    //   据えた駒の実メッシュで足元の出(見え面の側へ天端の縁から最も出る量)を測り、その 0.3m 前の地表で丈を選び直す(1 回)。
                    for (int attempt = 0; attempt < 2; attempt++)
                    {
                        go = Place(path, new Vector3(mid.x, crest, mid.y), psi, Vector3.one, parent, w.name + "_" + q + "_" + ci + "_" + i.ToString("00"));
                        if (go == null) break;
                        // 見え面を低い側へ・天端の前の縁を線へ(実メッシュ)
                        FaceWallToLine(go, lowN, a);
                        // 走りの端を区間の割りの端へ(実メッシュの射影)
                        var vs = Body(go.transform, 999999);
                        float mn = float.MaxValue, top = float.MinValue, foot = 0f; bot = float.MaxValue;
                        foreach (var v in vs) { var p2 = new Vector2(v.x, v.z) - a; float s = Vector2.Dot(p2, dir); mn = Mathf.Min(mn, s); top = Mathf.Max(top, v.y); bot = Mathf.Min(bot, v.y); foot = Mathf.Max(foot, Vector2.Dot(p2, lowN)); }
                        go.transform.position += new Vector3(dir.x, 0f, dir.y) * (t - mn) + Vector3.up * (crest - top);
                        bot += crest - top;
                        if (attempt > 0 || foot <= 0.3f) break;
                        float g2 = float.MaxValue;
                        for (int s3 = 0; s3 < 3; s3++)
                        {
                            Vector2 p = a + dir * Mathf.Clamp(t + W * (0.1f + 0.4f * s3), c.x, c.y) + lowN * (foot + 0.3f);
                            float gy = groundAt(p.x, p.y); if (!float.IsNaN(gy)) g2 = Mathf.Min(g2, gy);
                        }
                        if (g2 == float.MaxValue || g2 >= gMin - 0.01f) break;
                        gMin = g2; expose = crest - gMin;
                        string p2n = w.pathOfH(expose);
                        if (p2n == null || p2n == path) break;
                        UnityEngine.Object.DestroyImmediate(go); go = null; path = p2n;
                    }
                    if (go == null) continue;
                    // 硬い: 全体が地表の下に来る駒は置かない
                    if (CrestAboveGround(go, lowN, groundAt) <= 0f) { UnityEngine.Object.DestroyImmediate(go); buriedSkip++; continue; }
                    float fl = gMin == float.MaxValue ? 0f : bot - gMin;
                    if (fl > worstFloat) worstFloat = fl;
                    if (fl > 0.01f) log.AppendLine("  ★ " + go.name + ": 駒の底が見え面の前の地表より " + fl.ToString("F3") + "m 上(見付 " + expose.ToString("F2") + "m > 駒の丈)");
                    made.Add(go); mine.Add(go);
                }
            }
        }
        return made;
    }

    /// <summary>**天端の垣(四つ目垣・建仁寺垣)を土留めの天端へ据える**(EDO-0502)。⛔ ピボットで並べない ── 4手で:
    /// ① 線 = 天端の前の縁(<paramref name="nodes"/>)から高い側へ、その土留めの駒の**天端の控えの半分**(<see cref="CrestToBack"/>・実メッシュ)。
    /// 見え面(+Z)は低い側(駒の見え面 <see cref="WallFace"/> の多数)へ。口(<paramref name="gaps"/>・道のり s)は空ける。
    /// ② 走り: 最初の間は実メッシュの走りの端を区間の端(余りは両端へ等分)へ、次の間は前の間の実メッシュの端へ突き付ける(隙 0)。
    /// ③ 高さ: 足の下の土留めの天端(<paramref name="stones"/> の子孫)を測って据える(<see cref="SeatOnCrest"/>・根入れ 0.15 = 部材の床から下の丈)。
    /// ④ 走りの +X 端に親柱を、実メッシュの端を最後の間の端へ合わせて足す。
    /// 返り値 = 据えた間の数。<paramref name="worstFloat"/> = 一間の足の当たりの高低差の最悪(床は最も高い当たりへ ⇒ 浮きは無く、低い当たりの上が空く量。根入れ 0.15 の内なら見えない)。
    /// 硬い: 床 = 最も高い当たり(浮き 0)/ 柔らかい: 線の位置(控えの半分)。
    /// 当たる先: 各邸の土留めの天端の垣(岡部 fenceOnTop 4 欄)。法の肩・途中には置かない(施主 2026-09-06)。</summary>
    public static int PlaceCrestFence(string span, string post, List<Vector2> nodes, List<Vector2> gaps, List<GameObject> wallPieces,
                                      Transform stones, Transform parent, string prefix, out float worstFloat, out int posts, out string note)
    {
        worstFloat = float.NaN; posts = 0; note = "";
        int n = 0; float s0 = 0f;
        if (wallPieces == null || wallPieces.Count == 0) { note = "土留めの駒が無い ── 建てない"; return 0; }
        // 見え面の向き(駒の多数)と天端の控え(中央値)
        var depths = new List<float>(); Vector2 faceSum = Vector2.zero;
        foreach (var g in wallPieces) { if (g == null) continue; var f = WallFace(g); faceSum += f; float d = CrestToBack(g, f); if (!float.IsNaN(d) && d > 0.1f) depths.Add(d); }
        depths.Sort(); float setback = depths.Count > 0 ? depths[depths.Count / 2] * 0.5f : 0.45f;
        if (depths.Count == 0) note += "天端の控えが測れず 0.45m ";
        float worst = float.NegativeInfinity;
        var beds = new List<GameObject>(); foreach (Transform c in stones) if (c.gameObject.activeInHierarchy) beds.Add(c.gameObject);
        var ptops = new PartTops(beds);   // 天端の索引(区間を天端の段・端で切る ── SplitCutsByCrest)
        {
            for (int k = 0; k + 1 < nodes.Count; k++)
            {
                Vector2 a = nodes[k], b = nodes[k + 1]; float len = Vector2.Distance(a, b); if (len < 0.3f) { s0 += len; continue; }
                Vector2 dir = (b - a) / len, nrm = new Vector2(dir.y, -dir.x);
                Vector2 lowN = Vector2.Dot(faceSum, nrm) >= 0f ? nrm : -nrm;
                Vector2 off = -lowN * setback;
                var cuts = new List<Vector2> { new Vector2(0f, len) };
                foreach (var g in gaps)
                {
                    float g0 = g.x - s0, g1 = g.y - s0; var nx = new List<Vector2>();
                    foreach (var c in cuts) { if (g1 <= c.x || g0 >= c.y) { nx.Add(c); continue; } if (g0 > c.x) nx.Add(new Vector2(c.x, g0)); if (g1 < c.y) nx.Add(new Vector2(g1, c.y)); }
                    cuts = nx;
                }
                float psi = Mathf.Atan2(lowN.x, lowN.y) * Mathf.Rad2Deg;   // 局所 +Z = lowN
                cuts = SplitCutsByCrest(cuts, a, dir, off, ptops);
                foreach (var c in cuts)
                {
                    var probe = Place(span, Vector3.zero, psi, Vector3.one, parent, "_probe");
                    if (probe == null) { note += "部材が無い " + span; return n; }
                    Vector3 rx = probe.transform.right; Vector2 ux = new Vector2(rx.x, rx.z).normalized;   // 局所 +X の向き(測る)
                    float pw; { float mn = float.MaxValue, mx = float.MinValue; foreach (var v in Body(probe.transform, 4000)) { float u = Vector2.Dot(new Vector2(v.x, v.z), ux); mn = Mathf.Min(mn, u); mx = Mathf.Max(mx, u); } pw = mx - mn; }
                    UnityEngine.Object.DestroyImmediate(probe);
                    // 区間の端(局所 +X の向きで低い方から)
                    Vector2 pA = a + dir * c.x + off, pB = a + dir * c.y + off;
                    Vector2 lo = Vector2.Dot(pA, ux) <= Vector2.Dot(pB, ux) ? pA : pB, hi = lo == pA ? pB : pA;
                    float L = Vector2.Distance(pA, pB);
                    int m = Mathf.FloorToInt(L / pw + 1e-3f);
                    // ⭐ 1 間より短い区間(段違いの返しの run・EDO-0502 第25巡)は 1 枚を走りへ縮めて据える ── ⛔ 2026-10-05 まで建てず、
                    //   岡部 TW_Minami_Koshi の東の返し(run 1.42/1.82/1.82 を重ねて段違い)の垣が 0 間だった。0.3m 未満の切れ端は建てない。
                    float sxS = 1f; if (m < 1) { if (L < 0.3f) continue; m = 1; sxS = L / pw; pw = L; }
                    // ⭐ 口の脇の端は口へ寄せて親柱で止める(EDO-0502 2026-10-07・指図 K_Kuruwa.sode「天端の垣は口の両脇に柱を立てて止め」【硬】)──
                    //   ⛔ 2026-10-07 まで余りを両端へ等分し、親柱は +X の端だけ ⇒ 口の片側で垣が口の 0.5〜1.0m 手前で柱なしに切れていた。
                    //   余りは口でない端へ寄せる(両端とも口なら等分)。当たる先: 口を持つ全ての天端の垣(岡部 fenceOnTop 4 欄)。
                    bool openA = false, openB = false;
                    // 許しは 0.3 ── SplitCutsByCrest が端の天端の無い所を 0.1 刻みで落とすので、口の端の区間の端は口から最大 0.1〜0.2 ずれる
                    foreach (var g in gaps) { if (Mathf.Abs((g.y - s0) - c.x) < 0.3f) openA = true; if (Mathf.Abs((g.x - s0) - c.y) < 0.3f) openB = true; }
                    bool openLo = lo == pA ? openA : openB, openHi = lo == pA ? openB : openA;
                    float rem = L - m * pw;
                    float target = Vector2.Dot(lo, ux) + (openLo && !openHi ? 0f : openHi && !openLo ? rem : rem * 0.5f);
                    float firstMin = target;
                    Vector2 runU = (hi - lo).normalized;
                    GameObject last = null;
                    for (int i = 0; i < m; i++)
                    {
                        Vector2 p = lo + runU * ((L - m * pw) * 0.5f + pw * (i + 0.5f));
                        var go = Place(span, new Vector3(p.x, 0f, p.y), psi, new Vector3(sxS, 1f, 1f), parent, prefix + "_" + k + "_" + n.ToString("000"));
                        if (go == null) continue;
                        float mn = float.MaxValue; foreach (var v in Body(go.transform, 4000)) mn = Mathf.Min(mn, Vector2.Dot(new Vector2(v.x, v.z), ux));
                        go.transform.position += new Vector3(ux.x, 0f, ux.y) * (target - mn);
                        float mx2 = float.MinValue; foreach (var v in Body(go.transform, 4000)) mx2 = Mathf.Max(mx2, Vector2.Dot(new Vector2(v.x, v.z), ux));
                        target = mx2;
                        float fl; if (!SeatFenceOnBeds(go, ux, beds, out fl)) { note += go.name + " の下に天端も地表も無い "; UnityEngine.Object.DestroyImmediate(go); continue; }
                        if (fl > worst) worst = fl;
                        last = go; n++;
                    }
                    if (last != null && post != null)
                    {
                        var pg = Place(post, last.transform.position, psi, Vector3.one, parent, prefix + "_" + k + "_post");
                        if (pg != null)
                        {
                            float mx = float.MinValue; foreach (var v in Body(pg.transform, 4000)) mx = Mathf.Max(mx, Vector2.Dot(new Vector2(v.x, v.z), ux));
                            pg.transform.position += new Vector3(ux.x, 0f, ux.y) * (target - mx);
                            float fl2; if (SeatFenceOnBeds(pg, ux, beds, out fl2)) posts++; else UnityEngine.Object.DestroyImmediate(pg);
                        }
                    }
                    if (last != null && post != null && openLo)
                    {   // 口の側(−X の端)の親柱 ── 実メッシュの −X の端を最初の間の端へ
                        var pg = Place(post, last.transform.position, psi, Vector3.one, parent, prefix + "_" + k + "_postLo");
                        if (pg != null)
                        {
                            float mn = float.MaxValue; foreach (var v in Body(pg.transform, 4000)) mn = Mathf.Min(mn, Vector2.Dot(new Vector2(v.x, v.z), ux));
                            pg.transform.position += new Vector3(ux.x, 0f, ux.y) * (firstMin - mn);
                            float fl3; if (SeatFenceOnBeds(pg, ux, beds, out fl3)) posts++; else UnityEngine.Object.DestroyImmediate(pg);
                        }
                    }
                }
                s0 += len;
            }
        }
        worstFloat = float.IsNegativeInfinity(worst) ? float.NaN : worst;
        if (n > 0) note += "線 = 天端の前の縁から " + setback.ToString("F2") + "m";
        return n;
    }

    /// <summary>**垣の区間を天端の段と端で切る**(2026-10-06 EDO-0502 第36巡 ── 南の腰の西の返し Kaki_TW_Minami_Koshi#ret0_1_001 が
    /// 上の run の天端(+0.5)と返しの端の先(−0.47)を一枚で跨ぎ、最も高い当たりへ据わって根元が 0.489 浮いた)。
    /// 線(<paramref name="a"/> + <paramref name="dir"/>·s + <paramref name="off"/>)を 0.1m 刻みで天端の索引(<paramref name="tops"/>)に当て、
    /// 隣り合う点の天端が 0.3 を超えて違う所(段違い)で区間を切り、区間の頭と尻の天端の無い所(土留めの端の先)を落とす。
    /// 区間の半分以上が天端に載らない区間は触らない(線が天端の外を通る垣 ── 測りが当てにならない)。0.3m 未満の切れ端は呼び手が建てない。
    /// 硬い: 垣は一つの天端の上だけ(⛔ 段・端を一枚で跨がない)。当たる先: 天端の垣を据える全邸(岡部 fenceOnTop 4 欄・段違いの返し)。</summary>
    static List<Vector2> SplitCutsByCrest(List<Vector2> cuts, Vector2 a, Vector2 dir, Vector2 off, PartTops tops)
    {
        if (tops == null) return cuts;
        const float STEP = 0.1f, JUMP = 0.3f;
        var res = new List<Vector2>();
        foreach (var c in cuts)
        {
            var ss = new List<float>(); var ts = new List<float>();
            for (float s = c.x; s <= c.y + 1e-4f; s += STEP) { var q = a + dir * s + off; string who; ss.Add(s); ts.Add(tops.Top(q.x, q.y, out who)); }
            int on = 0; foreach (var t in ts) if (!float.IsNaN(t)) on++;
            if (ts.Count < 3 || on * 2 < ts.Count) { res.Add(c); continue; }
            int i0 = 0, i1 = ts.Count - 1;
            while (i0 < ts.Count && float.IsNaN(ts[i0])) i0++;
            while (i1 >= 0 && float.IsNaN(ts[i1])) i1--;
            if (i0 > i1) continue;
            float segS = i0 == 0 ? c.x : ss[i0], last = ts[i0];
            for (int i = i0 + 1; i <= i1; i++)
            {
                if (float.IsNaN(ts[i])) continue;                       // 継ぎ目の目地(区間の中の天端の抜け)は跨ぐ
                if (Mathf.Abs(ts[i] - last) > JUMP) { res.Add(new Vector2(segS, (ss[i - 1] + ss[i]) * 0.5f)); segS = (ss[i - 1] + ss[i]) * 0.5f; }
                last = ts[i];
            }
            res.Add(new Vector2(segS, i1 == ts.Count - 1 ? c.y : ss[i1]));
        }
        return res;
    }

    /// <summary>垣の駒の足(走りの両端と中ほど・局所 +X の向き <paramref name="ux"/> の実メッシュの範囲)の真下の当たり =
    /// 土留めの駒の上向きの面(<see cref="BedTopAt"/>)と描かれた地表の高い方、を測り、**最も高い当たり**へ床(底 + 根入れ 0.15)を据える。
    /// <paramref name="spread"/> = 最も高い当たり − 最も低い当たり(その分だけ床の下が空く所がある ── 根入れ 0.15 の内なら見えない)。</summary>
    static bool SeatFenceOnBeds(GameObject go, Vector2 ux, IList<GameObject> beds, out float spread, Func<float, float, float> bedAt = null)
    {
        spread = float.NaN;
        float mn = float.MaxValue, mx = float.MinValue, bot = float.MaxValue, top = float.MinValue; Vector2 c = Vector2.zero; int nv = 0;
        foreach (var v in Body(go.transform, 4000)) { float u = Vector2.Dot(new Vector2(v.x, v.z), ux); mn = Mathf.Min(mn, u); mx = Mathf.Max(mx, u); bot = Mathf.Min(bot, v.y); top = Mathf.Max(top, v.y); c += new Vector2(v.x, v.z); nv++; }
        if (nv == 0) return false; c /= nv;
        float cu = Vector2.Dot(c, ux);
        float hi = float.MinValue, lo = float.MaxValue;
        // ⭐ 床の索引(bedAt)を渡されたら、足の三点でなく**足あと全体**(走り 0.1m 刻み × 見込みの前・芯・後)を測る(2026-10-06 EDO-0502 第36巡)。
        //   三点だと駒の端が天端の縁・継ぎ目の面取りから外へ出た所を見落とし、根元が 0.04 浮いた(南の腰・東の北東の 14 駒)。
        var us = new List<float>(); var ws = new List<float> { 0f };
        if (bedAt != null)
        {
            Vector2 uz = new Vector2(-ux.y, ux.x); float wmn = float.MaxValue, wmx = float.MinValue;
            foreach (var v in Body(go.transform, 4000)) { float w = Vector2.Dot(new Vector2(v.x, v.z) - c, uz); wmn = Mathf.Min(wmn, w); wmx = Mathf.Max(wmx, w); }
            for (float u = mn + 0.02f; u <= mx - 0.02f + 1e-4f; u += 0.1f) us.Add(u); us.Add(mx - 0.02f);
            ws = new List<float> { wmn + 0.01f, (wmn + wmx) * 0.5f, wmx - 0.01f };
        }
        else us.AddRange(new[] { mn + 0.03f, (mn + mx) * 0.5f, mx - 0.03f });
        Vector2 uzz = new Vector2(-ux.y, ux.x);
        foreach (float u in us) foreach (float wv in ws)
        {
            Vector2 p = c + ux * (u - cu) + uzz * wv;
            float y;
            if (bedAt != null) { y = bedAt(p.x, p.y); if (float.IsNaN(y)) y = Ground(p.x, p.y); }   // 据わる床(描かれた地表と土留めの上向きの面の高い方 ── EdoBuild.Bed)。皮も天端も無い所は地形(⛔ 測れない点を飛ばすと、端が地形の上へ出た駒が 0.045 浮いた・第36巡)
            else
            {
                float g = Ground(p.x, p.y), b = BedTopAt(p, beds, g + 6f);   // 光線は 8m まで ⇒ 地表の 6m 上から(⛔ 据える前の駒の頭からでは天端に届かない)
                y = float.IsNaN(b) ? g : Mathf.Max(b, g);
            }
            if (float.IsNaN(y)) continue;
            hi = Mathf.Max(hi, y); lo = Mathf.Min(lo, y);
        }
        // ⭐ 足の実の頂点(底から 0.05 の帯)の真下の床も測る(2026-10-07 EDO-0502 第46巡)── 0.1m 刻みの格子は親柱の足(幅 0.06)が
        //   高さの違う天端の石の継ぎ目を跨ぐ所を見落とし、低い石の側が 0.047 浮いた(Kaki_TW_Minami_Koshi_0_007・床 20.81/20.99)。
        //   当たる先: ReseatCrestFence で据え直す全邸の天端の垣(岡部 fenceOnTop 4 欄)。
        if (bedAt != null)
            foreach (var v in Body(go.transform, 4000))
            {
                if (v.y > bot + 0.05f) continue;
                float y = bedAt(v.x, v.z); if (float.IsNaN(y)) y = Ground(v.x, v.z); if (float.IsNaN(y)) continue;
                hi = Mathf.Max(hi, y); lo = Mathf.Min(lo, y);
            }
        if (hi == float.MinValue) return false;
        // 床 = 最も高い当たり − 根入れ 0.15。ただし最も低い当たりから根元の帯(ROOT_TOUCH)の分は下へ ── 硬い・根元の浮き 0(埋めて隠す・docs/oki-kata.md §4)
        float floorY = bedAt != null ? Mathf.Min(hi - 0.15f, lo - ROOT_TOUCH) : hi - 0.15f;
        go.transform.position += Vector3.up * (floorY - bot);
        spread = hi - lo;
        return true;
    }

    /// <summary>天端の垣(<see cref="PlaceCrestFence"/> が据えた間と親柱)を、**皮を起こした後の据わる床**
    /// <paramref name="bedAt"/>(<see cref="Bed"/>.At = 描かれた地表と土留め・石段の上向きの面の高い方)で据え直す(2026-10-04 EDO-0502 第15巡)。
    /// 置き方は据えと同じ(足の三点の最も高い当たり − 根入れ 0.15)。走りの位置・向きは動かさない。
    /// ⛔ 皮の前の 2m 格子(Ground)で据えたままにしない ── 岡部 Kaki_TW_Higashi_Hokuto_5_post は格子が土留めの天端より 0.2 高く、床から 0.050 浮いた。
    /// 当たる先: 皮を起こす邸の天端の垣すべて(岡部 fenceOnTop 4 欄)。練塀の <see cref="SinkGroupToBed"/>(皮の後の据え直し)と対。
    /// ⟶ 返す: 据え直した駒の数(<paramref name="up"/>/<paramref name="dn"/> = 最も上げた・下げた量[m])。</summary>
    public static int ReseatCrestFence(Transform fgrp, Func<float, float, float> bedAt, out float up, out float dn)
    {
        up = 0f; dn = 0f; int n = 0;
        if (fgrp == null || bedAt == null) return 0;
        foreach (Transform c in fgrp)
        {
            if (!c.gameObject.activeInHierarchy) continue;
            Vector3 rx = c.right; Vector2 ux = new Vector2(rx.x, rx.z); if (ux.sqrMagnitude < 1e-6f) continue; ux.Normalize();
            float y0 = c.position.y, sp;
            if (!SeatFenceOnBeds(c.gameObject, ux, null, out sp, bedAt)) continue;
            float mv = c.position.y - y0; up = Mathf.Max(up, mv); dn = Mathf.Min(dn, mv); n++;
        }
        return n;
    }

    /// <summary>**段石の下を同じ段石で接地まで積む**(雁木の積み・2026-10-03 EDO-0502 第4巡 岡部 K_Kuruwa: 石垣の口から下の面へ
    /// 張り出す石段の段石が下の面から最大 1.49m 浮いた)。硬い: 浮き 0 ── 一番下の駒が地面に触れる(<see cref="Contact"/> ≤ 0)まで積む。
    /// 触れる所: 積む駒の**上面 = 上の駒の底**(実メッシュの RB で測る・⛔ ピボットで決めない)。位置と向きは上の駒と同じ(xz・yaw)。
    /// 一番下の駒は地面へ埋まる分だけ根入れ(埋めて隠す)。<paramref name="maxN"/> 段を積んでも届かなければ ⚠ を <paramref name="warn"/> へ。
    /// 当たる先: 下の面へ張り出す石段(指図 kaidans[] で、足元の面の外まで段が出る物)。全邸の石段の据え(PlaceKaidanAB)が呼べる。
    /// ⟶ 返す: 積んだ駒の数</summary>
    public static int StackDownToGround(GameObject top, string path, Transform parent, string name, int maxN, List<string> warn,
                                        Func<float, float, float> drawnAt = null)
    {
        if (top == null) return 0;
        int n = 0; var cur = top; Vector3 at; int cnt;
        // ⭐ drawnAt(描かれた地表 ── 縁の皮が描く面の高さ)を渡されたら、駒の底の四隅と芯の**最も浮く所**で測る
        //   (2026-10-03 EDO-0502 第6巡: 地形の 2m 格子の盛りに触れて止まり、皮が描く北東の郭の面 13.10 から 1.07m 浮いた)。
        Func<GameObject, float> gapOf = g =>
        {
            if (drawnAt == null) return Contact(g, out at, out cnt);
            var b = RB(g); float worst = float.NaN;
            foreach (var q in new[] { new Vector2(b.min.x, b.min.z), new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.min.z), new Vector2(b.max.x, b.max.z), new Vector2(b.center.x, b.center.z) })
            { float gy = drawnAt(q.x, q.y); if (float.IsNaN(gy)) continue; float d = b.min.y - gy; if (float.IsNaN(worst) || d > worst) worst = d; }
            return worst;
        };
        float gap = gapOf(cur);
        while (!float.IsNaN(gap) && gap > 0.005f && n < maxN)
        {
            var b = RB(cur);
            var go = Place(path, new Vector3(cur.transform.position.x, b.min.y, cur.transform.position.z), cur.transform.eulerAngles.y,
                           cur.transform.localScale, parent, name + "_tsumi" + n);
            if (go == null) break;
            var nb = RB(go);
            go.transform.position += new Vector3(b.center.x - nb.center.x, b.min.y - nb.max.y, b.center.z - nb.center.z);
            n++; cur = go;
            gap = gapOf(cur);
        }
        if (!float.IsNaN(gap) && gap > 0.005f && warn != null)
            warn.Add("段石 " + top.name + ": " + maxN + " 段積んでも地面まで " + gap.ToString("F2") + "m 届かない");
        return n;
    }

    /// <summary>折れ線 <paramref name="nodes"/> の上の点 q の道のり s と、線からの符号付きの離れ t(左手 = 正)。最も近い区間で測る。</summary>
    public static Vector2 ArcOf(List<Vector2> nodes, Vector2 q)
    {
        float best = float.MaxValue, bs = 0f, bt = 0f, s0 = 0f;
        for (int k = 0; k + 1 < nodes.Count; k++)
        {
            Vector2 a = nodes[k], b = nodes[k + 1]; float L = Vector2.Distance(a, b); if (L < 1e-4f) continue;
            Vector2 d = (b - a) / L; float u = Mathf.Clamp(Vector2.Dot(q - a, d), 0f, L);
            Vector2 foot = a + d * u; float dist = Vector2.Distance(q, foot);
            if (dist < best) { best = dist; bs = s0 + u; bt = Vector2.Dot(q - a, new Vector2(-d.y, d.x)); }
            s0 += L;
        }
        return new Vector2(bs, bt);
    }

    /// <summary>折れ線の道のり s の点(世界 xz)と、その区間の向き。</summary>
    public static Vector2 ArcPoint(List<Vector2> nodes, float s, out Vector2 dir)
    {
        float s0 = 0f; dir = Vector2.right;
        for (int k = 0; k + 1 < nodes.Count; k++)
        {
            Vector2 a = nodes[k], b = nodes[k + 1]; float L = Vector2.Distance(a, b); if (L < 1e-4f) continue;
            dir = (b - a) / L;
            if (s <= s0 + L || k + 2 == nodes.Count) return a + dir * (s - s0);
            s0 += L;
        }
        return nodes[nodes.Count - 1];
    }

    /// <summary>**土留めの口の端を、口を通る石段の実面で決める**(EDO-0502 第8巡)。紙の口 <paramref name="gap"/>(道のり s0,s1)の近く
    /// (±2m)にある石段の駒の実メッシュの頂点のうち、土留めの線から <paramref name="band"/> 以内の物を線へ射影し、その最小・最大を口とする
    /// (= 石段の側面が土留めの線を切る所)。硬い(許容0): 口の端と石段の側面の間に隙を残さない。駒が線の近くに無ければ紙の口のまま ⚠。
    /// 当たる先: 石段・坂が段の土留めを切る口(岡部 TW_Kado_Shumen×K_Dan1・TW_Kado_Hokuto×K_Kuruwa・TW_Higashi_Tsuyo×K_Tsuyo)。</summary>
    public static Vector2 GapFromPieces(List<Vector2> nodes, Vector2 gap, IList<GameObject> pieces, float band, out string note)
    {
        float mn = float.MaxValue, mx = float.MinValue; int n = 0;
        foreach (var g in pieces)
        {
            if (g == null) continue;
            foreach (var v in Body(g.transform, 4000))
            {
                var st = ArcOf(nodes, new Vector2(v.x, v.z));
                if (Mathf.Abs(st.y) > band || st.x < gap.x - 2f || st.x > gap.y + 2f) continue;
                mn = Mathf.Min(mn, st.x); mx = Mathf.Max(mx, st.x); n++;
            }
        }
        if (n == 0) { note = "⚠ 石段の駒が線の近くに無い ── 紙の口 [" + gap.x.ToString("F2") + "," + gap.y.ToString("F2") + "] のまま"; return gap; }
        note = "口 [" + gap.x.ToString("F2") + "," + gap.y.ToString("F2") + "] → 石段の実面 [" + mn.ToString("F2") + "," + mx.ToString("F2") + "]";
        return new Vector2(mn, mx);
    }

    /// <summary>**口の端の返し**(EDO-0502 第8巡・スキル unity-modular-stonewall の小口の作法)。土留めの口の端 <paramref name="p"/>(天端の前の縁の上)から、
    /// 口の軸 <paramref name="axis"/>(低い側 → 高い側)に沿って、口の床が天端に届く所まで短い run を引く(天端 = <paramref name="crest"/>・見え面は口の内 <paramref name="inward"/> へ)。
    /// 長さは測って決める: 口の内 0.4m の床(<paramref name="groundAt"/>)が天端に初めて届く所まで(上限 <paramref name="maxLen"/>)。
    /// 返り値 = 天端の前の縁の折れ線(2 点)。床が始めから天端に届いていれば null(返しは要らない)。
    /// 硬い: 口の脇に土の壁を見せない(返しの見え面が口の床まで)。当たる先: 段の土留めの口(石段・坂の切通し)全部。</summary>
    public static List<Vector2> GapReturnLine(Vector2 p, Vector2 axis, Vector2 inward, float crest, Func<float, float, float> groundAt, float maxLen, out float len)
    {
        len = 0f;
        for (float t = 0.25f; t <= maxLen; t += 0.25f)
        {
            Vector2 q = p + axis * t + inward * 0.4f;
            float gy = groundAt(q.x, q.y);
            if (float.IsNaN(gy) || gy >= crest - 0.01f) break;   // 床が天端に届いた(最初に届く所で止める)
            len = t;
        }
        if (len < 0.3f) return null;
        len += 0.25f;
        return new List<Vector2> { p, p + axis * len };
    }

    /// <summary>**野面の駒の見え面の法**(水平 / 鉛直)を駒の実メッシュから測る(2026-10-08 EDO-0502 第57巡)。見え面(局所 +Z)の頂点を
    /// 天端の帯と足の帯で取り、前の縁の差 ÷ 高さの差。⛔ 決め打ちしない(岡部の H4800 は 0.30)。測れなければ NaN。
    /// 当たる先: 法のある駒の見え面を高さごとに線へ合わせる所(<see cref="StairSideCrestLines"/>)。</summary>
    public static float FaceBatterOf(string path)
    {
        var bv = BodyAt(path, Vector3.zero, 0f, true); if (bv == null || bv.Count == 0) return float.NaN;
        float y0 = float.MaxValue, y1 = float.MinValue; foreach (var v in bv) { y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); }
        float h = y1 - y0; if (h < 0.5f) return float.NaN;
        Func<float, float> front = y => { float z = float.MinValue; foreach (var v in bv) if (Mathf.Abs(v.y - y) < h * 0.06f && Mathf.Abs(v.x) < 0.6f) z = Mathf.Max(z, v.z); return z; };
        float ya = y0 + h * 0.15f, yb = y1 - h * 0.1f, za = front(ya), zb = front(yb);
        if (za == float.MinValue || zb == float.MinValue) return float.NaN;
        return (za - zb) / (yb - ya);
    }

    /// <summary>**石段の脇の見え面を石段の端の線へ**(指図 kaidans[].sideFace・2026-10-08 EDO-0502 第57巡 施主指摘「門の内の石段が途中で幅が狭まって見える」)。
    /// 土留めを切って通る石段の両脇の返し(法 1:<paramref name="batter"/> の積み)の**天端の前の縁の線**を、側ごとに解く。見え面は法なので、
    /// 天端の線を石段の端の線(芯から ±<paramref name="halfW"/>・平面で平行な直線)から外へ batter ×(天端 − 足元の面)退けて引けば、
    /// 各段の踏面の高さで見え面が端の線に乗る ── 脇の面は一つ・手前へ出る面なし(第53巡までの返しは天端の線を端の線に引き、
    /// 法の足が下の段ほど段の内へ 0.5〜0.9 出ていた)。足元の面 <paramref name="surf"/> = 走り u(足 <paramref name="foot"/> から上手 <paramref name="up"/> へ)→ 高さ:
    /// 呼び手が据わった段石の天端(踏面の中ほど)と段の外の設計面で渡す(測った値)。折れ線は差が <paramref name="tol"/> 以下の点を間引く。
    /// 始まり = 天端の線の最初の区間を下手へ延ばして本線 <paramref name="wallNodes"/> と交わる点(口の端・出隅)。<paramref name="gapS"/> = 側ごとのその点の本線の道のり。
    /// 硬い(許容0): 各踏面の高さで見え面と端の線の差 ≤ tol × batter(間引きの許し)── 呼び手は据えた後に実測して刷ること。柔らかい: なし。
    /// 当たる先: 法のある土留めを切って通る石段の脇の返し全部(岡部 K_Dan1・K_Dan2・K_Tsuyo。袖を持つ石段は袖が受けるので当てない)。</summary>
    public static List<Vector2>[] StairSideCrestLines(List<Vector2> wallNodes, Vector2 foot, Vector2 up, float halfW, float crest, float batter,
        List<Vector2> surf, float uEnd, float tol, out float[] gapS, out string note)
    {
        gapS = new[] { float.NaN, float.NaN }; note = "";
        var res = new List<Vector2>[2];
        up.Normalize(); Vector2 n = new Vector2(-up.y, up.x);
        var su = new List<Vector2>(surf); su.Sort((p, q) => p.x.CompareTo(q.x));
        if (su.Count < 2) { note = "足元の面の点が足りない"; return res; }
        for (int si = 0; si < 2; si++)
        {
            float sg = si == 0 ? 1f : -1f;
            // u → 天端の線の外への退き(折れ線)。間引き = 一次で結んで差 ≤ tol の中の点を落とす(Douglas–Peucker)
            var off = new List<Vector2>(); foreach (var p in su) if (p.x <= uEnd + 1e-3f) off.Add(new Vector2(p.x, halfW + batter * Mathf.Max(0f, crest - p.y)));
            if (off.Count < 2) continue;
            var keep = new bool[off.Count]; keep[0] = keep[off.Count - 1] = true;
            System.Action<int, int> dp = null;
            dp = (i0, i1) =>
            {
                if (i1 <= i0 + 1) return; int bi = -1; float bd = tol;
                for (int i = i0 + 1; i < i1; i++)
                {
                    float t = (off[i].x - off[i0].x) / Mathf.Max(1e-4f, off[i1].x - off[i0].x);
                    float d = Mathf.Abs(off[i].y - Mathf.Lerp(off[i0].y, off[i1].y, t)); if (d > bd) { bd = d; bi = i; }
                }
                if (bi < 0) return; keep[bi] = true; dp(i0, bi); dp(bi, i1);
            };
            dp(0, off.Count - 1);
            var pl = new List<Vector2>(); for (int i = 0; i < off.Count; i++) if (keep[i]) pl.Add(foot + up * off[i].x + n * (sg * off[i].y));
            // 本線との交点: 天端の線の区間(最初の区間は下手へ 20m 延ばす)と本線の区間の交わり ── 最も下手の物
            Vector2 hit = Vector2.zero; int hitSeg = -1; float hitT = float.MaxValue, hitArc = float.NaN;
            for (int k = 0; k + 1 < pl.Count && hitSeg < 0; k++)
            {
                Vector2 a = pl[k], b = pl[k + 1]; if (k == 0) a = a - (b - a).normalized * 20f;
                float arc = 0f;
                for (int j = 0; j + 1 < wallNodes.Count; j++)
                {
                    Vector2 c = wallNodes[j], d = wallNodes[j + 1]; Vector2 r = b - a, s = d - c; float den = r.x * s.y - r.y * s.x;
                    if (Mathf.Abs(den) > 1e-6f)
                    {
                        Vector2 ca = c - a; float t = (ca.x * s.y - ca.y * s.x) / den, uu = (ca.x * r.y - ca.y * r.x) / den;
                        if (t >= 0f && t <= 1f && uu >= -1e-3f && uu <= 1f + 1e-3f && t < hitT) { hitT = t; hit = a + r * t; hitSeg = k; hitArc = arc + s.magnitude * Mathf.Clamp01(uu); }
                    }
                    arc += (d - c).magnitude;
                }
            }
            if (hitSeg < 0) { note += (si == 0 ? "右" : "左") + ": 天端の線が本線と交わらない "; continue; }
            var line = new List<Vector2> { hit }; for (int k = hitSeg + 1; k < pl.Count; k++) line.Add(pl[k]);
            res[si] = line; gapS[si] = hitArc;
            note += (si == 0 ? "右" : "左") + ": 天端の線 " + line.Count + " 点・本線の s=" + hitArc.ToString("F2") + "・退き " + off[0].y.ToString("F2") + "→" + off[off.Count - 1].y.ToString("F2") + " ";
        }
        return res;
    }

    // ============================================================ 段違いの継ぎ目の下の積み下ろし(EDO-0502 第11巡)
    /// <summary>**段違いの継ぎ目の下を同じ積みの駒で地表まで積み下ろす**(2026-10-04 EDO-0502 第11巡・指図 terraceWalls[].dropJoint)。
    /// 野面の段の境の駒(<see cref="PlaceNozuraRun"/> が段の境に据える勾配の駒・名 <c>*_dan</c>)は丈が一つ(H1.50)しか焼いていないので、
    /// 地盤が走りに沿って下がる袖では継ぎ目の下が抜けて土が見えた(岡部 TW_Kado_Sode_2_0_dan の底 18.32・地表 16.54 ── 抜け 1.423m)。
    /// 硬い(許容0): 継ぎ目の駒の下の抜け 0 ── 駒の外形(足の帯の頂点)と見え面の前 0.3m・走りの両端の先 0.3m の地表
    /// (<paramref name="groundAt"/> = 描かれた地表)の最も低い所へ、駒の底(実メッシュの最下)が届くまで積む。
    /// 積む駒 = **上の駒と同じ駒**(同じ FBX・同じ向きと伸縮 ── 勾配の駒は底も勾配なので、平らな駒を積むと楔の口が開く: 第11巡の初手で 0.35m)。
    /// 届くまで重ね、一番下は地表の下へ埋まる分だけ根入れ(埋めて隠す)。触れる所: 走りを 7 つの筋に割り、
    /// 筋ごとの**上の駒の底 − 積む駒の頭**の最大だけ積む駒を上げる(どの筋にも口を残さない・重なりは埋めて隠す)・
    /// **天端の帯の前の縁 = 上の駒の足の帯の前の縁**(見え面が法なりに続く)・走りの射影の中点どうし(⛔ ピボットで決めない)。
    /// 対象 = 段の境の駒と、それに触れる(外接を 0.3m 広げて重なる)同じ土留めの駒。抜けが無い駒は触らない。
    /// 当たる先: 野面の乱積みの段違いの土留め(岡部 TW_Kado_Sode・山王の野面の段の境・類型の縁の野面 ── 山王と類型は呼んでいない)。
    /// ⟶ 返す: 積んだ駒の数。<paramref name="worstBefore"/>/<paramref name="worstAfter"/> = 継ぎ目の駒の抜けの最悪(積む前・後)。</summary>
    public static int StackDownAtNozuraSteps(IList<KeyValuePair<GameObject, Vector2>> placed, Func<float, float, float> groundAt,
        Transform parent, int maxN, System.Text.StringBuilder log,
        out float worstBefore, out float worstAfter)
    {
        worstBefore = float.NegativeInfinity; worstAfter = float.NegativeInfinity;
        if (placed == null || placed.Count == 0) return 0;
        const float BAND = 0.15f, OUT = 0.3f;
        // 抜け = 駒の底 − 足元の描かれた地表の最低(外形の格子と前・両端の先)
        Func<GameObject, Vector2, float> gapOf = (g, fN) =>
        {
            var vs = Body(g.transform, 999999); if (vs.Count == 0) return float.NaN;
            float bot = float.MaxValue; foreach (var v in vs) bot = Mathf.Min(bot, v.y);
            Vector2 X = new Vector2(fN.y, -fN.x);
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var v in vs) if (v.y <= bot + BAND)
            { var q = new Vector2(v.x, v.z); float a = Vector2.Dot(q, X), b = Vector2.Dot(q, fN); x0 = Mathf.Min(x0, a); x1 = Mathf.Max(x1, a); z0 = Mathf.Min(z0, b); z1 = Mathf.Max(z1, b); }
            if (x0 == float.MaxValue) return float.NaN;
            x0 -= OUT; x1 += OUT; z1 += OUT;
            float gmin = float.NaN;
            for (int i = 0; i <= 6; i++) for (int j = 0; j <= 4; j++)
            {
                float a = Mathf.Lerp(x0, x1, i / 6f), b = Mathf.Lerp(z0, z1, j / 4f);
                Vector2 p = X * a + fN * b; float gy = groundAt(p.x, p.y);
                if (!float.IsNaN(gy) && (float.IsNaN(gmin) || gy < gmin)) gmin = gy;
            }
            return float.IsNaN(gmin) ? float.NaN : bot - gmin;
        };
        Func<GameObject, float> crestBand = g =>
        {
            var cells = new Dictionary<long, float>();
            foreach (var v in Body(g.transform, 999999))
            { long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
              float y; if (!cells.TryGetValue(key, out y) || v.y > y) cells[key] = v.y; }
            var ys = new List<float>(cells.Values); ys.Sort(); if (ys.Count == 0) return float.NaN;
            int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); return top[top.Count / 2];
        };
        // 対象: 段の境の駒と、それに触れる駒
        var targets = new List<KeyValuePair<GameObject, Vector2>>();
        foreach (var kv in placed)
        {
            if (kv.Key == null || !kv.Key.name.EndsWith("_dan")) continue;
            if (!targets.Exists(t => t.Key == kv.Key)) targets.Add(kv);
            var db = RB(kv.Key); db.Expand(new Vector3(0.3f, 0f, 0.3f));
            string run = System.Text.RegularExpressions.Regex.Match(kv.Key.name, @"^(.*?)_\d").Groups[1].Value;   // 同じ土留め(名の頭)
            foreach (var o in placed)
            {
                if (o.Key == null || o.Key == kv.Key || targets.Exists(t => t.Key == o.Key) || !o.Key.name.StartsWith(run + "_")) continue;
                var ob = RB(o.Key);
                if (ob.min.x <= db.max.x && ob.max.x >= db.min.x && ob.min.z <= db.max.z && ob.max.z >= db.min.z) targets.Add(o);
            }
        }
        int n = 0;
        foreach (var kv in targets)
        {
            var top = kv.Key; Vector2 fN = kv.Value; if (fN == Vector2.zero) continue;
            Vector2 X = new Vector2(fN.y, -fN.x);
            float gap = gapOf(top, fN);
            if (float.IsNaN(gap)) continue;
            worstBefore = Mathf.Max(worstBefore, gap);
            var cur = top; int k = 0;
            while (gap > 0.005f && k < maxN)
            {
                var srcObj = UnityEditor.PrefabUtility.GetCorrespondingObjectFromOriginalSource(top);
                string path = srcObj != null ? UnityEditor.AssetDatabase.GetAssetPath(srcObj) : null;
                if (string.IsNullOrEmpty(path)) { log.AppendLine("    ⛔ " + top.name + ": 駒の資産が引けない ── 抜け " + gap.ToString("F3") + "m のまま"); break; }
                var cb = RB(cur);
                var go = Place(path, new Vector3(cur.transform.position.x, cur.transform.position.y - cb.size.y, cur.transform.position.z), cur.transform.eulerAngles.y,
                               cur.transform.localScale, parent, top.name + "_tsumi" + k);
                if (go == null) break;
                var uvs = Body(cur.transform, 999999); var gvs = Body(go.transform, 999999);
                float ubot = float.MaxValue; foreach (var v in uvs) ubot = Mathf.Min(ubot, v.y);
                float gtop = float.MinValue; foreach (var v in gvs) gtop = Mathf.Max(gtop, v.y);
                // 前の縁(上の駒の足の帯 / 積む駒の頭の帯)と走りの射影の中点
                float uf = float.MinValue, gf = float.MinValue, ua0 = float.MaxValue, ua1 = float.MinValue, ga0 = float.MaxValue, ga1 = float.MinValue;
                foreach (var v in uvs) { var q = new Vector2(v.x, v.z); if (v.y <= ubot + BAND) uf = Mathf.Max(uf, Vector2.Dot(q, fN)); float a = Vector2.Dot(q, X); ua0 = Mathf.Min(ua0, a); ua1 = Mathf.Max(ua1, a); }
                foreach (var v in gvs) { var q = new Vector2(v.x, v.z); if (v.y >= gtop - BAND) gf = Mathf.Max(gf, Vector2.Dot(q, fN)); float a = Vector2.Dot(q, X); ga0 = Mathf.Min(ga0, a); ga1 = Mathf.Max(ga1, a); }
                Vector2 sh = fN * (uf - gf) + X * (0.5f * (ua0 + ua1) - 0.5f * (ga0 + ga1));
                go.transform.position += new Vector3(sh.x, 0f, sh.y);
                // 高さ: 筋ごとに「上の駒の底 − 積む駒の頭」を**同じ柱(0.1m の升)で**測った最小(= その筋の触れる所の隙)の、筋の最大だけ上げる
                //   (どの筋にも口を残さない・ほかの筋の重なりは埋めて隠す)。
                // ⭐ 2026-10-07 第47巡: 筋の中の底の最小と頭の最大を別々の所で取って引くと、どの柱の隙よりも小さい値になり、
                //    全部の筋で上の駒が浮いた(岡部 縁 Curb_R_UraZaka_0_004f が下の積み 004f_tsumi0 から +0.013・9 点)。⛔ 筋の最小と最大を引かない。
                gvs = Body(go.transform, 999999);
                const int NB = 7; const float CELL = 0.1f;
                var uCol = new Dictionary<long, float>(); var gCol = new Dictionary<long, float>(); var colBin = new Dictionary<long, int>();
                Func<Vector3, long> colOf = v => { var q = new Vector2(v.x, v.z); return ((long)Mathf.FloorToInt(Vector2.Dot(q, X) / CELL) << 32) ^ (uint)Mathf.FloorToInt(Vector2.Dot(q, fN) / CELL); };
                Func<Vector3, int> bin = v => Mathf.Clamp((int)((Vector2.Dot(new Vector2(v.x, v.z), X) - ua0) / Mathf.Max(1e-4f, ua1 - ua0) * NB), 0, NB - 1);
                foreach (var v in uvs) { long c = colOf(v); float y; if (!uCol.TryGetValue(c, out y) || v.y < y) uCol[c] = v.y; colBin[c] = bin(v); }
                foreach (var v in gvs) { long c = colOf(v); float y; if (!gCol.TryGetValue(c, out y) || v.y > y) gCol[c] = v.y; }
                var binGap = new float[NB]; for (int b = 0; b < NB; b++) binGap[b] = float.MaxValue;
                foreach (var kc in uCol) { float gy; if (!gCol.TryGetValue(kc.Key, out gy)) continue; int b = colBin[kc.Key]; binGap[b] = Mathf.Min(binGap[b], kc.Value - gy); }
                float lift = float.NegativeInfinity;
                for (int b = 0; b < NB; b++) if (binGap[b] < float.MaxValue) lift = Mathf.Max(lift, binGap[b]);
                if (float.IsNegativeInfinity(lift))
                {   // 同じ柱が一つも無い(駒が細い)── 筋の底の最小と頭の最大で(従前)
                    var ulo = new float[NB]; var ghi = new float[NB];
                    for (int b = 0; b < NB; b++) { ulo[b] = float.MaxValue; ghi[b] = float.MinValue; }
                    foreach (var v in uvs) { int b = bin(v); ulo[b] = Mathf.Min(ulo[b], v.y); }
                    foreach (var v in gvs) { int b = bin(v); ghi[b] = Mathf.Max(ghi[b], v.y); }
                    for (int b = 0; b < NB; b++) if (ulo[b] < float.MaxValue && ghi[b] > float.MinValue) lift = Mathf.Max(lift, ulo[b] - ghi[b]);
                }
                if (!float.IsNegativeInfinity(lift)) go.transform.position += Vector3.up * lift;
                n++; k++; cur = go;
                gap = gapOf(cur, fN);
                log.AppendLine("    積み下ろし " + top.name + " ← " + System.IO.Path.GetFileNameWithoutExtension(path) + "(頭を上の駒の底へ +" + (float.IsNegativeInfinity(lift) ? 0f : lift).ToString("0.000") + "・底 " + RB(go).min.y.ToString("F2") + "・抜け " + (float.IsNaN(gap) ? "-" : gap.ToString("+0.000;-0.000")) + "m)");
            }
            if (!float.IsNaN(gap)) worstAfter = Mathf.Max(worstAfter, gap);
            if (gap > 0.005f) log.AppendLine("    ⛔ " + top.name + ": " + maxN + " 段積んでも抜け " + gap.ToString("F3") + "m");
        }
        return n;
    }

    /// <summary>**段の土留めの線の先が棟の背へ入り込むなら、背から <paramref name="off"/> 離して背と平行に返し、高い側の妻の線で背まで閉じる**
    /// (2026-10-05・EDO-0502 第19巡 岡部 TW_Kado_Hokuto.end / returnN39_1 ── 門の内の土が石垣の端を回り N39_1 の背へ山になって崩れていた)。
    /// <paramref name="backStop"/>・<paramref name="backFar"/> = 棟の背の面の足元の線の両端(実メッシュで測った物)。stop = 土を受ける側の妻(高い側)。
    /// <paramref name="yard"/> = 背から庭(区画の内)への単位の向き。線を始まりから辿り、背から off の帯へ最初に入る点 X で切って
    /// X → 帯の縁の stop 側の端 → 背の線の stop の点、と継ぐ(途中に土の口なし)。
    /// <para>硬い: 背から off の内に石垣を立てない・返しの端は背の線で止める。柔らかい: off(一間)。
    /// 帯へ入らない(背の端の外で終わる・背に届かない)なら null ── 返しは要らない。</para>
    /// <para>返り値 = 新しい節点(始まりの側の節点はそのまま ⇒ 口の道のり s は変わらない)。
    /// <paramref name="trenchFar"/> = 背の線の上で、溝(返しと背の間)の stop の反対の端(X の射影)。</para>
    /// 当たる先: 段の土留めの線が長屋・棟の背に当たる所(岡部 TW_Kado_Hokuto × N39_1)。</summary>
    public static List<Vector2> ReturnAlongBack(List<Vector2> nodes, Vector2 backStop, Vector2 backFar, Vector2 yard, float off,
                                                out Vector2 trenchFar, out string note)
    {
        trenchFar = backStop; note = null;
        if (nodes == null || nodes.Count < 2) { note = "節点が無い"; return null; }
        yard = yard.normalized;
        Vector2 u = backFar - backStop; float Lb = u.magnitude; if (Lb < 1e-3f) { note = "背の線が無い"; return null; }
        u /= Lb;
        Vector2 P0 = backStop + yard * off;
        for (int i = 0; i + 1 < nodes.Count; i++)
        {
            Vector2 p = nodes[i], q = nodes[i + 1];
            float fp = Vector2.Dot(p - P0, yard), fq = Vector2.Dot(q - P0, yard);
            if (!(fp > 0f && fq <= 0f)) continue;
            float t = fp / (fp - fq); Vector2 X = Vector2.Lerp(p, q, t);
            float sx = Vector2.Dot(X - P0, u);
            if (sx < 0f || sx > Lb + off) continue;                    // 背の端の外を通る ── この棟の背ではない
            var res = new List<Vector2>();
            for (int k = 0; k <= i; k++) res.Add(nodes[k]);
            res.Add(X); res.Add(P0); res.Add(backStop);
            trenchFar = backStop + u * sx;
            note = "背から " + off.ToString("F3") + "m で返した: 交点 (" + X.x.ToString("F2") + "," + X.y.ToString("F2") + ")・返しの長さ " + sx.ToString("F2")
                 + "m・妻の線の閉じ " + off.ToString("F2") + "m(元の線の残り " + (Vector2.Distance(X, q) + SumLen(nodes, i + 1)).ToString("F2") + "m を外した)";
            return res;
        }
        note = "線が背から " + off.ToString("F2") + "m の帯へ入らない ── 返し要らない";
        return null;
    }

    static float SumLen(List<Vector2> nodes, int from)
    { float s = 0f; for (int k = from; k + 1 < nodes.Count; k++) s += Vector2.Distance(nodes[k], nodes[k + 1]); return s; }
}
