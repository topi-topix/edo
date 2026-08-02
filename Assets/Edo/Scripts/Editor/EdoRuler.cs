using UnityEngine;
using UnityEditor;

/// <summary>
/// 2点クリックで距離を測る定規ツール。
///
/// メニュー Edo ▸ Measure:
///  - Ruler (2点測定) (Cmd+Shift+K) … 測定モードのON/OFF(チェック付き)。
///
/// 使い方:
///  1) Cmd+Shift+K で測定モードON。
///  2) Scene上で地形やオブジェクト表面を1点クリック(始点A)、もう1点クリック(終点B)。
///  3) A-B間の 直線距離 / 水平距離(XZ) / 高低差(Y) がラベルで出る。各端点が
///     何を拾ったか(地形/オブジェクト名)も端点脇に表示。
///  4) さらにクリックすると新しい始点Aから測り直し。
///  5) Esc または もう一度 Cmd+Shift+K でモードOFF＆クリア。
///
/// クリック地点は「コライダー」「コライダー無しのメッシュ表面(Editorピッキング＋
/// レイ-三角形交差)」「地形ハイトフィールド」の3系統で拾い、レイ上いちばん手前の
/// ヒットを採用する。これで 地形↔地形 / 地形↔オブジェクト / オブジェクト↔オブジェクト
/// を混在して測れる。Read/Write 無効かつコライダー無しのインポートメッシュだけは
/// バウンディングボックス概算(名前末尾に ≈)へフォールバックする。
/// </summary>
[InitializeOnLoad]
public static class EdoRuler
{
    const string MenuPath = "Edo/Measure/Ruler (2点測定) %#k";
    const string PrefKey = "EdoRuler.Active";

    static bool _active;
    static bool _hasA;
    static bool _hasB;
    static Vector3 _a;
    static Vector3 _b;
    static string _aLabel = "";
    static string _bLabel = "";

