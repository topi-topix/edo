using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 類型ビルダー Stage5(庭)が「地表をどう塗ってほしいか」を**書き残すだけ**の印。
/// ⛔ 類型ビルダーは地形(高さ・アルファマップ)を書かない(`docs/typology-builder.md` §4.5 の
/// 覆さない線⑤)ので、ここには**駒を置くのと同じ意味で**帯・塊の位置だけを持たせる。実際に
/// 地形のスプラットへ塗るのは別の輪(`EdoGardenSurfacePaint`、`WaterBody` が水を別輪へ渡すのと同じ作り)。
///
/// <c>points</c> は 2m 格子点(x,0,z のワールド座標)。<c>radius</c> は塗るときの塗り半径 —
/// 格子の間隔よりわずかに広く取って、点と点の間に塗り残しの筋が出ないようにする(既定 1.5m)。
/// </summary>
public class NiwaGroundZone : MonoBehaviour
{
    /// <summary>"shirasu"(白砂利・参道/前庭)/ "moss"(苔+砂利・坪庭)/ "tataki"(叩き土・裏庭)</summary>
    public string kind;
    public List<Vector3> points = new List<Vector3>();
    public float radius = 1.5f;
}
