using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 地形を「断面(縦断面)」で直接作るツール。
/// Scene で 2 点をクリックして測線を引き、ウィンドウのグラフ（横=距離 m / 縦=標高 m）に
/// 現況の断面が出るので、その上に目標の断面を折れ線で描いて地形へ転写する。
///
/// ・帯の幅   … 測線の両側にこの幅だけ、断面どおりの高さに揃える（幅方向は水平）
/// ・すり付け … 帯の外側へこの距離をかけて既存地形へなめらかに繋ぐ。その外は一切動かない
/// ・標高はワールド Y ＝ 海抜(m)。グラフの数値をそのまま実測標高として読める
///
/// 葵坂のような坂の縦断勾配、河岸段丘、堤、堀の法面など「断面が決まっている地形」向け。
/// 細かい凹凸はブラシ（Edo ▸ 地形 ▸ 隆起・削りブラシ）で。
///
/// ★スナップショットは隆起ブラシと共有。適用前に『📸 保存』を押しておけば一発で戻せる。
///
/// メニュー: Edo ▸ 地形 ▸ 断面編集
/// </summary>
public class EdoSectionEditor : EditorWindow
{
    enum Interp { Linear, Spline }
    enum ApplyMode { Both, RaiseOnly, LowerOnly }

    // ---- 測線 ----
    [SerializeField] Vector3 ptA, ptB;      // ワールド座標（XZ を使う。Y は表示用の地面高さ）
    [SerializeField] bool hasLine;
    // ---- 断面（x=始点からの距離 m / y=標高 m）----
    [SerializeField] List<Vector2> pts = new List<Vector2>();
    [SerializeField] Interp interp = Interp.Linear;
    // ---- 転写 ----
    [SerializeField] float bandW = 20f;     // 帯の幅(m) 全幅
    [SerializeField] float featherW = 10f;  // すり付け幅(m)
    [SerializeField] ApplyMode applyMode = ApplyMode.Both;
    [SerializeField] bool snapGrid = true;  // 距離1m / 標高0.1m にスナップ
    [SerializeField] bool showList;

    int picking;            // 0=off / 1=始点待ち / 2=終点待ち
    int drag = -1;          // ドラッグ中の制御点
    Terrain terr; TerrainData td;
    float[] cur;            // 現況断面のキャッシュ
    string snapInfo = "";
    const int SAMPLES = 240;

    [MenuItem("Edo/地形/断面編集")]
    static void Open() => GetWindow<EdoSectionEditor>("断面編集");

    void OnEnable() { SceneView.duringSceneGui += OnScene; Ensure(); snapInfo = EdoTerrainSnapshot.Info; }
    void OnDisable() { SceneView.duringSceneGui -= OnScene; }
    void Ensure() { terr = Terrain.activeTerrain; td = terr != null ? terr.terrainData : null; }

    float CellM => td != null ? Mathf.Max(td.size.x, td.size.z) / (td.heightmapResolution - 1) : 1f;
    float LineLen => hasLine ? Vector2.Distance(new Vector2(ptA.x, ptA.z), new Vector2(ptB.x, ptB.z)) : 0f;
    float GroundY(float wx, float wz)
    {
        var p = new Vector3(wx, 0f, wz);
        return terr.SampleHeight(p) + terr.transform.position.y;
    }

