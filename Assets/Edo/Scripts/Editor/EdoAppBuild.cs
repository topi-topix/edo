using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

/// <summary>
/// 書き出し — 赤坂を Mac / Windows のアプリにして、施主の Mac(M1・8GB)で滑らかに歩ける所まで軽くする(EDO-0450)。
///
/// ⭐ **エディタには効かせない。** 軽くする手はすべて「アプリ用の画質」(品質 `App`)と、書き出すときだけ走る
///   シーンの下ごしらえ(<see cref="EdoAppSceneStrip"/>)に置く。赤坂のシーン・プレハブ・地形の資産は一切書き換えない
///   (手組み資産は正典・規則1)。エディタの品質は `PC` のまま。
///
///   1. **遠景の間引き** — GPU Resident Drawer の「小さい駒を描かない」(画面の割合で間引く)+ LOD の偏り 1。
///      地形の木は描く距離・板絵へ落とす距離を縮める。
///   2. **見えない物を描かない** — GPU のオクルージョンカリング(焼かない・塀と建物の陰の駒を毎フレーム落とす)。
///      三角形の多い模型(土塀・長屋・表店)は Mesh LOD で遠くの面を自動で間引く(<see cref="EdoAppMeshLod"/>)。
///      絵は書き出しで一辺 <see cref="MaxTextureSize"/> へ落とす。
///   3. **区域ごとの読み込み** — 図の上の置き場が要らないもの(古地図・現代地図の重ね・測地の目印・非表示の撤去物)を
///      書き出しから外す。読み込み単位の分割(追加シーン)は実測で要るとなってから(<see cref="EdoAppSceneStrip"/> 冒頭)。
///
/// ⛔ 書き出し一覧は開始画面(Boot)と赤坂の二枚だけ(SampleScene は外す)。Boot が開始画面を出し、赤坂を裏で読む
///   (<see cref="EnsureBootScene"/>・<c>EdoAppFlow</c>・画面は <c>Assets/Edo/UI/</c>)。
/// </summary>
public static class EdoAppBuild
{
    const string AppLevel = "App";

    // ── アプリの遠景(狙いの値・実測で詰める)──
    /// <summary>画面の高さに対してこの割合より小さく映る駒は描かない(GPU Resident Drawer)。</summary>
    public const float SmallMeshScreenPercent = 0.4f;
    /// <summary>地形の木を描く距離 / 板絵へ落とす距離 / 草 / 地形の粗さ / 地表の絵を一枚絵に落とす距離(m・px)。</summary>
    /// ⛔ 板絵の距離は木の距離と同じにする — SpeedTree の板絵は URP で白く飛ぶ(メモリ japanese-garden-urp-patches)。
    public const float TreeDistance = 600f, DetailDistance = 50f, HeightmapPixelError = 4f, BasemapDistance = 250f;
    /// <summary>書き出す絵の一辺の上限(px)。庭のパックの木の絵が 4096・無圧縮で 1 枚 112〜170MB ある。</summary>
    public const int MaxTextureSize = 2048;

    [MenuItem("Edo/書き出し/Mac アプリ", false, 900)]
    static void BuildMac() => Build(BuildTarget.StandaloneOSX);

    [MenuItem("Edo/書き出し/Windows アプリ", false, 901)]
    static void BuildWin() => Build(BuildTarget.StandaloneWindows64);

    [MenuItem("Edo/書き出し/アプリ用の画質と開始画面を整える", false, 920)]
    static void EnsureMenu() { EnsureAppQuality(); EnsureBootScene(); SetBuildScenes(); Debug.Log("[書き出し] 画質 App と書き出し一覧を整えた"); }

    static readonly string[] BuildScenes = { EdoAssets.Scenes.Boot, EdoAssets.Scenes.Akasaka };

