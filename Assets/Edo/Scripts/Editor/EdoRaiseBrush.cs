using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 地形を手描きで隆起／削り／ならしするブラシ。Scene で地形を左ドラッグすると、
/// 半径内の高さを盛り上げる(盛り土)・掘り下げる(削り)・平滑化する(ならし)。
/// 葵坂のように「今は無い丘」を地形に復元するのに使う。
///
/// ・盛り土 / 削り は「m/ストローク」で高さを加減。Alt(Option)を押しながらで一時的に反転。
/// ・なぞるほど盛り(削り)が積み重なる、標準的なスカルプト操作。フォールオフで自然なドーム状になる。
/// ・「ならし」モード＋● 円 = 岸などを部分的になだらかにする（旧 Bank Smooth Brush を統合）。
///
/// ★スナップショット: ブラシ前に『📸 スナップショット保存』で地形(＋水域スナップ)を丸ごと保存。
///   塗ったあと『↩ スナップショットに戻す』で一発で戻せる（Cmd+Z 連打不要）。
///   スナップは Library に保存され、スクリプト再コンパイルをまたいでも残る。
///
/// メニュー: Edo ▸ 地形 ▸ 隆起・削りブラシ
/// </summary>
public class EdoRaiseBrush : EditorWindow
{
    enum Mode { Raise, Lower, Smooth }
    enum Shape { Square, Circle }   // 四角をメインに（既定・トグル先頭）

    Mode mode = Mode.Raise;
    Shape shape = Shape.Square;
    float radius = 25f;
    float amountM = 0.5f;   // 盛り土/削りの1ストロークあたりの高さ(m)。四角(垂直)ではクリック地点±この高さのレベルに揃える
    float strength = 0.5f;  // ならしの強さ
    float squareAngleDeg = 0f;  // 四角の回転(度)。軸並行=0。90°で一周（正方形の対称性）
    bool painting;
    Terrain terr;
    TerrainData td;
    int aMinX, aMinZ, aMaxX, aMaxZ; bool touched;
    float strokeTargetN;   // 四角(垂直)の1ストロークの目標高さ(正規化)。ドラッグ中は一定
    string snapInfo = "";

    [MenuItem("Edo/地形/隆起・削りブラシ")]
    static void Open() => GetWindow<EdoRaiseBrush>("Raise / Lower");

    void OnEnable() { SceneView.duringSceneGui += OnScene; Ensure(); RefreshSnapInfo(); }
    void OnDisable() { SceneView.duringSceneGui -= OnScene; }
    void Ensure() { terr = Terrain.activeTerrain; td = terr != null ? terr.terrainData : null; }
    void RefreshSnapInfo() { snapInfo = EdoTerrainSnapshot.Info; }

