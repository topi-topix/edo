using UnityEngine;

namespace Edo.Geo
{
    /// <summary>
    /// 実世界の緯度経度を持つ地点。
    /// このコンポーネントを付けた GameObject は、目分量ではなく実座標で配置される。
    /// Inspector の右クリックメニューから「Snap To Coordinates」を実行すると
    /// GeoReference に従って正しい位置へ移動する。
    /// ⛔ ファイル名とクラス名を一致させる(この型が GeoReference.cs に同居していた間、シーンに台本の仮の写しが
    ///   埋め込まれ、アプリが赤坂を「corrupted / Position out of bounds」で読めなかった・2026-10-17 EDO-0450)。
    /// </summary>
    [ExecuteAlways]
    public class GeoMarker : MonoBehaviour
    {
        [Header("実世界の座標 (JGD2011)")]
        [Tooltip("緯度 [deg]")]
        public double latitude = GeoReference.OriginLat;

        [Tooltip("経度 [deg]")]
        public double longitude = GeoReference.OriginLon;

        [Tooltip("標高 [m] — 東京湾平均海面基準")]
        public double heightMsl = GeoReference.OriginHeight;

        [Header("出典")]
        [Tooltip("この座標をどこから得たか。切絵図の推定値なのか実測値なのかを必ず残す。")]
        public string source = "";

        [ContextMenu("Snap To Coordinates")]
        public void SnapToCoordinates()
        {
            transform.position = GeoReference.LatLonToUnity(latitude, longitude, heightMsl);
        }

        [ContextMenu("Read Coordinates From Current Position")]
        public void ReadFromCurrentPosition()
        {
            double lat, lon, h;
            GeoReference.UnityToLatLon(transform.position, out lat, out lon, out h);
            latitude = lat;
            longitude = lon;
            heightMsl = h;
        }
    }
}
