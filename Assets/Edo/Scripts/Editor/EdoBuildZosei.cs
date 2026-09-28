// EdoBuild — 造成(平場を採る)。2026-09-27・EDO-0477 P1(山王 Stage1_Grade と松江松平 DesignY の型を、図を持たない区画へ)。
//
// ⭐ 面の高さは地形が決める(CLAUDE.md 規則3・9)。棟の足あとの下の**造成前の地盤**(base_dem・規則13)の中央値を
//    その棟の平場の高さに採り、足あとの外は法面で地山へ擦り付ける。法は一枚の土の面(施主の規則: 盛土 1:1.5・切土 1:1.0)。
// ⭐ 造成は**区画の外へ出さない**(施主の規則)。区画の縁で地山に戻るよう、縁からの距離でも法を縛る ──
//    縁に近すぎて平場が平らに取れない棟は ⚠(柔らかい条件: 最も近い姿で建てて刷る・PlaceBest と同じ作法)。
// ⭐ 冪等: 毎回、区画の中の節点を造成前の地盤へ戻してから平場を起こす(松江松平 LoadNatural・山王 Stage1_Grade(prev) の型)。
//    二度流しても同じ面になる。⛔ live terrain を「造成前」として読まない(規則13 ── 自他の造成が焼き込まれる)。
// ⚠ 造成の後で、据えた駒は全部据え直す(施主の規則)── 呼び手の務め。
// 当たる先: 類型ビルダーで建てる全区画(武家・寺社・町屋・公有地)。図から起こした邸は自前の造成を持つので呼ばない。

using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

public static partial class EdoBuild
{
    static Func<float, float, float> _baseDem;

    /// <summary>区画の縁に沿って地山のまま残す幅[m] = 塀の足元(厚み 0.4〜0.6)+ 犬走り。【確度 U】一般類型。
    /// 当たる先: 区画の線の上に立つ全ての囲い(塀・長屋)。</summary>
    public const float EDGE_BERM = 1.0f;

