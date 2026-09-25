using System.Collections.Generic;
using UnityEngine;

// 石段の組 — 段石と袖(袖石垣)を一組の材で据える(EDO-0415・2026-09-23 施主指摘)。
//   「石段の脇の石垣が石段と物が違いすぎる(城の石垣)」「石段が黒ずんでいる」「色合いが合わない」。
//   ⇒ 石段の脇は**石段と同じ材・同じ切石の作り**の袖で、天端は石段の勾配に平行な一直線。
//   ⛔ 城の石垣 `EdoAssets.JC.CastleWall` を石段の袖に使わない(天端が駒ごとに段々になり、野面の城壁に見える)。
//      CastleWall は郭・外周・基壇の高い石垣(天端が水平な run)だけの部材。
//   正典: docs/typology-builder.md §4.7「石段の組」。
public static partial class EdoBuild
{
    /// <summary>袖の天端の線が段鼻の線から上がる高さ[m]。⚠ **部材の設計値の写し**で、正典は
    /// `EdoAssets.Own.IshidanSode` の註(部材方 2026-09-23【U】)。部材を焼き直して変えたらここも合わせる。
    /// ⛔ 位置合わせの基準点ではない — 実メッシュで測った段鼻と袖の天端の差をこの値にする。</summary>
    public const float ISHIDAN_SODE_KASA = 0.30f;

    /// <summary>**段石1段の脇に袖の駒を1つ据える**(石段の組・EDO-0415)。
    /// <paramref name="dan"/> = 据えた段石(ローカル +Z = 坂下・+X = 幅)、<paramref name="side"/> = +1 なら段石の +X 側 / −1 なら −X 側。
    /// 袖の駒 <paramref name="sodePath"/>(`EdoAssets.Own.IshidanSode(蹴上, 踏面, i)` — 段石と同じ i)を段石と同じ向きに仮置きし、
    /// **両方の実メッシュを測って**三方向を合わせる:
    /// ① 横 — 袖の内側の側面を段石の小口(幅方向の端の面)へ突き付ける(隙 0)。
    /// ② 走り — 袖の坂下の端を段石の段鼻の面にそろえる(段の境で隣の駒と面一になる)。
    /// ③ 高さ — 段鼻の真横での袖の天端を、段石の踏面 + <see cref="ISHIDAN_SODE_KASA"/> にする。
    /// ⛔ ピボット・bounds の中心で合わせない(規則21)。仮置きの位置は測る前の当て推量でしかない。
    /// 返り値 = 据えた駒。<paramref name="warn"/> に据えた後の検め(小口との隙が 5mm を超えたら)を返す。
    /// ⭐ 硬い条件: 小口との隙 0(許容0・超えたら ⚠ を刷って建てたまま検査で赤)。</summary>
    public static GameObject PlaceIshidanSode(GameObject dan, string sodePath, int side, Transform parent, string name,
                                              out string warn)
    {
        SodeRise r;
        return PlaceIshidanSode(dan, sodePath, side, parent, name, false, out warn, out r);
    }

    /// <summary><see cref="PlaceIshidanSode(GameObject,string,int,Transform,string,out string,out SodeRise)"/> の
    /// 天端の上げの勘定。</summary>
    public struct SodeRise
    {
        public float lift;       // 天端を段鼻の線 + 笠から上げた量[m](0 = 上げていない)
        public float limit;      // 上げられる上限[m](袖の内の面が段石の小口を底まで覆う範囲・実メッシュで測る)
        public float proud;      // 上げた後、袖の背の線で天端が地表より出る量の最大[m](柔らかい・報告のみ)
        public bool refused;     // 上限を超えるので据えなかった(硬い: 埋まった袖を積まない・小口を開けない)
        public float depth;      // 据えた駒の丈[m](天端の線から下端まで。PlaceIshidanSodeByDepth が選んだ物)
        public float neiriShort; // 底が見え面の足元の設計面 − 根入れ より上に出る量の最大[m](> 0 = 根入れ不足・硬い)
        public float dig;        // lineTop: 天端を段の線に置いたまま、背の地盤が天端より高い量の最大[m](背を造成で下げる量・CutEdgeSkin digParts)
    }

    /// <summary>**丈を選んで袖を据える**(EDO-0430 2026-09-24)。<paramref name="pathOf"/>(丈 → 袖のパス。
    /// 例 `d => EdoAssets.Own.IshidanSode(蹴上, 踏面, i, d)`)と焼いてある丈 <paramref name="depths"/>(浅い順。
    /// `EdoAssets.Own.IshidanSodeDepths`)を受け、**浅い丈から順に**据えて、天端を地盤まで上げる量が上げの上限
    /// (実メッシュで測る ── 袖の下端が段石の底より下)に収まる**最小の丈**を採る。
    /// ⭐ 硬い条件: どの丈でも上限を超える(または足りる丈の駒を焼いていない)なら**建てずに退けて** ⛔ を刷る
    /// (<see cref="SodeRise.refused"/>)。⛔ 足りない丈の袖を上げて下を開けない・埋まった袖を積まない。
    /// 選んだ丈は <see cref="SodeRise.depth"/> に返す ── 留めに切るときは同じ丈の駒を引く
    /// (<see cref="MiterIshidanSode(IList{GameObject},IList{GameObject},int,float,float,float,List{string},IList{float})"/>)。
    /// 当たる先: `copingRise:"groundHi"` の袖を持つ全ての石段(山王の男坂・女坂・郭の階・中門の内の階)。
    /// 深い丈が要るのは今は女坂の切通しの坂下・坂上だけ(3.20 を焼いたのも女坂 (0.300, 1.199) だけ)。</summary>
    public static GameObject PlaceIshidanSodeByDepth(GameObject dan, System.Func<float, string> pathOf, IList<float> depths,
                                                     int side, Transform parent, string name, bool groundHi,
                                                     out string warn, out SodeRise rise, bool lineTop = false,
                                                     System.Func<float, float, float> footAt = null, float neiri = 0.05f)
    {
        warn = null; rise = new SodeRise();
        string lastWarn = null; SodeRise last = new SodeRise(); float lastD = float.NaN; var unbaked = new List<string>();
        GameObject shortGo = null; SodeRise shortR = new SodeRise(); string shortW = null;
        for (int k = 0; k < depths.Count; k++)
        {
            float d = depths[k]; string path = pathOf(d);
            if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { unbaked.Add(d.ToString("F2")); continue; }
            string w; SodeRise r;
            var go = PlaceIshidanSode(dan, path, side, parent, name, groundHi, out w, out r, lineTop);
            r.depth = d;
            // ⭐ 硬い条件(許容0 の浮き・joints[69] 2026-09-25): 袖の底は見え面(段石から遠い側)の足元の設計面より neiri 下。
            //   足りなければ深い丈を試す(据える側で駒を下へ延ばす)。⛔ 皮を上げて塞がない。
            if (!r.refused && go != null && footAt != null)
            {
                r.neiriShort = SodeFootShort(go, dan, side, footAt, neiri);
                if (r.neiriShort > 1e-3f)
                {
                    if (shortGo != null) Object.DestroyImmediate(shortGo);
                    shortGo = go; shortR = r; shortW = w; continue;
                }
            }
            if (!r.refused) { if (shortGo != null) Object.DestroyImmediate(shortGo); warn = w; rise = r; return go; }
            lastWarn = w; last = r; lastD = d;
            if (!groundHi) break;                 // 上げない袖は丈で結果が変わらない
        }
        if (shortGo != null)
        {   // どの丈でも根入れが足りない ⇒ 最も深い丈で据えたまま ⛔ を刷る(退けると石段の脇が開く ── 部材の丈が要る)
            rise = shortR; warn = (shortW == null ? "" : shortW + " / ") + name + ": ⛔ 袖の底が見え面の足元の設計面 − " + neiri.ToString("F2") +
                   " より " + shortR.neiriShort.ToString("F2") + "m 上(焼いてある最も深い丈 " + shortR.depth.ToString("F2") + "m でも根入れが足りない ── 丈の深い袖の駒が要る)";
            return shortGo;
        }
        rise = last; rise.refused = true; rise.depth = lastD;
        warn = (lastWarn ?? (name + ": ⛔ 袖の駒を焼いていない")) +
               (unbaked.Count > 0 ? "(焼いていない丈: " + string.Join(", ", unbaked) + ")" : "") +
               (float.IsNaN(lastD) ? "" : "(試した最も深い丈 " + lastD.ToString("F2") + "m でも足りない)");
        return null;
    }

