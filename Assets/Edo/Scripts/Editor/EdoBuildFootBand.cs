using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 壁の内の足元の帯(練塀・土塀・長屋の背の内の床)── 据えた駒の実メッシュから内面を測り、その面に沿う帯の地面を高さの式で書く(EDO-0502 第115巡)。
// ⛔ 部材の基準点で内面を決めない ── 内面は駒の実頂点(座の帯の中)で測る。⛔ 区画の外へ書かない(allow が false の節点は触らない)。
public static partial class EdoBuild
{
    /// <summary>足元の帯の一本(辺に沿う直線)。a = 線の始め・ax = 走りの向き(単位)・inw = 内向き(単位)・sLo/sHi = 帯の走りの範囲(内面を測った駒の範囲で埋める)・
    /// dIn = 内面の控え(線から内へ・<see cref="MeasureFootLines"/> が実メッシュで測る)・yAt(s) = 帯の高さ(NaN なら書かない)・fillOnly = 低い所だけ盛る(切らない)・seatAt(s) = 駒の座(内面の帯を拾う高さの窓)。</summary>
    public class FootLine
    {
        public string name; public Vector2 a, ax, inw; public float sLo = float.MaxValue, sHi = float.MinValue, dIn = float.MinValue, len;
        public Func<float, float> yAt, seatAt; public bool fillOnly, noFeather; public int nPts;
        public int nBand, nTap; public float up, dn;
        /// <summary>駒ごとの内面(x = sLo・y = sHi・z = その駒の頂点の 95% 点の控え)── 隅の駒は直線の駒より内へ出る(岡部 Dobei_Kado_00 で +0.55)ので、内面は走り s ごとに覆う駒で取る。</summary>
        public List<Vector3> spans = new List<Vector3>();
        /// <summary>走り s の内面の控え(覆う駒の最も内・覆う駒が無ければ dIn = 駒の中央値)。</summary>
        public float DInAt(float s) { float d = float.MinValue; foreach (var p in spans) if (s >= p.x - 1e-3f && s <= p.y + 1e-3f) d = Mathf.Max(d, p.z); return d > float.MinValue ? d : dIn; }
    }

    /// <summary>駒の実頂点(座 −0.1〜+0.5 の帯の中)を一番近い線へ割り当て、線ごとの内面の控え dIn(最も内)と走りの範囲を測る。
    /// L 字の隅の駒・留め柱も頂点ごとに線を選ぶので、帯は隅を回って切れ目なく続く。当たる先: 練塀・塀の内の足元の帯を書く所すべて(いまは岡部 heiFootSpec)。</summary>
    public static void MeasureFootLines(List<FootLine> lines, IEnumerable<GameObject> pieces)
    {
        foreach (var go in pieces)
        {
            if (go == null || !go.activeInHierarchy) continue;
            var per = new Dictionary<FootLine, List<Vector2>>();
            foreach (var v in BodyExRoof(go.transform, 999999))
            {
                var q = new Vector2(v.x, v.z); FootLine best = null; float bd = float.MaxValue, bs = 0f;
                foreach (var L in lines)
                {
                    float s = Vector2.Dot(q - L.a, L.ax), sc = Mathf.Clamp(s, 0f, L.len), d = Vector2.Distance(q, L.a + L.ax * sc);
                    if (d < bd) { bd = d; best = L; bs = s; }
                }
                if (best == null || bd > 3f) continue;
                float st = best.seatAt != null ? best.seatAt(Mathf.Clamp(bs, 0f, best.len)) : float.NaN;
                if (!float.IsNaN(st) && (v.y < st - 0.1f || v.y > st + 0.5f)) continue;
                List<Vector2> l; if (!per.TryGetValue(best, out l)) per[best] = l = new List<Vector2>(); l.Add(new Vector2(bs, Vector2.Dot(q - best.a, best.inw)));
            }
            foreach (var kv in per)
            {
                if (kv.Value.Count < 8) continue;   // 隣の辺の腕の端の数点は拾わない
                // 内面 = 駒の本体の頂点(中央値 + 0.30 以内)の 95% 点 ── 隅の駒 Dobei_Kado_00 は足元に内へ 0.5 張る小さな出(頂点の 16%)を持ち、
                //   全頂点の 95% 点はその出を内面と読んだ(第117巡: 隅の腕で埋まった辺1〜4 で内面が 0.84 → 1.33・小段の溝の芯が 0.49 内へずれた)
                var ds = kv.Value.ConvertAll(p => p.y); ds.Sort(); float med = ds[ds.Count / 2]; var dm = ds.FindAll(x => x <= med + 0.30f);
                float d95 = dm[Mathf.Min(dm.Count - 1, Mathf.FloorToInt(0.95f * dm.Count))];
                float lo = float.MaxValue, hi = float.MinValue; foreach (var p in kv.Value) { lo = Mathf.Min(lo, p.x); hi = Mathf.Max(hi, p.x); }
                var L = kv.Key; L.spans.Add(new Vector3(lo, hi, d95)); L.sLo = Mathf.Min(L.sLo, lo); L.sHi = Mathf.Max(L.sHi, hi); L.nPts += kv.Value.Count;
            }
        }
        foreach (var L in lines) { if (L.spans.Count == 0) continue; var zs = L.spans.ConvertAll(p => p.z); zs.Sort(); L.dIn = zs[zs.Count / 2]; }
    }

