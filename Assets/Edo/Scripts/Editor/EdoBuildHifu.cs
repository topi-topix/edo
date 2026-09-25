// 縁の皮 — 地形に穴を開け、穴の縁から部材の面までを皮のメッシュで描く (EdoBuild の partial・2026-09-24・EDO-0430)
//
// ⭐ **何が足りなかったか**: 地形の高さは 2m 格子(赤坂)なので、切通しの石段の脇・土留めの天端の奥・造成した面の縁の
//    ような**縦の切れ目**を描けない。格子の節点は切れ目の向こうの高さを持ったまま、踏面や天端の上へ面を張る
//    (山王 2026-09-24: 女坂の踏面 812/7176 点が最大 1.15m 埋没・土留め 298 点・面の縁の突き合わせ 38 点)。
//    節点を掘ると隣の駒へ連鎖し(dig-to-unbury-cascades)、均すと崖に盛土が出る(terrace-rim-residual-is-the-ruler)。
//
// ⭕ 工法(普請奉行の決め 2026-09-24): **切れ目に掛かる升だけ地形に穴(holes)を開け、その升の中を 0.25m の皮で描く。**
//    皮の高さは元の地形(SampleHeight)を写し、造成した面の中では面の高さ、部材の近くでは部材の天端の下へ納める。
//    ・穴の升 = 部材の外形(margin 外まで)に掛かる升 + 面の縁で地形が面から faceTol を超えて外れる升の 3×3。
//      ⛔ 既に穴の升(井戸の口など)は触らない。⛔ 地形の木が立つ升も開けない(Unity が穴の中の木を消す)。
//    ・皮の縁(穴の升と地形の升の境)の点は**元の地形の高さのまま**(地形の升の縁は 2 節点の直線なので継ぎ目は 0)。
//      地形の LOD で縁がずれても見えないよう、縁に 0.3m の垂れ(両面)を付ける。
//    ・部材の天端より上へ出さない(硬い・許容0 = 皮が見え面に被らない): 各点で、その点と周り 8 点(0.25m)の
//      部材の天端の最小 − eps より下げる。部材の真下の点は天端 − under まで下げる(天端と面で重ならない)。
//    ・部材との隙(硬い・許容0): 皮は部材の外形の中まで続く(部材の下へ潜る)ので、外形の縁で皮が途切れない。
//      検め: 外形の 0.05m 外の点で皮 < 部材の底 − 0.01 の点(= 部材の下が覗く)と、外形の 0.05m 内で皮 > 天端の点を数える。
//    ・芝(detail)は皮が元の地形から 0.02m を超えて動いた 1m 升だけ消す(芝は元の地形の高さに生える)。
//    ・材質は地形の材質の写し(本体 + 足し込み)に地形のスプラットを結わえる ⇒ 地形と同じ見え。uv は地形の正規化座標。
//
// ⭐ **描かれた地表**(<see cref="Drawn"/>): 穴の升では皮の高さ、それ以外は地形。埋没・面の突き合わせ・天端の検めは
//    これで測る(⛔ 穴の升で SampleHeight を読まない ── 穴の下の消えた地形を測ることになる)。
//
// ⚠ 地形の編集(holes・detail)は Undo の外。高さ(heightmap)は動かさない。
// ⚠ 皮は部材の今の位置に合わせて起こす ── 部材を据え直す Stage(整地・石段・土留め)は、先に <see cref="ClearEdgeSkins"/>
//    で穴を塞いで皮を外し、据え直した後で皮を起こし直す。
// 当たる先: 切通しの石段(山王の女坂・男坂・参道の階)・天端を地盤に揃えた土留め(山王・土井・岡部の郭)・
//    造成した面の縁(全邸の段の縁)。井戸の口の穴(<see cref="CutHole"/>)とは升が重ならないようにしてある。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static partial class EdoBuild
{
    /// <summary>皮の GameObject の名の頭。<see cref="Drawn"/> はこの名の MeshFilter を皮と読む。</summary>
    public const string SKIN_PREFIX = "EdgeSkin_";
    /// <summary>皮のシェーダ(地形の本体・足し込みの写しに、層の値を Properties として足した物・Assets/Edo/Shaders/StochTerrain/)。</summary>
    const string SKIN_SHADER_BASE = "Edo/TerrainSkinStochastic", SKIN_SHADER_ADD = "Edo/TerrainSkinAdd";

    /// <summary>皮の中で高さを揃える造成の面(世界 XZ の多角形と面の高さ)。</summary>
    public struct SkinFace
    {
        public string name; public Vector2[] poly; public float y;
        public SkinFace(string name, Vector2[] poly, float y) { this.name = name; this.poly = poly; this.y = y; }
    }

    /// <summary>皮が面の外で写す**設計の地盤**(算出物 `graded` の節点格子。法面を含む)と法の勾配。
    /// 面の外の点は、面の中の節点を混ぜずに外の節点だけで引く(混ぜると面の縁が格子の鋸歯になる)。</summary>
    public sealed class SkinDesign
    {
        public float x0, z0, step; public int nx, nz; public float[] h; public bool[] ok;
        /// <summary>切土の法 1:batterCut / 盛土の法 1:batterFill(指図 `const`)。</summary>
        public float batterCut, batterFill;
        /// <summary>造成前の地盤(無い所は NaN)。渡すと、**部材の外形の中に入った地形の節点**を造成前の地盤に置き換えて、
        /// 設計面の外(造成しない地盤)を引く(<see cref="CutEdgeSkin"/> の CleanAt)。⭐ 2m 格子の節点が土留め・石垣の駒の下
        /// (見え面の 0.1〜1m 奥)に落ちると、その節点は天端の側の高さを持ち、見え面の前の地表を三角に持ち上げる
        /// (2026-09-25 山王 回廊の基壇の東の見え面の足元に高さ 0.3〜1m の山形が 2m おき)。</summary>
        public Func<float, float, float> baseAt;
    }

    /// <summary><see cref="CutEdgeSkin"/> の報告。</summary>
    public struct SkinReport
    {
        public int parts, cells, cellsParts, cellsFace, cellsBand, cellsFill, skipHole, skipTree, holesCut;
        public int verts, tris, pinned, faced, clamped, under, floored, designed, sloped, filled, fillLostTree;
        public float fillMax; public Vector3 fillAt;
        public float maxLower, maxRaise; public Vector3 lowerAt, raiseAt;
        public int detCells, trees, sealed_;
        /// <summary>digParts の背を下げた点の数・下げた量の最大(天端を段の線に置いた袖 ── 施主 2026-09-25)。</summary>
        public int dug; public float digMax; public Vector3 digAt;
        public int gapPts, gapN, gapBySkin, gapBig, coverPts, coverN;
        public float gapMax, coverMax; public Vector3 gapAt, coverAt; public string gapBy, coverBy;
        public string mesh;
        public override string ToString()
        {
            return "穴 " + holesCut + " 升(部材 " + cellsParts + "・面の縁 " + cellsFace + "(うち縁の線の帯 " + cellsBand + ")・裏込め " + cellsFill +
                   "・既に穴で触らず " + skipHole + "・地形の木が立つので開けず " + skipTree + ")" +
                   " / 皮 頂点 " + verts + "・三角 " + tris + "(縁の点 " + pinned + " は地形のまま)" +
                   " / 面の高さへ " + faced + " 点・面の外は設計の地盤へ " + designed + " 点(うち縁から法で受けた " + sloped + ")" +
                   " / 部材の天端の下へ " + clamped + " 点(うち真下 " + under + "・隣の底で止めた " + floored + ")" +
                   " / 裏込め(部材の底まで盛る)" + filled + " 点・最大 " + fillMax.ToString("F2") + "m @(" + fillAt.x.ToString("F1") + ", " + fillAt.z.ToString("F1") + ")" +
                   "・地形の木の升は穴を開けず被せた " + fillLostTree + " 升" +
                   " / 面の高さの皮で部材の底まで塞いだ " + sealed_ + " 点" +
                   (dug > 0 ? " / 背を下げた(天端 − 0.05 から法)" + dug + " 点・最大 " + digMax.ToString("F2") + "m @(" + digAt.x.ToString("F1") + ", " + digAt.z.ToString("F1") + ")" : "") +
                   " / 元の地形から 下げ 最大 " + maxLower.ToString("F2") + "m @(" + lowerAt.x.ToString("F1") + ", " + lowerAt.z.ToString("F1") + ")・上げ 最大 " + maxRaise.ToString("F2") + "m @(" + raiseAt.x.ToString("F1") + ", " + raiseAt.z.ToString("F1") + ")" +
                   " / 芝を消した 1m 升 " + detCells + " / 皮が 0.05m を超えて動いた所の地形の木 " + trees + " 本" +
                   "\n    硬い(許容0): 皮と部材の隙 ── 皮が作った " + gapBySkin + " / 元の地形でも同じ(部材の浮き・皮の外の欠陥) " + (gapN - gapBySkin) + " / " + gapPts + " 点(うち 0.05m を超える " + gapBig + ")" + (gapN > 0 ? "(最大 " + gapMax.ToString("F3") + "m @(" + gapAt.x.ToString("F2") + ", " + gapAt.z.ToString("F2") + ")〔" + gapBy + "〕)" : "") +
                   " / 皮が部材の天端に被る " + coverN + " / " + coverPts + " 点" + (coverN > 0 ? "(最大 " + coverMax.ToString("F3") + "m @(" + coverAt.x.ToString("F2") + ", " + coverAt.z.ToString("F2") + ")〔" + coverBy + "〕)" : "") +
                   " / メッシュ " + mesh;
        }
    }

    /// <summary>面の縁の線の帯の幅(縁からこの距離の中で地形が描く高さを検める)[m]。</summary>
    public const float BAND = 4f;
    /// <summary>面の外の点を縁から法で受ける最大の離れ[m]。</summary>
    const float BATTER_REACH = 6f;
    /// <summary>digParts(背を下げる部材)の天井が届く距離[m]。背の地盤が天端より DIG_REACH / digBatter − digUnder 以内の高さなら収まる。</summary>
    const float DIG_REACH = 3f;
    /// <summary>縁の線の点がこの距離の中に部材(土留め・石段)を持てば「囲いのある縁」── 法を当てない[m]。</summary>
    const float WALLED = 0.75f;
    /// <summary>裏込めの天端の平ら(部材の外形の縁から)[m]。皮の格子(0.25)の三角形が外形の 0.05m 外で底を割らない幅。</summary>
    public const float FLAT = 0.45f;
    /// <summary>地形の上へ被せる皮(地形の木の升)で、盛らない点を地形の下へ沈める深さ[m]。</summary>
    const float OV_SINK = 0.05f;
    /// <summary>裏込めが部材の天端の下へ潜る深さ(外形の縁の帯の中)[m]。天端と重ねず、縁の外で底を割らない。</summary>
    const float FILL_UNDER = 0.006f;
    /// <summary>裏込めを伸ばす最大の離れ(部材の外接矩形から)[m]。</summary>
    const float FILL_REACH = 12f;

    /// <summary>密な格子の chamfer 伝播。<paramref name="max"/> = 最大を 1 格子 d1(斜め d2)ずつ下げて伝える /
    /// false = 最小を上げて伝える。<paramref name="barrier"/> の点(種を除く)は伝えも受けもしない。</summary>
    static void Chamfer(float[] A, int w, int h, float d1, float d2, bool max, bool[] barrier, bool[] seed, int rounds)
    {
        float s = max ? -1f : 1f;
        Func<int, bool> Blk = k => barrier != null && barrier[k] && !(seed != null && seed[k]);
        for (int r = 0; r < rounds; r++)
        {
            for (int j = 0; j < h; j++)
                for (int i = 0; i < w; i++)
                {
                    int k = j * w + i; if (Blk(k)) continue; float v = A[k];
                    Action<int, float> U = (q, d) => { if (Blk(q)) return; float c = A[q] + s * d; if (max ? c > v : c < v) v = c; };
                    if (i > 0) U(k - 1, d1);
                    if (j > 0) { U(k - w, d1); if (i > 0) U(k - w - 1, d2); if (i < w - 1) U(k - w + 1, d2); }
                    A[k] = v;
                }
            for (int j = h - 1; j >= 0; j--)
                for (int i = w - 1; i >= 0; i--)
                {
                    int k = j * w + i; if (Blk(k)) continue; float v = A[k];
                    Action<int, float> U = (q, d) => { if (Blk(q)) return; float c = A[q] + s * d; if (max ? c > v : c < v) v = c; };
                    if (i < w - 1) U(k + 1, d1);
                    if (j < h - 1) { U(k + w, d1); if (i < w - 1) U(k + w + 1, d2); if (i > 0) U(k + w - 1, d2); }
                    A[k] = v;
                }
        }
    }

    /// <summary>点 p から多角形の辺までの最短距離と、その辺の上の最寄りの点。</summary>
    static float ClosestOnPoly(Vector2[] poly, Vector2 p, out Vector2 q)
    {
        float best = float.MaxValue; q = p;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length], ab = b - a;
            float l2 = ab.sqrMagnitude;
            float tt = l2 < 1e-12f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2);
            var c = a + ab * tt; float d = Vector2.Distance(p, c);
            if (d < best) { best = d; q = c; }
        }
        return best;
    }

    // ------------------------------------------------------------ 部材の天端を引く(空間の升で引く)
    // ⭐ 天端 = **上を向いた面**(法線の y > UP_NY)だけ。城の石垣の駒の控え(背の斜面)や石の尻は土に入るのが正しい納めなので、
    //   皮を下げる相手にしない(2026-09-24 実測: 全ての面で下げたら上の段の地盤が控えに沿って 3.4m 掘れた)。
    //   底(Bottom)は全ての面で引く。
    const float UP_NY = 0.7f;
    /// <summary>天端の帯の深さ・周りを見る半径[m](<see cref="TopIndex.banded"/>)。0.15 = 野面の天端の石の凹凸(±0.08)は入り、
    /// 天端の奥の控え(天端 − 0.3)は外れる ── 控えは上の面の土に入るのが正しい納め(0.3 では控えを天端と読み、背の帯に 0.25m の溝が残った)。</summary>
    public const float CREST_BAND = 0.15f, CREST_R = 0.6f;
    sealed class TopIndex
    {
        readonly List<Vector3[]> tris = new List<Vector3[]>();
        readonly List<int> owner = new List<int>();
        readonly List<bool> up = new List<bool>();
        readonly Dictionary<long, List<int>> hash = new Dictionary<long, List<int>>();
        const float B = 1f;
        public readonly List<Vector2[]> hulls = new List<Vector2[]>();
        public readonly List<string> names = new List<string>();
        public readonly List<Vector4> bounds = new List<Vector4>();   // 外形の外接矩形 (x0, z0, x1, z1)
        static long K(int i, int j) { return ((long)i << 32) ^ (uint)j; }
        /// <summary>天端の帯で篩う駒(土留め)。⭐ その駒の上向きの面は、周り <see cref="CREST_R"/> の同じ駒の最も高い上向きの面から
        /// <see cref="CREST_BAND"/> 以内だけを天端と読む ── 法(見え面)の石の上向きの小面を天端と取り違えて、足元の面を掘らない
        /// (2026-09-25 EDO-0430 実測: 本殿の西の野面の土留めの足で 28.30 の面が 27.99〜28.07 へ掘れ、石の下端が歯のように覗いた)。</summary>
        public readonly List<bool> banded = new List<bool>();
        public void Add(GameObject g) { Add(g, false); }
        public void Add(GameObject g, bool crestBand)
        {
            var ts = TrisOfMat(g.transform, null); if (ts.Count == 0) return;
            var hull = HullOfMat(g.transform, null); if (hull == null || hull.Length < 3) return;
            int k = hulls.Count; hulls.Add(hull); names.Add(g.name); banded.Add(crestBand);
            { float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
              foreach (var q in hull) { a0 = Mathf.Min(a0, q.x); a1 = Mathf.Max(a1, q.x); b0 = Mathf.Min(b0, q.y); b1 = Mathf.Max(b1, q.y); }
              bounds.Add(new Vector4(a0, b0, a1, b1)); }
            // 表の向き: 時計回りが表(Unity)。鏡に写した駒(行列式 < 0)は巻きが逆になる。
            var mf0 = g.GetComponentInChildren<MeshFilter>();
            float sgn = (mf0 != null ? mf0.transform.localToWorldMatrix.determinant : g.transform.localToWorldMatrix.determinant) < 0f ? -1f : 1f;
            foreach (var t in ts)
            {
                int id = tris.Count; tris.Add(t); owner.Add(k);
                var nv = Vector3.Cross(t[1] - t[0], t[2] - t[0]); float mag = nv.magnitude;
                up.Add(mag > 1e-9f && sgn * nv.y / mag > UP_NY);
                float x0 = Mathf.Min(t[0].x, Mathf.Min(t[1].x, t[2].x)), x1 = Mathf.Max(t[0].x, Mathf.Max(t[1].x, t[2].x));
                float z0 = Mathf.Min(t[0].z, Mathf.Min(t[1].z, t[2].z)), z1 = Mathf.Max(t[0].z, Mathf.Max(t[1].z, t[2].z));
                for (int i = Mathf.FloorToInt(x0 / B); i <= Mathf.FloorToInt(x1 / B); i++)
                    for (int j = Mathf.FloorToInt(z0 / B); j <= Mathf.FloorToInt(z1 / B); j++)
                    {
                        List<int> l; if (!hash.TryGetValue(K(i, j), out l)) { l = new List<int>(); hash[K(i, j)] = l; }
                        l.Add(id);
                    }
            }
        }
        /// <summary>(x,z) の真上の部材の**上を向いた面**の最も高い所(= 天端・踏面)。無ければ NaN。<paramref name="who"/> = その部材。</summary>
        public float Top(float x, float z, out int who)
        {
            float y = Scan(x, z, true, out who);
            if (who < 0 || !banded[who] || float.IsNaN(y)) return y;
            // 天端の帯: 周りの同じ駒の最も高い上向きの面 − CREST_BAND より低ければ法の面(天端でない)
            float mx = y;
            for (int a = 0; a < 8; a++)
            {
                float ang = a * Mathf.PI / 4f; float t2 = ScanOwner(x + Mathf.Cos(ang) * CREST_R, z + Mathf.Sin(ang) * CREST_R, who);
                if (!float.IsNaN(t2) && t2 > mx) mx = t2;
            }
            if (y < mx - CREST_BAND) { who = -1; return float.NaN; }
            return y;
        }
        /// <summary>篩わない天端(帯で外した法の面も含む)。</summary>
        public float TopRaw(float x, float z, out int who) { return Scan(x, z, true, out who); }
        float ScanOwner(float x, float z, int k)
        {
            float best = float.NaN, y;
            List<int> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return best;
            foreach (var id in l)
                if (owner[id] == k && up[id] && TriYAt(tris[id], x, z, out y) && (float.IsNaN(best) || y > best)) best = y;
            return best;
        }
        /// <summary>(x,z) の部材の最も低い面(= 底)。</summary>
        public float Bottom(float x, float z, out int who) { return Scan(x, z, false, out who); }
        /// <summary>(x,z) から平面で <paramref name="r"/> 以内を通る**鉛直な面**(石垣の見え面・小口)の、その位置での最も低い所。
        /// ⭐ 鉛直な面は平面に面積が無いので <see cref="Bottom"/> の縦の線に掛からない ── 殻の駒(底の面が無い)の見え面の脇では
        /// 底が天端に化けて「駒が浮く」と誤って数えた(2026-09-25 EDO-0430: 回廊の基壇・御供所の郭の石垣で 3,243 点)。無ければ NaN。</summary>
        public float WallBottom(float x, float z, float r, int only = -1)
        {
            float best = float.NaN;
            int i0 = Mathf.FloorToInt((x - r) / B), i1 = Mathf.FloorToInt((x + r) / B), j0 = Mathf.FloorToInt((z - r) / B), j1 = Mathf.FloorToInt((z + r) / B);
            var seen = new HashSet<int>();
            for (int i = i0; i <= i1; i++)
                for (int j = j0; j <= j1; j++)
                {
                    List<int> l; if (!hash.TryGetValue(K(i, j), out l)) continue;
                    foreach (var id in l)
                    {
                        if (!seen.Add(id) || (only >= 0 && owner[id] != only)) continue;
                        var t = tris[id];
                        var nv = Vector3.Cross(t[1] - t[0], t[2] - t[0]); float mag = nv.magnitude; if (mag < 1e-9f || Mathf.Abs(nv.y) / mag > 0.2f) continue;
                        // 平面で最も離れた二頂点を軸に取る
                        int a = 0, b = 1; float dmax = -1f;
                        for (int u = 0; u < 3; u++) for (int v = u + 1; v < 3; v++)
                            { float d = new Vector2(t[u].x - t[v].x, t[u].z - t[v].z).sqrMagnitude; if (d > dmax) { dmax = d; a = u; b = v; } }
                        if (dmax < 1e-6f) continue;
                        Vector2 A = new Vector2(t[a].x, t[a].z), ab = new Vector2(t[b].x, t[b].z) - A; float L2 = ab.sqrMagnitude;
                        float uq = Vector2.Dot(new Vector2(x, z) - A, ab) / L2; if (uq < -1e-3f || uq > 1f + 1e-3f) continue;
                        if ((A + ab * Mathf.Clamp01(uq) - new Vector2(x, z)).magnitude > r) continue;
                        for (int e = 0; e < 3; e++)
                        {
                            var p0 = t[e]; var p1 = t[(e + 1) % 3];
                            float u0 = Vector2.Dot(new Vector2(p0.x, p0.z) - A, ab) / L2, u1 = Vector2.Dot(new Vector2(p1.x, p1.z) - A, ab) / L2;
                            float lo = Mathf.Min(u0, u1), hi = Mathf.Max(u0, u1); if (uq < lo - 1e-3f || uq > hi + 1e-3f) continue;
                            float yy = hi - lo < 1e-5f ? Mathf.Min(p0.y, p1.y) : Mathf.Lerp(p0.y, p1.y, Mathf.Clamp01((uq - u0) / (u1 - u0)));
                            if (float.IsNaN(best) || yy < best) best = yy;
                        }
                    }
                }
            return best;
        }
        float Scan(float x, float z, bool top, out int who)
        {
            who = -1; float best = float.NaN, y;
            List<int> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return best;
            foreach (var id in l)
            {
                if (top && !up[id]) continue;
                if (TriYAt(tris[id], x, z, out y) && (float.IsNaN(best) || (top ? y > best : y < best))) { best = y; who = owner[id]; }
            }
            return best;
        }
    }

    /// <summary>**縁の皮を起こす。**<paramref name="parts"/>(石段・袖・土留め)の外形に掛かる地形の升と、
    /// <paramref name="faces"/> の縁で地形が面の高さから <paramref name="faceTol"/> を超えて外れる升に穴を開け、
    /// その升を <paramref name="step"/> 格子の皮で描く(皮は <paramref name="parent"/> の下に 1 枚)。
    /// ⛔ 高さ(heightmap)は動かさない。⛔ 呼ぶ前に同じ親の古い皮を <see cref="ClearEdgeSkins"/> で外すこと。
    /// 硬い条件(許容0): 皮が部材の天端に被らない・皮と部材の間に隙が無い ── 報告の <see cref="SkinReport.coverN"/> /
    /// <see cref="SkinReport.gapN"/>。</summary>
    /// <para>⭐ <paramref name="design"/> を渡すと(2026-09-25・EDO-0430)、**面の縁を升の境でなく面の多角形の線で切る**:
    /// 面の中は面の高さ、面の外は設計の地盤(<see cref="SkinDesign"/> の外の節点だけで引く)を、囲いの無い縁では
    /// 縁の線から法(切 1:batterCut / 盛 1:batterFill)で受ける。縁から <see cref="BAND"/> 以内で、2m 格子の地形がこれと
    /// <paramref name="drawTol"/> を超えて違う升を穴にする(升の中の縁の外側は設計の地盤 = 元の地形を皮で写す)。</para>
    /// <para>⭐ <paramref name="backfill"/> &gt; 0 のとき(1:n の盛土の法)、**部材の底より下に地形がある所は皮を部材の底まで盛る**
    /// (裏込めの土)── 外形の縁から <see cref="FLAT"/> までは底の高さ、その外は 1:n で元の地形へ下ろす。硬い条件(許容0)は
    /// 皮と部材の底の隙 0(<see cref="SkinReport.gapN"/>)。⛔ 掘らない(皮は元の地形より下げない側の話ではなく、上げる側)。</para>
    public static SkinReport CutEdgeSkin(string name, Transform parent, IList<GameObject> parts, IList<SkinFace> faces,
                                         float faceTol, float step = 0.25f, float margin = 0.5f, float eps = 0f, float under = 0.15f,
                                         SkinDesign design = null, float drawTol = 0.10f, float backfill = 0f, bool sealFace = false,
                                         IList<GameObject> digParts = null, float digUnder = 0.05f, float digBatter = 1f,
                                         IList<GameObject> crestBandParts = null)
    {
        var r = new SkinReport();
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int R = td.holesResolution; float cs = td.size.x / R;
        int N = Mathf.RoundToInt(cs / step);
        if (Mathf.Abs(N * step - cs) > 1e-4f) throw new Exception("皮の格子 " + step + " が穴の升 " + cs + " を割り切らない");
        var probe = Probe();

        // ---- 1 部材
        var idx = new TopIndex();
        var bandSet = crestBandParts != null ? new HashSet<GameObject>(crestBandParts) : null;
        foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g, bandSet != null && bandSet.Contains(g));
        r.parts = idx.hulls.Count;

        // ---- 2 穴の升
        var cells = new HashSet<long>();
        Func<int, int, long> CK = (i, j) => ((long)i << 32) ^ (uint)j;
        Func<float, int> CI = x => Mathf.FloorToInt((x - org.x) / cs);
        Func<float, int> CJ = z => Mathf.FloorToInt((z - org.z) / cs);
        var partCells = new HashSet<long>();
        foreach (var h in idx.hulls)
        {
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var p in h) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
            for (int i = CI(mnx - margin); i <= CI(mxx + margin); i++)
                for (int j = CJ(mnz - margin); j <= CJ(mxz + margin); j++)
                {
                    var lo = new Vector2(org.x + i * cs, org.z + j * cs);
                    if (RectOverlapsPoly(lo - Vector2.one * margin, lo + Vector2.one * (cs + margin), h)) partCells.Add(CK(i, j));
                }
        }
        // ⭐ 背を下げる部材(digParts): 天端 − digUnder から 1:digBatter で上る天井を皮に掛ける。升は DIG_REACH まで開ける
        //   (皮の縁 = 地形のままの点が天井より内に来ないように)。当たる先: `copingRise:"line"` の石段の袖。
        var digH = new List<Vector2[]>(); var digC = new List<Vector2>(); var digB = new List<Vector4>();
        if (digParts != null)
            foreach (var g in digParts)
            {
                if (g == null || !g.activeInHierarchy) continue;
                var h = HullOfMat(g.transform, null); if (h == null || h.Length < 3) continue;
                Vector2 c = Vector2.zero; float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var q in h) { c += q; mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
                digH.Add(h); digC.Add(c / h.Length); digB.Add(new Vector4(mnx, mnz, mxx, mxz));
                for (int i = CI(mnx - DIG_REACH); i <= CI(mxx + DIG_REACH); i++)
                    for (int j = CJ(mnz - DIG_REACH); j <= CJ(mxz + DIG_REACH); j++)
                    {
                        var lo = new Vector2(org.x + i * cs, org.z + j * cs);
                        if (RectOverlapsPoly(lo - Vector2.one * DIG_REACH, lo + Vector2.one * (cs + DIG_REACH), h)) partCells.Add(CK(i, j));
                    }
            }
        Func<Vector2, float> DigCap = q =>
        {
            float cap = float.NaN;
            for (int k = 0; k < digH.Count; k++)
            {
                var b = digB[k];
                if (q.x < b.x - DIG_REACH || q.x > b.z + DIG_REACH || q.y < b.y - DIG_REACH || q.y > b.w + DIG_REACH) continue;
                if (EdoGeom.PIP(digH[k], q)) continue;
                Vector2 cq; float d = ClosestOnPoly(digH[k], q, out cq); if (d > DIG_REACH) continue;
                Vector2 inw = cq + (digC[k] - cq).normalized * 0.05f;
                int who; float top = idx.Top(inw.x, inw.y, out who); if (float.IsNaN(top)) continue;
                float v = top - digUnder + d / Mathf.Max(0.1f, digBatter);
                if (float.IsNaN(cap) || v < cap) cap = v;
            }
            return cap;
        };
        var faceCells = new HashSet<long>();
        if (faces != null)
            foreach (var f in faces)
            {
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var p in f.poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
                for (int i = CI(mnx); i <= CI(mxx); i++)
                    for (int j = CJ(mnz); j <= CJ(mxz); j++)
                    {
                        float x0 = org.x + i * cs, z0 = org.z + j * cs; bool bad = false;
                        for (float x = x0 + 0.125f; x < x0 + cs && !bad; x += 0.25f)
                            for (float z = z0 + 0.125f; z < z0 + cs && !bad; z += 0.25f)
                                if (EdoGeom.PIP(f.poly, new Vector2(x, z)) && Mathf.Abs(probe.At(x, z) - f.y) > faceTol) bad = true;
                        if (!bad) continue;
                        for (int di = -1; di <= 1; di++) for (int dj = -1; dj <= 1; dj++) faceCells.Add(CK(i + di, j + dj));
                    }
            }

        // ---- 2b 点と部材・面の関係、面の外の設計の地盤(2026-09-25)
        // 点と部材の外形の関係: 2 = 外形の中 / 1 = 外形から NEAR 以内 / 0 = 離れている
        const float NEAR = 0.5f;
        Func<Vector2, float, int> NearAt = (q, nr) =>
        {
            int v = 0;
            for (int h = 0; h < idx.hulls.Count && v < 2; h++)
            {
                var hb = idx.bounds[h];
                if (q.x < hb.x - nr || q.x > hb.z + nr || q.y < hb.y - nr || q.y > hb.w + nr) continue;
                if (EdoGeom.PIP(idx.hulls[h], q)) v = 2;
                else if (EdgeDist(idx.hulls[h], q) < nr) v = 1;
            }
            return v;
        };
        // ⭐ 造成しない地盤の引き手(2026-09-25・EDO-0430): 地形の双一次だが、部材の外形の中に落ちた節点は造成前の地盤に置き換える。
        //   外形の中の節点は石垣の天端の側の高さ(整地が設計面の双一次で写した値)を持ち、見え面の前へ三角に張り出す ── その値を
        //   見え面の前の地盤に混ぜない。置き換える節点が無い升では地形そのもの(probe)。
        //   当たる先: 皮が設計面の外を描くすべての土留め・石垣の見え面の前(山王 TW_* 全て・野面の土留め・袖)。
        int HR = td.heightmapResolution; float hs = td.size.x / (HR - 1);
        var cleanNode = new Dictionary<long, float>();
        Func<int, int, float> NodeClean = (ni, nj) =>
        {
            long k = CK(ni, nj); float v; if (cleanNode.TryGetValue(k, out v)) return v;
            v = float.NaN;
            var q = new Vector2(org.x + ni * hs, org.z + nj * hs);
            if (NearAt(q, 0f) == 2) v = design.baseAt(q.x, q.y);
            cleanNode[k] = v; return v;
        };
        Func<float, float, float> CleanAt = (x, z) =>
        {
            if (design == null || design.baseAt == null) return probe.At(x, z);
            float fi = (x - org.x) / hs, fj = (z - org.z) / hs; int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj);
            float tx = fi - i, tz = fj - j;
            float a = NodeClean(i, j), b = NodeClean(i + 1, j), c = NodeClean(i, j + 1), d = NodeClean(i + 1, j + 1);
            if (float.IsNaN(a) && float.IsNaN(b) && float.IsNaN(c) && float.IsNaN(d)) return probe.At(x, z);
            if (float.IsNaN(a)) a = td.GetHeight(i, j) + org.y; if (float.IsNaN(b)) b = td.GetHeight(i + 1, j) + org.y;
            if (float.IsNaN(c)) c = td.GetHeight(i, j + 1) + org.y; if (float.IsNaN(d)) d = td.GetHeight(i + 1, j + 1) + org.y;
            return Mathf.Lerp(Mathf.Lerp(a, b, tx), Mathf.Lerp(c, d, tx), tz);
        };
        // 面の多角形(面積の小さい順 = 入れ子なら内の面が勝つ)
        var fl = new List<SkinFace>(); if (faces != null) fl.AddRange(faces);
        fl.Sort((a, b) => Area(a.poly).CompareTo(Area(b.poly)));
        Func<Vector2, float> FaceY = q => { foreach (var f in fl) if (EdoGeom.PIP(f.poly, q)) return f.y; return float.NaN; };
        // 設計の地盤の節点が面の中か(面の中の節点は面の外の点に混ぜない)
        var nodeIn = new Dictionary<long, bool>();
        Func<int, int, bool> NodeOut = (i, j) =>
        {
            if (design == null || i < 0 || j < 0 || i >= design.nx || j >= design.nz || !design.ok[j * design.nx + i]) return false;
            long k = CK(i, j); bool inF;
            if (!nodeIn.TryGetValue(k, out inF)) { inF = !float.IsNaN(FaceY(new Vector2(design.x0 + i * design.step, design.z0 + j * design.step))); nodeIn[k] = inF; }
            return !inF;
        };
        Func<float, float, float> DesignOut = (x, z) =>
        {
            if (design == null) return float.NaN;
            float fx = (x - design.x0) / design.step, fz = (z - design.z0) / design.step;
            int i = Mathf.FloorToInt(fx), j = Mathf.FloorToInt(fz); float tx = fx - i, tz = fz - j;
            double sw = 0, sv = 0, wm = 0;
            for (int di = 0; di <= 1; di++)
                for (int dj = 0; dj <= 1; dj++)
                {
                    float w = (di == 1 ? tx : 1f - tx) * (dj == 1 ? tz : 1f - tz);
                    if (w <= 1e-6f) continue;
                    int ni = i + di, nj = j + dj;
                    bool none = ni < 0 || nj < 0 || ni >= design.nx || nj >= design.nz || !design.ok[nj * design.nx + ni];
                    if (none) { wm += w; continue; }                      // 設計面の外の節点
                    if (!NodeOut(ni, nj)) continue;                       // 面の中の節点(面の外の点に混ぜない)
                    sw += w; sv += w * design.h[nj * design.nx + ni];
                }
            if (sw <= 0.05) return float.NaN;
            // ⭐ 欠けた隅があるときは「設計面 − 造成しない地盤」の差を混ぜ、その点の造成しない地盤に足す(2026-09-25・EDO-0430)。
            //   値そのものを混ぜると 1m 先のセルの高さが急な斜面の点へ写り、見え面の前に +0.1〜0.2m の段が残った。
            if (wm > 1e-6 && design.baseAt != null)
            {
                float gp = CleanAt(x, z);
                if (!float.IsNaN(gp))
                {
                    double ds = 0, dw = 0;
                    for (int di = 0; di <= 1; di++)
                        for (int dj = 0; dj <= 1; dj++)
                        {
                            float w = (di == 1 ? tx : 1f - tx) * (dj == 1 ? tz : 1f - tz);
                            if (w <= 1e-6f) continue;
                            int ni = i + di, nj = j + dj;
                            bool none = ni < 0 || nj < 0 || ni >= design.nx || nj >= design.nz || !design.ok[nj * design.nx + ni];
                            if (none) { dw += w; continue; }
                            if (!NodeOut(ni, nj)) continue;
                            float gc = CleanAt(design.x0 + ni * design.step, design.z0 + nj * design.step); if (float.IsNaN(gc)) continue;
                            ds += w * (design.h[nj * design.nx + ni] - gc); dw += w;
                        }
                    if (dw > 1e-6) return gp + (float)(ds / dw);
                }
            }
            // ⭐ 設計面の外の節点の重みは地形(造成しない地盤)で埋める(2026-09-25・EDO-0430)。⛔ 設計面の縁の値を外へ平らに延ばさない ──
            //   回廊の基壇の東の斜面で、設計面の縁(z 862)の値が 1m 外まで平らに延び、登る地形との間に幅 1m・深さ 0.2〜0.35m の溝が立った。
            if (wm > 1e-6) { float g = CleanAt(x, z); if (!float.IsNaN(g)) { sv += wm * g; sw += wm; } }
            return (float)(sv / sw);
        };
        // 面の外の点の描く高さ: 設計の地盤(無ければ地形)を、最寄りの**囲いの無い**面の縁から法で受ける。
        //   囲い(部材)が縁に立つ所は法を当てない(土留めの前に盛土を出さない)。sloped = 法で受けたか。
        Func<Vector2, bool[], float> OutsideY = (q, sloped) =>
        {
            float s = DesignOut(q.x, q.y); if (float.IsNaN(s)) s = CleanAt(q.x, q.y);
            if (design == null) return s;
            float bd = BATTER_REACH; SkinFace bf = default(SkinFace); Vector2 bq = Vector2.zero; bool found = false;
            foreach (var f in fl) { Vector2 cq; float d = ClosestOnPoly(f.poly, q, out cq); if (d < bd) { bd = d; bf = f; bq = cq; found = true; } }
            if (!found || NearAt(bq, WALLED) != 0) return s;
            float t = s > bf.y ? Mathf.Min(s, bf.y + bd / Mathf.Max(design.batterCut, 1e-3f))
                               : Mathf.Max(s, bf.y - bd / Mathf.Max(design.batterFill, 1e-3f));
            if (sloped != null && Mathf.Abs(t - s) > 1e-3f) sloped[0] = true;
            return t;
        };

        // ---- 2c 面の縁の線の帯: 縁から BAND 以内で、2m 格子の地形が描く高さと drawTol を超えて違う升
        var bandCells = new HashSet<long>();
        if (design != null)
            foreach (var f in fl)
            {
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var p in f.poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
                for (int i = CI(mnx - BAND); i <= CI(mxx + BAND); i++)
                    for (int j = CJ(mnz - BAND); j <= CJ(mxz + BAND); j++)
                    {
                        long ck = CK(i, j); if (bandCells.Contains(ck)) continue;
                        float x0 = org.x + i * cs, z0 = org.z + j * cs; bool bad = false;
                        for (float x = x0; x <= x0 + cs + 1e-4f && !bad; x += 0.5f)
                            for (float z = z0; z <= z0 + cs + 1e-4f && !bad; z += 0.5f)
                            {
                                var q = new Vector2(x, z);
                                if (EdgeDist(f.poly, q) > BAND || NearAt(q, NEAR) != 0) continue;
                                float want = FaceY(q); if (float.IsNaN(want)) want = OutsideY(q, null);
                                if (Mathf.Abs(want - probe.At(x, z)) > drawTol) bad = true;
                            }
                        if (bad) bandCells.Add(ck);
                    }
            }
        foreach (var c in bandCells) if (!faceCells.Contains(c)) { faceCells.Add(c); }

        // ---- 2d 裏込め: 部材の底から外へ 1:backfill で下ろす盛土の面(密な格子・chamfer)
        //   種 = 外形の辺を 0.25m で歩いた点の底(縁から 0.05/0.15/0.30m 内の最も低い面 ── MeasureSkin と同じ定義)を、
        //   その点から FLAT 以内の格子点へ。⛔ 部材の底より上の地形は触らない(max を取るだけ)。
        //   ⭐ 三つの枷(2026-09-25 実測: 枷なしでは回廊の基壇の背の 29.0 が壁を越えて表へ伝わり、石垣を丸ごと土に埋めた):
        //     ① 部材の外形の中は伝えない(種の帯を除く)── 背の盛土が駒を抜けて表へ出ない
        //     ② 天井 = 各辺の底から 1:backfill で**上る**面の最小 ── 石垣の表の根(底が低い辺)の前へ盛土を被せない
        //     ③ 皮の縁(地形のまま残す点)から 1:backfill で上る面の最小 ── 穴を開けられない升(地形の木)の脇で崖を作らない
        float[] FF = null, FC = null; bool[] FS = null, FB = null, FCS = null; int fgi0 = 0, fgj0 = 0, fw = 0, fh = 0;
        var fillCells = new HashSet<long>();
        float fd1 = 0f, fd2 = 0f;
        if (backfill > 0f && idx.hulls.Count > 0)
        {
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var hb in idx.bounds) { mnx = Mathf.Min(mnx, hb.x); mnz = Mathf.Min(mnz, hb.y); mxx = Mathf.Max(mxx, hb.z); mxz = Mathf.Max(mxz, hb.w); }
            fgi0 = Mathf.Max(0, Mathf.FloorToInt((mnx - FILL_REACH - org.x) / step)); fgj0 = Mathf.Max(0, Mathf.FloorToInt((mnz - FILL_REACH - org.z) / step));
            int fgi1 = Mathf.Min(R * N, Mathf.CeilToInt((mxx + FILL_REACH - org.x) / step)), fgj1 = Mathf.Min(R * N, Mathf.CeilToInt((mxz + FILL_REACH - org.z) / step));
            fw = fgi1 - fgi0 + 1; fh = fgj1 - fgj0 + 1;
            FF = new float[fw * fh]; FC = new float[fw * fh]; FS = new bool[fw * fh]; FB = new bool[fw * fh]; FCS = new bool[fw * fh];
            for (int k = 0; k < FF.Length; k++) { FF[k] = float.NegativeInfinity; FC[k] = float.PositiveInfinity; }
            // ① 外形の中の格子点
            for (int k = 0; k < idx.hulls.Count; k++)
            {
                var hb = idx.bounds[k];
                int i0 = Mathf.Max(0, Mathf.CeilToInt((hb.x - org.x) / step) - fgi0), i1 = Mathf.Min(fw - 1, Mathf.FloorToInt((hb.z - org.x) / step) - fgi0);
                int j0 = Mathf.Max(0, Mathf.CeilToInt((hb.y - org.z) / step) - fgj0), j1 = Mathf.Min(fh - 1, Mathf.FloorToInt((hb.w - org.z) / step) - fgj0);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                        if (!FB[j * fw + i] && EdoGeom.PIP(idx.hulls[k], new Vector2(org.x + (i + fgi0) * step, org.z + (j + fgj0) * step))) FB[j * fw + i] = true;
            }
            int FR = Mathf.CeilToInt(FLAT / step);
            for (int k = 0; k < idx.hulls.Count; k++)
            {
                var h = idx.hulls[k];
                Vector2 cen = Vector2.zero; foreach (var q in h) cen += q; cen /= h.Length;
                for (int e = 0; e < h.Length; e++)
                {
                    Vector2 A = h[e], Bv = h[(e + 1) % h.Length], ab = Bv - A; float L = ab.magnitude; if (L < 1e-4f) continue;
                    Vector2 tn = ab / L, nrm = new Vector2(tn.y, -tn.x);
                    if (Vector2.Dot(nrm, (A + Bv) * 0.5f - cen) < 0) nrm = -nrm;
                    int ns = Mathf.Max(1, Mathf.CeilToInt(L / step));
                    for (int si = 0; si <= ns; si++)
                    {
                        var pe = A + tn * (L * si / ns);
                        float bot = float.NaN; int wb;
                        foreach (var dd in new[] { 0.05f, 0.15f, 0.30f })
                        { var pq = pe - nrm * dd; float bq = idx.Bottom(pq.x, pq.y, out wb); if (!float.IsNaN(bq) && (float.IsNaN(bot) || bq < bot)) bot = bq; }
                        if (float.IsNaN(bot)) continue;
                        // ② の天井の種は「外が開いた地面で、地面が底より低い(駒が浮く)辺」だけ ── 隣の駒の中へ入る継ぎ目の辺・
                        //   地面に埋まった辺は種にしない(継ぎ目の辺の底は控えの深い所で、背の盛土を丸ごと押さえてしまう)。
                        var po = pe + nrm * 0.05f; bool ceil = probe.At(po.x, po.y) < bot;
                        if (ceil)
                            for (int k2 = 0; k2 < idx.hulls.Count && ceil; k2++)
                            {
                                if (k2 == k) continue; var b2 = idx.bounds[k2];
                                if (po.x < b2.x || po.x > b2.z || po.y < b2.y || po.y > b2.w) continue;
                                if (EdoGeom.PIP(idx.hulls[k2], po)) ceil = false;
                            }
                        int ci = Mathf.RoundToInt((pe.x - org.x) / step) - fgi0, cj = Mathf.RoundToInt((pe.y - org.z) / step) - fgj0;
                        for (int di = -FR; di <= FR; di++)
                            for (int dj = -FR; dj <= FR; dj++)
                            {
                                int ii = ci + di, jj = cj + dj; if (ii < 0 || jj < 0 || ii >= fw || jj >= fh) continue;
                                float gx = org.x + (ii + fgi0) * step, gz = org.z + (jj + fgj0) * step;
                                if ((gx - pe.x) * (gx - pe.x) + (gz - pe.y) * (gz - pe.y) > FLAT * FLAT) continue;
                                int kk = jj * fw + ii; if (bot > FF[kk]) FF[kk] = bot; FS[kk] = true;
                                // 天井の種は辺の外の側だけ(薄い駒で内の種が表へ抜けない)
                                if (ceil && (gx - pe.x) * nrm.x + (gz - pe.y) * nrm.y >= -1e-3f) { if (bot < FC[kk]) FC[kk] = bot; FCS[kk] = true; }
                            }
                    }
                }
            }
            fd1 = step / backfill; fd2 = step * 1.41421356f / backfill;
            Chamfer(FF, fw, fh, fd1, fd2, true, FB, FS, 3);
            Chamfer(FC, fw, fh, fd1, fd2, false, FB, FCS, 3);
            // 盛る所の升(盛土の面が地形より 0.02m を超えて高い点に触れる升)
            for (int j = 0; j < fh; j++)
                for (int i = 0; i < fw; i++)
                {
                    int k = j * fw + i; float v = Mathf.Min(FF[k], FC[k]); if (float.IsInfinity(v)) continue;
                    int gi = i + fgi0, gj = j + fgj0; float x = org.x + gi * step, z = org.z + gj * step;
                    if (v <= probe.At(x, z) + 0.02f) continue;
                    int ci = Mathf.FloorToInt((float)gi / N), cj = Mathf.FloorToInt((float)gj / N);
                    int ciLo = (gi % N == 0) ? ci - 1 : ci, cjLo = (gj % N == 0) ? cj - 1 : cj;
                    for (int ii = ciLo; ii <= ci; ii++) for (int jj = cjLo; jj <= cj; jj++) fillCells.Add(CK(ii, jj));
                }
        }
        float[] FP = null;   // ③ 皮の縁から上る天井(穴の升が決まってから引く)
        Func<int, int, float> FillAt = (gi, gj) =>
        {
            if (FF == null) return float.NaN;
            int i = gi - fgi0, j = gj - fgj0; if (i < 0 || j < 0 || i >= fw || j >= fh) return float.NaN;
            int k = j * fw + i; float v = Mathf.Min(FF[k], FC[k]); if (FP != null) v = Mathf.Min(v, FP[k]);
            return float.IsInfinity(v) ? float.NaN : v;
        };
        Func<int, int, bool> FillSeeded = (gi, gj) =>
        {
            if (FS == null) return false;
            int i = gi - fgi0, j = gj - fgj0; return i >= 0 && j >= 0 && i < fw && j < fh && FS[j * fw + i];
        };

        foreach (var c in partCells) cells.Add(c);
        foreach (var c in faceCells) cells.Add(c);
        foreach (var c in fillCells) cells.Add(c);
        // ⛔ 地形の木が立つ升には穴を開けない ── Unity は穴の升の地形の木を消す(SetHoles でも SetTreeInstances でも。
        //    2026-09-24 実測: 山王の社叢 70 本が消えた)。その升は地形のまま残し、報告に数える。
        var treeCells = new HashSet<long>();
        foreach (var ti in td.treeInstances)
            treeCells.Add(CK(CI(org.x + ti.position.x * td.size.x), CJ(org.z + ti.position.z * td.size.z)));
        // ⭐ 地形の木の升で裏込めが要る所は、穴を開けずに皮を**地形の上に被せる**(盛る側は穴が要らない・2026-09-25)。
        //   盛らない点は地形の下 OV_SINK へ沈めて隠す。木はそのまま(根元が盛土に入る)。
        var overlay = new HashSet<long>();
        foreach (var c in treeCells) if (cells.Remove(c)) { r.skipTree++; if (fillCells.Contains(c)) { overlay.Add(c); r.fillLostTree++; } }
        if (cells.Count == 0 && overlay.Count == 0) { r.mesh = "—"; return r; }
        int ci0 = int.MaxValue, ci1 = int.MinValue, cj0 = int.MaxValue, cj1 = int.MinValue;
        var cellsAll = new List<long>(cells); cellsAll.AddRange(overlay);
        foreach (var c in cellsAll) { int i = (int)(c >> 32), j = (int)(uint)(c & 0xffffffff); ci0 = Mathf.Min(ci0, i); ci1 = Mathf.Max(ci1, i); cj0 = Mathf.Min(cj0, j); cj1 = Mathf.Max(cj1, j); }
        ci0 = Mathf.Max(0, ci0); cj0 = Mathf.Max(0, cj0); ci1 = Mathf.Min(R - 1, ci1); cj1 = Mathf.Min(R - 1, cj1);
        int bw = ci1 - ci0 + 1, bh = cj1 - cj0 + 1;
        var hv = HolesBlock(td, ci0, cj0, bw, bh);
        var inSet = new bool[bh, bw]; var inOv = new bool[bh, bw];
        foreach (var c in overlay)
        {
            int i = (int)(c >> 32), j = (int)(uint)(c & 0xffffffff);
            if (i < ci0 || i > ci1 || j < cj0 || j > cj1 || !hv[j - cj0, i - ci0]) continue;
            inOv[j - cj0, i - ci0] = true;
        }
        foreach (var c in cells)
        {
            int i = (int)(c >> 32), j = (int)(uint)(c & 0xffffffff);
            if (i < ci0 || i > ci1 || j < cj0 || j > cj1) continue;
            if (!hv[j - cj0, i - ci0]) { r.skipHole++; continue; }     // 既に穴(井戸の口など)── 触らない
            inSet[j - cj0, i - ci0] = true; r.cells++;
            if (partCells.Contains(c)) r.cellsParts++;
            else if (faceCells.Contains(c)) { r.cellsFace++; if (bandCells.Contains(c)) r.cellsBand++; }
            else r.cellsFill++;
        }
        Func<int, int, bool> In = (i, j) => i >= ci0 && i <= ci1 && j >= cj0 && j <= cj1 && (inSet[j - cj0, i - ci0] || inOv[j - cj0, i - ci0]);
        Func<int, int, bool> Hole = (i, j) => i >= ci0 && i <= ci1 && j >= cj0 && j <= cj1 && inSet[j - cj0, i - ci0];
        if (FF != null)
        {
            // ③ 皮の縁(穴の升と地形の升の境の格子点 = 地形のまま)から 1:backfill で上る天井
            FP = new float[fw * fh]; var FPS = new bool[fw * fh];
            for (int k = 0; k < FP.Length; k++) FP[k] = float.PositiveInfinity;
            for (int j = 0; j < fh; j++)
                for (int i = 0; i < fw; i++)
                {
                    int gi = i + fgi0, gj = j + fgj0; int ci = Mathf.FloorToInt((float)gi / N), cj = Mathf.FloorToInt((float)gj / N);
                    int ciLo = (gi % N == 0) ? ci - 1 : ci, cjLo = (gj % N == 0) ? cj - 1 : cj;
                    bool anyIn = false, anyOut = false;
                    for (int ii = ciLo; ii <= ci; ii++) for (int jj = cjLo; jj <= cj; jj++) { if (In(ii, jj)) anyIn = true; else anyOut = true; }
                    if (!anyOut) continue;
                    int k = j * fw + i; FP[k] = probe.At(org.x + gi * step, org.z + gj * step); FPS[k] = true;
                }
            Chamfer(FP, fw, fh, fd1, fd2, false, null, FPS, 2);
        }

        // ---- 3 皮の高さ(格子の点ごと)
        // 格子の点 (gi, gj) = 地形の原点 + (gi, gj) × step。升 (i, j) の中は gi ∈ [iN, (i+1)N]。
        var H = new Dictionary<long, float>(); var O = new Dictionary<long, float>(); var PIN = new HashSet<long>(); var SUNK = new HashSet<long>();
        var topCache = new Dictionary<long, float>(); var faceTop = new HashSet<long>();
        // 部材の天端(篩わない)。⭐ 天端の帯で篩う駒(crestBandParts)の**法の面**の点は faceTop に記す ──
        //   そこでは天端の下へ納める cap を**足元の面の高さより下げない**(法の足は面の下へ入るのが正しい納め・掘らない)。
        Func<int, int, float> TopL = (gi, gj) =>
        {
            long k = CK(gi, gj); float v;
            if (topCache.TryGetValue(k, out v)) return v;
            int who; float x = org.x + gi * step, z = org.z + gj * step;
            v = idx.TopRaw(x, z, out who);
            if (!float.IsNaN(v) && who >= 0 && idx.banded[who] && float.IsNaN(idx.Top(x, z, out who))) faceTop.Add(k);
            topCache[k] = v; return v;
        };
        var botCache = new Dictionary<long, float>();
        Func<int, int, float> BotL = (gi, gj) =>
        {
            long k = CK(gi, gj); float v;
            if (botCache.TryGetValue(k, out v)) return v;
            int who; v = idx.Bottom(org.x + gi * step, org.z + gj * step, out who);
            botCache[k] = v; return v;
        };
        // 周りの天端で下げる範囲(格子の数)。2 = 0.5m ── 皮の四角の隅が外形から 0.35m 外にあっても天端の下へ入る。
        const int CAPR = 2;
        Func<Vector2, bool> InBandedHull = q =>
        {
            for (int h = 0; h < idx.hulls.Count; h++)
            {
                if (!idx.banded[h]) continue; var hb = idx.bounds[h];
                if (q.x < hb.x || q.x > hb.z || q.y < hb.y || q.y > hb.w) continue;
                if (EdoGeom.PIP(idx.hulls[h], q)) return true;
            }
            return false;
        };
        var nearCache = new Dictionary<long, int>();
        Func<int, int, int> NearPart = (gi, gj) =>
        {
            long k = CK(gi, gj); int v; if (nearCache.TryGetValue(k, out v)) return v;
            v = NearAt(new Vector2(org.x + gi * step, org.z + gj * step), NEAR);
            nearCache[k] = v; return v;
        };
        for (int i = ci0; i <= ci1; i++)
            for (int j = cj0; j <= cj1; j++)
            {
                if (!In(i, j)) continue;
                for (int a = 0; a <= N; a++)
                    for (int b = 0; b <= N; b++)
                    {
                        int gi = i * N + a, gj = j * N + b; long k = CK(gi, gj);
                        if (H.ContainsKey(k)) continue;
                        float x = org.x + gi * step, z = org.z + gj * step;
                        float orig = probe.At(x, z); O[k] = orig;
                        // 縁の点: 触れる升(1〜4)のどれかが穴でない ⇒ 地形のまま
                        bool edge = false;
                        int iLo = (a == 0) ? i - 1 : i, iHi = (a == N) ? i + 1 : i, jLo = (b == 0) ? j - 1 : j, jHi = (b == N) ? j + 1 : j;
                        for (int ii = iLo; ii <= iHi && !edge; ii++) for (int jj = jLo; jj <= jHi && !edge; jj++)
                                if ((ii == i || a == 0 || a == N) && (jj == j || b == 0 || b == N) && !In(ii, jj)) edge = true;
                        // 被せるだけの点(触れる皮の升が全部 地形の木の升)
                        bool ovOnly = true;
                        for (int ii = iLo; ii <= iHi && ovOnly; ii++) for (int jj = jLo; jj <= jHi && ovOnly; jj++)
                                if ((ii == i || a == 0 || a == N) && (jj == j || b == 0 || b == N) && Hole(ii, jj)) ovOnly = false;
                        if (edge) { H[k] = ovOnly ? orig - OV_SINK : orig; if (ovOnly) SUNK.Add(k); PIN.Add(k); continue; }
                        if (ovOnly)
                        {
                            float fo = FillAt(gi, gj), ho = orig - OV_SINK;
                            { float fy = FaceY(new Vector2(x, z)); if (!float.IsNaN(fy) && !float.IsNaN(fo)) fo = Mathf.Min(fo, fy + faceTol - 0.02f); }
                            if (!float.IsNaN(fo) && fo > orig + 1e-3f) { ho = fo; r.filled++; if (fo - orig > r.fillMax) { r.fillMax = fo - orig; r.fillAt = new Vector3(x, fo, z); } }
                            if (ho < orig) SUNK.Add(k);
                            H[k] = ho; continue;
                        }
                        float hgt = orig;
                        var p = new Vector2(x, z);
                        // 面の高さ: 部材の外形の中では当てない(部材の中の地盤は部材の面が決める)。
                        //   面の縁の外へ 1.5 格子まで伸ばすのは、部材から NEAR より離れた所だけ(土留めの背へ棚を出さない)。
                        bool faced = false; int near = NearPart(gi, gj);
                        if (near < 2)
                        {
                            foreach (var f in fl) if (EdoGeom.PIP(f.poly, p)) { hgt = f.y; faced = true; break; }
                            // ⭐ 設計があれば部材から NEAR 以内の外の点も設計の地盤で描く(2026-09-25・EDO-0430)── 地形のままにすると
                            //   駒の下の節点(天端の側の高さ)が見え面の足元へ山形を立てる。面の縁の延長(設計の無い枝)は従来どおり離れた点だけ。
                            if (!faced && (near == 0 || design != null))
                            {
                                if (design != null)
                                {
                                    // ⭐ 面の外 = 設計の地盤を縁の線から法で受ける(升の境で切らない)
                                    var sl = new bool[1]; hgt = OutsideY(p, sl);
                                    if (Mathf.Abs(hgt - orig) > 0.005f) r.designed++;
                                    if (sl[0]) r.sloped++;
                                }
                                else foreach (var f in fl) if (EdgeDist(f.poly, p) < step * 1.5f) { hgt = f.y; faced = true; break; }
                            }
                        }
                        // ⭐ 部材の外形の中で面の外の点も、設計があれば設計の地盤で描く(下の cap で駒の面の下へ納める)(2026-09-25・EDO-0430)。
                        //   地形のままにすると、法の足(外形の縁)の手前 0.3〜0.6m が駒の下の節点(天端の側の高さ)に引かれ、cap(法の面 − under)まで
                        //   持ち上がって見え面の足元に高さ 1m の土の尾根が立った(回廊の基壇の東の北半・犬走りの床の上)。
                        //   ⛔ 上げない(下げるだけ)── 切通しの石段の袖の外形の中は整地の後に天端の下へ下げてあり(TuckUnderCrest)、設計の地盤へ
                        //   上げると袖の天端を 0.59m 埋めた。
                        //   部材の底(その点の最も低い面)より下げない ── 男坂の袖(底が設計の地盤より 0.08m 高い)の外形の縁で、内の点を設計の地盤へ
                        //   下げると縁の 0.05m 外で底の下が 0.017m 覗いた。法の駒の底は根入れ(設計の地盤の下)なので効かない。
                        if (near == 2 && !faced && design != null && float.IsNaN(FaceY(p)))
                        {
                            //   ⚠ 底の面が無い殻の駒(城の石垣・隅)は Bottom が上の面そのもの ── 底と見なさない(天端まで上げて面の重なり 5 → 63)。
                            float dz = OutsideY(p, null); float bl = BotL(gi, gj), tl = TopL(gi, gj);
                            //   底が設計の地盤 + (faceTol − 0.02) を超えて高い駒は駒の側の話(sealFace と同じ許容)── 野面の法の足の石の下面(25.4〜25.5)
                            //   まで上げると犬走りの床 25.05 の上に 0.45m の土の縁が立った。
                            if (!float.IsNaN(bl) && !float.IsNaN(tl) && tl - bl > 0.05f && bl <= dz + faceTol - 0.02f) dz = Mathf.Max(dz, bl);
                            hgt = Mathf.Min(hgt, dz);
                        }
                        // ⭐ 天端の帯で篩う駒の**法の面の下**(外形の中・天端の帯の外)は、その点の面の高さで描く ── 法の足・控えは面の土の下へ入る
                        //   (2026-09-25: 野面の背と腰石垣の間の帯 SukibeiSoto_Chu が、腰石垣の深い法の上で元の地形 28.85 のまま 0.4m の溝になった)。
                        //   上向きの面が無い点(城の石垣の急な法の真下)も同じ ── 篩う駒の外形の中に限る。
                        if (near == 2 && !faced && (faceTop.Contains(CK(gi, gj)) || (float.IsNaN(TopL(gi, gj)) && InBandedHull(p))))
                        { float fy = FaceY(p); if (!float.IsNaN(fy)) { hgt = fy; faced = true; } }
                        if (faced) r.faced++;
                        float hgt0 = hgt;
                        // 部材の天端の下へ納める(真下 = 天端 − under / 周り 8 点の天端の最小 − eps)
                        float self = TopL(gi, gj), cap = float.NaN, capN1 = float.NaN;
                        // 法の面の cap の下限: 外形の外の点はその点の描く地盤(面・設計の地盤)、外形の中は足元の面(無ければ下限なし)
                        //   ── 法の足は地盤の下へ入るのが正しい納め。⛔ 法の面へ向けて地盤を掘り下げない(野面の隅の南で 29.55 → 27.88 と掘れた)。
                        //   面の外(造成しない地盤)では、法の面が地盤より 2×帯 を超えて低いときだけ ── 打ち切りの駒の先の天端が地盤へ沈む所
                        //   (天端が急に下がり帯で篩われる)は地盤の方を天端へ下げて被せない。
                        float fyIn = near < 2 ? float.NaN : FaceY(p);
                        Func<float, float> Floor = tq =>
                        {
                            if (near == 2 && !float.IsNaN(fyIn)) return Mathf.Max(tq, fyIn);
                            //   面の外の外形の中(出隅の駒の地盤側の腕など)も、法が地盤より 2×帯 を超えて低ければ地盤で止める
                            //   (野面の隅 kado3 の南の腕の下に 27.95 の穴が口を開けた・2026-09-25)
                            if (faced || hgt0 - tq > 2f * CREST_BAND) return Mathf.Max(tq, hgt0);
                            return tq;
                        };
                        if (!float.IsNaN(self)) { cap = self - under; if (faceTop.Contains(CK(gi, gj))) cap = Floor(cap); }
                        for (int di = -CAPR; di <= CAPR; di++)
                            for (int dj = -CAPR; dj <= CAPR; dj++)
                            {
                                if (di == 0 && dj == 0) continue;
                                float tq = TopL(gi + di, gj + dj); if (float.IsNaN(tq)) continue;
                                tq -= eps; if (faceTop.Contains(CK(gi + di, gj + dj))) tq = Floor(tq);
                                if (float.IsNaN(cap) || tq < cap) cap = tq;
                                if (Mathf.Abs(di) <= 1 && Mathf.Abs(dj) <= 1 && (float.IsNaN(capN1) || tq < capN1)) capN1 = tq;
                            }
                        // 裏込めの天端の下限: 外形の縁の帯(FLAT)では真下の天端 − FILL_UNDER まで・周りは 1 格子(0.25m)の天端まで。
                        //   ⭐ 土留めの背(駒に背の面が無く、底 = 天端)では皮が天端の高さまで来ないと縁の 0.05m 外で底を割る
                        //   (2026-09-25 実測: 前庭の西の土留めの背で 0.06〜0.10m)。
                        float capF = capN1;
                        if (!float.IsNaN(self)) { float sc = self - (FillSeeded(gi, gj) ? FILL_UNDER : under); capF = float.IsNaN(capF) ? sc : Mathf.Min(capF, sc); }
                        float pre = hgt;
                        if (!float.IsNaN(cap) && hgt > cap) { hgt = cap; r.clamped++; if (!float.IsNaN(self)) r.under++; }
                        // ⭐ 裏込め(backfill > 0): 部材の底より下にある所は底まで盛る。外形の中では(縁の FLAT の帯を除き)
                        //   その点の部材の底より上げない(駒の面から皮を出さない)。天端の下へ納める cap は守る。
                        float fv = FillAt(gi, gj);
                        if (!float.IsNaN(fv))
                        {
                            // 外形の中はその点の駒の底(最も低い面)より上げない ── 継ぎ目の辺の種が石垣の法の面を突き抜けて
                            //   表に土の筋を立てた(2026-09-25 回廊の基壇の東で実測)。背の縁(底 = 天端)では底 = 天端なので効かない。
                            if (near == 2) { float bs = BotL(gi, gj); if (!float.IsNaN(bs)) fv = Mathf.Min(fv, bs); }
                            // 造成の面の中は面の高さ + (faceTol − 0.02) より上げない(面は設計が決める・面の許容の内でだけ盛る)。
                            //   それより底の高い駒(開いた背が面より高い)は駒の側の話 ── 皮で隠さず隙に数える。
                            //   2026-09-25 実測: 底の無い駒の底 = 天端を種にした盛土が前庭の面へ 1.6m 溢れた。
                            //   ⚠ 部材から NEAR 以内は面の多角形の帰属があいまい(土留めの背が下の段の面の内に入る)なので当てない。
                            if (faced && near == 0) fv = Mathf.Min(fv, hgt0 + faceTol - 0.02f);
                            if (!float.IsNaN(capF)) fv = Mathf.Min(fv, capF);
                            if (fv > hgt + 1e-4f)
                            {
                                hgt = fv; r.filled++;
                                if (fv - orig > r.fillMax) { r.fillMax = fv - orig; r.fillAt = new Vector3(x, fv, z); }
                            }
                        }
                        // ⭐ 面の高さの皮で背を塞ぐ(sealFace・2026-09-25 普請奉行の決め・EDO-0430): 面の中で部材から NEAR 以内の外の点は、
                        //   隣の部材の底が皮より高く、かつ面 + (faceTol − 0.02) 以内なら底まで上げる(面の許容の内 ── 盛土の法は作らない)。
                        //   底は鉛直な見え面の下の縁も数える(殻の石垣の見え面の脇で底が天端に化けない)。それより高い底は駒の側の話。
                        //   外形の中の縁の帯(FLAT)の点も、その点の部材の底まで上げる(外の点と結ぶ三角形が縁で底を割らない)。
                        else if (sealFace && near >= 1 && fl.Count > 0)
                        {
                            float fy = FaceY(p);
                            // ⭐ 面の外(設計の地盤)も同じ許容で塞ぐ(2026-09-25・EDO-0430): 基準はその点の地盤(Stage1 が設計面へ写した値)。
                            //   男坂の北の袖の背(見え面が外を向く盛り上げの石段)で、設計の地盤が袖の底より 0.13m 低く底の下が覗いた ──
                            //   設計面の 2m 格子と部材の実の底の差で、許容の内。許容を超える底は駒の側の話(隙に数える)のは面の中と同じ。
                            if (float.IsNaN(fy) && !faced) fy = hgt;
                            bool rim = near == 1 || EdgeDistAny(idx, p, FLAT);
                            if (!float.IsNaN(fy) && rim)
                            {
                                // 隣の部材ごとに「底 = 最も低い面と鉛直な面の下の縁の低い方」を取り、その最大
                                float nb = float.NaN;
                                // ⭐ 半格子(0.125m)の点も見る ── 底が背の縁へ向かって上がる駒(袖の背の縁の面取り)では、格子の隣の底が
                                //   縁の底より 0.09m 低く、塞いでも縁の 0.05m 外で底の下が覗いた(2026-09-25 男坂の北の袖)。
                                int rr = near == 2 ? 0 : 2;
                                for (int di = -rr; di <= rr; di++)
                                    for (int dj = -rr; dj <= rr; dj++)
                                    {
                                        int who; float qx = org.x + (gi + di * 0.5f) * step, qz = org.z + (gj + dj * 0.5f) * step;
                                        float bq = idx.Bottom(qx, qz, out who); if (float.IsNaN(bq)) continue;
                                        // 鉛直な面の下の縁はその点のごく近く(0.2m)で取る ── 0.6m では段ごとに底が上がる袖で下の段の縁を拾い、
                                        //   縁の底より 0.08m 低く塞いだ。近くに無ければ(殻の石垣の見え面から離れた点)広く取る。
                                        float wb = idx.WallBottom(qx, qz, 0.2f, who); if (float.IsNaN(wb)) wb = idx.WallBottom(qx, qz, NEAR + 0.1f, who);
                                        if (!float.IsNaN(wb)) bq = Mathf.Min(bq, wb);
                                        if (float.IsNaN(nb) || bq > nb) nb = bq;
                                    }
                                if (!float.IsNaN(nb) && nb > hgt + 1e-4f && nb <= fy + faceTol - 0.02f)
                                {
                                    float v = near == 2 ? nb : nb + 0.005f; if (!float.IsNaN(capF)) v = Mathf.Min(v, capF);
                                    if (v > hgt) { hgt = v; r.sealed_++; }
                                }
                            }
                        }
                        // 外形の外の点は、隣(0.25m)の部材の底より下げない(= 部材の下を覗かせない・隙 0)。
                        //   段の脇で下の段の天端に引かれて上の段の底より下がるのを止める。元から底より低い所は触らない。
                        //   ⭐ 比べるのは元の地形(orig)── 設計の地盤で下げた点も同じ(2026-09-25・EDO-0430: 男坂の袖の縁で設計の地盤が底より
                        //   0.08m 低く、cap で下げていないので床の判定を素通りして底の下が 0.017m 覗いた)。
                        if (hgt < Mathf.Max(pre, orig) && near < 2 && float.IsNaN(fv))
                        {
                            float floor = float.NaN;
                            for (int di = -1; di <= 1; di++)
                                for (int dj = -1; dj <= 1; dj++)
                                {
                                    int who; float qx = org.x + (gi + di) * step, qz = org.z + (gj + dj) * step;
                                    float bq = idx.Bottom(qx, qz, out who); if (float.IsNaN(bq)) continue;
                                    // 殻の駒(底の面が無い石垣)は鉛直な見え面の下の縁が底 ── 天端を底と取り違えて地盤を戻さない
                                    //   鉛直な面の下の縁はごく近く(0.2m)で取り、無ければ広く(sealFace と同じ ── 0.6m では隣の段の縁を拾い床が 0.02 足りない)
                                    float wb = idx.WallBottom(qx, qz, 0.2f, who); if (float.IsNaN(wb)) wb = idx.WallBottom(qx, qz, NEAR + 0.1f, who);
                                    if (!float.IsNaN(wb)) bq = Mathf.Min(bq, wb);
                                    if (float.IsNaN(floor) || bq > floor) floor = bq;
                                }
                            if (!float.IsNaN(floor) && hgt < floor) { hgt = Mathf.Min(Mathf.Max(pre, orig), floor); r.floored++; }
                        }
                        if (digH.Count > 0 && near < 2)
                        {
                            float dc = DigCap(p);
                            if (!float.IsNaN(dc) && hgt > dc)
                            {
                                if (hgt - dc > r.digMax) { r.digMax = hgt - dc; r.digAt = new Vector3(x, dc, z); }
                                hgt = dc; r.dug++;
                            }
                        }
                        H[k] = hgt;
                        if (orig - hgt > r.maxLower) { r.maxLower = orig - hgt; r.lowerAt = new Vector3(x, hgt, z); }
                        if (hgt - orig > r.maxRaise) { r.maxRaise = hgt - orig; r.raiseAt = new Vector3(x, hgt, z); }
                    }
            }
        r.pinned = PIN.Count;

        // ---- 4 メッシュ
        var go = new GameObject(SKIN_PREFIX + name);
        go.transform.SetParent(parent, false);
        go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
        var inv = go.transform.worldToLocalMatrix;
        var V = new List<Vector3>(); var NM = new List<Vector3>(); var UV = new List<Vector2>(); var TR = new List<int>();
        var vid = new Dictionary<long, int>();
        Func<long, float> HAt = k => { float v; return H.TryGetValue(k, out v) ? v : float.NaN; };
        Func<int, int, int> Vx = (gi, gj) =>
        {
            long k = CK(gi, gj); int id; if (vid.TryGetValue(k, out id)) return id;
            float x = org.x + gi * step, z = org.z + gj * step, y = H[k];
            Vector3 n;
            if (PIN.Contains(k)) n = td.GetInterpolatedNormal((x - org.x) / td.size.x, (z - org.z) / td.size.z);
            else
            {
                float hl = HAt(CK(gi - 1, gj)), hr = HAt(CK(gi + 1, gj)), hd = HAt(CK(gi, gj - 1)), hu = HAt(CK(gi, gj + 1));
                if (float.IsNaN(hl)) hl = y; if (float.IsNaN(hr)) hr = y; if (float.IsNaN(hd)) hd = y; if (float.IsNaN(hu)) hu = y;
                n = new Vector3(-(hr - hl) / (2f * step), 1f, -(hu - hd) / (2f * step)).normalized;
            }
            id = V.Count; V.Add(inv.MultiplyPoint3x4(new Vector3(x, y, z))); NM.Add(inv.MultiplyVector(n).normalized);
            UV.Add(new Vector2((x - org.x) / td.size.x, (z - org.z) / td.size.z)); vid[k] = id; return id;
        };
        for (int i = ci0; i <= ci1; i++)
            for (int j = cj0; j <= cj1; j++)
            {
                if (!In(i, j)) continue;
                for (int a = 0; a < N; a++)
                    for (int b = 0; b < N; b++)
                    {
                        int gi = i * N + a, gj = j * N + b;
                        int v00 = Vx(gi, gj), v10 = Vx(gi + 1, gj), v01 = Vx(gi, gj + 1), v11 = Vx(gi + 1, gj + 1);
                        TR.Add(v00); TR.Add(v01); TR.Add(v11); TR.Add(v00); TR.Add(v11); TR.Add(v10);
                    }
                // 垂れ(穴の縁 ── 隣の升が地形)。両面。
                for (int side = 0; side < 4; side++)
                {
                    int ni = i + (side == 0 ? -1 : side == 1 ? 1 : 0), nj = j + (side == 2 ? -1 : side == 3 ? 1 : 0);
                    if (In(ni, nj)) continue;
                    for (int s = 0; s < N; s++)
                    {
                        int ga, gb, gc, gd;
                        if (side <= 1) { int gi = (side == 0 ? i : i + 1) * N; ga = gi; gb = j * N + s; gc = gi; gd = j * N + s + 1; }
                        else { int gj = (side == 2 ? j : j + 1) * N; ga = i * N + s; gb = gj; gc = i * N + s + 1; gd = gj; }
                        int top0 = Vx(ga, gb), top1 = Vx(gc, gd);
                        int b0 = V.Count; V.Add(V[top0] - inv.MultiplyVector(Vector3.up) * 0.3f); NM.Add(NM[top0]); UV.Add(UV[top0]);
                        int b1 = V.Count; V.Add(V[top1] - inv.MultiplyVector(Vector3.up) * 0.3f); NM.Add(NM[top1]); UV.Add(UV[top1]);
                        TR.Add(top0); TR.Add(top1); TR.Add(b1); TR.Add(top0); TR.Add(b1); TR.Add(b0);
                        TR.Add(top0); TR.Add(b1); TR.Add(top1); TR.Add(top0); TR.Add(b0); TR.Add(b1);
                    }
                }
            }
        var m = new Mesh { indexFormat = IndexFormat.UInt32 };
        m.SetVertices(V); m.SetNormals(NM); m.SetUVs(0, UV); m.SetTriangles(TR, 0); m.RecalculateBounds(); m.RecalculateTangents();
        r.verts = V.Count; r.tris = TR.Count / 3;
        m = EdoSolidMesh.Save(m, SKIN_PREFIX + name);
        r.mesh = AssetDatabase.GetAssetPath(m);
        go.AddComponent<MeshFilter>().sharedMesh = m;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterials = SkinMaterials(t);
        mr.shadowCastingMode = ShadowCastingMode.On; mr.receiveShadows = true;

        // ---- 5 穴を開ける
        for (int j = 0; j < bh; j++) for (int i = 0; i < bw; i++) if (inSet[j, i] && hv[j, i]) { hv[j, i] = false; r.holesCut++; }   // ⛔ 被せる升(inOv)は開けない
        td.SetHoles(ci0, cj0, hv);

        // ---- 6 芝(皮が元の地形から 0.02m を超えて動いた 1m 升)と地形の木の数え
        {
            int D = td.detailResolution; float dx = td.size.x / D, dz = td.size.z / D;
            var mark = new HashSet<long>();
            foreach (var kv in H)
            {
                if (Mathf.Abs(kv.Value - O[kv.Key]) <= 0.02f || SUNK.Contains(kv.Key)) continue;   // 地形の下へ沈めた被せの点は芝を残す
                int gi = (int)(kv.Key >> 32), gj = (int)(uint)(kv.Key & 0xffffffff);
                float x = gi * step, z = gj * step;   // 地形の原点からの距離
                for (int sx = -1; sx <= 1; sx += 2) for (int sz = -1; sz <= 1; sz += 2)
                        mark.Add(CK(Mathf.FloorToInt((x + sx * 0.01f) / dx), Mathf.FloorToInt((z + sz * 0.01f) / dz)));
            }
            if (mark.Count > 0)
            {
                int di0 = int.MaxValue, di1 = int.MinValue, dj0 = int.MaxValue, dj1 = int.MinValue;
                foreach (var c in mark) { int i = (int)(c >> 32), j = (int)(uint)(c & 0xffffffff); di0 = Mathf.Min(di0, i); di1 = Mathf.Max(di1, i); dj0 = Mathf.Min(dj0, j); dj1 = Mathf.Max(dj1, j); }
                di0 = Mathf.Clamp(di0, 0, D - 1); di1 = Mathf.Clamp(di1, 0, D - 1); dj0 = Mathf.Clamp(dj0, 0, D - 1); dj1 = Mathf.Clamp(dj1, 0, D - 1);
                int w = di1 - di0 + 1, h = dj1 - dj0 + 1;
                var changed = new bool[h, w];
                for (int l = 0; l < td.detailPrototypes.Length; l++)
                {
                    var d = DetailBlock(td, di0, dj0, w, h, l); bool any = false;
                    for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
                            if (d[j, i] != 0 && mark.Contains(CK(di0 + i, dj0 + j))) { d[j, i] = 0; changed[j, i] = true; any = true; }
                    if (any) td.SetDetailLayer(di0, dj0, l, d);
                }
                foreach (var b in changed) if (b) r.detCells++;
            }
            foreach (var ti in td.treeInstances)
            {
                float x = org.x + ti.position.x * td.size.x, z = org.z + ti.position.z * td.size.z;
                int i = CI(x), j = CJ(z); if (!In(i, j)) continue;
                int gi = Mathf.RoundToInt((x - org.x) / step), gj = Mathf.RoundToInt((z - org.z) / step);
                float hh, oo; if (!H.TryGetValue(CK(gi, gj), out hh) || !O.TryGetValue(CK(gi, gj), out oo)) continue;
                if (Mathf.Abs(hh - oo) > 0.05f) r.trees++;
            }
        }
        EditorUtility.SetDirty(td);

        // ---- 7 検め(硬い・許容0)── 皮を描かれた地表として測る
        MeasureSkin(idx, ref r, null);
        return r;
    }

    /// <summary>皮と部材の取り合いを測り直す(皮を起こし直さずに)。<paramref name="samples"/> に隙の点を最大 20 行刷る。</summary>
    public static SkinReport MeasureSkinContact(IList<GameObject> parts, List<string> samples = null, IList<GameObject> crestBandParts = null)
    {
        var bs = crestBandParts != null ? new HashSet<GameObject>(crestBandParts) : null;
        var idx = new TopIndex(); foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g, bs != null && bs.Contains(g));
        var r = new SkinReport(); r.parts = idx.hulls.Count; r.mesh = "—";
        MeasureSkin(idx, ref r, samples); return r;
    }

    /// <summary>皮と部材の隙を三つに分けて刷る(2026-09-25 普請奉行の決め・EDO-0430):
    /// **A 面の高さで塞がる**(外が面の中・部材の底 ≤ 面 + 許容)/ **B 駒が浮く**(外が面の中・底 &gt; 面 + 許容 ── 駒を据え直すか
    /// 丈の足りる駒に替える)/ **C 取り合い**(外が面の外で地表が底より低い ── 壁の外形と面の輪郭の取り合い)。
    /// 外へ 0.35m の所が他の駒の外形の中なら駒どうしの溝の中で**見えない**隙に数える。駒ごとの件数と最大を返す。</summary>
    public static string SkinGapTable(IList<GameObject> parts, IList<SkinFace> faces, float faceTol)
    {
        var idx = new TopIndex(); foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g);
        var dg = Drawn();
        var fl = new List<SkinFace>(); if (faces != null) fl.AddRange(faces);
        fl.Sort((a, b) => Area(a.poly).CompareTo(Area(b.poly)));
        // 駒ごと・類ごと: 件数・最大・その点
        var tab = new SortedDictionary<string, float[]>(StringComparer.Ordinal);   // [n, max, x, z, faceY or NaN, bottom]
        int[] cnt = new int[4]; int[] hid = new int[4];
        for (int k = 0; k < idx.hulls.Count; k++)
        {
            var h = idx.hulls[k];
            Vector2 cen = Vector2.zero; foreach (var q in h) cen += q; cen /= h.Length;
            for (int e = 0; e < h.Length; e++)
            {
                Vector2 A = h[e], Bv = h[(e + 1) % h.Length], ab = Bv - A; float L = ab.magnitude; if (L < 1e-4f) continue;
                Vector2 tn = ab / L, nrm = new Vector2(tn.y, -tn.x);
                if (Vector2.Dot(nrm, (A + Bv) * 0.5f - cen) < 0) nrm = -nrm;
                for (float s = 0.05f; s < L - 0.05f; s += 0.1f)
                {
                    var pe = A + tn * s; var pin = pe - nrm * 0.05f; var pout = pe + nrm * 0.05f;
                    // ⭐ 皮の外(地形のまま)の点も測る ── 斜面が壁の底より低い取り合いは皮の外に出る
                    int w1, w2;
                    // 被りは天端の帯で測る(帯で篩う駒の法の面は、足元の面の下へ入る根入れ ── 被りに数えない)。隙は篩わない天端の有無で測る。
                    float top = idx.Top(pin.x, pin.y, out w1), topRaw = idx.TopRaw(pin.x, pin.y, out w2), bot = idx.Bottom(pin.x, pin.y, out w2);
                    for (int q = 1; q <= 2; q++)
                    { var pq = pe - nrm * (0.15f * q); float bq = idx.Bottom(pq.x, pq.y, out w2); if (!float.IsNaN(bq) && (float.IsNaN(bot) || bq < bot)) bot = bq; }
                    // 鉛直な見え面・小口の下の縁(殻の駒)も底に数える
                    { float wb = idx.WallBottom(pe.x, pe.y, 0.10f); if (!float.IsNaN(wb) && (float.IsNaN(bot) || wb < bot)) bot = wb; }
                    if (float.IsNaN(top)) continue;
                    bool covered = false; foreach (var h2 in idx.hulls) if (EdoGeom.PIP(h2, pout)) { covered = true; break; }
                    if (covered) continue;
                    float gout = dg.At(pout.x, pout.y); if (float.IsNaN(gout) || gout >= bot - 0.01f) continue;
                    float fy = float.NaN; string fn = "-";
                    foreach (var f in fl) if (EdoGeom.PIP(f.poly, pout)) { fy = f.y; fn = f.name; break; }
                    int c = float.IsNaN(fy) ? 2 : (bot <= fy + faceTol - 0.02f ? 0 : 1);
                    var far = pe + nrm * 0.35f; bool hide = false;
                    for (int k2 = 0; k2 < idx.hulls.Count && !hide; k2++) if (k2 != k && EdoGeom.PIP(idx.hulls[k2], far)) hide = true;
                    if (hide) { hid[c]++; continue; }
                    cnt[c]++;
                    // 見え面(ローカル +X)の側か背の側か
                    var gk = parts[0] == null ? null : FindPart(parts, idx.names[k]);
                    string side = gk == null ? "?" : (Vector2.Dot(nrm, new Vector2(gk.transform.right.x, gk.transform.right.z)) > 0.5f ? "表" :
                                                     Vector2.Dot(nrm, new Vector2(gk.transform.right.x, gk.transform.right.z)) < -0.5f ? "背" : "小口");
                    string key = "ABC"[c] + " " + idx.names[k] + " " + side + (c == 2 ? "" : "〔面 " + fn + "〕");
                    float over = c == 1 ? bot - fy : bot - gout;
                    float[] v; if (!tab.TryGetValue(key, out v)) { v = new float[] { 0, -1, 0, 0, fy, bot }; tab[key] = v; }
                    v[0]++; if (over > v[1]) { v[1] = over; v[2] = pout.x; v[3] = pout.y; v[5] = bot; }
                }
            }
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("  隙の内訳(見える / 駒どうしの溝の中で見えない): A 面の高さで塞がる " + cnt[0] + " / " + hid[0] +
                      " ・ B 駒が浮く(底 > 面 + " + faceTol.ToString("F2") + ") " + cnt[1] + " / " + hid[1] +
                      " ・ C 面の外の取り合い " + cnt[2] + " / " + hid[2]);
        foreach (var kv in tab)
        {
            var v = kv.Value;
            sb.AppendLine("    " + kv.Key + " " + (int)v[0] + " 点 最大 " + v[1].ToString("F2") + "m @(" + v[2].ToString("F1") + ", " + v[3].ToString("F1") + ") 底 " + v[5].ToString("F2") +
                          (float.IsNaN(v[4]) ? "" : " 面 " + v[4].ToString("F2")));
        }
        return sb.ToString();
    }

    /// <summary>点 q が部材の外形の縁から <paramref name="d"/> 以内か(外形の中の縁の帯)。</summary>
    static bool EdgeDistAny(TopIndex idx, Vector2 q, float d)
    {
        for (int h = 0; h < idx.hulls.Count; h++)
        {
            var hb = idx.bounds[h];
            if (q.x < hb.x - d || q.x > hb.z + d || q.y < hb.y - d || q.y > hb.w + d) continue;
            if (EdgeDist(idx.hulls[h], q) < d) return true;
        }
        return false;
    }

    static GameObject FindPart(IList<GameObject> parts, string name)
    { foreach (var g in parts) if (g != null && g.name == name) return g; return null; }

    static void MeasureSkin(TopIndex idx, ref SkinReport r, List<string> samples)
    {
        var probe = Probe();
        var dg = Drawn();
        var gapBy = new Dictionary<string, int>(); var covBy = new Dictionary<string, int>();
        for (int k = 0; k < idx.hulls.Count; k++)
        {
            var h = idx.hulls[k];
            for (int e = 0; e < h.Length; e++)
            {
                Vector2 A = h[e], Bv = h[(e + 1) % h.Length], ab = Bv - A; float L = ab.magnitude; if (L < 1e-4f) continue;
                Vector2 tn = ab / L, nrm = new Vector2(tn.y, -tn.x);
                // 外向きの法線(凸包の中点から離れる向き)
                Vector2 cen = Vector2.zero; foreach (var q in h) cen += q; cen /= h.Length;
                if (Vector2.Dot(nrm, (A + Bv) * 0.5f - cen) < 0) nrm = -nrm;
                for (float s = 0.05f; s < L - 0.05f; s += 0.1f)
                {
                    var pe = A + tn * s; var pin = pe - nrm * 0.05f; var pout = pe + nrm * 0.05f;
                    if (!dg.InHole(pout.x, pout.y) && !dg.InHole(pin.x, pin.y) && !dg.Covered(pout.x, pout.y)) continue;    // 皮の外(地形)は測らない
                    int w1, w2;
                    // 被りは天端の帯で測る(帯で篩う駒の法の面は、足元の面の下へ入る根入れ ── 被りに数えない)。隙は篩わない天端の有無で測る。
                    float top = idx.Top(pin.x, pin.y, out w1), topRaw = idx.TopRaw(pin.x, pin.y, out w2), bot = idx.Bottom(pin.x, pin.y, out w2);
                    // 底は縁から 0.3m 内までの最も低い面(法のある石垣・開いた殻の駒は縁の真下に底が無い)
                    for (int q = 1; q <= 2; q++)
                    { var pq = pe - nrm * (0.15f * q); float bq = idx.Bottom(pq.x, pq.y, out w2); if (!float.IsNaN(bq) && (float.IsNaN(bot) || bq < bot)) bot = bq; }
                    // 鉛直な見え面・小口の下の縁(殻の駒)も底に数える
                    { float wb = idx.WallBottom(pe.x, pe.y, 0.10f); if (!float.IsNaN(wb) && (float.IsNaN(bot) || wb < bot)) bot = wb; }
                    if (float.IsNaN(topRaw)) continue;
                    // 被り: 外形の内で 皮 > 天端
                    float gin = dg.At(pin.x, pin.y);
                    if (!float.IsNaN(gin) && !float.IsNaN(top))
                    {
                        r.coverPts++;
                        if (gin > top + 1e-3f)
                        {
                            r.coverN++; int c0; covBy.TryGetValue(idx.names[k], out c0); covBy[idx.names[k]] = c0 + 1;
                            if (gin - top > r.coverMax) { r.coverMax = gin - top; r.coverAt = new Vector3(pin.x, top, pin.y); }
                            if (samples != null && samples.Count < 400)
                                samples.Add("[被り]" + idx.names[k] + " pin(" + pin.x.ToString("F2") + ", " + pin.y.ToString("F2") + ") 皮 " + gin.ToString("F2") + " 天端 " + top.ToString("F2") + " 外向き(" + nrm.x.ToString("F2") + ", " + nrm.y.ToString("F2") + ")");
                        }
                    }
                    // 隙: 外形の外(他の部材の下でない所)で 皮 < 底 − 0.01(部材の下が覗く)
                    bool covered = false; foreach (var h2 in idx.hulls) if (EdoGeom.PIP(h2, pout)) { covered = true; break; }
                    if (covered) continue;
                    float gout = dg.At(pout.x, pout.y); if (float.IsNaN(gout)) continue;
                    r.gapPts++;
                    if (gout < bot - 0.01f && probe.At(pout.x, pout.y) >= bot - 0.01f) r.gapBySkin++;
                    if (gout < bot - 0.01f)
                    {
                        r.gapN++; int c0; gapBy.TryGetValue(idx.names[k], out c0); gapBy[idx.names[k]] = c0 + 1;
                        if (bot - gout > 0.05f) r.gapBig++;
                        if (samples != null && samples.Count < 400 && (bot - gout > 0.05f || probe.At(pout.x, pout.y) >= bot - 0.01f))
                        { int wb; idx.Bottom(pin.x, pin.y, out wb);
                          samples.Add((dg.InHole(pout.x, pout.y) ? "[穴]" : "[地形]") + idx.names[k] + " pout(" + pout.x.ToString("F2") + ", " + pout.y.ToString("F2") + ") 皮 " + gout.ToString("F2") + " 元 " + probe.At(pout.x, pout.y).ToString("F2") + " 底 " + bot.ToString("F2") + "〔" + (wb >= 0 ? idx.names[wb] : "-") + "〕 天端 " + top.ToString("F2")); }
                        if (bot - gout > r.gapMax) { r.gapMax = bot - gout; r.gapAt = new Vector3(pout.x, bot, pout.y); }
                    }
                }
            }
        }
        r.gapBy = TopN(gapBy, 6); r.coverBy = TopN(covBy, 6);
    }

    static string TopN(Dictionary<string, int> d, int n)
    {
        var l = new List<KeyValuePair<string, int>>(d); l.Sort((a, b) => b.Value.CompareTo(a.Value));
        var s = new List<string>(); for (int i = 0; i < l.Count && i < n; i++) s.Add(l[i].Key + " " + l[i].Value);
        return string.Join("・", s);
    }
    static float Area(Vector2[] p)
    {
        float a = 0f; for (int i = 0; i < p.Length; i++) { var u = p[i]; var v = p[(i + 1) % p.Length]; a += u.x * v.y - v.x * u.y; }
        return Mathf.Abs(a) * 0.5f;
    }

    /// <summary>**皮を外して穴を塞ぐ。**<paramref name="parent"/> の下の <see cref="SKIN_PREFIX"/> の物ごとに、皮の三角形の芯が
    /// 載る地形の升を塞ぎ、皮を消し、皮のメッシュの資産も消す。返り値 = 塞いだ升の数。⛔ Undo の外。</summary>
    public static int ClearEdgeSkins(Transform parent)
    {
        if (parent == null) return 0;
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int R = td.holesResolution; float cs = td.size.x / R; int n = 0;
        var kill = new List<GameObject>();
        foreach (Transform c in parent) if (c.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) kill.Add(c.gameObject);
        foreach (var g in kill)
        {
            var mf = g.GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
            {
                var m = mf.sharedMesh; var l2w = g.transform.localToWorldMatrix; var vs = m.vertices; var tri = m.triangles;
                var cells = new HashSet<long>();
                int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
                for (int k = 0; k + 2 < tri.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((vs[tri[k]] + vs[tri[k + 1]] + vs[tri[k + 2]]) / 3f);
                    int i = Mathf.FloorToInt((c.x - org.x) / cs), j = Mathf.FloorToInt((c.z - org.z) / cs);
                    if (i < 0 || j < 0 || i >= R || j >= R) continue;
                    if (cells.Add(((long)i << 32) ^ (uint)j)) { i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
                }
                if (cells.Count > 0)
                {
                    int w = i1 - i0 + 1, h = j1 - j0 + 1;
                    var hv = HolesBlock(td, i0, j0, w, h);
                    for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
                            if (!hv[j, i] && cells.Contains(((long)(i0 + i) << 32) ^ (uint)(j0 + j))) { hv[j, i] = true; n++; }
                    td.SetHoles(i0, j0, hv);
                }
                string path = AssetDatabase.GetAssetPath(m);
                UnityEngine.Object.DestroyImmediate(g);
                if (!string.IsNullOrEmpty(path) && path.StartsWith(EdoAssets.Own.GenMeshDir, StringComparison.Ordinal)) AssetDatabase.DeleteAsset(path);
            }
            else UnityEngine.Object.DestroyImmediate(g);
        }
        if (kill.Count > 0) EditorUtility.SetDirty(td);
        return n;
    }

    /// <summary>皮の材質(本体・足し込み)を地形ごとに 1 枚ずつ起こす/結わえ直す(資産)。
    /// 地形の材質の写しに、地形の層(TerrainLayer)とスプラット(alphamapTextures)を地形と同じ名で渡す。</summary>
    static Material[] SkinMaterials(Terrain t)
    {
        var td = t.terrainData; var layers = td.terrainLayers;
        int passes = Mathf.Max(1, Mathf.CeilToInt(layers.Length / 4f));
        passes = Mathf.Min(passes, td.alphamapTextureCount);
        var outp = new Material[passes];
        if (!AssetDatabase.IsValidFolder(EdoAssets.Own.SkinMatDir))
        {
            string par = System.IO.Path.GetDirectoryName(EdoAssets.Own.SkinMatDir).Replace('\\', '/');
            AssetDatabase.CreateFolder(par, System.IO.Path.GetFileName(EdoAssets.Own.SkinMatDir));
        }
        for (int p = 0; p < passes; p++)
        {
            string path = EdoAssets.Own.SkinMat(t.name, p);
            // ⚠ 地形の材質のシェーダをそのまま使うと、地形が毎フレーム渡す層の値(_DiffuseRemapScale など)が
            //   Properties に無いので材質に保存されず、読み直すと 0 ⇒ 真っ黒(2026-09-24 実測)。層の値を宣言した写しを使う。
            var shader = Shader.Find(p == 0 ? SKIN_SHADER_BASE : SKIN_SHADER_ADD);
            if (shader == null) throw new Exception("皮のシェーダが無い: " + (p == 0 ? SKIN_SHADER_BASE : SKIN_SHADER_ADD));
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            mat.enableInstancing = false;
            mat.SetTexture("_Control", td.GetAlphamapTexture(p));
            mat.SetTextureScale("_Control", Vector2.one); mat.SetTextureOffset("_Control", Vector2.zero);
            mat.SetVector("_Control_ST", new Vector4(1, 1, 0, 0));
            bool anyNormal = false;
            for (int s = 0; s < 4; s++)
            {
                int li = p * 4 + s;
                var L = li < layers.Length ? layers[li] : null;
                string si = s.ToString();
                if (L == null)
                {
                    mat.SetTexture("_Splat" + si, null); mat.SetTexture("_Normal" + si, null); mat.SetTexture("_Mask" + si, null);
                    continue;
                }
                mat.SetTexture("_Splat" + si, L.diffuseTexture);
                var st = new Vector4(td.size.x / L.tileSize.x, td.size.z / L.tileSize.y, L.tileOffset.x / L.tileSize.x, L.tileOffset.y / L.tileSize.y);
                mat.SetTextureScale("_Splat" + si, new Vector2(st.x, st.y)); mat.SetTextureOffset("_Splat" + si, new Vector2(st.z, st.w));
                mat.SetVector("_Splat" + si + "_ST", st);
                mat.SetTexture("_Normal" + si, L.normalMapTexture); if (L.normalMapTexture != null) anyNormal = true;
                mat.SetFloat("_NormalScale" + si, L.normalScale);
                mat.SetTexture("_Mask" + si, L.maskMapTexture);
                mat.SetFloat("_LayerHasMask" + si, L.maskMapTexture != null ? 1f : 0f);
                mat.SetFloat("_Metallic" + si, L.metallic); mat.SetFloat("_Smoothness" + si, L.smoothness);
                // 滑らかさ = 層の定数(_SmoothnessSource 2)。⛔ 層の設定(赤坂は DiffuseAlphaChannel = 1)をそのまま写さない ──
                //   α = 1 の土や芝が艶を持ち、空を映して白く光った。定数にすると地形と同じ見えになる(2026-09-24 並べて撮って確認)。
                mat.SetFloat("_SmoothnessSource" + si, 2f);
                var dr = L.diffuseRemapMax; dr.w = 1f;
                mat.SetVector("_DiffuseRemapScale" + si, dr);
                mat.SetVector("_MaskMapRemapOffset" + si, L.maskMapRemapMin);
                mat.SetVector("_MaskMapRemapScale" + si, L.maskMapRemapMax - L.maskMapRemapMin);
                mat.SetFloat("_DiffuseHasAlpha" + si, 0f);
            }
            mat.SetFloat("_NumLayersCount", layers.Length);
            if (anyNormal) mat.EnableKeyword("_NORMALMAP"); else mat.DisableKeyword("_NORMALMAP");
            mat.DisableKeyword("_ALPHATEST_ON");
            mat.DisableKeyword("_TERRAIN_INSTANCED_PERPIXEL_NORMAL");
            mat.SetFloat("_EnableInstancedPerPixelNormal", 0f);
            EditorUtility.SetDirty(mat);
            outp[p] = mat;
        }
        AssetDatabase.SaveAssets();
        return outp;
    }

    // ------------------------------------------------------------ 描かれた地表
    /// <summary>**描かれた地表**を引く掴み。穴の升では皮の高さ(皮が無ければ NaN = 何も描かれていない)、
    /// それ以外は地形(SampleHeight)。シーンの <see cref="SKIN_PREFIX"/> の MeshFilter を一度だけ集める。
    /// ⛔ 1 巡の間に皮や穴を作り直したら掴み直すこと。</summary>
    public sealed class DrawnGround
    {
        readonly Terrain t; readonly float y0; readonly Vector3 org; readonly float cs;
        readonly int hi0, hj0, hw, hh; readonly bool[,] holes;
        readonly Dictionary<long, List<Vector3[]>> hash = new Dictionary<long, List<Vector3[]>>();
        const float B = 0.5f;
        public readonly int skins;
        static long K(int i, int j) { return ((long)i << 32) ^ (uint)j; }
        public DrawnGround(Terrain terrain)
        {
            t = terrain; y0 = t.transform.position.y; org = t.transform.position;
            var td = t.terrainData; int R = td.holesResolution; cs = td.size.x / R;
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var mf in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                if (mf.sharedMesh == null || !mf.gameObject.activeInHierarchy || !mf.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) continue;
                skins++;
                var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var tri = mf.sharedMesh.triangles;
                var w = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) w[i] = l2w.MultiplyPoint3x4(vs[i]);
                for (int k = 0; k + 2 < tri.Length; k += 3)
                {
                    var q = new[] { w[tri[k]], w[tri[k + 1]], w[tri[k + 2]] };
                    float x0 = Mathf.Min(q[0].x, Mathf.Min(q[1].x, q[2].x)), x1 = Mathf.Max(q[0].x, Mathf.Max(q[1].x, q[2].x));
                    float z0 = Mathf.Min(q[0].z, Mathf.Min(q[1].z, q[2].z)), z1 = Mathf.Max(q[0].z, Mathf.Max(q[1].z, q[2].z));
                    if (x1 - x0 < 1e-5f || z1 - z0 < 1e-5f) continue;       // 垂れ(鉛直)は地表でない
                    mnx = Mathf.Min(mnx, x0); mxx = Mathf.Max(mxx, x1); mnz = Mathf.Min(mnz, z0); mxz = Mathf.Max(mxz, z1);
                    for (int i = Mathf.FloorToInt(x0 / B); i <= Mathf.FloorToInt(x1 / B); i++)
                        for (int j = Mathf.FloorToInt(z0 / B); j <= Mathf.FloorToInt(z1 / B); j++)
                        {
                            List<Vector3[]> l; if (!hash.TryGetValue(K(i, j), out l)) { l = new List<Vector3[]>(); hash[K(i, j)] = l; }
                            l.Add(q);
                        }
                }
            }
            if (skins > 0)
            {
                hi0 = Mathf.Clamp(Mathf.FloorToInt((mnx - org.x) / cs) - 1, 0, R - 1); hj0 = Mathf.Clamp(Mathf.FloorToInt((mnz - org.z) / cs) - 1, 0, R - 1);
                int hi1 = Mathf.Clamp(Mathf.FloorToInt((mxx - org.x) / cs) + 1, 0, R - 1), hj1 = Mathf.Clamp(Mathf.FloorToInt((mxz - org.z) / cs) + 1, 0, R - 1);
                hw = hi1 - hi0 + 1; hh = hj1 - hj0 + 1;
                holes = HolesBlock(td, hi0, hj0, hw, hh);
            }
        }
        /// <summary>(x,z) の升が穴か(皮の範囲の中だけを見る。範囲の外の穴 ── 井戸の口など ── は false)。</summary>
        public bool InHole(float x, float z)
        {
            if (holes == null) return false;
            int i = Mathf.FloorToInt((x - org.x) / cs) - hi0, j = Mathf.FloorToInt((z - org.z) / cs) - hj0;
            return i >= 0 && j >= 0 && i < hw && j < hh && !holes[j, i];
        }
        /// <summary>(x,z) で皮が描かれているか(穴の升、または地形の上へ被せた皮が地形より高い)。</summary>
        public bool Covered(float x, float z)
        {
            if (InHole(x, z)) return true;
            if (skins == 0) return false;
            float s = Skin(x, z); return !float.IsNaN(s) && s > t.SampleHeight(new Vector3(x, 0f, z)) + y0 + 1e-3f;
        }
        /// <summary>皮の高さ(皮が無ければ NaN)。</summary>
        public float Skin(float x, float z)
        {
            List<Vector3[]> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return float.NaN;
            float best = float.NaN, y;
            foreach (var q in l) if (TriYAt(q, x, z, out y) && (float.IsNaN(best) || y > best)) best = y;
            return best;
        }
        /// <summary>描かれた地表の高さ。穴の升では皮(無ければ NaN)、それ以外は地形。</summary>
        public float At(float x, float z)
        {
            if (InHole(x, z)) return Skin(x, z);
            float g = t.SampleHeight(new Vector3(x, 0f, z)) + y0;
            // 地形の上へ被せた皮(地形の木の升の裏込め)は、地形より高い所だけ描かれる
            if (skins > 0) { float s = Skin(x, z); if (!float.IsNaN(s) && s > g) return s; }
            return g;
        }
    }

    /// <summary>描かれた地表の掴みを作る(<see cref="DrawnGround"/>)。</summary>
    public static DrawnGround Drawn() { return new DrawnGround(T()); }

    /// <summary>部材の**上を向いた面**の最も高い所を引く掴み(駒が他の駒の下に入っているかを見る)。</summary>
    public sealed class PartTops
    {
        readonly TopIndex idx = new TopIndex();
        public PartTops(IList<GameObject> parts) { foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g); }
        /// <summary>(x,z) の最も高い上向きの面と、その駒の名(無ければ NaN / null)。</summary>
        public float Top(float x, float z, out string who)
        { int w; float y = idx.Top(x, z, out w); who = w >= 0 ? idx.names[w] : null; return y; }
    }

    /// <summary>**駒の天端の埋没**を描かれた地表で数える(石段の段石など、天端が一枚の面の駒)。
    /// 天端(最も高い頂点から 0.02m 以内の頂点)のローカルの外接矩形を 0.05m 控えて <paramref name="step"/> で標本し、
    /// 描かれた地表 − 天端 > 0.01 の点を数える。返り値 = 埋没の点の数。
    /// <paramref name="over"/> を渡すと、**他の駒の面が天端より上にある点**(段石の端が袖・土留めの中へ入っている所 ──
    /// 見えない)は数えず <paramref name="hidden"/> に数える。</summary>
    public static int TopBurial(Transform piece, DrawnGround dg, PartTops over, out int samples, out int hidden,
                                out float worst, out Vector3 worstAt, float step = 0.25f)
    {
        samples = 0; hidden = 0; worst = 0f; worstAt = Vector3.zero; int n = 0;
        var pts = Body(piece, 4000, true); if (pts.Count == 0) return 0;
        float top = float.MinValue; foreach (var p in pts) top = Mathf.Max(top, p.y);
        float xmn = 1e9f, xmx = -1e9f, zmn = 1e9f, zmx = -1e9f;
        foreach (var p in pts)
        {
            if (p.y < top - 0.02f) continue; var l = piece.InverseTransformPoint(p);
            xmn = Mathf.Min(xmn, l.x); xmx = Mathf.Max(xmx, l.x); zmn = Mathf.Min(zmn, l.z); zmx = Mathf.Max(zmx, l.z);
        }
        for (float x = xmn + 0.05f; x <= xmx - 0.05f; x += step)
            for (float z = zmn + 0.05f; z <= zmx - 0.05f; z += step)
            {
                var w = piece.TransformPoint(new Vector3(x, 0, z)); samples++;
                if (over != null) { string who; float ot = over.Top(w.x, w.z, out who); if (!float.IsNaN(ot) && ot > top + 0.01f && who != piece.name) { hidden++; continue; } }
                float g = dg.At(w.x, w.z); if (float.IsNaN(g)) continue;
                float h = g - top;
                if (h > 0.01f) { n++; if (h > worst) { worst = h; worstAt = new Vector3(w.x, top, w.z); } }
            }
        return n;
    }
}
