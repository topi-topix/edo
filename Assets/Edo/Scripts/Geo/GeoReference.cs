using System;
using UnityEngine;

namespace Edo.Geo
{
    /// <summary>
    /// このプロジェクトのジオリファレンス定義。
    ///
    /// シーン原点の水平位置 (x, z) = 江戸見坂 (東京都港区虎ノ門)。
    /// 企画上の視点であり、プレイヤーのホームであるため原点に採用する。
    /// 原点を対象地域の中心付近に置くことで float の精度低下も回避できる
    /// (原点から 2.5km の地点でも誤差は 1mm 未満に収まる)。
    ///
    /// 鉛直方向は Y = 0 が海抜 0m (東京湾平均海面 T.P.)。
    /// つまり Unity の Y をそのまま標高として読める。
    /// 水平原点(江戸見坂)の地面は Y ≒ +25 付近に来る。
    ///
    /// 軸の対応:
    ///   Unity.x = 東 (平面直角座標の y)
    ///   Unity.y = 標高 [m] (東京湾平均海面基準)
    ///   Unity.z = 北 (平面直角座標の x)
    ///
    /// PLATEAU SDK でインポートする際は、オフセットに PlaneOriginEast / PlaneOriginNorth を
    /// 指定することで、現代の 3D 都市モデルがこの座標系に重なる。
    /// </summary>
    public static class GeoReference
    {
        /// <summary>シーン原点の緯度 [deg] — 江戸見坂</summary>
        public const double OriginLat = 35.6670198;

        /// <summary>シーン原点の経度 [deg] — 江戸見坂</summary>
        public const double OriginLon = 139.7456355;

        /// <summary>
        /// Unity の Y = 0 が指す標高 [m]。0 = 東京湾平均海面 (T.P.)。
        /// この値は「鉛直の基準面をどこに置くか」の定義であり、実測すべき量ではない。
        /// 0 にしてあるので Unity の Y 座標をそのまま標高として読める。
        /// </summary>
        public const double OriginHeight = 0.0;

        /// <summary>原点の平面直角座標 第IX系 における北方向成分 [m]</summary>
        public static readonly double PlaneOriginNorth;

        /// <summary>原点の平面直角座標 第IX系 における東方向成分 [m]</summary>
        public static readonly double PlaneOriginEast;

        static GeoReference()
        {
            double north, east;
            JapanPlaneRectIX.ToPlane(OriginLat, OriginLon, out north, out east);
            PlaneOriginNorth = north;
            PlaneOriginEast = east;
        }

        /// <summary>緯度経度と標高から Unity のワールド座標を求める。</summary>
        public static Vector3 LatLonToUnity(double latDeg, double lonDeg, double heightMsl)
        {
            double north, east;
            JapanPlaneRectIX.ToPlane(latDeg, lonDeg, out north, out east);

            return new Vector3(
                (float)(east - PlaneOriginEast),
                (float)(heightMsl - OriginHeight),
                (float)(north - PlaneOriginNorth));
        }

        /// <summary>標高を省略した場合は海抜 0m (Y = 0) に置く。地面に乗せたいなら標高を渡すこと。</summary>
        public static Vector3 LatLonToUnity(double latDeg, double lonDeg)
        {
            return LatLonToUnity(latDeg, lonDeg, OriginHeight);
        }

        /// <summary>Unity のワールド座標から緯度経度と標高を求める。</summary>
        public static void UnityToLatLon(Vector3 world, out double latDeg, out double lonDeg, out double heightMsl)
        {
            double north = world.z + PlaneOriginNorth;
            double east = world.x + PlaneOriginEast;

            JapanPlaneRectIX.ToLatLon(north, east, out latDeg, out lonDeg);
            heightMsl = world.y + OriginHeight;
        }

        /// <summary>2 つのワールド座標間の水平距離 [m]。</summary>
        public static float HorizontalDistance(Vector3 a, Vector3 b)
        {
            return Mathf.Sqrt((a.x - b.x) * (a.x - b.x) + (a.z - b.z) * (a.z - b.z));
        }

        /// <summary>a から b を見たときの方位角 [deg]。真北を 0 とし、時計回りに増加する。</summary>
        public static float Bearing(Vector3 a, Vector3 b)
        {
            float deg = Mathf.Atan2(b.x - a.x, b.z - a.z) * Mathf.Rad2Deg;
            return deg < 0f ? deg + 360f : deg;
        }
    }

    /// <summary>
    /// 実世界の緯度経度を持つ地点。
    /// このコンポーネントを付けた GameObject は、目分量ではなく実座標で配置される。
    /// Inspector の右クリックメニューから「Snap To Coordinates」を実行すると
    /// GeoReference に従って正しい位置へ移動する。
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