    void OnGUI()
    {
        if (terr == null) { if (GUILayout.Button("地形を再取得")) Ensure(); return; }

        // ---- スナップショット ----
        EditorGUILayout.LabelField("スナップショット（戻せるように保存）", EditorStyles.boldLabel);
        EditorGUILayout.LabelField("状態", snapInfo);
        GUI.backgroundColor = new Color(0.6f, 0.8f, 1f);
        if (GUILayout.Button("📸 スナップショット保存（ブラシ前に押す）", GUILayout.Height(28))) SaveSnapshot();
        GUI.backgroundColor = new Color(1f, 0.8f, 0.4f);
        using (new EditorGUI.DisabledScope(!EdoTerrainSnapshot.Exists))
            if (GUILayout.Button("↩ スナップショットに戻す", GUILayout.Height(28)))
            {
                if (EditorUtility.DisplayDialog("スナップショットに戻す", "保存した地形の状態に戻します。よろしいですか？", "戻す", "やめる"))
                    RestoreSnapshot();
            }
        GUI.backgroundColor = Color.white;

        EditorGUILayout.Space(6);
        // ---- ブラシ ----
        EditorGUILayout.LabelField("隆起ブラシ", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox(
            "モードと形を選び『▶ 塗る』→ Scene で地形を左ドラッグ。\n" +
            "・盛り土 = 盛り上げる / 削り = 掘り下げる / ならし = 凸凹を平滑化\n" +
            "・形 ■ 四角(垂直) = 正方形を『クリック地点±量』の一定レベルに揃える（天面フラット）\n" +
            "  └ 外枠の外は動かさず、壁のスロープは枠の内側に収まる（内側の細線＝平らになる天面）\n" +
            "  └ 回転スライダー、または Scene 上で [ ] キーで四角の向きを回せる\n" +
            "・形 ● 円(なだらか) = フォールオフで自然なドーム状（なぞるほど高く）\n" +
            "Alt(Option)を押しながらで 盛り土⇔削り を一時反転。一発で戻すなら上のスナップショット。",
            MessageType.Info);

        mode = (Mode)GUILayout.Toolbar((int)mode, new[] { "盛り土", "削り", "ならし" }, GUILayout.Height(24));
        shape = (Shape)GUILayout.Toolbar((int)shape, new[] { "■ 四角(垂直)", "● 円(なだらか)" }, GUILayout.Height(22));
        radius = EditorGUILayout.Slider(shape == Shape.Square ? "四角の半辺(m)" : "ブラシ半径(m)", radius, 3f, 150f);
        if (shape == Shape.Square)
        {
            using (new EditorGUILayout.HorizontalScope())
            {
                squareAngleDeg = EditorGUILayout.Slider("四角の回転(°)", squareAngleDeg, 0f, 90f);
                if (GUILayout.Button("0°", GUILayout.Width(36))) squareAngleDeg = 0f;
            }
        }
        if (mode == Mode.Smooth)
            strength = EditorGUILayout.Slider("ならしの強さ", strength, 0.05f, 1f);
        else
            amountM = EditorGUILayout.Slider(shape == Shape.Square ? "段差の高さ(m)" : "盛り/削り量(m/ストローク)", amountM, 0.02f, 5f);

        GUI.backgroundColor = painting ? new Color(1f, 0.5f, 0.5f) : new Color(0.6f, 1f, 0.6f);
        if (GUILayout.Button(painting ? "■ 停止" : "▶ 塗る", GUILayout.Height(32))) { painting = !painting; SceneView.RepaintAll(); }
        GUI.backgroundColor = Color.white;

        if (painting)
            EditorGUILayout.HelpBox("塗るモード中。Scene で左ドラッグしてください。", MessageType.None);
    }

    // ================= スナップショット（実体は EdoTerrainSnapshot と共有） =================
    void SaveSnapshot()
    {
        EdoTerrainSnapshot.Save(td);
        RefreshSnapInfo(); ShowNotification(new GUIContent("スナップショット保存"));
    }

    void RestoreSnapshot()
    {
        if (EdoTerrainSnapshot.Restore(terr, td))
            ShowNotification(new GUIContent("スナップショットに戻しました"));
    }

    // ================= ブラシ =================
    void OnScene(SceneView sv)
    {
        if (terr == null || !painting) return;
        Event e = Event.current;
        HandleUtility.AddDefaultControl(GUIUtility.GetControlID(FocusType.Passive));
        Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);

        // [ ] キーで四角を回転（塗る前でもドラッグ中でも効く）
        if (shape == Shape.Square && e.type == EventType.KeyDown &&
            (e.keyCode == KeyCode.LeftBracket || e.keyCode == KeyCode.RightBracket))
        {
            squareAngleDeg = Mathf.Repeat(squareAngleDeg + (e.keyCode == KeyCode.RightBracket ? 5f : -5f), 90f);
            Repaint(); sv.Repaint(); e.Use(); return;
        }

        bool invert = e.alt;
        if (Raycast(ray, out Vector3 hit))
        {
            Color c = mode == Mode.Smooth ? new Color(0.6f, 0.9f, 1f)
                    : (mode == Mode.Raise) ^ invert ? new Color(0.5f, 1f, 0.5f)   // 盛り土=緑
                                                    : new Color(1f, 0.6f, 0.4f);   // 削り=橙
            Handles.color = c;
            if (shape == Shape.Square)
            {
                float r = radius;
                float rad = squareAngleDeg * Mathf.Deg2Rad, cs = Mathf.Cos(rad), sn = Mathf.Sin(rad);
                Vector3 Corner(float ox, float oz) => hit + new Vector3(ox * cs - oz * sn, 0, ox * sn + oz * cs);
                // 外枠 = この外は一切動かない境界
                Handles.DrawAAPolyLine(3f, new[] { Corner(-r, -r), Corner(r, -r), Corner(r, r), Corner(-r, r), Corner(-r, -r) });
                // 内枠 = 実際に平らになる天面（外周1セルは壁のスロープになる）
                float wall = Mathf.Max(td.size.x, td.size.z) / (td.heightmapResolution - 1);
                float ri = Mathf.Max(r - wall, wall * 0.5f);
                Color ic = Handles.color; ic.a = 0.5f; Handles.color = ic;
                Handles.DrawAAPolyLine(1.5f, new[] { Corner(-ri, -ri), Corner(ri, -ri), Corner(ri, ri), Corner(-ri, ri), Corner(-ri, -ri) });
            }
            else
            {
                Handles.DrawWireDisc(hit, Vector3.up, radius);
                Handles.DrawWireDisc(hit, Vector3.up, Mathf.Max(0f, radius - 0.6f));
            }
        }

        // Alt はブラシ反転に使うので、Alt+ドラッグでの視点回転を奪わないよう button==0 のみ処理
        if (e.type == EventType.MouseDown && e.button == 0 && !e.control && !e.command)
        { Undo.RegisterCompleteObjectUndo(td, "Raise/Lower Brush"); touched = false; StampAt(ray, invert); e.Use(); }
        else if (e.type == EventType.MouseDrag && e.button == 0 && !e.control && !e.command)
        { StampAt(ray, invert); e.Use(); }
        else if (e.type == EventType.MouseUp && e.button == 0)
        { if (touched) UpdateSnapshots(); e.Use(); }
        sv.Repaint();
    }

