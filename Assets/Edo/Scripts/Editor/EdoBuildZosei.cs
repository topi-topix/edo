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
                int best = -1; float bd = float.MaxValue;
                for (int k = 0; k < pads.Count; k++)
                {
                    float d = EdoGeom.PIP(pads[k], q) ? 0f : EdoGeom.DistToPolyEdge(pads[k], q);
                    d = Mathf.Max(0f, d - margin);
                    if (d < bd) { bd = d; best = k; }
                }
                if (best >= 0)
                {
                    float p = outp[best].y;
                    y = Mathf.Clamp(b, p - bd / fillRun, p + bd / cutRun);   // 地盤が低ければ盛土の法、高ければ切土の法で平場へ
                }
                float e = EdoGeom.DistToPolyEdge(parcel, q);
                float y2 = Mathf.Clamp(y, b - e / cutRun, b + e / fillRun);   // 縁で地山へ戻す(区画の外へ出さない)
                if (best >= 0 && bd <= 0f && Mathf.Abs(y2 - y) > 0.01f) outp[best].squeezed++;
                y = y2;
                if (y < b) maxCut = Mathf.Max(maxCut, b - y); else maxFill = Mathf.Max(maxFill, y - b);
                H[j, i] = Mathf.Clamp01((y - tp.y) / ts.y);
                written++;
            }
        td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        int sq = 0; foreach (var hb in outp) sq += hb.squeezed;
        report = string.Format("造成: 平場 {0} 面・節点 {1}(区画の中だけ・毎回造成前の地盤から)・最大の切土 {2:F2}m・盛土 {3:F2}m{4}",
                               pads.Count, written, maxCut, maxFill,
                               sq > 0 ? string.Format(" ⚠ 区画の縁に近く平らに取れない節点 {0}(土留めが要る所・P3)", sq) : "");
        return outp;
    }

    static Vector2 NodeXZ(Vector3 tp, Vector3 ts, int res, int i, int j)
    {
        return new Vector2(tp.x + i * ts.x / (res - 1), tp.z + j * ts.z / (res - 1));
    }
}
