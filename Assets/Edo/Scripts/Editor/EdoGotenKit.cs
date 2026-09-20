// 御殿の棟を「江戸間の柱割り」で組むキット。
//
// Village Kit のプレハブ(閉じた一軒家)では入側から壁が見えて御殿にならない、という
// ユーザー裁定(2026-08-14)を受けて、Blender で部材から起こし直したものを並べる。
// 部材の生成は Tools/Blender/(README に規約と落とし穴)。パスは EdoAssets.Goten。
//
// 部材の規約: 幅X・高さY・厚みZ、**表(見え掛かり)= +Z**、ピボット = 一間の中心・床レベル。
//   1間 = 1.818m / 建具高 = 2.727m / 柱 = 0.182角 / 畳は一間角(=江戸間2畳)。
//
// 棟の構成は SKILL(unity-buke-yashiki) §B-2 のとおり「身舎のまわりに入側が回る」。
// ここでは前後(梁間方向)に入側を取る型を作る。左右の妻側は白壁。
//
// ⚠ 屋根は棟の寸法ごとに Blender で生成する:
//     blender --background --python Tools/Blender/build_goten_roof.py -- <桁行W> <梁間D> <名前>
//   ここでは寸法の合う既成の屋根があれば載せ、無ければ骨組みだけ組んで警告を出す。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoGotenKit
{
    public const float K = EdoAssets.Goten.Ken;      // 1.818
    public const float H = EdoAssets.Goten.DoorH;    // 2.727
    public const float JODAN = 0.15f;                // 上段の段の高さ

    // --- 雁行する棟どうしの屋根の取り合い ------------------------------------
    // ユーザー裁定(2026-08-14): **(a) 渡廊下の低い切妻で処理する**。谷や隅は作らず、
    // 各棟は独立した入母屋のまま置いて、その軒下を渡廊下の屋根がくぐる(福井図・二条城も同形)。
    // → 渡廊下の大棟の天端が棟の軒先より低い、が成立条件。数値は Roka が持つ。
    public const float MUNE_EAVE  = H - 0.15f;   // 棟の軒先(床から) = 2.577。Mune が屋根を置く高さ
    public const float ROKA_EAVE  = 1.55f;       // 渡廊下の軒先(床から)
    public const float ROKA_RIDGE = 0.953f;      // 軒先→大棟の天端(build_goten_roof の make_kirizuma)
    public const float ROKA_KETA  = 0.28f;       // 軒先→桁の天端。廊下の縁での屋根裏(0.60x0.5456)の直下
    // static readonly にしておく — const 同士だと畳み込まれて下のガードが「到達しないコード」になる
    static readonly float RokaRidgeTop = ROKA_EAVE + ROKA_RIDGE;   // 渡廊下の大棟の天端(床から)= 2.503

    /// <summary>濡縁の踏板は畳床より 0.28 下がる(Nureen 据付と同じ値)。
    /// ⚠ 2026-09-08(棟梁差戻し): 普請奉行の実測「軒下端(床上)」の基準線はこの濡縁面
    /// (外から見える唯一の「床」の縁)であって畳面(floor)ではないと判明 — 実測 27.340 は
    /// floor(0.62)−0.28 と mm 単位で一致した。<see cref="Mune"/> の <c>eaveAboveFloor</c> はこの縁から測る。</summary>
    public const float NUREEN_DROP = 0.28f;

    static GameObject Load(string path)
    {
        var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (go == null) Debug.LogError("[GotenKit] 見つからない: " + path);
        return go;
    }

    static GameObject Put(string path, Transform parent, Vector3 lp, float ry, float scaleY = 1f)
    {
        var src = Load(path);
        if (src == null) return null;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
        go.transform.localPosition = lp;
        go.transform.localRotation = Quaternion.Euler(0f, ry, 0f);
        if (!Mathf.Approximately(scaleY, 1f))
            go.transform.localScale = new Vector3(1f, scaleY, 1f);
        return go;
    }

    /// <summary>走り(local X)を縮めて据える版。⚠ 半間の端数を吸うためだけに使う
    /// (⛔ 部材を伸ばす向きには使わない)。</summary>
    static GameObject Put(string path, Transform parent, Vector3 lp, float ry, Vector3 scale)
    {
        var src = Load(path);
        if (src == null) return null;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
        go.transform.localPosition = lp;
        go.transform.localRotation = Quaternion.Euler(0f, ry, 0f);
        go.transform.localScale = scale;
        return go;
    }

    /// <summary>棟を1つ組む。
    /// nx = 身舎の桁行の間数(X) / nzZashiki = 身舎の間数(Z) / iri = 梁間(Z)方向の入側の間数。
    /// iriX = 桁行(X)方向の入側の間数。**1 にすると入側が四方に回る**(既定 0 = 前後だけ)。
    /// moyaBay = 身舎の部屋割り(間)。身舎の中の柱はこの通りの交点にしか立てず、
    /// partition=true(既定)なら同じ通りに襖+欄間を通して 3x3間=18畳の続き間にする。
    /// 原点は棟の南西角(入側を含めた外形の角・床レベル)。yaw は親側で与える。
    /// roofAsset に寸法の合う屋根FBXのパスを渡すと載せる(null なら骨組みのみ)。
    ///
    /// ⚠ 四方に回すのはユーザー裁定(2026-08-14)。指図が「入側が各棟の外周を巡り、隣の棟の
    /// 入側と辺を共有して直に繋がる/二条城で六棟を取り囲む廊下が一周」と書いているため。
    /// 前後だけにすると妻側が白壁のまま廊下に面し、Village Kit のプレハブを捨てた理由
    /// (廊下から壁が見える)がそのまま再現される。
    ///
    /// <para>⛔⛔ <paramref name="roofAtFloor"/> = **帯割りの屋根**(<see cref="EdoAssets.Goten.RoofBanded"/>)
    /// を載せるときだけ true。あちらは **FBX の z=0 が「床」**で、入母屋・寄棟の FBX(z=0 が軒先)と
    /// 基準が違う。⛔ 取り違えると **3.4m(軒高ぶん)浮く**。
    /// <paramref name="roofYaw"/> は棟の local に対する屋根の回し(度)— 帯割りの部材は
    /// **モデル局所 +X = 江戸間格子の +u** に焼いてあるので、桁行が v の棟では
    /// 「世界の yaw が格子の yaw ちょうどになる」差ぶんをここへ渡す(⛔ 呼び側で 90° を足さない)。</para>
    ///
    /// <para>⚠ 2026-09-08(普請検査差戻し→棟梁が実測式に直した): <paramref name="roofAtFloor"/>=false
    /// (入母屋・寄棟)の既定は `floor + H − 0.15`(=3.197m・棟の建具高 H に従属する値で、指図の軒高
    /// const とは無関係)。附属屋(厩・長屋類)や帯割り御殿のように**指図が軒高 const を持つ棟**では、
    /// <paramref name="roofEaveLocalY"/> に **指図の軒高(軒下端の濡縁上高さ・m。`gotenEave`/
    /// `nagayaGataEave`/`umayaEave`)をそのまま渡す**(既定 NaN=従来どおり)。
    /// ⛔⛔ **部材の系列(帯割り/入母屋)ごとにピボット基準が違う**(帯割りは z=0=床、入母屋は
    /// z=0=軒先のはずが実測では系列ごとに一定の食い違いがある)ので、**定数オフセットを決め打ちしない**。
    /// ここでは <paramref name="roofEaveLocalY"/> が非 NaN のとき、**据えた実メッシュの軒下端
    /// (`MeshFilter.sharedMesh.bounds.min.y`。ピボットからの実測)を測り**、軒下端が
    /// `(floor − NUREEN_DROP) + roofEaveLocalY` に来るよう Put 後に鉛直へ寄せ直す
    /// (roofAtFloor の値に関係なく同じ式が効く — 実測ベースなので系列の差を吸収する)。</para></summary>
    public static GameObject Mune(string name, Transform parent, Vector3 pos, float yaw,
                                  int nx, int nzZashiki, int iri = 1,
                                  float floor = 0.62f, string roofAsset = null,
                                  bool nureen = true, bool ceiling = true,
                                  int[] openBaysWest = null, int[] openBaysEast = null,
                                  int jodanFromIx = -1, int iriX = 0, int moyaBay = 3,
                                  bool partition = true,
                                  bool roofAtFloor = false, float roofYaw = 0f,
                                  float roofEaveLocalY = float.NaN)
    {
        if (moyaBay < 1) moyaBay = 1;
        // 妻側の建具を省く区画(床の間・違い棚・帳台構が入る所)。塞いだままだと飾りが壁の裏に隠れる
        System.Func<int[], int, bool> isOpen = (arr, j) => {
            if (arr == null) return false;
            foreach (var v in arr) if (v == j) return true;
            return false;
        };
        int nxZashiki = nx;
        nx = nxZashiki + 2 * iriX;
        int nz = nzZashiki + 2 * iri;
        float W = nx * K, D = nz * K;
        // 入側の升目(床は板敷き・畳を敷かない)
        System.Func<int, int, bool> isIrikawa = (i, j) =>
            j < iri || j >= nz - iri || i < iriX || i >= nx - iriX;

        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.localPosition = pos;
        g.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);

        // 上段の間 — jodanFromIx より奥(+X)の身舎は床が一段(0.15)上がる
        System.Func<int, bool, float> lv = (i, isIri) =>
            (jodanFromIx >= 0 && i >= jodanFromIx && !isIri) ? floor + JODAN : floor;

        // 床 — 入側は板敷き、身舎は畳
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                bool isIri = isIrikawa(i, j);
                Put(isIri ? EdoAssets.Goten.FloorBoard : EdoAssets.Goten.Tatami, g.transform,
                    new Vector3(i * K + K / 2f, lv(i, isIri), j * K + K / 2f), 0f);
            }

        // 上段框 — 段の際に通す
        if (jodanFromIx > iriX && jodanFromIx < nx - iriX)
            for (int j = iri; j < nz - iri; j++)
                Put(EdoAssets.Goten.JodanKamachi, g.transform,
                    new Vector3(jodanFromIx * K, floor, j * K + K / 2f), 270f);

        // 建具 — 身舎と入側の境に障子。表(+Z)を入側へ向ける。
        // 隅の升目(入側どうしが交わる所)には建具を立てない — 廊下が角を回れなくなる
        if (iri > 0)
            for (int i = iriX; i < nx - iriX; i++)
            {
                float y = lv(i, false);
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, y, iri * K), 180f);
                Put(EdoAssets.Goten.Shoji1ken, g.transform,
                    new Vector3(i * K + K / 2f, y, (nz - iri) * K), 0f);
            }

        // 妻側 — 入側が回っていれば障子、回っていなければ白壁。
        // どちらも openBays* の区画だけは空けて座敷飾りに明け渡す
        for (int j = iri; j < nz - iri; j++)
        {
            float c = j * K + K / 2f;
            if (!isOpen(openBaysWest, j))
            {
                if (iriX > 0)
                    Put(EdoAssets.Goten.Shoji1ken, g.transform,
                        new Vector3(iriX * K, lv(iriX, false), c), 270f);
                else
                    Put(EdoAssets.Goten.WallPlaster, g.transform,
                        new Vector3(0f, lv(0, false), c), 90f);
            }
            if (!isOpen(openBaysEast, j))
            {
                if (iriX > 0)
                    Put(EdoAssets.Goten.Shoji1ken, g.transform,
                        new Vector3((nx - iriX) * K, lv(nx - iriX - 1, false), c), 90f);
                else
                    Put(EdoAssets.Goten.WallPlaster, g.transform,
                        new Vector3(W, lv(nx - 1, false), c), 270f);
            }
        }

        // 続き間の間仕切り — 身舎を部屋割りの通り(moyaBay)で襖+欄間に切る。
        // ⚠ 柱を柱通りだけに減らした(bookmark 2026-08-15 #2)ので、これが無いと身舎が
        //   仕切りのない畳の平原になる。大広間の身舎は 20x12間 = 36.4x21.8m あり、
        //   一室では御殿にならない(実際の大広間も上段・二の間・三の間…の続き間)。
        //   3間ごとに通すと 3x3間 = 18畳の部屋が並ぶ。
        //   端数の帯(moyaBay で割り切れない残り)には通さない — 半端な小部屋を作らないため。
        if (partition)
        {
            // 桁行(X)の柱通り = 梁間方向へ通る襖(表は ±X)
            for (int ix = iriX + moyaBay; ix < nx - iriX; ix += moyaBay)
                for (int j = iri; j < nz - iri; j++)
                {
                    var c = new Vector3(ix * K, lv(ix, false), j * K + K / 2f);
                    Put(EdoAssets.Goten.Fusuma, g.transform, c, 90f);
                    Put(EdoAssets.Goten.Ranma, g.transform,
                        c + new Vector3(0f, EdoAssets.Goten.Uchinori, 0f), 90f);
                }
            // 梁間(Z)の柱通り = 桁行方向へ通る襖(表は ±Z)
            for (int jz = iri + moyaBay; jz < nz - iri; jz += moyaBay)
                for (int i = iriX; i < nx - iriX; i++)
                {
                    var c = new Vector3(i * K + K / 2f, lv(i, false), jz * K);
                    Put(EdoAssets.Goten.Fusuma, g.transform, c, 0f);
                    Put(EdoAssets.Goten.Ranma, g.transform,
                        c + new Vector3(0f, EdoAssets.Goten.Uchinori, 0f), 0f);
                }
        }

        // 柱 — **柱通りにだけ立てる**。
        // ⚠ 以前は一間ごとの格子点すべてに立てていた。広間の畳の上に 1.818m ピッチで柱が
        //   林立して「広間の中にこんなに柱が立っているのはおかしい」とユーザー指摘
        //   (bookmark 2026-08-15 #2)。書院造の身舎は大梁で飛ばすので、室内に立つのは
        //   部屋の隅(=間仕切りの通りの交点)だけ。
        //   立てる所: ①外周 ②入側と身舎の境(建具が載るので一間ごと) ③身舎の中は
        //   部屋割りの通り(moyaBay 間ごと)の交点だけ。
        for (int i = 0; i <= nx; i++)
            for (int j = 0; j <= nz; j++)
            {
                bool perim = i == 0 || i == nx || j == 0 || j == nz;
                bool iriLine = (iriX > 0 && (i == iriX || i == nx - iriX))
                            || (iri > 0 && (j == iri || j == nz - iri));
                bool roomLine = ((i - iriX) % moyaBay == 0 || i == nx - iriX)
                             && ((j - iri) % moyaBay == 0 || j == nz - iri);
                if (perim || iriLine || roomLine)
                    Put(EdoAssets.Goten.Column, g.transform, new Vector3(i * K, floor, j * K), 0f);
            }

        if (ceiling)
            for (int i = 0; i < nx; i++)
                for (int j = 0; j < nz; j++)
                    Put(EdoAssets.Goten.Ceiling, g.transform,
                        new Vector3(i * K + K / 2f, floor + H, j * K + K / 2f), 0f);

        if (nureen && iri > 0)
            for (int i = 0; i < nx; i++)
            {
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(i * K + K / 2f, floor - 0.28f, 0f), 0f);
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(i * K + K / 2f, floor - 0.28f, D), 180f);
            }
        // 妻側の濡縁 — 入側が四方に回るときだけ
        if (nureen && iriX > 0)
        {
            for (int j = 0; j < nz; j++)
            {
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(0f, floor - 0.28f, j * K + K / 2f), 90f);
                Put(EdoAssets.Goten.Nureen, g.transform,
                    new Vector3(W, floor - 0.28f, j * K + K / 2f), 270f);
            }
            // 四隅の升目(0.891角)。ここを空けると床が抜け、外縁に回した高欄が隅で切れる。
            // ⚠ 部材の**体積はピボットの (-X,-Z) 側**にある(高欄が +X 面と -Z 面、という
            //   説明とは逆の象限)。yaw は「体積が隅の外向きの象限へ回る」向きで取ること —
            //   90度ずれていて、四隅とも内側を埋めて外の升目が空いていた
            //   (ユーザー指摘 2026-08-15「よく見たら濡れ縁が切れてます」)。
            //   yaw 0 → 体積(-X,-Z) / 90 → (-X,+Z) / 180 → (+X,+Z) / 270 → (+X,-Z)
            Put(EdoAssets.Goten.NureenCorner, g.transform, new Vector3(W, floor - 0.28f, 0f), 270f);
            Put(EdoAssets.Goten.NureenCorner, g.transform, new Vector3(0f, floor - 0.28f, 0f), 0f);
            Put(EdoAssets.Goten.NureenCorner, g.transform, new Vector3(0f, floor - 0.28f, D), 90f);
            Put(EdoAssets.Goten.NureenCorner, g.transform, new Vector3(W, floor - 0.28f, D), 180f);
        }

        if (!string.IsNullOrEmpty(roofAsset))
        {
            // ⛔ 帯割り(roofAtFloor)は FBX の z=0 が**床**。入母屋・寄棟(z=0 が軒先)と足す高さが違う
            //   ⚠ ただし roofEaveLocalY が指定されているときは、この初期値は仮置きに過ぎない
            //   (Put 後に実メッシュを測って鉛直へ寄せ直すので roofAtFloor の違いは吸収される)
            bool haveEaveTarget = !float.IsNaN(roofEaveLocalY);
            float roofY = roofAtFloor ? floor : (haveEaveTarget ? floor : floor + H - 0.15f);
            var r = Put(roofAsset, g.transform,
                        new Vector3(W / 2f, roofY, D / 2f), roofYaw);
            if (r != null)
            {
                var mf = r.GetComponentInChildren<MeshFilter>();
                if (mf != null)
                {
                    // ⭐ 2026-09-08: 軒高は「軒下端(濡縁上の高さ)」で読む(普請奉行の裁定)。
                    //   部材の系列(帯割り/入母屋)ごとにピボット基準が食い違うので、**据えた実メッシュの
                    //   軒下端(bounds.min.y。ピボットからの実測)を測り**、目標の高さへ鉛直に寄せる。
                    //   ⛔ 系列ごとに定数オフセットを決め打ちしない(実メッシュから測る・規則5)。
                    if (haveEaveTarget)
                    {
                        float meshEaveLocal = mf.sharedMesh.bounds.min.y;         // ピボット→軒下端の実測(mesh空間)
                        float targetLocalY = (floor - NUREEN_DROP) + roofEaveLocalY;  // 棟の local 空間での目標
                        float neededPivotY = targetLocalY - meshEaveLocal;
                        var lp = r.transform.localPosition;
                        r.transform.localPosition = new Vector3(lp.x, neededPivotY, lp.z);
                    }
                    // 屋根の寸法が棟に合っているか確かめる(軒の出0.9m×2を見込む)
                    // 許容 0.45 — 隅棟が軒先の角で棟幅の半分(0.20)だけ外へ出るため、
                    // 外形は「軒の出×2」よりいつも 0.35 ほど大きく出る
                    // ⚠ 屋根を回して据える(帯割り)ときは、棟の local から見た差し渡しで比べる
                    var s0 = mf.sharedMesh.bounds.size;
                    bool swap = Mathf.Abs(Mathf.Sin(roofYaw * Mathf.Deg2Rad)) > 0.5f;
                    var s = swap ? new Vector3(s0.z, s0.y, s0.x) : s0;
                    if (Mathf.Abs(s.x - (W + 1.8f)) > 0.45f || Mathf.Abs(s.z - (D + 1.8f)) > 0.45f)
                        Debug.LogWarning(string.Format(
                            "[GotenKit] {0}: 屋根が棟に合っていない。屋根 {1:F2}x{2:F2} / 棟 {3:F2}x{4:F2}。" +
                            "build_goten_roof.py -- {3:F3} {4:F3} で作り直す", name, s.x, s.z, W, D));
                }
            }
        }
        else
        {
            Debug.LogWarning(string.Format(
                "[GotenKit] {0}: 屋根なし。blender --background --python Tools/Blender/build_goten_roof.py -- {1:F3} {2:F3} <名前>",
                name, W, D));
        }
        return g;
    }

    /// <summary>渡廊下で棟をつなぐ。板敷きの床 + 柱 + 桁 + 高欄 + 低い切妻屋根。
    /// 原点は廊下の南西角(床レベル)、桁行は +X に nx 間、幅は +Z へ 1間。yaw は親側で与える。
    ///
    /// 屋根は棟の軒下(床から 2.577)をくぐる高さに納めてある — 雁行の取り合いは
    /// 谷を作らずこれで処理する、というユーザー裁定(2026-08-14)に従う。
    /// 屋根FBXは両端が 0.30 ずつ長い。棟の軒の出 0.90 と合わせて 1.20 重なるので、
    /// **廊下の両端は必ず棟の壁面に突き付ける**(離すと取り合いに隙間が出る)。
    ///
    /// koranS/koranN = 桁行に沿う両縁の高欄(z=0 側 / z=K 側)。棟に接する側は false にする。
    /// colStart/colEnd = 両端の柱通り。**棟の柱と重なるので、棟に突き付ける側は false にする**
    /// (同じ柱を二重に置くと面が z-fighting する)。
    ///
    /// ⚠⚠ **`nx` は整数とはかぎらない。** 土井の `L_ImaDaidokoro` は **1.5間**で、
    /// 整数へ丸めて 2間で組むと居間棟へ **0.909m 食い込む**(2026-09-06 に踏んだ)。
    /// ⇒ **端数は最後の一駒を走り方向へ縮めて吸う**(床板・桁・高欄の X を rem 倍する)。
    /// 屋根は <see cref="EdoAssets.Goten.RoofKirizuma(float)"/> が端数の定尺を引く。
    ///
    /// <para>⭐⭐ **差し掛けの下屋(両流れ)で葺く**とき(松江松平 2026-09-17 ユーザー裁定A)は
    /// <paramref name="geyaHeadLocalY"/> に**廊下の頭の高さ**(この GameObject の local Y。
    /// = その端の当たり − 指図 `roka.clear`)を渡す。独立した切妻(<c>ROKA_EAVE</c>/<c>ROKA_RIDGE</c>)
    /// ではなく <see cref="EdoAssets.Goten.RoofRokaGeya(float)"/> を据える。
    /// ⛔ 既定(NaN)は従来どおりの切妻 — 土井・岡部の渡廊下はそのまま。</para>
    /// <para><paramref name="geyaKobai"/> = 下屋の勾配(指図 `const.sashikakeKobai`)。
    /// **柱・桁の天端は従属値** = 頭 − 幅の半分 × 勾配(= 柱筋での葺き面)。⛔ 数を決め打ちしない。</para>
    /// <para><paramref name="enita"/> = 床を <see cref="EdoAssets.Goten.RokaEnita"/>(厚1寸・
    /// **ピボットが板の天端**)で葺く。⛔ 入側の板敷き <see cref="EdoAssets.Goten.FloorBoard"/>
    /// (厚0.0636・ピボットが底)の置き換えではない。</para></summary>
    public static GameObject Roka(string name, Transform parent, Vector3 pos, float yaw, float nx,
                                  float floor = 0.62f, bool koranS = true, bool koranN = true,
                                  bool roof = true, bool colStart = true, bool colEnd = true,
                                  float geyaHeadLocalY = float.NaN, float geyaKobai = 0f,
                                  bool enita = false)
    {
        bool geya = !float.IsNaN(geyaHeadLocalY);
        if (!geya && RokaRidgeTop > MUNE_EAVE)
            Debug.LogWarning(string.Format(
                "[GotenKit] 渡廊下の大棟 {0:F3} が棟の軒先 {1:F3} より高い — (a)の取り合いが成立しない",
                RokaRidgeTop, MUNE_EAVE));

        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.localPosition = pos;
        g.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);

        // 柱・桁の天端(床から)。下屋のときは**柱筋での葺き面**へ従属させる(⛔ 定数で据えない)
        float colH = geya ? (geyaHeadLocalY - (K * 0.5f) * geyaKobai) - floor
                          : ROKA_EAVE + ROKA_KETA;
        if (colH <= EdoAssets.Goten.BeamH)
            Debug.LogWarning(string.Format(
                "[GotenKit] {0}: 柱筋の頭上が {1:F3}m しか無い — 下屋の頭({2:F3})か床({3:F3})を疑う",
                name, colH, geyaHeadLocalY, floor));
        float colS = colH / H;                              // 柱は建具丈のものを詰めて使う
        string board = enita ? EdoAssets.Goten.RokaEnita : EdoAssets.Goten.FloorBoard;

        // 一間の駒を並べ、**端数は最後の一駒を走り方向へ縮めて吸う**(⛔ 全長を丸めない)
        int nFull = Mathf.FloorToInt(nx + 1e-4f);
        float rem = nx - nFull;                          // 端数[間] 0..1
        int nBay = nFull + (rem > 1e-3f ? 1 : 0);
        for (int i = 0; i < nBay; i++)
        {
            float bw = (i < nFull) ? 1f : rem;           // この駒の間数
            float xc = i * K + bw * K / 2f;
            var sc = new Vector3(bw, 1f, 1f);
            Put(board, g.transform,
                new Vector3(xc, floor, K / 2f), 0f, sc);
            // 桁 — 柱の天端に渡す。屋根の裏に隠れる高さ
            Put(EdoAssets.Goten.Beam, g.transform,
                new Vector3(xc, floor + colH - EdoAssets.Goten.BeamH, 0f), 0f, sc);
            Put(EdoAssets.Goten.Beam, g.transform,
                new Vector3(xc, floor + colH - EdoAssets.Goten.BeamH, K), 180f, sc);
            if (koranS)
                Put(EdoAssets.Goten.Koran, g.transform,
                    new Vector3(xc, floor, 0f), 0f, sc);
            if (koranN)
                Put(EdoAssets.Goten.Koran, g.transform,
                    new Vector3(xc, floor, K), 180f, sc);
        }

        for (int i = 0; i <= nBay; i++)
        {
            if (i == 0 && !colStart) continue;
            if (i == nBay && !colEnd) continue;
            float xl = Mathf.Min(i, nFull) * K + (i > nFull ? rem * K : 0f);
            for (int j = 0; j < 2; j++)
                Put(EdoAssets.Goten.Column, g.transform,
                    new Vector3(xl, floor, j * K), 0f, colS);
        }

        if (roof)
        {
            // ⭐ 下屋はピボットの z=0 が**頭**(葺き下ろしの線)。⛔ 床でも軒先でもないので
            //   floor を足さない — 渡された頭の高さへそのまま据える。
            string asset = geya ? EdoAssets.Goten.RoofRokaGeya(nx)
                                : EdoAssets.Goten.RoofKirizuma(nx);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(asset) == null)
                Debug.LogWarning(string.Format(
                    "[GotenKit] {0}: {1}間の{2}屋根が無い({3})。" +
                    "blender --background --python Tools/Blender/build_goten_roof.py -- {4} {1}",
                    name, EdoAssets.Goten.KenTag(nx), geya ? "下屋" : "切妻", asset,
                    geya ? "geya" : "kirizuma"));
            else
                Put(asset, g.transform,
                    new Vector3(nx * K / 2f, geya ? geyaHeadLocalY : floor + ROKA_EAVE, K / 2f), 0f);
        }
        return g;
    }

    /// <summary>**渡廊下の床の段(框)。**段の線に一間の材を横たえ、
    /// **下の床の天端から上の床の天端まで**を塞ぐ(ピボットは材の底・長さは走りと直交する向き)。
    ///
    /// <para><paramref name="rise"/> = 両側の床の天端の差。⛔ **定数で持たない** —
    /// 指図(松江松平 `links[].dan`)は「框一段」としか言わず、落差は両側の段の面の**従属値**。</para>
    ///
    /// <para>⚠ **框の専用部材が無いので、桁材(成 <see cref="EdoAssets.Goten.BeamH"/>)を
    /// 段の高さへ縮めて充てている。**専用部材が焼けたら差し替える(部材方への候補)。
    /// ⛔ <see cref="EdoAssets.Goten.JodanKamachi"/> は使えない — 上段框は段 0.15 固定で、
    /// 上の床板(奥行 0.55)を抱いているため廊下の床板と二重になる。</para></summary>
    public static GameObject RokaKamachi(string name, Transform parent, Vector3 pos, float yaw, float rise)
    {
        var go = Put(EdoAssets.Goten.Beam, parent, pos, yaw,
                     new Vector3(1f, rise / EdoAssets.Goten.BeamH, 1f));
        if (go != null) go.name = name;
        return go;
    }

    /// <summary>続き間の仕切り = 襖 + 欄間の一列。棟のローカル座標で
    /// x の柱通りに、z0..z1 間(間数)の範囲へ通す。</summary>
    public static void Partition(Transform mune, float floor, int ix, int jz0, int jz1)
    {
        for (int j = jz0; j < jz1; j++)
        {
            var c = new Vector3(ix * K, floor, j * K + K / 2f);
            Put(EdoAssets.Goten.Fusuma, mune, c, 90f);
            Put(EdoAssets.Goten.Ranma, mune,
                c + new Vector3(0f, EdoAssets.Goten.Uchinori, 0f), 90f);
        }
    }

    /// <summary>座敷飾り — 上段の間の奥の壁に 床の間・違い棚・帳台構 を並べる。
    /// wall = 壁面の中心が乗る柱通り、yaw は室内へ向く向き(表=+Z)。3間分を使う。</summary>
    public static void Zashikikazari(Transform mune, Vector3 origin, float yaw,
                                     bool tokonoma = true, bool tana = true, bool chodai = true)
    {
        var f = Quaternion.Euler(0f, yaw, 0f);
        int slot = 0;
        System.Action<string> place = (asset) =>
        {
            var lp = origin + f * new Vector3((slot - 1) * K, 0f, 0f);
            Put(asset, mune, lp, yaw);
            slot++;
        };
        if (tokonoma) place(EdoAssets.Goten.Tokonoma); else slot++;
        if (tana) place(EdoAssets.Goten.Chigaidana); else slot++;
        if (chodai) place(EdoAssets.Goten.Chodaigamae); else slot++;
    }

    /// <summary>上段の間の段(框)。x の柱通りに沿って z0..z1 間へ通す。</summary>
    public static void Jodan(Transform mune, float floor, int ix, int jz0, int jz1, bool faceMinusX = true)
    {
        for (int j = jz0; j < jz1; j++)
            Put(EdoAssets.Goten.JodanKamachi, mune,
                new Vector3(ix * K, floor, j * K + K / 2f), faceMinusX ? 270f : 90f);
    }

    /// <summary>Blender が書き出した御殿FBXのマテリアルを Village Kit の既存 .mat へ当てる。
    /// FBX にはマテリアル名しか入っていないので、Unity 側で remap しないと白い模型になる。
    /// 新しい屋根・部材を生成するたびに走らせる(既に当たっているものは触らない)。
    ///
    /// <para>⛔⛔ **`Everywhere` は 1 本あたり 5〜20 秒**(プロジェクト全体 6.9GB を舐める)。
    /// 83 本を無条件に回すと **1 時間** Unity が 90〜100% CPU で埋まり、その間**他のすべての
    /// MCP 呼び出しが通らなくなる**(2026-09-09 の松江松平で実際に起きた。MCP のタイムアウト
    /// 再送で 7 本積まれて悪化した)。⇒ 既定は **まだ remap の当たっていない FBX だけ**を回す。
    /// 焼き直した FBX は新しいパス(寸法が名前に入る)で入るので `GetExternalObjectMap()` は空 =
    /// 必ず拾われる。⛔ タイムアウトが返っても叩き直さない — 進捗は `Logs/Editor.log` の
    /// `[GotenKit] マテリアル remap:` で数える。</para>
    ///
    /// <para>⚠ 材質名を変えて**同じパスへ**焼き直したときだけ既定では拾えない。そのときは
    /// 「(全部・時間がかかる)」の方を使う。</para></summary>
    [MenuItem("Edo/御殿/新しい御殿FBXのマテリアルをremap")]
    public static void RemapGotenMaterials() { RemapGotenMaterials(true); }

    [MenuItem("Edo/御殿/御殿FBXのマテリアルをremap(全部・1時間かかる)")]
    public static void RemapGotenMaterialsAll() { RemapGotenMaterials(false); }

    public static void RemapGotenMaterials(bool onlyUnmapped)
    {
        int done = 0, still = 0, skipped = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Edo/Models/Goten" }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter;
            if (imp == null) continue;
            // ⭐ 既に当たっている FBX は触らない(上の注記 — これが無いと 1 時間かかる)
            if (onlyUnmapped && imp.GetExternalObjectMap().Count > 0) { skipped++; continue; }
            imp.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            // Inspector の「Search and Remap」と同じ。BasedOnMaterialName + Everywhere で
            // Village Kit の Materials/ にある同名 .mat を拾う(同名の .mat は他に無いことを確認済み)
            imp.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName,
                                        ModelImporterMaterialSearch.Everywhere);
            AssetDatabase.WriteImportSettingsIfDirty(path);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            int n = imp.GetExternalObjectMap().Count;
            if (n > 0) done++;
            else
            {
                still++;
                Debug.LogWarning("[GotenKit] マテリアルが当たらなかった: " + path);
            }
        }
        AssetDatabase.SaveAssets();
        Debug.Log(string.Format("[GotenKit] マテリアル remap: {0}件が解決 / 未解決 {1} / 既に当たっていて触らなかった {2}",
                                done, still, skipped));
    }

    [MenuItem("Edo/御殿/部材テスト棟を建てる (8間x5間)")]
    public static void BuildTestMune()
    {
        var old = GameObject.Find("GotenKitTest");
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject("GotenKitTest");
        root.transform.position = new Vector3(0f, 300f, 0f);   // 既存の街に干渉しない空中で確認する
        var m = Mune("Mune_Test", root.transform, Vector3.zero, 0f, 8, 3, 1,
                     0.62f, EdoAssets.Goten.RoofIrimoya,
                     openBaysEast: new[] { 1, 2, 3 },      // 東の妻壁は座敷飾りに明け渡す
                     jodanFromIx: 5);                      // 東の3間を上段の間にする
        // 身舎を襖で割る(下段2室 + 上段)
        Partition(m.transform, 0.62f, 3, 1, 4);
        Partition(m.transform, 0.62f + JODAN, 5, 1, 4);
        // 飾りのピボット = 開口面。柱通り(x=W)に置くと床框だけが室内へ出る
        Zashikikazari(m.transform, new Vector3(8 * K, 0.62f + JODAN, 2.5f * K), 270f);
        Selection.activeGameObject = m;
        Debug.Log("[GotenKit] テスト棟を y=300 に建てた。確認したら GotenKitTest を消してよい");
    }

    [MenuItem("Edo/御殿/雁行テスト — 棟2つを渡廊下でつなぐ")]
    public static void BuildTestGankou()
    {
        var old = GameObject.Find("GotenGankouTest");
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject("GotenGankouTest");
        root.transform.position = new Vector3(60f, 300f, 0f);   // 空中で確認する

        // 主棟 8間x(身舎3+入側2)。z=4K..5K の帯が北側の入側
        float wA = 8 * K;
        Mune("Mune_A", root.transform, Vector3.zero, 0f, 8, 3, 1,
             0.62f, EdoAssets.Goten.RoofIrimoya);
        // 渡廊下 3間。廊下は**入側の帯をそのまま東へ延ばす**形で取り付く
        // (入側の妻側の端は Mune が最初から開けてある。妻壁に穴を開けるのではない)。
        // 屋根は両端 0.30 だけ長く、棟の軒の出 0.90 と合わせて 1.20 重なるので、
        // 廊下の端は棟の柱通りにぴたりと突き付ける。両端の柱は棟のものと重なるので置かない
        Roka("Roka_AB", root.transform, new Vector3(wA, 0f, 4 * K), 0f, 3,
             colStart: false, colEnd: false);
        // 副棟 5間角。北へ4間ずらして雁行させる。廊下は副棟の入側の西端に取り付く
        Mune("Mune_B", root.transform, new Vector3(wA + 3 * K, 0f, 4 * K), 0f, 5, 3, 1,
             0.62f, EdoAssets.Goten.RoofIrimoya5x5);

        Selection.activeGameObject = root;
        Debug.Log(string.Format(
            "[GotenKit] 雁行テストを y=300 に建てた。渡廊下の大棟 {0:F2} < 棟の軒先 {1:F2}(床から)",
            ROKA_EAVE + ROKA_RIDGE, MUNE_EAVE));
    }
}
