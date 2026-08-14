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
    public const float JODAN = 0.15f;                // 上段の段の高さ

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
                                  bool nureen = true, bool ceiling = true,
                                  int[] openBaysWest = null, int[] openBaysEast = null,
                                  int jodanFromIx = -1)
    {
        // 妻壁を開ける区画(床の間・違い棚・帳台構が入る所)。塞いだままだと飾りが壁の裏に隠れる
        System.Func<int[], int, bool> isOpen = (arr, j) => {
            if (arr == null) return false;
            foreach (var v in arr) if (v == j) return true;
            return false;
        };
        int nz = nzZashiki + 2 * iri;
        float W = nx * K, D = nz * K;

        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.localPosition = pos;
        g.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);

        // 上段の間 — jodanFromIx より奥(+X)の身舎は床が一段(0.15)上がる
        System.Func<int, bool, float> lv = (i, isIri) =>
            (jodanFromIx >= 0 && i >= jodanFromIx && !isIri) ? floor + JODAN : floor;

        // 床 — 入側は板敷き、身舎は畳
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                bool isIri = (j < iri || j >= nz - iri);
                Put(isIri ? EdoAssets.Goten.FloorBoard : EdoAssets.Goten.Tatami, g.transform,
                    new Vector3(i * K + K / 2f, lv(i, isIri), j * K + K / 2f), 0f);
            }

        // 上段框 — 段の際に通す
        if (jodanFromIx > 0 && jodanFromIx < nx)
            for (int j = iri; j < nz - iri; j++)
                Put(EdoAssets.Goten.JodanKamachi, g.transform,
                    new Vector3(jodanFromIx * K, floor, j * K + K / 2f), 270f);

        // 建具 — 身舎と入側の境に障子。表(+Z)を入側へ向ける
        for (int i = 0; i < nx; i++)
        {
            if (iri > 0)
            {
                float y = lv(i, false);
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, y, iri * K), 180f);
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, y, (nz - iri) * K), 0f);
            }
        }

        // 妻側 — 白壁(身舎の範囲)。入側の端は開けて廊下を通す
        for (int j = iri; j < nz - iri; j++)
        {
            if (!isOpen(openBaysWest, j))
                Put(EdoAssets.Goten.WallPlaster, g.transform,
                    new Vector3(0f, lv(0, false), j * K + K / 2f), 90f);
            if (!isOpen(openBaysEast, j))
                Put(EdoAssets.Goten.WallPlaster, g.transform,
                    new Vector3(W, lv(nx - 1, false), j * K + K / 2f), 270f);
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

    /// <summary>続き間の仕切り = 襖 + 欄間の一列。棟のローカル座標で
    /// x の柱通りに、z0..z1 間(間数)の範囲へ通す。</summary>
    public static void Partition(Transform mune, float floor, int ix, int jz0, int jz1)
    {
        for (int j = jz0; j < jz1; j++)
        {
            var c = new Vector3(ix * K, floor, j * K + K / 2f);
            Put(EdoAssets.Goten.Fusuma, mune, c, 90f);
            Put(EdoAssets.Goten.Ranma, mune,
                c + new Vector3(0f, EdoAssets.Goten.Uchinori, 0f), 90f);
        }
    }

    /// <summary>座敷飾り — 上段の間の奥の壁に 床の間・違い棚・帳台構 を並べる。
    /// wall = 壁面の中心が乗る柱通り、yaw は室内へ向く向き(表=+Z)。3間分を使う。</summary>
    public static void Zashikikazari(Transform mune, Vector3 origin, float yaw,
                                     bool tokonoma = true, bool tana = true, bool chodai = true)
    {
        var f = Quaternion.Euler(0f, yaw, 0f);
        int slot = 0;
        System.Action<string> place = (asset) =>
        {
            var lp = origin + f * new Vector3((slot - 1) * K, 0f, 0f);
            Put(asset, mune, lp, yaw);
            slot++;
        };
        if (tokonoma) place(EdoAssets.Goten.Tokonoma); else slot++;
        if (tana) place(EdoAssets.Goten.Chigaidana); else slot++;
        if (chodai) place(EdoAssets.Goten.Chodaigamae); else slot++;
    }

    /// <summary>上段の間の段(框)。x の柱通りに沿って z0..z1 間へ通す。</summary>
    public static void Jodan(Transform mune, float floor, int ix, int jz0, int jz1, bool faceMinusX = true)
    {
        for (int j = jz0; j < jz1; j++)
            Put(EdoAssets.Goten.JodanKamachi, mune,
                new Vector3(ix * K, floor, j * K + K / 2f), faceMinusX ? 270f : 90f);
    }

    [MenuItem("Edo/御殿/部材テスト棟を建てる (8間x5間)")]
    public static void BuildTestMune()
    {
        var old = GameObject.Find("GotenKitTest");
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject("GotenKitTest");
        root.transform.position = new Vector3(0f, 300f, 0f);   // 既存の街に干渉しない空中で確認する
        var m = Mune("Mune_Test", root.transform, Vector3.zero, 0f, 8, 3, 1,
                     0.62f, EdoAssets.Goten.RoofIrimoya,
                     openBaysEast: new[] { 1, 2, 3 },      // 東の妻壁は座敷飾りに明け渡す
                     jodanFromIx: 5);                      // 東の3間を上段の間にする
        // 身舎を襖で割る(下段2室 + 上段)
        Partition(m.transform, 0.62f, 3, 1, 4);
        Partition(m.transform, 0.62f + JODAN, 5, 1, 4);
        // 飾りのピボット = 開口面。柱通り(x=W)に置くと床框だけが室内へ出る
        Zashikikazari(m.transform, new Vector3(8 * K, 0.62f + JODAN, 2.5f * K), 270f);
        Selection.activeGameObject = m;
        Debug.Log("[GotenKit] テスト棟を y=300 に建てた。確認したら GotenKitTest を消してよい");
    }
}
