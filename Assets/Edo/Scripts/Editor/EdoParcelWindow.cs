// 敷地割の一覧 — Edo ▸ 敷地割 ▸ 一覧を開く
//   区画の名前・種別・色・覚書、頂点の数値、面積(坪)と辺長(間)を見て直す。
//   ビルダーからの取り込みと突き合わせ、C# 配列の書き出しもここ。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEditor;
using P = EdoParcels.Parcel;

public class EdoParcelWindow : EditorWindow
{
    Vector2 _scrollList, _scrollDetail;
    string _filter = "";
    int _catFilter = 0;          // 0 = 全部
    static EdoParcelWindow _inst;

    [MenuItem("Edo/敷地割/一覧を開く", false, 12)]
    public static void Open()
    {
        _inst = GetWindow<EdoParcelWindow>("敷地割");
        _inst.minSize = new Vector2(560, 360);
        _inst.Show();
    }

    public static void Refresh() { if (_inst != null) _inst.Repaint(); }

    void OnEnable() { _inst = this; }

    void OnGUI()
    {
        DrawToolbar();
        EditorGUILayout.BeginHorizontal();
        DrawList();
        DrawDetail();
        EditorGUILayout.EndHorizontal();
    }

    // ---- ツールバー ------------------------------------------------------

    void DrawToolbar()
    {
        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);

        if (GUILayout.Button("＋新規(Sceneで打つ)", EditorStyles.toolbarButton, GUILayout.Width(130)))
            EdoParcelTool.BeginDrawing();

        if (GUILayout.Button("ビルダーから取り込む", EditorStyles.toolbarButton, GUILayout.Width(126)))
            ImportFromBuilders();

        if (GUILayout.Button("突き合わせ", EditorStyles.toolbarButton, GUILayout.Width(72)))
            Debug.Log("[敷地割] 突き合わせ\n" + EdoParcels.DiffAgainstBuilders());

        if (GUILayout.Button("保存", EditorStyles.toolbarButton, GUILayout.Width(44)))
        { EdoParcels.Save(); AssetDatabase.Refresh(); ShowNotification(new GUIContent("保存した")); }

        if (GUILayout.Button("再読込", EditorStyles.toolbarButton, GUILayout.Width(52)))
        { EdoParcels.Load(); EdoParcelTool.Invalidate(); }

