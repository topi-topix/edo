// 敷地割ツール — Scene ビューで町割の多角形を打つ・直す。
//
// メニュー Edo ▸ 敷地割:
//   編集モード (Cmd+Shift+K) / 表示 / 一覧を開く / ビルダーと突き合わせる / 保存
//
// 操作(編集モード中):
//   頂点をドラッグ         … 動かす。一致する他区画の頂点も一緒に動く(共有点の連動、既定ON)
//   辺の上をクリック       … その位置に頂点を挿す(そのまま掴んで動かせる)
//   Shift + 頂点をクリック … その頂点を消す
//   区画の中をクリック     … その区画を選ぶ
//   ⌘(Ctrl) + 空所をクリック … 選択中の区画の末尾に頂点を足す
//   ＋新規 → 順に打つ → Enter か右クリック … 新しい区画を閉じる / Esc で取り消し
//   Delete                 … 選択中の頂点を消す
//
// 正典は docs/Sashizu/parcels.json (EdoParcels)。編集すると自動で保存する。
// 座標は世界の (x, z)。高さは持たない — 描くときだけ地形に載せる。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEditor;
using P = EdoParcels.Parcel;

[InitializeOnLoad]
public static class EdoParcelTool
{
    const string MenuEdit = "Edo/敷地割/編集モード %#k";
    const string MenuShow = "Edo/敷地割/表示";
    const string PrefEdit = "EdoParcel.Edit";
    const string PrefShow = "EdoParcel.Show";
    const string PrefLink = "EdoParcel.Link";
    const string PrefSnap = "EdoParcel.Snap";
    const string PrefRange = "EdoParcel.Range";

    const float GrabPx = 10f;       // 頂点を掴める画面半径
    const float EdgePx = 7f;        // 辺を掴める画面距離
    const float SnapPx = 12f;       // 他区画へ吸着する画面距離

    static bool _edit, _show, _link, _snap;
    static float _range;            // 描画するカメラからの半径 m (0 = 全部)

    public static P Selected;
    /// <summary>選択中の頂点。テストと外部からの操作用。</summary>
    public static int SelectedVertex { get { return _selVert; } set { _selVert = value; } }
    static int _selVert = -1;
    static int _dragVert = -1;
    static bool _dragging;
    static P _drawing;              // 新規作成中
    static Rect _hud;
    static double _lastSave;

    // 描画用のキャッシュ(地形に載せた折れ線)
    static readonly Dictionary<P, Vector3[]> _cache = new Dictionary<P, Vector3[]>();

    // ⚠ 区画のデータはシーンの外(docs/Sashizu/parcels.json)にあるので Unity の Undo は効かない。
    //   頂点をドラッグして間違えたときに戻せないと使い物にならないため、自前で持つ。
    static readonly List<List<P>> _undo = new List<List<P>>();
    const int UndoDepth = 40;

    // ---- 共有点 ----------------------------------------------------------
    //
    // 共有は **座標が一致していること** で表す(別に id を振らない)。区画の角は隣同士で
    // 同じ点を指しているのが正しい状態で、ここが割れていると屋敷の間に隙間や重なりが出る。
    // LinkTol より近い頂点は「同じ角」とみなし、動かすと一緒に動く。

    public const float LinkTol = 0.30f;

    static readonly Dictionary<P, bool[]> _shared = new Dictionary<P, bool[]>();
    static bool _sharedDirty = true;
    static int _seenVersion = -1;

    /// <summary>EdoParcels 側でデータが入れ替わっていたらキャッシュを捨てる。
    /// Parcel の参照をキーにしているので、Load 後は必ず作り直す必要がある。</summary>
    static void SyncVersion()
    {
        if (_seenVersion == EdoParcels.Version) return;
        _seenVersion = EdoParcels.Version;
        _cache.Clear();
        _sharedDirty = true;
    }

    static void RebuildShared()
    {
        _shared.Clear();
        var all = EdoParcels.All;
        foreach (var p in all) _shared[p] = new bool[p.pts.Count];
        for (int a = 0; a < all.Count; a++)
            for (int i = 0; i < all[a].pts.Count; i++)
            {
                if (_shared[all[a]][i]) continue;
                for (int b = 0; b < all.Count; b++)
                    for (int j = 0; j < all[b].pts.Count; j++)
                    {
                        if (a == b && i == j) continue;
                        if (Vector2.Distance(all[a].pts[i], all[b].pts[j]) <= LinkTol)
                        { _shared[all[a]][i] = true; _shared[all[b]][j] = true; }
                    }
            }
        _sharedDirty = false;
    }

    public static bool IsShared(P p, int i)
    {
        SyncVersion();
        if (_sharedDirty) RebuildShared();
        bool[] f;
        return _shared.TryGetValue(p, out f) && i >= 0 && i < f.Length && f[i];
    }

