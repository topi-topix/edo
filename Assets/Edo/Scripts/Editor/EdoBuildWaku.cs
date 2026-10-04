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

public static partial class EdoBuild
{
    /// <summary>**受けの駒の上へ据える**(石垣の天端に載る塀・長屋)。<paramref name="go"/> の実メッシュの頂点のうち、真下に受けの駒
    /// (<paramref name="beds"/> の局所の箱の中)がある物だけで「頂点 − 受けの天端」を取り、その最小が −<paramref name="embed"/>(根入れ)になる高さへ
    /// 鉛直に動かす。受けの無い頂点(門の口の下へ垂れる扉・石垣の端の外へ出る端)は数えない ── ⛔ 底(bounds.min)で据えない。
    /// 返り値 = 動かした量[m](受けに一つも載らなければ NaN・動かさない)。
    /// 当たる先: 石垣の基壇に載る練塀(斜面の run は駒ごとに受けの段が違う)・長屋門(扉が敷居まで垂れる)── 松江松平の外周。</summary>
    public static float SeatOnBeds(GameObject go, IList<Transform> beds, float embed, out int nOn)
    { return SeatOnBeds(go, beds, embed, float.NegativeInfinity, out nOn); }
    /// <summary><paramref name="minLocalY"/> より下(駒の局所 Y)の頂点は数えない ── 札が「土台の底 = 局所 0」と宣言し、その下へ垂れる物
    /// (長屋門の扉は敷居まで垂れる)を持つ駒に使う。</summary>
    public static float SeatOnBeds(GameObject go, IList<Transform> beds, float embed, float minLocalY, out int nOn)
    {
        nOn = 0;
        if (go == null || beds == null || beds.Count == 0) return float.NaN;
        var gb = RB(go);
        var boxes = new List<KeyValuePair<Transform, Vector4>>(); var tops = new List<float>();
        foreach (var bt in beds)
        {
            var rb = RB(bt.gameObject);
            if (rb.max.x < gb.min.x - 0.5f || rb.min.x > gb.max.x + 0.5f || rb.max.z < gb.min.z - 0.5f || rb.min.z > gb.max.z + 0.5f) continue;
            var inv = bt.worldToLocalMatrix; Vector3 lo = Vector3.one * 1e9f, hi = -Vector3.one * 1e9f; float top = float.MinValue;
            foreach (var v in Body(bt, 600)) { var l = inv.MultiplyPoint3x4(v); lo = Vector3.Min(lo, l); hi = Vector3.Max(hi, l); top = Mathf.Max(top, v.y); }
            boxes.Add(new KeyValuePair<Transform, Vector4>(bt, new Vector4(lo.x, lo.z, hi.x, hi.z))); tops.Add(top);
        }
        if (boxes.Count == 0) return float.NaN;
        float best = float.MaxValue;
        var g2l = go.transform.worldToLocalMatrix;
        foreach (var v in Body(go.transform, 6000))
        {
            if (!float.IsNegativeInfinity(minLocalY) && g2l.MultiplyPoint3x4(v).y < minLocalY) continue;
            float sup = float.MinValue;
            for (int i = 0; i < boxes.Count; i++)
            {
                var l = boxes[i].Key.worldToLocalMatrix.MultiplyPoint3x4(v); var b = boxes[i].Value;
                // 受けの箱の縁から 0.25m 内だけを受けと読む ── 門の口へ垂れる扉の頂点が石の端の上に掛かると、扉の下端を土台と取り違えて駒が浮く(御臺所門 1.9m)
                if (l.x >= b.x + 0.25f && l.x <= b.z - 0.25f && l.z >= b.y + 0.25f && l.z <= b.w - 0.25f) sup = Mathf.Max(sup, tops[i]);
            }
            if (sup == float.MinValue) continue;
            nOn++; best = Mathf.Min(best, v.y - sup);
        }
        if (nOn == 0) return float.NaN;
        float dy = -embed - best;
        go.transform.position += new Vector3(0f, dy, 0f);
        return dy;
    }
}

