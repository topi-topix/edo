// FBX の材を「借り先を名指しして」結び直す — 全邸で1本(EDO-0318 (a)・2026-09-21)。
//
// ⛔ **この処理の4本目の写しを作らない。**2026-09-21 まで、岡部・山王・松江松平の3つの邸ビルダーに
//    **同じ 30 行が3回**書いてあり、違うのは借り先(donorDirs)と対象(modelDirs)の並びだけだった。
//    その結果、新しく焼いた部材はどれか1つの写しの並びに足されるだけで、
//    「どの写しも見ていないフォルダ」が生まれる。実際に起きたこと:
//      ・2026-08-31 番所(Models/Mon)— 松江松平の写しが Fuzokuya しか見ておらず真っ白
//      ・2026-09-04 新造の木(Models/Trees)— 岡部の写しに無く真っ白
//      ・2026-09-06 立石(Models/Niwa)— 同上
//      ・2026-09-21 鐘楼・墓地(Models/Jisha)— **どの写しも見ていない**。しかも鐘楼の梵鐘は
//        Japanese Castle の `Ornament` で、この材が在る **Interior/Materials** を
//        どの写しも借り先に持っていなかった(EDO-0318 ③)。
//    ⇒ 芯を <see cref="EdoRemapMat.Run"/> 1本にして、各メニューは**並びを渡すだけ**にした。
//
// ⚠ `SearchAndRemapMaterials(..., Everywhere)` は使わない — プロジェクト全体(6.9GB)を舐めて
//    2026-08-24 にユーザーの PC が固まった。借り先は渡されたフォルダだけを見る。
// ⚠ FBX は材質の**名前**しか運ばない。焼いたフォルダを modelDirs に足し忘れると、
//    黙って真っ白のまま出る(上の事故4件はすべてこの型)。

using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoRemapMat
{
    /// <summary>借り先(<paramref name="donorDirs"/>)の .mat を名前で引き、
    /// 対象(<paramref name="modelDirs"/>)の FBX が名乗る材質名をそこへ結び直す。
    ///
    /// <para>⭐ <paramref name="donorDirs"/> は**先に書いた方が勝つ**(同名の .mat が複数あるとき)。
    /// フォルダは**再帰的に**舐めるので、`Assets/Edo/Materials` を渡せば
    /// `Assets/Edo/Materials/Sanno/Kirishi.mat` も拾える。</para>
    ///
    /// <para>⭕ 冪等 — 既に同じ .mat へ結ばれている材は触らない(`donor == m` で飛ばす)ので、
    /// 何度打っても FBX の再取り込みは起きない。</para>
    ///
    /// <para>⛔ 結べなかった材質名は**捨てずに戻り値へ刷る**(規則19)。
    /// 「remap n 本」だけだと、借り先の無い材が黙って真っ白のまま残る。</para></summary>
    /// <param name="label">戻り値の頭に付ける呼び名(「新造部材」「類型の部材」など)。</param>
    public static string Run(string[] donorDirs, string[] modelDirs, string label)
    {
        return Run(ByFolder(donorDirs), modelDirs, label);
    }

    /// <summary>借り先のフォルダを名前表へ畳む。先に書いたフォルダが勝つ。</summary>
    public static Dictionary<string, Material> ByFolder(string[] donorDirs)
    {
        var byName = new Dictionary<string, Material>();
        foreach (var dir in donorDirs)
        {
            if (!AssetDatabase.IsValidFolder(dir)) continue;
            foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { dir }))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                if (m != null && !byName.ContainsKey(m.name)) byName[m.name] = m;
            }
        }
        return byName;
    }

    /// <summary>借り先が**フォルダの .mat ではない**とき用(<see cref="EdoNagayaOmote"/> の表長屋は
    /// edogoyomi の直線材が材を .obj の**サブアセット**として抱えているので、
    /// <c>AssetDatabase.FindAssets("t:Material", dir)</c> では引けない)。</summary>
    public static string Run(Dictionary<string, Material> byName, string[] modelDirs, string label)
    {
        // ⚠ まだ Unity が取り込んでいないフォルダを渡すと FindAssets が落ちる
        modelDirs = System.Array.FindAll(modelDirs, AssetDatabase.IsValidFolder);
        if (modelDirs.Length == 0) return label + ": 対象フォルダが無い";
        int n = 0; var miss = new List<string>();
        foreach (var guid in AssetDatabase.FindAssets("t:Model", modelDirs))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter; if (imp == null) continue;
            imp.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path); if (go == null) continue;
            bool touched = false;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    Material donor;
                    if (!byName.TryGetValue(m.name, out donor)) { if (!miss.Contains(m.name)) miss.Add(m.name); continue; }
                    if (donor == m) continue;
                    imp.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), m.name), donor);
                    touched = true;
                }
            if (touched)
            {
                AssetDatabase.WriteImportSettingsIfDirty(path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                n++;
            }
        }
        AssetDatabase.SaveAssets();
        return label + ": remap " + n + " 本"
             + (miss.Count > 0 ? " / ⛔ 借り先が見つからない材: " + string.Join(", ", miss.ToArray()) : "");
    }

    // ───────────────────────── 類型の部材(邸に属さない・88区画で共用)─────────────────────────
    /// <summary>**類型ビルダーが建てる部材**の材を結び直す(EDO-0318)。
    /// 邸ごとのメニューでは当たらない — 類型の部材はどの邸の持ち物でもないから。
    ///
    /// <para>対象(2026-09-21): 裏長屋 `Models/Nagaya/Typ_UraNagaya_*` / 山門・薬医門・棟門 `Models/Mon` /
    /// 鐘楼・墓地 `Models/Jisha` / 厩・米蔵・作事小屋 `Models/Fuzokuya/Typ_*`。</para>
    ///
    /// <para>⚠ **借り先に Japanese Castle の `Interior/Materials` が要る** — 鐘楼の梵鐘が名乗る
    /// `Ornament` はそこにしか無く、邸の3つのメニューはどれも `Exterior/Materials` しか見ていない。
    /// ⚠ 基壇・縁石・墓石は `Kirishi`(`Assets/Edo/Materials/Sanno/Kirishi.mat`)。
    /// ⛔ `Foundation_A_01`(玉石積み)へ当て直さない — 墓石が「小石を積んだ山」に見える。</para></summary>
    [MenuItem("Edo/類型/新造部材のマテリアルをremap")]
    public static void RemapTypologyMenu() { Debug.Log("[類型] " + RemapTypology()); }
    public static string RemapTypology()
    {
        string[] donorDirs = {
            "Assets/Japanese Village Kit/Materials",
            "Assets/Japanese Castle/Meshes/Exterior/Materials",
            "Assets/Japanese Castle/Meshes/Interior/Materials",   // ⭐ 梵鐘の `Ornament`
            "Assets/Edo/Materials",                               // 再帰 ⇒ Sanno/Kirishi.mat も拾う
            "Assets/Waldemarst/FreeJapaneseGarden/Materials",
        };
        string[] modelDirs = {
            "Assets/Edo/Models/Nagaya", "Assets/Edo/Models/Mon",
            "Assets/Edo/Models/Jisha",  "Assets/Edo/Models/Fuzokuya",
        };
        return Run(donorDirs, modelDirs, "類型の部材");
    }
}
