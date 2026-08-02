using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// WaterBody のインスペクタ。ここだけで水域が完結するように作ってある：
///   ・深さ / 水位 = 地形の掘り込み（変更すると自動で掘り直す）
///   ・Shore Width / Foam / 色 = 見た目（即反映。マテリアルや "Generate" ボタンは触らない）
///   ・削除は必ず下の赤ボタンから（Deleteキーは掘り跡が残るので警告のみ）
/// Scene では水色ハンドルをドラッグで形を変更（水面は即反映、掘り込みは指を離すと自動反映）。
/// </summary>
[CustomEditor(typeof(WaterBody))]
public class WaterBodyEditor : Editor
{
    bool addMode;
    bool cornerMode;

    /// <summary>sharp リストを outline と同じ長さに揃える（不足は false=スムーズで埋める）。</summary>
    static void EnsureSharp(WaterBody wb)
    {
        if (wb.sharp == null) wb.sharp = new List<bool>();
        while (wb.sharp.Count < wb.outline.Count) wb.sharp.Add(false);
        while (wb.sharp.Count > wb.outline.Count) wb.sharp.RemoveAt(wb.sharp.Count - 1);
    }

    static void SetAllSharp(WaterBody wb, bool val)
    {
        EnsureSharp(wb);
        Undo.RecordObject(wb, "Set Corner Style");
        for (int i = 0; i < wb.sharp.Count; i++) wb.sharp[i] = val;
        WaterBaker.RebuildSurface(wb);
        EditorUtility.SetDirty(wb);
        SceneView.RepaintAll();
    }

    Material Mat(WaterBody wb)
    {
        var mr = wb.GetComponent<MeshRenderer>();
        return mr != null ? mr.sharedMaterial : null;
    }

