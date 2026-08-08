using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// Scene上を順にクリックして多角形を作り、その面積(㎡・坪)を測るツール。
///
/// メニュー Edo ▸ Measure:
///  - 敷地面積 (多角形測定) (Cmd+Shift+J) … 測定モードのON/OFF(チェック付き)。
///
/// 使い方:
///  1) Cmd+Shift+J で測定モードON。
///  2) Scene上で敷地の角を順にクリックしていく(石垣の角・地形など何でも拾える)。
///     3点目以降、多角形が自動的に閉じて面積が常に表示される。
///  3) 確定は次のいずれか: 始点の近くをクリック / Enter / ダブルクリック。
///  4) 右クリックで直前の点を1つ取り消し。Esc で全消去。
///  5) もう一度 Cmd+Shift+J でモードOFF。
///
/// 面積は各頂点の水平座標(X,Z)だけを使うシューレース公式(高低差は無視)。
///
/// 【重要】ピッキング(HandleUtility.PickGameObject)は内部でレンダリングを行うため、
/// Repaint / Layout イベント中に呼ぶと GUI 描画コンテキストが再入し
/// "GUI Window tried to begin rendering while something else had not finished rendering!"
/// のアサーション失敗を起こして Scene ビューの描画が壊れる。
/// そのため picking は MouseMove / MouseDrag / MouseDown のときだけ実行して
/// 結果を _cursor* にキャッシュし、描画時はキャッシュを読むだけにしている。
/// </summary>
[InitializeOnLoad]
public static class EdoAreaMeasure
{
    const string MenuPath = "Edo/Measure/敷地面積 (多角形測定) %#j";
    const string PrefKey = "EdoAreaMeasure.Active";
    const float TsuboPerM2 = 121f / 400f; // 1坪 = 400/121 m2
    const float KenM = 1.818f;
    const float CloseSnapPixels = 20f;

    static bool _active;
    static readonly List<Vector3> _points = new List<Vector3>();
    static readonly List<string> _labels = new List<string>();
    static bool _closed;

    // カーソル下のピック結果キャッシュ(入力イベント時のみ更新)
    static bool _hasCursor;
    static Vector3 _cursorPoint;
    static string _cursorLabel;

    static EdoAreaMeasure()
    {
        _active = EditorPrefs.GetBool(PrefKey, false);
        if (_active) SceneView.duringSceneGui += OnSceneGui;
        EditorApplication.delayCall += () => Menu.SetChecked(MenuPath, _active);
    }

    [MenuItem(MenuPath)]
    static void Toggle()
    {
        _active = !_active;
        EditorPrefs.SetBool(PrefKey, _active);
        Menu.SetChecked(MenuPath, _active);

        if (_active)
        {
            SceneView.duringSceneGui -= OnSceneGui;
            SceneView.duringSceneGui += OnSceneGui;
        }
        else
        {
            SceneView.duringSceneGui -= OnSceneGui;
            Clear();
        }
        SceneView.RepaintAll();
    }

    static void Clear()
    {
        _points.Clear();
        _labels.Clear();
        _closed = false;
        _hasCursor = false;
    }

    static void OnSceneGui(SceneView sv)
    {
        if (!_active) return;

        Event e = Event.current;
        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);

        switch (e.type)
        {
            case EventType.KeyDown:
                if (e.keyCode == KeyCode.Escape)
                {
                    Clear(); e.Use(); sv.Repaint(); return;
                }
                if ((e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) && _points.Count >= 3)
                {
                    _closed = true; e.Use(); sv.Repaint(); return;
                }
                break;

            // ピッキングはここでだけ行う(Repaint/Layout中は絶対に呼ばない)
            case EventType.MouseMove:
            case EventType.MouseDrag:
                _hasCursor = EdoScenePick.TryPick(e.mousePosition, out _cursorPoint, out _cursorLabel);
                if (!_closed && _points.Count > 0) sv.Repaint();
                break;

            case EventType.MouseDown:
                if (e.button == 0 && !e.alt)
                {
                    _hasCursor = EdoScenePick.TryPick(e.mousePosition, out _cursorPoint, out _cursorLabel);
                    if (_hasCursor) HandleLeftClick(e, sv);
                    e.Use();
                }
                else if (e.button == 1 && !_closed)
                {
                    if (_points.Count > 0)
                    {
                        _points.RemoveAt(_points.Count - 1);
                        _labels.RemoveAt(_labels.Count - 1);
                    }
                    e.Use(); sv.Repaint();
                }
                break;
        }