    void StampAt(Ray ray, bool invert)
    {
        if (!Raycast(ray, out Vector3 hit)) return;
        var pos = terr.transform.position; var size = td.size; int res = td.heightmapResolution;
        float mx = size.x / (res - 1), mz = size.z / (res - 1);   // 1セルの実寸(m)
        int cx = Mathf.RoundToInt((hit.x - pos.x) / size.x * (res - 1));
        int cz = Mathf.RoundToInt((hit.z - pos.z) / size.z * (res - 1));
        int rpx = Mathf.CeilToInt(radius / size.x * (res - 1)); const int pad = 2;
        // 回転した四角は対角がradius√2まで伸びるので走査範囲を広げる
        float reach = shape == Shape.Square ? radius * 1.4143f : radius;
        int scanX = Mathf.CeilToInt(reach / mx), scanZ = Mathf.CeilToInt(reach / mz);
        int x0 = Mathf.Clamp(cx - scanX - pad, 0, res - 1), x1 = Mathf.Clamp(cx + scanX + pad, 0, res - 1);
        int z0 = Mathf.Clamp(cz - scanZ - pad, 0, res - 1), z1 = Mathf.Clamp(cz + scanZ + pad, 0, res - 1);
        float sqRad = squareAngleDeg * Mathf.Deg2Rad, sqCs = Mathf.Cos(sqRad), sqSn = Mathf.Sin(sqRad);
        // 四角の一番外の1セル分は元の高さのまま残す → 斜面(壁)が枠の内側に収まり、枠の外は一切動かない
        float wall = Mathf.Max(mx, mz);
        float innerR = Mathf.Max(radius - wall, wall * 0.5f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1; if (w < 5 || h < 5) return;
        var H = td.GetHeights(x0, z0, w, h);
        var src = (float[,])H.Clone();

        // 盛り土/削り量(m) を正規化高さに換算
        float dhNorm = amountM / size.y;
        bool raise = (mode == Mode.Raise) ^ invert;
        float signed = (mode == Mode.Smooth) ? 0f : (raise ? dhNorm : -dhNorm);

        // 四角(垂直)の盛り/削り: ストローク開始時にクリック地点±量の目標レベルを固定 → なぞっても均一なフラット面になる
        if (shape == Shape.Square && mode != Mode.Smooth && !touched)
        {
            float targetY = hit.y + (raise ? amountM : -amountM);
            strokeTargetN = Mathf.Clamp01((targetY - pos.y) / size.y);
        }

        for (int z = pad; z < h - pad; z++)
            for (int x = pad; x < w - pad; x++)
            {
                int gx = x0 + x, gz = z0 + z; float dx = gx - cx, dz = gz - cz;

                // 形の内外判定とフォールオフ
                float fall;
                if (shape == Shape.Square)
                {
                    // 実寸(m)へ換算 → 四角のローカル軸(-angle回転)へ揃えて内外判定
                    float wx = dx * mx, wz = dz * mz;
                    float rx = wx * sqCs + wz * sqSn, rz = -wx * sqSn + wz * sqCs;
                    // innerR で判定 = 外周1セルは触らないので枠の外へスロープが漏れない
                    if (Mathf.Abs(rx) > innerR || Mathf.Abs(rz) > innerR) continue; // 回転対応の正方形
                    fall = 1f; // 垂直(フラット)
                }
                else
                {
                    float dist = Mathf.Sqrt(dx * dx + dz * dz) / Mathf.Max(1, rpx);
                    if (dist > 1f) continue;
                    fall = Mathf.SmoothStep(1f, 0f, dist);
                }

                if (mode == Mode.Smooth)
                {
                    float sum = 0; int n = 0;
                    for (int kz = -2; kz <= 2; kz++) for (int kx = -2; kx <= 2; kx++) { sum += src[z + kz, x + kx]; n++; }
                    H[z, x] = Mathf.Lerp(src[z, x], sum / n, fall * strength * 0.6f);
                }
                else if (shape == Shape.Square)
                {
                    // 目標レベルへ揃える（盛り=上げるだけ / 削り=下げるだけ）→ 天面フラット・側面垂直
                    H[z, x] = raise ? Mathf.Max(src[z, x], strokeTargetN) : Mathf.Min(src[z, x], strokeTargetN);
                }
                else
                {
                    H[z, x] = Mathf.Clamp01(src[z, x] + signed * fall);
                }
            }
        td.SetHeights(x0, z0, H);
        if (!touched) { aMinX = x0; aMinZ = z0; aMaxX = x1; aMaxZ = z1; touched = true; }
        else { aMinX = Mathf.Min(aMinX, x0); aMinZ = Mathf.Min(aMinZ, z0); aMaxX = Mathf.Max(aMaxX, x1); aMaxZ = Mathf.Max(aMaxZ, z1); }
    }

    void UpdateSnapshots() => EdoTerrainSnapshot.SyncWaterSnaps(td, aMinX, aMinZ, aMaxX, aMaxZ);

    bool Raycast(Ray ray, out Vector3 hit)
    {
        hit = Vector3.zero;
        if (Physics.Raycast(ray, out RaycastHit rh, 100000f)) { hit = rh.point; return true; }
        if (Mathf.Abs(ray.direction.y) > 1e-4f)
        {
            float t = -(ray.origin.y - terr.transform.position.y) / ray.direction.y;
            if (t > 0) { Vector3 p = ray.origin + ray.direction * t; p.y = terr.SampleHeight(p) + terr.transform.position.y; hit = p; return true; }
        }
        return false;
    }
}
