using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 手で水域(堀・池)を描くツール。メニュー Edo ▸ Water Tracer。
/// 古地図(⌘⇧Mで表示)の上をクリックして水際の輪郭をなぞり、『水を焼く』で
/// 編集可能な水域(WaterBody)を作る（掘り込み＋水面）。作った後は WaterBody を選んで
/// 点をドラッグ＝形を変える／『掘り直す』＝地形反映（WaterBodyEditor）。
/// なぞり中: 左クリック=点追加, Shift+クリック=削除, スクロール/中ドラッグ/Alt=移動・ズーム。
/// </summary>
public class EdoWaterTracer : EditorWindow
{
    readonly List<Vector3> pts = new List<Vector3>();
    bool tracing;
    float depth = 2.2f;

    [MenuItem("Edo/Water Tracer")]
    static void Open() { GetWindow<EdoWaterTracer>("Edo Water Tracer"); }

    void OnEnable() { SceneView.duringSceneGui += OnScene; }
    void OnDisable() { SceneView.duringSceneGui -= OnScene; }

    void OnGUI()
    {
        EditorGUILayout.HelpBox(
            "使い方\n" +
            "1) ⌘⇧M で古地図を表示（配置の下敷き）＋ Top視点\n" +
            "2) 『▶ 輪郭をなぞる』→ 水際(堀・池のふち)を左クリックで一周\n" +
            "    Shift+左クリック = 近くの点を削除\n" +
            "3) 『💧 水を焼く』→ 編集可能な水域が生成される（点はクリア）\n" +
            "・作った後は Hierarchy でその水域(Water_xxxx)を選ぶと、Sceneで点をドラッグして\n" +
            "  形を変えられる（広げ/縮め）。地形は Inspector の『掘り直す』で反映。", MessageType.Info);

        depth = EditorGUILayout.Slider("掘り込み深さ(m)", depth, 0.8f, 5f);

        GUI.backgroundColor = tracing ? new Color(1f, 0.5f, 0.5f) : new Color(0.6f, 0.8f, 1f);
        if (GUILayout.Button(tracing ? "■ なぞるのを止める" : "▶ 輪郭をなぞる", GUILayout.Height(34)))
        { tracing = !tracing; SceneView.RepaintAll(); }
        GUI.backgroundColor = Color.white;

        EditorGUILayout.LabelField("点の数", pts.Count.ToString());
        using (new EditorGUI.DisabledScope(pts.Count < 3))
        {
            GUI.backgroundColor = new Color(0.5f, 0.7f, 1f);
            if (GUILayout.Button("💧 水を焼く（編集可能な水域を作る）", GUILayout.Height(34))) Bake();
            GUI.backgroundColor = new Color(0.7f, 0.65f, 0.5f);
            if (GUILayout.Button("🏯 石垣濠を焼く（MoatWall を作る）", GUILayout.Height(34))) BakeMoat();
            GUI.backgroundColor = Color.white;
        }
        if (GUILayout.Button("点をクリア")) { pts.Clear(); SceneView.RepaintAll(); }
        if (tracing) EditorGUILayout.HelpBox("なぞり中：左クリック=点追加 / Shift+クリック=削除\n移動: スクロール=ズーム, 中ボタンドラッグ or Alt+ドラッグ=パン/回転（なぞり中でも動かせます）", MessageType.Warning);
    }

    void OnScene(SceneView sv)
    {
        // 画面上で一定サイズの大きめハンドル＋番号
        for (int i = 0; i < pts.Count; i++)
        {
            float hs = HandleUtility.GetHandleSize(pts[i]) * 0.09f;
            Handles.color = new Color(0.15f, 0.85f, 1f);
            Handles.SphereHandleCap(0, pts[i], Quaternion.identity, hs, EventType.Repaint);
            Handles.color = Color.white;
            Handles.Label(pts[i] + Vector3.up * hs * 2.2f, (i + 1).ToString());
            if (pts.Count >= 2) { Handles.color = new Color(0.2f, 0.7f, 1f, 0.9f); Handles.DrawLine(pts[i], pts[(i + 1) % pts.Count]); }
        }
        if (!tracing) return;
        Event e = Event.current;
        if (e.alt) return;  // Alt(回転/パン)はUnityに任せる
        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);
        if (e.type == EventType.MouseDown && e.button == 0)
        {
            if (TryRaycast(HandleUtility.GUIPointToWorldRay(e.mousePosition), out Vector3 hit))
            {
                if (e.shift) RemoveNear(hit); else pts.Add(hit);
                e.Use(); SceneView.RepaintAll(); Repaint();
            }
        }
    }

    void RemoveNear(Vector3 p)
    {
        int best = -1; float bd = 20f * 20f;
        for (int i = 0; i < pts.Count; i++) { float d = (pts[i] - p).sqrMagnitude; if (d < bd) { bd = d; best = i; } }
        if (best >= 0) pts.RemoveAt(best);
    }

    static bool TryRaycast(Ray ray, out Vector3 hit)
    {
        hit = Vector3.zero;
        if (Physics.Raycast(ray, out RaycastHit hi, 20000f)) { hit = hi.point; return true; }
        var t = Terrain.activeTerrain;
        if (t != null && Mathf.Abs(ray.direction.y) > 1e-4f)
        {
            float tt = -ray.origin.y / ray.direction.y;
            if (tt > 0f) { Vector3 p = ray.origin + ray.direction * tt; p.y = t.SampleHeight(p) + t.transform.position.y; hit = p; return true; }
        }
        return false;
    }

    void Bake()
    {
        var wb = WaterBaker.Create(pts, depth);
        pts.Clear();
        if (wb != null) Selection.activeGameObject = wb.gameObject;   // すぐ編集できるよう選択
        SceneView.RepaintAll(); Repaint();
    }

    /// <summary>なぞった輪郭から石垣濠(MoatWall)を作る。掘削/配置/水は MoatWall インスペクタで実行。</summary>
    void BakeMoat()
    {
        var go = new GameObject("MoatWall_" + System.DateTime.Now.ToString("HHmmss"));
        Undo.RegisterCreatedObjectUndo(go, "Create MoatWall");
        var wall = go.AddComponent<MoatWall>();
        wall.outline = new List<Vector3>(pts);
        // 既定の石垣モジュールセットがあれば割当
        var guids = AssetDatabase.FindAssets("t:MoatModuleSet");
        if (guids.Length > 0)
            wall.modules = AssetDatabase.LoadAssetAtPath<MoatModuleSet>(AssetDatabase.GUIDToAssetPath(guids[0]));
        // 水位を輪郭下の地形からざっくり推定（中央値-0.3m）
        var hs = new List<float>();
        foreach (var p in pts)
            foreach (var t in Terrain.activeTerrains)
            {
                var td = t.terrainData; var tp = t.transform.position; var s = td.size;
                if (p.x >= tp.x && p.x <= tp.x + s.x && p.z >= tp.z && p.z <= tp.z + s.z)
                { hs.Add(t.SampleHeight(new Vector3(p.x, 0, p.z)) + tp.y); break; }
            }
        if (hs.Count > 0) { hs.Sort(); wall.waterY = hs[hs.Count / 2] - 0.3f; }
        wall.backProfile = new List<BackStep> { new BackStep { width = 6f, dHeight = 0f } };
        pts.Clear();
        Selection.activeGameObject = go;
        Debug.Log($"[Moat] MoatWall を作成: waterY={wall.waterY:F1}。インスペクタで ①掘削→②石垣→③水面 を実行（保存推奨）。");
        SceneView.RepaintAll(); Repaint();
    }
}
