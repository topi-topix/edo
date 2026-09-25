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
        const float W = 1.818f, HALF = 0.909f;
        // 区間ごとの走りの向き・弧長・見え面(低い側)
        var dir = new Vector2[m - 1]; var face = new Vector2[m - 1]; var s0 = new float[m];
        for (int i = 0; i + 1 < m; i++)
        {
            float l = Vector2.Distance(P[i], P[i + 1]); dir[i] = (P[i + 1] - P[i]) / Mathf.Max(l, 1e-6f); s0[i + 1] = s0[i] + l;
            int vn, vx; var lo = LowSide(P[i], P[i + 1], groundAt, probe, 0.05f, null, out vn, out vx);
            face[i] = lo;
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
        // 見付: 天端 − 見え面の足元(線から前へ 0.25 と 0.7)の地表の最小 ⇒ 焼いてある段のうち床がその下に入る最小
        Func<float, float, float, int, float> needH = (sa, sb2, top, si) =>
        {
            float gmin = float.MaxValue;
            for (float s = sa; s <= sb2 + 1e-4f; s += Mathf.Max(0.1f, (sb2 - sa) / 6f))
            { int k = Mathf.Clamp(si < 0 ? segOf(s) : si, 0, m - 2); Vector2 q = at(Mathf.Clamp(s, 0f, L));
              foreach (float off in new[] { 0.25f, 0.7f })
              { float x = q.x + face[k].x * off, z = q.y + face[k].y * off;
                float g = w.footAt != null ? w.footAt(x, z) : float.NaN; if (float.IsNaN(g)) g = groundAt(x, z);
                if (!float.IsNaN(g)) gmin = Mathf.Min(gmin, g); } }
            float need = top - gmin;
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
        float worstCrest = 0f; int idx = 0;
        // 置いた駒を天端の線へ据える(高さ・見え面)── 測って寄せる
        Action<GameObject, float, Vector2, Vector2> seat = (g, crest, fN, lineA) =>
        {
            FaceWallToLine(g, fN, lineA);
            float c = crestOf(g); if (!float.IsNaN(c)) g.transform.position += Vector3.up * (crest - c);
            float c2 = crestOf(g); if (!float.IsNaN(c2)) worstCrest = Mathf.Max(worstCrest, Mathf.Abs(c2 - crest));
        };

        // ---- ① 固定の駒: 出隅と段の境 ----------------------------------------------------------
        var fixedSpans = new List<float[]>();                      // [s の始まり, s の終わり](走りの座標)
        for (int i = 1; i + 1 < m; i++)
        {
            float turn = Vector2.Angle(dir[i - 1], dir[i]); if (turn < 60f) continue;
            Vector2 f1 = face[i - 1], f2 = face[i];
            // 凸(出隅): 次の区間は前の区間の見え面の裏(−f1)へ向かう
            if (Vector2.Dot(dir[i], f1) > -0.3f) { log.AppendLine("    ⚠ " + name + " 折れ " + i + " は入隅 — 隅の駒は据えない"); continue; }
            float sc = s0[i]; float crest = w.crestAt(sc);
            float hk = needH(sc - HALF, sc + HALF, crest, -1);
            // 局所 +Z = 片方の見え面・+X = もう片方(+Z = +X を反時計 90°)
            Func<Vector2, Vector2> ccw = v => new Vector2(-v.y, v.x);
            Vector2 X = Vector2.Dot(ccw(f2), f1) > 0f ? f2 : f1; Vector2 Z = ccw(X);
            float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
            string path = w.kado(hk, idx);
            if (path == null || !System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, path)))
            { log.AppendLine("    ⛔ " + name + " 隅 " + i + ": 隅の駒が焼いていない(見付 " + hk + ")— 据えない"); continue; }
            var kg = Place(path, new Vector3(P[i].x, crest - hk, P[i].y), yaw, Vector3.one, parent, name + "_kado" + i);
            // 稜線を二本の天端の線の交点へ: 天端の帯の前の縁を各々の見え面の向きで測って寄せる
            for (int pass = 0; pass < 2; pass++)
            {
                var vs = Body(kg.transform, 999999); float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
                float e1 = float.MinValue, e2 = float.MinValue;
                foreach (var v in vs) if (v.y >= top - 0.15f)
                { Vector2 r = new Vector2(v.x, v.z) - P[i]; e1 = Mathf.Max(e1, Vector2.Dot(r, f1)); e2 = Mathf.Max(e2, Vector2.Dot(r, f2)); }
                kg.transform.position -= new Vector3(f1.x * e1 + f2.x * e2, 0f, f1.y * e1 + f2.y * e2);
                float c = crestOf(kg); if (!float.IsNaN(c)) kg.transform.position += Vector3.up * (crest - c);
            }
            { float c2 = crestOf(kg); if (!float.IsNaN(c2)) worstCrest = Mathf.Max(worstCrest, Mathf.Abs(c2 - crest)); }
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
            string path = w.dan(rises, idx);
            var dg = Place(path, new Vector3(c.x, mid - 1.5f, c.y), yaw, Vector3.one, parent, name + "_dan");
            seat(dg, mid, fN, c);
            // 走りの位置: 中心を段の境へ(両切り口の中点)
            var sp = span(dg, c, dir[si]); dg.transform.position -= new Vector3(dir[si].x, 0f, dir[si].y) * (0.5f * (sp[0] + sp[1]));
            sp = span(dg, c, dir[si]);
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
        log.AppendLine("    端: 始まり " + (freeA ? "打ち切り" : "相手の面へ s=" + sStart.ToString("F2")) + " / 終わり " + (freeB ? "打ち切り" : "相手の面へ s=" + sStop.ToString("F2") + "(線の終わり " + L.ToString("F2") + ")"));

        // ---- ③ 固定の駒の間を 1間の駒で埋める -------------------------------------------------
        fixedSpans.Sort((a, b) => a[0].CompareTo(b[0]));
        var gaps = new List<float[]>(); float cur0 = sStart;
        foreach (var f in fixedSpans) { gaps.Add(new[] { cur0, f[0], 0 }); cur0 = f[1]; }
        gaps.Add(new[] { cur0, sStop, 1 });
        float worstJoint = 0f; int nPieces = 0;
        for (int gi = 0; gi < gaps.Count; gi++)
        {
            float a = gaps[gi][0], b = gaps[gi][1], len = b - a;
            if (len < 0.05f) continue;
            bool lastFree = gi == gaps.Count - 1 && freeB, firstFree = gi == 0 && freeA;
            bool abutEnd = (gi == 0 && !freeA) || (gi == gaps.Count - 1 && !freeB);
            int N; float sc;
            if (len >= 0.85f * W) { N = Mathf.Max(1, Mathf.RoundToInt(len / W)); sc = len / (N * W); if (sc > 1.2f) { N++; sc = len / (N * W); } }
            else if (abutEnd) { N = 1; sc = Mathf.Max(0.4f, len / W); }    // 短い端は縮めて相手の面まで(縮めきれない分だけ相手の中へ)
            else { N = 1; sc = Mathf.Max(0.5f, len / W); }
            // 始まり側から連ねる(相手へ入れる短い端は、固定の駒の側から)
            bool fromB = gi == 0 && abutEnd && len < 0.85f * W;
            float edge = fromB ? b : a;
            for (int k = 0; k < N; k++)
            {
                float sMid = fromB ? edge - 0.5f * W * sc : edge + 0.5f * W * sc;
                int si = segOf(Mathf.Clamp(sMid, 0f, L)); Vector2 c = at(Mathf.Clamp(sMid, 0f, L)) + dir[si] * (sMid - Mathf.Clamp(sMid, 0f, L));
                float crest = w.crestAt(Mathf.Clamp(sMid, 0f, L));
                float h = needH(sMid - 0.5f * W * sc, sMid + 0.5f * W * sc, crest, si);
                Vector2 X = new Vector2(face[si].y, -face[si].x);
                float yaw = Mathf.Atan2(-X.y, X.x) * Mathf.Rad2Deg;
                bool kiriHere = (lastFree && k == N - 1 && !fromB) || (firstFree && k == 0 && !fromB);
                string path;
                if (kiriHere && w.kiri != null)
                {   // 打ち切り: 端へ向かって天端が下がる
                    bool towardPlus = Vector2.Dot(X, dir[si]) > 0f; bool endIsB = lastFree && k == N - 1;
                    path = w.kiri(endIsB ? !towardPlus : towardPlus, idx);
                }
                else path = w.straight(h, 0f, idx);
                var g = Place(path, new Vector3(c.x, crest - h, c.y), yaw, new Vector3(sc, 1f, 1f), parent, name + "_" + nPieces.ToString("000"));
                seat(g, crest, face[si], c);
                // 前の切り口へ突き付ける(実メッシュの走りへの射影)
                var sp = span(g, P[si], dir[si]);
                float want = fromB ? (edge - s0[si]) - sp[1] : (edge - s0[si]) - sp[0];
                g.transform.position += new Vector3(dir[si].x, 0f, dir[si].y) * want;
                sp = span(g, P[si], dir[si]);
                float nextEdge = fromB ? s0[si] + sp[0] : s0[si] + sp[1];
                edge = nextEdge; idx++; nPieces++;
                res.Add(new KeyValuePair<GameObject, Vector2>(g, face[si]));
            }
            // 最後の切り口と次の固定の駒(または端)との隙
            float resid = fromB ? edge - a : b - edge;
            if (!(abutEnd && len < 0.4f * W)) worstJoint = Mathf.Max(worstJoint, Mathf.Abs(resid));
            log.AppendLine("    間 " + gi + ": 走り " + len.ToString("F2") + "m に 1間の駒 " + N + "(伸縮 " + sc.ToString("F3") + ")・末の隙 " + resid.ToString("+0.000;-0.000"));
        }
        log.AppendLine("    ⇒ " + name + ": 駒 " + res.Count + "(直線 " + nPieces + ")/ 継ぎ目の隙の最悪 " + worstJoint.ToString("F3") + "m / 天端の差の最悪 " + worstCrest.ToString("F3") + "m");
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
}
