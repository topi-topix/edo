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
}