    static EdoRuler()
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
        _hasA = _hasB = false;
        _aLabel = _bLabel = "";
    }

    static void OnSceneGui(SceneView sv)
    {
        if (!_active) return;

        Event e = Event.current;

        // 選択・デセレクトを奪うためのデフォルトコントロール
        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);

        // Esc でクリア/解除
        if (e.type == EventType.KeyDown && e.keyCode == KeyCode.Escape)
        {
            Clear();
            e.Use();
            sv.Repaint();
            return;
        }

        // 左クリックで点を打つ(修飾キー無し。Altはカメラ操作に譲る)
        if (e.type == EventType.MouseDown && e.button == 0 && !e.alt)
        {
            if (TryPick(e.mousePosition, out Vector3 p, out string label))
            {
                if (!_hasA || (_hasA && _hasB))
                {
                    // 新規計測の始点
                    _a = p;
                    _aLabel = label;
                    _hasA = true;
                    _hasB = false;
                }
                else
                {
                    _b = p;
                    _bLabel = label;
                    _hasB = true;
                }
                e.Use();
                sv.Repaint();
            }
        }

        // ドラッグ中プレビュー用に常時再描画
        if (_hasA && !_hasB && e.type == EventType.MouseMove)
            sv.Repaint();

        DrawHandles(e);
        DrawHud(sv);
    }

    static void DrawHandles(Event e)
    {
        if (!_hasA) return;

        Handles.color = new Color(1f, 0.85f, 0.2f);
        float sizeA = HandleUtility.GetHandleSize(_a) * 0.08f;
        Handles.SphereHandleCap(0, _a, Quaternion.identity, sizeA, EventType.Repaint);
        DrawTag(_a, _aLabel);

        // 終点が未確定ならカーソル位置をプレビュー終点に
        Vector3 b = _b;
        string bLabel = _bLabel;
        bool showB = _hasB;
        if (!_hasB && TryPick(e.mousePosition, out Vector3 preview, out string previewLabel))
        {
            b = preview;
            bLabel = previewLabel;
            showB = true;
        }

        if (showB)
        {
            float sizeB = HandleUtility.GetHandleSize(b) * 0.08f;
            Handles.SphereHandleCap(0, b, Quaternion.identity, sizeB, EventType.Repaint);
            DrawTag(b, bLabel);

            Handles.color = new Color(1f, 0.85f, 0.2f);
            Handles.DrawLine(_a, b, 3f);

            // 水平/垂直の補助線(直角三角形)
            Vector3 corner = new Vector3(b.x, _a.y, b.z);
            Handles.color = new Color(1f, 1f, 1f, 0.35f);
            Handles.DrawDottedLine(_a, corner, 4f);
            Handles.DrawDottedLine(corner, b, 4f);

            DrawLabel(_a, b);
        }
    }

    /// <summary>端点脇に「拾った対象名」と「ワールド絶対座標(XYZ)」を小さく出す。</summary>
    static void DrawTag(Vector3 p, string label)
    {
        var style = new GUIStyle(EditorStyles.miniLabel)
        {
            normal = { textColor = new Color(0.75f, 0.9f, 1f) },
            fontSize = 10,
        };
        string name = string.IsNullOrEmpty(label) ? "" : "  " + label + "\n";
        string coord = $"  X {p.x:0.00}  Y {p.y:0.00}  Z {p.z:0.00}";
        Handles.Label(p, name + coord, style);
    }

    static void DrawLabel(Vector3 a, Vector3 b)
    {
        Vector3 d = b - a;
        float straight = d.magnitude;
        float horizontal = new Vector2(d.x, d.z).magnitude;
        float vertical = d.y;

        var style = new GUIStyle(EditorStyles.boldLabel)
        {
            normal = { textColor = Color.white },
            fontSize = 12,
            alignment = TextAnchor.MiddleLeft,
        };
        style.normal.background = Texture2D.grayTexture;

        string text =
            $"  直線 {straight:0.00} m\n" +
            $"  水平 {horizontal:0.00} m\n" +
            $"  高低差 {vertical:+0.00;-0.00;0.00} m  ";

        Vector3 mid = (a + b) * 0.5f;
        Handles.Label(mid, text, style);
    }

    static void DrawHud(SceneView sv)
    {
        Handles.BeginGUI();
        var r = new Rect(8, 8, 220, 22);
        var style = new GUIStyle(EditorStyles.miniBoldLabel)
        {
            normal = { textColor = new Color(1f, 0.85f, 0.2f) },
        };
        string hint = !_hasA ? "定規: 始点をクリック"
                     : !_hasB ? "定規: 終点をクリック"
                     : "定規: 次のクリックで測り直し";
        GUI.Label(r, "● " + hint + "  (Esc:クリア)", style);
        Handles.EndGUI();
    }

    /// <summary>
    /// スクリーン座標からワールド上の点を拾う。コライダー / コライダー無しの
    /// メッシュ表面 / 地形ハイトフィールド の3系統を試し、レイ上いちばん手前を採用。
    /// </summary>
    static bool TryPick(Vector2 guiPos, out Vector3 point, out string label)
    {
        point = default;
        label = null;
        Ray ray = HandleUtility.GUIPointToWorldRay(guiPos);

        float best = float.MaxValue;
        bool found = false;

        // 1) 物理コライダー(メッシュ・地形コライダー等)
        if (Physics.Raycast(ray, out var hit, 100000f))
        {
            best = hit.distance;
            point = hit.point;
            label = hit.collider.name;
            found = true;
        }

        // 2) コライダー無しのメッシュ表面(Editorのピッキング＋レイ-三角形交差)
        if (TryPickMesh(guiPos, ray, out Vector3 mp, out float md, out string mn) && md < best)
        {
            best = md;
            point = mp;
            label = mn;
            found = true;
        }

        // 3) 地形ハイトフィールド(コライダーが無い地形向けの保険)
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

    /// <summary>
    /// カーソル下のオブジェクトをEditorピッキングで特定し、そのメッシュ三角形との
    /// 交点を求める(コライダー不要)。Read/Write 無効なメッシュはバウンズ概算へ。
    /// </summary>
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
            // レイをローカル空間へ移してから三角形交差(方向は正規化しない=交点は lo+ld*t で復元)
            Vector3 lo = tr.InverseTransformPoint(ray.origin);
            Vector3 ld = tr.InverseTransformVector(ray.direction);
            var verts = mesh.vertices;
            var tris = mesh.triangles;
            float bestT = float.MaxValue;
            bool hit = false;
            for (int i = 0; i + 2 < tris.Length; i += 3)
            {
                if (RayTri(lo, ld, verts[tris[i]], verts[tris[i + 1]], verts[tris[i + 2]], out float t) && t < bestT)
                {
                    bestT = t;
                    hit = true;
                }
            }
            if (hit)
            {
                point = tr.TransformPoint(lo + ld * bestT);
                dist = Vector3.Distance(ray.origin, point);
                name = go.name;
                return true;
            }
            return false;
        }

        // Read/Write 無効 or メッシュ無し: レンダラのバウンディングボックスで概算
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

    /// <summary>Möller–Trumbore レイ-三角形交差。t>0 のとき交差(方向ld基準の媒介変数)。</summary>
    static bool RayTri(Vector3 o, Vector3 d, Vector3 v0, Vector3 v1, Vector3 v2, out float t)
    {
        t = 0f;
        const float EPS = 1e-8f;
        Vector3 e1 = v1 - v0, e2 = v2 - v0;
        Vector3 p = Vector3.Cross(d, e2);
        float det = Vector3.Dot(e1, p);
        if (det > -EPS && det < EPS) return false; // レイと平行
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

    /// <summary>レイをマーチングして地形ハイトフィールドとの交点を求める。</summary>
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
            float diff = pos.y - gy; // >0: 地表より上, <0: 地中
            if (havePrev && prevDiff > 0f && diff <= 0f)
            {
                // prevPos(上) と pos(下) の間で線形補間して交点を推定
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
            if (!found || y > groundY) groundY = y;
            found = true;
        }
        return found;
    }
}
