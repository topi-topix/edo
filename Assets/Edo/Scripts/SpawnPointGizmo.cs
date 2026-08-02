using UnityEngine;

/// <summary>スポーン地点を Scene で見つけやすくする大きめのギズモ（地面リング＋ポール＋向き矢印）。</summary>
public class SpawnPointGizmo : MonoBehaviour
{
    void OnDrawGizmos()
    {
        Vector3 p = transform.position;
        var t = Terrain.activeTerrain;
        if (t != null) p.y = t.SampleHeight(p) + t.transform.position.y;   // 地表に乗せて表示

        Gizmos.color = new Color(1f, 0.85f, 0.1f, 0.95f);
        DrawRing(p, 9f);
        DrawRing(p, 6f);
        Gizmos.DrawLine(p, p + Vector3.up * 25f);
        Gizmos.DrawSphere(p + Vector3.up * 25f, 2.2f);
        Gizmos.DrawSphere(p + Vector3.up * 2f, 2.2f);

        // 向き（開始時に向く方向）
        Gizmos.color = new Color(1f, 0.45f, 0f);
        Vector3 f = transform.forward; f.y = 0f;
        if (f.sqrMagnitude < 0.0001f) f = Vector3.forward;
        f.Normalize();
        Gizmos.DrawLine(p + Vector3.up * 1.5f, p + f * 14f + Vector3.up * 1.5f);
        Gizmos.DrawSphere(p + f * 14f + Vector3.up * 1.5f, 2f);
    }

    void DrawRing(Vector3 c, float r)
    {
        Vector3 prev = c + new Vector3(r, 0.2f, 0f);
        for (int i = 1; i <= 28; i++)
        {
            float a = i / 28f * Mathf.PI * 2f;
            Vector3 cur = c + new Vector3(Mathf.Cos(a) * r, 0.2f, Mathf.Sin(a) * r);
            Gizmos.DrawLine(prev, cur); prev = cur;
        }
    }
}
