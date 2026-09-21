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
///
/// ★★★★ 2026-09-21(EDO-0282③): **大きな屋敷は段ごとに入れ子プレハブへ割る。**
///   松江松平の1本は 42.0MB あり、門の位置を 1cm 直すだけでも 42.0MB が書き直されていた。
///   実測の内訳(`Edo_Yashiki_MatsudairaDewa.prefab`):
///     Buildings 21.3MB / Niwa 15.2MB / Fuzoku 3.6MB / Kakoi 0.94MB / Ishigaki 0.90MB / Mon 0.015MB
///   ⇒ ルート直下の群を1段=1プレハブ(<see cref="PartsDir"/>)へ出し、ルートは参照だけを持つ。
///     触っていない段は**開かない・書かない**ので、Stage5(門)だけ流した巡で動くのは 15KB になる。
///
///   ⛔ そのために <see cref="EnsureEditable"/> の解き方を Completely → **OutermostRoot** へ改めた。
///     Completely は葉のプレハブ(木・キットの部材)の接続まで全部ほどく。ほどけた段は次の
///     書き戻しで**生のオブジェクトとして**直列化されるので、同じ中身がまるまる太る。
///     実測: 庭(Niwa)は 5,155 個すべてが生のオブジェクトで 15.2MB — 一方、直前に建て直された
///     Buildings は 7,795 個がプレハブ参照のままで 21.3MB(1個あたり 2.7KB 対 3.1KB、
///     しかも生のほうは木の LOD まで1個ずつ展開されている)。
/// </summary>
public static class EdoYashikiPrefab
{
    public const string Dir = "Assets/Edo/Prefabs/Scene";

    /// <summary>段(ルート直下の群)の入れ子プレハブの置き場。⛔ 手で作る資産は置かない — ここは生成物だけ。</summary>
    public const string PartsDir = Dir + "/Parts";

    /// <summary>シーンに置いたままにするルート(地形・水・プレイヤー・オーバーレイ等)。</summary>
    static readonly HashSet<string> KeepInScene = new HashSet<string>{
        "ModernTerrain", "Water", "Player", "SpawnPoint", "GeoAnchors", "Directional Light",
        "PostVolume", "OldMapOverlay", "ModernMapOverlay", "Castle_Standin",
        "TempFences", "TempLineup", "Main Camera",
    };

    /// <summary>これ未満の小さなルートは切り出しても意味がないので置いたまま。</summary>
    const int MinTransforms = 50;

    /// <summary>
    /// 段へ割るルートの名簿(EDO-0282③)。
    /// ⛔ **載せてよいのは、ビルダーの Group() を <see cref="Group"/> へ委ねた邸だけ。**
    ///   委ねていないビルダーが段のインスタンスを Clear() すると、プレハブ由来の子の削除が
    ///   **例外を投げずに**無視される(クラス冒頭の ★★)。
    /// ⛔ 大きさで自動に決めない — 閾値で決めると、類型の 79 区画がある日いきなり Parts へ散る。
    /// 2026-09-21 時点で割るに値する大きさ(ファイル)は松江松平 42.0MB・岡部 37.0MB・土井 15.1MB の3本。
    /// 次に大きい 溜池干場 7.3MB・山王社 5.9MB は、ビルダーが2本に分かれているので保留。
    /// </summary>
    static readonly HashSet<string> SplitRoots = new HashSet<string>{
        "Edo_Yashiki_MatsudairaDewa", "Edo_Yashiki_OkabeChikuzen", "Edo_Yashiki_DoiOsumi",
    };

    static string Safe(string name)
    {
        var safe = name;
        foreach (var c in Path.GetInvalidFileNameChars()) safe = safe.Replace(c, '_');
        return safe;
    }

    static string PathFor(string rootName) { return Dir + "/" + Safe(rootName) + ".prefab"; }

