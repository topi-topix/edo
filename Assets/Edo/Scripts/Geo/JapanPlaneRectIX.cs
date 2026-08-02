using System;

namespace Edo.Geo
{
    /// <summary>
    /// 緯度経度(JGD2011) ⇔ 平面直角座標系 第IX系 (EPSG:6677) の相互変換。
    /// 国土地理院「平面直角座標への換算」のガウス・クリューゲル級数展開に基づく。
    /// pyproj (EPSG:6668 -> EPSG:6677) と 0.001mm 未満で一致することを検証済み。
    ///
    /// 第IX系の座標原点: 北緯 36 度, 東経 139 度 50 分
    /// 適用範囲: 東京都(島嶼部を除く)、福島、栃木、茨城、埼玉、千葉、群馬、神奈川
    ///
    /// 返り値の (x, y) は日本の測地系の慣例に従い x = 北方向, y = 東方向 [m]。
    /// Unity 座標への写像は GeoReference が担当する。
    /// </summary>
    public static class JapanPlaneRectIX
    {
        private const double EllipsoidA = 6378137.0;        // GRS80 長半径 [m]
        private const double InvFlattening = 298.257222101; // GRS80 逆扁平率
        private const double ScaleM0 = 0.9999;              // 縮尺係数

        private static readonly double Phi0;
        private static readonly double Lambda0;
        private static readonly double NRatio;
        private static readonly double[] Acoef;
        private static readonly double[] Alpha;
        private static readonly double[] Beta;
        private static readonly double[] Delta;
        private static readonly double ABar;
        private static readonly double SBar;

        static JapanPlaneRectIX()
        {
            Phi0 = 36.0 * Math.PI / 180.0;
            Lambda0 = (139.0 + 50.0 / 60.0) * Math.PI / 180.0;

            double n = 1.0 / (2.0 * InvFlattening - 1.0);
            NRatio = n;

            double n2 = n * n;
            double n3 = n2 * n;
            double n4 = n3 * n;
            double n5 = n4 * n;
            double n6 = n5 * n;

            Acoef = new[]
            {
                1.0 + n2 / 4.0 + n4 / 64.0,
                -1.5 * (n - n3 / 8.0 - n5 / 64.0),
                (15.0 / 16.0) * (n2 - n4 / 4.0),
                -(35.0 / 48.0) * (n3 - (5.0 / 16.0) * n5),
                (315.0 / 512.0) * n4,
                -(693.0 / 1280.0) * n5
            };

            Alpha = new[]
            {
                0.5 * n - (2.0 / 3.0) * n2 + (5.0 / 16.0) * n3 + (41.0 / 180.0) * n4 - (127.0 / 288.0) * n5,
                (13.0 / 48.0) * n2 - (3.0 / 5.0) * n3 + (557.0 / 1440.0) * n4 + (281.0 / 630.0) * n5,
                (61.0 / 240.0) * n3 - (103.0 / 140.0) * n4 + (15061.0 / 26880.0) * n5,
                (49561.0 / 161280.0) * n4 - (179.0 / 168.0) * n5,
                (34729.0 / 80640.0) * n5
            };

            Beta = new[]
            {
                0.5 * n - (2.0 / 3.0) * n2 + (37.0 / 96.0) * n3 - (1.0 / 360.0) * n4 - (81.0 / 512.0) * n5,
                (1.0 / 48.0) * n2 + (1.0 / 15.0) * n3 - (437.0 / 1440.0) * n4 + (46.0 / 105.0) * n5,
                (17.0 / 480.0) * n3 - (37.0 / 840.0) * n4 - (209.0 / 4480.0) * n5,
                (4397.0 / 161280.0) * n4 - (11.0 / 504.0) * n5,
                (4583.0 / 161280.0) * n5
            };

            Delta = new[]
            {
                2.0 * n - (2.0 / 3.0) * n2 - 2.0 * n3 + (116.0 / 45.0) * n4 + (26.0 / 45.0) * n5 - (2854.0 / 675.0) * n6,
                (7.0 / 3.0) * n2 - (8.0 / 5.0) * n3 - (227.0 / 45.0) * n4 + (2704.0 / 315.0) * n5 + (2323.0 / 945.0) * n6,
                (56.0 / 15.0) * n3 - (136.0 / 35.0) * n4 - (1262.0 / 105.0) * n5 + (73814.0 / 2835.0) * n6,
                (4279.0 / 630.0) * n4 - (332.0 / 35.0) * n5 - (399572.0 / 14175.0) * n6,
                (4174.0 / 315.0) * n5 - (144838.0 / 6237.0) * n6,
                (601676.0 / 22275.0) * n6
            };

            ABar = (ScaleM0 * EllipsoidA / (1.0 + n)) * Acoef[0];

            double s = Acoef[0] * Phi0;
            for (int j = 1; j <= 5; j++)
            {
                s += Acoef[j] * Math.Sin(2.0 * j * Phi0);
            }
            SBar = (ScaleM0 * EllipsoidA / (1.0 + n)) * s;
        }

