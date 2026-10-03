// 植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401)
//
// ⭐ **何が足りなかったか**: 山王の社叢(EdoSannoShaRebuild.Stage7_Shaso)は下層の木を
//    「ピボットを点の地表の高さへ置く」だけで据えていた(⛔ 規則21 — 基準点で位置を決めない)。
//    勾配 56〜79° の崖では山側の枝葉が地中へ 1.0〜1.8m 潜り、完成の表の「埋没・浮き」が赤になった。
//
// ⛔ **初版の誤り(c68f7959・同日に流して判明)**: 「当たりの浮き」を**全部の当たりの最大**で数え、
//    それを 0.7 に抑えるため木ごと下げていた。斜面では谷側の樹冠の下は地面から何mも離れているのが
//    当たり前で(浮きではない)、下げた結果 名指しの木 20 本が 14.8〜20.9m・下層 759/870 本が埋まった。
//    浮き・埋没は完成の表(GroundQA / Contact)と同じく**最も低い当たり1つ**の隙で数える
//    (docs/oki-kata.md §3・§4)。谷側の樹冠と地面の間は測らない。
//
// ⭕ <see cref="SeatPlant"/> — 触れている箇所は2種ある:
//    ・**根元**(局所の上向きで最も低い帯 = 幹の足・根張り)── これを地表へ着ける
//    ・**枝葉の当たり**(格子ごとの最下点・EdoBuild.GroundCandidates)── 斜面の山側では根元より先に地面へ当たる
//    1) 根元の最も低い当たりを地表へ(sink だけ潜らせる)。
//    2) 山側の枝葉の埋没が buryMax を超えるなら、超えた分だけ持ち上げる(根元はその分浮く)。
//    3) 根元の浮き(根元の当たりの最小の隙)が floatMax を超えれば**据えられない**と返す
//       (⛔ 黙って浮かせない・埋めない — 呼び手が数えて刷る)。閾値は完成の表と同じ数(規則4 の許容0)。
//    〔硬い制約〕埋没 ≤ buryMax・根元の浮き ≤ floatMax。据わらない木は置いたうえで名指しする。
//
// 当たる先: SeatPlant を呼ぶ所すべて(今は山王の社叢の下層と名指しの木 = Stage7_Shaso だけ)。
//   類型の庭の NiwaField.Put は SeatOnGround+起伏の据え直し+Contact で据えていて、同じ「谷側の樹冠を
//   浮きと数える」誤りは持たない(最小の隙で数えている)。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>植木を足元の当たりで据える。戻り値 = 埋没 ≤ <paramref name="buryMax"/> かつ 根元の浮き ≤ <paramref name="floatMax"/>
    /// で据わったか。<paramref name="bury"/> = 最も深い当たり(枝葉を含む)の埋没[m]、<paramref name="flt"/> = 根元の浮き[m]
    /// (根元の当たりのうち最も地面に近い所の隙。負なら根元は地中)。
    /// 根元 = 局所の上向き(transform.up)で最も低い当たりから <paramref name="footBand"/> 以内の当たり。
    /// ⛔ 基準点(ピボット)の高さは使わない。⛔ 谷側の樹冠の下の隙を浮きと数えない。当たりが測れなければ false(NaN を返す)。
    /// <paramref name="drawn"/> = 描かれた地表の掴み(<see cref="Drawn"/>)。⭐ 縁の皮を起こした邸では**皮の後に一度だけ作って渡す** ──
    /// 渡さなければ地形の格子(heightmap)で引き、皮の上で浮き 0.44・埋まり 0.26 が出た(岡部 第6巡・266 本・EDO-0502)。
    /// 皮の無い所・皮の升の継ぎ目(NaN)は地形で引く。当たる先: 皮のある邸で木を GameObject で据える所(岡部 Stage5・山王 Stage7 の名指しの木)。</summary>
    public static bool SeatPlant(GameObject go, float sink, out float bury, out float flt,
                                 float buryMax = 1.0f, float floatMax = 0.7f, float footBand = 0.3f,
                                 int maxSamples = 60000, DrawnGround drawn = null)
    {
        bury = flt = float.NaN;
        var pts = GroundCandidates(go.transform, maxSamples);
        if (pts.Count == 0) return false;
        var probe = Probe();
        System.Func<float, float, float> G = (x, z) =>
        {
            if (drawn == null) return probe.At(x, z);
            float d = drawn.At(x, z); return float.IsNaN(d) ? probe.At(x, z) : d;
        };
        Vector3 up = go.transform.up;
        float hmin = float.MaxValue;
        foreach (var p in pts) hmin = Mathf.Min(hmin, Vector3.Dot(p, up));
        float cmin = float.MaxValue, fmin = float.MaxValue;   // 全部の当たりの最小の隙 / 根元の当たりの最小の隙
        foreach (var p in pts)
        {
            float c = p.y - G(p.x, p.z);
            if (c < cmin) cmin = c;
            if (Vector3.Dot(p, up) <= hmin + footBand && c < fmin) fmin = c;
        }
        float dy = -sink - fmin;                          // 1) 根元を地表へ
        if (-(cmin + dy) > buryMax) dy = -buryMax - cmin; // 2) 山側の枝葉が埋まりすぎるなら持ち上げる
        go.transform.position += new Vector3(0f, dy, 0f);
        bury = Mathf.Max(0f, -(cmin + dy));
        flt = fmin + dy;
        return bury <= buryMax + 1e-4f && flt <= floatMax + 1e-4f;
    }

    // ── 幹の足(2026-09-25・EDO-0409)──────────────────────────────────────────────
    // ⭐ **何が足りなかったか**: 社叢の木は点へ**ピボット**を置いていた(⛔ 規則21)。部材によって幹の足は
    //    ピボットから最大 0.315m 離れていて、道辺 2m・芯々 1m の検めが実物の幹で外れた。
    // ⛔ **初版の誤り(18ac81b4)**: 「LOD0 の全頂点の最も低い 0.3m の帯の中点」は、紅葉6本・蔓7本で地面近くまで
    //    垂れる枝葉と根張りを拾い、幹から最大 0.39m 外れた(Tree_Momiji_Small_03)。
    // ⭕ 幹の足 = **地面に立つ幹そのものの断面の中心**(<see cref="TrunkFootOf(GameObject, out Vector2, out float)"/>):
    //    1) 幹 = LOD0 の樹皮の材(材の名に "bark")のサブメッシュだけ(無い部材は全部)── 葉の材は見ない。
    //    2) 幹の底の開口(境界の輪)が最も低い樹皮の頂点を通り、輪の形なら、その外接矩形の中点(榎・欅・松・椋…)。
    //    3) 輪が無い・潰れている(紅葉の根張り・蔓の閉じた茎)なら、樹皮の最も低い頂点から 0.02m 上の水平断面の
    //       切り口のうち、最も低い頂点に近い群(= 地面に立つ幹・茎の一本)の外接矩形の中点。
    //       (0.05m では紅葉の根張りの付け根を拾い 0.07m 外れた。蔓は茎が2〜4本あり、最も低い1本を採る)
    //    点に来るのはこの中心であってピボットではない。足元の高さは従来どおり LOD0 全頂点の最下。
    // 当たる先: 地形の木として植える所(山王 Stage7・EdoTrees.Plant)と GameObject で据える木(山王の名指しの木)。
    //   類型の庭(NiwaField.Put)はまだピボットで置いている ── 同じ型で直す番が来たら SeatPlantAt を呼ぶ。
    public const float TrunkFootBand = 0.3f;

    /// <summary>LOD0 の MeshFilter(LODGroup が無ければ見えている全部)。</summary>
    public static List<MeshFilter> Lod0Filters(GameObject root)
    {
        var L = new List<MeshFilter>();
        var lg = root.GetComponentInChildren<LODGroup>(true);
        if (lg != null)
        {
            var lods = lg.GetLODs();
            if (lods.Length > 0)
                foreach (var r in lods[0].renderers)
                {
                    if (r == null) continue;
                    var mf = r.GetComponent<MeshFilter>();
                    if (mf != null && mf.sharedMesh != null) L.Add(mf);
                }
            if (L.Count > 0) return L;
        }
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null) continue;
            L.Add(mf);
        }
        return L;
    }

    /// <summary>LOD0 の全頂点を「ルートの回転と位置を外した枠」(= 世界の m・ルートの向き)で。
    /// ルートの scale は掛かったまま(据えた木では据えた大きさの m になる。資産ではルートの scale = 1 の実寸)。</summary>
    public static List<Vector3> Lod0PointsRootFrame(GameObject root)
    {
        var L = new List<Vector3>();
        var tr = root.transform;
        var inv = Quaternion.Inverse(tr.rotation);
        foreach (var mf in Lod0Filters(root))
        {
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            foreach (var v in vs) L.Add(inv * (l2w.MultiplyPoint3x4(v) - tr.position));
        }
        return L;
    }

    public const float TrunkFootSlab = 0.02f;

    /// <summary>幹の足の中心(ルートの枠の xz)と足元の高さ(y = LOD0 全頂点の最下)。定義は上の節の 1)〜3)。
    /// ルートの枠 = <see cref="Lod0PointsRootFrame"/> と同じ(回転と位置を外し scale は掛かったまま)。</summary>
    public static bool TrunkFootOf(GameObject root, out Vector2 foot, out float yFoot)
    {
        foot = Vector2.zero; yFoot = 0f;
        var tr = root.transform; var inv = Quaternion.Inverse(tr.rotation);
        var fs = Lod0Filters(root);
        bool anyBark = false;
        foreach (var mf in fs)
            foreach (var mt in mf.GetComponent<Renderer>().sharedMaterials)
                if (mt != null && mt.name.ToLowerInvariant().Contains("bark")) anyBark = true;

        var P = new List<Vector3>(); var T = new List<int>();
        float yAll = float.MaxValue;
        foreach (var mf in fs)
        {
            var m = mf.sharedMesh; var mats = mf.GetComponent<Renderer>().sharedMaterials;
            var l2w = mf.transform.localToWorldMatrix; var vs = m.vertices;
            foreach (var v in vs) { float y = (inv * (l2w.MultiplyPoint3x4(v) - tr.position)).y; if (y < yAll) yAll = y; }
            var map = new Dictionary<int, int>();
            for (int s = 0; s < m.subMeshCount; s++)
            {
                if (m.GetTopology(s) != MeshTopology.Triangles) continue;
                var mt = s < mats.Length ? mats[s] : null;
                if (anyBark && (mt == null || !mt.name.ToLowerInvariant().Contains("bark"))) continue;
                foreach (var i in m.GetIndices(s))
                {
                    int g;
                    if (!map.TryGetValue(i, out g)) { g = P.Count; map[i] = g; P.Add(inv * (l2w.MultiplyPoint3x4(vs[i]) - tr.position)); }
                    T.Add(g);
                }
            }
        }
        if (P.Count == 0) return false;
        yFoot = yAll;

        // 同じ位置(1mm)の頂点を一つに(UV の継ぎ目で割れた頂点)
        var weld = new Dictionary<Vector3Int, int>(); var W = new int[P.Count];
        for (int i = 0; i < P.Count; i++)
        {
            var k = new Vector3Int(Mathf.RoundToInt(P[i].x * 1000f), Mathf.RoundToInt(P[i].y * 1000f), Mathf.RoundToInt(P[i].z * 1000f));
            int w; if (!weld.TryGetValue(k, out w)) { w = i; weld[k] = i; } W[i] = w;
        }
        int lo = -1; float ymin = float.MaxValue;
        for (int i = 0; i < P.Count; i++) if (P[i].y < ymin) { ymin = P[i].y; lo = W[i]; }

        // 辺の数え(1つの三角形にしか使われない辺 = 境界)
        var edgeUse = new Dictionary<long, int>();
        for (int t = 0; t + 2 < T.Count; t += 3)
            for (int e = 0; e < 3; e++)
            {
                int a = W[T[t + e]], b = W[T[t + (e + 1) % 3]]; if (a == b) continue;
                long key = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a;
                int c; edgeUse.TryGetValue(key, out c); edgeUse[key] = c + 1;
            }

        // 2) 幹の底の開口
        var bAdj = new Dictionary<int, List<int>>();
        foreach (var kv in edgeUse)
            if (kv.Value == 1) { int a = (int)(kv.Key >> 32), b = (int)(kv.Key & 0xffffffffL); AddAdj(bAdj, a, b); AddAdj(bAdj, b, a); }
        int lb = -1; float yb = float.MaxValue;
        foreach (var k in bAdj.Keys) if (P[k].y < yb) { yb = P[k].y; lb = k; }
        if (lb >= 0 && yb <= ymin + 0.02f)
        {
            var loop = Flood(bAdj, lb);
            Rect r = XZRect(P, loop);
            float big = Mathf.Max(r.width, r.height), small = Mathf.Min(r.width, r.height);
            if (loop.Count >= 5 && small >= 0.5f * big && small > 0.01f)
            { foot = r.center; return true; }
        }

        // 3) 最も低い樹皮の頂点から TrunkFootSlab 上の水平断面。切り口の点を 0.06m で繋いだ群のうち
        //    最も低い頂点に近い群(= 地面に立つ幹・茎の一本)の外接矩形の中点
        float Y = ymin + TrunkFootSlab;
        var cut = new List<Vector2>();
        for (int t = 0; t + 2 < T.Count; t += 3)
            for (int e = 0; e < 3; e++)
            {
                Vector3 a = P[T[t + e]], b = P[T[t + (e + 1) % 3]];
                if ((a.y - Y) * (b.y - Y) >= 0f) continue;
                float u = (Y - a.y) / (b.y - a.y);
                cut.Add(new Vector2(a.x + (b.x - a.x) * u, a.z + (b.z - a.z) * u));
            }
        var seedXZ = new Vector2(P[lo].x, P[lo].z);
        if (cut.Count == 0) { foot = seedXZ; return true; }
        foot = CutGroupNearest(cut, seedXZ, 0.06f).center;
        return true;
    }

    /// <summary>断面の切り口の点を <paramref name="link"/> で繋いだ群のうち、<paramref name="seed"/> に最も近い点を含む群の外接矩形。</summary>
    public static Rect CutGroupNearest(List<Vector2> cut, Vector2 seed, float link)
    {
        int s0 = 0; float d0 = float.MaxValue;
        for (int i = 0; i < cut.Count; i++) { float d = (cut[i] - seed).sqrMagnitude; if (d < d0) { d0 = d; s0 = i; } }
        var inG = new bool[cut.Count]; inG[s0] = true; var st = new Stack<int>(); st.Push(s0);
        float l2 = link * link;
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        while (st.Count > 0)
        {
            int a = st.Pop(); var q = cut[a];
            x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y);
            for (int b = 0; b < cut.Count; b++) if (!inG[b] && (cut[b] - q).sqrMagnitude < l2) { inG[b] = true; st.Push(b); }
        }
        return Rect.MinMaxRect(x0, z0, x1, z1);
    }

    static void AddAdj(Dictionary<int, List<int>> adj, int a, int b)
    {
        List<int> l; if (!adj.TryGetValue(a, out l)) { l = new List<int>(); adj[a] = l; } l.Add(b);
    }
    static HashSet<int> Flood(Dictionary<int, List<int>> adj, int seed)
    {
        var seen = new HashSet<int> { seed }; var st = new Stack<int>(); st.Push(seed);
        while (st.Count > 0) { List<int> l; if (!adj.TryGetValue(st.Pop(), out l)) continue; foreach (var b in l) if (seen.Add(b)) st.Push(b); }
        return seen;
    }
    static Rect XZRect(List<Vector3> P, IEnumerable<int> ids)
    {
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var i in ids) { x0 = Mathf.Min(x0, P[i].x); x1 = Mathf.Max(x1, P[i].x); z0 = Mathf.Min(z0, P[i].z); z1 = Mathf.Max(z1, P[i].z); }
        return Rect.MinMaxRect(x0, z0, x1, z1);
    }

    static readonly Dictionary<string, Vector2> _trunkFootCache = new Dictionary<string, Vector2>();

    /// <summary>部材の幹の足の中心(部材の局所 xz・scale 1・m)。部材ごとにキャッシュ。測れなければ (0,0)。</summary>
    public static Vector2 TrunkFootLocal(string prefabPath)
    {
        Vector2 f;
        if (_trunkFootCache.TryGetValue(prefabPath, out f)) return f;
        var go = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        f = Vector2.zero;
        if (go != null)
        {
            var inst = UnityEngine.Object.Instantiate(go);
            inst.hideFlags = HideFlags.HideAndDontSave;
            inst.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            inst.transform.localScale = Vector3.one;
            float yf;
            TrunkFootOf(inst, out f, out yf);
            UnityEngine.Object.DestroyImmediate(inst);
        }
        _trunkFootCache[prefabPath] = f;
        return f;
    }
    public static Vector2 TrunkFootLocal(GameObject prefab)
    {
        var p = prefab == null ? null : AssetDatabase.GetAssetPath(prefab);
        return string.IsNullOrEmpty(p) ? Vector2.zero : TrunkFootLocal(p);
    }

    /// <summary>地形の木(TreeInstance)のピボットの世界 xz = 点 − R(rotation)·(幹の足 × widthScale)。
    /// <paramref name="rotationRad"/> は TreeInstance.rotation(ラジアン・鉛直軸まわり)。</summary>
    public static Vector2 TreePivotForTrunk(Vector2 point, Vector2 footLocal, float widthScale, float rotationRad)
    {
        var d = Quaternion.AngleAxis(rotationRad * Mathf.Rad2Deg, Vector3.up) *
                new Vector3(footLocal.x * widthScale, 0f, footLocal.y * widthScale);
        return new Vector2(point.x - d.x, point.y - d.z);
    }

    /// <summary>据えた木の幹の足の中心(世界)。傾き・scale は据えたとおり(帯は上向きに 0.3m)。</summary>
    public static bool TrunkFootWorld(GameObject go, out Vector3 foot)
    {
        foot = Vector3.zero;
        Vector2 f; float yf;
        if (!TrunkFootOf(go, out f, out yf)) return false;
        foot = go.transform.position + go.transform.rotation * new Vector3(f.x, yf, f.y);
        return true;
    }

    /// <summary>幹の足の中心を <paramref name="trunkXZ"/> へ寄せてから <see cref="SeatPlant"/> で据える。
    /// ⛔ ピボットを点へ置かない。傾いた木も幹の足が点に来る(水平に寄せるだけなので SeatPlant の鉛直の据えと独立)。</summary>
    public static bool SeatPlantAt(GameObject go, Vector2 trunkXZ, float sink, out float bury, out float flt,
                                   float buryMax = 1.0f, float floatMax = 0.7f, DrawnGround drawn = null)
    {
        Vector3 f;
        if (TrunkFootWorld(go, out f))
            go.transform.position += new Vector3(trunkXZ.x - f.x, 0f, trunkXZ.y - f.z);
        return SeatPlant(go, sink, out bury, out flt, buryMax, floatMax, TrunkFootBand, 60000, drawn);
    }
}