    /// <summary>その角を共有している (区画, 頂点) を自分も含めて返す。</summary>
    public static List<KeyValuePair<P, int>> GroupOf(P p, int i)
    {
        var g = new List<KeyValuePair<P, int>>();
        if (p == null || i < 0 || i >= p.pts.Count) return g;
        Vector2 at = p.pts[i];
        foreach (var q in EdoParcels.All)
            for (int j = 0; j < q.pts.Count; j++)
                if (Vector2.Distance(q.pts[j], at) <= LinkTol) g.Add(new KeyValuePair<P, int>(q, j));
        return g;
    }

    /// <summary>選んだ頂点を、いちばん近い他区画の頂点(無ければ辺)へ溶接して共有にする。
    /// 辺へ寄せるときは相手側にも頂点を挿す — でないと片方だけ折れて隙間になる。</summary>
    public static void WeldSelected()
    {
        if (Selected == null || _selVert < 0 || _selVert >= Selected.pts.Count) return;
        Vector2 at = Selected.pts[_selVert];
        const float R = 4.0f;

        P bp = null; int bi = -1; float bd = R;
        foreach (var q in EdoParcels.All)
        {
            if (q == Selected) continue;
            for (int j = 0; j < q.pts.Count; j++)
            {
                float d = Vector2.Distance(q.pts[j], at);
                if (d < bd && d > 1e-4f) { bd = d; bp = q; bi = j; }
            }
        }
        if (bp != null)
        {
            PushUndo();
            MoveVertex(Selected, _selVert, bp.pts[bi]);
            Debug.Log(string.Format("[敷地割] {0} の頂点{1} を {2} の頂点{3} へ溶接({4:0.00}m 動かした)",
                                    Selected.id, _selVert, bp.id, bi, bd));
            _sharedDirty = true; Invalidate(); return;
        }

        // 頂点が無ければ辺へ
        P ep = null; int ei = -1; float ed = R; Vector2 epos = at;
        foreach (var q in EdoParcels.All)
        {
            if (q == Selected) continue;
            int n = q.pts.Count;
            for (int j = 0; j < n; j++)
            {
                Vector2 a = q.pts[j], b = q.pts[(j + 1) % n];
                Vector2 ab = b - a;
                float t = ab.sqrMagnitude < 1e-6f ? 0f : Mathf.Clamp01(Vector2.Dot(at - a, ab) / ab.sqrMagnitude);
                Vector2 pr = a + ab * t;
                float d = Vector2.Distance(pr, at);
                if (d < ed) { ed = d; ep = q; ei = j; epos = pr; }
            }
        }
        if (ep != null)
        {
            PushUndo();
            ep.pts.Insert(ei + 1, epos);       // 相手にも角を作る
            MoveVertex(Selected, _selVert, epos);
            Touch(ep);
            Debug.Log(string.Format("[敷地割] {0} の頂点{1} を {2} の辺{3} へ溶接。相手に頂点を挿した({4:0.00}m)",
                                    Selected.id, _selVert, ep.id, ei, ed));
            _sharedDirty = true; Invalidate(); return;
        }
        Debug.LogWarning("[敷地割] " + R.ToString("0") + "m 以内に溶接できる相手が無い");
    }

    /// <summary>選んだ頂点を共有から外す。**相手は動かさず、こちらだけ**敷地の内側へ
    /// LinkTol の倍だけ引く(座標が一致している限り連動は切れないため)。</summary>
    public static void UnweldSelected()
    {
        if (Selected == null || _selVert < 0 || _selVert >= Selected.pts.Count) return;
        var g = GroupOf(Selected, _selVert);
        if (g.Count <= 1) { Debug.Log("[敷地割] この頂点は共有していない"); return; }
        PushUndo();
        Vector2 at = Selected.pts[_selVert];
        Vector2 inward = (Selected.Centroid - at);
        inward = inward.sqrMagnitude < 1e-6f ? Vector2.right : inward.normalized;
        Selected.pts[_selVert] = at + inward * (LinkTol * 2f);   // 相手には触れない
        Touch(Selected);
        _sharedDirty = true; Invalidate();
        Debug.Log(string.Format("[敷地割] {0} の頂点{1} を共有から外した({2}区画で共有していた)。{3:0.00}m 内側へ引いた — 位置は打ち直すこと",
                                Selected.id, _selVert, g.Count, LinkTol * 2f));
    }

    public static void PushUndo()
    {
        var snap = new List<P>();
        foreach (var p in EdoParcels.All) snap.Add(p.Clone());
        _undo.Add(snap);
        if (_undo.Count > UndoDepth) _undo.RemoveAt(0);
    }

    public static void PopUndo()
    {
        if (_undo.Count == 0) { Debug.Log("[敷地割] これ以上戻せない"); return; }
        var snap = _undo[_undo.Count - 1];
        _undo.RemoveAt(_undo.Count - 1);
        string selId = Selected != null ? Selected.id : null;
        EdoParcels.All.Clear();
        EdoParcels.All.AddRange(snap);
        EdoParcels.MarkDirty();
        Selected = selId != null ? EdoParcels.Find(selId) : null;
        _selVert = -1;
        Invalidate();
        EdoParcelWindow.Refresh();
    }

