using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 石垣ピースの「現在位置」に地形を馴染ませるツール。
/// ・背面(陸側)の地形を石垣の天端まで上げて、壁と土地の隙間を埋める。
/// ・前面(水側)の地形を水面下まで下げて、石の面を露出させる（埋もれ防止）。
///
/// 使い方: 石垣ピース(または親 Edo_Ishigaki_SE)を選択 → ボタン。
///   何も選択していなければ Edo_Ishigaki_SE の全ピースが対象。
///   手で石垣を動かしたあとに押せば、その実位置に合わせて埋め直せる。
///
/// 各ピースの「水向き」= transform.right（配置時に石の面=ローカル+X を水側へ向けているため）。
/// メニュー: Edo ▸ 地形 ▸ 石垣に地形を馴染ませる
/// </summary>
public class EdoIshigakiFit : EditorWindow
{
    float backFill = 9f;   // 背面(陸側)を上げる幅(m)
    float faceExpose = 9f; // 前面(水側)を下げて石を出す幅(m)
    float footBelow = 4f;  // 水面からどれだけ下まで掘るか(m)
    float topDrop = 0.7f;  // 陸側の埋め高さを天端より下げる量(m)。ギザギザ縁をスカートの下に隠すため
    bool doFill = true, doExpose = true;
    string groupName = "Edo_Ishigaki_SE";
    const string SkirtName = "Edo_Ishigaki_Skirt";

    [MenuItem("Edo/地形/石垣に地形を馴染ませる")]
    static void Open() => GetWindow<EdoIshigakiFit>("Ishigaki Fit");

    void OnGUI()
    {
        EditorGUILayout.HelpBox(
            "石垣を選択 → ボタン。未選択なら " + groupName + " の全ピースが対象。\n" +
            "各石の実ジオメトリの『背面端』を境界に、そこで垂直の段差を作ります:\n" +
            "・背面の隙間を埋める = 境界より陸側を天端まで一律に上げる\n" +
            "・石を出す = 境界より水側(石の真下含む)を水面下まで一律に下げる\n" +
            "→ 反りの裏に土が隠れ、前面の三角残りも消えます。手で動かした後も実位置に追従。", MessageType.Info);
        doFill = EditorGUILayout.Toggle("背面の隙間を埋める", doFill);
        doExpose = EditorGUILayout.Toggle("石を出す(水側を掘る)", doExpose);
        backFill = EditorGUILayout.Slider("埋める幅(m,陸側)", backFill, 2f, 20f);
        faceExpose = EditorGUILayout.Slider("掘る幅(m,水側)", faceExpose, 2f, 20f);
        footBelow = EditorGUILayout.Slider("水面下の掘り(m,深さ)", footBelow, 1f, 10f);

        GUI.backgroundColor = new Color(0.6f, 1f, 0.6f);
        if (GUILayout.Button("▶ 選択(または全石垣)に地形を馴染ませる", GUILayout.Height(34))) Apply();
        GUI.backgroundColor = new Color(0.7f, 0.9f, 1f);
        if (GUILayout.Button("▶ 土手スカート生成(接合部の隙間/カクつきをメッシュで覆う)", GUILayout.Height(28))) BuildSkirt();
        GUI.backgroundColor = new Color(1f, 0.9f, 0.6f);
        if (GUILayout.Button("▶ 入隅フィラー挿入(屈曲部の壁の隙間を重ねて塞ぐ)")) AddCornerFillers();
        if (GUILayout.Button("▶ 端部の袖盛り土(石垣の両端を土手に埋める)")) BuildEndMounds();
        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("順番: ①馴染ませる → ②入隅フィラー → ③袖盛り土 → ④スカート生成。\n" +
            "地形は2m格子なので境界は必ずカクつく。スカートは石垣の天端裏に接着した草の帯メッシュで、" +
            "その原理的なカクつき/隙間を覆い隠す。", MessageType.None);

        EditorGUILayout.Space(6);
        EditorGUILayout.LabelField("地形の復元", EditorStyles.boldLabel);
        EditorGUILayout.LabelField("セーフティ", System.IO.File.Exists(SafetyPath)
            ? "保存あり: " + System.IO.File.GetLastWriteTime(SafetyPath).ToString("MM/dd HH:mm")
            : "保存なし");
        GUI.backgroundColor = new Color(0.6f, 0.8f, 1f);
        if (GUILayout.Button("📸 今の地形をセーフティ保存")) SaveSafety();
        GUI.backgroundColor = new Color(1f, 0.8f, 0.4f);
        using (new EditorGUI.DisabledScope(!System.IO.File.Exists(SafetyPath)))
            if (GUILayout.Button("↩ セーフティ地形に戻す(端の変形を消す)"))
                if (EditorUtility.DisplayDialog("地形を戻す", "保存したセーフティ地形に戻します。よろしいですか？", "戻す", "やめる")) Restore();
        GUI.backgroundColor = Color.white;
    }

