using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using Scene = UnityEngine.SceneManagement.Scene;

/// <summary>
/// **コードで起こすメッシュは、必ず資産にする**(EDO-0332。材質の <see cref="EdoSolidMat"/> の兄弟)。
///
/// `new Mesh()` の戻り値は資産でない。シーンに割り当てるとシーンファイルへ埋め込まれ、見た目は正しい。
/// だが**プレハブへ焼くと資産側の m_Mesh が null になる** — シーンでは override が効くので気づけないまま、
/// そのプレハブを別の場所へ置いた途端に**その部材だけ消える**。
/// 実測(2026-09-21): 大的場の `Azuchi`(安土の土壇)と成満寺の `Yane`(鐘楼の宝形屋根)の 2 枚がこれで、
/// この 2 邸だけ EDO-0301 の材質の焼き込みも通らなかった(焼くとメッシュが null になるため門番が断っていた)。
///
/// ここは起こしたメッシュを <c>AssetDatabase.CreateAsset</c> で
/// `Assets/Edo/Meshes/Gen/&lt;名&gt;_&lt;中身の指紋&gt;.asset` に落として返す。
/// **中身が同じなら同じ 1 枚**(指紋は頂点と三角の生のビット)なので、同じ形を何度起こしても資産は増えない。
///
/// ⭐ 置く側の作法: `go.AddComponent&lt;MeshFilter&gt;().sharedMesh = EdoSolidMesh.Save(mesh, "Azuchi");`
///   — `new Mesh()` をそのまま `sharedMesh` へ入れない。
/// </summary>
public static class EdoSolidMesh
{
    // ───────────────────────────── 起こす側 ─────────────────────────────

    /// <summary>起こしたメッシュを資産にして返す。中身が同じ資産が既にあればそれを返し、
    /// 渡されたメッシュは捨てる(同じ形で資産が増えない)。<paramref name="name"/> は読むための名前で、
    /// 同じ名前でも中身が違えば別の 1 枚になる。</summary>
    public static Mesh Save(Mesh m, string name)
    {
        if (m == null) return null;
        if (AssetDatabase.Contains(m)) return m;                 // もう資産(二度呼んでも安全)
        string path = EdoAssets.Own.GenMesh(Sanitize(name) + "_" + Fingerprint(m));
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing != null) { Object.DestroyImmediate(m); return existing; }
        EnsureFolder(EdoAssets.Own.GenMeshDir);
        m.name = Path.GetFileNameWithoutExtension(path);
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    /// <summary>名前引き。資産が既にあれば <paramref name="build"/> を**走らせない**。
    /// ⚠ 形を変えたら名前も変えること(中身で引かないので古い資産が居座る)。</summary>
    public static Mesh Get(string name, System.Func<Mesh> build)
    {
        string path = EdoAssets.Own.GenMesh(Sanitize(name));
        var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (m != null) return m;
        m = build();
        if (m == null) return null;
        EnsureFolder(EdoAssets.Own.GenMeshDir);
        m.name = Sanitize(name);
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    /// <summary>中身の指紋(頂点と三角の生のビットの FNV-1a・8 桁)。⛔ 座標を丸めない —
    /// 1mm 違う別物を同じ 1 枚にしてしまう。</summary>
    static string Fingerprint(Mesh m)
    {
        unchecked
        {
            ulong h = 1469598103934665603UL;
            var verts = m.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                h = Mix(h, System.BitConverter.SingleToInt32Bits(verts[i].x));
                h = Mix(h, System.BitConverter.SingleToInt32Bits(verts[i].y));
                h = Mix(h, System.BitConverter.SingleToInt32Bits(verts[i].z));
            }
            for (int s = 0; s < m.subMeshCount; s++)
            {
                var tri = m.GetTriangles(s);
                h = Mix(h, s * 7919 + 13);
                for (int i = 0; i < tri.Length; i++) h = Mix(h, tri[i]);
            }
            return (h ^ (h >> 32)).ToString("x16").Substring(0, 8);
        }
    }

