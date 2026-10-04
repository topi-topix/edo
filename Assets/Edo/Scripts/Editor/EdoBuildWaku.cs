// EdoBuild — 多角形の枠を解く・駒を線と面へ寄せる(2026-10-04・EDO-0554 松江松平 起こし直しの第2段)。
// 当たる先: 指図の欄が poly(四角だが格子に対して傾いた枠)で来る棟・附属屋(松江松平の内長屋 Uchi_* 9棟)と、
//   門の通路の返し石垣のように「線の端から決まった長さだけ・面を線に揃えて」積む駒(御臺所門の返し 2本)。
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図を読んでここへ渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**四辺形の枠を解く**(世界 xz の4点)。長い辺の向き <paramref name="axisLong"/>(単位)・長さ <paramref name="len"/>・
    /// 奥行 <paramref name="dep"/>(向かい合う辺の距離の平均)・芯 <paramref name="c"/>(4点の平均)を返す。
    /// 四角からの外れ(対辺の向きの差の最大[°])を返り値にする ── 呼び手は外れが大きければ ⚠ を刷る(柔らかい)。
    /// ⛔ 外接矩形にしない(傾いた枠は外接矩形で 1〜3 割太る)。</summary>
    public static float QuadFrame(IList<Vector2> w, out Vector2 c, out Vector2 axisLong, out float len, out float dep)
    {
        c = Vector2.zero; axisLong = Vector2.right; len = 0f; dep = 0f;
        if (w == null || w.Count != 4) return float.NaN;
        foreach (var p in w) c += p; c /= 4f;
        Vector2 e0 = w[1] - w[0], e1 = w[2] - w[1], e2 = w[3] - w[2], e3 = w[0] - w[3];
        float l02 = (e0.magnitude + e2.magnitude) * 0.5f, l13 = (e1.magnitude + e3.magnitude) * 0.5f;
        Vector2 aL = l02 >= l13 ? (e0.normalized - e2.normalized).normalized : (e1.normalized - e3.normalized).normalized;
        axisLong = aL; len = Mathf.Max(l02, l13);
        Vector2 nrm = new Vector2(-aL.y, aL.x);
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var p in w) { float t = Vector2.Dot(p - c, nrm); mn = Mathf.Min(mn, t); mx = Mathf.Max(mx, t); }
        dep = Mathf.Min(l02, l13);
        float skew = Mathf.Max(Vector2.Angle(e0, -e2), Vector2.Angle(e1, -e3));
        return skew;
    }

    /// <summary>**駒を線と面へ寄せる**(実メッシュで測る・⛔ ピボットで決めない)。据えた駒 <paramref name="go"/> の走り
    /// <paramref name="runDir"/>(単位・世界 xz)方向の実長を <paramref name="runLen"/> へ伸縮し(局所 Z を伸縮 ── 呼び手は局所 Z が走りに
    /// なる向きで据える)、走りの始まり(最小の射影)を <paramref name="startProj"/>、見え面(<paramref name="faceN"/> への射影の最大)を
    /// <paramref name="faceProj"/>、天端(最も高い頂点)を <paramref name="topY"/> へ揃える。硬い: 3つとも誤差 1mm。
    /// 返り値 = 伸縮の倍率(測れなければ NaN・駒は動かさない)。
    /// 当たる先: 門の通路の返し石垣(松江松平 御臺所門 komon.kaeshi)・線の端から決まった長さで止める石垣の駒すべて。</summary>
    public static float SnapPieceToLine(GameObject go, Vector2 runDir, float startProj, float runLen, Vector2 faceN, float faceProj, float topY)
    {
        if (go == null) return float.NaN;
        var b = Body(go.transform, 4000);
        if (b.Count == 0) return float.NaN;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in b) { float t = v.x * runDir.x + v.z * runDir.y; mn = Mathf.Min(mn, t); mx = Mathf.Max(mx, t); }
        float have = mx - mn; if (have < 1e-3f) return float.NaN;
        float k = runLen / have;
        var s = go.transform.localScale; go.transform.localScale = new Vector3(s.x, s.y, s.z * k);
        b = Body(go.transform, 4000);
        float rMin = float.MaxValue, fMax = float.MinValue, yMax = float.MinValue;
        foreach (var v in b)
        {
            rMin = Mathf.Min(rMin, v.x * runDir.x + v.z * runDir.y);
            fMax = Mathf.Max(fMax, v.x * faceN.x + v.z * faceN.y);
            yMax = Mathf.Max(yMax, v.y);
        }
        // 走りと面の法線が直交しない駒でも両方を満たす移動(2本の一次式を解く)
        float dr = startProj - rMin, df = faceProj - fMax;
        float cc = Vector2.Dot(runDir, faceN), den = 1f - cc * cc;
        float a = den > 1e-6f ? (dr - cc * df) / den : dr, bb = den > 1e-6f ? (df - cc * dr) / den : df;
        var mv = runDir * a + faceN * bb;
        go.transform.position += new Vector3(mv.x, topY - yMax, mv.y);
        return k;
    }
}
