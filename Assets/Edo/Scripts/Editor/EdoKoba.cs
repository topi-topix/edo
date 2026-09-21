using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Compilation;
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
/// ⭐ **隣も載る**(2026-09-21・EDO-0282①)。取り合いと区域侵犯は隣が居ないと測れないので、
///   足あとの台帳(`UserData/Koba/ashiato.json`)から 20m 以内のルートを機械で選んで載せる。
///   段へ割ってある邸は**囲いの段だけ**(松江松平 42MB → 1.8MB)。隣の名前には「(隣)」が付き、
///   ビルダーの `GameObject.Find(ルート名)` に当たらない = 触れない・書き戻らない。
///   台帳を採るのは `Edo/普請/作業場: 足あとを採る(赤坂で)`。
///
/// ⛔ **検証レンダと全域の見え方は作業場では見えない。** 最後に `赤坂へ戻す` で検める。
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
    /// ビルダーが建てるのに実際に要る物だけ。⚠ 赤坂に無い物は黙って飛ばす
    /// (`Main Camera` は赤坂のルートに無い — 検証レンダは撮るたびに仮のカメラを立てる)。</summary>
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

    [MenuItem("Edo/普請/作業場を開く(選択中のプレハブ・隣なし)", false, 302)]
    public static void OpenSelectedAloneMenu()
    {
        var o = Selection.activeObject;
        var path = o == null ? null : AssetDatabase.GetAssetPath(o);
        if (string.IsNullOrEmpty(path) || !path.StartsWith(EdoYashikiPrefab.Dir))
        {
            Debug.LogWarning("Project ウィンドウで " + EdoYashikiPrefab.Dir + " の .prefab を選んでから実行してください");
            return;
        }
        Debug.Log(Open(Path.GetFileNameWithoutExtension(path), false));
    }

    /// <summary>作業場を開き、屋敷を1軒と**その隣**を載せる。<paramref name="yashiki"/> は
    /// プレハブの名前(拡張子なし・例 "Edo_Yashiki_MatsudairaDewa")。空なら地形だけ。
    ///
    /// ⭐ **隣を載せるのは取り合いと境界のため**(EDO-0282①)。許容0の欠陥のうち
    ///   「区域侵犯」「隣との隙・めり込み」は隣が居ないと**測れない**ので、隣が居ないかぎり
    ///   棟梁は赤坂へ戻るしかなかった。赤坂を開くと 1回 15〜29 秒、そこで C# を1行直すと
    ///   ドメインリロードが 36 秒(作業場なら 6.9 秒)。
    ///
    /// 隣は<see cref="Tonari"/>が足あとの台帳から機械で選ぶ。段へ割ってある邸は
    /// **囲いの段だけ**載せる(松江松平なら 42MB → 1.8MB)。隣は名前に「(隣)」が付くので
    /// ビルダーの <c>GameObject.Find(ルート名)</c> には当たらず、台帳にも載らない = 書き戻らない。
    /// </summary>
    public static string Open(string yashiki, bool tonari = true, float margin = TonariMargin, int max = TonariMax)
    {
        var cur = EditorSceneManager.GetActiveScene();
        if (cur.isDirty)
            return "⛔ いまのシーン '" + cur.name + "' に未保存の変更がある。保存してから呼ぶこと";
        if (!File.Exists(EdoAssets.Scenes.Koba))
            return "⛔ 作業場が無い。赤坂を開いて Edo/普請/作業場を仕立てる を先に実行すること";

        var koba = EditorSceneManager.OpenScene(EdoAssets.Scenes.Koba, OpenSceneMode.Single);

        // ⛔ **消す前に、書き戻していない屋敷が載っていないか検める。**
        //   下の掃除は DestroyImmediate で無条件に消すが、Koba.unity は gitignore なので
        //   書き戻していない邸をここで消すと**本当に失われる**(赤坂なら .unity に残る)。
        //   2026-09-21(EDO-0282②)までは「解けたままのルートを無条件に書き戻す」処理が
        //   偶然この穴を塞いでいた。その処理をやめたので、門を明示的に置く。
        var lost = EdoYashikiPrefab.UnwrittenIn(koba);
        if (lost.Count > 0)
            return "⛔ 書き戻していない屋敷が作業場に載っている: " + string.Join(", ", lost)
                 + "\n  Edo/屋敷/プレハブへ書き戻す(触った分だけ) を実行してから開き直すこと";

        // ⚠ **冪等にする。** MCP がタイムアウトすると同じ呼び出しが再送され、
        //   素直に実体化するだけだと屋敷が何重にも積まれる(2026-09-19 に6重を実測)。
        //   前回の屋敷と隣を片付ける役も兼ねる。
        int swept = 0;
        var bring = new HashSet<string>(Bring);
        foreach (var r in koba.GetRootGameObjects())
        {
            if (bring.Contains(r.name)) continue;
            Object.DestroyImmediate(r);
            swept++;
        }
        string sweptMsg = swept > 0 ? "・前の " + swept + " 件を片付けた" : "";

        if (string.IsNullOrEmpty(yashiki))
        {
            if (swept > 0) EditorSceneManager.SaveScene(koba);
            return "作業場を開いた(屋敷なし・地形だけ" + sweptMsg + ")";
        }

        string path = EdoYashikiPrefab.Dir + "/" + yashiki + ".prefab";
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (asset == null) return "⛔ プレハブが無い: " + path;

        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        go.name = yashiki;
        Selection.activeGameObject = go;
        int trMe = go.GetComponentsInChildren<Transform>(true).Length;

        // ---- 隣 ----
        var loaded = new List<string>();
        string tonariMsg = "";
        if (tonari)
        {
            var names = Tonari(yashiki, margin, max);
            if (names.Count == 0)
            {
                tonariMsg = File.Exists(AshiatoPath)
                    ? "\n  ⚠ 隣は0件(" + margin.ToString("F0") + "m 以内に足あとが無い"
                      + (InAshiato(yashiki) ? "" : "・そもそも台帳に " + yashiki + " が載っていない") + ")"
                    : "\n  ⚠ 足あとの台帳が無いので隣を載せていない — 赤坂で Edo/普請/作業場: 足あとを採る";
            }
            foreach (var n in names)
            {
                var nb = LoadTonari(n);
                if (nb != null) loaded.Add(nb);
            }
            if (loaded.Count > 0) tonariMsg = "\n  隣 " + loaded.Count + " 件: " + string.Join(" / ", loaded);
        }

        // 載せた状態で保存しておく。次に切り替えるときモーダルが出ないため。
        EditorSceneManager.SaveScene(koba);
        return "作業場: " + yashiki + " を載せた(" + trMe + " transform" + sweptMsg + ")" + tonariMsg;
    }

    static bool InAshiato(string name)
    {
        foreach (var a in Ashiato()) if (a.name == name) return true;
        return false;
    }

    /// <summary>隣に付ける印。⭐ ビルダーの <c>GameObject.Find(ルート名)</c> に当たらないこと・
    /// 書き戻しの台帳の名前と一致しないことの両方を、この1文字が担っている。</summary>
    public const string TonariSuffix = "(隣)";

    /// <summary>囲いに当たる段の名前(部分一致)。隣は**この段だけ**載せる。</summary>
    static readonly string[] PerimeterStages = { "Kakoi", "Ishigaki", "Mon", "Fence", "Saku", "Nagaya" };

    /// <summary>隣を1軒載せる。戻り値は報告用の1行(載らなければ null)。</summary>
    static string LoadTonari(string name)
    {
        var stages = EdoYashikiPrefab.StageAssetsOf(name);
        if (stages.Length > 0)
        {
            // 段へ割ってある邸 — 囲いの段だけ。取り合いと境界に要るのは外周だけで、
            // 御殿と庭(松江松平なら 40MB)は隣として見る意味が無い。
            var holder = new GameObject(name + TonariSuffix);
            int n = 0, tr = 0;
            foreach (var p in stages)
            {
                var stem = Path.GetFileNameWithoutExtension(p);
                int cut = stem.IndexOf("__");
                var stage = cut < 0 ? stem : stem.Substring(cut + 2);
                bool want = false;
                foreach (var k in PerimeterStages) if (stage.IndexOf(k, System.StringComparison.OrdinalIgnoreCase) >= 0) { want = true; break; }
                if (!want) continue;
                var sa = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                if (sa == null) continue;
                var si = (GameObject)PrefabUtility.InstantiatePrefab(sa);
                si.transform.SetParent(holder.transform, true);
                tr += si.GetComponentsInChildren<Transform>(true).Length;
                n++;
            }
            if (n == 0) { Object.DestroyImmediate(holder); return null; }
            Lock(holder);
            return name + "(囲い " + n + "段・" + tr + "tr)";
        }

        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(EdoYashikiPrefab.Dir + "/" + name + ".prefab");
        if (asset == null) return null;                       // シーンには居たがプレハブが無いルート
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        go.name = name + TonariSuffix;
        Lock(go);
        return name + "(" + go.GetComponentsInChildren<Transform>(true).Length + "tr)";
    }

    /// <summary>隣は見るだけ。Scene ビューで拾えなくして、手が滑って動かないようにする。</summary>
    static void Lock(GameObject go)
    {
        SceneVisibilityManager.instance.DisablePicking(go, true);
    }

    // ---- 戻す --------------------------------------------------------------

    [MenuItem("Edo/普請/赤坂へ戻す", false, 303)]
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
    // ═══════════════════════ 足あと — 隣を機械で選ぶ(EDO-0282①) ═══════════════════════

    /// <summary>
    /// ルート1本の**外接矩形(XZ)**。隣接の判定はこれだけでやる。
    /// ⛔ 名前から区画を当てない — 邸名とプレハブ名と区画 id は三者とも綴りが違い、
    ///   類型79・旧83・手組みで規則も違う。実体の座標で当たれば表は要らない。
    /// </summary>
    public struct Ashi
    {
        public string name;
        public float x0, z0, x1, z1;
        public int tr;                                   // transform 数(重さの目安)
        public bool Near(Ashi o, float m)
        {
            return x0 - m <= o.x1 && o.x0 <= x1 + m && z0 - m <= o.z1 && o.z0 <= z1 + m;
        }
    }

    /// <summary>足あとの台帳。赤坂から採って json に置く(Unity の外からも読める)。</summary>
    public const string AshiatoRel = "UserData/Koba/ashiato.json";

    /// <summary>隣と見なす間合い(m)。区画は道を挟んで向かい合うので、道幅(2〜18m)より広く採る。</summary>
    public const float TonariMargin = 20f;

    /// <summary>1回に載せる隣の上限。これを超えたら遠い順に落とす(作業場が重くなったら本末転倒)。</summary>
    public const int TonariMax = 8;

    static string AshiatoPath { get { return Path.Combine(Directory.GetCurrentDirectory(), AshiatoRel); } }

    // ---- 採る ----------------------------------------------------------------

    [MenuItem("Edo/普請/作業場: 足あとを採る(赤坂で)", false, 304)]
    public static void HarvestMenu() { Debug.Log(Harvest()); }

    /// <summary>
    /// 赤坂の全ルートの外接矩形を採って <see cref="AshiatoRel"/> へ書く。
    /// ⭐ **赤坂が正典**(全部が載っている唯一の場所)。プレハブを1本ずつ読み込んで測ると
    ///   162 本で数分かかるうえ、シーンに居ないルートまで拾ってしまう。
    /// ⚠ 建て直して形が変わった邸は、次に赤坂を開いたときに採り直す(古い足あとは隣を1軒
    ///   取り違えるだけで、取り違えても実害は「載る邸が1軒多い/少ない」に留まる)。
    /// </summary>
    public static string Harvest()
    {
        var cur = EditorSceneManager.GetActiveScene();
        if (cur.path != EdoAssets.Scenes.Akasaka)
            return "⛔ 赤坂を開いた状態で実行すること(いまは '" + cur.path + "')";

        var list = new List<Ashi>();
        int skipped = 0;
        foreach (var r in cur.GetRootGameObjects())
        {
            if (EdoYashikiPrefab.IsKeepInScene(r.name)) { skipped++; continue; }
            Ashi a;
            if (!Measure(r, out a)) { skipped++; continue; }
            list.Add(a);
        }
        list.Sort((p, q) => string.CompareOrdinal(p.name, q.name));

        var sb = new System.Text.StringBuilder();
        sb.Append("{\n  \"_\": \"作業場が隣を選ぶための外接矩形(XZ・世界座標)。Edo/普請/作業場: 足あとを採る(赤坂で) が書く。手で編集しない\",\n");
        sb.Append("  \"harvested\": \"").Append(System.DateTime.Now.ToString("yyyy-MM-dd HH:mm")).Append("\",\n");
        sb.Append("  \"items\": [\n");
        for (int i = 0; i < list.Count; i++)
        {
            var a = list[i];
            sb.Append("    {\"n\": \"").Append(a.name).Append("\", \"x0\": ").Append(a.x0.ToString("F2"))
              .Append(", \"z0\": ").Append(a.z0.ToString("F2")).Append(", \"x1\": ").Append(a.x1.ToString("F2"))
              .Append(", \"z1\": ").Append(a.z1.ToString("F2")).Append(", \"tr\": ").Append(a.tr).Append("}")
              .Append(i + 1 < list.Count ? ",\n" : "\n");
        }
        sb.Append("  ]\n}\n");

        Directory.CreateDirectory(Path.GetDirectoryName(AshiatoPath));
        File.WriteAllText(AshiatoPath, sb.ToString());
        return "足あとを採った: " + list.Count + " ルート → " + AshiatoRel + "(置いたまま " + skipped + " 件)";
    }

    /// <summary>ルート1本の外接矩形。⛔ **ピボットで測らない** — 実メッシュの当たる範囲を採る
    /// (CLAUDE.md 規則21。囲いのピボットは邸の中心に無い)。</summary>
    static bool Measure(GameObject root, out Ashi a)
    {
        a = new Ashi { name = root.name };
        float x0 = float.MaxValue, z0 = float.MaxValue, x1 = float.MinValue, z1 = float.MinValue;
        var ts = root.GetComponentsInChildren<Transform>(true);
        a.tr = ts.Length;
        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
        {
            Bounds b;
            if (r.gameObject.activeInHierarchy && r.enabled) b = r.bounds;
            else
            {
                // ⚠ 非アクティブの Renderer の bounds は当てにならない。メッシュから起こす。
                var mf = r.GetComponent<MeshFilter>();
                if (mf == null || mf.sharedMesh == null) continue;
                var lb = mf.sharedMesh.bounds;
                b = new Bounds(r.transform.TransformPoint(lb.center), Vector3.zero);
                foreach (var s in Corners(lb)) b.Encapsulate(r.transform.TransformPoint(s));
            }
            x0 = Mathf.Min(x0, b.min.x); x1 = Mathf.Max(x1, b.max.x);
            z0 = Mathf.Min(z0, b.min.z); z1 = Mathf.Max(z1, b.max.z);
        }
        if (x0 > x1)   // Renderer が1つも無い(印だけのルート)— 位置で代用する
        {
            foreach (var t in ts)
            {
                var p = t.position;
                x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x);
                z0 = Mathf.Min(z0, p.z); z1 = Mathf.Max(z1, p.z);
            }
        }
        if (x0 > x1) return false;
        a.x0 = x0; a.z0 = z0; a.x1 = x1; a.z1 = z1;
        return true;
    }

    static IEnumerable<Vector3> Corners(Bounds b)
    {
        for (int i = 0; i < 8; i++)
            yield return new Vector3((i & 1) == 0 ? b.min.x : b.max.x,
                                     (i & 2) == 0 ? b.min.y : b.max.y,
                                     (i & 4) == 0 ? b.min.z : b.max.z);
    }

    // ---- 読む ----------------------------------------------------------------

    /// <summary>足あとの台帳を読む。無ければ空。</summary>
    public static List<Ashi> Ashiato()
    {
        var outp = new List<Ashi>();
        if (!File.Exists(AshiatoPath)) return outp;
        var root = EdoMiniJson.Parse(File.ReadAllText(AshiatoPath)) as Dictionary<string, object>;
        object items;
        if (root == null || !root.TryGetValue("items", out items)) return outp;
        foreach (var o in (List<object>)items)
        {
            var d = o as Dictionary<string, object>;
            if (d == null) continue;
            outp.Add(new Ashi
            {
                name = (string)d["n"],
                x0 = F(d, "x0"), z0 = F(d, "z0"), x1 = F(d, "x1"), z1 = F(d, "z1"),
                tr = (int)F(d, "tr"),
            });
        }
        return outp;
    }

    static float F(Dictionary<string, object> d, string k)
    {
        object v;
        if (!d.TryGetValue(k, out v) || v == null) return 0f;
        return System.Convert.ToSingle(v);
    }

    /// <summary>
    /// <paramref name="yashiki"/> の隣。間合い <paramref name="margin"/> m 以内に外接矩形が
    /// 掛かるルートを近い順に返す。台帳に的が居なければ空(隣なしで開く)。
    /// </summary>
    public static List<string> Tonari(string yashiki, float margin, int max)
    {
        var all = Ashiato();
        var outp = new List<string>();
        Ashi me = default(Ashi); bool found = false;
        foreach (var a in all) if (a.name == yashiki) { me = a; found = true; break; }
        if (!found) return outp;

        var hit = new List<KeyValuePair<float, string>>();
        foreach (var a in all)
        {
            if (a.name == yashiki || !me.Near(a, margin)) continue;
            // 間合い = 矩形どうしの距離(重なっていれば 0)
            float dx = Mathf.Max(0f, Mathf.Max(me.x0 - a.x1, a.x0 - me.x1));
            float dz = Mathf.Max(0f, Mathf.Max(me.z0 - a.z1, a.z0 - me.z1));
            hit.Add(new KeyValuePair<float, string>(Mathf.Sqrt(dx * dx + dz * dz), a.name));
        }
        hit.Sort((p, q) => p.Key.CompareTo(q.Key));
        foreach (var h in hit) { if (outp.Count >= max) break; outp.Add(h.Value); }
        return outp;
    }

    // ---- 名前の解決 --------------------------------------------------------

    /// <summary>
    /// 呼ぶ側が持っている呼び名(区画 id "matsudaira_dewa" / プレハブ名
    /// "Edo_Yashiki_MatsudairaDewa" / 類型 "Edo_Typo_okabe")からプレハブ名を当てる。
    /// ⚠ 当たらなければ null — **推測で別の邸を開かない**(松平は7家ある・CLAUDE.md 規則15)。
    /// </summary>
    public static string Resolve(string idOrName)
    {
        if (string.IsNullOrEmpty(idOrName)) return null;
        if (File.Exists(EdoYashikiPrefab.Dir + "/" + idOrName + ".prefab")) return idOrName;
        var typo = "Edo_Typo_" + idOrName;
        if (File.Exists(EdoYashikiPrefab.Dir + "/" + typo + ".prefab")) return typo;
        // 綴りを崩して1本だけ当たるなら採る。2本以上当たったら選ばない。
        var key = idOrName.Replace("_", "").Replace(" ", "").ToLowerInvariant();
        string hit = null; int n = 0;
        foreach (var f in Directory.GetFiles(EdoYashikiPrefab.Dir, "*.prefab"))
        {
            var stem = Path.GetFileNameWithoutExtension(f);
            if (stem.Replace("_", "").ToLowerInvariant().IndexOf(key, System.StringComparison.Ordinal) < 0) continue;
            hit = stem; n++;
        }
        return n == 1 ? hit : null;
    }

    /// <summary>呼び名で作業場を開く(<see cref="Resolve"/> → <see cref="Open"/>)。</summary>
    public static string OpenFor(string idOrName)
    {
        var name = Resolve(idOrName);
        if (name == null)
            return "⛔ 邸を特定できない: '" + idOrName + "'。プレハブ名(Edo_Yashiki_…)か区画 id で呼ぶこと";
        return Open(name);
    }
}

/// <summary>
/// 赤坂を開いたまま C# を直していたら、そのコンパイルの入口で ⚠ を出す(EDO-0282①)。
///
/// 実測 2026-09-21(`Logs/Editor.log` の1起動ぶん・`Tools/Unity/reload_cost.py`):
///   赤坂を開いたままのドメインリロード **15回 531秒**(中央値 34.3s・うち復元 397秒) /
///   作業場 **2回 11秒**(中央値 6.9s)。⇒ **その1起動で 428 秒が復元に溶けた。**
/// 人の記憶に頼ると忘れるので、コンパイルのたびに言う。
/// </summary>
[InitializeOnLoad]
static class EdoKobaNudge
{
    static EdoKobaNudge() { CompilationPipeline.compilationStarted += OnCompile; }

    static void OnCompile(object _)
    {
        if (UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene().path != EdoAssets.Scenes.Akasaka) return;
        Debug.LogWarning("⚠ 赤坂を開いたまま C# を直している — この後の復元だけで 30〜36 秒(作業場なら 6.9 秒・2026-09-21 実測)。\n"
                       + "  建て直しの輪は Edo/普請/作業場を開く(対象邸+隣+地形)で回すこと。→ EDO-0282①");
    }
}
