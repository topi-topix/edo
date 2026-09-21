using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// **コードで起こす無地の材質は、必ず資産にする**(EDO-0301)。
///
/// `new Material(Shader.Find(...))` の戻り値は資産でない。シーンには埋め込めるが、プレハブへ焼くと
/// 資産側の m_Materials が null になり、シーンでは override が効くので気づけないまま、そのプレハブを別の場所へ
/// 置いた途端にマゼンタになる(赤坂のプレハブインスタンス 162 本のうち 74 本が該当した)。
///
/// ここは **色ごとに 1 枚だけ** `Assets/Edo/Materials/Solid/Solid_RRGGBB.mat` を起こして返す。
/// 同じ色は同じ資産を指すので、シーンの材質の数も減る。
/// </summary>
public static class EdoSolidMat
{
    const string LitShader = "Universal Render Pipeline/Lit";

    const float DefaultSmoothness = 0.5f;   // URP/Lit の既定

    /// <summary>この色の無地の材質資産。無ければ起こす。⚠ 8bit に丸めた色で 1 枚(0.55 と 0.551 は同じ物)。
    /// 光沢が既定(0.5)でないときは別の 1 枚(`Solid_RRGGBB_s08` = 0.08)。</summary>
    public static Material Get(Color c, float smoothness = DefaultSmoothness)
    {
        string hex = ColorUtility.ToHtmlStringRGB(c);
        if (Mathf.Abs(smoothness - DefaultSmoothness) > 0.004f)
            hex += "_s" + Mathf.RoundToInt(smoothness * 100f).ToString("00");
        string path = EdoAssets.Own.SolidMat(hex);
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m != null) return m;

        var sh = Shader.Find(LitShader);
        if (sh == null) { Debug.LogError("EdoSolidMat: シェーダ " + LitShader + " が見つからない"); return null; }
        m = new Material(sh) { color = c };
        if (Mathf.Abs(smoothness - DefaultSmoothness) > 0.004f) m.SetFloat("_Smoothness", smoothness);
        EnsureFolder(EdoAssets.Own.SolidMatDir);
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    /// <summary>名前つきの材質資産を返す(無ければ既定値で起こす)。`init` は**起こしたときだけ**走る —
    /// 既存の資産を毎回上書きしない(手で直した色を戻さない)。</summary>
    public static Material Named(string name, System.Action<Material> init)
    {
        string path = EdoAssets.Own.Mat(name);
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m != null) return m;
        var sh = Shader.Find(LitShader);
        if (sh == null) { Debug.LogError("EdoSolidMat: シェーダ " + LitShader + " が見つからない"); return null; }
        m = new Material(sh);
        init?.Invoke(m);
        EnsureFolder(Path.GetDirectoryName(path).Replace('\\', '/'));
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    static void EnsureFolder(string folder)
    {
        if (AssetDatabase.IsValidFolder(folder)) return;
        string parent = Path.GetDirectoryName(folder).Replace('\\', '/');
        EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
    }

    // ───────────────────── 既存シーンの「資産でない材質」を直す ─────────────────────

    /// <summary>資産でない(=シーンにしか居ない)無地の URP/Lit か。テクスチャ・金属・他のシェーダは対象外。</summary>
    static bool IsLooseSolid(Material m, out Color color, out float smoothness)
    {
        color = Color.white; smoothness = DefaultSmoothness;
        if (m == null || !string.IsNullOrEmpty(AssetDatabase.GetAssetPath(m))) return false;
        if (m.shader == null || m.shader.name != LitShader) return false;
        if (m.mainTexture != null || m.HasFloat("_Metallic") && m.GetFloat("_Metallic") > 0.001f) return false;
        color = m.GetColor("_BaseColor");
        if (m.HasFloat("_Smoothness")) smoothness = m.GetFloat("_Smoothness");
        return true;
    }

    /// <summary>資産でない材質が何枚・どのルートに居るか(検査。書き換えない)。
    /// `Edo/屋敷/切り出し状況を検査` がこれを 1 行で出す — 0 になっていれば直っている。</summary>
    public static string CountLoose(UnityEngine.SceneManagement.Scene scene)
    {
        var mats = new System.Collections.Generic.HashSet<Material>();
        var roots = new System.Collections.Generic.HashSet<string>();
        int slots = 0, other = 0;
        foreach (var r in scene.GetRootGameObjects())
            foreach (var rd in r.GetComponentsInChildren<Renderer>(true))
                foreach (var m in rd.sharedMaterials)
                {
                    if (m == null || !string.IsNullOrEmpty(AssetDatabase.GetAssetPath(m))) continue;
                    if (m.hideFlags != HideFlags.None) continue;          // 効果用の一時材質(UnderwaterEffect)は対象外
                    if (IsLooseSolid(m, out _, out _)) { mats.Add(m); slots++; roots.Add(r.name); }
                    else other++;
                }
        return $"資産でない無地の材質={mats.Count} 枚({slots} 枠・{roots.Count} ルート)  無地でない資産外の材質={other} 枠";
    }