    /// <summary>書き出し一覧を 開始画面 → 赤坂 の二枚だけにする(最初の一枚がアプリの起動で開く)。</summary>
    public static void SetBuildScenes()
    {
        var cur = EditorBuildSettings.scenes;
        bool same = cur.Length == BuildScenes.Length;
        for (int i = 0; same && i < cur.Length; i++) same = cur[i].path == BuildScenes[i] && cur[i].enabled;
        if (same) return;
        var want = new EditorBuildSettingsScene[BuildScenes.Length];
        for (int i = 0; i < want.Length; i++) want[i] = new EditorBuildSettingsScene(BuildScenes[i], true);
        EditorBuildSettings.scenes = want;
    }

    /// <summary>
    /// アプリの最初の一枚(開始画面)を起こし、中身を毎回そろえる: 黒地のカメラ + 画面一式(UIDocument)+ <c>EdoAppFlow</c>。
    /// 画面の置き方(PanelSettings)も無ければ起こす。開いているシーンには触らない(追加で開いて保存し、すぐ閉じる)。
    /// </summary>
    public static void EnsureBootScene()
    {
        var panel = EnsurePanelSettings();
        var uxml = AssetDatabase.LoadAssetAtPath<UnityEngine.UIElements.VisualTreeAsset>(EdoAssets.App.Uxml);
        var titleImage = AssetDatabase.LoadAssetAtPath<Texture2D>(EdoAssets.App.TitleImage);
        if (uxml == null) { Debug.LogError($"[書き出し] 画面一式が無い: {EdoAssets.App.Uxml}"); return; }

        bool existed = File.Exists(EdoAssets.Scenes.Boot);
        var sc = existed
            ? UnityEditor.SceneManagement.EditorSceneManager.OpenScene(EdoAssets.Scenes.Boot, UnityEditor.SceneManagement.OpenSceneMode.Additive)
            : UnityEditor.SceneManagement.EditorSceneManager.NewScene(
                UnityEditor.SceneManagement.NewSceneSetup.EmptyScene, UnityEditor.SceneManagement.NewSceneMode.Additive);
        try
        {
            Camera cam = null; EdoAppFlow flow = null;
            foreach (var go in sc.GetRootGameObjects())
            {
                if (cam == null) cam = go.GetComponent<Camera>();
                if (flow == null) flow = go.GetComponent<EdoAppFlow>();
            }
            if (cam == null)
            {
                var g = new GameObject("BootCamera");
                SceneManager.MoveGameObjectToScene(g, sc);
                cam = g.AddComponent<Camera>();
            }
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.07f, 0.07f, 0.08f);
            cam.cullingMask = 0;
            if (flow == null)
            {
                var g = new GameObject("EdoApp");
                SceneManager.MoveGameObjectToScene(g, sc);
                flow = g.AddComponent<EdoAppFlow>();   // UIDocument は RequireComponent で付く
            }
            var doc = flow.GetComponent<UnityEngine.UIElements.UIDocument>();
            doc.panelSettings = panel;
            doc.visualTreeAsset = uxml;
            flow.sceneName = Path.GetFileNameWithoutExtension(EdoAssets.Scenes.Akasaka);
            flow.titleImage = titleImage;
            if (titleImage == null) Debug.LogWarning($"[書き出し] 開始画面の絵が無い({EdoAssets.App.TitleImage})— 無地で出す。赤坂を開いて Edo/書き出し/開始画面の絵を撮る");
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(sc);
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(sc, EdoAssets.Scenes.Boot);
        }
        finally { UnityEditor.SceneManagement.EditorSceneManager.CloseScene(sc, true); }
        if (!existed) Debug.Log($"[書き出し] 開始画面の一枚を起こした → {EdoAssets.Scenes.Boot}");
    }

    /// <summary>画面の置き方: 1920×1080 を基準に画面の大きさへ合わせる(縦横の比が違えば短い方に揃える)。</summary>
    static UnityEngine.UIElements.PanelSettings EnsurePanelSettings()
    {
        var ps = AssetDatabase.LoadAssetAtPath<UnityEngine.UIElements.PanelSettings>(EdoAssets.App.PanelSettings);
        if (ps == null)
        {
            ps = ScriptableObject.CreateInstance<UnityEngine.UIElements.PanelSettings>();
            AssetDatabase.CreateAsset(ps, EdoAssets.App.PanelSettings);
        }
        ps.themeStyleSheet = AssetDatabase.LoadAssetAtPath<UnityEngine.UIElements.ThemeStyleSheet>(EdoAssets.App.RuntimeTheme);
        ps.scaleMode = UnityEngine.UIElements.PanelScaleMode.ScaleWithScreenSize;
        ps.referenceResolution = new Vector2Int(1920, 1080);
        ps.screenMatchMode = UnityEngine.UIElements.PanelScreenMatchMode.MatchWidthOrHeight;
        ps.match = 0.5f;
        ps.sortingOrder = 100;
        EditorUtility.SetDirty(ps);
        AssetDatabase.SaveAssetIfDirty(ps);
        return ps;
    }

    /// <summary>
    /// 開始画面の背景を撮る — 赤坂を開いた状態で、始まりの位置(SpawnPoint)の目の高さから向きのまま 1920×1080 で撮り
    /// <see cref="EdoAssets.App.TitleImage"/> へ書く。撮り直しはこれを押し直すだけ(次の書き出しで開始画面に入る)。
    /// </summary>
    [MenuItem("Edo/書き出し/開始画面の絵を撮る(赤坂を開いて)", false, 921)]
    public static void RenderTitleImage()
    {
        var sp = GameObject.Find("SpawnPoint");
        if (sp == null || SceneManager.GetActiveScene().path != EdoAssets.Scenes.Akasaka)
        { Debug.LogError("[書き出し] 赤坂を開いてから撮る(SpawnPoint が要る)"); return; }

        const int W = 1920, H = 1080;
        var p = sp.transform.position;
        var terrain = Terrain.activeTerrain;
        float ground = p.y;
        if (Physics.Raycast(p + Vector3.up * 200f, Vector3.down, out var hit, 400f)) ground = hit.point.y;
        else if (terrain != null) ground = terrain.SampleHeight(p) + terrain.transform.position.y;

        var g = new GameObject("TitleShot");
        try
        {
            var cam = g.AddComponent<Camera>();
            g.transform.SetPositionAndRotation(new Vector3(p.x, ground + 1.6f, p.z), Quaternion.Euler(-4f, sp.transform.eulerAngles.y, 0f));
            cam.fieldOfView = 55f;
            cam.nearClipPlane = 0.1f; cam.farClipPlane = 3000f;
            cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(W, H, 24);
            cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt;
            var tx = new Texture2D(W, H, TextureFormat.RGB24, false);
            tx.ReadPixels(new Rect(0, 0, W, H), 0, 0); tx.Apply();
            RenderTexture.active = null; cam.targetTexture = null;
            File.WriteAllBytes(EdoAssets.App.TitleImage, tx.EncodeToJPG(90));
            Object.DestroyImmediate(rt); Object.DestroyImmediate(tx);
        }
        finally { Object.DestroyImmediate(g); }

        AssetDatabase.ImportAsset(EdoAssets.App.TitleImage);
        if (AssetImporter.GetAtPath(EdoAssets.App.TitleImage) is TextureImporter ti)
        {
            ti.textureType = TextureImporterType.Default;
            ti.mipmapEnabled = false;
            ti.maxTextureSize = 2048;
            ti.npotScale = TextureImporterNPOTScale.None;
            ti.SaveAndReimport();
        }
        Debug.Log($"[書き出し] 開始画面の絵を撮った → {EdoAssets.App.TitleImage}");
    }

    public static BuildReport Build(BuildTarget target)
    {
        if (!BuildPipeline.IsBuildTargetSupported(BuildPipeline.GetBuildTargetGroup(target), target))
        {
            Debug.LogError($"[書き出し] {target} の書き出し部品が Unity に入っていない(Unity Hub ▸ インストール ▸ モジュールを加える)");
            return null;
        }
        // ⛔ 開いているシーンに未保存の変更があると、書き出しの前に Unity が「保存しますか」のモーダルを出して
        //   主スレッドが止まる(MCP からは押せない・2026-09-27 に作業場 Koba で踏んだ)。保存するかは持ち主の窓が決めるので、ここでは断る
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            var sc = SceneManager.GetSceneAt(i);
            if (!sc.isDirty) continue;
            Debug.LogError($"[書き出し] 断った: 開いているシーン {sc.path} に未保存の変更がある(持ち主の窓が保存か破棄を決めてから)");
            return null;
        }
        EnsureBootScene();
        SetBuildScenes();
        int app = EnsureAppQuality();

        // アプリだけ App 品質で起きるよう、書き出す間だけ既定の品質を差し替えて戻す(エディタの品質は触らない)
        var qs = new SerializedObject(QualitySettings.GetQualitySettings());
        var plat = BuildPipeline.GetBuildTargetGroup(target) == BuildTargetGroup.Standalone ? "Standalone" : target.ToString();
        int prevDefault = GetPlatformDefault(qs, plat);
        int editorLevel = QualitySettings.GetQualityLevel();
        bool prevRetina = PlayerSettings.macRetinaSupport;
        int prevTex = EditorUserBuildSettings.overrideMaxTextureSize;
        try
        {
            SetPlatformDefault(qs, plat, app);
            // Retina の 4 倍の画素は M1 の GPU に重い。アプリは 1 倍の画素で描き、OS が引き伸ばす
            PlayerSettings.macRetinaSupport = false;
            EditorUserBuildSettings.overrideMaxTextureSize = MaxTextureSize;

            var sub = target == BuildTarget.StandaloneOSX ? "Mac/EdoAkasaka.app" : "Windows/EdoAkasaka.exe";
            var opt = new BuildPlayerOptions
            {
                scenes = BuildScenes,
                target = target,
                locationPathName = Path.Combine(EdoAssets.App.BuildDir, sub),
                options = BuildOptions.None,
            };
            var t0 = System.DateTime.Now;
            var rep = BuildPipeline.BuildPlayer(opt);
            var s = rep.summary;
            Debug.Log($"[書き出し] {target} {s.result} {s.totalSize / 1048576f:F0}MB 誤り{s.totalErrors} " +
                      $"{(System.DateTime.Now - t0).TotalMinutes:F1}分 → {s.outputPath}");
            return rep;
        }
        finally
        {
            SetPlatformDefault(qs, plat, prevDefault);
            PlayerSettings.macRetinaSupport = prevRetina;
            EditorUserBuildSettings.overrideMaxTextureSize = prevTex;
            QualitySettings.SetQualityLevel(editorLevel, false);
        }
    }

    // ── アプリ用の画質 ────────────────────────────────────────────────

    /// <summary>品質 `App` とその URP 資産を(無ければ)起こし、値を毎回そろえる。返り値は App の番号。</summary>
    public static int EnsureAppQuality()
    {
        var rp = EnsureAppPipeline();

        // GPU Resident Drawer は BatchRendererGroup の変種を書き出しに残さないと動かない(プロジェクト設定・書き出しにだけ効く)
        var gs = new SerializedObject(GraphicsSettings.GetGraphicsSettings());
        var brg = gs.FindProperty("m_BrgStripping");
        if (brg != null && brg.intValue != 1) { brg.intValue = 1; gs.ApplyModifiedPropertiesWithoutUndo(); }

        var qs = new SerializedObject(QualitySettings.GetQualitySettings());
        var arr = qs.FindProperty("m_QualitySettings");
        int app = -1, pc = -1;
        for (int i = 0; i < arr.arraySize; i++)
        {
            var n = arr.GetArrayElementAtIndex(i).FindPropertyRelative("name").stringValue;
            if (n == AppLevel) app = i;
            if (n == "PC") pc = i;
        }
        if (app < 0)
        {
            int src = pc >= 0 ? pc : 0;
            arr.InsertArrayElementAtIndex(src);        // src を複写して src+1 に置く
            app = arr.arraySize - 1;
            arr.MoveArrayElement(src + 1, app);
        }
        var e = arr.GetArrayElementAtIndex(app);
        e.FindPropertyRelative("name").stringValue = AppLevel;
        e.FindPropertyRelative("customRenderPipeline").objectReferenceValue = rp;
        e.FindPropertyRelative("lodBias").floatValue = 1f;
        e.FindPropertyRelative("shadowDistance").floatValue = 60f;
        e.FindPropertyRelative("vSyncCount").intValue = 1;
        e.FindPropertyRelative("terrainQualityOverrides").intValue = 0;   // 地形の距離は書き出し時に地形そのものへ書く
        qs.ApplyModifiedPropertiesWithoutUndo();
        return app;
    }

    static UniversalRenderPipelineAsset EnsureAppPipeline()
    {
        var path = EdoAssets.App.RPAsset;
        var rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(path);
        if (rp == null)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            AssetDatabase.CopyAsset(EdoAssets.App.PcRPAsset, path);
            rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(path);
        }
        var so = new SerializedObject(rp);
        void I(string p, int v) { var q = so.FindProperty(p); if (q != null) q.intValue = v; else Debug.LogWarning("[書き出し] 欄が無い " + p); }
        void F(string p, float v) { var q = so.FindProperty(p); if (q != null) q.floatValue = v; else Debug.LogWarning("[書き出し] 欄が無い " + p); }
        void B(string p, bool v) { var q = so.FindProperty(p); if (q != null) q.boolValue = v; else Debug.LogWarning("[書き出し] 欄が無い " + p); }
        I("m_GPUResidentDrawerMode", (int)GPUResidentDrawerMode.InstancedDrawing);
        B("m_GPUResidentDrawerEnableOcclusionCullingInCameras", true);
        F("m_SmallMeshScreenPercentage", SmallMeshScreenPercent);
        I("m_ShadowCascadeCount", 2);
        I("m_SoftShadowQuality", (int)SoftShadowQuality.Low);
        I("m_MainLightShadowmapResolution", 2048);
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(rp);
        AssetDatabase.SaveAssetIfDirty(rp);
        return rp;
    }

    // m_PerPlatformDefaultQuality は map<string,int>。直列化では first/second の配列
    static int GetPlatformDefault(SerializedObject qs, string plat)
    {
        var m = qs.FindProperty("m_PerPlatformDefaultQuality");
        for (int i = 0; i < m.arraySize; i++)
        {
            var e = m.GetArrayElementAtIndex(i);
            if (e.FindPropertyRelative("first").stringValue == plat) return e.FindPropertyRelative("second").intValue;
        }
        return -1;
    }

    static void SetPlatformDefault(SerializedObject qs, string plat, int level)
    {
        qs.Update();
        var m = qs.FindProperty("m_PerPlatformDefaultQuality");
        for (int i = 0; i < m.arraySize; i++)
        {
            var e = m.GetArrayElementAtIndex(i);
            if (e.FindPropertyRelative("first").stringValue != plat) continue;
            if (level < 0) m.DeleteArrayElementAtIndex(i);
            else e.FindPropertyRelative("second").intValue = level;
            qs.ApplyModifiedPropertiesWithoutUndo();
            return;
        }
        if (level < 0) return;
        m.InsertArrayElementAtIndex(m.arraySize);
        var n = m.GetArrayElementAtIndex(m.arraySize - 1);
        n.FindPropertyRelative("first").stringValue = plat;
        n.FindPropertyRelative("second").intValue = level;
        qs.ApplyModifiedPropertiesWithoutUndo();
    }
}

