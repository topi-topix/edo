using UnityEngine;
using UnityEditor;

/// <summary>
/// 「毎回まったく同じ真上からの視点」を作るためのメニュー。
///
/// シーンギズモの Y 軸をクリックしただけでは、下書き作業に必要な再現性が得られない:
///   1) 投影がパース(遠近)のままだと、画面中心から離れた物ほど高さに応じて外へ倒れて見える。
///      地図Quad・地形・建物はYが違うので、pivotが少し動くだけで相対位置がずれて見える。
///   2) pivot と size(画角の半分の高さ[m])が前の操作の値を引き継ぐので、毎回スケールが違う。
///   3) 回転がアニメーション補間で入るため、途中でマウス操作すると 90.000° ちょうどにならない。
///
/// メニュー Edo ▸ 視点:
///  - 真上から見る(正射) Cmd+Shift+T … 正射投影・回転 (90,0,0) を即時適用し、
///    pivot の XZ を 1m グリッド、size を 1-2-5 の段に丸めて固定。回転ロックも掛ける。
///  - 回転ロック切替               … 誤ってドラッグして傾くのを防ぐ ON/OFF。
/// </summary>
public static class EdoTopView
{
    const string MenuTop  = "Edo/視点/真上から見る（正射） %#t";
    const string MenuLock = "Edo/視点/回転ロック切替";

    /// <summary>真上・正射の正準姿勢。yaw=0 なので画面上が +Z(北)、右が +X。</summary>
    static readonly Quaternion TopRotation = Quaternion.Euler(90f, 0f, 0f);

    [MenuItem(MenuTop)]
    static void LookStraightDown()
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) { Debug.LogWarning("[EdoTopView] アクティブな Scene ビューがありません。"); return; }

        // 2Dモードだと -Z を向いてしまう(XY平面用)ので必ず解除
        if (sv.in2DMode) sv.in2DMode = false;

        // pivot: XZ は 1m グリッドへ、Y は真下の地表へ(正射なので見た目は変わらないが
        // ニア/ファー平面の基準になるため、地表付近に置いておくと安定する)
        Vector3 p = sv.pivot;
        p.x = Mathf.Round(p.x);
        p.z = Mathf.Round(p.z);
        p.y = TrySampleTerrain(p, out float gy) ? gy : 0f;

        // size: 1-2-5 の段に丸めて、毎回同じ縮尺に揃える
        float size = Snap125(Mathf.Max(sv.size, 1f));

        // instant=true でアニメーション補間を飛ばし、回転を厳密に 90° へ
        sv.LookAt(p, TopRotation, size, true, true);
        sv.isRotationLocked = true;
        sv.Repaint();

        float scale = sv.position.height > 0f ? size * 2f / sv.position.height : 0f;
        Debug.Log($"[EdoTopView] 真上・正射に固定: pivot=({p.x:F0}, {p.z:F0}) size={size:F0}m " +
                  $"(縦={size * 2f:F0}m / 約{scale:F2} m/px) 回転ロック=ON");
    }

    [MenuItem(MenuLock)]
    static void ToggleRotationLock()
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) { Debug.LogWarning("[EdoTopView] アクティブな Scene ビューがありません。"); return; }
        sv.isRotationLocked = !sv.isRotationLocked;
        sv.Repaint();
        Debug.Log($"[EdoTopView] 回転ロック={(sv.isRotationLocked ? "ON（傾かない）" : "OFF")}");
    }

    [MenuItem(MenuLock, true)]
    static bool ToggleRotationLockValidate()
    {
        var sv = SceneView.lastActiveSceneView;
        Menu.SetChecked(MenuLock, sv != null && sv.isRotationLocked);
        return sv != null;
    }

    /// <summary>1, 2, 5, 10, 20, 50 … の段へ丸める。</summary>
    static float Snap125(float v)
    {
        float e = Mathf.Pow(10f, Mathf.Floor(Mathf.Log10(v)));
        float m = v / e;
        float s = m < 1.5f ? 1f : m < 3.5f ? 2f : m < 7.5f ? 5f : 10f;
        return s * e;
    }

    /// <summary>world.xz 直下の地形高さ(world Y)。EdoSceneNav と同じ走査。</summary>
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
            if (!found || y > groundY) groundY = y;
            found = true;
        }
        return found;
    }
}