    /// <summary>段の入れ子プレハブのパス。⛔ ルート名を頭に付ける — 段名(Niwa・Mon…)は邸をまたいで重なる。</summary>
    public static string StagePathFor(string rootName, string stageName)
    {
        return PartsDir + "/" + Safe(rootName) + "__" + Safe(stageName) + ".prefab";
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
    ///
    /// ⭐ **安全側の入口**(EDO-0282③)。段へ割ってあるルートは、段も全部その場で解く。
    ///   呼び手がどの段を触るか分からないので、こうしないと Clear() が黙って失敗する。
    ///   ⚠ 全段を解くということは**全段を書き直す**ということ — 速さの利は出ない。
    ///   段ごとの利が欲しいビルダーは <see cref="Group"/> を通すこと(触った段だけ解く)。
    /// </summary>
    public static void EnsureEditable(GameObject root)
    {
        EnsureRootEditable(root);
        if (root == null) return;
        var kids = new List<Transform>();
        foreach (Transform t in root.transform) kids.Add(t);
        foreach (var t in kids) EnsureStageEditable(t.gameObject);
    }

    /// <summary>
    /// ルートの外側だけ解く。段の入れ子プレハブと葉のプレハブ(木・キットの部材)は**繋いだまま**。
    /// ⛔ Completely で解いてはいけない(EDO-0282③・クラス冒頭の ★★★★)。
    ///   葉まで解くと、次の書き戻しで同じ中身が生のオブジェクトとして直列化されて太る。
    ///   庭が 5,155 個すべて生になって 15.2MB を占めていたのがこれ。
    /// </summary>
    public static void EnsureRootEditable(GameObject root)
    {
        if (root == null) return;
        MarkTouched(root.scene, root.name);
        if (!PrefabUtility.IsAnyPrefabInstanceRoot(root)) return;
        PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
    }

    /// <summary>この駒は「うちが作った段の入れ子プレハブ」のインスタンスか。</summary>
    public static bool IsStageInstance(GameObject go)
    {
        if (go == null || !PrefabUtility.IsAnyPrefabInstanceRoot(go)) return false;
        var src = PrefabUtility.GetCorrespondingObjectFromSource(go);
        if (src == null) return false;
        var path = AssetDatabase.GetAssetPath(src);
        return !string.IsNullOrEmpty(path) && path.StartsWith(PartsDir + "/");
    }

    /// <summary>
    /// 段の群を組み替えられる状態にする。段が入れ子プレハブのインスタンスなら外側だけ解く。
    /// ⛔ これを通さずに Clear() すると、プレハブ由来の子の削除が**例外を投げずに**無視される。
    /// ⛔ 葉のプレハブ(木・部材)は解かない — 解くと書き戻しで太る(★★★★)。
    /// </summary>
    public static void EnsureStageEditable(GameObject stage)
    {
        if (!IsStageInstance(stage)) return;
        PrefabUtility.UnpackPrefabInstance(stage, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
    }

    /// <summary>
    /// 屋敷ルートの下の群を辿って返す(無ければ作る)。**全ビルダー共通の一本道**。
    /// <paramref name="child"/> は "Fuzoku/Kaidan" のようなスラッシュ区切り。空ならルート自身。
    ///
    /// ルートは外側だけ解き、**辿った先頭の段だけ**解く。他の段は繋いだままなので、
    /// 書き戻しがそこを飛ばせる(EDO-0282③)。
    /// ⛔ ここで段を勝手に全部解かないこと — 全部解いたら ③ の利はゼロになる。
    /// </summary>
    public static Transform Group(string rootName, string child)
    {
        var r = GameObject.Find(rootName);
        if (r == null) { r = new GameObject(rootName); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EnsureRootEditable(r);
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        bool first = true;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var go = new GameObject(seg);
                Undo.RegisterCreatedObjectUndo(go, "grp");
                go.transform.SetParent(cur, false);
                nx = go.transform;
            }
            else if (first) EnsureStageEditable(nx.gameObject);
            cur = nx;
            first = false;
        }
        return cur;
    }

    /// <summary>群の子を全部消す。⛔ 先に <see cref="Group"/> か <see cref="EnsureEditable"/> を通すこと。</summary>
    public static void Clear(Transform t)
    {
        for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(t.GetChild(i).gameObject);
    }

    // ───────────────────────── 書き戻す ─────────────────────────

    /// <summary>
    /// 1ルートをプレハブへ書き出して接続する。既にプレハブでも上書きして override を畳む。
    /// 大きなルートは先に段へ割り、**触っていない段は開かない・書かない**(EDO-0282③)。
    /// </summary>
    public static string One(GameObject go)
    {
        if (go == null) return "null";
        Directory.CreateDirectory(Dir);
        string path = PathFor(go.name);
        int n = go.GetComponentsInChildren<Transform>(true).Length;
        string stageNote = "";
        if (ShouldSplit(go))
        {
            int kept;
            int wrote = SplitStages(go, out kept);
            stageNote = $"\t段 書{wrote}/据置{kept}";
        }
        var pf = PrefabUtility.SaveAsPrefabAssetAndConnect(go, path, InteractionMode.AutomatedAction);
        return $"{go.name}\t{n}\t{(pf != null ? "OK" : "失敗")}{stageNote}";
    }

    // ───────────────────────── 段へ割る(EDO-0282③) ─────────────────────────

    /// <summary>
    /// 段へ割るルートか。決め方は二つだけ:
    /// ① <see cref="SplitRoots"/> の名簿に載っている
    /// ② **既に段のプレハブが出来ている**(一度割ったルートは割れたまま)
    /// 新しく割るときはメニュー「Edo/屋敷/段別の入れ子プレハブへ割る(選択中)」を押す。
    /// 以後は②で自動的に続くので、名簿に足し忘れても戻らない。
    /// </summary>
    public static bool ShouldSplit(GameObject go)
    {
        if (go == null || go.transform.childCount < 2) return false;
        if (SplitRoots.Contains(go.name)) return true;
        return Directory.Exists(PartsDir)
            && Directory.GetFiles(PartsDir, Safe(go.name) + "__*.prefab").Length > 0;
    }

    /// <summary>
    /// ルート直下の群を1段=1プレハブへ出す。戻り値は**書いた段の数**、<paramref name="kept"/> は据え置いた数。
    ///
    /// ⭐ 据え置きの判定は**シーンの状態そのもの**から採る — 台帳を二重に持たない。
    ///   「うちの段プレハブに繋がったままで override 0」＝ この巡で誰も触っていない、である。
    ///   触った段は <see cref="Group"/> が解いているので、必ず「繋がっていない」側に落ちる。
    /// ⚠ override の数は Editor.log へ出す — 0 にならない環境があれば据え置きが効かないので、
    ///   そのときはここのログが先に教える(規則19・輪に入っていない値は未検査)。
    /// </summary>
    static int SplitStages(GameObject root, out int kept)
    {
        Directory.CreateDirectory(PartsDir);
        kept = 0;
        int wrote = 0;
        var kids = new List<Transform>();
        foreach (Transform t in root.transform) kids.Add(t);
        foreach (var t in kids)
        {
            var go = t.gameObject;
            string path = StagePathFor(root.name, go.name);
            if (IsStageInstance(go))
            {
                var src = AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(go));
                int mods = PrefabUtility.GetObjectOverrides(go).Count
                         + PrefabUtility.GetAddedGameObjects(go).Count
                         + PrefabUtility.GetRemovedGameObjects(go).Count;
                if (src == path && mods == 0) { kept++; continue; }      // 誰も触っていない段 — 開かない
                Debug.Log($"[EdoWriteBack] 段 {root.name}/{go.name} を書く(override {mods}"
                        + (src == path ? "" : $" ・出所が違う {src}") + ")");
            }
            var sw = System.Diagnostics.Stopwatch.StartNew();
            PrefabUtility.SaveAsPrefabAssetAndConnect(go, path, InteractionMode.AutomatedAction);
            sw.Stop();
            long b = File.Exists(path) ? new FileInfo(path).Length : 0;
            Debug.Log($"[EdoWriteBack] 段 {root.name}/{go.name} {b / 1048576.0:F2}MB {sw.ElapsedMilliseconds}ms");
            wrote++;
        }
        return wrote;
    }