    public override void OnInspectorGUI()
    {
        var wb = (WaterBody)target;
        EnsureSharp(wb);   // 既存の水域(sharp未設定)もここで outline と同数に揃える

        EditorGUILayout.HelpBox(
            "この水域の設定はすべてここで完結します。\n" +
            "・形/深さ … Sceneで形をドラッグ or 深さを変え、『💧 地形を掘り直す』ボタンで反映\n" +
            "・見た目 … 『岸のなじみ幅』『泡』『色』（即反映）\n" +
            "※ マテリアルや『Generate』ボタンは触る必要はありません。", MessageType.Info);

        // ---- 地形の掘り込み（深さ/形）: 変更後『掘り直す』ボタンで反映 ----
        EditorGUILayout.LabelField("地形の掘り込み", EditorStyles.boldLabel);
        EditorGUI.BeginChangeCheck();
        float d = EditorGUILayout.Slider(new GUIContent("深さ(m)", "水面から底までの深さ。変更後『掘り直す』で反映"), wb.depth, 0.5f, 5f);
        if (EditorGUI.EndChangeCheck()) { Undo.RecordObject(wb, "Water Depth"); wb.depth = d; EditorUtility.SetDirty(wb); }

        EditorGUILayout.LabelField("水位(m)", wb.waterY.ToString("F2"));

        GUI.backgroundColor = new Color(0.5f, 0.7f, 1f);
        if (GUILayout.Button(new GUIContent("💧 地形を掘り直す（形・深さを反映）",
            "Sceneで形を変えたり深さを変えたら、これを押して地形の掘り込みに反映します"), GUILayout.Height(34)))
            WaterBaker.Recarve(wb);
        GUI.backgroundColor = Color.white;

        if (GUILayout.Button(new GUIContent("🌊 水位を地形に合わせる（あふれ/浮きを直す）",
            "掘る前の地形を基準に、あふれない安全な水位へ合わせて掘り直します（スナップは壊しません）")))
        { WaterBaker.FitToTerrain(wb); }

        if (GUILayout.Button(new GUIContent("🩹 水際の隙間を埋める（岸を均した後に押す）",
            "岸を均して水面より低くなり、水面のフチが浮いてできた隙間を埋めます。\n地形・水位・均した斜面は変えず、水面を汀線まで広げるだけ。隆起・削りブラシの「ならし」で水際を均した後に押してください。")))
        {
            int m = WaterBaker.FillShorelineGap(wb);
            Debug.Log(m > 0 ? ("水際の隙間を埋めました（" + m + "点を汀線まで広げた）") : "水面より低い岸はありませんでした（隙間なし）。");
        }

        EditorGUILayout.LabelField("輪郭の点数", wb.outline.Count.ToString());
        addMode = GUILayout.Toggle(addMode, addMode ? "■ 点の追加/削除 中（辺付近クリック=追加 / Shift+クリック=削除）" : "＋ 点を追加/削除する", "Button");
        if (addMode) cornerMode = false;

        // ---- 角のスタイル: 点ごとに スムーズ(丸) / 直角(角) を切替 ----
        EditorGUILayout.Space(2);
        EditorGUILayout.LabelField("角のスタイル（掘る形）", EditorStyles.boldLabel);
        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button(new GUIContent("全点スムーズ○", "すべての角を丸めて掘る（従来どおり）"))) SetAllSharp(wb, false);
            if (GUILayout.Button(new GUIContent("全点 直角□", "すべての角を直角のまま掘る"))) SetAllSharp(wb, true);
        }
        GUI.backgroundColor = cornerMode ? new Color(1f, 0.85f, 0.4f) : Color.white;
        cornerMode = GUILayout.Toggle(cornerMode,
            cornerMode ? "■ 角編集モード中（Sceneで点をクリックして 直角⇄スムーズ）" : "🔀 点ごとに 直角/スムーズ を切り替える", "Button");
        GUI.backgroundColor = Color.white;
        if (cornerMode) addMode = false;
        EditorGUILayout.HelpBox("平面(XZ)の角: スムーズ=青○ / 直角=黄□。切り替えたら『💧 地形を掘り直す』で反映。", MessageType.None);

        // ---- 壁の断面(Y方向): 垂直に掘る or なだらかに掘る ----
        EditorGUI.BeginChangeCheck();
        bool vw = GUILayout.Toggle(wb.verticalWalls,
            wb.verticalWalls ? "■ 壁を垂直に掘る（断面も直角・カクッと）" : "壁を垂直に掘る（断面を直角に）", "Button");
        if (EditorGUI.EndChangeCheck())
        {
            Undo.RecordObject(wb, "Vertical Walls");
            wb.verticalWalls = vw;
            EditorUtility.SetDirty(wb);
        }
        EditorGUILayout.HelpBox("OFF=壁が斜めに丸まる（従来）/ ON=壁を垂直に掘る。平面の直角と併せて完全な直角の掘り込みになります。", MessageType.None);

        EditorGUILayout.Space(6);

        // ---- 見た目（マテリアル）: 即反映。ここで完結させる ----
        EditorGUILayout.LabelField("見た目（岸・水の色）", EditorStyles.boldLabel);
        var mat = Mat(wb);
        if (mat == null)
        {
            EditorGUILayout.HelpBox("マテリアルが見つかりません。", MessageType.Warning);
        }
        else
        {
            EditorGUI.BeginChangeCheck();
            float shore = EditorGUILayout.Slider(new GUIContent("岸のなじみ幅 Shore(m)", "岸際が地面に溶ける幅。大きいほど岸がふわっと滑らかに。即反映"),
                mat.GetFloat("_ShoreWidth"), 0.5f, 12f);
            float foam = EditorGUILayout.Slider(new GUIContent("泡 Foam", "岸際の白い泡の量。即反映"), mat.GetFloat("_FoamAmount"), 0f, 1f);
            float fade = EditorGUILayout.Slider(new GUIContent("色の深さ Depth Fade(m)", "浅色→深色に変わる深さ。即反映"), mat.GetFloat("_DepthFade"), 1f, 12f);
            Color deep = EditorGUILayout.ColorField("深い色", mat.GetColor("_DeepColor"));
            Color shallow = EditorGUILayout.ColorField("浅い色", mat.GetColor("_ShallowColor"));

            EditorGUILayout.Space(2);
            EditorGUILayout.LabelField("リアルさ（波・反射・屈折）", EditorStyles.miniBoldLabel);
            float rip = EditorGUILayout.Slider(new GUIContent("さざ波の強さ", "0=鏡のよう / 大=荒い水面。池は弱め推奨"), mat.GetFloat("_NormalStrength"), 0f, 2f);
            float ripScale = EditorGUILayout.Slider(new GUIContent("さざ波の細かさ", "大きいほど細かい波"), mat.GetFloat("_NormalScale"), 0.1f, 1.5f);
            float wspeed = EditorGUILayout.Slider(new GUIContent("波の速さ", "さざ波の動く速さ"), mat.GetFloat("_WaveSpeed"), 0f, 1.5f);
            float refl = EditorGUILayout.Slider(new GUIContent("反射の強さ", "空/環境の映り込み"), mat.GetFloat("_ReflectionStrength"), 0f, 2f);
            float refr = EditorGUILayout.Slider(new GUIContent("屈折の歪み", "水中の地面が揺らぐ量"), mat.GetFloat("_RefractionStrength"), 0f, 0.08f);
            float glint = EditorGUILayout.Slider(new GUIContent("太陽のきらめき", "水面の陽光の反射"), mat.GetFloat("_SunSpecIntensity"), 0f, 8f);

            if (EditorGUI.EndChangeCheck())
            {
                Undo.RecordObject(mat, "Water Look");
                mat.SetFloat("_ShoreWidth", shore);
                mat.SetFloat("_FoamAmount", foam);
                mat.SetFloat("_DepthFade", fade);
                mat.SetColor("_DeepColor", deep);
                mat.SetColor("_ShallowColor", shallow);
                mat.SetFloat("_NormalStrength", rip);
                mat.SetFloat("_NormalScale", ripScale);
                mat.SetFloat("_WaveSpeed", wspeed);
                mat.SetFloat("_ReflectionStrength", refl);
                mat.SetFloat("_RefractionStrength", refr);
                mat.SetFloat("_SunSpecIntensity", glint);
                EditorUtility.SetDirty(mat);
                SceneView.RepaintAll();
            }
            EditorGUILayout.HelpBox("岸を滑らかに → 『岸のなじみ幅』を上げる。水を穏やかに → 『さざ波の強さ』を下げる。すべて即反映。", MessageType.None);
        }

        EditorGUILayout.Space(6);

        // ---- 削除 / 復元（安全）----
        EditorGUILayout.LabelField("削除・元に戻す", EditorStyles.boldLabel);
        using (new EditorGUI.DisabledScope(!wb.hasSnap))
        {
            if (GUILayout.Button("⛰ 掘り込みを埋めて地形を元に戻す（水域は残す）"))
            {
                Undo.RegisterCompleteObjectUndo(Terrain.activeTerrain.terrainData, "Restore Terrain");
                WaterBaker.RestoreTerrain(wb);
            }
            GUI.backgroundColor = new Color(1f, 0.55f, 0.5f);
            if (GUILayout.Button("🗑 この水域を削除して地形を元に戻す"))
            {
                if (EditorUtility.DisplayDialog("水域を削除",
                    "地形の掘り込みを埋め戻してから、この水域を削除します。よろしいですか？", "削除する", "やめる"))
                {
                    Undo.RegisterCompleteObjectUndo(Terrain.activeTerrain.terrainData, "Restore & Delete Water");
                    WaterBaker.RestoreAndDelete(wb);
                    GUIUtility.ExitGUI();
                }
            }
            GUI.backgroundColor = Color.white;
        }
        if (!wb.hasSnap) EditorGUILayout.HelpBox("まだ掘っていない（スナップ無し）ので復元は不要です。", MessageType.None);
        EditorGUILayout.HelpBox("⚠️ Deleteキーで消すと掘り跡が地形に残ります。必ず上の🗑ボタンで削除してください。", MessageType.Warning);
    }

    void OnSceneGUI()
    {
        var wb = (WaterBody)target;
        if (wb.outline == null || wb.outline.Count == 0) return;
        EnsureSharp(wb);

        Handles.color = new Color(0.2f, 0.7f, 1f, 0.9f);
        for (int i = 0; i < wb.outline.Count; i++)
            Handles.DrawLine(wb.outline[i], wb.outline[(i + 1) % wb.outline.Count]);

        var smoothCol = new Color(0.15f, 0.85f, 1f);
        var sharpCol = new Color(1f, 0.85f, 0.2f);

        if (cornerMode)
        {
            // 角編集モード: 点をクリックで 直角⇄スムーズ を1つずつ切替
            for (int i = 0; i < wb.outline.Count; i++)
            {
                Vector3 p = wb.outline[i];
                float hs = HandleUtility.GetHandleSize(p) * 0.11f;
                bool sh = wb.sharp[i];
                Handles.color = sh ? sharpCol : smoothCol;
                Handles.CapFunction cap = sh ? (Handles.CapFunction)Handles.CubeHandleCap : Handles.SphereHandleCap;
                if (Handles.Button(p, Quaternion.identity, hs, hs * 1.4f, cap))
                {
                    Undo.RecordObject(wb, "Toggle Corner Sharp");
                    wb.sharp[i] = !wb.sharp[i];
                    WaterBaker.RebuildSurface(wb);
                    EditorUtility.SetDirty(wb);
                }
            }
            Handles.BeginGUI();
            GUI.color = new Color(1f, 1f, 1f, 0.9f);
            GUILayout.BeginArea(new Rect(8, 8, 340, 24));
            GUILayout.Label("角編集: 点をクリックで 直角(黄□) ⇄ スムーズ(青○)", EditorStyles.helpBox);
            GUILayout.EndArea();
            GUI.color = Color.white;
            Handles.EndGUI();
            return;
        }

        // 通常: ドラッグで点を移動（角□/丸○で今のスタイルが分かる）
        for (int i = 0; i < wb.outline.Count; i++)
        {
            Vector3 p = wb.outline[i];
            float hs = HandleUtility.GetHandleSize(p) * 0.08f;
            bool sh = wb.sharp[i];
            EditorGUI.BeginChangeCheck();
            Handles.color = sh ? sharpCol : smoothCol;
            Handles.CapFunction cap = sh ? (Handles.CapFunction)Handles.CubeHandleCap : Handles.SphereHandleCap;
            Vector3 np = Handles.FreeMoveHandle(p, hs, Vector3.zero, cap);
            if (EditorGUI.EndChangeCheck())
            {
                Undo.RecordObject(wb, "Move Water Point");
                wb.outline[i] = ProjectXZ(np);
                WaterBaker.RebuildSurface(wb);   // 水面プレビューのみ即反映（地形は『掘り直す』で）
                EditorUtility.SetDirty(wb);
            }
        }

        if (addMode)
        {
            Event e = Event.current;
            if (e.alt) return;
            HandleUtility.AddDefaultControl(GUIUtility.GetControlID(FocusType.Passive));
            if (e.type == EventType.MouseDown && e.button == 0)
            {
                if (Raycast(e, out Vector3 hit))
                {
                    Undo.RecordObject(wb, "Edit Water Points");
                    if (e.shift) RemoveNear(wb, hit); else InsertOnNearestEdge(wb, hit);
                    WaterBaker.RebuildSurface(wb);   // 水面プレビューのみ（地形は『掘り直す』で）
                    EditorUtility.SetDirty(wb);
                    e.Use();
                }
            }
        }
    }

    static Vector3 ProjectXZ(Vector3 p)
    {
        var t = Terrain.activeTerrain;
        if (t != null) p.y = t.SampleHeight(p) + t.transform.position.y;
        return p;
    }

    static bool Raycast(Event e, out Vector3 hit)
    {
        hit = Vector3.zero;
        Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);
        if (Physics.Raycast(ray, out RaycastHit hi, 20000f)) { hit = hi.point; return true; }
        var t = Terrain.activeTerrain;
        if (t != null && Mathf.Abs(ray.direction.y) > 1e-4f)
        {
            float tt = -ray.origin.y / ray.direction.y;
            if (tt > 0f) { Vector3 p = ray.origin + ray.direction * tt; p.y = t.SampleHeight(p) + t.transform.position.y; hit = p; return true; }
        }
        return false;
    }

    static void RemoveNear(WaterBody wb, Vector3 p)
    {
        if (wb.outline.Count <= 3) return;
        EnsureSharp(wb);
        int best = -1; float bd = 30f * 30f;
        for (int i = 0; i < wb.outline.Count; i++) { float d = (wb.outline[i] - p).sqrMagnitude; if (d < bd) { bd = d; best = i; } }
        if (best >= 0) { wb.outline.RemoveAt(best); if (best < wb.sharp.Count) wb.sharp.RemoveAt(best); }
    }

    static void InsertOnNearestEdge(WaterBody wb, Vector3 p)
    {
        EnsureSharp(wb);
        int n = wb.outline.Count; int bestEdge = 0; float bestD = float.MaxValue;
        for (int i = 0; i < n; i++)
        {
            Vector3 a = wb.outline[i], b = wb.outline[(i + 1) % n];
            float dd = HandleUtility.DistancePointLine(p, a, b);
            if (dd < bestD) { bestD = dd; bestEdge = i; }
        }
        wb.outline.Insert(bestEdge + 1, ProjectXZ(p));
        wb.sharp.Insert(Mathf.Min(bestEdge + 1, wb.sharp.Count), false); // 新規点はスムーズ
    }
}
