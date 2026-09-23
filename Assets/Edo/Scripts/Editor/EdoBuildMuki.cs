// 向き(正面)の解き — EdoBuild の partial (2026-09-22・EDO-0261 ③)
//   ⭐ **なぜ共通の層に置くか。**「棟の正面をどちらへ向けるか」は邸をまたいで同じ問いで、
//      答えは二つの宣言の引き算でしかない:
//        ① **図が決める**「この棟の正面はどの方位か」(指図の `front` = 東/西/南/北)
//        ② **部材が決める**「その部材の正面はローカルのどの軸か」(`bom[].axis.front` = +X / +Z …)
//      yaw = ①の方位 − ②のローカル方位。⛔ 邸ビルダーがこの引き算を書き写さない(規則21)。
//   ⭐ 山王社が踏んだ型(2026-09-22): 社殿5棟の部材は **ローカル +X = 正面**、同じ社地へ足す
//      堂宇10棟の部材は **ローカル +Z = 正面**。yaw 0 で揃えて据えると後の10棟だけ 90° 北を向く。
//      ⇒ **部材ごとに違う**ので、実装が「この邸の正面は +X」と決め打ちしてはいけない。
//   ⛔ **方位の語も軸の綴りも「設計値」ではない**(語の辞書)。⛔ 宣言が無いときに 0 で埋めない —
//      `false` を返し、呼んだ側が「向きが宣言されていない」と刷って差し戻すこと。
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**方位の語 → 真北からの角[°・上から見て時計回り]。**16 方位。
    /// ⛔ 設計値ではない(語の辞書)。⭕ 同じ辞書が `Tools/Sashizu/bake_impl.py` の `_DIR_DEG` にある
    /// (門の yaw を焼く側)。⚠ 二重に持っているので、足すときは両方に足すこと。
    /// 世界の約束は **+Z = 北 / +X = 東**(算出物の `grid` が x = x0 + u×ken / z = z0 + v×ken)。</summary>
    public static bool DirDeg(string compass, out float deg)
    {
        deg = 0f;
        if (string.IsNullOrEmpty(compass)) return false;
        switch (compass.Trim())
        {
            case "北": deg = 0f; return true;
            case "北北東": deg = 22.5f; return true;
            case "北東": deg = 45f; return true;
            case "東北東": deg = 67.5f; return true;
            case "東": deg = 90f; return true;
            case "東南東": deg = 112.5f; return true;
            case "南東": deg = 135f; return true;
            case "南南東": deg = 157.5f; return true;
            case "南": deg = 180f; return true;
            case "南南西": deg = 202.5f; return true;
            case "南西": deg = 225f; return true;
            case "西南西": deg = 247.5f; return true;
            case "西": deg = 270f; return true;
            case "西北西": deg = 292.5f; return true;
            case "北西": deg = 315f; return true;
            case "北北西": deg = 337.5f; return true;
        }
        return false;
    }

    /// <summary>**部材のローカル軸の綴り → 真北からの角[°]**(Unity の Y 回転 0 のとき。+Z=北 / +X=東)。
    /// `bom[].axis.front` / `axis.pass` の綴りと同じ語彙。⛔ 設計値ではない(語の辞書)。</summary>
    public static bool LocalAxisDeg(string axis, out float deg)
    {
        deg = 0f;
        if (string.IsNullOrEmpty(axis)) return false;
        switch (axis.Trim())
        {
            case "+Z": case "Z": deg = 0f; return true;
            case "+X": case "X": deg = 90f; return true;
            case "-Z": case "−Z": deg = 180f; return true;
            case "-X": case "−X": deg = 270f; return true;
        }
        return false;
    }

    /// <summary>**正面を向ける yaw[°]**。<paramref name="front"/> = 図が宣言する正面の方位(東/西/南/北…)、
    /// <paramref name="localFront"/> = 部材が宣言する「正面はローカルのどの軸か」(+X / +Z …)。
    /// yaw = 方位 − ローカル方位(0〜360)。
    ///
    /// <para>⛔ **どちらかが宣言されていなければ false**(yaw は出さない)。呼んだ側は
    /// 「向きが宣言されていない」と刷って、⭕ **その棟だけ既定の姿(ふつうは yaw 0)で据え、
    /// 突き合わせに立てる**こと。⛔ 0 で埋めて「据わった」と報告しない(規則19: 未検査であって合格ではない)。</para>
    ///
    /// <para>⚠ この式は門の yaw を焼く `Tools/Sashizu/bake_impl.py::gate_yaw`(消えた生成器
    /// `build_sanno_sashizu.py::derive_gate_yaw` の写し)と同じ引き算。⛔ 別の式を作らない。</para></summary>
    public static bool FaceYaw(string front, string localFront, out float yaw)
    {
        yaw = 0f;
        float a, b;
        if (!DirDeg(front, out a) || !LocalAxisDeg(localFront, out b)) return false;
        yaw = Mathf.Repeat(a - b, 360f);
        return true;
    }

    /// <summary>**方位の語 → 世界の単位ベクトル**(XZ 平面。+Z=北 / +X=東)。
    /// 「正面の前へ出す」「南側へ寄せる」のように**向きを持って測る**ときに使う。
    /// ⛔ 出す距離はここで決めない — 距離は図が宣言する値(⛔ 実装が発明しない)。</summary>
    public static bool DirVec(string compass, out Vector2 v)
    {
        v = Vector2.zero;
        float d;
        if (!DirDeg(compass, out d)) return false;
        float r = d * Mathf.Deg2Rad;
        v = new Vector2(Mathf.Sin(r), Mathf.Cos(r));
        return true;
    }
}
