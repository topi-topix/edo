using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// シーンのルート(屋敷・町・寺社など)を1つずつ .prefab 資産に切り出し、
/// シーンには参照だけを残すための道具。
///
/// なぜ: LFS はファイルをバージョンごと丸ごと保存するので、
/// **1回のコミットで書き換わるファイルの大きさ**がそのまま保存量になる。
/// 全部が1枚のシーンに載っていると、どこを直しても全量が乗る。
/// 屋敷1軒＝1ファイルにすれば、直した屋敷のファイルだけが動く。
/// 屋敷が何軒に増えても1回のコミットは「その1軒分」で頭打ちになる。
///
/// ★★ ビルダーを走らせる前に「編集のために解く」、走らせた後に「プレハブへ書き戻す」。
///   Unity はプレハブインスタンスの**組み替え**(子の付け替え・プレハブ由来の子の削除)を
///   禁止しており、しかも**例外を投げずコンソールにエラーを出して黙って無視する**。
///   2026-08-16 に実測: `Setting the parent of a transform which resides in a Prefab
///   instance is not possible` が出て、Stage3_Retire のような処理が無言で失敗する。
///   解かずに走らせると「動いたように見えて何も起きていない」状態になる。
///
/// ★ 子を「足す」だけなら解かなくても動く(追加は override として通る)が、
///   走らせた後の「書き戻す」は必要。しないと変更がシーン側に積まれて元の木阿弥になる。
/// </summary>
public static class EdoYashikiPrefab
{
    public const string Dir = "Assets/Edo/Prefabs/Scene";

    /// <summary>シーンに置いたままにするルート(地形・水・プレイヤー・オーバーレイ等)。</summary>
    static readonly HashSet<string> KeepInScene = new HashSet<string>{
        "ModernTerrain", "Water", "Player", "SpawnPoint", "GeoAnchors", "Directional Light",
        "PostVolume", "OldMapOverlay", "ModernMapOverlay", "Castle_Standin",
        "TempFences", "TempLineup", "Main Camera",
    };

    /// <summary>これ未満の小さなルートは切り出しても意味がないので置いたまま。</summary>
    const int MinTransforms = 50;

    static string PathFor(string rootName)
    {
        var safe = rootName;
        foreach (var c in Path.GetInvalidFileNameChars()) safe = safe.Replace(c, '_');
        return Dir + "/" + safe + ".prefab";
    }

    public static bool ShouldConvert(GameObject go)
    {
        if (KeepInScene.Contains(go.name)) return false;
        return go.GetComponentsInChildren<Transform>(true).Length >= MinTransforms;
    }

    /// <summary>
    /// ビルダーが触る直前に呼ぶ。プレハブインスタンスなら解いて普通のオブジェクトに戻す。
    /// **全ビルダーの Group() の冒頭から呼ばれている** — ここが唯一の共通の通り道なので、
    /// ステージ関数を個別に叩いても必ず通る。
    /// 解かないと子の付け替え・削除が例外を投げずに黙って失敗する(クラス冒頭の ★★)。
    /// 保存時に EdoYashikiPrefabAutoSave が自動で書き戻すので、解きっぱなしでよい。
    /// </summary>
    public static void EnsureEditable(GameObject root)
    {
        if (root == null) return;
        if (!PrefabUtility.IsAnyPrefabInstanceRoot(root)) return;
        PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
    }

    /// <summary>1ルートをプレハブへ書き出して接続する。既にプレハブでも上書きして override を畳む。</summary>
    public static string One(GameObject go)
    {
        if (go == null) return "null";
        Directory.CreateDirectory(Dir);
        string path = PathFor(go.name);
        int n = go.GetComponentsInChildren<Transform>(true).Length;
        var pf = PrefabUtility.SaveAsPrefabAssetAndConnect(go, path, InteractionMode.AutomatedAction);
        return $"{go.name}\t{n}\t{(pf != null ? "OK" : "失敗")}";
    }

    /// <summary>名前を指定して切り出す（大量にあるので分割実行できるようにしてある）。</summary>
    public static string Convert(IEnumerable<string> rootNames)
    {
        var sb = new System.Text.StringBuilder();
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var byName = new Dictionary<string, GameObject>();
        foreach (var r in scene.GetRootGameObjects()) byName[r.name] = r;
        foreach (var nm in rootNames)
        {
            if (!byName.TryGetValue(nm, out var go)) { sb.AppendLine($"{nm}\t-\t見つからない"); continue; }
            sb.AppendLine(One(go));
        }
        return sb.ToString();
    }

