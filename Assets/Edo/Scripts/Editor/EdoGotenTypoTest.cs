// 類型の御殿複合(EDO-0318 ⑥)を**一筆だけ**建てて実測するための検分メニュー。
//
// ⭐ なぜ別立てか: 類型ビルダー(EdoTypologyBuilder)は 88 区画の車線で、御殿の据わりを見るのに
//    区画ぜんたいを建て直すのは高い。ここは `EdoBuild.GotenComplex` だけを呼び、建てて測って刷る。
// ⛔ ここに置き方を書かない(規則21)— 置く・測る・突き付ける・据えるは `EdoBuildGoten.cs` の持ち場。
// ⛔ この駒は書き戻さない — 見たら `GotenTypoTest` を消す。

using UnityEditor;
using UnityEngine;

public static class EdoGotenTypoTest
{
    /// <summary>試す区画(`omoya: goten` の9筆のうち、いちばん小さい物と大きい物)。</summary>
    const string SMALL = "sanbezakanishi_torii";     // 3,504 坪
    const string LARGE = "toranomonuchi_parcels_0";  // 11,911 坪

    [MenuItem("Edo/御殿/類型の御殿複合を試す(小さい区画)")]
    public static void BuildSmall() { Build(SMALL); }

    [MenuItem("Edo/御殿/類型の御殿複合を試す(大きい区画)")]
    public static void BuildLarge() { Build(LARGE); }

    static void Build(string id)
    {
        var poly = EdoParcels.Get(id);
        if (poly == null || poly.Length < 3) { Debug.LogError("[御殿テスト] 区画が引けない: " + id); return; }

        var old = GameObject.Find("GotenTypoTest");
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject("GotenTypoTest");

        // 表門の位置は類型ビルダーが接道辺から決める物。ここでは**いちばん長い辺の中点**で代用する
        // (⚠ 代用なので、この試しで見るのは「据わり・取り合い・区画への収まり」であって門との関係ではない)。
        int fi = 0; float best = -1f;
        for (int i = 0; i < poly.Length; i++)
        {
            float L = Vector2.Distance(poly[i], poly[(i + 1) % poly.Length]);
            if (L > best) { best = L; fi = i; }
        }
        var mid = (poly[fi] + poly[(fi + 1) % poly.Length]) * 0.5f;
        var inward = EdoGeom.InwardNormal(poly, fi);

        float spread; int n;
        float pad = EdoBuild.PadY(poly, 2f, out spread, out n);

        string note;
        var go = EdoBuild.GotenComplex(root.transform, "Goten_" + id, poly, mid, inward, pad,
                                       0f, 6f, 800, out note);
        Debug.Log(string.Format("[御殿テスト] {0}: 面 y={1:F2}(起伏 {2:F2}m)\n{3}", id, pad, spread, note));
        Selection.activeGameObject = go != null ? go : root;
        if (go != null) SceneView.lastActiveSceneView?.FrameSelected();
    }
}
