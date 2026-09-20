using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using Scene = UnityEngine.SceneManagement.Scene;

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
///   2026-08-16 に実測: Setting the parent of a transform which resides in a Prefab
///   instance is not possible が出て、Stage3_Retire のような処理が無言で失敗する。
///   解かずに走らせると「動いたように見えて何も起きていない」状態になる。
///
/// ★ 子を「足す」だけなら解かなくても動く(追加は override として通る)が、
///   走らせた後の「書き戻す」は必要。しないと変更がシーン側に積まれて元の木阿弥になる。
///
/// ★★★ 2026-09-21(EDO-0282②): **書き戻すのは「この巡で触ったルート」だけ。**
///   以前は保存のたびにシーンの全ルートを舐めていたので、1回の保存で 83 本中 74 本・
///   128MB を書き直して、git 上で実際に変わったのは 1 本という状態だった(実測)。
///   台帳(TouchKey)に載ったルートだけ書く。載せるのは EnsureEditable — 全ビルダーの
///   Group() が必ず通る唯一の共通路。
///   ⛔ 「プレハブ資産はあるがインスタンスでない」ルートを無条件に書き戻すのはやめた。
///     解けたまま置かれた他邸が、別邸の保存だけで上書きされていた(qa-and-pitfalls の ⛔⛔)。
///     いまは書かずに名指しで警告する(orphan)。救出は「プレハブへ書き戻す(選択中)」。
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

    // ───────────────────────── 台帳: この巡で触ったルート ─────────────────────────

    /// <summary>
    /// 触ったルートの台帳。**SessionState** に置く — static はドメインリロードで消え、
    /// EditorPrefs はエディタを再起動しても残って前の起動の亡霊が別シーンで発火する。
    /// SessionState の寿命(エディタ起動中だけ)が「この巡」とちょうど一致する。
    /// ⛔ 記録の単位は必ず scene.path と組。ルート名だけだと、作業場で触った邸を
    ///   赤坂の保存が拾って**赤坂側の(古い)同名ルート**を書き戻してしまう。
    /// </summary>
    const string TouchKey = "Edo.Prefab.Touched";

    /// <summary>書き戻しの前後で中身が変わったかを MD5 で検める(既定 on)。</summary>
    const string VerifyKey = "Edo.PrefabWriteBack.Verify";
    public static bool Verify
    {
        get { return EditorPrefs.GetBool(VerifyKey, true); }
        set { EditorPrefs.SetBool(VerifyKey, value); }
    }

    static string TouchLine(string scenePath, string root) { return scenePath + "\t" + root; }

    /// <summary>この巡で触ったルートとして台帳に載せる。★冪等 — MCP の再送で二重に積まない。</summary>
    public static void MarkTouched(Scene scene, string root)
    {
        if (string.IsNullOrEmpty(root)) return;
        var sp = scene.path;
        if (string.IsNullOrEmpty(sp)) return;          // プレハブステージ・未保存のシーン
        var line = TouchLine(sp, root);
        var cur = SessionState.GetString(TouchKey, "");
        foreach (var l in cur.Split('\n')) if (l == line) return;
        SessionState.SetString(TouchKey, cur.Length == 0 ? line : cur + "\n" + line);
    }

    /// <summary>そのシーンで触ったルート名。</summary>
    public static HashSet<string> TouchedIn(Scene scene)
    {
        var set = new HashSet<string>();
        var sp = scene.path;
        if (string.IsNullOrEmpty(sp)) return set;
        var head = sp + "\t";
        foreach (var l in SessionState.GetString(TouchKey, "").Split('\n'))
            if (l.StartsWith(head)) set.Add(l.Substring(head.Length));
        return set;
    }

    /// <summary>書き切ったルートを台帳から落とす。⛔ 書く前に落とさない — 途中で落ちても次の保存で拾える。</summary>
    public static void ForgetTouched(Scene scene, string root)
    {
        var sp = scene.path;
        if (string.IsNullOrEmpty(sp)) return;
        var line = TouchLine(sp, root);
        var keep = new List<string>();
        foreach (var l in SessionState.GetString(TouchKey, "").Split('\n'))
            if (l.Length > 0 && l != line) keep.Add(l);
        SessionState.SetString(TouchKey, string.Join("\n", keep));
    }

    public static void ClearTouched() { SessionState.SetString(TouchKey, ""); }

    /// <summary>
    /// **まだプレハブへ書き戻されていない**ルート。作業場の掃除の前に検めるためにある
    /// (Koba.unity は gitignore なので、ここで消すと本当に失われる)。
    /// 台帳に載っているもの ＋ 解けたままでプレハブ資産があるもの。
    /// </summary>
    public static List<string> UnwrittenIn(Scene scene)
    {
        var touched = TouchedIn(scene);
        var outp = new List<string>();
        foreach (var r in scene.GetRootGameObjects())
        {
            if (KeepInScene.Contains(r.name)) continue;
            bool isPf = PrefabUtility.IsAnyPrefabInstanceRoot(r);
            if (touched.Contains(r.name)) { outp.Add(r.name); continue; }
            if (!isPf && File.Exists(PathFor(r.name))) outp.Add(r.name);
        }
        return outp;
    }

    // ───────────────────────── 解く ─────────────────────────

    /// <summary>
    /// ビルダーが触る直前に呼ぶ。プレハブインスタンスなら解いて普通のオブジェクトに戻す。
    /// **全ビルダーの Group() の冒頭から呼ばれている** — ここが唯一の共通の通り道なので、
    /// ステージ関数を個別に叩いても必ず通る。
    /// 解かないと子の付け替え・削除が例外を投げずに黙って失敗する(クラス冒頭の ★★)。
    /// 保存時に EdoYashikiPrefabAutoSave が自動で書き戻すので、解きっぱなしでよい。
    /// ⛔ 台帳への記録は**早期 return より前**。既に解けている(2巡目・MCP の再送・
    ///   前セッションから解けたまま持ち越し)ときこそ書き戻しが要る。
    /// </summary>
    public static void EnsureEditable(GameObject root)
    {
        if (root == null) return;
        MarkTouched(root.scene, root.name);
        if (!PrefabUtility.IsAnyPrefabInstanceRoot(root)) return;
        PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
    }

    // ───────────────────────── 書き戻す ─────────────────────────

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

    static string Md5(string path)
    {
        if (!Verify || !File.Exists(path)) return null;
        using (var md5 = System.Security.Cryptography.MD5.Create())
        using (var fs = File.OpenRead(path))
            return System.BitConverter.ToString(md5.ComputeHash(fs));
    }

    /// <summary>One() を包んで、書いたバイト数・所要 ms・中身が実際に変わったかを Editor.log へ残す。</summary>
    static string OneLogged(GameObject go, out long bytes)
    {
        string path = PathFor(go.name);
        string h0 = Md5(path);
        int n = go.GetComponentsInChildren<Transform>(true).Length;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var line = One(go);
        sw.Stop();
        bytes = File.Exists(path) ? new FileInfo(path).Length : 0;
        string verdict = h0 == null ? "" : (h0 == Md5(path) ? " same(無駄)" : " changed");
        Debug.Log($"[EdoWriteBack] {go.name} tr={n} {bytes / 1048576.0:F1}MB {sw.ElapsedMilliseconds}ms{verdict}");
        return line;
    }

    public enum WriteBackScope
    {
        /// <summary>この巡で触ったルートだけ(既定)。</summary>
        Touched,
        /// <summary>シーンの全ルート(旧挙動・救済用)。⚠ 解けたままの他邸を巻き込む。</summary>
        All,
    }

    /// <summary>
    /// シーンのルートをプレハブへ書き戻す。
    /// <paramref name="scene"/> は**引数で受ける** — 保存フックは保存されるシーンを渡してくるのに、
    /// 以前は GetActiveScene() を見ていたので、追加読み込み環境では
    /// **保存していないシーンのルートを書き戻して**いた。
    /// <paramref name="markDirty"/> は保存フックからは false。
    /// sceneSaving の最中に dirty を立て直すと、保存し終えたシーンが即 dirty へ戻る。
    /// </summary>
    public static string WriteBack(Scene scene, WriteBackScope scope, bool markDirty)
    {
        var touched = TouchedIn(scene);
        var orphans = new List<string>();
        var sb = new System.Text.StringBuilder();
        int wrote = 0, skipUntouched = 0, skipNoMods = 0;
        long bytes = 0;
        var sw = System.Diagnostics.Stopwatch.StartNew();

        foreach (var r in scene.GetRootGameObjects())
        {
            bool isPf = PrefabUtility.IsAnyPrefabInstanceRoot(r);
            bool hasAsset = File.Exists(PathFor(r.name));
            if (!isPf && !hasAsset) continue;          // 未変換 — Convert の仕事(従来どおり触らない)

            int mods = isPf ? PrefabUtility.GetObjectOverrides(r).Count
                            + PrefabUtility.GetAddedGameObjects(r).Count
                            + PrefabUtility.GetRemovedGameObjects(r).Count : -1;
            bool hit = touched.Contains(r.name);
            string why = hit ? "台帳" : (isPf ? $"override {mods}" : "解けたまま");

            if (scope == WriteBackScope.Touched && !hit)
            {
                if (!isPf) { orphans.Add(r.name); skipUntouched++; continue; }   // ⛔ 他邸を巻き込まない
                if (mods == 0) { skipNoMods++; continue; }
                // プレハブインスタンスに override がある = Group() を通らない手直し。書く。
            }
            else if (scope == WriteBackScope.All && isPf && mods == 0 && !hit) { skipNoMods++; continue; }

            long b;
            sb.AppendLine("  " + OneLogged(r, out b) + $"\t({why})");
            bytes += b;
            wrote++;
            ForgetTouched(scene, r.name);
        }
        sw.Stop();

        if (wrote > 0 && markDirty)
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);

        Debug.Log($"[EdoWriteBack] done scene={Path.GetFileName(scene.path)} scope={scope}"
                + $" wrote={wrote} (untouched={skipUntouched} nomods={skipNoMods})"
                + $" bytes={bytes / 1048576.0:F1}MB ms={sw.ElapsedMilliseconds}");

        if (orphans.Count > 0)
            Debug.LogWarning($"⚠ [EdoWriteBack] 解けたまま放置されたルートが {orphans.Count} 件(書き戻していない):\n"
                + "   " + string.Join(", ", orphans)
                + "\n   自分のものなら Edo/屋敷/プレハブへ書き戻す(選択中) で明示的に書き戻すこと。"
                + "\n   他邸のものなら触らないのが正しい(以前はここで勝手に上書きしていた)。");

        return wrote == 0 ? "書き戻す変更はありません" : $"{wrote}件を書き戻しました\n{sb}";
    }

    /// <summary>旧 API。全ルートを舐める(救済用)。既存のスニペット・手引きのために残す。</summary>
    public static string WriteBackAll()
    {
        return WriteBack(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), WriteBackScope.All, true);
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
            long b;
            sb.AppendLine(OneLogged(go, out b));
            ForgetTouched(scene, nm);
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
            MarkTouched(scene, nm);
            if (!PrefabUtility.IsAnyPrefabInstanceRoot(go)) { sb.AppendLine($"{nm}\t既に解けている"); continue; }
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            sb.AppendLine($"{nm}\t解いた");
        }
        return sb.ToString();
    }

    // ───────────────────────── メニュー ─────────────────────────
    // ⛔ ここに EditorUtility.DisplayDialog を足さないこと。execute_menu_item 経由だと
    //    モーダルが主スレッドを止めて MCP の呼び出しが軒並みタイムアウトする。

    [MenuItem("Edo/屋敷/編集のためにプレハブを解く(選択中)")]
    public static void UnpackSelectedMenu()
    {
        var names = new List<string>();
        foreach (var o in Selection.gameObjects) names.Add(o.name);
        if (names.Count == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log(Unpack(names));
    }

    [MenuItem("Edo/屋敷/プレハブへ書き戻す(触った分だけ)")]
    public static void WriteBackTouchedMenu()
    {
        Debug.Log(WriteBack(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), WriteBackScope.Touched, true));
    }

    [MenuItem("Edo/屋敷/プレハブへ書き戻す(選択中)")]
    public static void WriteBackSelectedMenu()
    {
        var names = new List<string>();
        foreach (var o in Selection.gameObjects) names.Add(o.name);
        if (names.Count == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log(Convert(names));
    }

    [MenuItem("Edo/屋敷/プレハブへ書き戻す(全部・強制)")]
    public static void WriteBackAllMenu()
    {
        Debug.LogWarning("⚠ 全ルートを舐めます。解けたままの他邸も巻き込みます(救済用)。"
                       + "普段は Edo/屋敷/プレハブへ書き戻す(触った分だけ) を使うこと。");
        Debug.Log(WriteBackAll());
    }

    [MenuItem("Edo/屋敷/切り出し状況を検査")]
    public static void StatusMenu() { Debug.Log(Status()); }

    public static string Status()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var touched = TouchedIn(scene);
        var sb = new System.Text.StringBuilder("root\ttransform\t状態\toverride\t台帳\n");
        int conv = 0, left = 0, keep = 0, loose = 0;
        foreach (var r in scene.GetRootGameObjects())
        {
            int n = r.GetComponentsInChildren<Transform>(true).Length;
            if (KeepInScene.Contains(r.name)) { keep++; continue; }
            bool isPf = PrefabUtility.IsAnyPrefabInstanceRoot(r);
            bool hasAsset = File.Exists(PathFor(r.name));
            if (isPf) conv++; else if (n >= MinTransforms) left++;
            if (!isPf && hasAsset) loose++;
            int mods = isPf ? PrefabUtility.GetObjectOverrides(r).Count
                            + PrefabUtility.GetAddedGameObjects(r).Count
                            + PrefabUtility.GetRemovedGameObjects(r).Count : 0;
            string state = isPf ? "プレハブ" : (hasAsset ? "解けたまま" : "シーン直");
            if (isPf || n >= MinTransforms)
                sb.AppendLine($"{r.name}\t{n}\t{state}\t{mods}\t{(touched.Contains(r.name) ? "触った" : "")}");
        }
        sb.AppendLine($"\nプレハブ化済={conv}  解けたまま={loose}  未変換(>= {MinTransforms})={left}  シーンに残す={keep}");
        sb.AppendLine($"台帳({Path.GetFileName(scene.path)})={touched.Count} 件");
        return sb.ToString();
    }
}