    /// <summary>**段石1段の脇に袖の駒を1つ据える**。<paramref name="groundHi"/> = true なら指図の
    /// `copingRise:"groundHi"`(天端 = max(段鼻の線 + 笠, 高い側の地盤) ── 裁定 EDO-0182 (a))を読む:
    /// ①〜③ で据えた後、**袖の背の面の線**(段石から遠い側の面の 0.05m 外)で描かれた地表を走りに沿って測り、
    /// 天端の線より地表が高い分の最大だけ駒を鉛直に上げる(天端が土の始まりに揃う ⇒ 見える天端の帯は埋まらない)。
    /// ⭐ 上げの上限は**実メッシュで測る**: 上げた後も袖の下端が段石の底より下にある(= 袖の内の面が段石の小口を底まで覆う)。
    /// 超えるなら据えない(<see cref="SodeRise.refused"/>・⛔ 硬い条件 ── 埋まった袖も、小口の下が開いた袖も許容0)。
    /// ⚠ 走りの中で地表の勾配が段の勾配と違うと、上げた駒の天端は背の線で地表より出る(<see cref="SodeRise.proud"/>・柔らかい)。
    /// 当たる先: 石段の袖(`terraceWalls` の coping:"stair")を持つ全ての石段 ── 山王の男坂・女坂・参道の階・郭の階・中門の内の階。</summary>
    /// <para>⭐ <paramref name="lineTop"/> = true(`copingRise:"line"`・施主 2026-09-25「袖石が上下にガタガタしすぎ」):
    /// 天端は**上げない** ── 谷側の袖と同じく段鼻の線 + 笠の滑らかな線に置き、背の地盤が天端より高い分は
    /// <see cref="SodeRise.dig"/> に返して**背を造成で下げる**(<see cref="CutEdgeSkin"/> の digParts ── 天端 − 0.05 から法で元の地形へ)。</para>
    public static GameObject PlaceIshidanSode(GameObject dan, string sodePath, int side, Transform parent, string name,
                                              bool groundHi, out string warn, out SodeRise rise, bool lineTop = false)
    {
        rise = new SodeRise();
        var go = PlaceIshidanSodeFlat(dan, sodePath, side, parent, name, out warn);
        if (go == null || !groundHi) return go;
        var t = dan.transform;
        Vector3 right = t.right * Mathf.Sign(side == 0 ? 1 : side), fwd = t.forward;
        var sp = Body(go.transform, 4000, true); var dp = Body(t, 4000, true);
        if (sp.Count == 0 || dp.Count == 0) return go;
        float outer = float.MinValue, sBot = float.MaxValue, dBot = float.MaxValue, fMin = float.MaxValue, fMax = float.MinValue;
        foreach (var p in sp)
        {
            outer = Mathf.Max(outer, Vector3.Dot(p, right)); sBot = Mathf.Min(sBot, p.y);
            float f = Vector3.Dot(p, fwd); fMin = Mathf.Min(fMin, f); fMax = Mathf.Max(fMax, f);
        }
        foreach (var p in dp) dBot = Mathf.Min(dBot, p.y);
        rise.limit = Mathf.Max(0f, dBot - sBot);
        // 背の線を走りに沿って 0.05m 刻みで: 天端(その走りの位置の実メッシュの最高点)と地表
        const float BIN = 0.05f;
        int nb = Mathf.Max(1, Mathf.CeilToInt((fMax - fMin) / BIN));
        var top = new float[nb]; for (int i = 0; i < nb; i++) top[i] = float.NaN;
        foreach (var p in sp)
        {
            int k = Mathf.Clamp(Mathf.FloorToInt((Vector3.Dot(p, fwd) - fMin) / BIN), 0, nb - 1);
            if (float.IsNaN(top[k]) || p.y > top[k]) top[k] = p.y;
        }
        Vector3 o = go.transform.position; float oR = Vector3.Dot(o, right), oF = Vector3.Dot(o, fwd);
        var need = new float[nb]; float lift = 0f;
        for (int k = 0; k < nb; k++)
        {
            need[k] = float.NaN;
            if (float.IsNaN(top[k])) continue;
            float fk = fMin + (k + 0.5f) * BIN;
            Vector3 q = o + right * (outer + 0.05f - oR) + fwd * (fk - oF);
            need[k] = Ground(q.x, q.z) - top[k];
            if (need[k] > lift) lift = need[k];
        }
        if (lift <= 0.005f) return go;
        if (lineTop) { rise.dig = lift; return go; }
        if (lift > rise.limit + 1e-3f)
        {
            rise.refused = true; rise.lift = lift;
            warn = (warn == null ? "" : warn + " / ") + name + ": ⛔ 天端を地盤まで " + lift.ToString("F2") +
                   "m 上げると袖の下端が段石の底より " + (lift - rise.limit).ToString("F2") + "m 上に出る(上げの上限 " +
                   rise.limit.ToString("F2") + "m)⇒ 据えなかった(丈の足りる袖の駒が要る)";
            Object.DestroyImmediate(go);
            return null;
        }
        go.transform.position += Vector3.up * lift;
        rise.lift = lift;
        foreach (var n in need) if (!float.IsNaN(n)) rise.proud = Mathf.Max(rise.proud, lift - n);
        return go;
    }

    /// <summary>**袖の根入れの不足**[m](joints[69]・2026-09-25)。袖の見え面(段石から遠い側の面)の 0.05m 外の線を走りに沿って
    /// 0.1m 刻みで <paramref name="footAt"/>(足元の設計面)を引き、底(実メッシュの最低)が「足元の最低 − <paramref name="neiri"/>」より
    /// 上に出る量を返す(≤ 0 なら根入れが取れている)。当たる先: 石段の袖を持つ全ての石段(山王の男坂・女坂・郭の階・中門の内の階)。</summary>
    public static float SodeFootShort(GameObject sode, GameObject dan, int side, System.Func<float, float, float> footAt, float neiri)
    {
        var t = dan.transform; Vector3 right = t.right * Mathf.Sign(side == 0 ? 1 : side), fwd = t.forward;
        var sp = Body(sode.transform, 4000, true); if (sp.Count == 0) return 0f;
        float outer = float.MinValue, bot = float.MaxValue, f0 = float.MaxValue, f1 = float.MinValue;
        foreach (var p in sp) { outer = Mathf.Max(outer, Vector3.Dot(p, right)); bot = Mathf.Min(bot, p.y); float f = Vector3.Dot(p, fwd); f0 = Mathf.Min(f0, f); f1 = Mathf.Max(f1, f); }
        Vector3 o = sode.transform.position; float oR = Vector3.Dot(o, right), oF = Vector3.Dot(o, fwd);
        float gMin = float.MaxValue;
        int n = Mathf.Max(1, Mathf.CeilToInt((f1 - f0) / 0.1f));
        for (int k = 0; k <= n; k++)
        {
            float fk = Mathf.Lerp(f0, f1, (float)k / n);
            Vector3 q = o + right * (outer + 0.05f - oR) + fwd * (fk - oF);
            float g = footAt(q.x, q.z); if (!float.IsNaN(g)) gMin = Mathf.Min(gMin, g);
        }
        return gMin == float.MaxValue ? 0f : bot - (gMin - neiri);
    }

