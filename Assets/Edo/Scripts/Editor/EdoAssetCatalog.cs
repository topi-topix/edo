using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Edo.EditorTools
{
    /// <summary>
    /// プロジェクト内の「置ける物」(プレハブ・モデル)を全部走査して、
    /// 実寸・ピボット・ポリゴン数・使用状況つきの目録を docs/ に書き出す。
    ///
    /// 目的: 「〜を再現して」と言われたときに、フォルダを掘らずに
    ///       grep 一発で「使える物があるか / 何mか」を引けるようにすること。
    ///
    /// 出力:
    ///   docs/asset-index.tsv           … 全件。grep 用(1行1アセット)
    ///   docs/asset-index-summary.md    … フォルダ別の件数と代表寸法。人が読む用
    ///
    /// メニュー: Edo ▸ アセット目録 ▸ 目録を再生成
    /// </summary>
    public static class EdoAssetCatalog
    {
        // 走査対象。ここに無いフォルダは目録に載らない。
        static readonly string[] Roots =
        {
            "Assets/Edo",
            "Assets/edogoyomi",
            "Assets/Japanese Castle",
            "Assets/Japanese Village Kit",
            "Assets/Waldemarst",
            "Assets/NatureManufacture Assets",
        };

        // 目録に載せるモデル拡張子(プレハブは別途 t:Prefab で拾う)
        static readonly string[] ModelExt = { ".fbx", ".obj", ".glb", ".gltf", ".blend" };

        const string ScenePath = "Assets/Edo/Scenes/Akasaka.unity";
        const string ScriptsRoot = "Assets/Edo/Scripts";

        [MenuItem("Edo/アセット目録/目録を再生成", false, 10)]
        public static void Regenerate()
        {
            var t0 = DateTime.Now;
            var sceneGuids = CollectSceneGuids();
            var scriptText = CollectScriptText();

            var paths = CollectAssetPaths();
            var rows = new List<Row>(paths.Count);

            try
            {
                for (int i = 0; i < paths.Count; i++)
                {
                    if (i % 25 == 0 &&
                        EditorUtility.DisplayCancelableProgressBar(
                            "アセット目録", $"{i}/{paths.Count}  {paths[i]}", (float)i / paths.Count))
                        break;

                    var row = Measure(paths[i], sceneGuids, scriptText);
                    if (row != null) rows.Add(row);
                }
            }
            finally
            {
                EditorUtility.ClearProgressBar();
            }

            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "docs"));
            Directory.CreateDirectory(dir);
            var tsv = Path.Combine(dir, "asset-index.tsv");
            var md = Path.Combine(dir, "asset-index-summary.md");

            File.WriteAllText(tsv, BuildTsv(rows), new UTF8Encoding(false));
            File.WriteAllText(md, BuildSummary(rows), new UTF8Encoding(false));

            Debug.Log($"[EdoAssetCatalog] {rows.Count} 件を書き出しました " +
                      $"({(DateTime.Now - t0).TotalSeconds:F1}s)\n{tsv}\n{md}");
        }

        // ---- 収集 -------------------------------------------------------

        static List<string> CollectAssetPaths()
        {
            var existing = Roots.Where(AssetDatabase.IsValidFolder).ToArray();
            var list = new List<string>();

            foreach (var guid in AssetDatabase.FindAssets("t:Prefab", existing))
                list.Add(AssetDatabase.GUIDToAssetPath(guid));

            foreach (var guid in AssetDatabase.FindAssets("t:Model", existing))
            {
                var p = AssetDatabase.GUIDToAssetPath(guid);
                if (ModelExt.Contains(Path.GetExtension(p).ToLowerInvariant())) list.Add(p);
            }

            return list.Distinct().OrderBy(p => p, StringComparer.OrdinalIgnoreCase).ToList();
        }

        /// <summary>シーンファイルを直接なめて参照 GUID を集める(依存解決より速い)。</summary>
        static HashSet<string> CollectSceneGuids()
        {
            var set = new HashSet<string>();
            var full = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ScenePath));
            if (!File.Exists(full)) return set;

            const string key = "guid: ";
            using (var sr = new StreamReader(full))
            {
                string line;
                while ((line = sr.ReadLine()) != null)
                {
                    int i = line.IndexOf(key, StringComparison.Ordinal);
                    if (i < 0) continue;
                    i += key.Length;
                    if (i + 32 > line.Length) continue;
                    set.Add(line.Substring(i, 32));
                }
            }
            return set;
        }

        /// <summary>ビルダー群が文字列で参照しているパスを判定するため全文を連結する。</summary>
        static string CollectScriptText()
        {
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ScriptsRoot));
            if (!Directory.Exists(root)) return string.Empty;
            var sb = new StringBuilder();
            foreach (var f in Directory.GetFiles(root, "*.cs", SearchOption.AllDirectories))
                sb.Append(File.ReadAllText(f)).Append('\n');
            return sb.ToString();
        }

        // ---- 計測 -------------------------------------------------------

        class Row
        {
            public string Path, Pack, Folder, Name, Kind, Shaders;
            public Vector3 Size, RootScale;
            public float PivotBottom;   // ピボットから見た最下端の y。0 なら足元がピボット
            public int Tris, Renderers;
            public bool InScene, InScript;
        }

        static Row Measure(string path, HashSet<string> sceneGuids, string scriptText)
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (go == null) return null;

            var rends = go.GetComponentsInChildren<MeshFilter>(true);
            var skins = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var hasBounds = false;
            var min = Vector3.positiveInfinity;
            var max = Vector3.negativeInfinity;
            int tris = 0;
            var shaders = new HashSet<string>();

            // ルート自身の TRS を含めて測る(= PrefabUtility.InstantiatePrefab した実寸)。
            // ルートに補正スケールを持つプレハブがあるので、ルートを打ち消してはいけない。
            void Accum(Mesh mesh, Transform tr)
            {
                if (mesh == null) return;
                var m = tr.localToWorldMatrix;
                var b = mesh.bounds;
                for (int c = 0; c < 8; c++)
                {
                    var corner = new Vector3(
                        (c & 1) == 0 ? b.min.x : b.max.x,
                        (c & 2) == 0 ? b.min.y : b.max.y,
                        (c & 4) == 0 ? b.min.z : b.max.z);
                    var p = m.MultiplyPoint3x4(corner);
                    min = Vector3.Min(min, p);
                    max = Vector3.Max(max, p);
                }
                hasBounds = true;
                for (int s = 0; s < mesh.subMeshCount; s++) tris += (int)(mesh.GetIndexCount(s) / 3);
            }

            foreach (var mf in rends) Accum(mf.sharedMesh, mf.transform);
            foreach (var sk in skins) Accum(sk.sharedMesh, sk.transform);

            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                foreach (var mat in r.sharedMaterials)
                    if (mat != null && mat.shader != null) shaders.Add(mat.shader.name);

            var size = hasBounds ? max - min : Vector3.zero;
            var guid = AssetDatabase.AssetPathToGUID(path);

            return new Row
            {
                Path = path,
                Pack = path.Split('/')[1],
                Folder = System.IO.Path.GetDirectoryName(path).Replace('\\', '/'),
                Name = System.IO.Path.GetFileNameWithoutExtension(path),
                Kind = System.IO.Path.GetExtension(path).TrimStart('.').ToLowerInvariant(),
                Size = size,
                RootScale = go.transform.localScale,
                PivotBottom = hasBounds ? min.y : 0f,
                Tris = tris,
                Renderers = go.GetComponentsInChildren<Renderer>(true).Length,
                Shaders = ShaderTag(shaders),
                InScene = sceneGuids.Contains(guid),
                InScript = scriptText.Contains(path),
            };
        }

        /// <summary>マテリアルのピンク化リスクを一目で見るための粗いタグ。</summary>
        static string ShaderTag(HashSet<string> shaders)
        {
            if (shaders.Count == 0) return "-";
            bool urp = shaders.Any(s => s.StartsWith("Universal Render Pipeline", StringComparison.Ordinal)
                                        || s.StartsWith("Shader Graphs", StringComparison.Ordinal)
                                        || s.StartsWith("Edo/", StringComparison.Ordinal)
                                        || s.StartsWith("NatureManufacture", StringComparison.Ordinal));
            bool builtin = shaders.Any(s => s == "Standard" || s.StartsWith("Legacy Shaders", StringComparison.Ordinal)
                                        || s == "Nature/SpeedTree8" || s == "Nature/SpeedTree");
            if (urp && !builtin) return "URP";
            if (builtin && !urp) return "BUILTIN";   // URP ではピンクになる
            return builtin ? "MIXED" : "OTHER";
        }

        // ---- 出力 -------------------------------------------------------

        static string F(float v) => v.ToString("0.##", CultureInfo.InvariantCulture);

        static string BuildTsv(List<Row> rows)
        {
            var sb = new StringBuilder();
            sb.AppendLine("# edo-unity アセット目録 — Edo ▸ アセット目録 ▸ 目録を再生成 で更新");
            sb.AppendLine("# 寸法は scale=1 のときの実寸[m]。pivot_bottom はピボットから最下端までの y");
            sb.AppendLine("# (0 なら足元がピボット。負なら足元がピボットより下)");
            sb.AppendLine("# root_scale: ルート自身の補正スケール(1 でなければ共通ヘルパに Vector3.one を渡すと化ける)");
            sb.AppendLine("# shader: BUILTIN = URP でピンクになる。use: S=シーンで使用中 / B=ビルダーが参照");
            sb.AppendLine("path\tname\tpack\tkind\tsx\tsy\tsz\tpivot_bottom\troot_scale\ttris\trenderers\tshader\tuse");
            foreach (var r in rows)
            {
                var use = (r.InScene ? "S" : "") + (r.InScript ? "B" : "");
                var rs = r.RootScale == Vector3.one
                    ? "1"
                    : F(r.RootScale.x) + "," + F(r.RootScale.y) + "," + F(r.RootScale.z);
                sb.Append(r.Path).Append('\t').Append(r.Name).Append('\t').Append(r.Pack).Append('\t')
                  .Append(r.Kind).Append('\t')
                  .Append(F(r.Size.x)).Append('\t').Append(F(r.Size.y)).Append('\t').Append(F(r.Size.z)).Append('\t')
                  .Append(F(r.PivotBottom)).Append('\t').Append(rs).Append('\t')
                  .Append(r.Tris).Append('\t').Append(r.Renderers).Append('\t')
                  .Append(r.Shaders).Append('\t').Append(use.Length == 0 ? "-" : use).AppendLine();
            }
            return sb.ToString();
        }

        static string BuildSummary(List<Row> rows)
        {
            var sb = new StringBuilder();
            sb.AppendLine("# アセット目録 — フォルダ別サマリ");
            sb.AppendLine();
            sb.AppendLine("`Edo ▸ アセット目録 ▸ 目録を再生成` で自動生成。全件は `asset-index.tsv`。");
            sb.AppendLine();
            sb.AppendLine($"- 総数 **{rows.Count}** 点 / シーンで使用中 **{rows.Count(r => r.InScene)}** 点 " +
                          $"/ ビルダーが参照 **{rows.Count(r => r.InScript)}** 点");
            sb.AppendLine($"- URP でピンクになる(BUILTIN) **{rows.Count(r => r.Shaders == "BUILTIN")}** 点");
            sb.AppendLine();

            foreach (var pack in rows.GroupBy(r => r.Pack).OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase))
            {
                sb.AppendLine($"## {pack.Key} — {pack.Count()} 点");
                sb.AppendLine();
                sb.AppendLine("| フォルダ | 点数 | 幅の中央値[m] | 高さの中央値[m] | 使用中 |");
                sb.AppendLine("|---|---:|---:|---:|---:|");
                foreach (var g in pack.GroupBy(r => r.Folder).OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase))
                {
                    var w = Median(g.Select(r => Mathf.Max(r.Size.x, r.Size.z)));
                    var h = Median(g.Select(r => r.Size.y));
                    var used = g.Count(r => r.InScene || r.InScript);
                    sb.AppendLine($"| `{g.Key}` | {g.Count()} | {F(w)} | {F(h)} | {used} |");
                }
                sb.AppendLine();
            }
            return sb.ToString();
        }

        static float Median(IEnumerable<float> src)
        {
            var a = src.OrderBy(v => v).ToArray();
            if (a.Length == 0) return 0f;
            return a.Length % 2 == 1 ? a[a.Length / 2] : (a[a.Length / 2 - 1] + a[a.Length / 2]) * 0.5f;
        }
    }
}
