using UnityEngine;
using UnityEditor;

/// <summary>
/// 開発効率のための「フォーカス表示」ツール。
/// 江戸全域は Terrain 56タイル＋大テクスチャで重く、8GB級のマシンでは全ロードのまま
/// 拡大するとチラつき/スタッター(GPU・メモリ負荷)が出やすい。
/// 見ているエリア周辺のタイルだけ残して他を非表示にすると劇的に軽くなる。
///
/// メニュー（可逆・エディタ専用。シーンには残さない運用推奨）:
///  - Edo/視点/近くの地形タイルだけ表示 (Cmd+Shift+I) … Sceneビューの注視点周辺のタイルだけ残す
///  - Edo/視点/全地形タイルを表示        (Cmd+Shift+O) … 全タイルを再表示
///  - Edo/地図オーバーレイ/古地図 表示切替 (Cmd+Shift+M) … 古地図オーバーレイ(42MB)の表示ON/OFF
///
/// ⚠️ タイルを隠すとそのコライダーも無効になる。Play/歩行テスト前に「Show All」で戻すこと。
/// </summary>
public static class EdoFocus
{
    const string TerrainRoot = "EdoTerrain";
    const string OverlayName = "OldMapOverlay";
    // 注視点からこの距離(m)以内に掛かるタイルを残す。2400mタイルなので ~3x3 が残る。
    const float KeepRadius = 2500f;

    [MenuItem("Edo/視点/近くの地形タイルだけ表示 %#i")]
    static void IsolateNearView()
    {
        Vector3 c;
        var sel = Selection.activeGameObject;
        if (sel != null)
        {
            var r = sel.GetComponent<Renderer>();
            c = r != null ? r.bounds.center : sel.transform.position;
        }
        else if (SceneView.lastActiveSceneView != null)
        {
            c = SceneView.lastActiveSceneView.pivot; // Sceneビューの注視点
        }
        else { Debug.LogWarning("[EdoFocus] Sceneビューが無く選択もありません。"); return; }

        var root = GameObject.Find(TerrainRoot);
        if (root == null) { Debug.LogWarning("[EdoFocus] EdoTerrain が見つかりません。"); return; }

        int on = 0, off = 0;
        foreach (Transform t in root.transform)
        {
            bool keep = true;
            var ter = t.GetComponent<Terrain>();
            if (ter != null && ter.terrainData != null)
            {
                Vector3 tp = t.position; Vector3 sz = ter.terrainData.size;
                // タイル矩形(XZ)への最近点までの距離
                float nx = Mathf.Clamp(c.x, tp.x, tp.x + sz.x);
                float nz = Mathf.Clamp(c.z, tp.z, tp.z + sz.z);
                float d = Vector2.Distance(new Vector2(nx, nz), new Vector2(c.x, c.z));
                keep = d <= KeepRadius;
            }
            if (t.gameObject.activeSelf != keep) t.gameObject.SetActive(keep);
            if (keep) on++; else off++;
        }
        Debug.Log($"[EdoFocus] 注視点 {c:F0} 周辺のみ表示: active={on} hidden={off}（Show All で全復帰）");
        SceneView.RepaintAll();
    }

    [MenuItem("Edo/視点/全地形タイルを表示 %#o")]
    static void ShowAll()
    {
        var root = GameObject.Find(TerrainRoot);
        if (root == null) { Debug.LogWarning("[EdoFocus] EdoTerrain が見つかりません。"); return; }
        int n = 0;
        foreach (Transform t in root.transform)
            if (!t.gameObject.activeSelf) { t.gameObject.SetActive(true); n++; }
        Debug.Log($"[EdoFocus] 全タイル表示に復帰（{n}枚を再表示）");
        SceneView.RepaintAll();
    }

    [MenuItem("Edo/地図オーバーレイ/古地図 表示切替 %#m")]
    static void ToggleOverlay()
    {
        GameObject go = null;
        foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (tr.name == OverlayName) { go = tr.gameObject; break; }
        if (go == null) { Debug.LogWarning("[EdoFocus] OldMapOverlay が見つかりません。"); return; }
        go.SetActive(!go.activeSelf);
        Debug.Log($"[EdoFocus] OldMapOverlay active={go.activeSelf}");
        SceneView.RepaintAll();
    }
}
