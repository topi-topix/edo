// 寺社の本堂(と坊・社家の主屋)を、間数ごとに焼いた入母屋で組む — EdoBuild の一部(規則21)。
//
// ⛔ このファイルに「どの区画がどの間数か」を書かない — それは類型表(`main_hall_ken`)と
//    EdoTypologyBuilder.Jisha.cs の持ち場。ここに書くのは **どう組むか** だけ。
//
// ⭐ 何を直したか(EDO-0354・2026-09-22): 2026-09-21 まで jisha の主屋は `kind` で
//    `VK.BigHouse`(寺)/ `VK.House`(坊・社家)を選ぶだけで、表の `main_hall_ken`(16 区画)は
//    **ビルダーが名を読みもしない欄**だった。6 間の坊と 7 間の寺が同じ姿で建っていた。
//    御殿複合(EdoBuildGoten.cs)と同じ作り — `EdoGotenKit.Mune` に、**間数ぴったりに焼いた入母屋**を載せる。
//
// 【組み方】桁行 w 間・梁間 d 間(外形)。`Mune` の身舎は梁間 d−2 間・入側は前後に 1 間ずつ、
//   濡縁は桁行の両側。屋根は `EdoAssets.Goten.RoofIrimoya_(w, d)`(無い寸法は
//   `build_goten_roof.py -- <w×1.818> <d×1.818> Goten_Roof_Irimoya_<w>x<d>ken` で足す)。
// 【向き】ローカル +Z = 表。呼び手が門の方へ向ける(寺は参道の正面に本堂の表を向ける)。
// 【ピボット】**外形の中心・床レベル**(`Mune` の原点は南西角なので、中心へずらして包む)。
//   ⛔ 中心は据える基準ではない — 据えるのは `SeatOnGround` の接地箇所(規則21)。

using System;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>間数(外形)で本堂を建てる。桁行 <paramref name="wKen"/> ≥ 梁間 <paramref name="dKen"/>
    /// になるよう入れ替える(大棟は桁行に架かる)。焼いた入母屋が無い寸法は null を返し、
    /// <paramref name="note"/> に理由を書く(⛔ 黙って骨組みだけ建てない・規則19)。</summary>
    public static GameObject Honden(Transform parent, string name, int wKen, int dKen, out string note)
    {
        note = "";
        if (wKen < dKen) { int t = wKen; wKen = dKen; dKen = t; }
        if (dKen < 3) { note = string.Format("⛔ 本堂 {0}x{1}間: 梁間が 3 間未満(身舎 1 間+入側 2 間が要る)", wKen, dKen); return null; }
        string roof = EdoAssets.Goten.RoofIrimoya_(wKen, dKen);
        if (AssetDatabase.LoadAssetAtPath<GameObject>(roof) == null)
        {
            note = string.Format("⛔ 本堂 {0}x{1}間: 焼いた入母屋が無い({2}) — build_goten_roof.py で足す", wKen, dKen, roof);
            return null;
        }
        float k = EdoGotenKit.K;
        var root = new GameObject(name);
        root.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(root, "honden " + name);
        // Mune の原点は南西角(外形の角)。中心が根のピボットになるようずらす。
        var mu = EdoGotenKit.Mune(name + "_Mune", root.transform,
                                  new Vector3(-wKen * k * 0.5f, 0f, -dKen * k * 0.5f), 0f,
                                  wKen, dKen - 2, 1, 0.62f, roof);
        if (mu == null)
        {
            UnityEngine.Object.DestroyImmediate(root);
            note = string.Format("⛔ 本堂 {0}x{1}間: 棟が組めなかった(部材を検める)", wKen, dKen);
            return null;
        }
        // ⭐ 屋根の駒に名を付ける(2026-09-22・EDO-0354 ②)。御殿キットの屋根は `Goten_Roof_Irimoya_…` で
        //    `Body()` の屋根の篩(yane/noki/…)に**掛からない**ので、withRoof を false にしても屋根が落ちず
        //    「軒先で測る/壁体で測る」の分岐が恒真になっていた(本堂の頂点 38870 = 38870)。
        //    ⛔ `IsRoofName` の篩は広げない — この駒の中だけで名を付ける(EdoBuildGoten と同じ手)。
        NameRoofs(mu);
        note = string.Format("本堂 {0}x{1}間", wKen, dKen);
        return root;
    }
}