public static partial class EdoBuild
{
    /// <summary>**溝を折れ線に据える**(1m の駒を流れに沿って並べ、端数は区間の端の1本を切る ── ⛔ 全体を伸縮しない)。
    /// 駒の局所 +X = 流れの向き。高さは駒の**天端を描かれた地表へ**揃える(溝は地面に彫り込む物 ── 触れている箇所 = 天端の縁と地表)。
    /// <paramref name="cover"/>(点 → 石蓋にするか)が真の所は <paramref name="coverPath"/>、<paramref name="skip"/> が真の所(石組みで潜る区間)は据えない。
    /// <paramref name="inv"/>(点ごとの溝底)は狙い ── 据えた駒の下端との差の最大を <paramref name="invDev"/> に返す(柔らかい)。
    /// 当たる先: 指図が pts と inv を持つ溝(松江松平 MZ16/MZ17/MZ18・前庭の雨落ち)。</summary>
    public static List<GameObject> MizoOnPolyline(Transform parent, IList<Vector2> pts, IList<float> inv, string path, string coverPath,
        Func<Vector2, bool> cover, Func<Vector2, bool> skip, string prefix, out float invDev, out int nCover, out int nSkip)
    {
        var made = new List<GameObject>(); invDev = 0f; nCover = 0; nSkip = 0;
        for (int i = 0; i + 1 < pts.Count; i++)
        {
            Vector2 a = pts[i], b = pts[i + 1]; float L = Vector2.Distance(a, b); if (L < 0.05f) continue;
            Vector2 dir = (b - a) / L; float yaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;
            int full = Mathf.FloorToInt(L + 1e-4f); float rem = L - full; int k = full + (rem > 0.05f ? 1 : 0);
            for (int q = 0; q < k; q++)
            {
                float wq = q < full ? 1f : rem;
                Vector2 c = a + dir * (q + wq * 0.5f);
                if (skip != null && skip(c)) { nSkip++; continue; }
                bool cv = cover != null && coverPath != null && cover(c);
                var go = Place(cv ? coverPath : path, new Vector3(c.x, Ground(c.x, c.y), c.y), yaw, Vector3.one, parent, prefix + "_" + i + "_" + q);
                if (go == null) continue;
                if (wq < 0.999f) go.transform.localScale = new Vector3(wq, 1f, 1f);
                // 天端を地表へ(駒の実メッシュの最も高い所 = 天端の縁)
                var rb = RB(go); float g = Ground(c.x, c.y);
                go.transform.position += new Vector3(0f, g - rb.max.y + (cv ? 0.02f : 0f), 0f);
                if (cv) nCover++;
                if (inv != null && inv.Count == pts.Count)
                {
                    float want = Mathf.Lerp(inv[i], inv[i + 1], (q + wq * 0.5f) / L);
                    invDev = Mathf.Max(invDev, Mathf.Abs(RB(go).min.y - want));
                }
                made.Add(go);
            }
        }
        return made;
    }
}

public static partial class EdoBuild
{
    /// <summary>**左右の手を選ぶ**: 駒を局所 X で鏡にした姿と元の姿のうち、足元(下端から <paramref name="band"/> m)の実メッシュが
    /// 区画 <paramref name="parcel"/> の外へ出る量の小さい方を採る(硬い: 区域侵犯 0 に近い方)。返り値 = 採った姿の外へ出る量[m]・mirrored = 鏡にしたか。
    /// 当たる先: 腕の長さが左右で違う隅の駒(隅長屋 NagayaKado / NagayaKadoMonomi)を、焼いた手と逆の隅へ据えるとき(松江松平 P23)。</summary>
    public static float ChooseHandInside(GameObject go, Vector2[] parcel, float band, out bool mirrored)
    {
        mirrored = false;
        Func<float> outAmt = () =>
        {
            var rb = RB(go); float w = 0f;
            foreach (var v in Body(go.transform, 8000)) { if (v.y > rb.min.y + band) continue; var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(parcel, q)) w = Mathf.Max(w, EdoGeom.DistToPolyEdge(parcel, q)); }
            return w;
        };
        float o0 = outAmt();
        var s = go.transform.localScale; go.transform.localScale = new Vector3(-s.x, s.y, s.z);
        float o1 = outAmt();
        if (o1 < o0 - 1e-3f) { mirrored = true; return o1; }
        go.transform.localScale = s; return o0;
    }
}
