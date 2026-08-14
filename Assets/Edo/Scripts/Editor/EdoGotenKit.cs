// 御殿の棟を「江戸間の柱割り」で組むキット。
//
// Village Kit のプレハブ(閉じた一軒家)では入側から壁が見えて御殿にならない、という
// ユーザー裁定(2026-08-14)を受けて、Blender で部材から起こし直したものを並べる。
// 部材の生成は Tools/Blender/(README に規約と落とし穴)。パスは EdoAssets.Goten。
//
// 部材の規約: 幅X・高さY・厚みZ、**表(見え掛かり)= +Z**、ピボット = 一間の中心・床レベル。
//   1間 = 1.818m / 建具高 = 2.727m / 柱 = 0.182角 / 畳は一間角(=江戸間2畳)。
//
// 棟の構成は SKILL(unity-buke-yashiki) §B-2 のとおり「身舎のまわりに入側が回る」。
// ここでは前後(梁間方向)に入側を取る型を作る。左右の妻側は白壁。
//
// ⚠ 屋根は棟の寸法ごとに Blender で生成する:
//     blender --background --python Tools/Blender/build_goten_roof.py -- <桁行W> <梁間D> <名前>
//   ここでは寸法の合う既成の屋根があれば載せ、無ければ骨組みだけ組んで警告を出す。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoGotenKit
{
    public const float K = EdoAssets.Goten.Ken;      // 1.818
    public const float H = EdoAssets.Goten.DoorH;    // 2.727

    static GameObject Load(string path)
    {
        var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (go == null) Debug.LogError("[GotenKit] 見つからない: " + path);
        return go;
    }

    static GameObject Put(string path, Transform parent, Vector3 lp, float ry)
    {
        var src = Load(path);
        if (src == null) return null;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
        go.transform.localPosition = lp;
        go.transform.localRotation = Quaternion.Euler(0f, ry, 0f);
        return go;
    }

    /// <summary>棟を1つ組む。
    /// nx = 桁行の間数(X) / nzZashiki = 身舎の間数(Z) / iri = 前後の入側の間数(0で無し)。
    /// 原点は棟の南西角(床レベル)。yaw は親側で与える。
    /// roofAsset に寸法の合う屋根FBXのパスを渡すと載せる(null なら骨組みのみ)。</summary>
    public static GameObject Mune(string name, Transform parent, Vector3 pos, float yaw,
                                  int nx, int nzZashiki, int iri = 1,
                                  float floor = 0.62f, string roofAsset = null,
                                  bool nureen = true, bool ceiling = true)
    {
        int nz = nzZashiki + 2 * iri;
        float W = nx * K, D = nz * K;

        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.localPosition = pos;
        g.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);

        // 床 — 入側は板敷き、身舎は畳
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                bool isIri = (j < iri || j >= nz - iri);
                Put(isIri ? EdoAssets.Goten.FloorBoard : EdoAssets.Goten.Tatami, g.transform,
                    new Vector3(i * K + K / 2f, floor, j * K + K / 2f), 0f);
            }

        // 建具 — 身舎と入側の境に障子。表(+Z)を入側へ向ける
        for (int i = 0; i < nx; i++)
        {
            if (iri > 0)
            {
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, floor, iri * K), 180f);
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, floor, (nz - iri) * K), 0f);
            }
        }

        // 妻側 — 白壁(身舎の範囲)。入側の端は開けて廊下を通す
        for (int j = iri; j < nz - iri; j++)
        {
            Put(EdoAssets.Goten.WallPlaster, g.transform,
                new Vector3(0f, floor, j * K + K / 2f), 90f);
            Put(EdoAssets.Goten.WallPlaster, g.transform,
                new Vector3(W, floor, j * K + K / 2f), 270f);
        }

        // 柱 — 一間ごとの格子点
        for (int i = 0; i <= nx; i++)
            for (int j = 0; j <= nz; j++)
                Put(EdoAssets.Goten.Column, g.transform, new Vector3(i * K, floor, j * K), 0f);

        if (ceiling)
            for (int i = 0; i < nx; i++)
                for (int j = 0; j < nz; j++)
                    Put(EdoAssets.Goten.Ceiling, g.transform,
                        new Vector3(i * K + K / 2f, floor + H, j * K + K / 2f), 0f);

        if (nureen && iri > 0)
            for (int i = 0; i < nx; i++)
            {
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(i * K + K / 2f, floor - 0.28f, 0f), 0f);
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(i * K + K / 2f, floor - 0.28f, D), 180f);
            }

        if (!string.IsNullOrEmpty(roofAsset))
        {
            var r = Put(roofAsset, g.transform, new Vector3(W / 2f, floor + H - 0.15f, D / 2f), 0f);
            if (r != null)
            {
                // 屋根の寸法が棟に合っているか確かめる(軒の出0.9m×2を見込む)
                var mf = r.GetComponentInChildren<MeshFilter>();
                if (mf != null)
                {
                    var s = mf.sharedMesh.bounds.size;
                    if (Mathf.Abs(s.x - (W + 1.8f)) > 0.35f || Mathf.Abs(s.z - (D + 1.8f)) > 0.35f)
                        Debug.LogWarning(string.Format(
                            "[GotenKit] {0}: 屋根が棟に合っていない。屋根 {1:F2}x{2:F2} / 棟 {3:F2}x{4:F2}。" +
                            "build_goten_roof.py -- {3:F3} {4:F3} で作り直す", name, s.x, s.z, W, D));
                }
            }
        }
        else
        {
            Debug.LogWarning(string.Format(
                "[GotenKit] {0}: 屋根なし。blender --background --python Tools/Blender/build_goten_roof.py -- {1:F3} {2:F3} <名前>",
                name, W, D));
        }
        return g;
    }

    [MenuItem("Edo/御殿/部材テスト棟を建てる (8間x5間)")]
    public static void BuildTestMune()
    {
        var old = GameObject.Find("GotenKitTest");
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject("GotenKitTest");
        root.transform.position = new Vector3(0f, 300f, 0f);   // 既存の街に干渉しない空中で確認する
        var m = Mune("Mune_Test", root.transform, Vector3.zero, 0f, 8, 3, 1,
                     0.62f, EdoAssets.Goten.RoofIrimoya);
        Selection.activeGameObject = m;
        Debug.Log("[GotenKit] テスト棟を y=300 に建てた。確認したら GotenKitTest を消してよい");
    }
}
