// 野面の乱積みの土留めを一本の折れ線へ据える — EdoBuild の partial(2026-09-25・EDO-0430)
//   駒は 1間(切り口 X = ±0.909)の直線の駒・出隅 90° の隅の駒・段の境の勾配の駒(`EdoAssets.Own.SannoNozura*`)。
//   ⭐ 置き方の4手(docs/oki-kata.md §2): 固定側(隅・段の境・端の相手)を先に置く → 間の駒は前の駒の切り口へ
//      **実メッシュで測って**突き付ける(連鎖)→ 高さは天端の帯の実メッシュを天端の線へ・見え面は天端の前の縁を線へ
//      → 事後に寄せる関数は持たない。⛔ ピボットで並べない(置いた後に必ず測って寄せる)。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>野面の土留めの一本(隅と段の境で折れ・継ぐ)。</summary>
    public class NozuraWall
    {
        /// <summary>天端の線の折れ線(世界 xz)。</summary>
        public List<Vector2> nodes = new List<Vector2>();
        /// <summary>走り s → 設計の天端の高さ(段の境は階段状のまま渡す。流すのは勾配の駒)。</summary>
        public Func<float, float> crestAt;
        /// <summary>段の境の走り s(天端がそこで変わる)。勾配の駒をここへ中心で据える。</summary>
        public List<float> steps = new List<float>();
        /// <summary>直線の駒 (見付, 勾配, 個体) → パス。</summary>
        public Func<float, float, int, string> straight;
        /// <summary>隅の駒 (見付, 個体) → パス。</summary>
        public Func<float, int, string> kado;
        /// <summary>出隅の折れが 90° でない隅の駒(折れ°, 見付, 通し番号)→ パス(2026-10-05・EDO-0502 第18巡)。折れ 20〜60° に据える。
        /// 腕1 = 局所 −X(見え面 +Z)・腕2 = 局所 (cos 折れ, 0, −sin 折れ)。焼いていない組は null か無いパス ⇒ ⚠ を刷って据えない(従前の楔のまま)。</summary>
        public Func<float, float, int, string> kadoDeg = EdoAssets.Own.SannoNozuraKadoDeg;
        /// <summary>段の境の駒 (+X へ上がるか, 個体) → パス。</summary>
        public Func<bool, int, string> dan;
        /// <summary>打ち切りの駒 (+X へ上がるか, 個体) → パス(端に相手が居ないとき)。</summary>
        public Func<bool, int, string> kiri;
        /// <summary>(x, z) → 見え面の足元の面(指図の `foot` の平場)の高さ。平場の外は NaN。
        /// ⭐ 平場の中は皮がこの高さで描く ⇒ 見付はここで取る(2m 格子の地表は縁の節点に引かれて面より高く出る)。
        /// 平場の外は描かれた地表で取る。</summary>
        public Func<float, float, float> footAt;
        /// <summary>焼いてある見付(小さい順)。</summary>
        public float[] heights;
        /// <summary>始まり・終わりの端が突き付ける相手の駒(無ければ打ち切り)。</summary>
        public List<GameObject> startTo = new List<GameObject>(), endTo = new List<GameObject>();
        /// <summary>隅の腕の中へ入り得る相手(石段の袖)── 隅の腕が呑む量を測る(<see cref="KadoArmNeeds"/>・2026-09-26・EDO-0437 第7巡)。</summary>
        public IList<GameObject> kadoAbut;
        /// <summary>始まり・終わりの端が**入隅の通す側**(相手の土留めがこちらの見え面へ突き付ける)── 端は線の端点のまま・打ち切りの駒を使わない
        /// (2026-09-26・EDO-0437)。</summary>
        public bool startThrough, endThrough;
        /// <summary>見え面(低い側)を測る地表 ── 設計面(造成の面)。null なら描かれた地表。⭐ 据えた土留めの天端の下は皮・Tuck で
        /// 下げてあるので、描かれた地表で測ると隣の土留めの際で低い側を取り違える(切り込みの返し 1.7m が前庭の側を向いた・2026-09-26)。</summary>
        public Func<float, float, float> faceGroundAt;
        /// <summary>片端を斜めの鉛直面で切った駒 (角°, 切る端が局所 +X か, 見え面の側が長いか, 見付, 個体) → パス(2026-09-26・EDO-0437)。
        /// 端の相手の面が走りと斜めに交わるとき、その端に据える(<see cref="EdoAssets.Own.SannoNozuraKiriEnd"/>)。null なら使わない。</summary>
        public Func<float, bool, bool, float, int, string> kiriEnd;
        /// <summary>走り s → (低い側の地盤, 高い側の地盤)(指図の縦断 `profile` の列。無い所は NaN)。⭐ 駒ごとの見え面は、線のすぐ両脇(±0.35m)の
        /// 設計面がどちらの地盤に揃うかで決める(2026-09-26・EDO-0437)── 離れで測ると細い裏込めの帯の外(区画の線の際で下がる地盤)を拾い、
        /// 見付 0.3 未満の所では票が許容 0.05 を割って区間の向きへ戻った(前庭の E の南 5m が外を向いた)。</summary>
        public Func<float, Vector2> sidesAt;
        /// <summary>走り s → 名指した見え面の向き(<see cref="NozuraSeg.face"/>・無い所は zero)。在れば地表の低い側の票より先に採る
        /// (2026-10-07 EDO-0502 第42巡: 袖の坂を前の面より先へ延ばした低い端で、背の土が前より低く票が割れ、端の駒が背へ向いた ── 裏表)。</summary>
        public Func<float, Vector2> faceAt;
        /// <summary>小口を相手の法で切った短い駒 (天端の長さ, 切る端が局所 +X か, 見付) → パス(2026-09-26・EDO-0437 第3巡)。
        /// 入隅の可動側の端(<see cref="startConcave"/> / <see cref="endConcave"/>)で、鉛直な小口の代わりに据える(<see cref="EdoAssets.Own.SannoNozuraNoriEnd"/>)。null なら使わない。</summary>
        public Func<float, bool, float, string> noriEnd;
        /// <summary>始まり・終わりの端が**入隅の可動側**(通す側の見え面 = 法の面へ突き付ける)。</summary>
        public bool startConcave, endConcave;
        /// <summary>走りの範囲 (s の始まり, s の終わり, 見付の下限) ── 端の隅の駒と返しの駒の見付を揃える所(指図 kadoReturnUniform「隅の H を揃え、H の違う駒を並べない」・
        /// EDO-0502 第41巡)。範囲に掛かる駒は見付をこの値以上の焼いた段にする(高い段は沈める)。</summary>
        public List<Vector3> minHRanges = new List<Vector3>();
        /// <summary>走りの範囲 (s の始まり, s の終わり, 焼いた H) ── 駒の中ほどが範囲に入る駒は見付をこの H **ちょうど**にする(指図 sodeSlope 追記 2026-10-07
        /// 「低い端は水平の H0600 を一駒」・EDO-0502 第42巡)。<see cref="NozuraSeg.fixHEnd"/> から。</summary>
        public List<Vector3> fixHRanges = new List<Vector3>();
        /// <summary>走りの範囲 (s の始まり, s の終わり) ── 駒の中ほどが範囲に入る駒は勾配の駒を使わず水平(G+000)に据える(指図 sodeSlope 追記 2026-10-09
        /// 「最初の駒1つ分は天端を 21.0 で水平」【硬】・EDO-0502 第64巡)。<see cref="NozuraSeg.flatEnd"/> から。</summary>
        public List<Vector2> flatRanges = new List<Vector2>();
    }

    /// <summary>**野面の見え面の足元の前の地盤**(2026-10-11 EDO-0502 第107巡)。線 <paramref name="q"/> は天端の前の縁 ── 法尻は
    /// 法 <paramref name="batter"/> ×(天端 − 足元)だけ見え面の側 <paramref name="face"/> へ出る。法尻から <paramref name="off"/> 前の地盤を
    /// 不動点で求める(足元 g → 法尻 b·(t − g) → その前の g' … 3 回・見た中の最も低い値)。<paramref name="footAt"/>(指図の足元の面)が NaN なら
    /// <paramref name="groundAt"/>。batter が NaN か 0 なら従前どおり線から off。
    /// 硬い: 見付は法尻の前で取る(⛔ 法の下の地盤で見付を取らない ── 足元を切り下げた所で底が浮く)。
    /// 当たる先: PlaceNozuraRun の見付・PlaceNozuraNet の端の見付(endExpose)・積み止めの見付 ── 野面の土留めすべて(岡部・山王・土井。各邸を流し直すと
    /// 足元の前が下る所で駒が深く根入れする側へ変わる)。</summary>
    public static float FootAhead(Func<float, float, float> footAt, Func<float, float, float> groundAt, Vector2 q, Vector2 face, float off, float top, float batter)
    {
        float d = off, gMin = float.NaN;
        for (int it = 0; it < 4; it++)
        {
            float x = q.x + face.x * d, z = q.y + face.y * d;
            float g = footAt != null ? footAt(x, z) : float.NaN; if (float.IsNaN(g)) g = groundAt(x, z);
            if (float.IsNaN(g)) break;
            gMin = float.IsNaN(gMin) ? g : Mathf.Min(gMin, g);
            if (float.IsNaN(batter) || batter <= 1e-4f || float.IsNaN(top)) break;
            float d2 = off + batter * Mathf.Max(0f, top - g);
            if (Mathf.Abs(d2 - d) < 0.02f) break;
            d = d2;
        }
        return gMin;
    }

    static readonly Dictionary<string, float> _nozBatter = new Dictionary<string, float>();
    /// <summary>run の直線の駒の見え面の法(<see cref="FaceBatterOf"/> を H4.8 の駒で一度だけ測る)。測れなければ NaN。</summary>
    static float NozuraBatter(NozuraWall w)
    {
        if (w == null || w.straight == null) return float.NaN;
        string p = null; try { p = w.straight(4.8f, 0f, 0); } catch { p = null; }
        if (string.IsNullOrEmpty(p)) return float.NaN;
        float b; if (_nozBatter.TryGetValue(p, out b)) return b;
        b = FaceBatterOf(p); _nozBatter[p] = b; return b;
    }

    /// <summary>**名指した見え面は「側」だけ採り、向きは区間の線の法線にする**(2026-10-09・EDO-0502 第64巡・施主「石垣の部材のつなぎ目で段差」)。
    /// 指図・ビルダーが名指す見え面(<see cref="NozuraSeg.face"/> ── 石段の芯へ・背の逆)は区間の線と直交するとは限らない。
    /// 石段の脇の返しは天端の線が石段の軸から 2〜9° 振れる(見付が段ごとに 0.3 増え、法 3分で天端の前の縁が 0.09 ずつ退く ── StairSideCrestLines)のに、
    /// 見え面を軸の法線のまま据えたため、駒ごとに天端の前の縁を線へ寄せると継ぎ目ごとに見え面が 0.08〜0.42 前後へずれ(鋸の歯)、走りの向きに 0.05〜0.25 の口が開いて
    /// 土が覗いた(岡部 TW_Kado_Shumen_Side0/1・TW_Higashi_Tsuyo_Side0/1・積み止め)。⇒ 線の法線のうち名指した側を返す(一つの法の面に揃う)。
    /// 名指した向きが線とほぼ平行(|内積| &lt; 0.5)なら名指しのまま。【硬】(隙 0)。
    /// 当たる先: 名指した見え面を持つ野面の区間すべて(岡部 石段の脇の返し・袖の坂・腰の返し、PlaceNozuraNet の端の見立て・積み止め)。</summary>
    public static Vector2 FaceAcross(Vector2 named, Vector2 dir)
    {
        Vector2 n = new Vector2(dir.y, -dir.x); if (n.sqrMagnitude < 1e-8f) return named; n.Normalize();
        float d = Vector2.Dot(named.normalized, n);
        if (Mathf.Abs(d) < 0.5f) return named;
        return d > 0f ? n : -n;
    }

    /// <summary>**野面の乱積みの土留めを据える**(2026-09-25・EDO-0430)。見え面 = 描かれた地表の低い側
    /// (<see cref="LowSide"/> を区間ごとに)、天端 = <see cref="NozuraWall.crestAt"/>、見付 = 天端 − 見え面の足元の地表
    /// (焼いてある段の小さい方から、床が地表の下に入る最小)。
    /// <para>順: ① 出隅(折れ 60° 以上・凸)へ隅の駒・段の境へ勾配の駒を据える ② 端の相手の実面を測って端の走りを決める
    /// ③ 固定の駒の間を 1間の駒で埋める ── 駒数は間の実長から丸め、**走り方向だけ伸縮**(0.85〜1.20・切り口の形は変わらない)、
    /// 前の駒の切り口(実メッシュの走りへの射影の最大)へ次の駒の切り口(最小)を突き付けて連ねる。
    /// 高さは天端の帯(0.2m 角の筋ごとの最高点の中央値)を天端の線へ、見え面は天端の前の縁を線へ(<see cref="FaceWallToLine"/>)。</para>
    /// 返り値 = 据えた駒と見え面の向き。<paramref name="log"/> に継ぎ目の隙・端の隙・天端の差の最悪値を刷る。
    /// 当たる先: 野面の乱積みの土留めすべて(山王 本殿の西 TW_Nozura_*・前庭の土留め・男坂の下の見切り、今後の各邸の庭の土留め)。</summary>
    public static List<KeyValuePair<GameObject, Vector2>> PlaceNozuraRun(NozuraWall w, Func<float, float, float> groundAt,
        float probe, Transform parent, string name, System.Text.StringBuilder log)
    {
        var res = new List<KeyValuePair<GameObject, Vector2>>();
        var P = w.nodes; int m = P.Count; if (m < 2) return res;
        Func<float, float, float> faceG = w.faceGroundAt ?? groundAt;
        const float W = 1.818f, HALF = 0.909f;
        // 区間ごとの走りの向き・弧長・見え面(低い側)
        var dir = new Vector2[m - 1]; var face = new Vector2[m - 1]; var s0 = new float[m];
        for (int i = 0; i + 1 < m; i++)
        {
            float l = Vector2.Distance(P[i], P[i + 1]); dir[i] = (P[i + 1] - P[i]) / Mathf.Max(l, 1e-6f); s0[i + 1] = s0[i] + l;
            int vn, vx; var lo = LowSide(P[i], P[i + 1], faceG, probe, 0.05f, null, out vn, out vx);
            face[i] = lo;
            if (w.faceAt != null) { var fz = w.faceAt((s0[i] + s0[i + 1]) * 0.5f); if (fz.sqrMagnitude > 0.5f) { face[i] = FaceAcross(fz, dir[i]); vx = 0; } }
            if (vx > 0) log.AppendLine("    ⚠ " + name + " 区間 " + i + " で低い側が割れた(" + vn + " 対 " + vx + ")");
        }
        for (int i = 0; i + 1 < m; i++)   // 票の無い区間は隣の区間の向きを回して借りる
            if (face[i] == Vector2.zero)
            {
                int j = i > 0 && face[i - 1] != Vector2.zero ? i - 1 : (i + 2 < m && face[i + 1] != Vector2.zero ? i + 1 : -1);
                Vector2 rn = new Vector2(dir[i].y, -dir[i].x);
                face[i] = rn;
                // 隣の区間と同じ側(走りの右か左か)を見え面にする
                if (j >= 0) { float cross = dir[j].x * face[j].y - dir[j].y * face[j].x; float c2 = dir[i].x * rn.y - dir[i].y * rn.x; face[i] = Mathf.Sign(cross) == Mathf.Sign(c2) ? rn : -rn; }
                log.AppendLine("    ⚠ " + name + " 区間 " + i + " は両側の地表の差が無い — " + (j >= 0 ? "隣の区間と同じ側" : "走りの右") + "を見え面にした");
            }
        float L = s0[m - 1];
        Func<float, int> segOf = s => { for (int i = 0; i + 1 < m; i++) if (s <= s0[i + 1] + 1e-4f) return i; return m - 2; };
        Func<float, Vector2> at = s => { int i = segOf(s); return P[i] + dir[i] * (s - s0[i]); };
        // 見付: 天端 − 見え面の足元の前(法尻から前へ 0.25 と 0.7)の地表の最小 ⇒ 焼いてある段のうち床がその下に入る最小
        //   ⭐ 線は天端の前の縁 ── 法尻はそこから 法 ×(天端 − 足元)前に出る(H4.8 で 1.4m)。線から 0.25/0.7 で測ると法の下(見え面の裏の地盤)を
        //   読み、足元を切り下げた所(背の路地の床)で見付を 1m 少なく取って駒の底が浮き、皮が浮いた底の下を埋めて見え面の前に土の板が立った
        //   (岡部 TW_Higashi_Se 15 駒・+0.06〜+0.93・2026-10-11 EDO-0502 第107巡)⇒ <see cref="FootAhead"/> で法尻の前を測る。
        float batterW = NozuraBatter(w);
        Func<float, float, float, int, float> needH = (sa, sb2, top, si) =>
        {
            // ⭐ top = NaN は**天端が線に沿って傾く駒**(勾配の駒 ── 床も天端と一緒に傾く): 見付 = 走りの各点の (天端の線 − 足元) の最大
            //   (= 低い側の端の地盤で取る・2026-10-11 EDO-0502 第104巡)。top が数なら従前どおり 天端 − 足元の最小。
            float need = float.MinValue;
            for (float s = sa; s <= sb2 + 1e-4f; s += Mathf.Max(0.1f, (sb2 - sa) / 6f))
            { int k = Mathf.Clamp(si < 0 ? segOf(s) : si, 0, m - 2); Vector2 q = at(Mathf.Clamp(s, 0f, L));
              float t = float.IsNaN(top) ? w.crestAt(Mathf.Clamp(s, 0f, L)) : top; if (float.IsNaN(t)) continue;
              foreach (float off in new[] { 0.25f, 0.7f })
              { float g = FootAhead(w.footAt, groundAt, q, face[k], off, t, batterW);
                if (!float.IsNaN(g)) need = Mathf.Max(need, t - g); } }
            if (need == float.MinValue) need = float.IsNaN(top) ? 0f : top - float.MaxValue;
            foreach (var r in w.minHRanges) if (sb2 >= r.x && sa <= r.y) need = Mathf.Max(need, r.z);   // 端の隅の組の見付を揃える(kadoReturnUniform)
            { float midS = (sa + sb2) * 0.5f; foreach (var r in w.fixHRanges) if (midS >= r.x && midS <= r.y) return r.z; }   // 端の一駒の H を名指す(sodeSlope の低い端)
            foreach (var h in w.heights) if (h >= need - 1e-3f) return h;
            return w.heights[w.heights.Length - 1];
        };
        // ⚠ 野面の駒の天端の帯 = 0.2m 角の筋ごとの最高点の中央値(頭は天端の ±0.08)
        Func<GameObject, float> crestOf = g =>
        {
            var cells = new Dictionary<long, float>();
            // 駒の走りの中ほど(±0.25m)だけで測る ── 勾配の駒は端ほど天端が上下する
            Vector3 cc = RB(g).center; Vector3 ax = g.transform.right;
            foreach (var v in Body(g.transform, 999999))
            { if (Mathf.Abs(Vector3.Dot(v - cc, new Vector3(ax.x, 0f, ax.z).normalized)) > 0.25f) continue;
              long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
              float y; if (!cells.TryGetValue(key, out y) || v.y > y) cells[key] = v.y; }
            var ys = new List<float>(cells.Values); ys.Sort(); if (ys.Count == 0) return float.NaN;
            // 天端の面の筋だけ(上位 40%)── 見え面の法の筋は天端より低い
            int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); return top[top.Count / 2];
        };
        // 走りへの射影の [最小, 最大](天端の帯より下の全頂点)
        Func<GameObject, Vector2, Vector2, float[]> span = (g, o, d) =>
        { float a0 = float.MaxValue, a1 = float.MinValue; foreach (var v in Body(g.transform, 999999)) { float s = (v.x - o.x) * d.x + (v.z - o.y) * d.y; a0 = Mathf.Min(a0, s); a1 = Mathf.Max(a1, s); } return new[] { a0, a1 }; };
        // ⭐ **重ねの端の版(Nozura2)は継ぎ目の線で連ねる**(2026-10-11・EDO-0502 第104巡・施主「石垣の部材の境目の隙間および段差」)。
        //   Nozura2 は両端を継ぎ目の線(局所 X = ±0.909)から 0.02 + 0.026·深さ だけ隣の石へ延ばしてある(折れの凸の側に楔が開かない)。
        //   実メッシュの走りの射影の端(span)で連ねると重ねの分(H4.8 で片側 0.15)だけ駒が離れる ⇒ 射影の端から 伸縮 × 重ねの最大(部材の札
        //   EdoAssets.Own.Nozura2OverlapMax(焼いた見付))を内へ引いた所を継ぎ目の線とする(測った射影の端 − 札の重ね ── 基準点では置かない)。
        //   旧の駒(Sanno_Nozura_*)は従前どおり射影の端。当たる先: Nozura2 を渡す野面の run すべて(いまは岡部 Stage2b・道の縁の野面)。
        Func<string, float> bakedH = pth => { var mh = System.Text.RegularExpressions.Regex.Match(pth ?? "", @"_H(\d{4})_"); return mh.Success ? int.Parse(mh.Groups[1].Value) / 1000f : float.NaN; };
        Func<GameObject, string, Vector2, Vector2, float[]> jspan = (g, pth, o, d) =>
        {
            var s2 = span(g, o, d); if (!EdoAssets.Own.IsNozura2(pth)) return s2;
            float hb = bakedH(pth); if (float.IsNaN(hb)) return s2;
            float ov = Mathf.Abs(g.transform.lossyScale.x) * EdoAssets.Own.Nozura2OverlapMax(hb);
            return new[] { s2[0] + ov, s2[1] - ov };
        };
        bool isN2 = w.straight != null && EdoAssets.Own.IsNozura2(w.straight(1.2f, 0f, 0));
        // 焼いた勾配(名の G・局所 +X へ・伸縮前)
        Func<string, float> bakedG = pth => { var mg = System.Text.RegularExpressions.Regex.Match(pth ?? "", @"_G([+-]\d{3})_"); return mg.Success ? int.Parse(mg.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) / 1000f : 0f; };
        // ⭐ 勾配の駒の天端は**勾配を差し引いて**測る ── 天端の帯の上位 40% を採る crestOf は、傾いた天端では高い側の筋に偏る(勾配 0.69 で +0.1 前後)。
        //   局所 +X の世界の勾配(gW)で頂点の高さを駒の中ほどへ戻してから同じ帯の中央値を採る(= 中ほどの天端)。
        Func<GameObject, float, float> crestOfG = (g, gW) =>
        {
            var cells = new Dictionary<long, float>();
            Vector3 cc = RB(g).center; Vector3 ax = g.transform.right; Vector3 axh = new Vector3(ax.x, 0f, ax.z).normalized;
            foreach (var v in Body(g.transform, 999999))
            { float u = Vector3.Dot(v - cc, axh); if (Mathf.Abs(u) > 0.35f) continue; float y = v.y - gW * u;
              long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
              float y0; if (!cells.TryGetValue(key, out y0) || y > y0) cells[key] = y; }
            var ys = new List<float>(cells.Values); ys.Sort(); if (ys.Count == 0) return float.NaN;
            int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); return top[top.Count / 2];
        };
        // ⭐ 見え面は**駒の走りごと**に描かれた地表で測る(2026-09-26・EDO-0437)── 区間の途中で高低が入れ替わる土留め
        //   (山王 前庭の W・E)は区間の票が一つの向きしか取れず、半分の駒が土の側を向いた。城の石垣の駒ごとの flipLocal と同じ考え。
        //   票が無い(両側の地表の差が無い)所は区間の向きのまま。
        Func<int, float, float, Vector2> faceOn = (si, sa, sb) =>
        {
            float a0 = Mathf.Clamp(sa, s0[si], s0[si + 1]), b0 = Mathf.Clamp(sb, s0[si], s0[si + 1]);
            if (w.faceAt != null) { var fz = w.faceAt((a0 + b0) * 0.5f); if (fz.sqrMagnitude > 0.5f) return FaceAcross(fz, dir[si]); }   // 名指した見え面(袖の坂)── 側だけ採り、向きは区間の法線(FaceAcross)
            if (b0 - a0 < 0.3f) return face[si];
            if (w.sidesAt != null)
            {   // 指図の縦断の低い側・高い側の地盤に、線の両脇の設計面のどちらが揃うか
                Vector2 nR = new Vector2(dir[si].y, -dir[si].x); float vR = 0f; int nv = 0;
                for (int q = 0; q < 3; q++)
                {
                    float ss = a0 + (b0 - a0) * (q + 0.5f) / 3f; var lh = w.sidesAt(ss);
                    if (float.IsNaN(lh.x) || float.IsNaN(lh.y) || Mathf.Abs(lh.y - lh.x) < 0.03f) continue;
                    Vector2 pp = P[si] + dir[si] * (ss - s0[si]);
                    float gR = faceG(pp.x + nR.x * 0.35f, pp.y + nR.y * 0.35f), gL = faceG(pp.x - nR.x * 0.35f, pp.y - nR.y * 0.35f);
                    if (float.IsNaN(gR) || float.IsNaN(gL)) continue;
                    float right = Mathf.Abs(gR - lh.x) + Mathf.Abs(gL - lh.y), left = Mathf.Abs(gL - lh.x) + Mathf.Abs(gR - lh.y);
                    vR += left - right; nv++;
                }
                if (nv > 0 && Mathf.Abs(vR) > 1e-3f) return vR > 0f ? nR : -nR;
            }
            Vector2 pa = P[si] + dir[si] * (a0 - s0[si]), pb = P[si] + dir[si] * (b0 - s0[si]);
            int vn, vx; var lo = LowSide(pa, pb, faceG, probe, 0.05f, null, out vn, out vx);
            return lo == Vector2.zero || vn == vx ? face[si] : lo;
        };
        // ⭐ 天端の勾配は**駒の +X へ**測って渡す(2026-09-26・EDO-0437)── 走りの伸縮 sc で勾配は 1/sc に寝るので、焼いた勾配 = 求める勾配 × sc。
        //   部材の側(EdoAssets.Own.SannoNozura)が焼いてある最も近い勾配へ寄せる。
        Func<float, float, Vector2, int, float> gradeX = (sMid, halfLen, X, si) =>
        {
            float sa = Mathf.Clamp(sMid - halfLen, 0f, L), sb = Mathf.Clamp(sMid + halfLen, 0f, L);
            if (sb - sa < 0.2f) return 0f;
            float ca = w.crestAt(sa), cb = w.crestAt(sb); if (float.IsNaN(ca) || float.IsNaN(cb)) return 0f;
            float gRun = (cb - ca) / (sb - sa);
            return Vector2.Dot(X, dir[si]) >= 0f ? gRun : -gRun;
        };
        float worstCrest = 0f; int idx = 0; int flipped = 0; float worstGradeErr = 0f;
        // 置いた駒を天端の線へ据える(高さ・見え面)── 測って寄せる
        Action<GameObject, float, Vector2, Vector2> seat0 = (g, crest, fN, lineA) =>
        {
            FaceWallToLine(g, fN, lineA);
            float c = crestOf(g); if (!float.IsNaN(c)) g.transform.position += Vector3.up * (crest - c);
            float c2 = crestOf(g); if (!float.IsNaN(c2)) worstCrest = Mathf.Max(worstCrest, Mathf.Abs(c2 - crest));
        };
        Action<GameObject, float, Vector2, Vector2> seat = seat0;

        // ---- ① 固定の駒: 出隅と段の境 ----------------------------------------------------------
        var fixedSpans = new List<float[]>();                      // [s の始まり, s の終わり](走りの座標)
        for (int i = 1; i + 1 < m; i++)
        {
            float turn = Vector2.Angle(dir[i - 1], dir[i]);
            // ⭐ 折れ 20〜60° は折れの角で焼いた隅の駒を据える(2026-10-05・EDO-0502 第18巡)── 直線の駒の突き付けでは外の角に足元ほど広い楔
            //   (法の出 0.3×見付 が両腕で開く・岡部 TW_Higashi_Hokuto 49.4° で足元 0.79)が開いた。20° 未満は従前どおり直線の駒の継ぎ。
            //   当たる先: 野面の土留めの 20〜60° の出隅すべて(岡部 TW_Higashi_Hokuto・TW_Kado_Sode ほか、山王・松江松平・土井・類型の縁の野面)。
            bool oblique = turn < 60f;
            if (oblique && turn < 20f) continue;
            // 隅の二つの見え面は隅の際(腕の長さ 1間)で測る ── 区間の途中で入れ替わる土留めは区間の票と隅の際が違う
            Vector2 f1 = faceOn(i - 1, s0[i] - W, s0[i]), f2 = faceOn(i, s0[i], s0[i] + W);
            // 凸(出隅): 次の区間は前の区間の見え面の裏(−f1)へ向かう
            if (Vector2.Dot(dir[i], f1) > -0.3f) { log.AppendLine("    ⚠ " + name + " 折れ " + i + " は入隅 — 隅の駒は据えない"); continue; }
            float sc = s0[i]; float crest = w.crestAt(sc);
            float hk = needH(sc - HALF, sc + HALF, crest, -1);
            // 局所 +Z = 片方の見え面・+X = もう片方(+Z = +X を反時計 90°)
            Func<Vector2, Vector2> ccw = v => new Vector2(-v.y, v.x);
            Vector2 X = Vector2.Dot(ccw(f2), f1) > 0f ? f2 : f1; Vector2 Z = ccw(X);
            float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
            string path = oblique ? (w.kadoDeg != null ? w.kadoDeg(turn, hk, idx) : null) : w.kado(hk, idx);
            // ⭐ 折れ 60° 以上でも 90° から 5° を超えて外れる隅は、その折れで焼いた隅の駒が在ればそれを据える(2026-10-09・EDO-0502 第66巡)──
            //   折れ 103.4° に Kado90 を据えて 13.4° の楔の隙が開き、土が帯で見えた(岡部 TW_Kado_Shumen_Side0_0_kado11)。焼いていなければ従前の Kado90。
            //   向きは折れの駒と同じ式(腕1 = 局所 −X・腕2 = (cos deg, 0, −sin deg))── deg = 90 で Kado90 の向きと一致する。
            //   当たる先: 野面の土留めの 60° 以上で直角でない出隅すべて(焼いた組だけ効く ── いまは Kado103 × H4.80)。
            if (!oblique && Mathf.Abs(turn - 90f) > 5f && w.kadoDeg != null)
            {
                string pd = w.kadoDeg(turn, hk, idx);
                if (pd != null && System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, pd))) { path = pd; oblique = true; }
                else log.AppendLine("    ⚠ " + name + " 隅 " + i + ": 折れ " + turn.ToString("F1") + "° の隅の駒が焼いていない(見付 " + hk + "・" + (pd ?? "null") + ")── Kado90 のまま(外の角に楔)");
            }
            if (oblique)
            {
                // 腕1 は「見え面 F を反時計 90° 回した向き」へ伸びる腕(局所 +Z = F・−X = 腕1)。腕1 が前の区間か次の区間かは隅の巡りで決まる。
                Vector2 armA0 = -dir[i - 1], armB0 = dir[i];
                Vector2 F = Vector2.Dot(ccw(f1), armA0) >= Vector2.Dot(ccw(f2), armB0) ? f1 : f2;
                yaw = Mathf.Atan2(F.x, F.y) * Mathf.Rad2Deg;
            }
            if (path == null || !System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, path)))
            {
                if (oblique) log.AppendLine("    ⚠ " + name + " 隅 " + i + ": 折れ " + turn.ToString("F1") + "° の隅の駒が焼いていない(見付 " + hk + "・" + (path ?? "null") + ")── 直線の駒の継ぎのまま(外の角に楔)");
                else log.AppendLine("    ⛔ " + name + " 隅 " + i + ": 隅の駒が焼いていない(見付 " + hk + ")— 据えない");
                continue;
            }
            var kg = Place(path, new Vector3(P[i].x, crest - hk, P[i].y), yaw, Vector3.one, parent, name + "_kado" + i);
            // ⭐ 隅の駒の天端は**二本の腕の中ほど**で測る(2026-10-04・EDO-0502 第16巡)── crestOf は外接箱の芯を通る筋で測るので、L 字の駒では
            //   芯の筋が隅の内の法の石を拾い、天端を 0.4〜0.6 低く読んで駒を持ち上げた(岡部 TW_Higashi_Hokuto の隅 2 つ: 腕の天端 16.70/16.89・直線の 16.31)。
            //   腕ごとに直線の駒と同じ測り(走りに直交する ±0.25 の筋・上位 40% の中央値)で読み、高い方を天端とする(石の頭を run の天端より上へ出さない)。
            //   当たる先: 野面の土留めの出隅の駒すべて(岡部 TW_Higashi_Hokuto・山王 前庭の縁の出隅 *_kado*)。
            Vector2 armA = -dir[i - 1], armB = dir[i];
            Func<GameObject, float> crestKado = g =>
            {
                float best = float.NaN;
                foreach (var arm in new[] { armA, armB })
                {
                    var cells = new Dictionary<long, float>();
                    Vector3 cc = new Vector3(P[i].x + arm.x * 1.0f, 0f, P[i].y + arm.y * 1.0f);
                    foreach (var v in Body(g.transform, 999999))
                    {
                        if (Mathf.Abs((v.x - cc.x) * arm.x + (v.z - cc.z) * arm.y) > 0.25f) continue;
                        long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
                        float y; if (!cells.TryGetValue(key, out y) || v.y > y) cells[key] = v.y;
                    }
                    var ys = new List<float>(cells.Values); if (ys.Count == 0) continue; ys.Sort();
                    int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); float c = top[top.Count / 2];
                    if (float.IsNaN(best) || c > best) best = c;
                }
                return float.IsNaN(best) ? crestOf(g) : best;
            };
            // 稜線を二本の天端の線の交点へ: 天端の帯の前の縁を各々の見え面の向きで測って寄せる
            //   ⭐ 寄せて測るを収まるまで(EdoBuild.Converge・EDO-0454)── 決め打ちの2巡を置き換えた。
            //   稜線と天端はどちらも**狙い**(柔らかい・許容0の欠陥ではない)⇒ 未達は ⚠ で刷って据える(従前どおり退けない)。
            {
                Vector2 f1c = f1, f2c = f2, Pi = P[i]; float crestC = crest; var kgc = kg;
                Func<Vector2> edges = () =>
                {
                    var vs = Body(kgc.transform, 999999); float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
                    float e1 = float.MinValue, e2 = float.MinValue;
                    foreach (var v in vs) if (v.y >= top - 0.15f)
                    { Vector2 r = new Vector2(v.x, v.z) - Pi; e1 = Mathf.Max(e1, Vector2.Dot(r, f1c)); e2 = Mathf.Max(e2, Vector2.Dot(r, f2c)); }
                    return new Vector2(e1, e2);
                };
                var os = Converge(new[]
                {
                    Tori.Custom(kg.name + " 稜線", kg, false, -0.002f, 0.002f,
                        () => { var e = edges(); return Mathf.Abs(e.x) >= Mathf.Abs(e.y) ? e.x : e.y; },
                        () => { var e = edges();
                                // ⭐ 二つの見え面の向きが直交しない(折れ 20〜60° の隅)ときは d·f1 = e1・d·f2 = e2 を解く(2026-10-05・EDO-0502 第18巡)
                                //   ── f1·e1 + f2·e2 を引くだけだと斜交で過不足が出て 2 巡で 0.04〜0.05 残った。90° では従前と同じ。
                                float det = f1c.x * f2c.y - f1c.y * f2c.x; Vector3 d;
                                if (Mathf.Abs(det) > 0.2f) { float dx = (e.x * f2c.y - e.y * f1c.y) / det, dz = (f1c.x * e.y - f2c.x * e.x) / det; d = new Vector3(dx, 0f, dz); }
                                else d = new Vector3(f1c.x * e.x + f2c.x * e.y, 0f, f1c.y * e.x + f2c.y * e.y);
                                kgc.transform.position -= d; return d.magnitude; }),
                    Tori.Custom(kg.name + " 天端", kg, false, -0.002f, 0.002f,
                        () => { float c = crestKado(kgc); return float.IsNaN(c) ? float.NaN : c - crestC; },
                        () => { float c = crestKado(kgc); if (float.IsNaN(c)) return float.NaN; kgc.transform.position += Vector3.up * (crestC - c); return Mathf.Abs(crestC - c); }),
                });
                if (os.Reason.Length > 0) log.AppendLine("    ⚠ " + name + " 隅 " + i + ": " + os.Summary());
            }
            { float c2 = crestKado(kg); if (!float.IsNaN(c2)) worstCrest = Mathf.Max(worstCrest, Mathf.Abs(c2 - crest)); }
            // ⭐ 隅の腕の中へ石段の袖が入るか(硬い・許容0 のめり込み ── 2026-09-26・EDO-0437 第7巡)。城の石垣の出隅と同じ器(KadoArmNeeds・
            //   8 方向の光線)で、腕ごとに要る長さを測る。野面の隅は腕を詰めた組を焼いていない ⇒ 呑むなら ⚠ に要る腕の長さと駒の型を刷る(部材方へ)。
            //   当たる先: 野面の土留めの出隅で石段の袖が腕へ入る所(山王 前庭の北東 TW_Zentei_N_kado2 × 参道の階の東の袖)。
            if (w.kadoAbut != null && w.kadoAbut.Count > 0)
            {
                var kvs = Body(kg.transform, 999999); float kLo = float.MaxValue, kHi = float.MinValue, t1 = float.MinValue, t2 = float.MinValue;
                Vector2 a1 = -dir[i - 1], a2 = dir[i];
                foreach (var v in kvs) { kLo = Mathf.Min(kLo, v.y); kHi = Mathf.Max(kHi, v.y); Vector2 r = new Vector2(v.x, v.z) - P[i]; t1 = Mathf.Max(t1, Vector2.Dot(r, a1)); t2 = Mathf.Max(t2, Vector2.Dot(r, a2)); }
                float n1, n2; string b1, b2;
                KadoArmNeeds(kg, P[i], kLo, kHi, a1, a2, w.kadoAbut, float.MaxValue, out n1, out b1, out n2, out b2);
                var ci = System.Globalization.CultureInfo.InvariantCulture;
                if (b1 != null || b2 != null)
                    log.AppendLine("    ⚠ " + name + " 隅 " + i + "(" + System.IO.Path.GetFileNameWithoutExtension(path) + "): 腕が相手を呑む ── 要る腕 " +
                                   (b1 != null ? "前の区間の側 " + n1.ToString("F3", ci) + "(" + b1 + "・今 " + t1.ToString("F3", ci) + ")" : "前の区間の側 今のまま " + t1.ToString("F3", ci)) + " / " +
                                   (b2 != null ? "次の区間の側 " + n2.ToString("F3", ci) + "(" + b2 + "・今 " + t2.ToString("F3", ci) + ")" : "次の区間の側 今のまま " + t2.ToString("F3", ci)) +
                                   "。腕を詰めた野面の隅は焼いていない(部材方へ: 型 Sanno_Nozura_Kado90・見付 " + hk.ToString("F2", ci) + "・腕の長さは隅の稜線の点からの走り)");
            }
            var sp1 = span(kg, P[i], dir[i - 1]); var sp2 = span(kg, P[i], dir[i]);
            fixedSpans.Add(new[] { sc + sp1[0], sc + sp2[1], i, 0 });
            // 隅の見え面は二つ ⇒ 天端の帯の数え(TuckUnderCrest)には両面の間の対角を渡す(列が稜線の天端を通る)
            res.Add(new KeyValuePair<GameObject, Vector2>(kg, (f1 + f2).normalized)); idx++;
            log.AppendLine("    隅 " + i + ": " + System.IO.Path.GetFileNameWithoutExtension(path) + "(折れ " + turn.ToString("F1") + "°・覆う走り " + (sp1[0]).ToString("F2") + "〜+" + sp2[1].ToString("F2") + ")");
        }
        foreach (var ss in w.steps)
        {
            int si = segOf(ss); Vector2 c = at(ss); Vector2 fN = face[si];
            float lo = w.crestAt(ss - HALF), hi = w.crestAt(ss + HALF);
            Vector2 X = new Vector2(fN.y, -fN.x);                 // 局所 +X(+Z = 見え面)
            bool rises = Vector2.Dot(X, dir[si]) * (hi - lo) > 0f;
            float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg; float mid = 0.5f * (lo + hi);
            string path; GameObject dg;
            if (isN2)
            {   // ⭐ 段の境は**勾配の直線の駒(Nozura2)**で継ぐ(2026-10-11・EDO-0502 第104巡)── 段の境の駒は H1.5 の一種しか焼いておらず、
                //   見付の要る所(岡部 TW_KiriZaka_N/S の段の境)で足元に 0.43 の口が開いた。勾配 = 段の差 ÷ 一間に最も近い焼いた物・見付は走りの各点の最大。
                //   当たる先: Nozura2 を渡す野面の run の段の境すべて(岡部)。
                float hd = needH(ss - HALF, ss + HALF, float.NaN, si);
                float xr = Vector2.Dot(X, dir[si]) >= 0f ? 1f : -1f;
                path = w.straight(hd, xr * (hi - lo) / W, idx);
                dg = Place(path, new Vector3(c.x, mid - hd, c.y), yaw, Vector3.one, parent, name + "_dan");
                FaceWallToLine(dg, fN, c);
                float gWd = bakedG(path); float cmd = crestOfG(dg, gWd); if (!float.IsNaN(cmd)) dg.transform.position += Vector3.up * (mid - cmd);
            }
            else
            {
                path = w.dan(rises, idx);
                dg = Place(path, new Vector3(c.x, mid - 1.5f, c.y), yaw, Vector3.one, parent, name + "_dan");
                seat(dg, mid, fN, c);
            }
            // 走りの位置: 中心を段の境へ(両切り口の中点 ── Nozura2 は継ぎ目の線の中点)
            var sp = jspan(dg, path, c, dir[si]); dg.transform.position -= new Vector3(dir[si].x, 0f, dir[si].y) * (0.5f * (sp[0] + sp[1]));
            sp = jspan(dg, path, c, dir[si]);
            fixedSpans.Add(new[] { ss + sp[0], ss + sp[1], -1, 1 });
            res.Add(new KeyValuePair<GameObject, Vector2>(dg, fN)); idx++;
            log.AppendLine("    段の境 s=" + ss.ToString("F2") + ": " + System.IO.Path.GetFileNameWithoutExtension(path) + "(天端 " + lo.ToString("F2") + "→" + hi.ToString("F2") + ")");
        }
        // ---- ② 端: 相手の駒の実面まで ---------------------------------------------------------
        Func<List<GameObject>, float, int, float> endAt = (to, sEnd, sgn) =>
        {
            // ⭐ 相手の面は**三角形**で測る(城の石垣の駒は大きな面の殻で、頂点では面の中が空になる)。
            //   端の手前 3m から走りの向きへ、見える丈(地表より上・天端まで)と線の前後の格子で光線を打ち、
            //   全ての光線が相手の面へ届く所(= 当たりの距離の最大)を端とする。⛔ 隙を残さない(隙間 > めり込み)。
            int si = sgn > 0 ? m - 2 : 0; Vector2 o = at(sEnd); Vector2 d = dir[si] * sgn; float top = w.crestAt(sEnd);
            var hl = new List<float>();
            foreach (float lat in new[] { -0.3f, 0f, 0.1f })
            {
                Vector2 q = o + face[si] * lat - d * 3f; float g = groundAt(q.x + d.x * 3f, q.y + d.y * 3f);
                // ⭐ 見える丈は見え面の前の地表まで ── 天端を高い側の地盤に揃えた土留めは端の線の上の地表 = 天端で、光線が一本も立たなかった
                //   (前庭の SW の端が女坂の袖を測れず打ち切りになった・2026-09-26)
                { Vector2 fq = o + face[si] * 0.7f; float gf = faceG(fq.x, fq.y); if (!float.IsNaN(gf) && (float.IsNaN(g) || gf < g)) g = gf;
                  float ft = w.footAt != null ? w.footAt(fq.x, fq.y) : float.NaN; if (!float.IsNaN(ft) && ft < g) g = ft; }
                for (float y = top - 0.05f; y > (float.IsNaN(g) ? top - 1f : g) + 0.02f; y -= 0.15f)
                {
                    float hit = RayToBodies(to, new Vector3(q.x, y, q.y), new Vector3(d.x, 0f, d.y), 6f);
                    if (!float.IsNaN(hit)) hl.Add(hit - 3f);
                }
            }
            if (hl.Count == 0) return float.NaN;
            // 手前の面の当たりだけ(最初の当たり +0.6m 以内)の最大 ── 奥の駒へ抜けた光線は数えない
            hl.Sort(); float best = hl[0]; foreach (var x in hl) if (x <= hl[0] + 0.6f) best = x;
            return sEnd + sgn * best;
        };
        float sStart = 0f, sStop = L; bool freeA = true, freeB = true;
        if (w.startTo.Count > 0) { float e = endAt(w.startTo, 0f, -1); if (!float.IsNaN(e)) { sStart = e; freeA = false; } }
        if (w.endTo.Count > 0) { float e = endAt(w.endTo, L, +1); if (!float.IsNaN(e)) { sStop = e; freeB = false; } }
        if (w.startThrough) freeA = false;                          // 入隅の通す側: 線の端点で止め、打ち切りにしない
        if (w.endThrough) freeB = false;
        log.AppendLine("    端: 始まり " + (freeA ? "打ち切り" : "相手の面へ s=" + sStart.ToString("F2")) + " / 終わり " + (freeB ? "打ち切り" : "相手の面へ s=" + sStop.ToString("F2") + "(線の終わり " + L.ToString("F2") + ")"));

        // ---- ②' 斜めの相手には斜め切りの端の駒(2026-09-26・EDO-0437)---------------------------
        //   ⭐ 相手の面(女坂の袖の外面)を天端の近くで光線で測り、その平面の線が走りとなす角・向きから焼いた駒を引く。
        //   駒は伸縮させない。**天端の前の縁の切り口の端**(実メッシュ)を「相手の面 × 天端の線」の交点へ当てる ── 足の前・控えは
        //   枠の外へ出るので、走りの幅(射影)で突き付けない。伸縮は残りの直線の駒が吸う。
        var endKiri = new GameObject[2];
        for (int side = 0; side < 2; side++)
        {
            int sgn = side == 0 ? -1 : 1;
            var to = side == 0 ? w.startTo : w.endTo;
            bool free = side == 0 ? freeA : freeB, thr = side == 0 ? w.startThrough : w.endThrough;
            if (w.kiriEnd == null || to.Count == 0 || free || thr) continue;
            int si = sgn > 0 ? m - 2 : 0; Vector2 dOut = dir[si] * sgn; Vector2 o = at(sgn > 0 ? L : 0f);
            float top = w.crestAt(sgn > 0 ? L : 0f);
            Vector2 Q = Vector2.zero, tl = Vector2.zero; float sQ = float.NaN; float yHit = float.NaN; string dbg = "";
            float yLo = top - 2.5f; { Vector2 fq = o + face[si] * 0.7f; float gf = faceG(fq.x, fq.y); if (!float.IsNaN(gf)) yLo = gf + 0.05f; }
            for (float y = top - 0.05f; y > yLo && float.IsNaN(sQ); y -= 0.1f)
            {
                // ⭐ 相手の面の線は**天端の線の裏(lat < 0 ── 駒の控えの側)**の光線で引き、天端の線(lat 0)との交点を当てる所とする。
                //   線の上と前の光線は相手の端の角(女坂の袖の留め)の別の面を拾う(SE の西端で 46.8°・向きも逆に読んだ・2026-09-26)。
                var lats = new[] { -0.75f, -0.6f, -0.45f, -0.3f, -0.15f }; var hp = new List<Vector2>(); string dbgY = "";
                foreach (float lat in lats)
                {
                    Vector2 q = o + face[si] * lat - dOut * 3f;
                    float hit = RayToBodies(to, new Vector3(q.x, y, q.y), new Vector3(dOut.x, 0f, dOut.y), 6f);
                    dbgY += (float.IsNaN(hit) ? "—" : (hit - 3f).ToString("F2")) + " ";
                    if (!float.IsNaN(hit)) hp.Add(q + dOut * hit);
                }
                if (dbg.Length < 400) dbg += "y" + y.ToString("F2") + ":" + dbgY + "/ ";
                if (hp.Count < 3) continue;
                // 最小二乗の線(点の並びの主軸)── 裏から数えて一枚の面に乗る最も長い並びで(前の点は相手の端の角の別の面)
                Vector2 mc = Vector2.zero, t = Vector2.zero, nn = Vector2.zero; bool flat = false;
                for (int kk = hp.Count; kk >= 3 && !flat; kk--)
                {
                    mc = Vector2.zero; for (int q2 = 0; q2 < kk; q2++) mc += hp[q2]; mc /= kk;
                    float sxx = 0f, sxz = 0f, szz = 0f; for (int q2 = 0; q2 < kk; q2++) { var dd = hp[q2] - mc; sxx += dd.x * dd.x; sxz += dd.x * dd.y; szz += dd.y * dd.y; }
                    float ang = 0.5f * Mathf.Atan2(2f * sxz, sxx - szz); t = new Vector2(Mathf.Cos(ang), Mathf.Sin(ang));
                    if (Vector2.Dot(t, face[si]) < 0f) t = -t;             // 見え面の側へ
                    nn = new Vector2(-t.y, t.x); flat = true;
                    for (int q2 = 0; q2 < kk; q2++) if (Mathf.Abs(Vector2.Dot(hp[q2] - mc, nn)) > 0.03f) flat = false;
                }
                if (!flat) continue;
                // 天端の線(o を通り dOut)との交点
                float den = Vector2.Dot(dOut, nn); if (Mathf.Abs(den) < 0.1f) continue;
                float u = Vector2.Dot(mc - o, nn) / den;                     // o + dOut·u が線の上
                Q = o + dOut * u; tl = t; sQ = (sgn > 0 ? L : 0f) + sgn * u; yHit = y;
            }
            if (float.IsNaN(sQ)) { log.AppendLine("    (" + (side == 0 ? "始まり" : "終わり") + "の端: 相手の面を一枚の平面として測れず ── " + dbg + ")"); continue; }
            float deg = Vector2.Angle(tl, dOut); if (deg > 90f) deg = 180f - deg;
            if (deg < 5f || deg > 70f) continue;                       // 70° を超える(見切り石の丸い小口など)は直交と見る                       // 相手の面が走りに直交(か平行)── 直線の駒で突き付ける
            bool faceLonger = Vector2.Dot(tl, dOut) > 0f;               // tl は見え面の側へ向く(lat + が見え面)
            float sa = Mathf.Min(sQ, sQ - sgn * W), sb = Mathf.Max(sQ, sQ - sgn * W);
            Vector2 fN = faceOn(si, sa, sb);
            Vector2 X = new Vector2(fN.y, -fN.x); bool atPlusX = Vector2.Dot(X, dOut) > 0f;
            float crest = w.crestAt(Mathf.Clamp(0.5f * (sa + sb), 0f, L));
            float hNeed = needH(Mathf.Max(0f, sa), Mathf.Min(L, sb), crest, si);
            string path = null; float hUse = hNeed, dUse = deg; string root = System.IO.Directory.GetParent(Application.dataPath).FullName;
            foreach (var hh in w.heights)
            {
                if (hh < hNeed - 1e-3f || path != null) continue;   // 見付以上の段で最も低いもの(高い段は沈める)
                for (float dd = 0f; dd <= 5.0f + 1e-4f && path == null; dd += 0.1f)   // 焼いた角との差 ±5°(差は刷る)
                    foreach (float dg2 in new[] { deg - dd, deg + dd })
                    { string pth = w.kiriEnd(dg2, atPlusX, faceLonger, hh, idx);
                      if (pth != null && System.IO.File.Exists(System.IO.Path.Combine(root, pth))) { path = pth; hUse = hh; dUse = dg2; break; } }
            }
            if (path == null)
            { log.AppendLine("    ⚠ " + name + " の" + (side == 0 ? "始まり" : "終わり") + "の端: 相手の面が走りと " + deg.ToString("F1") + "° に交わるが、斜め切りの端の駒(" +
                             (atPlusX ? "+X" : "−X") + "・" + (faceLonger ? "見え面が長い" : "控えが長い") + "・見付 " + hNeed.ToString("F2") + " 以上)が焼いていない ── 直線の駒で相手の面まで"); continue; }
            float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
            Vector2 c0 = Q - dOut * HALF;
            var kg = Place(path, new Vector3(c0.x, crest - hUse, c0.y), yaw, Vector3.one, parent, name + "_kiriEnd" + side);
            // 相手の面の法線(相手の中へ向く)── 斜めの取り合いは**この向きで**測る(2026-09-26・EDO-0437 第2巡)。
            //   ⛔ 走りの向き(dOut)の筋で測らない: 筋 0.25m の中で斜めの面は 0.25/tan(角) ずれ、触れていても −0.27 と読む。
            Vector2 nTl = new Vector2(-tl.y, tl.x); Vector2 nIn = Vector2.Dot(nTl, dOut) >= 0f ? nTl : -nTl;
            Vector3 nIn3 = new Vector3(nIn.x, 0f, nIn.y); float along = Vector2.Dot(dOut, nIn);
            Func<GameObject, List<Vector3>> visK = go =>
            { var l = new List<Vector3>(); foreach (var v in Body(go.transform, 999999)) { float gy = faceG(v.x, v.z); if (float.IsNaN(gy) || v.y > gy + 0.02f) l.Add(v); } return l; };
            Func<float> touch = () =>
            {   // 切り口 × 相手の面: 見える所の頂点どうし、相手の面の法線の筋で(最小 = 触れている箇所・負 = めり込み)
                var pk0 = visK(kg); float cm = float.NaN;
                foreach (var pr in to) if (pr != null)
                { Vector3 a1; int c1; float cc = ContactPts(pk0, visK(pr), nIn3, out a1, out c1); if (!float.IsNaN(cc) && (float.IsNaN(cm) || cc < cm)) cm = cc; }
                return cm;
            };
            seat0(kg, crest, fN, Q);
            {   // 一手目の見当: 天端の前の縁の切り口の端(天端の帯で、線から ±0.06 の頂点の走りの外向きの最大)を Q へ
                //   ⚠ 野面の頭は不揃いで、端の石の頭が帯の下に入ると 0.7m 手前を「端」と読む(SW の東端・2026-09-26)⇒ 見当に留め、次の手で切り口を相手の面で測る
                var vs = Body(kg.transform, 999999); float tp = float.MinValue; foreach (var v in vs) tp = Mathf.Max(tp, v.y);
                float e = float.MinValue;
                foreach (var v in vs) if (v.y >= tp - 0.12f)
                { Vector2 r = new Vector2(v.x, v.z) - Q; if (Mathf.Abs(Vector2.Dot(r, fN)) < 0.06f) e = Mathf.Max(e, Vector2.Dot(r, dOut)); }
                if (e != float.MinValue) kg.transform.position -= new Vector3(dOut.x, 0f, dOut.y) * e;
                seat0(kg, crest, fN, Q);
            }
            // ⭐ 切り口を相手の面へ: 相手の面の法線で触れている箇所を測り、走りに沿って寄せて据え直す(接して 0)。
            //   寄せると据えが変わり据えると当たりが開く ⇒ 収まるまで(EdoBuild.Converge・EDO-0454。決め打ちの3巡を置き換えた)。
            //   硬い制約(めり込み)の合否はこの後の退ける判定が測る ── ここは寄せるだけ。
            if (along >= 0.2f)
            {
                var kgc = kg; float crestC = crest; Vector2 fNc = fN, Qc = Q, dOc = dOut; float alongC = along;
                Converge(new[] { Tori.Custom(kg.name + "→相手の面", kg, true, -0.002f, 0.002f, touch,
                    () => { float tc = touch(); if (float.IsNaN(tc)) return float.NaN;
                            kgc.transform.position += new Vector3(dOc.x, 0f, dOc.y) * (tc / alongC); seat0(kgc, crestC, fNc, Qc);
                            return Mathf.Abs(tc / alongC); }) });
            }
            // ⛔ 硬い制約(許容0): 据えた斜め切りの駒が相手へ見える所でめり込むなら退ける(設計面より上の頂点どうしを相手の面の法線で測る)。
            //   (女坂の足の袖 TW_Onna_N_000 へ −0.63・SE は控えが石段の上へ 1.97 浮いた・2026-09-26 ── 切り口の端の読み違い)。
            {
                var pk = visK(kg); float cmin = float.NaN; Vector3 cat = Vector3.zero;
                foreach (var pr in to) if (pr != null)
                { Vector3 a1; int c1; float cc = ContactPts(pk, visK(pr), nIn3, out a1, out c1); if (!float.IsNaN(cc) && (float.IsNaN(cmin) || cc < cmin)) { cmin = cc; cat = a1; } }
                // 浮き: 相手の面の外(相手の側へ 0.1 を超えて)へ出た所の最下点 − 描かれた地表。⭐ 升の中心で測る(法の面の頂点は殻なので、
                //   面の近くの升は最下の頂点が高く出る ── 切り口の手前で 1.14 の嘘の浮き・2026-09-26)
                float flo = float.NegativeInfinity; Vector3 fat = Vector3.zero;
                var cellsK = new Dictionary<long, float>();
                foreach (var v in Body(kg.transform, 999999))
                { long key = ((long)Mathf.FloorToInt(v.x / 0.25f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.25f); float y0; if (!cellsK.TryGetValue(key, out y0) || v.y < y0) cellsK[key] = v.y; }
                foreach (var kv in cellsK)
                { float x = ((int)(kv.Key >> 32) + 0.5f) * 0.25f, z = ((int)(kv.Key & 0xffffffffL) + 0.5f) * 0.25f;
                  if (Vector2.Dot(new Vector2(x, z) - Q, nIn) <= 0.1f) continue;
                  float gy = groundAt(x, z);
                  if (!float.IsNaN(gy) && kv.Value - gy > flo) { flo = kv.Value - gy; fat = new Vector3(x, kv.Value, z); } }
                if ((!float.IsNaN(cmin) && cmin < -0.005f) || flo > 0.05f)
                {
                    log.AppendLine("    ⛔ " + name + " の" + (side == 0 ? "始まり" : "終わり") + "の端: 斜め切りの駒 " + System.IO.Path.GetFileNameWithoutExtension(path) +
                                   " を退けた ── 相手へ " + (float.IsNaN(cmin) ? "—" : cmin.ToString("+0.000;-0.000")) + "m(" + cat.ToString("F2") + ")・切り口の外の浮き " +
                                   (float.IsNegativeInfinity(flo) ? "—" : flo.ToString("F2")) + "m(" + fat.ToString("F2") + ")。直線の駒で相手の面まで");
                    UnityEngine.Object.DestroyImmediate(kg); continue;
                }
            }
            float inner = float.MaxValue; foreach (var v in Body(kg.transform, 999999)) inner = Mathf.Min(inner, Vector2.Dot(new Vector2(v.x, v.z) - Q, dOut));
            float sIn = sQ + sgn * inner;
            fixedSpans.Add(new[] { Mathf.Min(sIn, sQ), Mathf.Max(sIn, sQ), -1, 2 });
            if (side == 0) sStart = sQ; else sStop = sQ;
            res.Add(new KeyValuePair<GameObject, Vector2>(kg, fN)); idx++; endKiri[side] = kg;
            log.AppendLine("    " + (side == 0 ? "始まり" : "終わり") + "の端: 斜め切りの駒 " + System.IO.Path.GetFileNameWithoutExtension(path) + "(相手の面の角 " + deg.ToString("F1") +
                           "°・焼いた角 " + dUse.ToString("F1") + "°・見付 " + hNeed.ToString("F2") + "→" + hUse.ToString("F2") + "・天端の前の縁の切り口を s=" + sQ.ToString("F2") + " へ・光線 y=" + yHit.ToString("F2") + ")");
        }

        // ---- ②'' 入隅の可動側の端には小口を相手の法で切った駒(2026-09-26・EDO-0437 第3巡)-------
        //   ⭐ 鉛直な小口を通す側の法の足(楔)へ突き付けると、縮めても低い石ほど深く入る(前庭 W の南の区間 −0.05 が 4 巡で残った)。
        //   小口を相手の法 1:0.3 で切った駒を**伸縮させず**に据える: 長さは区間(天端の高さで測った相手の面 〜 反対の端の相手の最も手前)に
        //   収まる最長で、残りが 0.05 以下(口)か直線の駒を縮めて埋まる長さ以上。天端の前の縁の切る端を相手の面へ向け、
        //   **触れている箇所を測って**走りに沿って寄せる(接して 0)。反対の端の相手へ入るなら一つ短い長さへ(硬い制約・許容0)。
        //   当たる先: 野面の土留めの入隅の可動側の端すべて(山王 前庭の W × SW、今後の庭の土留めの入隅)。
        for (int side = 0; side < 2; side++)
        {
            int sgn = side == 0 ? -1 : 1;
            var to = side == 0 ? w.startTo : w.endTo; var other = side == 0 ? w.endTo : w.startTo;
            bool conc = side == 0 ? w.startConcave : w.endConcave, free = side == 0 ? freeA : freeB, otherFree = side == 0 ? freeB : freeA;
            if (w.noriEnd == null || !conc || free || to.Count == 0 || endKiri[side] != null) continue;
            string sideName = side == 0 ? "始まり" : "終わり";
            int si = sgn > 0 ? m - 2 : 0; Vector2 dOut = dir[si] * sgn; Vector3 dOut3 = new Vector3(dOut.x, 0f, dOut.y);
            float sEnd = sgn > 0 ? L : 0f; float top = w.crestAt(sEnd);
            // 天端の高さ(天端の線の上と裏 0.3 まで)で、光線の当たりの最小(= 最も手前)
            Func<IList<GameObject>, Vector2, Vector2, float> nearAt = (bodies, from, d) =>
            {
                float best = float.NaN;
                foreach (float lat in new[] { 0f, -0.15f, -0.3f })
                    foreach (float dy in new[] { 0.05f, 0.15f })
                    {
                        Vector2 q = from + face[si] * lat;
                        float hh = RayToBodies(bodies, new Vector3(q.x, top - dy, q.y), new Vector3(d.x, 0f, d.y), 6f);
                        if (!float.IsNaN(hh) && (float.IsNaN(best) || hh < best)) best = hh;
                    }
                return best;
            };
            float hitMin = nearAt(to, at(sEnd) - dOut * 3f, dOut);
            if (float.IsNaN(hitMin)) { log.AppendLine("    (" + sideName + "の入隅: 相手の面を天端の高さで測れず ── 鉛直な小口のまま)"); continue; }
            float sQ = sEnd + sgn * (hitMin - 3f);
            Vector2 Q = at(Mathf.Clamp(sQ, 0f, L)) + dir[si] * (sQ - Mathf.Clamp(sQ, 0f, L));
            // 収まる長さ: 相手の面から、最初の固定の駒か反対の端の相手の最も手前まで
            float lim = side == 0 ? sStop : sStart; bool limIsOther = !otherFree && other.Count > 0;
            if (limIsOther) { float hn = nearAt(other, Q + dOut * 0.05f, -dOut); if (!float.IsNaN(hn)) lim = sQ - sgn * (hn + 0.05f); }
            foreach (var f in fixedSpans)
            {
                if (side == 0 && f[0] > sQ && f[0] < lim) { lim = f[0]; limIsOther = false; }
                if (side == 1 && f[1] < sQ && f[1] > lim) { lim = f[1]; limIsOther = false; }
            }
            float avail = Mathf.Abs(lim - sQ);
            //   長さの順: 残りが 0.05 以下(口)か直線の駒を縮めて埋まる長さ(③ の端の駒の下限 0.20 間)以上になる物を先に、次にその他を長い順
            //   (反対の端の相手が天端より下で前へ出ていると、天端で測った残りより手前で当たる ── 見切り石の足・2026-09-26)
            var lens = new List<float>(); var lens2 = new List<float>();
            for (float ls = EdoAssets.Own.SannoNozuraNoriMaxLen; ls >= 0.30f - 1e-4f; ls -= 0.05f)   // 上限は焼いた最長(H4.80 は 1.50〜1.80・第91巡)── 焼いていない組は File.Exists で落ちる
            {
                float r = avail - ls; if (r < -1e-3f) continue;
                if (r <= 0.05f || r >= 0.20f * W + 1e-3f) lens.Add(ls); else lens2.Add(ls);
            }
            if (limIsOther) { lens.AddRange(lens2); lens.Sort((a, b) => b.CompareTo(a)); }
            if (lens.Count == 0) { log.AppendLine("    ⚠ " + name + " の" + sideName + "の入隅: 区間 " + avail.ToString("F2") + "m に収まる法切りの駒の長さが無い ── 鉛直な小口のまま"); continue; }
            Func<GameObject, List<Vector3>> visN = go =>
            { var l = new List<Vector3>(); foreach (var v in Body(go.transform, 999999)) { float gy = faceG(v.x, v.z); if (float.IsNaN(gy) || v.y > gy + 0.02f) l.Add(v); } return l; };
            Func<GameObject, IList<GameObject>, Vector3, float> touchOn = (go, bodies, d) =>
            {
                var pk0 = visN(go); float cm = float.NaN;
                foreach (var pr in bodies) if (pr != null && pr != go)
                { Vector3 a1; int c1; float cc = ContactPts(pk0, visN(pr), d, out a1, out c1); if (!float.IsNaN(cc) && (float.IsNaN(cm) || cc < cm)) cm = cc; }
                return cm;
            };
            GameObject kg = null; string path = null; float hUse = 0f, hNeed = 0f, lenUse = 0f, cfin = float.NaN, cOth = float.NaN; Vector2 fN = Vector2.zero; string why = "";
            foreach (float ls in lens)
            {
                float sa0 = Mathf.Min(sQ, sQ - sgn * ls), sb0 = Mathf.Max(sQ, sQ - sgn * ls);
                fN = faceOn(si, sa0, sb0);
                Vector2 X = new Vector2(fN.y, -fN.x); bool atPlusX = Vector2.Dot(X, dOut) > 0f;
                float crest = w.crestAt(Mathf.Clamp(0.5f * (sa0 + sb0), 0f, L));
                hNeed = needH(Mathf.Max(0f, sa0), Mathf.Min(L, sb0), crest, si);
                path = null; string root = System.IO.Directory.GetParent(Application.dataPath).FullName;
                foreach (var hh in w.heights)
                {
                    if (hh < hNeed - 1e-3f) continue;
                    string pth = w.noriEnd(ls, atPlusX, hh);
                    if (pth != null && System.IO.File.Exists(System.IO.Path.Combine(root, pth))) { path = pth; hUse = hh; break; }
                }
                if (path == null) { why = "長さ " + ls.ToString("F2") + "・" + (atPlusX ? "+X" : "−X") + "・見付 " + hNeed.ToString("F2") + " 以上が焼いていない"; continue; }
                float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
                Vector2 c0 = Q - dOut * (0.5f * ls);
                kg = Place(path, new Vector3(c0.x, crest - hUse, c0.y), yaw, Vector3.one, parent, name + "_nori" + side);
                // 高さ・見え面は天端の線へ(測って寄せる)。走りは天端の前の縁の切る端を Q へ見当 → 触れている箇所で寄せる
                seat0(kg, crest, fN, Q);
                {
                    var vs = Body(kg.transform, 999999); float tp = float.MinValue; foreach (var v in vs) tp = Mathf.Max(tp, v.y);
                    float e = float.MinValue;
                    foreach (var v in vs) if (v.y >= tp - 0.12f)
                    { Vector2 r = new Vector2(v.x, v.z) - Q; if (Mathf.Abs(Vector2.Dot(r, fN)) < 0.10f) e = Mathf.Max(e, Vector2.Dot(r, dOut)); }
                    if (e != float.MinValue) kg.transform.position -= dOut3 * e;
                }
                // 寄せると据えが変わる ⇒ 収まるまで(EdoBuild.Converge・EDO-0454。決め打ちの4巡を置き換えた)。
                //   硬い制約(めり込み)の合否はこの後の cfin/cOth が測って退ける ── ここは寄せるだけ。
                {
                    var kgc = kg; float crestC = crest; Vector2 fNc = fN, Qc = Q; Vector3 dO3 = dOut3; var toC = to;
                    Converge(new[] { Tori.Custom(kg.name + "→相手", kg, true, -0.002f, 0.002f, () => touchOn(kgc, toC, dO3),
                        () => { float tc = touchOn(kgc, toC, dO3); if (float.IsNaN(tc)) return float.NaN;
                                kgc.transform.position += dO3 * tc; seat0(kgc, crestC, fNc, Qc); return Mathf.Abs(tc); }) });
                }
                cfin = touchOn(kg, to, dOut3);
                cOth = other.Count > 0 ? touchOn(kg, other, -dOut3) : float.NaN;
                if ((!float.IsNaN(cfin) && cfin < -0.005f) || (!float.IsNaN(cOth) && cOth < -0.005f))
                {   // ⛔ 硬い制約(許容0): 相手か反対の端の相手へ入る ⇒ 一つ短い長さへ
                    why = "長さ " + ls.ToString("F2") + " は相手へ " + (float.IsNaN(cfin) ? "—" : cfin.ToString("+0.000;-0.000")) + "・反対の端の相手へ " + (float.IsNaN(cOth) ? "—" : cOth.ToString("+0.000;-0.000"));
                    UnityEngine.Object.DestroyImmediate(kg); kg = null; continue;
                }
                lenUse = ls; break;
            }
            if (kg == null) { log.AppendLine("    ⚠ " + name + " の" + sideName + "の入隅: 法切りの駒を据えられない(" + why + ")── 鉛直な小口のまま"); continue; }
            // 駒の走りの範囲(実メッシュ)を固定の駒に。相手の側の端は相手の面(sQ)
            var spn = span(kg, P[si], dir[si]);
            float sNear = sgn > 0 ? s0[si] + spn[0] : s0[si] + spn[1];     // 内側(直線の駒が継ぐ側)の端
            fixedSpans.Add(new[] { Mathf.Min(sNear, sQ), Mathf.Max(sNear, sQ), -1, 3 });
            if (side == 0) sStart = sQ; else sStop = sQ;
            float rest = Mathf.Abs(lim - sNear);
            // 反対の端の相手との間(触れている箇所で測った cOth)が直線の駒を縮めて埋まる長さに足りない ⇒ 直線の駒を入れない(反対の端をこの駒の端に止める)
            bool gapLeft = false;
            if (limIsOther && (Mathf.Abs(avail - lenUse) <= 0.05f || (!float.IsNaN(cOth) && cOth < 0.20f * W)))
            { if (side == 0) sStop = sNear; else sStart = sNear; gapLeft = !float.IsNaN(cOth) && cOth > 0.005f; }
            res.Add(new KeyValuePair<GameObject, Vector2>(kg, fN)); idx++; endKiri[side] = kg;
            log.AppendLine("    " + sideName + "の入隅: 法切りの駒 " + System.IO.Path.GetFileNameWithoutExtension(path) + "(区間 " + avail.ToString("F2") +
                           "m・見付 " + hNeed.ToString("F2") + "→" + hUse.ToString("F2") + ")・相手へ " + (float.IsNaN(cfin) ? "—" : cfin.ToString("+0.000;-0.000")) +
                           "m・反対の端の相手へ " + (float.IsNaN(cOth) ? "—" : cOth.ToString("+0.000;-0.000")) + "m・天端での残り " + rest.ToString("F3") + "m" + (why != "" ? "(退けた長さ: " + why + ")" : "") +
                           (gapLeft ? " ⚠ 反対の端の相手との口 " + cOth.ToString("F3") + "m(焼いた長さの刻み 0.05 と相手の出入りで残る)" : ""));
        }

        // ---- ③ 固定の駒の間を 1間の駒で埋める -------------------------------------------------
        //   ⭐ 端を相手の面へ突き付けた run は、据えた端の駒と相手を実メッシュで測り(Contact)、めり込めば端を戻して**もう一度だけ**
        //   並べ直す(光線の当たりは線の前後 3 本だけ ── 石の出っ張りが測りの外で相手へ入った・男坂の袖 −0.02〜−0.03・2026-09-26)。
        fixedSpans.Sort((a, b) => a[0].CompareTo(b[0]));
        int idx0 = idx; int res0 = res.Count; float worstJoint = 0f; int nPieces = 0;
        const int FILL_PASSES = 12;
        //   ⭐ 端の駒 × 相手は、入る位置(penS)と口の位置(gapS)を巡ごとに覚え、両方が出たら間を二分して触れる所へ寄せる(2026-10-07 EDO-0502 第42巡:
        //   TW_Kado_Sode の上の端が −0.454 → −0.456 → +0.236 と戻し過ぎて口のまま終わった)。最後の巡の一つ前は口の側(入らない側)へ置き直す ── 硬い制約(めり込み)を守る。
        //   当たる先: 野面の run の、相手の実面へ突き付ける端すべて(岡部 Stage2b・山王 前庭)。
        var penS = new[] { float.NaN, float.NaN }; var penV = new[] { float.NaN, float.NaN }; var gapS = new[] { float.NaN, float.NaN }; var gapV = new[] { float.NaN, float.NaN };
        const float CONCAVE_TOUCH_BAND = 0.30f;   // 入隅の可動側の鉛直な小口が相手に触れる所を測る天端の帯(下は相手の法の中へ埋める)   // 伸縮が変わると端の石の出っ張りも変わる ⇒ 一度で収まらない(W × SW の入隅 −0.045 が残った・2026-09-26)
        for (int fillPass = 0; fillPass < FILL_PASSES; fillPass++)
        {
        idx = idx0; worstJoint = 0f; nPieces = 0; var endPiece = new GameObject[2];
        var passPieces = new List<GameObject>();
        var gaps = new List<float[]>(); float cur0 = sStart;
        foreach (var f in fixedSpans) { gaps.Add(new[] { cur0, f[0], 0 }); cur0 = f[1]; }
        gaps.Add(new[] { cur0, sStop, 1 });
        for (int gi = 0; gi < gaps.Count; gi++)
        {
            float a = gaps[gi][0], b = gaps[gi][1], len = b - a;
            if (len < 0.05f) continue;
            bool lastFree = gi == gaps.Count - 1 && freeB, firstFree = gi == 0 && freeA;
            bool abutEnd = (gi == 0 && !freeA) || (gi == gaps.Count - 1 && !freeB);
            int N; float sc;
            if (len >= 0.85f * W) { N = Mathf.Max(1, Mathf.RoundToInt(len / W)); sc = len / (N * W); if (sc > 1.2f) { N++; sc = len / (N * W); } }
            //   ⭐ 相手へ突き付ける短い端は 0.20 まで縮める ── 入隅の法と見切り石に挟まれた楔(前庭の W の南の区間 0.36〜0.40m)は 0.30 では
            //   縮めきれず、何巡戻しても同じ石が相手へ −0.086 入ったまま(2026-09-26)
            else if (abutEnd) { N = 1; sc = Mathf.Max(0.20f, len / W); }
            else if ((gi == gaps.Count - 1 && freeB) || (gi == 0 && freeA)) { N = 1; sc = Mathf.Max(0.30f, len / W); }    // 短い端は縮めて相手の面・端の線まで(縮めきれない分だけ外へ)
            //   ⭐ 打ち切らない自由な端(切り込みの返しの南の端 = 最上段の蹴上の面の通り)も縮めて線の端で止める ── 0.5 で止めると 0.2m 先へ出た(2026-09-26)
            else { N = 1; sc = Mathf.Max(0.5f, len / W); }
            // 始まり側から連ねる(相手へ入れる短い端は、固定の駒の側から)
            bool fromB = gi == 0 && abutEnd && len < 0.85f * W;
            float edge = fromB ? b : a;
            // ⭐ 勾配の連鎖(Nozura2・2026-10-11 EDO-0502 第104巡): 前の駒の終わりの天端に次の駒の始まりの天端を合わせ、勾配は
            //   「(次の継ぎ目の線の高さ − 今の天端)/ 駒の走り」に最も近い焼いた物 ⇒ 天端は継ぎ目で連続し、線との外れは一駒ごとに引き戻される。
            //   従前(駒の中ほどを線へ・勾配は線の勾配に最も近い物)は、線の勾配が焼いた最大を超える坂(岡部 K_Dan1 の下の北 0.69)で継ぎ目ごとに段になった。
            //   当たる先: Nozura2 を渡す野面の run の坂なりの区間すべて(岡部 主面の石段の脇・袖の坂・腰の返し・西の隅・東南)。
            float chainEnd = float.NaN;
            for (int k = 0; k < N; k++)
            {
                float sMid = fromB ? edge - 0.5f * W * sc : edge + 0.5f * W * sc;
                int si = segOf(Mathf.Clamp(sMid, 0f, L)); Vector2 c = at(Mathf.Clamp(sMid, 0f, L)) + dir[si] * (sMid - Mathf.Clamp(sMid, 0f, L));
                float crest = w.crestAt(Mathf.Clamp(sMid, 0f, L));
                Vector2 fN = faceOn(si, sMid - 0.5f * W * sc, sMid + 0.5f * W * sc);
                if (Vector2.Dot(fN, face[si]) < 0f) flipped++;
                var faceSave = face[si]; face[si] = fN;                  // 見付・打ち切りの向きもこの駒の見え面で
                float h = needH(sMid - 0.5f * W * sc, sMid + 0.5f * W * sc, isN2 ? float.NaN : crest, si);
                face[si] = faceSave;
                Vector2 X = new Vector2(fN.y, -fN.x);
                float gX = gradeX(sMid, 0.5f * W * sc, X, si);
                bool flatHere = false;
                foreach (var r in w.fixHRanges) if (sMid >= r.x && sMid <= r.y) { gX = 0f; flatHere = true; }   // 名指した端の一駒は水平(sodeSlope の低い端 ── ⛔ 傾けて刺さない)
                foreach (var r in w.flatRanges) if (sMid >= r.x && sMid <= r.y) { gX = 0f; flatHere = true; }   // 名指した端の水平の範囲(sodeSlope の上端の取り付き ── 第63巡は PlaceBest が G−275 を選び 21.24→20.80 に傾いた)
                float sgn2 = fromB ? -1f : 1f, sNext = edge + sgn2 * W * sc, xRun = Vector2.Dot(X, dir[si]) >= 0f ? 1f : -1f;
                float prevC = float.IsNaN(chainEnd) ? w.crestAt(Mathf.Clamp(edge, 0f, L)) : chainEnd;
                if (isN2 && !flatHere && !float.IsNaN(prevC))
                {
                    float cNext = w.crestAt(Mathf.Clamp(sNext, 0f, L));
                    if (!float.IsNaN(cNext)) gX = xRun * (cNext - prevC) / (sNext - edge);
                }
                float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
                bool kiriHere = (lastFree && k == N - 1 && !fromB) || (firstFree && k == 0 && !fromB);
                // ⛔ 打ち切りの駒(見付 0.15 で頭が下がる)は端の見付が最も低い段で足りる所だけ ── 見付の要る端に置くと床が地表から浮く
                //   (前庭の SE の東の端は天端 16.4・足元 14.5 で、打ち切りの駒が 1.47m 浮いた・2026-09-26)。許容0 の浮き ⇒ 見付の合う直線の駒で終える。
                if (kiriHere && h > w.heights[0] + 1e-3f)
                { log.AppendLine("    端の見付 " + h.ToString("F2") + " は打ち切りの駒では足りない ── 直線の駒で終える(端の切り口は地表の法で受ける)"); kiriHere = false; }
                string path = null; GameObject g = null;
                if (kiriHere && w.kiri != null)
                {   // 打ち切り: 端へ向かって天端が下がる
                    bool towardPlus = Vector2.Dot(X, dir[si]) > 0f; bool endIsB = lastFree && k == N - 1;
                    path = w.kiri(endIsB ? !towardPlus : towardPlus, idx);
                    g = Place(path, new Vector3(c.x, crest - h, c.y), yaw, new Vector3(sc, 1f, 1f), parent, name + "_" + nPieces.ToString("000"));
                    seat0(g, crest, fN, c);
                    // ⭐ 打ち切りの駒は、下がる天端が**周りの地表(背の面・前の地盤)の下へ入らない所**でだけ使う(許容0 ── 被りを作らない)。
                    //   端の地表が天端から十分に下がっていなければ(見付は残る)、打ち切りを退けて見付の合う直線の駒で終える。
                    Vector3 kat; float bur = SoilSideCrestShort(g, new[] { fN, -fN, dir[si], -dir[si] },
                        groundAt, out kat);
                    if (!float.IsNaN(bur) && bur > 0f)
                    {
                        log.AppendLine("    打ち切り " + System.IO.Path.GetFileNameWithoutExtension(path) + " は先の石が地表の下へ " + bur.ToString("F2") +
                                       "m 入る(" + kat.x.ToString("F1") + ", " + kat.z.ToString("F1") + ")── 見付 " + h.ToString("F2") + " の直線の駒で終える");
                        UnityEngine.Object.DestroyImmediate(g); g = null;
                    }
                }
                if (g == null)
                {
                    path = w.straight(h, gX * sc, idx);
                    g = Place(path, new Vector3(c.x, crest - h, c.y), yaw, new Vector3(sc, 1f, 1f), parent, name + "_" + nPieces.ToString("000"));
                    if (isN2 && EdoAssets.Own.IsNozura2(path) && !float.IsNaN(prevC))
                    {   // 連鎖: 中ほどの天端 = 前の終わりの天端 + 焼いた勾配 × 半走り(勾配を差し引いて測る)
                        float gW = bakedG(path) / sc;                       // 局所 +X の世界の勾配
                        float cMid = flatHere ? crest : prevC + xRun * gW * (sMid - edge);
                        FaceWallToLine(g, fN, c);
                        float cm = crestOfG(g, gW); if (!float.IsNaN(cm)) g.transform.position += Vector3.up * (cMid - cm);
                        float cm2 = crestOfG(g, gW); if (!float.IsNaN(cm2)) worstCrest = Mathf.Max(worstCrest, Mathf.Abs(cm2 - w.crestAt(Mathf.Clamp(sMid, 0f, L))));
                        chainEnd = cMid + xRun * gW * (sNext - sMid);
                    }
                    else { seat(g, crest, fN, c); chainEnd = float.NaN; }
                    // 焼いた勾配(ファイル名の G)と求めた勾配の差 × 半走り = 端の天端の外れ(狙い ±0.08)
                    var gm = System.Text.RegularExpressions.Regex.Match(path, @"_G([+-]\d{3})_");
                    if (gm.Success) { float gb = int.Parse(gm.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) / 1000f / sc;
                        worstGradeErr = Mathf.Max(worstGradeErr, Mathf.Abs(gb - gX) * 0.5f * W * sc); }
                }
                // 前の切り口へ突き付ける(実メッシュの走りへの射影)
                string gPath = path;
                var sp = jspan(g, gPath, P[si], dir[si]);
                float want = fromB ? (edge - s0[si]) - sp[1] : (edge - s0[si]) - sp[0];
                g.transform.position += new Vector3(dir[si].x, 0f, dir[si].y) * want;
                sp = jspan(g, gPath, P[si], dir[si]);
                if (!EdoAssets.Own.IsNozura2(gPath)) chainEnd = float.NaN;   // 打ち切り・旧の駒の後は線から測り直す
                float nextEdge = fromB ? s0[si] + sp[0] : s0[si] + sp[1];
                edge = nextEdge; idx++; nPieces++;
                res.Add(new KeyValuePair<GameObject, Vector2>(g, fN)); passPieces.Add(g);
                if (gi == 0 && k == (fromB ? N - 1 : 0)) endPiece[0] = g;   // 始まりの端に在る駒(fromB は固定の側から連ねる)
                if (gi == gaps.Count - 1 && k == N - 1) endPiece[1] = g;
            }
            // 最後の切り口と次の固定の駒(または端)との隙
            float resid = fromB ? edge - a : b - edge;
            if (!(abutEnd && len < 0.4f * W)) worstJoint = Mathf.Max(worstJoint, Mathf.Abs(resid));
            log.AppendLine("    間 " + gi + ": 走り " + len.ToString("F2") + "m に 1間の駒 " + N + "(伸縮 " + sc.ToString("F3") + ")・末の隙 " + resid.ToString("+0.000;-0.000"));
        }
        // 端の駒 × 相手: 触れている所を測る(光線でなく実メッシュの筋 ── Contact)
        bool redo = false;
        for (int side = 0; side < 2; side++)
        {
            var to = side == 0 ? w.startTo : w.endTo; var g = endPiece[side];
            bool free = side == 0 ? freeA : freeB, thr = side == 0 ? w.startThrough : w.endThrough;
            if (g == null || to.Count == 0 || free || thr || endKiri[side] != null) continue;
            // 端の駒が本当に端に在るか(固定の駒の間の駒でない)── 端の走りの側の最後の間だけ
            if ((side == 0 && gaps[0][1] - gaps[0][0] < 0.05f) || (side == 1 && gaps[gaps.Count - 1][1] - gaps[gaps.Count - 1][0] < 0.05f)) continue;
            int si = side == 0 ? 0 : m - 2; Vector2 dOut = dir[si] * (side == 0 ? -1f : 1f);
            // ⭐ 見える所だけ(設計面より上の頂点)── 法の相手へ鉛直の小口を突き付ける入隅は、地表の下で法の足へ入るのが正しい納め
            //   (前庭の W の短い区間で −0.62 を「めり込み」と読み、端を 0.62 戻しかけた・2026-09-26)
            Func<GameObject, List<Vector3>> vis = go =>
            { var l = new List<Vector3>(); foreach (var v in Body(go.transform, 999999)) { float gy = faceG(v.x, v.z); if (float.IsNaN(gy) || v.y > gy + 0.02f) l.Add(v); } return l; };
            var pg = vis(g);
            // ⭐ 入隅の可動側の鉛直な小口(法切りの駒が焼けていない所)は**天端の帯で触れる所まで**寄せ、下は相手の法の中へ埋める
            //   (2026-10-04・EDO-0502 第16巡・施主 2026-09-27「据えは埋めて隠すが基本・部材どうしのめり込みは数えない」)。
            //   見える頂点の全部で測ると、相手の法の足(下ほど前へ出る)で止まり、天端で 0.3×見付 の楔の口が開いて背の土が縦の三角に見えた
            //   (岡部 TW_Higashi_Hokuto_3_0 × 2_0 の入隅)。可動側の端は通す側の面の裏(= 相手の駒の中)にあるので、入った下の石は見えない。
            //   当たる先: 野面の土留めの入隅の可動側の端で法切りの駒を使わない所すべて(岡部 TW_Higashi_Hokuto 3_0・6_0、山王 前庭の入隅)。
            bool concEnd = side == 0 ? w.startConcave : w.endConcave;
            if (concEnd && pg.Count > 0)
            {
                float tp = float.MinValue; foreach (var v in pg) tp = Mathf.Max(tp, v.y);
                pg = pg.FindAll(v => v.y >= tp - CONCAVE_TOUCH_BAND);
            }
            float cmin = float.NaN; int cn = 0; Vector3 cat = Vector3.zero;
            foreach (var p in to) if (p != null && p != g)
            { Vector3 a1; int c1; float cc = ContactPts(pg, vis(p), new Vector3(dOut.x, 0f, dOut.y), out a1, out c1);
              if (!float.IsNaN(cc) && (float.IsNaN(cmin) || cc < cmin)) { cmin = cc; cn = c1; cat = a1; } }
            if (float.IsNaN(cmin)) continue;
            log.AppendLine("    " + (side == 0 ? "始まり" : "終わり") + "の端の駒 × 相手: " + cmin.ToString("+0.000;-0.000") + "m(筋 " + cn + "・" + cat.ToString("F2") + ")" + (fillPass < FILL_PASSES - 1 && cmin < -0.005f ? " ── めり込むので端を戻して並べ直す" : ""));
            float sNow = side == 0 ? sStart : sStop;
            if (cmin < -0.005f && (float.IsNaN(penV[side]) || cmin > penV[side] || float.IsNaN(gapS[side]))) { penS[side] = sNow; penV[side] = cmin; }
            else if (cmin > 0.005f && (float.IsNaN(gapV[side]) || cmin < gapV[side])) { gapS[side] = sNow; gapV[side] = cmin; }
            bool bracket = !float.IsNaN(penS[side]) && !float.IsNaN(gapS[side]);
            bool penult = fillPass == FILL_PASSES - 2;
            if (bracket && fillPass < FILL_PASSES - 1 && Mathf.Abs(cmin) > 0.005f)
            {   // 入る位置と口の位置の間を二分(最後の一つ前は口の側へ戻して入らずに終える)
                //   割線(入りと口の量で内分)・区間の 0.2〜0.8 に挟む(駒の出入りで当たりは滑らかでない)
                float u = Mathf.Clamp(gapV[side] / Mathf.Max(1e-4f, gapV[side] - penV[side]), 0.2f, 0.8f);
                float sNew = penult ? gapS[side] : gapS[side] + (penS[side] - gapS[side]) * u;
                if (Mathf.Abs(sNew - sNow) > 1e-4f)
                {
                    log.AppendLine("      ── 入る " + penS[side].ToString("F3") + " / 口 " + gapS[side].ToString("F3") + "(" + gapV[side].ToString("F3") + "m)の間 ⇒ " + (penult ? "口の側へ戻す" : "二分して並べ直す"));
                    redo = true; if (side == 0) sStart = sNew; else sStop = sNew;
                }
            }
            else if (fillPass < FILL_PASSES - 1 && cmin < -0.005f)
            {   // ⭐ 戻しは測った量より一回ごとに深く(1.0 → 1.5 → 2.0 倍 + 5mm)── 伸縮が変わると端の石の出っ張りも変わり、
                //   測った量ちょうどでは同じ筋の石が次の巡も相手へ入る(入隅 W × SW が −0.056 → −0.081 → −0.081 と収まらなかった・2026-09-26)
                float back = cmin * (1f + 0.5f * Mathf.Min(fillPass, 2)) - 0.005f;
                redo = true; if (side == 0) sStart -= back; else sStop += back; }
            else if (fillPass < FILL_PASSES - 1 && cmin > 0.005f && (concEnd || cmin <= 0.5f * W))
            {   // 口(許容0)⇒ 測った量だけ相手へ延ばして並べ直す(触れている箇所で寄せる)。入隅の可動側は天端の帯で測った口
                log.AppendLine("      ── " + (concEnd ? "天端の帯に" : "相手との") + "口 " + cmin.ToString("F3") + "m ⇒ 相手へ延ばして並べ直す");
                redo = true; if (side == 0) sStart -= cmin; else sStop += cmin; }
            else if (cmin < -0.005f)
            {   // ⛔ 硬い制約(許容0 のめり込み): 戻しきっても入る端の駒は建てない。鉛直な小口が相手の法の足へ入る楔
                //   (入隅の可動側が通す側の法と見切り石に挟まれた所 ── 前庭の W の南の区間・2026-09-26)は、縮めても低い石ほど深く入る。
                //   納めるには小口を相手の法で切った駒が要る(部材の話)。
                log.AppendLine("    ⛔ " + name + " の" + (side == 0 ? "始まり" : "終わり") + "の端の駒 " + g.name + " を退けた ── " + FILL_PASSES +
                               " 巡戻しても相手へ " + cmin.ToString("+0.000;-0.000") + "m 入る(" + cat.ToString("F2") + ")。小口を相手の法で切った駒が要る");
                res.RemoveAll(kv => kv.Key == g); UnityEngine.Object.DestroyImmediate(g);
            }
        }
        if (!redo) break;
        foreach (var g in passPieces) if (g != null) UnityEngine.Object.DestroyImmediate(g);
        res.RemoveRange(res0, res.Count - res0);
        } // fillPass
        log.AppendLine("    ⇒ " + name + ": 駒 " + res.Count + "(直線 " + nPieces + ")/ 継ぎ目の隙の最悪 " + worstJoint.ToString("F3") + "m / 天端の差の最悪 " + worstCrest.ToString("F3") + "m" +
                       " / 勾配の寄せで端の天端が外れる最悪 " + worstGradeErr.ToString("F3") + "m(狙い ±0.08)" + (flipped > 0 ? " / 区間と逆を向けた駒 " + flipped : ""));
        return res;
    }

    /// <summary>**走りの端を相手の駒の実面まで延ばす**(2026-09-25・EDO-0430)。点 <paramref name="from"/> から
    /// <paramref name="toward"/> の向きへ、半幅 <paramref name="halfT"/>・高さ [<paramref name="yLo"/>, <paramref name="yHi"/>] の帯に入る
    /// <paramref name="bodies"/> の頂点のうち最も手前の物までの距離(届かなければ NaN)。
    /// 当たる先: 柵・板塀の口の端を土留め・石垣の小口へ突き付けるすべて(山王 Ita_Keidai の kuchiAbut)。</summary>
    /// <summary>**光線を駒の三角形へ打つ**(2026-09-25・EDO-0430)。<paramref name="o"/> から <paramref name="d"/> の向きへ
    /// <paramref name="maxDist"/> 以内で当たる最初の三角形までの距離(当たらなければ NaN)。屋根は外す(Body と同じ篩)。
    /// ⭐ 頂点でなく面で測る ── 城の石垣の駒は大きな面の殻で、頂点の筋では面の中が空く。</summary>
    public static float RayToBodies(IList<GameObject> bodies, Vector3 o, Vector3 d, float maxDist)
    {
        d.Normalize(); float best = float.MaxValue;
        foreach (var g in bodies) if (g != null)
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                var mesh = mf.sharedMesh; if (mesh == null) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
                if (IsRoofName(PartName(g.transform, mf))) continue;
                var b = rr.bounds; b.Expand(0.05f); float bd;
                if (!b.Contains(o) && (!b.IntersectRay(new Ray(o, d), out bd) || bd > maxDist)) continue;
                var M = mf.transform.localToWorldMatrix; var vs = mesh.vertices; var ts = mesh.triangles;
                var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) W[i] = M.MultiplyPoint3x4(vs[i]);
                for (int t = 0; t + 2 < ts.Length; t += 3)
                {
                    Vector3 a = W[ts[t]], e1 = W[ts[t + 1]] - a, e2 = W[ts[t + 2]] - a;
                    Vector3 pv = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, pv); if (Mathf.Abs(det) < 1e-9f) continue;
                    float inv = 1f / det; Vector3 tv = o - a; float u = Vector3.Dot(tv, pv) * inv; if (u < 0f || u > 1f) continue;
                    Vector3 qv = Vector3.Cross(tv, e1); float v = Vector3.Dot(d, qv) * inv; if (v < 0f || u + v > 1f) continue;
                    float dist = Vector3.Dot(e2, qv) * inv; if (dist >= 0f && dist < best && dist <= maxDist) best = dist;
                }
            }
        return best == float.MaxValue ? float.NaN : best;
    }

    public static float ReachToBodies(Vector2 from, Vector2 toward, IList<GameObject> bodies, float halfT, float yLo, float yHi, float maxReach)
   
    {
        // 柵の丈の帯・半厚の幅を格子に割って光線を打ち、**最初に触れる所**(当たりの最小)まで ──
        //   ⛔ 最大を採らない(低い土留めの上を抜けた光線が奥の駒に当たり、端が 2.7m 奥へ延びた・2026-09-25 実測)
        Vector2 d = toward.normalized, n = new Vector2(d.y, -d.x); float best = float.MaxValue; int hits = 0;
        foreach (float lat in new[] { -halfT, 0f, halfT })
            for (float y = yLo + 0.1f; y <= yHi; y += 0.2f)
            {
                Vector2 q = from + n * lat;
                float hit = RayToBodies(bodies, new Vector3(q.x, y, q.y), new Vector3(d.x, 0f, d.y), maxReach);
                if (float.IsNaN(hit)) continue; hits++; best = Mathf.Min(best, hit);
            }
        return hits == 0 ? float.NaN : best;
    }
    /// <summary>**走りの端が相手の駒の中に在るなら、相手の実面まで詰める**(<see cref="ReachToBodies"/> の逆向き・2026-09-26・EDO-0430)。
    /// 端 <paramref name="end"/> から走りの内へ <paramref name="maxBack"/> 戻った点(駒の外)から端へ向けて、柵の丈の帯・半厚の幅で光線を打ち、
    /// 最初に触れる面までの距離 h を測る。h &lt; maxBack なら端は相手の中(または面の上)── 詰める量 maxBack − h を返す(当たらなければ 0 = 端は外)。
    /// ⛔ 紙の端の点のまま建てない(柵 `Ita_Keidai` の始まりが回廊の基壇の隅の駒の中 0.85m まで入っていた)。硬い条件(許容0 のめり込み)。
    /// 当たる先: 柵・板塀の run の端が土留め・石垣・基壇の駒の上や中で終わる所すべて(山王 Stage4 の柵の端。`kuchiAbut` の相方)。</summary>
    public static float RetractEndFromBodies(Vector2 end, Vector2 inward, IList<GameObject> bodies, float halfT, float yLo, float yHi, float maxBack)
    {
        if (bodies == null || bodies.Count == 0 || maxBack <= 0.01f) return 0f;
        Vector2 d = inward.normalized; Vector2 from = end + d * maxBack;
        // ⛔ 走りそのものが相手に沿って(法の足に)立っている run は「端が中に在る」ではない ── 戻った点の真上から下ろした光線が
        //   帯の中で相手に当たるなら測らない(前庭の南の板塀 `Ita_ZSW` は土留めの法の足に沿って立ち、端を 1.5m 詰めかけた・2026-09-26)。
        Vector2 nrm = new Vector2(d.y, -d.x);
        foreach (float lat in new[] { -halfT, 0f, halfT })
        {
            Vector2 q = from + nrm * lat;
            float down = RayToBodies(bodies, new Vector3(q.x, yHi + 1f, q.y), Vector3.down, yHi + 1f - yLo);
            if (!float.IsNaN(down)) return 0f;
        }
        float h = ReachToBodies(from, -d, bodies, halfT, yLo, yHi, maxBack);
        if (float.IsNaN(h) || h >= maxBack - 1e-4f) return 0f;
        return maxBack - h;
    }
    /// <summary>**受けの駒の天端の上に立つ走りの端を、受けの駒が足の下に在る所まで詰める**(2026-09-26・EDO-0437 第6巡)。
    /// 端 <paramref name="end"/> から走りの内 <paramref name="inward"/> へ 0.02m 刻みで進み、走りの芯と両脇(±<paramref name="halfT"/>)の三本の
    /// 鉛直の光線が <paramref name="beds"/>(土留め・石垣)の上向きの面に当たり、その面が描かれた地表 <paramref name="groundAt"/> 以上(= 足は地面でなく
    /// 受けの駒の天端に載る)になる最初の所までの距離を返す(端がもう受けの上なら 0・<paramref name="maxBack"/> までに無ければ 0 = 動かさない)。
    /// ⭐ 受けの駒が途切れる所(石段の袖へ突き付けた土留めの端)で塀も止める ── ⛔ 受けの外へ延ばして低い袖・地面の上へ浮かせない。硬い条件(浮き・めり込み 0)。
    /// 呼び手が「走りの中ほどが受けの天端に載る run」だけに掛ける(地面に立つ run には掛けない)。
    /// 当たる先: 座の無い板塀・柵が土留め・石垣の天端に載る run の端(山王 前庭の南西の板塀 `Ita_ZSW` の東の端 ── 女坂の袖の上)。</summary>
    public static float RetractEndToBedEdge(Vector2 end, Vector2 inward, IList<GameObject> beds, float halfT, float yTop, float maxBack, Func<float, float, float> groundAt)
    {
        if (beds == null || beds.Count == 0 || maxBack <= 0.01f) return 0f;
        Vector2 d = inward.normalized, nrm = new Vector2(d.y, -d.x);
        for (float s = 0f; s <= maxBack + 1e-4f; s += 0.02f)
        {
            bool ok = true;
            foreach (float lat in new[] { -halfT, 0f, halfT })
            {
                Vector2 q = end + d * s + nrm * lat;
                float h = RayToBodies(beds, new Vector3(q.x, yTop, q.y), Vector3.down, 8f);
                float g = groundAt(q.x, q.y);
                if (float.IsNaN(h) || (!float.IsNaN(g) && yTop - h < g - 0.01f)) { ok = false; break; }
            }
            if (ok) return s;
        }
        return 0f;
    }
    /// <summary>点 <paramref name="p"/> の真上から下ろした光線が <paramref name="beds"/> の上向きの面に最初に当たる高さ(当たらなければ NaN)。</summary>
    public static float BedTopAt(Vector2 p, IList<GameObject> beds, float yTop)
    {
        float h = RayToBodies(beds, new Vector3(p.x, yTop, p.y), Vector3.down, 8f);
        return float.IsNaN(h) ? float.NaN : yTop - h;
    }
    /// <summary>**土の側(背)の天端の足りなさ**(2026-09-25・EDO-0430)。駒 <paramref name="g"/> の上向きの面を 0.05m 刻みで引き、
    /// **背の帯**(見え面 <paramref name="faces"/> の裏へ <see cref="SOIL_SIDE"/> 進むと駒の外へ出る点 = 裏込めの土が触れる所)のうち、
    /// 検査と皮が「天端」と読む点(周り <see cref="CREST_R"/> の同じ駒の最高から <see cref="CREST_BAND"/> 以内 ── <c>TopIndex.Top</c> と同じ篩)について、
    /// その点の背の面の高さ <paramref name="soilAt"/>(x,z) − 天端 の最大を返す(正 = 天端が背の面より低い ⇒ 土が石に被るか、皮が石の下へ掘れて背の帯が溝になる)。
    /// 測れる点が無ければ NaN。<paramref name="at"/> = 最も足りない点。
    /// <para>⭐ 野面の乱積みは石の頭が不揃いで、背の帯の天端の石は駒の最高より 0.1〜0.2(最小 0.3〜0.48)低い ──
    /// 背の石を全て背の面より上げると前の石が面から 0.4〜0.75 飛び出す(2026-09-25 実測・山王 本殿の西)ので、据えの高さには使わない。</para>
    /// 当たる先: 打ち切りの駒の採否(<see cref="PlaceNozuraRun"/> ── 下がる天端が周りの地表の下へ入るなら直線の駒で終える)、
    /// 土留めの背の被りの下調べ。</summary>
    public static float SoilSideCrestShort(GameObject g, IList<Vector2> faces, Func<float, float, float> soilAt, out Vector3 at)
    {
        at = Vector3.zero;
        var tris = new List<Vector3[]>();
        foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            var M = mf.transform.localToWorldMatrix; float sgn = M.determinant < 0f ? -1f : 1f;
            var vs = mesh.vertices; var ts = mesh.triangles;
            var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) W[i] = M.MultiplyPoint3x4(vs[i]);
            for (int t = 0; t + 2 < ts.Length; t += 3)
            {
                var tri = new[] { W[ts[t]], W[ts[t + 1]], W[ts[t + 2]] };
                var nv = Vector3.Cross(tri[1] - tri[0], tri[2] - tri[0]); float mag = nv.magnitude;
                if (mag > 1e-9f && sgn * nv.y / mag > 0.7f) tris.Add(tri);
            }
        }
        if (tris.Count == 0) return float.NaN;
        const float B = 0.25f;
        var hash = new Dictionary<long, List<int>>();
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        for (int id = 0; id < tris.Count; id++)
        {
            var t = tris[id];
            float a0 = Mathf.Min(t[0].x, Mathf.Min(t[1].x, t[2].x)), a1 = Mathf.Max(t[0].x, Mathf.Max(t[1].x, t[2].x));
            float b0 = Mathf.Min(t[0].z, Mathf.Min(t[1].z, t[2].z)), b1 = Mathf.Max(t[0].z, Mathf.Max(t[1].z, t[2].z));
            x0 = Mathf.Min(x0, a0); x1 = Mathf.Max(x1, a1); z0 = Mathf.Min(z0, b0); z1 = Mathf.Max(z1, b1);
            for (int i = Mathf.FloorToInt(a0 / B); i <= Mathf.FloorToInt(a1 / B); i++)
                for (int j = Mathf.FloorToInt(b0 / B); j <= Mathf.FloorToInt(b1 / B); j++)
                { long k = ((long)i << 32) ^ (uint)j; List<int> l; if (!hash.TryGetValue(k, out l)) { l = new List<int>(); hash[k] = l; } l.Add(id); }
        }
        Func<float, float, float> top = (x, z) =>
        {
            List<int> l; if (!hash.TryGetValue(((long)Mathf.FloorToInt(x / B) << 32) ^ (uint)Mathf.FloorToInt(z / B), out l)) return float.NaN;
            float best = float.NaN, y;
            foreach (var id in l) if (TriYAt(tris[id], x, z, out y) && (float.IsNaN(best) || y > best)) best = y;
            return best;
        };
        float worst = float.NegativeInfinity;
        for (float x = x0 + 0.025f; x < x1; x += 0.05f)
            for (float z = z0 + 0.025f; z < z1; z += 0.05f)
            {
                float y = top(x, z); if (float.IsNaN(y)) continue;
                bool soil = false;
                foreach (var f in faces) if (float.IsNaN(top(x - f.x * SOIL_SIDE, z - f.y * SOIL_SIDE))) { soil = true; break; }
                if (!soil) continue;
                float mx = y;
                for (int a = 0; a < 8; a++)
                { float ang = a * Mathf.PI / 4f; float t2 = top(x + Mathf.Cos(ang) * CREST_R, z + Mathf.Sin(ang) * CREST_R); if (!float.IsNaN(t2) && t2 > mx) mx = t2; }
                if (y < mx - CREST_BAND) continue;                  // 天端の帯の外(法・控え)── 土に入るのが正しい納め
                float want = soilAt(x, z); if (float.IsNaN(want)) continue;
                if (want - y > worst) { worst = want - y; at = new Vector3(x, y, z); }
            }
        return float.IsNegativeInfinity(worst) ? float.NaN : worst;
    }
    /// <summary>背の帯の奥行[m]。皮は周り 0.5m(CAPR 2 × 0.25)の天端で下げるので、同じだけ見る。</summary>
    public const float SOIL_SIDE = 0.5f;

    /// <summary>**段違いの継ぎ目を勾配の駒で斜めに流す**(指図 TW_Kado_Sode.stepJoint・EDO-0502 2026-10-06 夕「袖の表が段々のまま」)。
    /// 天端が一直線の区間 <paramref name="runs"/>(天端は crestAt(0) で読む)のうち、端が一点で会い天端の違う二本の組ごとに、**高い側の区間の継ぎ目の側の端**を
    /// <paramref name="choices"/>(x = 流しの走り・y = 勾配。指図の「2 間の ±0.12」「1 間の ±0.275」を先の物から)の最初に取れる走りで切り、
    /// その区間の天端を高い天端 → 低い天端へ一次で下ろす(=継ぎ目で天端が連続・段の駒も積み下ろしも要らない)。走りの勾配は「落差 ÷ 走り」で、駒は焼いた勾配の最も近い物
    /// (<see cref="EdoAssets.Own.SannoNozura"/>)── 落差と「走り × 勾配」の差が <paramref name="headTol"/>(頭の不揃い)を超える組は取らない。
    /// 取れる = 高い側の区間の長さ ≥ 走り で、残る平らな所が 0 か <paramref name="minFlat"/> 以上。
    /// 硬い: 取れない継ぎ目は流さず <paramref name="unresolved"/> へ(呼ぶ側が退けて ⚠)。⟶ 返す: 切り直した区間の並び(流しの区間は flow = true・名は元の名 + "_nagare")。
    /// 当たる先: 段違いの run で天端を割る野面の土留めすべて(岡部 TW_Kado_Sode の袖・TW_Minami_Koshi の返し、今後の各邸の袖石垣)。</summary>
    public static List<NozuraSeg> FlowStepJoints(List<NozuraSeg> runs, IList<Vector2> choices, float minFlat, float headTol,
                                                 List<string> unresolved, System.Text.StringBuilder log)
    {
        const float TOL = 0.05f;
        int n = runs.Count;
        var cut = new float[n, 2]; var drop = new float[n, 2]; var lowC = new float[n, 2];   // 端 e の流しの走り(0 = 流さない)
        for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++)
        {
            var sk = runs[k]; if (sk.crestAt == null) continue;
            Vector2 ep = e == 0 ? sk.a : sk.b; float ck = sk.crestAt(0f);
            for (int j = 0; j < n; j++)
            {
                if (j == k || runs[j].crestAt == null) continue;
                int f = Vector2.Distance(ep, runs[j].a) <= TOL ? 0 : Vector2.Distance(ep, runs[j].b) <= TOL ? 1 : -1; if (f < 0) continue;
                float cj = runs[j].crestAt(0f), d = ck - cj; if (d <= 0.05f) continue;    // こちらが高い側の組だけ
                float other = cut[k, 1 - e];
                float got = 0f;
                foreach (var c in choices)
                {
                    float rest = sk.Len - other - c.x;
                    if (rest < -1e-3f || (rest > 0.01f && rest < minFlat)) continue;
                    if (Mathf.Abs(c.x * c.y - d) > headTol + 1e-3f) continue;
                    got = c.x; break;
                }
                string tag = sk.name + " 端" + e + " → " + runs[j].name + "(段 " + d.ToString("F2") + "・高い側の長さ " + sk.Len.ToString("F2") + ")";
                if (got <= 0f) { unresolved.Add(tag); if (log != null) log.AppendLine("    ⚠ stepJoint 取れない: " + tag); }
                else { cut[k, e] = got; drop[k, e] = d; lowC[k, e] = cj; if (log != null) log.AppendLine("    stepJoint 流し: " + tag + " ── 走り " + got.ToString("F2") + "・勾配 " + (d / got).ToString("F3")); }
                break;
            }
        }
        var res = new List<NozuraSeg>();
        for (int k = 0; k < n; k++)
        {
            var sk = runs[k]; float L = sk.Len;
            if (cut[k, 0] <= 0f && cut[k, 1] <= 0f) { res.Add(sk); continue; }
            Vector2 d = sk.Dir; float c0 = sk.crestAt(0f);
            float s0 = cut[k, 0], s1 = L - cut[k, 1];
            if (cut[k, 0] > 0f)
            {
                float lc = lowC[k, 0], Lc = cut[k, 0];
                var f0 = new NozuraSeg { name = sk.name + "_nagare0", a = sk.a, b = sk.a + d * Lc, crestAt = sl => Mathf.Lerp(lc, c0, Mathf.Clamp01(sl / Lc)), footAt = sk.footAt, sidesAt = null, movesAtConcave = sk.movesAtConcave, flow = true };
                f0.noAbut[0] = sk.noAbut[0]; f0.mikiriTo[0] = sk.mikiriTo[0]; res.Add(f0);
            }
            if (s1 - s0 > 0.01f)
            {
                var m = new NozuraSeg { name = sk.name, a = sk.a + d * s0, b = sk.a + d * s1, crestAt = sk.crestAt, footAt = sk.footAt, movesAtConcave = sk.movesAtConcave };
                if (cut[k, 0] <= 0f) { m.noAbut[0] = sk.noAbut[0]; m.mikiriTo[0] = sk.mikiriTo[0]; }
                if (cut[k, 1] <= 0f) { m.noAbut[1] = sk.noAbut[1]; m.mikiriTo[1] = sk.mikiriTo[1]; }
                res.Add(m);
            }
            if (cut[k, 1] > 0f)
            {
                float lc = lowC[k, 1], Lc = cut[k, 1];
                var f1 = new NozuraSeg { name = sk.name + "_nagare1", a = sk.a + d * s1, b = sk.b, crestAt = sl => Mathf.Lerp(c0, lc, Mathf.Clamp01(sl / Lc)), footAt = sk.footAt, movesAtConcave = sk.movesAtConcave, flow = true };
                f1.noAbut[1] = sk.noAbut[1]; f1.mikiriTo[1] = sk.mikiriTo[1]; res.Add(f1);
            }
        }
        return res;
    }

    // ============================================================ 野面の土留めの網(2026-09-26・EDO-0437)
    /// <summary>野面の土留めの一区間(直線)。指図の run を口(石段の口)で割った一本ずつ。</summary>
    public class NozuraSeg
    {
        public string name; public Vector2 a, b;
        /// <summary>区間の中の走り(0 … 長さ)→ 設計の天端。</summary>
        public Func<float, float> crestAt;
        /// <summary>見え面の足元の平場の高さ(平場の外は NaN)。</summary>
        public Func<float, float, float> footAt;
        /// <summary>入隅でこちらが可動側(相手の見え面へ端を突き付ける)── 指図 joints の moves がこの run を名指す。</summary>
        public bool movesAtConcave;
        /// <summary>区間の中の走り → (低い側の地盤, 高い側の地盤)(指図の縦断)。無ければ null。</summary>
        public Func<float, Vector2> sidesAt;
        /// <summary>端(0 = a / 1 = b)が口の縁で、見切り石を置いて相手(城の石垣・袖の駒)から一歩引く ── 相手の駒。無ければ null。</summary>
        public List<GameObject>[] mikiriTo = new List<GameObject>[2];
        /// <summary>端(0 = a / 1 = b)を近くの駒へ突き付けず打ち切りで終える ── 1 駒より短い run を上手の run の駒の裏へ重ねて埋める所
        /// (<see cref="RunsByCrestGap"/>・EDO-0502 第24巡)。突き付けると重ねた分だけ縮んで駒が 0 になった。</summary>
        public bool[] noAbut = new bool[2];
        /// <summary>段の境を勾配の駒で斜めに流す区間(<see cref="FlowStepJoints"/>)── 前後の区間との天端の折れを段の境(段の駒・積み下ろし)に数えない。</summary>
        public bool flow;
        /// <summary>区間全体の見付の下限(端の隅の返しの駒 ── kadoReturnUniform)。NaN なら無し。</summary>
        public float minH = float.NaN;
        /// <summary>端(0 = a / 1 = b)の際の一間と隅の駒の見付の下限(kadoReturnUniform ── 隅と並ぶ本線の駒も同じ H)。NaN なら無し。</summary>
        public float[] minHEnd = { float.NaN, float.NaN };
        /// <summary>端(0 = a / 1 = b)の小口を前の地表から沈める深さ(指図 sodeSlope「小口を前の地表から 0.3 以上下へ」【硬】)。NaN なら測らない。
        /// 据えた後に端の駒の小口の頂を測り、足りなければ ⛔ を刷る(⛔ 寄せない)。</summary>
        public float[] endSink = { float.NaN, float.NaN };
        /// <summary>端(0 = a / 1 = b)の一駒の焼いた H(見付の段)を名指す ── 指図 sodeSlope 追記 2026-10-07「低い端は水平の H0600 を一駒」。NaN なら無し。</summary>
        public float[] fixHEnd = { float.NaN, float.NaN };
        /// <summary>端(0 = a / 1 = b)から走りの長さ ── その内に中ほどが入る駒は水平(勾配の駒を選ばない)。指図 sodeSlope 追記 2026-10-09「最初の駒1つ分は水平」【硬】。NaN なら無し。</summary>
        public float[] flatEnd = { float.NaN, float.NaN };
        /// <summary>見え面の向き(水平の単位)を名指す ── 背の向きが指図・設計面で決まっている区間(袖の坂: 背 = 設計面の高い側)。zero なら地表で決める。</summary>
        public Vector2 face;
        /// <summary>**入隅の通す側の延長の余り**(指図 const.abutOrder 追記 2026-10-10o【硬】「入隅は、先に据える壁を角の点から後の壁の背の側へ『後の壁の控え+0.3』以上通して止める」)。
        /// この区間が入隅の通す側になった端で、線を角の点から先へ「後の壁の控え(焼いた直線の駒の控えの後端の最大)+ この値」以上通し、天端は同じ一直線で土に埋める。
        /// NaN なら通さない(従前 ── 線の端点で止める)。<see cref="ApplyAbutOrder"/> が立てる。</summary>
        public float passConcave = float.NaN;
        /// <summary>端(0 = a / 1 = b)を**名指した駒の実面へ突き付けて止める**(見切り石・隅の駒・打ち切りを置かない)── 指図 TW_Kado_Hokuto.cuts 追記 2026-10-10o
        /// 「口の両端の本線は石段の切石の袖の外の面に入隅で突き付けて止め」【硬】。無ければ null。</summary>
        public List<GameObject>[] abutTo = new List<GameObject>[2];
        public float Len { get { return Vector2.Distance(a, b); } }
        public Vector2 Dir { get { return (b - a).normalized; } }
    }

    /// <summary>**長屋の躯体か**(型で ── ⛔ 名の頭文字で見ない): 駒のメッシュの名か資産のパスに「Nagaya」を含む。
    /// 岡部では練塀の run(NW_Hei・N_Hei_26)の名も N で始まり、名で見ると練塀を長屋と見なして一間で塞いでいた(EDO-0502 第34巡)。
    /// 当たる先: 塞ぐ物・離れを長屋とそれ以外で分ける所すべて(NozuraEndRule.blockedDir・koshiKeep)。</summary>
    public static bool IsNagayaBody(GameObject g)
    {
        if (g == null) return false;
        foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
        {
            var m = mf.sharedMesh; if (m == null) continue;
            if (m.name.IndexOf("Nagaya", StringComparison.OrdinalIgnoreCase) >= 0) return true;
#if UNITY_EDITOR
            if (UnityEditor.AssetDatabase.GetAssetPath(m).IndexOf("Nagaya", StringComparison.OrdinalIgnoreCase) >= 0) return true;
#endif
        }
        return false;
    }

    /// <summary>**駒の走りの向き**(実メッシュの頂点の水平の主軸・単位)。点が一つも無ければ zero。⛔ 回転・基準点で見ない。
    /// 当たる先: 延ばす向きを「横切る」か「平行に走る」かを分ける所(NozuraEndRule.blockedDir)。</summary>
    public static Vector2 RunAxis(GameObject g)
    {
        var vs = Body(g.transform, 2000); if (vs.Count < 2) return Vector2.zero;
        Vector2 c = Vector2.zero; foreach (var v in vs) c += new Vector2(v.x, v.z); c /= vs.Count;
        float sxx = 0f, sxz = 0f, szz = 0f; foreach (var v in vs) { float dx = v.x - c.x, dz = v.z - c.y; sxx += dx * dx; sxz += dx * dz; szz += dz * dz; }
        float ang = 0.5f * Mathf.Atan2(2f * sxz, sxx - szz); return new Vector2(Mathf.Cos(ang), Mathf.Sin(ang));
    }

    /// <summary>**野面の土留めの端の納め**(2026-10-06・EDO-0502 第30巡・指図 nozuraEndRule)。相手の居ない端(打ち切りになる端)を
    /// 駒の継ぎ目の切り口で終えない【硬】── 端ごとに ① 延ばせる端は天端を背の地盤なりに勾配の駒(最大 <see cref="maxGrade"/>/m)で下げ、
    /// 見付が打ち切りの駒で足りる所(焼いた見付の最低)まで延ばして打ち切りの駒で終える ② 延ばす先が <see cref="blocked"/> で塞がる端は見切り石
    /// (<see cref="mikiri"/>・頭を端の天端に揃え、足りない見付は下へ沈める)③ どちらも取れない端は ⛔ で刷って数える(直線の駒で終えた端)。
    /// 渡さない邸(null)は従前どおり。当たる先: PlaceNozuraNet を呼ぶ全邸(岡部 Stage2b が渡す。山王・松江松平・土井は渡していない)。</summary>
    public class NozuraEndRule
    {
        /// <summary>点 → 塞がる理由(長屋の妻・溝の口・道・区画線)。塞がらなければ null。</summary>
        public Func<Vector2, string> blocked;
        /// <summary>点・延ばす向き → 塞がる理由(指図 nozuraEndRule 追記3: 塞ぐ物は延ばす向きを横切る実面と長屋の躯体から一間だけ ──
        /// 延ばす線に沿って平行に走る練塀・基壇は数えない)。在れば <see cref="blocked"/> に代えてこれを使う。</summary>
        public Func<Vector2, Vector2, string> blockedDir;
        /// <summary>塞がる理由(blockedDir が在ればそれ・無ければ blocked)。</summary>
        public string Block(Vector2 q, Vector2 dir) { return blockedDir != null ? blockedDir(q, dir) : blocked != null ? blocked(q) : null; }
        /// <summary>見付 → 見切り石のパス(焼いてある段のうち見付以上で最も低いもの)。</summary>
        public Func<float, string> mikiri;
        /// <summary>延ばす区間で天端を下げる勾配の上限 [m/m](焼いた勾配の駒 ±0.275)。</summary>
        public float maxGrade = 0.275f;
        /// <summary>延ばす長さの上限 [m]。</summary>
        public float maxExtend = 14f;
        /// <summary>記録: 端ごとの納め(打ち切り/見切り石/隅の駒/相手の面/⛔)。</summary>
        public List<string> record = new List<string>();
        /// <summary>**積み止めの駒を受ける口**(指図 TW_Minami_Koshi.returnEnd・TW_Nishi_Kado.endKado「③は積み止めで終える」・EDO-0502 第42巡)。
        /// (見付 H, 小口の面が局所 +X か, 個体) → 積み止めの駒のパス(<see cref="EdoAssets.Own.SannoNozuraTome"/>)。null(既定)なら ③ のまま直線の駒で終える。
        /// ③ の端は走りを <see cref="tomeRun"/> だけ縮めて直線の駒を並べ、その先へ積み止めの駒を据える(<see cref="PlaceNozuraTome"/>・第43巡)。</summary>
        public Func<float, bool, int, string> tome;
        /// <summary>要る見付(端の見付 + <see cref="tomeNeiri"/>)→ 焼いてある積み止めの段のうち最も低いもの(無ければ NaN ⇒ ③⛔)。</summary>
        public Func<float, float> tomeH;
        /// <summary>積み止めの根入れの下限(指図 追記b「見付+根入れ0.3以上の最も低い段」)と、駒の走り(天端の線で 0.909)。</summary>
        public float tomeNeiri = 0.3f, tomeRun = 0.909f;
        /// <summary>③ に落ちた端の数(直線の駒で終えた端)。</summary>
        public int unresolved;
        // ---- koshiEnd(指図 nozuraEndRule 追記 2026-10-06・EDO-0502 第31巡)── 背が法の腰の土留めの端の背を小段に切る ----
        /// <summary>区間の名 → 背が法の腰の土留めか(koshiEnd を当てる)。null なら当てない。</summary>
        public Func<string, bool> koshi;
        /// <summary>小段の高さ = 端の天端 − koshiDrop(指図 0.05)・小段の奥行 = 見え面の線から koshiBench(指図 一間 ── 石の控えを含めて読む・第31巡)・その先の法 1:koshiBatter(指図 1.5)・切りの上限 koshiCutMax(指図 1.0)。</summary>
        public float koshiDrop = 0.05f, koshiBench = 1.818f, koshiBatter = 1.5f, koshiCutMax = 1.0f;
        /// <summary>区間の名 → 切りの上限(指図 terraceWalls[].endCutMax ── 背が設計の切土の法なら 1.1・地山なら 1.0)。NaN・null なら koshiCutMax。</summary>
        public Func<string, float> koshiCutMaxOf;
        // ---- toeEnd(指図 nozuraEndRule 追記3・EDO-0502 第34巡)── 背が盛りの法尻の野面石の端は、見切り石が背の土に埋まるとき toeBench で背を描き直してから据え直す ----
        /// <summary>区間の名 → 背が盛りの法尻の土留めか(toeBench を当てる)。null なら当てない。</summary>
        public Func<string, bool> toe;
        /// <summary>toeBench の数(指図 天端 − toeDrop・控えの後端 + toeBehind・法 1:toeBatter)。盛りを減らす量は切りの上限に数えない。</summary>
        public float toeDrop = 0.05f, toeBehind = 0.3f, toeBatter = 1.5f;
        /// <summary>切らない所(点・切った後の高さ → 守るか ── 建物の足あと・塀の床の升)。null なら無し。</summary>
        public Func<Vector2, float, bool> toeKeep;
        /// <summary>小段と法が割ってはならない駒(練塀)と離れ(指図 犬走り 0.3)。</summary>
        public List<GameObject> koshiKeep; public float koshiKeepGap = 0.3f;
        /// <summary>区画(⛔ 外の節点は切らない)。</summary>
        public Vector2[] parcel;
        // ---- tallEnd(同 追記)── 見付が見切り石の最高段を超える端は背の側へ折り返す ----
        /// <summary>見切り石の最高段の見付(指図 2.4)。これを超える端を折り返す。0 なら当てない。</summary>
        public float tallMin = 0f;
        /// <summary>返しを終える「表の地表と背の地盤の差」(指図 0.6)と、返しの長さの上限 [m]。</summary>
        public float tallReturnDiff = 0.6f, tallReturnMax = 12f;
        // ---- ④ 差し込み(指図 nozuraEndRule 追記2 2026-10-06・EDO-0502 第32巡)── 端の先の見え面の線上の地盤が天端より高い端は、天端のまま線を延ばし
        //   地盤が天端 + insertReach に届く所から insertTail(半駒)先で終えて端の小口を地中に置く。延長の上限 insertMax(2 駒)。0 なら当てない ----
        /// <summary>差し込みの延長の上限 [m](指図 2 駒 3.6)。0 なら ④ を当てない。</summary>
        public float insertMax = 0f;
        /// <summary>届いたと見る地盤の高さ = 天端 + insertReach(指図 0.1)・届いた所から先へ insertTail(指図 半駒 0.9)で終える。</summary>
        public float insertReach = 0.1f, insertTail = 0.9f;
        // ---- koshiEnd の改め(同 追記2)── 小段の奥行の下限 = 駒の控えの後端 + koshiBenchBack・その先の法は背が切土なら koshiBatterCut ----
        /// <summary>小段の奥行の下限 = 駒の控えの後端 + koshiBenchBack(指図 0.3)【硬】。狙いは koshiBench(一間)【柔】。</summary>
        public float koshiBenchBack = 0.3f;
        /// <summary>背が切土の点か(⟶ 法 1:koshiBatterCut。指図 const.batterCut)。null なら全部 koshiBatter。</summary>
        public Func<Vector2, bool> koshiIsCut; public float koshiBatterCut = 1.0f;
        /// <summary>小段を端の先の低い側へ落とす勾配(指図 1/20)。</summary>
        public float koshiDrain = 20f;
        /// <summary>④ で差し込んだ端(xy = 元の端・zw = 延ばした量のベクトル)。呼び出し元が前の地表の水の向きを確かめる。</summary>
        public List<Vector4> insertDone = new List<Vector4>();
        // ---- ② 隅の駒の返し(指図 nozuraEndRule 2026-10-06 夕 ── 見切り石を野面の端に使わない)----
        /// <summary>② を見切り石でなく野面の出隅の隅の駒で背の側へ折り返す。返しの腕は retMin〜retMax、背の地盤が天端 − retBackDiff 以内に届いた所で終える【硬】。
        /// ②' 返せない端は端から一間を lowerGrade(下げ打ちの駒)で下げ、見付 ≤ lowerToExpose なら低い隅の駒(腕 retMin)で根を沈めて終える【硬】。どちらも取れなければ ③。</summary>
        public bool kadoReturn;
        /// <summary>隅の返しの腕が入ってはならない所(点・腕の向き → 理由)。指図「腕は塞ぐ物の実面・長屋の背の一間・犬走り 0.3 に入れない」── 延ばす向きの塞ぐ物(長屋の躯体から一間の全周)より狭い。
        /// null なら <see cref="Block"/>。</summary>
        public Func<Vector2, Vector2, string> armBlock;
        public string ArmBlock(Vector2 q, Vector2 dir) { return armBlock != null ? armBlock(q, dir) : Block(q, dir); }
        public float retMin = 0.909f, retMax = 1.818f, retBackDiff = 0.3f, lowerGrade = 0.275f, lowerToExpose = 0.9f;
        /// <summary>端ごとの型(指図の欄が名指す端 ── returnEnd・endKado・kadoReturnUniform・EDO-0502 第41巡)。(区間, 端) → 型。null・null を返せば上の既定。</summary>
        public Func<NozuraSeg, int, EndSpec> spec;
    }

    /// <summary>**名指された端の型**(<see cref="NozuraEndRule.spec"/>・EDO-0502 第41巡)。指図の欄の文の値を邸の側が読んで入れる(⛔ ここに数を決め打ちしない)。
    /// 順: ⓪ <see cref="abutAhead"/>(延ばす向きのその距離の内に相手の実面が在れば入隅で突き付け)→ ② 隅の返し(腕の向き <see cref="armDir"/>・
    /// 腕 <see cref="armMin"/>〜retMax か定尺 <see cref="armFixed"/>・<see cref="uniformH"/> で隅と返しと本線の際の H を揃える)→ ②' 下げ打ち(<see cref="lowerGrade"/> で
    /// 最大 <see cref="lowerMaxPieces"/> 駒・見付 ≤ <see cref="lowerToExpose"/>)→ ① 沈め(<see cref="sinkIfShort"/>: <see cref="sinkGrade"/> で最大 <see cref="sinkMaxPieces"/> 駒下げて見付 ≤ <see cref="sinkExpose"/>・隅なし)→ ③。</summary>
    public class EndSpec
    {
        public string label;
        public float abutAhead = float.NaN; public List<GameObject> abutPool;
        /// <summary>(端の点, 見え面の向き) → 腕の向き(単位)。null なら背の側(−見え面)。</summary>
        public Func<Vector2, Vector2, Vector2> armDir;
        public float armMin = float.NaN, armFixed = float.NaN; public bool uniformH;
        public bool noLower; public float lowerGrade = float.NaN, lowerToExpose = float.NaN; public int lowerMaxPieces = 1;
        public bool sinkIfShort; public float sinkGrade = float.NaN, sinkExpose = float.NaN; public int sinkMaxPieces = 1;
        /// <summary>名指しの積み止め(指図 returnEnd「端は積み止めで終える」・endKado「積み止めの H2400 で終える」)── ②〜④ を当てずに積み止めで終える。
        /// <see cref="tomeH"/> が NaN なら見付 + 根入れの規則で段を選ぶ。</summary>
        public bool tome; public float tomeH = float.NaN;
        /// <summary>**積み止めの行く手の塀からの離れ**【硬】(指図 TW_Nishi_Kado.endKado 追記 2026-10-07「積み止めの駒は埋まる控えまで含めて区画の線の外へ 0・
        /// 駒の最も外の点を塀の内面から 0.3 以上内 ── 端を run に沿って内へ引く(目安 0.9・PlaceBest)」・EDO-0502 第45巡)。NaN なら当てない。
        /// 引き = 端を走りに沿って内へ戻す量。候補 0〜<see cref="tomePullMax"/>(0.1 刻み)を <see cref="tomePullAim"/>【柔】に近い順に試し、
        /// <see cref="TomeClearShort"/>(区画の外 0・行く手の辺の塀 <see cref="tomeWalls"/> の内面 + 離れ)を通る所を <see cref="PlaceBest{T}"/> で選ぶ。</summary>
        public float tomeClear = float.NaN, tomePullAim = float.NaN, tomePullMax = 2.7f;
        public List<GameObject> tomeWalls; public Vector2[] tomeParcel;
    }

    /// <summary>**積み止めの駒が行く手の塀へ足りない離れ**(<see cref="EndSpec.tomeClear"/>・EDO-0502 第45巡)── 0 以下なら通る。
    /// ① 区画の外 0【硬】: 駒の実メッシュの頂点(埋まる控えまで)のうち区画の外の最も遠いもの。
    /// ② 行く手の辺(内向きの法線が走りの向き <paramref name="away"/> と向き合う辺 ── cos &lt; −0.7)ごとに、塀の内面 = 塀の駒の実メッシュの頂点のうち
    /// その辺が最も近く・駒の走りの範囲 ±1m・駒の天端 + 0.5 より下(駒が当たり得る高さ)の、辺からの内への最大。要る離れ = 内面 + <paramref name="clear"/>、
    /// 駒の最も外の点(辺からの内への最小)との差。⛔ ピボット・bounds で測らない。⛔ 走りに並ぶ辺(塀が駒の脇を走る)は数えない ── 引いても変わらない。
    /// 当たる先: 区画の線際の塀へ向かって終わる野面の積み止め(岡部 TW_Nishi_Kado_辺24_1_0)。⟶ 返す: 不足の最大(why に辺と内面)。</summary>
    public static float TomeClearShort(GameObject g, Vector2 away, IList<GameObject> walls, Vector2[] parcel, float clear, out string why)
    {
        why = ""; float worst = float.NegativeInfinity;
        var vs = Body(g.transform, 999999); if (vs.Count == 0) { why = "駒の頂点が無い"; return float.PositiveInfinity; }
        float topY = float.MinValue; foreach (var v in vs) topY = Mathf.Max(topY, v.y);
        if (parcel == null || parcel.Length < 3) { why = "区画が無い"; return float.PositiveInfinity; }
        foreach (var v in vs) { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(parcel, q)) { float d = EdoGeom.DistToPolyEdge(parcel, q); if (d > worst) { worst = d; why = "区画の外 " + d.ToString("F3"); } } }
        if (worst == float.NegativeInfinity) { worst = 0f; why = "区画の内"; }
        int n = parcel.Length;
        Vector2 gc = Vector2.zero; foreach (var v in vs) gc += new Vector2(v.x, v.z); gc /= vs.Count;
        Func<Vector2, int> nearestEdge = q => { int bi = -1; float bd = float.MaxValue; for (int j = 0; j < n; j++) { Vector2 A = parcel[j], B = parcel[(j + 1) % n], ab = B - A; float u = Mathf.Clamp01(Vector2.Dot(q - A, ab) / Mathf.Max(ab.sqrMagnitude, 1e-9f)); float d = (A + ab * u - q).sqrMagnitude; if (d < bd) { bd = d; bi = j; } } return bi; };
        for (int i = 0; i < n; i++)
        {
            Vector2 A = parcel[i], B = parcel[(i + 1) % n]; float len = Vector2.Distance(A, B); if (len < 1e-3f) continue;
            Vector2 d = (B - A) / len, inw = new Vector2(-d.y, d.x); if (!EdoGeom.PIP(parcel, (A + B) * 0.5f + inw * 0.05f)) inw = -inw;
            if (Vector2.Dot(inw, away) > -0.7f) continue;
            float s0 = float.MaxValue, s1 = float.MinValue, tMin = float.MaxValue;
            foreach (var v in vs) { var q = new Vector2(v.x, v.z); float s = Vector2.Dot(q - A, d); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); if (s >= -0.05f && s <= len + 0.05f) tMin = Mathf.Min(tMin, Vector2.Dot(q - A, inw)); }
            if (s1 < -0.05f || s0 > len + 0.05f || tMin > 4f) continue;   // 駒がこの辺の脇に無い・遠い
            float wIn = float.NegativeInfinity; string wn = null;
            if (walls != null) foreach (var w in walls)
            {
                if (w == null || !w.activeInHierarchy) continue;
                var bb = RB(w); if (bb.SqrDistance(new Vector3(gc.x, bb.center.y, gc.y)) > 36f) continue;
                foreach (var v in Body(w.transform, 999999))
                {
                    if (v.y > topY + 0.5f) continue; var q = new Vector2(v.x, v.z); float s = Vector2.Dot(q - A, d);
                    if (s < s0 - 1f || s > s1 + 1f || s < 0f || s > len) continue; float t = Vector2.Dot(q - A, inw); if (t < -1f || t > 3f) continue;
                    if (nearestEdge(q) != i) continue;
                    if (t > wIn) { wIn = t; wn = w.name; }
                }
            }
            if (wIn == float.NegativeInfinity) continue;
            float sh = wIn + clear - tMin;
            if (sh > worst) { worst = sh; why = "辺" + i + " の塀の内面 " + wIn.ToString("F2") + "(" + wn + ")+ " + clear.ToString("F2") + " に対し駒の最も外 " + tMin.ToString("F2"); }
            else if (why == "区画の内") why = "辺" + i + " の塀の内面 " + wIn.ToString("F2") + "(" + wn + ")+ " + clear.ToString("F2") + " ≤ 駒の最も外 " + tMin.ToString("F2");
        }
        return worst;
    }

    /// <summary>積み止めで終える端の段取り(PlaceNozuraNet の内)。</summary>
    class TomeEnd { public float H, crest, hT; public Vector2 ep, fN, away; public string label; }

    /// <summary>野面の端の ② / ②'(指図 nozuraEndRule 2026-10-06 夕)── 塞がる端を野面の出隅の隅の駒で背の側へ折り返す返しの区間を <paramref name="add"/> へ足す
    /// (隅の駒は鎖が出隅として据える・返しの終わりは打ち切り)。② = 返しの腕 retMin〜retMax で背の地盤(返しの見え面の裏 probe)が天端 − retBackDiff 以内に届く所まで。
    /// ②' = 届かない・塞がる端は、端から一間 <paramref name="W"/> を下げ打ち(lowerGrade)で下げ、見付 ≤ lowerToExpose なら腕 retMin の低い隅で終える(根は沈める)。
    /// 腕が塞ぐ物(endRule.Block = 長屋の背の一間・横切る実面・区画線)に入る端は取らない ⇒ ③(⛔ 見切り石・直線の駒で黙って終えない)。⟶ 返す: 端の型の記録。
    /// 当たる先: endRule.kadoReturn を渡す邸(岡部 Stage2b)の野面の端すべて。</summary>
    static string KadoReturnEnd(NozuraEndRule r, NozuraSeg sg, int e, Vector2 ep, Vector2 away, Vector2 fN, float c0, float h0, string why,
                                Func<float, float, float> groundAt, float probe, float W, List<NozuraSeg> add, float[] heights = null)
    {
        var sp = r.spec != null ? r.spec(sg, e) : null;
        // 腕の向き(指図 returnEnd「左右のうち長屋の躯体の実面から遠ざかる側」── 邸が測って渡す)。既定は背の側(−見え面)
        Vector2 armD = sp != null && sp.armDir != null ? sp.armDir(ep, fN) : -fN; if (armD == Vector2.zero) armD = -fN; armD.Normalize();
        float aMin = sp != null && !float.IsNaN(sp.armMin) ? sp.armMin : r.retMin;
        string tagS = sp != null && sp.label != null ? "〔" + sp.label + "〕" : "";
        // 腕の候補を測る: 腕の線 q = ep + armD·t の上で、塞ぐ物と背の地盤(返しの見え面 away の裏)
        Func<float, float, float> armLen = (crest, need) =>
        {
            float lastFree = 0f;
            for (float t = 0.1f; t <= r.retMax + 1e-3f; t += 0.1f)
            {
                Vector2 q = ep + armD * t;
                if (r.ArmBlock(q, armD) != null) return lastFree + 1e-3f < need ? -1f : (sp != null && !float.IsNaN(sp.armMin) ? lastFree : float.NaN);   // 名指しの端は塞ぐ物の手前まで(下限 armMin)
                lastFree = t;
                if (t + 1e-3f < need) continue;
                float bk = groundAt(q.x - away.x * probe, q.y - away.y * probe);
                if (!float.IsNaN(bk) && bk >= crest - r.retBackDiff) return t;
            }
            return sp != null && !float.IsNaN(sp.armMin) ? lastFree : float.NaN;
        };
        string head = "(" + (why ?? "延ばしても見付が下がらない") + "・見付 " + h0.ToString("F2") + ")" + tagS;
        // 見付を揃える H(kadoReturnUniform ── 端の見付以上で最も低い焼いた段)
        float hUni = float.NaN;
        if (sp != null && sp.uniformH && heights != null) { foreach (var hh in heights) if (hh >= h0 - 1e-3f) { hUni = hh; break; } if (float.IsNaN(hUni)) hUni = heights[heights.Length - 1]; }
        float Lr;
        // ⭐ 定尺一本の腕の区間は「隅の駒の腕(半駒 W/2)+ 定尺の直線の駒 armFixed」(2026-10-07 EDO-0502 第44巡)。
        //   旧は区間を armFixed にしていた ⇒ 隅の腕 0.909 を引いた残り 0.91 に直線の駒を ×0.45 に縮めて押し込み、石が潰れて隅の組みが乱れた
        //   (岡部 TW_Kita_Koshi_0_0_Kado0_124f sc 0.447)。余り(定尺 − 要る腕)は区間の先 = 背の土の側へ出して埋める。
        //   当たる先: endRule の EndSpec.armFixed を渡す端すべて(岡部 TW_Kita_Koshi.kadoReturnUniform の2端)。
        float armSeg = sp != null && !float.IsNaN(sp.armFixed) ? sp.armFixed + W * 0.5f : float.NaN;
        if (sp != null && !float.IsNaN(sp.armFixed))
        {   // 定尺一本(指図 kadoReturnUniform「腕は 1.8 の定尺一本で据えて余りは背の土へ埋める」)── 塞がれば測った腕へ(⚠)
            Lr = armSeg; for (float t = 0.1f; t <= armSeg + 1e-3f; t += 0.1f) if (r.ArmBlock(ep + armD * t, armD) != null) { Lr = armLen(c0, aMin); break; }
        }
        else Lr = armLen(c0, aMin);
        if (!float.IsNaN(Lr) && Lr >= aMin - 1e-3f)
        {
            float cc = c0; var ret = new NozuraSeg { name = sg.name + "_Kado" + e, a = ep, b = ep + armD * Lr, crestAt = sl => cc };
            // ⭐ 返しの見え面は端の外向き away(2026-10-07 第44巡)── 地表の低い側の票に任せると、背の側へ折れる短い腕は表の土の側を
            //   見え面に取り、隅を入隅と見立てて隅の駒を据えなかった(岡部 TW_Kita_Koshi_3_0_raise_Kaeshi1 端1)。
            ret.face = away.normalized;
            ret.noAbut[1] = true; if (!float.IsNaN(hUni)) { ret.minH = hUni; sg.minHEnd[e] = hUni; } add.Add(ret);
            return "②隅の駒で返し(腕 " + Lr.ToString("F2") + (Vector2.Dot(armD, -fN) > 0.5f ? "・背の側" : "・前の側") + "・天端 " + c0.ToString("F2")
                 + (sp != null && !float.IsNaN(sp.armFixed) ? (Mathf.Abs(Lr - armSeg) < 1e-3f ? "・隅の腕+定尺一本" : "・⚠ 定尺 " + sp.armFixed.ToString("F2") + " が塞がり測った腕") : "")
                 + (!float.IsNaN(hUni) ? "・隅と返しと際の H を " + hUni.ToString("F2") + " に揃える" : "") + ")" + head;
        }
        string armWhy = Lr < 0f || (!float.IsNaN(Lr) && Lr < aMin) ? "腕が塞ぐ物に入る: " + r.ArmBlock(ep + armD * Mathf.Max(0.1f, (float.IsNaN(Lr) ? 0f : Lr) + 0.1f), armD) + "(取れる腕 " + (float.IsNaN(Lr) || Lr < 0f ? "0.00" : Lr.ToString("F2")) + " < " + aMin.ToString("F2") + ")"
                                                                    : "背の地盤が腕 " + r.retMax.ToString("F1") + " 以内で天端−" + r.retBackDiff.ToString("F1") + " に届かない";
        // ②' 下げ打ち: 端から k 駒を下げ、低い隅の駒(腕 aMin〜retMin)で根を沈めて終える
        if (sp == null || !sp.noLower)
        {
            float lg = sp != null && !float.IsNaN(sp.lowerGrade) ? sp.lowerGrade : r.lowerGrade, lt = sp != null && !float.IsNaN(sp.lowerToExpose) ? sp.lowerToExpose : r.lowerToExpose;
            int kMax = sp != null ? Mathf.Max(1, sp.lowerMaxPieces) : 1, kUse = -1;
            for (int k = 1; k <= kMax; k++) if (h0 - lg * W * k <= lt + 1e-3f) { kUse = k; break; }
            string fail = null;
            if (kUse < 0) fail = "②' " + kMax + " 駒下げても見付 " + (h0 - lg * W * kMax).ToString("F2") + " > " + lt.ToString("F1");
            else if (sg.Len < kUse * W + 0.5f) fail = "②' 区間 " + sg.Len.ToString("F2") + "m が " + kUse + " 駒に足りない";
            float armLow = float.NaN;
            if (fail == null)
            {
                float lim = sp != null && !float.IsNaN(sp.armMin) ? r.retMin : r.retMin;
                armLow = lim; for (float t = 0.1f; t <= lim + 1e-3f; t += 0.1f) if (r.ArmBlock(ep + armD * t, armD) != null) { armLow = t - 0.1f; break; }
                if (armLow < aMin - 1e-3f) fail = "②' 低い隅の腕 " + Mathf.Max(0f, armLow).ToString("F2") + " < " + aMin.ToString("F2") + "(" + r.ArmBlock(ep + armD * Mathf.Max(0.1f, armLow + 0.1f), armD) + ")";
            }
            if (fail == null)
            {
                float dz = lg * W * kUse, c1 = c0 - dz, Lz = kUse * W; var old = sg.crestAt; float L = sg.Len;
                if (e == 1) sg.crestAt = sl => sl <= L - Lz ? old(sl) : old(L - Lz) - lg * (sl - (L - Lz));
                else sg.crestAt = sl => sl >= Lz ? old(sl) : old(Lz) - lg * (Lz - sl);
                var ret2 = new NozuraSeg { name = sg.name + "_Kado" + e, a = ep, b = ep + armD * armLow, crestAt = sl => c1 };
                ret2.face = away.normalized; ret2.noAbut[1] = true; add.Add(ret2);
                return "②'下げ打ち(" + kUse + " 駒で " + c0.ToString("F2") + "→" + c1.ToString("F2") + "・勾配 " + lg.ToString("F3") + "・見付 " + (h0 - dz).ToString("F2") + ")+ 低い隅の駒(腕 " + armLow.ToString("F2")
                     + (armLow < r.retMin - 1e-3f ? " ⚠ 隅の駒の腕 0.91 より短い ── 腕を詰めた隅は焼いていない" : "") + "・根を沈める)" + head;
            }
            if (sp == null || !sp.sinkIfShort) return "③⛔ ②返せず(" + armWhy + ")・" + fail + head;
            armWhy += "・" + fail;
        }
        // ① 沈め(指図 returnEnd「腕が 0.6 未満になる端は隅をやめ、返しの線の上で一駒を G−450 で下げ見付 0.15 で沈める」・endKado「0.6 未満なら隅を外して①で沈める」)
        if (sp != null && sp.sinkIfShort && !float.IsNaN(sp.sinkGrade))
        {
            int kS = -1; for (int k = 1; k <= Mathf.Max(1, sp.sinkMaxPieces); k++) if (h0 - sp.sinkGrade * W * k <= sp.sinkExpose + 1e-3f) { kS = k; break; }
            if (kS < 0) return "③⛔ ②返せず(" + armWhy + ")・① " + sp.sinkMaxPieces + " 駒を勾配 " + sp.sinkGrade.ToString("F2") + " で下げても見付 " + (h0 - sp.sinkGrade * W * sp.sinkMaxPieces).ToString("F2") + " > " + sp.sinkExpose.ToString("F2") + head;
            if (sg.Len < kS * W + 0.3f) return "③⛔ ②返せず(" + armWhy + ")・① 区間 " + sg.Len.ToString("F2") + "m が " + kS + " 駒に足りない" + head;
            float g2 = sp.sinkGrade, Lz = kS * W; var old = sg.crestAt; float L = sg.Len;
            if (e == 1) sg.crestAt = sl => sl <= L - Lz ? old(sl) : old(L - Lz) - g2 * (sl - (L - Lz));
            else sg.crestAt = sl => sl >= Lz ? old(sl) : old(Lz) - g2 * (Lz - sl);
            sg.noAbut[e] = true;   // 打ち切り(隅なし)
            return "①沈め(隅をやめ " + kS + " 駒を勾配 " + g2.ToString("F2") + " で " + c0.ToString("F2") + "→" + (c0 - g2 * Lz).ToString("F2") + "・見付 " + (h0 - g2 * Lz).ToString("F2") + " ── " + armWhy + ")" + head;
        }
        return "③⛔ ②返せず(" + armWhy + ")" + head;
    }

    /// <summary>**野面の土留めの網を据える**(2026-09-26・EDO-0437)。区間どうしの取り合いを**描かれた地表で測った見え面**から解き、
    /// 一直線・出隅で継ぐ区間は一本の折れ線に継いで <see cref="PlaceNozuraRun"/> へ渡す(向きの逆な区間は裏返して継ぐ)。
    /// <para>端の納め: ① **入隅**(次の区間が見え面の側へ折れる)は継がない ── 可動側(<see cref="NozuraSeg.movesAtConcave"/>、
    /// 無ければ両端とも入隅の区間)の端を、通す側の据わった駒の実面へ突き付ける。通す側は線の端点で止め、打ち切りにしない。
    /// ② **口の縁で見切り石**(<see cref="NozuraSeg.mikiriTo"/>)── 見切り石を先に据え(<see cref="PlaceNozuraMikiri"/>)、土留めの端をその脇へ突き付ける。
    /// ③ それ以外で端から 1.5m 以内に据わった駒(<paramref name="pool"/>)が在れば、その実面へ突き付ける ④ 何も無ければ打ち切りの駒。</para>
    /// 順: 通す側の区間を先に(可動側は相手が据わってから)。返り値 = 据えた駒と見え面の向き(駒の名は据わった区間の名)。
    /// 当たる先: 野面の乱積みの土留めすべて(山王 前庭の縁 TW_Zentei_*・切り込みの返し、今後の各邸の庭の土留め)。</summary>
    public static List<KeyValuePair<GameObject, Vector2>> PlaceNozuraNet(List<NozuraSeg> segs, Func<float, float, float> groundAt,
        Func<float, float, float> faceGroundAt, float probe,
        Transform parent, Func<float, float, int, string> straight, Func<float, int, string> kado, Func<bool, int, string> dan,
        Func<bool, int, string> kiri, Func<float, string> mikiriPath, float[] heights, List<GameObject> pool, System.Text.StringBuilder log,
        Func<float, bool, bool, float, int, string> kiriEnd = null, Func<float, bool, float, string> noriEnd = null,
        IList<GameObject> kadoAbut = null, NozuraEndRule endRule = null)
    {
        var res = new List<KeyValuePair<GameObject, Vector2>>();
        int n = segs.Count; if (n == 0) return res;
        const float W = 1.818f, TOL = 0.05f; float ctrlBack = 0f;
        // ⭐ 低い側を測る離れは**駒の天端の列の控え**(実メッシュ)── 城の石垣の奥行(2.4 + α)で測ると、野面の駒が受ける背の土の外
        //   (区画の線の際で地盤が下がる所)を拾って向きを違えた(前庭の E の南 5m が外を向いた・2026-09-26)。
        {
            var bv = BodyAt(straight(heights[0], 0f, 0), Vector3.zero, 0f, true);
            float top = float.MinValue; foreach (var v in bv) top = Mathf.Max(top, v.y);
            float zb = 0f; foreach (var v in bv) if (v.y >= top - 0.15f) zb = Mathf.Min(zb, v.z);
            if (zb < -0.2f) { log.AppendLine("  野面の低い側を測る離れ = 天端の列の控え " + (-zb).ToString("F2") + "m(城の石垣の " + probe.ToString("F2") + "m に代えて)"); probe = -zb; }
            foreach (var v in bv) ctrlBack = Mathf.Max(ctrlBack, -v.z);   // 駒の控えの後端(全頂点・koshiEnd の小段の奥行の下限)
        }
        // 入隅の通し(NozuraSeg.passConcave・const.abutOrder 10-10o)の「後の壁の控え」= 焼いた直線の駒(水平)の控えの後端の最大 ── 後の壁がどの段を据えても足りる
        float ctrlMax = ctrlBack;
        bool anyPass = false; foreach (var sg in segs) if (!float.IsNaN(sg.passConcave)) anyPass = true;
        if (anyPass)
            foreach (float hh in heights)
            {
                string pth = straight(hh, 0f, 0); if (string.IsNullOrEmpty(pth) || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(pth) == null) continue;
                foreach (var v in BodyAt(pth, Vector3.zero, 0f, true)) ctrlMax = Mathf.Max(ctrlMax, -v.z);
            }
        Func<NozuraSeg, int, Vector2> endPt = (sg, e) => e == 0 ? sg.a : sg.b;
        // 区間の端の際(1間)の見え面
        Func<NozuraSeg, int, Vector2> faceNear = (sg, e) =>
        {
            // 名指した見え面(NozuraSeg.face)が在れば先に採る ── 駒の向き(PlaceNozuraRun の faceAt)と継ぎの見立てを同じ向きで解く
            //   (2026-10-07 EDO-0502 第44巡: 隅の返しの腕の見え面を地表で測ると入隅と見立て、隅の駒が据わらなかった)
            if (sg.face.sqrMagnitude > 0.5f) return FaceAcross(sg.face, sg.Dir);
            float l = sg.Len, t = Mathf.Min(W, l);
            Vector2 pa = e == 0 ? sg.a : sg.b - sg.Dir * t, pb = e == 0 ? sg.a + sg.Dir * t : sg.b;
            var fg = faceGroundAt ?? groundAt;
            int vn, vx; var lo = LowSide(pa, pb, fg, probe, 0.05f, null, out vn, out vx);
            if (lo == Vector2.zero) lo = LowSide(sg.a, sg.b, fg, probe, 0.05f, null, out vn, out vx);
            return lo;
        };
        // 端の見付 = 端の駒が受け持つ走り(端から内へ 1.2W)で PlaceNozuraRun の needH と同じに測る(天端は走りの各点・足元は線の前 0.25/0.7 の最小の逆 = 最大の見付)
        float batN = NozuraBatter(new NozuraWall { straight = straight });   // 法尻の前で見付を取る(FootAhead)
        Func<NozuraSeg, int, Vector2, float> endExpose = (sg, e, fN0) =>
        {
            Vector2 ep0 = endPt(sg, e), aw = e == 1 ? sg.Dir : -sg.Dir; float h = float.MinValue;
            for (float s2 = 0f; s2 <= 1.2f * W + 1e-3f; s2 += 0.25f)
            {
                Vector2 q2 = ep0 - aw * Mathf.Min(s2, sg.Len); float cq = sg.crestAt(e == 0 ? Mathf.Min(s2, sg.Len) : Mathf.Max(0f, sg.Len - s2));
                foreach (float off in new[] { 0.25f, 0.7f })
                {
                    float fy = FootAhead(sg.footAt, groundAt, q2, fN0, off, cq, batN);
                    if (!float.IsNaN(fy)) h = Mathf.Max(h, cq - fy);
                }
            }
            return h == float.MinValue ? float.NaN : h;
        };
        // ---- tallEnd(指図 nozuraEndRule 追記・EDO-0502 第31巡)── 相手の居ない端で見付が見切り石の最高段(tallMin)を超える端は、
        //   背の側へ天端の揃った返しの区間を足す(出隅の隅の駒は鎖が kado で据える)。返しは表の地表(返しの見え面の前)と背の地盤の差が
        //   tallReturnDiff 未満になった所で終える(TW_Minami_Koshi.returnTop と同じ切り方)。塞ぐ物(blocked)に当たればそこで止める。
        //   硬い: 終わる所が見つからなければ返さない(③ で刷る)。当たる先: endRule.tallMin を渡す邸(岡部 Stage2b)の野面の端すべて。
        if (endRule != null && endRule.tallMin > 0f)
        {
            int n0 = segs.Count;
            for (int k = 0; k < n0; k++) for (int e = 0; e < 2; e++)
            {
                Vector2 ep = endPt(segs[k], e); bool joined = false;
                for (int j = 0; j < segs.Count && !joined; j++) for (int f = 0; f < 2; f++) if (j != k && Vector2.Distance(ep, endPt(segs[j], f)) <= TOL) joined = true;
                if (joined || segs[k].mikiriTo[e] != null || segs[k].noAbut[e] || segs[k].abutTo[e] != null) continue;
                bool near = false;
                foreach (var g in pool) if (g != null && !near) foreach (var v in Body(g.transform, 400)) if (Vector2.Distance(new Vector2(v.x, v.z), ep) < 1.5f) { near = true; break; }
                if (near) continue;
                Vector2 fN = faceNear(segs[k], e); if (fN == Vector2.zero) continue;
                float h0 = endExpose(segs[k], e, fN);
                if (float.IsNaN(h0) || h0 <= endRule.tallMin + 1e-3f) continue;
                Vector2 away = e == 1 ? segs[k].Dir : -segs[k].Dir;
                float c0 = segs[k].crestAt(e == 0 ? 0f : segs[k].Len);
                float Lr = float.NaN; string stop = null;
                for (float t = 0.5f; t <= endRule.tallReturnMax + 1e-3f; t += 0.25f)
                {
                    Vector2 q = ep - fN * t;
                    { stop = endRule.Block(q, -fN); if (stop != null) { Lr = t - 0.25f; break; } }
                    float fr = groundAt(q.x + away.x * 0.5f, q.y + away.y * 0.5f), bk = groundAt(q.x - away.x * probe, q.y - away.y * probe);
                    if (!float.IsNaN(fr) && !float.IsNaN(bk) && Mathf.Abs(bk - fr) < endRule.tallReturnDiff) { Lr = t; break; }
                }
                string tag = segs[k].name + " 端" + e;
                if (!float.IsNaN(Lr) && Lr <= 0.5f + 1e-3f && stop == null)
                { endRule.record.Add(tag + ": tallEnd ⛔ 見付 " + h0.ToString("F2") + " > " + endRule.tallMin.ToString("F1") + " ── 返しの初め(0.5m)で既に表と背の差 < " + endRule.tallReturnDiff.ToString("F1") + "(端の先も背も天端並みで返す土が無い・見付は見え面の前の地表の低さ)── 返さない(普請方へ)"); continue; }
                if (float.IsNaN(Lr) || Lr < 0.5f)
                { endRule.record.Add(tag + ": tallEnd ⛔ 見付 " + h0.ToString("F2") + " > " + endRule.tallMin.ToString("F1") + " ── 返しの終わる所が " + endRule.tallReturnMax.ToString("F0") + "m 以内に無い" + (stop != null ? "(" + stop + ")" : "")); continue; }
                float cc = c0;
                var ret = new NozuraSeg { name = segs[k].name + "_Kaeshi" + e, a = ep, b = ep - fN * Lr, crestAt = sl => cc };
                // 硬い: 返しの見え面は端の先(away)を向く出隅でなければならない・返しの終わりの見付は見切り石で受かる(≤ tallMin)こと ── どちらか外れれば返さない
                Vector2 rf = faceNear(ret, 0); float hr = endExpose(ret, 1, away);
                if (rf == Vector2.zero || Vector2.Dot(rf, away) < 0.5f || float.IsNaN(hr) || hr > endRule.tallMin + 1e-3f)
                {
                    endRule.record.Add(tag + ": tallEnd ⛔ 見付 " + h0.ToString("F2") + " > " + endRule.tallMin.ToString("F1") + " ── 返し " + Lr.ToString("F2") + "m は"
                        + (rf == Vector2.zero || Vector2.Dot(rf, away) < 0.5f ? "見え面が端の先を向かない(低い側が背 ── 出隅にならない)" : "")
                        + (float.IsNaN(hr) || hr > endRule.tallMin + 1e-3f ? "終わりの見付 " + hr.ToString("F2") + " が見切り石で受からない" : "") + " ── 返さない(普請方へ)");
                    continue;
                }
                segs.Add(ret);
                endRule.record.Add(tag + ": tallEnd 見付 " + h0.ToString("F2") + " > " + endRule.tallMin.ToString("F1") + " ⇒ 背の側へ返し " + Lr.ToString("F2") + "m(天端 " + c0.ToString("F2") + "・" + (stop != null ? "塞ぐ物 " + stop + " の手前" : "表と背の差 < " + endRule.tallReturnDiff.ToString("F1")) + ")");
            }
            n = segs.Count;
        }
        // ---- 端どうしの取り合い ----(②の隅の返しを足したら組み直す ── Links)
        int[,,] link = null, concave = null;
        void Links()
        {
        link = new int[n, 2, 2]; for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++) { link[k, e, 0] = -1; link[k, e, 1] = -1; }
        concave = new int[n, 2, 2]; for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++) { concave[k, e, 0] = -1; concave[k, e, 1] = -1; }
        for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++)
            for (int j = 0; j < n; j++) for (int f = 0; f < 2; f++)
            {
                if (j == k || Vector2.Distance(endPt(segs[k], e), endPt(segs[j], f)) > TOL) continue;
                Vector2 din = e == 1 ? segs[k].Dir : -segs[k].Dir, dout = f == 0 ? segs[j].Dir : -segs[j].Dir;
                float turn = Vector2.Angle(din, dout);
                Vector2 fk = faceNear(segs[k], e);
                bool ok = turn < 60f || (fk != Vector2.zero && Vector2.Dot(dout, fk) < -0.3f);
                // ⭐ 天端の違う区間は継がない(T 字・段違いの取り合い ── 低い天端の区間が高い区間の面へ突き付く)。
                //   一つの端に三本が集まる所(松江松平 中ノ口の庭の隅 u−13.5・u−4 ── 天端 26.7 の二本と 26.2 の一本・EDO-0554)で、
                //   後から見た相手が先の相手を上書きして「見立てが両側で割れた」になり、出隅が継がれず 1.04m の口が開いた。
                //   ⇒ 天端が揃う相手を先に採り、既に継いだ端は上書きしない。当たる先: 野面の網で三本以上が一点に集まる所すべて。
                //   ⚠ 二本だけが会う端(一直線の段違いの継ぎ目 ── 岡部 TW_Kado_Sode の 0.5 刻みの段)は従前どおり継ぐ(段の境の駒・積み下ろし)。
                //   ここまで割ると段違いが入隅の突き付けに化け、段の境の駒も積み下ろしも消えた(2026-10-04・EDO-0502 第16巡)。
                int meet = 0; for (int q = 0; q < n; q++) for (int g = 0; g < 2; g++) if (q != k && Vector2.Distance(endPt(segs[k], e), endPt(segs[q], g)) <= TOL) meet++;
                bool sameCrest = meet < 2 || segs[k].crestAt == null || segs[j].crestAt == null
                    || Mathf.Abs(segs[k].crestAt(e == 0 ? 0f : segs[k].Len) - segs[j].crestAt(f == 0 ? 0f : segs[j].Len)) < 0.10f;
                if (ok && sameCrest && link[k, e, 0] < 0) { link[k, e, 0] = j; link[k, e, 1] = f; }
                else if (!(ok && sameCrest) && concave[k, e, 0] < 0) { concave[k, e, 0] = j; concave[k, e, 1] = f; }
            }
        // 継ぐのは両側から見て一直線か出隅のときだけ(片側の見え面の測りが揺れても鎖が入隅を跨がない)
        for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++)
        {
            int j = link[k, e, 0]; if (j < 0) continue; int f = link[k, e, 1];
            if (link[j, f, 0] == k) continue;
            log.AppendLine("    ⚠ " + segs[k].name + " × " + segs[j].name + ": 継ぎの見立てが両側で割れた ── 入隅として継がない");
            link[k, e, 0] = -1; concave[k, e, 0] = j; concave[k, e, 1] = f;
            if (concave[j, f, 0] < 0) { concave[j, f, 0] = k; concave[j, f, 1] = e; }
        }
        }
        Links();
        // ---- 端の納め(endRule・指図 nozuraEndRule)── 相手の居ない端を ① 延ばして打ち切り / ② 見切り石 へ(鎖を組む前に区間を延ばす) ----
        var endPlan = new string[n, 2]; var koshiOk = new bool[n, 2];
        // 積み止め(endRule.tome・指図 nozuraEndRule 追記b・EDO-0502 第43巡)【硬】: ③ の端は直線の駒の小口で終えず、走りを駒の走り(0.909)だけ縮めて
        //   直線の駒を並べ、その先に積み止めの駒(小口にも面石・両角が稜)を据える。段は端の駒の走りの見付 + 根入れ以上の最も低い焼いた段(名指しがあればその段)。
        //   当たる先: endRule.tome を渡す邸(岡部 Stage2b)の野面の ③ の端すべて。
        var tomeAt = new Dictionary<NozuraSeg, TomeEnd[]>();
        Func<NozuraSeg, int, TomeEnd> tomeOf = (sg, e) => { TomeEnd[] t; return tomeAt.TryGetValue(sg, out t) ? t[e] : null; };
        Func<NozuraSeg, int, Vector2, EndSpec, string> planTome = (sg, e, fN, sp) =>
        {
            if (endRule == null || endRule.tome == null) return "";
            float T = endRule.tomeRun; Vector2 ep = endPt(sg, e), away = e == 1 ? sg.Dir : -sg.Dir;
            if (sg.Len < T + 0.2f) return "・積み止め ⛔ 区間 " + sg.Len.ToString("F2") + "m が駒の走り " + T.ToString("F3") + " + 0.2 に足りない(③ のまま)";
            float hT = float.MinValue;   // 積み止めの駒が受け持つ走り(端から内へ T)の見付の最大(足元は線の前 0.25/0.7 ── PlaceNozuraRun の needH と同じ測り)
            for (float s2 = 0f; s2 <= T + 1e-3f; s2 += 0.15f)
            {
                Vector2 q2 = ep - away * s2; float cq = sg.crestAt(e == 0 ? s2 : sg.Len - s2);
                foreach (float off in new[] { 0.25f, 0.7f })
                { float fy = FootAhead(sg.footAt, groundAt, q2, fN, off, cq, batN); if (!float.IsNaN(fy)) hT = Mathf.Max(hT, cq - fy); }
            }
            if (hT == float.MinValue) return "・積み止め ⛔ 端の見付が測れない(③ のまま)";
            float need = hT + endRule.tomeNeiri;
            float H = sp != null && !float.IsNaN(sp.tomeH) ? sp.tomeH : (endRule.tomeH != null ? endRule.tomeH(need) : float.NaN);
            if (float.IsNaN(H)) return "・積み止め ⛔ 見付 " + hT.ToString("F2") + " + 根入れ " + endRule.tomeNeiri.ToString("F2") + " = " + need.ToString("F2") + " を受ける段が焼けていない(③ のまま)";
            string p0 = endRule.tome(H, true, 0);
            if (string.IsNullOrEmpty(p0) || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p0) == null) return "・積み止め ⛔ 駒が読めない " + p0 + "(③ のまま)";
            // 行く手の塀からの離れ(EndSpec.tomeClear【硬】・EDO-0502 第45巡)── 端を走りに沿って内へ引く量を PlaceBest で選ぶ(試しに据えて実メッシュで測り、消す)
            float pull = 0f; string pullNote = "";
            if (sp != null && !float.IsNaN(sp.tomeClear))
            {
                float aim = float.IsNaN(sp.tomePullAim) ? 0f : sp.tomePullAim;
                var pulls = new List<float>(); for (int pi = 0; pi * 0.1f <= sp.tomePullMax + 1e-4f; pi++) { float pv = pi * 0.1f; if (sg.Len - pv >= T + 0.2f) pulls.Add(pv); }
                pulls.Sort((x, y) => Mathf.Abs(x - aim).CompareTo(Mathf.Abs(y - aim)));
                var pOf = new Dictionary<GameObject, float>(); string lastWhy = null; float lastSh = float.NaN, sh0 = float.NaN; string why0 = null;
                Func<float, GameObject> placeP = pv =>
                {
                    Vector2 e2 = ep - away * pv; float cj = sg.crestAt(e == 0 ? pv + T : sg.Len - pv - T); string r0;
                    var gp = PlaceNozuraTome(endRule.tome, H, e2, away, fN, cj, new List<GameObject>(), T, groundAt, null, "__tome_probe__", 0, out r0);
                    if (gp != null) pOf[gp] = pv; return gp;
                };
                { var g0 = placeP(0f); if (g0 != null) { sh0 = TomeClearShort(g0, away, sp.tomeWalls, sp.tomeParcel, sp.tomeClear, out why0); UnityEngine.Object.DestroyImmediate(g0); } }
                var hards = new List<Hard> { new Hard("積み止めの塀の内面からの離れ", g => { lastSh = TomeClearShort(g, away, sp.tomeWalls, sp.tomeParcel, sp.tomeClear, out lastWhy); return lastSh <= 1e-3f; }) };
                var softs = new List<Soft> { new Soft("引きの狙い", -0.05f, g => { float pv; return pOf.TryGetValue(g, out pv) ? -Mathf.Abs(pv - aim) : -99f; }) };
                var best = PlaceBest<float>(pulls, pulls.Count, placeP, hards, softs, new SeiyakuTally());
                if (best == null) return "・積み止め ⛔ 塀の内面から " + sp.tomeClear.ToString("F2") + " を取れる引きが 0〜" + sp.tomePullMax.ToString("F1") + " に無い(引き 0 で不足 " + sh0.ToString("F3") + "・" + why0 + ")(③ のまま)";
                pull = pOf[best]; float shB = TomeClearShort(best, away, sp.tomeWalls, sp.tomeParcel, sp.tomeClear, out lastWhy); UnityEngine.Object.DestroyImmediate(best);
                pullNote = "・端を走りに沿って内へ " + pull.ToString("F1") + " 引く(狙い " + aim.ToString("F1") + "【柔】" + (Mathf.Abs(pull - aim) > 0.05f ? " ⚠ 狙い未達" : "") + "・引き 0 では不足 " + sh0.ToString("F3") + "〔" + why0 + "〕→ 不足 " + shB.ToString("F3") + "〔" + lastWhy + "〕)";
                ep = ep - away * pull;
            }
            float cJ = sg.crestAt(e == 0 ? T + pull : sg.Len - T - pull);   // 継ぎ手(縮めた端)の天端 ── 隣の直線の駒と同じ天端の線
            if (e == 1) sg.b = ep - away * T;
            else
            {
                var oc = sg.crestAt; float sh = T + pull; sg.crestAt = sl => oc(sl + sh);
                if (sg.sidesAt != null) { var os = sg.sidesAt; sg.sidesAt = sl => os(sl + sh); }
                sg.a = ep - away * T;
            }
            TomeEnd[] arr; if (!tomeAt.TryGetValue(sg, out arr)) tomeAt[sg] = arr = new TomeEnd[2];
            arr[e] = new TomeEnd { H = H, crest = cJ, hT = hT, ep = ep, fN = fN, away = away, label = sp != null ? sp.label : null };
            return "・積み止め H" + H.ToString("F2") + "(端の見付 " + hT.ToString("F2") + " + 根入れ ≥ " + endRule.tomeNeiri.ToString("F2") + (sp != null && !float.IsNaN(sp.tomeH) ? "・段は名指し" : "") + ")── 走りを " + T.ToString("F3") + " 縮めて直線の駒を並べ、その先へ据える" + pullNote;
        };
        var kadoRet = new List<NozuraSeg>();   // ② 隅の駒の返し(endRule.kadoReturn)── 鎖を組む前に足して Links を組み直す
        if (endRule != null)
        {
            float kiriH = heights[0];
            for (int k = 0; k < n; k++) for (int e = 0; e < 2; e++)
            {
                if (link[k, e, 0] >= 0 || concave[k, e, 0] >= 0 || segs[k].mikiriTo[e] != null || segs[k].noAbut[e] || segs[k].abutTo[e] != null) continue;
                Vector2 ep = endPt(segs[k], e);
                // 別の区間の走りの中に在る端(重ねて埋める run の下に入る上手の run の端 ── RunsByCrestGap)は納めない(第32巡: 返しの中ほどに見切り石が立った)
                {
                    bool inside = false;
                    for (int j = 0; j < n && !inside; j++)
                    {
                        if (j == k) continue; var sj = segs[j]; float u = Vector2.Dot(ep - sj.a, sj.Dir);
                        if (u > 0.1f && u < sj.Len - 0.1f && Mathf.Abs(Vector2.Dot(ep - sj.a, new Vector2(-sj.Dir.y, sj.Dir.x))) < 0.1f) inside = true;
                    }
                    if (inside) { endRule.record.Add(segs[k].name + " 端" + e + ": 重ねた run の走りの中 ── 納めない(上の run の駒の裏)"); continue; }
                }
                // ⓪ 名指しの端(EndSpec.abutAhead・指図 endKado「延ばす向き 1.5m の内に境の石垣か練塀の実面があれば入隅で突き付けて終える」)── 実メッシュで測る
                string abutNote = null;
                {
                    var spE = endRule.spec != null ? endRule.spec(segs[k], e) : null;
                    if (spE != null && !float.IsNaN(spE.abutAhead) && spE.abutPool != null)
                    {
                        Vector2 awA = e == 1 ? segs[k].Dir : -segs[k].Dir, lt = new Vector2(-awA.y, awA.x); GameObject hg = null; float ht = float.MaxValue;
                        float cos30 = Mathf.Cos(30f * Mathf.Deg2Rad);
                        foreach (var g in spE.abutPool) if (g != null && g.activeInHierarchy)
                            foreach (var v in (Mathf.Abs(Vector2.Dot(RunAxis(g), awA)) >= cos30 ? new List<Vector3>() : Body(g.transform, 3000)))   // 延ばす線に沿って平行に走る塀・石垣は数えない(指図 nozuraEndRule 追記3) { Vector2 rr = new Vector2(v.x, v.z) - ep; float u = Vector2.Dot(rr, awA); if (u > 0f && u <= spE.abutAhead && Mathf.Abs(Vector2.Dot(rr, lt)) < 0.6f && u < ht) { ht = u; hg = g; } }
                        if (hg != null) { pool.Add(hg); endRule.record.Add(segs[k].name + " 端" + e + ": ⓪入隅で突き付け(延ばす向き " + ht.ToString("F2") + "m に " + hg.name + " の実面)〔" + spE.label + "〕"); continue; }
                        abutNote = "延ばす向き " + spE.abutAhead.ToString("F1") + "m の内に相手の実面なし(実測)";
                    }
                }
                bool near = false;
                foreach (var g in pool) if (g != null && !near)
                    foreach (var v in Body(g.transform, 400)) if (Vector2.Distance(new Vector2(v.x, v.z), ep) < 1.5f) { near = true; break; }
                if (near) continue;                                       // 相手の面へ(従前どおり)
                Vector2 fN = faceNear(segs[k], e); if (fN == Vector2.zero) continue;
                Vector2 away = e == 1 ? segs[k].Dir : -segs[k].Dir;
                float c0 = segs[k].crestAt(e == 0 ? 0f : segs[k].Len);
                Func<Vector2, float> footOf = q => { float fy = segs[k].footAt != null ? segs[k].footAt(q.x + fN.x * 0.5f, q.y + fN.y * 0.5f) : float.NaN;
                                                     return float.IsNaN(fy) ? groundAt(q.x + fN.x * 0.5f, q.y + fN.y * 0.5f) : fy; };
                // 端の見付は端の駒が受け持つ走り(端から内へ 1.2W)で PlaceNozuraRun の needH と同じに測る ── 端の一点だと坂の端で −0.18 と読み、
                //   打ち切りへ回した端が駒の奥で 1.20 の見付を残して直線の駒へ逃げた(第30巡)
                float h0 = endExpose(segs[k], e, fN);
                // 背の地盤 − 天端(天端の列の控えの奥)と、端の先の見え面の線の上の地盤 − 天端(一間まで・最大)を刷る(第31巡)
                float backD = groundAt(ep.x - fN.x * probe, ep.y - fN.y * probe) - c0, aheadD = float.MinValue;
                for (float sa = 0.25f; sa <= W + 1e-3f; sa += 0.25f) { float ga = groundAt(ep.x + away.x * sa, ep.y + away.y * sa); if (!float.IsNaN(ga)) aheadD = Mathf.Max(aheadD, ga - c0); }
                string meas = "[背−天端 " + backD.ToString("+0.00;-0.00") + "・先−天端 " + (aheadD == float.MinValue ? "-" : aheadD.ToString("+0.00;-0.00")) + "]";
                // 名指しの積み止め(指図 returnEnd・endKado「積み止めで終える」)── ②〜④ を当てない
                {
                    var spT = endRule.spec != null ? endRule.spec(segs[k], e) : null;
                    if (spT != null && spT.tome)
                    {
                        endPlan[k, e] = "③名指しの積み止め〔" + spT.label + "〕" + planTome(segs[k], e, fN, spT);
                        if (tomeOf(segs[k], e) == null) endRule.unresolved++;
                        endRule.record.Add(segs[k].name + " 端" + e + ": " + endPlan[k, e] + " " + meas);
                        continue;
                    }
                }
                // ④ 差し込み(指図 nozuraEndRule 追記2・①②より先・①を止めた邸でも当てる)【硬】: 端の先の見え面の線上の地盤が天端より高い端は、
                //   天端 c0 のまま線を延ばし、線上の地盤が c0 + insertReach に届く所から insertTail 先で終える(端の小口は地中)。上限 insertMax。
                //   延ばす先が塞がる(区画線・長屋の背から一間・据わった駒)か上限内で届かなければ ③。届いた所から先の区間の天端の土は根入れ(埋没に数えない)
                if (endRule.insertMax > 0f && aheadD > 0f)
                {
                    float reach = float.NaN; string stopI = null;
                    for (float sx = 0.25f; sx <= endRule.insertMax + 1e-3f; sx += 0.25f)
                    {
                        Vector2 q = ep + away * sx;
                        { stopI = endRule.Block(q, away); if (stopI != null) { stopI += " " + sx.ToString("F2") + "m 先"; break; } }
                        float gq = groundAt(q.x, q.y);
                        if (!float.IsNaN(gq) && gq >= c0 + endRule.insertReach - 1e-4f) { reach = sx; break; }
                    }
                    float E4 = float.IsNaN(reach) ? float.NaN : reach + endRule.insertTail;
                    if (!float.IsNaN(E4) && E4 <= endRule.insertMax + 1e-3f)
                    {   // 届いた所から先(半駒)の区間も塞がっていないこと
                        for (float sx = reach; sx <= E4 + 1e-3f && stopI == null; sx += 0.25f) stopI = endRule.Block(ep + away * sx, away);
                        if (stopI != null) E4 = float.NaN;
                    }
                    if (!float.IsNaN(E4) && E4 <= endRule.insertMax + 1e-3f)
                    {
                        var sg = segs[k]; var old0 = sg.crestAt; float L0 = sg.Len, cc = c0, EE = E4;
                        if (e == 1) { sg.b = ep + away * EE; sg.crestAt = sl => sl <= L0 ? old0(sl) : cc; }
                        else { sg.a = ep + away * EE; sg.crestAt = sl => sl >= EE ? old0(sl - EE) : cc; }
                        endPlan[k, e] = "④差し込み(天端 " + c0.ToString("F2") + " のまま " + EE.ToString("F2") + "m ── 地盤が天端+" + endRule.insertReach.ToString("F1") + " に届く所 " + reach.ToString("F2") + "m から半駒先)";
                        if (endRule.insertDone != null) endRule.insertDone.Add(new Vector4(ep.x, ep.y, away.x * EE, away.y * EE));
                    }
                    else
                    {
                        endPlan[k, e] = "③⛔ ④差し込みが取れない(" + (stopI != null ? "延ばす先が塞がる: " + stopI : "地盤が天端+" + endRule.insertReach.ToString("F1") + " に " + endRule.insertMax.ToString("F1") + "m 以内で届かない") + ")── 直線の駒で終える";
                        endPlan[k, e] += planTome(segs[k], e, fN, null);
                        if (tomeOf(segs[k], e) == null) endRule.unresolved++;
                    }
                    endRule.record.Add(segs[k].name + " 端" + e + ": " + endPlan[k, e] + " " + meas);
                    continue;
                }
                if (float.IsNaN(h0) || h0 <= kiriH + 1e-3f) { endRule.record.Add(segs[k].name + " 端" + e + ": 打ち切り(見付 " + h0.ToString("F2") + ") " + meas); continue; }
                // ① 延ばす: 天端 = max(背の地盤, 端の天端 − 勾配 × 道のり)。見付 ≤ 打ち切りの駒の見付になったら、そこから半駒先で終える
                string why = endRule.maxExtend <= 0f ? "①を止めた邸(maxExtend 0)" : null; float E = float.NaN; var tab = new List<Vector2>();
                for (float sx = 0.25f; sx <= endRule.maxExtend + 1e-3f; sx += 0.25f)
                {
                    Vector2 q = ep + away * sx;
                    { why = endRule.Block(q, away); if (why != null) break; }
                    float back = groundAt(q.x - fN.x * probe, q.y - fN.y * probe);
                    // 硬い(許容0 の埋没): 延ばす先の背の地盤が端の天端より高い ⇒ 延ばした駒の天端が土に埋まる(延ばす先は土の斜面)── 延ばせない
                    if (!float.IsNaN(back) && back > c0 + 0.05f) { why = "延ばす先の背の地盤 " + back.ToString("F2") + " が天端 " + c0.ToString("F2") + " より高い"; break; }
                    float cr = Mathf.Max(c0 - endRule.maxGrade * sx, float.IsNaN(back) ? float.MinValue : back);
                    cr = Mathf.Min(cr, c0);
                    tab.Add(new Vector2(sx, cr));
                    // 端の駒(打ち切り)が受け持つ走り [sx − 1.2W, sx] の全体で見付 ≤ 打ち切りの駒の見付(PlaceNozuraRun の needH と同じ測り:
                    //   天端は走りの中ほど・足元は線の前 0.25 と 0.7 の地表の最小)── 端の一点で測ると駒の走りの奥で見付が残り直線の駒へ逃げた(第30巡)
                    if (sx < 1.2f * W) continue;
                    float midS = sx - 0.6f * W, crMid = c0;
                    foreach (var tq in tab) if (tq.x <= midS + 1e-3f) crMid = tq.y;
                    float gmin = float.MaxValue;
                    for (float s2 = sx - 1.2f * W; s2 <= sx + 1e-3f; s2 += 0.25f)
                    { Vector2 q2 = ep + away * s2; foreach (float off in new[] { 0.25f, 0.7f })
                      { float x2 = q2.x + fN.x * off, z2 = q2.y + fN.y * off; float fy = segs[k].footAt != null ? segs[k].footAt(x2, z2) : float.NaN;
                        if (float.IsNaN(fy)) fy = groundAt(x2, z2); if (!float.IsNaN(fy)) gmin = Mathf.Min(gmin, fy); } }
                    if (crMid - gmin <= kiriH + 1e-3f) { E = sx; break; }
                }
                if (!float.IsNaN(E))
                {
                    var sg = segs[k]; var old0 = sg.crestAt; float L0 = sg.Len; var tb = tab;
                    Func<float, float> ext = d => { if (d <= 0f) return c0; for (int i = 1; i < tb.Count; i++) if (d <= tb[i].x) return Mathf.Lerp(tb[i - 1].y, tb[i].y, (d - tb[i - 1].x) / Mathf.Max(1e-4f, tb[i].x - tb[i - 1].x));
                                                return tb[tb.Count - 1].y; };
                    if (tb.Count > 0 && tb[0].x > 0f) tb.Insert(0, new Vector2(0f, c0));
                    if (e == 1) { sg.b = ep + away * E; sg.crestAt = sl => sl <= L0 ? old0(sl) : ext(sl - L0); }
                    else { sg.a = ep + away * E; sg.crestAt = sl => sl >= E ? old0(sl - E) : ext(E - sl); }
                    endPlan[k, e] = "①延ばして打ち切り(" + E.ToString("F2") + "m・見付 " + h0.ToString("F2") + " → 天端 " + c0.ToString("F2") + "→" + tb[tb.Count - 1].y.ToString("F2") + ")";
                }
                else if (endRule.kadoReturn)
                    endPlan[k, e] = KadoReturnEnd(endRule, segs[k], e, ep, away, fN, c0, h0, why, groundAt, probe, W, kadoRet, heights) + (abutNote != null ? "・" + abutNote : "");
                else
                {
                    string mp = endRule.mikiri == null ? null : endRule.mikiri(h0);
                    bool baked = !string.IsNullOrEmpty(mp) && System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, mp));
                    if (baked)
                    {
                        segs[k].mikiriTo[e] = new List<GameObject>(); endPlan[k, e] = "②見切り石(" + (why ?? "延ばしても見付が下がらない") + "・見付 " + h0.ToString("F2") + ")";
                        // koshiEnd(指図 nozuraEndRule 追記・第31巡): 背が法の腰の端は、見切り石が背の土に埋まって退けられたときだけ背を小段に切って据え直す(下の据えの所)。
                        //   硬い: 端の先の見え面の線の上の地盤が天端より高い端は切らない(普請方へ)
                        if (endRule.koshi != null && endRule.koshi(segs[k].name))
                        {
                            if (aheadD > 0f) endPlan[k, e] += " ・koshiEnd ⛔ 端の先の地盤が天端より " + aheadD.ToString("F2") + "m 高い ── 小段を切らない(普請方へ)";
                            else koshiOk[k, e] = true;
                        }
                    }
                    else endPlan[k, e] = "③⛔ 延ばせず(" + (why ?? "延ばしても見付が下がらない") + ")・見付 " + h0.ToString("F2") + " の見切り石が焼いていない";
                }
                // 積み止め(endRule.tome): ③ の端は積み止めの駒で終える(指図 nozuraEndRule 追記b)
                if (endRule.tome != null && endPlan[k, e] != null && endPlan[k, e].StartsWith("③") && tomeOf(segs[k], e) == null)
                    endPlan[k, e] += planTome(segs[k], e, fN, endRule.spec != null ? endRule.spec(segs[k], e) : null);
                endRule.record.Add(segs[k].name + " 端" + e + ": " + endPlan[k, e] + " " + meas);
            }
        }
        if (kadoRet.Count > 0)
        {
            segs.AddRange(kadoRet); int n0 = n; n = segs.Count;
            var ep2 = new string[n, 2]; var ko2 = new bool[n, 2];
            for (int k = 0; k < n0; k++) for (int e = 0; e < 2; e++) { ep2[k, e] = endPlan[k, e]; ko2[k, e] = koshiOk[k, e]; }
            endPlan = ep2; koshiOk = ko2;
            Links();
        }
        // 入隅の可動側
        Func<int, int, bool> moves = (k, e) =>
        {
            int j = concave[k, e, 0]; if (j < 0) return false;
            if (segs[k].movesAtConcave != segs[j].movesAtConcave) return segs[k].movesAtConcave;
            bool kBoth = concave[k, 0, 0] >= 0 && concave[k, 1, 0] >= 0, jBoth = concave[j, 0, 0] >= 0 && concave[j, 1, 0] >= 0;
            if (kBoth != jBoth) return kBoth;
            return k > j;                                   // 決まらない ⇒ 後の区間(⚠ で刷る)
        };
        // ---- 鎖 ----
        var chainOf = new int[n]; for (int k = 0; k < n; k++) chainOf[k] = -1;
        var chains = new List<List<KeyValuePair<int, bool>>>();   // (区間, 裏返すか)
        for (int pass = 0; pass < 2; pass++)
            for (int k0 = 0; k0 < n; k0++)
            {
                if (chainOf[k0] >= 0) continue;
                // 一巡目は継がれていない端から始める(継ぎの無い端の区間を頭に)
                int startE = link[k0, 0, 0] < 0 ? 0 : (link[k0, 1, 0] < 0 ? 1 : -1);
                if (startE < 0 && pass == 0) continue; if (startE < 0) startE = 0;
                var ch = new List<KeyValuePair<int, bool>>(); int k = k0; int eIn = startE;
                while (k >= 0 && chainOf[k] < 0)
                {
                    chainOf[k] = chains.Count; ch.Add(new KeyValuePair<int, bool>(k, eIn == 1));
                    int eOut = 1 - eIn; int j = link[k, eOut, 0]; if (j < 0) break;
                    eIn = link[k, eOut, 1]; k = j;
                }
                chains.Add(ch);
            }
        // ---- 順: 可動の端の相手の鎖を先に ----
        var order = new List<int>(); var done = new bool[chains.Count];
        for (int guard = 0; guard < chains.Count + 2 && order.Count < chains.Count; guard++)
            for (int c = 0; c < chains.Count; c++)
            {
                if (done[c]) continue; bool ready = true;
                foreach (var kv in chains[c]) for (int e = 0; e < 2; e++)
                    if (moves(kv.Key, e)) { int pc = chainOf[concave[kv.Key, e, 0]]; if (pc != c && !done[pc]) ready = false; }
                if (!ready && guard < chains.Count) continue;
                done[c] = true; order.Add(c);
            }
        var chainPieces = new Dictionary<int, List<GameObject>>();
        var segPieces = new Dictionary<int, List<GameObject>>(); for (int k = 0; k < n; k++) segPieces[k] = new List<GameObject>();
        int seq = 0;
        foreach (int c in order)
        {
            var ch = chains[c];
            var w = new NozuraWall { kadoAbut = kadoAbut };
            var cum = new List<float>(); float acc = 0f;
            foreach (var kv in ch)
            {
                var sg = segs[kv.Key]; Vector2 p0 = kv.Value ? sg.b : sg.a, p1 = kv.Value ? sg.a : sg.b;
                if (w.nodes.Count == 0) w.nodes.Add(p0);
                w.nodes.Add(p1); cum.Add(acc); acc += sg.Len;
            }
            var chL = ch; var cumL = cum;
            w.crestAt = s =>
            {
                int i = 0; for (int q = 0; q < cumL.Count; q++) if (s >= cumL[q] - 1e-4f) i = q;
                var sg = segs[chL[i].Key]; float ls = Mathf.Clamp(s - cumL[i], 0f, sg.Len);
                return sg.crestAt(chL[i].Value ? sg.Len - ls : ls);
            };
            w.faceAt = s =>
            {
                int i = 0; for (int q = 0; q < cumL.Count; q++) if (s >= cumL[q] - 1e-4f) i = q;
                return segs[chL[i].Key].face;
            };
            w.sidesAt = s =>
            {
                int i = 0; for (int q = 0; q < cumL.Count; q++) if (s >= cumL[q] - 1e-4f) i = q;
                var sg = segs[chL[i].Key]; if (sg.sidesAt == null) return new Vector2(float.NaN, float.NaN);
                float ls = Mathf.Clamp(s - cumL[i], 0f, sg.Len);
                return sg.sidesAt(chL[i].Value ? sg.Len - ls : ls);
            };
            // 見付の下限(kadoReturnUniform)── 区間全体(隅の駒の腕 ±半駒を含む)と端の際の一間
            for (int i = 0; i < ch.Count; i++)
            {
                var sg = segs[ch[i].Key]; float c0 = cum[i], c1 = cum[i] + sg.Len;
                if (!float.IsNaN(sg.minH)) w.minHRanges.Add(new Vector3(c0 - 0.909f, c1 + 0.909f, sg.minH));
                for (int e = 0; e < 2; e++)
                {
                    float pe = (e == 0) != ch[i].Value ? c0 : c1;   // 裏返した区間は端が入れ替わる
                    if (!float.IsNaN(sg.fixHEnd[e])) w.fixHRanges.Add(new Vector3(pe - W, pe + W, sg.fixHEnd[e]));
                    if (!float.IsNaN(sg.flatEnd[e])) w.flatRanges.Add(pe == c0 ? new Vector2(c0 - W, c0 + sg.flatEnd[e]) : new Vector2(c1 - sg.flatEnd[e], c1 + W));
                    if (float.IsNaN(sg.minHEnd[e])) continue;
                    w.minHRanges.Add(new Vector3(pe - W, pe + W, sg.minHEnd[e]));
                }
            }
            for (int i = 1; i < ch.Count; i++)
            {
                if (segs[ch[i - 1].Key].flow || segs[ch[i].Key].flow) continue;   // 流しの区間の両端は段でない(FlowStepJoints)
                float st = cum[i]; if (Mathf.Abs(w.crestAt(st - 0.5f) - w.crestAt(st + 0.5f)) > 0.05f) w.steps.Add(st);
            }
            // 鎖の足元: 区間ごとに足元を名指していれば**その点に最も近い区間の足元**で測る(⛔ 鎖の最初の足元で全区間を測らない ──
            //   EDO-0502 第106巡: 石段の脇の返し(足元 = 段石の踏面)と継いだ TW_Higashi_Se の本線が段石の踏面 13.4〜14.0 を足元と読み、
            //   見付が足りず駒の底が背の路地の床 12.4 の 1.0〜1.5 上で止まった)。名指しの無い区間は従前どおり最初の足元。
            //   当たる先: 足元の違う区間を一本に継ぐ野面の鎖すべて(岡部 石段の脇の返し × 本線・背の台の石垣 × 妻の面)。
            {
                Func<float, float, float> first = null; var fsegs = new List<NozuraSeg>(); var fns = new HashSet<Func<float, float, float>>();
                foreach (var kv in ch) { var sg = segs[kv.Key]; fsegs.Add(sg); if (sg.footAt != null) { if (first == null) first = sg.footAt; fns.Add(sg.footAt); } }
                if (fns.Count <= 1) w.footAt = first;
                else
                    w.footAt = (x, z) =>
                    {
                        var q = new Vector2(x, z); NozuraSeg best = null; float bd = float.MaxValue;
                        foreach (var sg in fsegs)
                        {
                            Vector2 ab = sg.b - sg.a; float L2 = ab.sqrMagnitude; float t = L2 < 1e-8f ? 0f : Mathf.Clamp01(Vector2.Dot(q - sg.a, ab) / L2);
                            float d = Vector2.Distance(q, sg.a + ab * t); if (d < bd) { bd = d; best = sg; }
                        }
                        var f = best != null && best.footAt != null ? best.footAt : first;
                        return f(x, z);
                    };
            }
            w.straight = straight; w.kado = kado; w.dan = dan; w.kiri = kiri; w.heights = heights; w.faceGroundAt = faceGroundAt; w.kiriEnd = kiriEnd; w.noriEnd = noriEnd;
            string nm = segs[ch[0].Key].name; var names = new List<string>(); foreach (var kv in ch) if (!names.Contains(segs[kv.Key].name)) names.Add(segs[kv.Key].name);
            // 端の納め
            var endDesc = new string[2]; var passEnds = new List<int[]>();   // (side, 区間, 端, 相手) ── 入隅の通す側で角から先へ通す端
            for (int side = 0; side < 2; side++)
            {
                var kv = side == 0 ? ch[0] : ch[ch.Count - 1];
                int k = kv.Key; int e = side == 0 ? (kv.Value ? 1 : 0) : (kv.Value ? 0 : 1);
                Vector2 ep = endPt(segs[k], e);
                var to = side == 0 ? w.startTo : w.endTo;
                if (tomeOf(segs[k], e) != null)
                {   // 積み止めの端: 縮めた線の端で直線の駒を止め(打ち切りの駒・近くの駒への突き付けを使わない)、その先へ積み止めの駒(下で据える)
                    if (side == 0) w.startThrough = true; else w.endThrough = true;
                    endDesc[side] = "積み止めの駒へ(走りを " + endRule.tomeRun.ToString("F3") + " 縮めた端)";
                }
                else if (concave[k, e, 0] >= 0)
                {
                    int j = concave[k, e, 0];
                    if (moves(k, e))
                    {
                        List<GameObject> pp; if (chainPieces.TryGetValue(chainOf[j], out pp)) to.AddRange(pp);
                        if (side == 0) w.startConcave = true; else w.endConcave = true;
                        endDesc[side] = "入隅の可動側 → " + segs[j].name + " の見え面へ(駒 " + to.Count + ")" +
                                        (segs[k].movesAtConcave == segs[j].movesAtConcave && (concave[k, 0, 0] >= 0) == (concave[k, 1, 0] >= 0) && (concave[j, 0, 0] >= 0) == (concave[j, 1, 0] >= 0) ? " ⚠ 可動側を指図から決められず後の区間にした" : "");
                    }
                    else
                    {
                        if (side == 0) w.startThrough = true; else w.endThrough = true; endDesc[side] = "入隅の通す側(" + segs[j].name + " が突き付く)";
                        if (!float.IsNaN(segs[k].passConcave)) { passEnds.Add(new int[] { side, k, e, j }); endDesc[side] += "・角から先へ通す"; }
                    }
                }
                else if (segs[k].abutTo[e] != null)
                {   // 名指した駒の実面へ突き付けて止める(見切り石・隅の駒・打ち切りを置かない ── NozuraSeg.abutTo)
                    foreach (var g in segs[k].abutTo[e]) if (g != null) to.Add(g);
                    endDesc[side] = "名指した駒の実面へ突き付けて止める(駒 " + to.Count + ")";
                }
                else if (segs[k].mikiriTo[e] != null)
                {
                    Vector2 away = e == 1 ? segs[k].Dir : -segs[k].Dir;       // 端から口へ
                    Vector2 fN = faceNear(segs[k], e); if (fN == Vector2.zero) fN = new Vector2(away.y, -away.x);
                    float fy = segs[k].footAt != null ? segs[k].footAt(ep.x + fN.x * 0.5f, ep.y + fN.y * 0.5f) : float.NaN;
                    if (float.IsNaN(fy)) fy = groundAt(ep.x + fN.x * 0.5f, ep.y + fN.y * 0.5f);
                    float cy = segs[k].crestAt(e == 0 ? 0f : segs[k].Len);
                    var mk = PlaceNozuraMikiri(mikiriPath, ep, away, fN, fy, cy, segs[k].mikiriTo[e], parent, segs[k].name + "_mikiri" + e, log, faceGroundAt);
                    if (mk == null && endRule != null && koshiOk[k, e] && segs[k].mikiriTo[e].Count == 0)
                    {   // koshiEnd: 背を小段に切って(切るだけ・切り ≤ koshiCutMax・練塀の犬走りを割らない)見切り石を据え直す
                        float cmx = endRule.koshiCutMaxOf != null ? endRule.koshiCutMaxOf(segs[k].name) : float.NaN; if (float.IsNaN(cmx)) cmx = endRule.koshiCutMax;
                        string kn; bool cut = CutKoshiBench(ep, away, fN, cy - endRule.koshiDrop, W, endRule.koshiBench, endRule.koshiBatter, cmx,
                                                            endRule.parcel, endRule.koshiKeep, endRule.koshiKeepGap, out kn,
                                                            ctrlBack + endRule.koshiBenchBack, endRule.koshiIsCut, endRule.koshiBatterCut, endRule.koshiDrain);
                        endRule.record.Add(segs[k].name + " 端" + e + ": koshiEnd " + (cut ? "小段を切った " : "⛔ ") + kn);
                        if (cut) mk = PlaceNozuraMikiri(mikiriPath, ep, away, fN, fy, cy, segs[k].mikiriTo[e], parent, segs[k].name + "_mikiri" + e, log, faceGroundAt);
                    }
                    if (mk == null && endRule != null && endRule.toe != null && endRule.toe(segs[k].name) && segs[k].mikiriTo[e].Count == 0)
                    {   // toeEnd(指図 nozuraEndRule 追記3): 背が盛りの法尻の端は toeBench で背を描き直して(切るだけ・盛りを減らす量は切りに数えない)見切り石を据え直す。
                        //   小段の走りは区間の全長 + 見切り石の外形の最大の寸(端の先へ)── 見切り石の背まで小段に入れる
                        float ext = 0f; string mpath = mikiriPath == null ? null : mikiriPath(Mathf.Max(0.3f, cy - fy)); var mo = string.IsNullOrEmpty(mpath) ? null : UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(mpath);
                        if (mo != null) foreach (var mf in mo.GetComponentsInChildren<MeshFilter>()) if (mf.sharedMesh != null) { var bs = Vector3.Scale(mf.sharedMesh.bounds.size, mf.transform.lossyScale); ext = Mathf.Max(ext, Mathf.Max(Mathf.Abs(bs.x), Mathf.Abs(bs.z))); }
                        var tb = ToeBenchOnSeg(segs[k], -fN, Mathf.Max(ctrlBack, ext) + endRule.toeBehind,   // 控えの後端 = 走りの駒と見切り石の深い方(見切り石は外形の最大の寸で)
                                               endRule.toeDrop, endRule.toeBatter, endRule.parcel, e == 0 ? ext : 0f, e == 1 ? ext : 0f);
                        float tcm; Vector2 tca; int tn = ToeBenchWrite(new List<ToeBench> { tb }, endRule.toeKeep, out tcm, out tca);
                        endRule.record.Add(segs[k].name + " 端" + e + ": toeEnd 背を描き直した 節点 " + tn + "・盛りを減らした最大 " + tcm.ToString("F2") + "m @(" + tca.x.ToString("F1") + ", " + tca.y.ToString("F1") + ")・小段の奥行 " + tb.w.ToString("F2") + "・端の先へ " + ext.ToString("F2"));
                        // 背の土は描き直した小段で測る(⭐ 2m 格子の地形は奥行 1.35 の小段を描けない ── 描くのは皮。皮の設計の地盤も同じ ToeBenchAt を読む)
                        Func<float, float, float> soilT = faceGroundAt == null ? null : (Func<float, float, float>)((x, z) => ToeBenchAt(tb, new Vector2(x, z), faceGroundAt(x, z)));
                        mk = PlaceNozuraMikiri(mikiriPath, ep, away, fN, fy, cy, segs[k].mikiriTo[e], parent, segs[k].name + "_mikiri" + e, log, soilT);
                    }
                    if (mk != null) { to.Add(mk); res.Add(new KeyValuePair<GameObject, Vector2>(mk, fN)); segPieces[k].Add(mk); pool.Add(mk); endDesc[side] = "口の縁 → 見切り石"; }
                    else
                    {   // 見切り石を退けた ⇒ 口の相手(城の石垣・袖)の実面へ直に突き付ける
                        to.AddRange(segs[k].mikiriTo[e]);
                        endDesc[side] = "口の縁 → ⛔ 見切り石を退けた ⇒ 相手の実面へ直に(駒 " + to.Count + ")";
                        if (segs[k].mikiriTo[e].Count == 0 && endRule != null) { endRule.unresolved++; endRule.record.Add(segs[k].name + " 端" + e + ": ③⛔ 見切り石を退けた(背の土が頭より高い)── 直線の駒で終える"); }
                    }
                }
                else if (segs[k].noAbut[e]) endDesc[side] = "打ち切り(重ねて埋める run の端 ── 突き付けない)";
                else
                {
                    foreach (var g in pool) if (g != null)
                        foreach (var v in Body(g.transform, 400)) if (Vector2.Distance(new Vector2(v.x, v.z), ep) < 1.5f) { to.Add(g); break; }
                    endDesc[side] = to.Count > 0 ? "近くの駒の実面へ(駒 " + to.Count + ")" : "打ち切り";
                }
            }
            log.AppendLine("  " + string.Join("+", names.ToArray()) + ": 野面の乱積み(始まり " + endDesc[0] + " / 終わり " + endDesc[1] + ")");
            var got = PlaceNozuraRun(w, groundAt, probe, parent, nm, log);
            var mine = new List<GameObject>();
            foreach (var kv in got)
            {
                var bc = RB(kv.Key).center; var c2 = new Vector2(bc.x, bc.z); int bi = ch[0].Key; float bd = float.MaxValue;
                foreach (var q in ch)
                {
                    var sg = segs[q.Key]; Vector2 ab = sg.b - sg.a; float u = Mathf.Clamp01(Vector2.Dot(c2 - sg.a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-9f));
                    float dd = Vector2.Distance(sg.a + ab * u, c2); if (dd < bd) { bd = dd; bi = q.Key; }
                }
                string tail = kv.Key.name.Substring(nm.Length);
                kv.Key.name = (tail.Contains("kado") || tail.Contains("dan")) ? segs[bi].name + tail : segs[bi].name + "_" + (seq++).ToString("000") + "f";
                segPieces[bi].Add(kv.Key); mine.Add(kv.Key); res.Add(kv);
                pool.Add(kv.Key);
            }
            chainPieces[c] = mine;
            // 積み止めの駒を据える(縮めた端の直線の駒の継ぎ目へ突き付ける)
            for (int side = 0; side < 2; side++)
            {
                var kv = side == 0 ? ch[0] : ch[ch.Count - 1]; int k = kv.Key; int e = side == 0 ? (kv.Value ? 1 : 0) : (kv.Value ? 0 : 1);
                var te = tomeOf(segs[k], e); if (te == null) continue;
                // 相手 = この鎖の駒だけ(端の点から 5m 以内)── 重ねて埋める上手の run(返しの #ret*_0)の駒は数えない: 天端の高い駒の裏へ入る所は
                //   埋めて隠す(部材どうしのめり込みは数えない)。数えると上の run の背の石に押されて端が 0.2〜0.3 先へ出た(第43巡・指図「今の位置のまま」)
                var mates = new List<GameObject>();
                foreach (var g in mine) if (g != null && !mates.Contains(g)) mates.Add(g);
                mates.RemoveAll(g => { var bb = RB(g); return bb.SqrDistance(new Vector3(te.ep.x, bb.center.y, te.ep.y)) > 25f; });
                string trec;
                var tg = PlaceNozuraTome(endRule.tome, te.H, te.ep, te.away, te.fN, te.crest, mates, endRule.tomeRun, groundAt, parent, segs[k].name + "_tome" + e, seq++, out trec);
                string rec = segs[k].name + " 端" + e + ": 積み止め " + trec + (te.label != null ? "〔" + te.label + "〕" : "");
                log.AppendLine("    " + rec); endRule.record.Add(rec);
                if (tg == null) { endRule.unresolved++; continue; }
                mine.Add(tg); res.Add(new KeyValuePair<GameObject, Vector2>(tg, te.fN)); segPieces[k].Add(tg); pool.Add(tg);
            }
            // ---- 入隅の通し(NozuraSeg.passConcave・指図 const.abutOrder 追記 2026-10-10o【硬】)── 通す側の端を角の点から後の壁の背の側へ
            //   「後の壁の控え(ctrlMax)+ 余り」以上通して止める。天端は本線と同じ一直線(端の勾配のまま延ばす)・段は端の駒と同じ H・見え面は本線の向き。
            //   置き方: 固定側 = この鎖の据わった駒(端の駒の実面へ突き付ける ── 始まりの相手)、可動側 = 通しの駒。通しの駒はこの鎖の駒に加え、
            //   後の壁(可動側)はその見え面へ突き付ける(口 ≤0.02・相手へ入らない ── PlaceNozuraRun の入隅の可動側)。
            //   硬い: 通しの駒の頂点が区画の外へ出れば退ける(endRule.parcel)。名 = 区間の名 + "_Tooshi" + 端(皮は土に埋める駒として扱う ── 埋没に数えない)。
            //   当たる先: abutOrder を持つ網(岡部 Stage2b)の野面の入隅の通す側すべて。
            foreach (var pe in passEnds)
            {
                int k = pe[1], e = pe[2], j = pe[3]; var sg = segs[k];
                Vector2 ep = endPt(sg, e), outD = e == 1 ? sg.Dir : -sg.Dir;
                Vector2 fN = faceNear(sg, e); if (fN == Vector2.zero) fN = new Vector2(outD.y, -outD.x);
                float need = ctrlMax + sg.passConcave;
                int np = Mathf.Max(1, Mathf.CeilToInt(need / (1.2f * W))); float ext = Mathf.Max(need, np * 0.85f * W + 0.01f);
                float lI = Mathf.Min(1f, sg.Len), cE = sg.crestAt(e == 0 ? 0f : sg.Len), cIn = sg.crestAt(e == 0 ? lI : sg.Len - lI), gr = lI > 1e-3f ? (cE - cIn) / lI : 0f;
                // 端の駒(角に最も近いこの鎖の駒)の H ── 焼いた駒のパスの "_H####" から
                GameObject eg = null; float bd = float.MaxValue;
                foreach (var g in mine) { if (g == null) continue; foreach (var v in Body(g.transform, 400)) { float d = Vector2.Distance(new Vector2(v.x, v.z), ep); if (d < bd) { bd = d; eg = g; } } }
                float H = float.NaN;
                if (eg != null)
                {
                    var src = UnityEditor.PrefabUtility.GetCorrespondingObjectFromOriginalSource(eg); string ap = src != null ? UnityEditor.AssetDatabase.GetAssetPath(src) : "";
                    var mH = System.Text.RegularExpressions.Regex.Match(ap, @"_H([0-9]{4})"); if (mH.Success) H = int.Parse(mH.Groups[1].Value) / 1000f;
                }
                string tag = sg.name + " 端" + e + " × " + segs[j].name;
                if (float.IsNaN(H)) { log.AppendLine("    ⛔ 入隅の通し " + tag + ": 端の駒の段が読めない(" + (eg == null ? "駒なし" : eg.name) + ")── 通さない"); if (endRule != null) endRule.unresolved++; continue; }
                var pw = new NozuraWall { kadoAbut = kadoAbut };
                pw.nodes.Add(ep); pw.nodes.Add(ep + outD * ext);
                pw.crestAt = s => cE + gr * s; pw.faceAt = s => fN;
                pw.fixHRanges.Add(new Vector3(-W, ext + W, H));
                pw.footAt = (x, z) => cE - H;
                pw.straight = straight; pw.kado = kado; pw.dan = dan; pw.kiri = kiri; pw.heights = heights; pw.faceGroundAt = faceGroundAt;
                foreach (var g in mine) if (g != null) { var bb = RB(g); if (bb.SqrDistance(new Vector3(ep.x, bb.center.y, ep.y)) < 9f) pw.startTo.Add(g); }
                pw.endThrough = true;
                string pn = sg.name + "_Tooshi" + e;
                var got2 = PlaceNozuraRun(pw, groundAt, probe, parent, pn, log);
                bool outP = false;
                if (endRule != null && endRule.parcel != null)
                    foreach (var kv in got2) foreach (var v in Body(kv.Key.transform, 4000)) if (!EdoGeom.PIP(endRule.parcel, new Vector2(v.x, v.z)) && EdoGeom.DistToPolyEdge(endRule.parcel, new Vector2(v.x, v.z)) > 0.005f) { outP = true; break; }
                if (outP)
                {
                    foreach (var kv in got2) if (kv.Key != null) UnityEngine.Object.DestroyImmediate(kv.Key);
                    string rec0 = tag + ": 入隅の通し ⛔ 区画の外へ出る(通し " + ext.ToString("F2") + "m)── 通さない";
                    log.AppendLine("    " + rec0); if (endRule != null) { endRule.record.Add(rec0); endRule.unresolved++; }
                    continue;
                }
                int ip = 0;
                foreach (var kv in got2)
                {
                    kv.Key.name = pn + "_" + (ip++).ToString("00");
                    mine.Add(kv.Key); res.Add(kv); segPieces[k].Add(kv.Key); pool.Add(kv.Key);
                }
                string rec = tag + ": 入隅の通し(abutOrder 10-10o)角から " + ext.ToString("F2") + "m(後の壁の控え " + ctrlMax.ToString("F2") + " + " + sg.passConcave.ToString("F2") + " 以上)・天端 " + cE.ToString("F2") + (Mathf.Abs(gr) > 1e-4f ? "(勾配 " + gr.ToString("F3") + " のまま)" : "") + "・H " + H.ToString("F2") + "・駒 " + got2.Count;
                log.AppendLine("    " + rec); if (endRule != null) endRule.record.Add(rec);
            }
            // 端の小口の沈み(NozuraSeg.endSink ── 指図 sodeSlope「小口を前の地表から 0.3 以上下へ」【硬】)── 端の駒の走りの最も外 0.15 の頂点の最高を
            //   見え面の前 0.5 の地表と比べて刷る(⛔ 寄せない ── 足りなければ ⛔ で記録)。当たる先: endSink を渡す区間(岡部 TW_Kado_Sode の低い端)
            for (int side = 0; side < 2; side++)
            {
                var kv = side == 0 ? ch[0] : ch[ch.Count - 1]; int k = kv.Key; int e = side == 0 ? (kv.Value ? 1 : 0) : (kv.Value ? 0 : 1);
                float need = segs[k].endSink[e]; if (float.IsNaN(need)) continue;
                Vector2 ep = endPt(segs[k], e), away = e == 1 ? segs[k].Dir : -segs[k].Dir;
                GameObject eg = null; float bu = float.MinValue;
                foreach (var g in mine) foreach (var v in Body(g.transform, 4000)) { float u = Vector2.Dot(new Vector2(v.x, v.z) - ep, away); if (u > bu) { bu = u; eg = g; } }
                if (eg == null) continue;
                float top = float.MinValue; Vector2 at0 = ep;
                foreach (var v in Body(eg.transform, 999999)) { float u = Vector2.Dot(new Vector2(v.x, v.z) - ep, away); if (u >= bu - 0.15f && v.y > top) { top = v.y; at0 = new Vector2(v.x, v.z); } }
                Vector2 fN = faceNear(segs[k], e); if (fN == Vector2.zero) fN = new Vector2(away.y, -away.x);
                float fr = groundAt(at0.x + fN.x * 0.5f, at0.y + fN.y * 0.5f), d = fr - top;
                string rec = segs[k].name + " 端" + e + ": 小口の沈み(" + eg.name + "・端の外 0.15 の頂 " + top.ToString("F2") + "・前の地表 " + fr.ToString("F2") + ")= " + d.ToString("+0.00;-0.00") + "m(要 ≥ " + need.ToString("F2") + ")" + (float.IsNaN(d) || d < need - 1e-3f ? " ⛔" : " ⭕");
                log.AppendLine("    " + rec); if (endRule != null) endRule.record.Add(rec);
            }
        }
        return res;
    }

    /// <summary>**野面の積み止めの駒を端へ据える**(2026-10-07・EDO-0502 第43巡・指図 nozuraEndRule 追記b・TW_Minami_Koshi.returnEnd・TW_Nishi_Kado.endKado)。
    /// ③ の端を直線の駒の小口で終えず、小口にも面石を積み両角を稜にした駒(<see cref="EdoAssets.Own.SannoNozuraTome"/>)で終える。
    /// 置き方の4手: 固定側 = 走りを <paramref name="run"/> 縮めて並べた直線の駒(<paramref name="mates"/>)/ 可動側 = この駒。
    /// ① 見え面: 天端の前の縁を線へ(<see cref="FaceWallToLine"/>)② 高さ: 継ぎ手の側の天端の帯(小口の稜の 0.2 を除く)を天端の線 <paramref name="crest"/> へ
    /// ③ 走り: 継ぎ手の面を隣の駒の切り口へ**触れている所**で突き付ける(<see cref="ContactPts"/> ── 走りの向きの筋ごとの隙の最小を 0 に)。
    /// ⛔ ピボット(稜・床)で位置を決めない ── 初めの置き場だけに使い、全部測って寄せる。硬い: 見え面が駒の +Z と逆に測れたら退ける(小口が逆の端へ行く)。
    /// ⟶ 返す: 据えた駒(退けたら null)・<paramref name="rec"/> に段と向き・継ぎ手の隙・小口の出(端の点から)・天端の差・前の地表から床までの根入れ。
    /// 当たる先: 野面の土留めの ③ の端すべて(岡部 Stage2b ── PlaceNozuraNet に endRule.tome を渡す邸)。</summary>
    public static GameObject PlaceNozuraTome(Func<float, bool, int, string> pathOf, float H, Vector2 ep, Vector2 away, Vector2 fN, float crest,
        IList<GameObject> mates, float run, Func<float, float, float> groundAt, Transform parent, string name, int i, out string rec)
    {
        Vector2 X = new Vector2(fN.y, -fN.x); bool plus = Vector2.Dot(X, away) > 0f;
        string path = pathOf(H, plus, i);
        if (string.IsNullOrEmpty(path) || UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { rec = "⛔ 駒が読めない " + path; return null; }
        float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
        var g = Place(path, new Vector3(ep.x, crest - H, ep.y), yaw, Vector3.one, parent, name);
        string tag = "H" + H.ToString("F2") + " " + (plus ? "P" : "M") + "(" + System.IO.Path.GetFileNameWithoutExtension(path) + ")";
        // ① 見え面: 天端の帯(最上点 − 0.15)の見え面の向きへの射影の最大 = 天端の前の縁を線へ。
        //   ⛔ FaceWallToLine は使わない ── 奥行(小口の面 1.818)が走り(0.909)より長い駒は FaceSide が向きを取り違えて 180° 回す(第43巡: M の 2 駒が裏を向いた)
        {
            var vs0 = Body(g.transform, 999999); float top0 = float.MinValue; foreach (var v in vs0) top0 = Mathf.Max(top0, v.y);
            float edge = float.MinValue; foreach (var v in vs0) if (v.y >= top0 - 0.15f) edge = Mathf.Max(edge, (v.x - ep.x) * fN.x + (v.z - ep.y) * fN.y);
            if (edge > float.MinValue) g.transform.position -= new Vector3(fN.x, 0f, fN.y) * edge;
        }
        // ② 天端(継ぎ手の側の帯)
        Func<float> crestOf = () =>
        {
            var cells = new Dictionary<long, float>();
            foreach (var v in Body(g.transform, 999999))
            {
                float u = (v.x - ep.x) * away.x + (v.z - ep.y) * away.y; if (u > -0.2f || u < -run + 0.1f) continue;
                long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
                float y; if (!cells.TryGetValue(key, out y) || v.y > y) cells[key] = v.y;
            }
            var ys = new List<float>(cells.Values); if (ys.Count == 0) return float.NaN; ys.Sort();
            int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); return top[top.Count / 2];
        };
        float c1 = crestOf(); if (!float.IsNaN(c1)) g.transform.position += Vector3.up * (crest - c1);
        float c2 = crestOf();
        // ③ 継ぎ手: 隣の駒の切り口(端の点から run より内の頂点だけ)へ触れている所で突き付ける
        var away3 = new Vector3(away.x, 0f, away.y);
        float moved0 = 0f;
        var mv = new List<Vector3>();
        foreach (var m in mates) if (m != null && m != g && m.activeInHierarchy)
            foreach (var v in Body(m.transform, 999999))
            {
                float u = (v.x - ep.x) * away.x + (v.z - ep.y) * away.y, lat = -((v.x - ep.x) * fN.x + (v.z - ep.y) * fN.y);
                if (u <= -run + 0.3f && u >= -run - 3f && lat >= -0.8f && lat <= 3f && v.y >= crest - H - 0.6f) mv.Add(v);
            }
        // 積み止めの駒は継ぎ手の側(端の点から run − 0.3 より内)だけで測る ── 小口の面の裏(奥行 1.818 の背の石)は隣の駒の背の石と筋が重なり、
        //   継ぎ手でない所を「めり込み」と読んで 0.2 外へ押し出した(第43巡)
        Func<List<Vector3>> tomeVs = () => { var l = new List<Vector3>(); foreach (var v in Body(g.transform, 999999)) if ((v.x - ep.x) * away.x + (v.z - ep.y) * away.y <= -run + 0.3f + moved0) l.Add(v); return l; };
        Vector3 at; int cnt; float gap = mv.Count == 0 ? float.NaN : ContactPts(mv, tomeVs(), away3, out at, out cnt);
        float moved = 0f, gap2 = float.NaN; int cnt2 = 0;
        if (!float.IsNaN(gap))
        {
            moved = -gap; g.transform.position += away3 * moved; moved0 = moved;
            gap2 = ContactPts(mv, tomeVs(), away3, out at, out cnt2);
        }
        // 刷る: 小口の出(天端の帯の端の点から away へ)・根入れ(小口の前 0.5 の地表 − 床)
        float topY = float.MinValue; var all = Body(g.transform, 999999); foreach (var v in all) topY = Mathf.Max(topY, v.y);
        float kU = float.MinValue; foreach (var v in all) if (v.y >= topY - 0.15f) kU = Mathf.Max(kU, (v.x - ep.x) * away.x + (v.z - ep.y) * away.y);
        Vector2 fq = ep + away * Mathf.Min(0f, kU) - away * 0.3f + fN * 0.5f; float gF = groundAt(fq.x, fq.y);
        float floorY = crest - H;   // 床 = 天端 − 段(駒の床レベル)
        // 見え面の天端の実面で、積み止めと隣の見えている駒の天端を比べる(指図 TW_Minami_Koshi.returnEnd 追記「隠れた駒と比べない」・EDO-0502 第45巡)──
        //   見え面の線から背へ 0.4・前へ 0.3 の帯の天端(0.2 の升ごとの最高の上 4 割の中央値)。隣 = 継ぎ手の手前 0.1〜0.9 の mates の頂点(この鎖の駒だけ)
        Func<IEnumerable<Vector3>, float, float, float> faceTop = (src, uLo, uHi) =>
        {
            var cells = new Dictionary<long, float>();
            foreach (var v in src)
            {
                float u = (v.x - ep.x) * away.x + (v.z - ep.y) * away.y, lat = (v.x - ep.x) * fN.x + (v.z - ep.y) * fN.y;
                if (u < uLo || u > uHi || lat < -0.4f || lat > 0.3f) continue;
                long key = ((long)Mathf.FloorToInt(v.x / 0.2f) << 32) ^ (uint)Mathf.FloorToInt(v.z / 0.2f);
                float y; if (!cells.TryGetValue(key, out y) || v.y > y) cells[key] = v.y;
            }
            var ys = new List<float>(cells.Values); if (ys.Count == 0) return float.NaN; ys.Sort();
            int k0 = (int)(ys.Count * 0.6f); var top = ys.GetRange(k0, ys.Count - k0); return top[top.Count / 2];
        };
        float fT = faceTop(Body(g.transform, 999999), -run + moved + 0.1f, -0.2f);
        var mAll = new List<Vector3>(); foreach (var m in mates) if (m != null && m != g && m.activeInHierarchy) mAll.AddRange(Body(m.transform, 999999));
        float fM = faceTop(mAll, -run + moved - 0.9f, -run + moved - 0.1f);
        rec = tag + "・継ぎ手 " + (float.IsNaN(gap2) ? "⚠ 相手の切り口が測れない(寄せず)" : gap2.ToString("+0.000;-0.000") + "m(筋 " + cnt2 + "・寄せ " + moved.ToString("+0.000;-0.000") + ")")
            + "・小口の出(端の点から)" + kU.ToString("+0.00;-0.00") + "m・天端の差 " + (float.IsNaN(c2) ? "-" : (c2 - crest).ToString("+0.000;-0.000"))
            + "・見え面の天端 積み止め " + (float.IsNaN(fT) ? "-" : fT.ToString("F2")) + " − 隣の見えている駒 " + (float.IsNaN(fM) ? "-(隣が無い)" : fM.ToString("F2") + " = " + (fT - fM).ToString("+0.00;-0.00"))
            + "・前の地表 " + gF.ToString("F2") + " − 床 " + floorY.ToString("F2") + " = 根入れ " + (gF - floorY).ToString("F2");
        return g;
    }

    /// <summary>**腰の土留めの端の背を小段に切る**(koshiEnd・指図 nozuraEndRule 追記 2026-10-06・EDO-0502 第31巡)。端 <paramref name="ep"/> から内へ一間
    /// (<paramref name="along"/>・端の駒と見切り石が座る区間)、見え面の線から背へ <paramref name="depth"/>(一間 ── 石の控えを含む)の帯を高さ <paramref name="y"/>
    /// (端の天端 − 0.05)の平らな小段にし、その外は切土 1:<paramref name="bc"/> の法で今の地盤へ擦り付ける。⭐ 2m 格子は節点の間を一次で描く ⇒ 帯 + 一升の節点まで平らに取る
    /// (<see cref="LevelPadAt"/> と同じ取り方)。硬い: **切るだけ**(盛らない)・区画の外の節点は触らない・切りの最大 > <paramref name="cutMax"/> なら切らない・
    /// 練塀(<paramref name="keep"/>)の実メッシュの足元から <paramref name="keepGap"/> 以内に切りが掛かれば切らない(犬走りを割る)。冪等(今の地盤を法で挟むだけ)。
    /// 当たる先: 背が法の腰の野面の土留めの相手の居ない端(岡部 TW_Kita_Koshi・TW_Nishi_Kado ── TW_Higashi_Minami は 2026-10-12 案A で石垣 野面へ)。⟶ 返す: 切ったか(note に節点数・切りの最大・退けた理由)</summary>
    public static bool CutKoshiBench(Vector2 ep, Vector2 away, Vector2 face, float y, float along, float depth, float bc, float cutMax,
                                     Vector2[] parcel, IList<GameObject> keep, float keepGap, out string note,
                                     float depthMin = float.NaN, Func<Vector2, bool> isCut = null, float bcCut = 1f, float drain = 0f)
    {
        // 改め(指図 nozuraEndRule 追記2・EDO-0502 第32巡): 奥行は見え面の線から測り、狙い depth【柔】から下限 depthMin(控えの後端 + 0.3)【硬】へ
        //   0.1 刻みで縮めて切り ≤ cutMax を満たす最も深い奥行を採る(PlaceBest と同じ ── 硬い条件の中で狙いに最も近い所)。
        //   小段の先の法は背が切土の節点なら 1:bcCut(const.batterCut)・盛土なら 1:bc。小段は端の先(away)へ 1/drain で落とす(端の側が低い)
        if (float.IsNaN(depthMin) || depthMin > depth) depthMin = depth;
        string last = null; var dps = new List<float>();
        for (float dp = depth; dp > depthMin + 1e-3f; dp -= 0.1f) dps.Add(dp);
        dps.Add(depthMin);
        foreach (float dp in dps)
        {
            string nt; int r = CutKoshiBenchAt(ep, away, face, y, along, dp, bc, cutMax, parcel, keep, keepGap, isCut, bcCut, drain, out nt);
            if (r == 1) { note = "奥行 " + dp.ToString("F2") + "(狙い " + depth.ToString("F2") + "・下限 " + depthMin.ToString("F2") + ")" + nt + (dp < depth - 1e-3f ? " ⚠ 狙い未達(奥行を縮めた)" : ""); return true; }
            if (r == 0) { note = nt; return false; }       // 切る節点なし(縮めても同じ)
            last = nt;
        }
        note = "下限の奥行 " + depthMin.ToString("F2") + " でも " + last; return false;
    }

    /// <summary>CutKoshiBench の一つの奥行。返り: 1 = 切った / 0 = 切らない(縮めても同じ)/ −1 = 切りが上限を超える(縮めれば通るかもしれない)。</summary>
    static int CutKoshiBenchAt(Vector2 ep, Vector2 away, Vector2 face, float y, float along, float depth, float bc, float cutMax,
                               Vector2[] parcel, IList<GameObject> keep, float keepGap, Func<Vector2, bool> isCut, float bcCut, float drain, out string note)
    {
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        // 帯(世界 xz の四隅): 走りは [端 − along, 端]・奥行は見え面の線 → 背へ depth
        var foot = new[] { ep, ep - away * along, ep - away * along - face * depth, ep - face * depth };
        Func<Vector2, float> benchY = p => drain > 0f ? y - (along - Mathf.Clamp(Vector2.Dot(ep - p, away), 0f, along)) / drain : y;
        // 小段の先は今の法を背へ平行に退ける(指図 追記2「今の法と同じ勾配で背へ平行に退けて今の地盤へ擦り付ける」)── 退ける量 Δ = 奥行 − 今の地盤が小段の高さを
        //   越える離れ(帯の走りの中ほどで測る)。法の面 = 今の地盤を見え面の側へ Δ ずらした値。Δ ≤ 0 なら法は触らない
        Vector2 midB = ep - away * (along * 0.5f); float d0 = depth;
        for (float dd = 0f; dd <= depth + 1e-3f; dd += 0.1f) { Vector2 q = midB - face * dd; float g0 = Ground(q.x, q.y); if (!float.IsNaN(g0) && g0 > y + 1e-3f) { d0 = dd; break; } }
        float shift = Mathf.Max(0f, depth - d0);
        Func<Vector2, float, float> target = (p, cur) =>
        {
            if (parcel != null && !EdoGeom.PIP(parcel, p)) return cur;
            if (EdoGeom.PIP(foot, p)) return Mathf.Min(cur, benchY(p));
            float d = DistPolyLine(foot, p);
            if (d <= cell) return Mathf.Min(cur, benchY(p));
            if (shift <= 0f) return cur;
            Vector2 q = p + face * shift; float sh = Ground(q.x, q.y);
            if (float.IsNaN(sh)) { float b = isCut != null && isCut(p) ? bcCut : bc; sh = benchY(p) + (d - cell) / b; }
            return Mathf.Min(cur, Mathf.Max(benchY(p), sh));
        };
        float reach = cell + 6f * bc + cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in foot) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        float cm = 0f, cmB = 0f, dAt = 0f; int n = 0;
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            float cur = H[iz, ix] * ts.y + tp.y, nw = target(p, cur);
            if (cur - nw > 1e-4f)
            {
                n++; float dd = EdoGeom.PIP(foot, p) ? 0f : DistPolyLine(foot, p);
                if (cur - nw > cm) { cm = cur - nw; dAt = dd; }
                if (dd <= cell) cmB = Mathf.Max(cmB, cur - nw);
            }
        }
        if (n == 0) { note = "切る節点なし(背の土は既に小段より低い)"; return 0; }
        if (cm > cutMax + 1e-3f) { note = "切りの最大 " + cm.ToString("F2") + "m > " + cutMax.ToString("F1") + "(小段の帯の中の最大 " + cmB.ToString("F2") + "・最大は小段の縁から " + dAt.ToString("F1") + "m の法)── 切らない"; return -1; }
        // 練塀の犬走り: 練塀の実メッシュの足元(最下から 0.3m の帯)の点で、切りの面(帯 + 離れ)が今の地盤より下がるなら割る
        if (keep != null)
            foreach (var g in keep) if (g != null)
            {
                var vs = Body(g.transform, 600); float lo = float.MaxValue; foreach (var v in vs) lo = Mathf.Min(lo, v.y);
                foreach (var v in vs)
                {
                    if (v.y > lo + 0.3f) continue; var p = new Vector2(v.x, v.z);
                    if (p.x < mnx - reach || p.x > mxx + reach || p.y < mnz - reach || p.y > mxz + reach) continue;
                    float d = EdoGeom.PIP(foot, p) ? 0f : DistPolyLine(foot, p);
                    // 犬走りの離れの分だけ見え面の側の点で切りの面を読む(切りの面が犬走りの幅だけ手前へ来ても足元を割らない)
                    Vector2 pk = p + face * keepGap; float tgt = target(pk, float.MaxValue), g0 = Ground(p.x, p.y);
                    if (tgt == float.MaxValue) continue;
                    if (!float.IsNaN(g0) && tgt < g0 - 0.01f) { note = "練塀 " + g.name + " の犬走り " + keepGap.ToString("F1") + " を割る(" + p.x.ToString("F1") + ", " + p.y.ToString("F1") + ")── 切らない"; return -1; }
                }
            }
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
        {
            var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
            float cur = H[iz, ix] * ts.y + tp.y, nw = target(p, cur);
            if (cur - nw > 1e-4f) H[iz, ix] = (nw - tp.y) / ts.y;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        note = "(法を背へ " + shift.ToString("F2") + "m 退けた・高さ " + y.ToString("F2") + (drain > 0f ? "→端で " + (y - along / drain).ToString("F2") : "") + "・節点 " + n + "・切りの最大 " + cm.ToString("F2") + "m)";
        return 1;
    }

    /// <summary>**口の縁の見切り石を据える**(2026-09-26・EDO-0437)。野面の土留めの線の端 <paramref name="edge"/> に、見え面 <paramref name="face"/>
    /// を線へ(天端の前の縁 = <see cref="FaceWallToLine"/>)、丈は見付(天端 <paramref name="crestY"/> − 足元の面 <paramref name="footY"/>)以上で焼いてある最も低い段
    /// (<paramref name="pathOfH"/>)、⭐ 高さは**天端で**合わせる(駒の最高 = 土留めの天端。段が見付より高い分は下へ沈む ── 床で据えると背の土に埋まる)、
    /// 走り <paramref name="toward"/>(端から口へ)の向きに相手 <paramref name="partners"/>(城の石垣・袖の駒)と**触れる所まで**寄せる
    /// (<see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/> の最小)。相手に届かなければ ⚠ で刷って端に置いたまま。
    /// 当たる先: 野面と城の石垣・石段の袖の間の見切り(山王 男坂の口の両脇、今後の各邸の庭の土留めと石段の取り合い)。</summary>
    public static GameObject PlaceNozuraMikiri(Func<float, string> pathOfH, Vector2 edge, Vector2 toward, Vector2 face, float footY, float crestY, IList<GameObject> partners,
                                               Transform parent, string name, System.Text.StringBuilder log, Func<float, float, float> soilAt = null)
    {
        if (pathOfH == null || float.IsNaN(crestY) || float.IsNaN(footY)) return null;
        float need = crestY - footY; string path = pathOfH(need);
        if (string.IsNullOrEmpty(path) || !System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, path)))
        { log.AppendLine("    ⛔ 見切り石 " + name + ": 見付 " + need.ToString("F2") + " 以上の見切り石が焼いていない(" + path + ")── 据えない"); return null; }
        Vector2 X = new Vector2(face.y, -face.x); float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
        Vector2 d = toward.normalized;
        var g = Place(path, new Vector3(edge.x - d.x * 1.0f, footY, edge.y - d.y * 1.0f), yaw, Vector3.one, parent, name);
        if (g == null) return null;
        FaceWallToLine(g, face, edge);
        float y1 = float.MinValue; foreach (var v in Body(g.transform, 999999)) y1 = Mathf.Max(y1, v.y);
        g.transform.position += Vector3.up * (crestY - y1);
        float y0 = float.MaxValue; foreach (var v in Body(g.transform, 999999)) y0 = Mathf.Min(y0, v.y);
        float best = float.NaN; Vector3 at = Vector3.zero; int cnt = 0;
        foreach (var p in partners) if (p != null)
        {
            Vector3 a1; int c1; float c = Contact(g, p, new Vector3(d.x, 0f, d.y), out a1, out c1);
            if (!float.IsNaN(c) && (float.IsNaN(best) || c < best)) { best = c; at = a1; cnt = c1; }
        }
        if (float.IsNaN(best) && partners.Count == 0)
        {   // 相手の居ない端(endRule ②)── 見切り石の外の小口(走りの先の面の実メッシュ)を土留めの線の端へ揃える
            float mx = float.MinValue; foreach (var v in Body(g.transform, 999999)) mx = Mathf.Max(mx, Vector2.Dot(new Vector2(v.x, v.z) - edge, d));
            best = -mx; cnt = 0;
        }
        else if (float.IsNaN(best)) { log.AppendLine("    ⚠ " + name + ": 見切り石が相手(" + partners.Count + " 駒)に向き合わない ── 端から 1.0m 引いたまま"); return g; }
        g.transform.position += new Vector3(d.x, 0f, d.y) * best;
        // ⛔ 硬い制約(許容0 の埋没): 背の土(<paramref name="soilAt"/>)が石の頭より上に来るなら据えない ── 見切り石は見え 0.6 の一石で、
        //   それより高い土は受けられない(男坂の口の南は背の地盤が 16.1・石の頭 15.1 で 0.62 埋まった・2026-09-26)。
        if (soilAt != null)
        {
            Vector3 bat; float bur = SoilSideCrestShort(g, new[] { face }, soilAt, out bat);
            if (!float.IsNaN(bur) && bur > 0.05f && MikiriBackSoilCut)
                log.AppendLine("    見切り石 " + name + ": 背の土が石の頭より " + bur.ToString("F2") + "m 高い ── 皮が背の土を頭より下げる(指図「見切り石の背の土は頭より低く」【硬】)ので据える");
            else if (!float.IsNaN(bur) && bur > 0.05f)
            {
                log.AppendLine("    ⛔ 見切り石 " + name + ": 背の土が石の頭より " + bur.ToString("F2") + "m 高い(" + bat.x.ToString("F1") + ", " + bat.z.ToString("F1") +
                               ")── 埋没(許容0)なので据えない。土留めの端は近くの駒の実面へ突き付ける");
                UnityEngine.Object.DestroyImmediate(g); return null;
            }
        }
        log.AppendLine("    見切り石 " + name + ": " + System.IO.Path.GetFileNameWithoutExtension(path) + "(見付 " + need.ToString("F2") + ")・天端 " + crestY.ToString("F2") + " に最高を揃え最下点 " + y0.ToString("F2") +
                       "(足元の面 " + footY.ToString("F2") + ")・相手へ " + best.ToString("+0.000;-0.000") + "m 寄せた(当たり " + at.ToString("F2") + "・筋 " + cnt + ")");
        return g;
    }


    /// <summary>**前の地表より低い天端の区間を置かない**(打ち切り ── 第87巡・岡部 指図 sideEnd/sodeSlope 追記 2026-10-10d【硬】「天端が前の地表より低い駒は置かない
    /// (打ち切りの駒の先に足さない)」)。区間 <paramref name="seg"/> を 0.1m おきに歩き、天端(crestAt)が前の地表 <paramref name="frontAt"/>(走りの点 → 前の地表)
    /// より低くなった所から低い端の側を切り落とす。区間の端の型(打ち切り・小口)は据える側(PlaceNozuraNet)がそのまま掛ける。
    /// ⟶ 返す: 0 = そのまま / 1 = 縮めた / 2 = 全部が前の地表より低い(置かない)。当たる先: 低い端を前の地表へ下ろす坂の袖・延長の run。</summary>
    public static int TrimSegBelowFront(NozuraSeg seg, Func<Vector2, float> frontAt, out float cutAt)
    {
        cutAt = float.NaN; float L = Vector2.Distance(seg.a, seg.b); if (L < 1e-3f || seg.crestAt == null) return 0;
        var t = (seg.b - seg.a) / L; bool lowAtB = seg.crestAt(L) <= seg.crestAt(0f);
        Func<float, bool> below = sl => { float g = frontAt(seg.a + t * sl); return !float.IsNaN(g) && seg.crestAt(sl) < g; };
        float keep0 = 0f, keep1 = L;
        if (lowAtB) { for (float sl = 0f; sl <= L + 1e-4f; sl += 0.1f) if (below(Mathf.Min(sl, L))) { keep1 = Mathf.Min(sl, L); break; } }
        else { for (float sl = L; sl >= -1e-4f; sl -= 0.1f) if (below(Mathf.Max(sl, 0f))) { keep0 = Mathf.Max(sl, 0f); break; } }
        if (keep1 - keep0 < 0.05f) { cutAt = lowAtB ? keep1 : keep0; return 2; }
        if (keep0 <= 1e-4f && keep1 >= L - 1e-4f) return 0;
        var crest0 = seg.crestAt; float off = keep0;
        var a0 = seg.a; seg.a = a0 + t * keep0; seg.b = a0 + t * keep1;
        if (off > 0f) seg.crestAt = sl => crest0(sl + off);
        cutAt = lowAtB ? keep1 : keep0; return 1;
    }

    /// <summary>**相手の区間の線を越えて据えない**(突き付けの前の縮め ── 第89巡・岡部 指図 ends 追記 2026-10-10f【硬】「隅の駒の見え面に突き付け、隅の駒の天端の帯・見え面の上に駒を据えない」)。
    /// 区間 <paramref name="seg"/> の端 e が、相手の区間 <paramref name="other"/> の線を、自分の反対の端の側から越えていれば、端を相手の線との交点まで縮める。
    /// 交点からの突き付け(相手の据わった駒の実面へ)は据える側(PlaceNozuraNet ③)が掛ける。⟶ 縮めた長さ(縮めなければ 0)。当たる先: 隅で他の run へ取り付く run の端。</summary>
    public static float TrimSegToPartnerLine(NozuraSeg seg, int e, NozuraSeg other)
    {
        Vector2 d = seg.b - seg.a; float L = d.magnitude; if (L < 1e-3f) return 0f; d /= L;
        Vector2 od = other.b - other.a; float oL = od.magnitude; if (oL < 1e-3f) return 0f; od /= oL; var on = new Vector2(-od.y, od.x);
        Vector2 ep = e == 1 ? seg.b : seg.a, sp = e == 1 ? seg.a : seg.b;
        float se = Vector2.Dot(ep - other.a, on), ss = Vector2.Dot(sp - other.a, on);
        if (Mathf.Abs(ss) < 1e-3f || Mathf.Sign(se) == Mathf.Sign(ss) || Mathf.Abs(se) < 1e-3f) return 0f;   // 越えていない
        float den = Vector2.Dot(e == 1 ? d : -d, on); if (Mathf.Abs(den) < 1e-3f) return 0f;
        float t = -se / den;   // 端から交点まで(負 = 戻る)
        var x = ep + (e == 1 ? d : -d) * t;
        float u = Vector2.Dot(x - other.a, od); if (u < -0.5f || u > oL + 0.5f) return 0f;   // 相手の線の外
        float cut = Vector2.Distance(ep, x); if (cut >= L - 0.05f) return 0f;
        if (e == 1) seg.b = x; else { var c0 = seg.crestAt; float off = cut; seg.a = x; if (c0 != null) seg.crestAt = sl => c0(sl + off); }
        return cut;
    }

    /// <summary>**交わる所を据える順の型**(const.abutOrder【硬】・第90巡):「隅の駒 → 本線 → 返し・袖・端 の順に据え、後から据える方が先の方の見え面に突き付ける」。
    /// 端どうしが <paramref name="near"/> 以内で出会う区間の組のうち、順位(<paramref name="rank"/> ── 大きいほど後)の違う組で、後の区間を可動側(movesAtConcave)・先の区間を通す側にする。
    /// <paramref name="passClear"/>(NaN でない時・const.abutOrder 追記 2026-10-10o【硬】): 全区間に <see cref="NozuraSeg.passConcave"/> を立て、
    /// 入隅の通す側になった端を角の点から「後の壁の控え + passClear」以上通す(延ばす・据えるのは PlaceNozuraNet)。
    /// ⟶ 書き換えた区間の数。当たる先: 野面の土留めの網(返し・袖・端を持つ全ての run)。</summary>
    public static int ApplyAbutOrder(List<NozuraSeg> segs, Func<NozuraSeg, int> rank, float near, System.Text.StringBuilder log, float passClear = float.NaN)
    {
        int n = 0;
        // 入隅の通し(const.abutOrder 追記 2026-10-10o【硬】): 全ての入隅で、先に据える壁(通す側)を角の点から後の壁の背の側へ「後の壁の控え + passClear」以上通す。
        //   通す側・可動側は据える側(PlaceNozuraNet)が決める ⇒ ここでは全区間に余りを持たせ、通す側になった端だけが延ばす。
        if (!float.IsNaN(passClear)) foreach (var sg in segs) sg.passConcave = passClear;
        for (int i = 0; i < segs.Count; i++)
            for (int j = 0; j < segs.Count; j++)
            {
                if (i == j) continue; int ri = rank(segs[i]), rj = rank(segs[j]); if (ri <= rj) continue;
                bool meet = false;
                foreach (var pi in new[] { segs[i].a, segs[i].b })
                {
                    var o = segs[j]; Vector2 d = o.b - o.a; float L = d.magnitude; if (L < 1e-3f) continue; d /= L;
                    float u = Mathf.Clamp(Vector2.Dot(pi - o.a, d), 0f, L); if (Vector2.Distance(o.a + d * u, pi) <= near) meet = true;
                }
                if (!meet) continue;
                if (!segs[i].movesAtConcave || segs[j].movesAtConcave) { if (log != null) log.AppendLine("    据える順(abutOrder): " + segs[i].name + " を " + segs[j].name + " へ突き付ける側に"); n++; }
                segs[i].movesAtConcave = true; segs[j].movesAtConcave = false;
            }
        return n;
    }

    /// <summary>見切り石の背の土を皮が頭より下げる(指図の欄 ── 岡部 roadEdge・cuts 追記 2026-10-10h)と呼び手が名乗るとき true ── 背の土が頭より高くても見切り石を退けない。
    /// ⚠ 呼び手は PlaceNozuraNet の前に立て、後に必ず戻す。</summary>
    public static bool MikiriBackSoilCut;
}
