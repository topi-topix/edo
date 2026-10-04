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

public static partial class EdoBuild
{
    /// <summary>**区画の辺の鎖から内へ一定の離れで引いた線**(世界 xz)。辺ごとの区間 (edge, s0, s1) を順に渡すと、継ぐ辺どうしは
    /// 内へずらした二本の線の交点で折り、継がない端は区間の端を内へずらした点で止める。内へずらして裏返った(向きが逆になった)
    /// 短い区間は落とす(鋭い隅で線が自分と交わらないように)。当たる先: 区画の線から内へ離して立てる柵・溝(松江松平の谷の境の柵)。</summary>
    public static List<Vector2> InsetChain(Vector2[] parcel, IList<Vector3> spans, float inset, Func<int, Vector2> outNormal)
    {
        int n = parcel.Length;
        Func<int, float, Vector2> at = (e, s) => { Vector2 a = parcel[e % n], b = parcel[(e + 1) % n]; return a + (b - a).normalized * s; };
        var pts = new List<Vector2>();
        for (int i = 0; i < spans.Count; i++)
        {
            int e = (int)spans[i].x; Vector2 inN = -outNormal(e);
            Vector2 a = at(e, spans[i].y) + inN * inset, b = at(e, spans[i].z) + inN * inset, d = (b - a).normalized;
            bool joinPrev = i > 0 && ((int)spans[i - 1].x + 1) % n == e && spans[i].y < 1e-3f;
            if (i == 0 || !joinPrev) pts.Add(a);
            else
            {
                int ep = (int)spans[i - 1].x; Vector2 inP = -outNormal(ep);
                Vector2 pa = at(ep, 0f) + inP * inset, pd = (parcel[(ep + 1) % n] - parcel[ep % n]).normalized;
                pts[pts.Count - 1] = EdoGeom.LineIntersect(pa, pd, a, d, pts[pts.Count - 1]);
            }
            pts.Add(b);
        }
        // 裏返った区間を落とす
        for (int k = pts.Count - 2; k >= 1; k--)
        {
            Vector2 d0 = pts[k] - pts[k - 1], d1 = pts[k + 1] - pts[k];
            if (Vector2.Dot(d0, d1) < -0.9f * d0.magnitude * d1.magnitude) pts.RemoveAt(k);
        }
        return pts;
    }

    /// <summary>**柵を折れ線に張る**(地形なり・1間の駒を描かれた地表の弦へ)。各区間を <see cref="GroundPolyline"/> で <paramref name="span"/> ごとに割り、
    /// <see cref="PlaceOnChordMeasured"/> で弦へ張る(見え面 +Z = <paramref name="faceSide"/> の側)。<paramref name="special"/> の点(世界 xz)に最も近い弦
    /// (芯から 1.5m 以内)は <paramref name="specialPath"/> の駒にする。最後の継ぎ目に端の杭 <paramref name="postPath"/>(+X 面 = 鎖の終わり)。
    /// 返り値 = 据えた駒。当たる先: 控柱つきの木柵(松江松平 谷の境 F_Tani_*/F_Okabe_*)。</summary>
    public static List<GameObject> FenceOnPolyline(Transform parent, List<Vector2> line, string path, string postPath, string specialPath,
        IList<Vector2> special, Func<Vector2, Vector2> faceSide, float span, float root, string prefix, out int nSpecial)
    {
        var made = new List<GameObject>(); nSpecial = 0;
        var used = new bool[special == null ? 0 : special.Count];
        Vector3 last = Vector3.zero;
        for (int i = 0; i + 1 < line.Count; i++)
        {
            var js = GroundPolyline(line[i], line[i + 1], span, root, root * 2f, 2);
            for (int k = 0; k + 1 < js.Count; k++)
            {
                Vector3 j0 = js[k], j1 = js[k + 1];
                Vector2 mid = new Vector2((j0.x + j1.x) * 0.5f, (j0.z + j1.z) * 0.5f);
                Vector2 outw = faceSide(mid);
                string p = path;
                if (special != null)
                    for (int q = 0; q < special.Count; q++)
                        if (!used[q] && Vector2.Distance(mid, special[q]) < 1.5f) { p = specialPath; used[q] = true; nSpecial++; break; }
                Vector3 a = j0, b = j1;
                if (!ChordFacing(a, b, outw)) { var t = a; a = b; b = t; }
                float lat = Vector2.Dot(mid, outw);
                var go = PlaceOnChordMeasured(p, a, b, outw, lat, 1f, parent, prefix + "_" + made.Count);
                if (go != null) made.Add(go);
                last = j1;
            }
        }
        if (postPath != null && line.Count >= 2)
        {
            Vector2 d = (line[line.Count - 1] - line[line.Count - 2]).normalized, o = faceSide(line[line.Count - 1]);
            float yaw = Mathf.Atan2(o.x, o.y) * Mathf.Rad2Deg;
            var post = Place(postPath, new Vector3(last.x, last.y, last.z), yaw, Vector3.one, parent, prefix + "_Post");
            if (post != null)
            {
                // +X 面を鎖の終わりへ(実メッシュで測る)・足元は描かれた地表へ根入れ
                var bd = Body(post.transform, 2000); float mx = float.MinValue, mnY = float.MaxValue;
                foreach (var v in bd) { mx = Mathf.Max(mx, v.x * d.x + v.z * d.y); mnY = Mathf.Min(mnY, v.y); }
                float sh = Vector2.Dot(new Vector2(last.x, last.z), d) - mx;
                post.transform.position += new Vector3(d.x * sh, Ground(last.x, last.z) - root - mnY, d.y * sh);
                made.Add(post);
            }
        }
        return made;
    }
}
