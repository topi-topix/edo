// EdoBuild — 継ぎ目を躯体の実面で納める(2026-10-03・EDO-0502 岡部の普請検査の差し戻し)。
//  ・一本物の長屋の躯体を走りの区間へ合わせる(妻壁の実面で継ぐ・FitBodyToSpan)
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

    /// <summary>**一本物の長屋の躯体を、走りの区間 [sLo, sHi] へ伸縮して合わせる**(硬い・隙 0 ── 継ぎ目は妻壁の実面で突き付く)。
    /// <para>由来: 2026-10-03 岡部(EDO-0502)。一本物の長屋は呼び寸法 = 破風まで含む全幅で、隣と破風で突き付くよう走りに並べていた。
    /// 妻壁は破風より両端で 0.322m 内へ引っ込むので、継ぎ目ごとに躯体が 0.644m 開き、屋根の下が素通しになった(8 箇所)。
    /// 平行移動だけで躯体を突き付けると、鎖の端に 0.644m × 継ぎ目の数が残り(辺41 で 2.58m)、端の練塀か台の石垣の上に穴が開く。
    /// ⇒ 駒ごとに走りの方向(局所 X)だけを伸縮して、躯体の区間を指図の区間そのものに合わせる。屋根は隣と 0.644m 重なる(部材どうしの
    /// めり込みは数えない ── docs/oki-kata.md §4)。</para>
    /// <para>硬い: 伸縮の量が <paramref name="maxStretch"/>(比)を超えるなら合わせず NaN(呼び手は ★ で刷る)。
    /// 返り値 = 合わせた後の躯体の区間の、狙いからの最大のずれ[m]。<paramref name="stretch"/> = 掛けた比(1 = 伸縮なし)。</para>
    /// 当たる先: 一本物で走りに並べる長屋(岡部の表長屋・帯の長屋・門長屋の脇の棟)。⛔ 門口を持つ駒(門長屋)には掛けない ── 口の幅と芯が動く。</summary>
    public static float FitBodyToSpan(GameObject go, Vector2 origin, Vector2 along, float sLo, float sHi,
                                      float maxStretch, out float stretch)
    {
        stretch = 1f;
        along = along.normalized;
        var sp = BodySpanAlong(go, origin, along);
        if (float.IsNaN(sp.x)) return float.NaN;
        float want = sHi - sLo, have = sp.y - sp.x;
        if (have < 0.5f || want < 0.5f) return float.NaN;
        float k = want / have;
        if (Mathf.Abs(k - 1f) > maxStretch) { stretch = k; return float.NaN; }
        // 局所 X(走り)だけを伸縮 → 区間の始まりを sLo へ平行移動(2 巡: 伸縮はピボットの周りで効く)
        var sc = go.transform.localScale; go.transform.localScale = new Vector3(sc.x * k, sc.y, sc.z);
        stretch = k;
        for (int it = 0; it < 2; it++)
        {
            sp = BodySpanAlong(go, origin, along);
            float mid = (sp.x + sp.y) * 0.5f, wantMid = (sLo + sHi) * 0.5f;
            go.transform.position += new Vector3(along.x, 0f, along.y) * (wantMid - mid);
        }
        sp = BodySpanAlong(go, origin, along);
        return Mathf.Max(Mathf.Abs(sp.x - sLo), Mathf.Abs(sp.y - sHi));
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