    /// <summary>造成前の地盤(`docs/Sashizu/base_dem.json`・2m 格子の双一次)。範囲外・欠けは NaN。</summary>
    public static Func<float, float, float> BaseDem()
    {
        if (_baseDem != null) return _baseDem;
        string path = Path.Combine(Path.GetDirectoryName(Application.dataPath), "docs/Sashizu/base_dem.json");
        var dem = EdoMiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
        float x0 = Convert.ToSingle(dem["x0"]), z0 = Convert.ToSingle(dem["z0"]), st = Convert.ToSingle(dem["step"]);
        var rows = dem["h"] as List<object>;
        int nz = rows.Count, nx = (rows[0] as List<object>).Count;
        var H = new float[nz, nx];
        for (int j = 0; j < nz; j++)
        {
            var r = rows[j] as List<object>;
            for (int i = 0; i < nx; i++) H[j, i] = (r == null || i >= r.Count || r[i] == null) ? float.NaN : Convert.ToSingle(r[i]);
        }
        _baseDem = (x, z) =>
        {
            float fi = (x - x0) / st, fj = (z - z0) / st;
            int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj);
            if (i < 0 || j < 0 || i + 1 >= nx || j + 1 >= nz) return float.NaN;
            float tx = fi - i, tz = fj - j;
            return Mathf.Lerp(Mathf.Lerp(H[j, i], H[j, i + 1], tx), Mathf.Lerp(H[j + 1, i], H[j + 1, i + 1], tx), tz);
        };
        return _baseDem;
    }

    /// <summary>平場の結果(棟ごと)。</summary>
    public class Hiraba
    {
        public float y;          // 平場の高さ(足あとの下の造成前の地盤の中央値)
        public float relief;     // 足あとの下の地盤の起伏(最大 − 最小)
        public int squeezed;     // 区画の縁の法の縛りで、平らに取れなかった足あとの節点
    }

    /// <summary>**棟の足あとごとに平場を採り、法面で地山へ擦り付ける。**<paramref name="pads"/> は棟の壁体の足あと
    /// (世界 xz の多角形。呼び手が実メッシュから測る)。<paramref name="margin"/> は足あとの外へ平らに取る幅(犬走り・雨落ち)。
    /// 返りは棟ごとの平場の高さ。区画の中の節点だけを書き、区画の外(道・隣)は触らない。
    /// <para>節点の高さ = 造成前の地盤 b を、最寄りの平場 p(高さ)からの距離 d で [p − d/盛土の法, p + d/切土の法] に挟む
    /// (地盤が低ければ盛土の法 1:1.5 で、高ければ切土の法 1:1.0 で平場へ擦り付く)。さらに区画の縁からの距離 e で
    /// [b − e/切土の法, b + e/盛土の法] に挟み、縁で地山へ戻す(区画の外へ造成を出さない)。</para></summary>
    public static List<Hiraba> GradePads(Vector2[] parcel, IList<Vector2[]> pads, float margin, out string report,
                                         float fillRun = 1.5f, float cutRun = 1.0f)
    {
        var outp = new List<Hiraba>();
        var dem = BaseDem();
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in parcel) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int w = i1 - i0 + 1, h = j1 - j0 + 1;
        var H = td.GetHeights(i0, j0, w, h);
        // ⭐ 平らに取る幅は**格子の対角以上**(2026-09-28 EDO-0477 実測)。地表は節点の間を双一次で結ぶので、足あとの縁に
        //    掛かる格子の 4 節点が全部平場でないと、縁の下で面が傾く ── 格子 2.0m に幅 1.0m では観理院の客殿の下端が
        //    0.17m 浮き 0.16m 埋まった。当たる先: GradePads を呼ぶ全区画(類型の全区画)。
        float cell = Mathf.Max(ts.x, ts.z) / (res - 1);
        margin = Mathf.Max(margin, cell * 1.415f);

        // 1. 平場の高さ = 足あと(+margin)の下の造成前の地盤の中央値
        foreach (var pad in pads)
        {
            var ys = new List<float>();
            float lo = float.MaxValue, hi = float.MinValue;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < w; i++)
                {
                    var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                    if (!EdoGeom.PIP(pad, q)) continue;
                    float b = dem(q.x, q.y); if (float.IsNaN(b)) b = H[j, i] * ts.y + tp.y;
                    ys.Add(b); lo = Mathf.Min(lo, b); hi = Mathf.Max(hi, b);
                }
            var hb = new Hiraba();
            if (ys.Count == 0) { var c = Centroid(pad); float b = dem(c.x, c.y); hb.y = float.IsNaN(b) ? Ground(c.x, c.y) : b; }
            else { ys.Sort(); hb.y = ys[ys.Count / 2]; hb.relief = hi - lo; }
            outp.Add(hb);
        }

        // 1b. 近い棟の平場を一つの高さに束ねる(2026-09-28 EDO-0477 実測)。⛔ 棟ごとに中央値を採ると、縁取りが触れ合う
        //    隣の平場と数cm違い、あいだの格子が傾いて下端が浮く(観理院の客殿 0.024m・鐘楼 0.038m)。足あとの間が
        //    縁取り 2 つぶんより近く、高さの差が PAD_MERGE_DY より小さい棟は、束の中で最も広い棟の高さへそろえる。
        //    差が大きい棟は束ねない(段として残す ── 規則3 の系統差 ±0.25 を超える均しをしない)。当たる先: 類型の全区画。
        int n = pads.Count; var grp = new int[n]; for (int k = 0; k < n; k++) grp[k] = k;
        Func<int, int> root = null; root = k => grp[k] == k ? k : (grp[k] = root(grp[k]));
        for (int a = 0; a < n; a++)
            for (int b2 = a + 1; b2 < n; b2++)
            {
                if (Mathf.Abs(outp[a].y - outp[b2].y) >= PAD_MERGE_DY) continue;
                if (PolyGap(pads[a], pads[b2]) >= 2f * margin) continue;
                grp[root(a)] = root(b2);
            }
        var areas = new float[n]; for (int k = 0; k < n; k++) areas[k] = Mathf.Abs(PolyArea(pads[k]));
        var lead = new Dictionary<int, int>();
        for (int k = 0; k < n; k++) { int r = root(k); if (!lead.ContainsKey(r) || areas[k] > areas[lead[r]]) lead[r] = k; }
        int merged = 0;
        for (int k = 0; k < n; k++) { int l = lead[root(k)]; if (l != k) { outp[k].y = outp[l].y; merged++; } }

        // 2. 区画の中の節点: 造成前の地盤へ戻し、最寄りの平場の法で挟み、縁の法で地山へ戻す
        int written = 0; float maxCut = 0f, maxFill = 0f;
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                if (!EdoGeom.PIP(parcel, q)) continue;
                float b = dem(q.x, q.y);
                if (float.IsNaN(b)) continue;                                 // 正典の地盤が無い所は触らない
                float y = b;
                // 最寄りの平場(足あとの外へ margin まで平ら)
                // ⭐ 平場は**足あとへの素の距離**が最も近い棟の物を採る(2026-09-28)。⛔ 縁取り(margin)を引いた後の距離で
                //    比べると、二棟の縁取りが重なる所で 0 が並び、先に見つかった棟の高さが隣の足あとの縁へ食い込んだ
                //    (観理院の物置 0.17m・蔵 0.09m の浮き)。
                int best = -1; float bd = float.MaxValue, braw = float.MaxValue;
                for (int k = 0; k < pads.Count; k++)
                {
                    float d = EdoGeom.PIP(pads[k], q) ? 0f : EdoGeom.DistToPolyEdge(pads[k], q);
                    if (d < braw) { braw = d; best = k; }
                }
                if (best >= 0) bd = Mathf.Max(0f, braw - margin);
                if (best >= 0)
                {
                    float p = outp[best].y;
                    y = Mathf.Clamp(b, p - bd / fillRun, p + bd / cutRun);   // 地盤が低ければ盛土の法、高ければ切土の法で平場へ
                }
                // 縁で地山へ戻す(区画の外へ出さない)。⭐ 縁から EDGE_BERM までは地山のまま残し、法はその内から起こす
                //    (2026-09-28 EDO-0477 実測: 縁から法を起こすと、区画の線の上に立つ塀の足元の内側が削られ、
                //    塀の厚み 0.42m のあいだで地面が 0.8m 落ちて塀の下端が浮いた ── 観理院 49/199 駒・最悪 0.76m)。
                float e = Mathf.Max(0f, EdoGeom.DistToPolyEdge(parcel, q) - EDGE_BERM);
                float y2 = Mathf.Clamp(y, b - e / cutRun, b + e / fillRun);
                if (best >= 0 && bd <= 0f && Mathf.Abs(y2 - y) > 0.01f) outp[best].squeezed++;
                y = y2;
                if (y < b) maxCut = Mathf.Max(maxCut, b - y); else maxFill = Mathf.Max(maxFill, y - b);
                H[j, i] = Mathf.Clamp01((y - tp.y) / ts.y);
                written++;
            }
        td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        int sq = 0; foreach (var hb in outp) sq += hb.squeezed;
        report = string.Format("造成: 平場 {0} 面(うち隣へ束ねた {5})・節点 {1}(区画の中だけ・毎回造成前の地盤から)・最大の切土 {2:F2}m・盛土 {3:F2}m{4}",
                               pads.Count, written, maxCut, maxFill,
                               sq > 0 ? string.Format(" ⚠ 区画の縁に近く平らに取れない節点 {0}(土留めが要る所・P3)", sq) : "", merged);
        return outp;
    }

    /// <summary>**この足あとに平場が取れるか**を置く前に測る(2026-09-28 EDO-0477)。<see cref="GradePads"/> と同じ格子・同じ法で、
    /// 足あと(+縁取り)の節点のうち、区画の縁の法に縛られて平場の高さまで切り盛りできない物を数える(0 なら取れる)。
    /// 硬い制約として <see cref="PlaceBest"/> へ渡す ── 取れない所に建てると下端が浮き・埋まる(観理院の本堂 浮き 1.72m・埋まり 0.92m、
    /// 区画の北の角から 2.7m で 27 節点)。当たる先: 造成して建てる類型の全棟(寺社の本堂・附属、武家の御殿・長屋以外の棟)。</summary>
    public static int PadSqueeze(Vector2[] parcel, Vector2[] foot, float margin, float fillRun = 1.5f, float cutRun = 1.0f)
    {
        var dem = BaseDem();
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = Mathf.Max(ts.x, ts.z) / (res - 1);
        margin = Mathf.Max(margin, cell * 1.415f);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in foot) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.FloorToInt((mnx - margin - tp.x) / ts.x * (res - 1)), i1 = Mathf.CeilToInt((mxx + margin - tp.x) / ts.x * (res - 1));
        int j0 = Mathf.FloorToInt((mnz - margin - tp.z) / ts.z * (res - 1)), j1 = Mathf.CeilToInt((mxz + margin - tp.z) / ts.z * (res - 1));
        var ys = new List<float>(); var ring = new List<Vector3>();
        for (int j = j0; j <= j1; j++)
            for (int i = i0; i <= i1; i++)
            {
                var q = NodeXZ(tp, ts, res, i, j);
                float b = dem(q.x, q.y); if (float.IsNaN(b)) continue;
                bool inside = EdoGeom.PIP(foot, q);
                if (inside) ys.Add(b);
                if (inside || EdoGeom.DistToPolyEdge(foot, q) <= margin) ring.Add(new Vector3(q.x, b, q.y));
            }
        if (ys.Count == 0) return 0;
        ys.Sort(); float pad = ys[ys.Count / 2];
        int n = 0;
        foreach (var r in ring)
        {
            var q = new Vector2(r.x, r.z);
            // 区画の外の節点は触らない(地山のまま)= e 0 ── 地山が平場の高さに揃っていれば取れる
            float e = EdoGeom.PIP(parcel, q) ? Mathf.Max(0f, EdoGeom.DistToPolyEdge(parcel, q) - EDGE_BERM) : 0f;
            if (pad - r.y > e / fillRun + 0.01f || r.y - pad > e / cutRun + 0.01f) n++;
        }
        return n;
    }

    /// <summary>隣の平場と束ねる高さの差の上限。【確度 U】── 棟ごとの系統差 ±0.25(規則3)をまたがない幅。</summary>
    public const float PAD_MERGE_DY = 0.30f;

    static float PolyArea(Vector2[] p)
    {
        float s = 0f; for (int i = 0; i < p.Length; i++) { var a = p[i]; var b = p[(i + 1) % p.Length]; s += a.x * b.y - b.x * a.y; }
        return 0.5f * s;
    }

    /// <summary>二つの多角形の縁どうしの最短距離(頂点↔相手の辺で近似。重なれば 0)。</summary>
    static float PolyGap(Vector2[] a, Vector2[] b)
    {
        float d = float.MaxValue;
        foreach (var q in a) { if (EdoGeom.PIP(b, q)) return 0f; d = Mathf.Min(d, EdoGeom.DistToPolyEdge(b, q)); }
        foreach (var q in b) { if (EdoGeom.PIP(a, q)) return 0f; d = Mathf.Min(d, EdoGeom.DistToPolyEdge(a, q)); }
        return d;
    }

    /// <summary>崖とみなす横断勾配(高さ/水平)。1:1.4(約 35°)より急なら崖。【確度 U】── 盛土の法 1:1.5 より急な地山は人が土で保てない。</summary>
    public const float CLIFF_SLOPE = 0.7f;

    /// <summary>崖と数える続きの最短[m]。これより短い急な所は塀の駒(2m)で跨ぐ段差として囲う。【確度 U】</summary>
    public const float CLIFF_MIN_RUN = 1.0f;

    /// <summary>**辺のうち塀が立てる区間**(2026-09-28・EDO-0477。施主の規則「崖の線は面の縁だけ囲う・崖の中腹に塀を建てない」)。
    /// 辺 a→b に沿って 0.25m ごとに、**今の地面**(造成の後)で塀の足あとの下を読み、崖に掛かる所を外して、
    /// 残る区間を [t0, t1](a からの距離)で返す。<paramref name="minSpan"/> より短い区間は捨てる。崖とみなすのは:
    /// ① 線に沿って ±0.5m の勾配が CLIFF_SLOPE より急(塀が崖を登る)② 線から内へ 0.5m の勾配が CLIFF_SLOPE より急(塀の内の半分が崖の面に掛かる)。
    /// ⭐ 線の外が高いだけの所(崖の裾・施主裁定X で線を寄せた所)は囲う ── 外の半分は崖の裾へ埋めて据える(根入れが基本・§0a)。
    /// ⛔ 2026-09-28 までは造成前の地盤で線の内外 ±1m の差を見ていて、造成で平らになった崖の裾まで崖と数え、
    /// 観理院 辺4 の頭 6m(うち平ら 3m)を素通しにした(EDO-0468 の検査・人が通れる口)。
    /// 当たる先: 類型の全区画の囲い(塀・柵の種別)。長屋の囲いは棟なので別に扱う(未)。</summary>
    public static List<float[]> CliffFreeSpans(Vector2 a, Vector2 b, Vector2 outward, float minSpan, out float cliffLen)
    {
        var outp = new List<float[]>(); cliffLen = 0f;
        float L = (b - a).magnitude; if (L < 1e-3f) return outp;
        var d = (b - a) / L; var inN = -outward.normalized;
        // ⭐ 刻み 0.25m・区間は**最後の崖でない標本**で終える(⛔ 崖と判じた標本で終えると最後の駒が崖へ登った ── 観理院 辺4 の下端 8.15)
        const float STEP = 0.25f;
        var ts = new List<float>(); var cl = new List<bool>();
        for (float s = 0f; s <= L + 1e-3f; s += STEP)
        {
            float t = Mathf.Min(s, L); var p = a + d * t;
            var p0 = a + d * Mathf.Max(0f, t - 0.5f); var p1 = a + d * Mathf.Min(L, t + 0.5f);
            float g = Ground(p.x, p.y), gi = Ground(p.x + inN.x * 0.5f, p.y + inN.y * 0.5f);
            float g0 = Ground(p0.x, p0.y), g1 = Ground(p1.x, p1.y);
            ts.Add(t);
            cl.Add(!float.IsNaN(g) && !float.IsNaN(gi) && !float.IsNaN(g0) && !float.IsNaN(g1)
                   && (Mathf.Abs(g1 - g0) / Mathf.Max(0.01f, (p1 - p0).magnitude) > CLIFF_SLOPE
                       || Mathf.Abs(g - gi) / 0.5f > CLIFF_SLOPE));
        }
        // ⭐ 崖の続きが CLIFF_MIN_RUN より短い所は崖と数えない ── 塀の駒 1 つで跨げる段差で、地盤の格子(2m)の角の段が崖と出る。
        //    ⛔ 2026-09-28 まで角の 0.75m が崖と出て区間が角から始まらず、角の延ばしが効かずに口が残った(観理院 v4 0.07m・EDO-0477)。
        for (int i = 0; i < cl.Count;)
        {
            if (!cl[i]) { i++; continue; }
            int j = i; while (j < cl.Count && cl[j]) j++;
            if ((j - i) * STEP < CLIFF_MIN_RUN) for (int k = i; k < j; k++) cl[k] = false;
            i = j;
        }
        float start = 0f, lastOk = 0f; bool open = true;
        for (int i = 0; i < ts.Count; i++)
        {
            float t = ts[i]; bool cliff = cl[i];
            if (cliff) cliffLen += STEP;
            if (cliff && open) { if (lastOk - start >= minSpan) outp.Add(new[] { start, lastOk }); open = false; }
            else if (!cliff && !open) { start = t; open = true; }
            if (!cliff) lastOk = t;
        }
        if (open && L - start >= minSpan) outp.Add(new[] { start, L });
        cliffLen = Mathf.Min(cliffLen, L);
        return outp;
    }

    static Vector2 NodeXZ(Vector3 tp, Vector3 ts, int res, int i, int j)
    {
        return new Vector2(tp.x + i * ts.x / (res - 1), tp.z + j * ts.z / (res - 1));
    }
}
