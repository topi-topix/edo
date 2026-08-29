// 長さ可変の表長屋(Blender 生成の FBX)を Unity 側で使えるようにする。
//
// 部材の生成は Tools/Blender/build_nagaya_omote.py。パスは EdoAssets.Own.NagayaOmote(len)。
// 素は edogoyomi の `knagaya01c/l/r` を窓割り(bay = 2.6874m)で切って並べたもので、
// マテリアルは **`knagayamap` 1枚だけ**。
//
// ⚠ FBX にはマテリアル**名**しか入らない。remap しないと真っ白な模型で出る。
// ⚠ さらに `SearchAndRemapMaterials` は**独立した .mat しか探さない**。edogoyomi の
//   直線材はマテリアルを .obj の中に**サブアセットとして抱えている**ので、名前が一致していても
//   当たらない(2026-08-19 に隅部材で実際に出た。EdoOkabeYashikiBuilder.BindDonorMaterials の注)。
//   → 提供元の .obj を丸ごと読み、同名のマテリアルを AddRemap で名指しで結ぶ。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoNagayaOmote
{
    public const string ModelDir = "Assets/Edo/Models/Nagaya";

    /// <summary>表長屋 FBX のマテリアルを、素の .obj が抱えている `knagayamap` へ結び直す。
    /// 新しい長さを Blender で出すたびに走らせる。</summary>
    [MenuItem("Edo/長屋/表長屋のマテリアルをremap")]
    public static void RemapMenu() { Debug.Log("[NagayaOmote] " + Remap()); }

    public static string Remap()
    {
        if (!AssetDatabase.IsValidFolder(ModelDir)) return ModelDir + " が無い";
        // 借り先は edogoyomi の直線材そのもの。ここ以外は舐めない
        // (プロジェクト全体 6.9GB を Everywhere で舐めるとユーザーの PC が固まる。2026-08-24)
        var byName = new Dictionary<string, Material>();
        foreach (var d in new[] { EdoAssets.Eg.KnagayaC, EdoAssets.Eg.KnagayaL, EdoAssets.Eg.KnagayaR })
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(d))
            {
                var m = o as Material;
                if (m != null && !byName.ContainsKey(m.name)) byName[m.name] = m;
            }

        int n = 0; var miss = new List<string>();
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { ModelDir }))
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
        return "remap " + n + " 本" + (miss.Count > 0 ? " / 借り先が見つからない材: " + string.Join(", ", miss.ToArray()) : "");
    }
}
