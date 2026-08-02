using UnityEngine;

/// <summary>
/// 石垣モジュール集合（Blender製の実ジオメトリピースを差す）。
/// 配置規約（Unity空間, Y-up）：
///  - 原点＝走り始端・最下・水際面の角
///  - +X=走り方向, +Y=上, 水際面は −Z 側（奥行きは +Z へ陸側）
///  - eulerOffset/posOffset で GLB取込後の向き・原点を一度だけ校正
/// まずは同寸のプレースホルダー箱で可、後で本ピース(decimate版)へ差し替え。
/// </summary>
[CreateAssetMenu(fileName = "MoatModuleSet", menuName = "Edo/Moat Module Set")]
public class MoatModuleSet : ScriptableObject
{
    [Header("直線モジュール（高さ別）")]
    public GameObject straightLow;
    public GameObject straightMid;
    public GameObject straightHigh;

    [Header("コーナー（出隅=凸/入隅=凹）")]
    public GameObject cornerConvex;
    public GameObject cornerConcave;

    [Header("寸法 (m)")]
    [Tooltip("直線1枚の走り方向長（タイル刻み）")] public float runLength = 2.0f;
    public float lowHeight = 1.2f;
    public float midHeight = 2.5f;
    public float highHeight = 5.0f;

    [Header("向き校正（GLB取込後に一度合わせる）")]
    public Vector3 eulerOffset = Vector3.zero;
    public Vector3 posOffset = Vector3.zero;

    [Header("コーナー配置")]
    [Tooltip("この角度(度)以上曲がる頂点をコーナーとして扱う")] public float turnThresholdDeg = 30f;
    [Tooltip("コーナーが隣接直線を食う長さ(m)。直線はこの分詰めて敷く")] public float cornerInset = 2.0f;
    [Tooltip("出隅(凸)ピースの回転補正")] public Vector3 convexEuler = Vector3.zero;
    [Tooltip("入隅(凹)ピースの回転補正")] public Vector3 concaveEuler = Vector3.zero;
    [Tooltip("コーナーピースの原点補正")] public Vector3 cornerPosOffset = Vector3.zero;

    /// <summary>壁高(天端-水位)に最も近い段の直線プレハブを返す。</summary>
    public GameObject PickStraight(float wallHeight, out float chosenHeight)
    {
        float dl = Mathf.Abs(wallHeight - lowHeight);
        float dm = Mathf.Abs(wallHeight - midHeight);
        float dh = Mathf.Abs(wallHeight - highHeight);
        if (dl <= dm && dl <= dh) { chosenHeight = lowHeight; return straightLow; }
        if (dm <= dh) { chosenHeight = midHeight; return straightMid; }
        chosenHeight = highHeight; return straightHigh;
    }
}