    // ===================================================================== GUI
    void OnGUI()
    {
        if (terr == null) { if (GUILayout.Button("地形を再取得")) Ensure(); return; }

        // ---- スナップショット ----
        EditorGUILayout.LabelField("スナップショット（戻せるように保存）", EditorStyles.boldLabel);
        EditorGUILayout.LabelField("状態", snapInfo);
        using (new EditorGUILayout.HorizontalScope())
        {
            GUI.backgroundColor = new Color(0.6f, 0.8f, 1f);
            if (GUILayout.Button("📸 保存（適用前に押す）", GUILayout.Height(24)))
            { EdoTerrainSnapshot.Save(td); snapInfo = EdoTerrainSnapshot.Info; ShowNotification(new GUIContent("スナップショット保存")); }
            GUI.backgroundColor = new Color(1f, 0.8f, 0.4f);
            using (new EditorGUI.DisabledScope(!EdoTerrainSnapshot.Exists))
                if (GUILayout.Button("↩ 戻す", GUILayout.Height(24), GUILayout.Width(90)))
                    if (EditorUtility.DisplayDialog("スナップショットに戻す", "保存した地形の状態に戻します。よろしいですか？", "戻す", "やめる"))
                        if (EdoTerrainSnapshot.Restore(terr, td)) { RebuildCurrent(); ShowNotification(new GUIContent("戻しました")); }
            GUI.backgroundColor = Color.white;
        }

        EditorGUILayout.Space(6);

        // ---- ① 測線 ----
        EditorGUILayout.LabelField("① 測線を引く", EditorStyles.boldLabel);
        GUI.backgroundColor = picking != 0 ? new Color(1f, 0.5f, 0.5f) : new Color(0.6f, 1f, 0.6f);
        if (GUILayout.Button(picking != 0 ? (picking == 1 ? "■ Scene で始点をクリック（押すと中止）" : "■ Scene で終点をクリック（押すと中止）")
                                          : (hasLine ? "▶ 測線を引き直す" : "▶ 測線を引く（Scene で2回クリック）"), GUILayout.Height(28)))
        { picking = picking != 0 ? 0 : 1; SceneView.RepaintAll(); }
        GUI.backgroundColor = Color.white;

        if (!hasLine)
        {
            EditorGUILayout.HelpBox("まず測線を引いてください。Scene で始点 → 終点の順にクリックします。\n" +
                                    "引いたあとは Scene 上の球ハンドルで端点を動かせます。", MessageType.Info);
            return;
        }

        using (new EditorGUILayout.HorizontalScope())
        {
            EditorGUI.BeginChangeCheck();
            float ax = EditorGUILayout.FloatField("始点 X", ptA.x), az = EditorGUILayout.FloatField("Z", ptA.z);
            if (EditorGUI.EndChangeCheck()) SetEnds(new Vector3(ax, 0, az), ptB);
        }
        using (new EditorGUILayout.HorizontalScope())
        {
            EditorGUI.BeginChangeCheck();
            float bx = EditorGUILayout.FloatField("終点 X", ptB.x), bz = EditorGUILayout.FloatField("Z", ptB.z);
            if (EditorGUI.EndChangeCheck()) SetEnds(ptA, new Vector3(bx, 0, bz));
        }

        float L = LineLen;
        float dY = pts.Count >= 2 ? pts[pts.Count - 1].y - pts[0].y : 0f;
        EditorGUILayout.LabelField($"水平距離 {L:F1} m ／ 目標: 始点 {pts[0].y:F2} m → 終点 {pts[pts.Count - 1].y:F2} m" +
                                   $"（高低差 {dY:+0.00;-0.00;0.00} m・平均勾配 {(L > 0.01f ? dY / L * 100f : 0f):F1} %）");

        EditorGUILayout.Space(4);

        // ---- ② 断面グラフ ----
        EditorGUILayout.LabelField("② 断面をつくる（灰=現況 / 橙=目標）", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox("グラフ上を左ドラッグ＝点を動かす／Shift+クリック＝点を追加／右クリック＝点を削除（両端は消せません）。\n" +
                                "両端の点は距離が固定で、標高だけ動きます。", MessageType.None);
        DrawGraph();

        using (new EditorGUILayout.HorizontalScope())
        {
            interp = (Interp)GUILayout.Toolbar((int)interp, new[] { "折れ線", "なめらか" }, GUILayout.Height(20));
            snapGrid = GUILayout.Toggle(snapGrid, "1m / 0.1m にスナップ", EditorStyles.miniButton, GUILayout.Height(20));
        }
        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button("現況を読み込む(9点)")) LoadCurrent(9);
            if (GUILayout.Button("両端を直線で結ぶ")) ResetToStraight();
        }

        showList = EditorGUILayout.Foldout(showList, $"制御点 {pts.Count} 個（数値で入れる）", true);
        if (showList) DrawPointList();

        EditorGUILayout.Space(6);

