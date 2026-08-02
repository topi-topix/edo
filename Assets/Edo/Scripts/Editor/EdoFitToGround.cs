using UnityEngine;
using UnityEditor;

/// <summary>
/// 選択したオブジェクトを地形(Terrain)の表面に接地させる。
/// 建物のピボットが底からズレていても、レンダラの境界(底)を地表に合わせるので浮かない。
///
/// 使い方: オブジェクトを選択 → メニュー Edo ▸ Fit Selected To Ground（ショートカット Ctrl+Shift+G）。
/// XZ(平面)の移動は手動で自由に行い、最後にこれで一括接地する運用を想定。
/// </summary>
public static class EdoFitToGround
{
    const float StoneEmbed = 0.05f; // 根石(基礎石)を地際にわずかに埋める量[m]
    const float Sink = 0.3f;        // 根石が無い建物の底を地表へ沈める量[m]

    // ショートカットはコードに固定せず、Unity の Shortcuts 設定でユーザーが割り当てる（衝突回避）。
    // 設定 ▸ Shortcuts で "Fit Selected To Ground" を検索して好きなキーを登録できる。
    [MenuItem("Edo/地形/選択物を地面に合わせる")]
    public static void FitSelected()
    {
        var objs = Selection.gameObjects;
        if (objs == null || objs.Length == 0) { Debug.LogWarning("[FitToGround] 接地するオブジェクトを選択してください。"); return; }

        int done = 0;
        foreach (var go in objs)
        {
            var rends = go.GetComponentsInChildren<Renderer>();
            if (rends.Length == 0) continue;

            var b = rends[0].bounds;
            for (int i = 1; i < rends.Length; i++) b.Encapsulate(rends[i].bounds);

            var terr = FindTerrainAt(b.center);
            if (terr == null) { Debug.LogWarning($"[FitToGround] {go.name}: 真下に Terrain がありません。"); continue; }

            float groundY = terr.SampleHeight(b.center) + terr.transform.position.y;

            // 石場建て: 根石(stone)があればその底を地際に据える。無ければ全体の底を地表に沈める。
            float stoneBottom = float.MaxValue;
            foreach (var r in rends)
                if (r.name.ToLower().Contains("stone") && r.bounds.min.y < stoneBottom)
                    stoneBottom = r.bounds.min.y;

            float delta = stoneBottom < float.MaxValue
                ? (groundY - StoneEmbed) - stoneBottom   // 根石の底を 地表-StoneEmbed へ
                : (groundY - Sink) - b.min.y;             // 根石なし: 建物底を 地表-Sink へ

            Undo.RecordObject(go.transform, "Fit To Ground");
            go.transform.position += new Vector3(0f, delta, 0f);
            done++;
        }
        Debug.Log($"[FitToGround] {done} 個を接地しました。");
    }

    // XZ がその Terrain の範囲内にある Terrain を返す（複数タイル対応）。
    static Terrain FindTerrainAt(Vector3 world)
    {
        Terrain best = null; float bestArea = float.MaxValue;
        foreach (var t in Terrain.activeTerrains)
        {
            var p = t.transform.position; var s = t.terrainData.size;
            if (world.x >= p.x && world.x <= p.x + s.x && world.z >= p.z && world.z <= p.z + s.z)
            {
                float area = s.x * s.z;                 // 入れ子なら小さいタイルを優先
                if (area < bestArea) { bestArea = area; best = t; }
            }
        }
        return best != null ? best : Terrain.activeTerrain;
    }
}
