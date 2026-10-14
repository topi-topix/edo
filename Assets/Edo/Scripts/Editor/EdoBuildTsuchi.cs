using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 地面を部材の実メッシュに合わせて切る・離す・擦り付ける手(EDO-0502 第138巡・普請方 2026-10-14 r137/r137b)。
// ⛔ 基準点・bounds で測らない ── 触れる所(段石の踏面・駒の外形・溝の帯の節点)を測って高さで指定する。
public static partial class EdoBuild
{
    /// <summary>**駒の外形の内か、縁から <paramref name="d"/> 以内か**を引く篩(実メッシュの頂点の水平の凸包 ── ⛔ bounds の矩形で篩わない)。
    /// 当たる先: 犬走り(練塀の足から 0.3)・棟の座の内へ盛らない篩すべて(岡部 TW_Kita_Koshi.endRaise の keepOut ── 第138巡 T5 で矩形の篩が
    /// 返しの背の 6m 四方を「犬走り」と読み、裏込めを止めていた)。</summary>
    public static Func<Vector2, bool> NearHulls(IList<GameObject> parts, float d)
    {
        var idx = new TopIndex(); foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g);
        return q =>
        {
            for (int k = 0; k < idx.hulls.Count; k++)
            {
                var b = idx.bounds[k]; if (q.x < b.x - d || q.x > b.z + d || q.y < b.y - d || q.y > b.w + d) continue;
                if (EdoGeom.PIP(idx.hulls[k], q) || EdgeDist(idx.hulls[k], q) < d) return true;
            }
            return false;
        };
    }

    /// <summary>**小段の背の向きを設計面の高い側へ揃える**(普請方 第137巡 r137b T4【硬】「小段の範囲は見え面の線から背の向きの符号つきの距離で取る・
    /// 見え面より前は触らない」)。各小段の線の中ほどから ±<paramref name="probe"/> の設計面(<see cref="BackBench.baseAt"/>)を測り、背の側が前の側より
    /// <paramref name="minDiff"/> を超えて低ければ back を裏返す(⛔ 線の向き・返しの向きの符号で決めない)。設計面が無い・差が小さい小段は触らない。
    /// ⟶ 裏返した小段の数(名は <paramref name="flipped"/> へ)。当たる先: BackBench を地形へ書く・皮の設計の地盤・GradeQA が読む小段すべて
    /// (岡部 延長の背の小段 sideEnd・出隅の踊り場・低い端の背の小段・脇の返しの背・端の天端上げ)。</summary>
    public static int OrientBenchesToHigh(IList<BackBench> ks, float probe, float minDiff, List<string> flipped)
    {
        int n = 0;
        foreach (var k in ks)
        {
            if (k == null || k.baseAt == null) continue;
            Vector2 m = (k.a + k.b) * 0.5f; float yB = k.baseAt(m + k.back * probe), yF = k.baseAt(m - k.back * probe);
            if (float.IsNaN(yB) || float.IsNaN(yF) || yB >= yF - minDiff) continue;
            k.back = -k.back; n++; if (flipped != null) flipped.Add(k.name + "(背 " + yB.ToString("F2") + " < 前 " + yF.ToString("F2") + ")");
        }
        return n;
    }

    /// <summary>**段石の真下の地盤を踏面より下へ切る**(普請方 第137巡 r137b T1【硬】「石段の平面の地盤は、各点で真上の段石の踏面の天端 −x 以下に高さで指定して切る・
    /// 段の上に土を載せない(描かれた地表 ≤ 踏面 −0.02)」)。節点ごとに、真上の段石の上を向いた面の最も高い所(<see cref="PartTops.RawTop"/> ── 実メッシュ)を踏面とし、
    /// 今の地盤が踏面 − <paramref name="below"/> より高ければそこへ下げる(切るだけ・⛔ 盛らない)。段石の無い所(背の平ら)は触らない。
    /// 書いた高さは <paramref name="recPath"/> へ(造成QA)。検め: 段石の踏面の 0.1 格子の点で、描かれた地形 − (踏面 − 0.02) の最大(≤ 0 で ⭕)。
    /// 当たる先: 平場の縁を切って張り出す石段すべて(岡部 K_Tsuyo・K_Dan1/2・K_Kuruwa)。⟶ 一行。</summary>
    public static string CutGroundUnderTreads(IList<GameObject> stones, float below, string recPath, IList<GameObject> cover = null)
    {
        // ⭐ 節点の踏面 = 節点とその周り(半径 1 升・8 方)の段石の上面の**最低**(第138巡の1回目: 節点の真上だけで測ると、段石の継ぎ目・蹴上の際の節点が切られず
        //   双一次の地表が下の段の踏面を 0.7 まで越えた)。段石の無い所(周りに一つも無い)は触らない。cover(脇の土留め)の上面が段石より高い点は検めで数えない(段石の端は土留めの下)
        var live = new List<GameObject>(); foreach (var g in stones) if (g != null && g.activeInHierarchy) live.Add(g);
        if (live.Count == 0) return "段石が無い ── 切らない";
        var tops = new PartTops(live); var idx = new TopIndex(); foreach (var g in live) idx.Add(g);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var b in idx.bounds) { mnx = Mathf.Min(mnx, b.x); mnz = Mathf.Min(mnz, b.y); mxx = Mathf.Max(mxx, b.z); mxz = Mathf.Max(mxz, b.w); }
        var t = T(); var td = t.terrainData; int R = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size; float cell = ts.x / (R - 1);
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / cell) - 1, 0, R - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / cell) - 1, 0, R - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / cell) + 1, 0, R - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / cell) + 1, 0, R - 1);
        var H = td.GetHeights(x0, z0, x1 - x0 + 1, z1 - z0 + 1); int n = 0; float mx = 0f; var rec = new Dictionary<long, float>();
        for (int iz = z0; iz <= z1; iz++) for (int ix = x0; ix <= x1; ix++)
        {
            float px = tp.x + ix * cell, pz = tp.z + iz * cell; float tr = tops.RawTop(px, pz);
            for (int a8 = 0; a8 < 8; a8++) { float an = a8 * Mathf.PI / 4f, v8 = tops.RawTop(px + cell * Mathf.Cos(an), pz + cell * Mathf.Sin(an)); if (!float.IsNaN(v8) && (float.IsNaN(tr) || v8 < tr)) tr = v8; }
            if (float.IsNaN(tr)) continue;
            float cur = H[iz - z0, ix - x0] * ts.y + tp.y, y = tr - below; if (cur <= y + 1e-4f) continue;
            mx = Mathf.Max(mx, cur - y); H[iz - z0, ix - x0] = (y - tp.y) / ts.y; n++; rec[((long)ix << 32) ^ (uint)iz] = y;
        }
        if (n > 0) { td.SetHeights(x0, z0, H); AssetDatabase.SaveAssetIfDirty(td); AppendNodeTargets(recPath, t.name, rec); }
        // 検め: 踏面の上に土が出ていないか(描かれた地形 = 双一次)
        float worst = float.MinValue; Vector2 wAt = Vector2.zero; int nPt = 0, nOver = 0, nCov = 0; PartTops cTops = null; if (cover != null && cover.Count > 0) cTops = new PartTops(cover);
        for (float x = mnx; x <= mxx; x += 0.1f) for (float z = mnz; z <= mxz; z += 0.1f)
        {
            float tr = tops.RawTop(x, z); if (float.IsNaN(tr)) continue;
            if (cTops != null) { float ct = cTops.RawTop(x, z); if (!float.IsNaN(ct) && ct > tr + 0.01f) { nCov++; continue; } }   // 段石の端が脇の土留めの下(見えない)
            float g = t.SampleHeight(new Vector3(x, 0f, z)) + tp.y; nPt++;
            float d = g - (tr - 0.02f); if (d > 1e-3f) nOver++; if (d > worst) { worst = d; wAt = new Vector2(x, z); }
        }
        return "段石の真下の地盤を踏面 −" + below.ToString("F2") + " へ切った: 段石 " + live.Count + "・節点 " + n + "・切り最大 " + mx.ToString("F2") + "m|検め 描かれた地表 − (踏面 −0.02) 最悪 "
             + (nPt == 0 ? "-" : worst.ToString("+0.000;-0.000") + " @(" + wAt.x.ToString("F1") + "," + wAt.y.ToString("F1") + ")") + "・超え " + nOver + "/" + nPt + " 点" + (nCov > 0 ? "(脇の土留めの下で数えない " + nCov + ")" : "") + (nOver > 0 ? " ⛔" : " ⭕");
    }

    /// <summary>**駒の天端から道へ一方向に離す**(普請方 第137巡 r137b T3【硬】「角の前の道の面は桝の天端 −0.02 から道へ 1/50 以上で離す(窪み無し)」)。
    /// 駒の実メッシュの水平の凸包からの距離 d の節点(<paramref name="where"/> が真の所・d ≤ <paramref name="radius"/>)を、
    /// 天端 <paramref name="top"/> − <paramref name="drop"/> − d × <paramref name="slope"/> より高ければそこへ下げる(切るだけ)。外形の内は触らない。
    /// 書いた高さは <paramref name="recPath"/> へ。当たる先: 道の際に据える桝・溝の頭(岡部 D_Corner_Masu)。⟶ 一行。</summary>
    public static string FallAwayFrom(GameObject piece, float top, float drop, float slope, float radius, Func<Vector2, bool> where, string recPath)
    {
        if (piece == null) return "駒が無い ── 離さない";
        var pts = new List<Vector2>(); foreach (var v in Body(piece.transform, 999999)) pts.Add(new Vector2(v.x, v.z));
        if (pts.Count < 3) return piece.name + ": 頂点が無い"; var hull = ConvexHull2(pts).ToArray();
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue; foreach (var q in hull) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        var t = T(); var td = t.terrainData; int R = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size; float cell = ts.x / (R - 1);
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - radius - tp.x) / cell), 0, R - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - radius - tp.z) / cell), 0, R - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + radius - tp.x) / cell), 0, R - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + radius - tp.z) / cell), 0, R - 1);
        var H = td.GetHeights(x0, z0, x1 - x0 + 1, z1 - z0 + 1); int n = 0; float mx = 0f; var rec = new Dictionary<long, float>();
        for (int iz = z0; iz <= z1; iz++) for (int ix = x0; ix <= x1; ix++)
        {
            var p = new Vector2(tp.x + ix * cell, tp.z + iz * cell); if (EdoGeom.PIP(hull, p)) continue; float d = EdgeDist(hull, p); if (d > radius) continue;
            if (where != null && !where(p)) continue;
            float cur = H[iz - z0, ix - x0] * ts.y + tp.y, y = top - drop - d * slope; if (cur <= y + 1e-4f) continue;
            mx = Mathf.Max(mx, cur - y); H[iz - z0, ix - x0] = (y - tp.y) / ts.y; n++; rec[((long)ix << 32) ^ (uint)iz] = y;
        }
        if (n > 0) { td.SetHeights(x0, z0, H); AssetDatabase.SaveAssetIfDirty(td); AppendNodeTargets(recPath, t.name, rec); }
        return piece.name + " の天端 " + top.ToString("F2") + " −" + drop.ToString("F2") + " から 1/" + (1f / Mathf.Max(slope, 1e-4f)).ToString("F0") + " で離した(" + radius.ToString("F1") + "m の内): 下げた節点 " + n + "・最大 " + mx.ToString("F3");
    }

    /// <summary>**溝の帯の外を 1:x で今の地盤へ擦り付ける**(普請方 第137巡 r137 K2 ②③【硬】「帯の外の縁から今の地盤へ 1:1.5 より緩く擦り付ける(切りも盛りも)・
    /// 擦り付けは練塀の犬走り・棟の座・区画の線の手前で止める・地盤との差が maxDiff を超える側は帯を延ばさず縁石の外に側石を一列積んで受ける」)。
    /// 帯の節点 <paramref name="band"/>(節点 → 書いた高さ)から外へ、距離 d の節点の高さを [帯 − d/x, 帯 + d/x] に収める(帯の値は最も近い帯の節点)。
    /// 帯の節点の今の地盤との差(帯の外の最初の節点で測る)が <paramref name="maxDiff"/> を超える所は擦り付けず、側石の要る所として <paramref name="sideNeed"/> へ
    /// (x, z, 差)を返す。<paramref name="keep"/> が真の節点は触らない。書いた高さは <paramref name="recPath"/> へ。⟶ 一行。
    /// 当たる先: 地表と面一に埋めた溝の両脇の帯すべて(岡部 D_MinamiHei の型A・型H の段落ち)。</summary>
    public static string TaperBandOutside(IDictionary<long, float> band, float x, float maxDiff, Func<Vector2, bool> keep, string recPath, List<Vector3> sideNeed)
    {
        if (band == null || band.Count == 0) return "帯の記録が無い ── 擦り付けない";
        var t = T(); var td = t.terrainData; int R = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size; float cell = ts.x / (R - 1);
        float reach = maxDiff * x + cell; int rN = Mathf.CeilToInt(reach / cell);
        int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
        foreach (var k in band.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
        i0 = Mathf.Max(0, i0 - rN); j0 = Mathf.Max(0, j0 - rN); i1 = Mathf.Min(R - 1, i1 + rN); j1 = Mathf.Min(R - 1, j1 + rN);
        var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
        // 帯の節点ごとに、帯の外の隣(4 近傍で帯でない節点)の今の地盤との差 ── 差が大きい帯の節点は側石で受ける(擦り付けの種にしない)
        var seeds = new List<long>(); int nSide = 0;
        foreach (var kv in band)
        {
            int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff); float worst = 0f; bool edge = false;
            foreach (var dd in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
            {
                int a = i + dd.x, b = j + dd.y; if (a < i0 || a > i1 || b < j0 || b > j1) continue; long kk = ((long)a << 32) ^ (uint)b; if (band.ContainsKey(kk)) continue;
                var q = new Vector2(tp.x + a * cell, tp.z + b * cell); if (keep != null && keep(q)) continue;
                edge = true; float cur = H[b - j0, a - i0] * ts.y + tp.y; worst = Mathf.Max(worst, Mathf.Abs(cur - kv.Value));
            }
            if (!edge) continue;
            if (worst > maxDiff + 1e-3f) { nSide++; if (sideNeed != null) sideNeed.Add(new Vector3(tp.x + i * cell, tp.z + j * cell, worst)); continue; }
            seeds.Add(kv.Key);
        }
        int n = 0; float mUp = 0f, mDn = 0f; var rec = new Dictionary<long, float>();
        for (int j = j0; j <= j1; j++) for (int i = i0; i <= i1; i++)
        {
            long k = ((long)i << 32) ^ (uint)j; if (band.ContainsKey(k)) continue;
            var p = new Vector2(tp.x + i * cell, tp.z + j * cell); if (keep != null && keep(p)) continue;
            float best = float.MaxValue, yb = float.NaN;
            foreach (var s in seeds)
            {
                int a = (int)(s >> 32), b = (int)(uint)(s & 0xffffffff); if (Mathf.Abs(a - i) > rN || Mathf.Abs(b - j) > rN) continue;
                float d = Mathf.Sqrt((a - i) * (a - i) + (b - j) * (b - j)) * cell; if (d < best) { best = d; yb = band[s]; }
            }
            if (float.IsNaN(yb) || best > reach) continue;
            float cur = H[j - j0, i - i0] * ts.y + tp.y, lo = yb - best / x, hi = yb + best / x, y = Mathf.Clamp(cur, lo, hi);
            if (Mathf.Abs(y - cur) < 1e-4f) continue;
            if (y > cur) mUp = Mathf.Max(mUp, y - cur); else mDn = Mathf.Max(mDn, cur - y);
            H[j - j0, i - i0] = (y - tp.y) / ts.y; n++; rec[k] = y;
        }
        if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); AppendNodeTargets(recPath, t.name, rec); }
        return "帯の外を 1:" + x.ToString("0.0") + " で今の地盤へ擦り付けた: 種 " + seeds.Count + "・節点 " + n + "(上げ最大 " + mUp.ToString("F2") + "・下げ最大 " + mDn.ToString("F2") + ")・差 > " + maxDiff.ToString("F2") + " で側石の要る帯の節点 " + nSide;
    }

    /// <summary>**天端と背の地盤の差を、各駒の控えの後端 +<paramref name="behind"/> の背で測る**(普請方 第137巡 r137b T2【硬】「検めは各駒の控えの後端 +0.05 の背の地盤で測る・
    /// 駒の外形の内は数えない(駒の下・見えない)」)。線の点ごとに、走り ±0.15 の駒の頂点のうち線から背へ [0, <paramref name="crestDepth"/>] の最高を天端、背の向きの射影の最大を
    /// 控えの後端とし、その +behind の点の地盤(<paramref name="ground"/>)と比べる。その点がどれかの駒の外形の内なら 0.05 ずつ 1.0 まで背へ送り、出なければ数えない。
    /// 超えた点は <paramref name="why"/> で「止めた相手」を添える。測るだけ。⟶ 一行(超えの数は <paramref name="nOver"/>)。当たる先: 袖の坂の硬い検め(岡部 TW_Kado_Sode・延長の袖)。</summary>
    public static string CrestBackDiffCheck(string key, IList<Vector2> line, IList<Vector2> back, float crestDepth, float maxDiff, float behind, IList<GameObject> pieces,
                                            Func<float, float, float> ground, Func<Vector2, string> why, out int nOver)
    {
        var vs = new List<Vector3>(); foreach (var g in pieces) if (g != null && g.activeInHierarchy) vs.AddRange(Body(g.transform, 999999));
        var idx = new TopIndex(); foreach (var g in pieces) if (g != null && g.activeInHierarchy) idx.Add(g);
        Func<Vector2, bool> inHull = q => { for (int k = 0; k < idx.hulls.Count; k++) { var b = idx.bounds[k]; if (q.x < b.x || q.x > b.z || q.y < b.y || q.y > b.w) continue; if (EdoGeom.PIP(idx.hulls[k], q)) return true; } return false; };
        float worst = float.MinValue; Vector2 wAt = Vector2.zero; float wC = 0f, wB = 0f; nOver = 0; int nPt = 0, nHid = 0; var over = new List<string>();
        for (int i = 0; i < line.Count; i++)
        {
            Vector2 p = line[i], n = back[Mathf.Min(i, back.Count - 1)], t = i + 1 < line.Count ? (line[i + 1] - p).normalized : (p - line[i - 1]).normalized;
            float top = float.MinValue, uB = float.MinValue;
            foreach (var v in vs) { Vector2 r = new Vector2(v.x, v.z) - p; if (Mathf.Abs(Vector2.Dot(r, t)) >= 0.15f) continue; float u = Vector2.Dot(r, n); if (u < 0f) continue; if (u <= crestDepth) top = Mathf.Max(top, v.y); if (u <= crestDepth + 2.0f) uB = Mathf.Max(uB, u); }
            if (top == float.MinValue || uB == float.MinValue) continue;
            Vector2 q = p + n * (uB + behind); float add = 0f; while (inHull(q) && add < 1.0f) { add += 0.05f; q += n * 0.05f; }
            if (inHull(q)) { nHid++; continue; }
            float bg = ground(q.x, q.y); if (float.IsNaN(bg)) continue;
            nPt++; float d = top - bg; if (d > maxDiff + 1e-3f) { nOver++; over.Add("(" + q.x.ToString("F1") + "," + q.y.ToString("F1") + ") " + d.ToString("+0.00") + (why != null ? " " + why(q) : "")); }
            if (d > worst) { worst = d; wAt = q; wC = top; wB = bg; }
        }
        return key + " の天端と背の地盤の差(硬 ≤ " + maxDiff.ToString("F2") + "・控えの後端 +" + behind.ToString("F2") + " の背・駒の外形の内は数えない): 最悪 " + (nPt == 0 ? "-" : worst.ToString("+0.00;-0.00")) + "m @(" + wAt.x.ToString("F1") + ", " + wAt.y.ToString("F1") + ")(天端 " + wC.ToString("F2") + "・背 " + wB.ToString("F2") + ")・超え " + nOver + "/" + nPt + " 点・外形の内で数えない " + nHid
             + (nOver > 0 ? " ⛔ " + string.Join(" / ", over.GetRange(0, Mathf.Min(12, over.Count)).ToArray()) + (over.Count > 12 ? " …" : "") : " ⭕");
    }
}