    /// <summary>
    /// 土手スカート: 各石垣ピースの背面天端エッジ(実ジオメトリ)に前縁を接着し、
    /// 陸側へ約5mなだらかに下って地形の下に潜るリボンメッシュ。
    /// ハイトマップ解像度(2m格子)では原理的に消せない接合部のカクつき/隙間を、メッシュ同士の接合で覆い隠す。
    /// </summary>
    void BuildSkirt()
    {
        var terr = Terrain.activeTerrain; if (terr == null) return;
        var tpos = terr.transform.position;
        var grp = GameObject.Find(groupName); if (grp == null) { ShowNotification(new GUIContent(groupName + " がありません")); return; }
        var roots = new List<Transform>(); foreach (Transform c in grp.transform) roots.Add(c);
        roots.Sort((a, b) => a.GetSiblingIndex().CompareTo(b.GetSiblingIndex()));

        var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        foreach (var rt in roots)
        {
            Vector3 right = rt.right; right.y = 0; if (right.sqrMagnitude < 1e-4f) continue; right.Normalize();
            Vector3 fwd = Vector3.Cross(Vector3.up, right).normalized;
            float backP = 1e9f, topY = -1e9f, minS = 1e9f, maxS = -1e9f;
            foreach (var mf in rt.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var lb = mf.sharedMesh.bounds; var mtx = mf.transform.localToWorldMatrix;
                for (int ci = 0; ci < 8; ci++)
                {
                    Vector3 lc = lb.center + Vector3.Scale(lb.extents,
                        new Vector3((ci & 1) == 0 ? -1 : 1, (ci & 2) == 0 ? -1 : 1, (ci & 4) == 0 ? -1 : 1));
                    Vector3 wc = mtx.MultiplyPoint3x4(lc);
                    float pr = Vector3.Dot(wc, right); if (pr < backP) backP = pr;
                    float ps = Vector3.Dot(wc, fwd); if (ps < minS) minS = ps; if (ps > maxS) maxS = ps;
                    if (wc.y > topY) topY = wc.y;
                }
            }
            if (topY < -1e8f) continue;
            minS -= 0.4f; maxS += 0.4f; // 隣ピースと重ねて切れ目を防ぐ
            var layer0 = AssetDatabase.LoadAssetAtPath<TerrainLayer>("Assets/Edo/Terrain/layers/L_grass.terrainlayer");
            float tile = (layer0 != null) ? layer0.tileSize.x : 4f;
            float[] D = { 0.20f, -1.8f, -4.5f, -7.0f, -9.5f }; // 前縁(石内)→裾。長め=カクつきの影も覆う
            const int cols = 5; int rows = D.Length; int b0 = verts.Count;
            for (int c = 0; c < cols; c++)
            {
                float s = Mathf.Lerp(minS, maxS, (float)c / (cols - 1));
                // 前縁の揺らぎ: 草が石の上に不規則にかかるようにして「綺麗すぎる境目」を消す
                Vector3 probe = right * backP + fwd * s;
                float inset = Mathf.Lerp(0.08f, 0.55f, Mathf.PerlinNoise(probe.x * 0.33f + 7.1f, probe.z * 0.33f + 3.7f));
                float dropv = Mathf.Lerp(0.02f, 0.13f, Mathf.PerlinNoise(probe.x * 0.51f, probe.z * 0.51f));
                Vector3 prev = Vector3.zero;
                for (int r2 = 0; r2 < rows; r2++)
                {
                    Vector3 v = right * (backP + ((r2 == 0) ? inset : D[r2])) + fwd * s;
                    if (r2 == 0) v.y = topY - dropv;
                    else if (r2 == 1) v.y = topY - 0.5f;
                    else
                    {
                        float ty = terr.SampleHeight(new Vector3(v.x, 0, v.z)) + tpos.y;
                        if (ty < topY - 2.2f) { v = prev - right * 0.3f; v.y = prev.y - 0.3f; } // 裾が掘り込みに落ちる→折り畳む(入隅の垂れ幕防止)
                        else v.y = ty - ((r2 == rows - 1) ? 0.55f : 0.22f);
                    }
                    prev = v;
                    verts.Add(v); uvs.Add(new Vector2(v.x, v.z) / tile);
                }
            }
            for (int c = 0; c < cols - 1; c++)
                for (int r2 = 0; r2 < rows - 1; r2++)
                {
                    int a = b0 + c * rows + r2, b = b0 + (c + 1) * rows + r2;
                    tris.AddRange(new[] { a, b, a + 1, b, b + 1, a + 1 });
                }
        }
        var mesh = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();

        var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>("Assets/Edo/Terrain/layers/L_grass.terrainlayer");
        var mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        if (layer != null && layer.diffuseTexture != null) mat.SetTexture("_BaseMap", layer.diffuseTexture);
        mat.SetFloat("_Smoothness", 0f); mat.SetFloat("_Metallic", 0f);
        mat.SetColor("_BaseColor", new Color(1.44f, 1.25f, 1.40f)); // 地形の実測平均色に合わせた較正値

        var old = GameObject.Find(SkirtName); if (old != null) Object.DestroyImmediate(old);
        var go = new GameObject(SkirtName);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        ShowNotification(new GUIContent($"スカート生成 ({verts.Count / 9}ピース)"));
    }