    static GameObject PlaceIshidanSodeFlat(GameObject dan, string sodePath, int side, Transform parent, string name,
                                           out string warn)
    {
        warn = null;
        var t = dan.transform;
        Vector3 right = t.right * Mathf.Sign(side == 0 ? 1 : side);
        Vector3 fwd = t.forward;                      // +Z = 坂下 = 段鼻の側

        // ---- 段石の実メッシュ ------------------------------------------------
        var dp = Body(t, 4000, true);
        if (dp.Count == 0) { warn = name + ": 段石の実メッシュが無い"; return null; }
        float yTread = float.MinValue;
        foreach (var p in dp) if (p.y > yTread) yTread = p.y;
        float nose = float.MinValue, koguchi = float.MinValue;
        foreach (var p in dp)
        {
            if (p.y > yTread - 0.02f) { float f = Vector3.Dot(p, fwd); if (f > nose) nose = f; }
            float r = Vector3.Dot(p, right); if (r > koguchi) koguchi = r;
        }

        // ---- 仮置き(当て推量)→ 袖の実メッシュを測る ---------------------------
        var go = Place(sodePath, t.position + right, t.eulerAngles.y,
                       Vector3.one, parent, name);
        if (go == null) { warn = name + ": 袖の部材が無い " + sodePath; return null; }
        var sp = Body(go.transform, 4000, true);
        if (sp.Count == 0) { warn = name + ": 袖の実メッシュが無い"; return go; }
        float inner = float.MaxValue, sNose = float.MinValue;
        foreach (var p in sp)
        {
            float r = Vector3.Dot(p, right); if (r < inner) inner = r;
            float f = Vector3.Dot(p, fwd); if (f > sNose) sNose = f;
        }
        // 段鼻の真横(坂下の端から 2cm 以内)での袖の天端
        float sTop = float.MinValue;
        foreach (var p in sp) if (Vector3.Dot(p, fwd) > sNose - 0.02f && p.y > sTop) sTop = p.y;

        go.transform.position += right * (koguchi - inner) + fwd * (nose - sNose)
                               + Vector3.up * (yTread + ISHIDAN_SODE_KASA - sTop);

        // ---- 検め: 小口との実際の隙(触れている箇所で測る)------------------------
        Vector3 at; int cnt;
        // ⚠ 筋は 0.25m(Contact の既定)。0.1m にすると段石・袖とも頂点が疎(400〜700)で、両方の頂点が同じ筋に
        //   入らず「測れず」、または小口の面取り(深さ 2cm)の頂点だけを拾って 0.015m の偽の隙が出る(2026-09-23 実測・
        //   男坂 30 駒。極値では全駒 0.000m で触れている)。
        float gap = Contact(go, dan, -right, out at, out cnt, 0.01f, 0.25f, 4000, true);
        if (float.IsNaN(gap) || Mathf.Abs(gap) > 0.005f)
            warn = name + ": 段石の小口との隙 " + (float.IsNaN(gap) ? "測れず" : gap.ToString("F3") + "m");
        return go;
    }

    /// <summary>**曲がる石段の袖を留めに切る**(EDO-0415 ②)。段石を段ごとに折れ線の向きで据える石段では、
    /// 折れ点で袖の外側に口(石段の半幅 × sin 折れ角)が開き、内側は重なる — 剛体の置き方では閉じない。
    /// ⇒ 折れの前後の2駒を、端を石段の芯の鉛直線の周りに折れ角の半分だけ回した駒
    /// (`EdoAssets.Own.IshidanSodeMiter` — 平らな袖と同じ局所座標)へ差し替え、**差し替えた後に継ぎ目を実測**する。
    /// <paramref name="dans"/>[i] = 段 i の段石(下から)、<paramref name="sodes"/>[i] = その脇の袖(無ければ null)、
    /// <paramref name="side"/> = 袖の側(±1)。返り値 = 切った継ぎ目の数。
    /// ⚠ 差し替えは同じ transform(平らな駒を実測で据えた位置)に置く — 切った駒は平らな駒と同じ体の端だけを
    /// 切り直した物なので、位置は平らな駒の実測が決めている。−X 側は鏡(localScale.x = −1)。
    /// ⭐ 硬い条件: 継ぎ目の口・重なり 0(許容0。5mm を超えたら ⚠)。焼いていない角は平らなまま ⚠。</summary>
    public static int MiterIshidanSode(IList<GameObject> dans, IList<GameObject> sodes, int side,
                                       float keri, float fumi, float w, List<string> warn)
    {
        return MiterIshidanSode(dans, sodes, side, keri, fumi, w, warn, null);
    }

    /// <summary>丈を段ごとに持つ版。<paramref name="depthOf"/>[i] = 段 i の袖の丈(<see cref="SodeRise.depth"/>・
    /// null または 0 は既定 2.20)⇒ 留めの駒も**同じ丈**の物を引く(丈違いの駒へ差し替えると下端が段石の底より上に出る)。</summary>
    public static int MiterIshidanSode(IList<GameObject> dans, IList<GameObject> sodes, int side,
                                       float keri, float fumi, float w, List<string> warn, IList<float> depthOf)
    {
        int m = Mathf.Min(dans.Count, sodes.Count);
        // 継ぎ目 j(段 j と j+1 の間)の留めの角(符号つき・正 = 外で伸びる)。袖が片方でも無い継ぎ目は 0。
        var hj = new float[Mathf.Max(0, m - 1)];
        var dj = new float[hj.Length];
        int n = 0;
        for (int j = 0; j + 1 < m; j++)
        {
            GameObject da = dans[j], db = dans[j + 1];
            if (da == null || db == null || sodes[j] == null || sodes[j + 1] == null) continue;
            float d = Mathf.DeltaAngle(da.transform.eulerAngles.y, db.transform.eulerAngles.y);
            if (Mathf.Abs(d) < 0.05f) continue;
            // 外側(口が開く側)= 曲がる向きと反対の側。上の段の登る向きが下の段の +X へ振れていれば +X が内。
            bool outer = side * Vector3.Dot(-db.transform.forward, da.transform.right) < 0f;
            hj[j] = (outer ? 1f : -1f) * Mathf.Abs(d) * 0.5f; dj[j] = d; n++;
        }
        if (n == 0) return 0;
        // 段 i の駒: 坂下の端(+Z)= 継ぎ目 i−1、坂上の端(−Z)= 継ぎ目 i。
        for (int i = 0; i < m; i++)
        {
            if (sodes[i] == null) continue;
            float hF = i > 0 ? hj[i - 1] : 0f, hB = i < hj.Length ? hj[i] : 0f;
            if (hF == 0f && hB == 0f) continue;
            float dep = depthOf != null && i < depthOf.Count && depthOf[i] > 0f ? depthOf[i] : EdoAssets.Own.ISHIDAN_SODE_DEPTH_STD;
            var ng = SwapIshidanSode(sodes[i], MiterPath(keri, fumi, w, hF, hB, i, dep), side, warn);
            if (ng != null) sodes[i] = ng;
        }
        // 検め: 継ぎ目の実際の口(下の駒から上の駒へ、登る向きに測る)
        for (int j = 0; j < hj.Length; j++)
        {
            if (hj[j] == 0f) continue;
            GameObject na = sodes[j], nb = sodes[j + 1];
            Vector3 at; int cnt;
            float gap = Contact(na, nb, -dans[j].transform.forward, out at, out cnt, 0.01f, 0.25f, 4000, true);
            if (float.IsNaN(gap) || Mathf.Abs(gap) > 0.005f)
                warn.Add(na.name + "→" + nb.name + ": 折れ " + dj[j].ToString("F2") + "° の継ぎ目 " +
                         (float.IsNaN(gap) ? "測れず" : gap.ToString("F3") + "m"));
        }
        return n;
    }