        GUILayout.FlexibleSpace();
        GUILayout.Label(string.Format("{0} 区画 / 計 {1:N0} 坪{2}",
            EdoParcels.All.Count, EdoParcels.All.Sum(p => p.Tsubo), EdoParcels.IsDirty ? "  *未保存" : ""),
            EditorStyles.miniLabel);
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);
        GUILayout.Label("絞り込み", EditorStyles.miniLabel, GUILayout.Width(48));
        _filter = GUILayout.TextField(_filter, EditorStyles.toolbarSearchField, GUILayout.Width(180));
        var cats = new[] { "全部" }.Concat(EdoParcels.Categories.Select(EdoParcels.CategoryLabel)).ToArray();
        _catFilter = EditorGUILayout.Popup(_catFilter, cats, EditorStyles.toolbarPopup, GUILayout.Width(120));
        GUILayout.FlexibleSpace();
        EditorGUILayout.EndHorizontal();
    }

    IEnumerable<P> Filtered()
    {
        foreach (var p in EdoParcels.All.OrderBy(x => x.category).ThenBy(x => x.id, StringComparer.Ordinal))
        {
            if (_catFilter > 0 && p.category != EdoParcels.Categories[_catFilter - 1]) continue;
            if (!string.IsNullOrEmpty(_filter))
            {
                string hay = (p.id + " " + p.label + " " + p.source + " " + p.note).ToLowerInvariant();
                if (!hay.Contains(_filter.ToLowerInvariant())) continue;
            }
            yield return p;
        }
    }

    // ---- 一覧 ------------------------------------------------------------

    void DrawList()
    {
        EditorGUILayout.BeginVertical(GUILayout.Width(300));
        _scrollList = EditorGUILayout.BeginScrollView(_scrollList);

        string cat = null;
        foreach (var p in Filtered())
        {
            if (p.category != cat)
            {
                cat = p.category;
                EditorGUILayout.LabelField(EdoParcels.CategoryLabel(cat), EditorStyles.boldLabel);
            }
            bool sel = EdoParcelTool.Selected == p;
            var bg = GUI.backgroundColor;
            if (sel) GUI.backgroundColor = new Color(0.5f, 0.8f, 1f);
            EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
            GUI.backgroundColor = bg;

            var r = GUILayoutUtility.GetRect(10, 14, GUILayout.Width(10));
            EditorGUI.DrawRect(new Rect(r.x, r.y + 2, 10, 10), p.Col);

            if (GUILayout.Button(string.IsNullOrEmpty(p.label) ? p.id : p.label,
                                 EditorStyles.label, GUILayout.Width(170)))
            {
                EdoParcelTool.Selected = p;
                SceneView.RepaintAll();
            }
            GUILayout.Label(string.Format("{0:N0}坪", p.Tsubo), EditorStyles.miniLabel, GUILayout.Width(58));
            if (GUILayout.Button("◎", EditorStyles.miniButton, GUILayout.Width(22)))
            { EdoParcelTool.Selected = p; FrameOn(p); }
            EditorGUILayout.EndHorizontal();
        }

        EditorGUILayout.EndScrollView();
        EditorGUILayout.EndVertical();
    }

    static void FrameOn(P p)
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) return;
        var c = p.Centroid;
        float radius = Mathf.Max(40f, p.Perimeter * 0.18f);
        sv.LookAt(new Vector3(c.x, EdoParcelTool.Ground(c) + 2f, c.y), sv.rotation, radius);
        sv.Repaint();
    }

    // ---- 詳細 ------------------------------------------------------------

    void DrawDetail()
    {
        EditorGUILayout.BeginVertical();
        var p = EdoParcelTool.Selected;
        if (p == null)
        {
            EditorGUILayout.HelpBox(
                "区画を選ぶと、名前・種別・頂点の数値をここで直せる。\n\n" +
                "Scene ビューでの操作は Edo ▸ 敷地割 ▸ 編集モード (Cmd+Shift+K):\n" +
                "  頂点ドラッグ = 動かす / 辺クリック = 頂点を挿す\n" +
                "  Shift+頂点 = 消す / ⌘+空所 = 末尾に足す\n" +
                "  ＋新規 → 順に打つ → Enter で閉じる", MessageType.Info);
            EditorGUILayout.EndVertical();
            return;
        }

        _scrollDetail = EditorGUILayout.BeginScrollView(_scrollDetail);
        EditorGUI.BeginChangeCheck();

        EditorGUILayout.LabelField("区画", EditorStyles.boldLabel);
        p.id = EditorGUILayout.TextField("id (ビルダーの鍵)", p.id);
        p.label = EditorGUILayout.TextField("表示名", p.label);
        int ci = Mathf.Max(0, Array.IndexOf(EdoParcels.Categories, p.category));
        ci = EditorGUILayout.Popup("種別", ci, EdoParcels.Categories.Select(EdoParcels.CategoryLabel).ToArray());
        p.category = EdoParcels.Categories[ci];

        EditorGUILayout.BeginHorizontal();
        EditorGUILayout.PrefixLabel("色");
        for (int i = 0; i < EdoParcels.Palette.Length; i++)
        {
            var bg = GUI.backgroundColor;
            GUI.backgroundColor = EdoParcels.Palette[i];
            if (GUILayout.Button(i == p.color ? "●" : " ", GUILayout.Width(26), GUILayout.Height(18))) p.color = i;
            GUI.backgroundColor = bg;
        }
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.LabelField("覚書(典拠・確度)");
        p.note = EditorGUILayout.TextArea(p.note, GUILayout.Height(38));
        using (new EditorGUI.DisabledScope(true))
            EditorGUILayout.TextField("取り込み元", string.IsNullOrEmpty(p.source) ? "(手で引いた)" : p.source);

        EditorGUILayout.Space(6);
        EditorGUILayout.LabelField("実測", EditorStyles.boldLabel);
        EditorGUILayout.LabelField(string.Format("面積  {0:N0} m²  =  {1:N0} 坪", p.AreaM2, p.Tsubo));
        EditorGUILayout.LabelField(string.Format("周長  {0:N1} m  =  {1:N1} 間", p.Perimeter, p.Perimeter / EdoParcels.KEN));
        EditorGUILayout.LabelField(string.Format("重心  x {0:0.0} / z {1:0.0}", p.Centroid.x, p.Centroid.y));

        EditorGUILayout.Space(6);
        EditorGUILayout.LabelField("頂点 (世界座標 x, z)", EditorStyles.boldLabel);
        int n = p.pts.Count;
        int del = -1;
        for (int i = 0; i < n; i++)
        {
            EditorGUILayout.BeginHorizontal();
            GUILayout.Label(i.ToString(), EditorStyles.miniLabel, GUILayout.Width(20));
            var v = p.pts[i];
            float nx = EditorGUILayout.FloatField(v.x, GUILayout.Width(72));
            float nz = EditorGUILayout.FloatField(v.y, GUILayout.Width(72));
            if (!Mathf.Approximately(nx, v.x) || !Mathf.Approximately(nz, v.y))
            { p.pts[i] = new Vector2(nx, nz); EdoParcelTool.Invalidate(p); EdoParcels.MarkDirty(); }
            float len = Vector2.Distance(p.pts[i], p.pts[(i + 1) % n]);
            GUILayout.Label(string.Format("辺{0}-{1}  {2:0.0}m ({3:0.0}間)  地盤 {4:0.0}m",
                            i, (i + 1) % n, len, len / EdoParcels.KEN, EdoParcelTool.Ground(p.pts[i])),
                            EditorStyles.miniLabel);
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("×", EditorStyles.miniButton, GUILayout.Width(20))) del = i;
            EditorGUILayout.EndHorizontal();
        }
        if (del >= 0 && n > 3)
        { p.pts.RemoveAt(del); EdoParcelTool.Invalidate(p); EdoParcels.MarkDirty(); }

        EditorGUILayout.Space(8);
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("C# 配列をコピー"))
        { EditorGUIUtility.systemCopyBuffer = ToCSharp(p); ShowNotification(new GUIContent("クリップボードへ")); }
        if (GUILayout.Button("向きを揃える(CCW)"))
        { if (p.SignedArea < 0) p.pts.Reverse(); EdoParcelTool.Invalidate(p); EdoParcels.MarkDirty(); }
        var bg2 = GUI.backgroundColor;
        GUI.backgroundColor = new Color(1f, 0.6f, 0.6f);
        if (GUILayout.Button("この区画を消す", GUILayout.Width(110)))
        {
            if (EditorUtility.DisplayDialog("敷地割", "'" + p.id + "' を消す。よいか。", "消す", "やめる"))
            { EdoParcels.Remove(p); EdoParcelTool.Selected = null; EdoParcelTool.Invalidate(); }
        }
        GUI.backgroundColor = bg2;
        EditorGUILayout.EndHorizontal();

        if (EditorGUI.EndChangeCheck()) EdoParcels.MarkDirty();

        EditorGUILayout.EndScrollView();
        EditorGUILayout.EndVertical();
    }

    static string ToCSharp(P p)
    {
        var ic = CultureInfo.InvariantCulture;
        var sb = new StringBuilder();
        sb.AppendLine("    // " + p.label + "  " + p.Tsubo.ToString("N0") + " 坪");
        sb.AppendLine("    public static readonly Vector2[] " + p.id.ToUpperInvariant() + " = {");
        for (int i = 0; i < p.pts.Count; i++)
        {
            if (i % 3 == 0) sb.Append("        ");
            sb.AppendFormat(ic, "new Vector2({0}f, {1}f)", p.pts[i].x.ToString("0.###", ic), p.pts[i].y.ToString("0.###", ic));
            sb.Append(i < p.pts.Count - 1 ? ", " : " };");
            if (i % 3 == 2 || i == p.pts.Count - 1) sb.AppendLine();
        }
        return sb.ToString();
    }

    // ---- 取り込み --------------------------------------------------------

    void ImportFromBuilders()
    {
        var h = EdoParcels.HarvestFromBuilders();
        var known = new HashSet<string>(EdoParcels.All.Select(x => x.source).Where(s => !string.IsNullOrEmpty(s)));
        var fresh = h.Where(x => !known.Contains(x.source)).ToList();
        if (fresh.Count == 0)
        { ShowNotification(new GUIContent("新しい区画は無い")); return; }

        if (!EditorUtility.DisplayDialog("敷地割",
            string.Format("ビルダーから {0} 区画を取り込む。\n既に取り込んだ物は触らない。", fresh.Count),
            "取り込む", "やめる")) return;

        foreach (var x in fresh)
        {
            string id = MakeId(x.source);
            string label = string.IsNullOrEmpty(x.label) ? id : x.label;
            var p = EdoParcels.Add(id, label, GuessCategory(x.source, x.label), GuessColor(x.source, x.label), x.pts);
            p.source = x.source;
        }
        EdoParcels.Save();
        EdoParcelTool.Invalidate();
        Debug.Log("[敷地割] " + fresh.Count + " 区画を取り込んだ。名前と種別を一覧で直すこと。");
    }

    static string MakeId(string source)
    {
        // "EdoSannoKitaBuilder.OKABE" → "okabe" / "EdoSannoJuboBuilder.PARCELS[3]" → "jubo_3"
        string s = source;
        int dot = s.IndexOf('.');
        string type = dot > 0 ? s.Substring(0, dot) : s;
        string field = dot > 0 ? s.Substring(dot + 1) : s;
        field = field.Replace("[", "_").Replace("]", "");
        string prefix = type.StartsWith("Edo") ? type.Substring(3) : type;
        prefix = prefix.Replace("Builder", "").Replace("Rebuild", "");
        return (prefix + "_" + field).ToLowerInvariant();
    }

    static string GuessCategory(string source, string label)
    {
        string s = (source + " " + label).ToLowerInvariant();
        if (label.Contains("院") || label.Contains("寺") || label.Contains("社") || s.Contains("jubo") || s.Contains("sha")) return "jisha";
        if (label.Contains("町") || s.Contains("machi") || s.Contains("tamachi") || s.Contains("shinmachi") || s.Contains("daichi")) return "machiya";
        if (s.Contains("azukari") || label.Contains("会所") || label.Contains("干場") || label.Contains("明地")) return "kouyuu";
        if (label.Contains("屋敷") || s.Contains("yashiki") || s.Contains("buke") || s.Contains("kita") || s.Contains("sanbezaka")) return "buke";
        return "other";
    }

    static int GuessColor(string source, string label)
    {
        switch (GuessCategory(source, label))
        {
            case "jisha": return 3;
            case "machiya": return 4;
            case "kouyuu": return 6;
            case "buke": return 2;
            default: return 5;
        }
    }
}