    /// <summary>入隅/屈曲部: 隣接ピースの角度差が大きい所にバイセクタ向きのフィラーを差し込み、壁の楔状の隙間を塞ぐ。</summary>
    void AddCornerFillers()
    {
        var grp = GameObject.Find(groupName); if (grp == null) return;
        var roots = new List<Transform>(); foreach (Transform c in grp.transform) roots.Add(c);
        roots.Sort((a, b) => a.GetSiblingIndex().CompareTo(b.GetSiblingIndex()));
        var toDel = new List<GameObject>();
        foreach (var r in roots) if (r.name.StartsWith("igfill_")) toDel.Add(r.gameObject);
        foreach (var g in toDel) Object.DestroyImmediate(g);
        roots.RemoveAll(r => r == null);
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Japanese Castle/Meshes/Exterior/Castle Wall 4x12.fbx");
        int fills = 0;
        for (int i = roots.Count - 2; i >= 0; i--)
        {
            var a = roots[i]; var b = roots[i + 1];
            float ang = Vector3.Angle(a.right, b.right);
            if (ang <= 5f) continue;
            int n = Mathf.CeilToInt(ang / 9f); // 9度ごとに1枚
            for (int k = n; k >= 1; k--)
            {
                float t = (float)k / (n + 1);
                Quaternion rot = Quaternion.Slerp(a.rotation, b.rotation, t);
                Vector3 waterDir = rot * Vector3.right; waterDir.y = 0; waterDir.Normalize();
                var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
                go.transform.SetParent(grp.transform);
                go.transform.rotation = rot;
                go.transform.position = Vector3.Lerp(a.position, b.position, t) - waterDir * 0.35f;
                go.transform.SetSiblingIndex(b.GetSiblingIndex());
                go.name = $"igfill_{i}_{k}"; fills++;
            }
        }
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        ShowNotification(new GUIContent($"フィラー {fills} 枚挿入"));
    }

