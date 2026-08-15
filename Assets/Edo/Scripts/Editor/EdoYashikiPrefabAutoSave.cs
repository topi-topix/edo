using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// シーンを保存する直前に、切り出し済みのルートを自動でプレハブへ書き戻す。
///
/// なぜ自動でやるか: ビルダーは `Group()` 経由で対象ルートを自動的に「解く」(EnsureEditable)。
/// 解いたままシーンを保存すると、屋敷の中身がまたシーンに直接書き込まれてしまい、
/// せっかく分けた意味が無くなる。人が毎回「書き戻す」を覚えている前提にはしない。
///
/// 手で `Overrides ▾ > Apply All` を押すのと同じことを、保存のたびに全ルートに対してやる。
/// ⚠ `Revert All` は押さないこと。書き戻す前の手直しが消える。
/// </summary>
[InitializeOnLoad]
public static class EdoYashikiPrefabAutoSave
{
    /// <summary>再入防止。書き戻しの中で SaveAssets が走るため。</summary>
    static bool _busy;

    /// <summary>切りたいときは Edo メニューから。既定は on。</summary>
    const string PrefKey = "Edo.PrefabAutoSave";
    public static bool Enabled
    {
        get { return EditorPrefs.GetBool(PrefKey, true); }
        set { EditorPrefs.SetBool(PrefKey, value); }
    }

    static EdoYashikiPrefabAutoSave()
    {
        EditorSceneManager.sceneSaving -= OnSaving;
        EditorSceneManager.sceneSaving += OnSaving;
    }

    static void OnSaving(UnityEngine.SceneManagement.Scene scene, string path)
    {
        if (!Enabled || _busy) return;
        _busy = true;
        try
        {
            var msg = EdoYashikiPrefab.WriteBackAll();
            if (!msg.StartsWith("書き戻す")) Debug.Log("[保存時の自動書き戻し] " + msg);
        }
        catch (System.Exception e) { Debug.LogError("[保存時の自動書き戻し] 失敗: " + e); }
        finally { _busy = false; }
    }

    [MenuItem("Edo/屋敷/保存時の自動書き戻しを切り替える")]
    static void Toggle()
    {
        Enabled = !Enabled;
        Debug.Log("保存時の自動書き戻し = " + (Enabled ? "ON" : "OFF"));
    }

    [MenuItem("Edo/屋敷/保存時の自動書き戻しを切り替える", true)]
    static bool ToggleValidate() { Menu.SetChecked("Edo/屋敷/保存時の自動書き戻しを切り替える", Enabled); return true; }
}
