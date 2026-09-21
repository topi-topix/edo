// 旧邸の重複を畳む (2026-09-21・EDO-0299 ④ / 施主裁定A)
//
// 【何の道具か】
//   全区画をまず類型で建てる方針(CLAUDE.md「制作パイプライン」)に切り替えた結果、
//   類型が持つ区画の上に、廃止した街区ビルダーが建てた旧邸 Edo_Yashiki_* が重なって残った。
//   この道具は、その重なりを **区画の多角形だけで機械的に** 見分けて畳む。
//
// 【⛔ 名前で当てない】
//   どの旧邸がどの区画かを名前から当てるのは 2026-09-21 に三度外した。判定は必ず、
//   ルート配下の Renderer の bounds 中心(世界 xz)を数えて、最も多く入った区画を採る。
//   その区画の類型表の built が hand なら **必ず残す**(図から起こした邸・手組み資産)。
//
// 【使い方】Edo/屋敷/旧邸の重複を検める → 表を読む → Edo/屋敷/旧邸の重複を畳む
//   畳むほうはシーンからルートを外し、対応する Edo_Yashiki_*.prefab も消す。
//   ⛔ 押す前にシーンを保存しておくこと(戻すのは Undo ではなく git)。
//   ⛔ 「プレハブへ書き戻す(全部・強制)」は押さない(docs/lessons.md・シーンが膨らむ)。
using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class EdoDupYashiki
{
    const string Root = "Edo_Yashiki_";
    const string PrefabDir = "Assets/Edo/Prefabs/Scene/";

    /// <summary>ルート go が最も多くの実体を置いている区画の id。判らなければ null。</summary>
    public static string ParcelOf(GameObject go, out int votes, out int total)
    {
        var tally = new Dictionary<string, int>();
        total = 0;
        foreach (var rd in go.GetComponentsInChildren<Renderer>(true))
        {
            var c = rd.bounds.center;
            var p = new Vector2(c.x, c.z);
            total++;
            foreach (var pc in EdoParcels.All)
                if (EdoGeom.PIP(pc.Poly, p)) { tally[pc.id] = tally.ContainsKey(pc.id) ? tally[pc.id] + 1 : 1; break; }
        }
        string best = null; votes = 0;
        foreach (var kv in tally) if (kv.Value > votes) { votes = kv.Value; best = kv.Key; }
        return best;
    }

    /// <summary>畳める旧邸(= hand でない区画に載る Edo_Yashiki_*)を、区画 id つきで並べる。</summary>
    public static List<KeyValuePair<GameObject, string>> Survey(StringBuilder log)
    {
        var outp = new List<KeyValuePair<GameObject, string>>();
        var scene = EditorSceneManager.GetActiveScene();
        foreach (var r in scene.GetRootGameObjects())
        {
            if (!r.name.StartsWith(Root)) continue;
            int v, t;
            string pid = ParcelOf(r, out v, out t);
            if (pid == null) { if (log != null) log.AppendLine("? " + r.name + " — 区画に載っていない(手で見ること)"); continue; }
            // 類型表に無い区画は「判らない」であって「畳んでよい」ではない(規則19)。残す側へ倒す。
            EdoTypologyBuilder.Spec spec;
            bool known = EdoTypologyBuilder.Table.TryGetValue(pid, out spec);
            bool hand = !known || spec.Hand;
            if (log != null)
                log.AppendLine((hand ? "残 " : "畳 ") + r.name + " → " + pid + (known ? "" : "(類型表に無い)") + "  " + v + "/" + t);
            if (!hand) outp.Add(new KeyValuePair<GameObject, string>(r, pid));
        }
        return outp;
    }

    [MenuItem("Edo/屋敷/旧邸の重複を検める")]
    public static void MenuSurvey()
    {
        var sb = new StringBuilder();
        var dup = Survey(sb);
        Debug.Log("[旧邸の重複] 畳める " + dup.Count + " 本(区画の多角形で判定・hand の区画は残す)\n" + sb);
    }

    [MenuItem("Edo/屋敷/旧邸の重複を畳む")]
    public static void MenuCollapse()
    {
        var sb = new StringBuilder();
        var dup = Survey(sb);
        if (dup.Count == 0) { Debug.Log("[旧邸の重複] 畳む物は無い"); return; }
        if (!EditorUtility.DisplayDialog("旧邸の重複を畳む",
                dup.Count + " 本のルートをシーンから外し、同名のプレハブも消します。\n" +
                "戻すのは git です。先にシーンを保存しておいてください。\n\n" + sb,
                "畳む", "やめる")) return;

        int gone = 0, assets = 0;
        foreach (var kv in dup)
        {
            string name = kv.Key.name;
            Object.DestroyImmediate(kv.Key);
            gone++;
            string path = PrefabDir + name + ".prefab";
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) != null && AssetDatabase.DeleteAsset(path)) assets++;
        }
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        AssetDatabase.Refresh();
        Debug.Log("[旧邸の重複] ルート " + gone + " 本・プレハブ " + assets + " 本を畳んだ。シーンを保存すること。\n" + sb);
    }
}
