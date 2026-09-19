using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// 作業場 — C# を直している間、赤坂を丸ごと載せないための軽いシーン。
///
/// なぜ: スクリプトを1行直すたびに Unity はドメインを作り直し、**開いているシーンを
/// まるごと退避して復元する**。赤坂は 83 プレハブ(松江松平 47MB・岡部 35MB ほか)が
/// 載っているので、この復元だけで 30 秒かかる。
///
/// 実測 2026-09-19(`Logs/Editor.log`・同じ 138 アセンブリ・同じ1行の変更):
///
///     ドメイン再読み込み合計          赤坂を開いたまま 53.4s → 空のシーン 12.9s
///     └ AwakeInstancesAfterBackupRestoration   30.9s → 0.7s   ← 差の主因
///     コンパイル(Csc)                            6s  →  4s
///
/// つまり遅さの正体はコンパイルではなく**シーンの復元**なので、
/// C# を回している間だけ一邸に減らす。
///
/// ★ 屋敷の実体は `Assets/Edo/Prefabs/Scene/*.prefab` 側にある(EdoYashikiPrefab)。
///   作業場で建てて保存すれば EdoYashikiPrefabAutoSave がプレハブへ書き戻すので、
///   **赤坂は次に開いたとき自動で追従する**。作業場から赤坂へ手で写す作業は要らない。
///
/// ⛔ **隣接との取り合い・区域侵犯・検証レンダは作業場では見えない。**
///   作業場で建て、最後に `赤坂へ戻す` で検める。この切り分けを崩さないこと。
///
/// ⛔ 地形は赤坂と**同じ** `ModernTerrain.asset` を指す(複製しない・作り直さない)。
///   作業場で造成を流すと赤坂の地形もそのまま変わる — それが正しい(地形は一枚きり)。
///   触る前の heightmap の退避は赤坂で作業するときと同じに要る(`.claude/rules/unity.md`)。
///
/// ⚠ どの入口も**未保存の変更があれば断る**。Unity の「保存しますか」モーダルは
///   エディタの主スレッドを止め、MCP の呼び出しが軒並みタイムアウトする
///   (2026-09-19 に実測・`Command TCS timed out` が延々と出る)。黙って止まるより断る。
/// </summary>
public static class EdoKoba
{
    /// <summary>作業場に持ち込むシーン常駐物。EdoYashikiPrefab.KeepInScene のうち、
    /// ビルダーが建てるのに実際に要る物だけ(地形・光・カメラ)。</summary>
    static readonly string[] Bring = { "ModernTerrain", "Directional Light", "Main Camera" };

    // ---- 仕立てる ----------------------------------------------------------

    [MenuItem("Edo/普請/作業場を仕立てる(赤坂から)", false, 300)]
    public static void ShitateruMenu() { Debug.Log(Shitateru()); }

    /// <summary>赤坂から地形・光・カメラを写して作業場シーンを起こす。赤坂は変えない。</summary>
    public static string Shitateru()
    {
        var cur = EditorSceneManager.GetActiveScene();
        if (cur.path != EdoAssets.Scenes.Akasaka)
            return "⛔ 赤坂を開いた状態で実行すること(いまは '" + cur.path + "')";
        if (cur.isDirty)
            return "⛔ 赤坂に未保存の変更がある。保存してから実行すること";

        var byName = new Dictionary<string, GameObject>();
        foreach (var r in cur.GetRootGameObjects()) byName[r.name] = r;

        var koba = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
        var got = new List<string>();
        foreach (var nm in Bring)
        {
            if (!byName.TryGetValue(nm, out var src)) { got.Add(nm + "=無い"); continue; }
            var copy = Object.Instantiate(src);
            copy.name = nm;
            SceneManager.MoveGameObjectToScene(copy, koba);
            got.Add(nm + "=写した");
        }

        EditorSceneManager.SaveScene(koba, EdoAssets.Scenes.Koba);
        EditorSceneManager.CloseScene(koba, true);
        return "作業場を仕立てた: " + EdoAssets.Scenes.Koba + "\n  " + string.Join(" / ", got);
    }

