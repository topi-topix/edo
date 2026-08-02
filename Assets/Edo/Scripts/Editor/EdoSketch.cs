using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;

/// <summary>
/// 水域・道などを本トレースする前の「下書き線」を Scene 上にラフに描くツール。
///
/// メニュー Edo ▸ 下書き:
///  - 描画モード (Cmd+Shift+D) … 下書きの描画ON/OFF(チェック付き)。
///  - 表示 … 下書き全体の表示/非表示(チェック付き)。
///  - 一筆消す … 直近の一筆を削除。
///  - 全消去 … このシーンの下書きを全消去。
///
/// 描き方(描画モードON時):
///  - 左ドラッグ = フリーハンドのペン(1本の線を引く)。
///  - 左クリック = 折れ線の頂点を置く(クリックで繋がる)。右クリック / Enter / Esc で一筆確定。
///  - Shift+左クリック = 最寄りの一筆をまるごと消す。
///  - Scene左上のHUDで 色 / 太さ / 一筆消し / 全消去 / 隠す を操作。
///
/// 描いた線は「シーンごと」に UserData/Sketches へJSON保存され、Unity再起動後も、
/// また Water Tracer 等で本トレース中も“下敷き”として見え続ける(描画モードOFF時は
/// クリックを奪わないので既存ツールと共存できる)。線は地形の裏に隠れないよう常に手前へ描く。
/// クリック地点は「コライダー → 地形ハイトフィールド → 水平面(y=0)」の順で拾う。
/// </summary>
[InitializeOnLoad]
public static class EdoSketch
{
    const string MenuDraw = "Edo/下書き/描画モード %#d";
    const string MenuEdit = "Edo/下書き/編集モード %#e";
    const string MenuShow = "Edo/下書き/表示";
    const string MenuUndo = "Edo/下書き/一筆消す";
    const string MenuClear = "Edo/下書き/全消去";

    const string PrefDraw = "EdoSketch.Draw";
    const string PrefEdit = "EdoSketch.Edit";
    const string PrefShow = "EdoSketch.Show";
    const string PrefColor = "EdoSketch.Color";
    const string PrefWidth = "EdoSketch.Width";

    const float GrabPx = 11f;   // 頂点/線をつかめる画面上の半径(px)
    const float EraserPx = 16f; // 消しゴムの画面上の半径(px)

    // パレット(下書き用の視認しやすい色)
    static readonly Color[] Palette =
    {
        new Color(1.00f, 0.25f, 0.20f), // 赤
        new Color(1.00f, 0.80f, 0.10f), // 黄
        new Color(0.20f, 0.85f, 1.00f), // 水色
        new Color(0.30f, 1.00f, 0.40f), // 緑
        new Color(1.00f, 0.45f, 0.90f), // 桃
        new Color(1.00f, 1.00f, 1.00f), // 白
    };

    [Serializable]
    class Stroke
    {
        public int color;
        public float width = 3f;
        public bool freehand;
        public List<Vector3> pts = new List<Vector3>();
    }

    [Serializable]
    class SketchData
    {
        public List<Stroke> strokes = new List<Stroke>();
    }

    static bool _draw;
    static bool _edit;
    static bool _show;
    static int _color;
    static float _width;

    static SketchData _data = new SketchData();
    static string _sceneKey = "";

    // 描画中の状態
    static Stroke _activePoly;      // クリックで作る折れ線(確定まで保持)
    static Stroke _activeFree;      // ドラッグ中のフリーハンド
    static bool _mouseDown;
    static bool _dragging;
    static Vector2 _downScreen;
    static Vector3 _downWorld;
    static Vector2 _lastSampleScreen;

    // 編集モードの状態
    static int _dragStroke = -1;    // ドラッグ中の頂点(所属stroke)
    static int _dragPt = -1;        // ドラッグ中の頂点(index)
    static bool _erasing;           // 消しゴム(右ドラッグ)実行中
    static Vector3 _eraseWorld;     // 消しゴム位置(表示用)

