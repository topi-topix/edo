// 勝手まわり(菜園の畝・自然の斜面に据える踏み段)の置き方 — EdoBuild の partial(2026-10-03・EDO-0532 施主裁定A)
//   ⭐ 規則21: 置く・測る・据えるのはここ。類型ビルダー(EdoTypologyBuilder.Katte.cs)は場所の決め方を渡すだけ。
//   ⛔ 部材の基準点で位置を決めない ── 畝の継ぎは実メッシュの小口(長手の端)を測って突き付け、段石は地表に天端を合わせる。
//   硬い条件(許容0): 畝・段石の下端の浮き(±0.01・浮けば根入れを足す。足しきれない駒は置かない)。
//   柔らかい条件(狙い): 菜園の広さ(最大の矩形)・段の蹴上の揃い(落差/段数 ≈ 蹴上)── 届かなければ ⚠ と実測。
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

public static partial class EdoBuild
{
    /// <summary>菜園の矩形(<paramref name="u"/>・<paramref name="v"/> を軸に、<paramref name="origin"/> からの局所 m)。</summary>
    public class FieldBox { public Vector2 o, u, v; public float x0, x1, z0, z1; public int cells; }

    /// <summary>**軸に揃えた最大の矩形**を格子 <paramref name="cell"/> で探す(ヒストグラム法)。<paramref name="ok"/> が
    /// 格子の升の中心で true を返す升だけを使う(地表の高さ・勾配・区画の縁・棟からの離れは呼び手が渡す)。
    /// 探す範囲は origin から ±<paramref name="reach"/>。升が一つも無ければ null。</summary>
    public static FieldBox FieldRect(Vector2 origin, Vector2 u, Vector2 v, Func<Vector2, bool> ok, float cell, float reach)
    {
        int n = Mathf.CeilToInt(2f * reach / cell);
        var good = new bool[n, n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
            {
                float x = -reach + (i + 0.5f) * cell, z = -reach + (j + 0.5f) * cell;
                good[i, j] = ok(origin + u * x + v * z);
            }
        var h = new int[n];
        int best = 0, bi0 = 0, bi1 = 0, bj0 = 0, bj1 = 0;
        for (int j = 0; j < n; j++)
        {
            for (int i = 0; i < n; i++) h[i] = good[i, j] ? h[i] + 1 : 0;
            var st = new Stack<int>();
            for (int i = 0; i <= n; i++)
            {
                int hi = i < n ? h[i] : 0;
                while (st.Count > 0 && h[st.Peek()] >= hi)
                {
                    int top = st.Pop(); int ht = h[top];
                    int left = st.Count > 0 ? st.Peek() + 1 : 0;
                    int area = ht * (i - left);
                    if (area > best) { best = area; bi0 = left; bi1 = i - 1; bj0 = j - ht + 1; bj1 = j; }
                }
                st.Push(i);
            }
        }
        if (best == 0) return null;
        return new FieldBox
        {
            o = origin, u = u, v = v, cells = best,
            x0 = -reach + bi0 * cell, x1 = -reach + (bi1 + 1) * cell,
            z0 = -reach + bj0 * cell, z1 = -reach + (bj1 + 1) * cell,
        };
    }

    /// <summary>矩形の四隅(世界の XZ)。</summary>
    public static Vector2[] FieldCorners(FieldBox b)
    {
        return new[] { b.o + b.u * b.x0 + b.v * b.z0, b.o + b.u * b.x1 + b.v * b.z0,
                       b.o + b.u * b.x1 + b.v * b.z1, b.o + b.u * b.x0 + b.v * b.z1 };
    }

    /// <summary>**畝を並べる。**矩形の長手に畝を通し、畝間(芯々)<paramref name="pitch"/> で並べる。
    /// 一本の畝は駒(局所 X が長手)を**実メッシュの小口を測って**突き付けで継ぐ(⛔ ピボットの間隔で並べない・規則21)。
    /// 据えは地面に触れる所で着け(<see cref="SeatOnGround"/>・<paramref name="sink"/> 沈め)、下手が浮けば
    /// その分だけ根入れを足す(硬い ±0.01)。足す量が <paramref name="maxBury"/> を超える駒は置かない(⚠ に数える)。</summary>
    public static List<GameObject> LayUne(string path, Transform parent, FieldBox b, float pitch, float sink, float maxBury, out string note)
    {
        var made = new List<GameObject>();
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (prefab == null) { note = "⛔ 畝の駒が無い: " + path; return made; }
        bool alongU = (b.x1 - b.x0) >= (b.z1 - b.z0);
        Vector2 ax = alongU ? b.u : b.v, ac = alongU ? b.v : b.u;
        float a0 = alongU ? b.x0 : b.z0, a1 = alongU ? b.x1 : b.z1, c0 = alongU ? b.z0 : b.x0, c1 = alongU ? b.z1 : b.x1;
        float yaw = Mathf.Atan2(ax.x, ax.y) * Mathf.Rad2Deg - 90f;   // 局所 +X を ax へ
        // 駒の長手と幅を実メッシュで測る(型紙を一度置いて)
        var tmpl = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        tmpl.transform.SetPositionAndRotation(Vector3.zero, Quaternion.Euler(0f, yaw, 0f));
        float lx0 = float.MaxValue, lx1 = float.MinValue, lz0 = float.MaxValue, lz1 = float.MinValue;
        foreach (var w in Body(tmpl.transform, 2000, true))
        {
            var l = tmpl.transform.InverseTransformPoint(w);
            lx0 = Mathf.Min(lx0, l.x); lx1 = Mathf.Max(lx1, l.x); lz0 = Mathf.Min(lz0, l.z); lz1 = Mathf.Max(lz1, l.z);
        }
        UnityEngine.Object.DestroyImmediate(tmpl);
        float len = lx1 - lx0, wid = lz1 - lz0;
        if (len < 0.1f) { note = "⛔ 畝の駒の長手が測れない"; return made; }
        int rows = Mathf.FloorToInt((c1 - c0 - wid) / pitch) + 1, per = Mathf.FloorToInt((a1 - a0) / len);
        float cs = c0 + 0.5f * ((c1 - c0) - (rows - 1) * pitch);    // 畝の芯の並びを矩形の中へ寄せる
        float as0 = a0 + 0.5f * ((a1 - a0) - per * len);              // 一本の畝の頭(小口)
        int dropped = 0; float worstBury = 0f;
        for (int r = 0; r < rows; r++)
            for (int k = 0; k < per; k++)
            {
                // 駒の −X 小口を as0 + k·len に突き付ける(実メッシュの小口 lx0 から位置を解く)
                float ca = as0 + k * len - lx0, cc = cs + r * pitch - 0.5f * (lz0 + lz1);
                var p = b.o + ax * ca + ac * cc;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
                go.name = string.Format("Une_{0:00}_{1:00}", r, k);
                go.transform.SetPositionAndRotation(new Vector3(p.x, Ground(p.x, p.y), p.y), Quaternion.Euler(0f, yaw, 0f));
                try { SeatOnGround(go, sink, 2000); }
                catch (Exception) { UnityEngine.Object.DestroyImmediate(go); dropped++; continue; }
                var rt = RootToBed(go, Ground, 0.05f);
                if (!float.IsNaN(rt.hi) && rt.hi > 0.01f)
                {
                    if (rt.hi > maxBury) { UnityEngine.Object.DestroyImmediate(go); dropped++; continue; }
                    go.transform.position -= new Vector3(0f, rt.hi, 0f);
                    worstBury = Mathf.Max(worstBury, rt.hi);
                }
                made.Add(go);
            }
        note = string.Format("畝 {0} 本 × {1} 駒(長手 {2:F2}m・畝間 芯々 {3:F2}m)= {4} 駒・下手の浮きを根入れで消した最大 {5:F3}m{6}",
                             rows, per, len, pitch, made.Count, worstBury, dropped > 0 ? string.Format("・⚠ 据わらず置かなかった {0}", dropped) : "");
        return made;
    }

    /// <summary>**自然の斜面に段石を据える**(斜面は崩さない・造成しない)。<paramref name="a"/>(上の平場)→ <paramref name="b"/>(下の平場)の
    /// 線の上で地表が落ちる区間(肩〜裾)を測り、落差 / <paramref name="keri"/> 段を肩から裾まで等しい間隔で一続きに置く(段どうしの芯々は
    /// <paramref name="fumi"/> 以上)。段石の +Z = 坂下。据えは天端を地表に合わせて <paramref name="proud"/> だけ出し(<see cref="SeatFlush"/>)、
    /// 下端の浮きは根入れで消す(硬い ±0.01)。<paramref name="blocked"/> が true の所(棟の足元)へは置かない(⚠ に数える)。</summary>
    public static List<GameObject> SlopeSteps(Func<int, string> pathOf, Transform parent, Vector2 a, Vector2 b, float keri, float fumi,
                                              string mat, float proud, Func<Vector2, bool> blocked, out string note)
    {
        var made = new List<GameObject>();
        float L = Vector2.Distance(a, b);
        if (L < 1f) { note = "⚠ 段: 上と下の平場が近すぎる"; return made; }
        var dir = (b - a) / L;
        // 地表を 0.1m 刻みで引き、上の平場の高さから下の平場の高さへ落ちる区間を採る
        var hs = new List<float>(); for (float s = 0f; s <= L; s += 0.1f) hs.Add(Ground(a.x + dir.x * s, a.y + dir.y * s));
        float top = hs[0], bot = hs[hs.Count - 1];
        float drop = top - bot;
        if (drop < keri) { note = string.Format("段: 落差 {0:F2}m が蹴上に届かない ── 段は要らない", drop); return made; }
        int n = Mathf.Max(1, Mathf.RoundToInt(drop / keri));
        float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
        // ⭐ 段は**斜面の肩から裾まで等しい間隔**で一続きに置く(2026-10-03)── ⛔ 段ごとに「地表がその段の高さを横切る所」へ置くと、
        //    裾の緩い所で最後の段だけ 1m 離れて落ちた。肩 = 上の平場から 0.05m 落ちた所・裾 = 下の平場まで 0.05m の所。
        int k0 = hs.FindIndex(h => h < top - 0.05f), k1 = hs.FindIndex(h => h <= bot + 0.05f);
        if (k0 < 0 || k1 <= k0) { note = "⚠ 段: 斜面の肩と裾が測れない"; return made; }
        float sA = k0 * 0.1f, sB = k1 * 0.1f, pitch = Mathf.Max(fumi, (sB - sA) / n);
        float sMid = 0.5f * (sA + sB), sFirst = sMid - pitch * (n - 1) * 0.5f;   // 走りが斜面より長ければ肩と裾へ等しく出す
        int skipped = 0; float worstBury = 0f;
        for (int i = 0; i < n; i++)
        {
            float s = sFirst + pitch * i;
            var p = a + dir * s;
            if (blocked != null && blocked(p)) { skipped++; continue; }
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(pathOf(i));
            if (prefab == null) { note = "⛔ 段石の駒が無い: " + pathOf(i); return made; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.name = "Danishi_" + i.ToString("00");
            go.transform.SetPositionAndRotation(new Vector3(p.x, Ground(p.x, p.y), p.y), Quaternion.Euler(0f, yaw, 0f));
            float rise;
            try { SeatFlush(go, mat, proud, out rise); }
            catch (Exception) { SeatOnGround(go, 0f, 2000); }
            var rt = RootToBed(go, Ground, 0.05f);
            if (!float.IsNaN(rt.hi) && rt.hi > 0.01f) { go.transform.position -= new Vector3(0f, rt.hi, 0f); worstBury = Mathf.Max(worstBury, rt.hi); }
            made.Add(go);
        }
        float s0 = sFirst, s1 = sFirst + pitch * (n - 1);
        note = string.Format("段石 {0}/{1} 段(落差 {2:F2}m・蹴上の狙い {3:F2}m → 実 {4:F2}m・走り {5:F1}m(段の間 {8:F2}m)・下手の浮きを根入れで消した最大 {6:F3}m){7}",
                             made.Count, n, drop, keri, drop / n, s1 - s0 + pitch, worstBury,
                             skipped > 0 ? string.Format("・⚠ 棟の足元で置かなかった {0}", skipped) : "", pitch);
        return made;
    }

    /// <summary>**踏面の高さが決まっている石段を、造成後の斜面へ据える**(2026-10-04・EDO-0533 土井 K_Kura1)。
    /// <paramref name="tops"/> = 段ごとの踏面の天端(下から・指図の y0 + 蹴上 × 段)。<paramref name="b"/>(下の面)→ <paramref name="a"/>(上の面)の線の上で、
    /// **地表がその段の天端を横切る所**へ段の踏面の**坂上の端**を当て(地表を 0.05m 刻みで引く・天端の 0.05m 下で横切りとみなす ── 2m 格子の造成は上の面の縁で 0.02〜0.04 下がる)、前の段から <paramref name="fumi"/> 未満なら fumi へ送る ──
    /// 踏面の下は全部地表より上・段鼻の前は蹴上の見え(地表は段の胴 = 蹴上の面が受ける)。⛔ 踏面の中ほどを交点へ当てると踏面の背に地表が 0.31m 被った(同日)。
    /// 天端は踏面の材 <paramref name="mat"/> の上面の帯(<see cref="FlushGap"/> と同じ測り)を tops[i] へ、下端の浮きは根入れで消す(硬い ±0.01)。
    /// ⛔ <see cref="SlopeSteps"/>(段を肩から裾へ等間隔・天端を地表へ)で据えると、2m 格子の造成の均した坂で段の差が 0.45/0.17/0.21/0.24 に割れた
    /// (欄の蹴上 0.275)── 蹴上は欄が決め、踏面の位置を地表で測る。段石の +Z = 坂下。返り値の註に段ごとの天端・段の間・踏面の背に被る地表の最悪を刷る。
    /// 当たる先: 指図が段数・蹴上・天端を名乗る土の斜面の石段(土井 kaidans・今後の各邸の邸内の石段で袖の無い物)。</summary>
    public static List<GameObject> SlopeStepsAt(Func<int, string> pathOf, Transform parent, Vector2 a, Vector2 b, IList<float> tops, float fumi,
                                                string mat, out string note)
    {
        var made = new List<GameObject>();
        float L = Vector2.Distance(a, b);
        if (L < 0.5f || tops.Count == 0) { note = "⚠ 段: 線が短いか段が無い"; return made; }
        var up = (a - b) / L;                                    // 坂上へ
        float yaw = Mathf.Atan2(-up.x, -up.y) * Mathf.Rad2Deg;   // +Z = 坂下
        float sPrev = float.NegativeInfinity; float worstFl = 0f, worstCover = 0f; var log = new List<string>(); int lost = 0;
        for (int i = 0; i < tops.Count; i++)
        {
            float s = float.NaN;
            for (float x = 0f; x <= L; x += 0.05f) { var q = b + up * x; if (Ground(q.x, q.y) >= tops[i] - 0.05f) { s = x; break; } }
            if (float.IsNaN(s)) { lost++; continue; }
            if (s < sPrev + fumi) s = sPrev + fumi;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(pathOf(i));
            if (prefab == null) { note = "⛔ 段石の駒が無い: " + pathOf(i); return made; }
            var p = b + up * s;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.name = "Danishi_" + i.ToString("00");
            go.transform.SetPositionAndRotation(new Vector3(p.x, tops[i], p.y), Quaternion.Euler(0f, yaw, 0f));
            // 踏面の坂上の端を地表の交点へ(実メッシュの踏面の帯 ── ピボットで合わせない)
            var vs = Body(go.transform, 999999);
            float yTop = float.MinValue; foreach (var v in vs) yTop = Mathf.Max(yTop, v.y);
            float f0 = float.MaxValue, f1 = float.MinValue;
            foreach (var v in vs) if (v.y >= yTop - 0.02f) { float t = Vector2.Dot(new Vector2(v.x, v.z) - p, up); f0 = Mathf.Min(f0, t); f1 = Mathf.Max(f1, t); }
            go.transform.position += new Vector3(up.x, 0f, up.y) * -f1 + new Vector3(0f, tops[i] - yTop, 0f);
            var rt = RootToBed(go, Ground, 0.05f);
            if (!float.IsNaN(rt.hi) && rt.hi > 0.01f) { go.transform.position -= new Vector3(0f, rt.hi, 0f); worstFl = Mathf.Max(worstFl, rt.hi); }
            // 踏面に被る地表(天端の帯の頂点の真上)
            foreach (var v in Body(go.transform, 999999)) if (v.y >= tops[i] - 0.02f) worstCover = Mathf.Max(worstCover, Ground(v.x, v.z) - v.y);
            log.Add(tops[i].ToString("F3") + "@" + s.ToString("F2"));
            made.Add(go); sPrev = s;
        }
        var gaps = new List<string>(); for (int i = 1; i < log.Count; i++) gaps.Add((float.Parse(log[i].Split('@')[1]) - float.Parse(log[i - 1].Split('@')[1])).ToString("F2"));
        note = string.Format("段石 {0}/{1} 段・天端@道のり {2}・段の間 {3}m(踏面の狙い ≥ {4:F2})・下端の浮きを根入れで消した最大 {5:F3}m・踏面に被る地表 最悪 {6:F3}m{7}",
                             made.Count, tops.Count, string.Join(" ", log.ToArray()), string.Join("/", gaps.ToArray()), fumi, worstFl, Mathf.Max(0f, worstCover),
                             lost > 0 ? string.Format("・⚠ 地表がその高さに届かず置かなかった {0}", lost) : "");
        return made;
    }

    /// <summary>**切石の段石を一段据える**(EDO-0502 2026-10-06 夕・指図 danStone)。段石は <see cref="EdoAssets.Own.SannoDan"/> の綴り(札 = 蹴上・踏面・幅)。
    /// 幅を <paramref name="width"/>・踏面を <paramref name="tread"/> へ札の値から伸縮し、+Z(見え面)を坂下(−<paramref name="up"/>)へ向ける。
    /// 触れる所を実メッシュで測って寄せる: **踏面の帯(上面から 0.02 の頂点)の最も坂下の線 = 段鼻**を <paramref name="noseMid"/> の線へ・
    /// **両の小口の中ほど**を <paramref name="noseMid"/> へ・**上面**を <paramref name="top"/> へ(⛔ ピボット・bounds の中心で決めない)。
    /// 硬い/柔らかい: どちらでもない(据え)── 札が読めなければ null。当たる先: 屋敷の中の石段すべて(岡部 kaidans・今後の各邸の邸内の石段)。</summary>
    public static GameObject PlaceDanStone(string path, Transform parent, string name, Vector2 noseMid, Vector2 up, float top, float width, float tread)
    {
        float k0, f0, w0; if (!EdoAssets.Own.SannoDanSpec(path, out k0, out f0, out w0)) return null;
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path); if (prefab == null) return null;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        go.name = name;
        float yaw = Mathf.Atan2(-up.x, -up.y) * Mathf.Rad2Deg;   // +Z = 坂下
        go.transform.SetPositionAndRotation(new Vector3(noseMid.x, top, noseMid.y), Quaternion.Euler(0f, yaw, 0f));
        go.transform.localScale = new Vector3(width / w0, 1f, tread / f0);
        var side = new Vector2(up.y, -up.x);
        var vs = Body(go.transform, 999999);
        float yTop = float.MinValue; foreach (var v in vs) yTop = Mathf.Max(yTop, v.y);
        float nose = float.MaxValue, s0 = float.MaxValue, s1 = float.MinValue;
        foreach (var v in vs)
        {
            var d = new Vector2(v.x, v.z) - noseMid;
            if (v.y >= yTop - 0.02f) nose = Mathf.Min(nose, Vector2.Dot(d, up));
            float sd = Vector2.Dot(d, side); s0 = Mathf.Min(s0, sd); s1 = Mathf.Max(s1, sd);
        }
        var mv = up * -nose + side * -(0.5f * (s0 + s1));
        go.transform.position += new Vector3(mv.x, top - yTop, mv.y);
        return go;
    }

    /// <summary>棟の壁体(屋根を外した実メッシュ)の頂点の重心(XZ)。⛔ ピボットではない。</summary>
    public static Vector2 BodyCentreXZ(Transform t)
    {
        var w = Body(t, 600, false); if (w.Count == 0) return new Vector2(t.position.x, t.position.z);
        float x = 0f, z = 0f; foreach (var q in w) { x += q.x; z += q.z; }
        return new Vector2(x / w.Count, z / w.Count);
    }

    /// <summary>棟の壁体の凸包を <paramref name="from"/> から <paramref name="to"/> の向きへ出た所から、さらに <paramref name="clear"/> 外の点。</summary>
    public static Vector2 ExitToward(Transform t, Vector2 from, Vector2 to, float clear)
    {
        var w = Body(t, 600, false); if (w.Count < 3) return from;
        var xz = new Vector2[w.Count]; for (int i = 0; i < w.Count; i++) xz[i] = new Vector2(w[i].x, w[i].z);
        var hi = EdoGeom.HullXZ(xz); var h = new Vector2[hi.Length]; for (int i = 0; i < hi.Length; i++) h[i] = xz[hi[i]];
        var d = (to - from).normalized;
        for (float s = 0f; s < 60f; s += 0.1f) { var p = from + d * s; if (!EdoGeom.PIP(h, p)) return p + d * clear; }
        return from;
    }
}
