using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// WaterBody の掘り込みスナップショット(snap)を、シーンの中ではなく
/// 外部のバイナリファイル(.bytes)に置くための保管係。
///
/// なぜ: 2026-08-15 時点で snap がシーンに直接埋まっており、池5個・646,481個の float で
/// **9.4 MB＝シーンファイルの9%** を占めていた。YAML は float 1個を約13バイトの文字列に
/// するため。バイナリなら4バイト。
///
/// ★ snap を書き換えたら必ず Save(wb) を呼ぶこと。呼ばないとドメインリロード
///   (スクリプト再コンパイル)で消える — snap はシリアライズされないキャッシュなので。
/// </summary>
public static class WaterSnapStore
{
    public const string Dir = "Assets/Edo/Water/snap";

    static string PathFor(WaterBody wb)
    {
        var safe = wb.name;
        foreach (var c in Path.GetInvalidFileNameChars()) safe = safe.Replace(c, '_');
        return Dir + "/" + safe + ".bytes";
    }

    /// <summary>snap をバイナリへ書き出し、wb.snapFile に繋ぐ。</summary>
    public static void Save(WaterBody wb)
    {
        if (wb == null) return;
        var s = wb.snap;
        if (s == null || s.Length == 0) return;

        Directory.CreateDirectory(Dir);
        string path = PathFor(wb);
        var bytes = new byte[s.Length * 4];
        System.Buffer.BlockCopy(s, 0, bytes, 0, bytes.Length);
        File.WriteAllBytes(path, bytes);
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);

        wb.snapFile = AssetDatabase.LoadAssetAtPath<TextAsset>(path);
        wb.snapLegacy = null;                 // シーンから旧データを落とす
        EditorUtility.SetDirty(wb);
    }

    [MenuItem("Edo/水域/snapを外部ファイルへ移す")]
    public static void MigrateAll()
    {
        var all = Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        int done = 0; long floats = 0;
        var log = new System.Text.StringBuilder();
        foreach (var wb in all)
        {
            if (!wb.hasSnap) { log.AppendLine($"  skip {wb.name} (snap無し)"); continue; }
            var s = wb.snap;                  // 外部ファイル→旧フィールドの順に解決される
            if (s == null || s.Length == 0) { log.AppendLine($"  skip {wb.name} (空)"); continue; }
            if (s.Length != wb.sW * wb.sH)
            { Debug.LogError($"[WaterSnapStore] {wb.name}: snap長 {s.Length} が sW*sH {wb.sW * wb.sH} と一致しない。移行を中止"); return; }
            Undo.RecordObject(wb, "Migrate water snap");
            Save(wb);
            done++; floats += s.Length;
            log.AppendLine($"  {wb.name}\t{wb.sW}x{wb.sH}\t{s.Length}個\t{s.Length * 4 / 1024}KB");
        }
        Debug.Log($"[WaterSnapStore] {done}/{all.Length} 個を移行。float {floats}個 = "
                + $"YAML約{floats * 13.0 / 1048576:F1}MB -> バイナリ{floats * 4.0 / 1048576:F1}MB\n{log}");
        if (done > 0) UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
    }

    /// <summary>移行できているかの検算。</summary>
    [MenuItem("Edo/水域/snapの置き場所を検査")]
    public static void Verify()
    {
        var sb = new System.Text.StringBuilder("[WaterSnapStore] 検査\n");
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            var s = wb.snap;
            sb.AppendLine($"  {wb.name}\thasSnap={wb.hasSnap}\tsnapFile={(wb.snapFile != null ? wb.snapFile.name : "なし")}"
                        + $"\t旧データ={(wb.snapLegacy != null ? wb.snapLegacy.Length.ToString() : "0")}"
                        + $"\t読めた長さ={(s != null ? s.Length : 0)}\t期待={wb.sW * wb.sH}");
        }
        Debug.Log(sb.ToString());
    }
}
