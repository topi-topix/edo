using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// Scene ビューの画角ブックマーク＋指摘メモ＋画像への印付け。
///
/// 使い方:
///  1. 問題箇所を Scene ビューで映して Cmd+Shift+B。
///     → その画角のスクショが自動保存され、一覧ウィンドウが開く。
///  2. 一覧ウィンドウでスクショを確認しながら:
///     - スクショを左クリック → 赤丸マーカー(番号付き)を置く「この箇所が変」
///     - マーカーを右クリック → 削除
///     - コメント欄に指摘を記入(自動保存)
///  3. AI に「ブックマーク見て」と言えば、画角+印付きスクショ+コメントをまとめて読み取って対応する。
///
/// 保存先: <project>/Screenshots/Bookmarks/  (Assets/ の外。Unity の import 対象にしない)
///   bookmarks.json = 画角・コメント・印(正規化座標)
///   bm_*.png       = 元スクショ / bm_*_ann.png = 印を焼き込んだ注釈版(AI が読む)
/// </summary>
public class EdoViewBookmarkWindow : EditorWindow
{
    [System.Serializable]
    public class Entry
    {
        public string id;
        public Vector3 pos;
        public Vector3 euler;
        public float fov = 60f;
        public float aspect = 1.7778f;   // 撮影時の Scene ビュー縦横比
        public bool ortho;               // Scene ビューが正投影(2D)だったか
        public float orthoSize;          // 正投影時のサイズ
        public string png;
        public string pngNoWater = "";   // 水域を非表示にして撮った同一画角の版(AIが見やすい)
        public string note = "";
        public string time;
        public List<Vector2> marks = new List<Vector2>(); // 画像上の正規化座標(左上原点)
    }

    [System.Serializable]
    public class Book { public List<Entry> entries = new List<Entry>(); }

    // プロジェクトルート直下(Assets/ の外)。1GB のスクショを Unity に import させないため。
    const string Dir = "Screenshots/Bookmarks";
    static string JsonPath => Dir + "/bookmarks.json";

    Book book;
    Vector2 scroll;
    readonly Dictionary<string, Texture2D> thumbs = new Dictionary<string, Texture2D>();
    static Texture2D ringTex;

    [MenuItem("Edo/視点/画角をブックマーク %#b")]
    static void AddBookmark()
    {
        var sv = SceneView.lastActiveSceneView;
        if (sv == null) return;
        var cam = sv.camera;

        System.IO.Directory.CreateDirectory(Dir);
        var b = Load();
        string id = System.DateTime.Now.ToString("yyyyMMdd_HHmmss_fff");
        string png = $"{Dir}/bm_{id}.png";

        // Scene ビューの実際の描画サイズ(縦横比)に合わせて撮る。
        // ここを 16:9 固定にすると、見ている画角とスクショがズレる。
        int sw = Mathf.Max(16, Mathf.RoundToInt(cam.pixelWidth));
        int sh = Mathf.Max(16, Mathf.RoundToInt(cam.pixelHeight));
        if (sw > 1920) { sh = Mathf.RoundToInt(sh * 1920f / sw); sw = 1920; }
        if (sh > 1920) { sw = Mathf.RoundToInt(sw * 1920f / sh); sh = 1920; }
        float aspect = (float)sw / sh;

        RenderShot(cam, sw, sh, aspect, false, png);              // 通常(水域あり)
        string pngNW = $"{Dir}/bm_{id}_nowater.png";
        RenderShot(cam, sw, sh, aspect, true, pngNW);             // 水域を非表示にした同一画角

        b.entries.Add(new Entry
        {
            id = id,
            pos = cam.transform.position,
            euler = cam.transform.eulerAngles,
            fov = cam.fieldOfView,
            aspect = aspect,
            ortho = cam.orthographic,
            orthoSize = cam.orthographicSize,
            png = png,
            pngNoWater = pngNW,
            time = System.DateTime.Now.ToString("MM/dd HH:mm")
        });
        Save(b);

        sv.ShowNotification(new GUIContent($"ブックマーク #{b.entries.Count} 保存"));
        var w = GetWindow<EdoViewBookmarkWindow>("画角ブックマーク");
        w.book = b; w.thumbs.Clear(); w.Repaint();
    }

