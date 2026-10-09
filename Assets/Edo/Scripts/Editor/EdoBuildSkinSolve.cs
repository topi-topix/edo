// 縁の皮の高さを解く — 一点ごとに許される高さの幅 [lo, hi] を出し、その中で狙いに最も近い高さを採る(EdoBuild の partial・2026-10-10・EDO-0502)
//
// ⭐ **何が足りなかったか**(第84巡の棚卸し・施主裁定「作り直す」2026-10-10): <see cref="EdoBuild.CutEdgeSkin"/> の段3〜3f は、皮の節点の高さを
//    23 の決まりが上から順に書き換え、最後に書いた決まりが勝っていた(優先順位がどこにも無い)。上げる決まりと下げる決まりが打ち消し合い
//    (外形の中の設計 ↔ 天端の下 / 見え面の前へ出さない ↔ 据わりの守り / 隅の前 ↔ 尖り・窪み ↔ 平ら)、場所ごとの例外を継ぎ足すたびに
//    別の所が崩れた。さらに「駒の下」を駒全体の凸包で取っていた ── 野面は根入れの足で地表の 1.4m 前まで出るので、見えている前の地表まで
//    「駒の下」と扱い、門の内の右下に 1.95 の窪み・裂け目・腰石垣を覆う土の帯を作った。
//
// ⭕ 解き方(計画の図 https://claude.ai/artifact/DNoDgt4D7f4g5571d1syyc):
//    1. 設計の狙い y*【柔】= 面の高さ(面の中)/ 設計の地盤を面の縁から法で受けた高さ(面の外 ── CutEdgeSkin の OutsideY)/ 小口の土(hold)/
//       天端の裏石の帯の土(const.nozuraCrestCover の Target)/ 平らな面(flat)の高さ。順に上書きせず、点ごとに一つの値を返す(<see cref="SolveCtx.Target"/>)。
//    2. 硬い幅 [lo, hi] を全部の決まりから同時に出す(<see cref="SkinHeightSolve"/>):
//       hi ── 見えている駒の天端 −0.02(皮が天端に被らない)/ 野面・城の石垣の見え面 −0.02(見え面の前・根入れの土 = 前の地表までは許す)/
//             天端の前の帯(0〜front)は天端 − capDrop(指図 const.nozuraCrestCover)/ 平らな面 y + e(根入れを隠す土 coverD の内は y + coverH)
//       lo ── 駒の断面の中の点は駒の底 +0.05(本当に駒の下の所だけ)/ 駒の足の縁から一格子の外は底(隙 0)/ 平らな面 y − e /
//             天端の裏石の帯の上は天端 + minSoil(指図)
//       「駒の下」は凸包でなく、駒の実メッシュを y* の高さで水平に輪切りにした断面(縦の線の当たりの出入り ── <see cref="TopIndex.Column"/>)で取る【硬】。
//       根入れの足が地表の前へ出ていても、y* の高さの断面に入らなければ「前の地表」。
//    3. 採る高さ = clamp(y*, lo, hi)。
//    4. lo &gt; hi は「矛盾」── 場所・どの決まり同士か・差の量を <see cref="SkinSolveLog"/> へ刷り、暫定に hi を採る(土を石の上に出さない)【硬・黙って片方を勝たせない】。
//    5. 最後に尖り・窪み(8 近傍のどれよりも高い・低い点)を [lo, hi] の幅の中だけで一度均す【柔】。
//    ⛔ 場所ごとの例外を書かない(駒の名・座標・欄の名で分けない)。決まりは駒の実メッシュと指図の値だけで決まる。
//    当たる先: CutEdgeSkin に solve: true を渡す邸(いまは岡部 Stage3b だけ)。山王社・土井は従来の段3〜3f のまま(⛔ 流さない)。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>直近の <see cref="SkinHeightSolve"/> の報告(件数・矛盾の上位)。呼び手が刷る。</summary>
    public static string SkinSolveLog = "";
    /// <summary>診断: 点を入れると、その点に最も近い格子の点の y*・[lo, hi]・決まりの名を <see cref="SkinSolveTraceLog"/> へ刷る(null なら何もしない)。</summary>
    public static List<Vector2> SkinSolveTrace;
    public static System.Text.StringBuilder SkinSolveTraceLog = new System.Text.StringBuilder();

    /// <summary>皮の高さを解くための CutEdgeSkin の手持ち(段1〜2d で作った物)。</summary>
    sealed class SolveCtx
    {
        public TopIndex idx; public SkinDesign design; public List<SkinFace> fl; public float faceTol;
        public Func<Vector2, float> FaceY, HoldY; public Func<Vector2, bool[], float> OutsideY;
        public Func<int, int, bool> In, Hole; public Func<int, int, long> CK;
        public int ci0, cj0, ci1, cj1, N; public float step; public Vector3 org;
        public GroundProbe probe;
        // 内で作る
        public Func<Vector2, bool> otherPart;
        /// <summary>点 q が、平らな面の高さ y + e より高い天端を持つ石垣の天端の前の縁より背(0〜back+skirt)に在るか ── そこは石垣が受ける上の地盤で、平らな面の内ではない。</summary>
        public Func<Vector2, float, bool> behindHigherWall;
        /// <summary>設計の狙い y*【柔】(面・設計の地盤・小口の土・天端の裏石の帯の土・平らな面)。</summary>
        public float Target(Vector2 q)
        {
            float y = FaceY(q);
            if (!float.IsNaN(y)) { float hy = HoldY(q); if (!float.IsNaN(hy) && hy > y) y = hy; }
            else y = design != null ? OutsideY(q, null) : probe.At(q.x, q.y);
            if (design != null && design.crestCover != null)
            {
                var cc = design.crestCover; float tg = cc.Target(q);
                if (!float.IsNaN(tg) && tg > y && !cc.Protected(q) && !(cc.keepOut != null && cc.keepOut(q)) && !(otherPart != null && otherPart(q))) y = tg;
            }
            if (design != null && design.flats != null)
                foreach (var ff in design.flats)
                    if (ff.poly != null && EdoGeom.PIP(ff.poly, q) && !(ff.exempt != null && ff.exempt(q)) && !(behindHigherWall != null && behindHigherWall(q, ff.y + ff.e))) { y = ff.y; break; }
            return y;
        }
    }

    /// <summary>駒 k の縦の線の当たりから、立体の区間 [底, 天](一つ)。天 = 一番上の当たり、底 = 一番下の当たりが下を向く面ならその高さ・上を向く面なら −∞(底の無い殻)。
    /// ⭐ 野面は石の寄せ集め(中に面が重なる)── 出入りで区間を割らず、駒を一つの塊として輪切りにする。当たりが無ければ false。</summary>
    static bool SolidOf(List<Vector3> hits, int k, out float bot, out float top)
    {
        bot = float.NaN; top = float.NaN; float lowY = float.PositiveInfinity, lowN = 0f, topY = float.NegativeInfinity;
        foreach (var h in hits) { if ((int)h.x != k || Mathf.Abs(h.z) <= 0.02f) continue; if (h.y > topY) topY = h.y; if (h.y < lowY) { lowY = h.y; lowN = h.z; } }
        if (float.IsInfinity(topY)) return false;
        top = topY; bot = lowN < 0f && lowY < topY - 1e-4f ? lowY : float.NegativeInfinity; return true;
    }

    /// <summary>**皮の高さを解く**(CutEdgeSkin の段3〜3f の代わり ── solve: true のとき)。H・O・PIN・SUNK を埋める。
    /// 硬い条件は [lo, hi] に、柔らかい条件(設計の狙い)は y* に入れ、clamp(y*, lo, hi) を採る。lo &gt; hi は矛盾として刷る。</summary>
    static void SkinHeightSolve(SolveCtx c, IList<GameObject> parts, HashSet<GameObject> bandSet,
                                Dictionary<long, float> H, Dictionary<long, float> O, HashSet<long> PIN, HashSet<long> SUNK, ref SkinReport r)
    {
        var idx = c.idx; var design = c.design; float step = c.step; var org = c.org; var CK = c.CK;
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        var cc = design != null ? design.crestCover : null;
        // 覆う駒(野面)でない部材の外形の中と縁 0.2 は天端の裏石の帯の土を盛らない(⛔ 段石・踊り場の上へ土を被せない ── 指図 const.nozuraCrestCover ③ と同じ)
        if (cc != null)
        {
            c.otherPart = q =>
            {
                for (int h = 0; h < idx.hulls.Count; h++)
                {
                    if (h < idx.gos.Count && cc.pieceSet.Contains(idx.gos[h])) continue;
                    var hb = idx.bounds[h]; if (q.x < hb.x - 0.2f || q.x > hb.z + 0.2f || q.y < hb.y - 0.2f || q.y > hb.w + 0.2f) continue;
                    if (EdoGeom.PIP(idx.hulls[h], q) || EdgeDist(idx.hulls[h], q) < 0.2f) return true;
                }
                return false;
            };
            cc.otherPart = c.otherPart;
        }
        var buried = design != null ? design.buried : null;
        const float UNDER = 0.02f;   // 皮を面・天端の下へ納める量(硬 ── 被り 0 の検めの 1mm より深く)
        Func<int, bool> IsBuried = k => buried != null && k >= 0 && k < idx.gos.Count && buried.Contains(idx.gos[k]);
        Func<int, bool> IsCover = k => cc != null && k >= 0 && k < idx.gos.Count && cc.pieceSet.Contains(idx.gos[k]);
        var goIdx = new Dictionary<GameObject, int>(); for (int k = 0; k < idx.gos.Count; k++) if (idx.gos[k] != null && !goIdx.ContainsKey(idx.gos[k])) goIdx[idx.gos[k]] = k;
        // 帯で篩う駒(野面・城の石垣)ごとの見え面の帯(天端の前の縁 → 法尻の平面)── 野面の天端の裏石の帯(const.nozuraCrestCover)とは別に、全ての石垣で作る
        var wf = new NozuraCrestCover(); var wfBins = new Dictionary<int, List<int>>();
        for (int k = 0; k < idx.gos.Count; k++)
        {
            if (!idx.banded[k] || idx.gos[k] == null) continue; int n0 = wf.list.Count;
            var mf0 = idx.gos[k].GetComponentInChildren<MeshFilter>(); bool kado = mf0 != null && mf0.sharedMesh != null && mf0.sharedMesh.name.Contains("_Kado");
            try { wf.Add(idx.gos[k], kado); } catch (Exception) { }
            var l = new List<int>(); for (int q = n0; q < wf.list.Count; q++) l.Add(q); if (l.Count > 0) wfBins[k] = l;
        }
        // 前の地表(帯ごと): 法尻の 0.6 前の設計の狙い y*(柔の値 ── 前の地表の皮もこの値で描かれる)
        var frontCache = new Dictionary<long, float>();
        Func<int, int, Vector2, float> FrontG = (fi, b, q) =>
        {
            long kk = ((long)fi << 20) | (long)b; float v; if (frontCache.TryGetValue(kk, out v)) return v;
            var fb = wf.list[fi]; v = float.NaN; float fu = fb.footU[b];
            if (!float.IsNaN(fu)) { float a = fb.a0 + (b + 0.5f) * 0.1f; var qf = fb.t * a + fb.f * (fu + 0.6f); v = c.Target(qf); }
            frontCache[kk] = v; return v;
        };
        // 平らな面の高さ y + e より高い天端の石垣の背か(⛔ 平らな面の輪郭が石垣の背の上の地盤まで入っても、そこは平らに引かない)
        c.behindHigherWall = (q, yMax) =>
        {
            foreach (var fb in wf.list)
            {
                int b; float d; if (!wf.FaceAt(fb, q, out b, out d) || d < 0f || d > wf.back + wf.skirtMax) continue;
                if (fb.crest[b] > yMax) return true;
            }
            return false;
        };
        // **見えている面の上限**(点 q の縦の線の一番上の当たりで決める・硬):
        //   石段・溝などの天端 −0.02 / 城の石垣の天端 −0.02 / 石垣の見え面(天端の前の縁より前)は min(見え面の平面, 実の石の面) −0.02 ── ただし前の地表(根入れの土)までは許す。
        //   設計で埋める駒(design.buried)・野面の天端(天端の前の帯と裏石の帯は下で別に)・背の側は決めない(+∞)。
        Func<float, float, List<Vector3>, string[], float> VisCap = (qx, qz, hl, why) =>
        {
            float gTop = float.NegativeInfinity, gN = 0f; int gW = -1;
            foreach (var hh in hl) if (Mathf.Abs(hh.z) > 0.02f && hh.y > gTop) { gTop = hh.y; gN = hh.z; gW = (int)hh.x; }
            if (gW < 0 || gN <= 0f || IsBuried(gW)) return float.PositiveInfinity;
            if (!idx.banded[gW]) { why[0] = "天端−0.02〔" + idx.names[gW] + "〕"; return gTop - UNDER; }
            int wT; float crest = idx.Top(qx, qz, out wT);
            if (wT == gW && !float.IsNaN(crest))
            {
                if (IsCover(gW)) return float.PositiveInfinity;   // 野面の天端は天端の前の帯(capDrop)と裏石の帯(土)で決める
                why[0] = "天端−0.02〔" + idx.names[gW] + "〕"; return gTop - UNDER;
            }
            List<int> bl; if (!wfBins.TryGetValue(gW, out bl)) return float.PositiveInfinity;
            var q2 = new Vector2(qx, qz); float cap = float.PositiveInfinity;
            foreach (int fi in bl)
            {
                var fb = wf.list[fi]; int b; float d; if (!wf.FaceAt(fb, q2, out b, out d) || d >= 0f) continue;
                float face = Mathf.Min(wf.FacePlaneY(fb, b, Vector2.Dot(q2, fb.f)), gTop) - UNDER;
                float g = FrontG(fi, b, q2); float v = !float.IsNaN(g) && g > face ? g : face;
                if (v < cap) { cap = v; why[0] = "見え面−0.02/前の地表〔" + idx.names[gW] + "〕"; }
            }
            return cap;
        };
        float capDrop = cc != null && !float.IsNaN(cc.capDrop) ? cc.capDrop : 0.02f;
        float seatTol = Mathf.Max(0f, c.faceTol - 0.02f);   // 駒の底が y* の上 seatTol 以内なら据わっている(断面に入れる)── 指図 checks.gradeTol − 0.02(旧 sealFace と同じ許し)
        const float EMBED = 0.05f;

        var hits = new List<Vector3>(); var hitR = new List<Vector3>();
        var owners = new HashSet<int>(); var why1 = new string[1];
        var LO = new Dictionary<long, float>(); var HI = new Dictionary<long, float>(); var YS = new Dictionary<long, float>();
        var conflicts = new List<KeyValuePair<float, string>>(); var pairN = new Dictionary<string, int>();
        int nSec = 0, nTop = 0, nRing = 0, nBot = 0, nEdgeBot = 0, nFlat = 0, nSoil = 0, nCeil = 0, nClampUp = 0, nClampDn = 0;
        int[] D8i = { 1, -1, 0, 0, 1, 1, -1, -1 }, D8j = { 0, 0, 1, -1, 1, -1, 1, -1 };

        for (int i = c.ci0; i <= c.ci1; i++)
            for (int j = c.cj0; j <= c.cj1; j++)
            {
                if (!c.In(i, j)) continue;
                for (int a = 0; a <= c.N; a++)
                    for (int b = 0; b <= c.N; b++)
                    {
                        int gi = i * c.N + a, gj = j * c.N + b; long key = CK(gi, gj);
                        if (H.ContainsKey(key)) continue;
                        float x = org.x + gi * step, z = org.z + gj * step;
                        float orig = c.probe.At(x, z); O[key] = orig;
                        // 縁の点: 触れる升のどれかが穴でない ⇒ 地形に PIN【硬】
                        bool edge = false;
                        int iLo = (a == 0) ? i - 1 : i, iHi = (a == c.N) ? i + 1 : i, jLo = (b == 0) ? j - 1 : j, jHi = (b == c.N) ? j + 1 : j;
                        for (int ii = iLo; ii <= iHi && !edge; ii++) for (int jj = jLo; jj <= jHi && !edge; jj++)
                                if ((ii == i || a == 0 || a == c.N) && (jj == j || b == 0 || b == c.N) && !c.In(ii, jj)) edge = true;
                        bool ovOnly = true;
                        for (int ii = iLo; ii <= iHi && ovOnly; ii++) for (int jj = jLo; jj <= jHi && ovOnly; jj++)
                                if ((ii == i || a == 0 || a == c.N) && (jj == j || b == 0 || b == c.N) && c.Hole(ii, jj)) ovOnly = false;
                        if (edge) { H[key] = ovOnly ? orig - OV_SINK : orig; if (ovOnly) SUNK.Add(key); PIN.Add(key); continue; }
                        if (ovOnly) { H[key] = orig - OV_SINK; SUNK.Add(key); continue; }   // 地形の木の升の上へ被せるだけの点(地形の下へ沈めて隠す)

                        var p = new Vector2(x, z);
                        float ys = c.Target(p); if (float.IsNaN(ys)) ys = orig;
                        float lo = float.NegativeInfinity, hi = float.PositiveInfinity; string loWhy = "", hiWhy = "";
                        Action<float, string> Lo = (v, w) => { if (v > lo) { lo = v; loWhy = w; } };
                        Action<float, string> Hi = (v, w) => { if (v < hi) { hi = v; hiWhy = w; } };

                        // 平らな面(指図 flat ±e・帯を含む)── 狙い y* を面の高さに(帯の外の点も)。上限・下限は駒の断面の外だけ(下で)
                        FlatFace fHit = null;
                        if (design != null && design.flats != null)
                            foreach (var ff in design.flats)
                            {
                                if (ff.poly == null || (ff.exempt != null && ff.exempt(p)) || c.behindHigherWall(p, ff.y + ff.e)) continue;
                                bool inF = EdoGeom.PIP(ff.poly, p);
                                if (!inF && ff.band)
                                {
                                    float dE; Vector2 nE = HullNearest(ff.poly, p, out dE);
                                    if (dE <= ff.bandMax && (p - nE).sqrMagnitude > 1e-8f)
                                    {
                                        var dir = (p - nE).normalized;
                                        for (float tt = 0f; tt <= ff.bandMax - dE + 1e-3f && !inF; tt += 0.1f)
                                        {
                                            var qq = p + dir * tt;
                                            if (ff.bandHulls != null) { foreach (var bh in ff.bandHulls) if (EdoGeom.PIP(bh, qq)) { inF = true; break; } }
                                            else for (int hk = 0; hk < idx.hulls.Count && !inF; hk++) if (EdoGeom.PIP(idx.hulls[hk], qq)) inF = true;
                                        }
                                    }
                                }
                                if (inF) { fHit = ff; ys = ff.y; break; }
                            }

                        // 断面: 駒を y* 〜 y* + seatTol で輪切りにした断面に点が入るか(凸包でなく実メッシュの縦の線で)
                        idx.Column(x, z, hits, null);
                        owners.Clear(); foreach (var hh in hits) owners.Add((int)hh.x);
                        bool sectioned = false;
                        foreach (int k in owners)
                        {
                            float sb0, st0; if (!SolidOf(hits, k, out sb0, out st0)) continue;
                            if (st0 < ys || sb0 > ys + seatTol) continue;
                            sectioned = true; nSec++;
                            if (!float.IsInfinity(sb0)) { Lo(sb0 + EMBED, "駒の底+0.05〔" + idx.names[k] + "〕"); nBot++; }
                        }
                        // 見えている面の上限 ── この点と、皮の三角形が渡る周り(0.125・0.25 の 8 方向)の点で
                        { why1[0] = null; float v = VisCap(x, z, hits, why1); if (v < hi) { Hi(v, why1[0]); nTop++; } }
                        float eb = float.NaN; string ebW = null;
                        for (int d = 0; d < 8; d++)
                            for (int sI = 1; sI <= 2; sI++)
                            {
                                float qx = x + D8i[d] * step * 0.5f * sI, qz = z + D8j[d] * step * 0.5f * sI;
                                idx.Column(qx, qz, hitR, null); if (hitR.Count == 0) continue;
                                why1[0] = null; float v = VisCap(qx, qz, hitR, why1); if (v < hi) { Hi(v, "周り " + why1[0]); nRing++; }
                                // 駒の足の縁の外一格子(隙 0): 周りの点で駒の底が y* 〜 y* + seatTol(据わっている駒)なら、その底より下げない
                                if (!sectioned)
                                {
                                    owners.Clear(); foreach (var hh in hitR) owners.Add((int)hh.x);
                                    foreach (int k in owners) { float sb1, st1; if (!SolidOf(hitR, k, out sb1, out st1) || float.IsInfinity(sb1)) continue; if (sb1 > ys && sb1 <= ys + seatTol && st1 >= ys && (float.IsNaN(eb) || sb1 > eb)) { eb = sb1; ebW = idx.names[k]; } }
                                }
                            }
                        if (!float.IsNaN(eb)) { Lo(eb, "足の縁の底〔" + ebW + "〕"); nEdgeBot++; }
                        // 野面の天端の前の帯(0〜front)の天井 = 天端 − capDrop・裏石の帯の上の土 ≥ 天端 + minSoil(指図 const.nozuraCrestCover)── 設計で埋める駒の帯は除く
                        if (cc != null)
                        {
                            bool kOut = cc.keepOut != null && cc.keepOut(p);
                            foreach (var fb in cc.list)
                            {
                                if (fb.go == null || (buried != null && buried.Contains(fb.go))) continue;
                                int bb; float dd; if (!cc.FaceAt(fb, p, out bb, out dd) || float.IsNaN(fb.crest[bb])) continue;
                                if (dd >= 0f && dd < cc.front && !kOut) { Hi(fb.crest[bb] - capDrop, "天端の前の帯 天端−capDrop〔" + fb.go.name + "〕"); nCeil++; }
                            }
                            if (cc.Designed(p) && !(c.otherPart != null && c.otherPart(p)))
                            {
                                bool over = false; foreach (var pf in cc.pieceFaces) if (EdoGeom.PIP(pf.hull, p)) { over = true; break; }
                                float cb = cc.CrestInBand(p);
                                if (over && !float.IsNaN(cb)) { Lo(cb + cc.minSoil, "裏石の帯の土 ≥ " + cc.minSoil.ToString("F2", ci)); nSoil++; }
                            }
                        }
                        // 平らな面の幅(駒の断面の外だけ)── 根入れを隠す土 coverD の内は y + coverH まで(指図)
                        if (fHit != null && !sectioned)
                        {
                            var ff = fHit; float hl2 = ff.y + ff.e;
                            if (!float.IsNaN(ff.coverD) && !float.IsNaN(ff.coverH))
                                for (int hk = 0; hk < idx.hulls.Count; hk++) { var hb = idx.bounds[hk]; if (p.x < hb.x - ff.coverD || p.x > hb.z + ff.coverD || p.y < hb.y - ff.coverD || p.y > hb.w + ff.coverD) continue; if (EdoGeom.PIP(idx.hulls[hk], p) || EdgeDist(idx.hulls[hk], p) <= ff.coverD) { hl2 = ff.y + ff.coverH; break; } }
                            Lo(ff.y - ff.e, "平ら " + ff.name + " −e"); Hi(hl2, "平ら " + ff.name + " +e"); nFlat++;
                        }
                        float hgt;
                        if (lo > hi + 1e-4f)
                        {
                            hgt = hi; float dq = lo - hi;
                            string pr = loWhy.Split('〔')[0] + " × " + hiWhy.Split('〔')[0]; int pn; pairN.TryGetValue(pr, out pn); pairN[pr] = pn + 1;
                            conflicts.Add(new KeyValuePair<float, string>(dq, "(" + x.ToString("F2", ci) + ", " + z.ToString("F2", ci) + ") 差 " + dq.ToString("F3", ci) + " lo " + lo.ToString("F2", ci) + "〔" + loWhy + "〕 > hi " + hi.ToString("F2", ci) + "〔" + hiWhy + "〕 y* " + ys.ToString("F2", ci)));
                            LO[key] = hi; HI[key] = hi;
                        }
                        else
                        {
                            hgt = Mathf.Clamp(ys, lo, hi); if (hgt > ys + 1e-4f) nClampUp++; else if (hgt < ys - 1e-4f) nClampDn++;
                            LO[key] = lo; HI[key] = hi;
                        }
                        YS[key] = ys; H[key] = hgt;
                        if (SkinSolveTrace != null) foreach (var tq in SkinSolveTrace) if (Mathf.Abs(tq.x - x) <= step * 0.5f && Mathf.Abs(tq.y - z) <= step * 0.5f)
                                    SkinSolveTraceLog.AppendLine("  (" + x.ToString("F2", ci) + ", " + z.ToString("F2", ci) + ") y* " + ys.ToString("F3", ci) + " lo " + lo.ToString("F3", ci) + "〔" + loWhy + "〕 hi " + hi.ToString("F3", ci) + "〔" + hiWhy + "〕 ⇒ " + hgt.ToString("F3", ci) + " 断面 " + sectioned + " 当たり " + hits.Count);
                        if (orig - hgt > r.maxLower) { r.maxLower = orig - hgt; r.lowerAt = new Vector3(x, hgt, z); }
                        if (hgt - orig > r.maxRaise) { r.maxRaise = hgt - orig; r.raiseAt = new Vector3(x, hgt, z); }
                    }
            }
        // 5 尖り・窪みの均し【柔】: 決まりに押された点(y* から動いた点)のうち 8 近傍のどれよりも高い(低い)点を、近傍の平均との中ほどへ ── [lo, hi] の内だけ
        int nSm = 0;
        {
            var H0 = new Dictionary<long, float>(H);
            foreach (var kv in H0)
            {
                if (PIN.Contains(kv.Key) || !LO.ContainsKey(kv.Key) || Mathf.Abs(kv.Value - YS[kv.Key]) < 1e-3f) continue;   // 狙いのままの点(設計の形 ── 小口の土の盛り・池の岸)は均さない
                int gi = (int)(kv.Key >> 32), gj = (int)(uint)(kv.Key & 0xffffffff);
                float mx = float.MinValue, mn = float.MaxValue, sum = 0f; int n = 0;
                for (int d = 0; d < 8; d++) { float hn; if (H0.TryGetValue(CK(gi + D8i[d], gj + D8j[d]), out hn)) { mx = Mathf.Max(mx, hn); mn = Mathf.Min(mn, hn); sum += hn; n++; } }
                if (n < 8) continue;
                float y0 = kv.Value; if (!(y0 > mx || y0 < mn)) continue;
                float y1 = Mathf.Clamp(0.5f * (y0 + sum / n), LO[kv.Key], HI[kv.Key]);
                if (Mathf.Abs(y1 - y0) > 1e-4f) { H[kv.Key] = y1; nSm++; }
            }
        }
        r.pinned = PIN.Count;
        conflicts.Sort((u, v) => v.Key.CompareTo(u.Key));
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("皮の高さを解いた(SkinHeightSolve・一点ごとの [lo, hi] と狙い y*): 節点 " + LO.Count + "・縁の点(地形に PIN)" + PIN.Count
                      + "・断面に入った区間 " + nSec + "(底+0.05 " + nBot + ")・見えている面の上限 " + nTop + "(周りから " + nRing + ")・天端の前の帯の天井 " + nCeil
                      + "・裏石の帯の土 " + nSoil + "・平ら " + nFlat + "・足の縁の底 " + nEdgeBot + " / 狙いより上げた " + nClampUp + "・下げた " + nClampDn + "・尖り窪みの均し " + nSm);
        sb.AppendLine("  矛盾(lo > hi・硬 ── hi を採った): " + conflicts.Count + (conflicts.Count > 0 ? "(最大 " + conflicts[0].Key.ToString("F3", ci) + ")" : " ⭕"));
        if (pairN.Count > 0)
        {
            var pl = new List<KeyValuePair<string, int>>(pairN); pl.Sort((u, v) => v.Value.CompareTo(u.Value));
            var tp = new List<string>(); for (int q = 0; q < Mathf.Min(8, pl.Count); q++) tp.Add(pl[q].Key + " " + pl[q].Value);
            sb.AppendLine("    組: " + string.Join("・", tp.ToArray()));
        }
        for (int q = 0; q < Mathf.Min(10, conflicts.Count); q++) sb.AppendLine("    " + (q + 1) + ". " + conflicts[q].Value);
        SkinSolveLog = sb.ToString();
    }

    /// <summary>診断: 駒 <paramref name="parts"/>(帯で篩う駒 <paramref name="band"/>)の縦の線の当たり(持ち主・高さ・法線 y)と天端の帯の判定を点ごとに刷る。皮は起こさない。</summary>
    public static string SkinSolveProbe(IList<GameObject> parts, IList<GameObject> band, IList<Vector2> pts)
    {
        var idx = new TopIndex(); var bs = new HashSet<GameObject>(band ?? new List<GameObject>());
        foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g, bs.Contains(g));
        var sb = new System.Text.StringBuilder(); var hits = new List<Vector3>(); var ids = new List<int>(); var ci = System.Globalization.CultureInfo.InvariantCulture;
        foreach (var p in pts)
        {
            idx.Column(p.x, p.y, hits, ids); int wT; float cr = idx.Top(p.x, p.y, out wT);
            sb.Append("(" + p.x.ToString("F2", ci) + ", " + p.y.ToString("F2", ci) + ") 天端の帯 " + cr.ToString("F2", ci) + (wT >= 0 ? "〔" + idx.names[wT] + "〕" : "") + " 当たり:");
            var ord = new List<int>(); for (int q = 0; q < hits.Count; q++) ord.Add(q); ord.Sort((a, b) => hits[b].y.CompareTo(hits[a].y));
            foreach (var q in ord) { var n = idx.Normal(ids[q]); sb.Append(" " + idx.names[(int)hits[q].x] + " " + hits[q].y.ToString("F2", ci) + " n(" + n.x.ToString("F2", ci) + "," + n.y.ToString("F2", ci) + "," + n.z.ToString("F2", ci) + ")"); }
            sb.AppendLine();
        }
        return sb.ToString();
    }
}