/// <summary>
/// 書き出すときだけ走るシーンの下ごしらえ。**エディタの再生(Play)では走らない**(report が null)。
/// 書き出し用に読み込んだ赤坂の写しに対して走り、赤坂の資産そのものは変えない。
///
/// ⚠ 読み込み単位の分割(屋敷ごとの追加シーン)は入れていない。1軒1プレハブの赤坂は区域の分け目が
///   そのまま屋敷なので、アプリの実測で記憶が足りないと分かったらここで屋敷のルートを追加シーンへ移す。
/// </summary>
class EdoAppSceneStrip : IProcessSceneWithReport
{
    public int callbackOrder => 0;

    public void OnProcessScene(Scene scene, BuildReport report)
    {
        if (report == null) return;                       // エディタの再生
        if (scene.path != EdoAssets.Scenes.Akasaka) return;

        int dropped = 0, inactive = 0;
        foreach (var root in scene.GetRootGameObjects())
        {
            if (System.Array.IndexOf(EdoAssets.App.EditorOnlyRoots, root.name) >= 0)
            { Object.DestroyImmediate(root); dropped++; continue; }
            inactive += DropInactive(root.transform);
        }

        foreach (var t in Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
        {
            if (t.gameObject.scene != scene) continue;
            t.treeDistance = EdoAppBuild.TreeDistance;
            t.treeBillboardDistance = EdoAppBuild.TreeDistance;
            t.treeCrossFadeLength = 10f;
            t.detailObjectDistance = EdoAppBuild.DetailDistance;
            t.heightmapPixelError = EdoAppBuild.HeightmapPixelError;
            t.basemapDistance = EdoAppBuild.BasemapDistance;
        }
        Debug.Log($"[書き出し] 下ごしらえ: 図の置き場 {dropped} 本と非表示の撤去物 {inactive} 塊を外した・地形の遠景を縮めた");
    }

    /// <summary>非表示の塊(撤去物)を外す。動く部品(自作の MonoBehaviour)が下にある塊は、実行時に点く恐れがあるので残す。
    /// ⛔ **プレハブの中の塊は外さない。** 2026-09-27 の初回の書き出しでプレハブの中の非表示 8 塊を消したところ、
    ///   アプリが起動時に赤坂(level0)を読めず「corrupted / Position out of bounds」で落ちた(3 回とも同じ)。
    ///   プレハブの繋がりを残したまま子を消すと、書き出したシーンの中の参照が食い違う疑いが濃い。</summary>
    static int DropInactive(Transform t)
    {
        if (!t.gameObject.activeSelf)
        {
            if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) return 0;
            if (t.GetComponentsInChildren<MonoBehaviour>(true).Length == 0) { Object.DestroyImmediate(t.gameObject); return 1; }
            return 0;
        }
        int n = 0;
        for (int i = t.childCount - 1; i >= 0; i--) n += DropInactive(t.GetChild(i));
        return n;
    }
}

