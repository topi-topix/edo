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
        readonly Dictionary<long, float> outCache = new Dictionary<long, float>();
        /// <summary>点 q が、平らな面の高さ y + e より高い天端を持つ石垣の天端の前の縁より背(0〜back+skirt)に在るか ── そこは石垣が受ける上の地盤で、平らな面の内ではない。</summary>
        public Func<Vector2, float, bool> behindHigherWall;
        /// <summary>点 q が、面の高さ fy を背で受ける石垣(天端 ≈ fy ± gradeTol・背の点は同じ面・前の地表は別の面)の天端の前の縁より前に在るか(第87巡【硬】)。
        /// そこは面でなく設計の地盤 ── 面の多角形が受けの石垣の見え面の前(足〜区画の線)まで入っても、面の高さを描かない。</summary>
        public Func<Vector2, float, bool> inFrontOfRetainer;
        /// <summary>盛りの縁の法を 1:n より急にしない(const.fillEdgeSlope【硬】を y* に・第87巡)── 解く前に掛けた y*(駒の外の点)。null なら掛けない。</summary>
        public Dictionary<long, float> ysFill;
        /// <summary>設計の狙い y*【柔】(面・設計の地盤・小口の土・天端の裏石の帯の土・平らな面)。</summary>
        public float Target(Vector2 q)
        {
            // 区画の外は今の地形(⛔ 面の多角形が区画の線の外へ出ても、区画の外の道・隣へ面の高さを描かない ── 第86巡: 表門の前の腰石垣の前の道に 16.50 の土の歯)
            //   ⭐ 第94巡: own は区画の外を描き終えた後 null(EdoBuildHifuSoto)── ownKept も見る。見ていなかったので区画の外 0.04 の点が面 16.50 を取り、
            //   門の口の段鼻の前に尖った土の山(r93_fumidan)・N39_1 の前の道に 16.1 の盛り(r93_tsuma)。当たる先: SkinHeightSolve を流す全ての邸の区画の外の点
            //   区画の外の地盤は縁の皮の区画の外と同じ測り(OutsideOwnGround ── 区画の内の地形の節点は造成前の地盤へ)。⛔ 今の地形の 2m 格子は台の 16.50 を線の外へ一次で引き、
            //   門の口の段鼻の前を 16.56 と読んだ(第94巡の一回目)
            { var ownT = design == null ? null : (design.own ?? design.ownKept);
              if (ownT != null && !EdoGeom.PIP(ownT, q))
              {
                  //   ⭐ 今の地形(probe)との min【硬: 盛らない】(第109巡)── 造成前の地盤(base_dem)は道を均す前の三べ坂の高まり 12.2〜12.5 を持ち、
                  //   2m 格子の双一次が線の内の節点からそれを線の外へ引いて、台の前の溝の外の道に線から 1:1 で下る土の棚(線の外 0.45 で道 +1.5・
                  //   辺41 s45〜62)を立てた。道は Stage1 が均して今の地形が持つ(区画の外は盛らない)。今の地形が線の内の台を引く所(第94巡の 16.56)は
                  //   造成前の側が低いので、低い方を採れば両方の楔を持たない。当たる先: SkinHeightSolve を流す邸の区画の外の点(いまは岡部)。
                  if (design.baseAt != null) { bool rep; float g = OutsideOwnGround(T(), q.x, q.y, ownT, design.baseAt, null, outCache, out rep);
                      if (rep && !float.IsNaN(g)) { float gp = probe.At(q.x, q.y); return float.IsNaN(gp) ? g : Mathf.Min(g, gp); } }
                  return probe.At(q.x, q.y);
              } }
            float y = FaceY(q);
            if (!float.IsNaN(y) && inFrontOfRetainer != null && inFrontOfRetainer(q, y)) y = float.NaN;
            if (!float.IsNaN(y)) { float hy = HoldY(q); if (!float.IsNaN(hy) && hy > y) y = hy; }
            else y = design != null ? OutsideY(q, null) : probe.At(q.x, q.y);
            if (design != null && design.crestCover != null)
            {
                var cc = design.crestCover; float tg = cc.Target(q);
                if (!float.IsNaN(tg) && tg > y && !cc.Protected(q) && !(cc.keepOut != null && cc.keepOut(q)) && !(otherPart != null && otherPart(q))) y = tg;
            }
            if (design != null && design.flats != null)
                foreach (var ff in design.flats)
                    if (ff.poly != null && EdoGeom.PIP(ff.poly, q) && !(ff.exempt != null && ff.exempt(q)) && !(behindHigherWall != null && behindHigherWall(q, ff.y + ff.e)) && !(inFrontOfRetainer != null && inFrontOfRetainer(q, ff.y))) { y = ff.y; break; }
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
        // **見えている天端の上限**(点 q の縦の線の一番上の当たり ── 許した駒 allow の中で・硬): 石段・溝などの天端 −0.02 / 城の石垣の天端(帯の内)−0.02。
        //   設計で埋める駒(design.buried)・野面の天端(天端の前の帯と裏石の帯で別に)・見え面(下の「全ての石垣の見え面の帯」で別に)は決めない(+∞)。
        Func<float, float, List<Vector3>, string[], Func<int, bool>, float> VisCap = (qx, qz, hl, why, allow) =>
        {
            float gTop = float.NegativeInfinity, gN = 0f; int gW = -1;
            foreach (var hh in hl) { int w = (int)hh.x; if (Mathf.Abs(hh.z) > 0.02f && hh.y > gTop && (allow == null || allow(w))) { gTop = hh.y; gN = hh.z; gW = w; } }
            if (gW < 0 || gN <= 0f || IsBuried(gW)) return float.PositiveInfinity;
            if (!idx.banded[gW]) { why[0] = "天端−0.02〔" + idx.names[gW] + "〕"; return gTop - UNDER; }
            int wT; float crest = idx.Top(qx, qz, out wT);
            if (wT == gW && !float.IsNaN(crest))
            {
                // 野面の天端は、設計で土を載せる裏石の帯(const.nozuraCrestCover の Designed)だけ土を許す ── 帯の外(表の石・keepOut・他の部材の脇)は天端 − capDrop(第88巡: 被りの検めと同じ帯の読み)
                if (IsCover(gW)) { if (cc.Designed(new Vector2(qx, qz))) return float.PositiveInfinity; why[0] = "野面の天端−capDrop〔" + idx.names[gW] + "〕"; return gTop - (float.IsNaN(cc.capDrop) ? UNDER : cc.capDrop); }
                why[0] = "天端−0.02〔" + idx.names[gW] + "〕"; return gTop - UNDER;
            }
            return float.PositiveInfinity;
        };
        // **全ての石垣の見え面の帯**(第86巡 (a)・硬): 点 q を外形の中に含み、天端の前の縁より前(d < 0)に置く全ての帯について
        //   min(見え面の平面, その駒の実の石の面) −0.02 ── ただし前の地表(根入れの土)までは許す。その最も低い物。
        //   ⛔ 縦の線の一番上の駒だけで判じない(下の駒の見え面を逃す)・⛔ 当たった三角形の法線で判じない(野面は石の寄せ集め)。
        var binPiece = new int[wf.list.Count]; var binHull = new Vector2[wf.list.Count][];
        for (int fi = 0; fi < wf.list.Count; fi++) { int k; binPiece[fi] = goIdx.TryGetValue(wf.list[fi].go, out k) ? k : -1; binHull[fi] = wf.HullOf(wf.list[fi].go); }
        // 帯の箱の升の索引(2m)── 点ごとに全ての帯を舐めない
        var binHash = new Dictionary<long, List<int>>();
        for (int fi = 0; fi < wf.list.Count; fi++)
        {
            var bx = wf.list[fi].box;
            for (int i2 = Mathf.FloorToInt(bx.x / 2f); i2 <= Mathf.FloorToInt(bx.z / 2f); i2++)
                for (int j2 = Mathf.FloorToInt(bx.y / 2f); j2 <= Mathf.FloorToInt(bx.w / 2f); j2++)
                { long hk = ((long)i2 << 32) ^ (uint)j2; List<int> l; if (!binHash.TryGetValue(hk, out l)) binHash[hk] = l = new List<int>(); l.Add(fi); }
        }
        var noBins = new List<int>();
        Func<Vector2, List<int>> BinsAt = q => { List<int> l; return binHash.TryGetValue(((long)Mathf.FloorToInt(q.x / 2f) << 32) ^ (uint)Mathf.FloorToInt(q.y / 2f), out l) ? l : noBins; };
        c.behindHigherWall = (q, yMax) =>
        {
            foreach (int fi in BinsAt(q))
            {
                var fb = wf.list[fi]; int b; float d; if (!wf.FaceAt(fb, q, out b, out d) || d < 0f || d > wf.back + wf.skirtMax) continue;
                if (fb.crest[b] > yMax) return true;
            }
            return false;
        };
        // 受けの駒の帯(第89巡): 帯で篩う石垣(wf)に加え、篩わない部材(門の踏み段・樋口・石段・溝)の見え面の帯も「面を受ける駒」として測る ── 見え面の上限(FaceEntries)には使わない
        var wfR = new NozuraCrestCover(); var wfRPiece = new List<int>(); var binHashR = new Dictionary<long, List<int>>();
        for (int k = 0; k < idx.gos.Count; k++)
        {
            if (idx.banded[k] || idx.gos[k] == null) continue; int n0 = wfR.list.Count;
            try { wfR.Add(idx.gos[k], false, false); } catch (Exception) { }
            for (int q = n0; q < wfR.list.Count; q++) wfRPiece.Add(k);
        }
        for (int fi = 0; fi < wfR.list.Count; fi++)
        {
            var bx = wfR.list[fi].box;
            for (int i2 = Mathf.FloorToInt(bx.x / 2f); i2 <= Mathf.FloorToInt(bx.z / 2f); i2++)
                for (int j2 = Mathf.FloorToInt(bx.y / 2f); j2 <= Mathf.FloorToInt(bx.w / 2f); j2++)
                { long hk = ((long)i2 << 32) ^ (uint)j2; List<int> l; if (!binHashR.TryGetValue(hk, out l)) binHashR[hk] = l = new List<int>(); l.Add(fi); }
        }
        var hRet = new List<Vector3>();
        c.inFrontOfRetainer = (q, fy) =>
        {
            bool col = false;
            long hq = ((long)Mathf.FloorToInt(q.x / 2f) << 32) ^ (uint)Mathf.FloorToInt(q.y / 2f);
            List<int> lR; binHashR.TryGetValue(hq, out lR);
            var all = new List<KeyValuePair<NozuraCrestCover.FaceBins, int>>();
            foreach (int fi in BinsAt(q)) all.Add(new KeyValuePair<NozuraCrestCover.FaceBins, int>(wf.list[fi], binPiece[fi]));
            if (lR != null) foreach (int fi in lR) all.Add(new KeyValuePair<NozuraCrestCover.FaceBins, int>(wfR.list[fi], wfRPiece[fi]));
            foreach (var kvb in all)
            {
                // 天端は割りの前後 ±0.5m の最高(第92巡: 見切り石の頭は荒い石で割りごとの天端が 15.68〜16.50 と揺れ、門の口の脇の割りが「受けでない」と読まれて
                //   平ら 16.50 の帯が見切り石の見え面の前(見切り石と踏み段の間)まで入り土が盛り上がった)。当たる先: 受けの石垣・見切り石・踏み段の全ての帯。
                var fb = kvb.Key; int b; float d; if (!wf.FaceAt(fb, q, out b, out d)) continue;
                float crB = float.NaN; for (int bb2 = Mathf.Max(0, b - 5); bb2 <= Mathf.Min(fb.crest.Length - 1, b + 5); bb2++) if (!float.IsNaN(fb.crest[bb2]) && (float.IsNaN(crB) || fb.crest[bb2] > crB)) crB = fb.crest[bb2];
                if (float.IsNaN(crB) || Mathf.Abs(crB - fy) > c.faceTol) continue;
                if (d >= 0f)
                {
                    // 天端の背の線まで(Kadonouchi.flat 追記 2026-10-10f【硬】「平らの輪郭は縁の石垣の天端の背の線で止め、見え面の上や外へ出さない」): 点の真下にその駒の石が在れば天端の上
                    if (!col) { idx.Column(q.x, q.y, hRet, null); col = true; }
                    int k = kvb.Value; bool over = false; foreach (var hh in hRet) if ((int)hh.x == k) { over = true; break; }
                    if (!over) continue;
                }
                float u = Vector2.Dot(q, fb.f); var back = q + fb.f * (d - 0.3f);   // 天端の前の縁の 0.3 背
                float yb = c.FaceY(back); if (float.IsNaN(yb) || Mathf.Abs(yb - fy) > c.faceTol) continue;
                float fu = fb.footU[b]; if (float.IsNaN(fu)) continue;
                var qf = q + fb.f * (fu - u + 0.6f); var ownR = design == null ? null : (design.own ?? design.ownKept); bool outOwn = ownR != null && !EdoGeom.PIP(ownR, qf);
                float yf = c.FaceY(qf); if (!outOwn && !float.IsNaN(yf) && Mathf.Abs(yf - fy) <= c.faceTol) continue;   // 前も同じ面 ── 受けの石垣でない(前が区画の外なら面の多角形が線の外へ出ていても受け ── 第89巡)
                return true;
            }
            return false;
        };
        // 見え面の帯の当たり(帯の番号 fi・割り b・min(平面, 実の石) − 0.02)── 前の地表は二度目に解いた皮で測り直す
        //   ⭐ 第92巡: 点が**別の駒の断面の中**(その駒が y* 〜 y* + seatTol で地盤を占める ── secK)なら、その点はこの駒の見え面の前でない(入隅で突き付いた駒の背の中・
        //   上の石の下の閉じた袋)── 見え面の上限を掛けない。r91 の矛盾の最多(駒の底 × 見え面 239 ── End1 056f × kado3・Sode_4 066f × 007f・Kaeshi 134f × 037f)は
        //   同じ段の入隅で、可動側の駒の背の中に通す側の見え面の帯が入っていた(⛔ 二段の重なりでない ── 底も天端も同じ)。当たる先: 野面・城の石垣の入隅すべて。
        Action<Vector2, List<Vector3>, List<Vector3>, HashSet<int>> FaceEntries = (q2, hl, outL, secK) =>
        {
            outL.Clear();
            foreach (int fi in BinsAt(q2))
            {
                int k = binPiece[fi]; if (k < 0 || IsBuried(k) || binHull[fi] == null) continue;
                if (secK != null) { bool other = false; foreach (int ks in secK) if (ks != k) { other = true; break; } if (other) continue; }
                var fb = wf.list[fi]; int b; float d; if (!wf.FaceAt(fb, q2, out b, out d) || d >= 0f) continue;
                if (!EdoGeom.PIP(binHull[fi], q2)) continue;
                float topK = float.NegativeInfinity; foreach (var hh in hl) if ((int)hh.x == k && Mathf.Abs(hh.z) > 0.02f && hh.y > topK) topK = hh.y;
                if (float.IsInfinity(topK)) continue;   // その駒の石が真下に無い点(隅の駒の入隅の凸包の中など)は見え面の前でない(第87巡: 凸包でなく断面で)
                float face = wf.FacePlaneY(fb, b, Vector2.Dot(q2, fb.f)); if (topK < face) face = topK;
                outL.Add(new Vector3(face - UNDER, fi, b));
            }
        };
        // 端の駒を埋める土の下限(design.buryLo = 天端 + buryMin・指図 sodeSlope 追記 2026-10-08【硬】)
        var buryAimV = new float[1];   // この点の埋める土の狙い(天端 + 狙い ── 柔)
        Func<List<Vector3>, string[], float> BuryLo = (hl, why) =>
        {
            float v = float.NegativeInfinity; if (design == null || design.buryLo == null) return v;
            foreach (var hh in hl) { int k = (int)hh.x; float bl; if (k >= 0 && k < idx.gos.Count && design.buryLo.TryGetValue(idx.gos[k], out bl) && bl > v) { v = bl; why[0] = "埋める駒の土 ≥ 天端+buryMin〔" + idx.names[k] + "〕";
                    float ba; if (design.buryAim != null && design.buryAim.TryGetValue(idx.gos[k], out ba) && ba > buryAimV[0]) buryAimV[0] = ba; } }
            return v;
        };
        float capDrop = cc != null && !float.IsNaN(cc.capDrop) ? cc.capDrop : 0.02f;
        // 見切り石(頭を見せる石・メッシュ名 Mikiri)の頭と外形 ── 背の土は頭より mikiriDrop 以上低く【硬】・mikiriFlat の内は平ら・先は 1:mikiriBatter【柔】(指図 10-10h)
        var mkTop = new List<float>(); var mkHull = new List<Vector2[]>();
        if (design != null && !float.IsNaN(design.mikiriDrop))
            for (int k = 0; k < idx.gos.Count; k++)
            {
                var g = idx.gos[k]; if (g == null) continue; var mf = g.GetComponentInChildren<MeshFilter>(); if (mf == null || mf.sharedMesh == null || !mf.sharedMesh.name.Contains("Mikiri")) continue;
                float tp = float.MinValue; foreach (var v in Body(g.transform, 999999)) tp = Mathf.Max(tp, v.y); mkTop.Add(tp); mkHull.Add(idx.hulls[k]);
            }
        int nMk = 0;
        float seatTol = Mathf.Max(0f, c.faceTol - 0.02f);   // 駒の底が y* の上 seatTol 以内なら据わっている(断面に入れる)── 指図 checks.gradeTol − 0.02(旧 sealFace と同じ許し)
        const float EMBED = 0.05f;

        var hits = new List<Vector3>(); var hitR = new List<Vector3>();
        var owners = new HashSet<int>(); var owners0 = new HashSet<int>(); var why1 = new string[1]; var secP = new HashSet<int>();
        var LO = new Dictionary<long, float>(); var HI = new Dictionary<long, float>(); var YS = new Dictionary<long, float>(); var LO0 = new Dictionary<long, float>();
        var BURYN = new HashSet<long>(); var FACE = new Dictionary<long, List<Vector3>>(); var FACEQ = new Dictionary<long, List<Vector2>>(); var feR = new List<Vector3>(); var HIO = new Dictionary<long, float>(); var HIOW = new Dictionary<long, string>(); var LOW = new Dictionary<long, string>();
        var conflicts = new List<KeyValuePair<float, string>>(); var pairN = new Dictionary<string, int>();
        int nToe = 0, nToeBack = 0; int nRim = 0, nSec = 0, nTop = 0, nFace = 0, nBury = 0, nRelax = 0, nFlatEdge = 0, nRing = 0, nBot = 0, nEdgeBot = 0, nFlat = 0, nSoil = 0, nCeil = 0, nClampUp = 0, nClampDn = 0;
        int[] D8i = { 1, -1, 0, 0, 1, 1, -1, -1 }, D8j = { 0, 0, 1, -1, 1, -1, 1, -1 };

        // 4a 盛りの縁の法(指図 const.fillEdgeSlope「盛りの縁は 1:n より急にしない」【硬】を設計の狙い y* へ ── 第87巡): 解く前に y* を全ての点で引き、
        //   駒の外・区画の内・面の外の点を、周りの y* から 1:n で下りる面まで上げる(盛るだけ)。駒の中(断面の当たり)を越えては伝えない ── 石垣が受ける落差は石垣の話。
        //   面の中の点は上げない(面は設計が決める)── 上げが要るのに面だった点は「法尻が面にかかる」として数える(野面石で受ける所 ── 普請方へ)。
        int nFillUp = 0, nFillFace = 0; float fillMax = 0f; Vector3 fillAt = Vector3.zero;
        if (design != null && !float.IsNaN(design.fillSlope) && design.fillSlope > 1e-3f)
        {
            int gi0 = c.ci0 * c.N, gj0 = c.cj0 * c.N, nwx = (c.ci1 - c.ci0 + 1) * c.N + 1, nwz = (c.cj1 - c.cj0 + 1) * c.N + 1;
            var Y0 = new float[nwx * nwz]; var G = new float[nwx * nwz]; var tgt = new bool[nwx * nwz]; var seed = new bool[nwx * nwz]; var isFace = new bool[nwx * nwz];
            for (int k = 0; k < G.Length; k++) { G[k] = float.NaN; Y0[k] = float.NaN; }
            var hp = new List<Vector3>();
            for (int i = c.ci0; i <= c.ci1; i++)
                for (int j = c.cj0; j <= c.cj1; j++)
                {
                    if (!c.In(i, j)) continue;
                    for (int a = 0; a <= c.N; a++)
                        for (int b = 0; b <= c.N; b++)
                        {
                            int gi = i * c.N + a, gj = j * c.N + b; int k = (gj - gj0) * nwx + (gi - gi0); if (!float.IsNaN(G[k])) continue;
                            float x = org.x + gi * step, z = org.z + gj * step; var q = new Vector2(x, z);
                            idx.Column(x, z, hp, null); if (hp.Count > 0) continue;   // 駒の中は伝えない
                            float y = c.Target(q); if (float.IsNaN(y)) y = c.probe.At(x, z);
                            Y0[k] = y; G[k] = y; seed[k] = true;
                            var ownP = design.own ?? design.ownKept; bool inOwn = ownP == null || EdoGeom.PIP(ownP, q);   // 区画の内だけ盛る(第92巡: own が null で門の口の前の道を盛っていた)
                            float fy = c.FaceY(q); isFace[k] = !float.IsNaN(fy);
                            tgt[k] = inOwn;
                        }
                }
            float w1 = step / design.fillSlope, w2 = step * 1.41421356f / design.fillSlope;
            int[] di = { -1, 0, 1, -1 }, dj = { -1, -1, -1, 0 };
            for (int pass = 0; pass < 2; pass++)
            {
                for (int jj = 0; jj < nwz; jj++)
                    for (int ii = 0; ii < nwx; ii++)
                    {
                        int j = pass == 0 ? jj : nwz - 1 - jj, i = pass == 0 ? ii : nwx - 1 - ii; int k = j * nwx + i; if (!seed[k] || !tgt[k]) continue;
                        for (int n = 0; n < 4; n++)
                        {
                            int i2 = i + (pass == 0 ? di[n] : -di[n]), j2 = j + (pass == 0 ? dj[n] : -dj[n]); if (i2 < 0 || j2 < 0 || i2 >= nwx || j2 >= nwz) continue;
                            int k2 = j2 * nwx + i2; if (!seed[k2]) continue;
                            float v = G[k2] - (di[n] != 0 && dj[n] != 0 ? w2 : w1); if (v > G[k]) G[k] = v;
                        }
                    }
            }
            c.ysFill = new Dictionary<long, float>();
            for (int k = 0; k < G.Length; k++)
            {
                if (!seed[k] || !tgt[k] || G[k] <= Y0[k] + 1e-3f) continue;
                int gi = gi0 + k % nwx, gj = gj0 + k / nwx;
                if (isFace[k]) { if (G[k] - Y0[k] > c.faceTol) nFillFace++; continue; }
                c.ysFill[CK(gi, gj)] = G[k]; nFillUp++;
                if (G[k] - Y0[k] > fillMax) { fillMax = G[k] - Y0[k]; fillAt = new Vector3(org.x + gi * step, G[k], org.z + gj * step); }
            }
        }

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
                        float ys = c.Target(p); if (float.IsNaN(ys)) ys = orig; float ysT0 = ys;
                        { float yf; if (c.ysFill != null && c.ysFill.TryGetValue(key, out yf) && yf > ys) ys = yf; }   // 盛りの縁の法(4a)
                        float ysT1 = ys;
                        float lo = float.NegativeInfinity, hi = float.PositiveInfinity; string loWhy = "", hiWhy = "";
                        Action<float, string> Lo = (v, w) => { if (v > lo) { lo = v; loWhy = w; } };
                        Action<float, string> Hi = (v, w) => { if (v < hi) { hi = v; hiWhy = w; } };

                        // 平らな面(指図 flat ±e・帯を含む)── 狙い y* を面の高さに(帯の外の点も)。上限・下限は駒の断面の外だけ(下で)
                        FlatFace fHit = null;
                        if (design != null && design.flats != null)
                            foreach (var ff in design.flats)
                            {
                                if (ff.poly == null || (ff.exempt != null && ff.exempt(p)) || c.behindHigherWall(p, ff.y + ff.e) || c.inFrontOfRetainer(p, ff.y)) continue;
                                { var ownF = design.own ?? design.ownKept; if (ownF != null && !EdoGeom.PIP(ownF, p)) continue; }   // 区画の外は今の地形(Target と同じ ── 第92巡: 平らの帯 bandMax が門の口の踏み段の前の道へ 16.50 を引いていた)
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
                        owners0.Clear(); foreach (var hh in hits) owners0.Add((int)hh.x);
                        bool sectioned = false; secP.Clear();
                        foreach (int k in owners)
                        {
                            float sb0, st0; if (!SolidOf(hits, k, out sb0, out st0)) continue;
                            if (st0 < ys || sb0 > ys + seatTol) continue;
                            sectioned = true; nSec++; secP.Add(k);
                            if (!float.IsInfinity(sb0)) { Lo(sb0 + EMBED, "駒の底+0.05〔" + idx.names[k] + "〕"); nBot++; }
                        }
                        // 見えている天端の上限 ── この点(縦の線の一番上)と、皮の三角形が渡る周り(0.125・0.25 の 8 方向)の点で。
                        //   周りは、その点の y* 〜 y* + seatTol の断面に入る駒(本当にその地盤に載る駒)だけ ── 隣の低い段の天端・陰の段は数えない(第86巡 (b))
                        { why1[0] = null; float v = VisCap(x, z, hits, why1, null); if (v < hi) { Hi(v, why1[0]); nTop++; } }
                        var fe = new List<Vector3>(); FaceEntries(p, hits, fe, secP); var feQ = new List<Vector2>(); foreach (var e0 in fe) feQ.Add(p);
                        buryAimV[0] = float.NegativeInfinity;
                        { why1[0] = null; float v = BuryLo(hits, why1); if (v > lo) { Lo(v, why1[0]); nBury++; } }
                        float eb = float.NaN; string ebW = null; var secR = new HashSet<int>(); float freeMin = float.NaN;
                        for (int d = 0; d < 8; d++)
                            for (int sI = 1; sI <= 2; sI++)
                            {
                                float qx = x + D8i[d] * step * 0.5f * sI, qz = z + D8j[d] * step * 0.5f * sI;
                                idx.Column(qx, qz, hitR, null);
                                if (hitR.Count == 0)
                                {   // 皮の隣の節点(一格子先)が部材の外 ── その狙いの高さ(縁の内の点の上限に使う)
                                    if (sI == 2 && hits.Count > 0) { var qn = new Vector2(qx, qz); float yn = c.Target(qn); if (float.IsNaN(yn)) yn = c.probe.At(qx, qz);
                                        float yfN; long kn = CK(gi + D8i[d], gj + D8j[d]); if (c.ysFill != null && c.ysFill.TryGetValue(kn, out yfN) && yfN > yn) yn = yfN;
                                        if (float.IsNaN(freeMin) || yn < freeMin) freeMin = yn; }
                                    continue;
                                }
                                owners.Clear(); foreach (var hh in hitR) owners.Add((int)hh.x);
                                secR.Clear();
                                foreach (int k in owners) { float sb1, st1; if (!SolidOf(hitR, k, out sb1, out st1)) continue; if (st1 >= ys && sb1 <= ys + seatTol) secR.Add(k);
                                    // 駒の足の縁の外一格子(隙 0): 周りの点で駒の底が y* 〜 y* + seatTol(据わっている駒)なら、その底より下げない
                                    if (!sectioned && !float.IsInfinity(sb1) && sb1 > ys && sb1 <= ys + seatTol && st1 >= ys && (float.IsNaN(eb) || sb1 > eb)) { eb = sb1; ebW = idx.names[k]; } }
                                if (secR.Count > 0) { why1[0] = null; float v = VisCap(qx, qz, hitR, why1, w => secR.Contains(w)); if (v < hi) { Hi(v, "周り " + why1[0]); nRing++; } }
                                { why1[0] = null; float v = BuryLo(hitR, why1); if (v > lo) { Lo(v, "周り " + why1[0]); nBury++; } }
                                // 周りの見え面の帯の上限(第87巡: 断面と関係なく戻す ── 皮の三角形が渡る先の点で見え面の前へ土を出さない)
                                FaceEntries(new Vector2(qx, qz), hitR, feR, secR); foreach (var e0 in feR) { fe.Add(e0); feQ.Add(new Vector2(qx, qz)); }
                            }
                        if (!float.IsNaN(eb)) { Lo(eb, "足の縁の底〔" + ebW + "〕"); nEdgeBot++; }
                        // 野面の天端の前の帯(0〜front)の天井 = 天端 − capDrop・裏石の帯の上の土 ≥ 天端 + minSoil(指図 const.nozuraCrestCover)── 設計で埋める駒の帯は除く
                        if (cc != null)
                        {
                            bool kOut = cc.keepOut != null && cc.keepOut(p);
                            foreach (var fb in cc.list)
                            {
                                if (fb.go == null || (buried != null && buried.Contains(fb.go))) continue;
                                { int kq; if (!goIdx.TryGetValue(fb.go, out kq) || !owners0.Contains(kq)) continue; }   // その駒の石が真下に在る点だけ(隅の駒の入隅の箱の中を天井にしない・第87巡)
                                int bb; float dd; if (!cc.FaceAt(fb, p, out bb, out dd) || float.IsNaN(fb.crest[bb])) continue;
                                if (dd >= 0f && dd < cc.front && !kOut)
                                {
                                    // 埋める土の下限と重なる所に限り天井を最大 ceilRelax 緩め、埋める土の狙いまでは許す(指図 sodeSlope 追記 2026-10-10e【硬】)
                                    float ce = fb.crest[bb] - capDrop; string cw = "天端の前の帯 天端−capDrop〔" + fb.go.name + "〕";
                                    if (!float.IsInfinity(buryAimV[0]) && design.ceilRelax > 0f && buryAimV[0] > ce) { float ce2 = Mathf.Min(ce + design.ceilRelax, buryAimV[0]); if (ce2 > ce) { ce = ce2; cw = "天端の前の帯(埋める土で緩めた)〔" + fb.go.name + "〕"; nRelax++; } }
                                    Hi(ce, cw); nCeil++;
                                }
                            }
                            if (cc.Designed(p) && !(c.otherPart != null && c.otherPart(p)))
                            {
                                bool over = false; foreach (var pf in cc.pieceFaces) if (EdoGeom.PIP(pf.hull, p)) { over = true; break; }
                                float cb = cc.CrestInBand(p);
                                if (over && !float.IsNaN(cb)) { Lo(cb + cc.minSoil, "裏石の帯の土 ≥ " + cc.minSoil.ToString("F2", ci)); nSoil++; }
                            }
                        }
                        // 平らな面の幅(駒の断面の外だけ)── 根入れを隠す土 coverD の内は y + coverH まで(指図)
                        // 平らの輪郭は縁の石垣の天端の背の線で止める(Kadonouchi.flat 追記 2026-10-10f【硬】): 皮の三角形が渡る周りの点に、平らを背で受ける石垣(天端 ≈ 平ら ± gradeTol)の
                        //   見え面が在る点は平らの縁 ── 平らの幅を掛けない(狙いは平らのまま・上限は見え面が決める)
                        bool flatEdge = false;
                        if (fHit != null) for (int ie = 0; ie < fe.Count && !flatEdge; ie++) { if (feQ[ie] == p) continue; var fb0 = wf.list[(int)fe[ie].y]; int b0 = (int)fe[ie].z; if (Mathf.Abs(fb0.crest[b0] - fHit.y) <= c.faceTol) flatEdge = true; }
                        if (flatEdge) nFlatEdge++;
                        if (fHit != null && !sectioned && !flatEdge)
                        {
                            var ff = fHit; float hl2 = ff.y + ff.e;
                            if (!float.IsNaN(ff.coverD) && !float.IsNaN(ff.coverH))
                                for (int hk = 0; hk < idx.hulls.Count; hk++) { var hb = idx.bounds[hk]; if (p.x < hb.x - ff.coverD || p.x > hb.z + ff.coverD || p.y < hb.y - ff.coverD || p.y > hb.w + ff.coverD) continue; if (EdoGeom.PIP(idx.hulls[hk], p) || EdgeDist(idx.hulls[hk], p) <= ff.coverD) { hl2 = ff.y + ff.coverH; break; } }
                            Lo(ff.y - ff.e, "平ら " + ff.name + " −e"); Hi(hl2, "平ら " + ff.name + " +e"); nFlat++;
                        }
                        // 石垣の足元の帯(const.toeBand【硬】・第97巡): 駒の断面の外・区画の内の点で、帯で篩う駒の見え面の法尻から前 0〜toeBandW に在れば
                        //   狙い = 法尻の高さ(平ら)・上限 = 法尻 + toeBandRise。法尻の高さ = その割りの見え面の平面が法尻の線で切る高さでなく、法尻の点の設計の狙い(前の地表の型)。
                        //   ⛔ 区画の外は今の地形(掛けない)。当たる先: 全ての石垣・野面の足元(岡部 辺24・S_Hei_20 の土の歯)。
                        if (design != null && !float.IsNaN(design.toeBandW) && !sectioned && hits.Count == 0)
                        {
                            var ownT = design.own ?? design.ownKept; if (ownT == null || EdoGeom.PIP(ownT, p))
                            {
                                float toeBest = float.NaN; string toeW = null;
                                foreach (int fiT in BinsAt(p))
                                {
                                    var fbT = wf.list[fiT]; int bT; float dT; if (!wf.FaceAt(fbT, p, out bT, out dT) || dT >= 0f) continue;
                                    float fuT = fbT.footU[bT]; if (float.IsNaN(fuT)) continue;
                                    float sT = Vector2.Dot(p, fbT.f) - fuT; if (sT < -0.05f || sT > design.toeBandW) continue;
                                    var qT = p - fbT.f * sT; float ty = c.Target(qT + fbT.f * 0.05f); if (float.IsNaN(ty)) continue;
                                    if (!float.IsNaN(fbT.botY[bT]) && ty < fbT.botY[bT]) ty = fbT.botY[bT];
                                    if (float.IsNaN(toeBest) || ty < toeBest) { toeBest = ty; toeW = fbT.go != null ? fbT.go.name : "?"; }
                                }
                                if (!float.IsNaN(toeBest)) { ys = toeBest; Hi(toeBest + design.toeBandRise, "足元の帯 法尻+" + design.toeBandRise.ToString("F2", ci) + "〔" + toeW + "〕"); nToe++; }
                            }
                        }
                        // 足元の帯の背の押さえ(const.toeBand 追記 2026-10-10p【硬】・第100巡): 法尻の線から背へ toeBackFar 以内の点(駒の下・断面でも)は
                        //   ≤ toeBackNear: 法尻 + toeBandRise / toeBackNear〜toeBackFar: min(天端 − toeBackCrestDrop, 法尻 + toeBandRise + 法の立ち上がり × (距離 − toeBackNear))。
                        //   法尻の高さは前の帯と同じ(法尻の点の 0.05 前の設計の狙い・駒の底より下げない)。法の立ち上がり = 1/k(k = 見え面の平面の水平/鉛直 ── FacePlaneY と同じ測り)。
                        //   埋める駒(通しの駒)は数えない。⛔ 区画の外は今の地形。当たる先: 帯で篩う全ての石垣・野面の法尻の背(岡部 辺24 の土の歯・平面より前)。
                        if (design != null && !float.IsNaN(design.toeBandW) && !float.IsNaN(design.toeBackNear) && !float.IsNaN(design.toeBackFar))
                        {
                            var ownB = design.own ?? design.ownKept; if (ownB == null || EdoGeom.PIP(ownB, p))
                            {
                                float capB = float.NaN; string capW = null;
                                foreach (int fiB in BinsAt(p))
                                {
                                    var fbB = wf.list[fiB]; if (fbB.go == null || (buried != null && buried.Contains(fbB.go))) continue;
                                    int bB; float dB; if (!wf.FaceAt(fbB, p, out bB, out dB)) continue;
                                    float fuB = fbB.footU[bB]; if (float.IsNaN(fuB) || float.IsNaN(fbB.crest[bB])) continue;
                                    float back = fuB - Vector2.Dot(p, fbB.f); if (back <= 0.05f || back > design.toeBackFar) continue;   // 0.05 以内は前の帯が受ける
                                    var qB = p + fbB.f * back; float tyB = c.Target(qB + fbB.f * 0.05f); if (float.IsNaN(tyB)) continue;
                                    if (!float.IsNaN(fbB.botY[bB]) && tyB < fbB.botY[bB]) tyB = fbB.botY[bB];
                                    float cb = tyB + design.toeBandRise;
                                    if (back > design.toeBackNear)
                                    {
                                        float cr = fbB.crest[bB], k = 0.3f;
                                        if (!float.IsNaN(fbB.botY[bB]) && cr - fbB.botY[bB] > 0.2f) k = Mathf.Clamp((fuB - fbB.frontU[bB]) / (cr - fbB.botY[bB]), 0.05f, 0.6f);
                                        cb = Mathf.Min(cr - (float.IsNaN(design.toeBackCrestDrop) ? 0f : design.toeBackCrestDrop), cb + (back - design.toeBackNear) / k);
                                    }
                                    if (float.IsNaN(capB) || cb < capB) { capB = cb; capW = fbB.go.name; }
                                }
                                if (!float.IsNaN(capB)) { Hi(capB, "足元の帯の背〔" + capW + "〕"); nToeBack++; }
                            }
                        }
                        float ysT2 = ys;
                        if (!float.IsInfinity(buryAimV[0]) && buryAimV[0] > ys) ys = buryAimV[0];   // 埋める土の狙い(柔)
                        float ysT3 = ys;
                        for (int mi = 0; mi < mkTop.Count; mi++)
                        {
                            float dm = EdoGeom.PIP(mkHull[mi], p) ? 0f : EdgeDist(mkHull[mi], p); float y0 = mkTop[mi] - design.mikiriDrop;
                            if (dm <= design.mikiriFlat) { Hi(y0, "見切り石の背の土 頭−" + design.mikiriDrop.ToString("F2", ci)); if (ys > y0) ys = y0; nMk++; }
                            else if (!float.IsNaN(design.mikiriBatter) && design.mikiriBatter > 0f) { float ya = y0 + (dm - design.mikiriFlat) / design.mikiriBatter; if (ys > ya) ys = ya; }
                        }
                        // ⭐ 部材の縁の内の点(第92巡・硬): 縦の線の一番上が帯で篩わない部材(石段・踏み段・樋口・溝など)で、皮の隣の節点(一格子先)が部材の外なら、
                        //   この点は隣の外の地表の狙いより高くしない(底 + 0.05 の下限までは下げる)── 縁の内の節点が天端の下まで上がると、外の節点へ渡る皮の三角形が
                        //   蹴込み・側面を抜けて部材の前に土の楔を立てる(r90/r91 の石段の右下の土の三角 ── 一段目の段石の内の節点 16.75・前の平ら 16.50)。
                        //   当たる先: 皮が囲む全ての帯で篩わない部材の外周(野面・城の石垣は見え面の帯と小口の土が決める ── 掛けない)。
                        if (!float.IsNaN(freeMin) && hits.Count > 0)
                        {
                            float gTop = float.NegativeInfinity; int gW = -1; foreach (var hh in hits) { if (Mathf.Abs(hh.z) > 0.02f && hh.y > gTop) { gTop = hh.y; gW = (int)hh.x; } }
                            if (gW >= 0 && !idx.banded[gW] && !IsBuried(gW) && freeMin < hi) { float cap = Mathf.Max(freeMin, lo); if (cap < hi) { Hi(cap, "部材の縁の内 ≤ 外の地表〔" + idx.names[gW] + "〕"); nRim++; } }
                        }
                        // 見え面の帯の上限は最後に(他の決まりの上限 hiOther を控えてから)── 二度目に前の地表を解いた皮で測り直す
                        float hiOther = hi; string hiOtherWhy = hiWhy;
                        if (fe.Count > 0)
                        {
                            bool buryN = !float.IsInfinity(buryAimV[0]); if (buryN) BURYN.Add(key);
                            for (int ie = 0; ie < fe.Count; ie++) { var e = fe[ie]; int fi = (int)e.y, bb = (int)e.z; float g = FrontG(fi, bb, feQ[ie]); if (buryN && !float.IsNaN(g) && design.buryFaceCover > 0f && !IsBuried(binPiece[fi])) g += design.buryFaceCover; float v = !float.IsNaN(g) && g > e.x ? g : e.x; if (v < hi) Hi(v, (feQ[ie] == p ? "" : "周り ") + "見え面−0.02/前の地表〔" + idx.names[binPiece[fi]] + "〕"); }
                            nFace++; FACE[key] = fe; FACEQ[key] = feQ; HIO[key] = hiOther; HIOW[key] = hiOtherWhy; LOW[key] = loWhy;
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
                        YS[key] = ys; H[key] = hgt; LO0[key] = lo;
                        if (SkinSolveTrace != null) foreach (var tq in SkinSolveTrace) if (Mathf.Abs(tq.x - x) <= step * 0.5f && Mathf.Abs(tq.y - z) <= step * 0.5f)
                                    SkinSolveTraceLog.AppendLine("  (" + x.ToString("F2", ci) + ", " + z.ToString("F2", ci) + ") y* " + ys.ToString("F3", ci) + " lo " + lo.ToString("F3", ci) + "〔" + loWhy + "〕 hi " + hi.ToString("F3", ci) + "〔" + hiWhy + "〕 ⇒ " + hgt.ToString("F3", ci) + " 断面 " + sectioned + " 当たり " + hits.Count + " 〔狙いの経過 Target " + ysT0.ToString("F3", ci) + "・盛りの縁 " + ysT1.ToString("F3", ci) + "・平ら " + ysT2.ToString("F3", ci) + "・埋める土 " + ysT3.ToString("F3", ci) + "・区画の内 " + (design == null || (design.own ?? design.ownKept) == null || EdoGeom.PIP(design.own ?? design.ownKept, p)) + "・地形 " + orig.ToString("F3", ci) + "〕");
                        if (orig - hgt > r.maxLower) { r.maxLower = orig - hgt; r.lowerAt = new Vector3(x, hgt, z); }
                        if (hgt - orig > r.maxRaise) { r.maxRaise = hgt - orig; r.raiseAt = new Vector3(x, hgt, z); }
                    }
            }
        // 4b 見え面の帯の前の地表を、一度目に解いた皮で測り直す(第86巡): 前の地表 = 法尻の 0.6 前の皮の高さ(皮の外なら今の地形)。
        //   ⛔ 一度目の y*(設計の狙い)は、前の地表が別の決まりで押し下げられた所で高すぎた(TW_Higashi_Tsuyo の前で 15.88、解いた皮は 13.3)。
        int nRe = 0; var conflicts2 = new List<KeyValuePair<float, string>>();
        {
            var H1 = new Dictionary<long, float>(H);
            Func<Vector2, float> SolvedAt = q =>
            {
                long kq = CK(Mathf.RoundToInt((q.x - org.x) / step), Mathf.RoundToInt((q.y - org.z) / step)); float v;
                return H1.TryGetValue(kq, out v) ? v : c.probe.At(q.x, q.y);
            };
            foreach (var kv in FACE)
            {
                long key = kv.Key; float hiN = HIO[key]; string hw = HIOW[key];
                int gi = (int)(key >> 32), gj = (int)(uint)(key & 0xffffffff); var p = new Vector2(org.x + gi * step, org.z + gj * step);
                var qL = FACEQ[key]; for (int ie = 0; ie < kv.Value.Count; ie++)
                {
                    var e = kv.Value[ie]; var qe = qL[ie]; int fi = (int)e.y, bb = (int)e.z; var fb = wf.list[fi]; float fu = fb.footU[bb]; float g = float.NaN;
                    if (!float.IsNaN(fu)) { float u = Vector2.Dot(qe, fb.f); g = SolvedAt(qe + fb.f * (fu - u + 0.6f)); }
                    if (BURYN.Contains(key) && !float.IsNaN(g) && design.buryFaceCover > 0f && !IsBuried(binPiece[fi])) g += design.buryFaceCover;   // 埋める土は隣の見え面の根元を被ってよい(sodeSlope 10-10f【硬】)
                    float v = !float.IsNaN(g) && g > e.x ? g : e.x; if (v < hiN) { hiN = v; hw = "見え面−0.02/前の地表(解いた皮)〔" + idx.names[binPiece[fi]] + "〕"; }
                }
                float lo = LO0[key], ys = YS[key]; float h2;
                if (lo > hiN + 1e-4f) { h2 = hiN; LO[key] = hiN; HI[key] = hiN; conflicts2.Add(new KeyValuePair<float, string>(lo - hiN, "(" + p.x.ToString("F2", ci) + ", " + p.y.ToString("F2", ci) + ") 差 " + (lo - hiN).ToString("F3", ci) + " lo " + lo.ToString("F2", ci) + "〔" + LOW[key] + "〕 > hi " + hiN.ToString("F2", ci) + "〔" + hw + "〕 y* " + ys.ToString("F2", ci))); }
                else { h2 = Mathf.Clamp(ys, lo, hiN); LO[key] = lo; HI[key] = hiN; }
                if (Mathf.Abs(h2 - H[key]) > 1e-4f) { H[key] = h2; nRe++; }
            }
            // 矛盾の表は二度目で測り直した見え面の点を差し替える
            var faceKeys = new HashSet<string>(); foreach (var kv in FACE) { int gi = (int)(kv.Key >> 32), gj = (int)(uint)(kv.Key & 0xffffffff); faceKeys.Add("(" + (org.x + gi * step).ToString("F2", ci) + ", " + (org.z + gj * step).ToString("F2", ci) + ")"); }
            conflicts.RemoveAll(cf => faceKeys.Contains(cf.Value.Substring(0, cf.Value.IndexOf(')') + 1)));
            conflicts.AddRange(conflicts2);
            pairN.Clear(); foreach (var cf in conflicts) { var m = System.Text.RegularExpressions.Regex.Match(cf.Value, @"〔([^〔〕]*?)(?:〔[^〕]*〕)?〕 > hi [0-9.\-]+〔([^〔〕]*?)(?:〔[^〕]*〕)?〕"); string pr = m.Success ? m.Groups[1].Value + " × " + m.Groups[2].Value : "?"; int pn; pairN.TryGetValue(pr, out pn); pairN[pr] = pn + 1; }
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
                      + "・断面に入った区間 " + nSec + "(底+0.05 " + nBot + ")・天端の上限 " + nTop + "(周りの断面の駒から " + nRing + ")・見え面の帯 " + nFace + "(前の地表を解いた皮で測り直して動いた " + nRe + ")・見切り石の背 " + nMk + "・埋める駒の土 " + nBury + "(天井を緩めた " + nRelax + ")・天端の前の帯の天井 " + nCeil
                      + "・裏石の帯の土 " + nSoil + "・平ら " + nFlat + "(縁の石垣の天端で止めた " + nFlatEdge + ")・足の縁の底 " + nEdgeBot + "・部材の縁の内 " + nRim + " / 狙いより上げた " + nClampUp + "・下げた " + nClampDn + "・尖り窪みの均し " + nSm);
        if (design != null && !float.IsNaN(design.toeBandW)) sb.AppendLine("  石垣の足元の帯(const.toeBand【硬】): 幅 " + design.toeBandW.ToString("F2", ci) + "・法尻 +" + design.toeBandRise.ToString("F2", ci) + " を上限に平ら ── 掛けた点 " + nToe
                                                                                 + (float.IsNaN(design.toeBackNear) ? "" : "・背の押さえ(10-10p) " + design.toeBackNear.ToString("F2", ci) + " 以内 法尻+" + design.toeBandRise.ToString("F2", ci) + "・〜" + design.toeBackFar.ToString("F2", ci) + " は天端−" + design.toeBackCrestDrop.ToString("F2", ci) + " と勾配なりの低い方 ── 掛けた点 " + nToeBack));
        if (design != null && !float.IsNaN(design.fillSlope)) sb.AppendLine("  盛りの縁の法 1:" + design.fillSlope.ToString("0.0", ci) + "(const.fillEdgeSlope・y* へ): 上げた点 " + nFillUp + "・最大 " + fillMax.ToString("F2", ci) + " @(" + fillAt.x.ToString("F1", ci) + ", " + fillAt.z.ToString("F1", ci) + ")・法尻が面にかかる点(上げが gradeTol を超えるのに面 ── 野面石で受ける所・普請方へ)" + nFillFace);
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
