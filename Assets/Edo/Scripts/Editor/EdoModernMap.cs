using UnityEngine;
using UnityEditor;

/// <summary>
/// 現代東京の地図(国土地理院 標準地図)を、古地図オーバーレイと「同一の投影・範囲」で
/// シーンに重ねる参照用ツール。古今の街路・堀・川を見比べるために使う。
///
/// 現代地図PNG(Assets/Edo/ModernMap/modern_center.png)は edo-map の
/// scripts/export_modern_overlay.py が古地図オーバーレイ(export_oldmap_overlay.py)と
/// 厳密に同じ equirectangular 投影・中心(139.74215, 35.67225)・±3000m・row0=north で焼いている。
/// そのため OldMapQuad メッシュ(地理的四隅をワールド座標に変換して配置済み)を
/// そのまま流用でき、古地図とピクセル単位で一致する。
///
/// メニュー: Edo ▸ 地図オーバーレイ ▸ …
///   ・現代地図 表示切替  … 生成(無ければ)＆表示/非表示をトグル
///   ・現代地図 不透明度＋/− … マテリアルの _BaseColor.a を増減
///
/// 古地図オーバーレイ(OldMapOverlay)との Z ファイト回避のため、
/// 現代地図は 2m 上に置く。両方表示しても干渉しない。
/// 高さの基準は OldMapQuad メッシュ側に焼かれている(海抜73m)。
/// </summary>
public static class EdoModernMap
{
    const string ObjName  = "ModernMapOverlay";
    const string MeshPath = "Assets/Edo/OldMap/OldMapQuad.asset";              // 古地図と共有(地理四隅で配置済み)
    const string MatPath  = "Assets/Edo/ModernMap/ModernMapOverlay.mat";
    const float  HeightOffset = 2f;                                            // 古地図(Y=48)より 2m 上

    /// <summary>
    /// 既存のオーバーレイを探す。⚠ <c>GameObject.Find</c> は**非アクティブを見つけない**ので使わない。
    /// 非表示のときにトグルすると「無い」と判定して重複を作る(2026-08-22 に実際に2個できていた)。
    /// </summary>
    static GameObject FindOverlay()
    {
        foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (go.name == ObjName && go.transform.parent == null) return go;
        return null;
    }

    [MenuItem("Edo/地図オーバーレイ/現代地図 表示切替 %#n")]      // Ctrl/Cmd + Shift + N（古地図トグルの %#m と衝突しないよう N）
    static void ToggleOverlay()
    {
        var go = FindOverlay() ?? CreateOverlay();
        if (go == null) return;
        Undo.RecordObject(go, "Toggle Modern Map Overlay");
        bool now = !go.activeSelf;
        go.SetActive(now);
        EditorUtility.SetDirty(go);
        if (now) Selection.activeGameObject = go;
        Debug.Log($"[EdoModernMap] 現代地図オーバーレイ: {(now ? "表示" : "非表示")}");
    }

    [MenuItem("Edo/地図オーバーレイ/現代地図 表示切替 %#n", true)]
    static bool ToggleOverlayValidate()
    {
        Menu.SetChecked("Edo/地図オーバーレイ/現代地図 表示切替 %#n",
            FindOverlay() is GameObject g && g.activeSelf);
        return true;
    }

    [MenuItem("Edo/地図オーバーレイ/現代地図 不透明度＋")]
    static void OpacityUp() => NudgeOpacity(+0.1f);

    [MenuItem("Edo/地図オーバーレイ/現代地図 不透明度−")]
    static void OpacityDown() => NudgeOpacity(-0.1f);

    static GameObject CreateOverlay()
    {
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
        var mat  = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
        if (mesh == null) { Debug.LogError($"[EdoModernMap] メッシュが見つからない: {MeshPath}"); return null; }
        if (mat  == null) { Debug.LogError($"[EdoModernMap] マテリアルが見つからない: {MatPath}(Unity で再インポートが必要かも)"); return null; }

        var go = new GameObject(ObjName);
        Undo.RegisterCreatedObjectUndo(go, "Create Modern Map Overlay");
        go.transform.position = new Vector3(0f, HeightOffset, 0f);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterial = mat;
        mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        mr.receiveShadows = false;
        Debug.Log("[EdoModernMap] 現代地図オーバーレイを作成した(国土地理院 標準地図)。");
        return go;
    }

    static void NudgeOpacity(float delta)
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
        if (mat == null) { Debug.LogError($"[EdoModernMap] マテリアルが見つからない: {MatPath}"); return; }
        Undo.RecordObject(mat, "Modern Map Opacity");
        Color c = mat.HasProperty("_BaseColor") ? mat.GetColor("_BaseColor") : Color.white;
        c.a = Mathf.Clamp01(c.a + delta);
        if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", c);
        if (mat.HasProperty("_Color"))     mat.SetColor("_Color", c);
        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssetIfDirty(mat);
        Debug.Log($"[EdoModernMap] 現代地図の不透明度: {c.a:0.0}");
    }
}
