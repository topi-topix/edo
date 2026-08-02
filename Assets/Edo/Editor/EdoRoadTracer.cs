using UnityEngine;
using UnityEditor;
using UnityEngine.Splines;
using Unity.Mathematics;

/// <summary>
/// 「地面をクリックして道をなぞる」ための簡単なトレーサー。
/// メニュー Edo ▸ Road Tracer で開く。純正スプラインツールの代わりに、
/// クリックで点を足す/Shift+クリックで消すだけで道を引ける。
/// </summary>
public class EdoRoadTracer : EditorWindow
{
    public SplineContainer target;
    public float width = 8f;
    bool tracing;

    [MenuItem("Edo/Road Tracer")]
    static void Open() { GetWindow<EdoRoadTracer>("Edo Road Tracer"); }

    void OnEnable() { SceneView.duringSceneGui += OnScene; }
    void OnDisable() { SceneView.duringSceneGui -= OnScene; }

    void OnGUI()
    {
        EditorGUILayout.HelpBox(
            "使い方\n" +
            "1) 『＋ 新しい道を作る』を押す（既存の道を続けるなら下の欄に入れる）\n" +
            "2) 『▶ トレース開始』を押す\n" +
            "3) 上(Top)視点で、古地図の通りに沿って地面を左クリック → 点が増え道が伸びる\n" +
            "    Shift+左クリック = 近くの点を削除\n" +
            "4) 終わったら『■ トレース停止』", MessageType.Info);

        if (target == null) target = Object.FindFirstObjectByType<SplineContainer>();
        target = (SplineContainer)EditorGUILayout.ObjectField("対象の道", target, typeof(SplineContainer), true);
        width = EditorGUILayout.Slider("道幅(m)", width, 2f, 14f);
        if (target != null)
        {
            var sr = target.GetComponent<SplineRoad>();
            if (sr != null && !Mathf.Approximately(sr.width, width)) { sr.width = width; EditorUtility.SetDirty(sr); }
        }

        if (GUILayout.Button("＋ 新しい道を作る", GUILayout.Height(28))) NewRoad();

        using (new EditorGUI.DisabledScope(target == null))
        {
            GUI.backgroundColor = tracing ? new Color(1f, 0.5f, 0.5f) : new Color(0.6f, 1f, 0.6f);
            if (GUILayout.Button(tracing ? "■ トレース停止" : "▶ トレース開始", GUILayout.Height(36)))
            { tracing = !tracing; SceneView.RepaintAll(); }
            GUI.backgroundColor = Color.white;
            if (target != null && target.Spline != null)
                EditorGUILayout.LabelField("点の数", target.Spline.Count.ToString());
            if (GUILayout.Button("↶ 最後の点を取消")) UndoLast();
        }
        if (tracing) EditorGUILayout.HelpBox("トレース中：Scene の地面を左クリックで点追加 / Shift+クリックで削除", MessageType.Warning);
    }

    void NewRoad()
    {
        var go = new GameObject("Road");
        Undo.RegisterCreatedObjectUndo(go, "New Road");
        var sc = go.AddComponent<SplineContainer>();
        sc.Spline = new Spline();
        var sr = go.AddComponent<SplineRoad>();
        sr.width = width;
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Edo/Materials/Road.mat");
        if (mat != null) go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        target = sc;
        Selection.activeGameObject = go;
        tracing = true;
        SceneView.RepaintAll();
    }

    void AddKnot(Vector3 p)
    {
        var s = target.Spline;
        s.Add(new BezierKnot(new float3(p.x, p.y, p.z)));
        if (s.Count >= 2) s.SetTangentMode(TangentMode.AutoSmooth);
        EditorUtility.SetDirty(target);
    }

    void UndoLast()
    {
        if (target == null || target.Spline == null || target.Spline.Count == 0) return;
        target.Spline.RemoveAt(target.Spline.Count - 1);
        EditorUtility.SetDirty(target);
        SceneView.RepaintAll();
    }

    void RemoveNear(Vector3 p)
    {
        var s = target.Spline; int best = -1; float bd = 25f * 25f;
        for (int i = 0; i < s.Count; i++)
        {
            float3 k = s[i].Position;
            float d = (new Vector3(k.x, k.y, k.z) - p).sqrMagnitude;
            if (d < bd) { bd = d; best = i; }
        }
        if (best >= 0) { s.RemoveAt(best); EditorUtility.SetDirty(target); }
    }

    bool RaycastGround(Ray ray, out Vector3 hit)
    {
        hit = Vector3.zero;
        RaycastHit hi;
        if (Physics.Raycast(ray, out hi, 20000f)) { hit = hi.point; return true; }
        var t = Terrain.activeTerrain;
        if (t != null && Mathf.Abs(ray.direction.y) > 1e-4f)
        {
            float tt = -ray.origin.y / ray.direction.y;
            if (tt > 0f) { Vector3 p = ray.origin + ray.direction * tt; p.y = t.SampleHeight(p) + t.transform.position.y; hit = p; return true; }
        }
        return false;
    }

    void OnScene(SceneView sv)
    {
        if (target != null && target.Spline != null)
        {
            Handles.color = Color.cyan;
            var s = target.Spline;
            Vector3 prev = Vector3.zero;
            for (int i = 0; i < s.Count; i++)
            {
                float3 k = s[i].Position; Vector3 wp = new Vector3(k.x, k.y, k.z);
                Handles.SphereHandleCap(0, wp, Quaternion.identity, 2.0f, EventType.Repaint);
                if (i > 0) Handles.DrawLine(prev, wp);
                prev = wp;
            }
        }
        if (!tracing || target == null) return;
        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);
        Event e = Event.current;
        if (e.type == EventType.MouseDown && e.button == 0)
        {
            Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);
            Vector3 hit;
            if (RaycastGround(ray, out hit))
            {
                if (e.shift) RemoveNear(hit); else AddKnot(hit);
                e.Use();
                SceneView.RepaintAll();
                Repaint();
            }
        }
    }
}
