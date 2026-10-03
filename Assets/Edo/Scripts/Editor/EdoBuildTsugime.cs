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
