// 配置・資産系の共有基盤 (Phase 2c, 2026-08-26)
//   EdoNishiTameikeBuilder (1305行の屋敷ビルダー) に埋まっていた共有ヘルパの本体をここへ移した。
//   NT 側はシグネチャ温存の1行委譲を残しており、NT を参照する既存16ファイルは無変更で動く。
//   各ビルダーの Ground 委譲チェーン (Shinmachi→Tamachi→TameikeKita 等) はここへ1段化済み。
//   ⛔ NagayaRun / DobeiRun / NaturalMode は既知の欠陥・状態込みで NT に残す (統一は別 Phase・ユーザー確認付き)。
using System;
using UnityEditor;
using UnityEngine;

public static class EdoBuild
{
    /// <summary>アクティブな Terrain (最初の1枚)。無ければ例外。</summary>
    public static Terrain T()
    {
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy) return t;
        throw new Exception("no active terrain");
    }

    /// <summary>live terrain の標高 (m)。⚠ 造成が乗る作業面 — 造成前の地盤は docs/Sashizu/base_dem.json が正典。</summary>
    public static float Ground(float x, float z) { var t = T(); return t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y; }

    static GameObject Load(string path)
    {
        var a = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (a == null) throw new Exception("asset not found: " + path);
        return a;
    }

    /// <summary>プレハブを実体化して置く。パスは EdoAssets 経由で渡すこと (規則11)。</summary>
    public static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = scale;
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }

    /// <summary>子孫 Renderer 全体のワールド Bounds。</summary>
    public static Bounds RB(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }

    /// <summary>Bounds の底面を y に据える。</summary>
    public static void SeatBottom(GameObject go, float y)
    {
        var b = RB(go);
        go.transform.position += new Vector3(0, y - b.min.y, 0);
    }

    /// <summary>it のローカル座標系での mesh 頂点 footprint (OBB)。Jubo/ToranomonUchi/TodaBlock のバイト同一実装を移設。</summary>
    public static void ObbFootprint(Transform it, out float mnx, out float mxx, out float mnz, out float mxz, out float mny)
    {
        mnx = float.MaxValue; mxx = float.MinValue; mnz = float.MaxValue; mxz = float.MinValue; mny = float.MaxValue;
        foreach (var mf in it.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var vts = mesh.vertices;
            for (int i = 0; i < vts.Length; i++)
            {
                var lp = it.InverseTransformPoint(mf.transform.TransformPoint(vts[i]));
                mnx = Mathf.Min(mnx, lp.x); mxx = Mathf.Max(mxx, lp.x);
                mnz = Mathf.Min(mnz, lp.z); mxz = Mathf.Max(mxz, lp.z);
                mny = Mathf.Min(mny, lp.y);
            }
        }
    }
}
