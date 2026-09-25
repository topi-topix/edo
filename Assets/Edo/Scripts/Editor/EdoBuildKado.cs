// 隅部材(留め継ぎ)の据え — EdoBuild の partial (2026-09-21・EDO-0289 ②)
//   松江松平が持っていた「隅を犬走りへ寄せる」「腕の実端面を測る」を共通の層へ引き取った。
//   岡部は隅を区画線の上に据えたまま run だけ犬走りへ寄せていたので、隅が壁面より 0.76m 外へ張り出し、
//   腕(±4.1m)は run の端と重なっていた(2026-09-21 実測)。⛔ 邸ビルダーにこの二つを書き写さない。
//   ⭐ 使い方(順が肝): 隅を**先に**据える → KadoFace で両腕の外面を犬走りへ寄せる → KadoArm で腕の実端面を測る
//      → 辺の端の run の端を、その実端面へ突き付ける。事後に寄せる関数は持たない(docs/oki-kata.md §2)。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary><see cref="KadoFace"/> が 2 元 1 次方程式を厳密に解く下限。両辺の外向き法線の外積の絶対値
    /// (= sin 折れ角)。これ未満は面の法線方向へだけ動かす。</summary>
    const float ExactSolveDet = 0.5f;

    /// <summary>**隅の折れ角[°]を区画から測る。**入りの走り(頂点の手前の辺)から出の走り(次の辺)への旋回で、
    /// 左へ曲がれば負・右へ曲がれば正。<paramref name="vertex"/> は折れ点の頂点番号。
    ///
    /// <para>⛔ **指図や算出物が宣言する `deg` を信じない**(規則21「部材の基準点で位置を決めない」と同じ型 —
    /// 宣言された寸法は、生成器を一度でも入れ替えた瞬間に実物と食い違う)。⭐ 2026-09-21 に実際に起きた:
    /// 岡部の生成器だけが折れ角を**符号を反転して**焼いていて、`EdoAssets.Own.Kado(part, deg)` が
    /// deg&lt;0 で選ぶ `M`(鏡像)変種のせいで、**隅 8 基すべてが鏡像の部材**で建っていた。
    /// 浅い隅(P1 +0.24°)は誤差 2×|deg| が小さく健全に見え、深い隅ほど壊れる —
    /// Kado_P11(+61.61°)が区画線を 2.862m、Kado_P0(+95.11°)が 2.261m 越えた。掲示板 EDO-0343。
    /// ⚠ 松江松平の宣言(+90.95 / +18.54 / −87.76 / +41.24 / +18.52)は実測と一致していたので、
    /// この関数へ移しても**建つ姿は変わらない**(移行の安全確認に使える)。</para>
    ///
    /// <para>⭕ 部材の名前の符号 = この旋回の符号。`Own.Kado` が `|deg| の四捨五入 + (負なら M)` で引く。</para></summary>
    public static float KadoDeg(Vector2[] poly, int vertex)
    {
        int n = poly.Length;
        Vector2 P = poly[((vertex % n) + n) % n];
        Vector2 a = poly[(((vertex - 1) % n) + n) % n];
        Vector2 b = poly[(((vertex + 1) % n) + n) % n];
        float hIn = Mathf.Atan2((P - a).x, (P - a).y) * Mathf.Rad2Deg;
        float hOut = Mathf.Atan2((b - P).x, (b - P).y) * Mathf.Rad2Deg;
        return Mathf.DeltaAngle(hIn, hOut);
    }

    /// <summary>**隅部材の両腕の外面を、平行移動だけで <paramref name="target"/>(区画線から外向きへ。犬走りなら −0.30)へ据える。**
    /// 折れ点 = 辺 <paramref name="e1"/> の終点 = 辺 e1+1 の始点。<b>yaw は動かさない</b>(折れ角は部材が持つ)。
    ///
    /// <para>⭐ 腕ごとに頂点を選り分けてから測る。⛔ 全頂点の最大投影を「その辺の外面」にしない — 入隅では
    /// もう一方の腕がその向きへ余計に張り出して別の腕の面を拾い、隅が 5.9m 動いた(松平 2026-09-07)。
    /// 辺 e の腕に属する頂点 = 折れ点から見てその腕の外向きにあり、かつ相手の腕の中心線からのはみ出しが
    /// 壁厚の 1.5 倍以内の物。選り分けは動かす前の位置で**一度だけ**行う(動かした後で選び直すと発散する)。</para>
    ///
    /// <para>折れ角が 30° 以上(|det| ≥ 0.5)なら 2 元 1 次方程式が exact に解ける。それより浅い隅では解が走り方向へ
    /// 暴れるので、<b>平均の法線方向</b>へだけ動かす(部材の折れ角は辺に合わせて焼いてあるので両腕の残差は小さい)。
    /// 両腕の残差が 0.05m を超えるときは note に出す。</para>
    /// 返り値 = 動かした量(xz)。測れなければ false(note に理由)。</summary>
    public static bool KadoFace(Transform kc, Vector2[] poly, int e1, Func<int, Vector2> outNormal,
                                float target, float wallT, out Vector2 moved, out string note)
    {
        moved = Vector2.zero; note = null;
        int n = poly.Length, e2 = (e1 + 1) % n;
        Vector2 a1 = poly[e1 % n], P = poly[e2 % n], a3 = poly[(e2 + 1) % n];
        Vector2 t1 = (a1 - P).normalized, t2 = (a3 - P).normalized;
        Vector2 kn1 = outNormal(e1), kn2 = outNormal(e2);
        var body = Body(kc, 999999);        // 隅は全頂点(間引かない — 留め継ぎの先端の疎な頂点が落ちる)
        if (body.Count == 0) { note = "メッシュ無し"; return false; }
        float ky0 = 1e9f, ky1 = -1e9f;
        foreach (var v in body) { if (v.y < ky0) ky0 = v.y; if (v.y > ky1) ky1 = v.y; }
        float lo = ky0 + (ky1 - ky0) * 0.15f, hi = ky0 + (ky1 - ky0) * 0.80f;     // 壁体の帯(屋根を除く)
        float cosT = Vector2.Dot(t1, t2), armThresh = wallT * 1.5f;
        float best1 = float.MinValue, best2 = float.MinValue;
        foreach (var w in body)
        {
            if (w.y < lo || w.y > hi) continue;
            Vector2 rel = new Vector2(w.x, w.z) - P;
            float d1 = Vector2.Dot(rel, t1), d2 = Vector2.Dot(rel, t2);
            if (d1 >= 0f && Mathf.Abs(d2 - d1 * cosT) <= armThresh) best1 = Mathf.Max(best1, Vector2.Dot(rel, kn1));
            if (d2 >= 0f && Mathf.Abs(d1 - d2 * cosT) <= armThresh) best2 = Mathf.Max(best2, Vector2.Dot(rel, kn2));
        }
        if (best1 == float.MinValue || best2 == float.MinValue) { note = "両辺の壁体を判別できず"; return false; }
        float r1 = target - best1, r2 = target - best2;
        float det = kn1.x * kn2.y - kn1.y * kn2.x;
        if (Mathf.Abs(det) >= ExactSolveDet)
        {
            moved = new Vector2((r1 * kn2.y - r2 * kn1.y) / det, (kn1.x * r2 - kn2.x * r1) / det);
        }
        else
        {
            // 折れ角が浅い(30° 未満)隅は、走り方向の解が 1/det に増幅されて暴れる(岡部 P3・折れ角 14.45° で
            // 実測 7.79m 動いた)。留め継ぎの位置は壁に沿って滑らせても面は変わらないので、動かすのは**面の法線方向だけ**。
            Vector2 km = (kn1 + kn2).normalized;
            float d = 0.5f * (r1 / Mathf.Max(0.5f, Vector2.Dot(km, kn1)) + r2 / Mathf.Max(0.5f, Vector2.Dot(km, kn2)));
            moved = km * d;
            if (Mathf.Abs(r1 - r2) > 0.05f) note = "折れ角が浅い(det=" + det.ToString("F3") + ")・両腕の面が " + Mathf.Abs(r1 - r2).ToString("F2") + "m 食い違う";
        }
        if (moved.sqrMagnitude > 0.02f * 0.02f) kc.position += new Vector3(moved.x, 0f, moved.y);
        return true;
    }

    /// <summary>**据えた隅部材の「腕」が、接する二辺の s をどこまで覆っているかを実メッシュで測る。**
    /// <paramref name="h"/> = 辺 e1(隅は s=L の側)で腕が覆う下限 / <paramref name="l"/> = 辺 e1+1(隅は s=0 の側)で腕が覆う上限。
    ///
    /// <para>⛔ 指図の `armRaw` を信じない — 部材が持つ寸法で、指図に写した瞬間に食い違う
    /// (松平 2026-09-20: 宣言 4.134m に対し実部材は 3.30m で、差がそのまま外周の口になった)。
    /// 測る帯は**軒下の壁体**(隅の座 +0.6〜1.4m)。⛔ 全メッシュで測ると軒・反り・鬼が先に届いて腕が 0.9m 長く出る。
    /// 辺の壁の帯(線の外 +0.40 〜 線の内 −(|target|+壁厚+0.40))に入る頂点だけがその辺の腕の壁。
    /// ⚠ 呼ぶのは <see cref="KadoFace"/> の**後**(面を寄せてから測る)。</para></summary>
    public static bool KadoArm(Transform kc, Vector2[] poly, int e1, Func<int, Vector2> outNormal,
                               float target, float wallT, float seatDrop, out float h, out float l)
    {
        h = l = 0f;
        int n = poly.Length, e2 = (e1 + 1) % n;
        var body = Body(kc, 999999);
        if (body.Count == 0) return false;
        float y0 = 1e9f; foreach (var v in body) if (v.y < y0) y0 = v.y;
        float seat = y0 + seatDrop;                     // 隅は seat − seatDrop に据える(直線材と同じ沈め)
        float bLo = seat + 0.6f, bHi = seat + 1.4f;
        float tHi = 0.40f, tLo = -(Mathf.Abs(target) + wallT + 0.40f);
        Func<int, float[]> reach = e =>
        {
            Vector2 apex = poly[e % n];
            Vector2 u = (poly[(e + 1) % n] - apex).normalized, nn = outNormal(e);
            float mn = float.MaxValue, mx = float.MinValue;
            foreach (var w in body)
            {
                if (w.y < bLo || w.y > bHi) continue;
                float t = (w.x - apex.x) * nn.x + (w.z - apex.y) * nn.y;
                if (t < tLo || t > tHi) continue;
                float s = (w.x - apex.x) * u.x + (w.z - apex.y) * u.y;
                if (s < mn) mn = s; if (s > mx) mx = s;
            }
            return mn == float.MaxValue ? null : new float[] { mn, mx };
        };
        var r1 = reach(e1); var r2 = reach(e2);
        if (r1 == null || r2 == null) return false;
        h = r1[0]; l = r2[1];
        return true;
    }

    /// <summary>**石垣の run の出隅へ隅の駒を据える**(2026-09-25・EDO-0430)。二本の run
    /// (<paramref name="runA"/> / <paramref name="runB"/> = 並べた直線材 `Castle Wall` 型の駒)が一点で折れて外へ凸に出る所に、
    /// 留め継ぎの隅の駒(<paramref name="pathOf"/>(deg, h) — 例 `EdoAssets.Own.IshigakiKado`)を**両脇の直線材の実メッシュから測って**据え、
    /// 腕が兼ねる端の 1 枚ずつを外す。<paramref name="nA"/>/<paramref name="nB"/> は各 run の外向き(見え面の側)の水平の単位ベクトル
    /// (向きだけ。位置は測る)。
    ///
    /// <para>測るもの: ① 各 run の端の駒の**控え(鉛直な背)の線** = 外向きへの射影の最小 — 二本の交点が隅の据え点
    /// ② **天端** = 両方の駒の最上点(食い違いは ⛔) ③ 据えた後、各腕の**天端の帯の見え面**が直線材の見え面と同じ線か・
    /// 天端が揃うか・腕の先が次の駒へ届くか(隙・めり込み)。部材の約束(`build_kado.py`): 腕は局所 −Z(見え面 −X)と
    /// +X 側(見え面 +Z)・据え点は内面の線の折れ点・y = 天端 − h。yaw は −X が片方の外向きに一致する解のうち、もう一方の
    /// 腕の見え面が他方の外向きに最も近い物。</para>
    ///
    /// <para>硬い条件(許容0 = 退ける): 天端の食い違い・見え面の食い違い・腕の先の隙が <paramref name="tol"/> を超えたら
    /// **建てずに直線材を残す**(note に ⛔)。丈 h は足元の地表(<paramref name="groundAt"/>)が天端 − h より上に来る
    /// 最小の焼いてある丈(4.0〜8.0 を 0.5 刻みで探す)。焼いていなければ ⚠ を返し建てない。</para>
    /// 当たる先: 石垣の run が凸に折れる所すべて(山王 回廊の基壇・御供所の郭・前庭の土留め、各邸の外周石垣の隅)。</summary>
    public static GameObject PlaceRunKado(IList<GameObject> runA, Vector2 nA, IList<GameObject> runB, Vector2 nB,
                                          Func<float, float, string> pathOf, Func<float, float, float> groundAt,
                                          Transform parent, string name, float tol, out string note, bool? convex = null)
    {
        note = null;
        // 見え面の側は法の出で測る(渡された向きは軸としてだけ使う): 下の帯が上の帯より前へ出る側が見え面
        nA = FaceSide(runA, nA.normalized); nB = FaceSide(runB, nB.normalized);
        float deg = Vector2.Angle(nA, nB);
        if (deg < 20f) { note = "折れが浅い(" + deg.ToString("F1") + "°)— 隅の駒は要らない"; return null; }
        // ① 各 run の控えの線(外向きへの射影の最小)と天端
        Func<IList<GameObject>, Vector2, float[]> back = (run, n) =>
        {
            float c = float.MaxValue, top = float.MinValue;
            foreach (var g in run) { if (g == null) continue;
                foreach (var v in Body(g.transform, 999999)) { c = Mathf.Min(c, v.x * n.x + v.z * n.y); top = Mathf.Max(top, v.y); } }
            return new float[] { c, top };
        };
        var bA = back(runA, nA); var bB = back(runB, nB);
        if (Mathf.Abs(bA[1] - bB[1]) > tol) { note = "⛔ 両脇の天端が " + Mathf.Abs(bA[1] - bB[1]).ToString("F3") + "m 食い違う — 建てない"; return null; }
        float crest = Mathf.Max(bA[1], bB[1]);
        float det = nA.x * nB.y - nA.y * nB.x;
        Vector2 P = new Vector2((bA[0] * nB.y - bB[0] * nA.y) / det, (nA.x * bB[0] - nB.x * bA[0]) / det);
        // 凸(出隅)か: 相手の run の駒は自分の外向きの内側に在る
        Func<IList<GameObject>, Vector2> cen = run => { Vector2 s = Vector2.zero; int k = 0; foreach (var g in run) if (g != null) { var b = RB(g); s += new Vector2(b.center.x, b.center.z); k++; } return k > 0 ? s / k : P; };
        //   ⭐ 呼び手が区間の走りから凹凸を知っていればそれを採る(短い区間の駒は隅の外まで張り出し、芯で測ると入隅と誤る ── 2026-09-25 山王 本殿の西の南西の隅 1.82m の区間)
        if (convex.HasValue ? !convex.Value : (Vector2.Dot(cen(runB) - P, nA) > 0f || Vector2.Dot(cen(runA) - P, nB) > 0f)) { note = "入隅 — 出隅の駒は据えない"; return null; }
        // yaw: 局所 −X → (−cosψ, sinψ) を片方の外向きへ。局所 +Z → (sinψ, cosψ) がもう一方へ最も近い方
        float psiA = Mathf.Atan2(nA.y, -nA.x) * Mathf.Rad2Deg, psiB = Mathf.Atan2(nB.y, -nB.x) * Mathf.Rad2Deg;
        Func<float, Vector2> zdir = p => new Vector2(Mathf.Sin(p * Mathf.Deg2Rad), Mathf.Cos(p * Mathf.Deg2Rad));
        bool xIsA = Vector2.Dot(zdir(psiA), nB) >= Vector2.Dot(zdir(psiB), nA);
        float psi = xIsA ? psiA : psiB;
        // 腕の走り(隅から離れる向き)
        Vector2 armX = -zdir(psi);                          // 局所 −Z の腕(見え面 −X)
        Vector2 armZ = new Vector2(Mathf.Cos(psi * Mathf.Deg2Rad), -Mathf.Sin(psi * Mathf.Deg2Rad));   // 局所 +X の腕(見え面 +Z)
        var runX = xIsA ? runA : runB; var runZ = xIsA ? runB : runA;
        Vector2 nX = xIsA ? nA : nB, nZ = xIsA ? nB : nA;
        // 隅の見え面: 隅の外(対角 1.5m)の地表が天端 − 0.5 より高ければ、隅は土に隠れて口は見えない ⇒ 据えない
        //   (据えると 5m の駒の天端を土が覆い、天端の埋没を増やす ── 2026-09-25 御供所の郭 N×E・社殿の腰石垣で実測 −0.15m)
        {
            Vector2 dq = P + (nX + nZ).normalized * 2.12f; float gd = groundAt(dq.x, dq.y);
            if (!float.IsNaN(gd) && crest - gd < 0.5f) { note = "隅は土に隠れる(隅の外の地表 = 天端 " + (gd - crest).ToString("+0.00;-0.00") + "m)— 据えない"; return null; }
        }
        // 丈: 両脇の直線材の底より浅くしない + 隅の据え点(両腕の控えの線の上)の地表より下まで届く
        //   ⛔ 隅の外の法の足先の地表では決めない ── 直線材も同じ所で浮き、そこは皮(縁の底へ寄せる)が受ける
        float gMin = float.MaxValue;
        foreach (var run in new IList<GameObject>[] { runA, runB })
            foreach (var g in run) if (g != null) foreach (var v in Body(g.transform, 999999)) gMin = Mathf.Min(gMin, v.y);
        float nbH = crest - gMin;                                    // 両脇の直線材の丈(実メッシュ)
        for (float u = 0f; u <= 2.01f; u += 0.25f)
            foreach (var q in new Vector2[] { P + armX * u, P + armZ * u })
            { float g = groundAt(q.x, q.y); if (!float.IsNaN(g)) gMin = Mathf.Min(gMin, g); }
        float degR = Mathf.Round(deg);
        string path = null; float h = 0f;
        // ⭐ 両脇の直線材と同じ丈の隅の駒が焼けていればそれを採る(2026-09-25・天端と足元が両脇と揃う)。
        //   腕の下の地表が両脇の底より低くても、そこは両脇の直線材の端と同じ納め(皮が受ける)。
        {
            float hp = Mathf.Round(nbH * 2f) / 2f; string pp = pathOf(degR, hp);
            if (Mathf.Abs(hp - nbH) < 0.05f && pp != null && System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, pp)))
            { path = pp; h = hp; }
        }
        if (path == null)
        for (float hh = 4.0f; hh <= 8.01f; hh += 0.5f)
        {
            if (gMin != float.MaxValue && crest - hh > gMin) continue;
            string pp = pathOf(degR, hh);
            if (System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, pp))) { path = pp; h = hh; break; }
        }
        if (path == null) { note = "⚠ 隅の駒が焼いていない(折れ " + degR + "°・要る丈 ≥ " + (crest - gMin).ToString("F2") + "m)— 建てない"; return null; }
        // 腕が兼ねる端の駒 = 隅に最も近い駒
        Func<IList<GameObject>, Vector2, GameObject> endOf = (run, arm) =>
        { GameObject best = null; float bd = float.MaxValue;
          foreach (var g in run) { if (g == null) continue; var b = RB(g); float d = Vector2.Dot(new Vector2(b.center.x, b.center.z) - P, arm); if (d < bd) { bd = d; best = g; } }
          return best; };
        var endX = endOf(runX, armX); var endZ = endOf(runZ, armZ);
        var kc = Place(path, new Vector3(P.x, crest - h, P.y), psi, Vector3.one, parent, name);
        // ③ 測る: 天端の帯(天端 −0.15 以上)の見え面と腕の先
        float kTop = float.MinValue; foreach (var v in Body(kc.transform, 999999)) kTop = Mathf.Max(kTop, v.y);
        Func<GameObject, Vector2, Vector2, float[]> crestFace = (g, n, arm) =>
        {   // [見え面の外向き射影の最大, 腕の走りの最小, 最大](天端の帯)
            float f = float.MinValue, s0 = float.MaxValue, s1 = float.MinValue;
            foreach (var v in Body(g.transform, 999999))
            {   if (v.y < crest - 0.15f) continue;
                Vector2 r = new Vector2(v.x, v.z) - P; float s = Vector2.Dot(r, arm);
                if (g == kc && s < 0.3f) continue;          // 隅の駒は自分の腕の側だけ
                f = Mathf.Max(f, Vector2.Dot(r, n)); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); }
            return new float[] { f, s0, s1 };
        };
        var sb = new System.Text.StringBuilder(); bool bad = Mathf.Abs(kTop - crest) > tol;
        sb.Append("天端の差 " + (kTop - crest).ToString("+0.000;-0.000"));
        var keep = new bool[2];
        var sides = new object[][] { new object[] { runX, nX, armX, endX, "−Z の腕" }, new object[] { runZ, nZ, armZ, endZ, "+X の腕" } };
        for (int si = 0; si < 2; si++)
        {
            var side = sides[si];
            var run = (IList<GameObject>)side[0]; var n = (Vector2)side[1]; var arm = (Vector2)side[2]; var end = (GameObject)side[3];
            var kf = crestFace(kc, n, arm);
            // 腕が端の駒を兼ねられるか: 端を外して次の駒が腕の先へ届くなら外す。届かなければ端の駒を残す(重ねは直線材どうしと同じ納め)
            for (int pass = 0; pass < 2; pass++)
            {
                float next = float.MaxValue, face = float.MinValue;
                foreach (var g in run) { if (g == null || (pass == 0 && g == end)) continue; var cf = crestFace(g, n, arm); if (cf[1] < next) { next = cf[1]; face = cf[0]; } }
                float dFace = face == float.MinValue ? 0f : kf[0] - face;       // + = 隅の駒が前へ出る(めり込み側の段差)
                float gap = next == float.MaxValue ? 0f : next - kf[2];          // + = 腕の先と次の駒の間の口
                if (pass == 0 && gap > tol) { keep[si] = true; continue; }
                sb.Append(" / " + side[4] + ": 見え面の差 " + dFace.ToString("+0.000;-0.000") + "・腕の先の口 " + gap.ToString("+0.000;-0.000") + (keep[si] ? "(端の駒を残した)" : ""));
                if (Mathf.Abs(dFace) > tol || gap > tol) bad = true;
                break;
            }
        }
        if (bad)
        {
            UnityEngine.Object.DestroyImmediate(kc);
            note = "⛔ 隅の駒が両脇と合わない — 建てない(" + sb + ")"; return null;
        }
        if (endX != null && !keep[0]) { runX.Remove(endX); UnityEngine.Object.DestroyImmediate(endX); }
        if (endZ != null && endZ != endX && !keep[1]) { runZ.Remove(endZ); UnityEngine.Object.DestroyImmediate(endZ); }
        note = System.IO.Path.GetFileNameWithoutExtension(path) + " を据えた(yaw " + psi.ToString("F2") + "・丈 " + h.ToString("F1") + "・足元の最低 " + gMin.ToString("F2") + ")/ " + sb;
        return kc;
    }

    /// <summary>石垣の run の区間の端ひとつ。<c>key</c> = 区間の駒の並びの名(<c>run#区間</c>)、<c>node</c> = run の折れ線の節点の番号、
    /// <c>outw</c> = 見え面の外向き、<c>away</c> = 端から区間の奥へ向かう走り。</summary>
    public struct RunEnd { public string key; public string run; public int node; public Vector2 p; public Vector2 outw; public Vector2 away; }

    /// <summary>**石垣の run の折れ目すべてに出隅の隅の駒を据える**(<see cref="PlaceRunKado"/> を区間の端の組ごとに呼ぶ)。
    /// 別々の run の端が重なる所だけでなく、**一本の折れ線の途中の角**(区間どうしの継ぎ目)も同じに扱う。
    ///
    /// <para>⭐ **継ぎ目が一直線の所には隅を置かない** ── 同じ点に集まる端のうち二つが一直線に続く(走りが逆向き・見え面が同じ向き)
    /// なら、そこは直線で継ぐ所(天端の段の境・別の run への継ぎ足し)。第三の run がそこへ突き当たる(T 字)ときも、隅の駒の天端が
    /// 一直線の相方の天端より 0.5m 以上高くない限り(= 隅の見え面が段として出ない限り)据えない
    /// ── 据えると継ぎ目の上に隅の駒が立ち、一直線の見え面に角が出る(山王 透塀の土台 TW_Koshi_W × _SW の隅が
    /// 本殿の西の土留め TW_Nozura_ShadenW と _SW の一直線の継ぎ目の上に来た・2026-09-25)。</para>
    /// <para>硬い条件(許容0)は <see cref="PlaceRunKado"/> のまま(合わなければ建てずに直線材を残す)。
    /// 当たる先: 石垣の run が凸に折れる所すべて ── 山王 土留め・透塀の土台・回廊の基壇・御供所の郭。各邸の外周石垣の隅も同じ口で呼べる。</para></summary>
    public static int PlaceRunCorners(IList<RunEnd> ends, IDictionary<string, List<GameObject>> pieces,
                                      Func<float, float, string> pathOf, Func<float, float, float> groundAt,
                                      Transform parent, float tol, System.Text.StringBuilder log, List<GameObject> made)
    {
        int kn = 0; var used = new bool[ends.Count];
        for (int i = 0; i < ends.Count; i++)
        {
            if (used[i]) continue;
            var cl = new List<RunEnd>();
            for (int j = i; j < ends.Count; j++)
                if (!used[j] && Vector2.Distance(ends[i].p, ends[j].p) < 0.05f) { used[j] = true; cl.Add(ends[j]); }
            if (cl.Count < 2) continue;
            // ① 一直線の継ぎ目か(走りが逆向き・見え面が同じ向きの二本)
            int sa = -1, sbI = -1;
            for (int a = 0; a < cl.Count && sa < 0; a++)
                for (int b = a + 1; b < cl.Count; b++)
                    if (cl[a].key != cl[b].key && Vector2.Dot(cl[a].away, cl[b].away) < -0.985f && Vector2.Dot(cl[a].outw, cl[b].outw) > 0.9f)
                    { sa = a; sbI = b; break; }
            Func<string, float> crestNear = key =>
            {   List<GameObject> r; float t = float.MinValue; if (!pieces.TryGetValue(key, out r)) return t;
                foreach (var g in r) if (g != null) { var bb = RB(g); if (Vector2.Distance(new Vector2(bb.center.x, bb.center.z), ends[i].p) < 6f) t = Mathf.Max(t, bb.max.y); }
                return t; };
            if (sa >= 0 && cl.Count == 2)
            {
                if (cl[sa].run != cl[sbI].run) log?.AppendLine("  継ぎ目が一直線(" + cl[sa].key + " → " + cl[sbI].key + ")── 隅を置かず直線で継ぐ");
                continue;
            }
            // ② 組ごとに出隅を試す
            bool loggedT = false;
            for (int a = 0; a < cl.Count; a++)
                for (int b = a + 1; b < cl.Count; b++)
                {
                    var ea = cl[a]; var eb = cl[b];
                    if (ea.key == eb.key) continue;
                    if (sa >= 0)
                    {   // 一直線の継ぎ目に第三の run が突き当たる(T 字): 隅の駒は継ぎ目の上に立つ。
                        //   ⇒ 一直線の二本の間には置かない。第三の run × 一直線の片方(B)の隅は、B の天端がもう片方(A)の天端より
                        //     0.5m 以上高い(隅の見え面が A の天端の上に段として出る)ときだけ試す ── 0.5 は PlaceRunKado の「隅は土に隠れる」と同じ。
                        if ((a == sa && b == sbI) || (a == sbI && b == sa)) continue;
                        int bIdx = (a == sa || a == sbI) ? a : ((b == sa || b == sbI) ? b : -1);
                        if (bIdx < 0) continue;
                        int aIdx = bIdx == sa ? sbI : sa;
                        float step = crestNear(cl[bIdx].key) - crestNear(cl[aIdx].key);
                        if (step < 0.5f)
                        {
                            if (!loggedT) log?.AppendLine("  継ぎ目が一直線(" + cl[aIdx].key + " → " + cl[bIdx].key + "・" + cl[a + b - bIdx].key + " が突き当たる・天端の段 " +
                                            step.ToString("+0.00;-0.00") + "m < 0.5)── 隅を置かず直線で継ぐ");
                            loggedT = true; continue;
                        }
                    }
                    List<GameObject> ra, rb;
                    if (!pieces.TryGetValue(ea.key, out ra) || !pieces.TryGetValue(eb.key, out rb) || ra.Count == 0 || rb.Count == 0) continue;
                    Vector2 P = ea.p;
                    var na = ra.FindAll(g => g != null && Vector2.Distance(new Vector2(RB(g).center.x, RB(g).center.z), P) < 6f);
                    var nb = rb.FindAll(g => g != null && Vector2.Distance(new Vector2(RB(g).center.x, RB(g).center.z), P) < 6f);
                    if (na.Count == 0 || nb.Count == 0) continue;
                    string kname = ea.run == eb.run ? ea.run + "_kado" + Mathf.Max(ea.node, eb.node)
                                                    : ea.run + "_x_" + eb.run.Substring(eb.run.LastIndexOf('_') + 1) + "_kado";
                    string note;
                    // 一本の折れ線の途中の角は、凹凸を区間の走りで決める: 出隅 = 相手の区間が自分の見え面の裏側へ延びる(両方とも)。
                    //   ⚠ 別々の run の間は従来どおり駒の芯で測る(run ごとの見え面は低い側を別々に測っていて、走りとの組が揃う保証が無い)
                    bool? cvx = null;
                    if (ea.run == eb.run) cvx = Vector2.Dot(eb.away, ea.outw) < 0f && Vector2.Dot(ea.away, eb.outw) < 0f;
                    var kc = PlaceRunKado(na, ea.outw, nb, eb.outw, pathOf, groundAt, parent, kname, tol, out note, cvx);
                    if (note != null && note.StartsWith("入隅") && ea.run != eb.run) continue;
                    if (kc != null)
                    {
                        kn++; made?.Add(kc);
                        ra.RemoveAll(g => g == null); rb.RemoveAll(g => g == null);
                    }
                    log?.AppendLine("  出隅 " + ea.key + " × " + eb.key + ": " + note);
                }
        }
        return kn;
    }

    /// <summary>石垣の駒の並び <paramref name="run"/> の見え面の外向きを、軸 <paramref name="axis"/> の ± のうち
    /// **下の帯(下 25%)が上の帯(上 15%)より前へ出る側**として測る(法の付いた面が見え面・鉛直な背は出ない)。</summary>
    public static Vector2 FaceSide(IList<GameObject> run, Vector2 axis)
    {
        float y0 = float.MaxValue, y1 = float.MinValue; var vs = new List<Vector3>();
        foreach (var g in run) if (g != null) vs.AddRange(Body(g.transform, 999999));
        foreach (var v in vs) { y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); }
        float lo = y0 + (y1 - y0) * 0.25f, hi = y1 - (y1 - y0) * 0.15f;
        float pb = float.MinValue, pt = float.MinValue, mb = float.MinValue, mt = float.MinValue;
        foreach (var v in vs)
        {
            float d = v.x * axis.x + v.z * axis.y;
            if (v.y <= lo) { pb = Mathf.Max(pb, d); mb = Mathf.Max(mb, -d); }
            if (v.y >= hi) { pt = Mathf.Max(pt, d); mt = Mathf.Max(mt, -d); }
        }
        return (pb - pt) >= (mb - mt) ? axis : -axis;
    }


    /// <summary>**石垣の駒の見え面(法の付いた面)が低い側を向いているかを測る**(2026-09-25・EDO-0430)。
    /// 見え面の向きは <see cref="FaceSide"/>(下の帯が前へ出る側)、地盤は <paramref name="groundAt"/>(描かれた地表)を
    /// 見え面の足の 0.8m 前と控えの 0.8m 後ろで取る。返り値 = 前 − 後ろ[m](+ なら見え面が高い側を向く = 裏返り)。
    /// 当たる先: 土留め・郭・腰石垣・基壇に `Castle Wall` 型の駒を並べる全ての run(山王 Stage3、各邸の外周石垣)。</summary>
    public static float WallFaceRise(GameObject piece, Func<float, float, float> groundAt)
    {
        var tr = piece.transform;
        Vector2 f = WallFace(piece);
        var vs = Body(tr, 999999); if (vs.Count == 0) return float.NaN;
        float fmax = float.MinValue, bmin = float.MaxValue; Vector2 cen = Vector2.zero;
        foreach (var v in vs) { float d = v.x * f.x + v.z * f.y; fmax = Mathf.Max(fmax, d); bmin = Mathf.Min(bmin, d); cen += new Vector2(v.x, v.z); }
        cen /= vs.Count; float cd = cen.x * f.x + cen.y * f.y;
        Vector2 pf = cen + f * (fmax - cd + 0.8f), pb = cen + f * (bmin - cd - 0.8f);
        return groundAt(pf.x, pf.y) - groundAt(pb.x, pb.y);
    }
    /// <summary>**石垣の駒の見え面の向き**(世界 XZ の単位)。見え面の軸は部材ごとに違う(Castle Wall は局所 ±X・野面の駒は局所 ±Z)
    /// ⇒ 両軸で法の出(<see cref="BatterOut"/>)を測り、出の大きい軸の <see cref="FaceSide"/> を採る(2026-09-25・EDO-0430)。
    /// 当たる先: 土留めの見え面の向き・天端の帯の数え(TuckUnderCrest の faces)を要る全て。</summary>
    public static Vector2 WallFace(GameObject piece)
    {
        // ⭐ 見え面は駒の**薄い向き**(走りを横切る向き)にある。法の出が両軸で出るとき(打ち切りの駒は走りの向きに天端が下がり、
        //   下の帯が走りの向きへ張り出して「法の出」に化ける ── 2026-09-25 EDO-0430 野面の打ち切り W_017f)は薄い軸を採る。
        var tr = piece.transform; var vs = Body(tr, 999999);
        Vector2 f = Vector2.zero; float bestOut = float.MinValue; Vector2 thinF = Vector2.zero; float thinOut = float.NaN, thinW = float.MaxValue;
        foreach (var a3 in new[] { tr.right, tr.forward })
        {
            var ax = new Vector2(a3.x, a3.z).normalized; var fs = FaceSide(new List<GameObject> { piece }, ax);
            float o = BatterOut(piece, fs); if (o > bestOut) { bestOut = o; f = fs; }
            float lo = float.MaxValue, hi = float.MinValue; foreach (var v in vs) { float d = v.x * ax.x + v.z * ax.y; lo = Mathf.Min(lo, d); hi = Mathf.Max(hi, d); }
            if (hi - lo < thinW) { thinW = hi - lo; thinF = fs; thinOut = o; }
        }
        if (!float.IsNaN(thinOut) && thinOut > 0.05f) return thinF;
        return f;
    }
    /// <summary>出隅の駒の二つの見え面(局所の二軸の <see cref="FaceSide"/>)。</summary>
    public static void KadoFaces(GameObject piece, out Vector2 f1, out Vector2 f2)
    {
        var tr = piece.transform;
        f1 = FaceSide(new List<GameObject> { piece }, new Vector2(tr.right.x, tr.right.z).normalized);
        f2 = FaceSide(new List<GameObject> { piece }, new Vector2(tr.forward.x, tr.forward.z).normalized);
    }
    /// <summary>**出隅の駒の見え面が低い側を向いているかを測る**(2026-09-25・EDO-0430)。隅の駒は見え面が二つ(局所の二軸・
    /// 各々 <see cref="FaceSide"/>)で、一軸の前後で測る <see cref="WallFaceRise"/> は後ろの点が隣の腕の前(低い面)に落ちて
    /// 「裏返り」と嘘を出す(野面の隅 kado2 で +0.25)。⇒ 後ろ = 二つの見え面の**対角の内**(両面の合成の逆向き)の 0.8m 先、
    /// 前 = 各々の見え面の 0.8m 先。返り値 = 前の高い方 − 後ろ[m](+ なら裏返り)。
    /// 当たる先: 野面の隅の駒(`SannoNozuraKado`)・城の石垣の出隅(`Ishigaki_Kado_*`)。</summary>
    public static float WallFaceRiseKado(GameObject piece, Func<float, float, float> groundAt)
    {
        var tr = piece.transform; var vs = Body(tr, 999999); if (vs.Count == 0) return float.NaN;
        Vector2 f1, f2; KadoFaces(piece, out f1, out f2);
        Vector2 cen = Vector2.zero; foreach (var v in vs) cen += new Vector2(v.x, v.z); cen /= vs.Count;
        Func<Vector2, float> ext = d => { float m = float.MinValue; foreach (var v in vs) m = Mathf.Max(m, Vector2.Dot(new Vector2(v.x, v.z) - cen, d)); return m; };
        Vector2 back = -(f1 + f2).normalized;
        Vector2 pb = cen + back * (ext(back) + 0.8f), p1 = cen + f1 * (ext(f1) + 0.8f), p2 = cen + f2 * (ext(f2) + 0.8f);
        return Mathf.Max(groundAt(p1.x, p1.y), groundAt(p2.x, p2.y)) - groundAt(pb.x, pb.y);
    }
    /// <summary>向き <paramref name="f"/> への法の出 = 下の帯(下 25%)の張り出し − 上の帯(上 15%)の張り出し[m]。</summary>
    static float BatterOut(GameObject piece, Vector2 f)
    {
        var vs = Body(piece.transform, 999999); float y0 = float.MaxValue, y1 = float.MinValue;
        foreach (var v in vs) { y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); }
        float lo = y0 + (y1 - y0) * 0.25f, hi = y1 - (y1 - y0) * 0.15f, pb = float.MinValue, pt = float.MinValue;
        foreach (var v in vs) { float d = v.x * f.x + v.z * f.y; if (v.y <= lo) pb = Mathf.Max(pb, d); if (v.y >= hi) pt = Mathf.Max(pt, d); }
        return pb - pt;
    }
    /// <summary>**線 a→b のどちら側が低いかを描かれた地表で測る**(2026-09-25・EDO-0430)。走りに沿って 1m おきに、
    /// 線の両側 <paramref name="probe"/> m の地表(<paramref name="groundAt"/>)を取り、差が <paramref name="eps"/> を超える点で
    /// 低い側に票を入れる。<paramref name="use"/>(走り s → 数えるか)で建つ区間だけに絞れる。返り値 = 低い側の単位法線
    /// (票が無ければ Vector2.zero ── 呼ぶ側が別の手掛かりで決める)。
    /// 当たる先: 土留め・郭・腰石垣・基壇の石垣の見え面の向き(山王 Stage3、各邸の外周石垣・護岸)。</summary>
    public static Vector2 LowSide(Vector2 a, Vector2 b, Func<float, float, float> groundAt, float probe, float eps,
                                  Func<float, bool> use, out int votes, out int against)
    {
        votes = against = 0;
        float len = Vector2.Distance(a, b); if (len < 1e-4f) return Vector2.zero;
        Vector2 dir = (b - a) / len, nrm = new Vector2(dir.y, -dir.x);
        int r = 0, l = 0;
        for (float s = Mathf.Min(0.5f, len * 0.5f); s <= len; s += 1f)
        {
            if (use != null && !use(s)) continue;
            Vector2 p = a + dir * s;
            float gR = groundAt(p.x + nrm.x * probe, p.y + nrm.y * probe), gL = groundAt(p.x - nrm.x * probe, p.y - nrm.y * probe);
            if (float.IsNaN(gR) || float.IsNaN(gL) || Mathf.Abs(gR - gL) <= eps) continue;
            if (gR < gL) r++; else l++;
        }
        if (r == 0 && l == 0) return Vector2.zero;
        votes = Mathf.Max(r, l); against = Mathf.Min(r, l);
        return r >= l ? nrm : -nrm;
    }

    /// <summary>**石垣の駒の見え面(法の面)を <paramref name="lowN"/> へ向け、天端の前の縁を線へ寄せる**(2026-09-25・EDO-0430)。
    /// ① 見え面は <see cref="FaceSide"/>(下の帯が前へ出る側)で測り、<paramref name="lowN"/> と逆なら駒の芯(実メッシュの外接箱の中心)
    /// で 180° 回す(走りの位置は動かない) ② 天端の帯(最上点 − <paramref name="band"/> 以上)の頂点の <paramref name="lowN"/> への射影の最大
    /// = 天端の前の縁を測り、線(<paramref name="lineA"/> を通り <paramref name="lowN"/> に直交)の上へ平行移動する。
    /// ⛔ 部材の基準点(ピボット)で線に合わせない ── 線は「面の縁」、触れているのは天端の前の縁。返り値 = 寄せた量[m](+ = 低い側へ)。
    /// 当たる先: Castle Wall 型の駒を並べる全ての土留め(山王 Stage3、各邸の外周石垣・護岸)。</summary>
    public static float FaceWallToLine(GameObject piece, Vector2 lowN, Vector2 lineA, float band = 0.15f)
    {
        var tr = piece.transform;
        var f = FaceSide(new List<GameObject> { piece }, lowN);
        if (Vector2.Dot(f, lowN) < 0f)
        {
            var c = RB(piece).center;
            tr.RotateAround(new Vector3(c.x, 0f, c.z), Vector3.up, 180f);
        }
        var vs = Body(tr, 999999); if (vs.Count == 0) return 0f;
        float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
        float edge = float.MinValue;
        foreach (var v in vs) if (v.y >= top - band) edge = Mathf.Max(edge, (v.x - lineA.x) * lowN.x + (v.z - lineA.y) * lowN.y);
        if (edge == float.MinValue) return 0f;
        tr.position -= new Vector3(lowN.x, 0f, lowN.y) * edge;
        return -edge;
    }
}
