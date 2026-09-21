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
    /// 焼き方: 付け替えた枠の**最寄りのプレハブインスタンス**ごとに、材質の override だけを
    /// <c>ApplyPrefabInstance</c> で資産へ書く。入れ子は**内側から**(段 → ルート)。
    /// ⛔ 材質以外の override(位置の手直しなど)があるインスタンスは**焼かない** — 名指しで残す。
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
                    var near = BakeTarget(rd);
                    if (near != null) instances.Add(near);
                    else if (!PrefabUtility.IsPartOfPrefabInstance(rd)) plain.Add(root.name);
                    else kitOnly.Add(root.name);
                }
                if (hit) rootsHit++;
            }
        }
        AssetDatabase.SaveAssets();
        made0 = AssetDatabase.FindAssets("t:Material", new[] { EdoAssets.Own.SolidMatDir }).Length;

        // 内側(深い)インスタンスから焼く。浅い側の override は、内側が焼けると消える。
        var order = new System.Collections.Generic.List<GameObject>(instances);
        order.Sort((a, b) => Depth(b.transform).CompareTo(Depth(a.transform)));
        int baked = 0; var refused = new System.Collections.Generic.List<string>();
        foreach (var inst in order)
        {
            if (inst == null) continue;
            // ⛔ 焼く前に「材質だけ」を確かめる。⚠ GetObjectOverrides(inst, true) は名前・位置の**既定の override**
            //   まで数えるので、これで判定すると全ルートが断られる(2026-09-21 実測: 1 枠のルートで 3 件)。
            string why = NotOnlyMaterials(inst);
            if (why != null) { refused.Add(inst.name + "(" + why + ")"); continue; }
            PrefabUtility.ApplyPrefabInstance(inst, InteractionMode.AutomatedAction);
            baked++;
        }
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
        return $"付け替え {slots} 枠 / {rootsHit} ルート / 材質資産 {made0} 枚 / 焼いたインスタンス {baked}/{order.Count}"
             + (kitOnly.Count > 0 ? $" / ⛔ 焼く先が邸のプレハブの外 {kitOnly.Count}({string.Join(",", kitOnly)})" : "")
             + (plain.Count > 0 ? $" / プレハブでないルート {plain.Count}({string.Join(",", plain)})" : "")
             + (refused.Count > 0 ? "\n⛔ 焼かなかった: " + string.Join(", ", refused) : "")
             + $"  ms={sw.ElapsedMilliseconds}";
    }

    /// <summary>この枠の材質を**焼いてよい**プレハブインスタンス。内側から外へ辿り、資産が
    /// <see cref="EdoYashikiPrefab.Dir"/> の下(赤坂の邸・段のプレハブ)にある最初の物。
    /// ⛔ **部品(キット・木・門など)の資産へは焼かない。** 部品のインスタンスへの材質の差し替えは
    ///   「その邸のその場所だけ」の override で、部品の資産へ焼くと**同じ部品を使う全部の場所**の色が変わる。
    ///   外側の邸のプレハブへ焼けば、入れ子の変更としてそこに残る。無ければ null。</summary>
    static GameObject BakeTarget(Component c)
    {
        var g = c.gameObject;
        while (g != null)
        {
            var inst = PrefabUtility.GetNearestPrefabInstanceRoot(g);
            if (inst == null) return null;
            var src = PrefabUtility.GetCorrespondingObjectFromSource(inst);
            var path = src != null ? AssetDatabase.GetAssetPath(src) : "";
            if (path.StartsWith(EdoYashikiPrefab.Dir + "/")) return inst;
            g = inst.transform.parent != null ? inst.transform.parent.gameObject : null;
        }
        return null;
    }

    /// <summary>このインスタンスの override が「レンダラーの m_Materials だけ」か。違えば理由を返す(焼いてよければ null)。
    /// ルート自身の名前・位置・回転は既定の override なので許す(ApplyPrefabInstance も資産へは書かない)。</summary>
    static string NotOnlyMaterials(GameObject inst)
    {
        if (PrefabUtility.GetAddedGameObjects(inst).Count + PrefabUtility.GetRemovedGameObjects(inst).Count > 0)
            return "構造の手直しあり";
        if (PrefabUtility.GetAddedComponents(inst).Count + PrefabUtility.GetRemovedComponents(inst).Count > 0)
            return "部品の増減あり";
        var srcRoot = PrefabUtility.GetCorrespondingObjectFromSource(inst);
        foreach (var mod in PrefabUtility.GetPropertyModifications(inst))
        {
            var t = mod.target;
            if (t is Renderer) { if (!mod.propertyPath.StartsWith("m_Materials")) return "材質以外の override: " + mod.propertyPath; }
            else if (srcRoot != null && (t == srcRoot || t == srcRoot.transform)) { /* ルートの名前・位置・回転 */ }
            else if (t != null) return "レンダラー以外の override: " + t.GetType().Name + "." + mod.propertyPath;
        }
        return null;
    }

    static int Depth(Transform t) { int d = 0; for (; t != null; t = t.parent) d++; return d; }

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
