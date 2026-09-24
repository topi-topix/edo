// 埋め込む駒・差し込む駒・載せる駒を据える (EdoBuild の partial・2026-09-23・EDO-0274)
//
// ⭐ **何が足りなかったか**: EdoBuild の据え方は「地面に載せる」(Contact/SeatOnGround)と
//    「駒どうしを突き付ける」(Contact/Abut)の二つで、どちらも**駒の実メッシュ全部**を相手に取る。
//    一体で焼いた部材が**材ごとに別の相手と触れる**とき(井筒+井桁の一体物: 井桁=木 が縁石=切石 に載り、
//    井筒=割栗の材 は石敷の穴に差さる)、全部で測ると差さっている筒がめり込み 1.5m と出て、
//    触れている所(井桁の下端と縁石の天端)が隠れる。
//    また、**天端を地表に揃えて埋める駒**(板石敷・舗装・伏せ枡)は地面との当たりが「底」ではなく
//    「天端の縁」で、SeatOnGround(最も低い所を地表へ)では 0.32m 浮く/沈む。
//
// ⭕ 足した道具(どれも**触れている箇所**を測る。⛔ 基準点・bounds の中心で位置を決めない):
//    ・<see cref="BodyOfMat"/> / <see cref="Section"/> … 材(サブメッシュ)で絞った頂点・水平断面
//    ・<see cref="ContactPts"/> … Contact(駒,駒) の中身(頂点の集まりどうし)
//    ・<see cref="RestGap"/> / <see cref="RestOn"/> … 材で絞り、**面で**鉛直の当たりを測って載せる
//    ・<see cref="FlushGap"/> / <see cref="SeatFlush"/> … 天端を地表に揃えて埋める
//    ・<see cref="CenterInOpening"/> … 差す駒を相手の穴の壁の断面へ芯出し(穴との離れを方位ごとに返す)
//    ・<see cref="CenterOnBed"/> … 足(柱)の断面を受け(礎石)の断面へ芯出し(足ごとの芯ずれを返す)
//    ・<see cref="HullOfMat"/> / <see cref="OpeningOf"/> … 駒の平面の外形・筒の口(実メッシュから)
//    ・<see cref="ClearDetailIn"/> / <see cref="CutHole"/> / <see cref="FillHoles"/> … 駒の下の芝を消す・口の下の地形を抜く
//    ・<see cref="TuckUnderCrest"/> … 天端を地表と同じ高さに据えた駒の下の節点を天端より下げ・芝を消す(EDO-0414)
//
// 当たる先: 山王の前庭の井戸(板石敷・井筒+井桁・井戸屋形)。同じ型は**一体で焼いた複合部材**
//   (門+礎石、灯籠+台石、手水鉢+水受け)と、**天端で埋める敷き物**(園路の敷石・延段・沓脱石)全部。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>材(サブメッシュの材質名)で絞った、駒の世界頂点。<paramref name="mat"/> が null/空なら全材。
    /// 材の名は**部分一致**(例 "Kirishi")。⛔ 間引かない — 当たりを落とす。
    /// 屋根の篩は掛けない(呼び手が材で名指しするので)。</summary>
    public static List<Vector3> BodyOfMat(Transform tr, string mat)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            if (string.IsNullOrEmpty(mat)) { foreach (var v in vs) L.Add(l2w.MultiplyPoint3x4(v)); continue; }
            var mats = rr.sharedMaterials;
            var seen = new HashSet<int>();
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mn = s < mats.Length && mats[s] != null ? mats[s].name : "";
                if (mn.IndexOf(mat, StringComparison.Ordinal) < 0) continue;
                foreach (var i in mf.sharedMesh.GetTriangles(s)) if (seen.Add(i)) L.Add(l2w.MultiplyPoint3x4(vs[i]));
            }
        }
        return L;
    }

    /// <summary>**実体化した駒の水平断面**(高さ <paramref name="y"/> で三角形を切った交点・世界座標)。
    /// <see cref="SectionAt"/> の実体版で、材(<paramref name="mat"/>・部分一致・null で全材)で絞れる。
    /// ⭐ 柱・筒のように頂点が上下の端にしか無い駒でも、その高さの実形が出る。</summary>
    public static List<Vector3> Section(Transform tr, float y, string mat = null)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var m = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
            var mats = rr.sharedMaterials;
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mn = s < mats.Length && mats[s] != null ? mats[s].name : "";
                if (!string.IsNullOrEmpty(mat) && mn.IndexOf(mat, StringComparison.Ordinal) < 0) continue;
                var tri = mf.sharedMesh.GetTriangles(s);
                for (int i = 0; i + 2 < tri.Length; i += 3)
                    for (int e = 0; e < 3; e++)
                    {
                        Vector3 p = w[tri[i + e]], q = w[tri[i + (e + 1) % 3]];
                        if ((p.y - y) * (q.y - y) > 0f) continue;
                        float dy = q.y - p.y;
                        if (Mathf.Abs(dy) < 1e-7f) continue;
                        L.Add(Vector3.Lerp(p, q, (y - p.y) / dy));
                    }
            }
        }
        return L;
    }

    /// <summary>**二つの頂点の集まりが触れている箇所**(<see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/> の中身)。
    /// <paramref name="dir"/> に直交する面を <paramref name="cell"/> 角の筋に割り、両方がいる筋だけで
    /// 「pa の前面 − pb の背面」を取る。返り値 = 最小の隙(負 = めり込み)・NaN = 向き合っていない。</summary>
    public static float ContactPts(List<Vector3> pa, List<Vector3> pb, Vector3 dir, out Vector3 at, out int count,
                                   float tol = 0.01f, float cell = 0.25f)
    {
        at = Vector3.zero; count = 0;
        var d = dir.normalized;
        var u = Vector3.Cross(d, Mathf.Abs(d.y) < 0.9f ? Vector3.up : Vector3.right).normalized;
        var v = Vector3.Cross(d, u).normalized;
        if (pa.Count == 0 || pb.Count == 0) return float.NaN;
        var fa = new Dictionary<long, float>();   // 筋ごと: a の前面(dir の最大)
        var fb = new Dictionary<long, float>();   // 筋ごと: b の背面(dir の最小)
        var pt = new Dictionary<long, Vector3>();
        Func<Vector3, long> key = w =>
            ((long)Mathf.RoundToInt(Vector3.Dot(w, u) / cell) << 32) ^ (uint)Mathf.RoundToInt(Vector3.Dot(w, v) / cell);
        foreach (var w in pa)
        {
            long k = key(w); float q = Vector3.Dot(w, d);
            float cur; if (!fa.TryGetValue(k, out cur) || q > cur) { fa[k] = q; pt[k] = w; }
        }
        foreach (var w in pb)
        {
            long k = key(w); float q = Vector3.Dot(w, d);
            float cur; if (!fb.TryGetValue(k, out cur) || q < cur) fb[k] = q;
        }
        float best = float.NaN;
        foreach (var kv in fa)
        {
            float qb; if (!fb.TryGetValue(kv.Key, out qb)) continue;
            float g = qb - kv.Value;
            if (float.IsNaN(best) || g < best) { best = g; at = pt[kv.Key]; }
        }
        if (float.IsNaN(best)) return best;                      // 筋が重ならない = 向き合っていない
        foreach (var kv in fa)
        {
            float qb; if (!fb.TryGetValue(kv.Key, out qb)) continue;
            if (qb - kv.Value - best <= tol) count++;
        }
        return best;
    }

    /// <summary>材で絞った三角形(世界座標)。</summary>
    static List<Vector3[]> TrisOfMat(Transform tr, string mat)
    {
        var L = new List<Vector3[]>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
            var mats = rr.sharedMaterials;
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mn = s < mats.Length && mats[s] != null ? mats[s].name : "";
                if (!string.IsNullOrEmpty(mat) && mn.IndexOf(mat, StringComparison.Ordinal) < 0) continue;
                var tri = mf.sharedMesh.GetTriangles(s);
                for (int i = 0; i + 2 < tri.Length; i += 3) L.Add(new[] { w[tri[i]], w[tri[i + 1]], w[tri[i + 2]] });
            }
        }
        return L;
    }

    /// <summary>点 (x,z) の真上/真下を通る鉛直線と三角形の交わりの高さ。三角形の平面投影の外なら false。</summary>
    static bool TriYAt(Vector3[] t, float x, float z, out float y)
    {
        y = 0f;
        float d = (t[1].z - t[2].z) * (t[0].x - t[2].x) + (t[2].x - t[1].x) * (t[0].z - t[2].z);
        if (Mathf.Abs(d) < 1e-10f) return false;                 // 鉛直な面(投影が線)
        float l0 = ((t[1].z - t[2].z) * (x - t[2].x) + (t[2].x - t[1].x) * (z - t[2].z)) / d;
        float l1 = ((t[2].z - t[0].z) * (x - t[2].x) + (t[0].x - t[2].x) * (z - t[2].z)) / d;
        float l2 = 1f - l0 - l1;
        const float e = -1e-5f;
        if (l0 < e || l1 < e || l2 < e) return false;
        y = l0 * t[0].y + l1 * t[1].y + l2 * t[2].y;
        return true;
    }

    /// <summary>**載る駒と受ける駒が鉛直に触れている箇所**(材で絞る・null で全材)。
    /// 載る駒の各頂点の真下にある受けの面の**最も高い所**との差と、受けの各頂点の真上にある載る駒の面の
    /// **最も低い所**との差の、両方の最小を取る。返り値 = 最小の隙[m](負 = めり込み・NaN = 上下に重ならない)、
    /// <paramref name="at"/> = その所、<paramref name="count"/> = 最小から <paramref name="tol"/> 以内の点の数。
    /// <para>⭐ **頂点ではなく面で測る。**<see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>
    /// は頂点を筋に割って「両方がいる筋」だけで測るので、**頂点が隅にしか無い平らな面**(柱の根・礎石の天端・
    /// 井桁の下端・縁石の天端)どうしは筋が重ならず、当たりを見落とす ── 2026-09-23 実測: 井戸屋形の柱 0.12 角と
    /// 礎石 0.45 角は 0.25m の筋で一度も重ならず、代わりに軒の隅が石敷の隅に「当たって」屋形が 1.93m 沈んだ。
    /// 井桁の木口は隣の礎石の隅と同じ筋に入り 0.05m 浮いた。</para></summary>
    public static float RestGap(GameObject mover, string moverMat, GameObject bed, string bedMat,
                                out Vector3 at, out int count, float tol = 0.005f)
    {
        at = mover.transform.position; count = 0;
        var mt = TrisOfMat(mover.transform, moverMat);
        var bt = TrisOfMat(bed.transform, bedMat);
        if (mt.Count == 0 || bt.Count == 0) return float.NaN;
        var gaps = new List<float>(); var pts = new List<Vector3>();
        // 載る駒の頂点 → 真下の受けの面(最も高い所)
        // ⭐ 相手の三角形は XZ の升(0.5m)に振り分けて引く ── 総当たりだと樹木(10万頂点)で数分止まる
        Action<List<Vector3[]>, List<Vector3[]>, bool> sweep = (src, dst, srcIsMover) =>
        {
            const float CELL = 0.5f;
            var grid = new Dictionary<long, List<Vector3[]>>();
            foreach (var q in dst)
            {
                float x0 = Mathf.Min(q[0].x, Mathf.Min(q[1].x, q[2].x)), x1 = Mathf.Max(q[0].x, Mathf.Max(q[1].x, q[2].x));
                float z0 = Mathf.Min(q[0].z, Mathf.Min(q[1].z, q[2].z)), z1 = Mathf.Max(q[0].z, Mathf.Max(q[1].z, q[2].z));
                for (int ix = Mathf.FloorToInt(x0 / CELL); ix <= Mathf.FloorToInt(x1 / CELL); ix++)
                    for (int iz = Mathf.FloorToInt(z0 / CELL); iz <= Mathf.FloorToInt(z1 / CELL); iz++)
                    {
                        long k = ((long)ix << 32) ^ (uint)iz;
                        List<Vector3[]> l; if (!grid.TryGetValue(k, out l)) grid[k] = l = new List<Vector3[]>();
                        l.Add(q);
                    }
            }
            var seen = new HashSet<Vector3>();
            foreach (var t in src)
                foreach (var p in t)
                {
                    if (!seen.Add(p)) continue;
                    List<Vector3[]> cand;
                    if (!grid.TryGetValue(((long)Mathf.FloorToInt(p.x / CELL) << 32) ^ (uint)Mathf.FloorToInt(p.z / CELL), out cand)) continue;
                    bool hit = false; float best = srcIsMover ? float.MinValue : float.MaxValue;
                    foreach (var q in cand)
                    {
                        float y;
                        if (!TriYAt(q, p.x, p.z, out y)) continue;
                        if (srcIsMover) { if (y > best) best = y; } else { if (y < best) best = y; }
                        hit = true;
                    }
                    if (!hit) continue;
                    gaps.Add(srcIsMover ? p.y - best : best - p.y); pts.Add(p);
                }
        };
        sweep(mt, bt, true);
        sweep(bt, mt, false);
        if (gaps.Count == 0) return float.NaN;
        float mn = float.MaxValue;
        for (int i = 0; i < gaps.Count; i++) if (gaps[i] < mn) { mn = gaps[i]; at = pts[i]; }
        foreach (var g in gaps) if (g - mn <= tol) count++;
        return mn;
    }

    /// <summary>**受けの上に載せる。**<see cref="RestGap"/> が <paramref name="gap"/>(0 = 接触)になる高さへ
    /// 鉛直に動かす。返り値 = 動かした量[m](上下に重ならなければ NaN で動かさない)。</summary>
    public static float RestOn(GameObject mover, string moverMat, GameObject bed, string bedMat, float gap,
                               out Vector3 at, out int count)
    {
        float c = RestGap(mover, moverMat, bed, bedMat, out at, out count);
        if (float.IsNaN(c)) return float.NaN;
        float dy = gap - c;
        mover.transform.position += new Vector3(0f, dy, 0f);
        RestGap(mover, moverMat, bed, bedMat, out at, out count);
        return dy;
    }

    /// <summary>**天端を地表に揃えて埋める駒の、天端と地表の差。**材 <paramref name="mat"/> の頂点を世界 XZ の
    /// <paramref name="cell"/> 角に割り、**格子ごとに最も高い頂点**(= 天端)と、その真下の描かれた地表
    /// (<see cref="Ground"/> と同じ面)の差を取る。返り値 = 最小(負 = 天端が土に埋まっている)、
    /// <paramref name="rise"/> = 最大(天端が地表から出ている量)。
    /// <para>⭐ 埋める駒(板石敷・舗装・伏せ枡・延段)が地面と触れるのは**底ではなく天端の縁**。
    /// ⛔ <see cref="SeatOnGround"/>(最も低い所を地表へ)で据えると、層の厚みぶん丸ごと浮く。</para></summary>
    public static float FlushGap(GameObject go, string mat, out float rise, out Vector3 at, out int count,
                                 float cell = 0.25f, float tol = 0.01f)
    {
        rise = float.NaN; at = go.transform.position; count = 0;
        var top = new Dictionary<long, Vector3>();
        foreach (var w in BodyOfMat(go.transform, mat))
        {
            long k = ((long)Mathf.RoundToInt(w.x / cell) << 32) ^ (uint)Mathf.RoundToInt(w.z / cell);
            Vector3 cur; if (!top.TryGetValue(k, out cur) || w.y > cur.y) top[k] = w;
        }
        if (top.Count == 0) return float.NaN;
        var probe = Probe();
        float best = float.NaN; var cs = new List<float>();
        foreach (var w in top.Values)
        {
            float c = w.y - probe.At(w.x, w.z); cs.Add(c);
            if (float.IsNaN(best) || c < best) { best = c; at = w; }
            if (float.IsNaN(rise) || c > rise) rise = c;
        }
        foreach (var c in cs) if (c - best <= tol) count++;
        return best;
    }

    /// <summary>**天端を地表に揃えて埋める。**<see cref="FlushGap"/> の最小が <paramref name="proud"/>
    /// (+ = 地表から出す量・0 = 面一)になる高さへ動かす。天端のどこも土に埋もれない高さで、
    /// 地表の起伏と駒の勾配のぶんは <paramref name="rise"/>(出ている量の最大)に出る。返り値 = 動かした量[m]。
    /// 測れる頂点が無ければ例外(黙って置かない)。</summary>
    public static float SeatFlush(GameObject go, string mat, float proud, out float rise, float cell = 0.25f)
    {
        Vector3 at; int n;
        float c = FlushGap(go, mat, out rise, out at, out n, cell);
        if (float.IsNaN(c)) throw new InvalidOperationException("SeatFlush: " + go.name + " に材『" + mat + "』の頂点が無い");
        float dy = proud - c;
        go.transform.position += new Vector3(0f, dy, 0f);
        FlushGap(go, mat, out rise, out at, out n, cell);
        return dy;
    }

    static void MidXZ(List<Vector3> pts, out Vector2 mid, out Vector2 half)
    {
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in pts)
        {
            if (p.x < mnx) mnx = p.x; if (p.x > mxx) mxx = p.x;
            if (p.z < mnz) mnz = p.z; if (p.z > mxz) mxz = p.z;
        }
        mid = new Vector2((mnx + mxx) * 0.5f, (mnz + mxz) * 0.5f);
        half = new Vector2((mxx - mnx) * 0.5f, (mxz - mnz) * 0.5f);
    }

    /// <summary>**差す駒を相手の穴へ芯出しする。**高さ <paramref name="y"/> で、差す駒(材 <paramref name="plugMat"/>)の
    /// 断面の外周と、受ける駒(材 <paramref name="socketMat"/>)の断面のうち**差す駒の外周から <paramref name="margin"/>
    /// 以内**にある物(= 穴の壁)を取り、両方の外形の中点を重ねる(水平だけ動かす)。
    /// 返り値 = 動かした量(XZ・測れなければ NaN で動かさない)。
    /// <paramref name="clearMin"/>/<paramref name="clearMax"/> = 16 方位ごとの「穴の壁 − 差す駒の外周」の最小/最大
    /// (負 = めり込み)。⭐ 穴の壁と外周は**触れている面そのもの**で、駒の基準点は使わない。</summary>
    public static Vector2 CenterInOpening(GameObject plug, string plugMat, GameObject socket, string socketMat,
                                          float y, float margin, out float clearMin, out float clearMax)
    {
        clearMin = clearMax = float.NaN;
        var P = Section(plug.transform, y, plugMat);
        if (P.Count < 8) return new Vector2(float.NaN, float.NaN);
        Vector2 cP, hP; MidXZ(P, out cP, out hP);
        float R = 0f; foreach (var p in P) R = Mathf.Max(R, Vector2.Distance(new Vector2(p.x, p.z), cP));
        var S = new List<Vector3>();
        foreach (var p in Section(socket.transform, y, socketMat))
            if (Vector2.Distance(new Vector2(p.x, p.z), cP) <= R + margin) S.Add(p);
        if (S.Count < 8) return new Vector2(float.NaN, float.NaN);
        Vector2 cS, hS; MidXZ(S, out cS, out hS);
        var sh = cS - cP;
        plug.transform.position += new Vector3(sh.x, 0f, sh.y);
        // 方位ごとの離れ(動かした後)
        var pMax = new float[16]; var sMin = new float[16];
        for (int i = 0; i < 16; i++) { pMax[i] = float.NaN; sMin[i] = float.NaN; }
        Func<Vector3, Vector2, int> sec = (p, off) =>
        {
            var d = new Vector2(p.x, p.z) + off - cS;
            float a = Mathf.Atan2(d.y, d.x); if (a < 0) a += 2 * Mathf.PI;
            return Mathf.Clamp((int)(a / (2 * Mathf.PI) * 16), 0, 15);
        };
        foreach (var p in P)
        {
            int i = sec(p, sh); float r = Vector2.Distance(new Vector2(p.x, p.z) + sh, cS);
            if (float.IsNaN(pMax[i]) || r > pMax[i]) pMax[i] = r;
        }
        foreach (var p in S)
        {
            int i = sec(p, Vector2.zero); float r = Vector2.Distance(new Vector2(p.x, p.z), cS);
            if (float.IsNaN(sMin[i]) || r < sMin[i]) sMin[i] = r;
        }
        for (int i = 0; i < 16; i++)
        {
            if (float.IsNaN(pMax[i]) || float.IsNaN(sMin[i])) continue;
            float c = sMin[i] - pMax[i];
            if (float.IsNaN(clearMin) || c < clearMin) clearMin = c;
            if (float.IsNaN(clearMax) || c > clearMax) clearMax = c;
        }
        return sh;
    }

    /// <summary>**足(柱)を受け(礎石)へ芯出しする。**載る駒(材 <paramref name="moverMat"/>)の高さ <paramref name="yMover"/> の
    /// 断面(= 足の実形)と、受ける駒(材 <paramref name="bedMat"/>)の高さ <paramref name="yBed"/> の断面のうち
    /// 足の外形から <paramref name="reach"/> 以内の物(= 受けの実形)を取り、外形の中点を重ねる(水平だけ動かす)。
    /// <paramref name="worstFoot"/> = 動かした後の**足ごと**(外形の中点から見た四象限)の芯ずれの最大[m]
    /// ⛔ 足どうしの平均で合わせて、一本だけ礎石を外れているのを見逃さないための検め。
    /// 返り値 = 動かした量(XZ・測れなければ NaN で動かさない)。</summary>
    public static Vector2 CenterOnBed(GameObject mover, string moverMat, float yMover, GameObject bed, string bedMat,
                                      float yBed, float reach, out float worstFoot)
    {
        worstFoot = float.NaN;
        var M = Section(mover.transform, yMover, moverMat);
        if (M.Count < 4) return new Vector2(float.NaN, float.NaN);
        Vector2 cM, hM; MidXZ(M, out cM, out hM);
        var B = new List<Vector3>();
        foreach (var p in Section(bed.transform, yBed, bedMat))
            if (Mathf.Abs(p.x - cM.x) <= hM.x + reach && Mathf.Abs(p.z - cM.y) <= hM.y + reach) B.Add(p);
        if (B.Count < 4) return new Vector2(float.NaN, float.NaN);
        Vector2 cB, hB; MidXZ(B, out cB, out hB);
        var sh = cB - cM;
        mover.transform.position += new Vector3(sh.x, 0f, sh.y);
        // 足ごとの芯ずれ(四象限)
        worstFoot = 0f;
        for (int q = 0; q < 4; q++)
        {
            var mq = new List<Vector3>(); var bq = new List<Vector3>();
            foreach (var p in M) { var d = new Vector2(p.x + sh.x, p.z + sh.y) - cB; if (Quad(d) == q) mq.Add(p + new Vector3(sh.x, 0f, sh.y)); }
            foreach (var p in B) { var d = new Vector2(p.x, p.z) - cB; if (Quad(d) == q) bq.Add(p); }
            if (mq.Count == 0 || bq.Count == 0) continue;
            Vector2 a, ha, b, hb; MidXZ(mq, out a, out ha); MidXZ(bq, out b, out hb);
            worstFoot = Mathf.Max(worstFoot, Vector2.Distance(a, b));
        }
        return sh;
    }
    static int Quad(Vector2 d) { return d.x >= 0 ? (d.y >= 0 ? 0 : 3) : (d.y >= 0 ? 1 : 2); }

    // ============================================================ 駒の下の地形(2026-09-23・EDO-0274)
    // ⭐ 埋め込んだ駒の下では地形の芝(detail)が駒を突き抜け、井戸・枡のように**口のある駒**の中は
    //    地形の面で塞がる。範囲は**据えた駒の実メッシュ**から出す(⛔ 指図の矩形・部材の寸法を写さない)。
    //    当たる先: 井戸(石敷・井筒)・延段と敷石・沓脱石・池や手水鉢の縁石・伏せ枡。
    // ⛔ 地形の編集は Undo の外 ── 呼ぶ前に TerrainData を退避すること(`.claude/rules/unity.md`)。

    /// <summary>駒(材 <paramref name="mat"/>・null で全材)の実メッシュの**平面の外形**(XZ の凸包・世界座標)。</summary>
    public static Vector2[] HullOfMat(Transform tr, string mat = null)
    {
        var pts = BodyOfMat(tr, mat);
        var p2 = new Vector2[pts.Count];
        for (int i = 0; i < pts.Count; i++) p2[i] = new Vector2(pts[i].x, pts[i].z);
        var idx = EdoGeom.HullXZ(p2);
        var hull = new Vector2[idx.Length];
        for (int i = 0; i < idx.Length; i++) hull[i] = p2[idx[i]];
        return hull;
    }

    /// <summary>**筒の口**(輪になった駒の内周)を高さ <paramref name="y"/> の断面から採る。断面の外形の中点から
    /// <paramref name="n"/> 方位それぞれで**最も内の交点**までを結んだ多角形(世界 XZ)。測れなければ null。
    /// ⭐ 井筒・枡・井戸側・手水鉢の口。⛔ 部材の寸法(内径)を写さない ── 実メッシュの内周を測る。</summary>
    public static Vector2[] OpeningOf(Transform tr, string mat, float y, int n = 32)
    {
        var S = Section(tr, y, mat);
        if (S.Count < n) return null;
        Vector2 c, h; MidXZ(S, out c, out h);
        var rmin = new float[n];
        for (int i = 0; i < n; i++) rmin[i] = float.MaxValue;
        foreach (var p in S)
        {
            var d = new Vector2(p.x, p.z) - c;
            float a = Mathf.Atan2(d.y, d.x); if (a < 0) a += 2 * Mathf.PI;
            int k = Mathf.Clamp((int)(a / (2 * Mathf.PI) * n), 0, n - 1);
            rmin[k] = Mathf.Min(rmin[k], d.magnitude);
        }
        var poly = new Vector2[n];
        for (int i = 0; i < n; i++)
        {
            if (rmin[i] == float.MaxValue) return null;             // 口が閉じていない方位がある
            // 方位の帯の端(小さい角)で結ぶと多角形が口の内に収まらないことがあるので、帯の中央で結び、
            // 帯の半角ぶん外へ広げる(弦が円弧の内に落ちる量 = r(1/cos(π/n) − 1))。
            float a = (i + 0.5f) / n * 2 * Mathf.PI;
            float r = rmin[i] / Mathf.Cos(Mathf.PI / n);
            poly[i] = c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r;
        }
        return poly;
    }

    /// <summary>軸に沿った矩形(世界 XZ)と凸でも凹でもよい多角形が重なるか。</summary>
    static bool RectOverlapsPoly(Vector2 lo, Vector2 hi, Vector2[] poly)
    {
        foreach (var p in poly) if (p.x >= lo.x && p.x <= hi.x && p.y >= lo.y && p.y <= hi.y) return true;
        var cs = new[] { lo, new Vector2(hi.x, lo.y), hi, new Vector2(lo.x, hi.y) };
        foreach (var q in cs) if (EdoGeom.PIP(poly, q)) return true;
        for (int i = 0; i < poly.Length; i++)
        {
            var a = poly[i]; var b = poly[(i + 1) % poly.Length];
            for (int e = 0; e < 4; e++) if (SegX(a, b, cs[e], cs[(e + 1) % 4])) return true;
        }
        return false;
    }
    static bool SegX(Vector2 p1, Vector2 p2, Vector2 q1, Vector2 q2)
    {
        Func<Vector2, Vector2, Vector2, float> cr = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
        float d1 = cr(q1, q2, p1), d2 = cr(q1, q2, p2), d3 = cr(p1, p2, q1), d4 = cr(p1, p2, q2);
        return ((d1 > 0) != (d2 > 0)) && ((d3 > 0) != (d4 > 0));
    }

    /// <summary>detail の矩形を **[y, x]・寸法 [h, w]** の配列で読む。
    /// <para>⚠ **Unity 6000.5 の `GetDetailLayer` / `GetHoles` は、中身は [y, x] の行優先なのに、配列の寸法を
    /// [w, h] と名乗って返す**(2026-09-23 実測: 40×30 を読むと GetLength(0)=40。`d[x,y]` とも `d[y,x]` とも
    /// 合わず、平らに並べた k 番目 = (x0 + k % w, y0 + k / w) だけが全点一致)。そのまま添字で引くと
    /// 正方でない範囲で**別のセルを消す**・添字あふれで落ちる。⇒ 平らに読み直して [h, w] に組み直す。
    /// 書き戻す <c>SetDetailLayer</c>/<c>SetHoles</c> へは組み直した [h, w] を渡す(文書どおりの形)。</para></summary>
    static int[,] DetailBlock(TerrainData td, int x0, int y0, int w, int h, int layer)
    {
        var raw = td.GetDetailLayer(x0, y0, w, h, layer);
        var o = new int[h, w]; int k = 0;
        foreach (var v in raw) { o[k / w, k % w] = v; k++; }
        return o;
    }
    /// <summary>holes の矩形を [y, x]・寸法 [h, w] で読む(true = 地形あり)。⚠ <see cref="DetailBlock"/> と同じ寸法の癖。</summary>
    static bool[,] HolesBlock(TerrainData td, int x0, int y0, int w, int h)
    {
        var raw = td.GetHoles(x0, y0, w, h);
        var o = new bool[h, w]; int k = 0;
        foreach (var v in raw) { o[k / w, k % w] = v; k++; }
        return o;
    }

    /// <summary>地形のセル範囲の報告。</summary>
    public struct TerrainCells
    {
        public int visited, changed;              // 重なったセル / 値が変わったセル
        public int joints;                        // (穴)覆いの検めで、駒の継ぎ目と数えた点(0.1m 刻み)
        public int i0, j0, i1, j1;                // セル番号の範囲(含む)
        public Vector2 lo, hi;                    // その世界 XZ の範囲
        public override string ToString()
        {
            return changed + " / " + visited + " セル" + (joints > 0 ? "(継ぎ目 " + joints + " 点)" : "") + " [" + i0 + ".." + i1 + "]×[" + j0 + ".." + j1 + "] = x " +
                   lo.x.ToString("F2") + "〜" + hi.x.ToString("F2") + " z " + lo.y.ToString("F2") + "〜" + hi.y.ToString("F2");
        }
    }

    /// <summary>**多角形に少しでも掛かる detail のセルを空にする**(全層)。返り値 = 掛かったセルと値の変わったセル。
    /// <para>⭐ 芝の一本はセルの中のどこにでも生えるので、**掛かったセルは全部**消す(芯が中にあるセルだけでは、
    /// 縁のセルの芝が駒の上へ出る)。その代わり駒の外へ最大 1 セル(赤坂は 1.0m)芝が退く ── 報告に範囲を刷る。</para></summary>
    public static TerrainCells ClearDetailIn(Vector2[] poly, Func<Vector2, Vector2, bool> cellOk = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int D = td.detailResolution; float cx = td.size.x / D, cz = td.size.z / D;
        var r = new TerrainCells();
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        r.i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - org.x) / cx), 0, D - 1); r.i1 = Mathf.Clamp(Mathf.FloorToInt((mxx - org.x) / cx), 0, D - 1);
        r.j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - org.z) / cz), 0, D - 1); r.j1 = Mathf.Clamp(Mathf.FloorToInt((mxz - org.z) / cz), 0, D - 1);
        int w = r.i1 - r.i0 + 1, h = r.j1 - r.j0 + 1;
        var hit = new bool[h, w];
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var lo = new Vector2(org.x + (r.i0 + i) * cx, org.z + (r.j0 + j) * cz);
                hit[j, i] = RectOverlapsPoly(lo, lo + new Vector2(cx, cz), poly) &&
                            (cellOk == null || cellOk(lo, lo + new Vector2(cx, cz)));
                if (hit[j, i]) r.visited++;
            }
        var changedCell = new bool[h, w];
        for (int l = 0; l < td.detailPrototypes.Length; l++)
        {
            var d = DetailBlock(td, r.i0, r.j0, w, h, l);
            bool any = false;
            for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
                    if (hit[j, i] && d[j, i] != 0) { d[j, i] = 0; changedCell[j, i] = true; any = true; }
            if (any) td.SetDetailLayer(r.i0, r.j0, l, d);
        }
        foreach (var b in changedCell) if (b) r.changed++;
        r.lo = new Vector2(org.x + r.i0 * cx, org.z + r.j0 * cz);
        r.hi = new Vector2(org.x + (r.i1 + 1) * cx, org.z + (r.j1 + 1) * cz);
        return r;
    }

    /// <summary>**口の下の地形に穴を開ける**(TerrainData の holes)。<paramref name="opening"/> に掛かる holes のセルを
    /// 全部抜く。ただし抜くセルのうち口の外の所は、**<paramref name="covers"/> の実メッシュが地表より上で覆っている**
    /// こと(0.1m 刻みで検める。<paramref name="joint"/> 以内に覆いがある点は駒どうしの継ぎ目と数える)── 覆われない所があれば**一つも抜かずに**理由を返す(穴の縁が見えるため)。
    /// <paramref name="why"/> = 抜かなかった理由(抜いたら null)。
    /// <para>⚠ holes のセルは高さの格子と同じ大きさ(赤坂は 2.0m)。口より大きく抜けるので、覆いの検めが要る。
    /// ⚠ 抜いた穴は駒を動かしても残る ── 据え直したら <see cref="FillHoles"/> で塞いでから抜き直す。</para></summary>
    public static TerrainCells CutHole(Vector2[] opening, GameObject[] covers, out string why, float joint = 0.02f)
    {
        why = null;
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int R = td.holesResolution; float cx = td.size.x / R, cz = td.size.z / R;
        var r = new TerrainCells();
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in opening) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        r.i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - org.x) / cx), 0, R - 1); r.i1 = Mathf.Clamp(Mathf.FloorToInt((mxx - org.x) / cx), 0, R - 1);
        r.j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - org.z) / cz), 0, R - 1); r.j1 = Mathf.Clamp(Mathf.FloorToInt((mxz - org.z) / cz), 0, R - 1);
        r.lo = new Vector2(org.x + r.i0 * cx, org.z + r.j0 * cz);
        r.hi = new Vector2(org.x + (r.i1 + 1) * cx, org.z + (r.j1 + 1) * cz);
        int w = r.i1 - r.i0 + 1, h = r.j1 - r.j0 + 1;
        var cut = new bool[h, w];
        var tris = new List<Vector3[]>();
        foreach (var g in covers) tris.AddRange(TrisOfMat(g.transform, null));
        var probe = Probe();
        const float STEP = 0.1f;
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var lo = new Vector2(org.x + (r.i0 + i) * cx, org.z + (r.j0 + j) * cz);
                if (!RectOverlapsPoly(lo, lo + new Vector2(cx, cz), opening)) continue;
                cut[j, i] = true; r.visited++;
                for (float x = lo.x + STEP * 0.5f; x < lo.x + cx; x += STEP)
                    for (float z = lo.y + STEP * 0.5f; z < lo.y + cz; z += STEP)
                    {
                        if (EdoGeom.PIP(opening, new Vector2(x, z))) continue;       // 口の中は見えてよい
                        float g = probe.At(x, z);
                        if (CoveredAt(tris, x, z, g)) continue;
                        // 駒と駒の継ぎ目(井筒の外周と石敷の穴の縁のような、多角形どうしの弦の差)は、
                        // <paramref name="joint"/> 以内に覆いがあれば継ぎ目と数える(⛔ 穴の縁ではない)
                        bool slit = false;
                        for (int k = 0; k < 8 && !slit; k++)
                        {
                            float a = k * Mathf.PI / 4f;
                            slit = CoveredAt(tris, x + Mathf.Cos(a) * joint, z + Mathf.Sin(a) * joint, g);
                        }
                        if (slit) { r.joints++; continue; }
                        {
                            why = "穴のセル (" + (r.i0 + i) + "," + (r.j0 + j) + ") の (" + x.ToString("F2") + ", " + z.ToString("F2") +
                                  ") を覆う駒が無い ── 穴の縁が見える";
                            return r;
                        }
                    }
            }
        var hv = HolesBlock(td, r.i0, r.j0, w, h);
        for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
                if (cut[j, i] && hv[j, i]) { hv[j, i] = false; r.changed++; }
        if (r.changed > 0) td.SetHoles(r.i0, r.j0, hv);
        return r;
    }

    static bool CoveredAt(List<Vector3[]> tris, float x, float z, float ground)
    {
        float y;
        foreach (var q in tris) if (TriYAt(q, x, z, out y) && y >= ground - 1e-3f) return true;
        return false;
    }

    /// <summary><see cref="CutHole"/> で抜いた範囲を塞ぐ(据え直しの前に)。返り値 = 塞いだセルの数。</summary>
    public static int FillHoles(TerrainCells cells)
    {
        var td = T().terrainData;
        int w = cells.i1 - cells.i0 + 1, h = cells.j1 - cells.j0 + 1, n = 0;
        if (w <= 0 || h <= 0) return 0;
        var hv = HolesBlock(td, cells.i0, cells.j0, w, h);
        for (int j = 0; j < h; j++) for (int i = 0; i < w; i++) if (!hv[j, i]) { hv[j, i] = true; n++; }
        if (n > 0) td.SetHoles(cells.i0, cells.j0, hv);
        return n;
    }
    // ============================================================ 天端の下の地形(2026-09-23・EDO-0414)
    // ⭐ **天端を地表と同じ高さに据えた駒**(土留めの石垣・石段の袖 ── 天端 = 高い側の地盤)は、
    //    駒の奥行きの中に地形の節点が残り、**その節点も天端と同じ高さ**なので、天端の面と地形の面が重なって
    //    斑に描かれ(z-fight)、芝(detail)は天端を突き抜ける(山王の前庭の北の土留め: 天端 14.500 と節点 14.500・
    //    天端の下の芝 20 セル)。⇒ 駒の**実メッシュの天端の外形**の中の節点を天端より <c>depth</c> 下げ、芝を消す。
    // ⚠ 地形の節点は赤坂で 2m 刻み。下げた節点の三角形は外形の外へ最大 1 セル掛かるので、外形の外の地表が
    //    どれだけ下がったかを必ず刷る(<see cref="CrestTuck.dipOut"/>)。⛔ 節点を上げない(下げるだけ)。
    // ⛔ 地形の編集は Undo の外 ── 呼ぶ前に TerrainData を退避すること(`.claude/rules/unity.md`)。
    //    整地(設計面へ寄せる段)を流し直すと節点は天端の高さへ戻るので、据え直しのたびにこれを呼ぶ。
    //    当たる先: 天端を `copingRise:"groundHi"` や段の面に揃えた土留め(山王の前庭・参道の階・石段の袖、
    //    土井の郭の土留め)、面一に埋めた基壇の縁。

    /// <summary><see cref="TuckUnderCrest"/> の報告。</summary>
    public struct CrestTuck
    {
        public int pieces, nodes, lowered;        // 駒 / 外形の中の節点 / 下げた節点
        public float maxDrop;                     // 節点を下げた量の最大
        public TerrainCells det;                  // 芝を消したセル(駒ごとの和)
        public int detVisited, detChanged;
        public int samples, thin;                 // 天端の検め点(外形の縁から inset 以上内) / 天端と地表が**面で**重なる点(前後左右 0.1m も差 < minGap)
        public int above, aboveNodes;             // 地表が天端より coTol を超えて高い点 / 節点(= 埋没・⛔ ここでは触らない・別の欠陥)
        public int faceIn;                        // 見え面を渡された駒の法(面)の点で地表の下 ── 根入れ(埋没に数えない)
        public int hidden;                        // 地表が天端より高いが**見える天端の帯の奥**(上の段の土・上の壁が始まった後)の点 ── 埋没に数えない
        public float aboveMax; public Vector3 aboveAt;
        public string thinBy;                     // 薄い点の多い駒(上位 5)
        public string aboveBy;                    // 埋没の点の多い駒(上位 5・最大の深さ)
        public float gapMin; public Vector3 gapAt; // 天端 − 地表 の最小とその所(硬い: minGap 以上)
        public float dipOut; public Vector3 dipAt; // 外形の外で地表が下がった量の最大(柔らかい: 報告のみ)
        public override string ToString()
        {
            return "駒 " + pieces + " / 外形の中の節点 " + nodes + " のうち下げた " + lowered + "(最大 " + maxDrop.ToString("F3") + "m)" +
                   " / 芝 " + detChanged + " / " + detVisited + " セル" +
                   " / 天端 − 地表 最小 " + (float.IsNaN(gapMin) ? "—" : gapMin.ToString("F3")) + "m @(" + gapAt.x.ToString("F2") + ", " + gapAt.z.ToString("F2") + ")" +
                   "・面の重なり " + thin + " / " + samples +
                   (hidden > 0 ? " / 帯の奥で土に入る控え " + hidden + "(埋没に数えない)" : "") +
                   (faceIn > 0 ? " / 法の根入れ " + faceIn + "(天端でない・数えない)" : "") +
                   (above > 0 ? " / 天端より地表が高い点 " + above + "(節点 " + aboveNodes + "・最大 " + aboveMax.ToString("F3") + "m @(" + aboveAt.x.ToString("F2") + ", " + aboveAt.z.ToString("F2") + ")・触らない)" : "") +
 (string.IsNullOrEmpty(thinBy) ? "" : "〔" + thinBy + "〕") +
                   (string.IsNullOrEmpty(aboveBy) ? "" : "〔埋没: " + aboveBy + "〕") +
                   " / 外形の外の地表の下がり 最大 " + dipOut.ToString("F3") + "m @(" + dipAt.x.ToString("F2") + ", " + dipAt.z.ToString("F2") + ")";
        }
    }

    /// <summary>**天端を地表と同じ高さに据えた駒の下の地形を納める。**各駒(材 <paramref name="mat"/>・null で全材)の
    /// 実メッシュの平面の外形の中にある地形の節点のうち、**真上の天端(実メッシュの上向きの面)− <paramref name="depth"/>**
    /// より高く、かつ天端 + <paramref name="coTol"/> 以下の物(= 天端と面が重なる節点)だけをそこまで下げ、外形に掛かる芝を消す。
    /// ⛔ 天端より <paramref name="coTol"/> を超えて高い節点(= 駒が土に埋まっている)は**触らない** ── 埋没は別の欠陥で、
    /// ここで掘ると外形の外まで地表が凹む(2026-09-23 実測: 条件を付けずに下げたら最大 3.29m 掘り、外の地表が 3.06m 凹んだ)。
    /// その数は <see cref="CrestTuck.above"/> に刷る。
    /// 検め(硬い・許容0): 外形の縁から <paramref name="inset"/> 以上内の 0.1m 格子で「天端 − 描かれた地表」を取り、
    /// その点と前後左右 0.1m がみな <paramref name="minGap"/> 未満の点(= 面の重なり)を <see cref="CrestTuck.thin"/> に数える
    /// (0 でなければ斑に見える)。天端を地表が斜めに横切る線は数えない。
    /// 外形の外の地表の下がりは柔らかい(報告のみ)。</summary>
    /// <para>⭐ **埋没は見える天端の帯で数える**(2026-09-24・EDO-0430 普請奉行の決め)。<paramref name="faces"/> に駒ごとの
    /// **見え面の外向き**(世界 XZ)を渡すと、地表が天端より高い点は、そこから見え面へ向かって天端の上を歩いて
    /// **見え面の縁まで覆われ続けている**ときだけ埋没に数える。途中で天端が地表から出ていれば、その点は帯の奥
    /// (上の段の土・上の壁が始まった後)で、石の控えが上の段の土の下に入る正しい納め ⇒ <see cref="CrestTuck.hidden"/>。
    /// null の駒(見え面を渡さない)は従来どおり全点を数える。当たる先: 段々に重ねた土留め(山王の郭・前庭・土台)、石段の袖。</para>
    /// <para><paramref name="measureOnly"/> = true なら地形に触らず検め(3)だけを行う(縁の皮を起こした後の埋没の数え・EDO-0430)。
    /// 検め(3)は**描かれた地表**(<see cref="Drawn"/>: 穴の升では皮)で測る。</para>
    public static CrestTuck TuckUnderCrest(IList<GameObject> pieces, string mat, float depth = 0.15f,
                                           float minGap = 0.01f, float inset = 0.10f, float coTol = 0.05f,
                                           IDictionary<GameObject, Vector3> faces = null, bool measureOnly = false)
    {
        var r = new CrestTuck { gapMin = float.NaN };
        var t = T(); var td = t.terrainData; var org = t.transform.position;
        int R = td.heightmapResolution; float cx = td.size.x / (R - 1), cz = td.size.z / (R - 1), sy = td.size.y;
        var probe = Probe();
        var hulls = new List<Vector2[]>(); var trisL = new List<List<Vector3[]>>(); var names = new List<string>();
        var faceL = new List<Vector2>();
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var g in pieces)
        {
            if (g == null) continue;
            var tris = TrisOfMat(g.transform, mat); if (tris.Count == 0) continue;
            var hull = HullOfMat(g.transform, mat); if (hull == null || hull.Length < 3) continue;
            hulls.Add(hull); trisL.Add(tris); names.Add(g.name); r.pieces++;
            Vector3 fv; faceL.Add(faces != null && faces.TryGetValue(g, out fv) ? new Vector2(fv.x, fv.z).normalized : Vector2.zero);
            foreach (var p in hull) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        }
        if (r.pieces == 0) return r;
        Func<List<Vector3[]>, float, float, float> Top = (tris, x, z) =>
        {
            float best = float.NaN, y;
            foreach (var q in tris) if (TriYAt(q, x, z, out y) && (float.IsNaN(best) || y > best)) best = y;
            return best;
        };
        // 天端と地表が**面で**重なっているか ── その点と前後左右 0.1m がみな |天端 − 地表| < minGap。
        //   ⭐ 線(天端の面取り・斜めの地表が天端を横切る所)は 0.1m で差が数 cm 変わるので数えない ── 斑に見えるのは面だけ。
        GroundProbe pr = probe;
        Func<float, float, float> gAt = (xx, zz) => pr.At(xx, zz);   // 検め(3)では描かれた地表へ差し替える
        Func<int, float, float, bool> Sheet = (k, x, z) =>
        {
            for (int d = 0; d < 5; d++)
            {
                float xx = x + (d == 1 ? 0.1f : d == 2 ? -0.1f : 0f), zz = z + (d == 3 ? 0.1f : d == 4 ? -0.1f : 0f);
                float top = Top(trisL[k], xx, zz); if (float.IsNaN(top)) return false;
                float gg = gAt(xx, zz);
                if (float.IsNaN(gg) || Mathf.Abs(top - gg) >= minGap) return false;
            }
            return true;
        };

        // 外形の外の地表の下がりを量るための「前」(外形の 1 セル外の輪まで・0.25m 格子)
        const float RING = 0.25f;
        var before = new List<Vector3>();
        const float STEP = 0.1f;
        if (!measureOnly)
        {
        Func<Vector2, bool> InAny = p => { foreach (var h in hulls) if (EdoGeom.PIP(h, p)) return true; return false; };
        for (float x = mnx - cx; x <= mxx + cx; x += RING)
            for (float z = mnz - cz; z <= mxz + cz; z += RING)
                if (!InAny(new Vector2(x, z))) before.Add(new Vector3(x, probe.At(x, z), z));

        // 1 節点を下げる
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - org.x) / cx), 0, R - 1), i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - org.x) / cx), 0, R - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - org.z) / cz), 0, R - 1), j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - org.z) / cz), 0, R - 1);
        int w = i1 - i0 + 1, hh = j1 - j0 + 1;
        var H = td.GetHeights(i0, j0, w, hh);                    // [z, x](高さは寸法の名札どおり)
        var H0 = (float[,])H.Clone();                           // 元の高さ ── 下げる条件は必ずこれで判定する(連鎖させない)
        for (int j = 0; j < hh; j++)
            for (int i = 0; i < w; i++)
            {
                var p = new Vector2(org.x + (i0 + i) * cx, org.z + (j0 + j) * cz);
                float lim = float.NaN, crest = float.NaN;
                for (int k = 0; k < hulls.Count; k++)
                {
                    if (!EdoGeom.PIP(hulls[k], p)) continue;
                    float top = Top(trisL[k], p.x, p.y); if (float.IsNaN(top)) continue;
                    if (float.IsNaN(crest) || top < crest) { crest = top; lim = top - depth; }
                }
                if (float.IsNaN(lim)) continue;
                r.nodes++;
                float cur = H[j, i] * sy + org.y;
                if (cur <= lim + 1e-3f) continue;                            // 下げ済み(高さの量子化ぶんの許容 ── 流し直しで数えない)
                if (cur > crest + coTol) { r.aboveNodes++; continue; }       // 埋没 ⛔ 触らない
                r.maxDrop = Mathf.Max(r.maxDrop, cur - lim);
                H[j, i] = Mathf.Clamp01((lim - org.y) / sy); r.lowered++;
            }
        if (r.lowered > 0) { td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap(); }

        // 1b 外形の縁・節点の無い細い駒 ── 天端の下が**外形の外の節点**で張られていて、まだ面が重なる所は、
        //    その点のセルの四隅のうち**元の高さが**天端と重なる節点を下げる(外の地表が最大 depth + coTol 下がる・柔らかい・dipOut に刷る)。
        //    ⛔ 条件を今の高さで見ない ── 下げた隣の点がまた「重なる」になり、斜面を連鎖して掘る(2026-09-23 実測: 3 巡で 0.75m)。
        for (int pass = 0; pass < 3; pass++)
        {
            probe = Probe(); pr = probe;
            int more = 0;
            for (int k = 0; k < hulls.Count; k++)
            {
                var h = hulls[k];
                float hx0 = float.MaxValue, hx1 = float.MinValue, hz0 = float.MaxValue, hz1 = float.MinValue;
                foreach (var p in h) { hx0 = Mathf.Min(hx0, p.x); hx1 = Mathf.Max(hx1, p.x); hz0 = Mathf.Min(hz0, p.y); hz1 = Mathf.Max(hz1, p.y); }
                for (float x = hx0 + STEP * 0.5f; x < hx1; x += STEP)
                    for (float z = hz0 + STEP * 0.5f; z < hz1; z += STEP)
                    {
                        var p = new Vector2(x, z);
                        if (!EdoGeom.PIP(h, p) || EdgeDist(h, p) < inset) continue;
                        float top = Top(trisL[k], x, z); if (float.IsNaN(top)) continue;
                        if (!Sheet(k, x, z)) continue;
                        int ci = Mathf.FloorToInt((x - org.x) / cx) - i0, cj = Mathf.FloorToInt((z - org.z) / cz) - j0;
                        for (int dj = 0; dj <= 1; dj++)
                            for (int di = 0; di <= 1; di++)
                            {
                                int ii = ci + di, jj = cj + dj;
                                if (ii < 0 || jj < 0 || ii >= w || jj >= hh) continue;
                                float orig = H0[jj, ii] * sy + org.y, cur = H[jj, ii] * sy + org.y, lim = top - depth;
                                if (orig <= lim + 1e-3f || orig > top + coTol || cur <= lim + 1e-3f) continue;
                                r.maxDrop = Mathf.Max(r.maxDrop, orig - lim);
                                H[jj, ii] = Mathf.Clamp01((lim - org.y) / sy); more++;
                            }
                    }
            }
            if (more == 0) break;
            r.lowered += more;
            td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        }

        // 2 芝を消す
        //   ⭐ **芝のセルごと**に決める: セルと外形の重なりのどこかで地表が天端 + coTol 以下(= 天端が地表から出ている)なら消す。
        //   ⛔ 埋まっている所(地表が天端 + coTol より高い)の芝は見えている地表の芝なので消さない。
        //   ⛔ 駒の中点ひとつで駒ごと飛ばさない ── 一部が埋まった駒の出ている所に芝が残った(2026-09-23 普請検査・TW_Zentei_W_007f)。
        probe = Probe();
        for (int k = 0; k < hulls.Count; k++)
        {
            var hk = hulls[k]; var tk = trisL[k]; var pk = probe;
            Func<Vector2, Vector2, bool> exposed = (lo, hi) =>
            {
                const int N = 5;
                for (int a = 0; a < N; a++)
                    for (int b = 0; b < N; b++)
                    {
                        float x = Mathf.Lerp(lo.x, hi.x, (a + 0.5f) / N), z = Mathf.Lerp(lo.y, hi.y, (b + 0.5f) / N);
                        if (!EdoGeom.PIP(hk, new Vector2(x, z))) continue;
                        float top = Top(tk, x, z); if (float.IsNaN(top)) continue;
                        if (pk.At(x, z) <= top + coTol) return true;
                    }
                return false;
            };
            var c = ClearDetailIn(hk, exposed); r.detVisited += c.visited; r.detChanged += c.changed; r.det = c;
        }
        }   // !measureOnly

        // 3 検め ── 天端 − 描かれた地表(外形の縁から inset 以上内)・外形の外の下がり
        //   ⭐ 描かれた地表 = 縁の皮の升では皮(<see cref="Drawn"/>・EDO-0430)。皮が無ければ地形と同じ。
        probe = Probe(); pr = probe;
        var dg = Drawn(); gAt = dg.At;
        var thinN = new Dictionary<string, int>();
        var abN = new Dictionary<string, int>(); var abD = new Dictionary<string, float>();
        // ⭐ 天端の帯(2026-09-24): 見え面を渡された駒は、各点の「見え面の向きの列」で天端の最高 − CREST_BAND より低い点を
        //   **面(法)**とみなし埋没に数えない(城の石垣の法の下部は根入れで地中にあるのが正)。天端の点が覆われていれば、
        //   見え面へ向かって天端の上を歩き、天端が地表から出る点に会えば帯の奥(hidden)、会わずに天端が尽きれば埋没。
        const float CREST_BAND = 0.10f;
        for (int k = 0; k < hulls.Count; k++)
        {
            var h = hulls[k];
            float hx0 = float.MaxValue, hx1 = float.MinValue, hz0 = float.MaxValue, hz1 = float.MinValue;
            foreach (var p in h) { hx0 = Mathf.Min(hx0, p.x); hx1 = Mathf.Max(hx1, p.x); hz0 = Mathf.Min(hz0, p.y); hz1 = Mathf.Max(hz1, p.y); }
            int nx = Mathf.Max(1, Mathf.CeilToInt((hx1 - hx0) / STEP)), nz = Mathf.Max(1, Mathf.CeilToInt((hz1 - hz0) / STEP));
            var TA = new float[nx, nz]; var GA = new float[nx, nz];
            for (int ix = 0; ix < nx; ix++)
                for (int iz = 0; iz < nz; iz++)
                {
                    TA[ix, iz] = float.NaN;
                    float x = hx0 + (ix + 0.5f) * STEP, z = hz0 + (iz + 0.5f) * STEP; var p = new Vector2(x, z);
                    if (!EdoGeom.PIP(h, p) || EdgeDist(h, p) < inset) continue;
                    float top = Top(trisL[k], x, z); if (float.IsNaN(top)) continue;
                    float gd = dg.At(x, z);
                    TA[ix, iz] = top; GA[ix, iz] = float.IsNaN(gd) ? float.NegativeInfinity : gd;
                }
            Vector2 fd = faceL[k];
            // 列の天端の最高(見え面の向きに前後へ)
            Func<Vector2, float> ColMax = (p0) =>
            {
                float mx = float.NaN;
                for (int sgn = -1; sgn <= 1; sgn += 2)
                    for (float m = 0f; m < 20f; m += STEP)
                    {
                        var q = p0 + fd * (m * sgn);
                        int qx = Mathf.FloorToInt((q.x - hx0) / STEP), qz = Mathf.FloorToInt((q.y - hz0) / STEP);
                        if (qx < 0 || qz < 0 || qx >= nx || qz >= nz) break;
                        float tq = TA[qx, qz]; if (float.IsNaN(tq)) continue;
                        if (float.IsNaN(mx) || tq > mx) mx = tq;
                    }
                return mx;
            };
            for (int ix = 0; ix < nx; ix++)
                for (int iz = 0; iz < nz; iz++)
                {
                    float top = TA[ix, iz]; if (float.IsNaN(top)) continue;
                    float x = hx0 + (ix + 0.5f) * STEP, z = hz0 + (iz + 0.5f) * STEP; var p = new Vector2(x, z);
                    float gap = top - GA[ix, iz];
                    r.samples++;
                    if (gap < -coTol)
                    {
                        // 見える天端の帯か: 見え面へ向かって歩き、縁まで覆われ続けるなら埋没
                        if (fd != Vector2.zero)
                        {
                            float cm = ColMax(p);
                            if (!float.IsNaN(cm) && top < cm - CREST_BAND) { r.faceIn++; continue; }   // 法(面)の根入れ ── 天端ではない
                            bool open = false;
                            for (float m = STEP; m < 20f; m += STEP)
                            {
                                var q = p + fd * m;
                                int qx = Mathf.FloorToInt((q.x - hx0) / STEP), qz = Mathf.FloorToInt((q.y - hz0) / STEP);
                                if (qx < 0 || qz < 0 || qx >= nx || qz >= nz) break;
                                float tq = TA[qx, qz]; if (float.IsNaN(tq)) break;
                                if (tq < cm - CREST_BAND) break;                         // 天端が尽きた(法へ入った)
                                if (tq - GA[qx, qz] >= -coTol) { open = true; break; }
                            }
                            if (open) { r.hidden++; continue; }
                        }
                        r.above++;
                        { int a0; abN.TryGetValue(names[k], out a0); abN[names[k]] = a0 + 1;
                          float d0; abD.TryGetValue(names[k], out d0); abD[names[k]] = Mathf.Max(d0, -gap); }
                        if (-gap > r.aboveMax) { r.aboveMax = -gap; r.aboveAt = new Vector3(x, top, z); }
                        continue;
                    }
                    if (gap < minGap && Sheet(k, x, z)) { r.thin++; int n0; thinN.TryGetValue(names[k], out n0); thinN[names[k]] = n0 + 1; }
                    if (float.IsNaN(r.gapMin) || gap < r.gapMin) { r.gapMin = gap; r.gapAt = new Vector3(x, top, z); }
                }
        }
        var tl = new List<KeyValuePair<string, int>>(thinN); tl.Sort((x, y) => y.Value.CompareTo(x.Value));
        var ts = new List<string>(); for (int i = 0; i < tl.Count && i < 5; i++) ts.Add(tl[i].Key + " " + tl[i].Value);
        r.thinBy = string.Join("・", ts);
        var al = new List<KeyValuePair<string, int>>(abN); al.Sort((x, y) => y.Value.CompareTo(x.Value));
        var ab = new List<string>(); for (int i = 0; i < al.Count && i < 8; i++) ab.Add(al[i].Key + " " + al[i].Value + "点/" + abD[al[i].Key].ToString("F2") + "m");
        r.aboveBy = string.Join("・", ab);
        foreach (var q in before)
        {
            float d = q.y - probe.At(q.x, q.z);
            if (d > r.dipOut) { r.dipOut = d; r.dipAt = q; }
        }
        return r;
    }

    /// <summary>点 p から多角形の辺までの最短距離。</summary>
    static float EdgeDist(Vector2[] poly, Vector2 p)
    {
        float best = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length], ab = b - a;
            float l2 = ab.sqrMagnitude;
            float tt = l2 < 1e-12f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2);
            best = Mathf.Min(best, Vector2.Distance(p, a + ab * tt));
        }
        return best;
    }
}