    /// <summary>
    /// ビルダーを走らせる前に、対象のプレハブインスタンスを解いて普通のオブジェクトに戻す。
    /// 解かないと子の付け替え・削除が黙って失敗する(クラス冒頭の ★★ を読むこと)。
    /// </summary>
    public static string Unpack(IEnumerable<string> rootNames)
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var byName = new Dictionary<string, GameObject>();
        foreach (var r in scene.GetRootGameObjects()) byName[r.name] = r;
        var sb = new System.Text.StringBuilder();
        foreach (var nm in rootNames)
        {
            if (!byName.TryGetValue(nm, out var go)) { sb.AppendLine($"{nm}\t見つからない"); continue; }
            if (!PrefabUtility.IsAnyPrefabInstanceRoot(go)) { sb.AppendLine($"{nm}\t既に解けている"); continue; }
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            sb.AppendLine($"{nm}\t解いた");
        }
        return sb.ToString();
    }

    [MenuItem("Edo/屋敷/編集のためにプレハブを解く(選択中)")]
    public static void UnpackSelectedMenu()
    {
        var names = new List<string>();
        foreach (var o in Selection.gameObjects) names.Add(o.name);
        if (names.Count == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log(Unpack(names));
    }

    [MenuItem("Edo/屋敷/プレハブへ書き戻す(全部)")]
    public static void WriteBackAllMenu() { Debug.Log(WriteBackAll()); }

    /// <summary>
    /// プレハブ化済みのルートすべてを、今のシーンの状態でプレハブへ書き戻す。
    /// ビルダーを走らせた後に実行する。override が畳まれてシーンが元の大きさに戻る。
    /// </summary>
    public static string WriteBackAll()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var sb = new System.Text.StringBuilder();
        int n = 0;
        foreach (var r in scene.GetRootGameObjects())
        {
            bool isPf = PrefabUtility.IsAnyPrefabInstanceRoot(r);
            // 解いたまま(プレハブ資産はあるがインスタンスでない)のものも書き戻す
            bool wasPf = !isPf && File.Exists(PathFor(r.name));
            if (!isPf && !wasPf) continue;
            int mods = isPf ? PrefabUtility.GetObjectOverrides(r).Count
                            + PrefabUtility.GetAddedGameObjects(r).Count
                            + PrefabUtility.GetRemovedGameObjects(r).Count : -1;
            if (isPf && mods == 0) continue;
            sb.AppendLine(One(r) + (wasPf ? "\t(解けていたので繋ぎ直し)" : $"\t(override {mods})"));
            n++;
        }
        if (n > 0) UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
        return n == 0 ? "書き戻す変更はありません" : $"{n}件を書き戻しました\n{sb}";
    }

    [MenuItem("Edo/屋敷/切り出し状況を検査")]
    public static void StatusMenu() { Debug.Log(Status()); }

    public static string Status()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var sb = new System.Text.StringBuilder("root\ttransform\t状態\toverride\n");
        int conv = 0, left = 0, keep = 0;
        foreach (var r in scene.GetRootGameObjects())
        {
            int n = r.GetComponentsInChildren<Transform>(true).Length;
            if (KeepInScene.Contains(r.name)) { keep++; continue; }
            bool isPf = PrefabUtility.IsAnyPrefabInstanceRoot(r);
            if (isPf) conv++; else if (n >= MinTransforms) left++;
            int mods = isPf ? PrefabUtility.GetObjectOverrides(r).Count
                            + PrefabUtility.GetAddedGameObjects(r).Count
                            + PrefabUtility.GetRemovedGameObjects(r).Count : 0;
            if (isPf || n >= MinTransforms)
                sb.AppendLine($"{r.name}\t{n}\t{(isPf ? "プレハブ" : "シーン直")}\t{mods}");
        }
        sb.AppendLine($"\nプレハブ化済={conv}  未変換(>= {MinTransforms})={left}  シーンに残す={keep}");
        return sb.ToString();
    }
}