    /// <summary>端部の袖盛り土: 石垣列の両端の外側に crest-0.6 から自然地形へ落ちる土手を盛り、端の露出を土に埋める。</summary>
    void BuildEndMounds()
    {
        var terr = Terrain.activeTerrain; if (terr == null) return;
        var td = terr.terrainData; var tpos = terr.transform.position; var tsize = td.size;
        int res = td.heightmapResolution;
        var grp = GameObject.Find(groupName); if (grp == null) return;
        var roots = new List<Transform>(); foreach (Transform c in grp.transform) roots.Add(c);
        roots.Sort((a, b) => a.GetSiblingIndex().CompareTo(b.GetSiblingIndex()));
        if (roots.Count < 2) return;
        Undo.RegisterCompleteObjectUndo(td, "Ishigaki end mounds");
        System.Action<Transform, Transform> mound = (endP, inner) =>
        {
            var rend = endP.GetComponentInChildren<Renderer>(); var b = rend.bounds;
            float crest = b.max.y;
            Vector3 outward = endP.position - inner.position; outward.y = 0; outward.Normalize();
            Vector3 E = new Vector3(b.center.x, 0, b.center.z) + outward * 1.5f;
            const float R = 11f;
            int gx0 = Mathf.Clamp(Mathf.FloorToInt((E.x - R - tpos.x) / tsize.x * (res - 1)), 0, res - 1);
            int gx1 = Mathf.Clamp(Mathf.CeilToInt((E.x + R - tpos.x) / tsize.x * (res - 1)), 0, res - 1);
            int gz0 = Mathf.Clamp(Mathf.FloorToInt((E.z - R - tpos.z) / tsize.z * (res - 1)), 0, res - 1);
            int gz1 = Mathf.Clamp(Mathf.CeilToInt((E.z + R - tpos.z) / tsize.z * (res - 1)), 0, res - 1);
            int w = gx1 - gx0 + 1, h = gz1 - gz0 + 1;
            var H = td.GetHeights(gx0, gz0, w, h);
            float topN = (crest - 0.6f - tpos.y) / tsize.y;
            for (int z = 0; z < h; z++)
                for (int x = 0; x < w; x++)
                {
                    float wx = tpos.x + (float)(gx0 + x) / (res - 1) * tsize.x;
                    float wz = tpos.z + (float)(gz0 + z) / (res - 1) * tsize.z;
                    Vector3 rel = new Vector3(wx - E.x, 0, wz - E.z);
                    float d = rel.magnitude; if (d > R) continue;
                    if (Vector3.Dot(rel, outward) < -2f) continue; // 列の内側はいじらない
                    float tgt = Mathf.Lerp(topN, H[z, x], Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(2f, R, d)));
                    if (tgt > H[z, x]) H[z, x] = tgt;
                }
            td.SetHeights(gx0, gz0, H);
        };
        mound(roots[0], roots[1]);
        mound(roots[roots.Count - 1], roots[roots.Count - 2]);
        terr.Flush();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        ShowNotification(new GUIContent("袖盛り土 完了"));
    }

    static string SafetyPath => System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "Library", "EdoIshigakiSafety.bin");

    void SaveSafety()
    {
        var terr = Terrain.activeTerrain; if (terr == null) return; var td = terr.terrainData;
        int res = td.heightmapResolution; var H = td.GetHeights(0, 0, res, res);
        var flat = new float[res * res];
        for (int z = 0; z < res; z++) for (int x = 0; x < res; x++) flat[z * res + x] = H[z, x];
        var bytes = new byte[flat.Length * 4]; System.Buffer.BlockCopy(flat, 0, bytes, 0, bytes.Length);
        using (var fs = new System.IO.FileStream(SafetyPath, System.IO.FileMode.Create))
        using (var bw = new System.IO.BinaryWriter(fs)) { bw.Write(res); bw.Write(bytes.Length); bw.Write(bytes); }
        ShowNotification(new GUIContent("セーフティ保存"));
    }

    void Restore()
    {
        if (!System.IO.File.Exists(SafetyPath)) return;
        var terr = Terrain.activeTerrain; if (terr == null) return; var td = terr.terrainData;
        using (var fs = new System.IO.FileStream(SafetyPath, System.IO.FileMode.Open))
        using (var br = new System.IO.BinaryReader(fs))
        {
            int r = br.ReadInt32();
            if (r != td.heightmapResolution) { EditorUtility.DisplayDialog("戻せません", "地形の解像度が変わっています。", "OK"); return; }
            int blen = br.ReadInt32(); var bytes = br.ReadBytes(blen);
            var flat = new float[r * r]; System.Buffer.BlockCopy(bytes, 0, flat, 0, blen);
            var H = new float[r, r]; for (int z = 0; z < r; z++) for (int x = 0; x < r; x++) H[z, x] = flat[z * r + x];
            Undo.RegisterCompleteObjectUndo(td, "Restore terrain (safety)"); td.SetHeights(0, 0, H); terr.Flush();
        }
        ShowNotification(new GUIContent("セーフティ地形に戻しました"));
    }

    void Apply()
    {
        var terr = Terrain.activeTerrain;
        if (terr == null) { ShowNotification(new GUIContent("Terrain が見つかりません")); return; }
        var td = terr.terrainData; var tpos = terr.transform.position; var tsize = td.size;

        // 対象ピース収集
        var roots = new List<Transform>();
        if (Selection.transforms != null && Selection.transforms.Length > 0)
        {
            foreach (var s in Selection.transforms)
                if (s.GetComponentInChildren<Renderer>() != null) roots.Add(s);
        }
        else
        {
            var grp = GameObject.Find(groupName);
            if (grp != null) foreach (Transform c in grp.transform) roots.Add(c);
        }
        if (roots.Count == 0) { ShowNotification(new GUIContent("対象の石垣がありません")); return; }
        // 岸沿いの順序を保つ（Hierarchy の並び順＝配置順）
        roots.Sort((a, b) => a.GetSiblingIndex().CompareTo(b.GetSiblingIndex()));

        // 各ピースについて: 背面境界点(石の陸側の端)・水向き法線・天端Y を、実メッシュ頂点から算出
        //  境界を石の"背面"に置くことで、盛った土が反りの効いた石の裏に完全に隠れ、
        //  境界より水側(石の真下含む)を掘ることで前面の三角残りが消える。
        var Bp = new List<Vector3>();   // 背面境界点(XZ, y=0)
        var Nw = new List<Vector3>();   // 水向き法線(水平)
        var Top = new List<float>();    // 天端Y(world)
        foreach (var r in roots)
        {
            Vector3 water = r.right; water.y = 0f;
            if (water.sqrMagnitude < 1e-4f) continue; water.Normalize();
            float backProj = 1e9f, topY = -1e9f; Vector3 centerXZ = Vector3.zero; int cc = 0;
            foreach (var mf in r.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var lb = mf.sharedMesh.bounds; var mtx = mf.transform.localToWorldMatrix;
                for (int ci = 0; ci < 8; ci++)
                {
                    Vector3 lc = lb.center + Vector3.Scale(lb.extents,
                        new Vector3((ci & 1) == 0 ? -1 : 1, (ci & 2) == 0 ? -1 : 1, (ci & 4) == 0 ? -1 : 1));
                    Vector3 wc = mtx.MultiplyPoint3x4(lc);
                    centerXZ += new Vector3(wc.x, 0, wc.z); cc++;
                    float proj = Vector3.Dot(new Vector3(wc.x, 0, wc.z), water); // N方向の投影
                    if (proj < backProj) backProj = proj;
                    if (wc.y > topY) topY = wc.y;
                }
            }
            if (cc == 0) continue;
            centerXZ /= cc;
            // 背面境界点 = 中心XZから水向きの最も後方(min投影)へ。境界のN投影値=backProj。
            // 中心のN投影を基準に境界点を作る
            float cProj = Vector3.Dot(centerXZ, water);
            Vector3 boundary = centerXZ + water * (backProj - cProj); // = 背面端に一致
            Bp.Add(new Vector3(boundary.x, 0, boundary.z)); Nw.Add(water); Top.Add(topY);
        }
        int m = Bp.Count; if (m == 0) return;

        // 背面境界ラインを軽く平滑化(隣接ピースのジグザグを取り、埋めの縁のカクつきを抑える)
        for (int iter = 0; iter < 2; iter++)
        {
            var sm = new List<Vector3>(Bp);
            for (int i = 1; i < m - 1; i++)
                sm[i] = Bp[i - 1] * 0.25f + Bp[i] * 0.5f + Bp[i + 1] * 0.25f;
            Bp = sm;
        }

        // 水面Y
        float waterY = -1e9f;
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            var wy = (float)wb.GetType().GetField("waterY").GetValue(wb);
            if (wy > waterY) waterY = wy;
        }
        if (waterY < -1e8f) waterY = tpos.y; // fallback

        // 範囲
        float minx = 1e9f, maxx = -1e9f, minz = 1e9f, maxz = -1e9f;
        foreach (var p in Bp) { minx = Mathf.Min(minx, p.x); maxx = Mathf.Max(maxx, p.x); minz = Mathf.Min(minz, p.z); maxz = Mathf.Max(maxz, p.z); }
        float pad = Mathf.Max(backFill, faceExpose) + 6f; minx -= pad; maxx += pad; minz -= pad; maxz += pad;

        int res = td.heightmapResolution;
        int gx0 = Mathf.Clamp(Mathf.FloorToInt((minx - tpos.x) / tsize.x * (res - 1)), 0, res - 1);
        int gx1 = Mathf.Clamp(Mathf.CeilToInt((maxx - tpos.x) / tsize.x * (res - 1)), 0, res - 1);
        int gz0 = Mathf.Clamp(Mathf.FloorToInt((minz - tpos.z) / tsize.z * (res - 1)), 0, res - 1);
        int gz1 = Mathf.Clamp(Mathf.CeilToInt((maxz - tpos.z) / tsize.z * (res - 1)), 0, res - 1);
        int w = gx1 - gx0 + 1, h = gz1 - gz0 + 1;

        Undo.RegisterCompleteObjectUndo(td, "Ishigaki Fit");
        var H = td.GetHeights(gx0, gz0, w, h);
        float footN = (waterY - footBelow - tpos.y) / tsize.y;
        int fillN = 0, carveN = 0;
        float feather = 1.7f;

        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = tpos.x + (float)(gx0 + x) / (res - 1) * tsize.x;
                float wz = tpos.z + (float)(gz0 + z) / (res - 1) * tsize.z;
                Vector2 col = new Vector2(wx, wz);
                // 背面境界ポリラインへの最近点・符号付き側・天端
                float bestD = 1e9f; float side = 0f; float topN = 0f; int bestSeg = 0; float bestT = 0f;
                for (int i = 0; i < m - 1; i++)
                {
                    Vector2 a = new Vector2(Bp[i].x, Bp[i].z);
                    Vector2 bb = new Vector2(Bp[i + 1].x, Bp[i + 1].z);
                    Vector2 ab = bb - a; float segLen2 = Mathf.Max(1e-4f, ab.sqrMagnitude);
                    float t = Mathf.Clamp01(Vector2.Dot(col - a, ab) / segLen2);
                    Vector2 q = a + ab * t; float d = Vector2.Distance(col, q);
                    if (d < bestD)
                    {
                        bestD = d; bestSeg = i; bestT = t;
                        Vector3 nrm = Vector3.Lerp(Nw[i], Nw[i + 1], t); nrm.y = 0; nrm.Normalize();
                        side = Vector3.Dot(new Vector3(col.x - q.x, 0, col.y - q.y), nrm);
                        topN = (Mathf.Lerp(Top[i], Top[i + 1], t) - topDrop - tpos.y) / tsize.y;
                    }
                }
                // 壁の両端より外側へはみ出したテクセルは触らない(端で扇状に変形しない)
                bool offEnd = (bestSeg == 0 && bestT <= 0.001f) || (bestSeg == m - 2 && bestT >= 0.999f);
                if (offEnd && bestD > 2f) continue;

                if (side <= 0f && doFill) // 陸側: 天端まで一律に上げる(境界で垂直段差)
                {
                    float ad = -side;
                    float tgt = (ad <= backFill) ? topN
                             : Mathf.Lerp(topN, H[z, x], Mathf.InverseLerp(backFill, backFill * feather, ad));
                    if (tgt > H[z, x]) { H[z, x] = tgt; fillN++; }
                }
                else if (side > 0f && doExpose) // 水側(石の真下含む): 水面下まで一律に下げる
                {
                    float ad = side;
                    float tgt = (ad <= faceExpose) ? footN
                             : Mathf.Lerp(footN, H[z, x], Mathf.InverseLerp(faceExpose, faceExpose * feather, ad));
                    if (tgt < H[z, x]) { H[z, x] = tgt; carveN++; }
                }
            }
        td.SetHeights(gx0, gz0, H); terr.Flush();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        ShowNotification(new GUIContent($"馴染ませ完了 (埋め{fillN}/掘り{carveN})"));
        Debug.Log($"[EdoIshigakiFit] pieces={m} fill={fillN} carve={carveN} waterY={waterY:F1}");
    }
}