/// <summary>
/// 三角形の多い模型に Mesh LOD(遠くで面を自動で間引く)を付ける。在庫のパックは gitignore で .meta が版に残らないので、
/// 取り込みのたびにここで付け直す。対象は <see cref="EdoAssets.App.MeshLodModels"/>。
/// ⚠ 頂点は変わらない(間引きは添字の列を足すだけ)。駒の面を測るビルダーには効かない。
/// </summary>
class EdoAppMeshLod : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        foreach (var p in EdoAssets.App.MeshLodModels)
        {
            if (!assetPath.StartsWith(p)) continue;
            var mi = (ModelImporter)assetImporter;
            if (!mi.generateMeshLods) mi.generateMeshLods = true;
            return;
        }
    }

    [MenuItem("Edo/書き出し/遠くの面を間引く模型を取り込み直す", false, 921)]
    static void Reimport()
    {
        int n = 0;
        foreach (var g in AssetDatabase.FindAssets("t:Model", new[] { "Assets" }))
        {
            var path = AssetDatabase.GUIDToAssetPath(g);
            foreach (var p in EdoAssets.App.MeshLodModels)
                if (path.StartsWith(p))
                {
                    var mi = AssetImporter.GetAtPath(path) as ModelImporter;
                    if (mi != null && !mi.generateMeshLods) { AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate); n++; }
                    break;
                }
        }
        Debug.Log($"[書き出し] Mesh LOD を付けて取り込み直した模型 {n} 本");
    }
}