    static EdoParcelTool()
    {
        _edit = EditorPrefs.GetBool(PrefEdit, false);
        _show = EditorPrefs.GetBool(PrefShow, true);
        _link = EditorPrefs.GetBool(PrefLink, true);
        _snap = EditorPrefs.GetBool(PrefSnap, true);
        _range = EditorPrefs.GetFloat(PrefRange, 900f);

        SceneView.duringSceneGui -= OnSceneGui;
        SceneView.duringSceneGui += OnSceneGui;
        EditorApplication.quitting += FlushSave;
        AssemblyReloadEvents.beforeAssemblyReload += FlushSave;

        EditorApplication.delayCall += () =>
        {
            Menu.SetChecked(MenuEdit, _edit);
            Menu.SetChecked(MenuShow, _show);
        };
    }

    // ---- メニュー --------------------------------------------------------

    [MenuItem(MenuEdit, false, 10)]
    static void ToggleEdit()
    {
        _edit = !_edit;
        EditorPrefs.SetBool(PrefEdit, _edit);
        Menu.SetChecked(MenuEdit, _edit);
        if (_edit) _show = true;
        CancelDrawing();
        SceneView.RepaintAll();
    }

    [MenuItem(MenuShow, false, 11)]
    static void ToggleShow()
    {
        _show = !_show;
        EditorPrefs.SetBool(PrefShow, _show);
        Menu.SetChecked(MenuShow, _show);
        SceneView.RepaintAll();
    }

    // ---- 共有点の検査 ------------------------------------------------------

    /// <summary>「近いのに一致していない」角を洗い出す。屋敷の間の隙間・重なりは
    /// たいていこれ — 隣の角を打ち直したときに片方だけ動いて割れた跡。</summary>
    [MenuItem("Edo/敷地割/共有点を検める", false, 43)]
    public static void CheckShares()
    {
        var all = EdoParcels.All;
        int exact = 0;
        var near = new List<string>();
        for (int a = 0; a < all.Count; a++)
            for (int i = 0; i < all[a].pts.Count; i++)
                for (int b = a + 1; b < all.Count; b++)
                    for (int j = 0; j < all[b].pts.Count; j++)
                    {
                        float d = Vector2.Distance(all[a].pts[i], all[b].pts[j]);
                        if (d <= LinkTol) { exact++; continue; }
                        if (d <= NearTol)
                            near.Add(string.Format("  {0:0.00}m  {1}[{2}] — {3}[{4}]   ({5:0.0}, {6:0.0})",
                                     d, all[a].id, i, all[b].id, j, all[a].pts[i].x, all[a].pts[i].y));
                    }
        near.Sort();
        Debug.Log(string.Format("[敷地割] 共有点の検査\n  一致している対 {0}\n  近いのに一致していない対 {1} (>{2:0.0}m 〜 {3:0.0}m)\n{4}",
                  exact, near.Count, LinkTol, NearTol,
                  near.Count == 0 ? "  (無し)" : string.Join("\n", near.ToArray())));
    }

    public const float NearTol = 1.5f;

    /// <summary>近いのに一致していない角を、まとめて片方へ寄せて共有にする。
    /// **形が動く**ので、必ず何件動かすか見せてから実行する。</summary>
    [MenuItem("Edo/敷地割/近い角をまとめて共有にする…", false, 44)]
    public static void WeldAll()
    {
        var all = EdoParcels.All;
        var pairs = new List<KeyValuePair<KeyValuePair<P, int>, KeyValuePair<P, int>>>();
        for (int a = 0; a < all.Count; a++)
            for (int i = 0; i < all[a].pts.Count; i++)
                for (int b = a + 1; b < all.Count; b++)
                    for (int j = 0; j < all[b].pts.Count; j++)
                    {
                        float d = Vector2.Distance(all[a].pts[i], all[b].pts[j]);
                        if (d > LinkTol && d <= NearTol)
                            pairs.Add(new KeyValuePair<KeyValuePair<P, int>, KeyValuePair<P, int>>(
                                new KeyValuePair<P, int>(all[a], i), new KeyValuePair<P, int>(all[b], j)));
                    }
        if (pairs.Count == 0) { Debug.Log("[敷地割] 寄せる角は無い"); return; }
        if (!EditorUtility.DisplayDialog("敷地割",
            string.Format("近いのに一致していない角が {0} 対ある。\n中点へ寄せて共有にする。\n\n⚠ 区画の形が動く。⌘Z で戻せる。", pairs.Count),
            "寄せる", "やめる")) return;

        PushUndo();
        int done = 0;
        foreach (var pr in pairs)
        {
            var A = pr.Key; var B = pr.Value;
            if (Vector2.Distance(A.Key.pts[A.Value], B.Key.pts[B.Value]) <= LinkTol) continue;  // 先に寄って済んだ
            Vector2 mid = (A.Key.pts[A.Value] + B.Key.pts[B.Value]) * 0.5f;
            MoveVertex(A.Key, A.Value, mid);
            MoveVertex(B.Key, B.Value, mid);
            done++;
        }
        _sharedDirty = true; Invalidate();
        EdoParcels.Save();
        Debug.Log("[敷地割] " + done + " 対を共有にした");
    }

