using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

[CustomEditor(typeof(MoatWall))]
public class MoatWallEditor : Editor
{
    public override void OnInspectorGUI()
    {
        var wall = (MoatWall)target;
        DrawDefaultInspector();

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("背面プロファイル プリセット", EditorStyles.boldLabel);
        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button("面一の平場"))
            {
                Undo.RecordObject(wall, "Preset Flush");
                wall.backProfile = new List<BackStep> { new BackStep { width = 6f, dHeight = 0f } };
                EditorUtility.SetDirty(wall);
            }
            if (GUILayout.Button("犬走り＋平場"))
            {
                Undo.RecordObject(wall, "Preset Walkway");
                wall.backProfile = new List<BackStep> {
                    new BackStep { width = 1.5f, dHeight = -0.6f }, // 天端少し下の細い通路
                    new BackStep { width = 6f,   dHeight = 0f    }, // その奥の平場(天端高)
                };
                EditorUtility.SetDirty(wall);
            }
        }

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("土木ベイク", EditorStyles.boldLabel);
        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button("① 掘削 Carve")) MoatWallBaker.Carve(wall);
            if (GUILayout.Button("復元 Restore")) MoatWallBaker.Restore(wall);
        }
        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button("② 石垣配置 Place")) MoatWallBaker.PlaceWalls(wall);
            if (GUILayout.Button("③ 水面 Water")) MoatWallBaker.BuildWater(wall);
        }
        if (GUILayout.Button("通し実行（掘削→石垣→水）"))
        {
            MoatWallBaker.Carve(wall);
            MoatWallBaker.PlaceWalls(wall);
            MoatWallBaker.BuildWater(wall);
        }
        EditorGUILayout.HelpBox("輪郭= 水際の天端ライン(閉ループ)。Sceneビューで黄点をドラッグして形を調整。\n断面: 水側=濠底へ掘削 / 陸側=背面プロファイルで天端まで土充填 → 既存地形へブレンド。", MessageType.Info);
    }

    void OnSceneGUI()
    {
        var wall = (MoatWall)target;
        var ol = wall.outline; if (ol == null || ol.Count == 0) return;

        Handles.color = new Color(1f, 0.85f, 0.1f, 1f);
        int n = ol.Count;
        for (int i = 0; i < n; i++)
        {
            Vector3 a = ol[i], b = ol[(i + 1) % n];
            Handles.DrawLine(a, b);
        }
        // 頂点ハンドル
        EditorGUI.BeginChangeCheck();
        for (int i = 0; i < n; i++)
        {
            float size = HandleUtility.GetHandleSize(ol[i]) * 0.08f;
            Vector3 np = Handles.FreeMoveHandle(ol[i], size, Vector3.zero, Handles.DotHandleCap);
            if (np != ol[i])
            {
                Undo.RecordObject(wall, "Move Moat Point");
                ol[i] = np;
                EditorUtility.SetDirty(wall);
            }
        }
        EditorGUI.EndChangeCheck();
    }

    // ---- テスト濠生成（半蔵濠付近に合成の細長い輪郭） ----
    [MenuItem("Edo/Moat/Create Test Moat (near Hanzobori)")]
    static void CreateTest()
    {
        var go = new GameObject("MoatWall_Test");
        var wall = go.AddComponent<MoatWall>();
        // 半蔵濠付近(北西, world ~ (150,1450))に細長い矩形輪郭（幅~60m, 長さ~200m）
        float cx = 150f, cz = 1450f, halfW = 30f, halfL = 100f;
        wall.outline = new List<Vector3> {
            new Vector3(cx - halfW, 0, cz - halfL),
            new Vector3(cx + halfW, 0, cz - halfL),
            new Vector3(cx + halfW, 0, cz + halfL),
            new Vector3(cx - halfW, 0, cz + halfL),
        };
        // 地表からおおよその水位を推定
        float surf = SampleTerrain(new Vector2(cx, cz));
        wall.waterY = surf - 3f;   // 水面は地表より3m下と仮置き
        wall.moatDepth = 4f;
        wall.topHeight = 2.5f;
        wall.backProfile = new List<BackStep> { new BackStep { width = 6f, dHeight = 0f } };
        Undo.RegisterCreatedObjectUndo(go, "Create Test Moat");
        Selection.activeGameObject = go;
        SceneView.lastActiveSceneView?.Frame(new Bounds(new Vector3(cx, surf, cz), new Vector3(200, 50, 260)), false);
        Debug.Log($"[Moat] テスト濠を生成: waterY={wall.waterY:F1} (地表~{surf:F1})。インスペクタで掘削を実行。");
    }

    static float SampleTerrain(Vector2 xz)
    {
        foreach (var t in Terrain.activeTerrains)
        {
            var td = t.terrainData; if (td == null) continue;
            Vector3 tp = t.transform.position; Vector3 sz = td.size;
            if (xz.x >= tp.x && xz.x <= tp.x + sz.x && xz.y >= tp.z && xz.y <= tp.z + sz.z)
                return t.SampleHeight(new Vector3(xz.x, 0, xz.y)) + tp.y;
        }
        return 0f;
    }
}