        /// <summary>緯度経度 [deg] を平面直角座標 第IX系 [m] に変換する。x = 北, y = 東。</summary>
        public static void ToPlane(double latDeg, double lonDeg, out double x, out double y)
        {
            double phi = latDeg * Math.PI / 180.0;
            double lam = lonDeg * Math.PI / 180.0;

            double lc = Math.Cos(lam - Lambda0);
            double ls = Math.Sin(lam - Lambda0);

            double r = 2.0 * Math.Sqrt(NRatio) / (1.0 + NRatio);
            double sinPhi = Math.Sin(phi);
            double t = Math.Sinh(Atanh(sinPhi) - r * Atanh(r * sinPhi));
            double tBar = Math.Sqrt(1.0 + t * t);

            double xi = Math.Atan2(t, lc);
            double eta = Atanh(ls / tBar);

            double sx = 0.0;
            double sy = 0.0;
            for (int j = 1; j <= 5; j++)
            {
                double aj = Alpha[j - 1];
                sx += aj * Math.Sin(2.0 * j * xi) * Math.Cosh(2.0 * j * eta);
                sy += aj * Math.Cos(2.0 * j * xi) * Math.Sinh(2.0 * j * eta);
            }

            x = ABar * (xi + sx) - SBar;
            y = ABar * (eta + sy);
        }

        /// <summary>平面直角座標 第IX系 [m] を緯度経度 [deg] に変換する。x = 北, y = 東。</summary>
        public static void ToLatLon(double x, double y, out double latDeg, out double lonDeg)
        {
            double xi = (x + SBar) / ABar;
            double eta = y / ABar;

            double dxi = 0.0;
            double deta = 0.0;
            for (int j = 1; j <= 5; j++)
            {
                double bj = Beta[j - 1];
                dxi += bj * Math.Sin(2.0 * j * xi) * Math.Cosh(2.0 * j * eta);
                deta += bj * Math.Cos(2.0 * j * xi) * Math.Sinh(2.0 * j * eta);
            }

            double xi2 = xi - dxi;
            double eta2 = eta - deta;

            double chi = Math.Asin(Math.Sin(xi2) / Math.Cosh(eta2));

            double phi = chi;
            for (int j = 1; j <= 6; j++)
            {
                phi += Delta[j - 1] * Math.Sin(2.0 * j * chi);
            }

            latDeg = phi * 180.0 / Math.PI;
            lonDeg = (Lambda0 + Math.Atan2(Math.Sinh(eta2), Math.Cos(xi2))) * 180.0 / Math.PI;
        }

        // Math.Atanh は実行環境によって未提供のため自前で定義する
        private static double Atanh(double v)
        {
            return 0.5 * Math.Log((1.0 + v) / (1.0 - v));
        }
    }
}