    static ulong Mix(ulong h, int v)
    {
        unchecked
        {
            for (int i = 0; i < 4; i++) { h ^= (byte)(((uint)v) >> (i * 8)); h *= 1099511628211UL; }
            return h;
        }
    }

    static string Sanitize(string s)
    {
        var sb = new System.Text.StringBuilder();
        foreach (char c in s) sb.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
        return sb.Length == 0 ? "Mesh" : sb.ToString();
    }

    static void EnsureFolder(string folder)
    {
        if (AssetDatabase.IsValidFolder(folder)) return;
        string parent = Path.GetDirectoryName(folder).Replace('\\', '/');
        EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
    }

    // ───────────────── 既存シーンの「資産でないメッシュ」を直す ─────────────────

    /// <summary>資産でない(=シーンにしか居ない)メッシュか。
    /// ⚠ 一時的な効果用(<c>hideFlags</c> つき。UnderwaterEffect の板など)は対象外 — 保存もされない。</summary>
    static bool IsLoose(Mesh m)
    {
        return m != null && m.hideFlags == HideFlags.None && !AssetDatabase.Contains(m);
    }

    /// <summary>資産でないメッシュが何枚・どのルートに居るか(検査。書き換えない)。
    /// `Edo/屋敷/切り出し状況を検査` がこれを 1 行で出す — 0 になっていれば直っている。</summary>
    public static string CountLoose(Scene scene)
    {
        var meshes = new HashSet<Mesh>();
        var where = new List<string>();
        foreach (var r in scene.GetRootGameObjects())
            foreach (var mf in r.GetComponentsInChildren<MeshFilter>(true))
                if (IsLoose(mf.sharedMesh) && meshes.Add(mf.sharedMesh))
                    where.Add(r.name + "/" + mf.gameObject.name
                            + (EdoYashikiPrefab.BakeTargetFor(mf) != null ? "(プレハブ)" : ""));
        return $"資産でないメッシュ={meshes.Count} 枚"
             + (where.Count > 0 ? ": " + string.Join(", ", where) : "");
    }

    [MenuItem("Edo/屋敷/埋め込みメッシュを資産へ(検査)")]
    public static void CountLooseMenu()
    {
        Debug.Log("[EdoSolidMesh] " + CountLoose(UnityEngine.SceneManagement.SceneManager.GetActiveScene()));
    }

    /// <summary>
    /// シーンの「資産でないメッシュ」を資産へ落として付け替え、**プレハブ資産の側へも焼く**(EDO-0332)。
    /// 同じメッシュを指す <see cref="MeshCollider"/> も一緒に付け替える(片方だけ直すと当たりが消える)。
    ///
    /// 焼き方は材質と同じ — 最寄りの邸のプレハブインスタンスへ <c>ApplyPrefabInstance</c>。
    /// 判定は <see cref="EdoYashikiPrefab.BakeAssetSwaps"/> が持つので、材質の付け替えが済んでいる
    /// インスタンスなら**同じ 1 回で材質も焼ける**(この 2 邸が EDO-0301 で焼けなかった理由がこれ)。
    /// <paramref name="onlyRoots"/> を渡すとそのルートだけ。null なら全ルート。
    /// </summary>
    public static string Migrate(Scene scene, ICollection<string> onlyRoots = null)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        // ⭐ **先に全部の参照を集めてから資産にする。** Save は同じ形の資産が既にあると渡されたメッシュを
        //   捨てるので、あとから mf.sharedMesh を読み直すと消えた物を掴む(他の枠が null のまま残る)。
        var users = new Dictionary<Mesh, List<Component>>();   // 資産でないメッシュ → それを指す枠
        var label = new Dictionary<Mesh, string>();            // → 資産の名(<邸>_<物>)
        foreach (var root in scene.GetRootGameObjects())
        {
            if (onlyRoots != null && !onlyRoots.Contains(root.name)) continue;
            string stem = root.name.StartsWith("Edo_") ? root.name.Substring(4) : root.name;
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
                Note(users, label, mf.sharedMesh, mf, stem + "_" + mf.gameObject.name);
            // 当たり(MeshCollider)が同じメッシュを指していたら一緒に付け替える(片方だけ直すと当たりが消える)
            foreach (var mc in root.GetComponentsInChildren<MeshCollider>(true))
                Note(users, label, mc.sharedMesh, mc, stem + "_" + mc.gameObject.name);
        }