    /// <summary>**塀の内に沿う溝の芯の離れ(足の内の縁から)**(岡部 const.heiLine.innerDitch【硬】「溝の外の縁 = 足の内の縁 + clear 以上」・第125巡)── 狙いの離れ
    /// <paramref name="want"/>(足の内の縁 = <see cref="FootLine.dIn"/> から芯まで)と、溝の駒の外の縁(<see cref="MizoPieceOf"/> の横の |x| の最大 ── 地際の張り出し・板を含む)が
    /// 足の内の縁 + <paramref name="clear"/> に来る離れの大きい方。駒の幅・深さは変えない(線だけ内へ平行に移す)。⟶ 離れ・<paramref name="halfMax"/> = 駒の外の縁の半幅の最大。
    /// 硬い(塀の足が溝・桝に掛からない)/ 狙い want は柔らかい(離れが want を越えたら呼び手が ⚠ と床の狭まり = 離れ − want を刷る)。
    /// 当たる先: 塀の内に沿う溝・桝(岡部 D_MinamiHei の main・yuka・west・桝 G0)── 同じ型の土井 D11・他邸の塀の内の溝は未適用。</summary>
    public static float DitchCoreOff(float want, float clear, IEnumerable<string> piecePaths, out float halfMax)
    {
        halfMax = 0f;
        foreach (var p in piecePaths) { var m = MizoPieceOf(p); if (!m.ok) continue; halfMax = Mathf.Max(halfMax, Mathf.Max(Mathf.Abs(m.xMin), Mathf.Abs(m.xMax))); }
        return Mathf.Max(want, clear + halfMax);
    }