    // ---- 描画キャッシュ ---------------------------------------------------

    public static void Invalidate(P p = null)
    {
        if (p == null) { _cache.Clear(); _sharedDirty = true; }
        else _cache.Remove(p);
        SceneView.RepaintAll();
    }

    static Vector3[] Ring(P p)
    {
        SyncVersion();
        Vector3[] r;
        if (_cache.TryGetValue(p, out r)) return r;
        var pts = new List<Vector3>();
        int n = p.pts.Count;
        for (int i = 0; i < n; i++)
        {
            Vector2 a = p.pts[i], b = p.pts[(i + 1) % n];
            float len = Vector2.Distance(a, b);
            int seg = Mathf.Clamp(Mathf.CeilToInt(len / 8f), 1, 64);
            for (int s = 0; s < seg; s++)
            {
                Vector2 q = Vector2.Lerp(a, b, s / (float)seg);
                pts.Add(new Vector3(q.x, Ground(q) + 0.6f, q.y));
            }
        }
        if (pts.Count > 0) pts.Add(pts[0]);
        r = pts.ToArray();
        _cache[p] = r;
        return r;
    }

    public static float Ground(Vector2 p)
    {
        float best = 0f; bool found = false;
        foreach (var t in Terrain.activeTerrains)
        {
            if (t == null || !t.isActiveAndEnabled) continue;
            var tp = t.transform.position; var ts = t.terrainData.size;
            if (p.x < tp.x || p.x > tp.x + ts.x || p.y < tp.z || p.y > tp.z + ts.z) continue;
            float y = t.SampleHeight(new Vector3(p.x, 0f, p.y)) + tp.y;
            if (!found || y > best) best = y;
            found = true;
        }
        return best;
    }

    static Vector3 W(Vector2 p, float lift = 0.6f) { return new Vector3(p.x, Ground(p) + lift, p.y); }

    // ---- Scene GUI -------------------------------------------------------

    static void OnSceneGui(SceneView sv)
    {
        if (!_show) return;
        SyncVersion();
        var e = Event.current;

        DrawParcels(sv, e);
        DrawHud(sv);

        if (!_edit) return;

        if (_hud.Contains(e.mousePosition))
        {
            if (e.type == EventType.MouseDown || e.type == EventType.MouseUp || e.type == EventType.MouseDrag) return;
        }

        int id = GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);
        if (e.alt) return;