    /// <summary>焼いた留めの駒のパス。角は 0.01° に丸めて綴るので、焼いた側(指図の折れ線から算出)と
    /// 据えた段石の yaw 差(float)とで丸めが 1 桁ずれ得る ⇒ 各端 ±0.01° まで探す(0.01° の口は 1mm 未満)。</summary>
    static string MiterPath(float keri, float fumi, float w, float hF, float hB, int i, float depth)
    {
        var dd = new[] { 0f, 0.01f, -0.01f };
        foreach (float a in dd)
            foreach (float b in dd)
            {
                if ((hF == 0f && a != 0f) || (hB == 0f && b != 0f)) continue;
                string p = EdoAssets.Own.IshidanSodeMiter(keri, fumi, w, hF + a, hB + b, i, depth);
                if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p) != null) return p;
            }
        return EdoAssets.Own.IshidanSodeMiter(keri, fumi, w, hF, hB, i, depth);
    }

    /// <summary>据えた袖を、同じ位置で切った駒へ差し替える。焼いていなければ元のまま ⚠ を足して null。</summary>
    static GameObject SwapIshidanSode(GameObject old, string path, int side, List<string> warn)
    {
        if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
        { warn.Add(old.name + ": 留めの駒を焼いていない " + path + "(平らなまま・口が残る)"); return null; }
        var t = old.transform;
        var go = Place(path, t.position, t.eulerAngles.y, new Vector3(side < 0 ? -1f : 1f, 1f, 1f), t.parent, old.name);
        if (go == null) return null;
        go.transform.SetSiblingIndex(t.GetSiblingIndex());
        Object.DestroyImmediate(old);
        return go;
    }

    /// <summary>袖を据える側 = 段石の ±X のどちらに、その袖の土留めの線があるか。
    /// <paramref name="wallNodes"/> = 土留め run の折れ線(世界 XZ)。段石の芯から最も近い節点が +X 側なら +1。</summary>
    public static int IshidanSodeSide(GameObject dan, List<Vector2> wallNodes)
    {
        var t = dan.transform; Vector2 c = new Vector2(t.position.x, t.position.z);
        float bd = float.MaxValue; Vector2 q = c;
        for (int i = 1; i < wallNodes.Count; i++)
        {
            Vector2 a = wallNodes[i - 1], b = wallNodes[i]; Vector2 ab = b - a; float l2 = ab.sqrMagnitude;
            float u = l2 < 1e-9f ? 0f : Mathf.Clamp01(Vector2.Dot(c - a, ab) / l2);
            Vector2 h = a + ab * u; float d = (h - c).sqrMagnitude;
            if (d < bd) { bd = d; q = h; }
        }
        return Vector2.Dot(q - c, new Vector2(t.right.x, t.right.z)) >= 0f ? 1 : -1;
    }

    /// <summary>**石垣の区間の天端の前の縁を、石段の最上段の段石の背の端へ突き付ける**(指図 joints[72]「奥の辺の外面 × 最上段」・2026-09-25・EDO-0430)。
    /// 石段の上端を受ける土留め(切り込みの奥の辺)は、天端と最上段の踏面が同じ高さで並ぶ ── 取り合いは**その高さの帯**で測る:
    /// 駒の並び <paramref name="pieces"/> の天端の帯(各駒の最上点 − <paramref name="band"/> 以上)の頂点の <paramref name="outw"/>(見え面の外向き =
    /// 石段の坂下の側)への射影の最大 = 天端の前の縁、段石 <paramref name="step"/> の踏面の帯の頂点の射影の最小 = 段石の背の端。
    /// 並び全体を <paramref name="outw"/> に沿って平行移動し、両者を一致させる(一直線の天端のまま・隙 0・重なり 0)。
    /// ⛔ 全身の Contact で押さない ── 法の付いた見え面は天端より下で段石の胴(地中)へ入るので、全身で当てると天端に
    /// 0.1m 超の口が開く。⛔ ピボットで合わせない。返り値 = 動かした量[m](+ = 坂下へ・測れなければ NaN)。
    /// 当たる先: 石段の上端を土留めで受ける所すべて(山王 前庭の切り込みの奥の辺。各邸で石段を面の縁へ切り込ませる所)。</summary>
    public static float AbutCrestToStep(IList<GameObject> pieces, Vector2 outw, GameObject step, float band = 0.15f)
    {
        if (step == null || pieces == null || pieces.Count == 0) return float.NaN;
        float front = float.MinValue;
        foreach (var g in pieces)
        {
            if (g == null) continue;
            var vs = Body(g.transform, 999999); float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
            foreach (var v in vs) if (v.y >= top - band) front = Mathf.Max(front, v.x * outw.x + v.z * outw.y);
        }
        var sv = Body(step.transform, 999999, true); float st = float.MinValue; foreach (var v in sv) st = Mathf.Max(st, v.y);
        float back = float.MaxValue;
        foreach (var v in sv) if (v.y >= st - band) back = Mathf.Min(back, v.x * outw.x + v.z * outw.y);
        if (front == float.MinValue || back == float.MaxValue) return float.NaN;
        float shift = back - front;
        foreach (var g in pieces) if (g != null) g.transform.position += new Vector3(outw.x, 0f, outw.y) * shift;
        return shift;
    }

    /// <summary>**最上段の段石の外形を包む面の輪郭**(取り合いの「被せ」── 面の輪郭が最上段の小口まで届き外形を包む・EDO-0430)。
    /// 段石の実メッシュを段の局所の軸(+Z = 坂下 = 表)で測り、表の線(段鼻)から背の外 <paramref name="m"/>・両の小口の外
    /// <paramref name="m"/> までの矩形を世界 XZ で返す。⛔ 表の線より前(下の段の側)へは出さない。測れなければ null。
    /// 当たる先: 面が最上段を包む石段すべて(山王 女坂 × Keidai。男坂・郭の階も欄に「被せ」を書けば同じ型)。</summary>
    public static Vector2[] WrapTopStep(GameObject dan, float m)
    {
        var t = dan.transform; var vs = Body(t, 999999, true); if (vs.Count == 0) return null;
        Vector3 f = t.forward; f.y = 0f; f.Normalize(); Vector3 r = t.right; r.y = 0f; r.Normalize();
        Vector3 o = t.position;
        float s0 = float.MaxValue, s1 = float.MinValue, w0 = float.MaxValue, w1 = float.MinValue;
        foreach (var v in vs) { var d = v - o; float s = Vector3.Dot(d, f), w = Vector3.Dot(d, r); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); w0 = Mathf.Min(w0, w); w1 = Mathf.Max(w1, w); }
        // s1 = 表(坂下・段鼻)/ s0 = 背
        System.Func<float, float, Vector2> P = (s, w) => { var q = o + f * s + r * w; return new Vector2(q.x, q.z); };
        return new[] { P(s1, w0 - m), P(s1, w1 + m), P(s0 - m, w1 + m), P(s0 - m, w0 - m) };
    }

    // ================================================================ 端を相手の面へ突き付ける(法の付いた壁と鉛直な端)
    /// <summary>駒 <paramref name="g"/> の実メッシュの、水平の向き <paramref name="outDir"/> への射影の [最小, 最大](駒の位置からの距離)。</summary>
    static Vector2 ExtentAlong(GameObject g, Vector3 outDir)
    {
        float lo = float.MaxValue, hi = float.MinValue; Vector3 o = g.transform.position;
        foreach (var v in Body(g.transform, 999999, true)) { float d = Vector3.Dot(v - o, outDir); lo = Mathf.Min(lo, d); hi = Mathf.Max(hi, d); }
        return new Vector2(lo, hi);
    }

    /// <summary>**駒の端の面から相手の面までの離れ**を、高さ <paramref name="y"/> の水平な光線で測る(2026-09-25・EDO-0430)。
    /// 端 = 駒の実メッシュの <paramref name="outDir"/> への射影の最大。その端の <paramref name="maxIn"/> 内側から、端に沿う向き
    /// <paramref name="perp"/> の各オフセット <paramref name="along"/>[m](駒の位置から)で <paramref name="outDir"/> へ光線を打ち、
    /// <paramref name="walls"/> の三角形に当たるまでの距離 − <paramref name="maxIn"/> を返す(+ = 口・− = 相手の面が駒の内へ入る・当たらなければ NaN)。
    /// ⭐ 頂点でなく面で測る(<see cref="RayToBodies"/>)── 野面の駒は頂点が疎で、筋の頂点では面の中が空く。</summary>
    public static float[] EndOffsets(GameObject g, Vector3 outDir, Vector3 perp, float[] along, float y, IList<GameObject> walls, float maxIn, float maxOut)
    {
        outDir.y = 0f; outDir.Normalize(); perp.y = 0f; perp.Normalize();
        float e = ExtentAlong(g, outDir).y; var res = new float[along.Length];
        for (int k = 0; k < along.Length; k++)
        {
            Vector3 o = g.transform.position + outDir * (e - maxIn) + perp * along[k]; o.y = y;
            float h = RayToBodies(walls, o, outDir, maxIn + maxOut);
            res[k] = float.IsNaN(h) ? float.NaN : h - maxIn;
        }
        return res;
    }

    /// <summary>**駒の片方の端だけを <paramref name="delta"/>[m] 動かす**(+ = <paramref name="outDir"/> へ伸ばす・− = 詰める)。
    /// 反対の端は動かさない。駒の局所の軸のうち <paramref name="outDir"/> に平行な軸の縮尺を変え、位置を寄せて反対の端を保つ
    /// (端は実メッシュの射影で測る ── ⛔ ピボットで合わせない)。返り値 = 軸の縮尺の比(駒が回っていて平行な軸が無ければ NaN・動かさない)。</summary>
    public static float ResizeEnd(GameObject g, Vector3 outDir, float delta)
    {
        outDir.y = 0f; outDir.Normalize(); var t = g.transform;
        int axis = -1; float best = 0.999f;
        var ax = new[] { t.right, t.up, t.forward };
        for (int i = 0; i < 3; i++) { float c = Mathf.Abs(Vector3.Dot(ax[i], outDir)); if (c > best) { best = c; axis = i; } }
        if (axis < 0) return float.NaN;
        var ex = ExtentAlong(g, outDir); float L = ex.y - ex.x; if (L < 1e-4f) return float.NaN;
        float k = (L + delta) / L;
        var sc = t.localScale; sc[axis] *= k; t.localScale = sc;
        float c0 = ex.y + delta - k * ex.y;          // 端の新しい位置 − 縮尺だけ変えた端の位置
        t.position += outDir * c0;
        return k;
    }

    /// <summary>端の突き付けの報告(<see cref="AbutEndToFace"/>)。</summary>
    public struct EndAbut
    {
        public bool touched;   // 相手の面が端の前後 [−maxIn, +maxOut] に在った
        public bool mixed;     // 端に沿って相手の面の離れが割れた(二つの面に跨る)⇒ 動かしていない
        public float moved;    // 端を動かした量(+ 伸ばす / − 詰める)
        public float spread;   // 標本の離れの幅
        public float gapHi, biteLo;   // 据えた後: 上の高さでの口(+)・下の高さでのめり込み(+)
    }

    /// <summary>**鉛直な端を、法の付いた相手の面へ、高さの中ほどで突き付ける**(2026-09-25・EDO-0430 施主指示)。
    /// 駒 <paramref name="g"/> の <paramref name="outDir"/> 側の端(鉛直)と、相手 <paramref name="walls"/> の面(法 1:0.25 の野面など)は
    /// 高さで離れが変わる ── 見える高さ [<paramref name="yLo"/>, <paramref name="yHi"/>] の**中ほど**の水平な光線で離れを測り、端をそこまで
    /// 詰めるか伸ばす(<see cref="ResizeEnd"/>)。上端では口、下端ではめり込みが残る(法 0.25 × 見える高さ / 2)── その数を
    /// <see cref="EndAbut.gapHi"/> / <see cref="EndAbut.biteLo"/> に返す(実メッシュで測り直した値)。
    /// 端に沿う標本(<paramref name="along"/>)の離れの幅が <paramref name="spreadTol"/> を超えたら、端が二つの面に跨るので**動かさない**
    /// (<see cref="EndAbut.mixed"/>)── 片方へ寄せるともう片方に同じだけの口が開く。
    /// ⭐ 硬い条件の測り(許容0の隙・めり込み)は呼び出し側が gapHi / biteLo で数える。⛔ ピボット・bounds の中心で合わせない。
    /// 当たる先: 石段の段石の小口 × 切り込みの返し・郭の縁の土留め(<see cref="AbutStepEndsToWalls"/>)、石段の袖の背の小口 × 縁の土留めの法。</summary>
    public static EndAbut AbutEndToFace(GameObject g, Vector3 outDir, Vector3 perp, float[] along, float yLo, float yHi,
                                        IList<GameObject> walls, float maxIn, float maxOut, float spreadTol)
    {
        var r = new EndAbut { moved = 0f };
        float yMid = (yLo + yHi) * 0.5f;
        var offs = EndOffsets(g, outDir, perp, along, yMid, walls, maxIn, maxOut);
        var hit = new List<float>(); foreach (var o in offs) if (!float.IsNaN(o)) hit.Add(o);
        if (hit.Count == 0) return r;
        r.touched = true; hit.Sort();
        r.spread = hit[hit.Count - 1] - hit[0];
        if (r.spread > spreadTol) { r.mixed = true; return r; }
        float d = hit[hit.Count / 2];
        if (Mathf.Abs(d) > 0.002f && !float.IsNaN(ResizeEnd(g, outDir, d))) r.moved = d;
        // 据えた後の上端・下端(当たった標本の所だけ)
        var hiO = EndOffsets(g, outDir, perp, along, yHi, walls, maxIn, maxOut);
        var loO = EndOffsets(g, outDir, perp, along, yLo, walls, maxIn, maxOut);
        for (int k = 0; k < along.Length; k++)
        {
            if (float.IsNaN(offs[k])) continue;
            if (!float.IsNaN(hiO[k])) r.gapHi = Mathf.Max(r.gapHi, hiO[k]);
            if (!float.IsNaN(loO[k])) r.biteLo = Mathf.Max(r.biteLo, -loO[k]);
        }
        return r;
    }

    /// <summary>**石段の段石の両の小口を、脇の土留め(法の付いた面)へ段ごとに突き付ける**(2026-09-25・EDO-0430 施主指示)。
    /// 段石は小口が鉛直、切り込みの返しは野面の法 1:0.25 ── 段ごとに**その段の蹴上の中ほど**(踏面 − 蹴上/2)の高さで相手の面を
    /// 光線で測り(<see cref="AbutEndToFace"/>)、段石の長さを段ごとに詰める/伸ばす。上端の口・下端のめり込みは 0.25 × 蹴上 / 2。
    /// 標本は端に沿って踏面の内(段鼻から一段の踏面ぶん)に 5 点。端が二つの面(返しと袖など)に跨る段は動かさず数に返す。
    /// <paramref name="walls"/> には土留めの駒と袖の駒を渡す(段石どうしは渡さない)。伸ばすのは口 <paramref name="maxOut"/> 以内だけ
    /// (離れた壁まで段を延ばさない)。返り値の各段: 段名 → 報告。
    /// 当たる先: 石段が土留め・袖に脇から接するすべて(山王 参道の階 × 切り込みの返し、男坂・女坂・郭の階・中門の内の袖 ── 袖は鉛直なので離れ 0 で動かない)。</summary>
    /// <summary>段石の芯(石段の軸の上の点)の印の子の名。<see cref="AbutStepEndsToWalls"/> が片側を詰める前に据えた原点に置く。</summary>
    public const string AXIS_MARK = "_axis";
    /// <summary>段石の芯(石段の軸の上の点)。印 <see cref="AXIS_MARK"/> があればその位置、無ければ駒の位置。</summary>
    public static Vector3 StepAxis(Transform dan) { var a = dan.Find(AXIS_MARK); return a != null ? a.position : dan.position; }

    public static List<KeyValuePair<string, EndAbut>> AbutStepEndsToWalls(IList<GameObject> dans, float keri, float fumi, IList<GameObject> walls,
                                                                          float maxIn = 0.5f, float maxOut = 0.10f, float spreadTol = 0.031f)
    {
        var res = new List<KeyValuePair<string, EndAbut>>();
        var along = new float[5]; for (int k = 0; k < 5; k++) along[k] = (-0.4f + 0.2f * k) * fumi;
        foreach (var dg in dans)
        {
            if (dg == null) continue;
            float top = float.MinValue; foreach (var v in Body(dg.transform, 999999, true)) top = Mathf.Max(top, v.y);
            // 踏面の内の標本: 段鼻(+Z 側の実メッシュの端)から一段の踏面ぶん奥まで
            Vector3 f = dg.transform.forward; f.y = 0f; f.Normalize();
            float nose = ExtentAlong(dg, f).y;
            var al = new float[5]; for (int k = 0; k < 5; k++) al[k] = nose - fumi * 0.5f + along[k];
            // ⭐ 段の芯(石段の軸の上の点 = 据えた原点)を子 `_axis` に残す ── 片側だけ詰めると駒の原点は軸から外れる。
            //   検め(石段の端点・平面長)は `_axis` で測る。⛔ 位置合わせには使わない(規則21 ── 測るための印)。
            var axT = dg.transform.Find(AXIS_MARK);
            if (axT == null) { var ax = new GameObject(AXIS_MARK); ax.transform.SetParent(dg.transform, false); axT = ax.transform; }
            Vector3 axW = axT.position;   // 駒を詰めても印は世界の同じ点に残す(下で戻す)
            foreach (int side in new[] { -1, 1 })
            {
                Vector3 od = dg.transform.right * side;
                var r = AbutEndToFace(dg, od, f, al, top - keri + 0.02f, top - 0.02f, walls, maxIn, maxOut, spreadTol);
                if (r.touched) res.Add(new KeyValuePair<string, EndAbut>(dg.name + (side < 0 ? "−X" : "+X"), r));
            }
            axT.position = axW;
        }
        return res;
    }

    // ================================================================ 端を法の面で切った駒へ差し替える(EDO-0430 2026-09-26)
    /// <summary>光線が <paramref name="bodies"/> の三角形を通る距離のうち**最も遠い物**(駒の中から打てば、外の面を出る所)。
    /// ⭐ 凸な部品を継いだ駒(<see cref="EdoAssets.Own.SannoDanKiri"/>)は中に蓋が残るので、最初の当たりでなく最後の当たりで外面を取る。</summary>
    public static float RayFarthest(IList<GameObject> bodies, Vector3 o, Vector3 d, float maxDist)
    {
        d.Normalize(); float best = float.MinValue;
        foreach (var g in bodies) if (g != null)
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                var mesh = mf.sharedMesh; if (mesh == null) continue;
                var M = mf.transform.localToWorldMatrix; var vs = mesh.vertices; var ts = mesh.triangles;
                var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) W[i] = M.MultiplyPoint3x4(vs[i]);
                for (int t = 0; t + 2 < ts.Length; t += 3)
                {
                    Vector3 a = W[ts[t]], e1 = W[ts[t + 1]] - a, e2 = W[ts[t + 2]] - a;
                    Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-9f) continue;
                    float inv = 1f / det; Vector3 tv = o - a; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                    Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                    float dist = Vector3.Dot(e2, qv) * inv; if (dist >= 0f && dist <= maxDist && dist > best) best = dist;
                }
            }
        return best == float.MinValue ? float.NaN : best;
    }

    /// <summary>段石の端が法の面の相手(返し・隅の駒)に当たる形の実測(<see cref="MeasureStepEndOnBatter"/>)。</summary>
    public struct BatterEnd
    {
        public bool touched;    // 蹴上の中ほどの高さで、端の前後に相手の面が在った
        public bool mixed;      // 当たった標本の離れが割れた(斜めに交わる・二つの面)⇒ 切る形が決まらない
        public bool straddle;   // 端の一部だけが相手に当たる(返しと袖に跨る)
        public bool uphill;     // 跨ぐとき、相手の隅が坂上(−Z)の側
        public float d;         // 蹴上の中ほどでの返しの面の食い込み(+ = 小口より内)
        public float za;        // 跨ぐとき、隅の駒のもう一面の Z(段の局所・蹴上の中ほど)
        public float spread;    // 当たった標本の離れの幅
    }

    /// <summary>**段石の片方の端と法の面の相手の取り合いを測る**(2026-09-26・EDO-0430)。<paramref name="flatDan"/> は**平らな段石を縮尺 1 で
    /// 据えた物**(小口 = 幅/2)。その段の**蹴上の中ほど**(踏面 − 蹴上/2)の高さで、端に沿って駒の奥行きの全長に 13 点、端から外へ光線を打ち
    /// (<see cref="EndOffsets"/>)、相手の面の食い込み d を取る。一部の標本だけが当たるなら跨ぐ端で、当たらない側から当たる側へ、端の
    /// 内(小口と返しの面の間)を光線で打って隅の駒のもう一面の Z(za)を取る。⭐ 面で測る(頂点でない)。⛔ ピボットで合わせない
    /// (標本の位置は実メッシュの射影から取る)。
    /// 当たる先: 石段の段石 × 切り込みの返し・郭の縁の土留め(野面の法 1:0.25)── 端を切った駒 <see cref="EdoAssets.Own.SannoDanKiri"/> の d・za。</summary>
    public static BatterEnd MeasureStepEndOnBatter(GameObject flatDan, int side, float keri, IList<GameObject> walls,
                                                   float maxIn = 0.5f, float maxOut = 0.10f, float spreadTol = 0.031f)
    {
        var r = new BatterEnd();
        Vector3 f = flatDan.transform.forward; f.y = 0f; f.Normalize();
        Vector3 od = flatDan.transform.right * side; od.y = 0f; od.Normalize();
        float top = float.MinValue; foreach (var v in Body(flatDan.transform, 999999, true)) top = Mathf.Max(top, v.y);
        float yMid = top - keri * 0.5f;
        var ez = ExtentAlong(flatDan, f);
        const int N = 13; var al = new float[N];
        for (int k = 0; k < N; k++) al[k] = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / (N - 1);
        var offs = EndOffsets(flatDan, od, f, al, yMid, walls, maxIn, maxOut);
        var hit = new List<float>(); int firstHit = -1, lastHit = -1, miss = 0;
        for (int k = 0; k < N; k++)
        {
            if (float.IsNaN(offs[k])) { miss++; continue; }
            hit.Add(offs[k]); if (firstHit < 0) firstHit = k; lastHit = k;
        }
        if (hit.Count == 0) return r;
        r.touched = true; hit.Sort();
        r.spread = hit[hit.Count - 1] - hit[0];
        if (r.spread > spreadTol) { r.mixed = true; return r; }
        r.d = -hit[hit.Count / 2];
        if (miss == 0) return r;
        // 跨ぐ端: 当たる標本が一続きで、片方の端に寄っていること(真ん中だけ・飛び飛びは形が決まらない)
        if (lastHit - firstHit + 1 != hit.Count || (firstHit != 0 && lastHit != N - 1)) { r.mixed = true; return r; }
        r.straddle = true; r.uphill = firstHit == 0;   // 当たる標本が −Z(坂上)の側から始まる
        // 隅の駒のもう一面: 小口と返しの面の間を、当たらない側から当たる側へ打つ
        float xEnd = ExtentAlong(flatDan, od).y;
        Vector3 dir = r.uphill ? -f : f;
        float s0 = r.uphill ? ez.y + 0.05f : ez.x - 0.05f;
        Vector3 o = flatDan.transform.position + od * (xEnd - r.d * 0.5f) + f * s0; o.y = yMid;
        float h = RayToBodies(walls, o, dir, ez.y - ez.x + 0.2f);
        if (float.IsNaN(h)) { r.mixed = true; return r; }
        r.za = r.uphill ? s0 - h : s0 + h;
        return r;
    }

    /// <summary>**袖の背(坂上の端)と法の面の相手の離れ e を測る**(2026-09-26・EDO-0430)。<paramref name="flatSode"/> は平らな袖
    /// (<see cref="EdoAssets.Own.IshidanSode(float,float,int,float)"/>)を縮尺 1 で据えた物。袖の局所の高さ
    /// <see cref="EdoAssets.Own.SodeNoriYc"/> で、袖の中の 3 点から坂上へ光線を打ち、相手の面までの距離 − 袖の背の外面までの距離を返す
    /// (+ = 背より坂上に相手 = 口・− = 相手が袖に食い込む・当たらなければ NaN)。<paramref name="spread"/> = 3 点の幅。
    /// 当たる先: 石段の袖の run の坂上の端 × 隅の駒・返しの野面の法 ── 背を法に切った駒 <see cref="EdoAssets.Own.IshidanSodeNori"/> の e。</summary>
    public static float MeasureSodeBackOnBatter(GameObject sode, float keri, IList<GameObject> walls, out float spread, float maxOut = 0.6f)
    {
        spread = 0f;
        Vector3 f = sode.transform.forward; f.y = 0f; f.Normalize();
        Vector3 rt = sode.transform.right; rt.y = 0f; rt.Normalize();
        float yc = sode.transform.position.y + EdoAssets.Own.SodeNoriYc(keri) * sode.transform.lossyScale.y;
        var own = new List<GameObject> { sode };
        var es = new List<float>();
        foreach (float a in new[] { -0.2f, 0f, 0.2f })
        {
            // 光線の起点は袖の中(袖の実メッシュの奥行きの中ほど)
            var ez = ExtentAlong(sode, f);
            Vector3 o = sode.transform.position + rt * a + f * ((ez.x + ez.y) * 0.5f); o.y = yc;
            float b = RayFarthest(own, o, -f, 5f); if (float.IsNaN(b)) continue;
            float w = RayToBodies(walls, o, -f, b + maxOut); if (float.IsNaN(w)) continue;
            es.Add(w - b);
        }
        if (es.Count == 0) return float.NaN;
        es.Sort(); spread = es[es.Count - 1] - es[0];
        return es[es.Count / 2];
    }

    /// <summary>光線での隙(+)/ めり込み(−): 駒の中の点 <paramref name="o"/> から <paramref name="dir"/> へ、相手までの距離 − 駒の外面までの距離。</summary>
    static float GapAlong(GameObject piece, IList<GameObject> others, Vector3 o, Vector3 dir, float maxOut)
    {
        float b = RayFarthest(new List<GameObject> { piece }, o, dir, 8f); if (float.IsNaN(b)) return float.NaN;
        float w = RayToBodies(others, o, dir, b + maxOut); if (float.IsNaN(w)) return float.NaN;
        return w - b;
    }

    /// <summary>駒を同じ位置・向き・縮尺で別の部材へ差し替える(新しい駒を置いてから旧を消す ── 例外で群が欠けないように)。子の印 `_axis` は世界の同じ点へ移す。</summary>
    static GameObject SwapPart(GameObject old, string path)
    {
        var t = old.transform;
        var g = Place(path, t.position, t.eulerAngles.y, t.localScale, t.parent, old.name);
        g.transform.SetSiblingIndex(t.GetSiblingIndex());
        var ax = t.Find(AXIS_MARK);
        if (ax != null) { var m = new GameObject(AXIS_MARK); m.transform.SetParent(g.transform, false); m.transform.position = ax.position; }
        Object.DestroyImmediate(old);
        return g;
    }

    /// <summary>**石段の段石の端・袖の背を、法の面の相手に合わせて切った駒へ差し替える**(2026-09-26・EDO-0430 施主裁定B・EDO-0442)。
    /// 鉛直な駒を法 1:0.25 の野面へ中ほどで突き付けると、上下に 0.25×丈/2 の口とめり込みが残る(<see cref="AbutEndToFace"/>)。
    /// 焼いてある「端を法で切った駒」があれば差し替えて口・めり込みを 0 にする:
    /// ① 段石 — 平らな段石を縮尺 1 で芯(<see cref="StepAxis"/> ── Stage2 が据えた所)に仮に置いた物で両端を測り
    ///   (<see cref="MeasureStepEndOnBatter"/>)、d・za に合う駒(<paramref name="kiriPath"/>・測りの誤差 <paramref name="tol"/> で引く)へ差し替える。
    /// ② 袖 — 袖の run(`TW_<行>_<番>`)の**坂上の端の駒**だけ。坂下の端を保って縮尺 1 に戻した平らな袖で e を測り
    ///   (<see cref="MeasureSodeBackOnBatter"/>)、<see cref="EdoAssets.Own.SodeNoriSnap"/> の駒へ差し替え、残りだけ <see cref="ResizeEnd"/> で詰める。
    /// 焼いていない組は差し替えず(平らなまま → 呼び手が中ほどの突き付けを掛ける)、焼く一覧の行を <paramref name="sb"/> に刷る。
    /// 斜めに交わる・二つの面に割れる端は切る形が決まらないので差し替えず ⚠ を刷る。
    /// 返り値 = 差し替えた駒(呼び手は突き付けを掛けない)。据えた後の口・めり込みは実メッシュを光線で測り直して刷る。
    /// ⭐ 硬い条件(許容0): 口・めり込み ≤ 0.005。超えたら ⚠。
    /// 当たる先: 石段が野面の返し・隅の駒に脇から・背から接するすべて(山王 参道の階 × 前庭の北の切り込み。女坂の足・郭の階も測る)。</summary>
    public static HashSet<GameObject> CutStairEndsToBatter(string label, IList<GameObject> dans, IList<GameObject> sodes, float keri, float fumi,
        IList<GameObject> walls, System.Func<int, string> flatDanPath, System.Func<int, string, string, string> kiriPath,
        System.Func<GameObject, int, string> flatSodePath, System.Func<int, float, string> noriPath, System.Text.StringBuilder sb, float tol = 0.003f)
    {
        var done = new HashSet<GameObject>();
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var need = new List<string>(); int nDan = 0, nSode = 0; float worst = 0f;
        // ① 段石
        foreach (var dg0 in dans)
        {
            if (dg0 == null) continue; int i;
            if (!int.TryParse(dg0.name.Substring(dg0.name.IndexOf('_') + 1), out i)) continue;
            string flat = flatDanPath(i);
            var probe = Place(flat, StepAxis(dg0.transform), dg0.transform.eulerAngles.y, Vector3.one, dg0.transform.parent, "__probe_dan");
            BatterEnd eL, eR;
            try { eL = MeasureStepEndOnBatter(probe, -1, keri, walls); eR = MeasureStepEndOnBatter(probe, 1, keri, walls); }
            finally { Object.DestroyImmediate(probe); }
            if (!eL.touched && !eR.touched) continue;
            if (eL.mixed || eR.mixed)
            {
                sb.AppendLine("    ⚠ " + label + " " + dg0.name + ": 端が相手の面と斜めに交わるか二つの面に割れ、切る形が決まらない(" +
                              (eL.mixed ? "−X 幅 " + eL.spread.ToString("F3") : "") + (eR.mixed ? " +X 幅 " + eR.spread.ToString("F3") : "") + ")── 差し替えない");
                continue;
            }
            System.Func<BatterEnd, string> spec = e => !e.touched || (!e.straddle && Mathf.Abs(e.d) < 0.002f) ? EdoAssets.Own.DanKiriNone
                : e.straddle ? EdoAssets.Own.DanKiriEnd(e.d, e.za, e.uphill) : EdoAssets.Own.DanKiriEnd(e.d);
            string sL = spec(eL), sR = spec(eR);
            if (sL == EdoAssets.Own.DanKiriNone && sR == EdoAssets.Own.DanKiriNone) continue;
            string want = kiriPath(i, sL, sR);
            string got = EdoAssets.Own.NearestBaked(want, tol);
            if (got == null)
            {
                need.Add(i + " " + (i % 2 == 0 ? "a" : "b") + " L" + (sL == EdoAssets.Own.DanKiriNone ? "-" : sL) + " R" + (sR == EdoAssets.Own.DanKiriNone ? "-" : sR));
                continue;
            }
            // 平らな段石を芯へ戻してから差し替える(突き付けの縮尺を持ち越さない)
            var t0 = dg0.transform; Vector3 ax = StepAxis(t0);
            t0.localScale = Vector3.one; t0.position = ax;
            var ng = SwapPart(dg0, got); done.Add(ng); nDan++;
            // 据えた後: 端に沿って 13 点 × 3 高さ(踏面の下・中ほど・蹴上の下端の上)で、駒の外面から相手(土留め+袖)までを測る
            var others = new List<GameObject>(walls); foreach (var s in sodes) if (s != null) others.Add(s);
            Vector3 f = ng.transform.forward; f.y = 0f; f.Normalize();
            float top = float.MinValue; foreach (var v in Body(ng.transform, 999999, true)) top = Mathf.Max(top, v.y);
            var ez = ExtentAlong(ng, f); float gMax = 0f, bMax = 0f; int nS = 0;
            foreach (int side in new[] { -1, 1 })
            {
                var e = side < 0 ? eL : eR; if (!e.touched) continue;
                Vector3 od = ng.transform.right * side; od.y = 0f; od.Normalize();
                float xEnd = ExtentAlong(ng, od).y;
                foreach (float yy in new[] { top - 0.02f, top - keri * 0.5f, top - keri + 0.02f })
                    for (int k = 0; k < 13; k++)
                    {
                        float s = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / 12f;
                        Vector3 o = ng.transform.position + od * (xEnd - 0.6f) + f * s; o.y = yy;
                        float gp = GapAlong(ng, others, o, od, 0.10f); if (float.IsNaN(gp)) continue;
                        nS++; if (gp > 0) gMax = Mathf.Max(gMax, gp); else bMax = Mathf.Max(bMax, -gp);
                    }
                if (e.straddle)   // 欠いた奥の面 × 隅の駒のもう一面
                    foreach (float yy in new[] { top - 0.02f, top - keri * 0.5f, top - keri + 0.02f })
                    {
                        Vector3 dir = e.uphill ? -f : f;
                        Vector3 o = ng.transform.position + od * (xEnd - Mathf.Max(0.01f, e.d * 0.5f)) + f * (e.za + (e.uphill ? 0.15f : -0.15f)); o.y = yy;
                        float gp = GapAlong(ng, walls, o, dir, 0.10f); if (float.IsNaN(gp)) continue;
                        nS++; if (gp > 0) gMax = Mathf.Max(gMax, gp); else bMax = Mathf.Max(bMax, -gp);
                    }
            }
            worst = Mathf.Max(worst, Mathf.Max(gMax, bMax));
            sb.AppendLine("    " + label + " " + ng.name + " → " + System.IO.Path.GetFileNameWithoutExtension(got) +
                          "(測った −X " + (eL.touched ? "d " + eL.d.ToString("F3", inv) + (eL.straddle ? " za " + eL.za.ToString("F3", inv) : "") : "当たらず") +
                          " / +X " + (eR.touched ? "d " + eR.d.ToString("F3", inv) + (eR.straddle ? " za " + eR.za.ToString("F3", inv) : "") : "当たらず") +
                          ")/ 据えた後 口 " + gMax.ToString("F3") + " めり込み " + bMax.ToString("F3") + "(当たり " + nS + ")" +
                          (Mathf.Max(gMax, bMax) > 0.005f ? " ⚠" : ""));
        }
        // ② 袖の坂上の端の駒
        var topIdx = new Dictionary<string, int>();
        foreach (var sg in sodes)
        {
            if (sg == null) continue; int us = sg.name.LastIndexOf('_'); int ii;
            if (us < 0 || !int.TryParse(sg.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
            string row = sg.name.Substring(0, us); int cur;
            if (!topIdx.TryGetValue(row, out cur) || ii > cur) topIdx[row] = ii;
        }
        foreach (var sg0 in sodes)
        {
            if (sg0 == null) continue; int us = sg0.name.LastIndexOf('_'); int ii;
            if (us < 0 || !int.TryParse(sg0.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
            if (topIdx[sg0.name.Substring(0, us)] != ii) continue;
            string flat = flatSodePath(sg0, ii); if (flat == null) continue;
            var t0 = sg0.transform; Vector3 f = t0.forward; f.y = 0f; f.Normalize();
            // 坂下の端(+Z の実メッシュの端)を保って、平らな袖を縮尺 1 で仮に置く
            float front = Vector3.Dot(t0.position, f) + ExtentAlong(sg0, f).y;
            var sc = t0.localScale; sc.z = Mathf.Sign(sc.z);
            var probe = Place(flat, t0.position, t0.eulerAngles.y, sc, t0.parent, "__probe_sode");
            float pf = Vector3.Dot(probe.transform.position, f) + ExtentAlong(probe, f).y;
            probe.transform.position += f * (front - pf);
            float spread; float e;
            try { e = MeasureSodeBackOnBatter(probe, keri, walls, out spread); }
            catch { Object.DestroyImmediate(probe); throw; }
            Vector3 flatPos = probe.transform.position;
            Object.DestroyImmediate(probe);
            if (float.IsNaN(e)) continue;
            if (spread > 0.031f) { sb.AppendLine("    ⚠ " + label + " " + sg0.name + " の背: 相手の面が斜めに交わる(幅 " + spread.ToString("F3") + ")── 差し替えない"); continue; }
            float snap = EdoAssets.Own.SodeNoriSnap(e);
            string got = noriPath(ii, snap);
            if (got == null || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(got) == null)
            { sb.AppendLine("    " + label + " " + sg0.name + " の背: e " + e.ToString("+0.000;-0.000", inv) + " の駒(E" + snap.ToString("+0.00;-0.00", inv) + ")が焼けていない ── 差し替えない"); continue; }
            t0.localScale = sc; t0.position = flatPos;
            var ng = SwapPart(sg0, got); done.Add(ng); nSode++;
            // 丸めの残りを詰める: Yc の高さで背の外面 → 相手の面の口を測り、Yc での駒の長さの比で縮尺する
            float rest = 0f;
            for (int it = 0; it < 2; it++)
            {
                float sp2; float g2 = MeasureSodeBackOnBatter(ng, keri, walls, out sp2);
                if (float.IsNaN(g2) || Mathf.Abs(g2) < 0.0005f) break;
                Vector3 rt = ng.transform.right; var ez = ExtentAlong(ng, f);
                Vector3 o = ng.transform.position + f * ((ez.x + ez.y) * 0.5f);
                o.y = ng.transform.position.y + EdoAssets.Own.SodeNoriYc(keri);
                var own = new List<GameObject> { ng };
                float lyc = RayFarthest(own, o, -f, 5f) + RayFarthest(own, o, f, 5f);
                float lext = ez.y - ez.x;
                ResizeEnd(ng, -f, g2 * lext / lyc); rest += g2;
            }
            // 据えた後: 段の踏面の上 〜 袖の天端の下で 5 高さ × 3 点
            float sTop = float.MinValue, sBot = float.MaxValue; foreach (var v in Body(ng.transform, 999999, true)) { sTop = Mathf.Max(sTop, v.y); }
            sBot = ng.transform.position.y;   // 段の踏面の高さ(袖の局所 Y=0 の面 ── 測る高さの下限の目安)
            float gMax = 0f, bMax = 0f; int nS = 0;
            Vector3 rr = ng.transform.right; rr.y = 0f; rr.Normalize();
            var ez2 = ExtentAlong(ng, f);
            for (int hk = 0; hk < 5; hk++)
            {
                float yy = Mathf.Lerp(sBot + 0.02f, sTop - 0.02f, hk / 4f);
                foreach (float a in new[] { -0.2f, 0f, 0.2f })
                {
                    Vector3 o = ng.transform.position + rr * a + f * ((ez2.x + ez2.y) * 0.5f); o.y = yy;
                    float gp = GapAlong(ng, walls, o, -f, 0.10f); if (float.IsNaN(gp)) continue;
                    nS++; if (gp > 0) gMax = Mathf.Max(gMax, gp); else bMax = Mathf.Max(bMax, -gp);
                }
            }
            worst = Mathf.Max(worst, Mathf.Max(gMax, bMax));
            sb.AppendLine("    " + label + " " + ng.name + " の背 → " + System.IO.Path.GetFileNameWithoutExtension(got) + "(測った e " + e.ToString("+0.000;-0.000", inv) +
                          "・残り " + rest.ToString("+0.000;-0.000", inv) + " を詰めた)/ 据えた後 口 " + gMax.ToString("F3") + " めり込み " + bMax.ToString("F3") +
                          "(当たり " + nS + ")" + (Mathf.Max(gMax, bMax) > 0.005f ? " ⚠" : ""));
        }
        if (nDan + nSode > 0 || need.Count > 0)
            sb.AppendLine("  " + label + ": 端を法で切った駒へ差し替え 段石 " + nDan + " / 袖 " + nSode + " ── 口・めり込みの最大 " + worst.ToString("F3") +
                          (need.Count > 0 ? " / ⚠ 焼いていない段石 " + need.Count + "(焼く一覧の行: " + string.Join(" | ", need) + ")" : ""));
        return done;
    }
}
