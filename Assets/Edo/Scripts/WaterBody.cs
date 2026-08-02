using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 編集できる水域。輪郭の点(outline)を保持し、水面メッシュ＋地形の掘り込みを生成する。
/// 実際の生成/掘り直しはエディタの WaterBaker が行う（点のドラッグや『掘り直す』ボタン）。
/// snap は掘り込みを元に戻す(縮小時)ための地形スナップショット。
/// </summary>
[RequireComponent(typeof(MeshFilter))]
[RequireComponent(typeof(MeshRenderer))]
public class WaterBody : MonoBehaviour
{
    public List<Vector3> outline = new List<Vector3>();

    [Tooltip("頂点ごとの角スタイル: true=直角(角を残す) / false=スムーズ(丸める)。outline と同じ長さ。空/短い場合は該当点はスムーズ扱い")]
    public List<bool> sharp = new List<bool>();

    public float depth = 2.2f;
    public float waterY = 0f;

    [Tooltip("true=壁を垂直に掘る(断面が直角・カクッと)。false=なだらかに掘る(従来・壁が斜めに丸まる)")]
    public bool verticalWalls = false;

    [Tooltip("水域の外側の低い地面を水位まで盛り上げて土手を作り、水が浮かない/漏れないようにする")]
    public bool raiseBanks = true;
    [Tooltip("土手の幅(m)")]
    public float bankWidth = 10f;

    // 掘り込み復元用スナップショット（初回の掘り込み前に固定領域を保存）
    [HideInInspector] public float[] snap;
    [HideInInspector] public int sX, sZ, sW, sH;
    [HideInInspector] public bool hasSnap;
}
