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
    /// <para>⭐ 第140巡(普請方 F_Hori.r139【硬】「帯の高さ = 線から内へ 0.30 の今の地盤を、道のり ±0.9 の移動平均で均した一筋。盛り・切りとも ≤0.30」)──
    /// <paramref name="sampleIn"/> &gt; 0 なら、一筋の元は線から内へ sampleIn の <paramref name="baseAt"/>(今の地盤を渡す)。<paramref name="label"/> は記録の名(既定 base_dem)。</para>
    public static string FenceFootBand(Vector2 a, Vector2 b, Vector2 inward, float w, float maxDiff, float win, Func<float, float, float> baseAt, Vector2[] parcel, Func<Vector2, bool> keepOut, string recPath, out Func<float, float> profile, float sampleIn = 0f, string label = null)
    {
        float L = Vector2.Distance(a, b); profile = null; if (L < 0.1f) return "線が短い ── 描かない";
        Vector2 t = (b - a) / L; int n = Mathf.CeilToInt(L / 0.25f) + 1; var raw = new float[n];
        for (int i = 0; i < n; i++) { var q = a + t * Mathf.Min(L, i * 0.25f) + inward * sampleIn; raw[i] = baseAt(q.x, q.y); }
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
        return "足元の帯(線から内へ 0〜" + w.ToString("0.00") + "・" + (label ?? "base_dem") + " を ±" + (win * 0.5f).ToString("0.0") + "m で通した一筋 " + yLo.ToString("F2") + "〜" + yHi.ToString("F2") + "): 節点 " + nW + "・盛り 最大 " + up.ToString("F2") + "・切り 最大 " + dn.ToString("F2")
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

    // ================================================================ 第140巡(普請方 第139巡の返し northSideR139 N1〜N3 / endRaiseR139 / F_Hori.r139)
    /// <summary>**溝の駒の縁石の外の縁の両端**(向き <paramref name="n"/> の側・世界 xz)── 駒の局所の長さの端 zMin / zMax(<see cref="MizoPieceOf"/>)で、
    /// 縁石の外の縁(<see cref="CurbOuterPoint"/> と同じ局所の x)を世界へ写す。測れなければ false。
    /// 当たる先: 溝の駒の継ぎ目ごとに折れる線を引く所(岡部 TW_Minami_Mizo の法尻の線 ── N3)。</summary>
    public static bool CurbOuterEnds(GameObject piece, Vector2 n, out Vector2 a, out Vector2 b, out float top)
    {
        a = b = new Vector2(float.NaN, float.NaN); top = float.NaN; if (piece == null) return false;
        string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(piece); if (string.IsNullOrEmpty(path)) return false;
        var m = MizoPieceOf(path); if (!m.ok) return false;
        var tr = piece.transform; Vector3 rx = tr.right; int side = Vector2.Dot(new Vector2(rx.x, rx.z), n) >= 0f ? 1 : -1;
        float xa, xb, t; if (!MizoCurbTop(path, side, out xa, out xb, out t)) return false;
        float xo = side > 0 ? Mathf.Max(xa, xb) : Mathf.Min(xa, xb);
        var wa = tr.TransformPoint(new Vector3(xo, t, m.zMin)); var wb = tr.TransformPoint(new Vector3(xo, t, m.zMax));
        a = new Vector2(wa.x, wa.z); b = new Vector2(wb.x, wb.z); top = 0.5f * (wa.y + wb.y); return true;
    }

    /// <summary>**溝の縁石の外の縁の折れ線と、それを c だけ出した法尻の線**(普請方 第139巡 northSideR139 N3【硬: 法尻 − 縁石の外の縁 0.00〜+0.10】
    /// 「法尻の線 = 溝の縁石の外の縁 + c を、溝の駒の継ぎ目ごとに折れる折れ線で通す・折れが cornerDeg 以下の所は直線の駒の継ぎで折る・それを超える曲がりは隅の駒で継ぐ」)。
    /// 鎖 <paramref name="ch"/>(溝の芯・脚 i の背の向き <paramref name="nrm"/>)の脚ごとに、その脚に沿う溝の駒(走りが脚と 10° 以内)の縁石の外の縁の両端を実メッシュで測り
    /// (<see cref="CurbOuterEnds"/>)、脚の上の道のりの順に並べる(0.3 以内の点は平均 ── 型の変わり目の横ずれは隣の駒へ緩く渡る)。鎖の折れの所は前後の脚の縁の線の交点を
    /// 一つの頂点にする(折れの際 0.6 の内の点は捨てる ── 曲がりの間の駒は隅の駒の下)。縁の測れない脚は隣の脚の離れを借りる。⟶ 法尻の線(離れ = 縁 + c + extraAt(縁の点) ── 溝の筋へ入った駒の所だけ局所に足す)。
    /// <paramref name="curbLine"/> = 同じ頂点の縁そのもの(測りの基準)・<paramref name="legN"/> = 線の区間ごとの背の向き・<paramref name="legOf"/> = 区間ごとの鎖の脚。
    /// ⛔ 座標を書かない・基準点で測らない。当たる先: 溝の縁に沿って立てる土留め・帯の線(岡部 TW_Minami_Mizo)。</summary>
    public static List<Vector2> CurbToeLine(IList<Vector2> ch, IList<Vector2> nrm, IList<GameObject> mz, float clr, Func<Vector2, float> extraAt, out List<Vector2> curbLine, out List<Vector2> legN, out List<int> legOf, out int nMeasured, float cornerDeg = 15f)
    {
        int nl = ch.Count - 1; nMeasured = 0; curbLine = new List<Vector2>(); legN = new List<Vector2>(); legOf = new List<int>();
        var tl = new Vector2[nl]; var Ll = new float[nl]; for (int i = 0; i < nl; i++) { Ll[i] = Vector2.Distance(ch[i], ch[i + 1]); tl[i] = (ch[i + 1] - ch[i]) / Mathf.Max(1e-6f, Ll[i]); }
        var pts = new List<Vector2>[nl]; for (int i = 0; i < nl; i++) pts[i] = new List<Vector2>();   // (道のり, 離れ)
        foreach (var g in mz)
        {
            if (g == null) continue; var pc = new Vector2(g.transform.position.x, g.transform.position.z); Vector3 fz = g.transform.forward; var f2 = new Vector2(fz.x, fz.z); if (f2.sqrMagnitude < 1e-6f) continue; f2.Normalize();
            int bi = -1; float bd = float.MaxValue;
            for (int i = 0; i < nl; i++) { if (Mathf.Abs(Vector2.Dot(f2, tl[i])) < 0.985f) continue; float u = Vector2.Dot(pc - ch[i], tl[i]); if (u < -0.6f || u > Ll[i] + 0.6f) continue; float d = Mathf.Abs(Vector2.Dot(pc - ch[i], nrm[i])); if (d < bd) { bd = d; bi = i; } }
            if (bi < 0 || bd > 1.5f) continue;
            Vector2 a, b; float tp; if (!CurbOuterEnds(g, nrm[bi], out a, out b, out tp)) continue;
            foreach (var q in new[] { a, b }) { float lat = Vector2.Dot(q - ch[bi], nrm[bi]); if (lat < 0f || lat > 2f) continue; pts[bi].Add(new Vector2(Vector2.Dot(q - ch[bi], tl[bi]), lat)); }
            nMeasured++;
        }
        var turn = new float[ch.Count]; for (int i = 1; i < nl; i++) turn[i] = Vector2.Angle(tl[i - 1], tl[i]);
        for (int i = 0; i < nl; i++)
        {
            pts[i].Sort((p, q) => p.x.CompareTo(q.x)); var mg = new List<Vector2>();
            foreach (var p in pts[i]) { if (mg.Count > 0 && p.x - mg[mg.Count - 1].x < 0.3f) { var l = mg[mg.Count - 1]; mg[mg.Count - 1] = new Vector2(0.5f * (l.x + p.x), 0.5f * (l.y + p.y)); } else mg.Add(p); }
            pts[i] = mg;
        }
        // 折れの際の点を先に捨てる(曲がりの間の駒は隅の駒の下)── 交点はこの残した点の離れで引く(⛔ 捨てた点の離れで交点を引くと隣の区間の向きが脚から振れ、隅の折れが鎖の折れとずれる)
        for (int i = 0; i < nl; i++)
        {
            float exA0 = i > 0 && turn[i] >= 3f ? 0.6f : 0.3f, exB0 = i + 1 < nl && turn[i + 1] >= 3f ? 0.6f : 0.3f; float Li = Ll[i];
            pts[i] = pts[i].FindAll(p => p.x >= exA0 && p.x <= Li - exB0);
        }
        // 測れない脚は隣の脚の端の離れを借りる
        Func<int, bool, float> latEnd = (i, atEnd) =>
        {
            for (int d = 0; d < nl; d++) foreach (int j in new[] { i - d, i + d }) { if (j < 0 || j >= nl || pts[j].Count == 0) continue; var L = pts[j]; return j == i ? (atEnd ? L[L.Count - 1].y : L[0].y) : (j < i ? L[L.Count - 1].y : L[0].y); }
            return 0.6f;
        };
        Func<Vector2, float> exq0 = q => extraAt != null ? Mathf.Max(0f, extraAt(q)) : 0f;
        // ⭐ 折れ(≥ cornerDeg)の際 2.5 の内は足す量を一つの値(その内の最大)にする ── 両脚を平行に出し、隅の折れを鎖の折れのまま保つ
        //   (⛔ 点ごとに足すと腕ごとに違う量で出て折れが 38 → 33° に化け、焼いた隅の駒が引けず楔が残った ── 第140巡の一度目の流し)。その先 2.5 で点ごとの量へ戻す
        var cornerPts = new List<Vector2>(); for (int i = 1; i < nl; i++) if (turn[i] >= cornerDeg) cornerPts.Add(ch[i] + 0.5f * (nrm[i - 1] + nrm[i]) * latEnd(i, false));
        var cornerMax = new List<float>();
        foreach (var cp in cornerPts) { float m = 0f; for (float u = -2.5f; u <= 2.5f + 1e-3f; u += 0.25f) foreach (var d in new[] { new Vector2(1f, 0f), new Vector2(0f, 1f) }) { var q = cp + d * u; m = Mathf.Max(m, exq0(q)); } cornerMax.Add(m); }
        for (int it = 0; it < 3; it++) for (int a = 0; a < cornerPts.Count; a++) for (int b = 0; b < cornerPts.Count; b++) if (a != b && Vector2.Distance(cornerPts[a], cornerPts[b]) <= 5f) cornerMax[a] = Mathf.Max(cornerMax[a], cornerMax[b]);   // 近い隅どうし(間の脚が短い)は同じ量
        Func<Vector2, float> exq = q => { float v = exq0(q); for (int k = 0; k < cornerPts.Count; k++) { float d = Vector2.Distance(q, cornerPts[k]); float w = d <= 2.5f ? 1f : Mathf.Clamp01(1f - (d - 2.5f) / 2.5f); if (d <= 2.5f) v = cornerMax[k]; else v = Mathf.Max(v, cornerMax[k] * w); } return v; };
        var curbV = new List<Vector2>(); var vLeg = new List<int>(); var toeV = new List<Vector2>();
        Action<Vector2, Vector2, int> addV = (cv, tv, leg) => { curbV.Add(cv); toeV.Add(tv); vLeg.Add(leg); };
        { float l0 = latEnd(0, false); var c0 = ch[0] + nrm[0] * l0; addV(c0, ch[0] + nrm[0] * (l0 + clr + exq(c0)), 0); }
        for (int i = 0; i < nl; i++)
        {
            float exA = i > 0 && turn[i] >= 3f ? 0.6f : 0.3f, exB = i + 1 < nl && turn[i + 1] >= 3f ? 0.6f : 0.3f;
            foreach (var p in pts[i]) { if (p.x < exA || p.x > Ll[i] - exB) continue; var cq = ch[i] + tl[i] * p.x + nrm[i] * p.y; addV(cq, ch[i] + tl[i] * p.x + nrm[i] * (p.y + clr + exq(cq)), i); }
            if (i + 1 < nl)
            {   // 折れ: 前後の脚の縁の線の交点(縁と法尻の両方)
                float la = latEnd(i, true), lb = latEnd(i + 1, false);
                Func<float, float, Vector2> X = (oa, ob) =>
                {
                    Vector2 p0 = ch[i + 1] + nrm[i] * oa, p1 = ch[i + 1] + nrm[i + 1] * ob; Vector2 d0 = tl[i], d1 = tl[i + 1]; float den = d0.x * d1.y - d0.y * d1.x;
                    if (Mathf.Abs(den) < 1e-4f || turn[i + 1] < 3f) return 0.5f * (p0 + p1);
                    Vector2 w = p1 - p0; float tt = (w.x * d1.y - w.y * d1.x) / den; var r = p0 + d0 * tt; return Vector2.Distance(r, ch[i + 1]) > 4f ? 0.5f * (p0 + p1) : r;
                };
                var xc = X(la, lb); float xe = exq(xc); addV(xc, X(la + clr + xe, lb + clr + xe), i + 1);
            }
        }
        { float l1 = latEnd(nl - 1, true); var c1 = ch[nl] + nrm[nl - 1] * l1; addV(c1, ch[nl] + nrm[nl - 1] * (l1 + clr + exq(c1)), nl - 1); }
        // 区間の背の向き(脚の背の側の法線)と鎖の脚
        var toe = new List<Vector2>(); var cl = new List<Vector2>(); var lg = new List<int>();
        for (int k = 0; k < toeV.Count; k++) { if (toe.Count > 0 && Vector2.Distance(toe[toe.Count - 1], toeV[k]) < 0.05f) continue; toe.Add(toeV[k]); cl.Add(curbV[k]); lg.Add(vLeg[k]); }
        for (int k = 0; k + 1 < toe.Count; k++) { Vector2 t = (toe[k + 1] - toe[k]).normalized, p = new Vector2(-t.y, t.x); int leg = lg[k]; if (Vector2.Dot(p, nrm[leg]) < 0f) p = -p; legN.Add(p); legOf.Add(leg); }
        curbLine = cl; return toe;
    }

    // ================================================================ 第141巡(普請方 第140巡の返し northSideR140 P1・P2)
    /// <summary>**溝の駒の北の外形の包絡線と、それに沿う法尻の線**(普請方 northSideR140 P1【硬: 法尻 − 包絡線 0.00〜+0.10】
    /// 「包絡線は縁石・段落ちの小口石・桝のうち、その所で最も北へ出る外形を結んだもの・幅が変わる所はそこに掛かる一駒を ≤15° 振って移る(その一駒は差 0〜Δ【柔】・2.5m に広げない【硬】)・
    /// 長く幅が広い所は区間の全体で線を Δ だけ背へ通す(線は折らずに平行に退ける)」)。
    /// 鎖 <paramref name="ch"/> の脚ごとに、近い溝の駒すべて(隣の脚の駒・桝・小口石も)の石の外の縁(<see cref="CurbOuterEnds"/> ── 地際の板は数えない)を脚の座標(道のり u, 離れ)へ写し、
    /// 0.25 ごとの包絡 E(u) = その u を覆う縁の離れの最大を取る。E を高さの揃った段(差 ≤0.05)に割り、段ごとに幅の値 V を持たせ、低い隣へは <paramref name="rampLen"/>(一駒)で
    /// 振って下ろす(角 ≤ <paramref name="rampMaxDeg"/>)── 法尻 T(u) = max(各段の V − 傾き × 段からの離れ) + c。鎖の折れ(≥ <paramref name="cornerDeg"/>)の際 <paramref name="cornerZone"/> は
    /// 両脚の E を同じ値(最大)にする(両脚を平行に退ける ── 隅の角を鎖の折れのまま)。折れの所は前後の脚の線の交点。⟶ 法尻の線。<paramref name="envLine"/> = 同じ道のりの包絡線(測りの基準)、
    /// <paramref name="rampPts"/> = 振って移る所の点(x, z, その所の差 T − c − E)── 呼び手はそこに掛かる駒だけ差を Δ まで許す【柔】。
    /// ⛔ 座標を書かない・基準点で測らない・溝の筋へ入らない(包絡線の外)。当たる先: 溝の縁に沿って立てる土留め(岡部 TW_Minami_Mizo)── 幅の違う溝の駒が並ぶ縁すべて。</summary>
    public static List<Vector2> MizoEnvelopeToeLine(IList<Vector2> ch, IList<Vector2> nrm, IList<GameObject> mz, float clr, float rampLen, float rampMaxDeg, float cornerDeg, float cornerZone,
                                                   Func<Vector2, float> extraAt, out List<Vector2> envLine, out List<Vector2> envN, out List<Vector2> legN, out List<int> legOf, out List<Vector3> rampPts, out int nMeasured)
    {
        int nl = ch.Count - 1; nMeasured = 0; envLine = new List<Vector2>(); envN = new List<Vector2>(); legN = new List<Vector2>(); legOf = new List<int>(); rampPts = new List<Vector3>();
        var tl = new Vector2[nl]; var Ll = new float[nl]; for (int i = 0; i < nl; i++) { Ll[i] = Vector2.Distance(ch[i], ch[i + 1]); tl[i] = (ch[i + 1] - ch[i]) / Mathf.Max(1e-6f, Ll[i]); }
        // 溝の駒ごとの石の外の縁(背の側)── 駒の向きに最も近い脚の背の向きで測る
        var segA = new List<Vector2>(); var segB = new List<Vector2>();
        foreach (var g in mz)
        {
            if (g == null) continue; var pc = new Vector2(g.transform.position.x, g.transform.position.z); Vector3 fz = g.transform.forward; var f2 = new Vector2(fz.x, fz.z); if (f2.sqrMagnitude < 1e-6f) continue; f2.Normalize();
            int bi = -1; float bd = float.MaxValue;
            for (int i = 0; i < nl; i++) { float al = Mathf.Abs(Vector2.Dot(f2, tl[i])); float u = Vector2.Dot(pc - ch[i], tl[i]); if (u < -1.0f || u > Ll[i] + 1.0f) continue; float d = Mathf.Abs(Vector2.Dot(pc - ch[i], nrm[i])) + (1f - al) * 4f; if (d < bd) { bd = d; bi = i; } }
            if (bi < 0 || bd > 2.0f) continue;
            Vector2 a, b; float tp; if (!CurbOuterEnds(g, nrm[bi], out a, out b, out tp)) continue;
            segA.Add(a); segB.Add(b); nMeasured++;
        }
        float ds = 0.25f; var E = new float[nl][]; var U = new float[nl][];
        for (int i = 0; i < nl; i++)
        {
            int nS = Mathf.Max(2, Mathf.CeilToInt(Ll[i] / ds) + 1); E[i] = new float[nS]; U[i] = new float[nS];
            for (int k = 0; k < nS; k++) { U[i][k] = Mathf.Min(Ll[i], k * ds); E[i][k] = float.NaN; }
            for (int j = 0; j < segA.Count; j++)
            {
                float ua = Vector2.Dot(segA[j] - ch[i], tl[i]), ub = Vector2.Dot(segB[j] - ch[i], tl[i]); float la = Vector2.Dot(segA[j] - ch[i], nrm[i]), lb = Vector2.Dot(segB[j] - ch[i], nrm[i]);
                if (la < -0.2f && lb < -0.2f) continue; if (la > 2.5f || lb > 2.5f) continue;   // 背の側の縁だけ(向かいの縁・遠い駒は数えない)
                float u0 = Mathf.Min(ua, ub), u1 = Mathf.Max(ua, ub); if (u1 < -0.05f || u0 > Ll[i] + 0.05f) continue;
                for (int k = 0; k < nS; k++)
                {
                    float u = U[i][k]; if (u < u0 - 0.05f || u > u1 + 0.05f) continue;
                    float t = u1 - u0 < 1e-4f ? 0.5f : Mathf.Clamp01((u - ua) / (ub - ua)); float lat = Mathf.Lerp(la, lb, t);
                    if (float.IsNaN(E[i][k]) || lat > E[i][k]) E[i][k] = lat;
                }
            }
            // 覆わない所は近い所の値(脚の内)
            for (int k = 1; k < nS; k++) if (float.IsNaN(E[i][k])) E[i][k] = E[i][k - 1];
            for (int k = nS - 2; k >= 0; k--) if (float.IsNaN(E[i][k])) E[i][k] = E[i][k + 1];
        }
        for (int i = 0; i < nl; i++) if (float.IsNaN(E[i][0])) { float v = float.NaN; for (int d = 1; d < nl && float.IsNaN(v); d++) foreach (int j in new[] { i - d, i + d }) if (j >= 0 && j < nl && !float.IsNaN(E[j][0])) { v = j < i ? E[j][E[j].Length - 1] : E[j][0]; break; } for (int k = 0; k < E[i].Length; k++) E[i][k] = float.IsNaN(v) ? 0.3f : v; }
        var turn = new float[ch.Count]; for (int i = 1; i < nl; i++) turn[i] = Vector2.Angle(tl[i - 1], tl[i]);
        // 隅の際は両脚の包絡を同じ値(最大)に ── 両脚を平行に退ける
        for (int i = 1; i < nl; i++)
        {
            if (turn[i] < cornerDeg) continue; float m = float.MinValue; var A = E[i - 1]; var B = E[i];
            for (int k = 0; k < A.Length; k++) if (U[i - 1][k] >= Ll[i - 1] - cornerZone) m = Mathf.Max(m, A[k]);
            for (int k = 0; k < B.Length; k++) if (U[i][k] <= cornerZone) m = Mathf.Max(m, B[k]);
            for (int k = 0; k < A.Length; k++) if (U[i - 1][k] >= Ll[i - 1] - cornerZone) A[k] = m;
            for (int k = 0; k < B.Length; k++) if (U[i][k] <= cornerZone) B[k] = m;
        }
        // 段に割り、低い隣へは一駒で振って下ろす(角 ≤ rampMaxDeg)
        float kMax = Mathf.Tan(rampMaxDeg * Mathf.Deg2Rad);
        var T = new float[nl][];
        for (int i = 0; i < nl; i++)
        {
            var e = E[i]; int n = e.Length; var runA = new List<int>(); var runB = new List<int>(); var runV = new List<float>();
            { int a = 0; float mx = e[0], mn = e[0]; for (int k = 1; k <= n; k++) { bool brk = k == n || Mathf.Max(mx, e[k]) - Mathf.Min(mn, e[k]) > 0.05f; if (brk) { runA.Add(a); runB.Add(k - 1); runV.Add(mx); if (k < n) { a = k; mx = e[k]; mn = e[k]; } } else { mx = Mathf.Max(mx, e[k]); mn = Mathf.Min(mn, e[k]); } } }
            var t = new float[n]; for (int k = 0; k < n; k++) t[k] = float.MinValue;
            for (int r = 0; r < runV.Count; r++)
            {
                float vl = r > 0 ? runV[r - 1] : runV[r], vr = r + 1 < runV.Count ? runV[r + 1] : runV[r]; float dv = runV[r] - Mathf.Min(vl, vr);
                float slope = dv > 1e-3f ? Mathf.Min(kMax, dv / Mathf.Max(0.25f, rampLen)) : 1e3f;
                float ua = U[i][runA[r]], ub = U[i][runB[r]];
                for (int k = 0; k < n; k++) { float u = U[i][k]; float dist = u < ua ? ua - u : (u > ub ? u - ub : 0f); float v = runV[r] - slope * dist; if (v > t[k]) t[k] = v; }
            }
            T[i] = t;
        }
        // 溝の筋へ入った駒の所の足し(呼び手の解き直し ── 隅の際は一つの値)
        Func<Vector2, float> exq0 = q => extraAt != null ? extraAt(q) : 0f;   // 符号つき(呼び手の測りで前へも背へも)
        var cornerPts = new List<Vector2>(); for (int i = 1; i < nl; i++) if (turn[i] >= cornerDeg) cornerPts.Add(ch[i] + 0.5f * (nrm[i - 1] + nrm[i]) * T[i][0]);
        var cornerMax = new List<float>();
        foreach (var cp in cornerPts) { float m = 0f; for (float u = -2.5f; u <= 2.5f + 1e-3f; u += 0.25f) foreach (var d in new[] { new Vector2(1f, 0f), new Vector2(0f, 1f) }) m = Mathf.Max(m, exq0(cp + d * u)); cornerMax.Add(m); }
        Func<Vector2, float> exq = q => { float v = exq0(q); for (int k = 0; k < cornerPts.Count; k++) { float d = Vector2.Distance(q, cornerPts[k]); if (d <= 2.5f) v = Mathf.Max(v, cornerMax[k]); else v = Mathf.Max(v, cornerMax[k] * Mathf.Clamp01(1f - (d - 2.5f) / 2.5f)); } return v; };
        var envV = new List<Vector2>(); var toeV = new List<Vector2>(); var vLeg = new List<int>();
        Action<Vector2, Vector2, int> addV = (cv, tv, leg) => { envV.Add(cv); toeV.Add(tv); vLeg.Add(leg); };
        for (int i = 0; i < nl; i++)
        {
            float exA = i > 0 && turn[i] >= 3f ? 0.6f : 0f, exB = i + 1 < nl && turn[i + 1] >= 3f ? 0.6f : 0f; var t = T[i]; var e = E[i]; int n = t.Length;
            for (int k = 0; k < n; k++)
            {
                float u = U[i][k]; if ((i > 0 && u < exA) || (i + 1 < nl && u > Ll[i] - exB)) continue;
                bool keep = k == 0 || k == n - 1; if (!keep) { float d2 = (t[k + 1] - t[k]) - (t[k] - t[k - 1]); keep = Mathf.Abs(d2) > 0.004f; }
                if (i > 0 && k == 0) keep = false;
                if (i + 1 < nl && k == n - 1) keep = false;
                var cq = ch[i] + tl[i] * u + nrm[i] * e[k];
                float tq = t[k] + clr + exq(cq);
                if (t[k] - e[k] > 0.06f) rampPts.Add(new Vector3(cq.x, cq.y, t[k] - e[k]));
                if (keep) addV(cq, ch[i] + tl[i] * u + nrm[i] * tq, i);
            }
            if (i + 1 < nl)
            {   // 折れ: 前後の脚の線の交点
                float la = T[i][n - 1], lb = T[i + 1][0], ea = E[i][n - 1], eb = E[i + 1][0];
                Func<float, float, Vector2> X = (oa, ob) =>
                {
                    Vector2 p0 = ch[i + 1] + nrm[i] * oa, p1 = ch[i + 1] + nrm[i + 1] * ob; Vector2 d0 = tl[i], d1 = tl[i + 1]; float den = d0.x * d1.y - d0.y * d1.x;
                    if (Mathf.Abs(den) < 1e-4f || turn[i + 1] < 3f) return 0.5f * (p0 + p1);
                    Vector2 w = p1 - p0; float tt = (w.x * d1.y - w.y * d1.x) / den; var r = p0 + d0 * tt; return Vector2.Distance(r, ch[i + 1]) > 4f ? 0.5f * (p0 + p1) : r;
                };
                var xc = X(ea, eb); float xe = exq(xc); addV(xc, X(la + clr + xe, lb + clr + xe), i + 1);
            }
        }
        var toe = new List<Vector2>(); var el = new List<Vector2>(); var lg = new List<int>();
        for (int k = 0; k < toeV.Count; k++) { if (toe.Count > 0 && Vector2.Distance(toe[toe.Count - 1], toeV[k]) < 0.05f) continue; toe.Add(toeV[k]); el.Add(envV[k]); lg.Add(vLeg[k]); }
        for (int k = 0; k + 1 < toe.Count; k++) { Vector2 t2 = (toe[k + 1] - toe[k]).normalized, p = new Vector2(-t2.y, t2.x); int leg = lg[k]; if (Vector2.Dot(p, nrm[leg]) < 0f) p = -p; legN.Add(p); legOf.Add(leg); }
        // 測りの基準の包絡線は全ての升の点で(折れの際も)
        for (int i = 0; i < nl; i++) for (int k = 0; k < E[i].Length; k++) { envLine.Add(ch[i] + tl[i] * U[i][k] + nrm[i] * E[i][k]); envN.Add(nrm[i]); }
        return toe;
    }

    /// <summary>**点 q の包絡線からの符号つきの離れ**(背の向き +)── <see cref="MizoEnvelopeToeLine"/> の envLine(升の点の列)と点ごとの背の向き envN で、最も近い区間への離れ。</summary>
    public static float SignedFromEnvelope(List<Vector2> env, List<Vector2> envN, Vector2 q)
    {
        float bd = float.MaxValue, sd = float.NaN;
        for (int k = 0; k + 1 < env.Count; k++)
        {
            Vector2 a = env[k]; if (Mathf.Abs(a.x - q.x) > 3f || Mathf.Abs(a.y - q.y) > 3f) continue;
            Vector2 ab = env[k + 1] - a; float L2 = ab.sqrMagnitude; if (L2 < 1e-8f || L2 > 2.25f) continue; float tt = Mathf.Clamp01(Vector2.Dot(q - a, ab) / L2); var f = a + ab * tt; float d = (q - f).sqrMagnitude;
            if (d < bd) { bd = d; sd = Vector2.Dot(q - f, envN[k]); }
        }
        return sd;
    }

    /// <summary>**折れ線を頂点ごとの離れで背へ出す**(頂点の背の向き = 隣の区間の法線の二等分・離れ / cos(半角) ── 留めの交点)。区間の法線 <paramref name="segN"/>。
    /// 当たる先: 法尻の線から天端の前の縁の線を見付ごとの法の出で引く所(岡部 TW_Minami_Mizo)。</summary>
    public static List<Vector2> OffsetPolylineByVertex(IList<Vector2> pl, IList<Vector2> segN, IList<float> off)
    {
        var r = new List<Vector2>(); int n = pl.Count;
        for (int v = 0; v < n; v++)
        {
            Vector2 na = v > 0 ? segN[Mathf.Min(v - 1, segN.Count - 1)] : segN[0], nb = v < n - 1 ? segN[Mathf.Min(v, segN.Count - 1)] : segN[segN.Count - 1];
            Vector2 nv = (na + nb); if (nv.sqrMagnitude < 1e-6f) nv = nb; nv.Normalize(); float c = Mathf.Max(0.5f, Vector2.Dot(nv, nb));
            r.Add(pl[v] + nv * (off[v] / c));
        }
        return r;
    }

    /// <summary>**低い土留めの背は盛るだけ・切らない**(普請方 第139巡 northSideR139 N2【硬】「見え面から <paramref name="near"/> の内で天端を超える土だけを天端まで削る(切り ≤ <paramref name="cutMax"/>)・
    /// それより奥は触らない・天端の背の地盤が天端より低い所だけ天端 −<paramref name="fillDrop"/> まで盛り、その先は 1:<paramref name="bf"/> より緩く今の法へ擦り付ける・切りの擦り付けは書かない・
    /// 曲がりの背は二つの脚の背を一つの面として道のりで補う・天端の上の土は 1/<paramref name="drain"/> で溝の側へ」)。
    /// 天端 c(s) は据えた駒の実メッシュの天端(線から背へ <paramref name="near"/>・走り ±0.15 の頂点の最高)を道のりで補った一続きの線 ── 線 <paramref name="line"/> 全体を一本で
    /// (⛔ 脚ごとに書いて max/min で重ねない)。節点の背への離れは**線への最も近い所からの距離**(折れの外の扇も同じ面 ── 符号は頂点の二等分の向き)。
    /// 前(見え面の側)・区画の外・<paramref name="keepOut"/> は触らない。⟶ 記録の一行(削った・盛った・切りが上限で止まった節点)と、天端 − 背の地盤の測り(<paramref name="crestMinusBack"/> = [最小, 最大])。
    /// 当たる先: 法の途中に立てた低い土留めの背(岡部 TW_Minami_Mizo)── 小段を取る背は <see cref="CrestFollowBackBench"/>。</summary>
    public static string CrestBackFillOnly(string name, IList<GameObject> pieces, IList<Vector2> line, float near, float cutMax, float fillDrop, float bf, float drain,
                                           Vector2[] parcel, Func<Vector2, bool> keepOut, string recPath, out Vector2 crestMinusBack)
    {
        crestMinusBack = new Vector2(float.NaN, float.NaN);
        if (line == null || line.Count < 2 || pieces == null || pieces.Count == 0) return name + ": 線か駒が無い ── 描かない";
        int nL = line.Count; var cum = new float[nL]; for (int i = 1; i < nL; i++) cum[i] = cum[i - 1] + Vector2.Distance(line[i - 1], line[i]);
        float Ltot = cum[nL - 1]; if (Ltot < 0.1f) return name + ": 線が短い ── 描かない";
        // 背の向き: 駒の頂点の重心の側(区間ごと)── 線の左右のどちらに駒の控えが在るか
        var vs = new List<Vector3>(); foreach (var g in pieces) if (g != null && g.activeInHierarchy) vs.AddRange(Body(g.transform, 999999));
        var segN = new Vector2[nL - 1];
        for (int i = 0; i + 1 < nL; i++) { Vector2 t = (line[i + 1] - line[i]).normalized; segN[i] = new Vector2(-t.y, t.x); }
        { float sum = 0f; foreach (var v in vs) { var q = new Vector2(v.x, v.z); float dq; float s = NearestS(new List<Vector2>(line), q, out dq); int k = 0; for (int i = 0; i + 1 < nL; i++) if (s >= cum[i] - 1e-4f) k = i; sum += Vector2.Dot(q - line[k], segN[k]); }
          if (sum < 0f) for (int i = 0; i < segN.Length; i++) segN[i] = -segN[i]; }
        var vN = new Vector2[nL]; for (int v = 0; v < nL; v++) { Vector2 a = v > 0 ? segN[v - 1] : segN[0], b = v < nL - 1 ? segN[v] : segN[nL - 2]; var c = a + b; vN[v] = c.sqrMagnitude < 1e-6f ? b : c.normalized; }
        Func<Vector2, Vector2> proj = q =>
        {   // (道のり s, 背への離れ dn)── 最も近い所への距離。端点へ寄った所は頂点の二等分の向きで符号
            float bd = float.MaxValue; Vector2 r = new Vector2(float.NaN, float.NaN);
            for (int i = 0; i + 1 < nL; i++)
            {
                Vector2 a = line[i], ab = line[i + 1] - a; float L = ab.magnitude; if (L < 1e-4f) continue; Vector2 t = ab / L;
                float u = Vector2.Dot(q - a, t), uc = Mathf.Clamp(u, 0f, L); Vector2 f = a + t * uc; float d = Vector2.Distance(q, f);
                if (d < bd - 1e-5f)
                {
                    bd = d; Vector2 sn = uc <= 1e-4f ? vN[i] : (uc >= L - 1e-4f ? vN[i + 1] : segN[i]);
                    float sg = Vector2.Dot(q - f, sn) >= 0f ? 1f : -1f;
                    float sOut = (i == 0 && u < 0f) ? u : ((i == nL - 2 && u > L) ? cum[i] + u : cum[i] + uc);
                    r = new Vector2(sOut, sg * d);
                }
            }
            return r;
        };
        float ds = 0.25f; int nS = Mathf.CeilToInt(Ltot / ds) + 1; var cr = new float[nS]; for (int i = 0; i < nS; i++) cr[i] = float.NaN;
        foreach (var v in vs)
        {
            var pr = proj(new Vector2(v.x, v.z)); if (float.IsNaN(pr.x) || pr.y < -0.05f || pr.y > near) continue;
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
        float reach = near + bf * 3f + 2f * cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in line) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1; var H = td.GetHeights(x0, z0, w, h); int nCut = 0, nFill = 0, nCap = 0; float cutMx = 0f, fillMx = 0f, capMx = 0f; var rec = recPath != null ? new Dictionary<long, float>() : null;
        float cbMin = float.MaxValue, cbMax = float.MinValue;
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            if (parcel != null && !EdoGeom.PIP(parcel, p)) continue; if (keepOut != null && keepOut(p)) continue;
            var pr = proj(p); if (float.IsNaN(pr.x) || pr.y < 0f) continue;                       // 前(見え面の側)は触らない
            if (pr.x < -near || pr.x > Ltot + near) continue;                                      // 線の両端の先は触らない(端は打ち切りの駒が受ける)
            float c = crestAt(pr.x), cur = H[iz, ix] * ts.y + tp.y, nw = cur;
            if (pr.y <= near)
            {   // 天端の裏石の帯: 天端を超える土は天端まで(1/drain で溝の側へ下がる面)── 切り ≤ cutMax
                float capY = c;
                if (cur > capY + 1e-4f) { float want = Mathf.Max(capY, cur - cutMax); if (want > capY + 1e-3f) { nCap++; capMx = Mathf.Max(capMx, cur - capY); } nw = want; }
                float fillY = c - fillDrop - (near - pr.y) / Mathf.Max(1f, drain);
                if (cur < fillY - 1e-4f) nw = fillY;
            }
            else
            {   // 奥: 盛るだけ(天端 − fillDrop から 1:bf で下ろした面が今の地盤より高い所)
                float fillY = c - fillDrop - (pr.y - near) / bf;
                if (cur < fillY - 1e-4f) nw = fillY;
            }
            if (Mathf.Abs(nw - cur) < 1e-4f) continue;
            if (nw > cur) { nFill++; fillMx = Mathf.Max(fillMx, nw - cur); } else { nCut++; cutMx = Mathf.Max(cutMx, cur - nw); }
            H[iz, ix] = (nw - tp.y) / ts.y; if (rec != null) rec[((long)(x0 + ix) << 32) ^ (uint)(z0 + iz)] = nw;
        }
        if (nCut + nFill > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        if (rec != null && rec.Count > 0) AppendNodeTargets(recPath, t0.name, rec);
        // 測り: 天端 − 見え面から near の内の地盤の節点(書いた後の格子の値 ── 見え面の背の帯の内)。⛔ near の点の双一次で測らない(帯の外の節点を混ぜる)
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            if (parcel != null && !EdoGeom.PIP(parcel, p)) continue; if (keepOut != null && keepOut(p)) continue;
            var pr = proj(p); if (float.IsNaN(pr.x) || pr.y < 0f || pr.y > near || pr.x < 0f || pr.x > Ltot) continue;
            float dcb = crestAt(pr.x) - (H[iz, ix] * ts.y + tp.y); cbMin = Mathf.Min(cbMin, dcb); cbMax = Mathf.Max(cbMax, dcb);
        }
        if (cbMin < float.MaxValue) crestMinusBack = new Vector2(cbMin, cbMax);
        float cMin = float.MaxValue, cMax = float.MinValue; foreach (var c in cr) { cMin = Mathf.Min(cMin, c); cMax = Mathf.Max(cMax, c); }
        return name + ": 駒の天端 " + cMin.ToString("F2") + "〜" + cMax.ToString("F2") + "(" + Ltot.ToString("F1") + "m・一本の線・測った点 " + nHave + "/" + nS + ")・背は盛るだけ: 見え面から " + near.ToString("0.00")
             + " の内の天端を超える土を削った節点 " + nCut + "(最大 " + cutMx.ToString("F2") + (nCap > 0 ? "・⛔ 切り ≤" + cutMax.ToString("0.00") + " で止めた " + nCap + "(超え 最大 " + capMx.ToString("F2") + ")" : "・切り ≤" + cutMax.ToString("0.00") + " ⭕") + ")"
             + "・天端 −" + fillDrop.ToString("0.00") + " へ盛り 1:" + bf.ToString("0.0") + " で擦り付けた節点 " + nFill + "(最大 " + fillMx.ToString("F2") + ")"
             + "|天端 − 見え面から " + near.ToString("0.00") + " の内の地盤の節点 " + (cbMin < float.MaxValue ? cbMin.ToString("+0.00;-0.00") + "〜" + cbMax.ToString("+0.00;-0.00") + (cbMin < -0.005f ? " ⛔(天端の下に土【硬】)" : " ⭕") + (cbMax > 0.15f + 1e-3f ? "・⚠ 差 > 0.15 の所あり(狙い【柔】)" : "") : "-");
    }

    /// <summary>**野面の継ぎ目の天端の段**(測るだけ・普請方 第139巡 northSideR139 N1【硬: 継ぎ目の天端の段 ≤ maxStep】)。駒を線 <paramref name="line"/> の道のりの順に並べ、
    /// 隣どうしの継ぎ目(前の駒の走りの終わりと次の駒の始まりの中点)で、各駒の天端(継ぎ目の 0.2 内の頂点の最高)の差。⟶ 頭の一行(組・段の最大・超えた組)。
    /// 当たる先: 坂なりに走る野面の土留め(岡部 TW_Minami_Mizo)。</summary>
    public static string NozuraJointStepReport(IList<GameObject> pieces, List<Vector2> line, float maxStep, out float worst, out int nOver)
    {
        // 駒ごとの天端の線 = 道のり 0.1 の升ごとの頂点の最高(天端の石)を、駒の走りの中ほど(15〜85%)で一次式に当てた物 ── 継ぎ目の天端はその式を継ぎ目まで延ばした値。
        // ⛔ 継ぎ目の帯の頂点の最高で測らない(法の足の石が走りの先へ出て帯を外し、坂の駒では中ほどの高い石を拾う ── 0.5〜3.5 の偽の段)
        worst = 0f; nOver = 0; var items = new List<KeyValuePair<float, GameObject>>(); var fit = new Dictionary<GameObject, Vector4>();   // (a, b, sLo, sHi): y = a + b·s
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue; var vs = Body(g.transform, 999999); if (vs.Count == 0) continue;
            var bins = new Dictionary<int, float>(); float sLo = float.MaxValue, sHi = float.MinValue;
            foreach (var v in vs) { float dq; float s = NearestS(line, new Vector2(v.x, v.z), out dq); int b = Mathf.FloorToInt(s / 0.1f); float o; if (!bins.TryGetValue(b, out o) || v.y > o) bins[b] = v.y; }
            float yTop = float.MinValue; foreach (var kv in bins) yTop = Mathf.Max(yTop, kv.Value);
            //   走りの端 = 天端の帯(駒の最高から 1.0 の内 ── 坂の駒の低い端も入る)の升の端
            foreach (var kv in bins) if (kv.Value >= yTop - 1.0f) { sLo = Mathf.Min(sLo, kv.Key * 0.1f); sHi = Mathf.Max(sHi, (kv.Key + 1) * 0.1f); }
            if (sHi <= sLo) continue;
            double n = 0, sx = 0, sy = 0, sxx = 0, sxy = 0; float a0 = sLo + 0.15f * (sHi - sLo), a1 = sLo + 0.85f * (sHi - sLo);
            foreach (var kv in bins) { float s = (kv.Key + 0.5f) * 0.1f; if (s < a0 || s > a1) continue; n++; sx += s; sy += kv.Value; sxx += s * s; sxy += s * kv.Value; }
            if (n < 2) continue; double den = n * sxx - sx * sx; float bb = den > 1e-9 ? (float)((n * sxy - sx * sy) / den) : 0f; float aa = (float)((sy - bb * sx) / n);
            fit[g] = new Vector4(aa, bb, sLo, sHi); items.Add(new KeyValuePair<float, GameObject>(0.5f * (sLo + sHi), g));
        }
        items.Sort((a, b) => a.Key.CompareTo(b.Key)); string ww = ""; var ls = new List<string>();
        for (int k = 0; k + 1 < items.Count; k++)
        {
            var A = fit[items[k].Value]; var B = fit[items[k + 1].Value];
            if (B.z - A.w > 0.5f) continue;   // 離れた駒(端の打ち切りの後・区間の切れ)は継ぎ目でない
            float sj = 0.5f * (A.w + B.z), yA = A.x + A.y * sj, yB = B.x + B.y * sj, d = Mathf.Abs(yA - yB);
            if (d > maxStep + 1e-3f) { nOver++; ls.Add(items[k].Value.name + "×" + items[k + 1].Value.name + " " + d.ToString("F3")); }
            if (d > worst) { worst = d; ww = items[k].Value.name + "×" + items[k + 1].Value.name; }
        }
        return "継ぎ目の天端の段(組 " + Mathf.Max(0, items.Count - 1) + "・硬 ≤" + maxStep.ToString("0.00") + "・駒ごとの天端の一次式を継ぎ目へ延ばして): 最大 " + worst.ToString("F3") + (ww != "" ? " " + ww : "") + (nOver > 0 ? " ⛔ 超え " + nOver + " 組: " + string.Join("・", ls.GetRange(0, Mathf.Min(8, ls.Count)).ToArray()) : " ⭕");
    }

    /// <summary>**書いた節点に囲まれた書いていない節点を、隣の書いた値の平均で埋める**(普請方 第139巡 TW_Kita_Koshi.endRaiseR139【硬】「Stage3d の地面を書く手の最後に、
    /// 継ぎ目を閉じる手を一つ足す: 書いた節点に四方を囲まれた書いていない節点は、隣の書いた値の平均で埋める」)。記録(<paramref name="recPaths"/>)の節点を「書いた」とし、
    /// 書いていない節点の 4 連結の塊のうち、塊の外の隣がすべて書いた節点か駒の外形の中(<paramref name="hidden"/>)で、塊の節点が <paramref name="maxNodes"/> 以下の物を
    /// 囲まれた書き残しとする。値は書いた隣(今の地表)だけを固定して、塊の内を隣の平均へ繰り返し寄せる(1 升幅の帯は両脇の平均)。区画の外は触らない。
    /// 書いた高さは <paramref name="recOut"/> へ。⟶ 記録の一行。当たる先: 背の小段と擦り付けを別々に書く所すべて(岡部 TW_Kita_Koshi の返しの腕の先・TW_Kado_Sode の一枚の小段・
    /// SideEnd1・Higashi_Se の肩・溝の帯)。</summary>
    public static string CloseEnclosedUnwritten(IList<string> recPaths, Func<Vector2, bool> hidden, Vector2[] parcel, int maxNodes, string recOut)
    {
        var t = T(); var td = t.terrainData; int R = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size; float cell = ts.x / (R - 1);
        var wr = new HashSet<long>(); foreach (var rp in recPaths) { var m = LoadNodeTargets(rp, t.name); if (m != null) foreach (var k in m.Keys) wr.Add(k); }
        if (wr.Count == 0) return "囲まれた書き残し: 記録なし";
        Func<int, int, long> key = (ix, iz) => ((long)ix << 32) ^ (uint)iz;
        var cand = new HashSet<long>();
        foreach (var k in wr)
        {
            int ix = (int)(k >> 32), iz = (int)(uint)(k & 0xffffffffL);
            foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
            { int jx = ix + d.x, jz = iz + d.y; if (jx < 1 || jz < 1 || jx >= R - 1 || jz >= R - 1) continue; long kk = key(jx, jz); if (!wr.Contains(kk)) cand.Add(kk); }
        }
        var done = new HashSet<long>(); var openSet = new HashSet<long>(); int nComp = 0, nNodes = 0, nBig = 0; float upMx = 0f, dnMx = 0f; var rec = new Dictionary<long, float>(); var at = new List<string>();
        var Hc = new Dictionary<long, float>();
        Func<long, float> hgt = kk => { float v; if (Hc.TryGetValue(kk, out v)) return v; v = td.GetHeight((int)(kk >> 32), (int)(uint)(kk & 0xffffffffL)) + tp.y; Hc[kk] = v; return v; };
        Func<long, Vector2> pos = kk => new Vector2(tp.x + (int)(kk >> 32) * cell, tp.z + (int)(uint)(kk & 0xffffffffL) * cell);
        foreach (var c0 in cand)
        {
            if (done.Contains(c0) || wr.Contains(c0)) continue;
            var comp = new List<long>(); var q = new Queue<long>(); q.Enqueue(c0); done.Add(c0); bool open = false;
            while (q.Count > 0)
            {
                var k = q.Dequeue(); var p = pos(k);
                if (hidden != null && hidden(p)) continue;                          // 駒の外形の中は壁(塊に入れない)
                if (parcel != null && !EdoGeom.PIP(parcel, p)) { open = true; continue; }
                comp.Add(k); if (comp.Count > maxNodes) { open = true; break; }
                int ix = (int)(k >> 32), iz = (int)(uint)(k & 0xffffffffL);
                foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
                {
                    int jx = ix + d.x, jz = iz + d.y; if (jx < 1 || jz < 1 || jx >= R - 1 || jz >= R - 1) { open = true; continue; }
                    long kk = key(jx, jz); if (wr.Contains(kk)) continue; if (openSet.Contains(kk)) { open = true; continue; } if (done.Contains(kk)) continue; done.Add(kk); q.Enqueue(kk);
                }
            }
            if (open) { if (comp.Count > maxNodes) nBig++; foreach (var k in comp) openSet.Add(k); foreach (var k in q) openSet.Add(k); continue; }
            if (comp.Count == 0) continue;
            // 書いた隣を固定して塊の内を平均へ(ヤコビ 40 回)
            var cs = new HashSet<long>(comp); var val = new Dictionary<long, float>(); foreach (var k in comp) val[k] = hgt(k);
            for (int it = 0; it < 40; it++)
            {
                var nv = new Dictionary<long, float>();
                foreach (var k in comp)
                {
                    int ix = (int)(k >> 32), iz = (int)(uint)(k & 0xffffffffL); float acc = 0f; int n = 0;
                    foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
                    { long kk = key(ix + d.x, iz + d.y); if (cs.Contains(kk)) { acc += val[kk]; n++; } else if (wr.Contains(kk)) { acc += hgt(kk); n++; } }
                    nv[k] = n > 0 ? acc / n : val[k];
                }
                val = nv;
            }
            nComp++;
            foreach (var k in comp) { float cur = hgt(k), y = val[k]; if (Mathf.Abs(y - cur) < 1e-4f) continue; td.SetHeightsDelayLOD((int)(k >> 32), (int)(uint)(k & 0xffffffffL), new float[,] { { (y - tp.y) / ts.y } }); rec[k] = y; nNodes++; if (y > cur) upMx = Mathf.Max(upMx, y - cur); else dnMx = Mathf.Max(dnMx, cur - y); }
            if (comp.Count >= 3) { var p0 = pos(comp[0]); at.Add("(" + p0.x.ToString("F1") + "," + p0.y.ToString("F1") + ") " + comp.Count); }
        }
        // ⭐ 向かい合う二方を書いた節点に挟まれた帯(幅 ≤ 3 升)── 細い帯の端が書いていない広い所へ抜けていると塊の手では「囲まれていない」になる
        //   (岡部 TW_Kita_Koshi の返しの腕の先: 小段と擦り付けの間の一升幅・約 3m の帯は両端が外へ抜けていた)。挟む向きのうち短い方で一次に補う。
        int nSand = 0; float sMx = 0f;
        var cand2 = new HashSet<long>(cand);   // 幅 2〜3 升の帯の奥の節点は書いた節点に接しない ⇒ 候補を一升広げる
        foreach (var c0 in cand) { int ix = (int)(c0 >> 32), iz = (int)(uint)(c0 & 0xffffffffL); foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) }) { int jx = ix + d.x, jz = iz + d.y; if (jx < 1 || jz < 1 || jx >= R - 1 || jz >= R - 1) continue; long kk = key(jx, jz); if (!wr.Contains(kk)) cand2.Add(kk); } }
        foreach (var c0 in cand2)
        {
            if (wr.Contains(c0) || rec.ContainsKey(c0)) continue; var p = pos(c0); if (hidden != null && hidden(p)) continue; if (parcel != null && !EdoGeom.PIP(parcel, p)) continue;
            int ix = (int)(c0 >> 32), iz = (int)(uint)(c0 & 0xffffffffL); float best = float.NaN; int bestSpan = int.MaxValue;
            foreach (var ax in new[] { new Vector2Int(1, 0), new Vector2Int(0, 1) })
            {
                int a = 0, b = 0;
                for (int k = 1; k <= 3; k++) { long kk = key(ix - ax.x * k, iz - ax.y * k); if (wr.Contains(kk)) { a = k; break; } if (hidden != null && hidden(pos(kk))) break; }
                for (int k = 1; k <= 3; k++) { long kk = key(ix + ax.x * k, iz + ax.y * k); if (wr.Contains(kk)) { b = k; break; } if (hidden != null && hidden(pos(kk))) break; }
                if (a == 0 || b == 0 || a + b - 1 > 3 || a + b >= bestSpan) continue;
                float ya = hgt(key(ix - ax.x * a, iz - ax.y * a)), yb = hgt(key(ix + ax.x * b, iz + ax.y * b)); best = Mathf.Lerp(ya, yb, a / (float)(a + b)); bestSpan = a + b;
            }
            if (float.IsNaN(best)) continue; float cur = hgt(c0); if (Mathf.Abs(best - cur) < 1e-4f) continue;
            rec[c0] = best; nSand++; sMx = Mathf.Max(sMx, Mathf.Abs(best - cur));
        }
        // ⭐ 書いた面と駒の外形の間に残った帯(幅 ≤ 2 升)── 一方が書いた節点・向かいが駒の外形の中: 書いた面を外形まで延ばす
        //   (普請方 endRaiseR139【硬】「造成の書き手は、駒の外形の縁で止めず、外形の内へ 0.25 以上重ねて書く」を節点で ── 書き手ごとに外形の縁を避けた一升が残る所すべて)
        int nHull = 0; float hMx = 0f;
        if (hidden != null)
            foreach (var c0 in cand2)
            {
                if (wr.Contains(c0) || rec.ContainsKey(c0)) continue; var p = pos(c0); if (hidden(p)) continue; if (parcel != null && !EdoGeom.PIP(parcel, p)) continue;
                int ix = (int)(c0 >> 32), iz = (int)(uint)(c0 & 0xffffffffL); float best = float.NaN; int bestSpan = int.MaxValue;
                foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
                {
                    int a = 0, b = 0;   // a = 書いた節点まで(+d)・b = 外形の中まで(−d)
                    for (int k = 1; k <= 2; k++) { long kk = key(ix + d.x * k, iz + d.y * k); if (wr.Contains(kk)) { a = k; break; } if (hidden(pos(kk))) break; }
                    for (int k = 1; k <= 2; k++) { long kk = key(ix - d.x * k, iz - d.y * k); if (hidden(pos(kk))) { b = k; break; } if (wr.Contains(kk)) break; }
                    if (a == 0 || b == 0 || a + b - 1 > 2 || a + b >= bestSpan) continue;
                    best = hgt(key(ix + d.x * a, iz + d.y * a)); bestSpan = a + b;
                }
                if (float.IsNaN(best)) continue; float cur = hgt(c0); if (Mathf.Abs(best - cur) < 0.02f) continue;
                rec[c0] = best; nHull++; hMx = Mathf.Max(hMx, Mathf.Abs(best - cur));
            }
        //   書く(挟まれた帯は全部の値を決めてから ── 書いた値を隣の補いに混ぜない)
        foreach (var kv in rec) td.SetHeightsDelayLOD((int)(kv.Key >> 32), (int)(uint)(kv.Key & 0xffffffffL), new float[,] { { (kv.Value - tp.y) / ts.y } });
        if (nNodes + nSand + nHull > 0) td.SyncHeightmap();
        if (recOut != null && rec.Count > 0) AppendNodeTargets(recOut, t.name, rec);
        return "囲まれた書き残しを隣の書いた値の平均で埋めた(記録の節点 " + wr.Count + "・塊 ≤" + maxNodes + "): 塊 " + nComp + "・書いた節点 " + nNodes + "(上げ 最大 " + upMx.ToString("F2") + "・下げ 最大 " + dnMx.ToString("F2") + ")"
             + "・向かい合う二方に挟まれた幅 ≤3 升の書き残し " + nSand + " 節点(差 最大 " + sMx.ToString("F2") + ")・書いた面と駒の外形の間の幅 ≤2 升へ書いた面を延ばした " + nHull + " 節点(差 最大 " + hMx.ToString("F2") + ")"
             + (nBig > 0 ? "・大きい塊(囲まれていない扱い)" + nBig : "") + (at.Count > 0 ? "|" + string.Join("・", at.GetRange(0, Mathf.Min(8, at.Count)).ToArray()) : "");
    }
}