        // 描画のみ(ピッキングしない)
        DrawHandles();
        DrawHud();
    }

    static void HandleLeftClick(Event e, SceneView sv)
    {
        if (_closed)
        {
            // 確定後のクリックは新しい多角形の1点目
            Clear();
            _hasCursor = EdoScenePick.TryPick(e.mousePosition, out _cursorPoint, out _cursorLabel);
            if (_hasCursor) { _points.Add(_cursorPoint); _labels.Add(_cursorLabel); }
            sv.Repaint();
            return;
        }

        // ダブルクリック、または始点近くのクリックで確定
        if (_points.Count >= 3 &&
            (e.clickCount >= 2 || ScreenDist(_points[0], e.mousePosition) < CloseSnapPixels))
        {
            _closed = true;
            sv.Repaint();
            return;
        }

        _points.Add(_cursorPoint);
        _labels.Add(_cursorLabel);
        sv.Repaint();
    }

    static float ScreenDist(Vector3 worldPoint, Vector2 guiPos)
    {
        Vector2 sp = HandleUtility.WorldToGUIPoint(worldPoint);
        return Vector2.Distance(sp, guiPos);
    }

    static void DrawHandles()
    {
        if (_points.Count == 0) return;

        // 頂点
        Handles.color = new Color(1f, 0.85f, 0.2f);
        for (int i = 0; i < _points.Count; i++)
        {
            float size = HandleUtility.GetHandleSize(_points[i]) * 0.07f;
            Handles.SphereHandleCap(0, _points[i], Quaternion.identity, size, EventType.Repaint);
        }

        // 確定済みの辺
        for (int i = 0; i + 1 < _points.Count; i++)
        {
            Handles.color = new Color(1f, 0.85f, 0.2f);
            Handles.DrawLine(_points[i], _points[i + 1], 3f);
            DrawEdgeLabel(_points[i], _points[i + 1]);
        }

        if (_closed)
        {
            Handles.color = new Color(1f, 0.85f, 0.2f);
            Handles.DrawLine(_points[_points.Count - 1], _points[0], 3f);
            DrawEdgeLabel(_points[_points.Count - 1], _points[0]);
        }
        else
        {
            if (_hasCursor)
            {
                // 次のクリック位置のプレビュー(キャッシュ済みの点を描くだけ)
                Handles.color = new Color(1f, 1f, 1f, 0.55f);
                Handles.DrawDottedLine(_points[_points.Count - 1], _cursorPoint, 3f);

                float sizeC = HandleUtility.GetHandleSize(_cursorPoint) * 0.06f;
                Handles.SphereHandleCap(0, _cursorPoint, Quaternion.identity, sizeC, EventType.Repaint);
                DrawTag(_cursorPoint, _cursorLabel);
            }
            if (_points.Count >= 3)
            {
                Handles.color = new Color(1f, 0.85f, 0.2f, 0.35f);
                Handles.DrawDottedLine(_points[_points.Count - 1], _points[0], 2f);
            }
        }

        if (_points.Count >= 3) DrawAreaLabel(_points);
    }

    static void DrawTag(Vector3 p, string label)
    {
        var style = new GUIStyle(EditorStyles.miniLabel)
        {
            normal = { textColor = new Color(0.75f, 0.9f, 1f) },
            fontSize = 10,
        };
        string name = string.IsNullOrEmpty(label) ? "" : "  " + label + "\n";
        Handles.Label(p, name + $"  X {p.x:0.00}  Z {p.z:0.00}", style);
    }

    static void DrawEdgeLabel(Vector3 a, Vector3 b)
    {
        float horiz = new Vector2(b.x - a.x, b.z - a.z).magnitude;
        var style = new GUIStyle(EditorStyles.miniLabel)
        {
            normal = { textColor = new Color(1f, 0.95f, 0.7f) },
            fontSize = 10,
        };
        Handles.Label((a + b) * 0.5f, $"{horiz:0.00} m ({horiz / KenM:0.00}間)", style);
    }

    static void DrawAreaLabel(List<Vector3> pts)
    {
        float m2 = PolygonArea(pts);
        float tsubo = m2 * TsuboPerM2;
        float per = 0f;
        for (int i = 0; i < pts.Count; i++)
        {
            var a = pts[i]; var b = pts[(i + 1) % pts.Count];
            per += new Vector2(b.x - a.x, b.z - a.z).magnitude;
        }

        Vector3 centroid = Vector3.zero;
        foreach (var p in pts) centroid += p;
        centroid /= pts.Count;

        var style = new GUIStyle(EditorStyles.boldLabel)
        {
            normal = { textColor = Color.white, background = Texture2D.grayTexture },
            fontSize = 13,
            alignment = TextAnchor.MiddleCenter,
        };

        string state = _closed ? "確定" : "(見込み)";
        Handles.Label(centroid, $"  面積 {state}\n  {m2:0.0} m2 = {tsubo:0.0} 坪\n  周長 {per:0.0} m  ", style);
    }

    static void DrawHud()
    {
        Handles.BeginGUI();
        var style = new GUIStyle(EditorStyles.miniBoldLabel)
        {
            normal = { textColor = new Color(1f, 0.85f, 0.2f) },
        };
        string hint;
        if (_closed) hint = $"敷地面積: 確定({_points.Count}点)。クリックで新しい多角形";
        else if (_points.Count == 0) hint = "敷地面積: 1点目(角)をクリック";
        else hint = $"敷地面積: {_points.Count}点。始点付近クリック/Enter/ダブルクリックで確定 (右クリック:1つ戻す / Esc:全消去)";
        GUI.Label(new Rect(8, 8, 460, 22), "● " + hint, style);
        Handles.EndGUI();
    }

    static float PolygonArea(List<Vector3> pts)
    {
        float s = 0f;
        for (int i = 0; i < pts.Count; i++)
        {
            var p = pts[i]; var q = pts[(i + 1) % pts.Count];
            s += p.x * q.z - q.x * p.z;
        }
        return Mathf.Abs(s) * 0.5f;
    }
}