    /// <summary>**内の足元の帯を書く**(硬: 帯の中は yAt・柔: 帯の外 featherN の勾配で今の地面へ摺り付け)。節点ごとに一番近い線(走りの範囲 [sLo, sHi] で切った距離)を選び、
    /// 内面からの離れ d = (節点 − 線)·inw − dIn が [from, to] なら帯・(to, to + reach] なら摺り付け。allow(q) が false の節点(区画の外・線から半升)は触らない。
    /// fillOnly の線は低い所だけ盛る。⟶ 書いた節点の数。当たる先: 練塀の内の足元の床を座で受ける所(岡部 角 P0 の南・辺4・5 の溝の床・辺6 の頭)。</summary>
    public static int WriteFootBand(List<FootLine> lines, float from, float to, float featherN, float reach, Func<Vector2, bool> allow) { return WriteFootBand(lines, from, to, featherN, reach, allow, float.NaN); }
    /// <summary><paramref name="featherCutN"/>: 切る側の摺り付けの勾配 1:n(NaN = 盛る側と同じ <paramref name="featherN"/>)── 盛 1:1.5・切 1:1.0 のように分ける帯(岡部 const.heiLine.tenba の内の帯・第121巡)。</summary>
    public static int WriteFootBand(List<FootLine> lines, float from, float to, float featherN, float reach, Func<Vector2, bool> allow, float featherCutN)
    {
        if (float.IsNaN(featherCutN)) featherCutN = featherN;
        var use = lines.FindAll(L => L.nPts > 0 && L.dIn > float.MinValue && L.yAt != null);
        if (use.Count == 0) return 0;
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue; float pad = Mathf.Max(0f, -from) + to + reach + 0.5f;
        foreach (var L in use) foreach (var s in new[] { L.sLo, L.sHi }) foreach (var dd in new[] { L.DInAt(s) + from - 1.0f, L.DInAt(s) + to + reach + 1.0f, L.dIn + from - 1.0f, L.dIn + to + reach + 1.0f })
                { var p = L.a + L.ax * s + L.inw * dd; x0 = Mathf.Min(x0, p.x - pad); x1 = Mathf.Max(x1, p.x + pad); z0 = Mathf.Min(z0, p.y - pad); z1 = Mathf.Max(z1, p.y + pad); }
        int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 - org.x) / hs));
        int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 - org.z) / hs));
        if (i1 < i0 || j1 < j0) return 0;
        var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1); int n = 0;
        for (int j = j0; j <= j1; j++)
            for (int i = i0; i <= i1; i++)
            {
                var q = new Vector2(org.x + i * hs, org.z + j * hs); if (allow != null && !allow(q)) continue;
                FootLine best = null; float bd = float.MaxValue, bs = 0f;
                foreach (var L in use)
                {
                    float s = Vector2.Dot(q - L.a, L.ax), sc = Mathf.Clamp(s, L.sLo, L.sHi);
                    float d = Vector2.Distance(q, L.a + L.ax * sc + L.inw * L.DInAt(sc));
                    if (d < bd) { bd = d; best = L; bs = s; }
                }
                if (best == null || bs < best.sLo - 1e-3f || bs > best.sHi + 1e-3f) continue;
                float dI = Vector2.Dot(q - best.a, best.inw) - best.DInAt(bs); if (dI < from - 1e-4f || dI > to + (best.noFeather ? 0f : reach)) continue;
                float yB = best.yAt(bs); if (float.IsNaN(yB)) continue;
                float cur = H[j - j0, i - i0] * td.size.y + org.y, y;
                if (dI <= to + 1e-4f) { y = best.fillOnly ? Mathf.Max(cur, yB) : yB; if (Mathf.Abs(y - cur) > 1e-4f) best.nBand++; }
                else { float lim = (dI - to) / featherN, limC = (dI - to) / featherCutN; y = cur < yB ? Mathf.Max(cur, yB - lim) : (best.fillOnly ? cur : Mathf.Min(cur, yB + limC)); if (Mathf.Abs(y - cur) > 1e-4f) best.nTap++; }
                if (Mathf.Abs(y - cur) < 1e-4f) continue;
                if (y > cur) best.up = Mathf.Max(best.up, y - cur); else best.dn = Mathf.Max(best.dn, cur - y);
                H[j - j0, i - i0] = (y - org.y) / td.size.y; n++;
            }
        if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        return n;
    }

    /// <summary>節点 q が帯の中なら帯の高さ(一番近い線の yAt)・帯の外・低い所だけ盛る線なら NaN ── 駒の下を下げる処理の下限に使う(帯の上に埋まった駒の天端で帯を掘らない)。</summary>
    public static float FootBandAt(List<FootLine> lines, Vector2 q, float from, float to)
    {
        FootLine best = null; float bd = float.MaxValue, bs = 0f;
        foreach (var L in lines) { if (L.nPts == 0 || L.yAt == null) continue; float s = Vector2.Dot(q - L.a, L.ax), sc = Mathf.Clamp(s, L.sLo, L.sHi); float d = Vector2.Distance(q, L.a + L.ax * sc + L.inw * L.DInAt(sc)); if (d < bd) { bd = d; best = L; bs = s; } }
        if (best == null || best.fillOnly || bs < best.sLo - 1e-3f || bs > best.sHi + 1e-3f) return float.NaN;
        float dI = Vector2.Dot(q - best.a, best.inw) - best.DInAt(bs); if (dI < from - 1e-4f || dI > to + 1e-4f) return float.NaN;
        return best.yAt(bs);
    }

    /// <summary>**足の浮き・埋まりを測る**(測るだけ)── 駒ごとに、足 = 駒の実頂点の最も低い所(据えた駒は水平 ⇒ 足は一本の高さ)、内面 = その駒の頂点の 95% 点の控え。
    /// 駒が覆う走りの区間を 0.25m ごとに、内面の 0.05 内の地表と比べる。浮き = 足 − 地表(> 0 が浮き・⛔ 低ポリの面の頂点は端にしか無いので升ごとの最低で測らない)。
    /// ⟶ 線ごとの 浮きの最大・埋まりの最小/最大・測った点の数。</summary>
    public static string FootFloatReport(List<FootLine> lines, IEnumerable<GameObject> pieces)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var stat = new Dictionary<FootLine, Vector4>(); var at = new Dictionary<FootLine, string>(); foreach (var L in lines) { stat[L] = new Vector4(float.MinValue, float.MaxValue, float.MinValue, 0); at[L] = "-"; }
        foreach (var go in pieces)
        {
            if (go == null || !go.activeInHierarchy) continue;
            var vs = BodyExRoof(go.transform, 999999); if (vs.Count == 0) continue; float bot = float.MaxValue; foreach (var v in vs) bot = Mathf.Min(bot, v.y);
            var per = new Dictionary<FootLine, List<Vector2>>();
            foreach (var v in vs)
            {
                var q = new Vector2(v.x, v.z); FootLine best = null; float bd = float.MaxValue, bs = 0f;
                foreach (var L in lines) { if (L.nPts == 0) continue; float s = Vector2.Dot(q - L.a, L.ax), sc = Mathf.Clamp(s, 0f, L.len), d = Vector2.Distance(q, L.a + L.ax * sc); if (d < bd) { bd = d; best = L; bs = s; } }
                if (best == null || bd > 3f) continue; List<Vector2> l; if (!per.TryGetValue(best, out l)) per[best] = l = new List<Vector2>(); l.Add(new Vector2(bs, Vector2.Dot(q - best.a, best.inw)));
            }
            foreach (var kv in per)
            {
                if (kv.Value.Count < 8) continue; var L = kv.Key; var ds = kv.Value.ConvertAll(p => p.y); ds.Sort(); float d95 = ds[Mathf.Min(ds.Count - 1, Mathf.FloorToInt(0.95f * ds.Count))];
                float lo = float.MaxValue, hi = float.MinValue; foreach (var p in kv.Value) { lo = Mathf.Min(lo, p.x); hi = Mathf.Max(hi, p.x); }
                lo = Mathf.Max(lo, Mathf.Max(0f, L.sLo)); hi = Mathf.Min(hi, Mathf.Min(L.len, L.sHi));
                var st = stat[L];
                for (float s = lo + 0.05f; s <= hi - 0.05f + 1e-4f; s += 0.25f)
                {
                    var q = L.a + L.ax * s + L.inw * (d95 + 0.05f); float g = Ground(q.x, q.y), f = bot - g;
                    if (f > st.x) { st.x = f; at[L] = go.name + " s" + s.ToString("F2", inv); }
                    st.y = Mathf.Min(st.y, -f); st.z = Mathf.Max(st.z, -f); st.w += 1;
                }
                stat[L] = st;
            }
        }
        var sb = new System.Text.StringBuilder();
        foreach (var L in lines)
        {
            var st = stat[L]; if (st.w == 0) { sb.Append(L.name + " 足 0 点・"); continue; }
            sb.Append(L.name + " 足 " + st.w.ToString("0") + " 点・浮き 最大 " + st.x.ToString("+0.000;-0.000", inv) + (st.x <= 1e-3f ? " ⭕" : " ⛔ @" + at[L]) + "・埋まり " + st.y.ToString("F2", inv) + "〜" + st.z.ToString("F2", inv) + " / ");
        }
        return sb.ToString();
    }

    /// <summary>**低い窪みを面へ盛る**(硬: 窪み無し・面 yMin 以上)── seeds から 4 近傍で、今の地面 &lt; yMin かつ stop(q) が false の節点を広げ(半径 rMax・節点 nMax まで)、
    /// 面 = yMin + fall × (排け口の節点までの距離) へ盛る(低い所だけ・切らない)。排け口 = 広げた先で stop だった節点のうち outlet(q) が true の物(路地の床など)。
    /// ⟶ 盛った節点・体積・排け口の数。当たる先: 塀の隅の小庭の窪み(岡部 角の庭)。</summary>
    public static string FillPocket(List<Vector2> seeds, float yMin, float fall, float rMax, int nMax, Func<Vector2, bool> stop, Func<Vector2, bool> outlet, Func<Vector2, float> yCap, List<Vector2> filled = null)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        if (seeds == null || seeds.Count == 0) return "窪み: 種が無い";
        Vector2 c0 = Vector2.zero; foreach (var sd in seeds) c0 += sd; c0 /= seeds.Count; int ci = Mathf.RoundToInt((c0.x - org.x) / hs), cj = Mathf.RoundToInt((c0.y - org.z) / hs), rr = Mathf.CeilToInt(rMax / hs) + 2;
        int i0 = Mathf.Max(0, ci - rr), i1 = Mathf.Min(R - 1, ci + rr), j0 = Mathf.Max(0, cj - rr), j1 = Mathf.Min(R - 1, cj + rr);
        var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1); int W = i1 - i0 + 1, Hh = j1 - j0 + 1;
        Func<int, int, Vector2> P = (i, j) => new Vector2(org.x + (i + i0) * hs, org.z + (j + j0) * hs);
        Func<int, int, float> G = (i, j) => H[j, i] * td.size.y + org.y;
        var inSet = new bool[W, Hh]; var seen = new bool[W, Hh]; var q = new Queue<Vector2Int>(); var outs = new List<Vector2>(); var set = new List<Vector2Int>();
        foreach (var s in seeds) { int i = Mathf.RoundToInt((s.x - org.x) / hs) - i0, j = Mathf.RoundToInt((s.y - org.z) / hs) - j0; if (i < 0 || j < 0 || i >= W || j >= Hh || seen[i, j]) continue; seen[i, j] = true; var p = P(i, j); if (stop(p) || G(i, j) >= yMin) continue; inSet[i, j] = true; q.Enqueue(new Vector2Int(i, j)); set.Add(new Vector2Int(i, j)); }
        while (q.Count > 0 && set.Count < nMax)
        {
            var u = q.Dequeue();
            foreach (var dv in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
            {
                int i = u.x + dv.x, j = u.y + dv.y; if (i < 0 || j < 0 || i >= W || j >= Hh || seen[i, j]) continue; seen[i, j] = true;
                var p = P(i, j); if (Vector2.Distance(p, c0) > rMax) continue;
                if (stop(p)) { if (outlet != null && outlet(p)) outs.Add(p); continue; }
                if (G(i, j) >= yMin) continue;
                inSet[i, j] = true; q.Enqueue(new Vector2Int(i, j)); set.Add(new Vector2Int(i, j));
            }
        }
        int nw = 0; float vol = 0f, upMax = 0f;
        foreach (var u in set)
        {
            var p = P(u.x, u.y); float dmin = float.MaxValue; foreach (var o in outs) dmin = Mathf.Min(dmin, Vector2.Distance(p, o)); if (outs.Count == 0) dmin = 0f;
            float y = yMin + fall * dmin; if (yCap != null) { float cp = yCap(p); if (!float.IsNaN(cp)) y = Mathf.Min(y, Mathf.Max(yMin, cp)); }
            float cur = G(u.x, u.y); if (y <= cur + 1e-4f) continue;
            vol += (y - cur) * hs * hs; upMax = Mathf.Max(upMax, y - cur); H[u.y, u.x] = (y - org.y) / td.size.y; nw++;
        }
        if (nw > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        if (filled != null) foreach (var u in set) filled.Add(P(u.x, u.y));
        return "窪みを盛った: 節点 " + nw + "(広げた " + set.Count + (set.Count >= nMax ? " ⚠ 上限で止めた" : "") + ")・盛り 最大 " + upMax.ToString("F2", inv) + "m・" + vol.ToString("F1", inv) + "m³・面 " + yMin.ToString("F2", inv) + " + " + fall.ToString("0.000", inv) + "×(排け口まで)・排け口の節点 " + outs.Count;
    }
}