    [MenuItem("Edo/屋敷/埋め込み材質を資産へ(検査)")]
    public static void CountLooseMenu()
    {
        Debug.Log("[EdoSolidMat] " + CountLoose(UnityEngine.SceneManagement.SceneManager.GetActiveScene()));
    }

    /// <summary>
    /// シーンの「資産でない無地の材質」を、同じ色の <see cref="Get"/> の資産へ付け替え、
    /// **プレハブ資産の側へも焼く**(EDO-0301)。付け替えるだけではシーンの override が資産の参照に変わるだけで、
    /// プレハブ資産側は null のまま — そのプレハブを別の場所へ置くとマゼンタになる。
    ///
    /// 焼き方: 付け替えた枠の**最寄りのプレハブインスタンス**ごとに
    /// <see cref="EdoYashikiPrefab.BakeAssetSwaps"/> で資産へ書く(内側から・資産への差し替えだけ)。
    /// ⛔ 位置の手直しなど**差し替え以外の override** があるインスタンスは焼かない — 名指しで残す。
    /// ⛔ **メッシュが資産でないインスタンスも焼かない** — 焼くと資産側の m_Mesh が null になる。
    ///    先に `Edo/屋敷/埋め込みメッシュを資産へ` を通すこと(EDO-0332)。
    /// <paramref name="onlyRoots"/> を渡すとそのルートだけ(試験用)。null なら全ルート。
    /// </summary>
    public static string Migrate(UnityEngine.SceneManagement.Scene scene,
                                 System.Collections.Generic.ICollection<string> onlyRoots = null)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        int slots = 0, rootsHit = 0;
        var made0 = 0;
        var instances = new System.Collections.Generic.HashSet<GameObject>();
        var plain = new System.Collections.Generic.HashSet<string>();     // プレハブでないルート(焼く先が無い)
        var kitOnly = new System.Collections.Generic.HashSet<string>();   // 焼く先が邸のプレハブの外(部品の資産)しか無いルート

        // ⛔ StartAssetEditing で囲まない — 中で起こした資産は Load できず、同じ色を二重に起こしてしまう
        {
            foreach (var root in scene.GetRootGameObjects())
            {
                if (onlyRoots != null && !onlyRoots.Contains(root.name)) continue;
                bool hit = false;
                foreach (var rd in root.GetComponentsInChildren<Renderer>(true))
                {
                    var arr = rd.sharedMaterials;
                    SerializedObject so = null;
                    for (int i = 0; i < arr.Length; i++)
                    {
                        if (!IsLooseSolid(arr[i], out var col, out var sm) || arr[i].hideFlags != HideFlags.None) continue;
                        var asset = Get(col, sm);
                        if (asset == null) continue;
                        if (so == null) so = new SerializedObject(rd);
                        so.FindProperty("m_Materials.Array.data[" + i + "]").objectReferenceValue = asset;
                        slots++; hit = true;
                    }
                    if (so == null) continue;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    var near = EdoYashikiPrefab.BakeTargetFor(rd);
                    if (near != null) instances.Add(near);
                    else if (!PrefabUtility.IsPartOfPrefabInstance(rd)) plain.Add(root.name);
                    else kitOnly.Add(root.name);
                }
                if (hit) rootsHit++;
            }
        }
        AssetDatabase.SaveAssets();
        made0 = AssetDatabase.FindAssets("t:Material", new[] { EdoAssets.Own.SolidMatDir }).Length;

        // 焼くのは EdoYashikiPrefab.BakeAssetSwaps(内側から・資産を指す差し替えだけ)。
        // ⛔ メッシュが資産でないインスタンスはここで断られる(EDO-0332)— 焼くと資産側の m_Mesh が null になる。
        int baked; string refused = EdoYashikiPrefab.BakeAssetSwaps(instances, out baked);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
        return $"付け替え {slots} 枠 / {rootsHit} ルート / 材質資産 {made0} 枚 / 焼いたインスタンス {baked}/{instances.Count}"
             + (kitOnly.Count > 0 ? $" / ⛔ 焼く先が邸のプレハブの外 {kitOnly.Count}({string.Join(",", kitOnly)})" : "")
             + (plain.Count > 0 ? $" / プレハブでないルート {plain.Count}({string.Join(",", plain)})" : "")
             + (refused.Length > 0 ? "\n⛔ 焼かなかった: " + refused : "")
             + $"  ms={sw.ElapsedMilliseconds}";
    }

    [MenuItem("Edo/屋敷/埋め込み材質を資産へ(選択中のルートだけ)")]
    public static void MigrateSelectedMenu()
    {
        var names = new System.Collections.Generic.HashSet<string>();
        foreach (var o in Selection.gameObjects) names.Add(o.transform.root.name);
        if (names.Count == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log("[EdoSolidMat] " + Migrate(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), names));
    }

    [MenuItem("Edo/屋敷/埋め込み材質を資産へ(全ルート)")]
    public static void MigrateAllMenu()
    {
        Debug.Log("[EdoSolidMat] " + Migrate(UnityEngine.SceneManagement.SceneManager.GetActiveScene()));
    }
}
