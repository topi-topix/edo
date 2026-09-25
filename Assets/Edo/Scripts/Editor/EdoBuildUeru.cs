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
    /// ⛔ 基準点(ピボット)の高さは使わない。⛔ 谷側の樹冠の下の隙を浮きと数えない。当たりが測れなければ false(NaN を返す)。</summary>
    public static bool SeatPlant(GameObject go, float sink, out float bury, out float flt,
                                 float buryMax = 1.0f, float floatMax = 0.7f, float footBand = 0.3f,
                                 int maxSamples = 60000)
    {
        bury = flt = float.NaN;
        var pts = GroundCandidates(go.transform, maxSamples);
        if (pts.Count == 0) return false;
        var probe = Probe();
        Vector3 up = go.transform.up;
        float hmin = float.MaxValue;
        foreach (var p in pts) hmin = Mathf.Min(hmin, Vector3.Dot(p, up));
        float cmin = float.MaxValue, fmin = float.MaxValue;   // 全部の当たりの最小の隙 / 根元の当たりの最小の隙
        foreach (var p in pts)
        {
            float c = p.y - probe.At(p.x, p.z);
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
    // ⭕ 幹の足 = LOD0 のメッシュ頂点のうち、局所の上向きで最も低い帯(<see cref="SeatPlant"/> の footBand と
    //    同じ 0.3m)の水平の中心(帯の頂点の xz の外接矩形の中点)。点に来るのはこの中心であってピボットではない。
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

    /// <summary>頂点の群(ルートの枠)から幹の足の中心(xz)と足元の高さ(y)を。</summary>
    public static bool TrunkFootOf(List<Vector3> pts, out Vector2 foot, out float yFoot)
    {
        foot = Vector2.zero; yFoot = 0f;
        if (pts == null || pts.Count == 0) return false;
        float ymin = float.MaxValue;
        foreach (var p in pts) if (p.y < ymin) ymin = p.y;
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var p in pts)
        {
            if (p.y > ymin + TrunkFootBand) continue;
            x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); z0 = Mathf.Min(z0, p.z); z1 = Mathf.Max(z1, p.z);
        }
        foot = new Vector2((x0 + x1) * 0.5f, (z0 + z1) * 0.5f); yFoot = ymin;
        return true;
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
            TrunkFootOf(Lod0PointsRootFrame(inst), out f, out yf);
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
        if (!TrunkFootOf(Lod0PointsRootFrame(go), out f, out yf)) return false;
        foot = go.transform.position + go.transform.rotation * new Vector3(f.x, yf, f.y);
        return true;
    }

    /// <summary>幹の足の中心を <paramref name="trunkXZ"/> へ寄せてから <see cref="SeatPlant"/> で据える。
    /// ⛔ ピボットを点へ置かない。傾いた木も幹の足が点に来る(水平に寄せるだけなので SeatPlant の鉛直の据えと独立)。</summary>
    public static bool SeatPlantAt(GameObject go, Vector2 trunkXZ, float sink, out float bury, out float flt,
                                   float buryMax = 1.0f, float floatMax = 0.7f)
    {
        Vector3 f;
        if (TrunkFootWorld(go, out f))
            go.transform.position += new Vector3(trunkXZ.x - f.x, 0f, trunkXZ.y - f.z);
        return SeatPlant(go, sink, out bury, out flt, buryMax, floatMax, TrunkFootBand);
    }
}
