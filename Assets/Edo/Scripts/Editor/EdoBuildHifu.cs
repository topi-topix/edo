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
    /// <summary>植栽の点(幹の足)から地形の木のピボットまでのずれの上限[m] ── 縁の皮の穴を避ける升の半径(EDO-0495)。</summary>
    const float PLANT_PIVOT_R = 0.40f;

    /// <summary>皮の GameObject の名の頭。<see cref="Drawn"/> はこの名の MeshFilter を皮と読む。</summary>
    public const string SKIN_PREFIX = "EdgeSkin_";
    /// <summary>皮のシェーダ(地形の本体・足し込みの写しに、層の値を Properties として足した物・Assets/Edo/Shaders/StochTerrain/)。</summary>
    const string SKIN_SHADER_BASE = "Edo/TerrainSkinStochastic", SKIN_SHADER_ADD = "Edo/TerrainSkinAdd";

    /// <summary>皮の中で高さを揃える造成の面(世界 XZ の多角形と面の高さ)。</summary>
    public struct SkinFace
    {
        public string name; public Vector2[] poly; public float y;
        /// <summary>この面の中で地形が面から外れてよい量[m](0 = <see cref="CutEdgeSkin"/> の faceTol)。超える升は穴を開けて皮で面を描く。
        /// 硬い面(石段の上がり口の段石の背 ±0.02 ── 岡部 K_Dan1・2026-10-07 第47巡)だけ小さくする。</summary>
        public float tol;
        public SkinFace(string name, Vector2[] poly, float y) { this.name = name; this.poly = poly; this.y = y; this.tol = 0f; }
        public SkinFace(string name, Vector2[] poly, float y, float tol) { this.name = name; this.poly = poly; this.y = y; this.tol = tol; }
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
        /// <summary>設計の持ち主の区画(無ければ null)。⭐ 区画の外の点は設計の地盤でなく**今の地形**(隣が造成した地盤)を写す ──
        /// 設計の地盤は持ち主の区画の中の話で、隣の区画の中は隣の造成が決める。⛔ 2026-09-28 まで山王社の皮が観理院の中へ
        /// 削る前の高さ(11〜13m)で芝を描き、観理院の崖の縁の石垣の前に横に通る板が浮いた(EDO-0477)。
        /// 当たる先: CutEdgeSkin に設計を渡す全邸(いまは山王社 Stage9)。</summary>
        public Vector2[] own;
        /// <summary>**法で受けない節点**(null なら無し・h と同じ並び)。立てた節点の周り(双一次の 4 点のどれか)の点は、面の外でも
        /// 最寄りの面の縁から法で受けず(OutsideY の切土の側の頭打ち)設計の地盤そのものを描く。⭐ 部材の小口に被せる土(岡部 TW_Kado_Sode の
        /// 低い端「高さ 0.15・長さ 0.25 の土を 1:1.5 で被せる」【硬】)は面(門の内 16.50)の縁の脇で面より高い ⇒ 法の頭打ちが面の高さへ
        /// 削り戻して小口が 0.15 見えた(2026-10-07 EDO-0502 第49巡)。当たる先: 設計の地盤を部材の脇で面より上へ盛る全ての欄(いまは岡部の小口の土)。</summary>
        public bool[] hold;
        /// <summary>**設計で土に埋める駒**(見え面を持たない ── 2026-10-08 EDO-0502 第56巡・指図 sodeSlope 追記 2026-10-08「低い端の水平の駒は土で完全に埋める」)。
        /// 皮の検めの「皮が部材の天端に被る」から外す(埋めるのが設計)。渡すのは盛った土(hold)を作る側。当たる先: 岡部 Stage3b の端の駒。</summary>
        public HashSet<GameObject> buried;
        /// <summary>**野面の石垣の天端の裏石の帯を土で覆う**(指図 const.nozuraCrestCover・2026-10-09 EDO-0502 第63巡)。null なら無し。
        /// <see cref="CutEdgeSkin"/> の最後(3f ── 3e の盛った土の後)に皮の節点で効かせ、皮の検めの「被り」から設計の帯を外す。</summary>
        public NozuraCrestCover crestCover;
    }

    /// <summary>**野面の石垣の天端の裏石の帯を土で覆う型**(指図 const.nozuraCrestCover・普請方の設計 2026-10-09・EDO-0502 第63巡・
    /// 施主の写真「天端が割れた板を並べたよう」── 天端の裏石 2 列の平らな帯(見え面から 0.36〜1.04)が背の土 天端−0.15 から顔を出していた)。
    /// 駒ごと・見え面ごとに実メッシュを走りの 0.1m の帯へ割り、帯ごとの天端(最も高い頂点)と天端の前の縁(天端 − 0.15 以上の頂点の最も前)を測る。
    /// 皮の節点 q の見え面からの奥行 d = 前の縁 − q で:
    /// ① front ≤ d ≤ back の地盤 = 天端 + rise − (d − front)·drain(最高は front の線・背へ 1/20)── 帯の上の土 ≥ 0.02【硬】・0.03 は狙い【柔】。
    /// ② back より先は 1:bf で今の地盤(各欄の小段)へ下りる【柔】(⛔ 下げない ── 盛るだけ)。
    /// ③ 見え面の前 0.3 から front まで(表の石の上 0〜0.36・前の地表)はどの駒の物でも盛らない【硬】(出隅の隅の駒の二つの面・段の境の上の駒の見え面)。
    /// ④ keepOut(長屋の背の一間・犬走り 0.3)の点は盛らない【硬】── 入るなら普請方へ戻す(blocked に数える)。
    /// 坂の駒・段なりの所は帯ごとの天端(= その駒の天端の線)で測る。当たる先: 野面の乱積みの段の土留めを持つ全邸(いまは岡部 Stage3b の Dan)。
    /// 生成した皮の検めは <see cref="Designed"/> で設計の帯を「被り」に数えない(表の石の上 0〜front は【硬】のまま数える)。</summary>
    public sealed class NozuraCrestCover
    {
        public float front = 0.36f, back = 1.10f, rise = 0.03f, drain = 0.05f, bf = 3f, skirtMax = 1.5f, frontGuard = 0.3f;
        /// <summary>帯の上の土の下限【硬】── 帯の頂(front の線)を、裏石の後端(帯ごとの控え)で minSoil を割らない高さまで上げる(rise は狙い【柔】)。</summary>
        public float minSoil = 0.02f;
        /// <summary>表の石の上の、帯の縁の手前 edgeW の皮の節点は駒の天端 − 0.003 まで上げる(0.25m の皮の格子の一次の面が帯の縁で石の天端の下へ潜り、裏石が顔を出すのを止める)。</summary>
        public float edgeW = 0.3f;
        public readonly HashSet<GameObject> pieceSet = new HashSet<GameObject>();
        /// <summary>覆う駒でない部材の外形の中と縁(<see cref="CutEdgeSkin"/> の 3f が皮の部材から差す)── 盛らない・帯の検めに数えない。</summary>
        public Func<Vector2, bool> otherPart;
        public int otherSkipped;
        public Func<Vector2, bool> keepOut;
        public int faces, pieces, blocked; public float blockedMax; public Vector3 blockedAt;
        public sealed class FaceBins { public GameObject go; public Vector2 f, t; public float a0; public float[] crest, frontU, riseB; public Vector4 box; }
        public readonly List<FaceBins> list = new List<FaceBins>();
        /// <summary>駒ごとの外形(凸包)と見え面ごとの前の縁(face, 前の縁の u)── ③ を帯の割りに依らず駒の外形で測る(隅の駒の腕の継ぎで帯が欠けても表の石を守る)。</summary>
        public sealed class PieceFaces { public Vector2[] hull; public Vector4 box; public List<Vector3> faces = new List<Vector3>(); }
        public readonly List<PieceFaces> pieceFaces = new List<PieceFaces>();
        const float BIN = 0.1f;

        /// <summary>駒を足す(見え面は <see cref="WallFace"/>・隅の駒は <see cref="KadoFaces"/> の二面)。</summary>
        public void Add(GameObject go, bool kado)
        {
            var vs = Body(go.transform, 999999); if (vs.Count == 0) return;
            var fs = new List<Vector2>();
            if (kado) { Vector2 f1, f2; KadoFaces(go, out f1, out f2); if (f1 != Vector2.zero) fs.Add(f1.normalized); if (f2 != Vector2.zero) fs.Add(f2.normalized); }
            else { var f = WallFace(go); if (f != Vector2.zero) fs.Add(f.normalized); }
            if (fs.Count == 0) return; pieces++; pieceSet.Add(go);
            // 隅の駒は頂点を近い方の見え面の腕へ分ける(⛔ 分けないと片方の腕の帯にもう一方の腕の石が入り、表の石の上を帯と読む)
            var own = new List<Vector3>[fs.Count];
            if (fs.Count == 1) own[0] = vs;
            else
            {
                for (int i = 0; i < fs.Count; i++) own[i] = new List<Vector3>();
                var um = new float[fs.Count]; for (int i = 0; i < fs.Count; i++) { um[i] = float.MinValue; foreach (var v in vs) um[i] = Mathf.Max(um[i], v.x * fs[i].x + v.z * fs[i].y); }
                foreach (var v in vs) { int bi = 0; float be = float.MaxValue; for (int i = 0; i < fs.Count; i++) { float e = um[i] - (v.x * fs[i].x + v.z * fs[i].y); if (e < be) { be = e; bi = i; } } own[bi].Add(v); }
            }
            float bx0 = float.MaxValue, bz0 = float.MaxValue, bx1 = float.MinValue, bz1 = float.MinValue;
            foreach (var v in vs) { bx0 = Mathf.Min(bx0, v.x); bz0 = Mathf.Min(bz0, v.z); bx1 = Mathf.Max(bx1, v.x); bz1 = Mathf.Max(bz1, v.z); }
            float pad = back + skirtMax + 0.5f;
            var pf = new PieceFaces(); { var p2 = new List<Vector2>(); foreach (var v in vs) p2.Add(new Vector2(v.x, v.z)); pf.hull = ConvexHull2(p2).ToArray(); pf.box = new Vector4(bx0, bz0, bx1, bz1); }
            for (int fi = 0; fi < fs.Count; fi++)
            {
                var f = fs[fi]; var ov = own[fi]; if (ov.Count == 0) continue;
                var t = new Vector2(-f.y, f.x); float a0 = float.MaxValue, a1 = float.MinValue;
                foreach (var v in ov) { float a = v.x * t.x + v.z * t.y; a0 = Mathf.Min(a0, a); a1 = Mathf.Max(a1, a); }
                int n = Mathf.Max(1, Mathf.CeilToInt((a1 - a0) / BIN)); var cr = new float[n]; var fu = new float[n]; var bu = new float[n]; var rb = new float[n];
                for (int b = 0; b < n; b++) { cr[b] = float.NaN; fu[b] = float.NaN; bu[b] = float.NaN; }
                foreach (var v in ov) { int b = Mathf.Clamp(Mathf.FloorToInt((v.x * t.x + v.z * t.y - a0) / BIN), 0, n - 1); if (float.IsNaN(cr[b]) || v.y > cr[b]) cr[b] = v.y; }
                foreach (var v in ov)
                {
                    int b = Mathf.Clamp(Mathf.FloorToInt((v.x * t.x + v.z * t.y - a0) / BIN), 0, n - 1); if (v.y < cr[b] - 2f * CREST_BAND) continue;
                    float u = v.x * f.x + v.z * f.y; if (float.IsNaN(bu[b]) || u < bu[b]) bu[b] = u;   // 裏石の後端(天端 − 0.3 までの石)
                    if (v.y < cr[b] - CREST_BAND) continue;
                    if (float.IsNaN(fu[b]) || u > fu[b]) fu[b] = u;
                }
                // 帯の頂の上げ: 裏石の後端(天端の帯の最も奥)で土 ≥ minSoil【硬】── rise(狙い)と比べて高い方
                for (int b = 0; b < n; b++) rb[b] = float.IsNaN(fu[b]) ? rise : Mathf.Max(rise, minSoil + 0.005f + Mathf.Max(0f, Mathf.Min(back, fu[b] - bu[b]) - front) * drain);
                list.Add(new FaceBins { go = go, f = f, t = t, a0 = a0, crest = cr, frontU = fu, riseB = rb, box = new Vector4(bx0 - pad, bz0 - pad, bx1 + pad, bz1 + pad) });
                faces++;
                float fmax = float.MinValue; foreach (var x in fu) if (!float.IsNaN(x)) fmax = Mathf.Max(fmax, x);
                if (fmax > float.MinValue) pf.faces.Add(new Vector3(f.x, f.y, fmax));
            }
            if (pf.hull.Length >= 3 && pf.faces.Count > 0) pieceFaces.Add(pf);
        }

        bool Bin(FaceBins fb, Vector2 q, out float d, out float c) { float r; return Bin(fb, q, out d, out c, out r); }
        bool Bin(FaceBins fb, Vector2 q, out float d, out float c, out float rs)
        {
            d = float.NaN; c = float.NaN; rs = rise;
            if (q.x < fb.box.x || q.x > fb.box.z || q.y < fb.box.y || q.y > fb.box.w) return false;
            int b = Mathf.FloorToInt((Vector2.Dot(q, fb.t) - fb.a0) / BIN); if (b < 0 || b >= fb.crest.Length || float.IsNaN(fb.crest[b]) || float.IsNaN(fb.frontU[b])) return false;
            d = fb.frontU[b] - Vector2.Dot(q, fb.f); c = fb.crest[b]; rs = fb.riseB[b]; return true;
        }
        /// <summary>③ 表の石の上(0〜front)と見え面の前 frontGuard のどれかに入る点(盛らない・被りに数える)。</summary>
        public bool Protected(Vector2 q)
        {
            foreach (var fb in list) { float d, c; if (Bin(fb, q, out d, out c) && d >= -frontGuard && d < front) return true; }
            // 駒の外形(+ frontGuard)の中で、どれかの見え面の前の縁から front 未満(前の縁の面で測る ── 帯の割りの欠けに依らない)
            foreach (var pf in pieceFaces)
            {
                if (q.x < pf.box.x - frontGuard || q.x > pf.box.z + frontGuard || q.y < pf.box.y - frontGuard || q.y > pf.box.w + frontGuard) continue;
                if (!EdoGeom.PIP(pf.hull, q) && EdgeDist(pf.hull, q) >= frontGuard) continue;
                foreach (var fc in pf.faces) { float d = fc.z - (q.x * fc.x + q.y * fc.y); if (d >= -frontGuard && d < front) return true; }
            }
            return false;
        }
        /// <summary>①② 設計の地盤(どの面にも入らなければ NaN)。③ は見ない。</summary>
        public float Target(Vector2 q)
        {
            float best = float.NaN;
            foreach (var fb in list)
            {
                float d, c, rs; if (!Bin(fb, q, out d, out c, out rs) || d < front || d > back + skirtMax) continue;
                float y = d <= back ? c + rs - (d - front) * drain : c + rs - (back - front) * drain - (d - back) / bf;
                if (float.IsNaN(best) || y > best) best = y;
            }
            return best;
        }
        /// <summary>表の石の上で帯の縁の手前 edgeW に入る点(どれかの面)。</summary>
        public bool NearBandEdge(Vector2 q)
        { foreach (var fb in list) { float d, c; if (Bin(fb, q, out d, out c) && d >= front - edgeW && d < front) return true; } return false; }
        /// <summary>帯の中(front〜back)の天端(どの面にも入らなければ NaN)── 検めの基準。</summary>
        public float CrestInBand(Vector2 q)
        {
            float best = float.NaN;
            foreach (var fb in list) { float d, c; if (Bin(fb, q, out d, out c) && d >= front && d <= back && (float.IsNaN(best) || c > best)) best = c; }
            return best;
        }
        /// <summary>皮の検めで「被り」に数えない点 = 設計で土を載せる帯(③ と keepOut の点は数える)。</summary>
        public bool Designed(Vector2 q)
        {
            if (Protected(q) || (keepOut != null && keepOut(q))) return false;
            return !float.IsNaN(Target(q));
        }
        /// <summary>皮の高さ y の点 q を、盛る所なら盛った高さへ(⛔ 下げない)。keepOut に当たって盛らなかった点は blocked に数える。</summary>
        public float Apply(Vector2 q, float y)
        {
            float tg = Target(q); if (float.IsNaN(tg) || tg <= y + 1e-4f) return y;
            if (Protected(q)) return y;
            if (keepOut != null && keepOut(q)) { blocked++; if (tg - y > blockedMax) { blockedMax = tg - y; blockedAt = new Vector3(q.x, y, q.y); } return y; }
            return tg;
        }
        /// <summary>据えた後の検め(描かれた地表 dg で・**その駒の石の上**の点だけ ── 駒の上向きの面(TopIndex)の真上で持ち主がその駒の点):
        /// 帯(front + 0.04 〜 back)の土の厚み(地表 − 石の上面)の最小 ≥ minSoil【硬】/ 表の石の上(d 0.05〜front − 0.03)で 地表 > 石の上面 の点【硬・0】。点は帯ごとに 0.1m おき。</summary>
        public string Measure(Func<float, float, float> dg)
        {
            var ti = new TopIndex(); foreach (var g in pieceSet) if (g != null && g.activeInHierarchy) ti.Add(g);
            int nB = 0, nLow = 0, nF = 0, nOver = 0; float minB = float.MaxValue, maxF = float.MinValue; Vector3 minAt = Vector3.zero, fAt = Vector3.zero; string minBy = "-", fBy = "-";
            foreach (var fb in list)
                for (int b = 0; b < fb.crest.Length; b++)
                {
                    if (float.IsNaN(fb.crest[b]) || float.IsNaN(fb.frontU[b])) continue;
                    float a = fb.a0 + (b + 0.5f) * BIN;
                    for (float d = 0.05f; d <= back + 1e-3f; d += 0.1f)
                    {
                        var q = fb.t * a + fb.f * (fb.frontU[b] - d);
                        bool inBand = d >= front + 0.04f, inFront = d <= front - 0.03f;
                        if (!inBand && !inFront) continue;
                        int w; float top = ti.TopRaw(q.x, q.y, out w); if (float.IsNaN(top) || w < 0 || w >= ti.gos.Count || ti.gos[w] != fb.go) continue;   // その駒の石の上だけ
                        if (inBand && (Protected(q) || (keepOut != null && keepOut(q)) || (otherPart != null && otherPart(q)))) continue;
                        float g = dg(q.x, q.y); if (float.IsNaN(g)) continue; float s = g - top;
                        if (inBand)
                        {
                            nB++; if (s < minSoil - 1e-4f) nLow++;
                            if (s < minB) { minB = s; minAt = new Vector3(q.x, top, q.y); minBy = fb.go.name; }
                        }
                        else
                        {
                            nF++; if (s > 1e-3f) nOver++;
                            if (s > maxF) { maxF = s; fAt = new Vector3(q.x, top, q.y); fBy = fb.go.name; }
                        }
                    }
                }
            return "天端の裏石の帯(" + front.ToString("F2") + "〜" + back.ToString("F2") + "): 駒 " + pieces + "・面 " + faces + "・石の上の点 " + nB + "・土の厚みの最小 " + (nB > 0 ? minB.ToString("+0.000;-0.000") : "-")
                 + " @(" + minAt.x.ToString("F1") + ", " + minAt.z.ToString("F1") + ")〔" + minBy + "〕・" + minSoil.ToString("F2") + " 未満 " + nLow + " 点【硬】"
                 + " / 表の石の上(0〜" + front.ToString("F2") + "): 点 " + nF + "・地表 > 石の上面 " + nOver + " 点【硬】(最大 " + (nF > 0 ? maxF.ToString("+0.000;-0.000") : "-") + " @(" + fAt.x.ToString("F1") + ", " + fAt.z.ToString("F1") + ")〔" + fBy + "〕)"
                 + " / 石段など他の部材の上で盛らなかった皮の節点 " + otherSkipped + " / 長屋の背の一間・犬走りで盛らなかった皮の節点 " + blocked + (blocked > 0 ? "(最大 " + blockedMax.ToString("F2") + " @(" + blockedAt.x.ToString("F1") + ", " + blockedAt.z.ToString("F1") + ")── 普請方へ)" : "");
        }
    }

    /// <summary><see cref="CutEdgeSkin"/> の報告。</summary>
    public struct SkinReport
    {
        /// <summary>描く区域(drawAreas)で開けた升の数。</summary>
        public int cellsDraw;
        public int parts, cells, cellsParts, cellsFace, cellsBand, cellsFill, skipHole, skipTree, skipPlant, holesCut;
        /// <summary>穴を開けた後に穴の升に立つ植栽の点(<c>plantPoints</c>)の数。硬い条件・許容0。</summary>
        public int plantOnHole;
        public int stairFaced;
        public int holdRaised; public float holdRaisedMax;   // 3e 盛った土を最後に効かせた節点の数と最大の上げ
        public int crestCovered; public float crestCoverMax;   // 3f 野面の天端の裏石の帯を覆った皮の節点の数と最大の上げ(SkinDesign.crestCover)
        public int verts, tris, pinned, faced, clamped, under, floored, designed, sloped, filled, fillLostTree;
        public float fillMax; public Vector3 fillAt;
        public float maxLower, maxRaise; public Vector3 lowerAt, raiseAt;
        public int detCells, trees, sealed_, backSealed;
        /// <summary>見え面の前へ出る皮の辺を下げた点・下げた量の最大(<see cref="CutEdgeSkin"/> の「3b」・2026-09-26 EDO-0437 第5巡)。</summary>
        public int faceDropped; public float faceDropMax; public Vector3 faceDropAt;
        /// <summary>外形の縁で閉じた点(<see cref="CloseRimAtHull"/>): 底の下を閉じるため上げた / 天端に被らないよう下げた / 許容を超えて触らない。</summary>
        public int rimRaised, rimLowered, rimRefused; public float rimRaiseMax, rimLowerMax;
        /// <summary>縁の点(皮と地形の境・地形のまま)の下の地形の節点で、天端の帯の駒の天端より高かった物を天端の下へ下げた数と最大(<see cref="PIN_TUCK_MAX"/>)。</summary>
        public int pinTucked, pinTuckRefused; public float pinTuckMax;
        /// <summary>digParts の背を下げた点の数・下げた量の最大(天端を段の線に置いた袖 ── 施主 2026-09-25)。</summary>
        public int dug; public float digMax; public Vector3 digAt;
        public int gapPts, gapN, gapBySkin, gapBig, coverPts, coverN;
        public float gapMax, coverMax; public Vector3 gapAt, coverAt; public string gapBy, coverBy;
        public string mesh;
        /// <summary>床を覆う部材(floorParts)と測った床の天端。</summary>
        public string floors;
        /// <summary>門の上向きの面の下へ納めた皮の点。</summary>
        public int gateUnder;
        /// <summary>据わりの守り(<c>seated</c> を渡したとき・2026-10-05 EDO-0533): 守った駒・部材に載るので外した駒・地面に触れていた点 /
        /// 皮を上げた頂点(うち床を周りへ法で下ろした頂点)・最大 / 部材の天端に譲った頂点・譲らせた部材 / 床に届かない触れる点(駒の側)・最大・駒の名。
        /// ⛔ 2026-10-05 第10巡で「被る升を皮から外して元の地形のまま残す」は廃した(元の地形が溝・受けに被った)。</summary>
        public bool seatGuard; public int seatPieces, seatOnPart, seatContacts, seatRaised, seatMound, seatYield, seatUnmet;
        public float seatRaiseMax, seatUnmetMax; public Vector3 seatRaiseAt, seatUnmetAt; public string seatRaiseBy, seatYieldBy, seatUnmetBy;
        /// <summary>被りのうち、外形の内の点が**皮でなく地形の升**(穴を開けなかった升 ── 地形の木・植栽の点・守りで外した升)に在る物。</summary>
        public int coverTerrain;
        /// <summary>coverTerrain のうち、地形の木・植栽の点が立つので穴を開けなかった升の物(駒の側 ── 木・植栽が溝・受けの升に立つ)と、その相手の部材。</summary>
        public int coverPlantCell; public string coverPlantBy;
        /// <summary>溝の脇の守り(<c>keepGradeBeside</c> を渡したとき・2026-10-05 EDO-0533 第14巡): 溝の駒の外形の外で、溝・蓋の天端で下げる cap を造成の面で止めた点 /
        /// 外形の縁で閉じる(3c)の下げを造成の面で止めた点。<see cref="coverSunk"/> = 被りのうち、溝・蓋の天端が造成の面より低い所の物(溝の側 ──
        /// 深さの版が足りず天端が地盤の下へ沈んだ溝・地盤の下に据わった蓋。皮は造成の面より下げない)。</summary>
        public int keepHeld, keepRimHeld, coverSunk; public string coverSunkBy;
        /// <summary>溝の脇の法(<c>keepBatter</c> &gt; 0 を渡したとき・2026-10-06 EDO-0533 第15巡): 溝の天端が造成の面より沈んだ所で、外形の外の皮を
        /// 天端の外の辺から切土の法(1:keepBatter)で造成の面まで上げた点(= 造成の面より下げた点)と、その下げの最大・場所。</summary>
        public int keepBatterCut; public float keepBatterMax; public Vector3 keepBatterAt;
        /// <summary>面の縁の内に沿う溝の外の帯を溝の天端 − KEEP_RIM_TUCK へ下げた点の数(第18巡)。</summary>
        public int rimStrip;
        public override string ToString()
        {
            return (string.IsNullOrEmpty(floors) ? "" : "床を覆う部材:" + floors + "(面の下へ納めた皮 " + gateUnder + " 点) / ") + "穴 " + holesCut + " 升(部材 " + cellsParts + "・面の縁 " + cellsFace + "(うち縁の線の帯 " + cellsBand + ")・裏込め " + cellsFill +
                   "・既に穴で触らず " + skipHole + "・地形の木が立つので開けず " + skipTree + "・植栽の点が立つので開けず " + skipPlant + ")" +
                   (plantOnHole > 0 ? " ⛔ 穴の上の植栽の点 " + plantOnHole : "") +
                   " / 皮 頂点 " + verts + "・三角 " + tris + "(縁の点 " + pinned + " は地形のまま)" +
                   " / 面の高さへ " + faced + " 点(うち石段の外形の中と前 " + stairFaced + ")" + (holdRaised > 0 ? "・盛った土を最後に効かせた " + holdRaised + " 点(最大 +" + holdRaisedMax.ToString("F2") + ")" : "") + (crestCovered > 0 ? "・野面の天端の裏石の帯を覆った " + crestCovered + " 点(最大 +" + crestCoverMax.ToString("F2") + ")" : "") + "・面の外は設計の地盤へ " + designed + " 点(うち縁から法で受けた " + sloped + ")" +
                   " / 部材の天端の下へ " + clamped + " 点(うち真下 " + under + "・隣の底で止めた " + floored + ")" +
                   " / 裏込め(部材の底まで盛る)" + filled + " 点・最大 " + fillMax.ToString("F2") + "m @(" + fillAt.x.ToString("F1") + ", " + fillAt.z.ToString("F1") + ")" +
                   "・地形の木の升は穴を開けず被せた " + fillLostTree + " 升" +
                   " / 面の高さの皮で部材の底まで塞いだ " + sealed_ + " 点・背の土を駒の底まで上げた " + backSealed + " 点" +
                   " / 外形の縁で底の下を閉じた " + rimRaised + " 点(最大 " + rimRaiseMax.ToString("F3") + ")・天端の下へ納めた " + rimLowered + " 点(最大 " + rimLowerMax.ToString("F3") + ")" + (rimRefused > 0 ? "・⚠ 許容を超え触らず " + rimRefused : "") +
                   (pinTucked + pinTuckRefused > 0 ? " / 縁の点の下の地形の節点を天端の下へ " + pinTucked + "(最大 " + pinTuckMax.ToString("F3") + ")" + (pinTuckRefused > 0 ? "・⚠ 埋没で触らず " + pinTuckRefused : "") : "") +
                   " / 見え面の前へ出る皮の辺を下げた " + faceDropped + " 点" + (faceDropped > 0 ? "・最大 " + faceDropMax.ToString("F2") + "m @(" + faceDropAt.x.ToString("F1") + ", " + faceDropAt.z.ToString("F1") + ")" : "") +
                   (dug > 0 ? " / 背を下げた(天端 − 0.05 から法)" + dug + " 点・最大 " + digMax.ToString("F2") + "m @(" + digAt.x.ToString("F1") + ", " + digAt.z.ToString("F1") + ")" : "") +
                   " / 元の地形から 下げ 最大 " + maxLower.ToString("F2") + "m @(" + lowerAt.x.ToString("F1") + ", " + lowerAt.z.ToString("F1") + ")・上げ 最大 " + maxRaise.ToString("F2") + "m @(" + raiseAt.x.ToString("F1") + ", " + raiseAt.z.ToString("F1") + ")" +
                   " / 芝を消した 1m 升 " + detCells + " / 皮が 0.05m を超えて動いた所の地形の木 " + trees + " 本" +
                   "\n    硬い(許容0): 皮と部材の隙 ── 皮が作った " + gapBySkin + " / 元の地形でも同じ(部材の浮き・皮の外の欠陥) " + (gapN - gapBySkin) + " / " + gapPts + " 点(うち 0.05m を超える " + gapBig + ")" + (gapN > 0 ? "(最大 " + gapMax.ToString("F3") + "m @(" + gapAt.x.ToString("F2") + ", " + gapAt.z.ToString("F2") + ")〔" + gapBy + "〕)" : "") +
                   " / 皮が部材の天端に被る " + coverN + " / " + coverPts + " 点" + (coverN > 0 ? "(最大 " + coverMax.ToString("F3") + "m @(" + coverAt.x.ToString("F2") + ", " + coverAt.z.ToString("F2") + ")〔" + coverBy + "〕)" : "") +
                   (coverTerrain > 0 ? "(うち皮でなく穴を開けなかった地形の升が被る " + coverTerrain +
                                       (coverPlantCell > 0 ? "・そのうち地形の木・植栽の点が立つ升 " + coverPlantCell + "〔" + coverPlantBy + "〕── 駒の側" : "") + ")" : "") +
                   (coverSunk > 0 ? "(うち溝・蓋の天端が造成の面より低い所 " + coverSunk + "〔" + coverSunkBy + "〕── 溝の側・皮は造成の面より下げない)" : "") +
                   (keepHeld + keepRimHeld > 0 ? " / 溝の脇の皮を造成の面で止めた " + keepHeld + " 点・外形の縁で閉じる下げを止めた " + keepRimHeld + " 点" : "") +
                   (rimStrip > 0 ? " / 面の縁の内に沿う溝の外の帯を溝の天端 − 0.02 へ下げた " + rimStrip + " 点" : "") +
                   (keepBatterCut > 0 ? " / 溝の天端が沈んだ脇を天端の外の辺から法で上げた " + keepBatterCut + " 点(造成の面から最大 " + keepBatterMax.ToString("F2") + "m 下げ @(" + keepBatterAt.x.ToString("F1") + ", " + keepBatterAt.z.ToString("F1") + ")── 溝の側: 天端の沈み)" : "") +
                   " / メッシュ " + mesh +
                   (seatGuard ? "\n    硬い(許容0): 据わりの守り ── 駒 " + seatPieces + "(部材に載るので外した " + seatOnPart + ")・地面に触れていた点 " + seatContacts +
                                " / 皮を上げた頂点 " + seatRaised + "(うち周りへ法で下ろした " + seatMound + ")" + (seatRaised > 0 ? "・最大 " + seatRaiseMax.ToString("F3") + "m @(" + seatRaiseAt.x.ToString("F1") + ", " + seatRaiseAt.z.ToString("F1") + ")〔" + seatRaiseBy + "〕" : "") +
                                (seatYield > 0 ? " / 部材の天端に譲った頂点 " + seatYield + "〔" + seatYieldBy + "〕" : "") +
                                (seatUnmet > 0 ? " / ⛔ 床に届かない触れる点(駒の側)" + seatUnmet + "・最大 " + seatUnmetMax.ToString("F3") + "m @(" + seatUnmetAt.x.ToString("F1") + ", " + seatUnmetAt.z.ToString("F1") + ")〔" + seatUnmetBy + "〕" : "") : "");
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
    /// <summary>土留めの背の外形の縁で、外の地盤(0.6m 先)が駒の底より低いときに底まで盛ってよい高さ[m](2026-09-26・EDO-0437 第3巡)。</summary>
    public const float BACK_FILL = 0.35f;
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
    /// <summary>下を向いた面(駒の底)と読む法線の y の下限(−)。法・見え面(y ≥ −0.3)は底でない(<see cref="TopIndex.FootBottom"/>)。</summary>
    const float DOWN_NY = 0.3f;
    /// <summary>天端の帯の深さ・周りを見る半径[m](<see cref="TopIndex.banded"/>)。0.15 = 野面の天端の石の凹凸(±0.08)は入り、
    /// 天端の奥の控え(天端 − 0.3)は外れる ── 控えは上の面の土に入るのが正しい納め(0.3 では控えを天端と読み、背の帯に 0.25m の溝が残った)。</summary>
    public const float CREST_BAND = 0.15f, CREST_R = 0.6f;
    /// <summary>溝の脇の法(<see cref="CutEdgeSkin"/> の keepBatter): 法の足を溝の駒の天端の外の辺より下げる量[m](縁石の外の面へ皮を納める ──
    /// 天端に被らない)と、法を引く外形からの範囲の上限[m](沈み 1.5m まで・法 1:1 で)。</summary>
    const float KEEP_RIM_TUCK = 0.02f, KEEP_BATTER_R = 1.5f;
    /// <summary>段石の背の縁(StairBackRim): 天端の下へ納める深さ・外の地盤が天端に揃うと見なす差・隣の駒が同じ段石と見なす天端の差。</summary>
    const float STAIR_RIM_TUCK = 0.02f, STAIR_RIM_LEVEL = 0.12f, STAIR_RIM_COVER = 0.10f;
    /// <summary>面の縁のどちらの側に溝が在るかを測る離れ[m](<see cref="CutEdgeSkin"/> の OutsideY ── 縁から外へこの距離の点のこの距離以内に掘る部材が在れば「法の側に溝」)。</summary>
    const float DITCH_SIDE_R = 0.35f;
    /// <summary>凸な外形の縁上で点 <paramref name="p"/> に最も近い点と、その距離。</summary>
    static Vector2 HullNearest(Vector2[] poly, Vector2 p, out float dist)
    {
        Vector2 best = p; dist = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length], ab = b - a; float l2 = ab.sqrMagnitude;
            float t = l2 > 1e-12f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2) : 0f;
            var c = a + ab * t; float d = (p - c).magnitude;
            if (d < dist) { dist = d; best = c; }
        }
        return best;
    }
    sealed class TopIndex
    {
        readonly List<Vector3[]> tris = new List<Vector3[]>();
        readonly List<int> owner = new List<int>();
        readonly List<bool> up = new List<bool>();
        readonly List<bool> down = new List<bool>();   // 下を向いた面(駒の底)── FootBottom が法の面と見分ける
        readonly List<Vector3> nrm = new List<Vector3>();   // 表の向きの単位法線(鏡の駒は巻きを直した)── UnderFace が見え面と背・小口を見分ける
        readonly Dictionary<long, List<int>> hash = new Dictionary<long, List<int>>();
        const float B = 1f;
        public readonly List<Vector2[]> hulls = new List<Vector2[]>();
        public readonly List<string> names = new List<string>();
        /// <summary>外形ごとの部材(見え面の向きを測る ── <see cref="WallFace"/>)。</summary>
        public readonly List<GameObject> gos = new List<GameObject>();
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
            AddTris(g, g.name, ts, hull, crestBand);
        }
        /// <summary>駒の三角形の一部(<paramref name="ts"/>)だけを部材として入れる(門の床 ── <see cref="FloorTris"/>・EDO-0428)。</summary>
        public void AddTris(GameObject g, string name, List<Vector3[]> ts, Vector2[] hull, bool crestBand)
        {
            if (ts == null || ts.Count == 0 || hull == null || hull.Length < 3) return;
            int k = hulls.Count; hulls.Add(hull); names.Add(name); banded.Add(crestBand); gos.Add(g);
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
                down.Add(mag > 1e-9f && sgn * nv.y / mag < -DOWN_NY);
                nrm.Add(mag > 1e-9f ? sgn * nv / mag : Vector3.zero);
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
        /// <summary>(x,z) の駒の、周り <see cref="CREST_R"/> の同じ駒の最も高い上向きの面(= 近くの天端)。駒が無ければ NaN。
        /// 当たる先: 皮の cap が法の足の石で掘るかを決める(CutEdgeSkin の Floor)。</summary>
        public float CrestAround(float x, float z)
        {
            int who; float y = Scan(x, z, true, out who); if (who < 0 || float.IsNaN(y)) return float.NaN;
            float mx = y;
            for (int a = 0; a < 8; a++)
            {
                float ang = a * Mathf.PI / 4f; float t2 = ScanOwner(x + Mathf.Cos(ang) * CREST_R, z + Mathf.Sin(ang) * CREST_R, who);
                if (!float.IsNaN(t2) && t2 > mx) mx = t2;
            }
            return mx;
        }
        /// <summary>(x,z) の真上に駒 <paramref name="k"/> の**見え面**(上を向かない面で、表の法線の水平が <paramref name="fv"/> の側 ── 内積 &gt; 0.3)が在るか。
        /// = 点が法の帯(見え面の足の線と天端の前の縁の間)の下に在る。⛔ 背・小口・外形の縁の帯(天端も見え面も上に無い所)は false。
        /// 当たる先: <see cref="CutEdgeSkin"/> の 3b の候補(城の石垣の滑らかな見え面の下の点 ── 2026-10-05 EDO-0502 第23巡)。</summary>
        public bool UnderFace(float x, float z, int k, Vector2 fv)
        {
            float y;
            List<int> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return false;
            foreach (var id in l)
            {
                if (owner[id] != k || up[id]) continue; var n = nrm[id];
                if (n.x * fv.x + n.z * fv.y > 0.3f && TriYAt(tris[id], x, z, out y)) return true;
            }
            return false;
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
        /// <summary>(x,z) の、外形 <paramref name="k"/> の駒だけの最も低い面。無ければ NaN。当たる先: 据わりの守りの掘る部材の底の標本(<see cref="SeatGuard"/>)。</summary>
        public float BottomOwner(float x, float z, int k)
        {
            float best = float.NaN, y;
            List<int> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return best;
            foreach (var id in l)
                if (owner[id] == k && TriYAt(tris[id], x, z, out y) && (float.IsNaN(best) || y < best)) best = y;
            return best;
        }
        /// <summary>**皮を寄せる底**(x,z)── 最も低い面が下を向いた面(駒の底)ならその高さ。最も低い面が**法・見え面**(下を向かない ──
        /// 殻の駒・隅の駒の傾いた面の途中)なら、それは底でなく面の途中 ── その駒の**見え面の足の線**(<see cref="WallBottom"/> を
        /// 近く 0.2m と広く <paramref name="rWide"/> で取った低い方)を底とする。駒が無ければ NaN。
        /// ⭐ 2026-10-04 EDO-0502 第10巡: 塞ぎ(sealFace)と床が隅の駒(TW_Kado_Shumen_kado2_3_0)の法の途中 16.71〜17.36 を底と読み、
        /// 鉛直に近い小面の WallBottom(0.2) も石の目地の段 16.85〜16.93 を返して、面 16.50 の皮を見え面の足元 0.25m で +0.17〜0.28
        /// 盛り上げた(近景の三角の歯)。当たる先: CutEdgeSkin を通る全邸(岡部 Stage3b・山王 Stage9)の塞ぎ・床。</summary>
        public float FootBottom(float x, float z, float rWide, out int who) { bool dn; return FootBottom(x, z, rWide, out who, out dn); }
        /// <summary><paramref name="isDown"/> = 最も低い面が下を向いた面(駒の本当の底)だったか。</summary>
        public float FootBottom(float x, float z, float rWide, out int who, out bool isDown)
        {
            who = -1; isDown = false; float best = float.NaN, y; int bi = -1;
            List<int> l; if (!hash.TryGetValue(K(Mathf.FloorToInt(x / B), Mathf.FloorToInt(z / B)), out l)) return best;
            foreach (var id in l)
                if (TriYAt(tris[id], x, z, out y) && (float.IsNaN(best) || y < best)) { best = y; bi = id; who = owner[id]; }
            if (bi < 0) return best;
            if (down[bi]) { isDown = true; return best; }
            float w0 = WallBottom(x, z, 0.2f, who), w1 = WallBottom(x, z, rWide, who);
            float foot = float.IsNaN(w0) ? w1 : (float.IsNaN(w1) ? w0 : Mathf.Min(w0, w1));
            return float.IsNaN(foot) ? best : Mathf.Min(best, foot);
        }
        /// <summary>(x,z) から平面で <paramref name="r"/> 以内を通る**鉛直な面**(石垣の見え面・小口)の、その位置での最も低い所。
        /// ⭐ 鉛直な面は平面に面積が無いので <see cref="Bottom"/> の縦の線に掛からない ── 殻の駒(底の面が無い)の見え面の脇では
        /// 底が天端に化けて「駒が浮く」と誤って数えた(2026-09-25 EDO-0430: 回廊の基壇・御供所の郭の石垣で 3,243 点)。無ければ NaN。
        /// ⭐ **法(のり)の面も数える**(天端・踏面 = 上を向いた面 <see cref="UP_NY"/> 以外の全て・2026-09-25 v18)。法の足(根入れ)は
        /// 法の面の下の縁で、法の途中の点の <see cref="Bottom"/> は法の面そのもの(殻の駒に底の面は無い)── 隣の点の底を最大で採る皮の
        /// 塞ぎ(sealFace)と床(隣の底より下げない)が法の途中の高さを底と読み、見え面の足元 0.3m に +0.1〜0.5m の土の縁を立てた
        /// (回廊の基壇の東・北の犬走りの床 25.05 の上。駒の底は 25.00 で根入れ済み)。</summary>
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
                        var nv = Vector3.Cross(t[1] - t[0], t[2] - t[0]); float mag = nv.magnitude; if (mag < 1e-9f || Mathf.Abs(nv.y) / mag > UP_NY) continue;
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
        /// <summary>**光線を部材の三角形へ打つ**(<paramref name="o"/> から <paramref name="d"/> へ <paramref name="maxDist"/> 以内の最初の当たりの距離・無ければ NaN)。
        /// 升の索引で引くので短い光線は速い(2026-09-26・EDO-0437 第5巡 ── 皮の辺が見え面の前へ出るかを測る)。<paramref name="only"/> ≥ 0 ならその駒だけ。</summary>
        public float Ray(Vector3 o, Vector3 d, float maxDist, int only = -1) { return Ray(o, d, maxDist, only, null); }
        /// <summary><paramref name="okOwner"/> が false を返す駒の三角形は当たりに数えない(3b: 入隅の向かいの壁を「石の後ろ」と読まない・第25巡)。</summary>
        public float Ray(Vector3 o, Vector3 d, float maxDist, int only, Func<int, bool> okOwner)
        {
            d.Normalize(); Vector3 e = o + d * maxDist; float best = float.NaN;
            int i0 = Mathf.FloorToInt(Mathf.Min(o.x, e.x) / B), i1 = Mathf.FloorToInt(Mathf.Max(o.x, e.x) / B);
            int j0 = Mathf.FloorToInt(Mathf.Min(o.z, e.z) / B), j1 = Mathf.FloorToInt(Mathf.Max(o.z, e.z) / B);
            HashSet<int> seen = (i0 == i1 && j0 == j1) ? null : new HashSet<int>();
            for (int i = i0; i <= i1; i++)
                for (int j = j0; j <= j1; j++)
                {
                    List<int> l; if (!hash.TryGetValue(K(i, j), out l)) continue;
                    foreach (var id in l)
                    {
                        if ((only >= 0 && owner[id] != only) || (seen != null && !seen.Add(id))) continue;
                        if (okOwner != null && !okOwner(owner[id])) continue;
                        var t = tris[id];
                        Vector3 e1 = t[1] - t[0], e2 = t[2] - t[0];
                        Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-9f) continue;
                        float inv = 1f / det; Vector3 tv = o - t[0]; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                        Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                        float dist = Vector3.Dot(e2, qv) * inv;
                        if (dist >= 0f && dist <= maxDist && (float.IsNaN(best) || dist < best)) best = dist;
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

    /// <summary>**門の床(基壇)の三角形**(EDO-0428)。駒の外形の中点を含む面(<paramref name="faces"/>)の高さ ±<see cref="FLOOR_REACH"/> にある
    /// 上向きの面の最高 = 床の天端 <paramref name="floorTop"/>。床 = 全頂点がその天端 + 0.005 以下の三角形(柱・壁・屋根は上へ抜けるので入らない)。
    /// 外形 <paramref name="hull"/> は床の三角形の凸包。面が無い・上向きの面が無ければ null。
    /// 当たる先: 面の高さに天端を据えた門・棟の基壇すべて(山王 楼門の基壇 28.30 = 境内の面 ── 皮と地形が同じ高さで斑に出た)。</summary>
    public static List<Vector3[]> FloorTris(GameObject g, IList<SkinFace> faces, out float floorTop, out Vector2[] hull)
    {
        floorTop = float.NaN; hull = null;
        if (faces == null || faces.Count == 0) return null;
        var ts = TrisOfMat(g.transform, null); if (ts.Count == 0) return null;
        var mf0 = g.GetComponentInChildren<MeshFilter>();
        float sgn = (mf0 != null ? mf0.transform.localToWorldMatrix.determinant : g.transform.localToWorldMatrix.determinant) < 0f ? -1f : 1f;
        var all = HullOfMat(g.transform, null); if (all == null || all.Length < 3) return null;
        Vector2 c = Vector2.zero; foreach (var q in all) c += q; c /= all.Length;
        float fy = float.NaN; float fa = float.MaxValue;
        foreach (var f in faces) if (EdoGeom.PIP(f.poly, c)) { float a = Area(f.poly); if (a < fa) { fa = a; fy = f.y; } }
        if (float.IsNaN(fy)) return null;
        foreach (var t in ts)
        {
            var nv = Vector3.Cross(t[1] - t[0], t[2] - t[0]); float mag = nv.magnitude;
            if (mag < 1e-9f || sgn * nv.y / mag <= UP_NY) continue;
            float yc = (t[0].y + t[1].y + t[2].y) / 3f; if (Mathf.Abs(yc - fy) > FLOOR_REACH) continue;
            float ym = Mathf.Max(t[0].y, Mathf.Max(t[1].y, t[2].y));
            if (float.IsNaN(floorTop) || ym > floorTop) floorTop = ym;
        }
        if (float.IsNaN(floorTop)) return null;
        var L = new List<Vector3[]>(); var p2 = new List<Vector2>();
        foreach (var t in ts)
        {
            if (Mathf.Max(t[0].y, Mathf.Max(t[1].y, t[2].y)) > floorTop + 0.005f) continue;
            L.Add(t); foreach (var v in t) p2.Add(new Vector2(v.x, v.z));
        }
        if (L.Count == 0) return null;
        // 外形は床より下へ届く屋根でない三角形すべて(敷居・縁・礎石・柱の足)── 床の帯の外へ出る上向きの面にも穴を開ける(EDO-0428 二巡目)
        foreach (var t in OpenUpTris(g, false))
            if (Mathf.Min(t[0].y, Mathf.Min(t[1].y, t[2].y)) <= floorTop + 0.005f) foreach (var v in t) p2.Add(new Vector2(v.x, v.z));
        var hi = EdoGeom.HullXZ(p2.ToArray()); hull = new Vector2[hi.Length];
        for (int i = 0; i < hi.Length; i++) hull[i] = p2[hi[i]];
        return L;
    }
    /// <summary>駒の**屋根・軒でない**三角形(<paramref name="upOnly"/> なら上向きの面だけ)。屋根は材の名とメッシュの名で篩う
    /// (<see cref="IsRoofName"/> と "roof")── 一体で焼いた門は屋根が材(サブメッシュ)で分かれる。</summary>
    public static List<Vector3[]> OpenUpTris(GameObject g, bool upOnly = true)
    {
        var L = new List<Vector3[]>();
        foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (IsRoofName(PartName(g.transform, mf))) continue;
            var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            float sgn = m.determinant < 0f ? -1f : 1f;
            var mats = rr.sharedMaterials;
            for (int sm = 0; sm < mf.sharedMesh.subMeshCount; sm++)
            {
                string mn = sm < mats.Length && mats[sm] != null ? mats[sm].name : "";
                if (IsRoofName(mn) || mn.ToLower().Contains("roof")) continue;
                var tri = mf.sharedMesh.GetTriangles(sm);
                for (int i = 0; i + 2 < tri.Length; i += 3)
                {
                    Vector3 a = m.MultiplyPoint3x4(vs[tri[i]]), b = m.MultiplyPoint3x4(vs[tri[i + 1]]), c = m.MultiplyPoint3x4(vs[tri[i + 2]]);
                    if (upOnly) { var nv = Vector3.Cross(b - a, c - a); float mag = nv.magnitude; if (mag < 1e-9f || sgn * nv.y / mag <= UP_NY) continue; }
                    L.Add(new[] { a, b, c });
                }
            }
        }
        return L;
    }
    /// <summary>皮を門の上向きの面の下へ納める量[m](硬い: 面 − 皮 ≥ 0.02 ── 普請検査 EDO-0428 二巡目)。</summary>
    public const float GATE_UNDER = 0.03f;
    /// <summary>皮に埋まる門の上向きの面を拾う深さ[m](= 皮の天端の下へ納める量 under と同じ)。⛔ 深くしない ── 0.5 にしたら坂下の門の
    /// 基壇の中の段(地中)まで拾い、皮を 0.3m 掘って隣の段石の底が 0.15 覗いた(EDO-0428 二巡目)。</summary>
    public const float GATE_BURY = 0.15f;
    /// <summary><see cref="FloorTris"/> が床の天端を探す、面の高さからの幅[m]。</summary>
    public const float FLOOR_REACH = 0.5f;

    /// <summary>**皮の高さの追跡**(診断・2026-10-07 EDO-0502 第42巡): 点を入れると CutEdgeSkin が、その点に最も近い格子の点の高さを段ごとに
    /// <see cref="SkinTraceLog"/> へ刷る(どの段が皮を下げ・上げたかを名指す)。null(既定)なら何もしない。当たる先: 皮の窪み・盛りの原因を測るとき(全邸)。</summary>
    public static List<Vector2> SkinTrace;
    public static System.Text.StringBuilder SkinTraceLog = new System.Text.StringBuilder();
    static bool TrHit(float x, float z) { foreach (var q in SkinTrace) if (Mathf.Abs(q.x - x) <= 0.125f && Mathf.Abs(q.y - z) <= 0.125f) return true; return false; }
    static void TrLog(float x, float z, string tag, float h) { SkinTraceLog.AppendLine("  (" + x.ToString("F2") + ", " + z.ToString("F2") + ") " + tag + ": " + h.ToString("F3")); }
    static void TrDump(string tag, Dictionary<long, float> H, float ox, float oz, float step)
    {
        foreach (var q in SkinTrace)
        {
            int gi = Mathf.RoundToInt((q.x - ox) / step), gj = Mathf.RoundToInt((q.y - oz) / step); float v;
            long k = ((long)gi << 32) ^ (uint)gj;
            SkinTraceLog.AppendLine("  (" + (ox + gi * step).ToString("F2") + ", " + (oz + gj * step).ToString("F2") + ") " + tag + ": " + (H.TryGetValue(k, out v) ? v.ToString("F3") : "—"));
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
    /// <para>⭐ <paramref name="hollowParts"/>(掘る部材 ── 溝・桝・受け。2026-10-05 EDO-0533 土井): 中に窪み(溝の底)を持つ部材。
    /// (1) 隣の点の天端で皮を下げる cap は、この駒の外の点では窪みの底でなく**縁の天端**(<see cref="TopIndex.CrestAround"/>)で取る、
    /// (2) 石段の前・脇の下げ(底から法で受ける・石段の前を面に揃える)の相手にしない ── 溝の底は石段の足ではない。
    /// 渡さなければ従来どおり(岡部・山王・観理院・十坊は渡していない)。</para>
    /// <para>⭐ <paramref name="seated"/>(既に据わった駒 ── 硬い・許容0。2026-10-05 EDO-0533): 渡すと最後に**据わりの守り**を掛ける ──
    /// parts と seated の各駒の、地面に触れていた頂点(0.25m 升ごとの最下点で、高さ ≤ 元の地形 + <see cref="SEAT_TOL"/>・他の部材の上に
    /// 載っていない物)の下で、皮を min(元の地形, その頂点) より下げない。⇒ 皮は地形が描いていた高さより下げて駒を浮かせない。
    /// 上げた所は周りへ盛土の法で下ろす(鉛直の板を立てない)。上げる頂点は、その頂点に触れる三角形のどこでも**部材の天端を越えない**所で止め
    /// (天端に譲る・自分の駒も含む)、譲って届かない触れる点は駒の側として名乗る(<see cref="SkinReport.seatUnmet"/>)。⛔ 升を外して元の地形へ戻さない。
    /// 渡さなければ守りは掛からない。</para>
    /// <para>⭐ <paramref name="keepGradeBeside"/>(溝の脇の守り ── 硬い・許容0。2026-10-05 EDO-0533 第14巡): 掘る部材のうち**窪みを持つ溝の駒**(蓋石は入れない)。
    /// 渡すと、この駒たちの外形の**外**の点では、掘る部材(溝・蓋)の天端で皮を下げる cap(真下・隣の点とも)と 3c の縁で閉じる下げを、その点の
    /// **造成の面**(cap を掛ける前の高さ = 面・設計の地盤)で止める ⇒ 溝の外の地表は溝を掘る前の造成の面より下がらない。下げてよいのは溝の駒の外形の内だけ。
    /// 溝・蓋の天端が造成の面より低い所では皮がその縁に被る ── 被りのうち該当する物は <see cref="SkinReport.coverSunk"/>(溝の側)として名乗る。
    /// ⛔ 2026-10-05 第13巡まで、溝 D2 の天端が地盤の 0.5〜0.64m 下にある所(深さの版の上限 0.30 を超える区間)で、溝の外形の外 0.5m の皮を天端 26.06 まで
    /// 下げ(地盤 26.6)、幅 0.84 の蓋石の両端・蔵の石段の脇が 0.16〜0.5m の窪みの上に出ていた。渡さなければ従来どおり。</para>
    /// <para>⭐ <paramref name="keepBatter"/> &gt; 0(溝の脇の法 ── 硬い・許容0。2026-10-06 EDO-0533 第15巡): 上の守りの床を、点ごとに
    /// **min(造成の面, 最寄りの溝の駒の天端の外の辺の高さ − <see cref="KEEP_RIM_TUCK"/> + 外形の縁からの水平距離 ÷ keepBatter)** にする
    /// (位置について連続な床 ── 二値で止めない)。溝の外の皮はこの床まで下げ、床より下げない。天端が造成の面にある溝では床 = 造成の面(従来と同じ)、
    /// 天端が沈んだ溝(深さの版が勾配の落ちに足りない区間 ── S9 の「深さが上限を超える区間」)では、天端の外の辺から切土の法で造成の面まで上がる。
    /// ⛔ 2026-10-05 第14巡まで、守りは頂点ごとに「造成の面で止める/止めない」の二値で、外形の外の頂点は造成の面(26.30)・内の頂点は天端 − under(25.75)
    /// のまま、溝の斜めの線が 0.25m 格子を階段に横切る所で隣どうしが 0.55m 違い、三角形が溝の縁石に被る歯形(三角の山の列)が立った(溝 D2 seg1 の脇・
    /// 被り 1,481 点が「溝の側」)。0 なら第14巡の二値の守りのまま。当たる先: keepGradeBeside を渡す邸(いまは土井 Stage4b)の全ての溝の脇。</para>
    /// <summary>縁の点の下の地形の節点を天端の下へ下げる上限(天端からの高さ)。超える節点は駒の埋没 ── 触らない(<see cref="SkinReport.pinTuckRefused"/>)。</summary>
    const float PIN_TUCK_MAX = 0.40f;

    public static SkinReport CutEdgeSkin(string name, Transform parent, IList<GameObject> parts, IList<SkinFace> faces,
                                         float faceTol, float step = 0.25f, float margin = 0.5f, float eps = 0f, float under = 0.15f,
                                         SkinDesign design = null, float drawTol = 0.10f, float backfill = 0f, bool sealFace = false,
                                         IList<GameObject> digParts = null, float digUnder = 0.05f, float digBatter = 1f,
                                         IList<GameObject> crestBandParts = null, IList<Vector2> plantPoints = null,
                                         IList<GameObject> floorParts = null, IList<Vector2[]> faceKeepOut = null,
                                         IList<GameObject> hollowParts = null, IList<GameObject> seated = null,
                                         IList<GameObject> keepGradeBeside = null, float keepBatter = 0f, bool stairApronFrontOnly = false,
                                         IList<Vector2[]> drawAreas = null)
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
        // ⭐ 床を覆う部材(門の基壇 ── floorParts・EDO-0428): 床の帯の三角形だけを部材に入れる。皮は床の外形の中で床の天端 − under へ
        //   納まり、床の外形に掛かる升は穴になる(地形も皮も床と同じ高さで斑に描かれない)。⛔ 屋根・軒の外形で穴を開けない。
        r.floors = "";
        var gateUp = new List<Vector3[]>(); var gateHash = new Dictionary<long, List<int>>();
        if (floorParts != null)
            foreach (var g in floorParts)
            {
                if (g == null || !g.activeInHierarchy) continue;
                float ft; Vector2[] flh; var ftr = FloorTris(g, faces, out ft, out flh);
                if (ftr == null) { r.floors += " " + g.name + "(床の面が無い・入れず)"; continue; }
                idx.AddTris(g, g.name + "(床)", ftr, flh, false);
                r.floors += " " + g.name + "(床 " + ft.ToString("F2") + ")";
                foreach (var gt in OpenUpTris(g))
                {
                    int id = gateUp.Count; gateUp.Add(gt);
                    float x0 = Mathf.Min(gt[0].x, Mathf.Min(gt[1].x, gt[2].x)), x1 = Mathf.Max(gt[0].x, Mathf.Max(gt[1].x, gt[2].x));
                    float z0 = Mathf.Min(gt[0].z, Mathf.Min(gt[1].z, gt[2].z)), z1 = Mathf.Max(gt[0].z, Mathf.Max(gt[1].z, gt[2].z));
                    for (int i = Mathf.FloorToInt(x0); i <= Mathf.FloorToInt(x1); i++)
                        for (int j = Mathf.FloorToInt(z0); j <= Mathf.FloorToInt(z1); j++)
                        { long kk = ((long)i << 32) ^ (uint)j; List<int> l; if (!gateHash.TryGetValue(kk, out l)) { l = new List<int>(); gateHash[kk] = l; } l.Add(id); }
                }
            }
        r.parts = idx.hulls.Count;
        // 掘る部材(hollowParts)の外形の番号
        var hollowSet = hollowParts != null ? new HashSet<GameObject>(hollowParts) : null;
        Func<int, bool> IsHollow = w => hollowSet != null && w >= 0 && w < idx.gos.Count && hollowSet.Contains(idx.gos[w]);
        // 溝の脇の守り(keepGradeBeside): 溝の駒の外形の番号と、点がそのどれかの外形の内か
        var keepSet = keepGradeBeside != null ? new HashSet<GameObject>(keepGradeBeside) : null;
        var keepHulls = new List<int>();
        if (keepSet != null) for (int k = 0; k < idx.gos.Count; k++) if (keepSet.Contains(idx.gos[k])) keepHulls.Add(k);
        Func<Vector2, bool> InKeepHull = q =>
        {
            foreach (var k in keepHulls)
            {
                var hb = idx.bounds[k];
                if (q.x < hb.x || q.x > hb.z || q.y < hb.y || q.y > hb.w) continue;
                if (EdoGeom.PIP(idx.hulls[k], q)) return true;
            }
            return false;
        };
        // 点 → その点の造成の面(溝の外形の外で、掘る部材の cap が当たった点だけ)── 3c の下げもここで止める
        var keepFloor = keepSet != null ? new Dictionary<long, float>() : null;
        // 溝の脇の法(keepBatter > 0): 外形の外の点 q の床 = 溝の駒ごとに「天端の外の辺の高さ − KEEP_RIM_TUCK + max(0, 外形の縁からの距離 − step) ÷ keepBatter」の最小
        //   (q を含む外形は呼び手が除く)。天端の外の辺の高さ = 外形の縁の最寄りの点から内へ 0.03・0.08m の、その駒の上向きの面の最高。無ければ NaN。
        //   min を取る関数はどれも位置について連続 ⇒ 床は連続(頂点ごとの二値で止めない ── 歯形を立てない)。
        Func<Vector2, float> BatterFloor = q =>
        {
            if (keepSet == null || keepBatter <= 1e-3f) return float.NaN;
            float best = float.NaN;
            foreach (var k in keepHulls)
            {
                var hb = idx.bounds[k];
                if (q.x < hb.x - KEEP_BATTER_R || q.x > hb.z + KEEP_BATTER_R || q.y < hb.y - KEEP_BATTER_R || q.y > hb.w + KEEP_BATTER_R) continue;
                float d; var c = HullNearest(idx.hulls[k], q, out d);
                if (d > KEEP_BATTER_R || d < 1e-5f) continue;
                var inw = (c - q) / d; float rim = float.NaN;
                foreach (float s in new[] { 0.03f, 0.08f })
                {
                    int who; var sp = c + inw * s; float tp = idx.TopRaw(sp.x, sp.y, out who);
                    if (who == k && !float.IsNaN(tp) && (float.IsNaN(rim) || tp > rim)) rim = tp;
                }
                if (float.IsNaN(rim)) continue;
                //   ⭐ 外形の縁から一格子(step)までは平ら(天端 − KEEP_RIM_TUCK)── 法をそこから始める(2026-10-06 EDO-0533 第21巡)。
                //   ⛔ 第20巡まで縁から法を始め、縁の外 0.02m より先の格子点が天端より高くなり得て、その点と外形の内の点の三角形が縁石を斜めに横切り、
                //   溝 D2 seg1 の外の縁石の天端に皮が波打って被った(溝はまっすぐ並んでいるのに、ぎざぎざに見えた)。
                float f = rim - KEEP_RIM_TUCK + Mathf.Max(0f, d - step) / keepBatter;
                if (float.IsNaN(best) || f < best) best = f;
            }
            return best;
        };

        // 面の縁の内に沿う溝の天端(溝の外の帯の皮を溝の天端より上に残さない ── 2026-10-06 EDO-0533 第18巡)。
        //   点 q が溝の外形の外で、q から rr 以内の溝の駒の最寄りの点 c が向き o(面の縁へ出る向き)と逆の側(= 面の内の側)に在れば、
        //   その駒の天端の外の辺の高さ(BatterFloor と同じ測り)を返す。無ければ NaN。
        Func<Vector2, Vector2, float, float> RimInward = (q, o, rr) =>
        {
            if (keepSet == null || keepBatter <= 1e-3f) return float.NaN;
            float best = float.NaN, bestD = float.MaxValue;
            foreach (var k in keepHulls)
            {
                var hb = idx.bounds[k];
                if (q.x < hb.x - rr || q.x > hb.z + rr || q.y < hb.y - rr || q.y > hb.w + rr) continue;
                if (EdoGeom.PIP(idx.hulls[k], q)) return float.NaN;
                float d; var c = HullNearest(idx.hulls[k], q, out d);
                if (d > rr || d < 1e-5f || d >= bestD) continue;
                if (Vector2.Dot(c - q, o) > 0f) continue;   // 溝が縁の側(外)に在る ── 帯でない
                var inw = (c - q) / d; float rim = float.NaN;
                foreach (float s2 in new[] { 0.03f, 0.08f })
                {
                    int who; var sp = c + inw * s2; float tp = idx.TopRaw(sp.x, sp.y, out who);
                    if (who == k && !float.IsNaN(tp) && (float.IsNaN(rim) || tp > rim)) rim = tp;
                }
                if (float.IsNaN(rim)) continue;
                best = rim; bestD = d;
            }
            return best;
        };

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
        // ⭐ 面の縁の升から外す区域(faceKeepOut・2026-10-04 EDO-0533 土井): 庭の土工(池・築山)のように面の上で**意図して**
        //   面の高さから外した地盤。外さないと「面から tol を超えて外れた升」と読んで皮を面の高さで張り、池を埋め築山を削る。
        //   当たる先: 面の上に庭・池を掘る全邸(土井の泉水・松江松平・岡部の庭)。部材の升・裏込めの升は外さない。
        Func<Vector2, bool> InKeepOut = q => { if (faceKeepOut == null) return false; foreach (var ko in faceKeepOut) if (ko != null && EdoGeom.PIP(ko, q)) return true; return false; };
        var faceCells = new HashSet<long>();
        if (faces != null)
            foreach (var f in faces)
            {
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var p in f.poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
                for (int i = CI(mnx); i <= CI(mxx); i++)
                    for (int j = CJ(mnz); j <= CJ(mxz); j++)
                    {
                        float x0 = org.x + i * cs, z0 = org.z + j * cs; bool bad = false; float ftol = f.tol > 0f ? f.tol : faceTol;
                        for (float x = x0 + 0.125f; x < x0 + cs && !bad; x += 0.25f)
                            for (float z = z0 + 0.125f; z < z0 + cs && !bad; z += 0.25f)
                                if (EdoGeom.PIP(f.poly, new Vector2(x, z)) && !InKeepOut(new Vector2(x, z)) && Mathf.Abs(probe.At(x, z) - f.y) > ftol) bad = true;
                        if (!bad) continue;
                        for (int di = -1; di <= 1; di++) for (int dj = -1; dj <= 1; dj++)
                        {
                            if (InKeepOut(new Vector2(org.x + (i + di + 0.5f) * cs, org.z + (j + dj + 0.5f) * cs))) continue;
                            faceCells.Add(CK(i + di, j + dj));
                        }
                    }
            }

        // ---- 2b 点と部材・面の関係、面の外の設計の地盤(2026-09-25)
        // 点と部材の外形の関係: 2 = 外形の中 / 1 = 外形から NEAR 以内 / 0 = 離れている
        const float NEAR = 0.5f;
        const float STAIR_APRON = 1.5f;   // 石段の前を面に揃える幅(面の縁と石段の足の間 ── 岡部 K_Dan1 で 0.75〜1.25m)
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
        // ⭐ 溝は囲いでない(keepBatter &gt; 0 のとき・2026-10-06 EDO-0533 第16巡): 囲い(法を当てない縁)を測るとき掘る部材(溝・桝・受け・蓋)の外形を数えない
        //   ── 溝は土を留めない(地表に掘り込む駒)。⛔ 第15巡まで、下の面(26.75)の縁が溝 D2 seg1 の谷の側の外形から WALLED 以内に在り「囲いのある縁」と
        //   読んで法を当てず、溝と面の間の細い帯が 2m 格子の設計の地盤(≥ 27.36)のまま残り、keepBatter の床(溝の天端から外へ上る法)で上ってから
        //   面へ 0.5〜0.6m 切り立った ── 溝の斜めの線が 0.25m 格子を横切る列ごとに三角の山が立つ鋸(蔵の基壇の前・溝 D2 seg1_2 の南の脇)。
        //   法で受ければ帯は面の縁で面の高さ・溝の側で min(天端の外の辺 − tuck, 面 + 離れ ÷ 法)── 位置について連続(崖を立てない)。
        //   切土の側(設計の地盤 &gt; 面)だけ ── 下げるだけで面の高さより下げない ⇒ 被りは増えない・隙は面の点(既に面の高さ)より悪くならない。
        //   当たる先: keepBatter を渡す邸(いまは土井 Stage4b)の、面の縁に沿う溝・蓋の脇のすべて。渡さない邸は従来どおり(溝も囲いに数える)。
        bool ditchOpen = keepBatter > 1e-3f && hollowSet != null;
        // 石段の脇か(stairApronFrontOnly): 当たった石段の駒の位置 (hx,hz) の足 fb と天端の中ほどより点の高さ h が高い ⇒ 点は段の**前**(足元の面の側)でなく
        //   段の側面に沿う斜面(上の段の側面は斜面に埋まる)。天端が無ければ脇と読まない。
        Func<float, float, float, float, bool> StairSide = (hx, hz, fb, h) =>
        {
            int wT; float tS = idx.TopRaw(hx, hz, out wT);
            return !float.IsNaN(tS) && h > 0.5f * (fb + tS);
        };
        // 点 q から r 以内に掘る部材(溝・桝・受け・蓋)の外形が在るか(外形の中も含む)
        Func<Vector2, float, bool> HollowNear = (q, rr) =>
        {
            for (int h = 0; h < idx.hulls.Count; h++)
            {
                if (!IsHollow(h)) continue;
                var hb = idx.bounds[h];
                if (q.x < hb.x - rr || q.x > hb.z + rr || q.y < hb.y - rr || q.y > hb.w + rr) continue;
                if (EdoGeom.PIP(idx.hulls[h], q) || EdgeDist(idx.hulls[h], q) < rr) return true;
            }
            return false;
        };
        // 点 q の真上に、掘る部材でない駒(躯体・塀・石段)の**足**(下面が面の高さ y + 0.3 より低い ── 軒の裏・屋根は足でない)が在るか
        Func<Vector2, float, bool> UnderSolidFoot = (q, y) =>
        {
            int w; float b = idx.Bottom(q.x, q.y, out w);
            return !float.IsNaN(b) && w >= 0 && !IsHollow(w) && b <= y + 0.3f;
        };
        Func<Vector2, bool> WalledAt = q =>
        {
            if (!ditchOpen) return NearAt(q, WALLED) != 0;
            for (int h = 0; h < idx.hulls.Count; h++)
            {
                if (IsHollow(h)) continue;
                var hb = idx.bounds[h];
                if (q.x < hb.x - WALLED || q.x > hb.z + WALLED || q.y < hb.y - WALLED || q.y > hb.w + WALLED) continue;
                if (EdoGeom.PIP(idx.hulls[h], q) || EdgeDist(idx.hulls[h], q) < WALLED) return true;
            }
            return false;
        };
        // SkinDesign.hold: 立てた節点を周りに持つ点は、その升の設計の地盤の双一次(面の中の節点も混ぜる ── 面の高さで描かれる)。無ければ NaN
        Func<Vector2, float> HoldY = (q) =>
        {
            if (design == null || design.hold == null) return float.NaN;
            float fx = (q.x - design.x0) / design.step, fz = (q.y - design.z0) / design.step;
            int i0 = Mathf.FloorToInt(fx), j0 = Mathf.FloorToInt(fz); float tx = fx - i0, tz = fz - j0; bool any = false; double sw = 0, sv = 0;
            for (int di = 0; di <= 1; di++)
                for (int dj = 0; dj <= 1; dj++)
                {
                    int ni = i0 + di, nj = j0 + dj; if (ni < 0 || nj < 0 || ni >= design.nx || nj >= design.nz) continue;
                    int k = nj * design.nx + ni; if (!design.ok[k]) continue;
                    if (design.hold[k]) any = true;
                    float w = (di == 1 ? tx : 1f - tx) * (dj == 1 ? tz : 1f - tz); sw += w; sv += w * design.h[k];
                }
            return any && sw > 1e-6 ? (float)(sv / sw) : float.NaN;
        };
        // 面の外の点の描く高さ: 設計の地盤(無ければ地形)を、最寄りの**囲いの無い**面の縁から法で受ける。
        //   囲い(部材)が縁に立つ所は法を当てない(土留めの前に盛土を出さない)。sloped = 法で受けたか。
        Func<Vector2, bool[], float> OutsideY = (q, sloped) =>
        {
            if (design != null && design.own != null && !EdoGeom.PIP(design.own, q)) return probe.At(q.x, q.y);   // 区画の外は今の地形
            float s = DesignOut(q.x, q.y); if (float.IsNaN(s)) s = CleanAt(q.x, q.y);
            if (design == null) return s;
            { float hy = HoldY(q); if (!float.IsNaN(hy)) return float.IsNaN(s) ? hy : Mathf.Max(s, hy); }   // 法で受けない節点の周り(SkinDesign.hold)
            float bd = BATTER_REACH; SkinFace bf = default(SkinFace); Vector2 bq = Vector2.zero; bool found = false;
            foreach (var f in fl) { Vector2 cq; float d = ClosestOnPoly(f.poly, q, out cq); if (d < bd) { bd = d; bf = f; bq = cq; found = true; } }
            if (!found || WalledAt(bq)) return s;
            //   溝だけが縁に立つ所は切土の側(設計の地盤が面より高い ⇒ 下げるだけ・面の高さより下げない)にだけ法を当てる ──
            //   盛土の側で溝の脇を上げると溝の天端に被り得るので従来どおり(皮の被りを増やさない)
            //   ⭐ ただし溝が面の**内の側**だけに在る縁(溝の外の辺と面の縁の間の細い帯の先 ── 法は溝から離れる向きに下りる)は法で受ける
            //   (2026-10-06 EDO-0533 第17巡): 溝に被り得るのは法の側(縁の外)に溝が在るときだけ。⛔ 第16巡まで、蔵の座(27.50)の縁が溝 D2 seg2 の
            //   外の辺の 0.1〜0.2m 先に在り、縁の外の点が設計の地盤(27.16)のまま残って縁で 0.34m の崖が立ち、溝に沿う斜めの縁の線が 0.25m 格子を
            //   横切る列ごとに三角の山が並ぶ鋸になった。当たる先: keepBatter を渡す邸(いまは土井 Stage4b)の、面の縁の内に沿う溝・蓋のすべて。
            if (ditchOpen && s <= bf.y && NearAt(bq, WALLED) != 0 && (bd < 1e-4f || HollowNear(bq + (q - bq) / bd * DITCH_SIDE_R, DITCH_SIDE_R))) return s;
            //   ⭐ 縁の内に沿う溝の外の帯は溝の天端 − KEEP_RIM_TUCK まで下げてある(面の点の側・第18巡)⇒ 盛土の側の法も、縁の高さでなくその高さから下ろす
            //   (縁で 27.50 から下ろすと、溝の外の帯の先に畝が残る ── 第17巡 蔵の石段の脇 D2 seg2 の外 0.06〜0.21m に 27.50 の山 9 点)
            float top = bf.y;
            if (ditchOpen && s <= bf.y && bd > 1e-4f)
            {
                float rim = RimInward(bq, (q - bq) / bd, DITCH_SIDE_R);
                if (!float.IsNaN(rim)) top = Mathf.Min(top, rim - KEEP_RIM_TUCK);
            }
            float t = s > bf.y ? Mathf.Min(s, bf.y + bd / Mathf.Max(design.batterCut, 1e-3f))
                               : Mathf.Max(s, top - bd / Mathf.Max(design.batterFill, 1e-3f));
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
                        if (InKeepOut(new Vector2(x0 + 0.5f * cs, z0 + 0.5f * cs))) continue;   // 庭の土工の区域は面の縁の帯にも数えない
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
        // ---- 2c' 描く区域(drawAreas・2026-10-09 EDO-0502 第61巡): 区域の中で、2m 格子の地形が設計の地盤(OutsideY)と drawTol を超えて違う升を穴にする ──
        //   面の縁でも部材の脇でもない所の、格子より細かい設計(池の岸の断面・背の小段)を皮で描く。faceKeepOut と独立(庭の区域でも開ける)。
        //   ⛔ 2026-10-08 第60巡まで: 岡部 書院の泉水の岸を 2m 格子が描き、汀の外 2〜3m まで地表が水面 20.7 より低く(縁の 1520/3203 点)、水面が板のように浮いた。
        //   当たる先: drawAreas を渡す邸(いまは岡部 Stage3b ── 庭の汀の帯・背の小段)。渡さなければ従来どおり。
        int drawN = 0;
        if (design != null && drawAreas != null)
            foreach (var da in drawAreas)
            {
                if (da == null || da.Length < 3) continue;
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var p in da) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
                for (int i = CI(mnx); i <= CI(mxx); i++)
                    for (int j = CJ(mnz); j <= CJ(mxz); j++)
                    {
                        long ck = CK(i, j); if (faceCells.Contains(ck)) continue;
                        float x0 = org.x + i * cs, z0 = org.z + j * cs; bool bad = false;
                        for (float x = x0; x <= x0 + cs + 1e-4f && !bad; x += 0.5f)
                            for (float z = z0; z <= z0 + cs + 1e-4f && !bad; z += 0.5f)
                            {
                                var q = new Vector2(x, z); if (!EdoGeom.PIP(da, q)) continue;
                                float want = FaceY(q); if (float.IsNaN(want)) want = OutsideY(q, null);
                                if (!float.IsNaN(want) && Mathf.Abs(want - probe.At(x, z)) > drawTol) bad = true;
                            }
                        if (bad) { faceCells.Add(ck); drawN++; }
                    }
            }
        r.cellsDraw = drawN;

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
        // ⛔ 植栽の点(算出物の planting.points)の升も開けない ── 焼き直しで後から植える木は、この時点の treeInstances に
        //   まだ居ない。穴の升に植えると SetTreeInstances が黙って落とす(2026-09-25 実測: 前庭の帯の低木 4 本・EDO-0430)。
        //   硬い条件(許容0)。その升は地形のまま残し、皮はその縁で地形へ継ぐ(縁の点は地形に留まる)。
        //   ⭐ 点は**幹の足**で、地形の木はピボット(= 点 − 幹の足のずれ・最大 0.32m 前後・TreePivotForTrunk)に立つ ──
        //   点のまわり PLANT_PIVOT_R に掛かる升を全部残す。⛔ 2026-10-01 まで点の升だけ残し、ピボットが隣の穴の升に落ちた
        //   木が 1 本消えた(山王の帯3 中木・EDO-0495)。当たる先: 縁の皮を張る全邸(山王・観理院・十坊の皮)。
        if (plantPoints != null)
            foreach (var pp in plantPoints)
                for (int dx = -1; dx <= 1; dx++)
                    for (int dz = -1; dz <= 1; dz++)
                    {
                        var c = CK(CI(pp.x + dx * PLANT_PIVOT_R), CJ(pp.y + dz * PLANT_PIVOT_R));
                        if (treeCells.Contains(c)) continue;
                        treeCells.Add(c);
                        if (cells.Contains(c)) r.skipPlant++;
                    }
        foreach (var c in treeCells) if (cells.Remove(c)) { r.skipTree++; if (fillCells.Contains(c)) { overlay.Add(c); r.fillLostTree++; } }
        r.skipTree -= r.skipPlant;
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
        // ⭐ 縁の点の下の地形の節点を天端の下へ(2026-10-07 EDO-0502 第46巡): 皮の縁の点(穴の升と地形の升の境)は地形のまま描く(PIN)ので、
        //   その節点が天端の帯の駒の外形の中で天端より高いと、皮も隣の地形の升も天端の上へ被る ── CloseRimAtHull は PIN を動かさないので直せない。
        //   岡部 辺24 の野面 TW_Nishi_Kado_辺24_0_0_071f〜073f と基壇 IG_S_Hei_21_191 の天端 11.77 に、節点 (-651.88, 964.07) 11.97・(966.07) 12.10 が
        //   0.02〜0.20 被った(7 点)。節点は駒の外形の中(石の下)なので天端 − 0.003 へ下げても見えない。硬い: 被り 0。
        //   ⛔ 天端より PIN_TUCK_MAX を超えて高い節点は駒が土に埋まっている(埋没は別の欠陥・掘ると外の地表が凹む ── TuckUnderCrest と同じ守り)。
        //   当たる先: CutEdgeSkin を通る全邸(岡部 3b・山王 9・土井 4b)の、穴の升の境が天端の帯の駒の外形を横切る所。
        if (bandSet != null && bandSet.Count > 0)
        {
            int hR = td.heightmapResolution; float hc = td.size.x / (hR - 1);
            if (Mathf.Abs(hc - cs) < 1e-4f)
            {
                bool wrote = false;
                for (int ni = ci0; ni <= ci1 + 1; ni++)
                    for (int nj = cj0; nj <= cj1 + 1; nj++)
                    {
                        if (ni < 0 || nj < 0 || ni >= hR || nj >= hR) continue;
                        bool anyIn = false, anyOut = false;
                        for (int ii = ni - 1; ii <= ni; ii++) for (int jj = nj - 1; jj <= nj; jj++) { if (In(ii, jj)) anyIn = true; else anyOut = true; }
                        if (!anyIn || !anyOut) continue;   // 縁の点だけ
                        float x = org.x + ni * cs, z = org.z + nj * cs; int who;
                        float top = idx.Top(x, z, out who);
                        if (float.IsNaN(top) || who < 0 || !idx.banded[who]) continue;
                        var hh = td.GetHeights(ni, nj, 1, 1); float cur = hh[0, 0] * td.size.y + org.y;
                        float lim = top - 0.003f;
                        if (cur <= lim + 1e-4f) continue;
                        if (cur > top + PIN_TUCK_MAX) { r.pinTuckRefused++; continue; }
                        hh[0, 0] = Mathf.Clamp01((lim - org.y) / td.size.y); td.SetHeightsDelayLOD(ni, nj, hh); wrote = true;
                        r.pinTucked++; r.pinTuckMax = Mathf.Max(r.pinTuckMax, cur - lim);
                    }
                if (wrote) { td.SyncHeightmap(); probe = Probe(); }
            }
        }
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
        var topCache = new Dictionary<long, float>(); var faceTop = new HashSet<long>(); var crestTop = new HashSet<long>();
        // 部材の天端(篩わない)。⭐ 天端の帯で篩う駒(crestBandParts)の**法の面**の点は faceTop に記す ──
        //   そこでは天端の下へ納める cap を**足元の面の高さより下げない**(法の足は面の下へ入るのが正しい納め・掘らない)。
        var topWho = new Dictionary<long, int>();
        Func<int, int, float> TopL = (gi, gj) =>
        {
            long k = CK(gi, gj); float v;
            if (topCache.TryGetValue(k, out v)) return v;
            int who; float x = org.x + gi * step, z = org.z + gj * step;
            v = idx.TopRaw(x, z, out who); topWho[k] = who;
            if (!float.IsNaN(v) && who >= 0 && idx.banded[who]) { int w2; if (float.IsNaN(idx.Top(x, z, out w2))) faceTop.Add(k); else crestTop.Add(k); }
            topCache[k] = v; return v;
        };
        // ⭐ 掘る部材(hollowParts)の縁の天端(2026-10-05 EDO-0533): 隣の点が溝の窪みの上なら、その駒の外の点を窪みの底まで下げない ──
        //   溝の外の地盤は**縁の天端**の下へ納めれば被らない。⛔ 2026-10-04 まで窪みの底(TopRaw)を cap に採り、土井の溝 858 駒の脇 0.5m の
        //   皮を溝の底まで下げて、脇に据わっていた長屋・棟・植栽を 0.3〜0.8m 浮かせた。
        var rimCache = new Dictionary<long, float>();
        Func<int, int, float> RimL = (gi, gj) =>
        {
            long k = CK(gi, gj); float v; if (rimCache.TryGetValue(k, out v)) return v;
            v = idx.CrestAround(org.x + gi * step, org.z + gj * step); rimCache[k] = v; return v;
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
        // ⭐ **段石の背の縁**(2026-10-07 EDO-0502 第42巡 施主指摘 B): 天端の帯で篩わない駒(石段)の外形の中で、真上にその駒の天端が在り、
        //   隣(1 格子)の外の点の設計の地盤が天端 − STAIR_RIM_LEVEL 以上(= 上の面が段石の背に揃う)なら、その点は天端 − STAIR_RIM_TUCK で描く。
        //   ⛔ 2026-10-07 まで「面の外の外形の中は駒の本当の底まで下げる(見えない)」で積みの底 17.84 まで下げ、外の点 18.73 との三角形が
        //   段石の背の縁から 0.13〜0.5m の帯で 0.85 窪んで背の面を見せた(岡部 K_Dan1 の上がり口・皮の追跡で名指した)。外形の縁の点は隣の外の点と
        //   三角形で結ばれる ⇒ 見えないのは外形の奥の点だけ。隣の点がすべて「同じ高さの駒の下」か「天端に揃う外の地盤」の時だけ当てる(下の段の踏面・脇の低い地盤へ皮を被せない)。
        //   当たる先: CutEdgeSkin に石段を渡す全邸(岡部 Stage3b・山王 Stage9・土井 Stage4b)の、上の面へ上がる石段の最上段の背。
        var stairRim = new HashSet<long>(); string rimWhy = null;
        Func<int, int, float, bool> StairBackRim = (gi, gj, top) =>
        {
            rimWhy = null;
            bool outerLevel = false;
            for (int di = -1; di <= 1; di++)
                for (int dj = -1; dj <= 1; dj++)
                {
                    if (di == 0 && dj == 0) continue;
                    int np = NearPart(gi + di, gj + dj);
                    if (np == 2)
                    {
                        float tn = TopL(gi + di, gj + dj);
                        if (!float.IsNaN(tn) && tn >= top - STAIR_RIM_COVER) continue;   // 同じ段石(か同じ高さの駒)の下 ── 見えない
                        if (!float.IsNaN(tn)) { rimWhy = "隣 (" + di + "," + dj + ") 駒の天端 " + tn.ToString("F2"); return false; }   // 低い駒の上(下の段の踏面)── 被せない
                        //   駒の上向きの面の無い外形の中(脇の城の石垣の法の下 ── 返しの見え面の前の路盤)は外の点と同じに地盤で見る
                    }
                    var q = new Vector2(org.x + (gi + di) * step, org.z + (gj + dj) * step);
                    float fy = FaceY(q); float oy = float.IsNaN(fy) ? (design != null ? OutsideY(q, null) : float.NaN) : fy;
                    if (float.IsNaN(oy) || oy < top - STAIR_RIM_LEVEL) { rimWhy = "隣 (" + di + "," + dj + ") 外の地盤 " + oy.ToString("F2") + " np " + np; return false; }   // 外の地盤が天端より低い(段石の前・脇)── 従前どおり
                    outerLevel = true;
                }
            return outerLevel;
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
                        bool trc = SkinTrace != null && TrHit(x, z); if (trc) TrLog(x, z, "元の地形", hgt);
                        // 面の高さ: 部材の外形の中では当てない(部材の中の地盤は部材の面が決める)。
                        //   面の縁の外へ 1.5 格子まで伸ばすのは、部材から NEAR より離れた所だけ(土留めの背へ棚を出さない)。
                        bool faced = false; int near = NearPart(gi, gj);
                        if (near < 2)
                        {
                            foreach (var f in fl) if (EdoGeom.PIP(f.poly, p)) { hgt = f.y; faced = true; break; }
                            // ⭐ 面の中でも立てた節点(SkinDesign.hold ── 部材の小口に被せる土)の周りは面より上へ描く(⛔ 下げない・2026-10-07 EDO-0502 第49巡)
                            if (faced) { float hy = HoldY(p); if (!float.IsNaN(hy) && hy > hgt) { hgt = hy; if (trc) TrLog(x, z, "立てた節点", hgt); } }
                            // ⭐ 面の縁の内に沿う溝の、縁の側の帯(溝の外の辺〜面の縁)は、溝の天端 − KEEP_RIM_TUCK より上に残さない(柔らかい ── 見た目の畝を消す・
                            //   2026-10-06 EDO-0533 第18巡)。⛔ 第17巡まで、蔵の座(27.50)の縁が溝 D2 seg2 の外の辺の 0.06〜0.21m 先に在り、帯が 27.50 のまま
                            //   溝の天端(27.40〜27.45)より 0.05〜0.1 高く残って、その先の法との間に畝(周りより 0.19〜0.31 高い山 9 点)が立った。
                            //   当たる先: keepBatter を渡す邸(いまは土井 Stage4b)の、面の縁の内に沿う溝のすべて。
                            //   ⭐ 据わった駒(掘る部材でない ── 土蔵・棟の躯体)の外形の中の点は下げない(2026-10-07 EDO-0533 第31巡): 溝を躯体の足から 0.05 離すと、
                            //   帯が蔵の足の下へ入り、足の外形の縁の点を溝の天端 − tuck(27.39)へ下げて蔵の隅が 0.100 浮いた(Kura1)。駒の下の点は下の cap が駒の面の下へ納める。
                            //   当たる先: keepBatter を渡す邸(土井 Stage4b)の、面の縁の内に沿う溝の脇に据わった駒すべて
                            if (faced && ditchOpen && design != null && !UnderSolidFoot(p, hgt))
                                foreach (var f in fl)
                                {
                                    if (!EdoGeom.PIP(f.poly, p)) continue;
                                    Vector2 cq; float de = ClosestOnPoly(f.poly, p, out cq);
                                    if (de < 1e-4f || de > DITCH_SIDE_R) break;
                                    float rim = RimInward(p, (cq - p) / de, DITCH_SIDE_R);
                                    if (!float.IsNaN(rim) && hgt > rim - KEEP_RIM_TUCK) { hgt = rim - KEEP_RIM_TUCK; r.rimStrip++; }
                                    break;
                                }
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
                        if (trc) TrLog(x, z, "面・設計(near " + near + " faced " + faced + ")", hgt);
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
                            bool botOk = !float.IsNaN(bl) && !float.IsNaN(tl) && tl - bl > 0.05f && bl <= dz + faceTol - 0.02f;
                            if (botOk) dz = Mathf.Max(dz, bl);
                            hgt = Mathf.Min(hgt, dz);
                            // ⭐ 駒の底までは上げる(2026-09-26・EDO-0437 第3巡)── 2m 格子の地形は土留めの背の外形の中で面の段を跨いで落ち
                            //   (前庭の SE の背: 設計の地盤 16.65・駒の底 16.50・地形 15.8)、外形の外の設計の地盤との間の三角形が背の底の下を
                            //   0.54m 覗かせた。底は駒のどの面より低いので天端は埋まらない(「上げない」の由来 ── 袖の天端を埋めた ── は設計の地盤へ上げた話)。
                            if (botOk && hgt < Mathf.Min(bl, dz)) hgt = Mathf.Min(bl, dz);
                        }
                        if (trc) TrLog(x, z, "外形の中の設計", hgt);
                        // ⭐ 天端の帯で篩う駒の**法の面の下**(外形の中・天端の帯の外)は、その点の面の高さで描く ── 法の足・控えは面の土の下へ入る
                        //   (2026-09-25: 野面の背と腰石垣の間の帯 SukibeiSoto_Chu が、腰石垣の深い法の上で元の地形 28.85 のまま 0.4m の溝になった)。
                        //   上向きの面が無い点(城の石垣の急な法の真下)も同じ ── 篩う駒の外形の中に限る。
                        if (near == 2 && !faced && (faceTop.Contains(CK(gi, gj)) || (float.IsNaN(TopL(gi, gj)) && InBandedHull(p))))
                        { float fy = FaceY(p); if (!float.IsNaN(fy)) { hgt = fy; faced = true; } }
                        if (trc) TrLog(x, z, "法の面の下", hgt);
                        // ⭐ 背の土を駒の底まで(2026-09-26・EDO-0437 第3巡)── 駒の外形の中と縁の近く(NEAR 以内)で、面の外の点は、
                        //   駒の底(その点の最も低い面 / 近くの駒の底の最大)が**周り 0.6m の外形の外の地盤以下**なら、その底まで上げる
                        //   (底 ≦ 外の地盤 = 背の土はそこまで在る。底は駒のどの面より低いので天端は埋まらない)。
                        //   設計面の節点が駒の下で落ちて造成前の地盤(低い)で引かれると、土留めの背の外形の縁に溝ができ底の下が覗く
                        //   (前庭の SE の背: 外の地盤 16.3〜16.8・駒の底 16.50・縁の溝 15.7 ⇒ 0.54m)。
                        //   当たる先: 土留め・石垣・袖の背(外形の縁)が盛土・造成の境に掛かる所すべて。
                        if (near >= 1 && !faced && design != null && float.IsNaN(FaceY(p)))
                        {
                            float bl2 = float.NaN;
                            // 外形の中でも駒の面が上下に無い点(凹んだ駒の外接の外形の中 ── SE の背の 831.07)は外形の外と同じに近くの底で
                            bool inBody = near == 2 && !(float.IsNaN(TopL(gi, gj)) && float.IsNaN(BotL(gi, gj)));
                            if (inBody)
                            {
                                float b2 = BotL(gi, gj), t2 = TopL(gi, gj);
                                // 底の面が無い点(背の控えの鉛直な面の脇)は鉛直な面の下の縁を底に(sealFace と同じ・0.2m 以内)
                                if (float.IsNaN(b2) && !float.IsNaN(t2)) { int who0; idx.TopRaw(x, z, out who0); float wb0 = idx.WallBottom(x, z, 0.2f, who0); if (!float.IsNaN(wb0)) b2 = wb0; }
                                if (!float.IsNaN(b2) && !float.IsNaN(t2) && t2 - b2 > 0.05f) bl2 = b2;
                            }
                            else
                                for (int di = -2; di <= 2; di++)
                                    for (int dj = -2; dj <= 2; dj++)
                                    {
                                        int who; float qx = org.x + (gi + di * 0.5f) * step, qz = org.z + (gj + dj * 0.5f) * step;
                                        float bq = idx.Bottom(qx, qz, out who); if (float.IsNaN(bq)) continue;
                                        float tq = idx.TopRaw(qx, qz, out who); if (float.IsNaN(tq) || tq - bq <= 0.05f) continue;
                                        if (float.IsNaN(bl2) || bq > bl2) bl2 = bq;
                                    }
                            if (!float.IsNaN(bl2) && hgt < bl2 - 1e-3f)
                            {
                                float og = float.NaN;
                                for (int a8 = 0; a8 < 8; a8++)
                                {
                                    float an = a8 * Mathf.PI / 4f; var q = p + new Vector2(Mathf.Cos(an), Mathf.Sin(an)) * 0.6f;
                                    if (NearAt(q, 0.01f) == 2) continue;
                                    float oy = FaceY(q); if (float.IsNaN(oy)) oy = OutsideY(q, null);   // 外の地盤 = 面の中は面の高さ・外は設計の地盤
                                    if (!float.IsNaN(oy) && (float.IsNaN(og) || oy > og)) og = oy;
                                }
                                //   外の地盤が底より低くても BACK_FILL 以内なら底まで盛る(裏込めの土 ── 縁から 0.6m で外の地盤へ下りる)。
                                //   それより低い外の地盤は駒が浮いている(駒の側の話 ── 隙に数える)。
                                if (!float.IsNaN(og) && og >= bl2 - BACK_FILL) { hgt = Mathf.Max(hgt, bl2); r.backSealed++; }
                            }
                        }
                        if (trc) TrLog(x, z, "背の土", hgt);
                        // ⭐ 天端の帯で篩わない駒(石段・その積み)の外形の中で面の中の点は、駒の本当の底(下を向いた面)が面 + 許容の内なら
                        //   面の高さで描く(2026-10-04 EDO-0502 第10巡)── 地形のまま(2m 格子の天端の側の高さ)を踏面の下へ納めるだけだと、
                        //   外の点(面 16.50)との三角形が段の前の 0.25m に土の斜面を立て(石段 K_Dan1 の最下段の前 16.53〜16.85)、積みの底が浮いて見えた。
                        //   ⛔ 上げない(下げるだけ)。⛔ 土留め(帯で篩う駒)の外形の中は触らない(背の土は上の面・法の下は Floor が決める)。
                        //   当たる先: CutEdgeSkin に石段・段を渡す全邸(岡部 Stage3b の Kaidan・山王 Stage9 の段)。
                        if (near == 2 && !faced)
                        {
                            float fyS = FaceY(p); float tS = TopL(gi, gj); int wR; float trR = float.NaN;
                            if (!float.IsNaN(tS)) { trR = idx.TopRaw(x, z, out wR); if (wR < 0 || idx.banded[wR]) trR = float.NaN; }
                            bool rimOk = !float.IsNaN(trR) && StairBackRim(gi, gj, trR);
                            if (trc) TrLog(x, z, "段石の背の縁? top " + tS.ToString("F2") + " raw " + trR.ToString("F2") + " " + (rimOk ? "⭕" : (rimWhy ?? "—")), hgt);
                            if (rimOk)
                            { hgt = trR - STAIR_RIM_TUCK; faced = true; stairRim.Add(k); r.stairFaced++; }
                            else if (!float.IsNaN(fyS) && hgt > fyS)
                            {
                                int wS; bool dn; float fb = idx.FootBottom(x, z, NEAR + 0.1f, out wS, out dn);
                                if (wS >= 0 && !idx.banded[wS] && fb <= fyS + faceTol - 0.02f) { hgt = fyS; faced = true; r.stairFaced++; }
                            }
                            else if (float.IsNaN(fyS) && design != null)
                            {
                                // 面の外(石段が面と面の間の設計の地盤に立つ所)は駒の本当の底まで下げる(外形の中 ── 見えない)
                                int wS; bool dn; float fb = idx.FootBottom(x, z, NEAR + 0.1f, out wS, out dn);
                                if (wS >= 0 && !idx.banded[wS] && hgt > fb)
                                {
                                    // ⭐ 近くの面(STAIR_APRON 以内)に石段の足が面 ± 許容の内で埋まっているなら、底でなく**面の高さ**まで下げる(底より下げない)
                                    //   (2026-10-08 EDO-0502 第52巡 施主指摘「一段目の下の縁で地面が鋸の歯」)。⛔ 底(16.33)まで下げると、段の前の点(下の「石段の前」が面 16.50 に
                                    //   揃える)との三角形が 0.25 格子と段の向き(10.5°)の差で段石の前に 0〜0.17 の窪みを周期 1.37m の鋸の歯に並べた(岡部 K_Dan1 一段目)。
                                    //   外形の中の点は面の高さでも駒の中(底より上・天端より下)に隠れる。足が面より上の駒(上の段の積み)は従前どおり底まで。
                                    //   当たる先: CutEdgeSkin に石段を渡す全邸(岡部 Stage3b・山王 Stage9・土井 Stage4b)の、面の縁の外の設計の地盤に立つ石段の外形の中すべて。
                                    float fyN = float.NaN;
                                    for (int a8 = 0; a8 < 8 && float.IsNaN(fyN); a8++)
                                    {
                                        float an = a8 * Mathf.PI / 4f;
                                        for (float rr = 0.25f; rr <= STAIR_APRON + 1e-3f; rr += 0.25f)
                                        { float fq = FaceY(p + new Vector2(Mathf.Cos(an), Mathf.Sin(an)) * rr); if (!float.IsNaN(fq)) { fyN = fq; break; } }
                                    }
                                    float to = (!float.IsNaN(fyN) && !IsHollow(wS) && Mathf.Abs(fb - fyN) <= faceTol - 0.02f) ? Mathf.Max(fb, fyN) : fb;
                                    if (hgt > to) { hgt = to; r.stairFaced++; }
                                }
                            }
                        }
                        if (trc) TrLog(x, z, "石段の外形", hgt);
                        //   (石段の積みの駒は底の面を持たない殻 ── 底は FootBottom が見え面の足の線で取る)
                        // ⭐ 同じ駒(帯で篩わない駒)の外形の外 NEAR 以内で面の外の点は、底から盛土の法(1:batterFill)で受けた高さより
                        //   上げない(2026-10-04 EDO-0502 第10巡)── 石段 K_Dan1 は門の内の面(16.50)の縁の 1m 外に立ち、その間の設計の地盤は
                        //   上の面へ上る勾配(16.6〜16.9)── 段の積みの底 16.46 の前に土の斜面が被り、底の線が影の筋に見えた。⛔ 上げない(下げるだけ)。
                        //   当たる先: CutEdgeSkin に石段・段を渡す全邸(岡部 Stage3b・山王 Stage9)の、面の外に立つ石段の前と脇。
                        else if (near <= 1 && !faced && design != null && float.IsNaN(FaceY(p)))
                        {
                            // 面の縁から STAIR_APRON 以内で、近くの石段の足が面 ± 許容の内なら、その間は面の高さ(石段の前を面に揃える)
                            float fyA = float.NaN, fbA = float.NaN;
                            for (int a8 = 0; a8 < 8 && float.IsNaN(fyA); a8++)
                            {
                                float an = a8 * Mathf.PI / 4f;
                                for (float rr = 0.25f; rr <= STAIR_APRON + 1e-3f; rr += 0.25f)
                                { float fq = FaceY(p + new Vector2(Mathf.Cos(an), Mathf.Sin(an)) * rr); if (!float.IsNaN(fq)) { fyA = fq; break; } }
                            }
                            if (!float.IsNaN(fyA))
                                for (int a8 = 0; a8 < 8; a8++)
                                {
                                    float an = a8 * Mathf.PI / 4f; var dv = new Vector2(Mathf.Cos(an), Mathf.Sin(an));
                                    for (float rr = 0f; rr <= STAIR_APRON + 1e-3f; rr += 0.125f)
                                    {
                                        int wS; bool dn; float fb = idx.FootBottom(x + dv.x * rr, z + dv.y * rr, NEAR + 0.1f, out wS, out dn);
                                        if (float.IsNaN(fb)) continue;
                                        // ⭐ stairApronFrontOnly(土井 Stage4b・2026-10-06 EDO-0533 第17巡): 石段の**脇**(StairSide)は揃えない。⛔ 2026-10-06 まで、蔵の石段
                                        //   K_Kura1 の北の脇で 8 方向の光線のどれかが上の段の側面に当たった頂点だけが面 26.42 へ落ち、斜面 27.1〜27.3 の中に深さ 0.7〜0.8 の穴が
                                        //   斜めに並ぶ鋸になった。当たる先: stairApronFrontOnly を渡す邸(いまは土井 Stage4b)の、面の外に立つ石段の脇すべて。渡さない邸(岡部・山王)は不変。
                                        bool frontOk = !stairApronFrontOnly || !StairSide(x + dv.x * rr, z + dv.y * rr, fb, hgt);
                                        if (wS >= 0 && !idx.banded[wS] && !IsHollow(wS) && frontOk && Mathf.Abs(fb - fyA) <= faceTol - 0.02f && (float.IsNaN(fbA) || fb < fbA)) fbA = fb;   // 掘る部材の底は石段の足でない
                                        break;
                                    }
                                }
                            if (!float.IsNaN(fbA) && hgt > Mathf.Max(fyA, fbA)) { hgt = Mathf.Max(fyA, fbA); faced = true; r.stairFaced++; }
                            // ⭐ 足が面より下に埋まる石段の前で、設計の地盤が面より低い点は面まで上げる(2026-10-08 EDO-0502 第52巡)── 下げるだけだと
                            //   外形の中(面の高さ)と前の点(設計の地盤 16.41)の間に 0.09 の窪みが段の前に残った(岡部 K_Dan1 一段目)。上げる幅は許容(faceTol − 0.02)まで。
                            //   当たる先: CutEdgeSkin に石段を渡す全邸の、面の縁の外に立つ石段の前(STAIR_APRON 以内・stairApronFrontOnly の邸は脇を除く)。
                            //   ⚠ 既に面の高さ(差 1mm 以内)の点も「揃えた」印を立てる ── 立てないと次の「底から法」が段の底(16.33)から 1:1.5 で 16.41 へ下げた(同日・トレースで名指し)。
                            else if (!float.IsNaN(fbA) && hgt >= Mathf.Max(fyA, fbA) - 1e-3f) { faced = true; }
                            else if (!float.IsNaN(fbA) && fbA <= fyA + 1e-3f && hgt < fyA && hgt >= fyA - (faceTol - 0.02f)) { hgt = fyA; faced = true; r.stairFaced++; }
                        }
                        if (trc) TrLog(x, z, "石段の前", hgt);
                        if (near == 1 && !faced && design != null && float.IsNaN(FaceY(p)))
                        {
                            float kF = 1f / Mathf.Max(design.batterFill, 1e-3f), lim = float.NaN;
                            for (int a8 = 0; a8 < 8; a8++)
                            {
                                float an = a8 * Mathf.PI / 4f; var dv = new Vector2(Mathf.Cos(an), Mathf.Sin(an));
                                for (float rr = 0.125f; rr <= NEAR + 1e-3f; rr += 0.125f)
                                {
                                    int wS; bool dn; float fb = idx.FootBottom(x + dv.x * rr, z + dv.y * rr, NEAR + 0.1f, out wS, out dn);
                                    if (float.IsNaN(fb)) continue;
                                    //   石段の脇(stairApronFrontOnly・StairSide)の底からも法で受けない ── 上の段の側面は斜面に埋まる(蔵の石段 K_Kura1 の最上段の北の脇に深さ 0.4 の溝・2026-10-06 第17巡)
                                    // ⭐ 駒の天端の高さに居る点(石段の上がり口の段石の背 = 上の面の側)は、その駒の底から法で受けない(2026-10-07 EDO-0502 第41巡 施主指摘 D):
                                    //   上の面の地盤(天端 −0.02)が段石の底から 1:1.5 の法で 0〜0.4m の帯だけ引き下げられ、段石の背に窪みが出た(岡部 K_Dan1 の上がり口)。
                                    //   段石の前・脇(地盤が天端より下)は従前どおり。当たる先: CutEdgeSkin に石段を渡す全邸の、上の面へ上がる石段の最上段の背。
                                    bool atTop = wS >= 0 && wS < idx.gos.Count && idx.gos[wS] != null && hgt >= RB(idx.gos[wS]).max.y - 0.1f;
                                    if (wS >= 0 && !idx.banded[wS] && !IsHollow(wS) && !atTop && (!stairApronFrontOnly || !StairSide(x + dv.x * rr, z + dv.y * rr, fb, hgt))) { float l2 = fb + rr * kF; if (float.IsNaN(lim) || l2 < lim) lim = l2; }   // 掘る部材(溝)の底から法で受けない ── 溝の脇を底まで掘った(EDO-0533)
                                    break;   // その向きの最初の駒で止める
                                }
                            }
                            if (!float.IsNaN(lim) && hgt > lim) { hgt = lim; r.stairFaced++; }
                        }
                        if (trc) TrLog(x, z, "底から法", hgt);
                        if (faced) r.faced++;
                        float hgt0 = hgt;
                        // 部材の天端の下へ納める(真下 = 天端 − under / 周り 8 点の天端の最小 − eps)
                        float self = TopL(gi, gj), cap = float.NaN, capN1 = float.NaN;
                        // 法の面の cap の下限: 外形の外の点はその点の描く地盤(面・設計の地盤)、外形の中は足元の面(無ければ下限なし)
                        //   ── 法の足は地盤の下へ入るのが正しい納め。⛔ 法の面へ向けて地盤を掘り下げない(野面の隅の南で 29.55 → 27.88 と掘れた)。
                        //   面の外(造成しない地盤)では、法の面が地盤より 2×帯 を超えて低いときだけ ── 打ち切りの駒の先の天端が地盤へ沈む所
                        //   (天端が急に下がり帯で篩われる)は地盤の方を天端へ下げて被せない。
                        float fyIn = near < 2 ? float.NaN : FaceY(p);
                        Func<float, int, int, float> Floor = (tq, fi, fj) =>
                        {
                            if (near == 2 && !float.IsNaN(fyIn)) return Mathf.Max(tq, fyIn);
                            //   面の外の外形の中(出隅の駒の地盤側の腕など)も、法が地盤より 2×帯 を超えて低ければ地盤で止める
                            //   (野面の隅 kado3 の南の腕の下に 27.95 の穴が口を開けた・2026-09-25)
                            if (faced || hgt0 - tq > 2f * CREST_BAND) return Mathf.Max(tq, hgt0);
                            //   ⭐ 法の面の石の上向きの小面が、その駒の近くの天端より地盤の方が CREST_BAND を超えて低い所(= 土留めが地盤から立ち上がる
                            //   見え面の足元)は、地盤の下の根入れ ── 掘らない(2026-09-26 EDO-0437 第6巡: 前庭の東の野面 TW_Zentei_E の足元で、
                            //   足の石の頭 13.59 まで皮を下げ、見え面の前 0.2〜0.8m に深さ 0.2〜0.25 の溝の筋が立った)。
                            //   地盤が近くの天端と 2×帯 以内(打ち切りの駒の先で天端が地盤へ沈む所・見付 0.3 未満の低い所)は従来どおり天端の下へ
                            //   (帯 1 つでは前庭の東の南端 E_016f の見付 0.15 の所で天端に 0.036 被った)。
                            float cr = idx.CrestAround(org.x + fi * step, org.z + fj * step);
                            if (!float.IsNaN(cr) && hgt0 < cr - 2f * CREST_BAND && hgt0 > tq) return hgt0;
                            return tq;
                        };
                        // ⭐ 溝の脇の守り(keepGradeBeside・硬い): この点が溝の駒の外形の外なら、掘る部材(溝・蓋)の天端で下げる cap を造成の面 hgt0 で止める
                        //   (cap を掛ける前の高さ = 面・設計の地盤)。外形の内か(keepY = NaN)は掘る部材の cap に当たったときだけ引く。
                        float keepY = float.NaN; bool keepAsked = false, keepHit = false;
                        //   keepBatter > 0 なら床は min(造成の面, 溝の天端の外の辺からの法)── 位置について連続(BatterFloor)
                        Func<float> KeepY = () =>
                        {
                            if (!keepAsked)
                            {
                                keepAsked = true;
                                if (keepSet != null && !InKeepHull(p)) { float bf = BatterFloor(p); keepY = float.IsNaN(bf) ? hgt0 : Mathf.Min(hgt0, bf); }
                            }
                            return keepY;
                        };
                        if (!float.IsNaN(self))
                        {
                            cap = self - under; if (faceTop.Contains(CK(gi, gj))) cap = Floor(cap, gi, gj);
                            int sw; if (keepSet != null && topWho.TryGetValue(CK(gi, gj), out sw) && IsHollow(sw)) { float ky = KeepY(); if (!float.IsNaN(ky)) { keepHit = true; if (cap < ky) cap = ky; } }
                        }
                        for (int di = -CAPR; di <= CAPR; di++)
                            for (int dj = -CAPR; dj <= CAPR; dj++)
                            {
                                if (di == 0 && dj == 0) continue;
                                float tq = TopL(gi + di, gj + dj); if (float.IsNaN(tq)) continue;
                                // ⭐ 2 格子先の低い天端が、間の点の高い駒の天端の陰なら引かない(2026-10-07 EDO-0502 第42巡 施主指摘 B):
                                //   皮の三角形は隣の点(1 格子)までしか渡らない ⇒ 間に高い駒(上の段石)が立つ先の低い天端(下の段の踏面)には被らない。
                                //   ⛔ 2026-10-07 まで、上の段石の背の縁の外の点が 0.45 先の下の段の踏面 18.47 で引き下げられ、背の縁が 0.2〜0.3 窪んだ(岡部 K_Dan1)。
                                //   当たる先: CutEdgeSkin を通る全邸の、段石・段の背の縁(上の駒の陰の下の駒の天端)。
                                if (Mathf.Abs(di) == 2 || Mathf.Abs(dj) == 2)
                                {
                                    float tm = TopL(gi + (di / 2 != 0 ? di / 2 : 0), gj + (dj / 2 != 0 ? dj / 2 : 0));
                                    if (!float.IsNaN(tm) && tm > tq + STAIR_RIM_COVER) continue;
                                }
                                int hw = -1;
                                if (hollowSet != null)
                                {
                                    topWho.TryGetValue(CK(gi + di, gj + dj), out hw);
                                    // 掘る部材の窪みの上の隣: この点がその駒の外形の外なら、窪みの底でなく縁の天端で取る(外形の中は従来どおり)
                                    if (IsHollow(hw) && !EdoGeom.PIP(idx.hulls[hw], p)) { float rm = RimL(gi + di, gj + dj); if (!float.IsNaN(rm) && rm > tq) tq = rm; }
                                }
                                tq -= eps; if (faceTop.Contains(CK(gi + di, gj + dj))) tq = Floor(tq, gi + di, gj + dj);
                                // ⭐ 面(造成の面)の中で部材の外形の外の点は、土留めの天端の帯(crestBandParts)の石の頭が面より低くても
                                //   面の高さより下げない(2026-09-27・EDO-0437 普請検査 r15 ── 返しの隅石の腕の先の頭 14.31 に引かれて、
                                //   前庭 14.50 の皮が隅石の背と袖の背の際で 0.37 窪んだ)。石の頭が面の下へ入るのは土留めが面を受ける正しい納め。
                                //   頭が面より帯 2 つ(0.30)を超えて低い所(打ち切りの先・低い見付)は従来どおり天端の下へ。
                                else if (faced && near < 2 && crestTop.Contains(CK(gi + di, gj + dj)) && tq < hgt0 && hgt0 - tq <= 2f * CREST_BAND) tq = hgt0;
                                if (keepSet != null && IsHollow(hw)) { float ky = KeepY(); if (!float.IsNaN(ky)) { keepHit = true; if (tq < ky) tq = ky; } }   // 溝の外の点は造成の面より下げない
                                if (float.IsNaN(cap) || tq < cap) cap = tq;
                                if (Mathf.Abs(di) <= 1 && Mathf.Abs(dj) <= 1 && (float.IsNaN(capN1) || tq < capN1)) capN1 = tq;
                            }
                        // 裏込めの天端の下限: 外形の縁の帯(FLAT)では真下の天端 − FILL_UNDER まで・周りは 1 格子(0.25m)の天端まで。
                        //   ⭐ 土留めの背(駒に背の面が無く、底 = 天端)では皮が天端の高さまで来ないと縁の 0.05m 外で底を割る
                        //   (2026-09-25 実測: 前庭の西の土留めの背で 0.06〜0.10m)。
                        float capF = capN1;
                        if (!float.IsNaN(self)) { float sc = self - (FillSeeded(gi, gj) ? FILL_UNDER : under); capF = float.IsNaN(capF) ? sc : Mathf.Min(capF, sc); }
                        float pre = hgt;
                        if (stairRim.Contains(k) && !float.IsNaN(self)) cap = self - STAIR_RIM_TUCK;   // 段石の背の縁: 自分の段石の天端の下だけ(下の段の天端で引き下げない)
                        if (!float.IsNaN(cap) && hgt > cap) { hgt = cap; r.clamped++; if (!float.IsNaN(self)) r.under++; }
                        if (trc) TrLog(x, z, "天端の下(self " + self.ToString("F2") + " cap " + cap.ToString("F2") + ")", hgt);
                        // ⭐ 溝の脇の法(keepBatter > 0・硬): 天端が沈んだ溝の外形の外は、床(天端の外の辺からの法)まで下げる ── 造成の面のまま残すと
                        //   外形の内の頂点(天端 − under)との三角形が縁石に被って歯形になる。床が造成の面にある点(沈んでいない溝・法の届かない点)は触らない。
                        if (keepBatter > 1e-3f && keepSet != null)
                        {
                            float ky = KeepY();
                            if (!float.IsNaN(ky) && ky < hgt0 - 1e-4f)
                            {
                                keepHit = true;
                                if (hgt > ky)
                                {
                                    hgt = ky; r.keepBatterCut++;
                                    if (hgt0 - ky > r.keepBatterMax) { r.keepBatterMax = hgt0 - ky; r.keepBatterAt = new Vector3(x, ky, z); }
                                }
                            }
                        }
                        if (keepHit) { keepFloor[k] = keepY; if (hgt >= keepY - 1e-4f && !float.IsNaN(cap)) r.keepHeld++; }
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
                                //   ⭐ 外形(凸包)の中でも駒の面が真上・真下に無い点(凹んだ駒の外接の中の空き)は外と同じに近くの底で塞ぐ
                                //   (2026-09-26 EDO-0437 第6巡: 野面の打ち切りの駒 TW_Zentei_SW_013f・W_028f の端で天端の石だけが張り出し、
                                //   その下の空きの点が底を持たず、石の下が 0.02〜0.04 覗いた)。
                                bool air = near == 2 && float.IsNaN(BotL(gi, gj)) && float.IsNaN(TopL(gi, gj));
                                int rr = near == 2 && !air ? 0 : 2;
                                for (int di = -rr; di <= rr; di++)
                                    for (int dj = -rr; dj <= rr; dj++)
                                    {
                                        int who; float qx = org.x + (gi + di * 0.5f) * step, qz = org.z + (gj + dj * 0.5f) * step;
                                        float bq = idx.FootBottom(qx, qz, NEAR + 0.1f, out who); if (float.IsNaN(bq)) continue;   // 法の途中は底でない(見え面の足の線)
                                        // 鉛直な面の下の縁はその点のごく近く(0.2m)で取る ── 0.6m では段ごとに底が上がる袖で下の段の縁を拾い、
                                        //   縁の底より 0.08m 低く塞いだ。近くに無ければ(殻の石垣の見え面から離れた点)広く取る。
                                        float wb = idx.WallBottom(qx, qz, 0.2f, who); if (float.IsNaN(wb)) wb = idx.WallBottom(qx, qz, NEAR + 0.1f, who);
                                        if (!float.IsNaN(wb)) bq = Mathf.Min(bq, wb);
                                        if (float.IsNaN(nb) || bq > nb) nb = bq;
                                    }
                                if (!float.IsNaN(nb) && nb > hgt + 1e-4f && nb <= fy + faceTol - 0.02f)
                                {
                                    float v = near == 2 && !air ? nb : nb + 0.005f; if (!float.IsNaN(capF)) v = Mathf.Min(v, capF);
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
                                    float bq = idx.FootBottom(qx, qz, NEAR + 0.1f, out who); if (float.IsNaN(bq)) continue;   // 法の途中は底でない(見え面の足の線)
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
                        // ⭐ 門の上向きの面(屋根・軒を除く)の下へ皮を GATE_UNDER 納める ── 面が皮と同じ高さ(± 0.02)か、皮に 0.5 以内で埋まる所
                        //   (敷居・縁・基壇の段。床の帯の外へ出る面も・EDO-0428 二巡目)
                        if (gateUp.Count > 0)
                        {
                            //   皮の三角形は隣の格子点まで直線で渡るので、この点の周り ±step の見える面も拾う ── 格子点だけで納めると段の縁で皮が面を跨いで出た。
                            float mn = float.NaN;
                            //   刻みは step/4(0.0625)── 基壇の天端の三角形の割れ目から覗く下の棚(幅数 cm)も拾う(普請検査 EDO-0428 二巡目 (−485.48, 841.98))
                            for (int sa = -4; sa <= 4; sa++)
                                for (int sc = -4; sc <= 4; sc++)
                                {
                                    float qx = x + sa * step * 0.25f, qz = z + sc * step * 0.25f; List<int> gl;
                                    if (!gateHash.TryGetValue(((long)Mathf.FloorToInt(qx) << 32) ^ (uint)Mathf.FloorToInt(qz), out gl)) continue;
                                    //   隠れた面(上に別の面が被る)も数える ── 天端の三角形の割れ目から下の棚が覗く(幅 2〜4cm)。基壇の中の皮は下げても見えない
                                    foreach (var id in gl)
                                    {
                                        float ys; if (!TriYAt(gateUp[id], qx, qz, out ys)) continue;
                                        if (ys < hgt + 0.02f && ys >= hgt - GATE_BURY && (float.IsNaN(mn) || ys < mn)) mn = ys;
                                    }
                                }
                            if (!float.IsNaN(mn) && hgt > mn - GATE_UNDER) { hgt = mn - GATE_UNDER; r.gateUnder++; }
                        }
                        if (trc) TrLog(x, z, "格子の点の終わり", hgt);
                        H[k] = hgt;
                        if (orig - hgt > r.maxLower) { r.maxLower = orig - hgt; r.lowerAt = new Vector3(x, hgt, z); }
                        if (hgt - orig > r.maxRaise) { r.maxRaise = hgt - orig; r.raiseAt = new Vector3(x, hgt, z); }
                    }
            }
        if (SkinTrace != null) TrDump("3b の前", H, org.x, org.z, step);
        // ---- 3b 見え面の前へ皮を出さない(硬い・許容0 ── 2026-09-26 EDO-0437 第5巡)
        //   皮の格子(0.25)の点は、土留めの外形の中では天端の下(cap)へ納まり、隣の外の点は足元の地盤 ── その間の三角形は法の見え面と
        //   ほぼ同じ傾きで張り、野面の石の出入り(±0.07〜0.2)と目地から土の帯として覗いた(前庭の東の縁 z≈854.8〜855.1 で見え面の前に
        //   13.64〜14.32 の土・足元の土の山)。⇒ 天端の帯で篩う駒の外形の中の点から、**見え面の側の低い隣の点**への辺
        //   (メッシュの辺 = 4 方向と対角 (+1,+1)/(−1,−1))を 5 点で測り、見え面の向きの水平の光線が 0.6m の内に部材の面へ当たらない
        //   (= 石の中でも石の後ろでもなく、見え面の前の空に在る)なら、その点を 0.05 ずつ下げる。下限 = その辺の低い端の高さと、その点の
        //   部材の底(外形の中で皮が駒の底を割らない)の高い方。下げた点の奥の辺も測り直す(最大 8 巡)。
        //   ⛔ 上げない。⛔ 外形の外の点(足元の地盤)は触らない ── 足元の高さは設計の地盤と面が決める。⛔ 背の側(見え面と逆)の辺は測らない
        //   (背の土は天端の側 ── 面の高さ)。当たる先: CutEdgeSkin を通る全邸の、天端の帯で篩う土留め・石垣(crestBandParts)の見え面の前。
        if (bandSet != null && bandSet.Count > 0)
        {
            var nbr = new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1), new Vector2Int(1, 1), new Vector2Int(-1, -1) };
            var faceOf = new Dictionary<int, Vector2>();
            var cand = new List<long>(); var candWho = new Dictionary<long, List<int>>(); var underFace = new HashSet<long>();
            // ⭐ 硬い面(SkinFace.tol > 0 ── 石段の上がり口の段石の背の平ら)の中の点は下げない(2026-10-07 EDO-0502 第47巡):
            //   面の高さが硬い所では、返しの石垣の法の下の点も面の高さが地盤(法の足はその下へ根入れ)。⛔ 下げると岡部 K_Dan1 の上がり口の背が
            //   返しの見え面の前で 18.73 → 18.58 と窪んだ(この 3b が段鼻へ下りる斜めの隣を「見え面の側の低い点」と読んだ)。
            var hardFaces = new List<SkinFace>(); foreach (var f0 in fl) if (f0.tol > 0f) hardFaces.Add(f0);
            foreach (var kv in H)
            {
                if (PIN.Contains(kv.Key)) continue;
                int gi = (int)(kv.Key >> 32), gj = (int)(uint)(kv.Key & 0xffffffff);
                float x = org.x + gi * step, z = org.z + gj * step;
                if (NearPart(gi, gj) != 2) continue;
                if (hardFaces.Count > 0) { bool inHard = false; foreach (var hf in hardFaces) if (EdoGeom.PIP(hf.poly, new Vector2(x, z))) { inHard = true; break; } if (inHard) continue; }
                int who; float tr = idx.TopRaw(x, z, out who);
                // ⭐ 上を向いた面の無い法の帯(城の石垣の滑らかな見え面 ── 法線の y 0.24 < UP_NY)の下の点も候補に入れる(2026-10-05 EDO-0502 第23巡):
                //   TopRaw が NaN でも、真上にその駒の**見え面**が在れば(TopIndex.UnderFace)法の帯の下の点。⛔ 2026-10-05 まで TopRaw の NaN で外し、門の内の
                //   TW_Kado_Shumen_0_0 の法の帯(外形の中 3 駒)の皮の点が 1 点も測られず、見え面の線の点 17.39 から前の地盤 16.94 へ張る
                //   皮の三角が法の前へ立っていた(野面は石の頭の小面が上を向くので候補に入っていた)。
                //   ⛔ 外形の中というだけで入れない ── 天端も見え面も上に無い背の帯(外形の縁)の点まで下げ、TW_Higashi_Hokuto_6_0 の背に
                //   深さ 1.4m の窪みを掘って小口の隙を 7→13 に増やした(同じ巡の試し)。
                //   当たる先: CutEdgeSkin を通る全邸の、天端の帯で篩う城の石垣(Castle Wall)の法の帯(岡部 Stage3b の外周・郭の石垣・山王 Stage9 の土留め)。
                if (float.IsNaN(tr) || who < 0 || !idx.banded[who]) who = -1;
                // ⭐ 外形の中の点が**複数の駒の外形**に入る所(入隅で袖と城の石垣が重なる所)は、天端の一番高い駒だけでなく、点を外形に含む
                //   天端の帯の駒すべての見え面の向きで測る(2026-10-05 EDO-0502 第21巡: 門の内の袖 × TW_Kado_Shumen_0_0 の入隅で、点が袖の駒の外形の
                //   中と読まれ袖の見え面の向きだけを測り、城の石垣の見え面の 0.02m 奥の点から前の地盤へ張る皮の三角が法の前へ突き出ていた)。
                //   当たる先: CutEdgeSkin を通る全邸の、天端の帯の駒が入隅で重なる所(岡部 Stage3b・山王 Stage9)。
                var whos = new List<int>();
                for (int k = 0; k < idx.gos.Count; k++)
                {
                    if (!idx.banded[k]) continue; var bb = idx.bounds[k];
                    if (x < bb.x - 0.01f || x > bb.z + 0.01f || z < bb.y - 0.01f || z > bb.w + 0.01f) continue;
                    if (k != who && (idx.hulls[k] == null || !EdoGeom.PIP(idx.hulls[k], new Vector2(x, z)))) continue;
                    if (!faceOf.ContainsKey(k)) { Vector2 fv = Vector2.zero; try { fv = WallFace(idx.gos[k]); } catch (Exception) { } faceOf[k] = fv; }
                    if (faceOf[k].sqrMagnitude < 0.5f) continue;
                    if (who < 0 && !idx.UnderFace(x, z, k, faceOf[k])) continue;   // 天端の無い点は見え面の下だけ
                    whos.Add(k);
                }
                if (whos.Count == 0) continue;
                cand.Add(kv.Key); candWho[kv.Key] = whos; if (who < 0) underFace.Add(kv.Key);
            }
            Func<long, Vector3> PosOf = kk => { int gi = (int)(kk >> 32), gj = (int)(uint)(kk & 0xffffffff); return new Vector3(org.x + gi * step, H[kk], org.z + gj * step); };
            // 辺 k(高さ hk)→ k2 が見え面の前の空を通るか
            //   ⭐ 法の面の上の点(天端の帯の外 = faceTop)は点そのもの(t = 0)も測る ── 面の多角形が見え面の前まで張り出していると、
            //   皮は面の高さ(Floor)で法の石の上に被り(前庭の東の縁の北端 z≈863: 石の頭 14.37 の上に皮 14.44)、辺の途中の点は石の中に入る。
            //   ⛔ 天端の帯の点では t = 0 を測らない(天端の背の面の点が天端の石の上を抜けて「見える」と読まれ、背に溝を掘る)。
            // ⭐ 当たりに数えるのは、見え面が測る向きと逆を向かない駒だけ(2026-10-05 EDO-0502 第25巡): 入隅(門の内の袖 TW_Kado_Sode_3_0 の
            //   積み × TW_Kado_Shumen_0_0)では、袖の積みの法の前に張った皮から見え面の向きへ打つ光線が 0.6m の内で向かいの城の石垣の
            //   見え面に当たり「石の後ろ」と読まれ、皮が積みの天端の下 16.79 で平らに残って箱形の土の盛りが立った。向かいの壁(見え面が
            //   こちらを向く・内積 < −0.3)は前の空の向こうの物で、石の後ろではない。当たる先: CutEdgeSkin を通る全邸の入隅の 3b。
            Func<Vector2, Func<int, bool>> notFacing = fv0 => k =>
            {
                Vector2 f; if (!faceOf.TryGetValue(k, out f)) { f = Vector2.zero; try { f = WallFace(idx.gos[k]); } catch (Exception) { } faceOf[k] = f; }
                return f.sqrMagnitude < 0.5f || Vector2.Dot(f, fv0) >= -0.3f;
            };
            Func<long, float, long, Vector2, bool> Exposed = (kk, hk, k2, fv) =>
            {
                var okF = notFacing(fv);
                var P = PosOf(kk); P.y = hk; var Q = PosOf(k2); if (hk - Q.y <= 0.02f) return false;
                Vector3 f3 = new Vector3(fv.x, 0f, fv.y);
                int gi0 = (int)(kk >> 32), gj0 = (int)(uint)(kk & 0xffffffff);
                bool onFace = !float.IsNaN(TopL(gi0, gj0)) && faceTop.Contains(kk);
                if (onFace && float.IsNaN(idx.Ray(P, f3, 0.6f, -1, okF))) return true;
                foreach (float tt in new[] { 0.1f, 0.3f, 0.5f, 0.7f, 0.9f })
                {
                    var q = Vector3.Lerp(P, Q, tt); if (q.y <= Q.y + 0.01f) continue;
                    if (float.IsNaN(idx.Ray(q, f3, 0.6f, -1, okF))) return true;
                }
                return false;
            };
            for (int pass = 0; pass < 8; pass++)
            {
                int changed = 0;
                foreach (var kk in cand)
                {
                    int gi = (int)(kk >> 32), gj = (int)(uint)(kk & 0xffffffff);
                    float hk = H[kk]; float nh = hk;
                    foreach (var whoK in candWho[kk])
                    {
                    var fv = faceOf[whoK];
                    float lo = float.NaN; var front = new List<long>();
                    foreach (var o2 in nbr)
                    {
                        long k2 = CK(gi + o2.x, gj + o2.y); float h2;
                        if (!H.TryGetValue(k2, out h2) || h2 >= nh - 0.02f) continue;
                        if (Vector2.Dot(new Vector2(o2.x, o2.y).normalized, fv) < 0.3f) continue;   // 見え面の側だけ
                        front.Add(k2); if (float.IsNaN(lo) || h2 > lo) lo = h2;
                    }
                    if (front.Count == 0) continue;
                    // 見え面の下の点(underFace)の底は、その駒の見え面の足の線(WallBottom ── 殻の駒の法の途中は底でない)。⛔ BotL(最も低い面)は
                    //   法の帯の下で法の面そのものを返し、見え面の線の点を 1cm も下げられなかった(2026-10-05 第23巡)。⛔ 広い輪の FootBottom は
                    //   段違いの隣の駒の低い足を拾う ── その駒だけ・0.2m で取る。天端の下の点は従来どおり BotL。
                    float bl = BotL(gi, gj);
                    if (underFace.Contains(kk)) { float wb = idx.WallBottom(org.x + gi * step, org.z + gj * step, 0.2f, whoK); if (!float.IsNaN(wb)) bl = wb; }
                    float floor = float.IsNaN(bl) ? lo : Mathf.Max(lo, Mathf.Min(bl, nh));
                    while (nh > floor + 1e-4f)
                    {
                        bool any = false; foreach (var k2 in front) if (Exposed(kk, nh, k2, fv)) { any = true; break; }
                        if (!any) break;
                        nh = Mathf.Max(floor, nh - 0.05f);
                    }
                    }
                    if (nh < hk - 1e-4f)
                    {
                        H[kk] = nh; changed++;
                        if (hk - nh > r.faceDropMax) { r.faceDropMax = hk - nh; r.faceDropAt = new Vector3(org.x + gi * step, nh, org.z + gj * step); }
                    }
                }
                r.faceDropped += changed;
                if (changed == 0) break;
            }
        }
        if (SkinTrace != null) TrDump("3c の前", H, org.x, org.z, step);
        // ---- 3c 外形の縁で閉じる(硬い・許容0 ── 2026-09-26 EDO-0437 第7巡)

        CloseRimAtHull(idx, H, PIN, CK, org, step, FaceY, faceTol, ref r, keepSet != null ? IsHollow : null, keepFloor);   // ⚠ ref ── 2026-10-05 まで値渡しで rimRaised/rimLowered が報告で常に 0 だった

        if (SkinTrace != null) TrDump("3d の前", H, org.x, org.z, step);
        // ---- 3d 据わりの守り(硬い・許容0 ── 2026-10-05 EDO-0533 土井 全項目の検査: 駒の浮き 27・一部の浮き 88・植栽 35・溝 171)
        //   皮は 3〜3c で面・設計の地盤・部材の天端・石段の足へ寄せて**元の地形より下げる**ことがある。その升に先に据わっていた駒
        //   (外周の長屋・棟・植栽・溝)は元の地形で据えてあるので、下げた分だけ当たりが全部そろって浮く。⇒ 最後に、駒が地面に触れていた
        //   頂点の下で皮を min(元の地形, 頂点) まで戻す(上げるだけ)。⛔ 部材の基準点で測らない ── 実メッシュの頂点(0.25m 升ごとの最下点)。
        //   上げた所は周りへ盛土の法で下ろし(鉛直の板を立てない)、部材の天端(三角形の中の標本)を越える所は天端に譲る ──
        //   ⛔ 升を外して元の地形へ戻さない(元の地形は溝・受けの天端より高い・2026-10-05 第10巡)。譲って届かない点は駒の側として名乗る。
        if (seated != null)
            SeatGuard(idx, parts, seated, H, O, PIN, In, ci0, cj0, ci1, cj1, N, step, org, probe, CK,
                      design != null && design.batterFill > 1e-3f ? design.batterFill : SEAT_BATTER, ref r, hollowSet);
        r.pinned = PIN.Count;


        // ---- 3e 盛った土は最後に勝つ(SkinDesign.hold・2026-10-08 EDO-0502 第55巡 施主側の裁き「型を一つに」)── 立てた土(部材の小口・端の駒を
        //   土で隠す盛り)は設計の意図そのもの。3〜3d のどの枝の押し下げ(面の高さ・法の面の下・天端の下の cap・見え面の前・石段の外形)より後に、
        //   hold の節点の周り(HoldY が値を持つ点)だけを y = max(y, HoldY) にする。⛔ 枝ごとに hold を除外しない(第49〜53巡で 5 か所に散った)。
        //   縁の点(PIN ── 地形と継ぐ)は触らない。当たる先: SkinDesign.hold を渡す邸だけ(今は岡部 Stage3b の小口の土)── hold の無い邸の皮は不変。
        if (design != null && design.hold != null)
        {
            int raised = 0; float rmx = 0f; var keys = new List<long>(H.Keys);
            foreach (var kk in keys)
            {
                if (PIN.Contains(kk)) continue;
                int gi = (int)(kk >> 32), gj = (int)(uint)(kk & 0xffffffff);
                float hy = HoldY(new Vector2(org.x + gi * step, org.z + gj * step));
                if (!float.IsNaN(hy) && hy > H[kk] + 1e-4f) { rmx = Mathf.Max(rmx, hy - H[kk]); H[kk] = hy; raised++; }
            }
            r.holdRaised = raised; r.holdRaisedMax = rmx;
        }
        // ---- 3f 野面の石垣の天端の裏石の帯を土で覆う(SkinDesign.crestCover・指図 const.nozuraCrestCover・2026-10-09 EDO-0502 第63巡)──
        //   皮の節点ごとに NozuraCrestCover.Apply(盛るだけ・表の石の上と見え面の前は盛らない)。設計の格子(双一次)でなく皮の節点で効かせる
        //   ⛔ 設計の格子に置くと 0.25m の双一次が表の石の上(0〜0.36)へ土を引き込む。縁の点(PIN)は触らない。当たる先: crestCover を渡す邸だけ。
        if (design != null && design.crestCover != null)
        {
            int raised = 0; float rmx = 0f; var keys = new List<long>(H.Keys); var ccv = design.crestCover;
            // 覆う駒(野面)でない部材(石段・城の石垣・段石)の外形の中と縁 0.2 は盛らない(⛔ 段石・踊り場の上へ土を被せない)
            ccv.otherPart = q =>
            {
                for (int h = 0; h < idx.hulls.Count; h++)
                {
                    if (h < idx.gos.Count && ccv.pieceSet.Contains(idx.gos[h])) continue;
                    var hb = idx.bounds[h]; if (q.x < hb.x - 0.2f || q.x > hb.z + 0.2f || q.y < hb.y - 0.2f || q.y > hb.w + 0.2f) continue;
                    if (EdgeOrIn(idx.hulls[h], q, 0.2f)) return true;
                }
                return false;
            };
            foreach (var kk in keys)
            {
                if (PIN.Contains(kk)) continue;
                int gi = (int)(kk >> 32), gj = (int)(uint)(kk & 0xffffffff);
                var q3 = new Vector2(org.x + gi * step, org.z + gj * step); float y0 = H[kk];
                if (!float.IsNaN(ccv.Target(q3)) && ccv.otherPart(q3)) { ccv.otherSkipped++; continue; }
                float y1 = design.crestCover.Apply(q3, y0);
                // 表の石の上で帯の縁の手前は駒の天端 − 0.003 まで(⛔ 越えない)上げる ── 皮の一次の面が帯の縁で石の天端の下へ潜らない
                if (y1 <= y0 + 1e-4f && design.crestCover.Protected(q3) && design.crestCover.NearBandEdge(q3))
                { int w3; float tp = idx.Top(q3.x, q3.y, out w3); if (!float.IsNaN(tp) && w3 >= 0 && w3 < idx.gos.Count && design.crestCover.pieceSet.Contains(idx.gos[w3]) && tp - 0.003f > y0) y1 = tp - 0.003f; }
                if (y1 > y0 + 1e-4f) { rmx = Mathf.Max(rmx, y1 - y0); H[kk] = y1; raised++; }
            }
            r.crestCovered = raised; r.crestCoverMax = rmx;
        }
        if (SkinTrace != null) TrDump("4 の前", H, org.x, org.z, step);
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
        // 検め(硬い・許容0): 植栽の点の下に穴が無いこと(既に穴だった升も数える)
        if (plantPoints != null)
            foreach (var pp in plantPoints)
            {
                int i = CI(pp.x) - ci0, j = CJ(pp.y) - cj0;
                if (i >= 0 && j >= 0 && i < bw && j < bh && !hv[j, i]) r.plantOnHole++;
            }

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
        // 溝の脇の守り: 被りのうち、掘る部材の天端が外形の外 0.05 の造成の面より低い所は溝の側(皮は造成の面より下げない)
        Func<int, Vector2, float, bool> sunk = null;
        if (keepSet != null)
            sunk = (k, q, top) =>
            {
                if (!IsHollow(k)) return false;
                float g = FaceY(q); if (float.IsNaN(g)) g = OutsideY(q, null);
                return !float.IsNaN(g) && g > top + 1e-3f;
            };
        MeasureSkin(idx, ref r, null, (px, pz) => treeCells.Contains(CK(CI(px), CJ(pz))), sunk, design != null ? design.buried : null,
                    design != null && design.crestCover != null ? (Func<Vector2, bool>)design.crestCover.Designed : null);
        return r;
    }

    /// <summary>皮と部材の取り合いを測り直す(皮を起こし直さずに)。<paramref name="samples"/> に隙の点を最大 20 行刷る。</summary>
    public static SkinReport MeasureSkinContact(IList<GameObject> parts, List<string> samples = null, IList<GameObject> crestBandParts = null, NozuraCrestCover crestCover = null)
    {
        var bs = crestBandParts != null ? new HashSet<GameObject>(crestBandParts) : null;
        var idx = new TopIndex(); foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g, bs != null && bs.Contains(g));
        var r = new SkinReport(); r.parts = idx.hulls.Count; r.mesh = "—";
        MeasureSkin(idx, ref r, samples, null, null, null, crestCover != null ? (Func<Vector2, bool>)crestCover.Designed : null); return r;
    }

    /// <summary>**皮を駒の実メッシュの外形の縁で閉じる**(2026-09-26・EDO-0437 第7巡)。格子(0.25m)の点ごとに決めた皮は、点の間を三角形で
    /// 直線に渡るので、外形の縁(= 張り出す天端の石の縁)の真下を通る所で底を割ったり(隙)、天端を越えたり(被り)する ──
    /// 打ち切りの駒の端で天端の石(厚さ 0.2)だけが張り出す所(山王 前庭の南西 `TW_Zentei_SW_013f`・西 `W_028f` で 0.02〜0.044)と、
    /// 面が天端より僅かに高い縁(`TW_Zentei_W_006f` ほか 4 点・0.013)。
    /// <para>外形の各辺を 0.1m ごとに歩き、縁の点 pe から外へ 0.05 の点では **縁の真下の底**(pe から内へ 0.05/0.15/0.30 の最も低い面と、
    /// pe の 0.10 以内の鉛直な面の下の縁 ── 普請検査と同じ物差し)を、内へ 0.05 の点では**天端**(帯で篩った天端)を相手に、
    /// その点を含む皮の三角形(格子の対角 (0,0)-(1,1) で割った物)の値を出し、底を割る(− 0.005)なら重みの最も大きい動かせる頂点を
    /// 上げ、天端を越えるなら天端を越える動かせる頂点を下げる(三角形の値がちょうど相手 ± 0.003 になる量)。⛔ ±0.25 の固定の窓で拾わない。</para>
    /// <para>硬い条件: 隙 0・被り 0。動かさない: 縁の点(PIN = 地形のまま)。上げる量の上限 = 面(無ければ今の皮)+ faceTol − 0.02
    /// を超える底(それは駒が浮く ── 駒の側の話)と、頂点の真上の駒の天端(天端を越えて上げない)。当たる先: CutEdgeSkin を通る全邸の
    /// 部材(石段・袖・土留め・踏石)の外形の縁すべて。</para></summary>
    static void CloseRimAtHull(TopIndex idx, Dictionary<long, float> H, HashSet<long> PIN, Func<int, int, long> CK, Vector3 org, float step,
                               Func<Vector2, float> FaceY, float faceTol, ref SkinReport r,
                               Func<int, bool> keepFor = null, Dictionary<long, float> keepFloor = null)
    {
        // keepFor(k) の駒(掘る部材)の縁で天端に被らないよう下げるとき、keepFloor に造成の面を持つ頂点(溝の外形の外)はそこより下げない
        //   (溝の脇の守り・CutEdgeSkin の keepGradeBeside ── 被りは溝の側として残る)
        // 点 q を含む三角形の頂点と重み
        Func<Vector2, long[], float[], bool> Tri = (q, ks, ws) =>
        {
            float fx = (q.x - org.x) / step, fz = (q.y - org.z) / step;
            int gi = Mathf.FloorToInt(fx), gj = Mathf.FloorToInt(fz); float u = fx - gi, v = fz - gj;
            // 三角形 (00,01,11) は v ≥ u、(00,11,10) は u > v
            if (v >= u) { ks[0] = CK(gi, gj); ks[1] = CK(gi, gj + 1); ks[2] = CK(gi + 1, gj + 1); ws[0] = 1f - v; ws[1] = v - u; ws[2] = u; }
            else { ks[0] = CK(gi, gj); ks[1] = CK(gi + 1, gj + 1); ks[2] = CK(gi + 1, gj); ws[0] = 1f - u; ws[1] = v; ws[2] = u - v; }
            for (int e = 0; e < 3; e++) if (!H.ContainsKey(ks[e])) return false;
            return true;
        };
        Func<long, Vector2> XZ = kk => new Vector2(org.x + (int)(kk >> 32) * step, org.z + (int)(uint)(kk & 0xffffffff) * step);
        Func<long, float> Cap = kk => { var q = XZ(kk); int w; float t = idx.TopRaw(q.x, q.y, out w); return t; };
        for (int pass = 0; pass < 3; pass++)
        {
            int moved = 0;
            for (int k = 0; k < idx.hulls.Count; k++)
            {
                var h = idx.hulls[k];
                Vector2 cen = Vector2.zero; foreach (var q in h) cen += q; cen /= h.Length;
                for (int e = 0; e < h.Length; e++)
                {
                    Vector2 A = h[e], Bv = h[(e + 1) % h.Length], ab = Bv - A; float L = ab.magnitude; if (L < 1e-4f) continue;
                    Vector2 tn = ab / L, nrm = new Vector2(tn.y, -tn.x);
                    if (Vector2.Dot(nrm, (A + Bv) * 0.5f - cen) < 0) nrm = -nrm;
                    for (float s = 0.05f; s < L - 0.05f + 1e-4f; s += 0.05f)
                    {
                        var pe = A + tn * s; var pin = pe - nrm * 0.05f; var pout = pe + nrm * 0.05f;
                        var ks = new long[3]; var ws = new float[3]; int w1, w2;
                        // 天端(内へ 0.05)── 被らない
                        float top = idx.Top(pin.x, pin.y, out w1);
                        if (!float.IsNaN(top) && Tri(pin, ks, ws))
                        {
                            float g = 0f; for (int i = 0; i < 3; i++) g += ws[i] * H[ks[i]];
                            if (g > top + 0.0005f)
                            {
                                // 天端を越える動かせる頂点を、重みの大きい順に下げる
                                float need = g - (top - 0.003f);
                                var ord = new List<int> { 0, 1, 2 }; ord.Sort((a, b) => ws[b].CompareTo(ws[a]));
                                foreach (int i in ord)
                                {
                                    if (need <= 0f || ws[i] < 0.05f || PIN.Contains(ks[i]) || H[ks[i]] <= top) continue;
                                    float dv = Mathf.Min(need / ws[i], H[ks[i]] - (top - 0.003f));
                                    float kf; if (keepFor != null && keepFloor != null && keepFor(k) && keepFloor.TryGetValue(ks[i], out kf))
                                    { if (H[ks[i]] - dv < kf) { if (pass == 0) r.keepRimHeld++; dv = H[ks[i]] - kf; } if (dv <= 1e-5f) continue; }
                                    H[ks[i]] -= dv; need -= dv * ws[i]; r.rimLowered++; r.rimLowerMax = Mathf.Max(r.rimLowerMax, dv); moved++;
                                }
                            }
                        }
                        // 底(外へ 0.05 の点から見える縁の真下)── 割らない
                        bool covered = false; foreach (var h2 in idx.hulls) if (EdoGeom.PIP(h2, pout)) { covered = true; break; }
                        if (covered) continue;
                        float topRaw = idx.TopRaw(pin.x, pin.y, out w2); if (float.IsNaN(topRaw)) continue;
                        float bot = idx.Bottom(pin.x, pin.y, out w2);
                        for (int q = 1; q <= 2; q++) { var pq = pe - nrm * (0.15f * q); float bq = idx.Bottom(pq.x, pq.y, out w2); if (!float.IsNaN(bq) && (float.IsNaN(bot) || bq < bot)) bot = bq; }
                        { float wb = idx.WallBottom(pe.x, pe.y, 0.10f); if (!float.IsNaN(wb) && (float.IsNaN(bot) || wb < bot)) bot = wb; }
                        if (float.IsNaN(bot) || !Tri(pout, ks, ws)) continue;
                        float go = 0f; for (int i = 0; i < 3; i++) go += ws[i] * H[ks[i]];
                        if (go >= bot - 0.005f) continue;
                        float fy = FaceY(pout); float refY = float.IsNaN(fy) ? go : fy;
                        if (bot > refY + faceTol - 0.02f) { if (pass == 0) r.rimRefused++; continue; }
                        {
                            float need = (bot + 0.003f) - go;
                            var ord = new List<int> { 0, 1, 2 }; ord.Sort((a, b) => ws[b].CompareTo(ws[a]));
                            foreach (int i in ord)
                            {
                                if (need <= 0f || ws[i] < 0.05f || PIN.Contains(ks[i])) continue;
                                float cap = Cap(ks[i]); float lim = float.IsNaN(cap) ? refY + faceTol - 0.02f : Mathf.Min(cap - 0.003f, refY + faceTol - 0.02f);
                                float dv = Mathf.Min(need / ws[i], lim - H[ks[i]]); if (dv <= 0f) continue;
                                H[ks[i]] += dv; need -= dv * ws[i]; r.rimRaised++; r.rimRaiseMax = Mathf.Max(r.rimRaiseMax, dv); moved++;
                            }
                        }
                    }
                }
            }
            if (moved == 0) break;
        }
    }

    /// <summary>据わりの守りで「地面に触れていた」と読む頂点の高さの上限(元の地形からの浮き)[m]。地面に置く物の接地の許容(±0.01)より
    /// 広く取る ── 据えた後に地形の LOD・2m 格子の双一次で数 cm ずれた駒も守る。それより高い頂点は地面に触れていない(縁の下・礎石の上の柱)。</summary>
    public const float SEAT_TOL = 0.05f;
    /// <summary>他の部材の上向きの面に載っていると読む窓(頂点の下 0.05・上 0.02)[m] ── 蓋石が溝の縁に載る・石灯籠が石段に載る。</summary>
    const float SEAT_ON_PART_LO = 0.05f, SEAT_ON_PART_HI = 0.02f;

    /// <summary>**据わりの守りに渡す駒を集める**(<see cref="CutEdgeSkin"/> の <c>seated</c>)── <paramref name="root"/> の下の
    /// 生きた MeshFilter の持ち主すべて。<paramref name="exclude"/> の下(皮の群など)は除く。parts と重なっても CutEdgeSkin の側で外す。</summary>
    public static List<GameObject> SeatedUnder(Transform root, params Transform[] exclude)
    {
        var L = new List<GameObject>(); if (root == null) return L;
        var ex = new HashSet<Transform>(); if (exclude != null) foreach (var e in exclude) if (e != null) ex.Add(e);
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || !mf.gameObject.activeInHierarchy || mf.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            bool skip = false; for (var a = mf.transform; a != null && !skip; a = a.parent) if (ex.Contains(a)) skip = true;
            if (!skip) L.Add(mf.gameObject);
        }
        return L;
    }

    /// <summary>据わりの守りで上げた所を周りへ下ろす法(1:n)の既定値 ── 設計の盛土の法(<see cref="SkinDesign.batterFill"/>)が無いとき。</summary>
    const float SEAT_BATTER = 1.5f;
    /// <summary>据わりの守りで皮を上げる量の上限を測る、頂点の周りの標本の刻み(格子の 1/4)── 三角形の中で部材の天端を越えないかを見る。</summary>
    const int SEAT_SUB = 4;

    /// <summary>**据わりの守り**(<see cref="CutEdgeSkin"/> の 3d・硬い・許容0・2026-10-05 EDO-0533)。
    /// <para>駒 = parts の各駒(子のメッシュ全部で一つ)と seated の各メッシュ(parts の子・皮は除く)。駒ごとに、皮の升の中の頂点を 0.25m 升ごとの
    /// 最下点へ間引き(<see cref="LowestPerCell"/> と同じ考え ── 同じ升の中では地面に先に着くのは最下点)、高さが元の地形 + <see cref="SEAT_TOL"/>
    /// 以下の点を「地面に触れていた点」とする。点の真下に**他の部材**の上向きの面が頂点 −0.05〜+0.02 にあれば、その点は部材に載る(地面でない)。
    /// 載る点が駒の触れる点の 1/4 を超える駒(蓋石・石段の上の灯籠)は丸ごと外す。</para>
    /// <para>触れていた点ごとに下限 = min(元の地形, 頂点) を取り、その点を含む皮の三角形(メッシュと同じ対角で割った物)の値が下限 − 0.003 を
    /// 割るなら、縁の点(PIN = 地形のまま)でない頂点に**床**(下限)を掛ける(縁の点が低くて足りなければ重みの最も大きい頂点に +0.10 まで)。⛔ 下げない。</para>
    /// <para>⭐ **床は周りへ法で下ろす**(1:<paramref name="batter"/>・2026-10-05 第10巡)── 三角形の 3 頂点だけを上げると、上げ幅(最大 1.04m)が
    /// 0.25m の中で立ち、皮に鉛直の板が立った(土井 廊下 L_HiromaOku_Kaidan の柱の脇 0.35m・材質 Hifu_ModernTerrain_0)。床は隣の頂点へ
    /// 距離/法 ずつ下げて伝え、今の皮の高さに届いた所で止める(埋めて隠す ── 駒の足元は小さな土の盛りになる)。</para>
    /// <para>⭐ **部材の天端を越えない**(硬い・許容0)── 上げる頂点ごとに、その頂点に触れる三角形の中の標本(格子の 1/<see cref="SEAT_SUB"/>)で
    /// 部材の天端(帯で篩う・自分の駒も含む)− 0.003 を越えない上限を取り、床をそこで止める(部材の天端に譲る)。
    /// ⛔ 2026-10-05 第9巡まで、上限を上げた頂点の真上だけで測り、三角形が隣の溝の壁を跨いで窪みの中へ張り出した所を見落とした上、
    /// 越える頂点の升を皮から外して元の地形のまま残した ── 元の地形は溝・受けの天端より高いので、その升の地形が駒に被った
    /// (被り 276 → 1,396 点・うち外した升 256 の地形 335 点)。いまは升を外さない。</para>
    /// <para>譲って床に届かない触れる点は**駒の側**(駒の足が隣の部材の天端より高い所に据わる)── 件数と駒の名を <see cref="SkinReport.seatUnmet"/>・
    /// <see cref="SkinReport.seatUnmetBy"/> に、譲らせた部材の名を <see cref="SkinReport.seatYieldBy"/> に刷る。</para>
    /// 当たる先: CutEdgeSkin に seated を渡す邸(いまは土井 Stage4b)。岡部・山王は渡していない ── 同じ浮きが出たら seated を渡せば効く。</summary>
    static void SeatGuard(TopIndex idx, IList<GameObject> parts, IList<GameObject> seated, Dictionary<long, float> H, Dictionary<long, float> O,
                          HashSet<long> PIN, Func<int, int, bool> In, int ci0, int cj0, int ci1, int cj1, int N, float step,
                          Vector3 org, GroundProbe probe, Func<int, int, long> CK, float batter, ref SkinReport r,
                          HashSet<GameObject> hollowSet = null)
    {
        r.seatGuard = true;
        float cs = step * N;
        if (batter <= 1e-3f) batter = SEAT_BATTER;
        var partSet = new HashSet<Transform>(); foreach (var g in parts) if (g != null) partSet.Add(g.transform);
        Func<Transform, GameObject> PartOf = tr => { for (var a = tr; a != null; a = a.parent) if (partSet.Contains(a)) return a.gameObject; return null; };
        // 駒の一覧(持ち主の部材 = parts の駒なら自分・seated なら null)
        var pieces = new List<KeyValuePair<GameObject, MeshFilter[]>>();
        foreach (var g in parts) if (g != null && g.activeInHierarchy) pieces.Add(new KeyValuePair<GameObject, MeshFilter[]>(g, g.GetComponentsInChildren<MeshFilter>()));
        int nParts = pieces.Count;
        var seenMf = new HashSet<MeshFilter>();
        foreach (var g in seated)
        {
            if (g == null || !g.activeInHierarchy) continue;
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                if (!seenMf.Add(mf) || PartOf(mf.transform) != null || mf.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) continue;
                pieces.Add(new KeyValuePair<GameObject, MeshFilter[]>(mf.gameObject, new[] { mf }));
            }
        }
        float wx0 = org.x + ci0 * cs, wx1 = org.x + (ci1 + 1) * cs, wz0 = org.z + cj0 * cs, wz1 = org.z + (cj1 + 1) * cs;
        Func<float, float, long[], float[], bool> Tri = (x, z, ks, ws) =>
        {
            float fx = (x - org.x) / step, fz = (z - org.z) / step;
            int gi = Mathf.FloorToInt(fx), gj = Mathf.FloorToInt(fz); float u = fx - gi, v = fz - gj;
            if (v >= u) { ks[0] = CK(gi, gj); ks[1] = CK(gi, gj + 1); ks[2] = CK(gi + 1, gj + 1); ws[0] = 1f - v; ws[1] = v - u; ws[2] = u; }
            else { ks[0] = CK(gi, gj); ks[1] = CK(gi + 1, gj + 1); ks[2] = CK(gi + 1, gj); ws[0] = 1f - u; ws[1] = v; ws[2] = u - v; }
            for (int e = 0; e < 3; e++) if (!H.ContainsKey(ks[e])) return false;
            return true;
        };
        // ---- 1 触れる点と床(上げる頂点の下限)
        var F = new Dictionary<long, float>();            // 頂点 → 床
        var Fsrc = new Dictionary<long, string>();        // 床を掛けさせた駒の名
        var direct = new HashSet<long>();                 // 触れる点の三角形の頂点として床を掛けた物(法で伝えた物でない)
        var touches = new List<KeyValuePair<Vector3, string>>();
        Action<long, float, string> SetF = (k, v, nm) => { float f0; if (!F.TryGetValue(k, out f0) || v > f0) { F[k] = v; Fsrc[k] = nm; } };
        for (int pi = 0; pi < pieces.Count; pi++)
        {
            var owner = pi < nParts ? pieces[pi].Key : null;
            var low = new Dictionary<long, Vector3>();
            foreach (var mf in pieces[pi].Value)
            {
                if (mf == null || mf.sharedMesh == null || !mf.gameObject.activeInHierarchy) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                var b = rr.bounds; if (b.max.x < wx0 || b.min.x > wx1 || b.max.z < wz0 || b.min.z > wz1) continue;
                var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
                for (int i = 0; i < vs.Length; i++)
                {
                    var w = m.MultiplyPoint3x4(vs[i]);
                    int qi = Mathf.FloorToInt((w.x - org.x) / step), qj = Mathf.FloorToInt((w.z - org.z) / step);
                    if (!In(Mathf.FloorToInt((float)qi / N), Mathf.FloorToInt((float)qj / N))) continue;
                    long qk = CK(qi, qj); Vector3 o; if (!low.TryGetValue(qk, out o) || w.y < o.y) low[qk] = w;
                }
            }
            // ⭐ 掘る部材(hollowSet ── 土井が渡す・2026-10-05 EDO-0533 第11巡の直し)は、頂点に加えて**底の面の全体**を 0.125m 毎に標本に取る ──
            //   溝の駒は低ポリの箱で頂点が四隅と縁にしか無く、頂点の升だけを床へ上げると駒の中ほどの皮は 3 の cap(窪みの底 − under 0.15)のまま残り、
            //   底の薄い型(B 玉石・C/D 素掘り)の駒の底の帯が皮から 0.10〜0.15 浮いた(溝の一部浮き 243 の大半 ── D10・D6・D1 seg3)。
            //   標本の真下に他の部材の面がある所(溝の上に掛かる蓋石の中ほど・重ねた駒の重なり)は取らない(その駒は地面でなく部材に載る)。
            //   当たる先: CutEdgeSkin に hollowParts と seated を両方渡す邸(いまは土井 Stage4b)。渡さない邸は不変。
            var extra = new List<Vector3>();
            if (owner != null && hollowSet != null && hollowSet.Contains(owner))
                for (int k = 0; k < idx.gos.Count; k++)
                {
                    if (idx.gos[k] != owner) continue;
                    var hb = idx.bounds[k]; var hull = idx.hulls[k];
                    for (float x = Mathf.Floor(hb.x / 0.125f) * 0.125f; x <= hb.z; x += 0.125f)
                        for (float z = Mathf.Floor(hb.y / 0.125f) * 0.125f; z <= hb.w; z += 0.125f)
                        {
                            if (x < wx0 || x > wx1 || z < wz0 || z > wz1) continue;
                            var q = new Vector2(x, z); if (!EdoGeom.PIP(hull, q) || EdoGeom.DistToPolyEdge(hull, q) < 0.02f) continue;
                            if (!In(Mathf.FloorToInt((x - org.x) / step / N), Mathf.FloorToInt((z - org.z) / step / N))) continue;
                            float yb = idx.BottomOwner(x, z, k); if (float.IsNaN(yb)) continue;
                            int wl; float yl = idx.Bottom(x, z, out wl); if (wl >= 0 && wl != k && !float.IsNaN(yl) && yl < yb - 0.005f) continue;
                            extra.Add(new Vector3(x, yb, z));
                        }
                }
            if (low.Count == 0 && extra.Count == 0) continue;
            var touch = new List<Vector3>(); int onPart = 0;
            foreach (var v in low.Values)
            {
                float og = probe.At(v.x, v.z); if (float.IsNaN(og) || v.y > og + SEAT_TOL) continue;
                int wo; float tp = idx.TopRaw(v.x, v.z, out wo);
                if (wo >= 0 && idx.gos[wo] != owner && !float.IsNaN(tp) && tp >= v.y - SEAT_ON_PART_LO && tp <= v.y + SEAT_ON_PART_HI) { onPart++; continue; }
                touch.Add(new Vector3(v.x, Mathf.Min(og, v.y), v.z));   // y = 下限
            }
            foreach (var v in extra)
            {
                float og = probe.At(v.x, v.z); if (float.IsNaN(og) || v.y > og + SEAT_TOL) continue;
                int wo; float tp = idx.TopRaw(v.x, v.z, out wo);
                if (wo >= 0 && idx.gos[wo] != owner && !float.IsNaN(tp) && tp >= v.y - SEAT_ON_PART_LO && tp <= v.y + SEAT_ON_PART_HI) continue;   // 載る点は数えずに外す(比は頂点で見る)
                touch.Add(new Vector3(v.x, Mathf.Min(og, v.y), v.z));
            }
            if (touch.Count == 0) continue;
            if (onPart * 4 > touch.Count + onPart) { r.seatOnPart++; continue; }
            r.seatPieces++;
            string nm = pieces[pi].Key.name;
            var ks = new long[3]; var ws = new float[3];
            foreach (var c in touch)
            {
                r.seatContacts++;
                if (!Tri(c.x, c.z, ks, ws)) continue;
                float g = 0f; for (int e = 0; e < 3; e++) g += ws[e] * H[ks[e]];
                if (g >= c.y - 0.003f) continue;
                touches.Add(new KeyValuePair<Vector3, string>(c, nm));
                // 縁の点でない頂点を下限まで上げた後の値(縁の点は地形のまま)
                float g2 = 0f;
                for (int e = 0; e < 3; e++)
                {
                    bool mov = !PIN.Contains(ks[e]);
                    float hv = mov ? Mathf.Max(H[ks[e]], c.y) : H[ks[e]];
                    if (mov && H[ks[e]] < c.y) { SetF(ks[e], c.y, nm); direct.Add(ks[e]); }
                    g2 += ws[e] * hv;
                }
                if (g2 < c.y - 0.003f)
                {
                    // 縁の点(地形のまま)が低い ── 重みの最も大きい動かせる頂点で補う(+0.10 まで)
                    int best = -1; for (int e = 0; e < 3; e++) if (!PIN.Contains(ks[e]) && ws[e] >= 0.05f && (best < 0 || ws[e] > ws[best])) best = e;
                    if (best >= 0)
                    {
                        float hb = Mathf.Max(H[ks[best]], c.y);
                        float add = Mathf.Min((c.y - 0.003f - g2) / ws[best] + 1e-4f, 0.10f);
                        SetF(ks[best], hb + add, nm); direct.Add(ks[best]);
                    }
                }
            }
        }
        if (F.Count == 0) { r.seatRaiseBy = ""; r.seatUnmetBy = ""; r.seatYieldBy = ""; return; }
        // ---- 2 床を周りへ法で下ろす(上げた所を 0.25m の中で立てない)── 今の皮の高さに届いた所で止める
        {
            var q = new Queue<long>(F.Keys);
            float d1 = step / batter, d2 = step * 1.41421356f / batter;
            int guard = 0;
            while (q.Count > 0 && guard++ < 2000000)
            {
                long k = q.Dequeue(); float fk = F[k];
                int gi = (int)(k >> 32), gj = (int)(uint)(k & 0xffffffff);
                for (int di = -1; di <= 1; di++)
                    for (int dj = -1; dj <= 1; dj++)
                    {
                        if (di == 0 && dj == 0) continue;
                        long n = CK(gi + di, gj + dj); float hn;
                        if (!H.TryGetValue(n, out hn) || PIN.Contains(n)) continue;
                        float cand = fk - ((di != 0 && dj != 0) ? d2 : d1);
                        if (cand <= hn + 1e-4f) continue;
                        float fn; if (F.TryGetValue(n, out fn) && fn >= cand - 1e-5f) continue;
                        F[n] = cand; Fsrc[n] = Fsrc[k]; q.Enqueue(n);
                    }
            }
        }
        // ---- 3 部材の天端を越えない上限(その頂点に触れる三角形の中の標本で)
        var topQ = new Dictionary<long, float>(); var topW = new Dictionary<long, int>();
        Func<int, int, float> TopAtSub = (si, sj) =>
        {
            long kk = CK(si, sj); float v; if (topQ.TryGetValue(kk, out v)) return v;
            int who; v = idx.Top(org.x + si * step / SEAT_SUB, org.z + sj * step / SEAT_SUB, out who);
            topQ[kk] = v; topW[kk] = who; return v;
        };
        var ks2 = new long[3]; var ws2 = new float[3];
        int bindW = -1;
        Func<long, float> Bound = k =>
        {
            int gi = (int)(k >> 32), gj = (int)(uint)(k & 0xffffffff);
            float B = float.PositiveInfinity; bindW = -1;
            for (int a = -SEAT_SUB; a <= SEAT_SUB; a++)
                for (int b = -SEAT_SUB; b <= SEAT_SUB; b++)
                {
                    int si = gi * SEAT_SUB + a, sj = gj * SEAT_SUB + b;
                    float tp = TopAtSub(si, sj); if (float.IsNaN(tp)) continue;
                    float x = org.x + si * step / SEAT_SUB, z = org.z + sj * step / SEAT_SUB;
                    // 標本を格子の内側へ僅かに寄せて、頂点 k に触れる三角形を引く(境の上の標本が隣の三角形に落ちないよう)
                    float ex = x + (a < 0 ? 1e-4f : a > 0 ? -1e-4f : 0f), ez = z + (b < 0 ? 1e-4f : b > 0 ? -1e-4f : 0f);
                    if (!Tri(ex, ez, ks2, ws2)) continue;
                    int e = -1; for (int t = 0; t < 3; t++) if (ks2[t] == k) e = t;
                    if (e < 0 || ws2[e] < 0.05f) continue;
                    float rest = 0f; for (int t = 0; t < 3; t++) if (t != e) rest += ws2[t] * H[ks2[t]];
                    float bb = (tp - 0.003f - rest) / ws2[e];
                    if (bb < B) { B = bb; bindW = topW[CK(si, sj)]; }
                }
            return B;
        };
        var H0 = new Dictionary<long, float>(); foreach (var k in F.Keys) H0[k] = H[k];
        var keys = new List<long>(F.Keys);
        // 上げる(床まで・上限で止める)を 3 巡 ── 隣を上げると上限が下がるので測り直す
        for (int it = 0; it < 3; it++)
            foreach (var k in keys)
            {
                float target = F[k];
                float B = Bound(k);
                H[k] = Mathf.Max(H0[k], Mathf.Min(target, B));
            }
        // 締め: 下げるだけの 1 巡(下げると他の上限は上がるだけ ⇒ 巡の後は全ての上げた頂点が上限の内)
        var yieldBy = new Dictionary<string, int>();
        foreach (var k in keys)
        {
            float B = Bound(k);
            if (H[k] > B) H[k] = Mathf.Max(H0[k], B);
            if (direct.Contains(k) && H[k] < F[k] - 1e-3f)
            {
                r.seatYield++;
                string who = bindW >= 0 ? idx.names[bindW] : "-";
                int n0; yieldBy.TryGetValue(who, out n0); yieldBy[who] = n0 + 1;
            }
        }
        // ---- 4 数える
        var raisedName = new Dictionary<string, int>();
        foreach (var k in keys)
        {
            float dv = H[k] - H0[k]; if (dv <= 1e-4f) continue;
            r.seatRaised++; if (!direct.Contains(k)) r.seatMound++;
            int n0; string nm = Fsrc[k]; raisedName.TryGetValue(nm, out n0); raisedName[nm] = n0 + 1;
            if (dv > r.seatRaiseMax) { r.seatRaiseMax = dv; int gi = (int)(k >> 32), gj = (int)(uint)(k & 0xffffffff); r.seatRaiseAt = new Vector3(org.x + gi * step, H[k], org.z + gj * step); }
        }
        var unmetName = new Dictionary<string, int>();
        {
            var ks = new long[3]; var ws = new float[3];
            foreach (var kv in touches)
            {
                var c = kv.Key; if (!Tri(c.x, c.z, ks, ws)) continue;
                float g = 0f; for (int e = 0; e < 3; e++) g += ws[e] * H[ks[e]];
                if (g >= c.y - 0.003f) continue;
                r.seatUnmet++; if (c.y - g > r.seatUnmetMax) { r.seatUnmetMax = c.y - g; r.seatUnmetAt = c; }
                int u0; unmetName.TryGetValue(kv.Value, out u0); unmetName[kv.Value] = u0 + 1;
            }
        }
        r.seatRaiseBy = TopN(raisedName, 6); r.seatUnmetBy = TopN(unmetName, 6); r.seatYieldBy = TopN(yieldBy, 6);
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

    /// <summary>点 q が外形の中か、縁から <paramref name="d"/> 以内か。</summary>
    static bool EdgeOrIn(Vector2[] hull, Vector2 q, float d) { return EdoGeom.PIP(hull, q) || EdgeDist(hull, q) < d; }

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

    static void MeasureSkin(TopIndex idx, ref SkinReport r, List<string> samples, Func<float, float, bool> plantCell = null,
                            Func<int, Vector2, float, bool> sunkHollow = null, HashSet<GameObject> buried = null, Func<Vector2, bool> coverDesigned = null)
    {
        var plantBy = new Dictionary<string, int>(); var sunkBy = new Dictionary<string, int>();
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
                    // 設計で土に埋める駒(SkinDesign.buried)は見え面を持たない ⇒ 被りに数えない
                    // 設計で土を載せる野面の天端の裏石の帯(SkinDesign.crestCover ── 見え面から 0.36 より奥)も被りに数えない(表の石の上 0〜0.36 は数える【硬】)
                    if (!float.IsNaN(gin) && !float.IsNaN(top) && !(buried != null && k < idx.gos.Count && buried.Contains(idx.gos[k])) && !(coverDesigned != null && coverDesigned(pin)))
                    {
                        r.coverPts++;
                        if (gin > top + 1e-3f)
                        {
                            r.coverN++; int c0; covBy.TryGetValue(idx.names[k], out c0); covBy[idx.names[k]] = c0 + 1;
                            if (sunkHollow != null && sunkHollow(k, pout, top)) { r.coverSunk++; int s0; sunkBy.TryGetValue(idx.names[k], out s0); sunkBy[idx.names[k]] = s0 + 1; }
                            if (!dg.InHole(pin.x, pin.y))
                            {
                                r.coverTerrain++;   // 皮でなく地形の升(穴を開けなかった升)が被る
                                // 地形の木・植栽の点が立つので穴を開けなかった升 ── 皮では直せない(穴を開けると Unity が木を消す)・駒の側
                                if (plantCell != null && plantCell(pin.x, pin.y)) { r.coverPlantCell++; int p0; plantBy.TryGetValue(idx.names[k], out p0); plantBy[idx.names[k]] = p0 + 1; }
                            }
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
        r.gapBy = TopN(gapBy, 6); r.coverBy = TopN(covBy, 6); r.coverPlantBy = TopN(plantBy, 6); r.coverSunkBy = TopN(sunkBy, 6);
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
    /// <summary>最後に外した縁の皮の三角形(世界座標)── <see cref="DrawnExpected"/> が読む。domain reload で消える(同じ巡の中だけ)。</summary>
    static readonly List<Vector3[]> PrevSkin = new List<Vector3[]>();
    public static int ClearEdgeSkins(Transform parent)
    {
        if (parent == null) return 0;
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int R = td.holesResolution; float cs = td.size.x / R; int n = 0;
        var kill = new List<GameObject>();
        foreach (Transform c in parent) if (c.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) kill.Add(c.gameObject);
        if (kill.Count > 0) PrevSkin.Clear();
        foreach (var g in kill)
        {
            var mf = g.GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
            {
                var m = mf.sharedMesh; var l2w = g.transform.localToWorldMatrix; var vs = m.vertices; var tri = m.triangles;
                for (int k = 0; k + 2 < tri.Length; k += 3) PrevSkin.Add(new[] { l2w.MultiplyPoint3x4(vs[tri[k]]), l2w.MultiplyPoint3x4(vs[tri[k + 1]]), l2w.MultiplyPoint3x4(vs[tri[k + 2]]) });
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
        readonly Terrain t; readonly float y0; readonly Vector3 org; float cs;
        int hi0, hj0, hw, hh; bool[,] holes;
        readonly Dictionary<long, List<Vector3[]>> hash = new Dictionary<long, List<Vector3[]>>();
        const float B = 0.5f;
        public int skins;
        static long K(int i, int j) { return ((long)i << 32) ^ (uint)j; }
        readonly bool prev;
        public DrawnGround(Terrain terrain) : this(terrain, null) { }
        /// <summary><paramref name="prevSkin"/> が渡され、生きている皮が無ければ、その三角形を皮として読む(穴は塞がれている ── 皮の在る所は皮を返す)。</summary>
        public DrawnGround(Terrain terrain, List<Vector3[]> prevSkin)
        {
            t = terrain; y0 = t.transform.position.y; org = t.transform.position;
            bool live = false;
            foreach (var mf in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
                if (mf.sharedMesh != null && mf.gameObject.activeInHierarchy && mf.name.StartsWith(SKIN_PREFIX, StringComparison.Ordinal)) { live = true; break; }
            if (!live && prevSkin != null && prevSkin.Count > 0)
            {
                prev = true;
                foreach (var q in prevSkin)
                {
                    float x0 = Mathf.Min(q[0].x, Mathf.Min(q[1].x, q[2].x)), x1 = Mathf.Max(q[0].x, Mathf.Max(q[1].x, q[2].x));
                    float z0 = Mathf.Min(q[0].z, Mathf.Min(q[1].z, q[2].z)), z1 = Mathf.Max(q[0].z, Mathf.Max(q[1].z, q[2].z));
                    if (x1 - x0 < 1e-5f || z1 - z0 < 1e-5f) continue;
                    for (int i = Mathf.FloorToInt(x0 / B); i <= Mathf.FloorToInt(x1 / B); i++)
                        for (int j = Mathf.FloorToInt(z0 / B); j <= Mathf.FloorToInt(z1 / B); j++)
                        {
                            List<Vector3[]> l; if (!hash.TryGetValue(K(i, j), out l)) { l = new List<Vector3[]>(); hash[K(i, j)] = l; }
                            l.Add(q);
                        }
                }
                return;
            }
            Init();
        }
        void Init()
        {
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
            if (prev) { float sp = Skin(x, z); if (!float.IsNaN(sp)) return sp; return t.SampleHeight(new Vector3(x, 0f, z)) + y0; }
            if (InHole(x, z)) return Skin(x, z);
            float g = t.SampleHeight(new Vector3(x, 0f, z)) + y0;
            // 地形の上へ被せた皮(地形の木の升の裏込め)は、地形より高い所だけ描かれる
            if (skins > 0) { float s = Skin(x, z); if (!float.IsNaN(s) && s > g) return s; }
            return g;
        }
    }

    /// <summary>描かれた地表の掴みを作る(<see cref="DrawnGround"/>)。</summary>
    public static DrawnGround Drawn() { return new DrawnGround(T()); }
    /// <summary>**皮を外している間も、外す前の皮を描かれた地表として読む掴み**(2026-09-26・EDO-0437 第11巡)。土留めの Stage は頭で縁の皮を外し
    /// (<see cref="ClearEdgeSkins"/>・穴を塞ぐ)、最後の Stage で皮を起こし直す ── その間の <see cref="Drawn"/> は穴の下に残る造成前の地形を返し、
    /// 参道の階の段 0 の端の隅石の当たり(y 13.10)を地形 13.33 の下と読んで見えないとした(皮は 11.94)。生きている皮が在れば <see cref="Drawn"/> と同じ。
    /// 当たる先: 皮を外した後・起こす前に見える地表で割る測りすべて(石段の端の退け・端の切りの見える当たり)。</summary>
    public static DrawnGround DrawnExpected() { return new DrawnGround(T(), PrevSkin); }

    /// <summary>部材の**上を向いた面**の最も高い所を引く掴み(駒が他の駒の下に入っているかを見る)。</summary>
    public sealed class PartTops
    {
        readonly TopIndex idx = new TopIndex();
        public PartTops(IList<GameObject> parts) { foreach (var g in parts) if (g != null && g.activeInHierarchy) idx.Add(g); }
        /// <summary>(x,z) の最も高い上向きの面と、その駒の名(無ければ NaN / null)。</summary>
        public float Top(float x, float z, out string who)
        { int w; float y = idx.Top(x, z, out w); who = w >= 0 ? idx.names[w] : null; return y; }
        /// <summary>(x,z) の部材の上向きの面の最も高い所(帯で篩わない・無ければ NaN)。</summary>
        public float RawTop(float x, float z) { int w; return idx.TopRaw(x, z, out w); }
    }

    // ---------------------------------------------------------------- 当たりの床(2026-09-27・EDO-0437/EDO-0480 ── docs/oki-kata.md §0a)
    /// <summary>**当たりの床** = 下端が**接すると決めた相手の面**だけを返す床。相手は (1) 石(土留め・袖)の**天端** ── 上向きの面のうち
    /// 天端の帯(<see cref="CREST_BAND"/>)に入る所、(2) 部材の載っていない所の**描かれた地表**。部材の上向きの面が在るのに天端の帯に
    /// 入らない所(野面の**目地** ── 石と石の間の、天端の 0.19 下の目地の底の板)は**跨ぎ**で NaN を返す ── 接する想定の無い所なので
    /// 据えの相手にも測りの相手にもしない。
    /// ⛔ 目地の底や、石の外形の下に隠れた地表で下端を測らない(2026-09-27 施主「設置する想定ではないところを測って隙間があると考えるのはナンセンス」)。
    /// 当たる先: 石の天端と地面に載せて光付けする部材(板塀の地覆・柱 ── <see cref="PostBoardRunScribed"/>)。以後、天端に載る部材の据え全て(EDO-0480)。</summary>
    public sealed class AtariBed
    {
        /// <summary>目地と読む深さ・周りを見る半径[m]。野面の目地は幅 0.02〜0.04・底は天端の 0.19〜0.20 下(`build_sanno_nozura.py`)。
        /// 半径 0.04 なら目地のどこからでも少なくとも片側の石の天端に届き、石の天端の凹凸(数 cm で 1〜2 cm)は深さ 0.05 に届かない。
        /// ⛔ 周り 0.6(<see cref="CREST_R"/>)の同じ駒の天端で篩わない ── 駒の端・見え面の際では輪が駒の外へ出て目地の底を天端と読んだ(2026-09-27 実測 0.18)。</summary>
        public const float JOINT_DEPTH = 0.05f, JOINT_R = 0.04f;
        /// <summary>目地に詰まった土を当たりに採る面一の許し[m](地面に置く物の接地の許容 ±0.01 と同じ)。</summary>
        public const float JOINT_SOIL_FLUSH = 0.01f;
        readonly DrawnGround dg; readonly PartTops tops;
        /// <summary>石の上向きの面の高さを升 <see cref="CELL"/> で覚える(目地の見分けは一点に 17 本引くので、覚えないと 1 駒に数分かかった)。</summary>
        const float CELL = 0.00125f;
        readonly Dictionary<long, float> raw = new Dictionary<long, float>();
        public AtariBed(IList<GameObject> stones) { dg = Drawn(); tops = stones == null || stones.Count == 0 ? null : new PartTops(stones); }
        float Raw(float x, float z)
        {
            int i = Mathf.RoundToInt(x / CELL), j = Mathf.RoundToInt(z / CELL); long k = ((long)i << 32) ^ (uint)j;
            float v; if (!raw.TryGetValue(k, out v)) { v = tops.RawTop(i * CELL, j * CELL); raw[k] = v; } return v;
        }
        /// <summary>(x,z) の当たりの面の高さ。跨ぎ(目地)では NaN。</summary>
        public float At(float x, float z) { bool span; return At(x, z, out span); }
        /// <summary><paramref name="span"/> = 跨ぎ(石の上向きの面が、周り <see cref="JOINT_R"/> の石の天端より <see cref="JOINT_DEPTH"/> 以上深い所 ── 目地)。</summary>
        public float At(float x, float z, out bool span)
        {
            span = false;
            float g = dg.At(x, z);
            if (tops == null) return g;
            float r0 = Raw(x, z);
            // 周り JOINT_R の最も高い相手の面(石の天端・地表)。そこより JOINT_DEPTH 以上深い所は、目地・石の縁の外の落ち(見え面の外の地表)で跨ぎ
            float mx = float.IsNaN(r0) ? g : (float.IsNaN(g) ? r0 : Mathf.Max(r0, g));
            if (float.IsNaN(mx)) return float.NaN;
            float top = mx;
            for (int r = 1; r <= 2; r++)
                for (int a = 0; a < 8; a++)
                {
                    float ang = a * Mathf.PI / 4f, rr = JOINT_R * r / 2f, px = x + Mathf.Cos(ang) * rr, pz = z + Mathf.Sin(ang) * rr;
                    float t = Raw(px, pz);
                    if (!float.IsNaN(t) && t > top) top = t;
                }
            if (float.IsNaN(r0)) { if (g >= top - JOINT_DEPTH) return g; span = true; return float.NaN; }   // 石の載っていない所 ── 地表が相手(石の縁の下へ落ちた地表は跨ぎ)
            if (r0 >= top - JOINT_DEPTH) return float.IsNaN(g) ? r0 : Mathf.Max(r0, g);   // 石の天端(土が被っていれば地表)
            float mxS = top;
            // 目地。土が天端と面一(<see cref="JOINT_SOIL_FLUSH"/> 以内)まで詰まっていれば、その土が相手。⛔ 目地の中の低い土・石の下に隠れた地表を相手にしない
            //   (2026-09-27 実測: 天端の 0.045 下の目地の土を相手に取り、地覆がそこへ 0.05 浮くと数えた)
            if (!float.IsNaN(g) && g >= mxS - JOINT_SOIL_FLUSH) return g;
            span = true; return float.NaN;
        }
    }

    // ---------------------------------------------------------------- 据わる床(2026-09-25・EDO-0430)
    /// <summary>**据わる床** = 描かれた地表(<see cref="Drawn"/> ── 縁の皮の升では皮)と、据えた部材(土留め・石段・袖)の
    /// 上向きの面の、高い方。門・柵のように**土留めの天端にも地面にも載る駒**が触れる相手。
    /// ⛔ 地形だけで測らない ── 山王の楼門は南東の隅が腰の土留めの天端(28.30)に載っていて床との隙は −0.60(根入れ)なのに、
    /// 土留めの外形の中の(見えない)地表 26.91 で測ると「浮き 0.79m」と出た(2026-09-25)。
    /// 当たる先: 門・柵・板塀の据え(山王 Stage4/5)と、その接地の検査。</summary>
    public sealed class Bed
    {
        readonly DrawnGround dg; readonly PartTops tops;
        public Bed(IList<GameObject> parts) { dg = Drawn(); tops = parts == null ? null : new PartTops(parts); }
        /// <summary>(x,z) の床の高さ(描かれた地表と部材の上面の高い方。どちらも無ければ NaN)。</summary>
        public float At(float x, float z)
        {
            float g = dg.At(x, z);
            if (tops != null)
            {
                string who; float t = tops.Top(x, z, out who);
                if (!float.IsNaN(t) && (float.IsNaN(g) || t > g)) g = t;
            }
            return g;
        }
    }

    /// <summary><see cref="Contact(GameObject,out Vector3,out int,float,int)"/> と同じ測り(格子ごとの最下点)を、
    /// 任意の床 <paramref name="bedAt"/> に対して取る。返り値 = 触れている所の隙(正=浮き・負=埋没)。測れなければ NaN。</summary>
    public static float ContactOn(GameObject go, Func<float, float, float> bedAt, out Vector3 at, out int count,
                                  float tol = 0.01f, int maxSamples = 4000)
    {
        var pts = GroundCandidates(go.transform, maxSamples);
        float best = float.NaN; at = go.transform.position; count = 0;
        var cs = new List<float>(pts.Count);
        foreach (var p in pts)
        {
            float b = bedAt(p.x, p.z); if (float.IsNaN(b)) continue;
            float c = p.y - b; cs.Add(c);
            if (float.IsNaN(best) || c < best) { best = c; at = p; }
        }
        if (float.IsNaN(best)) return best;
        foreach (var c in cs) if (c - best <= tol) count++;
        return best;
    }

    /// <summary>**浮いていれば床へ下ろす。**座(指図の面の高さ・`sill`/`seat`)は**上限**として置いた駒を、
    /// 床(<see cref="Bed"/>)から浮いていれば触れる所まで下ろす。触れているか、根入れで埋まっていれば動かさない
    /// (根入れ・基壇の埋め込みは部材の設計)。硬い条件: 浮き 0。返り値 = 下ろした量[m](0 以上)。
    /// <paramref name="before"/> = 下ろす前の隙。⛔ 上げない(埋まりを消す向きには動かさない ── それは座の話)。
    /// ⛔ 基準点(ピボット)で高さを決めない ── 測るのは実メッシュの触れる所(規則21)。
    /// 当たる先: 座を一つの値で持つ門・柵の走り(山王の勝手口の木戸と `Ita_Keidai` の御供所の郭の区間 ──
    /// 座 28.30 のまま一段低い郭 27.35 の上に建ち 0.8m 浮いていた)。</summary>
    public static float SettleOnBed(GameObject go, Func<float, float, float> bedAt, out float before, int maxSamples = 4000)
    {
        Vector3 at; int n;
        before = ContactOn(go, bedAt, out at, out n, 0.01f, maxSamples);
        if (float.IsNaN(before)) throw new InvalidOperationException("SettleOnBed: " + go.name + " の下に床が測れない");
        if (before <= 0f) return 0f;
        go.transform.position -= new Vector3(0f, before, 0f);
        return before;
    }

    /// <summary>走りの継ぎ目(駒の原点 = 地盤の高さ・根入れ <paramref name="root"/> を持つ柵の柱)の高さ:
    /// 座 <paramref name="seat"/> で駒の足元(座 − 根入れ)が床より上に出る(= 浮く)なら床へ、そうでなければ座。
    /// <see cref="SettleOnBed"/> と同じ「座は上限・浮けば床へ」を継ぎ目の点で取る。</summary>
    public static float SeatOrBed(float x, float z, float seat, float root, Func<float, float, float> bedAt)
    {
        float b = bedAt(x, z);
        return (!float.IsNaN(b) && b < seat - root) ? b : seat;
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