/// <summary>
/// Scene上のクリック位置からワールド座標を拾う共通ロジック。
/// コライダー / コライダー無しのメッシュ表面(Editorピッキング＋レイ-三角形交差) /
/// 地形ハイトフィールド の3系統を試し、レイ上いちばん手前のヒットを採用する。
///
/// 【重要】内部で HandleUtility.PickGameObject を使うため、
/// Repaint / Layout イベント中に呼んではいけない(GUI描画コンテキストが再入して壊れる)。
/// 呼んでよいのは MouseDown / MouseMove / MouseDrag など入力イベントのときだけ。
/// </summary>
static class EdoScenePick
{
    public static bool TryPick(Vector2 guiPos, out Vector3 point, out string label)
    {
        point = default;
        label = null;
        Ray ray = HandleUtility.GUIPointToWorldRay(guiPos);

        float best = float.MaxValue;
        bool found = false;

        if (Physics.Raycast(ray, out var hit, 100000f))
        {
            best = hit.distance;
            point = hit.point;
            label = hit.collider.name;
            found = true;
        }

        if (TryPickMesh(guiPos, ray, out Vector3 mp, out float md, out string mn) && md < best)
        {
            best = md;
            point = mp;
            label = mn;
            found = true;
        }

        if (TryRaycastTerrain(ray, out Vector3 tp))
        {
            float dist = Vector3.Distance(ray.origin, tp);
            if (dist < best)
            {
                point = tp;
                label = "地形";
                found = true;
            }
        }

        return found;
    }

    static bool TryPickMesh(Vector2 guiPos, Ray ray, out Vector3 point, out float dist, out string name)
    {
        point = default;
        dist = float.MaxValue;
        name = null;

        GameObject go = HandleUtility.PickGameObject(guiPos, false);
        if (go == null) return false;

        var mf = go.GetComponent<MeshFilter>();
        Mesh mesh = mf != null ? mf.sharedMesh : null;

        if (mesh != null && mesh.isReadable)
        {
            var tr = go.transform;
            Vector3 lo = tr.InverseTransformPoint(ray.origin);
            Vector3 ld = tr.InverseTransformVector(ray.direction);
            var verts = mesh.vertices;
            var tris = mesh.triangles;
            float bestT = float.MaxValue;
            bool hitAny = false;
            for (int i = 0; i + 2 < tris.Length; i += 3)
            {
                if (RayTri(lo, ld, verts[tris[i]], verts[tris[i + 1]], verts[tris[i + 2]], out float t) && t < bestT)
                {
                    bestT = t;
                    hitAny = true;
                }
            }
            if (hitAny)
            {
                point = tr.TransformPoint(lo + ld * bestT);
                dist = Vector3.Distance(ray.origin, point);
                name = go.name;
                return true;
            }
            return false;
        }

        var rend = go.GetComponent<Renderer>();
        if (rend != null && rend.bounds.IntersectRay(ray, out float bd))
        {
            point = ray.origin + ray.direction.normalized * bd;
            dist = bd;
            name = go.name + " ≈";
            return true;
        }
        return false;
    }

    static bool RayTri(Vector3 o, Vector3 d, Vector3 v0, Vector3 v1, Vector3 v2, out float t)
    {
        t = 0f;
        const float EPS = 1e-8f;
        Vector3 e1 = v1 - v0, e2 = v2 - v0;
        Vector3 p = Vector3.Cross(d, e2);
        float det = Vector3.Dot(e1, p);
        if (det > -EPS && det < EPS) return false;
        float inv = 1f / det;
        Vector3 tv = o - v0;
        float u = Vector3.Dot(tv, p) * inv;
        if (u < 0f || u > 1f) return false;
        Vector3 q = Vector3.Cross(tv, e1);
        float v = Vector3.Dot(d, q) * inv;
        if (v < 0f || u + v > 1f) return false;
        t = Vector3.Dot(e2, q) * inv;
        return t > EPS;
    }

    static bool TryRaycastTerrain(Ray ray, out Vector3 point)
    {
        point = default;
        const float maxDist = 20000f;
        const float step = 2f;
        float prevDiff = 0f;
        bool havePrev = false;
        Vector3 prevPos = ray.origin;

        for (float t = 0f; t <= maxDist; t += step)
        {
            Vector3 pos = ray.origin + ray.direction * t;
            if (!TrySampleTerrain(pos, out float gy))
            {
                havePrev = false;
                continue;
            }
            float diff = pos.y - gy;
            if (havePrev && prevDiff > 0f && diff <= 0f)
            {
                float f = prevDiff / (prevDiff - diff);
                point = Vector3.Lerp(prevPos, pos, f);
                if (TrySampleTerrain(point, out float fy)) point.y = fy;
                return true;
            }
            prevDiff = diff;
            prevPos = pos;
            havePrev = true;
        }
        return false;
    }

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
