// 御殿複合(表向・中奥・奥向の3核)を組む — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは
// EdoBuild の関数だけ」)。部材は EdoGotenKit(Mune / Roka)、屋根は焼いてある入母屋の定尺から引く。
//
// ⛔ このファイルに「どの区画が御殿を持つか」を書かない — それは類型表と EdoTypologyBuilder の持ち場。
//    ここに書くのは **どう組み、どこへ置き、どう据え、どう突き付けるか** だけ。
//
// ⭐ 何を直したか(EDO-0318 ⑥・2026-09-21): 2026-09-21 まで `omoya: goten` の9筆(全部 daimyo_kami)は
//    `Plan()` が **VK.BigHouse + House×2 + SmallHouse** を積み、`Spot()` が区画の内側の格子点へ
//    **ばらばらに散らして**いた。大名上屋敷の御殿は「**一つの連続御殿複合**が敷地の大半を占める
//    (散在パビリオンではない)」([福井図]・estate-types.md §上屋敷)物なので、姿が根本から違った。
//
// 【組み方の典拠】
//   ・中軸 = **表門 → 玄関 → 表向 → 中奥 → 奥向** が一直線([中屋敷図]の注記・estate-types.md)。
//   ・3核は別棟だが近接し、**渡廊下でつなぐ**。屋根の取り合いは谷も隅も作らず、各棟は独立した入母屋の
//     まま置いて **その軒下を渡廊下の低い切妻がくぐる**(2026-08-14 施主裁定・EdoGotenKit の冒頭)。
//   ・⇒ 棟どうしの壁の離れは「軒の出 0.90 × 2 = 1.80m」より広く取る。渡廊下 2間 = 3.636m で足りる。
//
// 【なぜ桁行が敷地の奥へ走るか】渡廊下は棟の **妻側(入側の帯の端)** へ突き付ける物で、そこには濡縁が
//   回っていない(`Mune` は iriX=0 のとき濡縁を桁行の両側にだけ置く)。⇒ 妻を中軸へ向ける = 桁行が
//   中軸に沿う。濡縁は左右の庭へ面し、玄関の側には入母屋の妻(破風)が立つ。
//   ⛔ 梁間を中軸へ向けると渡廊下が濡縁と高欄へめり込む。
//
// 置き方の作法は docs/oki-kata.md(触れている箇所を測る)。
//   ① 固定側 = 門構え(Stage 1 で据わっている)。この複合は門の実位置から測った中軸の上に載る。
//   ② 可動側 = 玄関から奥へ、**前の駒の実メッシュへ突き付けて**(`Abut`・屋根を外して測る)鎖でつなぐ。
//   ③ 高さは複合ぜんたいを一枚の面として **触れている箇所** で据える(`SeatOnGround`)。

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    // ── 段(核の寸法の組)──────────────────────────────────────────────
    // ⭐ **焼いてある入母屋の定尺からしか採らない。**(w=桁行・d=梁間、外形の間数)。
    //    ⛔ 無い寸法を書くと `Mune` が屋根なしで組み上がり、骨組みだけの棟が建つ。
    //    ⛔ 棟の大小に史料の根拠は無い(確度 U)— 在るのは「表向がいちばん大きい」という並びだけ
    //    ([福井図] 表=玄関+大広間+黒書院 / 中央=大台所 / 奥=居間)。だから段は
    //    **表向 ≥ 奥向 > 中奥** の順だけを守り、絶対値は敷地の余地と建坪の目標が決める。
    static readonly int[,] GOTEN_TIERS =
    {
        // 表向 w,d   中奥 w,d   奥向 w,d      建坪[間²] / 中軸の長さ[間](玄関6+渡廊下2×3を含む)
        { 18, 16,     12, 11,     16, 12 },   // 612 / 58
        { 16, 12,     11, 10,     14, 14 },   // 498 / 53
        { 14, 14,     10, 10,     12, 12 },   // 440 / 48
        { 12, 12,      9,  6,     11, 10 },   // 308 / 44
        { 11, 10,      6,  6,     10, 10 },   // 246 / 39
        { 10,  6,      6,  6,      9,  6 },   // 150 / 37
    };
    const int GOTEN_GENKAN_KEN = 6;    // 玄関棟(6×6間)。⭐ 6x6ken は焼いてある定尺
    const int GOTEN_LINK_KEN   = 2;    // 渡廊下の間数。軒の出 0.90×2 = 1.80m < 2間 3.636m
    const int GOTEN_STEP_KEN   = 3;    // 雁行の振り(奥の棟ほど横へ振る)

    /// <summary>濡縁が桁行の外へ出る見込み[m]。⚠ **置ける所を探す下見の余白**にだけ使う概算で、
    /// 取り合いと区域侵犯は**建てた実メッシュ**で測り直す(規則5)。</summary>
    const float GOTEN_NUREEN_OUT = 1.0f;

    /// <summary>[福井図] の 6,600 坪 = 21,818 m²。建蔽率の史料値が採れる唯一の上屋敷。</summary>
    const float GOTEN_FUKUI_M2 = 6600f * 3.3058f;
    /// <summary>複合の足元の地面の起伏[m]の許容。複合は一枚の面で据える(いちばん高い地面に載る)ので、
    /// **起伏はそのまま低い側の床下の開きになる**。
    /// <para>⛔ 2026-09-22 まで 2.0m だった — 「縁の下として正しい姿」と書いていたが、**検証レンダで崩れた**:
    /// 戸田の複合は床下が 2.1m 開き、建物の下を光が抜けて向こうの塀と木立が見えた(高床の楼閣の姿)。
    /// 元は奥向の下にあった**小さな塚ひとつ**(地面 中央 11.34 に対し最高 13.55)で、
    /// 一枚の面は塚に載るので 80m の複合ぜんたいが 2.1m 持ち上がっていた。</para>
    /// <para>⭐ 今の値は**規則3 の「棟ごとの系統差は ±0.25m 以内」と縁の下の高さ**から採る —
    /// 縁の下は束石と地覆が見える 0.45m ほどで、規則3 の系統差 ±0.25m を足して 0.70m。
    /// これは**置き所を絞る篩**なので、実現する開きより少し緩い 0.8m を使う
    /// (下見の起伏 = 足元の地面の最高−最低で、一枚の面で据えたあとの開きはそれより小さくなることが多い —
    /// 2026-09-22 実測で 起伏 0.74 → 開き 0.73 / 起伏 0.75 → 開き 0.69)。⚠ 確度 U(当方の見当)。</para>
    /// <para>⛔ **合否はこの篩で出さない。**据えたあとの <see cref="GOTEN_UNDERFLOOR_MAX"/> で出す。</para></summary>
    const float GOTEN_RELIEF_OK = 0.80f;

    /// <summary>据えたあとに許す**床下の開き**[m]。⭐ **`EdoTypologyBuilder.Inspect` の「浮き」の閾値と同じ数**。
    /// ⛔ ビルダーの合否を検査より緩くしない — 緩いと「ビルダーは通したのに検査が赤」が常態になり、
    /// 赤を読み流す癖が付く(規則19・memory `check-must-name-what-it-measures`)。動かすなら両方動かす。</summary>
    const float GOTEN_UNDERFLOOR_MAX = 0.70f;

    /// <summary>下見で足元の地面を引く格子[m]。⛔ 3m にしない — 2026-09-22 の戸田で
    /// **2.2m の塚が格子の目を抜けた**(地形は 2m/px なので 3m 格子は地形より粗い)。</summary>
    const float GOTEN_PROBE_STEP = 1.2f;

    /// <summary>下見の矩形を外へ広げる量[m]。⭐ **縁と軒の出**のぶん、実メッシュは下見の矩形より広い —
    /// 矩形の内だけ引くと、縁の真下の塚を見落とす(2026-09-22 戸田の元の一つ)。</summary>
    const float GOTEN_PROBE_GROW = 1.2f;

    /// <summary>上屋敷の建蔽率(御殿+長屋)の史料値 5〜6割 [福井図] の中。</summary>
    const float GOTEN_KENPEI = 0.55f;

    /// <summary>**御殿の建坪の目安**[m²]。
    /// <para>= 建蔽率 <see cref="GOTEN_KENPEI"/> × 敷地 − **実測した外周(囲い・門)の建坪**。
    /// ⚠ 建蔽率の史料値は [福井図] 6,600 坪の一点しかないので、**6,600 坪で頭打ち**にする —
    /// [中屋敷図] の 1.8 万坪級は「中央の御殿クラスタ+外周長屋+**広い余白**」で上屋敷より明確に疎、と
    /// estate-types.md が書いており、割合をそのまま大きい敷地へ伸ばすのは n=1 の類型への昇格になる。</para>
    /// <para>⛔ ここで出るのは**目標**であって、建つ大きさではない — 実際は
    /// <see cref="GOTEN_TIERS"/>(焼いてある屋根の定尺)と区画の余地のうち小さい方が決める。</para></summary>
    public static float GotenTargetArea(Vector2[] poly, Transform root)
    {
        float a = Mathf.Abs(EdoGeom.SignedArea(poly));
        float built = 0f;
        if (root != null)
            foreach (Transform grp in root)
                if (grp.name == "Kakoi" || grp.name == "Mon") built += FootprintXZ(grp);
        return Mathf.Max(0f, GOTEN_KENPEI * Mathf.Min(a, GOTEN_FUKUI_M2) - built);
    }

    /// <summary>群の直下の駒の**壁体**の footprint[m²]の合計(駒ごとの局所軸での外形。⛔ 世界軸の
    /// 外接箱で測らない — 斜めの辺に沿う塀で 2 倍に出る)。⚠ 駒どうしの重なりは引かない概算。</summary>
    public static float FootprintXZ(Transform group, int maxSamples = 200)
    {
        float s = 0f;
        foreach (Transform t in group)
        {
            var pts = Body(t, maxSamples);
            if (pts.Count == 0) continue;
            Vector3 ax = t.rotation * Vector3.right, az = t.rotation * Vector3.forward;
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var p in pts)
            {
                float qx = Vector3.Dot(p, ax), qz = Vector3.Dot(p, az);
                mnx = Mathf.Min(mnx, qx); mxx = Mathf.Max(mxx, qx);
                mnz = Mathf.Min(mnz, qz); mxz = Mathf.Max(mxz, qz);
            }
            s += (mxx - mnx) * (mxz - mnz);
        }
        return s;
    }

    /// <summary>**御殿複合を建てる。**中軸(門から敷地の奥へ)に 玄関 → 表向 → 中奥 → 奥向 を並べ、
    /// 渡廊下でつなぐ。返るのは複合ぜんたいの根(⭐ 類型の検査は**群の直下の駒ひとつ**を数えるので、
    /// 複合は必ず一つの根にまとめる — 棟ごとにばらすと「浮き 1000 件」の嘘の赤が出る)。
    ///
    /// <para><paramref name="gateC"/> = 表門の中心(世界 XZ)、<paramref name="inward"/> = 門から敷地の
    /// 奥へ向かう単位ベクトル。<paramref name="setback"/> = 囲いの内側から棟までの引き[m]。
    /// <paramref name="targetArea"/> = 建坪の目標[m²](<see cref="GotenTargetArea"/>。0 以下なら効かない)。</para>
    ///
    /// <para>置けなければ null を返し、<paramref name="note"/> に理由を書く(⛔ 黙って落とさない・規則19)。</para></summary>
    public static GameObject GotenComplex(Transform parent, string name, Vector2[] poly,
                                          Vector2 gateC, Vector2 inward, float pad,
                                          float targetArea, float setback, int verts,
                                          out string note)
    {
        note = "";
        var vDir = inward.normalized;
        var uDir = new Vector2(vDir.y, -vDir.x);       // 複合の局所 +X(Unity の yaw と同じ取り方)

        // 区画を複合の局所座標(u=横・v=奥)で見たときの広がり
        float uMin = float.MaxValue, uMax = float.MinValue, vMax = float.MinValue;
        foreach (var p in poly)
        {
            var q = p - gateC;
            float u = Vector2.Dot(q, uDir), v = Vector2.Dot(q, vDir);
            uMin = Mathf.Min(uMin, u); uMax = Mathf.Max(uMax, u); vMax = Mathf.Max(vMax, v);
        }

        // ── 段と据える所を選ぶ(下見。⛔ ここで建てない — 建てて測るのは選んだ一つだけ)────
        int tier = -1, side = 0; float bestU = 0f, bestV = 0f, bestScore = float.MaxValue;
        float bestRelief = float.NaN;
        // 起伏が大きくて採れる置き所が無かったときの次善(起伏がいちばん小さい置き所。同じなら小さい段)
        int fbTier = -1, fbSide = 0; float fbU = 0f, fbV = 0f, fbRelief = float.MaxValue;
        var cen = Centroid(poly);
        float cenU = Vector2.Dot(cen - gateC, uDir), cenV = Vector2.Dot(cen - gateC, vDir);
        var probe = Probe();
        for (int t = 0; t < GOTEN_TIERS.GetLength(0) && tier < 0; t++)
        {
            if (targetArea > 0f && TierArea(t) > targetArea) continue;   // 目標より大きい段は採らない
            for (int sg = 1; sg >= -1; sg -= 2)
                for (float v0 = setback; v0 <= vMax - setback; v0 += 3.0f)
                    for (float u0 = uMin; u0 <= uMax; u0 += 3.0f)
                    {
                        var rects = TierRects(t, sg, u0, v0);
                        if (!RectsFit(rects, poly, gateC, uDir, vDir, setback)) continue;
                        // ⭐ 足元の起伏が小さい所へ据える。複合は一枚の面で据える(いちばん高い地面に載る)ので、
                        //    起伏がそのまま**低い側の縁の下の高さ**になる。⛔ 中央への寄せだけで選ばない —
                        //    2026-09-22 の三べ坂 abe は起伏 17m の斜面の真ん中を選び、10m の高床に据わった。
                        float relief = ReliefUnder(rects, gateC, uDir, vDir, probe);
                        if (relief < fbRelief - 1e-3f) { fbRelief = relief; fbTier = t; fbSide = sg; fbU = u0; fbV = v0; }
                        if (relief > GOTEN_RELIEF_OK) continue;
                        // ⭐ 敷地の真ん中へ寄せる([中屋敷図]「御殿群は敷地中央に固まり、周囲は空地」)
                        float cu = 0f, cv = 0f;
                        foreach (var r in rects) { cu += (r.x + r.y) * 0.5f; cv += (r.z + r.w) * 0.5f; }
                        cu /= rects.Count; cv /= rects.Count;
                        // ⭐ 起伏の小さい所を先に採り、中央への寄せは同じ起伏のときの裁き。
                        //    ⛔ 中央への寄せだけで選ばない(2026-09-22 戸田: 許容の内でも塚寄りを選んでいた)
                        float sc = Mathf.Abs(cu - cenU) + Mathf.Abs(cv - cenV) + relief * 8f;
                        if (sc < bestScore) { bestScore = sc; tier = t; side = sg; bestU = u0; bestV = v0; bestRelief = relief; }
                    }
            if (tier >= 0) break;
        }
        string steep = "";
        if (tier < 0 && fbTier >= 0)
        {
            // どの段も起伏の許容を超える — 起伏がいちばん小さい所を採り、⚠ を刷る(黙って高床にしない・規則19)
            tier = fbTier; side = fbSide; bestU = fbU; bestV = fbV; bestRelief = fbRelief;
            steep = string.Format("⚠ 足元の起伏 {0:F1}m が許容 {1:F1}m を超える(どの段でも) — 低い側の縁の下が最大 {0:F1}m 開く。" +
                                  "斜面は造成か段の分けが要る(規則3・手組みの領分)", fbRelief, GOTEN_RELIEF_OK);
        }
        if (tier < 0)
        {
            note = string.Format("⛔ 御殿複合: いちばん小さい段({0}間×{1}間ほか・中軸 {2:F0}m)でも" +
                                 "囲いの内側({3:F0}m 引き)に収まらない",
                                 GOTEN_TIERS[GOTEN_TIERS.GetLength(0) - 1, 0],
                                 GOTEN_TIERS[GOTEN_TIERS.GetLength(0) - 1, 1],
                                 TierRunKen(GOTEN_TIERS.GetLength(0) - 1) * EdoGotenKit.K, setback);
            return null;
        }

        // ── 建てる ───────────────────────────────────────────────────
        float psi = Mathf.Atan2(vDir.x, vDir.y) * Mathf.Rad2Deg;   // 局所 +Z を inward へ向ける
        var root = new GameObject(name);
        root.transform.SetParent(parent, true);
        root.transform.position = new Vector3(gateC.x + uDir.x * bestU + vDir.x * bestV, pad,
                                              gateC.y + uDir.y * bestU + vDir.y * bestV);
        root.transform.rotation = Quaternion.Euler(0f, psi, 0f);
        Undo.RegisterCreatedObjectUndo(root, "goten " + name);

        // 核の並び(奥へ)。u は「その核の +u 側の端」— 雁行の振りは側(side)へ寄せる
        var cores = new List<GameObject>();
        var links = new List<GameObject>();
        float vCur = 0f;
        var made = new List<KeyValuePair<string, Vector2Int>>();   // 名 → (桁行,梁間)[間]

        GameObject prev = null;
        for (int k = 0; k < 4; k++)                       // 0=玄関 1=表向 2=中奥 3=奥向
        {
            int w = k == 0 ? GOTEN_GENKAN_KEN : GOTEN_TIERS[tier, (k - 1) * 2];
            int d = k == 0 ? GOTEN_GENKAN_KEN : GOTEN_TIERS[tier, (k - 1) * 2 + 1];
            float uc = side * Mathf.Max(0, k - 1) * GOTEN_STEP_KEN * EdoGotenKit.K;   // 雁行(玄関と表向は中軸の上)
            // 渡廊下 — 前の核の妻へ。⭐ 両核の横の重なりの中で通す
            if (k > 0)
            {
                int pd = k == 1 ? GOTEN_GENKAN_KEN : GOTEN_TIERS[tier, (k - 2) * 2 + 1];
                float puc = side * Mathf.Max(0, k - 2) * GOTEN_STEP_KEN * EdoGotenKit.K;
                float lo = Mathf.Max(uc - d * EdoGotenKit.K, puc - pd * EdoGotenKit.K);
                float hi = Mathf.Min(uc, puc);
                float lu = (lo + hi) * 0.5f + EdoGotenKit.K * 0.5f;   // 廊下は幅1間・局所 +X の側が原点
                var rk = EdoGotenKit.Roka(name + "_Roka" + k, root.transform,
                                          new Vector3(lu, 0f, vCur), 270f, GOTEN_LINK_KEN,
                                          colStart: false, colEnd: false);
                if (rk != null)
                {
                    NameRoofs(rk);
                    // ⭐ 前の核の**実メッシュ**へ突き付ける(⛔ 屋根は外して測る — 渡廊下は軒の下を
                    //    くぐるのが正しい姿で、屋根ごと測ると軒先で 1.2m 手前に止まる)
                    if (prev != null) AbutQuiet(rk, prev, -ToV3(vDir), verts);
                    links.Add(rk);
                    prev = rk;
                }
                vCur = LocalEnd(root.transform, prev, vDir);
            }
            var mu = EdoGotenKit.Mune(name + (k == 0 ? "_Genkan" : k == 1 ? "_Omote" : k == 2 ? "_Nakaoku" : "_Oku"),
                                      root.transform, new Vector3(uc, 0f, vCur), 270f,
                                      w, d - 2, 1, 0.62f, EdoAssets.Goten.RoofIrimoya_(w, d));
            if (mu == null) { note = "⛔ 御殿複合: 棟が組めなかった(部材を検める)"; return root; }
            NameRoofs(mu);
            if (prev != null) AbutQuiet(mu, prev, -ToV3(vDir), verts);
            cores.Add(mu); made.Add(new KeyValuePair<string, Vector2Int>(mu.name, new Vector2Int(w, d)));
            prev = mu;
            vCur = LocalEnd(root.transform, prev, vDir);
        }

        // ── 据える(複合ぜんたいを一枚の面として・触れている箇所で)──────────────────
        // ⭐ 核ごとに据えない: 御殿は一続きの床で、棟ごとに高さが違うと渡廊下が折れる。
        //    複合の中でいちばん高い地面に載る = **どこも埋まらない**(規則4 埋没は許容0)。
        //    ⚠ 足元の起伏ぶん低い側の縁の下が開く — それは縁の下として正しい姿で、呼び手が刷る。
        float seat = float.NaN;
        try { seat = SeatOnGround(root, 0f, verts); }
        catch (Exception) { note = "⛔ 御殿複合: 接地箇所が測れない"; }

        // ── 測る(建てた実メッシュで・0 件でも刷る・規則19)───────────────────────
        float outWall = 0f, outEave = 0f;
        foreach (var g in cores) { outWall = Mathf.Max(outWall, OutsideOf(poly, g.transform, false)); }
        foreach (var g in cores) { outEave = Mathf.Max(outEave, OutsideOf(poly, g.transform, true)); }
        foreach (var g in links) { outWall = Mathf.Max(outWall, OutsideOf(poly, g.transform, false)); }
        float worstJoint = float.NaN;
        for (int i = 0; i < links.Count; i++)
        {
            Vector3 at; int nc;
            // ⭐ dir は「廊下から相手へ向かう向き」。手前の核(cores[i])は −v の側、奥の核(cores[i+1])は +v の側。
            //    ⛔ 逆に書くと相手の背面まで測って −(核の奥行) が出る(2026-09-22 実測で −26.8m の嘘)。
            float g1 = Contact(links[i], cores[i], -ToV3(vDir), out at, out nc, 0.01f, 0.25f, verts, false);
            float g2 = Contact(links[i], cores[i + 1], ToV3(vDir), out at, out nc, 0.01f, 0.25f, verts, false);
            foreach (var g in new[] { g1, g2 })
                if (!float.IsNaN(g) && (float.IsNaN(worstJoint) || g < worstJoint)) worstJoint = g;
        }
        float m2 = TierArea(tier) + GOTEN_GENKAN_KEN * GOTEN_GENKAN_KEN * EdoGotenKit.K * EdoGotenKit.K;
        var kinds = new List<string>();
        foreach (var kv in made) kinds.Add(string.Format("{0}={1}x{2}間", Tail(kv.Key), kv.Value.x, kv.Value.y));

        note = string.Format(
            "  御殿複合: {0}核+渡廊下{1}({2}) 建坪 {3:F0}m²={4:F0}坪 / 雁行 {5}間振り{6} / " +
            "据え {7} / 壁体が区画の外 {8:F2}m・軒 {9:F2}m / 廊下と棟の当たり {10}",
            cores.Count, links.Count, string.Join(" ", kinds.ToArray()), m2, m2 / 3.3058f,
            GOTEN_STEP_KEN, side > 0 ? "(左)" : "(右)",
            float.IsNaN(seat) ? "⛔測れず" : string.Format("{0:F2}m", seat),
            outWall, outEave,
            float.IsNaN(worstJoint) ? "⛔測れず"
                : string.Format("{0:F2}m{1}", worstJoint, worstJoint < -0.01f ? "(⛔ めり込み)" : ""));
        // ⭐ 床下の開きは**据えたあとに棟ごとで実測**する(下見の起伏は当てにしない・規則19)
        string ufName;
        float uf = UnderfloorGap(cores, links, verts, out ufName);
        note += string.Format("\n    足元の起伏(下見) {0:F2}m(許容 {1:F1}m) / **床下の開き(実測・棟ごと) {2:F2}m**{3}{4}",
                              bestRelief, GOTEN_RELIEF_OK, uf,
                              uf > GOTEN_UNDERFLOOR_MAX + 0.01f
                                ? string.Format(" ⛔ 許容 {0:F2}m 超({1})— 床下が抜けて見える。造成か段の分けが要る(規則3)",
                                                GOTEN_UNDERFLOOR_MAX, ufName)
                                : "",
                              steep.Length > 0 ? "\n    " + steep : "");
        return root;
    }

    // ───────────────────────── 下働き ─────────────────────────

    static Vector3 ToV3(Vector2 v) { return new Vector3(v.x, 0f, v.y); }
    static string Tail(string n) { int i = n.LastIndexOf('_'); return i < 0 ? n : n.Substring(i + 1); }

    /// <summary>矩形の並びの足元の地面の起伏 = 最高 − 最低[m]。
    /// <para>矩形は <see cref="GOTEN_PROBE_GROW"/> だけ外へ広げ(縁と軒の下も足元)、
    /// <see cref="GOTEN_PROBE_STEP"/> の格子で引く。⛔ **格子を地形より粗くしない** — 3m 格子は
    /// 2m/px の地形より粗く、2026-09-22 の戸田では 2.2m の塚が目を抜けて許容 2.0m を通った。</para></summary>
    static float ReliefUnder(List<Vector4> rects, Vector2 org, Vector2 uDir, Vector2 vDir, GroundProbe probe)
    {
        float lo = float.MaxValue, hi = float.MinValue;
        foreach (var r0 in rects)
        {
            var r = new Vector4(r0.x - GOTEN_PROBE_GROW, r0.y + GOTEN_PROBE_GROW,
                                r0.z - GOTEN_PROBE_GROW, r0.w + GOTEN_PROBE_GROW);
            int nu = Mathf.Max(2, Mathf.CeilToInt((r.y - r.x) / GOTEN_PROBE_STEP));
            int nv = Mathf.Max(2, Mathf.CeilToInt((r.w - r.z) / GOTEN_PROBE_STEP));
            for (int i = 0; i <= nu; i++)
                for (int j = 0; j <= nv; j++)
                {
                    float u = Mathf.Lerp(r.x, r.y, i / (float)nu), v = Mathf.Lerp(r.z, r.w, j / (float)nv);
                    var w = org + uDir * u + vDir * v;
                    float y = probe.At(w.x, w.y);
                    if (y < lo) lo = y; if (y > hi) hi = y;
                }
        }
        return hi - lo;
    }

    /// <summary>据えたあとの**床下の開き**[m] — 棟ごとに実メッシュで接地を測り、最大を返す。
    /// <para>⛔ 複合ぜんたいで <see cref="Contact(GameObject,out Vector3,out int,float,int)"/> を呼んで
    /// 検めたことにしない。あれは**子の最小**を返すので、塚に載った 1 棟が 0.00m を返すと
    /// 他の 6 棟が 2m 浮いていても「⭕ 0.00m」になる(2026-09-22 戸田・全ての数値の関門が通っていた)。</para></summary>
    static float UnderfloorGap(List<GameObject> cores, List<GameObject> links, int verts, out string worstName)
    {
        float worst = 0f; worstName = "";
        var all = new List<GameObject>(cores); all.AddRange(links);
        foreach (var g in all)
        {
            Vector3 at; int nc;
            float d = Contact(g, out at, out nc, 0.01f, verts);
            if (float.IsNaN(d)) continue;
            if (d > worst) { worst = d; worstName = g.name; }
        }
        return worst;
    }

    /// <summary>段の建坪[m²](玄関を含まない3核)。</summary>
    static float TierArea(int t)
    {
        float k2 = EdoGotenKit.K * EdoGotenKit.K;
        return (GOTEN_TIERS[t, 0] * GOTEN_TIERS[t, 1] + GOTEN_TIERS[t, 2] * GOTEN_TIERS[t, 3]
              + GOTEN_TIERS[t, 4] * GOTEN_TIERS[t, 5]) * k2;
    }

    /// <summary>段の中軸の長さ[間](玄関+渡廊下3本を含む)。</summary>
    static int TierRunKen(int t)
    {
        return GOTEN_GENKAN_KEN + 3 * GOTEN_LINK_KEN
             + GOTEN_TIERS[t, 0] + GOTEN_TIERS[t, 2] + GOTEN_TIERS[t, 4];
    }

    /// <summary>段を局所座標の矩形(x=u0, y=u1, z=v0, w=v1)の並びにする。下見用の概算で、
    /// 濡縁の見込み <see cref="GOTEN_NUREEN_OUT"/> を横へ足す。⛔ 軒は足さない(区域侵犯は壁体で数える・裁定A)。</summary>
    static List<Vector4> TierRects(int t, int side, float uOff, float v0)
    {
        var L = new List<Vector4>();
        float v = v0;
        for (int k = 0; k < 4; k++)
        {
            int w = k == 0 ? GOTEN_GENKAN_KEN : GOTEN_TIERS[t, (k - 1) * 2];
            int d = k == 0 ? GOTEN_GENKAN_KEN : GOTEN_TIERS[t, (k - 1) * 2 + 1];
            float uc = uOff + side * Mathf.Max(0, k - 1) * GOTEN_STEP_KEN * EdoGotenKit.K;
            if (k > 0) v += GOTEN_LINK_KEN * EdoGotenKit.K;
            L.Add(new Vector4(uc - d * EdoGotenKit.K - GOTEN_NUREEN_OUT, uc + GOTEN_NUREEN_OUT,
                              v, v + w * EdoGotenKit.K));
            v += w * EdoGotenKit.K;
        }
        return L;
    }

    /// <summary>矩形の並びが、区画の内側 <paramref name="setback"/> に収まるか。
    /// ⛔ 四隅だけ見ない — 凹んだ区画では辺の途中で外へ出る。四隅で粗く落としてから 2m 格子で検める。</summary>
    static bool RectsFit(List<Vector4> rects, Vector2[] poly, Vector2 org, Vector2 uDir, Vector2 vDir, float setback)
    {
        foreach (var r in rects)                       // ① 四隅(ほとんどの位置はここで落ちる)
            for (int i = 0; i < 4; i++)
                if (!InsideBy(poly, org + uDir * ((i & 1) == 0 ? r.x : r.y)
                                        + vDir * ((i & 2) == 0 ? r.z : r.w), setback)) return false;
        foreach (var r in rects)                       // ② 2m 格子
        {
            int nu = Mathf.Max(2, Mathf.CeilToInt((r.y - r.x) / 2.0f) + 1);
            int nv = Mathf.Max(2, Mathf.CeilToInt((r.w - r.z) / 2.0f) + 1);
            for (int i = 0; i < nu; i++)
                for (int j = 0; j < nv; j++)
                {
                    float u = Mathf.Lerp(r.x, r.y, i / (float)(nu - 1));
                    float v = Mathf.Lerp(r.z, r.w, j / (float)(nv - 1));
                    if (!InsideBy(poly, org + uDir * u + vDir * v, setback)) return false;
                }
        }
        return true;
    }

    /// <summary>点が区画の内側で、縁から <paramref name="setback"/> 以上あるか。</summary>
    static bool InsideBy(Vector2[] poly, Vector2 p, float setback)
    {
        return EdoGeom.PIP(poly, p) && EdoGeom.DistToPolyEdge(poly, p) >= setback;
    }

    static Vector2 Centroid(Vector2[] poly)
    {
        var c = Vector2.zero;
        foreach (var p in poly) c += p;
        return c / poly.Length;
    }

    /// <summary>駒の壁体(または軒込み)が区画の外へ出た量[m]。0 なら収まっている。</summary>
    static float OutsideOf(Vector2[] poly, Transform t, bool withRoof)
    {
        float over = 0f;
        foreach (var w in Body(t, 600, withRoof))
        {
            var q = new Vector2(w.x, w.z);
            if (!EdoGeom.PIP(poly, q)) over = Mathf.Max(over, EdoGeom.DistToPolyEdge(poly, q));
        }
        return over;
    }

    /// <summary>相手の駒へ突き付ける(屋根を外して測る)。向き合っていなければ動かさない。</summary>
    /// <summary>屋根の駒の名を、<see cref="IsRoofName"/> の篩に掛かる名にする。
    /// <para>⛔ 2026-09-22 に踏んだ(EDO-0318 ⑥): 御殿キットの屋根は `Goten_Roof_Irimoya_…` /
    /// `Goten_Roof_Kirizuma_…` で、`Body()` の屋根の篩(yane/noki/taruki/mune/keta のローマ字)に
    /// **掛からない**。「屋根を外して測る」つもりが屋根込みで測り、廊下の屋根の棟が相手の軒と同じ高さの筋に
    /// 入ると −1.1m のめり込みが出た(据えで全体が動くと筋の割り付けが変わって現れる)。
    /// ⛔ 篩(`IsRoofName`)を広げない — 他邸の壁体の実測値が黙って動く。この複合の駒の中だけで名を付ける。</para></summary>
    static void NameRoofs(GameObject piece)
    {
        foreach (var mf in piece.GetComponentsInChildren<MeshFilter>(true))
        {
            string n = mf.gameObject.name;
            if (n.ToLower().Contains("roof") && !IsRoofName(n)) mf.gameObject.name = n + "_yane";
        }
    }

    static void AbutQuiet(GameObject mover, GameObject other, Vector3 dir, int verts)
    {
        Vector3 at; int nc;
        Abut(mover, other, dir, 0f, out at, out nc, 0.25f, verts, false);
    }

    /// <summary>駒の壁体の、複合の奥向き(<paramref name="vDir"/>)での端を、
    /// **根の局所座標**で返す(次の駒を置く所)。</summary>
    static float LocalEnd(Transform root, GameObject go, Vector2 vDir)
    {
        float mx = float.MinValue;
        var ax = ToV3(vDir);
        foreach (var w in Body(go.transform, 600))
            mx = Mathf.Max(mx, Vector3.Dot(w - root.position, ax));
        return mx;
    }
}