    static Rect _hudRect;

    static EdoSketch()
    {
        _draw = EditorPrefs.GetBool(PrefDraw, false);
        _edit = EditorPrefs.GetBool(PrefEdit, false);
        _show = EditorPrefs.GetBool(PrefShow, true);
        _color = Mathf.Clamp(EditorPrefs.GetInt(PrefColor, 0), 0, Palette.Length - 1);
        _width = Mathf.Clamp(EditorPrefs.GetFloat(PrefWidth, 3f), 1f, 10f);

        SceneView.duringSceneGui -= OnSceneGui;
        SceneView.duringSceneGui += OnSceneGui;

        EditorSceneManager.sceneOpened += (s, m) => ReloadForActiveScene();
        EditorSceneManager.newSceneCreated += (s, m, o) => ReloadForActiveScene();
        EditorApplication.quitting += Save;

        EditorApplication.delayCall += () =>
        {
            ReloadForActiveScene();
            Menu.SetChecked(MenuDraw, _draw);
            Menu.SetChecked(MenuEdit, _edit);
            Menu.SetChecked(MenuShow, _show);
        };
    }

    // ---- メニュー ---------------------------------------------------------

    [MenuItem(MenuDraw)]
    static void ToggleDraw()
    {
        _draw = !_draw;
        EditorPrefs.SetBool(PrefDraw, _draw);
        Menu.SetChecked(MenuDraw, _draw);
        if (_draw)
        {
            if (_edit) { _edit = false; EditorPrefs.SetBool(PrefEdit, false); Menu.SetChecked(MenuEdit, false); }
            if (!_show) ToggleShow(); // 描くなら表示もON
        }
        FinishPolyline();
        SceneView.RepaintAll();
    }

    [MenuItem(MenuEdit)]
    static void ToggleEdit()
    {
        _edit = !_edit;
        EditorPrefs.SetBool(PrefEdit, _edit);
        Menu.SetChecked(MenuEdit, _edit);
        if (_edit)
        {
            if (_draw) { _draw = false; EditorPrefs.SetBool(PrefDraw, false); Menu.SetChecked(MenuDraw, false); }
            if (!_show) ToggleShow();
        }
        FinishPolyline();
        _dragStroke = _dragPt = -1;
        _erasing = false;
        SceneView.RepaintAll();
    }

    [MenuItem(MenuShow)]
    static void ToggleShow()
    {
        _show = !_show;
        EditorPrefs.SetBool(PrefShow, _show);
        Menu.SetChecked(MenuShow, _show);
        SceneView.RepaintAll();
    }

    [MenuItem(MenuUndo)]
    static void UndoLast()
    {
        FinishPolyline();
        if (_data.strokes.Count > 0)
        {
            _data.strokes.RemoveAt(_data.strokes.Count - 1);
            Save();
            SceneView.RepaintAll();
        }
    }

    [MenuItem(MenuUndo, true)]
    static bool UndoLastValidate() => _data != null && _data.strokes.Count > 0;

    [MenuItem(MenuClear)]
    static void ClearAll()
    {
        if (_data.strokes.Count == 0) return;
        if (!EditorUtility.DisplayDialog("下書きを全消去",
            $"このシーンの下書き {_data.strokes.Count} 本をすべて消します。よろしいですか？",
            "全消去", "やめる")) return;
        _activePoly = null;
        _data.strokes.Clear();
        Save();
        SceneView.RepaintAll();
    }

    [MenuItem(MenuClear, true)]
    static bool ClearAllValidate() => _data != null && _data.strokes.Count > 0;

    // ---- Scene GUI --------------------------------------------------------

    static void OnSceneGui(SceneView sv)
    {
        if (!_show) return;

        Event e = Event.current;

        DrawHud(sv);
        DrawStrokes(e);
        if (_edit) DrawEditOverlay(e);

        if (!_draw && !_edit) return;

        // HUD上の操作は下書き入力として扱わない
        if (_hudRect.Contains(e.mousePosition))
        {
            if (e.type == EventType.MouseDown || e.type == EventType.MouseUp || e.type == EventType.MouseDrag)
                return;
        }

        // 選択・デセレクトを奪う
        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);

