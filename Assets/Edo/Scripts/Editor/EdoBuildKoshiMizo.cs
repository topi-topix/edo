// EdoBuild — 溝に沿う低い土留めと、地盤なりの板柵の据え(2026-10-15・EDO-0502 第139巡・普請方 第138巡の返し northSideR138 / endRaiseR138 / F_Hori.r138)。
//  ・溝の駒の縁石の外の縁を実メッシュで測る(CurbOuterPoint)
//  ・脚ごとに離れの違う折れ線を平行に出す(OffsetPolylineLegs)・天端の変わりを抑える(LimitStep)
//  ・据えた駒の天端に沿う背の小段を切りも盛りも高さで描く(CrestFollowBackBench)
//  ・板柵の足元の帯を坂なりの一筋で描く(FenceFootBand)・板を一枚ごとに地盤なりに水平に据える(LevelFenceRun / SeatLevelFence)・浮きを測る(FenceFloatReport)
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図を読んで渡すだけ。⛔ 基準点・bounds で測らない。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    static readonly Dictionary<string, Vector3> _curbOuterCache = new Dictionary<string, Vector3>();

    /// <summary>**溝の駒の縁石の外の縁**(向き <paramref name="n"/> の側・世界 xz)と縁石の天端。局所の縁石の帯は <see cref="MizoCurbTop"/>(実メッシュ)で測り、
    /// その側の帯の外の端(|x| の大きい方)を駒の向き・倍率で世界へ写す。⛔ ピボット・halfW の定数で決めない。測れなければ false。
    /// 当たる先: 溝の縁に沿う土留め・帯の線を引く所(岡部 TW_Minami_Mizo の見え面の線 = 北の縁石の外の縁 + c)。</summary>
    public static bool CurbOuterPoint(GameObject piece, Vector2 n, out Vector2 at, out float top)
    {
        at = new Vector2(float.NaN, float.NaN); top = float.NaN; if (piece == null) return false;
        string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(piece); if (string.IsNullOrEmpty(path)) return false;
        var tr = piece.transform; Vector3 rx = tr.right; int side = Vector2.Dot(new Vector2(rx.x, rx.z), n) >= 0f ? 1 : -1;
        string key = path + "|" + side; Vector3 c;
        if (!_curbOuterCache.TryGetValue(key, out c))
        {
            float xa, xb, t; if (!MizoCurbTop(path, side, out xa, out xb, out t)) return false;
            float xo = side > 0 ? Mathf.Max(xa, xb) : Mathf.Min(xa, xb); c = new Vector3(xo, t, 0f); _curbOuterCache[key] = c;
        }
        var w = tr.TransformPoint(new Vector3(c.x, c.y, 0f)); at = new Vector2(w.x, w.z); top = w.y; return true;
    }

    static readonly Dictionary<string, Vector4> _mizoChannelCache = new Dictionary<string, Vector4>();
    /// <summary>**点 v が溝の駒の縁石の内(溝の筋)に入るか** ── 駒の局所で、長さ [zMin, zMax] の内・横 |x| が両側の縁石の外の縁より内・高さが縁石の天端より上。
    /// 地際の張り出し(縁石の外の板)は数えない(板は据えた駒の下に埋まる)。⛔ 外接の箱・凸包で見ない(張り出しで偽の当たり)。当たる先: 溝の縁に寄せて立てる土留め・駒の検め(岡部 TW_Minami_Mizo)。</summary>
    public static bool IntoMizoChannel(GameObject mizo, Vector3 v)
    {
        if (mizo == null) return false; string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(mizo); if (string.IsNullOrEmpty(path)) return false;
        Vector4 c;
        if (!_mizoChannelCache.TryGetValue(path, out c))
        {
            var m = MizoPieceOf(path); float xa, xb, t1, t2, ya, yb; if (!m.ok || !MizoCurbTop(path, 1, out xa, out xb, out t1) || !MizoCurbTop(path, -1, out ya, out yb, out t2)) { c = new Vector4(float.NaN, 0, 0, 0); }
            else c = new Vector4(Mathf.Max(xa, xb), Mathf.Min(ya, yb), m.zMin, m.zMax);
            _mizoChannelCache[path] = c;
        }
        if (float.IsNaN(c.x)) return false;
        var lv = mizo.transform.InverseTransformPoint(v); float ctop = 0f; { float tt; if (MizoCurbTopCached(path, out tt)) ctop = tt; }
        return lv.z >= c.z && lv.z <= c.w && lv.x < c.x - 1e-3f && lv.x > c.y + 1e-3f && lv.y > ctop + 0.01f;
    }
    /// <summary><see cref="IntoMizoChannel"/> の深さ(縁石の外の縁の近い方からの横の離れ・世界の長さ)── 入らなければ NaN。線を引き直す量に使う。</summary>
    public static float MizoChannelDepth(GameObject mizo, Vector3 v)
    {
        if (!IntoMizoChannel(mizo, v)) return float.NaN;
        string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(mizo); var c = _mizoChannelCache[path]; var lv = mizo.transform.InverseTransformPoint(v);
        return Mathf.Min(c.x - lv.x, lv.x - c.y) * Mathf.Abs(mizo.transform.lossyScale.x);
    }
    static readonly Dictionary<string, float> _curbTopCache = new Dictionary<string, float>();
    static bool MizoCurbTopCached(string path, out float top)
    {
        if (_curbTopCache.TryGetValue(path, out top)) return !float.IsNaN(top);
        float xa, xb; if (!MizoCurbTop(path, 1, out xa, out xb, out top)) top = float.NaN; _curbTopCache[path] = top; return !float.IsNaN(top);
    }

    /// <summary>**脚ごとに離れの違う折れ線を平行に出す**(脚 i を向き n[i] へ off[i] だけ平行移動し、隣の脚との交点で継ぐ)。隣どうしの折れが
    /// <paramref name="mergeDeg"/> 未満の脚は一本に束ね、離れは大きい方を採る(ほぼ一直線の脚の継ぎ目で短い段を作らない)。⟶ 出した折れ線と、その脚ごとの n。
    /// 当たる先: 溝・線に沿う土留めの線を測った離れで引く所(岡部 TW_Minami_Mizo)。</summary>
    public static List<Vector2> OffsetPolylineLegs(IList<Vector2> pl, IList<float> off, IList<Vector2> n, float mergeDeg, out List<Vector2> legN, out List<int> legOf)
    {
        legN = new List<Vector2>(); legOf = new List<int>();
        var A0 = new List<Vector2>(); var B0 = new List<Vector2>(); var Nn = new List<Vector2>(); var Of = new List<float>(); var src = new List<int>();
        for (int i = 0; i + 1 < pl.Count; i++)
        {
            Vector2 a = pl[i], b = pl[i + 1]; if (Vector2.Distance(a, b) < 1e-3f) continue;
            if (A0.Count > 0 && Vector2.Angle(B0[B0.Count - 1] - A0[A0.Count - 1], b - a) < mergeDeg && Mathf.Abs(Of[Of.Count - 1] - off[i]) <= 0.05f)
            { int k = A0.Count - 1; B0[k] = b; Of[k] = Mathf.Max(Of[k], off[i]); continue; }
            A0.Add(a); B0.Add(b); Nn.Add(n[i]); Of.Add(off[i]); src.Add(i);
        }
        int m = A0.Count; if (m == 0) return new List<Vector2>();
        // 束ねた脚の向きは端から端の向きに直した n(元の n の側を保つ)
        for (int k = 0; k < m; k++) { Vector2 t = (B0[k] - A0[k]).normalized, p = new Vector2(-t.y, t.x); if (Vector2.Dot(p, Nn[k]) < 0f) p = -p; Nn[k] = p; }
        // ⭐ ほぼ平行(< 3°)で離れの違う隣どうしは、離れの小さい側の脚に渡りの脚(長さ max(1.818, 2.5 × 離れの差))を足して継ぐ ── 交点が遠くへ飛ばない・
        //   大きい離れの脚は継ぎ目まで保つ(小さい離れの所で線が溝から遠いのは良い側)
        for (int k = 0; k + 1 < A0.Count; k++)
        {
            Vector2 d0 = (B0[k] - A0[k]).normalized, d1 = (B0[k + 1] - A0[k + 1]).normalized; float dOf = Of[k + 1] - Of[k];
            if (Vector2.Angle(d0, d1) >= 3f || Mathf.Abs(dOf) <= 0.05f) continue;
            float Lt = Mathf.Max(1.818f, 2.5f * Mathf.Abs(dOf));
            if (dOf < 0f) { float L1 = Vector2.Distance(A0[k + 1], B0[k + 1]); if (L1 <= Lt + 0.5f) continue; Vector2 j = A0[k + 1] + d1 * Lt;   // 後の脚が小さい: 後の脚の頭に渡り
                A0.Insert(k + 1, A0[k + 1]); B0.Insert(k + 1, j); Nn.Insert(k + 1, Nn[k + 1]); Of.Insert(k + 1, float.NaN); src.Insert(k + 1, src[k + 1]); A0[k + 2] = j; k++; }
            else { float L0 = Vector2.Distance(A0[k], B0[k]); if (L0 <= Lt + 0.5f) continue; Vector2 j = B0[k] - d0 * Lt;   // 前の脚が小さい: 前の脚の尻に渡り
                A0.Insert(k + 1, j); B0.Insert(k + 1, B0[k]); Nn.Insert(k + 1, Nn[k]); Of.Insert(k + 1, float.NaN); src.Insert(k + 1, src[k]); B0[k] = j; k++; }
        }
        m = A0.Count; var res = new List<Vector2>();
        // 渡りの脚(Of = NaN)は前後の脚の端点を直に結ぶ
        Func<int, Vector2> startOf = k => A0[k] + Nn[k] * Of[k]; Func<int, Vector2> endOf = k => B0[k] + Nn[k] * Of[k];
        res.Add(float.IsNaN(Of[0]) ? A0[0] : startOf(0));
        for (int k = 0; k + 1 < m; k++)
        {
            if (float.IsNaN(Of[k]) || float.IsNaN(Of[k + 1])) { if (float.IsNaN(Of[k]) && !float.IsNaN(Of[k + 1])) res.Add(startOf(k + 1)); else if (!float.IsNaN(Of[k])) res.Add(endOf(k)); continue; }
            Vector2 p0 = A0[k] + Nn[k] * Of[k], d0 = (B0[k] - A0[k]).normalized, p1 = A0[k + 1] + Nn[k + 1] * Of[k + 1], d1 = (B0[k + 1] - A0[k + 1]).normalized;
            float den = d0.x * d1.y - d0.y * d1.x; Vector2 X; Vector2 mid = (B0[k] + Nn[k] * Of[k] + A0[k + 1] + Nn[k + 1] * Of[k + 1]) * 0.5f;
            if (Mathf.Abs(den) < 1e-5f || Vector2.Angle(d0, d1) < 3f) X = mid; else { Vector2 w = p1 - p0; float tt = (w.x * d1.y - w.y * d1.x) / den; X = p0 + d0 * tt; if (Vector2.Distance(X, B0[k]) > 2f + Mathf.Max(Of[k], Of[k + 1]) * 3f) X = mid; }   // ほぼ平行は中点で継ぐ(交点が遠くへ飛ばない)
            res.Add(X);
        }
        res.Add(float.IsNaN(Of[m - 1]) ? B0[m - 1] : endOf(m - 1));
        for (int k = 0; k < m; k++) if (float.IsNaN(Of[k])) { Vector2 a = res[k], b = res[k + 1], t = (b - a).normalized, p = new Vector2(-t.y, t.x); if (Vector2.Dot(p, Nn[k]) < 0f) p = -p; Nn[k] = p; }
        legN.AddRange(Nn); legOf.AddRange(src); return res;
    }

    /// <summary>**並びの値の隣どうしの差を <paramref name="maxStep"/> 以下へ**(前から・後ろから一度ずつ、隣の値 ± maxStep へ挟む)。値を通す一筋を作る ── 駒ごとの天端の変わりの上限
    /// (指図 northSideR138「駒ごとの変わり ≤0.15 で通した坂なりの一筋」)。NaN は飛ばす。当たる先: 地盤なりの土留めの天端の線(岡部 TW_Minami_Mizo)。</summary>
    public static void LimitStep(float[] v, float maxStep)
    {
        for (int pass = 0; pass < 2; pass++)
        {
            int prev = -1;
            for (int ii = 0; ii < v.Length; ii++)
            {
                int i = pass == 0 ? ii : v.Length - 1 - ii; if (float.IsNaN(v[i])) continue;
                if (prev >= 0) v[i] = Mathf.Clamp(v[i], v[prev] - maxStep * Mathf.Abs(i - prev), v[prev] + maxStep * Mathf.Abs(i - prev));
                prev = i;
            }
        }
    }

    /// <summary>**据えた駒の天端に沿う背の小段を、切りも盛りも高さで描く**(普請方 第138巡 northSideR138【硬】「天端の線から w は天端 −drop の平らを取り、その先は今の法へ擦り付ける・
    /// 天端の上の土は 1/drain で溝の側へ向ける」)。天端 c(s) は <see cref="CrestFollowBackFill"/> と同じく据えた駒の実メッシュの天端(線から背へ <paramref name="crestDepth"/>・走り ±0.15 の頂点の最高)を
    /// 道のりで補間した一続きの線。小段 = c(s) − drop − (w − dn)/drain(前ほど下がる)・その先と線の両端の先は 1:bf で今の地盤へ(高ければ切り・低ければ盛り)。
    /// 前(見え面の側)・区画の外・<paramref name="keepOut"/> は触らない。書いた高さは <paramref name="recPath"/>(造成QA・升目の段の検め)。⟶ 返す: 記録の一行。
    /// 当たる先: 法の途中に立てた低い土留めの背(岡部 TW_Minami_Mizo)── 盛るだけの背は <see cref="CrestFollowBackFill"/>。</summary>
    public static string CrestFollowBackBench(string name, IList<GameObject> pieces, IList<Vector2> line, IList<Vector2> back, float crestDepth, float drop, float benchW, float drain, float bf,
                                              Vector2[] parcel, Func<Vector2, bool> keepOut, string recPath)
    {
        if (line == null || line.Count < 2 || pieces == null || pieces.Count == 0) return name + ": 線か駒が無い ── 描かない";
        var cum = new float[line.Count]; for (int i = 1; i < line.Count; i++) cum[i] = cum[i - 1] + Vector2.Distance(line[i - 1], line[i]);
        float Ltot = cum[line.Count - 1]; if (Ltot < 0.1f) return name + ": 線が短い ── 描かない";
        var vs = new List<Vector3>(); foreach (var g in pieces) if (g != null && g.activeInHierarchy) vs.AddRange(Body(g.transform, 999999));
        Func<Vector2, Vector3> proj = q =>
        {
            float bd = float.MaxValue; Vector3 r = new Vector3(float.NaN, float.NaN, -1);
            for (int i = 0; i + 1 < line.Count; i++)
            {
                Vector2 a = line[i], ab = line[i + 1] - a; float L = ab.magnitude; if (L < 1e-4f) continue; Vector2 t = ab / L;
                float u = Vector2.Dot(q - a, t), uc = Mathf.Clamp(u, 0f, L); Vector2 f = a + t * uc; float d = Vector2.Distance(q, f);
                if (d < bd) { bd = d; Vector2 bk = back[Mathf.Min(i, back.Count - 1)]; r = new Vector3(cum[i] + u, Vector2.Dot(q - f, bk), i); }
            }
            return r;
        };
        float ds = 0.25f; int nS = Mathf.CeilToInt(Ltot / ds) + 1; var cr = new float[nS]; for (int i = 0; i < nS; i++) cr[i] = float.NaN;
        foreach (var v in vs)
        {
            var pr = proj(new Vector2(v.x, v.z)); if (pr.z < 0 || pr.y < -0.05f || pr.y > crestDepth) continue;
            if (pr.x < -0.15f || pr.x > Ltot + 0.15f) continue;
            int i0 = Mathf.Clamp(Mathf.FloorToInt((pr.x - 0.15f) / ds), 0, nS - 1), i1 = Mathf.Clamp(Mathf.CeilToInt((pr.x + 0.15f) / ds), 0, nS - 1);
            for (int i = i0; i <= i1; i++) if (Mathf.Abs(i * ds - pr.x) <= 0.15f + 1e-4f && (float.IsNaN(cr[i]) || v.y > cr[i])) cr[i] = v.y;
        }
        int nHave = 0; for (int i = 0; i < nS; i++) if (!float.IsNaN(cr[i])) nHave++;
        if (nHave == 0) return name + ": 線の上に駒の天端が無い ── 描かない";
        for (int i = 1; i < nS; i++) if (float.IsNaN(cr[i])) cr[i] = cr[i - 1];
        for (int i = nS - 2; i >= 0; i--) if (float.IsNaN(cr[i])) cr[i] = cr[i + 1];
        Func<float, float> crestAt = s => { float x = Mathf.Clamp(s, 0f, Ltot) / ds; int i = Mathf.Clamp(Mathf.FloorToInt(x), 0, nS - 1), j = Mathf.Min(i + 1, nS - 1); return Mathf.Lerp(cr[i], cr[j], x - i); };
        var t0 = T(); var td = t0.terrainData; int hres = td.heightmapResolution; Vector3 tp = t0.transform.position, ts = td.size; float cell = ts.x / (hres - 1);
        float reach = benchW + bf * 4f + 2f * cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in line) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1; var H = td.GetHeights(x0, z0, w, h); int nUp = 0, nDn = 0; float upMx = 0f, dnMx = 0f; var rec = recPath != null ? new Dictionary<long, float>() : null;
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            if (parcel != null && !EdoGeom.PIP(parcel, p)) continue; if (keepOut != null && keepOut(p)) continue;
            var pr = proj(p); if (pr.z < 0 || pr.y < 0f) continue;
            float s = pr.x, dEnd = s < 0f ? -s : (s > Ltot ? s - Ltot : 0f);
            float hh = Mathf.Sqrt(Mathf.Pow(Mathf.Max(0f, pr.y - benchW), 2f) + dEnd * dEnd);
            float bench = crestAt(s) - drop - (drain > 0f ? Mathf.Max(0f, benchW - pr.y) / drain : 0f);
            float cur = H[iz, ix] * ts.y + tp.y, lo = bench - hh / bf, hi = bench + hh / bf;
            if (hh > reach) continue;
            float nw = Mathf.Clamp(cur, lo, hi); if (Mathf.Abs(nw - cur) < 1e-4f) continue;
            if (nw > cur) { nUp++; upMx = Mathf.Max(upMx, nw - cur); } else { nDn++; dnMx = Mathf.Max(dnMx, cur - nw); }
            H[iz, ix] = (nw - tp.y) / ts.y; if (rec != null) rec[((long)(x0 + ix) << 32) ^ (uint)(z0 + iz)] = nw;
        }
        if (nUp + nDn > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        if (rec != null && rec.Count > 0) AppendNodeTargets(recPath, t0.name, rec);
        float cMin = float.MaxValue, cMax = float.MinValue; foreach (var c in cr) { cMin = Mathf.Min(cMin, c); cMax = Mathf.Max(cMax, c); }
        return name + ": 駒の天端 " + cMin.ToString("F2") + "〜" + cMax.ToString("F2") + "(" + Ltot.ToString("F1") + "m・測った点 " + nHave + "/" + nS + ")に沿う小段 天端 −" + drop.ToString("F2") + "・奥行 " + benchW.ToString("F2")
             + (drain > 0f ? "・前へ 1/" + drain.ToString("0") : "") + "・その先 1:" + bf.ToString("0.0") + " で今の地盤へ・盛った節点 " + nUp + "(最大 " + upMx.ToString("F2") + ")・切った節点 " + nDn + "(最大 " + dnMx.ToString("F2") + ")";
    }

    /// <summary>**板柵の足元の帯を坂なりの一筋で描く**(普請方 第138巡 F_Hori.r138【硬】「柵の足元の帯 = 線から内へ 0〜w。高さは線の上の base_dem の値を道のりで通した坂なりの一筋とし、
    /// 高さで指定して描く(盛り・切りとも ≤maxDiff・区画の内だけ)」)。線 a→b の上の base_dem を 0.25 ごとに取り、走り ±<paramref name="win"/>/2 の平均で一筋に通す。
    /// 帯の節点(走り [0, L]・線から内へ [0, w])を一筋の高さへ(今の地盤から ±maxDiff で頭打ち)。区画の外・<paramref name="keepOut"/> は触らない。⟶ 返す: 記録の一行。
    /// 当たる先: 区画の線の際の板柵・木柵の足元(岡部 F_Hori)。</summary>
    public static string FenceFootBand(Vector2 a, Vector2 b, Vector2 inward, float w, float maxDiff, float win, Func<float, float, float> baseAt, Vector2[] parcel, Func<Vector2, bool> keepOut, string recPath, out Func<float, float> profile)
    {
        float L = Vector2.Distance(a, b); profile = null; if (L < 0.1f) return "線が短い ── 描かない";
        Vector2 t = (b - a) / L; int n = Mathf.CeilToInt(L / 0.25f) + 1; var raw = new float[n];
        for (int i = 0; i < n; i++) { var q = a + t * Mathf.Min(L, i * 0.25f); raw[i] = baseAt(q.x, q.y); }
        var sm = new float[n]; int hw = Mathf.Max(0, Mathf.RoundToInt(win * 0.5f / 0.25f));
        for (int i = 0; i < n; i++) { float acc = 0f; int c = 0; for (int k = Mathf.Max(0, i - hw); k <= Mathf.Min(n - 1, i + hw); k++) if (!float.IsNaN(raw[k])) { acc += raw[k]; c++; } sm[i] = c > 0 ? acc / c : float.NaN; }
        Func<float, float> prof = s => { float x = Mathf.Clamp(s, 0f, L) / 0.25f; int i = Mathf.Clamp(Mathf.FloorToInt(x), 0, n - 1), j = Mathf.Min(i + 1, n - 1); return Mathf.Lerp(sm[i], sm[j], x - i); };
        profile = prof;
        var t0 = T(); var td = t0.terrainData; int hres = td.heightmapResolution; Vector3 tp = t0.transform.position, ts = td.size; float cell = ts.x / (hres - 1);
        float mnx = Mathf.Min(a.x, b.x) - w - 1f, mxx = Mathf.Max(a.x, b.x) + w + 1f, mnz = Mathf.Min(a.y, b.y) - w - 1f, mxz = Mathf.Max(a.y, b.y) + w + 1f;
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / cell), 0, hres - 1);
        int ww = x1 - x0 + 1, hh = z1 - z0 + 1; var H = td.GetHeights(x0, z0, ww, hh); int nW = 0, nCap = 0; float up = 0f, dn = 0f, capMx = 0f; var rec = recPath != null ? new Dictionary<long, float>() : null;
        for (int iz = 0; iz < hh; iz++) for (int ix = 0; ix < ww; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            float s = Vector2.Dot(p - a, t), d = Vector2.Dot(p - a, inward); if (s < 0f || s > L || d < -1e-4f || d > w + 1e-4f) continue;
            if (parcel != null && !EdoGeom.PIP(parcel, p)) continue; if (keepOut != null && keepOut(p)) continue;
            float y = prof(s); if (float.IsNaN(y)) continue;
            float cur = H[iz, ix] * ts.y + tp.y, nw = y;
            //   盛り・切り ≤ maxDiff【硬】に届かない節点は書かない(頭打ちで書くと帯の縁に段の溝ができる ── 第139巡 岡部の汀で 749/773 節点・要る差 2.55)⇒ 数えて刷る
            if (Mathf.Abs(y - cur) > maxDiff + 1e-4f) { nCap++; capMx = Mathf.Max(capMx, Mathf.Abs(y - cur)); continue; }
            if (Mathf.Abs(nw - cur) < 1e-4f) continue;
            if (nw > cur) up = Mathf.Max(up, nw - cur); else dn = Mathf.Max(dn, cur - nw);
            H[iz, ix] = (nw - tp.y) / ts.y; nW++; if (rec != null) rec[((long)(x0 + ix) << 32) ^ (uint)(z0 + iz)] = nw;
        }
        if (nW > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); AssetDatabase.SaveAssetIfDirty(td); }
        if (rec != null && rec.Count > 0) AppendNodeTargets(recPath, t0.name, rec);
        float yLo = float.MaxValue, yHi = float.MinValue; foreach (var v in sm) if (!float.IsNaN(v)) { yLo = Mathf.Min(yLo, v); yHi = Mathf.Max(yHi, v); }
        return "足元の帯(線から内へ 0〜" + w.ToString("0.00") + "・base_dem を ±" + (win * 0.5f).ToString("0.0") + "m で通した一筋 " + yLo.ToString("F2") + "〜" + yHi.ToString("F2") + "): 節点 " + nW + "・盛り 最大 " + up.ToString("F2") + "・切り 最大 " + dn.ToString("F2")
             + (nCap > 0 ? "・⛔ 今の地盤から ±" + maxDiff.ToString("0.00") + " に一筋が届かず書かなかった " + nCap + " 節点(要る差 最大 " + capMx.ToString("F2") + " ── 普請方へ)" : "・届かない節点 0");
    }

    static readonly Dictionary<string, Vector2> _panelZ = new Dictionary<string, Vector2>();
    /// <summary>板の局所の厚みの範囲 z(実メッシュ)── 地盤を厚みの両面と芯の三筋で測る(岸の斜面で外の縁が浮かない)。</summary>
    public static Vector2 PanelZLocal(string path)
    {
        Vector2 r; if (_panelZ.TryGetValue(path, out r)) return r;
        float lo = float.MaxValue, hi = float.MinValue; foreach (var v in BodyAt(path, Vector3.zero, 0f, true)) { lo = Mathf.Min(lo, v.z); hi = Mathf.Max(hi, v.z); }
        r = lo < hi ? new Vector2(lo, hi) : Vector2.zero; _panelZ[path] = r; return r;
    }
    /// <summary>板の局所の下端(柱の根を除く板の最も低い所)── 駒の実メッシュで、局所 y が根(原点より下)より上の頂点の最小。⛔ 定数で持たない。</summary>
    public static float PanelBottomLocal(string path)
    {
        var vs = BodyAt(path, Vector3.zero, 0f, true); float lo = float.MaxValue; foreach (var v in vs) if (v.y > 1e-3f) lo = Mathf.Min(lo, v.y); return lo == float.MaxValue ? 0f : lo;
    }

    /// <summary>**板柵を板ごとに水平に、地盤なりに据える**(普請方 第138巡 F_Hori.r138【硬】「柵は弦に張らず、一枚ごとに地盤なりに据える。板の下端 = その板の下の最も低い所 +gapLo〜+gapHi。
    /// 柱は rootMin 以上根入れ。隣の板との下端の差 ≤maxNb で坂なりに通す。浮き(下端 − 地盤)> floatMax は 0」)。辺 a→b を水平の実寸 W(<see cref="RunMeasure"/>)で割り、端の短い板は x の倍率で詰める。
    /// 高さは <see cref="SeatLevelFence"/>(据えた後の地盤で測る ── 後の造成の後に呼び直す)。⟶ 据えた板(柱は板の +X の端)。lastJoint = 終わりの点(端の杭を立てる所)。
    /// 当たる先: 地形なりの板柵(岡部 F_Hori)── 弦に張る <see cref="ChordFenceRun"/> の代わり。</summary>
    public static List<GameObject> LevelFenceRun(string path, Vector2 a, Vector2 b, Vector2 outward, float latLine, Transform parent, string prefix, int startIndex, out Vector3 lastJoint)
    {
        var made = new List<GameObject>(); var rx = RunMeasure(path); float W = rx.W; float L = Vector2.Distance(a, b);
        lastJoint = new Vector3(b.x, Ground(b.x, b.y), b.y); if (L < 0.05f || W < 1e-3f) return made;
        Vector2 dir = (b - a) / L; float yaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;
        // ⭐ 表(局所 +Z)を outward へ ── ChordFacing と同じ決め(j0→j1 の向きで yaw が決まる)
        bool fwd = ChordFacing(new Vector3(a.x, 0f, a.y), new Vector3(b.x, 0f, b.y), outward);
        if (!fwd) yaw += 180f;
        var yawQ = Quaternion.Euler(0f, yaw, 0f);
        int nB = Mathf.CeilToInt(L / W - 1e-3f);
        for (int k = 0; k < nB; k++)
        {
            float s0 = k * W, s1 = Mathf.Min(L, s0 + W), sx = (s1 - s0) / W; if (s1 - s0 < 0.05f) continue;
            Vector2 m = a + dir * ((s0 + s1) * 0.5f);
            var scale = new Vector3(sx, 1f, 1f); var anchorL = new Vector3((rx.lo + rx.hi) * 0.5f, 0f, 0f);
            var pos = new Vector3(m.x, Ground(m.x, m.y), m.y) - yawQ * Vector3.Scale(scale, anchorL);
            var go = Place(path, pos, yaw, scale, parent, prefix + "_" + (startIndex + k)); if (go == null) continue;
            go.transform.rotation = yawQ; go.transform.position = pos;
            // 奥行: 据えた駒の実測の厚みの中央を latLine(outward への射影)へ
            float zl = float.MaxValue, zh = float.MinValue; foreach (var v in Body(go.transform, 4000)) { float pz = Vector2.Dot(new Vector2(v.x, v.z), outward); zl = Mathf.Min(zl, pz); zh = Mathf.Max(zh, pz); }
            if (zl < zh) { float sh = latLine - (zl + zh) * 0.5f; go.transform.position += new Vector3(outward.x * sh, 0f, outward.y * sh); }
            made.Add(go);
        }
        return made;
    }

    /// <summary>**水平の板柵を板ごとに地盤なりに据え直す**(<see cref="LevelFenceRun"/> の板を、今の地盤で)。板の下端の線(局所 y = <see cref="PanelBottomLocal"/>)の下の地盤を 0.1 ごとに測り、
    /// 下端 = 最も低い所 + gapT(gapLo〜gapHi の中)。隣の板との下端の差 > maxNb は高い側を下げて通す(下げるだけ ── 浮きを増やさない)。柱(板の端の根)の根入れ = 柱の足の地盤 − 柱の下端を刷る。
    /// ⟶ 記録の一行(浮きの最悪・隣の差の最大・狙いの外の板・根入れの最小)。当たる先: 岡部 F_Hori。</summary>
    public static string SeatLevelFence(List<GameObject> boards, Func<float, float, float> groundAt, float gapLo, float gapHi, float maxNb, float rootMin, out float worstFloat, out float minRoot)
    {
        worstFloat = 0f; minRoot = float.MaxValue;
        boards = boards.FindAll(g => g != null && !string.IsNullOrEmpty(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g)) && PrefabUtility.GetNearestPrefabInstanceRoot(g) == g);   // 弦に張った枠(剪断の入れ子)は測らない
        int n = boards.Count; if (n == 0) return "板が無い(水平に据えた板の駒が無い ── 弦に張った柵は Stage2 から流し直す)";
        var bot = new float[n]; var gmin = new float[n]; float gapT = (gapLo + gapHi) * 0.5f;
        for (int k = 0; k < n; k++)
        {
            var go = boards[k]; string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go); float bl = PanelBottomLocal(path); var rx = RunMeasure(path);
            var pz = PanelZLocal(path); float mn = float.MaxValue; for (float x = rx.lo; x <= rx.hi + 1e-4f; x += 0.1f) foreach (var zz in new[] { pz.x, 0f, pz.y }) { var w = go.transform.TransformPoint(new Vector3(Mathf.Min(x, rx.hi), bl, zz)); float g = groundAt(w.x, w.z); if (!float.IsNaN(g)) mn = Mathf.Min(mn, g); }
            gmin[k] = mn; bot[k] = mn + gapT;
        }
        // 隣の差 ≤ maxNb ── 高い側を下げる(前から・後ろから一度ずつ)
        for (int pass = 0; pass < 2; pass++) for (int ii = 1; ii < n; ii++) { int k = pass == 0 ? ii : n - 1 - ii, pk = pass == 0 ? k - 1 : k + 1; if (bot[k] > bot[pk] + maxNb) bot[k] = bot[pk] + maxNb; }
        int nLow = 0; float nbMx = 0f;
        for (int k = 0; k < n; k++)
        {
            var go = boards[k]; string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go); float bl = PanelBottomLocal(path); var ry = RunMeasureY(path); var rx = RunMeasure(path);
            var w0 = go.transform.TransformPoint(new Vector3(0f, bl, 0f)); go.transform.position += Vector3.up * (bot[k] - w0.y);
            if (bot[k] < gmin[k] + gapLo - 1e-3f) nLow++;
            if (k > 0) nbMx = Mathf.Max(nbMx, Mathf.Abs(bot[k] - bot[k - 1]));
            // 浮き = 下端 − 地盤 の最大(0.1 ごと)
            var pz2 = PanelZLocal(path); for (float x = rx.lo; x <= rx.hi + 1e-4f; x += 0.1f) foreach (var zz in new[] { pz2.x, 0f, pz2.y }) { var w = go.transform.TransformPoint(new Vector3(Mathf.Min(x, rx.hi), bl, zz)); float g = groundAt(w.x, w.z); if (!float.IsNaN(g)) worstFloat = Mathf.Max(worstFloat, w.y - g); }
            // 柱の根入れ: 板の下端より下の頂点(根)の足の地盤 − 根の下端
            float pl = float.MaxValue; Vector3 pAt = Vector3.zero; foreach (var v in Body(go.transform, 4000)) { var lv = go.transform.InverseTransformPoint(v); if (lv.y < bl - 1e-3f && v.y < pl) { pl = v.y; pAt = v; } }
            if (pl < float.MaxValue) { float g = groundAt(pAt.x, pAt.z); if (!float.IsNaN(g)) minRoot = Mathf.Min(minRoot, g - pl); }
        }
        return "板 " + n + " 枚を水平に地盤なりへ(下端 = 板の下の最も低い所 +" + gapT.ToString("0.000") + "・隣の差 ≤" + maxNb.ToString("0.00") + " は下げて通す): 浮きの最悪 " + worstFloat.ToString("F3") + "・隣の差の最大 " + nbMx.ToString("F3")
             + (nLow > 0 ? "・⚠ 隣に合わせて +" + gapLo.ToString("0.00") + " より深く下げた板 " + nLow : "") + "・柱の根入れの最小 " + (minRoot == float.MaxValue ? "-" : minRoot.ToString("F2")) + (minRoot < rootMin - 1e-3f ? " ⛔(≥" + rootMin.ToString("0.00") + " に届かない ── 部材の柱の根の長さ)" : " ⭕");
    }

    /// <summary>**板柵の浮き**(測るだけ・普請方 第138巡 F_Hori.r138「この柵を据えた後に浮きを測る」【硬: 浮き > floatMax は 0】)。板ごとに下端の線(局所 y = <see cref="PanelBottomLocal"/>)を 0.1 ごとに、
    /// 下端 − 描かれた地盤の最大。⟶ 頭の一行(板・浮きの最悪・超えた板)。当たる先: 地盤なりの板柵(岡部 F_Hori)── 造成QA(GroundQA)の後ろに刷る。</summary>
    public static string FenceFloatReport(IList<GameObject> boards, Func<float, float, float> groundAt, float floatMax, out int nOver, out float worst)
    {
        nOver = 0; worst = 0f; string ww = ""; int n = 0;
        foreach (var go in boards)
        {
            if (go == null || !go.activeInHierarchy) continue; string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go); if (string.IsNullOrEmpty(path)) continue;
            float bl = PanelBottomLocal(path); var rx = RunMeasure(path); float f = 0f; n++; var pz = PanelZLocal(path);
            for (float x = rx.lo; x <= rx.hi + 1e-4f; x += 0.1f) foreach (var zz in new[] { pz.x, 0f, pz.y }) { var w = go.transform.TransformPoint(new Vector3(Mathf.Min(x, rx.hi), bl, zz)); float g = groundAt(w.x, w.z); if (!float.IsNaN(g)) f = Mathf.Max(f, w.y - g); }
            if (f > floatMax + 1e-4f) nOver++; if (f > worst) { worst = f; ww = go.name; }
        }
        return "板 " + n + "・浮きの最悪 " + worst.ToString("F3") + (ww != "" ? " " + ww : "") + "・> " + floatMax.ToString("0.00") + " の板 " + nOver + (nOver > 0 ? " ⛔" : " ⭕");
    }
}