    // ---- 開く --------------------------------------------------------------

    [MenuItem("Edo/普請/作業場を開く(選択中のプレハブ)", false, 301)]
    public static void OpenSelectedMenu()
    {
        var o = Selection.activeObject;
        var path = o == null ? null : AssetDatabase.GetAssetPath(o);
        if (string.IsNullOrEmpty(path) || !path.StartsWith(EdoYashikiPrefab.Dir))
        {
            Debug.LogWarning("Project ウィンドウで " + EdoYashikiPrefab.Dir + " の .prefab を選んでから実行してください");
            return;
        }
        Debug.Log(Open(Path.GetFileNameWithoutExtension(path)));
    }

    /// <summary>作業場を開き、屋敷を1軒だけ載せる。<paramref name="yashiki"/> は
    /// プレハブの名前(拡張子なし・例 "Edo_Yashiki_MatsudairaDewa")。空なら地形だけ。</summary>
    public static string Open(string yashiki)
    {
        var cur = EditorSceneManager.GetActiveScene();
        if (cur.isDirty)
            return "⛔ いまのシーン '" + cur.name + "' に未保存の変更がある。保存してから呼ぶこと";
        if (!File.Exists(EdoAssets.Scenes.Koba))
            return "⛔ 作業場が無い。赤坂を開いて Edo/普請/作業場を仕立てる を先に実行すること";

        var koba = EditorSceneManager.OpenScene(EdoAssets.Scenes.Koba, OpenSceneMode.Single);

        // ⚠ **冪等にする。** MCP がタイムアウトすると同じ呼び出しが再送され、
        //   素直に実体化するだけだと屋敷が何重にも積まれる(2026-09-19 に6重を実測)。
        //   前回の屋敷を片付ける役も兼ねる — 作業場に載るのは常に一邸。
        int swept = 0;
        var bring = new HashSet<string>(Bring);
        foreach (var r in koba.GetRootGameObjects())
        {
            if (bring.Contains(r.name)) continue;
            Object.DestroyImmediate(r);
            swept++;
        }

        if (string.IsNullOrEmpty(yashiki))
        {
            if (swept > 0) EditorSceneManager.SaveScene(koba);
            return "作業場を開いた(屋敷なし・地形だけ" + (swept > 0 ? "・前の屋敷 " + swept + " 件を片付けた" : "") + ")";
        }

        string path = EdoYashikiPrefab.Dir + "/" + yashiki + ".prefab";
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (asset == null) return "⛔ プレハブが無い: " + path;

        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        go.name = yashiki;
        Selection.activeGameObject = go;

        // 載せた状態で保存しておく。次に切り替えるときモーダルが出ないため。
        EditorSceneManager.SaveScene(koba);
        return "作業場: " + yashiki + " を載せた(" + go.GetComponentsInChildren<Transform>(true).Length + " transform"
             + (swept > 0 ? "・前の屋敷 " + swept + " 件を片付けた" : "") + ")";
    }

    // ---- 戻す --------------------------------------------------------------

    [MenuItem("Edo/普請/赤坂へ戻す", false, 302)]
    public static void BackToAkasakaMenu() { Debug.Log(BackToAkasaka()); }

    /// <summary>赤坂へ戻す。取り合い・境界・検証レンダはここでしか見られない。</summary>
    public static string BackToAkasaka()
    {
        var cur = EditorSceneManager.GetActiveScene();
        if (cur.isDirty)
            return "⛔ いまのシーン '" + cur.name + "' に未保存の変更がある。保存してから戻すこと";
        EditorSceneManager.OpenScene(EdoAssets.Scenes.Akasaka, OpenSceneMode.Single);
        return "赤坂へ戻した";
    }
}