        if (e.alt) return; // Alt はカメラ操作へ譲る

        if (_edit) { HandleEditInput(sv, e); return; }

        switch (e.type)
        {
            case EventType.KeyDown:
                if (e.keyCode == KeyCode.Escape || e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter)
                {
                    FinishPolyline();
                    e.Use();
                    sv.Repaint();
                }
                break;

            case EventType.MouseDown:
                if (e.button == 1) // 右クリック=折れ線確定
                {
                    FinishPolyline();
                    e.Use();
                    sv.Repaint();
                    break;
                }
                if (e.button == 0)
                {
                    if (e.shift)
                    {
                        if (TryPick(e.mousePosition, out Vector3 hp)) EraseNearest(hp);
                        e.Use();
                        sv.Repaint();
                        break;
                    }
                    _mouseDown = true;
                    _dragging = false;
                    _downScreen = e.mousePosition;
                    _lastSampleScreen = e.mousePosition;
                    TryPick(e.mousePosition, out _downWorld);
                    e.Use();
                }
                break;

            case EventType.MouseDrag:
                if (_mouseDown && e.button == 0)
                {
                    if (!_dragging && (e.mousePosition - _downScreen).magnitude > 4f)
                    {
                        // フリーハンド開始(押した点を起点に)
                        FinishPolyline();
                        _dragging = true;
                        _activeFree = new Stroke { color = _color, width = _width, freehand = true };
                        _activeFree.pts.Add(_downWorld);
                        _data.strokes.Add(_activeFree);
                    }
                    if (_dragging && (e.mousePosition - _lastSampleScreen).magnitude > 4f)
                    {
                        if (TryPick(e.mousePosition, out Vector3 p))
                        {
                            _activeFree.pts.Add(p);
                            _lastSampleScreen = e.mousePosition;
                        }
                    }
                    e.Use();
                    sv.Repaint();
                }
                break;

            case EventType.MouseUp:
                if (_mouseDown && e.button == 0)
                {
                    if (_dragging)
                    {
                        // フリーハンド確定(点が少なすぎたら破棄)
                        if (_activeFree != null && _activeFree.pts.Count < 2)
                            _data.strokes.Remove(_activeFree);
                        _activeFree = null;
                        Save();
                    }
                    else
                    {
                        // クリック=折れ線の頂点を置く
                        if (TryPick(e.mousePosition, out Vector3 p))
                        {
                            if (_activePoly == null)
                            {
                                _activePoly = new Stroke { color = _color, width = _width, freehand = false };
                                _data.strokes.Add(_activePoly);
                            }
                            _activePoly.pts.Add(p);
                            Save();
                        }
                    }
                    _mouseDown = false;
                    _dragging = false;
                    e.Use();
                    sv.Repaint();
                }
                break;

            case EventType.MouseMove:
                if (_activePoly != null) sv.Repaint(); // ラバーバンド更新
                break;
        }
    }

    static void FinishPolyline()
    {
        if (_activePoly != null)
        {
            if (_activePoly.pts.Count < 2)
                _data.strokes.Remove(_activePoly);
            _activePoly = null;
            Save();
        }
    }

    // ---- 編集モード(頂点編集 / 一部消し) --------------------------------

    static void HandleEditInput(SceneView sv, Event e)
    {
        switch (e.type)
        {
            case EventType.MouseDown:
                if (e.button == 1) // 右ボタン=消しゴム開始
                {
                    _erasing = true;
                    ApplyEraserAt(e.mousePosition);
                    e.Use(); sv.Repaint();
                    break;
                }
                if (e.button == 0)
                {
                    if (FindVertex(e.mousePosition, out int si, out int pi))
                    {
                        if (e.shift)
                        {
                            // 頂点を1つ削除(=線の一部を消す)
                            DeleteVertex(si, pi);
                        }
                        else
                        {
                            _dragStroke = si; _dragPt = pi; // 頂点をつかんで移動
                        }
                        e.Use(); sv.Repaint();
                    }
                    else if (FindSegment(e.mousePosition, out int ssi, out int seg))
                    {
                        // 線の途中に頂点を挿入してそのままドラッグ
                        if (TryPick(e.mousePosition, out Vector3 np))
                        {
                            _data.strokes[ssi].pts.Insert(seg + 1, np);
                            _dragStroke = ssi; _dragPt = seg + 1;
                            e.Use(); sv.Repaint();
                        }
                    }
                }
                break;

            case EventType.MouseDrag:
                if (_erasing && e.button == 1)
                {
                    ApplyEraserAt(e.mousePosition);
                    e.Use(); sv.Repaint();
                }
                else if (_dragStroke >= 0 && e.button == 0)
                {
                    if (TryPick(e.mousePosition, out Vector3 p) &&
                        _dragStroke < _data.strokes.Count &&
                        _dragPt < _data.strokes[_dragStroke].pts.Count)
                    {
                        _data.strokes[_dragStroke].pts[_dragPt] = p;
                    }
                    e.Use(); sv.Repaint();
                }
                break;

            case EventType.MouseUp:
                if (_erasing && e.button == 1) { _erasing = false; Save(); e.Use(); sv.Repaint(); }
                else if (_dragStroke >= 0 && e.button == 0)
                {
                    _dragStroke = _dragPt = -1;
                    Save();
                    e.Use(); sv.Repaint();
                }
                break;

            case EventType.MouseMove:
                sv.Repaint(); // カーソル近傍のハイライト更新
                break;
        }
    }

    static void DeleteVertex(int si, int pi)
    {
        if (si < 0 || si >= _data.strokes.Count) return;
        var s = _data.strokes[si];
        if (pi < 0 || pi >= s.pts.Count) return;
        s.pts.RemoveAt(pi);
        if (s.pts.Count < 2) _data.strokes.RemoveAt(si); // 線として成立しなくなったら破棄
        Save();
    }

    /// <summary>カーソル最寄りの頂点(全stroke)を画面距離で探す。</summary>
    static bool FindVertex(Vector2 sp, out int si, out int pi)
    {
        si = pi = -1;
        float best = GrabPx * GrabPx;
        for (int i = 0; i < _data.strokes.Count; i++)
        {
            var s = _data.strokes[i];
            for (int j = 0; j < s.pts.Count; j++)
            {
                Vector2 g = HandleUtility.WorldToGUIPoint(s.pts[j]);
                float d = (g - sp).sqrMagnitude;
                if (d < best) { best = d; si = i; pi = j; }
            }
        }
        return si >= 0;
    }

    /// <summary>カーソル最寄りの線分(全stroke)を画面距離で探す。挿入点の判定用。</summary>
    static bool FindSegment(Vector2 sp, out int si, out int seg)
    {
        si = seg = -1;
        float best = GrabPx * GrabPx;
        for (int i = 0; i < _data.strokes.Count; i++)
        {
            var s = _data.strokes[i];
            for (int j = 0; j + 1 < s.pts.Count; j++)
            {
                Vector2 a = HandleUtility.WorldToGUIPoint(s.pts[j]);
                Vector2 b = HandleUtility.WorldToGUIPoint(s.pts[j + 1]);
                float d = SqDistPointSeg2D(sp, a, b);
                if (d < best) { best = d; si = i; seg = j; }
            }
        }
        return si >= 0;
    }

    /// <summary>消しゴム: 画面半径 EraserPx 内の点を除き、隙間で線を分割する。</summary>
    static void ApplyEraserAt(Vector2 sp)
    {
        TryPick(sp, out _eraseWorld);
        float r2 = EraserPx * EraserPx;
        bool changed = false;

        for (int i = _data.strokes.Count - 1; i >= 0; i--)
        {
            var s = _data.strokes[i];
            var runs = new List<List<Vector3>>();
            var cur = new List<Vector3>();
            int removed = 0;
            foreach (var p in s.pts)
            {
                Vector2 g = HandleUtility.WorldToGUIPoint(p);
                if ((g - sp).sqrMagnitude <= r2)
                {
                    removed++;
                    if (cur.Count > 0) { runs.Add(cur); cur = new List<Vector3>(); }
                }
                else cur.Add(p);
            }
            if (removed == 0) continue;
            if (cur.Count > 0) runs.Add(cur);

            changed = true;
            _data.strokes.RemoveAt(i);
            // 2点以上の残片だけを線として復帰(消えた箇所で自然に分割される)
            int insertAt = i;
            foreach (var run in runs)
            {
                if (run.Count < 2) continue;
                _data.strokes.Insert(insertAt++, new Stroke
                {
                    color = s.color, width = s.width, freehand = s.freehand, pts = run
                });
            }
        }
        if (changed) SceneView.RepaintAll();
    }

    static void DrawEditOverlay(Event e)
    {
        var prevZ = Handles.zTest;
        Handles.zTest = CompareFunction.Always;

        // 全stroke の頂点をつかめる点として表示(最寄りは強調)
        FindVertex(e.mousePosition, out int hi, out int hj);
        for (int i = 0; i < _data.strokes.Count; i++)
        {
            var s = _data.strokes[i];
            Color c = Palette[Mathf.Clamp(s.color, 0, Palette.Length - 1)];
            for (int j = 0; j < s.pts.Count; j++)
            {
                bool hot = (i == hi && j == hj) || (i == _dragStroke && j == _dragPt);
                Handles.color = hot ? Color.white : c;
                float hs = HandleUtility.GetHandleSize(s.pts[j]) * (hot ? 0.045f : 0.03f);
                Handles.DotHandleCap(0, s.pts[j], Quaternion.identity, hs, EventType.Repaint);
            }
        }

        // 消しゴムの範囲を円で表示
        if (_erasing)
        {
            Handles.color = new Color(1f, 0.4f, 0.3f, 0.9f);
            float wr = HandleUtility.GetHandleSize(_eraseWorld) * (EraserPx / 64f);
            Handles.DrawWireDisc(_eraseWorld, Vector3.up, wr);
        }

        Handles.zTest = prevZ;
        Handles.color = Color.white;
    }

    static float SqDistPointSeg2D(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 ab = b - a;
        float t = Vector2.Dot(p - a, ab) / Mathf.Max(1e-6f, ab.sqrMagnitude);
        t = Mathf.Clamp01(t);
        return (a + ab * t - p).sqrMagnitude;
    }

    // ---- 描画 -------------------------------------------------------------

    static void DrawStrokes(Event e)
    {
        var prevZ = Handles.zTest;
        Handles.zTest = CompareFunction.Always; // 地形の裏に隠れない下敷き

        foreach (var s in _data.strokes)
        {
            if (s == null || s.pts.Count == 0) continue;
            Handles.color = Palette[Mathf.Clamp(s.color, 0, Palette.Length - 1)];
            for (int i = 0; i + 1 < s.pts.Count; i++)
                Handles.DrawLine(s.pts[i], s.pts[i + 1], s.width);

            if (!s.freehand)
            {
                // 折れ線は頂点に小さな点を出す
                foreach (var p in s.pts)
                {
                    float hs = HandleUtility.GetHandleSize(p) * 0.03f;
                    Handles.DotHandleCap(0, p, Quaternion.identity, hs, EventType.Repaint);
                }
            }
        }

        // 作りかけの折れ線: 最終頂点からカーソルへラバーバンド
        if (_draw && _activePoly != null && _activePoly.pts.Count > 0 &&
            !_hudRect.Contains(e.mousePosition) &&
            TryPick(e.mousePosition, out Vector3 cur))
        {
            Handles.color = Palette[Mathf.Clamp(_activePoly.color, 0, Palette.Length - 1)] * new Color(1, 1, 1, 0.6f);
            Handles.DrawDottedLine(_activePoly.pts[_activePoly.pts.Count - 1], cur, 3f);
        }

        Handles.zTest = prevZ;
        Handles.color = Color.white;
    }

    static void DrawHud(SceneView sv)
    {
        Handles.BeginGUI();

        float w = 258f;
        float h = _draw ? 92f : _edit ? 74f : 40f;
        _hudRect = new Rect(8, 8, w, h);
        GUILayout.BeginArea(_hudRect, GUI.skin.box);

        GUILayout.BeginHorizontal();
        Color titleCol = _draw ? new Color(0.4f, 1f, 0.6f)
                       : _edit ? new Color(0.5f, 0.8f, 1f)
                       : new Color(0.8f, 0.8f, 0.8f);
        var titleStyle = new GUIStyle(EditorStyles.miniBoldLabel) { normal = { textColor = titleCol } };
        string title = _draw ? "✎ 下書き: 描画中" : _edit ? "✜ 下書き: 編集中" : "下書き: 表示のみ";
        GUILayout.Label(title, titleStyle);
        GUILayout.FlexibleSpace();
        GUILayout.Label($"{_data.strokes.Count}本", EditorStyles.miniLabel);
        if (GUILayout.Button("隠す", EditorStyles.miniButton, GUILayout.Width(38)))
            ToggleShow();
        GUILayout.EndHorizontal();

        if (_edit)
        {
            var help = new GUIStyle(EditorStyles.miniLabel) { wordWrap = true };
            GUILayout.Label("頂点ドラッグ=移動 / 線上クリック=頂点追加\nShift+クリック=頂点削除 / 右ドラッグ=消しゴム", help);
            GUILayout.BeginHorizontal();
            GUILayout.FlexibleSpace();
            using (new EditorGUI.DisabledScope(_data.strokes.Count == 0))
            {
                if (GUILayout.Button("一筆消", EditorStyles.miniButton, GUILayout.Width(46)))
                    UndoLast();
                if (GUILayout.Button("全消去", EditorStyles.miniButton, GUILayout.Width(46)))
                    ClearAll();
            }
            GUILayout.EndHorizontal();
        }

        if (_draw)
        {
            // 色スワッチ
            GUILayout.BeginHorizontal();
            GUILayout.Label("色", EditorStyles.miniLabel, GUILayout.Width(16));
            for (int i = 0; i < Palette.Length; i++)
            {
                var prev = GUI.backgroundColor;
                GUI.backgroundColor = Palette[i];
                string cap = i == _color ? "●" : " ";
                if (GUILayout.Button(cap, GUILayout.Width(26), GUILayout.Height(18)))
                {
                    _color = i;
                    EditorPrefs.SetInt(PrefColor, _color);
                }
                GUI.backgroundColor = prev;
            }
            GUILayout.EndHorizontal();

            // 太さ・編集
            GUILayout.BeginHorizontal();
            GUILayout.Label($"太さ {_width:0}", EditorStyles.miniLabel, GUILayout.Width(46));
            if (GUILayout.Button("−", EditorStyles.miniButton, GUILayout.Width(24)))
            { _width = Mathf.Max(1f, _width - 1f); EditorPrefs.SetFloat(PrefWidth, _width); }
            if (GUILayout.Button("＋", EditorStyles.miniButton, GUILayout.Width(24)))
            { _width = Mathf.Min(10f, _width + 1f); EditorPrefs.SetFloat(PrefWidth, _width); }
            GUILayout.FlexibleSpace();
            using (new EditorGUI.DisabledScope(_data.strokes.Count == 0))
            {
                if (GUILayout.Button("一筆消", EditorStyles.miniButton, GUILayout.Width(46)))
                    UndoLast();
                if (GUILayout.Button("全消去", EditorStyles.miniButton, GUILayout.Width(46)))
                    ClearAll();
            }
            GUILayout.EndHorizontal();
        }

        GUILayout.EndArea();
        Handles.EndGUI();
    }

    // ---- 消去 -------------------------------------------------------------

    static void EraseNearest(Vector3 world)
    {
        int best = -1;
        float bestD = float.MaxValue;
        for (int i = 0; i < _data.strokes.Count; i++)
        {
            var s = _data.strokes[i];
            for (int j = 0; j + 1 < s.pts.Count; j++)
            {
                float d = SqDistPointSeg(world, s.pts[j], s.pts[j + 1]);
                if (d < bestD) { bestD = d; best = i; }
            }
            if (s.pts.Count == 1)
            {
                float d = (s.pts[0] - world).sqrMagnitude;
                if (d < bestD) { bestD = d; best = i; }
            }
        }
        // 画面上の見かけ半径で当たり判定(遠近をならす)
        if (best >= 0)
        {
            float tol = HandleUtility.GetHandleSize(world) * 0.5f;
            if (bestD <= tol * tol)
            {
                if (_data.strokes[best] == _activePoly) _activePoly = null;
                _data.strokes.RemoveAt(best);
                Save();
            }
        }
    }

    static float SqDistPointSeg(Vector3 p, Vector3 a, Vector3 b)
    {
        Vector3 ab = b - a;
        float t = Vector3.Dot(p - a, ab) / Mathf.Max(1e-6f, ab.sqrMagnitude);
        t = Mathf.Clamp01(t);
        return (a + ab * t - p).sqrMagnitude;
    }

    // ---- ピッキング(コライダー→地形→水平面) ------------------------------

    static bool TryPick(Vector2 guiPos, out Vector3 point)
    {
        point = default;
        Ray ray = HandleUtility.GUIPointToWorldRay(guiPos);

        if (Physics.Raycast(ray, out var hit, 100000f))
        {
            point = hit.point;
            return true;
        }
        if (TryRaycastTerrain(ray, out point))
            return true;

        // 水平面 y=0 との交点(古地図Quad等、コライダーの無い下敷き向け)
        if (Mathf.Abs(ray.direction.y) > 1e-5f)
        {
            float t = -ray.origin.y / ray.direction.y;
            if (t > 0f) { point = ray.origin + ray.direction * t; return true; }
        }
        return false;
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
            if (!TrySampleTerrain(pos, out float gy)) { havePrev = false; continue; }
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

    // ---- 保存/読込(シーン別 JSON) --------------------------------------

    static string SketchDir
    {
        get
        {
            string root = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(root, "UserData", "Sketches");
        }
    }

    static string FilePathForActiveScene()
    {
        var scene = EditorSceneManager.GetActiveScene();
        string key = string.IsNullOrEmpty(scene.path) ? scene.name : scene.path;
        if (string.IsNullOrEmpty(key)) key = "Untitled";
        var sb = new StringBuilder();
        foreach (char c in key)
            sb.Append(Array.IndexOf(Path.GetInvalidFileNameChars(), c) >= 0 || c == '/' || c == '\\' ? '_' : c);
        return Path.Combine(SketchDir, sb.ToString() + ".json");
    }

    static void ReloadForActiveScene()
    {
        _activePoly = null;
        _activeFree = null;
        _mouseDown = _dragging = false;
        _sceneKey = FilePathForActiveScene();
        _data = new SketchData();
        try
        {
            if (File.Exists(_sceneKey))
            {
                string json = File.ReadAllText(_sceneKey);
                var d = JsonUtility.FromJson<SketchData>(json);
                if (d != null && d.strokes != null) _data = d;
            }
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[EdoSketch] 読込失敗: {ex.Message}");
        }
        SceneView.RepaintAll();
    }

    static void Save()
    {
        try
        {
            if (string.IsNullOrEmpty(_sceneKey)) _sceneKey = FilePathForActiveScene();
            Directory.CreateDirectory(SketchDir);
            File.WriteAllText(_sceneKey, JsonUtility.ToJson(_data, true));
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[EdoSketch] 保存失敗: {ex.Message}");
        }
    }
}
