using UnityEngine;

/// <summary>
/// Play開始時にプレイヤーを SpawnPoint マーカーの位置・向きへ移動する（確認用の自由スポーン）。
/// シーンで "SpawnPoint" を好きな場所へ動かして ▶Play すれば、そこから始まる。
/// マーカーの Y 回転 = 開始時に向く方向。地形の高さには自動で乗る。
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class PlayerSpawn : MonoBehaviour
{
    [Tooltip("このマーカー(空オブジェクト)の位置・Y回転でスポーンします")]
    public Transform spawnPoint;

    [Tooltip("地形の高さに自動で乗せる")]
    public bool snapToTerrain = true;

    public float clearance = 0.1f;

    void Start()
    {
        if (spawnPoint != null)
            TeleportTo(spawnPoint.position, spawnPoint.eulerAngles.y);
    }

    public void TeleportTo(Vector3 pos, float yaw)
    {
        if (snapToTerrain)
        {
            float surfaceY;
            if (TrySampleTerrainY(pos, out surfaceY))
                pos.y = surfaceY + clearance;
        }
        var cc = GetComponent<CharacterController>();
        if (cc != null) cc.enabled = false;   // CharacterControllerはテレポート時に一旦切る
        transform.position = pos;
        transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        if (cc != null) cc.enabled = true;
    }

    /// <summary>
    /// pos(XZ) の地表 Y を返す。**多タイル地形対応**: EdoTerrain のように Terrain が
    /// 複数タイルに分かれていても、pos を含むタイルを探して高さを取る。
    /// （旧実装は Terrain.activeTerrain 1枚だけを見ており、範囲外だと誤った高さ→地下スポーンになっていた）
    /// </summary>
    static bool TrySampleTerrainY(Vector3 pos, out float y)
    {
        foreach (var ter in Terrain.activeTerrains)
        {
            if (ter == null || ter.terrainData == null) continue;
            Vector3 tp = ter.transform.position;
            Vector3 sz = ter.terrainData.size;
            if (pos.x >= tp.x && pos.x <= tp.x + sz.x &&
                pos.z >= tp.z && pos.z <= tp.z + sz.z)
            {
                y = ter.SampleHeight(pos) + tp.y;
                return true;
            }
        }
        // フォールバック: 上空からレイキャスト（地形コライダーに乗る）
        RaycastHit hit;
        if (Physics.Raycast(pos + Vector3.up * 2000f, Vector3.down, out hit, 5000f))
        {
            y = hit.point.y;
            return true;
        }
        y = 0f;
        return false;
    }

    void OnDrawGizmos()
    {
        if (spawnPoint == null) return;
        Vector3 p = spawnPoint.position + Vector3.up;
        Gizmos.color = new Color(0.2f, 0.9f, 1f, 0.9f);
        Gizmos.DrawSphere(p, 0.8f);
        Vector3 fwd = spawnPoint.forward; fwd.y = 0f;
        if (fwd.sqrMagnitude < 0.0001f) fwd = Vector3.forward;
        fwd.Normalize();
        Gizmos.DrawLine(p, p + fwd * 3f);
        Gizmos.DrawSphere(p + fwd * 3f, 0.3f);
    }
}
