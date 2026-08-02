using UnityEngine;
using UnityEditor;

/// <summary>
/// Sceneビューのナビ補助。
/// 広大な地形(4km四方)ではピボット(回転・ズームの中心)が地中や遠方に落ちやすく、
/// スクロールズームがピボットへ寄る仕様のため「地表を突き抜けてズームできない」状態になる。
///
/// メニュー Edo ▸ View:
///  - Drop Pivot To Ground (Cmd+Shift+G) … 画面中央の地表にピボットを落として寄る。
///    これで以後のスクロールズームが地表面へ収束する。
///  - Frame Ground At Player            … プレイヤー地点の地表へ寄る。
///
/// ※ さらに快適にするなら Preferences を開き検索窓に "zoom" と入れて
///   「Zoom towards mouse pointer(マウス位置へズーム)」を ON にすると、
///   カーソル下の地表へズームするようになる(Unity全体設定/任意)。
/// </summary>
public static class EdoSceneNav
{
    const float DefaultSize = 45f; // 落下後のフレーミング半径(m)

    [MenuItem("Edo/視点/ピボットを地面に落とす %#g")]
    static void DropPivotToGround()
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) { Debug.LogWarning("[EdoSceneNav] アクティブな Scene ビューがありません。"); return; }

        var cam = sv.camera;
        Vector3 hit;

        // 1) 画面中央からレイを飛ばしてコライダーに当てる(見ている地点に落とす)
        Ray ray = cam.ViewportPointToRay(new Vector3(0.5f, 0.5f, 0f));
        if (Physics.Raycast(ray, out var rh, 100000f))
        {
            hit = rh.point;
        }
        else if (TrySampleTerrain(sv.pivot, out float gy))
        {
            // 2) コライダーに当たらなければ現在ピボットの真下の地形高さを使う
            hit = new Vector3(sv.pivot.x, gy, sv.pivot.z);
        }
        else
        {
            Debug.LogWarning("[EdoSceneNav] 地表が見つかりませんでした(地形/コライダー外)。");
            return;
        }

        sv.pivot = hit;
        sv.size = Mathf.Min(sv.size, DefaultSize);
        sv.Repaint();
        Debug.Log($"[EdoSceneNav] ピボットを地表へ: {hit:F1}（size={sv.size:F0}）");
    }

    [MenuItem("Edo/視点/プレイヤー地点を映す")]
    static void FrameGroundAtPlayer()
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) { Debug.LogWarning("[EdoSceneNav] アクティブな Scene ビューがありません。"); return; }
        var player = GameObject.Find("Player");
        Vector3 p = player != null ? player.transform.position : Vector3.zero;
        if (TrySampleTerrain(p, out float gy)) p.y = gy;
        sv.pivot = p;
        sv.size = DefaultSize;
        sv.Repaint();
        Debug.Log($"[EdoSceneNav] プレイヤー地点の地表へ: {p:F1}");
    }

    /// <summary>world.xz 直下の地形高さ(world Y)を返す。アクティブな Terrain を全走査。</summary>
    static bool TrySampleTerrain(Vector3 world, out float groundY)
    {
        groundY = 0f;
        bool found = false;
        foreach (var ter in Terrain.activeTerrains)
        {
            if (ter == null || !ter.isActiveAndEnabled) continue;
            var pos = ter.transform.position;
            var sz = ter.terrainData.size;
            if (world.x < pos.x || world.x > pos.x + sz.x ||
                world.z < pos.z || world.z > pos.z + sz.z) continue;
            float y = ter.SampleHeight(world) + pos.y;
            if (!found || y > groundY) groundY = y; // 複数タイル重なりは高い方
            found = true;
        }
        return found;
    }
}
