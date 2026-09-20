using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// シーンを保存する直前に、**この巡で触ったルートだけ**をプレハブへ書き戻す。
///
/// なぜ自動でやるか: ビルダーは Group() 経由で対象ルートを自動的に「解く」(EnsureEditable)。
/// 解いたままシーンを保存すると、屋敷の中身がまたシーンに直接書き込まれてしまい、
/// せっかく分けた意味が無くなる。人が毎回「書き戻す」を覚えている前提にはしない。
///
/// ⚠ Revert All は押さないこと。書き戻す前の手直しが消える。
///
/// ★ 2026-09-21(EDO-0282②)で範囲を絞った。以前は全ルートを舐めていたので、
///   1回の保存で 83 本中 74 本・128MB を書き直し、git 上で実際に変わったのは 1 本だった。
///
/// ★ markDirty: false を渡すのが肝。以前は書き戻しの最後に MarkAllScenesDirty() を
///   呼んでいたが、ここは sceneSaving の**最中**なので、保存し終えたシーンが即 dirty へ戻り、
///   開いている別シーンまで dirty になっていた(Unity の保存モーダルが出ると MCP が全滅する)。
///   書き戻しでルートが PrefabInstance 参照1本に化けるのは、いま走っている保存にそのまま乗る。
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
        EditorSceneManager.sceneOpened -= OnOpened;
        EditorSceneManager.sceneOpened += OnOpened;
    }

    static void OnSaving(UnityEngine.SceneManagement.Scene scene, string path)
    {
        if (!Enabled || _busy) return;
        _busy = true;
        try
        {
            var msg = EdoYashikiPrefab.WriteBack(scene, EdoYashikiPrefab.WriteBackScope.Touched, false);
            if (!msg.StartsWith("書き戻す")) Debug.Log("[保存時の自動書き戻し] " + msg);
        }
        catch (System.Exception e) { Debug.LogError("[保存時の自動書き戻し] 失敗: " + e); }
        finally { _busy = false; }
    }

    /// <summary>
    /// シーンを開いた直後にも「解けたまま」を検める。
    /// ★ 台帳は SessionState なので**エディタを再起動すると消える**。
    ///   前の起動で解けたまま保存された邸を拾えるのは、この網だけ。
    /// 費用はルート数 × File.Exists なので無視できる。
    /// </summary>
    static void OnOpened(UnityEngine.SceneManagement.Scene scene, OpenSceneMode mode)
    {
        if (!Enabled) return;
        try
        {
            var loose = EdoYashikiPrefab.UnwrittenIn(scene);
            if (loose.Count > 0)
                Debug.LogWarning($"⚠ [EdoWriteBack] 書き戻されていないルートが {loose.Count} 件:\n"
                    + "   " + string.Join(", ", loose)
                    + "\n   自分のものなら Edo/屋敷/プレハブへ書き戻す(選択中)。"
                    + "\n   ⭐ 中身はシーンが持っているので消えてはいない(シーンが太るだけ)。");
        }
        catch (System.Exception e) { Debug.LogError("[解けたままの検め] 失敗: " + e); }
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