        HandleInput(sv, e);
        AutoSave();
    }

    static IEnumerable<P> Visible(SceneView sv)
    {
        var cam = sv != null && sv.camera != null ? sv.camera.transform.position : Vector3.zero;
        var c2 = new Vector2(cam.x, cam.z);
        foreach (var p in EdoParcels.All)
        {
            if (p.pts.Count < 2) continue;
            if (_range > 1f && p != Selected && p != _drawing)
            {
                if (Vector2.Distance(p.Centroid, c2) > _range) continue;
            }
            yield return p;
        }
    }

    static void DrawParcels(SceneView sv, Event e)
    {
        var zt = Handles.zTest;
        Handles.zTest = UnityEngine.Rendering.CompareFunction.Always;

        foreach (var p in Visible(sv))
        {
            bool sel = p == Selected;
            var c = p.Col;
            Handles.color = sel ? Color.white : new Color(c.r, c.g, c.b, 0.85f);
            var ring = Ring(p);
            if (ring.Length >= 2) Handles.DrawAAPolyLine(sel ? 5f : 3f, ring);

            if (sel || _edit)
            {
                for (int i = 0; i < p.pts.Count; i++)
                {
                    bool hot = sel && i == _selVert;
                    var w = W(p.pts[i]);
                    float hs = HandleUtility.GetHandleSize(w) * (hot ? 0.05f : 0.035f);
                    Handles.color = hot ? Color.white : c;
                    Handles.DotHandleCap(0, w, Quaternion.identity, hs, EventType.Repaint);
                    // 共有している角は二重丸。割れていると隣との間に隙間が出るので目で分かるようにする
                    if (IsShared(p, i))
                    {
                        Handles.color = Color.white;
                        Handles.DrawWireDisc(w, Vector3.up, hs * 2.6f, 2f);
                    }
                }
            }

            // 名前と坪数
            var ctr = W(p.Centroid, 1.2f);
            var style = new GUIStyle(EditorStyles.miniLabel)
            {
                alignment = TextAnchor.MiddleCenter,
                normal = { textColor = sel ? Color.white : new Color(c.r, c.g, c.b) },
                fontStyle = sel ? FontStyle.Bold : FontStyle.Normal
            };
            string cap = string.IsNullOrEmpty(p.label) ? p.id : p.label;
            if (sel) cap += string.Format("\n{0:N0} 坪 / {1:N0} m²  {2}頂点", p.Tsubo, p.AreaM2, p.pts.Count);
            Handles.Label(ctr, cap, style);
        }

        // 作成中
        if (_drawing != null && _drawing.pts.Count > 0)
        {
            Handles.color = _drawing.Col;
            var pts = _drawing.pts.Select(q => W(q)).ToArray();
            if (pts.Length >= 2) Handles.DrawAAPolyLine(4f, pts);
            foreach (var w in pts)
                Handles.DotHandleCap(0, w, Quaternion.identity, HandleUtility.GetHandleSize(w) * 0.045f, EventType.Repaint);
            Vector3 hover;
            if (TryPick(e.mousePosition, out hover))
            {
                Handles.color = new Color(1f, 1f, 1f, 0.6f);
                Handles.DrawDottedLine(pts[pts.Length - 1], hover, 3f);
                if (pts.Length >= 2) Handles.DrawDottedLine(hover, pts[0], 3f);
            }
        }

        Handles.zTest = zt;
    }

    // ---- 入力 ------------------------------------------------------------

    static void HandleInput(SceneView sv, Event e)
    {
        // 新規作成中
        if (_drawing != null)
        {
            if (e.type == EventType.KeyDown)
            {
                if (e.keyCode == KeyCode.Escape) { CancelDrawing(); e.Use(); return; }
                if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) { FinishDrawing(); e.Use(); return; }
            }
            if (e.type == EventType.MouseDown && e.button == 1) { FinishDrawing(); e.Use(); return; }
            if (e.type == EventType.MouseDown && e.button == 0)
            {
                Vector3 w;
                if (TryPick(e.mousePosition, out w))
                {
                    var q = new Vector2(w.x, w.z);
                    if (_snap) q = SnapTo(q, e.mousePosition, null);
                    _drawing.pts.Add(q);
                    e.Use(); sv.Repaint();
                }
                return;
            }
            return;
        }

        switch (e.type)
        {
            case EventType.KeyDown:
                if ((e.keyCode == KeyCode.Delete || e.keyCode == KeyCode.Backspace) && Selected != null && _selVert >= 0)
                { PushUndo(); DeleteVertex(Selected, _selVert); e.Use(); sv.Repaint(); }
                else if (e.keyCode == KeyCode.Z && (e.command || e.control))
                { PopUndo(); e.Use(); sv.Repaint(); }
                else if (e.keyCode == KeyCode.W && !e.command && !e.control)
                { WeldSelected(); e.Use(); sv.Repaint(); }
                else if (e.keyCode == KeyCode.U && !e.command && !e.control)
                { UnweldSelected(); e.Use(); sv.Repaint(); }
                break;

            case EventType.MouseDown:
                if (e.button != 0) break;
                {
                    P hp; int hv;
                    if (HitVertex(e.mousePosition, out hp, out hv))
                    {
                        Selected = hp; _selVert = hv;
                        if (e.shift) { PushUndo(); DeleteVertex(hp, hv); e.Use(); sv.Repaint(); break; }
                        PushUndo();
                        _dragVert = hv; _dragging = false;
                        e.Use(); sv.Repaint(); break;
                    }

                    P ep; int ei; Vector2 epos;
                    if (HitEdge(e.mousePosition, out ep, out ei, out epos))
                    {
                        PushUndo();
                        ep.pts.Insert(ei + 1, epos);
                        Selected = ep; _selVert = ei + 1; _dragVert = ei + 1; _dragging = false;
                        Touch(ep);
                        e.Use(); sv.Repaint(); break;
                    }

                    if ((e.command || e.control) && Selected != null)
                    {
                        Vector3 w;
                        if (TryPick(e.mousePosition, out w))
                        {
                            PushUndo();
                            Selected.pts.Add(new Vector2(w.x, w.z));
                            _selVert = Selected.pts.Count - 1;
                            Touch(Selected);
                            e.Use(); sv.Repaint(); break;
                        }
                    }

                    var inside = PickParcel(e.mousePosition);
                    if (inside != null) { Selected = inside; _selVert = -1; e.Use(); sv.Repaint(); }
                    else { Selected = null; _selVert = -1; sv.Repaint(); }
                }
                break;

            case EventType.MouseDrag:
                if (_dragVert >= 0 && Selected != null)
                {
                    Vector3 w;
                    if (TryPick(e.mousePosition, out w))
                    {
                        var q = new Vector2(w.x, w.z);
                        if (_snap) q = SnapTo(q, e.mousePosition, Selected);
                        // ⌘(Ctrl)を押しながら引くと、この一回だけ共有を連れて行かない
                        MoveVertex(Selected, _dragVert, q, !(e.command || e.control));
                        _dragging = true;
                        e.Use(); sv.Repaint();
                    }
                }
                break;

            case EventType.MouseUp:
                if (_dragVert >= 0) { _dragVert = -1; if (_dragging) EdoParcels.MarkDirty(); _dragging = false; e.Use(); }
                break;
        }
    }

    /// <summary>頂点を動かす。共有点(0.30m 以内で一致していた他区画の頂点)も一緒に動かす。
    /// これをやらないと三分岐点が割れて、隣り合う屋敷の間に隙間や重なりが出る。</summary>
    static void MoveVertex(P p, int i, Vector2 to, bool linkOverride = true)
    {
        Vector2 from = p.pts[i];
        p.pts[i] = to;
        Touch(p);
        _sharedDirty = true;
        if (!_link || !linkOverride) return;
        foreach (var q in EdoParcels.All)
        {
            for (int j = 0; j < q.pts.Count; j++)
            {
                if (q == p && j == i) continue;
                if (Vector2.Distance(q.pts[j], from) <= LinkTol) { q.pts[j] = to; Touch(q); }
            }
        }
    }

    static void DeleteVertex(P p, int i)
    {
        if (p.pts.Count <= 3) { Debug.LogWarning("[敷地割] 3頂点未満にはできない: " + p.id); return; }
        p.pts.RemoveAt(i);
        _selVert = Mathf.Clamp(i - 1, 0, p.pts.Count - 1);
        Touch(p);
        EdoParcels.MarkDirty();
    }

    static void Touch(P p)
    {
        EdoParcels.MarkDirty();
        _seenVersion = EdoParcels.Version;   // 自分の編集なので全捨てはしない
        Invalidate(p);
        _sharedDirty = true;
    }

    // ---- 当たり判定 -------------------------------------------------------

    static bool HitVertex(Vector2 gui, out P hp, out int hv)
    {
        hp = null; hv = -1;
        float best = GrabPx;
        foreach (var p in Visible(SceneView.lastActiveSceneView))
            for (int i = 0; i < p.pts.Count; i++)
            {
                float d = Vector2.Distance(gui, HandleUtility.WorldToGUIPoint(W(p.pts[i])));
                if (d < best) { best = d; hp = p; hv = i; }
            }
        return hp != null;
    }

    static bool HitEdge(Vector2 gui, out P hp, out int hi, out Vector2 hpos)
    {
        hp = null; hi = -1; hpos = Vector2.zero;
        float best = EdgePx;
        foreach (var p in Visible(SceneView.lastActiveSceneView))
        {
            int n = p.pts.Count;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = HandleUtility.WorldToGUIPoint(W(p.pts[i]));
                Vector2 b = HandleUtility.WorldToGUIPoint(W(p.pts[(i + 1) % n]));
                float d = HandleUtility.DistancePointToLineSegment(gui, a, b);
                if (d < best)
                {
                    best = d; hp = p; hi = i;
                    Vector2 ab = b - a;
                    float t = ab.sqrMagnitude < 1e-4f ? 0f : Mathf.Clamp01(Vector2.Dot(gui - a, ab) / ab.sqrMagnitude);
                    hpos = Vector2.Lerp(p.pts[i], p.pts[(i + 1) % n], t);
                }
            }
        }
        return hp != null;
    }

    static P PickParcel(Vector2 gui)
    {
        Vector3 w;
        if (!TryPick(gui, out w)) return null;
        var q = new Vector2(w.x, w.z);
        P best = null; float bestArea = float.MaxValue;
        foreach (var p in Visible(SceneView.lastActiveSceneView))
            if (PIP(p, q) && p.AreaM2 < bestArea) { best = p; bestArea = p.AreaM2; }
        return best;
    }

    // EdoGeom.PIP と実装差あり — 統一は裁定待ち
    static bool PIP(P p, Vector2 q)
    {
        bool ins = false; int n = p.pts.Count;
        for (int i = 0, j = n - 1; i < n; j = i++)
            if (((p.pts[i].y > q.y) != (p.pts[j].y > q.y)) &&
                (q.x < (p.pts[j].x - p.pts[i].x) * (q.y - p.pts[i].y) / (p.pts[j].y - p.pts[i].y) + p.pts[i].x))
                ins = !ins;
        return ins;
    }

    /// <summary>近くの他区画の頂点 → 辺 の順に吸着する。境界を共有する屋敷が
    /// 数cm ずれて隙間になるのを防ぐ。</summary>
    static Vector2 SnapTo(Vector2 q, Vector2 gui, P self)
    {
        Vector2 bestV = q; float bestD = SnapPx;
        foreach (var p in Visible(SceneView.lastActiveSceneView))
            for (int i = 0; i < p.pts.Count; i++)
            {
                if (p == self && (i == _dragVert)) continue;
                float d = Vector2.Distance(gui, HandleUtility.WorldToGUIPoint(W(p.pts[i])));
                if (d < bestD) { bestD = d; bestV = p.pts[i]; }
            }
        if (bestD < SnapPx) return bestV;

        float bestE = SnapPx; Vector2 bestP = q;
        foreach (var p in Visible(SceneView.lastActiveSceneView))
        {
            if (p == self) continue;
            int n = p.pts.Count;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = HandleUtility.WorldToGUIPoint(W(p.pts[i]));
                Vector2 b = HandleUtility.WorldToGUIPoint(W(p.pts[(i + 1) % n]));
                float d = HandleUtility.DistancePointToLineSegment(gui, a, b);
                if (d < bestE)
                {
                    bestE = d;
                    Vector2 ab = b - a;
                    float t = ab.sqrMagnitude < 1e-4f ? 0f : Mathf.Clamp01(Vector2.Dot(gui - a, ab) / ab.sqrMagnitude);
                    bestP = Vector2.Lerp(p.pts[i], p.pts[(i + 1) % n], t);
                }
            }
        }
        return bestE < SnapPx ? bestP : q;
    }

    // ---- 新規作成 --------------------------------------------------------

    public static void BeginDrawing(string category = "buke", int color = 5)
    {
        _drawing = new P { id = "new", label = "(新規)", category = category, color = color };
        _edit = true;
        EditorPrefs.SetBool(PrefEdit, true);
        Menu.SetChecked(MenuEdit, true);
        SceneView.RepaintAll();
    }

    static void FinishDrawing()
    {
        if (_drawing != null && _drawing.pts.Count >= 3)
        {
            var p = EdoParcels.Add("parcel", "(名前を付ける)", _drawing.category, _drawing.color, _drawing.pts);
            Selected = p; _selVert = -1;
            EdoParcels.Save();
            EdoParcelWindow.Refresh();
            Debug.Log(string.Format("[敷地割] 新しい区画 '{0}' — {1:N0} 坪 / {2} 頂点。一覧で名前と種別を付ける。",
                                    p.id, p.Tsubo, p.pts.Count));
        }
        _drawing = null;
        Invalidate();
    }

    static void CancelDrawing() { _drawing = null; SceneView.RepaintAll(); }
    public static bool IsDrawing { get { return _drawing != null; } }

    // ---- HUD -------------------------------------------------------------

    static void DrawHud(SceneView sv)
    {
        Handles.BeginGUI();
        float w = 292f;
        float h = _edit ? (_drawing != null ? 96f : (Selected != null && _selVert >= 0 ? 186f : 152f)) : 44f;
        _hud = new Rect(8, 112, w, h);
        GUILayout.BeginArea(_hud, GUI.skin.box);

        GUILayout.BeginHorizontal();
        var col = _drawing != null ? new Color(1f, 0.85f, 0.4f)
                : _edit ? new Color(0.5f, 1f, 0.7f) : new Color(0.8f, 0.8f, 0.8f);
        var ts = new GUIStyle(EditorStyles.miniBoldLabel) { normal = { textColor = col } };
        GUILayout.Label(_drawing != null ? "◇ 敷地割: 作図中" : _edit ? "✜ 敷地割: 編集中" : "敷地割: 表示のみ", ts);
        GUILayout.FlexibleSpace();
        GUILayout.Label(EdoParcels.All.Count + "区画" + (EdoParcels.IsDirty ? " *" : ""), EditorStyles.miniLabel);
        if (GUILayout.Button("一覧", EditorStyles.miniButton, GUILayout.Width(34))) EdoParcelWindow.Open();
        if (GUILayout.Button("隠す", EditorStyles.miniButton, GUILayout.Width(34))) ToggleShow();
        GUILayout.EndHorizontal();

        if (_edit && _drawing != null)
        {
            GUILayout.Label("クリックで頂点を打つ / Enter・右クリックで閉じる / Esc 取消",
                            new GUIStyle(EditorStyles.miniLabel) { wordWrap = true });
            GUILayout.Label(_drawing.pts.Count + " 頂点", EditorStyles.miniLabel);
        }
        else if (_edit)
        {
            var help = new GUIStyle(EditorStyles.miniLabel) { wordWrap = true };
            GUILayout.Label("頂点ドラッグ=動かす(⌘ドラッグ=共有を連れない)\n辺クリック=挿す / Shift+頂点=消す / ⌘Z=戻す\nW=共有にする / U=外す", help);

            if (Selected != null)
            {
                GUILayout.Label(string.Format("▸ {0}  {1:N0}坪 / 周 {2:N0}m / {3}頂点",
                                string.IsNullOrEmpty(Selected.label) ? Selected.id : Selected.label,
                                Selected.Tsubo, Selected.Perimeter, Selected.pts.Count),
                                EditorStyles.miniLabel);
                if (_selVert >= 0 && _selVert < Selected.pts.Count)
                {
                    var v = Selected.pts[_selVert];
                    int n = Selected.pts.Count;
                    float e0 = Vector2.Distance(Selected.pts[(_selVert + n - 1) % n], v);
                    float e1 = Vector2.Distance(v, Selected.pts[(_selVert + 1) % n]);
                    GUILayout.Label(string.Format("  頂点{0}  x {1:0.0} / z {2:0.0} / 地盤 {3:0.0}m   辺 {4:0.0}m・{5:0.0}m",
                                    _selVert, v.x, v.y, Ground(v), e0, e1), EditorStyles.miniLabel);

                    var grp = GroupOf(Selected, _selVert);
                    GUILayout.BeginHorizontal();
                    if (grp.Count > 1)
                    {
                        var others = grp.Where(kv => kv.Key != Selected).Select(kv => kv.Key.id);
                        GUILayout.Label("  ◎共有: " + string.Join(", ", others.ToArray()),
                                        new GUIStyle(EditorStyles.miniLabel) { normal = { textColor = Color.white } });
                    }
                    else GUILayout.Label("  ○単独", EditorStyles.miniLabel);
                    GUILayout.FlexibleSpace();
                    using (new EditorGUI.DisabledScope(grp.Count > 1))
                        if (GUILayout.Button("共有にする", EditorStyles.miniButton, GUILayout.Width(66))) WeldSelected();
                    using (new EditorGUI.DisabledScope(grp.Count <= 1))
                        if (GUILayout.Button("外す", EditorStyles.miniButton, GUILayout.Width(38))) UnweldSelected();
                    GUILayout.EndHorizontal();
                }
            }
            else GUILayout.Label("(区画の中をクリックで選ぶ)", EditorStyles.miniLabel);

            GUILayout.BeginHorizontal();
            bool nl = GUILayout.Toggle(_link, "共有点連動", EditorStyles.miniButton, GUILayout.Width(72));
            if (nl != _link) { _link = nl; EditorPrefs.SetBool(PrefLink, _link); }
            bool ns = GUILayout.Toggle(_snap, "吸着", EditorStyles.miniButton, GUILayout.Width(42));
            if (ns != _snap) { _snap = ns; EditorPrefs.SetBool(PrefSnap, _snap); }
            using (new EditorGUI.DisabledScope(_undo.Count == 0))
                if (GUILayout.Button("戻す", EditorStyles.miniButton, GUILayout.Width(38))) PopUndo();
            if (GUILayout.Button("＋新規", EditorStyles.miniButton, GUILayout.Width(48))) BeginDrawing();
            if (GUILayout.Button("保存", EditorStyles.miniButton, GUILayout.Width(38)))
            { EdoParcels.Save(); AssetDatabase.Refresh(); }
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            GUILayout.Label("表示半径", EditorStyles.miniLabel, GUILayout.Width(50));
            float nr = GUILayout.HorizontalSlider(_range, 0f, 3000f);
            if (Mathf.Abs(nr - _range) > 1f) { _range = nr; EditorPrefs.SetFloat(PrefRange, _range); Invalidate(); }
            GUILayout.Label(_range < 1f ? "全部" : string.Format("{0:N0}m", _range), EditorStyles.miniLabel, GUILayout.Width(44));
            GUILayout.EndHorizontal();
        }

        GUILayout.EndArea();
        Handles.EndGUI();
    }

    // ---- ピッキング(EdoSketch と同じ作法) --------------------------------

    static bool TryPick(Vector2 guiPos, out Vector3 point)
    {
        point = default(Vector3);
        Ray ray = HandleUtility.GUIPointToWorldRay(guiPos);
        if (RaycastTerrain(ray, out point)) return true;
        RaycastHit hit;
        if (Physics.Raycast(ray, out hit, 100000f)) { point = hit.point; return true; }
        if (Mathf.Abs(ray.direction.y) > 1e-5f)
        {
            float t = -ray.origin.y / ray.direction.y;
            if (t > 0f) { point = ray.origin + ray.direction * t; return true; }
        }
        return false;
    }

    static bool RaycastTerrain(Ray ray, out Vector3 point)
    {
        point = default(Vector3);
        const float maxDist = 20000f, step = 2f;
        float prevDiff = 0f; bool havePrev = false; Vector3 prev = ray.origin;
        for (float t = 0f; t <= maxDist; t += step)
        {
            Vector3 pos = ray.origin + ray.direction * t;
            float gy;
            if (!SampleGround(pos, out gy)) { havePrev = false; continue; }
            float diff = pos.y - gy;
            if (havePrev && prevDiff > 0f && diff <= 0f)
            {
                float f = prevDiff / (prevDiff - diff);
                point = Vector3.Lerp(prev, pos, f);
                float fy;
                if (SampleGround(point, out fy)) point.y = fy;
                return true;
            }
            prevDiff = diff; prev = pos; havePrev = true;
        }
        return false;
    }

    static bool SampleGround(Vector3 world, out float y)
    {
        y = 0f; bool found = false;
        foreach (var t in Terrain.activeTerrains)
        {
            if (t == null || !t.isActiveAndEnabled) continue;
            var tp = t.transform.position; var ts = t.terrainData.size;
            if (world.x < tp.x || world.x > tp.x + ts.x || world.z < tp.z || world.z > tp.z + ts.z) continue;
            float h = t.SampleHeight(world) + tp.y;
            if (!found || h > y) y = h;
            found = true;
        }
        return found;
    }

    // ---- 自動保存 --------------------------------------------------------

    static void AutoSave()
    {
        if (!EdoParcels.IsDirty) return;
        double now = EditorApplication.timeSinceStartup;
        if (now - _lastSave < 2.0) return;
        _lastSave = now;
        EdoParcels.Save();
    }

    static void FlushSave() { if (EdoParcels.IsDirty) EdoParcels.Save(); }
}