        // ---- ③ 転写 ----
        EditorGUILayout.LabelField("③ 地形へ転写", EditorStyles.boldLabel);
        bandW = EditorGUILayout.Slider("帯の幅(m)", bandW, 2f, 400f);
        featherW = EditorGUILayout.Slider("すり付け幅(m)", featherW, 0f, 200f);
        applyMode = (ApplyMode)GUILayout.Toolbar((int)applyMode, new[] { "盛り＋削り", "盛りのみ", "削りのみ" }, GUILayout.Height(20));

        if (bandW < CellM * 2f)
            EditorGUILayout.HelpBox($"帯の幅が地形の 1 セル({CellM:F1} m)に対して細すぎます。{CellM * 2f:F0} m 以上を推奨。", MessageType.Warning);

        GUI.backgroundColor = new Color(0.6f, 1f, 0.6f);
        using (new EditorGUI.DisabledScope(pts.Count < 2 || LineLen < 0.5f))
            if (GUILayout.Button("▶ 地形に適用", GUILayout.Height(32))) Apply();
        GUI.backgroundColor = Color.white;
    }

    // --------------------------------------------------------------- グラフ
    void DrawGraph()
    {
        Rect full = GUILayoutUtility.GetRect(10, 10000, 230, 230);
        Rect gr = new Rect(full.x + 48, full.y + 8, full.width - 58, full.height - 30);
        if (cur == null || cur.Length != SAMPLES + 1) RebuildCurrent();

        float L = Mathf.Max(LineLen, 0.001f);
        GetYRange(out float y0, out float y1);
        Vector2 P(float d, float y) => new Vector2(gr.x + d / L * gr.width,
                                                   gr.yMax - Mathf.Clamp01((y - y0) / (y1 - y0)) * gr.height);

        if (Event.current.type == EventType.Repaint)
        {
            EditorGUI.DrawRect(gr, new Color(0.16f, 0.16f, 0.16f));

            // 目盛り（標高）
            var lab = new GUIStyle(EditorStyles.miniLabel) { alignment = TextAnchor.MiddleRight };
            float stepY = NiceStep(y1 - y0);
            for (float y = Mathf.Ceil(y0 / stepY) * stepY; y <= y1; y += stepY)
            {
                float py = P(0, y).y;
                EditorGUI.DrawRect(new Rect(gr.x, py, gr.width, 1), new Color(1, 1, 1, y == 0f ? 0.35f : 0.10f));
                GUI.Label(new Rect(full.x, py - 8, 44, 16), $"{y:F0}", lab);
            }
            // 目盛り（距離）
            var lab2 = new GUIStyle(EditorStyles.miniLabel) { alignment = TextAnchor.UpperCenter };
            float stepX = NiceStep(L);
            for (float d = 0; d <= L + 0.01f; d += stepX)
            {
                float px = P(d, y0).x;
                EditorGUI.DrawRect(new Rect(px, gr.y, 1, gr.height), new Color(1, 1, 1, 0.08f));
                GUI.Label(new Rect(px - 24, gr.yMax + 2, 48, 16), $"{d:F0}", lab2);
            }

            // 現況（灰）
            var line = new Vector3[SAMPLES + 1];
            for (int i = 0; i <= SAMPLES; i++) { float d = L * i / SAMPLES; line[i] = P(d, cur[i]); }
            Handles.color = new Color(0.75f, 0.75f, 0.75f, 0.9f);
            Handles.DrawAAPolyLine(2f, line);

            // 目標（橙）
            for (int i = 0; i <= SAMPLES; i++) { float d = L * i / SAMPLES; line[i] = P(d, Eval(d)); }
            Handles.color = new Color(1f, 0.65f, 0.25f, 1f);
            Handles.DrawAAPolyLine(3f, line);

            // 制御点
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 p = P(pts[i].x, pts[i].y);
                bool end = i == 0 || i == pts.Count - 1;
                EditorGUI.DrawRect(new Rect(p.x - 4, p.y - 4, 8, 8), end ? new Color(1f, 0.9f, 0.5f) : Color.white);
            }
            GUI.Label(new Rect(full.x + 2, full.y - 2, 60, 16), "標高 m", EditorStyles.miniLabel);
            GUI.Label(new Rect(gr.xMax - 40, gr.yMax + 2, 44, 16), "距離 m", EditorStyles.miniLabel);
        }

        // ----- マウス -----
        var e = Event.current;
        int id = GUIUtility.GetControlID(FocusType.Passive);
        float DfromPx(float px) => Mathf.Clamp((px - gr.x) / gr.width * L, 0f, L);
        float YfromPx(float py) => y0 + (gr.yMax - py) / gr.height * (y1 - y0);

        if (e.type == EventType.MouseDown && full.Contains(e.mousePosition))
        {
            int near = NearestPoint(e.mousePosition, P);
            if (e.button == 1)
            {
                if (near > 0 && near < pts.Count - 1) { pts.RemoveAt(near); e.Use(); Repaint(); SceneView.RepaintAll(); }
            }
            else if (e.button == 0)
            {
                if (e.shift || near < 0)
                {
                    float d = DfromPx(e.mousePosition.x), y = YfromPx(e.mousePosition.y);
                    if (d > 0.01f && d < L - 0.01f)
                    {
                        pts.Add(new Vector2(d, y)); pts.Sort((u, v) => u.x.CompareTo(v.x));
                        drag = pts.FindIndex(q => Mathf.Approximately(q.x, d));
                        GUIUtility.hotControl = id;
                    }
                }
                else { drag = near; GUIUtility.hotControl = id; }
                e.Use(); Repaint();
            }
        }
        else if (e.type == EventType.MouseDrag && GUIUtility.hotControl == id && drag >= 0 && drag < pts.Count)
        {
            float y = YfromPx(e.mousePosition.y);
            float d = pts[drag].x;
            if (drag > 0 && drag < pts.Count - 1)
            {
                d = DfromPx(e.mousePosition.x);
                d = Mathf.Clamp(d, pts[drag - 1].x + 0.01f, pts[drag + 1].x - 0.01f);
            }
            pts[drag] = Snap(new Vector2(d, y));
            e.Use(); Repaint(); SceneView.RepaintAll();
        }
        else if (e.type == EventType.MouseUp && GUIUtility.hotControl == id)
        { GUIUtility.hotControl = 0; drag = -1; e.Use(); Repaint(); }
    }

    int NearestPoint(Vector2 mouse, System.Func<float, float, Vector2> P)
    {
        int best = -1; float bd = 10f;
        for (int i = 0; i < pts.Count; i++)
        {
            float d = Vector2.Distance(mouse, P(pts[i].x, pts[i].y));
            if (d < bd) { bd = d; best = i; }
        }
        return best;
    }

    Vector2 Snap(Vector2 p)
    {
        if (!snapGrid) return p;
        return new Vector2(Mathf.Round(p.x), Mathf.Round(p.y * 10f) / 10f);
    }

    void DrawPointList()
    {
        for (int i = 0; i < pts.Count; i++)
        {
            using (new EditorGUILayout.HorizontalScope())
            {
                EditorGUILayout.LabelField($"{i}", GUILayout.Width(18));
                EditorGUI.BeginChangeCheck();
                float d = EditorGUILayout.FloatField(pts[i].x, GUILayout.Width(60));
                float y = EditorGUILayout.FloatField(pts[i].y, GUILayout.Width(60));
                if (EditorGUI.EndChangeCheck())
                {
                    if (i == 0) d = 0f; else if (i == pts.Count - 1) d = LineLen;
                    else d = Mathf.Clamp(d, pts[i - 1].x + 0.01f, pts[i + 1].x - 0.01f);
                    pts[i] = new Vector2(d, y); SceneView.RepaintAll();
                }
                if (i < pts.Count - 1)
                {
                    float run = pts[i + 1].x - pts[i].x, rise = pts[i + 1].y - pts[i].y;
                    EditorGUILayout.LabelField($"→ 勾配 {(run > 0.01f ? rise / run * 100f : 0f):F1} %", EditorStyles.miniLabel);
                }
                else GUILayout.FlexibleSpace();
                using (new EditorGUI.DisabledScope(i == 0 || i == pts.Count - 1))
                    if (GUILayout.Button("×", GUILayout.Width(22))) { pts.RemoveAt(i); SceneView.RepaintAll(); break; }
            }
        }
        if (GUILayout.Button("＋ 中点に点を追加"))
        {
            float d = LineLen * 0.5f;
            pts.Add(new Vector2(d, Eval(d))); pts.Sort((u, v) => u.x.CompareTo(v.x));
        }
    }

    static float NiceStep(float span)
    {
        float raw = Mathf.Max(span, 0.001f) / 6f;
        float mag = Mathf.Pow(10, Mathf.Floor(Mathf.Log10(raw)));
        float n = raw / mag;
        return (n <= 1f ? 1f : n <= 2f ? 2f : n <= 5f ? 5f : 10f) * mag;
    }

    void GetYRange(out float y0, out float y1)
    {
        float lo = float.MaxValue, hi = float.MinValue;
        if (cur != null) foreach (var v in cur) { lo = Mathf.Min(lo, v); hi = Mathf.Max(hi, v); }
        foreach (var p in pts) { lo = Mathf.Min(lo, p.y); hi = Mathf.Max(hi, p.y); }
        if (lo > hi) { lo = 0; hi = 10; }
        float pad = Mathf.Max((hi - lo) * 0.15f, 1f);
        y0 = Mathf.Floor((lo - pad)); y1 = Mathf.Ceil((hi + pad));
        if (y1 - y0 < 4f) y1 = y0 + 4f;
    }

    // ------------------------------------------------------------- 断面の評価
    float Eval(float d)
    {
        int n = pts.Count;
        if (n == 0) return 0f;
        if (n == 1 || d <= pts[0].x) return pts[0].y;
        if (d >= pts[n - 1].x) return pts[n - 1].y;
        int i = 0; while (i < n - 2 && pts[i + 1].x < d) i++;
        float span = Mathf.Max(pts[i + 1].x - pts[i].x, 1e-4f);
        float u = Mathf.Clamp01((d - pts[i].x) / span);
        if (interp == Interp.Linear) return Mathf.Lerp(pts[i].y, pts[i + 1].y, u);
        float p0 = pts[Mathf.Max(0, i - 1)].y, p1 = pts[i].y, p2 = pts[i + 1].y, p3 = pts[Mathf.Min(n - 1, i + 2)].y;
        return 0.5f * ((2f * p1) + (-p0 + p2) * u + (2f * p0 - 5f * p1 + 4f * p2 - p3) * u * u
                        + (-p0 + 3f * p1 - 3f * p2 + p3) * u * u * u);
    }

    // ------------------------------------------------------------- 測線の操作
    void SetEnds(Vector3 a, Vector3 b)
    {
        float oldL = LineLen;
        ptA = new Vector3(a.x, GroundY(a.x, a.z), a.z);
        ptB = new Vector3(b.x, GroundY(b.x, b.z), b.z);
        float newL = LineLen;
        if (hasLine && oldL > 0.01f && pts.Count >= 2)
        {
            float k = newL / oldL;
            for (int i = 0; i < pts.Count; i++) pts[i] = new Vector2(pts[i].x * k, pts[i].y);
            pts[pts.Count - 1] = new Vector2(newL, pts[pts.Count - 1].y);
        }
        hasLine = true;
        RebuildCurrent(); Repaint(); SceneView.RepaintAll();
    }

    void RebuildCurrent()
    {
        cur = new float[SAMPLES + 1];
        if (!hasLine || terr == null) return;
        Vector2 A = new Vector2(ptA.x, ptA.z), B = new Vector2(ptB.x, ptB.z);
        for (int i = 0; i <= SAMPLES; i++)
        {
            Vector2 p = Vector2.Lerp(A, B, (float)i / SAMPLES);
            cur[i] = GroundY(p.x, p.y);
        }
    }

    void ResetToStraight()
    {
        RebuildCurrent();
        pts = new List<Vector2> { new Vector2(0f, cur[0]), new Vector2(LineLen, cur[SAMPLES]) };
        SceneView.RepaintAll();
    }

    void LoadCurrent(int n)
    {
        RebuildCurrent();
        n = Mathf.Max(2, n);
        pts = new List<Vector2>();
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / (n - 1);
            pts.Add(Snap(new Vector2(LineLen * t, cur[Mathf.RoundToInt(t * SAMPLES)])));
        }
        pts[0] = new Vector2(0f, pts[0].y); pts[n - 1] = new Vector2(LineLen, pts[n - 1].y);
        SceneView.RepaintAll();
    }

    // ------------------------------------------------------------------ 転写
    void Apply()
    {
        var pos = terr.transform.position; var size = td.size; int res = td.heightmapResolution;
        float mx = size.x / (res - 1), mz = size.z / (res - 1);
        Vector2 A = new Vector2(ptA.x, ptA.z), B = new Vector2(ptB.x, ptB.z);
        Vector2 dir = B - A; float L = dir.magnitude; if (L < 0.5f) return;
        dir /= L; Vector2 nrm = new Vector2(-dir.y, dir.x);
        float half = bandW * 0.5f, reach = half + featherW;

        int x0 = Mathf.Clamp(Mathf.FloorToInt((Mathf.Min(A.x, B.x) - reach - pos.x) / mx) - 1, 0, res - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((Mathf.Max(A.x, B.x) + reach - pos.x) / mx) + 1, 0, res - 1);
        int z0 = Mathf.Clamp(Mathf.FloorToInt((Mathf.Min(A.y, B.y) - reach - pos.z) / mz) - 1, 0, res - 1);
        int z1 = Mathf.Clamp(Mathf.CeilToInt((Mathf.Max(A.y, B.y) + reach - pos.z) / mz) + 1, 0, res - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        if (w < 2 || h < 2) { ShowNotification(new GUIContent("測線が地形の外です")); return; }

        Undo.RegisterCompleteObjectUndo(td, "断面で造成");
        var H = td.GetHeights(x0, z0, w, h);

        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = pos.x + (x0 + x) * mx, wz = pos.z + (z0 + z) * mz;
                Vector2 rel = new Vector2(wx, wz) - A;
                float s = Vector2.Dot(rel, dir);
                float dp = Mathf.Abs(Vector2.Dot(rel, nrm));

                float outAlong = Mathf.Max(0f, Mathf.Max(-s, s - L));
                float outPerp = Mathf.Max(0f, dp - half);
                float e = Mathf.Sqrt(outAlong * outAlong + outPerp * outPerp);
                if (e > 0f && e >= featherW) continue;                  // 帯＋すり付けの外は一切動かさない
                float wgt = e <= 0f ? 1f : 1f - Mathf.SmoothStep(0f, 1f, e / featherW);

                float targetY = Eval(Mathf.Clamp(s, 0f, L));
                float tn = Mathf.Clamp01((targetY - pos.y) / size.y);
                float src = H[z, x];
                float v = Mathf.Lerp(src, tn, wgt);
                if (applyMode == ApplyMode.RaiseOnly) v = Mathf.Max(src, v);
                else if (applyMode == ApplyMode.LowerOnly) v = Mathf.Min(src, v);
                H[z, x] = v;
            }

        td.SetHeights(x0, z0, H);
        terr.Flush();
        EdoTerrainSnapshot.SyncWaterSnaps(td, x0, z0, x1, z1);
        RebuildCurrent();
        SceneView.RepaintAll(); Repaint();
        ShowNotification(new GUIContent("断面を適用しました"));
    }

    // ================================================================= Scene
    void OnScene(SceneView sv)
    {
        if (terr == null) return;
        var e = Event.current;

        // ---- 測線のピック ----
        if (picking != 0)
        {
            HandleUtility.AddDefaultControl(GUIUtility.GetControlID(FocusType.Passive));
            if (Raycast(HandleUtility.GUIPointToWorldRay(e.mousePosition), out Vector3 hp))
            {
                Handles.color = picking == 1 ? Color.green : Color.cyan;
                Handles.DrawWireDisc(hp, Vector3.up, 3f);
                Handles.Label(hp + Vector3.up * 4f, picking == 1 ? "始点" : "終点");
                if (picking == 2) { Handles.color = Color.yellow; Handles.DrawAAPolyLine(3f, ptA, hp); }
            }
            if (e.type == EventType.MouseDown && e.button == 0 && !e.alt)
            {
                if (Raycast(HandleUtility.GUIPointToWorldRay(e.mousePosition), out Vector3 p))
                {
                    if (picking == 1) { ptA = p; picking = 2; }
                    else
                    {
                        hasLine = true; ptB = p;
                        SetEnds(ptA, ptB); ResetToStraight(); picking = 0;
                    }
                }
                e.Use(); Repaint();
            }
            sv.Repaint();
            return;
        }

        if (!hasLine) return;

        // ---- 端点ハンドル ----
        EditorGUI.BeginChangeCheck();
        Vector3 na = Handles.FreeMoveHandle(ptA, HandleUtility.GetHandleSize(ptA) * 0.09f, Vector3.zero, Handles.SphereHandleCap);
        Vector3 nb = Handles.FreeMoveHandle(ptB, HandleUtility.GetHandleSize(ptB) * 0.09f, Vector3.zero, Handles.SphereHandleCap);
        if (EditorGUI.EndChangeCheck()) SetEnds(na, nb);

        // ---- 帯・すり付けの外形 ----
        Vector2 A = new Vector2(ptA.x, ptA.z), B = new Vector2(ptB.x, ptB.z);
        Vector2 dir = B - A; float L = dir.magnitude; if (L < 0.01f) return;
        dir /= L; Vector2 nrm = new Vector2(-dir.y, dir.x);
        DrawBand(A, B, dir, nrm, bandW * 0.5f, new Color(1f, 0.65f, 0.25f, 0.9f));
        if (featherW > 0.01f)
            DrawBand(A, B, dir, nrm, bandW * 0.5f + featherW, new Color(1f, 0.65f, 0.25f, 0.35f));

        // ---- 目標断面を 3D で表示 ----
        const int N = 96;
        var prof = new Vector3[N + 1];
        for (int i = 0; i <= N; i++)
        {
            float s = L * i / N;
            Vector2 p = A + dir * s;
            prof[i] = new Vector3(p.x, Eval(s), p.y);
        }
        Handles.color = new Color(1f, 0.5f, 0.1f);
        Handles.DrawAAPolyLine(4f, prof);
        Handles.Label(prof[0] + Vector3.up * 2f, $"始 {pts[0].y:F2} m");
        Handles.Label(prof[N] + Vector3.up * 2f, $"終 {pts[pts.Count - 1].y:F2} m");
        for (int i = 1; i < pts.Count - 1; i++)
        {
            Vector2 p = A + dir * Mathf.Clamp(pts[i].x, 0f, L);
            var w = new Vector3(p.x, pts[i].y, p.y);
            Handles.color = Color.white; Handles.SphereHandleCap(0, w, Quaternion.identity, HandleUtility.GetHandleSize(w) * 0.06f, EventType.Repaint);
            Handles.Label(w + Vector3.up * 2f, $"{pts[i].x:F0}m / {pts[i].y:F2}m");
        }
    }

    /// <summary>帯の外形を地形に貼り付いた折れ線で描く。</summary>
    void DrawBand(Vector2 A, Vector2 B, Vector2 dir, Vector2 nrm, float half, Color c)
    {
        const int N = 64;
        Handles.color = c;
        for (int side = -1; side <= 1; side += 2)
        {
            var line = new Vector3[N + 1];
            for (int i = 0; i <= N; i++)
            {
                Vector2 p = Vector2.Lerp(A, B, (float)i / N) + nrm * (half * side);
                line[i] = new Vector3(p.x, GroundY(p.x, p.y) + 0.3f, p.y);
            }
            Handles.DrawAAPolyLine(2f, line);
        }
        for (int endp = 0; endp <= 1; endp++)
        {
            Vector2 o = endp == 0 ? A : B;
            var line = new Vector3[9];
            for (int i = 0; i <= 8; i++)
            {
                Vector2 p = o + nrm * Mathf.Lerp(-half, half, i / 8f);
                line[i] = new Vector3(p.x, GroundY(p.x, p.y) + 0.3f, p.y);
            }
            Handles.DrawAAPolyLine(2f, line);
        }
    }

    bool Raycast(Ray ray, out Vector3 hit)
    {
        hit = Vector3.zero;
        if (Physics.Raycast(ray, out RaycastHit rh, 100000f)) { hit = rh.point; return true; }
        if (Mathf.Abs(ray.direction.y) > 1e-4f)
        {
            float t = -(ray.origin.y - terr.transform.position.y) / ray.direction.y;
            if (t > 0) { Vector3 p = ray.origin + ray.direction * t; p.y = GroundY(p.x, p.z); hit = p; return true; }
        }
        return false;
    }
}