    [MenuItem("Edo/視点/ブックマーク一覧")]
    static void OpenWindow() => GetWindow<EdoViewBookmarkWindow>("画角ブックマーク");

    static Book Load()
    {
        if (!System.IO.File.Exists(JsonPath)) return new Book();
        try { return JsonUtility.FromJson<Book>(System.IO.File.ReadAllText(JsonPath)) ?? new Book(); }
        catch { return new Book(); }
    }

    static void Save(Book b) => System.IO.File.WriteAllText(JsonPath, JsonUtility.ToJson(b, true));

    void OnEnable() { book = Load(); }

    Texture2D Thumb(string png)
    {
        if (thumbs.TryGetValue(png, out var t) && t != null) return t;
        if (!System.IO.File.Exists(png)) return null;
        var tx = new Texture2D(2, 2);
        tx.LoadImage(System.IO.File.ReadAllBytes(png));
        thumbs[png] = tx;
        return tx;
    }

    static Texture2D RingTex()
    {
        if (ringTex != null) return ringTex;
        const int S = 64; float c = (S - 1) / 2f, rOut = 29f, rIn = 23f;
        ringTex = new Texture2D(S, S, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave };
        var px = new Color32[S * S];
        for (int y = 0; y < S; y++)
            for (int x = 0; x < S; x++)
            {
                float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c));
                px[y * S + x] = (d <= rOut && d >= rIn) ? new Color32(255, 40, 40, 235) : new Color32(0, 0, 0, 0);
            }
        ringTex.SetPixels32(px); ringTex.Apply();
        return ringTex;
    }

    /// <summary>指定カメラ画角で撮影しPNG保存。hideWater=true なら水域メッシュを一時的に隠して撮る。</summary>
    static void RenderShot(Camera src, int sw, int sh, float aspect, bool hideWater, string outPath)
    {
        List<Renderer> hidden = hideWater ? HideWaterRenderers() : null;
        var g = new GameObject("bmshot") { hideFlags = HideFlags.HideAndDontSave };
        var c2 = g.AddComponent<Camera>();
        c2.CopyFrom(src);
        c2.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
        c2.aspect = aspect;
        c2.clearFlags = CameraClearFlags.Skybox;
        c2.targetTexture = null;
        var rt = new RenderTexture(sw, sh, 24);
        c2.targetTexture = rt; c2.Render();
        RenderTexture.active = rt;
        var tx = new Texture2D(sw, sh, TextureFormat.RGB24, false);
        tx.ReadPixels(new Rect(0, 0, sw, sh), 0, 0); tx.Apply();
        System.IO.File.WriteAllBytes(outPath, tx.EncodeToPNG());
        RenderTexture.active = null; c2.targetTexture = null;
        Object.DestroyImmediate(rt); Object.DestroyImmediate(g); Object.DestroyImmediate(tx);
        if (hidden != null) foreach (var r in hidden) if (r != null) r.enabled = true;
    }

    /// <summary>水域(Edo/Water系シェーダ・WaterBody・名前に Water を含む)の描画を一時的に無効化。</summary>
    static List<Renderer> HideWaterRenderers()
    {
        var hidden = new List<Renderer>();
        foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
        {
            if (!r.enabled) continue;
            bool isWater = r.GetComponent<WaterBody>() != null || r.GetComponentInParent<WaterBody>() != null;
            if (!isWater)
            {
                var m = r.sharedMaterial; string sh = (m != null && m.shader != null) ? m.shader.name : "";
                string n = r.gameObject.name;
                if (sh.IndexOf("Water", System.StringComparison.OrdinalIgnoreCase) >= 0 ||
                    sh.IndexOf("Edo/Mote", System.StringComparison.OrdinalIgnoreCase) >= 0 ||
                    n.IndexOf("Water", System.StringComparison.OrdinalIgnoreCase) >= 0) isWater = true;
            }
            if (isWater) { r.enabled = false; hidden.Add(r); }
        }
        return hidden;
    }

    /// <summary>印を元スクショに焼き込んだ注釈版 (_ann.png) を書き出す。AI はこれを読む。水域非表示版もあれば同時に。</summary>
    static void WriteAnnotated(Entry e)
    {
        AnnotateOne(e.png, e.marks);
        if (!string.IsNullOrEmpty(e.pngNoWater)) AnnotateOne(e.pngNoWater, e.marks);
    }

    static void AnnotateOne(string srcPng, List<Vector2> marks)
    {
        string ann = srcPng.Replace(".png", "_ann.png");
        if (marks.Count == 0) { if (System.IO.File.Exists(ann)) System.IO.File.Delete(ann); return; }
        if (!System.IO.File.Exists(srcPng)) return;
        var e = new Entry { marks = marks }; // 以降の既存ロジックが e.marks を参照
        var tx = new Texture2D(2, 2);
        tx.LoadImage(System.IO.File.ReadAllBytes(srcPng));
        int W = tx.width, H = tx.height;
        var px = tx.GetPixels32();
        for (int mi = 0; mi < e.marks.Count; mi++)
        {
            var m = e.marks[mi];
            int cx = Mathf.RoundToInt(m.x * W);
            int cy = Mathf.RoundToInt((1f - m.y) * H); // テクスチャは下原点
            // 赤リング (半径40px, 太さ6px)
            for (int dy = -46; dy <= 46; dy++)
                for (int dx = -46; dx <= 46; dx++)
                {
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    if (d < 37f || d > 43f) continue;
                    int x = cx + dx, y = cy + dy;
                    if (x < 0 || x >= W || y < 0 || y >= H) continue;
                    px[y * W + x] = new Color32(255, 40, 40, 255);
                }
            // 番号: リング右上に太い赤のタリーマーク(縦棒 mi+1 本)で表現
            int bars = Mathf.Min(mi + 1, 8);
            for (int b2 = 0; b2 < bars; b2++)
                for (int dy = 0; dy < 22; dy++)
                    for (int dx = 0; dx < 5; dx++)
                    {
                        int x = cx + 34 + b2 * 9 + dx, y = cy + 34 + dy;
                        if (x < 0 || x >= W || y < 0 || y >= H) continue;
                        px[y * W + x] = new Color32(255, 40, 40, 255);
                    }
        }
        tx.SetPixels32(px); tx.Apply();
        System.IO.File.WriteAllBytes(ann, tx.EncodeToPNG());
        Object.DestroyImmediate(tx);
    }

    void OnGUI()
    {
        if (book == null) book = Load();
        EditorGUILayout.HelpBox("Cmd+Shift+B = 今の Scene ビュー画角をスクショ付きで記録。\n" +
            "スクショを左クリック=赤丸マーカー / マーカー右クリック=削除。コメントも記入したら AI に「ブックマーク見て」。", MessageType.Info);

        using (new EditorGUILayout.HorizontalScope())
        {
            if (GUILayout.Button("再読込")) { book = Load(); thumbs.Clear(); }
            GUI.backgroundColor = new Color(1f, 0.7f, 0.6f);
            if (GUILayout.Button("全消去") &&
                EditorUtility.DisplayDialog("全消去", "ブックマークとスクショを全て削除します。よろしいですか？", "削除", "やめる"))
            {
                foreach (var e in book.entries)
                {
                    if (!string.IsNullOrEmpty(e.png))
                    {
                        if (System.IO.File.Exists(e.png)) System.IO.File.Delete(e.png);
                        string ann = e.png.Replace(".png", "_ann.png");
                        if (System.IO.File.Exists(ann)) System.IO.File.Delete(ann);
                    }
                }
                book = new Book(); Save(book); thumbs.Clear();
            }
            GUI.backgroundColor = Color.white;
        }

        if (book.entries.Count == 0)
        {
            EditorGUILayout.LabelField("ブックマークはまだありません。Scene ビューで Cmd+Shift+B。");
            return;
        }

        scroll = EditorGUILayout.BeginScrollView(scroll);
        int del = -1;
        for (int i = 0; i < book.entries.Count; i++)
        {
            var e = book.entries[i];
            EditorGUILayout.BeginVertical("box");
            EditorGUILayout.LabelField($"#{i + 1}  ({e.time})  印:{e.marks.Count}個", EditorStyles.boldLabel);

            var t = Thumb(e.png);
            if (t != null)
            {
                float w = EditorGUIUtility.currentViewWidth - 40f;
                float h = w * t.height / t.width;
                var r = GUILayoutUtility.GetRect(w, h, GUILayout.ExpandWidth(false));
                GUI.DrawTexture(r, t, ScaleMode.StretchToFill);

                // 印の描画
                for (int mi = 0; mi < e.marks.Count; mi++)
                {
                    var m = e.marks[mi];
                    float mx = r.x + m.x * r.width, my = r.y + m.y * r.height;
                    GUI.DrawTexture(new Rect(mx - 16, my - 16, 32, 32), RingTex(), ScaleMode.StretchToFill);
                    var st = new GUIStyle(EditorStyles.boldLabel);
                    st.normal.textColor = new Color(1f, 0.2f, 0.2f);
                    GUI.Label(new Rect(mx + 12, my + 8, 30, 20), (mi + 1).ToString(), st);
                }

                // クリックで印の追加/削除
                var ev = Event.current;
                if (ev.type == EventType.MouseDown && r.Contains(ev.mousePosition))
                {
                    var uv = new Vector2((ev.mousePosition.x - r.x) / r.width, (ev.mousePosition.y - r.y) / r.height);
                    if (ev.button == 0)
                    {
                        e.marks.Add(uv); Save(book); WriteAnnotated(e); ev.Use(); Repaint();
                    }
                    else if (ev.button == 1 && e.marks.Count > 0)
                    {
                        int nearest = -1; float best = 1e9f;
                        for (int mi = 0; mi < e.marks.Count; mi++)
                        {
                            float d = Vector2.Distance(new Vector2(e.marks[mi].x * r.width, e.marks[mi].y * r.height),
                                                       new Vector2(uv.x * r.width, uv.y * r.height));
                            if (d < best) { best = d; nearest = mi; }
                        }
                        if (nearest >= 0 && best < 40f)
                        {
                            e.marks.RemoveAt(nearest); Save(book); WriteAnnotated(e); ev.Use(); Repaint();
                        }
                    }
                }
            }

            EditorGUILayout.LabelField("指摘・コメント:");
            string newNote = EditorGUILayout.TextArea(e.note, GUILayout.MinHeight(40));
            if (newNote != e.note) { e.note = newNote; Save(book); }

            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("この画角へ移動"))
                {
                    var sv = SceneView.lastActiveSceneView;
                    if (sv != null)
                    {
                        var rot = Quaternion.Euler(e.euler);
                        sv.LookAtDirect(e.pos + rot * Vector3.forward * 8f, rot, 8f);
                    }
                }
                if (GUILayout.Button("印を全消去", GUILayout.Width(90)))
                {
                    e.marks.Clear(); Save(book); WriteAnnotated(e);
                }
                if (GUILayout.Button("削除", GUILayout.Width(60))) del = i;
            }
            EditorGUILayout.EndVertical();
            EditorGUILayout.Space(4);
        }
        EditorGUILayout.EndScrollView();

        if (del >= 0)
        {
            var e = book.entries[del];
            if (!string.IsNullOrEmpty(e.png))
            {
                if (System.IO.File.Exists(e.png)) System.IO.File.Delete(e.png);
                string ann = e.png.Replace(".png", "_ann.png");
                if (System.IO.File.Exists(ann)) System.IO.File.Delete(ann);
            }
            book.entries.RemoveAt(del); Save(book);
        }
    }
}
