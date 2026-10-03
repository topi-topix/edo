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
                    var go = Place(path, new Vector3(mid.x, crest, mid.y), psi, Vector3.one, parent, w.name + "_" + q + "_" + ci + "_" + i.ToString("00"));
                    if (go == null) continue;
                    // 見え面を低い側へ・天端の前の縁を線へ(実メッシュ)
                    FaceWallToLine(go, lowN, a);
                    // 走りの端を区間の割りの端へ(実メッシュの射影)
                    var vs = Body(go.transform, 999999);
                    float mn = float.MaxValue, top = float.MinValue, bot = float.MaxValue;
                    foreach (var v in vs) { float s = Vector2.Dot(new Vector2(v.x, v.z) - a, dir); mn = Mathf.Min(mn, s); top = Mathf.Max(top, v.y); bot = Mathf.Min(bot, v.y); }
                    go.transform.position += new Vector3(dir.x, 0f, dir.y) * (t - mn) + Vector3.up * (crest - top);
                    bot += crest - top;
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
                    int m = Mathf.FloorToInt(L / pw + 1e-3f); if (m < 1) continue;
                    float target = Vector2.Dot(lo, ux) + (L - m * pw) * 0.5f;
                    Vector2 runU = (hi - lo).normalized;
                    GameObject last = null;
                    for (int i = 0; i < m; i++)
                    {
                        Vector2 p = lo + runU * ((L - m * pw) * 0.5f + pw * (i + 0.5f));
                        var go = Place(span, new Vector3(p.x, 0f, p.y), psi, Vector3.one, parent, prefix + "_" + k + "_" + n.ToString("000"));
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
                }
                s0 += len;
            }
        }
        worstFloat = float.IsNegativeInfinity(worst) ? float.NaN : worst;
        if (n > 0) note += "線 = 天端の前の縁から " + setback.ToString("F2") + "m";
        return n;
    }

    /// <summary>垣の駒の足(走りの両端と中ほど・局所 +X の向き <paramref name="ux"/> の実メッシュの範囲)の真下の当たり =
    /// 土留めの駒の上向きの面(<see cref="BedTopAt"/>)と描かれた地表の高い方、を測り、**最も高い当たり**へ床(底 + 根入れ 0.15)を据える。
    /// <paramref name="spread"/> = 最も高い当たり − 最も低い当たり(その分だけ床の下が空く所がある ── 根入れ 0.15 の内なら見えない)。</summary>
    static bool SeatFenceOnBeds(GameObject go, Vector2 ux, IList<GameObject> beds, out float spread)
    {
        spread = float.NaN;
        float mn = float.MaxValue, mx = float.MinValue, bot = float.MaxValue, top = float.MinValue; Vector2 c = Vector2.zero; int nv = 0;
        foreach (var v in Body(go.transform, 4000)) { float u = Vector2.Dot(new Vector2(v.x, v.z), ux); mn = Mathf.Min(mn, u); mx = Mathf.Max(mx, u); bot = Mathf.Min(bot, v.y); top = Mathf.Max(top, v.y); c += new Vector2(v.x, v.z); nv++; }
        if (nv == 0) return false; c /= nv;
        float cu = Vector2.Dot(c, ux);
        float hi = float.MinValue, lo = float.MaxValue;
        foreach (float u in new[] { mn + 0.03f, (mn + mx) * 0.5f, mx - 0.03f })
        {
            Vector2 p = c + ux * (u - cu);
            float g = Ground(p.x, p.y), b = BedTopAt(p, beds, g + 6f);   // 光線は 8m まで ⇒ 地表の 6m 上から(⛔ 据える前の駒の頭からでは天端に届かない)
            float y = float.IsNaN(b) ? g : Mathf.Max(b, g);
            if (float.IsNaN(y)) continue;
            hi = Mathf.Max(hi, y); lo = Mathf.Min(lo, y);
        }
        if (hi == float.MinValue) return false;
        go.transform.position += Vector3.up * (hi - 0.15f - bot);
        spread = hi - lo;
        return true;
    }

    /// <summary>**段石の下を同じ段石で接地まで積む**(雁木の積み・2026-10-03 EDO-0502 第4巡 岡部 K_Kuruwa: 石垣の口から下の面へ
    /// 張り出す石段の段石が下の面から最大 1.49m 浮いた)。硬い: 浮き 0 ── 一番下の駒が地面に触れる(<see cref="Contact"/> ≤ 0)まで積む。
    /// 触れる所: 積む駒の**上面 = 上の駒の底**(実メッシュの RB で測る・⛔ ピボットで決めない)。位置と向きは上の駒と同じ(xz・yaw)。
    /// 一番下の駒は地面へ埋まる分だけ根入れ(埋めて隠す)。<paramref name="maxN"/> 段を積んでも届かなければ ⚠ を <paramref name="warn"/> へ。
    /// 当たる先: 下の面へ張り出す石段(指図 kaidans[] で、足元の面の外まで段が出る物)。全邸の石段の据え(PlaceKaidanAB)が呼べる。
    /// ⟶ 返す: 積んだ駒の数</summary>
    public static int StackDownToGround(GameObject top, string path, Transform parent, string name, int maxN, List<string> warn)
    {
        if (top == null) return 0;
        int n = 0; var cur = top; Vector3 at; int cnt;
        float gap = Contact(cur, out at, out cnt);
        while (!float.IsNaN(gap) && gap > 0.005f && n < maxN)
        {
            var b = RB(cur);
            var go = Place(path, new Vector3(cur.transform.position.x, b.min.y, cur.transform.position.z), cur.transform.eulerAngles.y,
                           cur.transform.localScale, parent, name + "_tsumi" + n);
            if (go == null) break;
            var nb = RB(go);
            go.transform.position += new Vector3(b.center.x - nb.center.x, b.min.y - nb.max.y, b.center.z - nb.center.z);
            n++; cur = go;
            gap = Contact(cur, out at, out cnt);
        }
        if (!float.IsNaN(gap) && gap > 0.005f && warn != null)
            warn.Add("段石 " + top.name + ": " + maxN + " 段積んでも地面まで " + gap.ToString("F2") + "m 届かない");
        return n;
    }
}
