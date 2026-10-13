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

    /// <summary>**据えた駒の平面の外形の索引**(駒ごとに壁体の頂点の凸包・2m の升で引く)── 「その節点の地面は駒に覆われて見えないか」を問う(<see cref="Covers"/>)。
    /// 造成QA が駒の下の地面(溝・石垣の下げ・塀の足の下の上げ ── 駒の外形の中と縁の一升)を超過と別に刷るのに使う(EDO-0502 第129巡)。
    /// ⛔ 凸包なので L 字の駒は入りの三角を含む(覆うと読む側に倒れる)── 隅の駒は腕ごとの駒でないと甘く読む。当たる先: 造成QA(岡部)。</summary>
    public class HullIndex
    {
        readonly List<Vector2[]> hulls = new List<Vector2[]>(); readonly List<Vector4> box = new List<Vector4>();
        readonly Dictionary<long, List<int>> cells = new Dictionary<long, List<int>>();
        static long K(int x, int z) { return ((long)x << 32) ^ (uint)z; }
        public int Count { get { return hulls.Count; } }
        public void Add(GameObject g)
        {
            if (g == null || !g.activeInHierarchy) return;
            var vs = Body(g.transform, 4000); if (vs.Count < 3) return;
            var pts = new List<Vector2>(vs.Count); foreach (var v in vs) pts.Add(new Vector2(v.x, v.z));
            var h = ConvexHull2(pts); if (h == null || h.Count < 3) return;
            var ha = h.ToArray(); float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var q in ha) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
            int id = hulls.Count; hulls.Add(ha); box.Add(new Vector4(x0, z0, x1, z1));
            for (int ix = Mathf.FloorToInt(x0 / 2f) - 1; ix <= Mathf.FloorToInt(x1 / 2f) + 1; ix++)
                for (int iz = Mathf.FloorToInt(z0 / 2f) - 1; iz <= Mathf.FloorToInt(z1 / 2f) + 1; iz++)
                { List<int> l; long k = K(ix, iz); if (!cells.TryGetValue(k, out l)) cells[k] = l = new List<int>(); l.Add(id); }
        }
        /// <summary>点 q が駒の外形の中か、外形から <paramref name="pad"/> 以内か。</summary>
        public bool Covers(Vector2 q, float pad)
        {
            List<int> l; if (!cells.TryGetValue(K(Mathf.FloorToInt(q.x / 2f), Mathf.FloorToInt(q.y / 2f)), out l)) return false;
            foreach (var id in l)
            {
                var b = box[id]; if (q.x < b.x - pad || q.x > b.z + pad || q.y < b.y - pad || q.y > b.w + pad) continue;
                if (EdoGeom.PIP(hulls[id], q) || (pad > 0f && EdgeDistPublic(hulls[id], q) <= pad)) return true;
            }
            return false;
        }
    }

    /// <summary>書いた帯の**設計**(線・内面の控え・走りの範囲・帯の高さ yAt を 0.1m ごとに)を <paramref name="path"/> へ残す(上書き)。造成QA が domain reload の後も
    /// 同じ帯を引けるように(帯の線は据えた駒の実メッシュと天端の線から解くので、算出物 graded は知らない)。⛔ 地形の今の高さは書かない ── 欄の式の値だけ。
    /// 当たる先: WriteFootBand を呼ぶ所(岡部 天端の線の内の帯・heiFootSpec の帯)── EDO-0502 第129巡。</summary>
    public static void SaveFootBand(string path, List<FootLine> lines, float from, float to, float featherN, float featherCutN, float reach)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder();
        sb.AppendLine("P\t" + from.ToString("R", inv) + "\t" + to.ToString("R", inv) + "\t" + featherN.ToString("R", inv) + "\t" + (float.IsNaN(featherCutN) ? featherN : featherCutN).ToString("R", inv) + "\t" + reach.ToString("R", inv));
        foreach (var L in lines)
        {
            if (L.nPts == 0 || L.dIn <= float.MinValue || L.yAt == null) continue;
            sb.AppendLine("L\t" + L.name + "\t" + L.a.x.ToString("R", inv) + "\t" + L.a.y.ToString("R", inv) + "\t" + L.ax.x.ToString("R", inv) + "\t" + L.ax.y.ToString("R", inv) + "\t" + L.inw.x.ToString("R", inv) + "\t" + L.inw.y.ToString("R", inv)
                        + "\t" + L.len.ToString("R", inv) + "\t" + L.sLo.ToString("R", inv) + "\t" + L.sHi.ToString("R", inv) + "\t" + L.dIn.ToString("R", inv) + "\t" + L.nPts + "\t" + (L.noFeather ? 1 : 0) + "\t" + (L.fillOnly ? 1 : 0));
            foreach (var sp in L.spans) sb.AppendLine("S\t" + sp.x.ToString("R", inv) + "\t" + sp.y.ToString("R", inv) + "\t" + sp.z.ToString("R", inv));
            var ys = new List<string>(); for (float sv = 0f; sv <= L.len + 1e-4f; sv += 0.1f) ys.Add(L.yAt(sv).ToString("R", inv));
            sb.AppendLine("Y\t0.1\t" + string.Join("\t", ys.ToArray()));
        }
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
        System.IO.File.WriteAllText(path, sb.ToString());
    }

    /// <summary><see cref="SaveFootBand"/> で残した帯を読み直す(yAt は 0.1m ごとの値の一次補間)。無ければ null。</summary>
    public static List<FootLine> LoadFootBand(string path, out float from, out float to, out float featherN, out float featherCutN, out float reach)
    {
        from = to = featherN = featherCutN = reach = float.NaN;
        if (!System.IO.File.Exists(path)) return null;
        var inv = System.Globalization.CultureInfo.InvariantCulture; var res = new List<FootLine>(); FootLine cur = null;
        foreach (var ln in System.IO.File.ReadAllLines(path))
        {
            var f = ln.Split('\t'); if (f.Length == 0) continue;
            if (f[0] == "P" && f.Length >= 6) { from = float.Parse(f[1], inv); to = float.Parse(f[2], inv); featherN = float.Parse(f[3], inv); featherCutN = float.Parse(f[4], inv); reach = float.Parse(f[5], inv); }
            else if (f[0] == "L" && f.Length >= 15)
            {
                cur = new FootLine { name = f[1], a = new Vector2(float.Parse(f[2], inv), float.Parse(f[3], inv)), ax = new Vector2(float.Parse(f[4], inv), float.Parse(f[5], inv)), inw = new Vector2(float.Parse(f[6], inv), float.Parse(f[7], inv)),
                                     len = float.Parse(f[8], inv), sLo = float.Parse(f[9], inv), sHi = float.Parse(f[10], inv), dIn = float.Parse(f[11], inv), nPts = int.Parse(f[12]), noFeather = f[13] == "1", fillOnly = f[14] == "1" };
                res.Add(cur);
            }
            else if (f[0] == "S" && cur != null && f.Length >= 4) cur.spans.Add(new Vector3(float.Parse(f[1], inv), float.Parse(f[2], inv), float.Parse(f[3], inv)));
            else if (f[0] == "Y" && cur != null && f.Length >= 3)
            {
                float st = float.Parse(f[1], inv); var v = new float[f.Length - 2]; for (int i = 2; i < f.Length; i++) v[i - 2] = float.Parse(f[i], inv);
                cur.yAt = sv => { if (v.Length == 0) return float.NaN; float u = Mathf.Clamp(sv / st, 0f, v.Length - 1); int i0 = Mathf.FloorToInt(u), i1 = Mathf.Min(v.Length - 1, i0 + 1); return Mathf.Lerp(v[i0], v[i1], u - i0); };
            }
        }
        return res;
    }

    /// <summary>節点 q が帯 [from, to] か摺り付け (to, to + reach] の中なら帯の高さ(一番近い線の yAt・<see cref="WriteFootBand"/> と同じ線の選び)、外なら NaN。
    /// <paramref name="dI"/> = 内面からの離れ(帯の中か摺り付けかを呼び手が分ける)。測るだけ ── 造成QA が「設計面からの差が帯の跡か」を数える(式を二重に持たない)。
    /// 当たる先: WriteFootBand で書いた帯を持つ邸の造成QA(岡部 天端の線の内の帯・EDO-0502 第129巡)。</summary>
    public static float FootBandReachAt(List<FootLine> lines, Vector2 q, float from, float to, float reach, out float dI)
    {
        dI = float.NaN; FootLine best = null; float bd = float.MaxValue, bs = 0f;
        foreach (var L in lines)
        {
            if (L.nPts == 0 || L.dIn <= float.MinValue || L.yAt == null) continue;
            float s = Vector2.Dot(q - L.a, L.ax), sc = Mathf.Clamp(s, L.sLo, L.sHi); float d = Vector2.Distance(q, L.a + L.ax * sc + L.inw * L.DInAt(sc));
            if (d < bd) { bd = d; best = L; bs = s; }
        }
        if (best == null || bs < best.sLo - 1e-3f || bs > best.sHi + 1e-3f) return float.NaN;
        float di = Vector2.Dot(q - best.a, best.inw) - best.DInAt(bs); if (di < from - 1e-4f || di > to + (best.noFeather ? 0f : reach) + 1e-4f) return float.NaN;
        dI = di; return best.yAt(bs);
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

    /// <summary>**塀の足の頂点の石の上の浮き**(測るだけ・2026-10-14 EDO-0502 第131巡 ── 普請検査の hei2 の測りを関数へ写し、隣の駒の閉じを足した)。
    /// 駒ごとに足の頂点(0.25m の升ごとの最も低い頂点 +0.02 の内)の真下の石の面(<paramref name="stones"/> の三角形・頂点 +0.3 より下で最も高い所)を測り、浮き = 頂点 − 面。
    /// 下 1m に石が無い点は「石なし」(地面の上 ── この測りの外)。⭐ 浮いた点の真下の隙が**隣の塀の駒の躯体で閉じる**(隣の駒の足の外形の 0.03 内で、隣の駒の底 ≤ 面 + 0.02・
    /// 天端 ≥ 頂点)なら、見えない隙として別に数える(第130巡: 上の段の棟止め NW_Hei_1_TomeA の足の隅の頂点が下の段の台の天端の上 0.91 に出ていたが、下の段の塀の躯体がその下を閉じ、内外の近景で隙は見えない)。
    /// ⟶ 頭の一行(駒・点・浮き・閉じ・最大)+ 浮きの駒ごとの行。当たる先: 段を下る練塀・棟止めの足と台の石垣の取り合い(岡部の外周)── 塀を石の天端に据える邸すべて。</summary>
    public static string HeiFootOnStoneReport(IList<GameObject> walls, IList<GameObject> stones, out int nFloat, out float worst)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; nFloat = 0; worst = 0f;
        var sbb = new List<Bounds>(); foreach (var st in stones) sbb.Add(RB(st));
        var triCache = new Dictionary<GameObject, Vector3[]>();
        Func<GameObject, Vector3[]> tris = g => { Vector3[] r; if (triCache.TryGetValue(g, out r)) return r; var L = new List<Vector3>(); foreach (var mf in g.GetComponentsInChildren<MeshFilter>()) { if (mf.sharedMesh == null) continue; var vs = mf.sharedMesh.vertices; var ts = mf.sharedMesh.triangles; var m = mf.transform.localToWorldMatrix; var w = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]); for (int i = 0; i < ts.Length; i++) L.Add(w[ts[i]]); } r = L.ToArray(); triCache[g] = r; return r; };
        Func<Vector3[], float, float, float, float> hitY = (T, x, z, yTop) => { float best = float.NegativeInfinity; for (int i = 0; i + 2 < T.Length; i += 3) { Vector3 a = T[i], b = T[i + 1], c = T[i + 2]; if (x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || z < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || z > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue; float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue; float l1 = ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / d, l2 = ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / d, l3 = 1 - l1 - l2; if (l1 < -1e-4f || l2 < -1e-4f || l3 < -1e-4f) continue; float y = l1 * a.y + l2 * b.y + l3 * c.y; if (y <= yTop && y > best) best = y; } return best; };
        // 隣の塀の駒: 足の外形(屋根を除く躯体)・底・天端
        var wHull = new Dictionary<GameObject, List<Vector2>>(); var wBot = new Dictionary<GameObject, float>(); var wTop = new Dictionary<GameObject, float>(); var wB = new Dictionary<GameObject, Bounds>();
        foreach (var w in walls) { if (w == null || !w.activeInHierarchy) continue; var vs = BodyExRoof(w.transform, 999999); if (vs.Count < 3) continue; float y0 = float.MaxValue, y1 = float.MinValue; var xz = new List<Vector2>(); foreach (var v in vs) { y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); xz.Add(new Vector2(v.x, v.z)); } var h = ConvexHull2(xz); if (h.Count < 3) continue; wHull[w] = h; wBot[w] = y0; wTop[w] = y1; wB[w] = RB(w); }
        var lines = new List<string>(); int pieces = 0, ptsAll = 0, ptsFl = 0, ptsClosed = 0, ptsVoid = 0; string flW = "";
        foreach (var pc in walls)
        {
            if (pc == null || !pc.activeInHierarchy || !wHull.ContainsKey(pc)) continue;
            var pa = Body(pc.transform, 999999, false); if (pa.Count == 0) continue;
            var cellMin = new Dictionary<long, float>();
            foreach (var v in pa) { long k = ((long)Mathf.FloorToInt(v.x / 0.25f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.25f); float o; if (!cellMin.TryGetValue(k, out o) || v.y < o) cellMin[k] = v.y; }
            var b = RB(pc); b.Expand(new Vector3(0.2f, 4f, 0.2f)); var near = new List<Vector3[]>(); for (int i = 0; i < stones.Count; i++) if (stones[i] != null && stones[i].activeInHierarchy && sbb[i].Intersects(b)) near.Add(tris(stones[i]));
            if (near.Count == 0) continue;
            var nbs = new List<GameObject>(); var bb = wB[pc]; bb.Expand(0.3f); foreach (var kv in wB) if (kv.Key != pc && kv.Value.Intersects(bb)) nbs.Add(kv.Key);
            pieces++; int pf = 0, pcl = 0; float pmax = 0f; Vector3 pat = Vector3.zero; string clBy = ""; var seen = new HashSet<long>();
            foreach (var v in pa)
            {
                int cx = Mathf.FloorToInt(v.x / 0.25f), cz = Mathf.FloorToInt(v.z / 0.25f); long k = ((long)cx << 32) ^ (uint)cz; if (v.y > cellMin[k] + 0.02f) continue; long k2 = ((long)Mathf.RoundToInt(v.x * 50) << 32) ^ (uint)Mathf.RoundToInt(v.z * 50); if (!seen.Add(k2)) continue;
                //   ⭐ 足でない頂点を外す: 隣の升(3×3)に 0.05 より低い頂点が在れば、その頂点は小口・切った端の面の上の点(低ポリの駒は底の頂点が隅にしか無い ──
                //   第131巡 N_Hei_26_1_4 の 0.202 は端の小口の面の頂点 19.31 で、隣の升の足は 19.00)。坂なりの駒は 0.35m で 0.05 より下らない(1/7 以下)。
                { bool lower = false; for (int ix = -1; ix <= 1 && !lower; ix++) for (int iz = -1; iz <= 1 && !lower; iz++) { float o; if (cellMin.TryGetValue(((long)(cx + ix) << 32) ^ (uint)(cz + iz), out o) && o < v.y - 0.05f) lower = true; } if (lower) continue; }
                float best = float.NegativeInfinity; foreach (var T in near) { float y = hitY(T, v.x, v.z, v.y + 0.3f); if (y > best) best = y; }
                ptsAll++; if (float.IsNegativeInfinity(best) || v.y - best > 1.0f) { ptsVoid++; continue; }
                float g = v.y - best; if (g <= 0.01f) continue;
                GameObject cl = null; var q = new Vector2(v.x, v.z);
                foreach (var nb in nbs) { if (wBot[nb] > best + 0.02f || wTop[nb] < v.y) continue; float gp = PointHullGapXZ(q, wHull[nb]); if (!float.IsNaN(gp) && gp <= 0.03f) { cl = nb; break; } }
                if (cl != null) { pcl++; ptsClosed++; clBy = cl.name; continue; }
                pf++; ptsFl++; if (g > pmax) { pmax = g; pat = v; }
            }
            if (pf > 0) { nFloat++; if (pmax > worst) { worst = pmax; flW = pc.name; } lines.Add("    浮き " + pc.name + " 点 " + pf + " 最大 " + pmax.ToString("F3", inv) + " @(" + pat.x.ToString("F2", inv) + "," + pat.y.ToString("F2", inv) + "," + pat.z.ToString("F2", inv) + ")" + (pcl > 0 ? "・隣で閉じる " + pcl : "")); }
            else if (pcl > 0) lines.Add("    閉じ " + pc.name + " 点 " + pcl + "(隣の駒 " + clBy + " の躯体が隙を閉じる ── 見えない)");
        }
        return "塀の足の頂点の石の上の浮き(> 0.01): 駒 " + pieces + "・足の点 " + ptsAll + "・浮き " + ptsFl + " 点(駒 " + nFloat + ")最大 " + worst.ToString("F3", inv) + (nFloat == 0 ? " ⭕" : " ⛔ " + flW)
             + "・隣の塀の駒の躯体が閉じる " + ptsClosed + " 点(見えない)・下 1m に石なし " + ptsVoid + "\n" + string.Join("\n", lines.ToArray());
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
