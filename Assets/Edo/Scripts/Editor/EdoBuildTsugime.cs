// EdoBuild — 継ぎ目を躯体の実面で納める(2026-10-03・EDO-0502 岡部の普請検査の差し戻し)。
//  ・長屋の躯体の端(札)どうしを平行移動だけで突き付ける(SpecBodySpanAlong / AbutBodyAlong)
//  ・躯体の走りの区間を測る(BodySpanAlong)
//  ・地形なりの板柵を板ごとに弦へ張る(ChordFenceRun)
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図を読んで渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>駒の**躯体**(屋根の材を除く・<see cref="BodyExRoof"/>)の、走り <paramref name="along"/> 上の区間 [最小, 最大]
    /// (<paramref name="origin"/> からの距離 s)。測るのは躯体の下端から <paramref name="bandLo"/>〜<paramref name="bandHi"/> の帯だけ ──
    /// 一階の庇・二階の軒・破風は帯の上に出るので拾わない。測れなければ (NaN, NaN)。
    /// ⛔ OBB・外接箱・呼び寸法で代用しない(一本物の長屋は破風が妻壁より 0.322m 出る・2026-10-03 岡部)。</summary>
    public static Vector2 BodySpanAlong(GameObject go, Vector2 origin, Vector2 along, float bandLo = 0.30f, float bandHi = 2.00f)
    {
        var pts = BodyExRoof(go.transform, 6000);
        if (pts.Count == 0) return new Vector2(float.NaN, float.NaN);
        float y0 = float.MaxValue; foreach (var p in pts) y0 = Mathf.Min(y0, p.y);
        along = along.normalized;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var p in pts)
        {
            if (p.y < y0 + bandLo || p.y > y0 + bandHi) continue;
            float s = Vector2.Dot(new Vector2(p.x, p.z) - origin, along);
            if (s < mn) mn = s; if (s > mx) mx = s;
        }
        return mn == float.MaxValue ? new Vector2(float.NaN, float.NaN) : new Vector2(mn, mx);
    }

    /// <summary>駒の**躯体の端(札の jambL / jambR)**の、走り <paramref name="along"/> 上の区間 [最小, 最大](<paramref name="origin"/> からの s)。
    /// 札の無い駒は (NaN, NaN)。⭐ 躯体 = 呼び寸法の長屋(<c>EdoAssets.Own.NagayaOmote2FKutai</c>)では jamb.x = ±len/2 が妻の海鼠の外面。
    /// ⛔ 外接箱・ピボットで代用しない(破風が妻壁より 0.322m 外へ出る)。</summary>
    public static Vector2 SpecBodySpanAlong(GameObject go, Vector2 origin, Vector2 along)
    {
        var path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        var sp = string.IsNullOrEmpty(path) ? null : EdoPartSpec.Get(path);
        if (sp == null || sp.jambL == null || sp.jambR == null) return new Vector2(float.NaN, float.NaN);
        along = along.normalized;
        float a = Vector2.Dot(EdoPartSpec.JambWorld(go.transform, sp.jambL) - origin, along);
        float b = Vector2.Dot(EdoPartSpec.JambWorld(go.transform, sp.jambR) - origin, along);
        return new Vector2(Mathf.Min(a, b), Mathf.Max(a, b));
    }

    /// <summary>**長さの固定された駒(長屋)を、走りに沿う平行移動だけで、前の相手の躯体の端へ突き付ける**(硬い・隙 0)。
    /// <paramref name="sTarget"/> = 相手の躯体の端の s。<paramref name="lowEnd"/>=true ならこの駒の躯体の低い側の端を、false なら高い側の端を
    /// そこへ着ける。測るのは札の躯体の端(<see cref="SpecBodySpanAlong"/>)── 破風の重なりは埋めて隠す(docs/oki-kata.md §0a・§4)。
    /// ⛔ 伸縮しない(柱間 1.818m と窓割りが崩れる・§2)。端数は鎖の末端の伸縮側(練塀)へ流す。
    /// 返り値 = 動かした量[m](札が無ければ NaN)。
    /// 当たる先: 躯体 = 呼び寸法の長屋を走りに並べる所(岡部の表長屋・門長屋の脇の棟)。札を持つ長屋なら他邸も同じ。</summary>
    public static float AbutBodyAlong(GameObject go, Vector2 origin, Vector2 along, float sTarget, bool lowEnd)
    {
        along = along.normalized;
        var sp = SpecBodySpanAlong(go, origin, along);
        if (float.IsNaN(sp.x)) return float.NaN;
        float d = sTarget - (lowEnd ? sp.x : sp.y);
        go.transform.position += new Vector3(along.x, 0f, along.y) * d;
        return d;
    }

    /// <summary>**継ぎ目の素通しを目の高さの帯の断面で測る**(2026-10-05・EDO-0533 第9巡)。走り <paramref name="along"/> の上で
    /// <paramref name="lo"/>(s の小さい側)と <paramref name="hi"/>(大きい側)の継ぎ目を、二つの駒の足元のうち高い方から
    /// <paramref name="bandAbove"/> までを <paramref name="step"/> 刻みの水平断面(三角形と面の交わり)で切り、高さごとに
    /// 「hi の端の面 − lo の端の面」を取る。返り値 = その最大[m](正 = その高さで素通しの隙・負 = めり込み)・測れなければ NaN。
    /// <paramref name="atY"/> = 最大の高さ(世界)・<paramref name="openBand"/> = 隙が 0.001 を超える高さの帯の厚み[m]。
    /// <para>⭐ <see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>(筋ごとの最小)は**どこか一筋が当たれば 0** を返すので、
    /// 妻の海鼠(±len/2)が当たっていれば、座の違う隣どうしで**上の棟の土台(海鼠より 0.030 内)・下の棟の漆喰(0.0335 内)**の高さに開く
    /// 素通しを捕まえない(土井 通用門 E13_N09 の両脇・表門 × E13_N11 で 0.030〜0.036 を ⭕ と刷った ── メモリ「門と塀の閉じ」の再発)。
    /// 当たる先: 座の違う表長屋・門長屋どうしの継ぎ目すべて(土井 辺13 の段の継ぎ目・岡部・松江松平の段の付いた外周)。測るだけで動かさない。</para></summary>
    public static float SeamSlit(GameObject lo, GameObject hi, Vector2 origin, Vector2 along, out float atY, out float openBand,
                                 float bandAbove = 2.5f, float step = 0.05f)
    {
        atY = float.NaN; openBand = 0f;
        along = along.normalized;
        var spL = SpecBodySpanAlong(lo, origin, along);
        float sJ = !float.IsNaN(spL.y) ? spL.y : BodySpanAlong(lo, origin, along, 0.3f, 2.0f).y;
        if (float.IsNaN(sJ)) return float.NaN;
        System.Func<Vector3, float> S = p => Vector2.Dot(new Vector2(p.x, p.z) - origin, along);
        // 継ぎ目の際(±0.5m)の躯体の下端 ── 高い方から帯を取る(門長屋の扉口の切り下げは際の外)
        float bLo = float.MaxValue, bHi = float.MaxValue;
        foreach (var p in BodyExRoof(lo.transform, 20000)) if (Mathf.Abs(S(p) - sJ) <= 0.5f) bLo = Mathf.Min(bLo, p.y);
        foreach (var p in BodyExRoof(hi.transform, 20000)) if (Mathf.Abs(S(p) - sJ) <= 0.5f) bHi = Mathf.Min(bHi, p.y);
        if (bLo == float.MaxValue || bHi == float.MaxValue) return float.NaN;
        float y0 = Mathf.Max(bLo, bHi) + 0.02f, y1 = Mathf.Max(bLo, bHi) + bandAbove;
        float worst = float.NaN;
        for (float y = y0; y <= y1 + 1e-4f; y += step)
        {
            float a = float.MinValue, b = float.MaxValue;
            foreach (var p in Section(lo.transform, y)) { float s = S(p); if (s >= sJ - 1.0f && s <= sJ + 0.5f) a = Mathf.Max(a, s); }
            foreach (var p in Section(hi.transform, y)) { float s = S(p); if (s >= sJ - 0.5f && s <= sJ + 1.0f) b = Mathf.Min(b, s); }
            if (a == float.MinValue || b == float.MaxValue) continue;
            float g = b - a;
            if (g > 0.001f) openBand += step;
            if (float.IsNaN(worst) || g > worst) { worst = g; atY = y; }
        }
        return worst;
    }

    // ───────────────────────────── 出隅の留めの長屋(二等分の面で切った版・EDO-0533 2026-10-04)
    //  据えの型: ① 両辺の壁の外面の線(区画の線から内へ c = 基壇の控え + 犬走り)の交点 Q を求める(FaceLineCorner)
    //            ② 要る長さ = Q から反対の端(隣の棟の躯体の端の s)までの壁の外面の長さ ⇒ 焼いた版を札の長さで引く(PickMiterCut)
    //            ③ 札の front を壁の外面の線へ・留めた端の札 jamb を Q へ(AbutBodyAlong)── 反対の妻は隣の棟へ突き付く
    //  ⛔ ピボット・外接箱で決めない。⛔ 伸縮しない。⛔ 留めた棟に PullAlongInside を掛けない(引くと留めの口が開く)。
    //  硬い: 札の長さが要る長さより 0.001 を超えて短い(留めか継ぎ目に隙)⇒ 建てない。柔らかい: 長い分(≤ 0.03)は隣の妻へ埋めて隠す。
    //  当たる先: 区画の出隅の頂点で、両辺の表長屋(同じ座・同じ二階)が出会う所すべて ── 土井 頂点13(E12_N03 × E13_N01)。
    //            土井 頂点15(E14_N1 × E15_N1・待ち)・岡部/松江松平の外周の出隅も同じ口で引ける(焼いてあれば)。

    /// <summary>二本の**壁の外面の線**(辺の始点 <paramref name="a1"/>・走り <paramref name="d1"/>・外向き <paramref name="out1"/> の線から内へ
    /// <paramref name="c1"/>)の交点 Q(外隅)。平行なら (NaN, NaN)。⭐ 控えが辺ごとに違っても Q は二本の線の交点のまま(二等分の面は
    /// 二本の線の角だけで決まる ⇒ 焼いた留めの切り口は c に依らず合う・変わるのは長さだけ)。</summary>
    public static Vector2 FaceLineCorner(Vector2 a1, Vector2 d1, Vector2 out1, float c1, Vector2 a2, Vector2 d2, Vector2 out2, float c2)
    {
        d1 = d1.normalized; d2 = d2.normalized;
        Vector2 p1 = a1 - out1.normalized * c1, p2 = a2 - out2.normalized * c2;
        float den = d1.x * d2.y - d1.y * d2.x;
        if (Mathf.Abs(den) < 1e-5f) return new Vector2(float.NaN, float.NaN);
        Vector2 w = p2 - p1;
        return p1 + d1 * ((w.x * d2.y - w.y * d2.x) / den);
    }

    /// <summary>札の躯体の長さ(jambR.x − jambL.x)。札が無ければ NaN。</summary>
    public static float SpecBodyLen(EdoPartSpec.Spec sp)
    {
        return sp == null || sp.jambL == null || sp.jambR == null ? float.NaN : sp.jambR.x - sp.jambL.x;
    }

    /// <summary>**長さの決まった留めの駒を、要る長さ <paramref name="need"/> から札で引く**。名の長さは 0.01m 刻み(<paramref name="pathOf"/>)なので、
    /// 四捨五入と切り上げの二つを試し、**焼いてあって札の長さが need − <paramref name="shortTol"/> 〜 need + <paramref name="longTol"/> に入る**最初の版を返す。
    /// 返り値 = 採れたか。<paramref name="path"/> = 採った版(採れなければ焼くべき版 = 切り上げの名)、<paramref name="lenSpec"/> = その札の長さ(無ければ NaN)。
    /// ⛔ 伸縮しない ── 合わなければ呼び手は建てずに待つ(硬い)。当たる先: 出隅の留めの長屋(<c>EdoAssets.Own.NagayaOmote2FKutaiMiterCut</c>)。</summary>
    public static bool PickMiterCut(Func<float, string> pathOf, float need, out string path, out float lenSpec,
                                    float shortTol = 0.001f, float longTol = 0.03f)
    {
        float lr = Mathf.Round(need * 100f) / 100f, lc = Mathf.Ceil(need * 100f - 1e-3f) / 100f;
        path = pathOf(lc); lenSpec = float.NaN;
        foreach (float L in lr == lc ? new[] { lr } : new[] { lr, lc })
        {
            string p = pathOf(L);
            if (!System.IO.File.Exists(p)) continue;
            if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) continue;   // 焼いたが Unity が取り込んでいない(.meta 無し)── 据えられない
            var sp = EdoPartSpec.Get(p); float len = SpecBodyLen(sp);
            if (float.IsNaN(len)) continue;
            lenSpec = len;
            float diff = len - need;
            if (diff >= -shortTol && diff <= longTol) { path = p; return true; }
        }
        return false;
    }

    /// <summary>札の足の外形から、**どちらの端が留めて切ってあるか**を読む(背の側の足の端が躯体の端 jamb より 0.05m 以上内へ入る端 = 切った端)。
    /// 返す: (−X 端が切ってあるか, +X 端が切ってあるか)。札の端と欄の端の取り違え(局所 ±X と走りの向き)を据える前に捕まえる(硬い)。</summary>
    public static bool[] SpecMiterCutEnds(EdoPartSpec.Spec sp)
    {
        if (sp == null || sp.jambL == null || sp.jambR == null || sp.foot == null || sp.foot.Count == 0) return new[] { false, false };
        float zb = float.MaxValue; foreach (var q in sp.foot) zb = Mathf.Min(zb, q.y);
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var q in sp.foot) if (q.y <= zb + 0.01f) { mn = Mathf.Min(mn, q.x); mx = Mathf.Max(mx, q.x); }
        return new[] { mn - sp.jambL.x > 0.05f, sp.jambR.x - mx > 0.05f };
    }

    /// <summary>**留めた端の札 jamb の外面の点(局所 x = jamb.x・z = front)を外隅 <paramref name="q"/> へ平面で寄せる**(硬い・高さは動かさない)。
    /// 走りと外面の線へ別々に寄せる(<see cref="AbutBodyAlong"/> と札の front)だけだと、二棟の留めの点どうしに 0.0013m 残った
    /// (土井 頂点13 E12_N03 × E13_N01・第43巡)── 最後に点そのものを Q へ置く。返り値 = 動かした距離[m](札が無ければ NaN)。
    /// 当たる先: 出隅を留めて納める表長屋の全部(土井 頂点13・岡部・松江松平の留め)。</summary>
    public static float SnapMiterJambTo(GameObject go, bool right, Vector2 q)
    {
        var path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        var sp = string.IsNullOrEmpty(path) ? null : EdoPartSpec.Get(path);
        if (sp == null || sp.jambL == null || sp.jambR == null) return float.NaN;
        Vector2 w = EdoPartSpec.W(go.transform, right ? sp.jambR.x : sp.jambL.x, sp.front), dv = q - w;
        go.transform.position += new Vector3(dv.x, 0f, dv.y);
        return dv.magnitude;
    }

    /// <summary>出隅で出会う二棟の**留めた端の札 jamb の外面の点**(局所 x = jamb.x・z = front)どうしの距離[m](0 = 外隅 Q で閉じている)。
    /// <paramref name="aRight"/> = a の留めた端が +X 端か。札が無ければ NaN。</summary>
    public static float MiterCornerGap(GameObject a, bool aRight, GameObject b, bool bRight)
    {
        Func<GameObject, bool, Vector2> pt = (go, right) =>
        {
            var path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
            var sp = string.IsNullOrEmpty(path) ? null : EdoPartSpec.Get(path);
            if (sp == null || sp.jambL == null || sp.jambR == null) return new Vector2(float.NaN, float.NaN);
            return EdoPartSpec.W(go.transform, right ? sp.jambR.x : sp.jambL.x, sp.front);
        };
        Vector2 pa = pt(a, aRight), pb = pt(b, bRight);
        return float.IsNaN(pa.x) || float.IsNaN(pb.x) ? float.NaN : Vector2.Distance(pa, pb);
    }

    // ───────────────────────────── 直角でない出隅は最初から留めて建てる(既定の型・docs/oki-kata.md §2a・施主指示 2026-10-16・EDO-0502)
    //  外周の長屋が区画の線の折れで出会う所は、二棟とも角の二等分の面で切った版(Own.NagayaOmote2FKutaiMiterCut ほか)で据える【硬】。
    //  ① 既定で留めるか = MiterByDefault(直線でも直角 ±3° でもない折れ)② Q = 据えた二棟の札の外面の線の交点(FaceLineCorner)
    //  ③ 要る長さ = Q から反対の端(隣の棟の躯体の端)⇒ 焼いた版を札で引く(PickMiterCutOrWait)── 無ければ建てず「要る版」を待ちへ
    //  ④ 差し替えて据える(ReplaceWithMiterCut: 札の外面を線へ・留めた端の jamb を Q へ)⑤ 出隅の突き抜け(MiterOverrun)を数える【硬・許容0】
    //  当たる先: 外周の長屋が区画の折れで出会う所すべて(岡部 頂点13〜18・40・41 / 土井 頂点13・15 / 松江松平の外周)。
    //            同じ型は練塀・石垣の run の出隅にも要る(練塀は隅の駒 Kado・石垣は PlaceRunCorners が持つ ── 長屋だけが直角のまま重ねていた)。

    /// <summary>直線とみなす折れ[度]・直角とみなす幅[度](90 ± これ)── <see cref="MiterByDefault"/> の既定。</summary>
    public const float MITER_STRAIGHT_DEG = 0.05f, MITER_RIGHT_TOL_DEG = 3f;

    /// <summary>多角形 <paramref name="P"/> の頂点 v の符号付きの折れ[度](走りの向きで左へ折れれば +)。</summary>
    public static float VertexFold(Vector2[] P, int v)
    {
        int n = P.Length;
        Vector2 a = P[((v - 1) % n + n) % n], b = P[(v % n + n) % n], c = P[((v + 1) % n + n) % n];
        Vector2 d1 = b - a, d2 = c - b;
        return Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg;
    }

    /// <summary>頂点 v が**出隅**(区画の外へ角が出る)か ── 多角形の巻き(符号付き面積)と折れの符号で決める。</summary>
    public static bool IsConvexVertex(Vector2[] P, int v)
    {
        float A = 0f; int n = P.Length;
        for (int i = 0; i < n; i++) { var p = P[i]; var q = P[(i + 1) % n]; A += p.x * q.y - q.x * p.y; }
        float f = VertexFold(P, v);
        return A < 0f ? f < 0f : f > 0f;
    }

    /// <summary>**既定で留めるか**(硬い): 折れの大きさ |<paramref name="foldDeg"/>| が直線(≤ <paramref name="minDeg"/>)でも直角(|90 − 折れ| ≤ <paramref name="rightTolDeg"/>)でもなければ留める。
    /// <paramref name="rightTolDeg"/> &lt; 0 なら直角でも留める(土井の表長屋の型 ── 30° 以上の出隅は全部留める)。</summary>
    public static bool MiterByDefault(float foldDeg, float minDeg = MITER_STRAIGHT_DEG, float rightTolDeg = MITER_RIGHT_TOL_DEG)
    {
        float a = Mathf.Abs(foldDeg);
        return a > minDeg && (rightTolDeg < 0f || Mathf.Abs(a - 90f) > rightTolDeg);
    }

    /// <summary>据えた駒の**札の外面の線**(局所 z = front)を世界の平面へ: 点 <paramref name="p"/>(局所 x = 0)・走り <paramref name="dir"/>(局所 +X)・
    /// 外向き <paramref name="outward"/>(局所 +Z)。札が無ければ false。</summary>
    public static bool SpecFrontLine(GameObject go, out Vector2 p, out Vector2 dir, out Vector2 outward)
    {
        p = dir = outward = Vector2.zero;
        var path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        var sp = string.IsNullOrEmpty(path) ? null : EdoPartSpec.Get(path);
        if (sp == null) return false;
        p = EdoPartSpec.W(go.transform, 0f, sp.front);
        dir = (EdoPartSpec.W(go.transform, 1f, sp.front) - p).normalized;
        outward = (EdoPartSpec.W(go.transform, 0f, sp.front + 1f) - p).normalized;
        return true;
    }

    /// <summary>**出隅の突き抜け**[m](硬い・許容0): 駒 <paramref name="a"/> の躯体の帯(底〜+<paramref name="bandHi"/> ── 二階の軒は帯の外・軒は越えてよい 裁定A)の頂点のうち、
    /// **留めの面(角の二等分の線・<paramref name="vtx"/> を通り法線 <paramref name="nTowardB"/>)より相手の側**に在る物が、相手の外面の線(<paramref name="bFront"/> を通り外向き
    /// <paramref name="oB"/>)より外へ出る量の最大。0 以下 = 突き抜けない(−∞ = 相手の側に頂点が無い ── 留めの面で切れている)。躯体が測れなければ NaN。
    /// ⭐ 控えの違う二棟(岡部 頂点14: 1.05 / 0.80)は外面が角で段になる ── それは突き抜けでない(相手の側へ入った頂点だけを数える)。⛔ 外接箱・ピボットで測らない。
    /// 当たる先: 出隅で出会う二棟すべて(留めた版・剪断の版・直角の妻のどれでも同じ物差し)。</summary>
    static string _ovAt = "";
    /// <summary>**出隅の突き抜け**[m](硬い・許容0): 駒 <paramref name="a"/> の躯体の帯(底〜<see cref="EdoPartSpec.BAND_HI"/> ── 庇・二階の軒は帯の外・軒は越えてよい 裁定A)の頂点のうち、
    /// **留めの面(角の二等分の線・<paramref name="vtx"/> を通り法線 <paramref name="nTowardB"/>)より相手の側**に在る物が、**相手 <paramref name="b"/> の同じ高さの外面**
    /// (留めの面から 1.0m 内の相手の躯体の頂点の、外向き <paramref name="oB"/> への最大・高さ 0.05 刻み ── 土台・海鼠の腰の出も相手の形で比べる)より外へ出る量の最大。
    /// その高さに相手の頂点が無ければ相手の札の外面(<paramref name="bFront"/>)で比べる。0 以下 = 突き抜けない(−∞ = 相手の側に頂点が無い ── 留めの面で切れている)。躯体が測れなければ NaN。
    /// ⭐ 控えの違う二棟(岡部 頂点14: 1.05 / 0.80)は外面が角で段になる ── それは突き抜けでない(相手の側へ入った頂点だけを数える)。⛔ 外接箱・ピボットで測らない。
    /// 当たる先: 出隅で出会う二棟すべて(留めた版・剪断の版・直角の妻のどれでも同じ物差し)。</summary>
    public static float MiterOverrun(GameObject a, GameObject b, Vector2 bFront, Vector2 oB, Vector2 vtx, Vector2 nTowardB)
    {
        var pts = BodyExRoof(a.transform, 999999);
        if (pts.Count == 0) return float.NaN;
        float y0 = float.MaxValue; foreach (var p in pts) y0 = Mathf.Min(y0, p.y);
        oB = oB.normalized; nTowardB = nTowardB.normalized;
        // 相手の外面の形(高さ 0.05 刻みの最大の出・留めの面から 1.0m 内)
        var face = new Dictionary<int, float>();
        if (b != null)
            foreach (var p in BodyExRoof(b.transform, 999999))
            {
                var w = new Vector2(p.x, p.z); float t = Vector2.Dot(w - vtx, nTowardB); if (t < -0.05f || t > 1.0f) continue;
                int k = Mathf.FloorToInt(p.y / 0.05f); float dv = Vector2.Dot(w - bFront, oB); float cur;
                if (!face.TryGetValue(k, out cur) || dv > cur) face[k] = dv;
            }
        float worst = float.NegativeInfinity;
        foreach (var p in pts)
        {
            if (p.y > y0 + EdoPartSpec.BAND_HI) continue;
            var w = new Vector2(p.x, p.z);
            if (Vector2.Dot(w - vtx, nTowardB) <= 0.0005f) continue;
            int k = Mathf.FloorToInt(p.y / 0.05f); float ref0 = 0f, f1;
            bool hit = false; foreach (int kk in new[] { k - 1, k, k + 1 }) if (face.TryGetValue(kk, out f1)) { ref0 = hit ? Mathf.Max(ref0, f1) : f1; hit = true; }
            float dv = Vector2.Dot(w - bFront, oB) - (hit ? Mathf.Max(0f, ref0) : 0f);
            if (dv > worst) { worst = dv; _ovAt = "高さ +" + (p.y - y0).ToString("F2") + "・留めの面から " + Vector2.Dot(w - vtx, nTowardB).ToString("F2"); }
        }
        return worst;   // −∞ = 相手の側に頂点が無い
    }

    /// <summary>区画の頂点 v の**留めの面**(角の二等分の線): 通る点 = 頂点・法線 = 辺 v−1 の側から辺 v の側へ(<c>(d_v + d_{v−1}).normalized</c>)。
    /// ⭐ 留めの面は区画の線の角で決まる ── 控え c が棟ごとに違っても、各棟の外面の線とこの線の交わりがその棟の留めた端(外隅)になる(c が同じなら二本の外面の線の交点 Q と同じ)。</summary>
    public static Vector2 MiterPlaneNormal(Vector2[] P, int v)
    {
        int n = P.Length;
        Vector2 dp = (P[(v % n + n) % n] - P[((v - 1) % n + n) % n]).normalized, dn = (P[((v + 1) % n + n) % n] - P[(v % n + n) % n]).normalized;
        return (dn + dp).normalized;
    }

    /// <summary>据えた駒の札の留めた端の外面の点(局所 x = jamb.x・z = front)。<paramref name="right"/> = +X 端。札が無ければ (NaN, NaN)。</summary>
    public static Vector2 MiterJambPoint(GameObject go, bool right)
    {
        var path = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        var sp = string.IsNullOrEmpty(path) ? null : EdoPartSpec.Get(path);
        if (sp == null || sp.jambL == null || sp.jambR == null) return new Vector2(float.NaN, float.NaN);
        return EdoPartSpec.W(go.transform, right ? sp.jambR.x : sp.jambL.x, sp.front);
    }

    /// <summary><see cref="PickMiterCut"/> を引き、**無ければ待ちの一行**(「要る版: 名・θL・θR・長さ」)を返す(硬い ── 伸縮しない・重ねない ⇒ 建てない)。
    /// 札の留めた端(<see cref="SpecMiterCutEnds"/>)が θ の端と合わなければそれも待ち。<paramref name="hint"/> は待ちの末尾に足す焼き方。
    /// ⭐ <paramref name="bothEnds"/> = 両端を留める棟(第144巡・岡部 頂点16 の +0.005): 両端とも相手の留めの面に受けられ、伸び縮みの逃げが無い ⇒
    /// 札の余り(札の長さ − 要る長さ)の行き先は <see cref="ReplaceWithMiterCut"/> が決める ── 長い分は入隅の端が一つだけならそこへ(相手の躯体の中へ埋まる)、
    /// それ以外(両端とも出隅・両端とも入隅・短い分)は両端へ半分ずつ。半分ずつ割る版は |余り| ≤ 2 × <paramref name="endTol"/> でなければ採らない(硬い)。
    /// 入隅の端が一つだけの棟(<paramref name="oneConcave"/>)の長い分は片端の棟と同じ ≤ 0.03。採った後の突き抜け 0 は <see cref="MiterOverrun"/> が硬く測る。
    /// 既定(bothEnds = false)の振る舞いは前のまま(土井)。</summary>
    public static bool PickMiterCutOrWait(Func<float, string> pathOf, float need, string label, float thL, float thR, string hint,
                                          out string path, out float lenSpec, out string wait, bool bothEnds = false, float endTol = 0.001f, bool oneConcave = false)
    {
        wait = null;
        bool got = bothEnds ? PickMiterCut(pathOf, need, out path, out lenSpec, 2f * endTol, oneConcave ? 0.03f : 2f * endTol) : PickMiterCut(pathOf, need, out path, out lenSpec);
        if (got)
        {
            var cut = SpecMiterCutEnds(EdoPartSpec.Get(path));
            // 出隅(θ > 0)の端は背の足が jamb より内へ入る ⇒ 切った端と読める。入隅(θ < 0)は背が長くなる ⇒ 札の足では切った端と読めない(直角の端と同じに見える)
            if (cut[0] == (thL > 0f) && cut[1] == (thR > 0f)) return true;
            wait = label + ": 札の留めた端(−X " + cut[0] + " / +X " + cut[1] + ")が欄の出隅の端と合わない " + path;
            return false;
        }
        if (System.IO.File.Exists(path) && UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
        { wait = label + ": 版 " + System.IO.Path.GetFileNameWithoutExtension(path) + " は焼いてあるが Unity が取り込んでいない(.meta 無し)── AssetDatabase.Refresh と材の remap の後に流し直す ⇒ 今は建てない"; return false; }
        wait = label + ": 要る版 " + System.IO.Path.GetFileNameWithoutExtension(path) + "(θL " + thL.ToString("0.###") + "°・θR " + thR.ToString("0.###")
             + "°・長さ Q〜反対の端 " + need.ToString("F3") + "m・札 " + (float.IsNaN(lenSpec) ? "-" : lenSpec.ToString("F3")) + ")── 伸縮しない・重ねない ⇒ 建てない"
             + (bothEnds ? (oneConcave ? "(両端を留める・入隅の端が一つ ⇒ 札は要る長さ −" + (2f * endTol).ToString("0.####") + "〜+0.03・長い分は入隅の端へ)" : "(両端を留める ⇒ 札は要る長さ ±" + (2f * endTol).ToString("0.####") + " で焼く・余りは両端へ割る)") : "")
             + (string.IsNullOrEmpty(hint) ? "" : " → " + hint);
        return false;
    }

    /// <summary>**据えた駒 <paramref name="old"/> を留めの版 <paramref name="path"/> へ差し替えて据える**(硬い・置き方の4手 ── 固定側は外隅 Q)。
    /// 高さ = 旧い駒の躯体の底(同じ断面)・外面 = 札の front を外面の線(<paramref name="frontP"/>・外向き <paramref name="outward"/>)へ・
    /// 走り = 留めた端の札 jamb を Q へ(<see cref="AbutBodyAlong"/> → <see cref="SnapMiterJambTo"/>)。
    /// ⭐ 両端とも留めるなら lo の Q へ据えた後、hi の jamb の外面の点が qHi を越える量 e(走りの向き・実測)を測り、余りの行き先を決める(第144巡: lo へ合わせ切ると
    /// 余りが全部 hi の端の越えになり、座の違う相手で突き抜け +0.005): 長い分(e &gt; 0)で入隅の端が一つだけ(<paramref name="loConcave"/> ≠ <paramref name="hiConcave"/>)なら
    /// その端へ全部(入隅の越えは相手の躯体の中 ── 埋めて隠す)、それ以外は両端へ半分ずつ。余りの大きさの硬い関門は <see cref="PickMiterCutOrWait"/>(bothEnds)。
    /// 旧い駒は据えた後に消す(⛔ 先に消さない)。返り値 = 据えた駒(失敗 null)。
    /// 当たる先: 両端を留める外周の長屋(岡部 N13_0・N15_0・N16_0・N17_0)── 片端の棟・土井(この関数を呼ばない)は変わらない。</summary>
    public static GameObject ReplaceWithMiterCut(GameObject old, string path, Vector2 frontP, Vector2 d, Vector2 outward,
                                                 bool loMiter, Vector2 qLo, bool hiMiter, Vector2 qHi, bool loConcave = false, bool hiConcave = false)
    {
        var sp = EdoPartSpec.Get(path); if (sp == null || old == null || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) return null;
        var parent = old.transform.parent; string name = old.name;
        float yOld = float.MaxValue; foreach (var p in BodyExRoof(old.transform, 999999)) yOld = Mathf.Min(yOld, p.y);
        var go = Place(path, old.transform.position, old.transform.eulerAngles.y, Vector3.one, parent, name + "__mc");
        if (go == null) return null;
        float yNew = float.MaxValue; foreach (var p in BodyExRoof(go.transform, 999999)) yNew = Mathf.Min(yNew, p.y);
        if (yOld < float.MaxValue && yNew < float.MaxValue) go.transform.position += new Vector3(0f, yOld - yNew, 0f);
        d = d.normalized; outward = outward.normalized;
        Vector3 fw = go.transform.TransformPoint(new Vector3(0f, 0f, sp.front));
        go.transform.position -= new Vector3(outward.x, 0f, outward.y) * Vector2.Dot(new Vector2(fw.x, fw.z) - frontP, outward);
        bool plusXisHi = Vector2.Dot(EdoPartSpec.W(go.transform, 1f, 0f) - EdoPartSpec.W(go.transform, 0f, 0f), d) > 0f;
        if (loMiter)
        {
            AbutBodyAlong(go, frontP, d, Vector2.Dot(qLo - frontP, d), true); SnapMiterJambTo(go, !plusXisHi, qLo);
            if (hiMiter)
            {
                Vector2 jHi = MiterJambPoint(go, plusXisHi);
                if (!float.IsNaN(jHi.x))
                {
                    float e = Vector2.Dot(jHi - qHi, d);
                    float back = e > 0f && loConcave != hiConcave ? (hiConcave ? 0f : e) : 0.5f * e;   // 長い分は入隅の端一つへ・他は半分ずつ
                    go.transform.position -= new Vector3(d.x, 0f, d.y) * back;
                }
            }
        }
        else if (hiMiter) { AbutBodyAlong(go, frontP, d, Vector2.Dot(qHi - frontP, d), false); SnapMiterJambTo(go, plusXisHi, qHi); }
        UnityEngine.Object.DestroyImmediate(old);
        go.name = name;
        return go;
    }

    /// <summary>外周の一棟(<see cref="MiterPerimeterCorners"/> へ渡す): 据えた駒・区画の辺・欄の s(辺の始点からの区画の線の上の距離)・
    /// 留めの版の名の引き方 <c>pathOf(L, thL, thR, 局所 −X 端の世界の点, 局所 +X の世界の向き)</c>(門長屋は −X 端から口の芯を出す)。</summary>
    public class PerimPiece
    {
        public GameObject go; public int edge; public float s0, s1, seat = float.NaN; public string label, hint;
        public Func<float, float, float, Vector2, Vector2, string> pathOf;
    }

    /// <summary>**外周の棟が区画の折れで出会う所を、既定で留めて据える**(docs/oki-kata.md §2a・硬い)。
    /// 頂点 v で、辺 v−1 の終わりの棟 A と辺 v の始めの棟 B が出会い(欄の s が頂点から <paramref name="vtxTol"/> 内)、折れが <see cref="MiterByDefault"/> なら:
    /// 留めの面 = 区画の角の二等分の線(<see cref="MiterPlaneNormal"/>)。棟ごとの外隅 = その棟の札の外面の線と留めの面の交わり(控えが違えば外面は角で段になる)。
    /// 棟ごとに留める端(片方か両方)の θ と、要る長さ(外隅から反対の端 = 同じ辺の隣の棟の躯体の端・無ければ自分の端)で版を引き(<see cref="PickMiterCutOrWait"/>)、
    /// あれば差し替える(<see cref="ReplaceWithMiterCut"/>)。その後に頂点ごとに突き抜け(<see cref="MiterOverrun"/> 両向き)と、切った版なら留めた端の外面の点が
    /// 留めの面に載るか(離れ ≤ 0.001)を測り、**超えれば切った版でない棟を消す(建てない・重ねない)**── 剪断で留めた版(_m)は測って 0 なら据えたまま(⚠)。
    /// θ は全角[度]・入隅は負。返り値 = 刷る文。<paramref name="overrunBad"/> = 突き抜けが許容を超えた頂点の数。
    /// 当たる先: 岡部の外周の長屋(頂点13〜18・40・41)・類型ビルダーの外周の長屋・松江松平の外周。土井は表長屋の据えで同じ部品(MiterByDefault・PickMiterCutOrWait・MiterOverrun)を呼ぶ。</summary>
    public static string MiterPerimeterCorners(Vector2[] P, List<PerimPiece> pcs, List<string> wait, out int overrunBad, out float worstOverrun,
                                               float minDeg = MITER_STRAIGHT_DEG, float rightTolDeg = MITER_RIGHT_TOL_DEG, float vtxTol = 0.01f, float tol = 0.001f)
    {
        overrunBad = 0; worstOverrun = float.NegativeInfinity;
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        int n = P.Length;
        Func<int, float> elen = e => Vector2.Distance(P[(e % n + n) % n], P[((e + 1) % n + n) % n]);
        Func<int, Vector2> edir = e => (P[((e + 1) % n + n) % n] - P[(e % n + n) % n]).normalized;
        pcs.RemoveAll(x => x == null || x.go == null || !x.go.activeInHierarchy);
        // ── 頂点ごとの出会い { v, A, B, foldDeg, convex, 留めの面の法線(A→B) }
        var corners = new List<object[]>();
        for (int v = 0; v < n; v++)
        {
            int ep = (v - 1 + n) % n;
            PerimPiece A = null, B = null;
            foreach (var x in pcs) { if (x.edge == ep && x.s1 >= elen(ep) - vtxTol) A = x; if (x.edge == v && x.s0 <= vtxTol) B = x; }
            if (A == null || B == null || A == B) continue;
            float f = VertexFold(P, v);
            if (!MiterByDefault(f, minDeg, rightTolDeg)) continue;
            // 留めの面の通る点: 二棟の札の外面の線の交点 Q(外面が角で段なく閉じる)。控えが違い、Q が頂点の二等分の線から控え c より離れる(浅い折れ ──
            // 岡部 頂点14: 控え 1.05 / 0.80・折れ 3.4° で Q が頂点から 4.3m)なら頂点を通る(外面は角で控えの差だけ段になる)
            Vector2 nn = MiterPlaneNormal(P, v), X = P[v]; string via = "頂点";
            Vector2 pa, da, oa, pb, db, ob;
            if (SpecFrontLine(A.go, out pa, out da, out oa) && SpecFrontLine(B.go, out pb, out db, out ob))
            {
                Vector2 q = FaceLineCorner(pa, da, oa, 0f, pb, db, ob, 0f);
                float cMax = Mathf.Max(Mathf.Abs(Vector2.Dot(P[v] - pa, oa)), Mathf.Abs(Vector2.Dot(P[v] - pb, ob)));
                if (!float.IsNaN(q.x) && Mathf.Abs(Vector2.Dot(q - P[v], nn)) <= cMax) { X = q; via = "外面の線の交点"; }
            }
            corners.Add(new object[] { v, A, B, f, IsConvexVertex(P, v), nn, X, via });
        }
        if (corners.Count == 0) return "出隅の留め: 留める頂点なし";
        // 棟の外面の線と留めの面の交わり(その棟の外隅)
        Func<object[], GameObject, Vector2> cornerOf = (c, go) =>
        {
            Vector2 fp, fd, fo; if (!SpecFrontLine(go, out fp, out fd, out fo)) return new Vector2(float.NaN, float.NaN);
            Vector2 nn = (Vector2)c[5]; Vector2 bis = new Vector2(-nn.y, nn.x);
            return FaceLineCorner(fp, fd, fo, 0f, (Vector2)c[6], bis, nn, 0f);
        };
        // ── 棟ごとに留める端と版を引く
        var cutDone = new HashSet<PerimPiece>(); var lacking = new Dictionary<PerimPiece, string>();
        var touched = new List<PerimPiece>();
        foreach (var c in corners) foreach (var x in new[] { (PerimPiece)c[1], (PerimPiece)c[2] }) if (!touched.Contains(x)) touched.Add(x);
        foreach (var x in touched)
        {
            object[] lo = null, hi = null;
            foreach (var c in corners) { if (c[2] == x) lo = c; if (c[1] == x) hi = c; }
            Vector2 fp, fd, fo; if (!SpecFrontLine(x.go, out fp, out fd, out fo)) { lacking[x] = x.label + ": 札が無く外面の線が測れない"; continue; }
            Vector2 d = edir(x.edge);
            var span = SpecBodySpanAlong(x.go, fp, d);
            if (float.IsNaN(span.x)) { lacking[x] = x.label + ": 札が無く躯体の端が測れない"; continue; }
            float sLo = span.x, sHi = span.y;
            foreach (var y in pcs)
            {
                if (y == x || y.edge != x.edge) continue;
                var ys = SpecBodySpanAlong(y.go, fp, d); if (float.IsNaN(ys.x)) continue;
                if (lo == null && Mathf.Abs(y.s1 - x.s0) <= 0.30f) sLo = ys.y;
                if (hi == null && Mathf.Abs(y.s0 - x.s1) <= 0.30f) sHi = ys.x;
            }
            Vector2 qLo = Vector2.zero, qHi = Vector2.zero; float thLo = 0f, thHi = 0f;
            if (lo != null) { qLo = cornerOf(lo, x.go); sLo = Vector2.Dot(qLo - fp, d); float f = Mathf.Abs((float)lo[3]); thLo = (bool)lo[4] ? f : -f; }
            if (hi != null) { qHi = cornerOf(hi, x.go); sHi = Vector2.Dot(qHi - fp, d); float f = Mathf.Abs((float)hi[3]); thHi = (bool)hi[4] ? f : -f; }
            if (float.IsNaN(sLo) || float.IsNaN(sHi)) { lacking[x] = x.label + ": 外面の線が留めの面と交わらない"; continue; }
            Vector2 xDir = (EdoPartSpec.W(x.go.transform, 1f, 0f) - EdoPartSpec.W(x.go.transform, 0f, 0f)).normalized;
            bool plusXisHi = Vector2.Dot(xDir, d) > 0f;
            float thL = plusXisHi ? thLo : thHi, thR = plusXisHi ? thHi : thLo;
            float need = sHi - sLo;
            float sFixLo = sLo, sFixHi = sHi; bool loFixed = lo != null;
            Func<float, string> pathOf = L =>
            {
                float a = loFixed ? sFixLo : sFixHi - L, b = loFixed ? sFixLo + L : sFixHi;
                Vector2 left = fp + d * (plusXisHi ? a : b);
                return x.pathOf(L, thL, thR, left, xDir);
            };
            string seatNote = "";
            foreach (var c in new[] { lo, hi })
            {
                if (c == null) continue; var o = (PerimPiece)(c == lo ? c[1] : c[2]);
                if (!float.IsNaN(x.seat) && !float.IsNaN(o.seat) && Mathf.Abs(x.seat - o.seat) > 0.001f)
                    seatNote += "・頂点" + c[0] + " の相手 " + o.label + " と座が違う(" + x.seat.ToString("F2", inv) + " / " + o.seat.ToString("F2", inv) + " ── 屋根の継ぎ方は部材方)";
            }
            string path, w; float lenSpec;
            bool loCc = lo != null && !(bool)lo[4], hiCc = hi != null && !(bool)hi[4];
            if (PickMiterCutOrWait(pathOf, need, x.label, thL, thR, x.hint, out path, out lenSpec, out w, lo != null && hi != null, tol, loCc != hiCc))
            {
                var ng = ReplaceWithMiterCut(x.go, path, fp, d, fo, lo != null, qLo, hi != null, qHi, loCc, hiCc);
                if (ng == null) { lacking[x] = x.label + ": 留めの版を据えられない " + path; continue; }
                x.go = ng; cutDone.Add(x);
                sb.Append("  ⭕ " + x.label + ": 留めの版 " + System.IO.Path.GetFileNameWithoutExtension(path) + "(札 " + lenSpec.ToString("F3", inv) + "・要る " + need.ToString("F3", inv) + ")" + seatNote + "\n");
            }
            else lacking[x] = w + seatNote;
        }
        // ── 頂点ごとの突き抜けと留めの面への載り(硬い)── 超えれば切った版でない棟を建てない
        var drop = new HashSet<PerimPiece>();
        foreach (var c in corners)
        {
            int v = (int)c[0]; var A = (PerimPiece)c[1]; var B = (PerimPiece)c[2]; Vector2 nn = (Vector2)c[5];
            if (A.go == null || B.go == null) continue;
            Vector2 pa, da, oa, pb, db, ob; SpecFrontLine(A.go, out pa, out da, out oa); SpecFrontLine(B.go, out pb, out db, out ob);
            Vector2 X = (Vector2)c[6];
            float ab = MiterOverrun(A.go, B.go, pb, ob, X, nn); string atAB = _ovAt; float ba = MiterOverrun(B.go, A.go, pa, oa, X, -nn); string atBA = _ovAt;
            bool measured = !float.IsNaN(ab) && !float.IsNaN(ba);
            float ov = measured ? Mathf.Max(ab, ba) : float.NaN;
            // 切った版の留めた端の外面の点が留めの面に載るか(A の留めた端 = 辺 v−1 の走りの hi 端・B = 辺 v の lo 端)。
            // 符号付き: 正 = 留めの面の手前で止まる(口・硬い)/ 負 = 面を越えて相手へ入る(めり込み ── 埋めて隠す・数えない)。両端を留めた棟は長さの 0.01 の丸めが後の端に出る
            float off = float.NaN;
            foreach (var x in new[] { A, B })
            {
                if (!cutDone.Contains(x)) continue;
                bool hiEnd = x == A; Vector2 dx = edir(x.edge);
                bool plusXisHi = Vector2.Dot(EdoPartSpec.W(x.go.transform, 1f, 0f) - EdoPartSpec.W(x.go.transform, 0f, 0f), dx) > 0f;
                Vector2 jp = MiterJambPoint(x.go, hiEnd == plusXisHi);
                float o2 = (x == A ? -1f : 1f) * Vector2.Dot(jp - X, nn); off = float.IsNaN(off) ? o2 : Mathf.Max(off, o2);
            }
            bool shearA = IsShearMiter(A.go), shearB = IsShearMiter(B.go);
            bool okOv = measured && ov <= tol, okOff = float.IsNaN(off) || off <= tol;
            if (measured && ov > worstOverrun) worstOverrun = ov;
            bool okKind = (cutDone.Contains(A) || shearA) && (cutDone.Contains(B) || shearB);
            bool ok = okOv && okOff && okKind;
            if (!okOv) overrunBad++;
            string mk = ok ? (cutDone.Contains(A) && cutDone.Contains(B) ? "⭕" : "⚠") : "✗";
            sb.Append("  " + mk + " 出隅の留め 頂点" + v + "(" + A.label + " × " + B.label + "・折れ " + ((float)c[3]).ToString("0.###", inv) + "°・" + ((bool)c[4] ? "出隅" : "入隅")
                    + "): 突き抜け " + (!measured ? "測れない" : float.IsNegativeInfinity(ov) ? "なし(相手の側に頂点が無い)" : ov.ToString("+0.000;-0.000", inv) + "m")
                    + (measured && !float.IsNegativeInfinity(ov) ? "(" + A.label.Replace("表長屋 ", "") + "→相手 " + (float.IsNegativeInfinity(ab) ? "なし" : ab.ToString("+0.000;-0.000", inv) + "@" + atAB) + " / "
                       + B.label.Replace("表長屋 ", "") + "→相手 " + (float.IsNegativeInfinity(ba) ? "なし" : ba.ToString("+0.000;-0.000", inv) + "@" + atBA) + ")" : "")
                    + (float.IsNaN(off) ? "" : "・留めた端の口(正)/めり込み(負) " + off.ToString("+0.0000;-0.0000", inv) + "m")
                    + "・留めの面は" + c[7] + "を通る・控えの差 " + Mathf.Abs(Vector2.Dot(pb - P[v], ob) - Vector2.Dot(pa - P[v], oa)).ToString("F3", inv) + "m"
                    + "・版 " + Kind(A, cutDone, shearA) + " / " + Kind(B, cutDone, shearB) + "\n");
            if (!ok)
                foreach (var x in new[] { A, B })
                {
                    bool cut = cutDone.Contains(x);
                    if (cut ? !(okOv && okOff) : !(IsShearMiter(x.go) && okOv && okOff)) drop.Add(x);
                }
        }
        foreach (var x in drop)
        {
            string why; if (!lacking.TryGetValue(x, out why)) why = x.label + ": 出隅で突き抜け・留めの面からの離れが許容 0 を超える";
            wait.Add("出隅の留め " + why + " ⇒ 建てない(重ねて据えない)");
            sb.Append("  ✗ " + x.label + ": 建てない(" + why + ")\n");
            UnityEngine.Object.DestroyImmediate(x.go); x.go = null;
        }
        foreach (var kv in lacking) if (!drop.Contains(kv.Key)) sb.Append("  ⚠ " + kv.Value + "(剪断の留めの版で突き抜け 0 ⇒ 据えたまま)\n");
        return "出隅の留め: 頂点 " + corners.Count + "・切った版 " + cutDone.Count + "・建てない " + drop.Count + "・突き抜けの超え " + overrunBad
             + "・突き抜け 最悪 " + (float.IsNegativeInfinity(worstOverrun) ? "なし" : worstOverrun.ToString("+0.000;-0.000", inv) + "m") + "\n" + sb;
    }

    static string Kind(PerimPiece x, HashSet<PerimPiece> cut, bool shear) { return cut.Contains(x) ? "切った留め" : (shear ? "剪断の留め" : "直角の妻"); }

    /// <summary>据えた駒が剪断で留めた版(名の末尾 `_kutai_m&lt;L&gt;x&lt;R&gt;` ── <c>EdoAssets.Own.NagayaOmote2FKutaiMiter</c>)か。切った版(`_mc`)は含まない。</summary>
    public static bool IsShearMiter(GameObject go)
    {
        if (go == null) return false;
        var p = UnityEditor.PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go) ?? "";
        return System.Text.RegularExpressions.Regex.IsMatch(System.IO.Path.GetFileNameWithoutExtension(p), @"_kutai_m-?\d+x-?\d+$");
    }

    /// <summary>**長屋・門長屋の土台の底(当たり)を、足の下の基壇の天端 <paramref name="crest"/> へ据える**(高さだけ・硬い ±0.001)。
    /// 当たり = 躯体の外面の帯(外面の線 <paramref name="frontLine"/> から奥へ 0.3m・<see cref="Body"/> の全頂点)の最下点。
    /// 走り <paramref name="along"/> の区間 [<paramref name="skipLo"/>, <paramref name="skipHi"/>](<paramref name="frontLine"/> からの s)は除く ──
    /// 扉と方立が敷居まで下がる門長屋の口(札の passage・<c>--gate-drop</c>)は天端の下へ出るのが正しい。
    /// ⛔ 外接箱の底(<see cref="SeatBottom"/>)で据えない ── 口の扉の下端を天端に載せ、土台が 0.70m 浮いた。
    /// 返り値 = 据える前の 当たり − 天端[m](NaN = 帯に頂点が無い)。
    /// 当たる先: 基壇の天端に載る口つきの長屋(土井 通用門 E13_N09・表門)。口の無い長屋は skipLo &gt; skipHi で同じ。</summary>
    public static float SeatBedOnCrest(GameObject go, float crest, Vector2 frontLine, Vector2 outward, Vector2 along, float skipLo, float skipHi)
    {
        return SeatBedOnCrest(go, crest, frontLine, outward, along, new List<Vector2> { new Vector2(skipLo, skipHi) });
    }

    /// <summary><see cref="SeatBedOnCrest(GameObject,float,Vector2,Vector2,Vector2,float,float)"/> の、除く区間が幾つもある版
    /// (長屋門の扉口と潜戸 ── どちらも敷居が土台の底より下がる)。当たる先: 土井の表門(EDO-0533)・潜戸を切り下げた長屋門の全部。</summary>
    public static float SeatBedOnCrest(GameObject go, float crest, Vector2 frontLine, Vector2 outward, Vector2 along, List<Vector2> skips)
    {
        outward = outward.normalized; along = along.normalized;
        float bed = float.MaxValue;
        foreach (var v in Body(go.transform, 999999))
        {
            var q = new Vector2(v.x, v.z) - frontLine;
            float t = Vector2.Dot(q, outward); if (t > 0.01f || t < -0.3f) continue;
            float s = Vector2.Dot(q, along); bool skip = false;
            foreach (var k in skips) if (s >= k.x && s <= k.y) { skip = true; break; }
            if (skip) continue;
            bed = Mathf.Min(bed, v.y);
        }
        if (bed == float.MaxValue) return float.NaN;
        go.transform.position += new Vector3(0f, crest - bed, 0f);
        return bed - crest;
    }

    /// <summary>**地形なりの板柵を、板ごとに弦へ張る**(硬い・浮き 0 / 隙 0)。辺 a→b を描かれた地表の道のりで割り
    /// (<see cref="GroundPolyline"/>)、継ぎ目から継ぎ目へ <see cref="PlaceOnChordMeasured"/> で剪断して張る ── 柱は鉛直のまま、
    /// 板の下端が地表なりに下り、隣の板とは継ぎ目で同じ高さ(段違い 0・継ぎ目の口 0)。
    /// 足元は部材の根入れ(<see cref="RunMeasureY"/>.Root)だけ地表の下へ沈める(継ぎ目の均しの上限も同じ値)。
    /// <para>由来: 2026-10-03 岡部の汀の木柵(辺25・80.6m)。水平の板を 1 枚ずつ地表へ下ろして据えていたので、斜面で隣と最大 2.22m の
    /// 段違い・板の端 21 枚が最大 2.30m 浮き・ピッチと実寸の差で継ぎ目が 0.014m ずつ開いた。</para>
    /// 返すのは張った駒(端の杭は呼び手が末の継ぎ目に立てる ── <paramref name="lastJoint"/>)。
    /// <paramref name="latLine"/> = 板の厚みの中央を置く、<paramref name="outward"/> への射影(区画の線の上なら線の射影)。
    /// 当たる先: 地形なりに走る板柵・板塀のうち、天端(seat)を持たない物(岡部の汀の木柵 F_Hori)。</summary>
    /// <summary><see cref="ChordFenceRun"/> の最後の走りの、収めた後の浮きの最悪と継ぎ目の最深の沈め[m](刷る用)。</summary>
    public static float LastChordFloat, LastChordDeepest;

    public static List<GameObject> ChordFenceRun(string path, Vector2 a, Vector2 b, Vector2 outward, float latLine,
                                                 Transform parent, string prefix, int startIndex, out Vector3 lastJoint)
    {
        var made = new List<GameObject>();
        float span = RunMeasure(path).W;
        float root = RunMeasureY(path).Root;
        var js = GroundPolyline(a, b, span, root, root * 2f);
        if (js.Count < 2) { lastJoint = new Vector3(b.x, Ground(b.x, b.y), b.y); return made; }
        // 足元(部材の最下点)を根入れぶん地表の下へ
        for (int k = 0; k < js.Count; k++) js[k] = js[k] - Vector3.up * root;
        // 板ごとの浮きは RootChordRun が継ぎ目を下げて収める(横断勾配で厚みの低い側が浮く所も・根入れの上限 CHORD_ROOT_MAX)
        float wf, deep;
        made = RootChordRun(js, (k, j0, j1) =>
        {
            bool fwd = ChordFacing(j0, j1, outward);
            var go = fwd ? PlaceOnChordMeasured(path, j0, j1, outward, latLine, 1f, parent, prefix + "_" + (startIndex + k))
                         : PlaceOnChordMeasured(path, j1, j0, outward, latLine, 1f, parent, prefix + "_" + (startIndex + k));
            return go != null ? new List<GameObject> { go } : new List<GameObject>();
        }, out wf, out deep);
        LastChordFloat = wf; LastChordDeepest = deep;
        lastJoint = js[js.Count - 1] + Vector3.up * root;
        return made;
    }
}
