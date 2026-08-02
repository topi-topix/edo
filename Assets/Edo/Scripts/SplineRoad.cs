using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Splines;

/// <summary>
/// SplineContainer のスプラインに沿って、地形に追従する道メッシュ(リボン)を生成する。
/// Scene ビューでスプラインの制御点(knot)をクリックで足して古地図の通りをなぞると、
/// 道が実寸幅で地形に沿って自動生成される（編集中もリアルタイム更新）。
/// GameObject は原点・無回転で使うこと（local=world）。
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(SplineContainer))]
[RequireComponent(typeof(MeshFilter))]
[RequireComponent(typeof(MeshRenderer))]
public class SplineRoad : MonoBehaviour
{
    [Tooltip("道幅(m)。表通り〜6-11m、路地〜3-4m")]
    public float width = 6f;
    [Tooltip("地形からの浮かせ量(Zファイト回避)")]
    public float lift = 0.12f;
    [Tooltip("サンプル間隔(m)。小さいほど滑らか")]
    public float step = 3f;
    public bool followTerrain = true;

    SplineContainer sc;
    Mesh mesh;

    void OnEnable() { sc = GetComponent<SplineContainer>(); Rebuild(); }
    void Update() { Rebuild(); }

    float GroundY(float x, float z, float fallback)
    {
        if (!followTerrain) return fallback;
        var t = Terrain.activeTerrain;
        if (t == null) return fallback;
        return t.SampleHeight(new Vector3(x, 0f, z)) + t.transform.position.y;
    }

    void Rebuild()
    {
        if (sc == null) sc = GetComponent<SplineContainer>();
        if (sc == null || sc.Spline == null || sc.Spline.Count < 2) return;
        float len = sc.CalculateLength();
        if (len < 0.01f) return;

        int n = Mathf.Max(2, Mathf.CeilToInt(len / Mathf.Max(0.5f, step)));
        var verts = new List<Vector3>();
        var tris = new List<int>();
        var uv = new List<Vector2>();
        Vector2 prev = Vector2.zero;
        float acc = 0f;

        for (int i = 0; i <= n; i++)
        {
            float u = (float)i / n;
            Vector3 pos = (Vector3)sc.EvaluatePosition(u);
            Vector3 tan = (Vector3)sc.EvaluateTangent(u);
            tan.y = 0f;
            if (tan.sqrMagnitude < 1e-5f) tan = Vector3.forward;
            tan.Normalize();
            Vector3 right = new Vector3(tan.z, 0f, -tan.x);
            Vector3 lc = new Vector3(pos.x, 0f, pos.z) - right * (width * 0.5f);
            Vector3 rc = new Vector3(pos.x, 0f, pos.z) + right * (width * 0.5f);
            lc.y = GroundY(lc.x, lc.z, pos.y) + lift;
            rc.y = GroundY(rc.x, rc.z, pos.y) + lift;

            Vector2 cur = new Vector2(pos.x, pos.z);
            if (i > 0) acc += Vector2.Distance(cur, prev);
            prev = cur;

            verts.Add(lc); verts.Add(rc);
            uv.Add(new Vector2(0f, acc / width)); uv.Add(new Vector2(1f, acc / width));
        }
        for (int i = 0; i < n; i++)
        {
            int b = i * 2;
            tris.Add(b); tris.Add(b + 2); tris.Add(b + 1);
            tris.Add(b + 1); tris.Add(b + 2); tris.Add(b + 3);
        }
        if (mesh == null) { mesh = new Mesh(); mesh.name = "SplineRoadMesh"; }
        mesh.Clear();
        mesh.SetVertices(verts);
        mesh.SetTriangles(tris, 0);
        mesh.SetUVs(0, uv);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        GetComponent<MeshFilter>().sharedMesh = mesh;
    }
}
