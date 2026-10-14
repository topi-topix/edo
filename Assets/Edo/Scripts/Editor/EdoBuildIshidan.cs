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
                                                     System.Func<float, float, float> footAt = null, float neiri = 0.05f,
                                                     float kasa = ISHIDAN_SODE_KASA)
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
            var go = PlaceIshidanSode(dan, path, side, parent, name, groundHi, out w, out r, lineTop, kasa);
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
                                              bool groundHi, out string warn, out SodeRise rise, bool lineTop = false,
                                              float kasa = ISHIDAN_SODE_KASA)
    {
        rise = new SodeRise();
        var go = PlaceIshidanSodeFlat(dan, sodePath, side, parent, name, out warn, kasa);
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
                                           out string warn, float kasa = ISHIDAN_SODE_KASA)
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
                               + Vector3.up * (yTread + kasa - sTop);

        // ---- 検め: 小口との実際の隙(触れている箇所で測る)------------------------
        // ⚠ 頂点の筋(Contact)で測らない。段石・袖とも頂点が疎(100〜700)で、筋 0.25m でも 0.1m でも
        //   面取り・打込接ぎの目地(深さ 1.5〜2cm)の頂点だけが同じ筋に入り、触れている駒に 0.015〜0.020 の偽の隙が出る
        //   (2026-09-23 男坂 30 駒・2026-10-07 岡部 K_Kuruwa の袖 R_08/L_08。光線では全駒 0.000)。⇒ 面で測る(KoguchiGap)。
        int hit, tot;
        float gap = KoguchiGap(dan, new[] { go }, side, out hit, out tot);
        if (float.IsNaN(gap) || Mathf.Abs(gap) > 0.005f)
            warn = name + ": 段石の小口との隙 " + (float.IsNaN(gap) ? "測れず" : gap.ToString("F3") + "m") + "(光線 " + hit + "/" + tot + ")";
        return go;
    }

    /// <summary>**段石の小口と袖の隙を面で測る**(EDO-0502 2026-10-07)。段石の小口の面(<paramref name="side"/> 側で最も外の
    /// 頂点 3mm 以内の範囲)を 7×7 に割り、各点の 0.05m 内から外へ光線を打って <paramref name="sodes"/> の三角形までの距離を測る。
    /// 返り値 = 最小の隙[m](0 = 触れている・負 = めり込み・NaN = どの光線も袖に当たらない)。<paramref name="hit"/> = 当たった光線の数。
    /// ⭐ 頂点の筋(<see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>)は疎な駒で面取り・目地の頂点だけを
    /// 拾い偽の隙を出す ⇒ 面と面の取り合いは光線で。当たる先: 石段の袖を持つ全ての石段(岡部 K_Kuruwa・山王の男坂・女坂・郭の階)。
    /// 硬い条件の検め(許容0 = 5mm を超えたら ⚠)。</summary>
    public static float KoguchiGap(GameObject dan, IList<GameObject> sodes, int side, out int hit, out int tot)
    {
        hit = 0; tot = 0;
        var t = dan.transform; Vector3 right = t.right * Mathf.Sign(side == 0 ? 1 : side), fwd = t.forward;
        var dp = Body(t, 4000, true); if (dp.Count == 0) return float.NaN;
        float kog = float.MinValue; foreach (var p in dp) kog = Mathf.Max(kog, Vector3.Dot(p, right));
        float f0 = float.MaxValue, f1 = float.MinValue, y0 = float.MaxValue, y1 = float.MinValue;
        foreach (var p in dp)
            if (Vector3.Dot(p, right) > kog - 0.003f)
            { float f = Vector3.Dot(p, fwd); f0 = Mathf.Min(f0, f); f1 = Mathf.Max(f1, f); y0 = Mathf.Min(y0, p.y); y1 = Mathf.Max(y1, p.y); }
        Vector3 o0 = t.position; float oR = Vector3.Dot(o0, right), oF = Vector3.Dot(o0, fwd);
        float best = float.NaN;
        for (int a = 0; a <= 6; a++)
            for (int b = 0; b <= 6; b++)
            {
                float f = Mathf.Lerp(f0 + 0.01f, f1 - 0.01f, a / 6f), y = Mathf.Lerp(y0 + 0.01f, y1 - 0.01f, b / 6f);
                Vector3 o = o0 + right * (kog - 0.05f - oR) + fwd * (f - oF); o.y = y; tot++;
                float h = RayToBodies(sodes, o, right, 0.5f);
                if (float.IsNaN(h)) continue;
                hit++; float g = h - 0.05f;
                if (float.IsNaN(best) || g < best) best = g;
            }
        return best;
    }

    /// <summary><see cref="PlaceIshidanSodeRow"/> の検め(全て実メッシュで測った値)。</summary>
    public struct SodeRowReport
    {
        public int placed, ext, refused;   // 段の脇に据えた駒・坂下へ継いだ駒・退けた段
        public float kasa;                 // 使った笠の上がり(段鼻の線から袖の天端まで)
        public bool faceHit;               // 上端の相手(土留めの見え面)を測れたか
        public float crest, atFace;        // 相手の天端・面の位置での袖の天端 − 相手の天端(0 = 入隅で天端が揃う)
        public float overCrest;            // 面より奥(相手の中)で袖の天端が相手の天端を越える量の最大(見えるのは相手の天端の上だけ)
        public bool sinkOk; public float endSink;   // 坂下の端の小口の天端が足元の地盤より下がった量(≥ sink で合格)
    }

    /// <summary>**石段の片側の袖を一列に据える**(EDO-0502 2026-10-07・岡部 K_Kuruwa.sode「両脇を袖石垣で受ける」)。
    /// 段石の列 <paramref name="dans"/>(下から・各段の <paramref name="side"/> 側の端の段石)の脇に、段ごとの袖の駒を
    /// <see cref="PlaceIshidanSodeByDepth"/> で据え(丈は足元の根入れに足りる最小)、上端と下端を相手に合わせて納める:
    /// ① 上端の相手 = 石段が切った土留めの駒 <paramref name="walls"/>。袖の線(段石の小口の外 0.15 / 0.45)で坂下から坂上へ光線を
    ///   打ち、見え面の走りの位置を測る(天端 = 面の近くの駒の最高)。⛔ 面を紙の線で決めない。
    /// ② 笠の上がり = min(狙い <paramref name="kasaTarget"/>【柔】, 相手の天端 − 面の位置の段鼻の線)【硬: 入隅で相手の天端を越えない】。
    ///   ≤ <paramref name="minKasa"/> なら ⛔(段石の小口が耳石より上に出る ── 硬い条件どうしがぶつかる)を刷って minKasa で据える。
    /// ③ 段鼻が面より坂下にある段だけ据える(面より奥の段の脇は土留めの中)。
    /// ④ 坂下の端は、最下段の袖の坂下の端へ同じ断面の駒を「端の面・内の面・天端」の三つを実メッシュで突き付けて継ぎ、
    ///   継いだ駒の坂下の端の天端 ≤ 足元の地盤 − <paramref name="sink"/> になったら止める【硬・小口を地上に見せない】。
    /// ①' <paramref name="planRay"/>(袖を本線より先に据える所): 上端の相手を本線の**計画の見え面の線**で測る(光線 (原点, 向き) → 線までの距離・交わらなければ NaN)。
    ///   天端は <paramref name="planCrest"/>(計画の天端)。⛔ 駒を測らない(まだ据わっていない)。
    /// ⛔ ピボット・bounds の中心で合わせない。当たる先: 土留めを切って張り出す屋敷の中の石段(岡部 K_Kuruwa)。
    /// 山王の石段の袖(Stage2_Kaidan)は段ごとの PlaceIshidanSodeByDepth のまま(①②④ は相手が切通し・返しなので使わない)。</summary>
    public static List<GameObject> PlaceIshidanSodeRow(IList<GameObject> dans, int side, System.Func<int, float, string> pathOf, IList<float> depths,
                                                       Transform parent, string name, float kasaTarget, float minKasa, IList<GameObject> walls,
                                                       float sink, System.Func<float, float, float> footAt, float neiri, List<string> warn,
                                                       out SodeRowReport rep, int maxExt = 8,
                                                       System.Func<Vector3, Vector3, float> planRay = null, float planCrest = float.NaN,
                                                       int stopNose = -1, bool kasaPerStep = false)
    {
        // stopNose(普請方 第137巡 K_Kuruwa.sodeR137【硬】「左右とも袖は n 段目の段鼻で止める」): 0 始まりの段の番号 ── その段より上の段の脇には袖を立てない。
        // kasaPerStep(同【硬: 相手の天端を越えない】「袖の笠の天端 = min(段鼻を結ぶ線 + 狙い, 相手の天端)・上端の近くでは相手の天端で水平に寝かせる」): 笠の上がりを段ごとに
        //   min(狙い, 相手の天端 − 次の段の踏面)にする(⛔ 一列一つの上がりにすると入隅の 0 が全段に効いて笠が段鼻の線まで下がった・第137巡)。下限(笠 ≥ 踏面)は段ごとに minKasa で検める。
        rep = new SodeRowReport(); rep.atFace = float.NaN; rep.overCrest = float.NaN; rep.endSink = float.NaN;
        var res = new List<GameObject>();
        int n = dans == null ? 0 : dans.Count; if (n == 0) return res;
        var top = dans[n - 1].transform;
        Vector3 right = top.right * Mathf.Sign(side == 0 ? 1 : side), fwd = top.forward;
        // 段石ごとの段鼻(踏面の帯の最も坂下)と踏面の高さ
        var noseF = new float[n]; var tread = new float[n]; float kog = float.MinValue;
        for (int i = 0; i < n; i++)
        {
            noseF[i] = float.NaN; tread[i] = float.NaN; if (dans[i] == null) continue;
            var vs = Body(dans[i].transform, 4000, true); if (vs.Count == 0) continue;
            float yt = float.MinValue; foreach (var p in vs) yt = Mathf.Max(yt, p.y);
            float nf = float.MinValue; foreach (var p in vs) { if (p.y > yt - 0.02f) nf = Mathf.Max(nf, Vector3.Dot(p, fwd)); kog = Mathf.Max(kog, Vector3.Dot(p, right)); }
            noseF[i] = nf; tread[i] = yt;
        }
        // 段鼻の線(上の二段から): f の位置の高さ
        int i1 = n - 1, i0 = n - 2; while (i1 >= 0 && float.IsNaN(noseF[i1])) i1--; i0 = i1 - 1; while (i0 >= 0 && float.IsNaN(noseF[i0])) i0--;
        if (i1 < 0 || i0 < 0) { warn.Add(name + ": 段石が二段無い ── 袖を据えない"); return res; }
        float slope = (tread[i1] - tread[i0]) / Mathf.Max(1e-4f, noseF[i0] - noseF[i1]);   // 坂上(−f)へ 1m で上がる高さ
        System.Func<float, float> noseLine = f => tread[i1] + (noseF[i1] - f) * slope;
        // ① 上端の相手の面
        float fFace = float.NegativeInfinity, crest = float.NaN;
        if (planRay != null && !float.IsNaN(planCrest))
        {   // ①' 上端の相手 = 本線の**計画の見え面の線**(区間の線と向き・天端の前の縁)── 駒より先に袖を据える所(指図 TW_Kado_Hokuto.cuts 追記 2026-10-10o
            //   「袖の上端は本線の駒でなく、本線の計画の見え面の線で決める」【硬】── 据える順 段石 → 袖 → 本線 の循環を断つ)。光線は袖の線(小口の外 0.15 / 0.45)で坂上へ。
            float fStart = noseF[0] + 1.0f;
            foreach (float lat in new[] { 0.15f, 0.45f })
            {
                Vector3 o = right * (kog + lat) + fwd * fStart;
                float h = planRay(o, -fwd); if (!float.IsNaN(h)) fFace = Mathf.Max(fFace, fStart - h);
            }
            rep.faceHit = !float.IsNegativeInfinity(fFace); crest = planCrest; rep.crest = crest;
            if (!rep.faceHit) warn.Add(name + ": ⚠ 上端の相手(本線の計画の見え面の線)に袖の線が交わらない ── 上端は最上段で止める");
        }
        else if (walls != null && walls.Count > 0)
        {
            float fStart = noseF[0] + 1.0f;
            float y0 = tread[i1];
            float f1 = float.NegativeInfinity;
            foreach (float lat in new[] { 0.15f, 0.45f })
            {
                Vector3 o = right * (kog + lat) + fwd * fStart; o.y = y0;
                float h = RayToBodies(walls, o, -fwd, 30f); if (!float.IsNaN(h)) f1 = Mathf.Max(f1, fStart - h);
            }
            if (!float.IsNegativeInfinity(f1))
            {
                crest = float.MinValue;
                foreach (var w in walls) foreach (var p in Body(w.transform, 20000, true))
                {
                    float r = Vector3.Dot(p, right), f = Vector3.Dot(p, fwd);
                    if (r >= kog - 0.05f && r <= kog + 0.65f && f <= f1 + 0.5f && f >= f1 - 2.0f) crest = Mathf.Max(crest, p.y);
                }
                foreach (float lat in new[] { 0.15f, 0.45f })
                {
                    Vector3 o = right * (kog + lat) + fwd * fStart; o.y = crest - 0.02f;
                    float h = RayToBodies(walls, o, -fwd, 30f); if (!float.IsNaN(h)) fFace = Mathf.Max(fFace, fStart - h);
                }
                rep.faceHit = !float.IsNegativeInfinity(fFace); rep.crest = crest;
            }
            if (!rep.faceHit) warn.Add(name + ": ⚠ 上端の相手(土留めの見え面)を光線で測れない ── 上端は最上段で止める");
        }
        // ② 笠の上がり
        float kasa = kasaTarget;
        if (rep.faceHit && !kasaPerStep) kasa = Mathf.Min(kasaTarget, crest - noseLine(fFace));
        if (kasaPerStep) { /* 段ごと(③) */ }
        else if (kasa <= minKasa)
        {
            warn.Add(name + ": ⛔ 入隅で相手の天端 " + crest.ToString("F2") + " を越えない笠の上がり " + kasa.ToString("F3") + " が下限 " + minKasa.ToString("F3") +
                     " 以下(段石の小口が耳石より上に出る)── 下限で据えた");
            kasa = minKasa;
        }
        else if (kasa < kasaTarget - 1e-3f)
            warn.Add(name + ": ⚠ 笠の上がり " + kasa.ToString("F3") + "(狙い " + kasaTarget.ToString("F2") + "【柔】── 入隅で相手の天端 " + crest.ToString("F2") + " を越えない上限【硬】)");
        rep.kasa = kasa;
        // ③ 段の脇に据える
        for (int i = 0; i < n; i++)
        {
            if (dans[i] == null || float.IsNaN(noseF[i])) continue;
            if (rep.faceHit && noseF[i] <= fFace) continue;              // 段鼻が面より奥 = 土留めの中
            if (stopNose >= 0 && i >= stopNose) continue;                // n 段目の段鼻で止める(その段から上の脇は立てない)
            float kasaI = kasa;
            if (kasaPerStep && !float.IsNaN(crest))
            {
                int iu = i + 1; while (iu < n && float.IsNaN(tread[iu])) iu++;
                float upY = iu < n ? tread[iu] : (rep.faceHit ? noseLine(fFace) : tread[i]);   // 袖の駒の上の端の段鼻の線の高さ
                kasaI = Mathf.Min(kasaTarget, crest - upY);
                if (kasaI < minKasa - 1e-4f) { warn.Add(name + "_" + i.ToString("00") + ": ⛔ 笠の上がり " + kasaI.ToString("F3") + " < 下限 " + minKasa.ToString("F3") + "(相手の天端 " + crest.ToString("F2") + " を越えないと笠が踏面より下がる)── 下限で据えた"); kasaI = minKasa; }
                else if (kasaI < kasaTarget - 1e-3f) warn.Add(name + "_" + i.ToString("00") + ": ⚠ 笠の上がり " + kasaI.ToString("F3") + "(狙い " + kasaTarget.ToString("F2") + "【柔】── 相手の天端 " + crest.ToString("F2") + " で寝かせた【硬】)");
                rep.kasa = i == 0 ? kasaI : Mathf.Min(rep.kasa, kasaI);
            }
            string w; SodeRise rz; int ic = i;
            var sg = PlaceIshidanSodeByDepth(dans[i], d => pathOf(ic, d), depths, side, parent, name + "_" + i.ToString("00"), false,
                                             out w, out rz, false, footAt, neiri, kasaI);
            if (w != null) warn.Add(w);
            if (sg == null || rz.refused) { rep.refused++; continue; }
            res.Add(sg); rep.placed++;
        }
        if (res.Count == 0) return res;
        // 入隅の検め: 面の位置の袖の天端と相手の天端、面より奥で越える量
        if (rep.faceHit)
        {
            float atF = float.MinValue, over = float.MinValue;
            foreach (var p in Body(res[res.Count - 1].transform, 4000, true))
            {
                float f = Vector3.Dot(p, fwd);
                if (Mathf.Abs(f - fFace) < 0.03f) atF = Mathf.Max(atF, p.y);
                if (f < fFace) over = Mathf.Max(over, p.y - crest);
            }
            rep.atFace = atF == float.MinValue ? float.NaN : atF - crest;
            rep.overCrest = over == float.MinValue ? 0f : Mathf.Max(0f, over);
        }
        // ④ 坂下へ継いで小口を沈める
        var prev = res[0];
        for (int k = 1; k <= maxExt + 1; k++)
        {
            var pv = Body(prev.transform, 4000, true);
            float fMax = float.MinValue, rIn = float.MaxValue, rOut = float.MinValue;
            foreach (var p in pv) { fMax = Mathf.Max(fMax, Vector3.Dot(p, fwd)); float r = Vector3.Dot(p, right); rIn = Mathf.Min(rIn, r); rOut = Mathf.Max(rOut, r); }
            float endTop = float.MinValue; foreach (var p in pv) if (Vector3.Dot(p, fwd) > fMax - 0.02f) endTop = Mathf.Max(endTop, p.y);
            float gEnd = float.MaxValue;
            foreach (float a in new[] { 0.1f, 0.5f, 0.9f })
            { Vector3 q = right * Mathf.Lerp(rIn, rOut, a) + fwd * (fMax + 0.02f); gEnd = Mathf.Min(gEnd, footAt(q.x, q.z)); }
            rep.endSink = gEnd - endTop;
            if (rep.endSink >= sink - 1e-3f) { rep.sinkOk = true; break; }
            if (k > maxExt) break;
            var go = Place(pathOf(-k, depths[0]), prev.transform.position, prev.transform.eulerAngles.y, Vector3.one, parent, name + "_x" + k);
            if (go == null) { warn.Add(name + ": 坂下へ継ぐ袖の駒が無い " + pathOf(-k, depths[0])); break; }
            var nv = Body(go.transform, 4000, true);
            float fMin = float.MaxValue, rIn2 = float.MaxValue;
            foreach (var p in nv) { fMin = Mathf.Min(fMin, Vector3.Dot(p, fwd)); rIn2 = Mathf.Min(rIn2, Vector3.Dot(p, right)); }
            float stTop = float.MinValue; foreach (var p in nv) if (Vector3.Dot(p, fwd) < fMin + 0.02f) stTop = Mathf.Max(stTop, p.y);
            go.transform.position += fwd * (fMax - fMin) + right * (rIn - rIn2) + Vector3.up * (endTop - stTop);
            res.Add(go); rep.ext++; prev = go;
        }
        if (!rep.sinkOk)
            warn.Add(name + ": ⛔ 坂下の端の小口が地盤 − " + sink.ToString("F2") + " まで沈まない(沈み " + rep.endSink.ToString("F2") + "・継いだ " + rep.ext + ")");
        return res;
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
    public static Vector2 ExtentAlong(GameObject g, Vector3 outDir)
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
        // ⭐ 斜めに交わる端(EDO-0430 2026-09-26 女坂の足): 相手の面が一枚の平面で、端の走り Z に対して角を持つ
        public bool angled;     // 離れが Z の一次式に乗った(一枚の平面)⇒ d・deg・nori で切れる
        public float deg;       // 面の平面の線が段の走り(Z)となす角[°]。+ は坂下(+Z)ほど外へ開く
        public float nori;      // 面の法(水平/鉛直)。+ は上ほど外
        public float resid;     // 一次式からの外れの最大(斜めでも二つの面ならここが大きい)
        public bool noriKnown;  // 真っ直ぐに当たる端でも法を測れた(nori に入る)
        public bool stretch;    // 面が端の外に出る所がある(駒を伸ばしてから切る ── 脇に袖が在れば袖へめり込む)
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
        if (r.spread > spreadTol) { r.mixed = true; FitObliqueEnd(flatDan, od, f, ez, keri, yMid, walls, ref r); return r; }
        r.d = -hit[hit.Count / 2];
        // ⭐ 相手の面の法を測る(2026-09-26)── 焼く駒の既定は法 1:0.25(野面の返し)。鉛直の城の石垣に当たる端を 1:0.25 で切ると、
        //   蹴上の下端で 0.025 の口が開いた(郭の階の段 2・3 の +X × TW_Gusho_E)。当たった標本ごとに ± 0.35 蹴上の高さの離れの差を取る。
        {
            float dy = keri * 0.35f;
            var hiO = EndOffsets(flatDan, od, f, al, yMid + dy, walls, maxIn, maxOut);
            var loO = EndOffsets(flatDan, od, f, al, yMid - dy, walls, maxIn, maxOut);
            var ns = new List<float>();
            for (int k = 0; k < N; k++) if (!float.IsNaN(offs[k]) && !float.IsNaN(hiO[k]) && !float.IsNaN(loO[k])) ns.Add((hiO[k] - loO[k]) / (2f * dy));
            if (ns.Count > 0) { ns.Sort(); r.nori = ns[ns.Count / 2]; r.noriKnown = true; }
        }
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

    /// <summary>**端と斜めに交わる相手の面を一枚の平面として測る**(2026-09-26・EDO-0430 女坂の足 × 前庭の南の土留めの隅)。
    /// 離れが割れた端(<see cref="MeasureStepEndOnBatter"/> の mixed)で、窓を広げて(内 1.5m・外 1.0m)端に沿って 25 点 × 3 高さ
    /// (蹴上の中ほど ± 0.35 蹴上)の光線を打ち、蹴上の中ほどの離れを Z の一次式へ当てる。外れの最大 ≤ 0.01 なら一枚の平面:
    /// d = −(Z = 0 の離れ)・deg = atan(傾き)・nori = 高さの差の傾き(<see cref="EdoAssets.Own.DanKiriEnd(float,float,float)"/> の綴り)。
    /// 外れが大きければ相手の隅(二つの面)に当たっている ⇒ mixed のまま(一枚の面では切れない)。⭐ 面で測る。⛔ ピボットで合わせない
    /// (Z は仮に芯へ据えた駒の局所 ── 踏面の中心の線が Z = 0)。
    /// 当たる先: 石段の段石の端 × 走りに斜めに交わる土留め・隅の駒(山王 女坂の段 0・1)。</summary>
    static void FitObliqueEnd(GameObject flatDan, Vector3 od, Vector3 f, Vector2 ez, float keri, float yMid, IList<GameObject> walls, ref BatterEnd r)
    {
        const int N = 25; var al = new float[N];
        for (int k = 0; k < N; k++) al[k] = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / (N - 1);
        float dy = keri * 0.35f;
        var m = EndOffsets(flatDan, od, f, al, yMid, walls, 1.5f, 1.0f);
        var hi = EndOffsets(flatDan, od, f, al, yMid + dy, walls, 1.5f, 1.0f);
        var lo = EndOffsets(flatDan, od, f, al, yMid - dy, walls, 1.5f, 1.0f);
        double sx = 0, sy = 0, sxx = 0, sxy = 0; int n = 0;
        for (int k = 0; k < N; k++) if (!float.IsNaN(m[k])) { sx += al[k]; sy += m[k]; sxx += al[k] * al[k]; sxy += al[k] * m[k]; n++; }
        if (n < 7) return;
        double den = n * sxx - sx * sx; if (System.Math.Abs(den) < 1e-9) return;
        float c1 = (float)((n * sxy - sx * sy) / den), c0 = (float)((sy - c1 * sx) / n);
        float res = 0f; for (int k = 0; k < N; k++) if (!float.IsNaN(m[k])) res = Mathf.Max(res, Mathf.Abs(m[k] - (c0 + c1 * al[k])));
        r.resid = res;
        if (res > 0.01f) return;                        // 二つの面(相手の隅)── 一枚の面では切れない
        float ns = 0f; int nn = 0;
        for (int k = 0; k < N; k++) if (!float.IsNaN(hi[k]) && !float.IsNaN(lo[k])) { ns += (hi[k] - lo[k]) / (2f * dy); nn++; }
        r.nori = nn > 0 ? ns / nn : 0f; if (Mathf.Abs(r.nori) < 0.005f) r.nori = 0f;
        r.mixed = false; r.angled = true;
        r.d = -c0; r.deg = Mathf.Atan(c1) * Mathf.Rad2Deg;
        // 面が端の外に出る所(踏面の上・蹴上の下の高さで Z の両端)
        float top = yMid + keri * 0.5f, bot = yMid - keri * 0.5f;
        foreach (float z in new[] { ez.x, ez.y }) foreach (float y in new[] { top, bot })
            if (c0 + c1 * z + r.nori * (y - yMid) > 0.002f) r.stretch = true;
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

    /// <summary>**袖の背と野面の相手の離れを石の出の包絡で測る**(2026-09-26・EDO-0437 第3巡)。<see cref="MeasureSodeBackOnBatter"/> と同じ光線を
    /// 5 点 × 5 高さ(袖の局所 Y 0.03〜天端の下)で打ち、各点の口から法 <paramref name="nori"/> の傾きを引いて Yc へ戻した値の**最小**を返す
    /// (= 背を法 nori で切ったとき、どの石にもめり込まない最大の e)。<paramref name="spread"/> = Yc の行の幅。
    /// 当たる先: 石段の袖の背 × 野面の乱積みの隅の駒・返し(山王 参道の階の袖 × 前庭の北の切り込み)。</summary>
    public static float MeasureSodeBackEnvelope(GameObject sode, float keri, IList<GameObject> walls, float nori, out float spread, float maxOut = 0.6f,
                                                System.Func<float, float, float> visAt = null)
    {
        spread = 0f;
        Vector3 f = sode.transform.forward; f.y = 0f; f.Normalize();
        Vector3 rt = sode.transform.right; rt.y = 0f; rt.Normalize();
        float sy = sode.transform.lossyScale.y, yc = EdoAssets.Own.SodeNoriYc(keri);
        var own = new List<GameObject> { sode }; var ez = ExtentAlong(sode, f);
        float best = float.NaN; var row = new List<float>();
        // ⭐ 密に(9 × 9)── 5 × 5 では野面の石の出の間を抜け、据えた後に 0.05 入った(参道の階の東の袖 × 切り込みの隅・2026-09-26)
        //   ⭐ 見える地表(<paramref name="visAt"/>)が渡されたら、袖の底から天端まで打ち、当たった点が見える地表 + 0.02 より上の物だけ数える
        //   (2026-09-26 EDO-0437 第6巡)── 踏面の上だけ(局所 Y 0.03〜)を打つと、踏面より下で見え面の外へ出ている背(外の地表 11.98・
        //   踏面 13.75)が隅の石へ 0.035 入ったまま残った(参道の階の東の袖 001f × 前庭の北東の隅 N_kado2)。
        float y0 = 0.03f;
        if (visAt != null) { float bmin = float.MaxValue; foreach (var v in Body(sode.transform, 999999, true)) bmin = Mathf.Min(bmin, v.y); y0 = (bmin - sode.transform.position.y) / Mathf.Max(1e-4f, sy) + 0.03f; }
        var yls = new List<float>(); int nq = visAt != null ? 17 : 9;
        for (int q = 0; q < nq; q++) yls.Add(Mathf.Lerp(y0, 0.30f + keri - 0.02f, q / (float)(nq - 1))); yls.Add(yc);
        foreach (float yl in yls)
            for (int ai = 0; ai < 9; ai++)
            {
                float a = Mathf.Lerp(-0.28f, 0.28f, ai / 8f);
                Vector3 o = sode.transform.position + rt * a + f * ((ez.x + ez.y) * 0.5f); o.y = sode.transform.position.y + yl * sy;
                float b = RayFarthest(own, o, -f, 5f); if (float.IsNaN(b)) continue;
                float w = RayToBodies(walls, o, -f, b + maxOut); if (float.IsNaN(w)) continue;
                if (visAt != null && Mathf.Abs(yl - yc) > 1e-4f) { Vector3 hp = o - f * w; float g = visAt(hp.x, hp.z); if (!float.IsNaN(g) && o.y <= g + 0.02f) continue; }
                float v = (w - b) - nori * (yl - yc);
                if (Mathf.Abs(yl - yc) < 1e-4f) row.Add(w - b);
                if (float.IsNaN(best) || v < best) best = v;
            }
        if (row.Count > 1) { row.Sort(); spread = row[row.Count - 1] - row[0]; }
        return best;
    }

    /// <summary>**段石の端と野面の相手の包絡の切り d**(2026-09-26・EDO-0437 第3巡)。平らな段石 <paramref name="flatDan"/> の端 <paramref name="side"/> に沿って
    /// 25 点 × 蹴上の丈を 0.03 刻み で光線を打ち、相手の面の当たり o(+ = 口)から d = max(nori·(y − 蹴上の中ほど) − o)
    /// (法 <paramref name="nori"/> の面で最も深く入る石まで)。⭐ 数えるのは**見える当たり**だけ(当たった点が設計面 <paramref name="visAt"/> + 0.02 より上 ──
    /// 地表の下で相手の法の足へ入るのは正しい納め)。<paramref name="straddle"/> = 端の一部の標本が相手に一度も当たらない(隅と袖に跨る ⇒ 全長では切れない)。
    /// 見える当たりが無ければ NaN。当たる先: 石段の段石 × 野面の乱積みの返し・隅の駒(山王 参道の階)。</summary>
    public static float EnvelopeCut(GameObject flatDan, int side, float keri, IList<GameObject> walls, float nori, System.Func<float, float, float> visAt, out bool straddle)
    {
        straddle = false;
        Vector3 f = flatDan.transform.forward; f.y = 0f; f.Normalize();
        Vector3 od = flatDan.transform.right * side; od.y = 0f; od.Normalize();
        float top = float.MinValue; foreach (var v in Body(flatDan.transform, 999999, true)) top = Mathf.Max(top, v.y);
        float yMid = top - keri * 0.5f; var ez = ExtentAlong(flatDan, f); float xe = ExtentAlong(flatDan, od).y;
        const int N = 25; float d = float.NaN; int miss = 0, hitCols = 0;
        for (int k = 0; k < N; k++)
        {
            float a = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / (N - 1); bool any = false;
            for (float y = top - 0.01f; y > top - keri; y -= 0.03f)
            {
                Vector3 o = flatDan.transform.position + od * (xe - 0.5f) + f * a; o.y = y;
                float h = RayToBodies(walls, o, od, 0.6f); if (float.IsNaN(h)) continue;
                any = true; Vector3 hp = o + od * h;
                if (visAt != null) { float g = visAt(hp.x, hp.z); if (!float.IsNaN(g) && y <= g + 0.02f) continue; }
                float c = nori * (y - yMid) - (h - 0.5f); if (float.IsNaN(d) || c > d) d = c;
            }
            if (any) hitCols++; else miss++;
        }
        straddle = hitCols > 0 && miss > 0;
        return d;
    }

    /// <summary>**跨ぐ端の隅の駒のもう一面を野面の包絡で測る**(2026-09-26・EDO-0437 第4巡)。<see cref="EnvelopeCut(GameObject,int,float,IList{GameObject},float,System.Func{float,float,float},out bool)"/> が
    /// 跨ぐ(一部の列だけ当たる)と言った端について、当たる列が一続きで片方の端に寄っていれば、当たらない側から当たる側へ
    /// 端の内(小口と包絡の切りの面 <paramref name="dEnv"/> の間)を 3 点 × 蹴上の丈 0.03 刻みで打ち、**見える当たり**のうち最も
    /// 当たらない側へ出ている石の面を za(段の局所・<see cref="MeasureStepEndOnBatter"/> と同じ枠)に取る。uphill = 当たる列が −Z 側から始まる。
    /// 形が決まらない(当たる列が飛び飛び・真ん中だけ・もう一面に当たらない)なら false。⭐ 面で測る(頂点・ピボットで合わせない)。
    /// 当たる先: 石段の段石 × 野面の乱積みの隅の駒と袖に跨る端(山王 参道の階の段 1。女坂・郭の階の段も同じ枝を通る)。</summary>
    public static bool EnvelopeStraddle(GameObject flatDan, int side, float keri, IList<GameObject> walls, float dEnv, System.Func<float, float, float> visAt, out bool uphill, out float za)
    {
        uphill = false; za = float.NaN;
        Vector3 f = flatDan.transform.forward; f.y = 0f; f.Normalize();
        Vector3 od = flatDan.transform.right * side; od.y = 0f; od.Normalize();
        float top = float.MinValue; foreach (var v in Body(flatDan.transform, 999999, true)) top = Mathf.Max(top, v.y);
        var ez = ExtentAlong(flatDan, f); float xe = ExtentAlong(flatDan, od).y;
        const int N = 25; var hitCol = new bool[N]; int first = -1, last = -1, cnt = 0;
        for (int k = 0; k < N; k++)
        {
            float a = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / (N - 1);
            for (float y = top - 0.01f; y > top - keri; y -= 0.03f)
            {
                Vector3 o = flatDan.transform.position + od * (xe - 0.5f) + f * a; o.y = y;
                if (!float.IsNaN(RayToBodies(walls, o, od, 0.6f))) { hitCol[k] = true; break; }
            }
            if (hitCol[k]) { cnt++; if (first < 0) first = k; last = k; }
        }
        if (cnt == 0 || cnt == N || last - first + 1 != cnt || (first != 0 && last != N - 1)) return false;
        uphill = first == 0;
        Vector3 dir = uphill ? -f : f; float s0 = uphill ? ez.y + 0.05f : ez.x - 0.05f;
        float hMin = float.NaN;
        //   欠く奥行(小口から包絡の切りの面まで)を 0.01 刻み × 蹴上の丈を 0.01 刻みで打つ ── 野面の石は数 cm ごとに出入りするので、
        //   粗い 3 点では最も出た石を見落とし za が 0.06 甘く出た(2026-09-26 参道の階の段 1 −X・部材方の 0.005 刻みの実測と比べて)
        for (float xin = 0.005f; xin <= Mathf.Max(0.01f, dEnv + 0.015f); xin += 0.01f)
            for (float y = top - 0.01f; y > top - keri; y -= 0.01f)
            {
                Vector3 o = flatDan.transform.position + od * (xe - xin) + f * s0; o.y = y;
                float h = RayToBodies(walls, o, dir, ez.y - ez.x + 0.2f); if (float.IsNaN(h)) continue;
                Vector3 hp = o + dir * h;
                if (visAt != null) { float g = visAt(hp.x, hp.z); if (!float.IsNaN(g) && y <= g + 0.02f) continue; }
                if (float.IsNaN(hMin) || h < hMin) hMin = h;
            }
        if (float.IsNaN(hMin)) return false;
        za = uphill ? s0 - hMin : s0 + hMin;
        return true;
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

    /// <summary>**相手の石の形に沿わせて焼いた駒へ、据えを変えずに差し替える**(2026-09-26・EDO-0437 第11巡)。<paramref name="pieces"/> の駒ごとに
    /// <paramref name="fitPathOf"/> が返す資産が在れば、同じ位置・向き・縮尺(<see cref="SwapPart"/>)で差し替える。沿わせた駒の形は据えの従属値
    /// (焼いた時の配置と相手の位置が前提)── ⛔ 差し替えた駒に端の突き付け・<see cref="ResizeEnd"/> を掛けない・相手を退けない(<see cref="YieldWallsToSteps"/> の fixedNear)。
    /// 返り値 = 旧 → 新。資産が無い駒は触らない。当たる先: 野面の返し・隅石に端・背が接する石段の段石と袖(山王 参道の階 段 1〜4・袖 W1/E1)。</summary>
    public static Dictionary<GameObject, GameObject> SwapToFitted(IList<GameObject> pieces, System.Func<GameObject, string> fitPathOf, System.Text.StringBuilder sb)
    {
        var map = new Dictionary<GameObject, GameObject>();
        foreach (var g in pieces)
        {
            if (g == null) continue;
            string p = fitPathOf(g); if (string.IsNullOrEmpty(p) || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) continue;
            var mf = g.GetComponentInChildren<MeshFilter>(); string cur = mf != null && mf.sharedMesh != null ? UnityEditor.AssetDatabase.GetAssetPath(mf.sharedMesh) : "";
            string nm = g.name, from = System.IO.Path.GetFileNameWithoutExtension(cur);
            var ng = cur == p ? g : SwapPart(g, p);
            map[g] = ng;
            if (sb != null) sb.AppendLine("    " + nm + " → " + System.IO.Path.GetFileNameWithoutExtension(p) + "(相手の石に沿わせた駒・据えは " + from + " のまま・突き付けを掛けない)");
        }
        return map;
    }

    /// <summary>**段石の端に脇から接する土留めの駒を、その段に合わせて焼いた駒へ、据えを変えずに差し替える**(2026-09-27・EDO-0437 r14)。
    /// 相手は実メッシュで選ぶ: 段 <paramref name="step"/> の局所で、端の外 |x| ∈ [幅/2 − 0.05, 幅/2 + <paramref name="reach"/>]・段の丈と走りの中に
    /// 頂点を持つ駒(<paramref name="walls"/> のうち)。脇 = 局所 X の符号('W' = −X / 'E' = +X)。<paramref name="fitPathOf"/>(駒・脇)が返す資産が在り、
    /// その名が今の部材の名 + "_" で始まる(= 今の部材から焼いた物)ときだけ <see cref="SwapPart"/> で差し替える(位置・向き・縮尺はそのまま)。
    /// ⛔ 名で駒を指さない(測って選ぶ)。返り値 = 旧 → 新(呼び手は群の一覧を差し替える)。
    /// 当たる先: 野面の返しが最上段の端に脇から接する所(山王 参道の階 段 4 × 前庭の天端 012f/027f)。</summary>
    public static Dictionary<GameObject, GameObject> SwapWallsBesideStep(GameObject step, IList<GameObject> walls, System.Func<GameObject, char, string> fitPathOf,
                                                                         System.Text.StringBuilder sb, float reach = 0.30f)
    {
        var map = new Dictionary<GameObject, GameObject>();
        if (step == null) return map;
        var W2L = step.transform.worldToLocalMatrix; var mf0 = step.GetComponentInChildren<MeshFilter>(); if (mf0 == null || mf0.sharedMesh == null) return map;
        var M0 = W2L * mf0.transform.localToWorldMatrix; var lb = new Bounds(M0.MultiplyPoint3x4(mf0.sharedMesh.vertices[0]), Vector3.zero);
        foreach (var v in mf0.sharedMesh.vertices) lb.Encapsulate(M0.MultiplyPoint3x4(v));
        float half = Mathf.Max(-lb.min.x, lb.max.x);
        var sbb = RB(step); sbb.Expand(reach + 0.1f);
        foreach (var w in new List<GameObject>(walls))
        {
            if (w == null || !w.activeInHierarchy || !RB(w).Intersects(sbb)) continue;
            int side = 0;
            foreach (var v in Body(w.transform, 999999, true))
            {
                var l = W2L.MultiplyPoint3x4(v);
                if (l.y < lb.min.y || l.y > lb.max.y + 0.02f || l.z < lb.min.z || l.z > lb.max.z) continue;
                float ax = Mathf.Abs(l.x); if (ax < half - 0.05f || ax > half + reach) continue;
                side = l.x < 0f ? -1 : 1; break;
            }
            if (side == 0) continue;
            string p = fitPathOf(w, side < 0 ? 'W' : 'E'); if (string.IsNullOrEmpty(p) || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) continue;
            var mf = w.GetComponentInChildren<MeshFilter>(); string cur = mf != null && mf.sharedMesh != null ? UnityEditor.AssetDatabase.GetAssetPath(mf.sharedMesh) : "";
            string curName = System.IO.Path.GetFileNameWithoutExtension(cur), newName = System.IO.Path.GetFileNameWithoutExtension(p);
            if (cur == p) { map[w] = w; continue; }
            if (!newName.StartsWith(curName + "_")) continue;
            string nm = w.name; var ng = SwapPart(w, p); map[w] = ng;
            if (sb != null) sb.AppendLine("    " + nm + "(段 " + step.name + " の" + (side < 0 ? "−X" : "+X") + " の端に接する)→ " + newName + "(据えは " + curName + " のまま)");
        }
        return map;
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
        System.Func<GameObject, int, string> flatSodePath, System.Func<GameObject, int, float, string> noriPath, System.Text.StringBuilder sb, float tol = 0.003f,
        float envNori = float.NaN, System.Func<GameObject, float> sodeEnvNori = null, System.Func<float, float, float> envVisAt = null,
        System.Func<GameObject, bool> envWall = null)
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
            System.Func<BatterEnd, string> say = e => e.angled
                ? "d " + e.d.ToString("+0.000;-0.000", inv) + " 角 " + e.deg.ToString("+0.000;-0.000", inv) + "°" + (e.nori != 0f ? " 法 " + e.nori.ToString("F3", inv) : "") + " 外れ " + e.resid.ToString("F3", inv)
                : e.mixed ? "幅 " + e.spread.ToString("F3", inv) + (e.resid > 0f ? "・一次式の外れ " + e.resid.ToString("F3", inv) + "(二つの面)" : e.spread <= 0.031f ? "(当たりが飛び飛び)" : "")
                : e.touched ? "d " + e.d.ToString("+0.000;-0.000", inv) + (e.noriKnown ? " 法 " + e.nori.ToString("F3", inv) : "") : "当たらず";
            // ⭐ 相手が野面の乱積み(法 <paramref name="envNori"/>)で当たりが割れる端は、石の出の**包絡**で切る(2026-09-26・EDO-0437 第3巡)──
            //   野面の石は ±0.07 出入りし、一枚の面に乗らない(参道の階の段 2 の −X が切り込みの隅の駒へ −0.086 入った)。
            //   端に沿って 13 点 × 3 高さの離れから、法の面で最も深く入る石まで切る d(<see cref="EnvelopeCut"/>)。石の凹みの口は野面の納めで残る。
            string envL = null, envR = null; float envDL = float.NaN, envDR = float.NaN;
            // ⭐ 相手が野面なら、中ほどの一本の測りが割れていなくても包絡で切る(2026-09-26・EDO-0437 第4巡)── 中ほどの中央値は石の出入りを
            //   均して d 0 と読み、段 3 の +X へ隅の石が 0.08〜0.11 入ったまま(段 0・段 4 は中ほどで当たらず測りもしなかった)。
            //   野面の相手(<paramref name="envWall"/>)だけを相手にして、見える当たりが在る端はすべて包絡で決める。
            var envWalls = walls;
            if (envWall != null) { envWalls = new List<GameObject>(); foreach (var w in walls) if (w != null && envWall(w)) envWalls.Add(w); }
            if (!float.IsNaN(envNori) && envWalls.Count > 0)
            {
                foreach (int side in new[] { -1, 1 })
                {
                    var e = side < 0 ? eL : eR; if (envWall == null && !e.mixed) continue;
                    var pr = Place(flat, StepAxis(dg0.transform), dg0.transform.eulerAngles.y, Vector3.one, dg0.transform.parent, "__probe_dan");
                    float dEnv; bool strad;
                    try { dEnv = EnvelopeCut(pr, side, keri, envWalls, envNori, envVisAt, out strad); } finally { Object.DestroyImmediate(pr); }
                    if (envWall != null && float.IsNaN(dEnv))
                    {   // 野面に見える当たりが無い ⇒ 割れた中ほどの測りは地表の下の石を拾っただけ ── 切らない(包絡と同じ物差し)。割れていなければ従来の測り
                        if (e.mixed) { if (side < 0) { eL.mixed = false; eL.touched = false; } else { eR.mixed = false; eR.touched = false; } }
                        continue;
                    }
                    if (side < 0) eL.touched = true; else eR.touched = true;
                    if (strad && !float.IsNaN(dEnv) && dEnv > 0.002f)
                    {   // ⭐ 隅と袖に跨る端(EDO-0437 第4巡): 全長で切ると袖との間に d の口が開く ⇒ 跨ぐ端の法つきの型
                        //   (<see cref="EdoAssets.Own.DanKiriEnd(float,float,bool,float)"/>)で、隅の駒のもう一面 za から当たる側だけを欠く。
                        //   d・za は見える当たりの包絡 + 余り 0.015 / 0.010(当たらない側へ)── 焼いた組は NearestBaked が 0.015 以内で引く。
                        bool upS; float zaS; bool okS;
                        var pz = Place(flat, StepAxis(dg0.transform), dg0.transform.eulerAngles.y, Vector3.one, dg0.transform.parent, "__probe_dan");
                        try { okS = EnvelopeStraddle(pz, side, keri, envWalls, dEnv, envVisAt, out upS, out zaS); } finally { Object.DestroyImmediate(pz); }
                        if (!okS)
                        {
                            sb.AppendLine("    ⚠ " + label + " " + dg0.name + " の" + (side < 0 ? "−X" : "+X") + ": 野面の隅と袖に跨り、見える当たりが " + dEnv.ToString("F3", inv) +
                                          "m 入るが、当たる列が一続きでない・隅のもう一面が測れない ── 差し替えない");
                            continue;
                        }
                        float zaW = zaS + (upS ? 0.010f : -0.010f);
                        string spS = EdoAssets.Own.DanKiriEnd(dEnv + 0.015f, zaW, upS, envNori);
                        if (side < 0) { envL = spS; envDL = dEnv; eL.mixed = false; eL.straddle = true; eL.uphill = upS; eL.za = zaW; eL.d = dEnv; }
                        else { envR = spS; envDR = dEnv; eR.mixed = false; eR.straddle = true; eR.uphill = upS; eR.za = zaW; eR.d = dEnv; }
                        continue;
                    }
                    string sp = float.IsNaN(dEnv) || dEnv <= 0.002f ? EdoAssets.Own.DanKiriNone : EdoAssets.Own.DanKiriEnd(dEnv + 0.015f, 0f, envNori);
                    if (side < 0) { envL = sp; envDL = dEnv; eL.mixed = false; } else { envR = sp; envDR = dEnv; eR.mixed = false; }
                }
            }
            if (!eL.touched && !eR.touched) continue;
            if (eL.mixed || eR.mixed)
            {
                sb.AppendLine("    ⚠ " + label + " " + dg0.name + ": 端の当たりが割れ、一枚の面で切る形が決まらない(−X " + say(eL) + " / +X " + say(eR) + ")── 差し替えない");
                continue;
            }
            // ⭐ 斜めの面が端の外へ出る所は、焼く駒が小口を伸ばしてから切る(build_sanno_buzai.py dan_kiri)── 脇に袖が据わっていれば
            //   伸ばした所が袖へめり込む。⇒ 差し替えず・焼く一覧にも載せず ⚠(袖と相手の取り合いが先)。
            bool blocked = false;
            foreach (int side in new[] { -1, 1 })
            {
                var e = side < 0 ? eL : eR; if (!e.angled || !e.stretch) continue;
                var pr = Place(flat, StepAxis(dg0.transform), dg0.transform.eulerAngles.y, Vector3.one, dg0.transform.parent, "__probe_dan");
                try
                {
                    Vector3 f0 = pr.transform.forward; f0.y = 0f; f0.Normalize();
                    Vector3 od0 = pr.transform.right * side; od0.y = 0f; od0.Normalize();
                    float top0 = float.MinValue; foreach (var v in Body(pr.transform, 999999, true)) top0 = Mathf.Max(top0, v.y);
                    var ez0 = ExtentAlong(pr, f0); var al0 = new float[9];
                    for (int k = 0; k < 9; k++) al0[k] = ez0.x + 0.02f + (ez0.y - ez0.x - 0.04f) * k / 8f;
                    var so = EndOffsets(pr, od0, f0, al0, top0 - keri * 0.5f, sodes, 0.05f, 0.05f);
                    foreach (var x in so) if (!float.IsNaN(x) && Mathf.Abs(x) < 0.03f) { blocked = true; break; }
                }
                finally { Object.DestroyImmediate(pr); }
            }
            if (blocked)
            {
                sb.AppendLine("    ⚠ " + label + " " + dg0.name + ": 端が相手の面と斜めに交わる(−X " + say(eL) + " / +X " + say(eR) +
                              ")が、面の出る側に袖が据わっている ── 伸ばして切ると袖へめり込むので差し替えない(袖と相手の取り合いが先)");
                continue;
            }
            // 法の読み: 焼く駒の既定 1:0.25 から 0.03 以内なら既定の綴り(d / d·za)、鉛直(|法| < 0.03)で食い込み 0 なら切らない、
            //   それ以外の真っ直ぐな端は斜め切りの綴りに角 0 と測った法を載せる。跨ぐ端で法が既定でないものは焼く型が無い ⇒ ⚠。
            System.Func<BatterEnd, bool> stdNori = e => !e.noriKnown || Mathf.Abs(e.nori - 0.25f) <= 0.03f;
            System.Func<BatterEnd, bool> vertFlush = e => e.noriKnown && Mathf.Abs(e.nori) < 0.03f && Mathf.Abs(e.d) < 0.002f;
            System.Func<BatterEnd, string> spec = e => !e.touched || (!e.straddle && !e.angled && Mathf.Abs(e.d) < 0.002f && stdNori(e)) || (!e.angled && vertFlush(e)) ? EdoAssets.Own.DanKiriNone
                : e.angled ? EdoAssets.Own.DanKiriEnd(e.d, e.deg, e.nori)
                : e.straddle ? (stdNori(e) ? EdoAssets.Own.DanKiriEnd(e.d, e.za, e.uphill) : null)
                : stdNori(e) ? EdoAssets.Own.DanKiriEnd(e.d) : EdoAssets.Own.DanKiriEnd(e.d, 0f, Mathf.Abs(e.nori) < 0.005f ? 0f : e.nori);
            string sL = envL ?? spec(eL), sR = envR ?? spec(eR);
            if (sL == null || sR == null)
            {
                sb.AppendLine("    ⚠ " + label + " " + dg0.name + ": 端が隅に跨り、相手の法が焼く型の 1:0.25 でない(−X 法 " + eL.nori.ToString("F3", inv) + " / +X 法 " + eR.nori.ToString("F3", inv) + ")── 差し替えない");
                continue;
            }
            if (sL == EdoAssets.Own.DanKiriNone && sR == EdoAssets.Own.DanKiriNone) continue;
            string want = kiriPath(i, sL, sR);
            // 包絡で切る端は、焼いた d のうち包絡以上で +0.03 以内(めり込まない側へ丸める)
            bool envUsed = (envL != null && envL != EdoAssets.Own.DanKiriNone) || (envR != null && envR != EdoAssets.Own.DanKiriNone);
            string got = EdoAssets.Own.NearestBaked(want, envUsed ? 0.015f : tol);
            if (envUsed)
                sb.AppendLine("    " + label + " " + dg0.name + ": 野面の相手へ石の出の包絡で切る(−X " + (float.IsNaN(envDL) ? say(eL) : "包絡 d " + envDL.ToString("+0.000;-0.000", inv)) +
                              " / +X " + (float.IsNaN(envDR) ? say(eR) : "包絡 d " + envDR.ToString("+0.000;-0.000", inv)) + " 法 " + envNori.ToString("F2", inv) + ")→ " + (got == null ? "焼いていない" : System.IO.Path.GetFileNameWithoutExtension(got)));
            if (got == null)
            {
                need.Add(i + " " + (i % 2 == 0 ? "a" : "b") + " L" + (sL == EdoAssets.Own.DanKiriNone ? "-" : sL) + " R" + (sR == EdoAssets.Own.DanKiriNone ? "-" : sR));
                continue;
            }
            // 平らな段石を芯へ戻してから差し替える(突き付けの縮尺を持ち越さない)
            var t0 = dg0.transform; Vector3 ax = StepAxis(t0);
            // ⚠ 印 `_axis` は駒の子 ── 縮尺と位置を戻すと一緒に動く。世界の芯へ戻す(2026-09-26 郭の階で印が 0.117 ずれ、次の巡の測りが狂った)
            var axT0 = t0.Find(AXIS_MARK);
            t0.localScale = Vector3.one; t0.position = ax;
            if (axT0 != null) axT0.position = ax;
            var ng = SwapPart(dg0, got); done.Add(ng); nDan++;
            // 据えた後: 端に沿って 13 点 × 3 高さ(踏面の下・中ほど・蹴上の下端の上)で、駒の外面から相手(土留め+袖)までを測る
            var others = new List<GameObject>(walls); foreach (var s in sodes) if (s != null) others.Add(s);
            Vector3 f = ng.transform.forward; f.y = 0f; f.Normalize();
            float top = float.MinValue; foreach (var v in Body(ng.transform, 999999, true)) top = Mathf.Max(top, v.y);
            var ez = ExtentAlong(ng, f); float gMax = 0f, bMax = 0f, gGroove = 0f; int nS = 0, nGroove = 0;
            foreach (int side in new[] { -1, 1 })
            {
                var e = side < 0 ? eL : eR; if (!e.touched) continue;
                Vector3 od = ng.transform.right * side; od.y = 0f; od.Normalize();
                float xEnd = ExtentAlong(ng, od).y;
                foreach (float yy in new[] { top - 0.02f, top - keri * 0.5f, top - keri + 0.02f })
                {
                    // ⭐ 口は端に沿って三標本(≥ 0.08m)続く物だけ数える ── 袖の石の目地(幅 0.02 の溝・斜めに走る)は一〜二標本だけ
                    //   0.012〜0.019 の偽の口を出す(2026-09-26 参道の階 段 1・郭の階 段 3。面一は前後の標本で 0.000)。短い口は目地として別に数える。
                    var row = new float[13];
                    for (int k = 0; k < 13; k++)
                    {
                        float s = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / 12f;
                        Vector3 o = ng.transform.position + od * (xEnd - 0.6f) + f * s; o.y = yy;
                        row[k] = GapAlong(ng, others, o, od, 0.10f); if (float.IsNaN(row[k])) continue;
                        // 包絡で切った端は、包絡と同じく**見える当たり**だけ数える(地表の下で相手の法の足へ入るのは正しい納め ── 切りと検めの物差しを揃える)
                        if (!float.IsNaN(side < 0 ? envDL : envDR) && envVisAt != null)
                        {
                            Vector3 hp = o + od * (0.6f + row[k]); float gv = envVisAt(hp.x, hp.z);
                            if (!float.IsNaN(gv) && yy <= gv + 0.02f) { row[k] = float.NaN; continue; }
                        }
                        nS++; if (row[k] < 0) bMax = Mathf.Max(bMax, -row[k]);
                    }
                    for (int k = 0; k < 13; k++)
                    {
                        if (float.IsNaN(row[k]) || row[k] <= 0f) continue;
                        // 三つ続き(≥ 0.08m)の中に居るか ── 斜めの目地は浅い角で二標本に掛かる(郭の階 段 3 の +X 下端 0.012/0.006)
                        System.Func<int, bool> op = j => j >= 0 && j < 13 && !float.IsNaN(row[j]) && row[j] > 0.005f;
                        bool nb = (op(k - 1) && op(k + 1)) || (op(k - 2) && op(k - 1)) || (op(k + 1) && op(k + 2));
                        if (row[k] <= 0.005f || nb) gMax = Mathf.Max(gMax, row[k]); else { nGroove++; gGroove = Mathf.Max(gGroove, row[k]); }
                    }
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
                          "(測った −X " + say(eL) + (eL.straddle ? " za " + eL.za.ToString("F3", inv) : "") +
                          " / +X " + say(eR) + (eR.straddle ? " za " + eR.za.ToString("F3", inv) : "") +
                          ")/ 据えた後 口 " + gMax.ToString("F3") + " めり込み " + bMax.ToString("F3") + "(当たり " + nS + ")" +
                          (nGroove > 0 ? "・袖の目地の短い溝 " + nGroove + " 点(最大 " + gGroove.ToString("F3") + ")は口に数えない" : "") +
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
            // ⭐ 相手が野面(法 sNori)なら石の出の包絡で e を取り、めり込まない側へ 0.05 に切り下げる(2026-09-26・EDO-0437 第3巡)
            float sNori = sodeEnvNori != null ? sodeEnvNori(sg0) : float.NaN; bool env = !float.IsNaN(sNori);
            try { e = env ? MeasureSodeBackEnvelope(probe, keri, walls, sNori, out spread, 0.6f, envVisAt) : MeasureSodeBackOnBatter(probe, keri, walls, out spread); }
            catch { Object.DestroyImmediate(probe); throw; }
            Vector3 flatPos = probe.transform.position;
            Object.DestroyImmediate(probe);
            if (float.IsNaN(e)) continue;
            if (spread > (env ? 0.50f : 0.031f)) { sb.AppendLine("    ⚠ " + label + " " + sg0.name + " の背: 相手の面が斜めに交わる(幅 " + spread.ToString("F3") + ")── 差し替えない"); continue; }
            float snap = env ? Mathf.Floor(e / 0.05f + 1e-3f) * 0.05f : EdoAssets.Own.SodeNoriSnap(e);
            string got = noriPath(sg0, ii, snap);
            if (got == null || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(got) == null)
            { sb.AppendLine("    " + label + " " + sg0.name + " の背: e " + e.ToString("+0.000;-0.000", inv) + " の駒(E" + snap.ToString("+0.00;-0.00", inv) + ")が焼けていない ── 差し替えない"); continue; }
            t0.localScale = sc; t0.position = flatPos;
            var ng = SwapPart(sg0, got); done.Add(ng); nSode++;
            // 丸めの残りを詰める: Yc の高さで背の外面 → 相手の面の口を測り、Yc での駒の長さの比で縮尺する
            float rest = 0f;
            for (int it = 0; it < 2; it++)
            {
                float sp2; float g2 = env ? MeasureSodeBackEnvelope(ng, keri, walls, sNori, out sp2, 0.6f, envVisAt) : MeasureSodeBackOnBatter(ng, keri, walls, out sp2);
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

    // ================================================================ 袖の脇の面 × 隅の駒・土留めの法(EDO-0437 第8巡 2026-09-26)
    /// <summary>駒の三角形を世界座標へ一度だけ焼いて光線を打つ器(<see cref="RayToBodies"/> / <see cref="RayFarthest"/> と同じ測り ──
    /// 呼ぶたびに頂点を変換し直さない)。wall = true なら屋根・隠した描き手を外す(RayToBodies と同じ篩)。</summary>
    sealed class WorldTris
    {
        readonly List<Vector3> A = new List<Vector3>(), E1 = new List<Vector3>(), E2 = new List<Vector3>();
        public WorldTris(GameObject g, bool wall)
        {
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                var mesh = mf.sharedMesh; if (mesh == null) continue;
                if (wall)
                {
                    var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
                    if (IsRoofName(PartName(g.transform, mf))) continue;
                }
                var M = mf.transform.localToWorldMatrix; var vs = mesh.vertices; var ts = mesh.triangles;
                var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) W[i] = M.MultiplyPoint3x4(vs[i]);
                for (int t = 0; t + 2 < ts.Length; t += 3) { A.Add(W[ts[t]]); E1.Add(W[ts[t + 1]] - W[ts[t]]); E2.Add(W[ts[t + 2]] - W[ts[t]]); }
            }
        }
        /// <summary>o から d へ maxDist 以内の当たり(farthest なら最も遠い面・でなければ光線に向く表の面のうち最も近い)。無ければ NaN。</summary>
        public float Ray(Vector3 o, Vector3 d, float maxDist, bool farthest)
        {
            d.Normalize(); float best = farthest ? float.MinValue : float.MaxValue;
            for (int t = 0; t < A.Count; t++)
            {
                Vector3 e1 = E1[t], e2 = E2[t];
                Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-9f) continue;
                float inv = 1f / det; Vector3 tv = o - A[t]; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                float dist = Vector3.Dot(e2, qv) * inv; if (dist < 0f || dist > maxDist) continue;
                // 近い当たりは相手の**表**の面だけ(光線に向く面)── 袖の中の点が相手の中に在ると、相手の裏の面を拾って逆の脇の入りに化けた
                if (!farthest && Vector3.Dot(Vector3.Cross(e1, e2), d) >= 0f) continue;
                if (farthest ? dist > best : dist < best) best = dist;
            }
            return (farthest ? best == float.MinValue : best == float.MaxValue) ? float.NaN : best;
        }
        /// <summary>点 p が駒の中か(8 方向の光線 ── <see cref="MeshInside"/> と同じ決まり: 全ての向きで当たり 1 以上・奇数が 5 本以上)。
        /// 物理の一時の当たりを使わないので、MeshInside と同時に使える(小さな駒 ── 段石 ── だけに使う)。</summary>
        public bool Inside(Vector3 p)
        {
            int odd = 0;
            for (int q = 0; q < 8; q++)
            {
                Vector3 d = q < 6 ? new Vector3(Mathf.Cos(q * Mathf.PI / 3f + 0.13f), 0.07f, Mathf.Sin(q * Mathf.PI / 3f + 0.13f)).normalized
                          : q == 6 ? new Vector3(0.11f, 1f, 0.07f).normalized : new Vector3(-0.09f, -1f, 0.13f).normalized;
                int c = 0;
                for (int t = 0; t < A.Count; t++)
                {
                    Vector3 e1 = E1[t], e2 = E2[t];
                    Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-10f) continue;
                    float inv = 1f / det; Vector3 tv = p - A[t]; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                    Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                    if (Vector3.Dot(e2, qv) * inv > 1e-5f) c++;
                }
                if (c == 0) return false;
                if ((c & 1) == 1) odd++;
            }
            return odd >= 5;
        }
        /// <summary>o から d へ maxDist 以内の最も近い当たり(面の向きを問わない ── 中の点が駒を出る所)。無ければ NaN。</summary>
        public float RayAny(Vector3 o, Vector3 d, float maxDist)
        {
            d.Normalize(); float best = float.MaxValue;
            for (int t = 0; t < A.Count; t++)
            {
                Vector3 e1 = E1[t], e2 = E2[t];
                Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-9f) continue;
                float inv = 1f / det; Vector3 tv = o - A[t]; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                float dist = Vector3.Dot(e2, qv) * inv; if (dist < 1e-5f || dist > maxDist) continue;
                if (dist < best) best = dist;
            }
            return best == float.MaxValue ? float.NaN : best;
        }
    }

    /// <summary><see cref="YieldWallsToSteps"/> の一件(土留めの駒ひとつ)。need = 動かす前に見える所で段石と重なる深さ(段の幅の向き)/
    /// moved = 段の外へ退けた量 / after = 退けた後に残る見える重なり / refused = 退ける量が上限を超え、または二つの石段に挟まれて動かさなかった。</summary>
    public struct StepYield { public GameObject wall; public string steps; public float need, moved, after; public bool refused; public string why; }

    /// <summary>**段石の端に被さる土留め・隅の駒を、段の外へ退ける**(2026-09-26・EDO-0437 第9巡・普請奉行の決め「段は動かさない ── 隅石の据えの側で避ける」)。
    /// 段石 <paramref name="steps"/> は蹴上・踏面が段数からの従属値で、端も法で切って据え済み ── 動かさない。外接箱が段石と重なる土留めの駒
    /// <paramref name="walls"/> ごとに、⑴ 駒の頂点のうち段石の中(<see cref="MeshInside"/>・8 方向の光線)に在り**見える**(見える地表 <paramref name="visAt"/> + 0.02 より上)
    /// 物から、段の幅の向き(段石の +X/−X のうち駒の側)へ段石を出る距離、⑵ 段石の頂点のうち駒の中に在り見える物から、逆の向きへ駒を出る距離を
    /// **実メッシュへ光線を打って**測り、その最大だけ駒を段の外へ平行に退ける(3 巡まで測り直す)。⛔ ピボット・外接箱の中心で決めない。
    /// 硬い(許容0 のめり込み)── 退ける量が <paramref name="maxMove"/> を超える・両脇の段に挟まれる駒は動かさず refused(部材の話)。
    /// 見える地表の下の重なりは数えない(根入れ)。当たる先: 石段の端が脇の土留め・野面の隅に納まる所すべて(山王 参道の階 × 前庭の切り込みの
    /// 隅 Kiri_kado2・N_kado2 と返しの野面 Kiri_012f/027f。男坂・女坂・郭の階・中門の内の階も同じ枝で測る)。</summary>
    public static List<StepYield> YieldWallsToSteps(IList<GameObject> steps, IList<GameObject> walls, System.Func<float, float, float> visAt, float keri, float maxMove = 0.15f, IList<GameObject> fixedNear = null)
    {
        var res = new List<StepYield>();
        float lowTop = float.MaxValue; foreach (var s in steps) if (s != null && s.activeInHierarchy) lowTop = Mathf.Min(lowTop, RB(s).max.y);
        foreach (var w in walls)
        {
            if (w == null || !w.activeInHierarchy) continue;
            var wb = RB(w); var hits = new List<GameObject>();
            foreach (var s in steps) if (s != null && s.activeInHierarchy && RB(s).Intersects(wb) && (fixedNear == null || !fixedNear.Contains(s))) hits.Add(s);
            if (hits.Count == 0) continue;
            // 退ける向き = 段の幅の向き(段石の right の水平)のうち駒の側。段ごとに駒の側を測り、割れたら動かさない。
            Vector3 u = Vector3.zero; bool split = false;
            foreach (var s in hits)
            {
                Vector3 rt = s.transform.right; rt.y = 0f; rt.Normalize();
                var sb = RB(s); Vector3 dc = wb.center - sb.center; dc.y = 0f;
                Vector3 us = Vector3.Dot(dc, rt) >= 0f ? rt : -rt;
                if (u == Vector3.zero) u = us; else if (Vector3.Dot(u, us) < 0.9f) split = true;
            }
            // ⭐ 相手に沿わせて焼いた駒(fixedNear)に接する駒は退けない ── 退けると焼いた形と合わなくなる(隙)。重なりは測って刷るだけ。
            bool frozen = false;
            if (fixedNear != null) foreach (var f in fixedNear) { if (f == null) continue; var fb = RB(f); fb.Expand(0.05f); if (fb.Intersects(wb)) { frozen = true; break; } }
            if (frozen)
            {
                float nf = Need(w, hits, u, visAt, keri, lowTop, steps);
                if (nf > 0.003f) { var nm0 = new List<string>(); foreach (var s in hits) nm0.Add(s.name);
                    res.Add(new StepYield { wall = w, steps = string.Join("・", nm0.ToArray()), need = nf, after = nf, refused = true, why = "相手に沿わせて焼いた駒に接する(退けると形が合わない)── 段の端を沿わせて焼く駒が要る" }); }
                continue;
            }
            // 段ごとに測り、退ける量が上限を超える段は外して別に刷る(部材の話 ── その段の端を切る)。残りの段で退ける。
            var over = new List<GameObject>();
            foreach (var s in hits)
            {
                float n1 = Need(w, new List<GameObject> { s }, u, visAt, keri, lowTop, steps);
                if (n1 + 0.003f > maxMove)
                {
                    over.Add(s);
                    res.Add(new StepYield { wall = w, steps = s.name, need = n1, after = n1, refused = true, why = "退ける量 " + n1.ToString("F3") + " が上限 " + maxMove.ToString("F2") + " を超える ── 段の端を切る駒が要る" });
                }
            }
            foreach (var s in over) hits.Remove(s);
            if (hits.Count == 0) continue;
            float need = Need(w, hits, u, visAt, keri, lowTop, steps), moved = 0f, cur = need;
            var y = new StepYield { wall = w, need = need };
            var nm = new List<string>(); foreach (var s in hits) nm.Add(s.name); y.steps = string.Join("・", nm.ToArray());
            if (need <= 0.003f) continue;
            if (split) { y.refused = true; y.why = "両脇の段に挟まれる"; y.after = need; res.Add(y); continue; }
            for (int it = 0; it < 3 && cur > 0.003f; it++)
            {
                float step = cur + 0.003f;
                if (moved + step > maxMove) { y.refused = true; y.why = "退ける量 " + (moved + step).ToString("F3") + " が上限 " + maxMove.ToString("F2") + " を超える"; break; }
                w.transform.position += u * step; moved += step;
                cur = Need(w, hits, u, visAt, keri, lowTop, steps);
            }
            if (y.refused && moved > 0f) { w.transform.position -= u * moved; moved = 0f; cur = need; }
            y.moved = moved; y.after = cur; res.Add(y);
        }
        return res;
    }

    /// <summary><see cref="YieldWallsToSteps"/> の測り: 駒 <paramref name="w"/> を +<paramref name="u"/> へ退けて見える重なりが消える量。</summary>
    static float Need(GameObject w, IList<GameObject> steps, Vector3 u, System.Func<float, float, float> visAt, float keri, float lowTop, IList<GameObject> allSteps)
    {
        float need = 0f; var wb = RB(w);
        var wt = new WorldTris(w, false);
        // ⚠ MeshInside は層 31 の一時の当たりを使う ── 二つを同時に生かすと光線が両方に当たる。一つずつ作って捨てる。
        var ovs = new List<Bounds>(); var live = new List<GameObject>(); var lowK = new List<bool>();
        foreach (var s in steps)
        {
            var sb = RB(s); if (!sb.Intersects(wb)) continue;
            var mn = Vector3.Max(sb.min, wb.min); var mx = Vector3.Min(sb.max, wb.max); var ov = new Bounds((mn + mx) * 0.5f, mx - mn); ov.Expand(0.004f);
            ovs.Add(ov); live.Add(s);
        }
        var wv = Body(w.transform, 999999, true);
        var others = new List<KeyValuePair<Bounds, WorldTris>>(); var otherGo = new List<GameObject>();
        foreach (var o in allSteps) { if (o == null || !o.activeInHierarchy) continue; var ob = RB(o); ob.Expand(0.01f); if (!ob.Intersects(wb)) continue; others.Add(new KeyValuePair<Bounds, WorldTris>(ob, new WorldTris(o, false))); otherGo.Add(o); }
        System.Func<Vector3, GameObject, bool> InOther = (v, self) =>
        {
            for (int q = 0; q < others.Count; q++) if (otherGo[q] != self && others[q].Key.Contains(v) && others[q].Value.Inside(v)) return true;
            return false;
        };
        for (int k = 0; k < live.Count; k++)
        {
            var s = live[k]; var ov = ovs[k]; var st = new WorldTris(s, false);
            //   ⭐ 他の段の中に在る点は見えない(下の段の踏面の下へ潜る控え ── 参道の階の段 1 の控えで隅の石の足を 0.28 と読んだ)。
            //   ⚠ 見える地表で割るのは最も下の段だけ ── 上の段は地表より上に在る。土留めの Stage の中では皮が外されていて、描かれた地表は
            //     造成前の地形(段の踏面より高い所がある)を返し、隅の石の当たりを全部「地表の下」と読んで退けなかった(2026-09-26)。
            bool low = RB(s).max.y <= lowTop + 0.01f; lowK.Add(low);
            // ⑴ 駒の頂点が段の中 → 段を +u へ出る距離(最も近い面 = 段の端の外面。⛔ 最も遠い面は段の下の張り出しを拾い 0.28 と読んだ)
            using (var inS = new MeshInside(s))
                foreach (var v in wv)
                {
                    if (!ov.Contains(v)) continue;
                    float g = visAt != null && low ? visAt(v.x, v.z) : float.NaN; if (!float.IsNaN(g) && v.y <= g + 0.02f) continue;
                    if (!inS.Inside(v) || InOther(v, s)) continue;
                    float d = st.RayAny(v, u, 1.0f); if (!float.IsNaN(d) && d > need) need = d;
                }
        }
        // ⑵ 段の頂点が駒の中 → 駒を −u へ出る距離(最も近い面)
        using (var inW = new MeshInside(w))
            for (int k = 0; k < live.Count; k++)
                foreach (var v in Body(live[k].transform, 999999, true))
                {
                    if (!ovs[k].Contains(v)) continue;
                    float g = visAt != null && lowK[k] ? visAt(v.x, v.z) : float.NaN; if (!float.IsNaN(g) && v.y <= g + 0.02f) continue;
                    if (!inW.Inside(v) || InOther(v, live[k])) continue;
                    float d = wt.RayAny(v, -u, 1.0f); if (!float.IsNaN(d) && d > need) need = d;
                }
        return need;
    }

    /// <summary><see cref="MeasureSodeSideBites"/> の一件(袖の駒 × 相手の駒 × 脇の向き)。bite = 袖の脇の外面から相手の面が入る深さの最大[m]
    /// (全ての高さ)/ biteVis = そのうち**見える**当たり(当たった点が見える地表 + 0.02 より上)の最大 / y・a = 入る所の高さと走り(袖の局所・+ = 坂下)の範囲 /
    /// nori = 相手の面の法(高さ 1 あたり外へ出る量・列ごとの中央値)/ deg = 相手の面が袖の脇に対して平面で振れる角(+ = 坂下ほど深く入る)/
    /// za = 入る所の坂上・坂下の端のうち、駒の端でない方(隅のもう一面 ── 駒の端まで入れば NaN)。</summary>
    public struct SodeSideBite
    {
        public GameObject sode, wall; public int side, n;
        public float bite, biteVis, yLo, yHi, aLo, aHi, nori, deg, za;
        public bool uphill;
    }

    /// <summary>**石段の袖の脇の面へ入る相手(隅の駒・土留めの法の足)を測る**(2026-09-26・EDO-0437 第8巡・普請奉行の決め「袖が譲る」)。
    /// 袖の駒ごとに、外形の重なる相手(<paramref name="walls"/>)について、脇の両の向きで走り 13 列 × 丈 0.05 刻みに、袖の反対の脇の内から
    /// 外へ光線を打ち、袖の外面を出る所(<see cref="RayFarthest"/>)と相手の面に当たる所の差で入りを測る。⭐ 面で測る(頂点・ピボットで合わせない)。
    /// 見える地表 <paramref name="visAt"/>(NaN 可)より下の当たりは biteVis に数えない(法の足の根入れの中)。入りが 0.005 以下の組は返さない。
    /// 硬い(許容0): めり込み。⟶ 袖の脇を相手の法で切った駒(焼く値 = d・deg・nori・za)。当たる先: 石段の袖が隅の駒・土留めの法の足に脇から
    /// 並ぶ所すべて(山王 女坂の北の袖 × 回廊の出隅 E×S。参道の階・郭の階・中門の内の階も同じ枝で測る)。</summary>
    public static List<SodeSideBite> MeasureSodeSideBites(IList<GameObject> sodes, IList<GameObject> walls, System.Func<float, float, float> visAt)
    {
        var res = new List<SodeSideBite>();
        foreach (var sg in sodes)
        {
            if (sg == null || !sg.activeInHierarchy) continue;
            var rb = RB(sg); rb.Expand(0.02f);
            Vector3 f = sg.transform.forward; f.y = 0f; f.Normalize();
            var ez = ExtentAlong(sg, f);
            float yMin = float.MaxValue, yMax = float.MinValue;
            foreach (var v in Body(sg.transform, 999999, true)) { yMin = Mathf.Min(yMin, v.y); yMax = Mathf.Max(yMax, v.y); }
            var own = new WorldTris(sg, false);
            foreach (var w in walls)
            {
                if (w == null || w == sg || !w.activeInHierarchy || !RB(w).Intersects(rb)) continue;
                var wl = new WorldTris(w, true);
                foreach (int side in new[] { -1, 1 })
                {
                    Vector3 od = sg.transform.right * side; od.y = 0f; od.Normalize();
                    var ep = ExtentAlong(sg, od);
                    const int N = 13; float step = 0.10f;
                    var r = new SodeSideBite { sode = sg, wall = w, side = side, bite = 0f, biteVis = 0f, yLo = float.MaxValue, yHi = float.MinValue,
                                               aLo = float.MaxValue, aHi = float.MinValue, nori = float.NaN, deg = float.NaN, za = float.NaN };
                    var slopes = new List<float>(); var rowsA = new Dictionary<int, List<Vector2>>();
                    for (int k = 0; k < N; k++)
                    {
                        float a = ez.x + 0.02f + (ez.y - ez.x - 0.04f) * k / (N - 1);
                        var col = new List<Vector2>();
                        int hy = 0;
                        for (float y = yMin + 0.02f; y <= yMax - 0.02f; y += step, hy++)
                        {
                            Vector3 o = sg.transform.position + f * a + od * (ep.x + 0.05f); o.y = y;
                            float b = own.Ray(o, od, 3f, true); if (float.IsNaN(b)) continue;
                            float h = wl.Ray(o, od, b + 0.30f, false); if (float.IsNaN(h)) continue;
                            float gp = h - b; col.Add(new Vector2(y, gp));
                            List<Vector2> row; if (!rowsA.TryGetValue(hy, out row)) { row = new List<Vector2>(); rowsA[hy] = row; } row.Add(new Vector2(a, gp));
                            if (gp >= -0.005f) continue;
                            r.n++; r.bite = Mathf.Max(r.bite, -gp);
                            r.yLo = Mathf.Min(r.yLo, y); r.yHi = Mathf.Max(r.yHi, y); r.aLo = Mathf.Min(r.aLo, a); r.aHi = Mathf.Max(r.aHi, a);
                            Vector3 hp = o + od * h; float g = visAt == null ? float.NaN : visAt(hp.x, hp.z);
                            if (float.IsNaN(g) || y > g + 0.02f) r.biteVis = Mathf.Max(r.biteVis, -gp);
                        }
                        // 法 = 列の中の隙の高さに対する傾き(最小二乗)
                        if (col.Count >= 3)
                        {
                            float my = 0f, mg = 0f; foreach (var c in col) { my += c.x; mg += c.y; } my /= col.Count; mg /= col.Count;
                            float sxy = 0f, sxx = 0f; foreach (var c in col) { sxy += (c.x - my) * (c.y - mg); sxx += (c.x - my) * (c.x - my); }
                            if (sxx > 1e-6f) slopes.Add(sxy / sxx);
                        }
                    }
                    if (r.n == 0) continue;
                    slopes.Sort(); if (slopes.Count > 0) r.nori = slopes[slopes.Count / 2];
                    // 平面の振れ = 入る所の行ごとの、走りに対する隙の傾き(入る列だけ)の中央値
                    var degs = new List<float>();
                    foreach (var kv in rowsA)
                    {
                        var pts = kv.Value.FindAll(p => p.x >= r.aLo - 1e-4f && p.x <= r.aHi + 1e-4f);
                        if (pts.Count < 3) continue;
                        float ma = 0f, mg = 0f; foreach (var p in pts) { ma += p.x; mg += p.y; } ma /= pts.Count; mg /= pts.Count;
                        float sxy = 0f, sxx = 0f; foreach (var p in pts) { sxy += (p.x - ma) * (p.y - mg); sxx += (p.x - ma) * (p.x - ma); }
                        if (sxx > 1e-6f) degs.Add(-Mathf.Atan(sxy / sxx) * Mathf.Rad2Deg);
                    }
                    degs.Sort(); if (degs.Count > 0) r.deg = degs[degs.Count / 2];
                    // 入る所が駒の片方の端から始まり、途中で止まるなら、止まる所が隅のもう一面
                    float colStep = (ez.y - ez.x - 0.04f) / (N - 1);
                    bool atLo = r.aLo <= ez.x + 0.02f + 1e-3f, atHi = r.aHi >= ez.y - 0.02f - 1e-3f;
                    //   (走り a は駒の +Z = 坂下が + ⇒ 小さい端から入る = 坂上の側を欠く)
                    if (atLo && !atHi) { r.uphill = true; r.za = r.aHi + colStep * 0.5f; }
                    else if (atHi && !atLo) { r.uphill = false; r.za = r.aLo - colStep * 0.5f; }
                    res.Add(r);
                }
            }
        }
        return res;
    }

    // ================================================================ 敷石(踏石・石段の頭の踏み止め)・袖の端を相手の面まで延ばす(EDO-0428 2026-09-26)
    //   施主統合 EDO-0428: 男坂の頭の踏み止め(指図 kaidans[].fumitome)を建てる C# が無く、楼門の基壇と最上段の間に 0.52m の口が
    //   芝で残った。算出物 setae.fumiishi の 4 件(二ノ鳥居の足元・仁王門の敷居前・参道の階の上端・男坂の頭)がどれも未建立だった。
    //   ⭐ 縁は相手の実メッシュの面で決める(天端の帯へ光線)。⛔ ピボット・bounds の中心・算出物の四角の座標で端を決めない
    //   (四角は相手が無い端と幅の目安だけ)。

    /// <summary><see cref="LayShikiishi"/> の報告。口・食い込みは据えた後に天端の帯で光線を打って測った最大(相手の在る端だけ・無ければ NaN)。</summary>
    public struct Shiki
    {
        public int slabs; public float depth, width, top;
        public float backGap, backBite, frontGap, frontBite, sideGap, sideBite;
        public int backHits, frontHits, sideHits;
        public float expose;     // 相手の無い縁で 天端 − 地表(0.05 外)の最大 = 縁の見付(柔らかい・報告のみ)
        public float buried;     // 外形の中で 地表 − 天端 の最大(> 0.005 は天端が土に埋まる・硬い)
        public string part;
        public override string ToString()
        {
            System.Func<float, string> F = v => float.IsNaN(v) ? "—" : v.ToString("F3");
            return slabs + " 枚(" + part + ")奥行 " + depth.ToString("F3") + " × 幅 " + width.ToString("F3") + " / 天端 " + top.ToString("F3") +
                   " / 背の相手: 口 " + F(backGap) + " 食い込み " + F(backBite) + "(当たり " + backHits + ")" +
                   " / 前の相手: 口 " + F(frontGap) + " 食い込み " + F(frontBite) + "(当たり " + frontHits + ")" +
                   " / 脇の相手: 口 " + F(sideGap) + " 食い込み " + F(sideBite) + "(当たり " + sideHits + ")" +
                   " / 縁の見付 最大 " + expose.ToString("F3") + " / 天端の埋没 " + (buried > 0.005f ? "⛔ " : "") + Mathf.Max(0f, buried).ToString("F3");
        }
    }

    /// <summary>**天端の帯へ光線を打つ。**高さ <paramref name="yTop"/> − 0.005 から <paramref name="band"/> 下まで 0.01 刻みで
    /// <paramref name="o"/>(高さは無視)から <paramref name="d"/> へ打ち、<b>最初に当たった高さ</b>での距離(当たらなければ NaN)。
    /// ⭐ 見える取り合いは天端の縁 ── 相手の面が法(石垣)でも、天端の帯の当たりが見える口を決める。胴・尾(地中)で当てない。</summary>
    public static float RayAtTopBand(IList<GameObject> mates, Vector3 o, Vector3 d, float maxDist, float yTop, float band = 0.08f)
    {
        for (float dy = 0.005f; dy <= band + 1e-4f; dy += 0.01f)
        {
            o.y = yTop - dy; float h = RayToBodies(mates, o, d, maxDist);
            if (!float.IsNaN(h)) return h;
        }
        return float.NaN;
    }

    /// <summary>**駒の端を相手の面まで伸ばす**(<see cref="StretchEnd"/>)。端(<paramref name="dir"/> の側)の少し内から、駒の厚み
    /// (dir に直交)の 3 点で相手の天端の帯(<paramref name="yTop"/>)へ光線を打ち、**最も遠い当たり**まで伸ばす(見える高さで口 0 ──
    /// 閉じは「隙間 > めり込み」)。返り値 = 伸ばした量[m](当たらなければ NaN・駒は触らない)。<paramref name="spread"/> = 当たりの割れ
    /// (相手の面が走りに斜め・法のとき > 0 ── その分は帯の下で相手の中へ入る)。
    /// 当たる先: 石段の袖の走りが段の外(踏み止め・踊り場)へ延び、相手(基壇・腰石垣)の面で止まる所(山王 男坂の頭 × 楼門の腰)。</summary>
    public static float ExtendEndToFace(GameObject piece, Vector3 dir, IList<GameObject> mates, float yTop, float maxReach, out float spread, out int hits)
    {
        spread = 0f; hits = 0;
        dir.y = 0f; dir.Normalize(); var perp = new Vector3(dir.z, 0f, -dir.x);
        var ed = ExtentAlong(piece, dir); var ep = ExtentAlong(piece, perp);
        Vector3 o0 = piece.transform.position;
        float far = float.MinValue, near = float.MaxValue;
        // ⭐ 光線は駒の走りの中ほどから打つ(2026-09-27 EDO-0459)── 端の少し内から打つと、端が既に相手の面を越えている駒
        //   (小口を法で切った駒は天端の稜が帯より先に出る)で原点が相手の中に入り、相手の奥の面まで 0.4m 伸ばした。
        float oa = (ed.x + ed.y) * 0.5f;
        foreach (float a in new[] { ep.x + 0.05f, (ep.x + ep.y) * 0.5f, ep.y - 0.05f })
        {
            Vector3 o = o0 + dir * oa + perp * a;
            float h = RayAtTopBand(mates, o, dir, maxReach + (ed.y - oa), yTop); if (float.IsNaN(h)) continue;
            float t = Vector3.Dot(new Vector3(o.x, 0f, o.z), dir) + h; hits++;
            far = Mathf.Max(far, t); near = Mathf.Min(near, t);
        }
        if (hits == 0) return float.NaN;
        spread = far - near;
        float got = StretchEnd(piece.transform, null, dir, +1f, far);
        // 見える口を閉じる(駒の端の面取り・法の分)── 天端の帯で駒の中から相手まで測り、残る口だけ伸ばす(最大 3 巡)
        for (int pass = 0; pass < 3 && !float.IsNaN(got); pass++)
        {
            float gw = MeasureEndGap(piece, dir, mates, yTop);
            if (float.IsNaN(gw) || gw <= 0.002f) break;
            got += StretchEnd(piece.transform, null, dir, +1f, EdgeAlong(piece.transform, dir, +1f) + gw);
        }
        return got;
    }

    /// <summary>駒の <paramref name="dir"/> の端と相手の面の見える口[m](+ 口 / − 食い込み)の最大 ── 駒の厚みの 3 点 × 天端の帯
    /// (<paramref name="yTop"/> − 0.005 から下へ、最初に当たる高さ)。当たらなければ NaN。</summary>
    public static float MeasureEndGap(GameObject piece, Vector3 dir, IList<GameObject> mates, float yTop)
    {
        dir.y = 0f; dir.Normalize(); var perp = new Vector3(dir.z, 0f, -dir.x);
        var ed = ExtentAlong(piece, dir); var ep = ExtentAlong(piece, perp); Vector3 o0 = piece.transform.position;
        float worst = float.NaN;
        foreach (float a in new[] { ep.x + 0.05f, (ep.x + ep.y) * 0.5f, ep.y - 0.05f })
        {
            Vector3 o = o0 + dir * (ed.y - 0.10f) + perp * a;
            for (float dy = 0.005f; dy <= 0.085f; dy += 0.01f)
            {
                o.y = yTop - dy; float gp = GapAlong(piece, mates, o, dir, 0.3f); if (float.IsNaN(gp)) continue;
                worst = float.IsNaN(worst) ? gp : Mathf.Max(worst, gp); break;
            }
        }
        return worst;
    }

    /// <summary><see cref="LayFlatSode"/> の検め(全て実メッシュで測った値)。</summary>
    public struct FlatSode
    {
        public float depth;      // 選んだ丈[m](差し替える駒の底と同じ根入れが取れる最小の丈)
        public float topBelow;   // 下の斜めの袖の坂上の端(段鼻)での天端[m] ── 水平の袖の天端はこれに揃える
        public float topLo, topHi; // 据えた水平の袖の天端: 坂下の端・坂上の端[m]
        public float step;       // 坂下の端の天端 − topBelow[m](段差。0 が狙い)
        public float sideIn, sideOut; // 脇の面の食い違い[m](下の袖の端の面 − 水平の袖の面・左右)
        public float gapBelow;   // 坂下の端 × 下の袖の坂上の端の見える口[m](+ 口 / − 食い込み)
        public float ext;        // 坂上の端を相手の面まで伸ばした量[m](NaN = 当たらず)
        public float spread; public int hits; // 当たりの割れ・数
        public float gapMate;    // 坂上の端 × 相手の面の見える口[m]
        public float profMin, profMax; // 坂上の端 × 相手の面を高さ方向(帯の下 1m まで 0.1 刻み)に測った 最もめり込む値・最も開く値[m]
        public float pulled;     // 高さ方向のめり込みを詰めた量[m](0 = 詰めていない)
    }

    /// <summary>**駒の端と相手の面の取り合いを高さ方向に測る**(EDO-0459)。駒の走りの中ほど・厚みの 3 点から <paramref name="dir"/> へ、
    /// <paramref name="yTop"/> − 0.05 から下へ 0.1 刻み(最大 1m・駒の底まで)で「相手までの距離 − 駒の外面までの距離」を取り、
    /// 最小(最もめり込む・負)と最大(最も開く)を返す。相手の無い高さは数えない。測れなければ NaN。
    /// ⭐ 天端の帯だけで突き付けると、相手の天端の稜の丸み・面取りの分だけ奥で当たり、帯の下が一様にめり込む(男坂 × kado1 で −0.009)。</summary>
    public static void EndGapProfile(GameObject piece, Vector3 dir, IList<GameObject> mates, float yTop, out float gMin, out float gMax)
    {
        gMin = float.NaN; gMax = float.NaN;
        dir.y = 0f; dir.Normalize(); var perp = new Vector3(dir.z, 0f, -dir.x);
        var ed = ExtentAlong(piece, dir); var ep = ExtentAlong(piece, perp); Vector3 o0 = piece.transform.position;
        float bot = float.MaxValue; foreach (var p in Body(piece.transform, 999999, true)) bot = Mathf.Min(bot, p.y);
        float yLo = Mathf.Max(bot + 0.05f, yTop - 1.0f);
        for (float y = yTop - 0.05f; y >= yLo; y -= 0.1f)
            foreach (float a in new[] { ep.x + 0.05f, (ep.x + ep.y) * 0.5f, ep.y - 0.05f })
            {
                Vector3 o = o0 + dir * ((ed.x + ed.y) * 0.5f) + perp * a; o.y = y;
                float gp = GapAlong(piece, mates, o, dir, 0.3f); if (float.IsNaN(gp)) continue;
                gMin = float.IsNaN(gMin) ? gp : Mathf.Min(gMin, gp); gMax = float.IsNaN(gMax) ? gp : Mathf.Max(gMax, gp);
            }
    }

    /// <summary>**石段の袖の最上段の駒を、天端が水平な袖へ差し替えて相手の面まで伸ばす**(EDO-0459 施主裁定A 2026-09-26)。
    /// 斜めの袖を段の外(踏み止め・踊り場)へ延ばすと天端が勾配のまま上がり続ける(男坂の頭で 28.58 → 29.05)。⇒ 最上段の駒を
    /// 水平の袖 <paramref name="pathOf"/>(丈 → `EdoAssets.Own.IshidanSodeFlat`)へ替え、**下の斜めの袖 <paramref name="below"/> の実メッシュを測って**据える:
    /// ① 高さ — 下の袖の坂上の端(= 最上段の段鼻)の天端の最高へ水平の袖の天端を揃える(段差 0)。
    /// ② 横 — 下の袖の坂上の端の脇の二面(外・内)の中ほどへ、水平の袖の脇の二面の中ほどを寄せる(同じ厚み 0.60 ⇒ 両面とも面一)。
    /// ③ 走り — 水平の袖の坂下の端を下の袖の坂上の端の面へ突き付け(隙 0)、坂上の端を <see cref="ExtendEndToFace"/> で
    ///    相手 <paramref name="mates"/>(基壇・腰石垣)の天端の帯 <paramref name="yBand"/> の面まで伸ばす(Z だけ伸縮 ⇒ 天端は水平のまま)。
    /// 丈 = 差し替える駒 <paramref name="old"/> の底(根入れ)を下回らない最小の丈(<paramref name="depths"/> は浅い順)。
    /// 差し替えは据えた後に旧を消す(同じ名・同じ親)。⛔ ピボット・bounds の中心で合わせない(仮置きは当て推量)。
    /// 硬い条件: 段差・坂下の口・相手との口 0(5mm を超えたら <paramref name="warn"/>)。相手の天端より高く出る小口は裁定どおり(欠陥ではない)。
    /// ⚠ 坂上の端は鉛直 ⇒ 相手の面が法(腰の隅 1:0.25)だと天端の帯より下で相手の中へ入る(法の楔・男坂で 0.2m 下がるごとに 0.05)。
    /// 解くのは端を法で切った水平の袖の駒(部材)。
    /// 当たる先: 石段の袖の走りが段の外へ延びて相手の面で止まる所 ── 今は指図 `kaidans[].fumitome` を持つ山王の男坂(南北の 2 駒)だけ。
    /// <paramref name="mates"/> が空で <paramref name="flushTo"/>(最上段の段石)を渡すと、坂上の端は相手へ伸ばさず最上段の上の端と同じ通りに揃える
    /// (見切り ── 山王の参道の階の段4 の袖 W・E。部材は走りを踏面の実長で焼いた `IshidanSodeFlat(depth, len)` ⇒ 伸縮 ≈ 1)。</summary>
    public static GameObject LayFlatSode(GameObject old, GameObject below, System.Func<float, string> pathOf, IList<float> depths,
                                         Vector3 up, IList<GameObject> mates, float yBand, float maxReach, out FlatSode rep, out string warn,
                                         GameObject flushTo = null)
    {
        rep = new FlatSode { depth = float.NaN, ext = float.NaN, gapBelow = float.NaN, gapMate = float.NaN };
        warn = null; string nm = old.name;
        up.y = 0f; up.Normalize(); var perp = new Vector3(up.z, 0f, -up.x);
        var bp = Body(below.transform, 999999, true);
        if (bp.Count == 0) { warn = below.name + ": 下の袖の実メッシュが無い"; return null; }
        float eUp = float.MinValue; foreach (var p in bp) eUp = Mathf.Max(eUp, Vector3.Dot(p, up));
        float topB = float.MinValue, bLo = float.MaxValue, bHi = float.MinValue;
        foreach (var p in bp)
        {
            if (Vector3.Dot(p, up) < eUp - 0.03f) continue;
            topB = Mathf.Max(topB, p.y); float s = Vector3.Dot(p, perp); bLo = Mathf.Min(bLo, s); bHi = Mathf.Max(bHi, s);
        }
        rep.topBelow = topB;
        float oldBot = float.MaxValue; foreach (var p in Body(old.transform, 999999, true)) oldBot = Mathf.Min(oldBot, p.y);
        // ⛔ 硬い: 旧の駒の実メッシュが測れない(部材を消した・焼き直した後)なら丈を選ばない ── 当て推量で浅い丈を据えた(2026-09-27 南が 2.20 に化けた)。石段から流し直す。
        if (oldBot == float.MaxValue) { warn = nm + ": ⛔ 差し替える旧の駒の実メッシュが無い(部材が消えた?)── 丈を選べないので据えない。石段(Stage2)から流し直すこと"; return null; }
        float depth = depths[depths.Count - 1];
        foreach (var d in depths) if (topB - d <= oldBot + 0.02f) { depth = d; break; }
        rep.depth = depth;
        string path = pathOf(depth);
        if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { warn = nm + ": ⛔ 水平の袖を焼いていない " + path; return null; }
        // ---- 仮置き(当て推量)→ 実メッシュを測って三方向を寄せる
        var go = Place(path, below.transform.position, below.transform.eulerAngles.y, Vector3.one, old.transform.parent, old.name);
        if (go == null) { warn = nm + ": 水平の袖を置けない"; return null; }
        var np = Body(go.transform, 999999, true);
        float nDown = float.MaxValue, nTop = float.MinValue, nLo = float.MaxValue, nHi = float.MinValue;
        foreach (var p in np)
        {
            nDown = Mathf.Min(nDown, Vector3.Dot(p, up)); nTop = Mathf.Max(nTop, p.y);
            float s = Vector3.Dot(p, perp); nLo = Mathf.Min(nLo, s); nHi = Mathf.Max(nHi, s);
        }
        go.transform.position += up * (eUp - nDown) + perp * ((bLo + bHi) * 0.5f - (nLo + nHi) * 0.5f) + Vector3.up * (topB - nTop);
        rep.sideIn = bLo - (nLo + (bLo + bHi) * 0.5f - (nLo + nHi) * 0.5f);
        rep.sideOut = bHi - (nHi + (bLo + bHi) * 0.5f - (nLo + nHi) * 0.5f);
        // ---- 坂上の端を相手の面まで
        //   ⭐ 相手が無く坂上の端が「見切り」(指図 joints: 小口を最上段の上の端と同じ通りに揃えて終える)なら、
        //   <paramref name="flushTo"/>(最上段の段石)の実メッシュの坂上の端へ揃える(EDO-0437 参道の階の段4 2026-09-27)。
        bool flush = (mates == null || mates.Count == 0) && flushTo != null;
        float spread = 0f; int hits = 0; float flushAt = float.NaN;
        if (flush)
        {
            // 最上段の上の端 = **踏面(天端の帯 0.02)の坂上の縁** ── 段石の胴は次の段(ここでは面)の下へ 0.1 潜るので、全メッシュの端で測ると 0.1 伸びた
            var fv = Body(flushTo.transform, 999999, true); float fTop = float.MinValue; foreach (var p in fv) fTop = Mathf.Max(fTop, p.y);
            foreach (var p in fv) if (p.y >= fTop - 0.02f) { float a = Vector3.Dot(p, up); flushAt = float.IsNaN(flushAt) ? a : Mathf.Max(flushAt, a); }
            rep.ext = float.IsNaN(flushAt) ? float.NaN : StretchEnd(go.transform, null, up, +1f, flushAt);
        }
        else rep.ext = ExtendEndToFace(go, up, mates, yBand, maxReach, out spread, out hits);
        rep.spread = spread; rep.hits = hits;
        // ⭐ 高さ方向に測り、最も深いめり込みだけ詰める(閉じは「隙間 > めり込み」)
        if (!flush && !float.IsNaN(rep.ext))
        {
            float pMin, pMax; EndGapProfile(go, up, mates, yBand, out pMin, out pMax);
            if (!float.IsNaN(pMin) && pMin < -0.002f) { StretchEnd(go.transform, null, up, +1f, EdgeAlong(go.transform, up, +1f) + pMin); rep.pulled = -pMin; }
        }
        if (!flush) { float pMin, pMax; EndGapProfile(go, up, mates, yBand, out pMin, out pMax); rep.profMin = pMin; rep.profMax = pMax; }
        else { rep.profMin = float.NaN; rep.profMax = float.NaN; }
        Object.DestroyImmediate(old);
        // ---- 検め
        np = Body(go.transform, 999999, true);
        float d0 = float.MaxValue, d1 = float.MinValue; foreach (var p in np) { float a = Vector3.Dot(p, up); d0 = Mathf.Min(d0, a); d1 = Mathf.Max(d1, a); }
        rep.topLo = float.MinValue; rep.topHi = float.MinValue;
        foreach (var p in np)
        {
            float a = Vector3.Dot(p, up);
            if (a < d0 + 0.05f) rep.topLo = Mathf.Max(rep.topLo, p.y);
            if (a > d1 - 0.05f) rep.topHi = Mathf.Max(rep.topHi, p.y);
        }
        rep.step = rep.topLo - topB;
        // 継ぎ目の口は面取り(0.02)の下で測る ── 天端の縁の帯では水平の袖の面取りの V を 0.015 の口と読む(2026-09-27 実測・下は 0.0001)
        rep.gapBelow = MeasureEndGap(go, -up, new List<GameObject> { below }, topB - 0.02f);
        rep.gapMate = flush ? (float.IsNaN(flushAt) ? float.NaN : EdgeAlong(go.transform, up, +1f) - flushAt) : MeasureEndGap(go, up, mates, yBand);
        var bad = new List<string>();
        if (Mathf.Abs(rep.step) > 0.005f) bad.Add("段差 " + rep.step.ToString("+0.000;-0.000"));
        if (Mathf.Abs(rep.topHi - rep.topLo) > 0.005f) bad.Add("水平の狂い " + (rep.topHi - rep.topLo).ToString("+0.000;-0.000"));
        if (float.IsNaN(rep.gapBelow) || Mathf.Abs(rep.gapBelow) > 0.005f) bad.Add("下の袖との口 " + (float.IsNaN(rep.gapBelow) ? "測れず" : rep.gapBelow.ToString("+0.000;-0.000")));
        if (float.IsNaN(rep.ext)) bad.Add(flush ? "最上段の坂上の端を測れず" : "相手の面に当たらず(伸ばさない)");
        else if (flush) { if (float.IsNaN(rep.gapMate) || Mathf.Abs(rep.gapMate) > 0.005f) bad.Add("最上段の上の端との見切りの差 " + (float.IsNaN(rep.gapMate) ? "測れず" : rep.gapMate.ToString("+0.000;-0.000"))); }
        else if (float.IsNaN(rep.gapMate) || rep.gapMate > 0.005f) bad.Add("相手との口 " + (float.IsNaN(rep.gapMate) ? "測れず" : rep.gapMate.ToString("+0.000;-0.000")));
        if (!float.IsNaN(rep.profMin) && (rep.profMin < -0.005f || rep.profMax > 0.005f)) bad.Add("相手との取り合い(高さ方向)" + rep.profMin.ToString("+0.000;-0.000") + "〜" + rep.profMax.ToString("+0.000;-0.000"));
        if (bad.Count > 0) warn = nm + ": ⚠ " + string.Join("・", bad.ToArray());
        return go;
    }

    /// <summary>**敷石を据える**(踏石・石段の頭の踏み止め・EDO-0428)。四角 <paramref name="quad"/>(世界 XZ・算出物)の中へ、段石
    /// <paramref name="pathOf"/>(個体 i → 部材)を前 <paramref name="front"/>(部材の局所 +Z = 見え面の向き)へ並べて敷く。
    /// <para>① 端: 背(−front)・前(+front)・脇(±横)は、相手 <paramref name="backMates"/> / <paramref name="frontMates"/> /
    /// <paramref name="sideMates"/> の**天端の帯**(<see cref="RayAtTopBand"/>)へ四角の中から光線を打って測った面。相手が無い・当たらない端は
    /// 四角の縁。⭐ 当たりが割れたら最も遠い所まで(見える口 0・割れた分は帯の下で相手へ入る)。</para>
    /// <para>② 枚数 = 奥行 ÷ 部材の走りの丸め(1 以上)。各枚を等分の区間へ <see cref="StretchEnd"/> で伸縮(前 → 背 → 脇の順。
    /// ピボットに頼らない)。</para>
    /// <para>③ 天端: <paramref name="top"/>(指図の面の高さ)。NaN なら各枚の外形の中の地表の最大(= 天端がどこでも土に埋まらない)。
    /// 高さは据えた実メッシュの最高点で合わせる。</para>
    /// 硬い: 天端の埋没 0・相手との見える口 0。柔らかい(報告のみ): 相手の無い縁の見付。</summary>
    public static List<GameObject> LayShikiishi(System.Func<int, string> pathOf, Vector2[] quad, Vector2 front, float top, Transform parent, string name,
                                                IList<GameObject> backMates, IList<GameObject> frontMates, IList<GameObject> sideMates, out Shiki rep)
    {
        rep = new Shiki { backGap = float.NaN, backBite = float.NaN, frontGap = float.NaN, frontBite = float.NaN, sideGap = float.NaN, sideBite = float.NaN };
        var res = new List<GameObject>();
        Vector2 f = front.normalized, s = new Vector2(f.y, -f.x);
        Vector3 F3 = new Vector3(f.x, 0f, f.y), S3 = new Vector3(s.x, 0f, s.y);
        float fLo = float.MaxValue, fHi = float.MinValue, sLo = float.MaxValue, sHi = float.MinValue;
        foreach (var q in quad) { float a = Vector2.Dot(q, f), b = Vector2.Dot(q, s); fLo = Mathf.Min(fLo, a); fHi = Mathf.Max(fHi, a); sLo = Mathf.Min(sLo, b); sHi = Mathf.Max(sHi, b); }
        System.Func<float, float, Vector3> W = (a, b) => { var p = f * a + s * b; return new Vector3(p.x, 0f, p.y); };
        float fMid = (fLo + fHi) * 0.5f, sMid = (sLo + sHi) * 0.5f;
        // 測る高さ(光線の帯の頭)── 天端が無ければ四角の中の地表の最大
        float yRay = top;
        if (float.IsNaN(yRay)) { yRay = float.MinValue; for (int i = 0; i <= 4; i++) for (int j = 0; j <= 4; j++) { var p = W(Mathf.Lerp(fLo, fHi, i / 4f), Mathf.Lerp(sLo, sHi, j / 4f)); yRay = Mathf.Max(yRay, Ground(p.x, p.z)); } }
        float reachF = (fHi - fLo) * 0.5f + 0.6f, reachS = (sHi - sLo) * 0.5f + 0.6f;
        // ① 端を相手の面で
        System.Func<IList<GameObject>, Vector3, float, float, bool, float> EndAt = (mates, d, fromA, fallback, alongS) =>
        {
            if (mates == null || mates.Count == 0) return fallback;
            float best = float.NaN;
            float[] ks = { 0.1f, 0.3f, 0.5f, 0.7f, 0.9f };
            foreach (var k in ks)
            {
                Vector3 o = alongS ? W(Mathf.Lerp(fLo, fHi, k), fromA) : W(fromA, Mathf.Lerp(sLo, sHi, k));
                float h = RayAtTopBand(mates, o, d, alongS ? reachS : reachF, yRay); if (float.IsNaN(h)) continue;
                float t = Vector3.Dot(o, d) + h;                    // d の向きの座標(遠いほど大)
                best = float.IsNaN(best) ? t : Mathf.Max(best, t);
            }
            if (float.IsNaN(best)) return fallback;
            // d の向きの座標 → f / s の座標(d = ±F3 / ±S3)
            return (Vector3.Dot(d, alongS ? S3 : F3) > 0f) ? best : -best;
        };
        float fb = EndAt(backMates, -F3, fMid, fLo, false);
        float ff = EndAt(frontMates, F3, fMid, fHi, false);
        float sl = EndAt(sideMates, -S3, sMid, sLo, true);
        float sh = EndAt(sideMates, S3, sMid, sHi, true);
        rep.depth = ff - fb; rep.width = sh - sl;
        if (rep.depth < 0.1f || rep.width < 0.1f) { rep.part = "奥行か幅が 0.1 未満 ── 据えない"; return res; }
        // ② 枚数
        string p0 = pathOf(0); rep.part = System.IO.Path.GetFileNameWithoutExtension(p0);
        var probe = Place(p0, W(fMid, sMid), Mathf.Atan2(f.x, f.y) * Mathf.Rad2Deg, Vector3.one, parent, name + "_probe");
        if (probe == null) { rep.part = "部材が無い: " + p0; return res; }
        float run = LocalSpan(probe.transform, Vector3.forward); Object.DestroyImmediate(probe);
        int n = Mathf.Max(1, Mathf.RoundToInt(rep.depth / Mathf.Max(0.05f, run)));
        float L = rep.depth / n;
        for (int k = 0; k < n; k++)
        {
            float a0 = fb + L * k, a1 = fb + L * (k + 1);
            var g = Place(pathOf(k), W((a0 + a1) * 0.5f, (sl + sh) * 0.5f), Mathf.Atan2(f.x, f.y) * Mathf.Rad2Deg, Vector3.one, parent,
                          n == 1 ? name : name + "_" + k.ToString("00"));
            if (g == null) continue;
            StretchEnd(g.transform, null, F3, +1f, a1);
            StretchEnd(g.transform, null, F3, -1f, a0);
            StretchEnd(g.transform, null, S3, +1f, sh);
            StretchEnd(g.transform, null, S3, -1f, sl);
            // ③ 天端
            float ty = top;
            if (float.IsNaN(ty))
            {
                ty = float.MinValue;
                for (int i = 0; i <= 4; i++) for (int j = 0; j <= 4; j++) { var p = W(Mathf.Lerp(a0, a1, i / 4f), Mathf.Lerp(sl, sh, j / 4f)); ty = Mathf.Max(ty, Ground(p.x, p.z)); }
            }
            float mx = float.MinValue; foreach (var v in Body(g.transform, 999999, true)) mx = Mathf.Max(mx, v.y);
            g.transform.position += Vector3.up * (ty - mx);
            rep.top = ty;
            res.Add(g);
        }
        rep.slabs = res.Count;
        if (res.Count == 0) return res;
        float topM = rep.top;
        // ①' 見える口を閉じる: 端の駒の天端の帯で相手までの口を測り、口が残れば端をそこまで伸ばす(面取り・法の分。最大 3 巡)。
        //   ⭐ 閉じは「隙間 > めり込み」── 0 を外すなら帯の下で相手へ入る側へ(見えない)。
        System.Func<IList<GameObject>, GameObject, Vector3, float> TopGap = (mates, own, d) =>
        {
            if (mates == null || mates.Count == 0) return float.NaN;
            float worst = float.NaN;
            foreach (var k in new[] { 0.1f, 0.3f, 0.5f, 0.7f, 0.9f })
            {
                Vector3 o = W(Vector3.Dot(own.transform.position, F3), Mathf.Lerp(sl, sh, k));
                for (float dy = 0.005f; dy <= 0.085f; dy += 0.01f)
                {
                    var oo = o; oo.y = topM - dy;
                    float gp = GapAlong(own, mates, oo, d, 0.3f); if (float.IsNaN(gp)) continue;
                    worst = float.IsNaN(worst) ? gp : Mathf.Max(worst, gp); break;
                }
            }
            return worst;
        };
        System.Func<GameObject, Vector3, float> SideGap = (own, d) =>
        {
            if (sideMates == null || sideMates.Count == 0) return float.NaN;
            float worst = float.NaN; var ef = ExtentAlong(own, F3); float fo = Vector3.Dot(own.transform.position, F3);
            foreach (var k in new[] { 0.2f, 0.5f, 0.8f })
            {
                Vector3 o = W(fo + Mathf.Lerp(ef.x, ef.y, k), (sl + sh) * 0.5f);
                for (float dy = 0.005f; dy <= 0.085f; dy += 0.01f)
                {
                    var oo = o; oo.y = topM - dy;
                    float gp = GapAlong(own, sideMates, oo, d, 0.3f); if (float.IsNaN(gp)) continue;
                    worst = float.IsNaN(worst) ? gp : Mathf.Max(worst, gp); break;
                }
            }
            return worst;
        };
        for (int pass = 0; pass < 3; pass++)
        {
            bool moved = false;
            foreach (var g in res)
                foreach (var sg0 in new[] { 1f, -1f })
                {
                    float gs = SideGap(g, S3 * sg0);
                    if (!float.IsNaN(gs) && gs > 0.002f) { StretchEnd(g.transform, null, S3, sg0, EdgeAlong(g.transform, S3, sg0) + sg0 * gs); moved = true; }
                }
            float gb = TopGap(backMates, res[0], -F3);
            if (!float.IsNaN(gb) && gb > 0.002f) { StretchEnd(res[0].transform, null, F3, -1f, EdgeAlong(res[0].transform, F3, -1f) - gb); moved = true; }
            var last = res[res.Count - 1];
            float gf = TopGap(frontMates, last, F3);
            if (!float.IsNaN(gf) && gf > 0.002f) { StretchEnd(last.transform, null, F3, +1f, EdgeAlong(last.transform, F3, +1f) + gf); moved = true; }
            if (!moved) break;
        }
        // 据えた後の実測: 天端の帯で、敷石の中から相手へ(口 + / 食い込み −)
        System.Action<IList<GameObject>, Vector3, float, bool, System.Action<float>> Meas = (mates, d, fromA, alongS, put) =>
        {
            if (mates == null || mates.Count == 0) return;
            foreach (var k in new[] { 0.1f, 0.3f, 0.5f, 0.7f, 0.9f })
            {
                Vector3 o = alongS ? W(Mathf.Lerp(fb, ff, k), fromA) : W(fromA, Mathf.Lerp(sl, sh, k));
                GameObject own = null; float bd = float.MaxValue;
                foreach (var g in res) { float dd = Vector3.Distance(new Vector3(g.transform.position.x, 0f, g.transform.position.z), o); if (dd < bd) { bd = dd; own = g; } }
                if (alongS) { own = null; bd = float.MaxValue; foreach (var g in res) { float dd = Mathf.Abs(Vector3.Dot(g.transform.position, F3) - Vector3.Dot(o, F3)); if (dd < bd) { bd = dd; own = g; } } }
                else own = Vector3.Dot(d, F3) > 0f ? res[res.Count - 1] : res[0];
                for (float dy = 0.005f; dy <= 0.085f; dy += 0.02f)
                {
                    var oo = o; oo.y = topM - dy;
                    float gp = GapAlong(own, mates, oo, d, 0.3f); if (float.IsNaN(gp)) continue;
                    put(gp); break;
                }
            }
        };
        int bh = 0, fh = 0, sh2 = 0; float bg = 0f, bb = 0f, fg = 0f, fbi = 0f, sg = 0f, sbi = 0f;
        Meas(backMates, -F3, fMid, false, gp => { bh++; if (gp > 0) bg = Mathf.Max(bg, gp); else bb = Mathf.Max(bb, -gp); });
        Meas(frontMates, F3, fMid, false, gp => { fh++; if (gp > 0) fg = Mathf.Max(fg, gp); else fbi = Mathf.Max(fbi, -gp); });
        Meas(sideMates, -S3, sMid, true, gp => { sh2++; if (gp > 0) sg = Mathf.Max(sg, gp); else sbi = Mathf.Max(sbi, -gp); });
        Meas(sideMates, S3, sMid, true, gp => { sh2++; if (gp > 0) sg = Mathf.Max(sg, gp); else sbi = Mathf.Max(sbi, -gp); });
        rep.backHits = bh; rep.frontHits = fh; rep.sideHits = sh2;
        if (bh > 0) { rep.backGap = bg; rep.backBite = bb; }
        if (fh > 0) { rep.frontGap = fg; rep.frontBite = fbi; }
        if (sh2 > 0) { rep.sideGap = sg; rep.sideBite = sbi; }
        // 縁の見付(相手の無い縁)・天端の埋没(外形の中)
        var allMates = new List<GameObject>();
        foreach (var ml in new[] { backMates, frontMates, sideMates }) if (ml != null) allMates.AddRange(ml);
        foreach (var g in res)
        {
            float gt = float.MinValue; foreach (var v in Body(g.transform, 999999, true)) gt = Mathf.Max(gt, v.y);
            var hull = HullOfMat(g.transform, null);
            Vector2 c = Vector2.zero; foreach (var q in hull) c += q; c /= Mathf.Max(1, hull.Length);
            foreach (var q in hull)
            {
                var outP = q + (q - c).normalized * 0.05f; var inP = q + (c - q).normalized * 0.05f;
                // 縁の外が相手・隣の敷石に覆われていれば見付でない(真上から光線)
                bool covered = !float.IsNaN(RayToBodies(allMates, new Vector3(outP.x, gt + 0.5f, outP.y), Vector3.down, 0.6f))
                            || !float.IsNaN(RayToBodies(res, new Vector3(outP.x, gt + 0.5f, outP.y), Vector3.down, 0.6f));
                if (!covered) rep.expose = Mathf.Max(rep.expose, gt - Ground(outP.x, outP.y));
                rep.buried = Mathf.Max(rep.buried, Ground(inP.x, inP.y) - gt);
            }
            rep.buried = Mathf.Max(rep.buried, Ground(c.x, c.y) - gt);
        }
        return res;
    }

    /// <summary>**相手の上向きの面と同じ高さで重なる駒を下げる**(普請奉行の決め 2026-09-26・EDO-0428 二巡目)。<paramref name="pieces"/>
    /// (下の側 ── 土留め・腰石垣)の天端(屋根でない上向きの面の最高)を 0.1m 格子で測り、同じ点に <paramref name="others"/>(門・敷石)の
    /// 上向きの面が ±<paramref name="tol"/> で在れば(= 二つの面が同じ高さで重なり斑に描かれる)、その駒を <paramref name="drop"/> 下げる。
    /// ⛔ 上げない。⛔ 相手は動かさない(施主裁定の天端は相手の天端として残る)。同じ高さで無くなれば二度目は動かない(冪等)。
    /// 返り値 = 下げた駒の数。<paramref name="report"/> = 駒ごとの重なりの点数(前 → 後)。
    /// 当たる先: 門・棟の基壇の下へ天端を入れた腰石垣・土留めの隅(山王 楼門の腰の隅 2 駒)、面の高さに据えた敷石の縁に掛かる土留め。</summary>
    public static int SinkCoplanarUnder(IList<GameObject> pieces, IList<GameObject> others, out string report,
                                        float tol = 0.005f, float drop = 0.01f, bool measureOnly = false, float maxDrop = 0.03f)
    {
        var sb = new System.Text.StringBuilder(); int lowered = 0;
        var ot = new List<Vector3[]>(); var oh = new Dictionary<long, List<int>>();
        foreach (var o in others)
        {
            if (o == null || !o.activeInHierarchy) continue;
            foreach (var t in Hifu_OpenUp(o))
            {
                int id = ot.Count; ot.Add(t);
                for (int i = Mathf.FloorToInt(Mathf.Min(t[0].x, Mathf.Min(t[1].x, t[2].x))); i <= Mathf.FloorToInt(Mathf.Max(t[0].x, Mathf.Max(t[1].x, t[2].x))); i++)
                    for (int j = Mathf.FloorToInt(Mathf.Min(t[0].z, Mathf.Min(t[1].z, t[2].z))); j <= Mathf.FloorToInt(Mathf.Max(t[0].z, Mathf.Max(t[1].z, t[2].z))); j++)
                    { long k = ((long)i << 32) ^ (uint)j; List<int> l; if (!oh.TryGetValue(k, out l)) { l = new List<int>(); oh[k] = l; } l.Add(id); }
            }
        }
        System.Func<GameObject, int> Count = g =>
        {
            var pt = Hifu_OpenUp(g); if (pt.Count == 0) return 0;
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var t in pt) foreach (var v in t) { x0 = Mathf.Min(x0, v.x); x1 = Mathf.Max(x1, v.x); z0 = Mathf.Min(z0, v.z); z1 = Mathf.Max(z1, v.z); }
            int n = 0;
            for (float x = x0 + 0.05f; x < x1; x += 0.1f)
                for (float z = z0 + 0.05f; z < z1; z += 0.1f)
                {
                    List<int> l; if (!oh.TryGetValue(((long)Mathf.FloorToInt(x) << 32) ^ (uint)Mathf.FloorToInt(z), out l)) continue;
                    float top = float.NaN, y;
                    foreach (var t in pt) if (Hifu_TriYAt(t, x, z, out y) && (float.IsNaN(top) || y > top)) top = y;
                    if (float.IsNaN(top)) continue;
                    foreach (var id in l) if (Hifu_TriYAt(ot[id], x, z, out y) && Mathf.Abs(y - top) < tol) { n++; break; }
                }
            return n;
        };
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy || ot.Count == 0) continue;
            int n0 = Count(g); if (n0 == 0) continue;
            int n1 = n0; float dropped = 0f;
            //   相手の面が斜め・段で下にも同じ高さの面がある所は、無くなるまで drop ずつ(上限 maxDrop)
            while (!measureOnly && n1 > 0 && dropped + drop <= maxDrop + 1e-5f) { g.transform.position -= Vector3.up * drop; dropped += drop; n1 = Count(g); }
            if (dropped > 0f) lowered++;
            sb.Append(" " + g.name + " " + n0 + "→" + n1 + (dropped > 0f ? "(" + dropped.ToString("F2") + ")" : ""));
        }
        report = (measureOnly ? "同じ高さで重なる駒:" : "同じ高さで重なる駒を " + drop.ToString("F2") + " ずつ下げた(上限 " + maxDrop.ToString("F2") + "):") + (sb.Length > 0 ? sb.ToString() : " 無し");
        return lowered;
    }
    static List<Vector3[]> Hifu_OpenUp(GameObject g) { return OpenUpTris(g, true); }
    static bool Hifu_TriYAt(Vector3[] t, float x, float z, out float y) { return TriYAt(t, x, z, out y); }
}