    /// <summary>ルートの段プレハブのうち、いまのルートに同名の子が居ないもの(取り残し)。</summary>
    public static List<string> StaleStageAssets(GameObject root)
    {
        var outp = new List<string>();
        if (root == null || !Directory.Exists(PartsDir)) return outp;
        var live = new HashSet<string>();
        foreach (Transform t in root.transform) live.Add(Path.GetFileName(StagePathFor(root.name, t.name)));
        string head = Safe(root.name) + "__";
        foreach (var f in Directory.GetFiles(PartsDir, "*.prefab"))
        {
            var fn = Path.GetFileName(f);
            if (!fn.StartsWith(head) || live.Contains(fn)) continue;
            outp.Add(PartsDir + "/" + fn);
        }
        return outp;
    }

    static string Md5(string path)
    {
        if (!Verify || !File.Exists(path)) return null;
        using (var md5 = System.Security.Cryptography.MD5.Create())
        using (var fs = File.OpenRead(path))
            return System.BitConverter.ToString(md5.ComputeHash(fs));
    }

    /// <summary>
    /// One() を包んで、書いたバイト数・所要 ms・中身が実際に変わったかを Editor.log へ残す。
    /// <paramref name="bytes"/> は**ルート＋段のファイルの合計**(③の後はルート単体が小さくなるので、
    /// ルートだけ数えると「速くなった」と誤読する)。
    /// </summary>
    static string OneLogged(GameObject go, out long bytes)
    {
        string path = PathFor(go.name);
        string h0 = Md5(path);
        int n = go.GetComponentsInChildren<Transform>(true).Length;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var line = One(go);
        sw.Stop();
        bytes = File.Exists(path) ? new FileInfo(path).Length : 0;
        long stageBytes = 0;
        foreach (Transform t in go.transform)
        {
            var sp = StagePathFor(go.name, t.name);
            if (File.Exists(sp)) stageBytes += new FileInfo(sp).Length;
        }
        bytes += stageBytes;
        string verdict = h0 == null ? "" : (h0 == Md5(path) ? " same(無駄)" : " changed");
        Debug.Log($"[EdoWriteBack] {go.name} tr={n} 本体{(bytes - stageBytes) / 1048576.0:F2}MB"
                + (stageBytes > 0 ? $" + 段{stageBytes / 1048576.0:F2}MB" : "")
                + $" {sw.ElapsedMilliseconds}ms{verdict}");
        var stale = StaleStageAssets(go);
        if (stale.Count > 0)
            Debug.LogWarning($"⚠ [EdoWriteBack] {go.name} に居ない段のプレハブが {stale.Count} 件残っている:\n   "
                + string.Join("\n   ", stale)
                + "\n   建て方が変わって段が減ったのなら、確かめてから手で消すこと(⛔ 自動では消さない)。");
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

    [MenuItem("Edo/屋敷/段別の入れ子プレハブへ割る(選択中)")]
    public static void SplitSelectedMenu()
    {
        var sb = new System.Text.StringBuilder();
        foreach (var o in Selection.gameObjects)
        {
            if (o.transform.parent != null) { sb.AppendLine($"{o.name}\tルートではない"); continue; }
            if (o.transform.childCount < 2) { sb.AppendLine($"{o.name}\t直下の群が1つ以下なので割る意味がない"); continue; }
            // ⭐ 名簿に無くてもここでは割る。割れば段のプレハブが残るので、以後 ShouldSplit が②で拾う。
            EnsureRootEditable(o);
            int kept; int wrote = SplitStages(o, out kept);
            PrefabUtility.SaveAsPrefabAssetAndConnect(o, PathFor(o.name), InteractionMode.AutomatedAction);
            ForgetTouched(o.scene, o.name);
            sb.AppendLine($"{o.name}\t段 書{wrote}/据置{kept}");
        }
        if (sb.Length == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log(sb.ToString());
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
        sb.Append(StageStatus(scene));
        return sb.ToString();
    }

    /// <summary>段へ割ったルートの内訳(ファイルの大きさつき)。どこが重いかをここで見る。</summary>
    public static string StageStatus(Scene scene)
    {
        var sb = new System.Text.StringBuilder();
        foreach (var r in scene.GetRootGameObjects())
        {
            if (KeepInScene.Contains(r.name) || !ShouldSplit(r)) continue;
            sb.AppendLine($"\n段の内訳 {r.name}\t段\tMB\ttransform\t状態");
            long tot = 0;
            foreach (Transform t in r.transform)
            {
                var sp = StagePathFor(r.name, t.name);
                long b = File.Exists(sp) ? new FileInfo(sp).Length : 0;
                tot += b;
                int n = t.GetComponentsInChildren<Transform>(true).Length;
                string st = IsStageInstance(t.gameObject) ? "繋がっている" : (File.Exists(sp) ? "解けたまま" : "未分割");
                sb.AppendLine($"\t{t.name}\t{b / 1048576.0:F2}\t{n}\t{st}");
            }
            long rb = File.Exists(PathFor(r.name)) ? new FileInfo(PathFor(r.name)).Length : 0;
            sb.AppendLine($"\t(本体)\t{rb / 1048576.0:F2}\t-\t-");
            sb.AppendLine($"\t合計\t{(tot + rb) / 1048576.0:F2}");
        }
        return sb.ToString();
    }
}
