using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 内堀(濠)を「1本の水際輪郭ライン」を唯一の正として作る土木データ。
/// 生成（掘削→背面充填→石垣配置→水）は Editor の MoatWallBaker が行う。
///
/// 断面（輪郭に直交、s=輪郭からの符号付き距離。内=水側 −、外=陸側 +）：
///   水面 ── 濠底(waterY-moatDepth) ──[輪郭s=0]──石垣footprint(掘り下げ)──
///   ── 背面プロファイル(段のリスト:天端基準) ── blend ── 既存地形
/// backProfile を差し替えるだけで「面一の平場」も「犬走り＋平場」も表現できる。
///
/// ⚠️ EdoTerrain は56タイル。MoatWallBaker は全タイル横断で掘る（activeTerrain 1枚に依存しない）。
/// </summary>
public class MoatWall : MonoBehaviour
{
    [Tooltip("石垣ピースの集合（高さ別直線＋コーナー）")]
    public MoatModuleSet modules;

    [Tooltip("水際の輪郭（石垣天端が通る線）。ワールド座標・閉ループ。古地図からトレースして作る。")]
    public List<Vector3> outline = new List<Vector3>();

    [Header("水位・深さ (m, 世界Y)")]
    public float waterY = 0f;
    [Tooltip("水位から濠底まで")] public float moatDepth = 4f;
    [Tooltip("水位から天端(石垣上端/平場)まで = 実質の壁高")] public float topHeight = 2.5f;

    [Header("石垣 footprint")]
    [Tooltip("輪郭から陸側へ、石垣が占める幅(掘り下げ帯)。石垣の奥行きに合わせる")]
    public float wallFootprint = 2.0f;

    [Header("背面(陸側)プロファイル：天端(waterY+topHeight)基準の段リスト。")]
    [Tooltip("面一=平場1段[width,0]。犬走り=先に低い段[細幅,-drop]→平場[width,0]。")]
    public List<BackStep> backProfile = new List<BackStep>();
    [Tooltip("背面プロファイル末端から既存地形へブレンドする幅")] public float backBlend = 12f;

    [Header("水面メッシュ")]
    public bool buildWaterSurface = true;

    // 掘削の復元用スナップショット（タイルごと）
    [HideInInspector] public List<TileCarveSnap> snaps = new List<TileCarveSnap>();

    void Reset()
    {
        // 既定＝面一の平場（多くの城郭）
        backProfile = new List<BackStep> { new BackStep { width = 6f, dHeight = 0f } };
    }

    public float MoatBedY => waterY - moatDepth;
    public float TopY => waterY + topHeight;
}

/// <summary>背面プロファイルの1段。天端(TopY)からの相対高 dHeight。面一なら dHeight=0。</summary>
[System.Serializable]
public class BackStep
{
    [Tooltip("この段の幅(m, 陸側へ)")] public float width = 6f;
    [Tooltip("天端からの高さ差(m)。0=天端と面一、負=一段低い(犬走り)")] public float dHeight = 0f;
}

/// <summary>掘削前の地形高さをタイル単位で保存（復元用）。</summary>
[System.Serializable]
public class TileCarveSnap
{
    public string terrainName;
    public int x, z, w, h;
    public float[] heights; // w*h, row-major (z*w+x)
}
