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