        var instances = new HashSet<GameObject>();
        var plain = new HashSet<string>();                // プレハブでないルート(焼く先が無い)
        var kitOnly = new HashSet<string>();              // 焼く先が邸のプレハブの外しか無いルート
        int slots = 0, cols = 0;
        // ⛔ StartAssetEditing で囲まない — 中で起こした資産は Load できず、同じ形を二重に起こしてしまう
        foreach (var kv in users)
        {
            var asset = Save(kv.Key, label[kv.Key]);
            if (asset == null) continue;
            foreach (var c in kv.Value)
            {
                Repoint(c, "m_Mesh", asset);
                if (c is MeshCollider) cols++; else slots++;
                var near = EdoYashikiPrefab.BakeTargetFor(c);
                if (near != null) instances.Add(near);
                else if (!PrefabUtility.IsPartOfPrefabInstance(c)) plain.Add(c.transform.root.name);
                else kitOnly.Add(c.transform.root.name);
            }
        }
        AssetDatabase.SaveAssets();

        int baked; string refused = EdoYashikiPrefab.BakeAssetSwaps(instances, out baked);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
        return $"資産にしたメッシュ {users.Count} 枚 / 付け替え {slots} 枠(当たり {cols} 枠) / 焼いたインスタンス {baked}/{instances.Count}"
             + (kitOnly.Count > 0 ? $" / ⛔ 焼く先が邸のプレハブの外 {kitOnly.Count}({string.Join(",", kitOnly)})" : "")
             + (plain.Count > 0 ? $" / プレハブでないルート {plain.Count}({string.Join(",", plain)})" : "")
             + (refused.Length > 0 ? "\n⛔ 焼かなかった: " + refused : "")
             + $"  ms={sw.ElapsedMilliseconds}";
    }

    static void Note(Dictionary<Mesh, List<Component>> users, Dictionary<Mesh, string> label,
                     Mesh m, Component c, string name)
    {
        if (!IsLoose(m)) return;
        if (!users.TryGetValue(m, out var list)) { users[m] = list = new List<Component>(); label[m] = name; }
        list.Add(c);
    }

    /// <summary>プレハブの override として正しく記録されるよう SerializedObject 経由で差し替える。</summary>
    static void Repoint(Component c, string prop, Object asset)
    {
        var so = new SerializedObject(c);
        so.FindProperty(prop).objectReferenceValue = asset;
        so.ApplyModifiedPropertiesWithoutUndo();
    }

    [MenuItem("Edo/屋敷/埋め込みメッシュを資産へ(選択中のルートだけ)")]
    public static void MigrateSelectedMenu()
    {
        var names = new HashSet<string>();
        foreach (var o in Selection.gameObjects) names.Add(o.transform.root.name);
        if (names.Count == 0) { Debug.LogWarning("ルートを選択してから実行してください"); return; }
        Debug.Log("[EdoSolidMesh] " + Migrate(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), names));
    }

    [MenuItem("Edo/屋敷/埋め込みメッシュを資産へ(全ルート)")]
    public static void MigrateAllMenu()
    {
        Debug.Log("[EdoSolidMesh] " + Migrate(UnityEngine.SceneManagement.SceneManager.GetActiveScene()));
    }
}
