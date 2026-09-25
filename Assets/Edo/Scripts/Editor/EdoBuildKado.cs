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
        // ⭐ 硬い条件(許容0 の埋没): 両方の見え面で天端が前の地表の下に来る隅の駒 = 全体が埋まる駒は置かない(joints[68]・2026-09-25)
        {
            float ex = CrestAboveGround(kc, nX, groundAt), ez = CrestAboveGround(kc, nZ, groundAt);
            if (!float.IsNaN(ex) && !float.IsNaN(ez) && ex <= 0f && ez <= 0f)
            {
                UnityEngine.Object.DestroyImmediate(kc);
                note = "⛔ 隅の駒の天端が両方の見え面の前の地表の下(" + ex.ToString("+0.00;-0.00") + " / " + ez.ToString("+0.00;-0.00") + "m)── 全体が埋まるので建てない";
                return null;
            }
        }
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
    /// <summary>**駒の天端が見え面の前の地表より上に出るか**(全体が地表の下に来る駒を見分ける・2026-09-25 EDO-0430 joints[68])。
    /// 駒の実メッシュを見え面の走り(<paramref name="outw"/> に直交)に 0.25m の帯へ割り、帯ごとに天端(最も高い頂点)と
    /// 天端の帯(天端 − <see cref="CREST_BAND"/> 以上)の前の縁を取り、前の縁の <paramref name="probe"/> 先の地表と比べる。
    /// 返り値 = 天端 − 地表 の最大[m](≤ 0 なら全ての帯で天端が地表の下 = **全体が埋まる駒**)。
    /// ⛔ 天端の真下の地表では測らない ── 2m 格子の節点が駒の外形の中に落ちると天端の側の高さを持ち、埋まっていない駒を埋まったと読む。
    /// 当たる先: 城の石垣の駒を並べる全ての run(山王 Stage3 の土留め・腰石垣・基壇・郭、隅の駒 <see cref="PlaceRunKado"/>)。</summary>
    public static float CrestAboveGround(GameObject piece, Vector2 outw, Func<float, float, float> groundAt, float probe = 0.3f)
    {
        var vs = Body(piece.transform, 999999); if (vs.Count == 0) return float.NaN;
        outw = outw.normalized; Vector2 run = new Vector2(-outw.y, outw.x);
        float s0 = float.MaxValue, s1 = float.MinValue;
        foreach (var v in vs) { float s = v.x * run.x + v.z * run.y; s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); }
        const float BIN = 0.25f; int nb = Mathf.Max(1, Mathf.CeilToInt((s1 - s0) / BIN));
        var top = new float[nb]; var front = new float[nb];
        for (int i = 0; i < nb; i++) { top[i] = float.MinValue; front[i] = float.MinValue; }
        foreach (var v in vs) { int k = Mathf.Clamp(Mathf.FloorToInt((v.x * run.x + v.z * run.y - s0) / BIN), 0, nb - 1); top[k] = Mathf.Max(top[k], v.y); }
        foreach (var v in vs)
        {
            int k = Mathf.Clamp(Mathf.FloorToInt((v.x * run.x + v.z * run.y - s0) / BIN), 0, nb - 1);
            if (v.y >= top[k] - CREST_BAND) front[k] = Mathf.Max(front[k], v.x * outw.x + v.z * outw.y);
        }
        float best = float.NegativeInfinity;
        for (int k = 0; k < nb; k++)
        {
            if (top[k] == float.MinValue) continue;
            float s = s0 + (k + 0.5f) * BIN; Vector2 q = run * s + outw * (front[k] + probe);
            float g = groundAt(q.x, q.y); if (float.IsNaN(g)) continue;
            best = Mathf.Max(best, top[k] - g);
        }
        return float.IsNegativeInfinity(best) ? float.NaN : best;
    }

    /// <summary>**駒の端の小口が地表より上に出るか**(run の端で埋まる駒を退けた後の検め・2026-09-25 EDO-0430 joints[67])。
    /// <paramref name="away"/> = 端から外(退けた駒の側)への走り。天端の帯の端の点の <paramref name="probe"/> 先の地表と、その点の天端を比べる。
    /// 返り値 = 天端 − 地表[m](> 0 なら小口の上が地表より上に出ている)。</summary>
    public static float EndAboveGround(GameObject piece, Vector2 away, Func<float, float, float> groundAt, float probe = 0.3f)
    {
        var vs = Body(piece.transform, 999999); if (vs.Count == 0) return float.NaN;
        away = away.normalized; float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
        float e = float.MinValue; foreach (var v in vs) if (v.y >= top - CREST_BAND) e = Mathf.Max(e, v.x * away.x + v.z * away.y);
        float best = float.NegativeInfinity;
        foreach (var v in vs)
        {
            if (v.y < top - CREST_BAND || v.x * away.x + v.z * away.y < e - 0.05f) continue;
            Vector2 q = new Vector2(v.x, v.z) + away * probe; float g = groundAt(q.x, q.y); if (float.IsNaN(g)) continue;
            best = Mathf.Max(best, v.y - g);
        }
        return float.IsNegativeInfinity(best) ? float.NaN : best;
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

    /// <summary>**一本の折れ線の土留めの「低い側の手」を区間の票の差で決める**(2026-09-25・EDO-0430)。
    /// 一本の run の見え面は走りに対して同じ手(右か左)にある ── 区間ごとに <see cref="LowSide"/> の票を取り、
    /// 右手の票の差の和を返す(+ = 右手が低い / − = 左手 / 0 = 決まらない)。短い区間(切り込みの返し 1.7m は票が 2 つ)で
    /// 票が割れたとき、同じ run の他の区間の手で決める。⛔ 割れた票を右手に倒さない(切り込みの東の返しが前庭の側を向いた)。
    /// 当たる先: 折れる土留め・郭の石垣・切り込みの返し(山王 Stage3、各邸の外周石垣・護岸)。</summary>
    public static int RunLowHand(IList<Vector2[]> segs, Func<float, float, float> groundAt, float probe, float eps,
                                 Func<int, float, bool> use)
    {
        int margin = 0;
        for (int i = 0; i < segs.Count; i++)
        {
            var sg = segs[i]; if (sg == null || sg.Length < 2) continue;
            float len = Vector2.Distance(sg[0], sg[1]); if (len < 1e-4f) continue;
            Vector2 dir = (sg[1] - sg[0]) / len, nrm = new Vector2(dir.y, -dir.x);
            int ii = i; int v, x;
            var low = LowSide(sg[0], sg[1], groundAt, probe, eps, use == null ? null : (Func<float, bool>)(s => use(ii, s)), out v, out x);
            if (low == Vector2.zero) continue;
            margin += (Vector2.Dot(low, nrm) > 0f ? 1 : -1) * (v - x);
        }
        return margin;
    }

    /// <summary>**折れ線 <paramref name="run"/> を線分 p0→p1 へ射影したとき、線分の上で重なる長さ**[m](2026-09-25・EDO-0430)。
    /// 石段の袖を**袖の run が走る段だけ**に据えるために使う(段の踏面の [s0, s1] と袖の走りの重なり)。
    /// ⛔ 脇の離れ(段の芯からの距離)だけで決めない ── 切り込みの中は返しの土留めが持つのに、段の全長へ袖を据えて返しと重ねた。
    /// 当たる先: 石段の袖(男坂・女坂・参道の階・郭の階・中門の内の階、各邸の石段)。</summary>
    public static float OverlapAlong(Vector2 p0, Vector2 p1, IList<Vector2> run)
    {
        float len = Vector2.Distance(p0, p1); if (len < 1e-5f || run == null || run.Count == 0) return 0f;
        Vector2 d = (p1 - p0) / len; float lo = float.MaxValue, hi = float.MinValue;
        foreach (var q in run) { float t = Vector2.Dot(q - p0, d); lo = Mathf.Min(lo, t); hi = Mathf.Max(hi, t); }
        return Mathf.Max(0f, Mathf.Min(len, hi) - Mathf.Max(0f, lo));
    }

    /// <summary>**駒より短い区間の、どちらの端が出隅か**(2026-09-25・EDO-0430)。区間 [a, b](見え面の外向き <paramref name="outw"/>)の
    /// 端ごとに、そこへ端を持つ別の区間(<paramref name="segs"/>・一直線に続く物は除く)の走りを見て、相手が自分の見え面の裏へ延びれば
    /// 出隅(凸)・見え面の前へ延びれば入隅(凹)。返り値 = +1(a だけが出隅)/ −1(b だけが出隅)/ 0(どちらでもない・両方)。
    /// ⭐ 短い区間は駒を出隅の側へ突き付け、余りを入隅の側(相手の見え面の裏 = 土の中)で重ねる(<see cref="FlushRunEnd"/>)。
    /// ⛔ 駒を区間の芯に置かない ── 1.7m の区間に 2.0m の駒を芯で置くと出隅で相手の天端の線より 0.15m 前へ出る
    /// (山王 前庭の切り込みの返し TW_Zentei_Kiri・2026-09-25)。
    /// 当たる先: 駒の長さより短い区間を持つ石垣の run すべて(山王 Stage3 の土留め・各邸の外周石垣の短い折れ)。</summary>
    public static int ShortSegConvexEnd(Vector2 a, Vector2 b, Vector2 outw, IList<Vector2[]> segs, float tol = 0.05f)
    {
        float len = Vector2.Distance(a, b); if (len < 1e-4f) return 0;
        Vector2 dir = (b - a) / len;
        Func<Vector2, int> kind = e =>
        {   // +1 = 出隅・−1 = 入隅・0 = 相手なし
            int k = 0;
            foreach (var o in segs)
            {
                if (o == null || o.Length < 2) continue;
                if ((Vector2.Distance(o[0], a) < tol && Vector2.Distance(o[1], b) < tol) ||
                    (Vector2.Distance(o[0], b) < tol && Vector2.Distance(o[1], a) < tol)) continue;      // 自分
                Vector2 far;
                if (Vector2.Distance(o[0], e) < tol) far = o[1]; else if (Vector2.Distance(o[1], e) < tol) far = o[0]; else continue;
                Vector2 d2 = far - e; if (d2.sqrMagnitude < 1e-6f) continue; d2.Normalize();
                if (Mathf.Abs(dir.x * d2.y - dir.y * d2.x) < 0.02f) continue;                            // 一直線に続く
                float s = Vector2.Dot(d2, outw);
                if (s < -0.1f) k = k < 0 ? 0 : 1; else if (s > 0.1f) k = k > 0 ? 0 : -1;
            }
            return k;
        };
        int ka = kind(a), kb = kind(b);
        if (ka > 0 && kb <= 0) return 1;
        if (kb > 0 && ka <= 0) return -1;
        return 0;
    }

    /// <summary>**駒の端を区間の端へ突き付ける**(<see cref="ShortSegConvexEnd"/> の相方・2026-09-25・EDO-0430)。
    /// 天端の帯(最上点 − <paramref name="band"/> 以上)の頂点の <paramref name="toward"/>(区間の内から端へ向かう走り)への射影の最大
    /// = 駒の端を実メッシュで測り、端の点 <paramref name="end"/>(相手の天端の前の縁の線の上)まで走りに沿って平行移動する。
    /// ⛔ ピボットで合わせない。返り値 = 動かした量[m](+ = 端の側へ)。</summary>
    public static float FlushRunEnd(GameObject piece, Vector2 end, Vector2 toward, float band = 0.15f)
    {
        var vs = Body(piece.transform, 999999); if (vs.Count == 0) return 0f;
        float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
        float m = float.MinValue;
        foreach (var v in vs) if (v.y >= top - band) m = Mathf.Max(m, (v.x - end.x) * toward.x + (v.z - end.y) * toward.y);
        if (m == float.MinValue) return 0f;
        piece.transform.position -= new Vector3(toward.x, 0f, toward.y) * m;
        return -m;
    }

    /// <summary>**基壇(天端が両側の地盤より上の石垣)の見え面の向きを、端で継ぐ壁の走りから決める**(2026-09-25・EDO-0430)。
    /// 基壇は両側が低いので地表では向きが決まらない。基壇を囲む壁は端どうしで継がれ、継いだ相手は**基壇の側へ**走る ──
    /// 見え面はその逆。<paramref name="others"/> = 基壇の壁の区間 [a, b](自分を含んでよい)。a・b から <paramref name="tol"/> 以内に
    /// 端がある区間の走り(継ぎ目から先へ)を足し、法線の逆側を返す(継ぐ相手が無い・打ち消し合うなら Vector2.zero)。
    /// ⛔ 同族の壁の芯(重心)から外へ、はしない ── 門で割れた基壇(山王の回廊は楼門で南北の二塊)では妻の石垣が門の側でなく
    /// 塊の内へ向いた。⛔ 地表で測らない ── 隣の壁の見え面の前の低い地盤が 2m 格子で基壇の内へ滲み、妻の石垣が裏返った。
    /// 当たる先: 回廊・楼門・社殿の基壇、門の両脇で切れる土台の石垣(山王 Stage3、各邸の基壇の石垣)。</summary>
    public static Vector2 BlockOutward(Vector2 a, Vector2 b, IList<Vector2[]> others, float tol = 0.05f)
    {
        float len = Vector2.Distance(a, b); if (len < 1e-4f) return Vector2.zero;
        Vector2 dir = (b - a) / len, nrm = new Vector2(dir.y, -dir.x), acc = Vector2.zero;
        foreach (var o in others)
        {
            if (o == null || o.Length < 2) continue;
            if ((Vector2.Distance(o[0], a) < tol && Vector2.Distance(o[1], b) < tol) ||
                (Vector2.Distance(o[0], b) < tol && Vector2.Distance(o[1], a) < tol)) continue;       // 自分
            float ol = Vector2.Distance(o[0], o[1]); if (ol < 1e-4f) continue;
            foreach (var e in new[] { a, b })
            {
                if (Vector2.Distance(o[0], e) < tol) acc += (o[1] - o[0]) / ol;
                else if (Vector2.Distance(o[1], e) < tol) acc += (o[0] - o[1]) / ol;
            }
        }
        float d = Vector2.Dot(acc, nrm);
        if (Mathf.Abs(d) < 1e-3f) return Vector2.zero;
        return d > 0f ? -nrm : nrm;
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

    // ============================================================ 一直線の継ぎ目・二段築の下段(2026-09-25・EDO-0430)
    /// <summary>**run の端 <paramref name="end"/> の先へ、別の区間(<paramref name="others"/> の [a, b])が一直線に続くか**を測る。
    /// <paramref name="away"/> = 端から run の外へ向かう走り。続く区間の片方の端が <paramref name="end"/> に重なり(<paramref name="tolM"/>)、
    /// もう片方の端が <paramref name="away"/> の向き(<paramref name="tolDeg"/> 以内)に在れば true。
    /// ⭐ 一直線に続く端は「隅へ続く端」ではなく「次のスパンへ続く端」── 端の型を c(隅部材が受ける・柱なし)で閉じると
    /// 隅部材の立たない継ぎ目に口が開く(山王 透塀の段の境 4 箇所に 0.18m の口・柱なし ── 段を無くした 2026-09-25 に一直線の継ぎ目になった)。
    /// 当たる先: run を区間に割って据える塀・透塀・柵の全て(山王 透塀 Sukibei_* 12 本。各邸の塀の run が一直線で継ぐ所)。</summary>
    public static bool ContinuesStraight(Vector2 end, Vector2 away, IList<Vector2[]> others, float tolM = 0.05f, float tolDeg = 1f)
    {
        foreach (var o in others)
        {
            if (o == null || o.Length < 2) continue;
            Vector2 near, far;
            if (Vector2.Distance(o[0], end) < tolM) { near = o[0]; far = o[o.Length - 1]; }
            else if (Vector2.Distance(o[o.Length - 1], end) < tolM) { near = o[o.Length - 1]; far = o[0]; }
            else continue;
            Vector2 d = far - near; if (d.sqrMagnitude < 1e-6f) continue;
            if (Vector2.Angle(d, away) <= tolDeg) return true;
        }
        return false;
    }

    // 下段の走りの標本 keep が、角の点 corner に当たる端(最初か最後)で残っているか
    static bool CornerKept(bool[] keep, TierUpper u, Vector2 corner)
    {
        // 端のどちらが角か: 上段の a に近い端 = 標本の 0
        bool atA = Vector2.Distance(u.a, corner) < Vector2.Distance(u.b, corner);
        return atA ? keep[0] : keep[keep.Length - 1];
    }
    /// <summary>二段築の上段の区間ひとつ ── 据わった上段の駒(<c>pieces</c>)と区間の線 [a, b](天端の前の縁の線)・見え面の外向き。</summary>
    public struct TierUpper { public string run; public Vector2 a, b, outw; public List<GameObject> pieces; }

    /// <summary>**石垣の駒の控え** = 天端の前の縁(天端の帯 <paramref name="band"/> の外向きへの射影の最大)− 背(全頂点の射影の最小)[m]。
    /// ⛔ 定数で持たない(部材を替えた瞬間に段の取り合いが破れる)。</summary>
    public static float CrestToBack(GameObject piece, Vector2 outw, float band = 0.15f)
    {
        var vs = Body(piece.transform, 999999); if (vs.Count == 0) return float.NaN;
        float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
        float front = float.MinValue, back = float.MaxValue;
        foreach (var v in vs)
        {
            float d = v.x * outw.x + v.z * outw.y;
            back = Mathf.Min(back, d); if (v.y >= top - band) front = Mathf.Max(front, d);
        }
        return front - back;
    }

    /// <summary>**二段築の下段を、据わった上段の駒の実メッシュから測って据える**(指図 `terraceWalls[].tierPlan`・2026-09-25・EDO-0430)。
    /// <para>置き方の 4 手: ① 固定側 = 据わった上段。下段の天端 = 上段の駒の実測の底(載せ・隙 0)、下段の背 = 上段の天端の前の縁の線
    /// (突き付け・隙 0)⇒ 下段の天端の前の縁の線 = 上段の線 + 駒の控え(<see cref="CrestToBack"/>・実メッシュで測る = `stepOut:"pieceDepth"`)。
    /// 区間どうしが節点で折れる所は、控えだけ外へ出した二本の線の交点を下段の角にする(下段は折れ線として一続きに回る)。
    /// ② 走り = 上段の底が見え面の側の地盤(<paramref name="groundAt"/>)より上に出る所(`lowerSpan:"upperFootExposed"`)、
    /// 両端は下段の見え面の前の地盤が下段の天端に届く所(= 小口が地盤の下)まで延ばす。③ 駒は区間の端から端まで等しい送り
    /// (<paramref name="runLen"/>・送りの上限 <paramref name="pitchMax"/>)で並べ、<see cref="FaceWallToLine"/> で天端の前の縁を線へ寄せ、
    /// 天端を実測で上段の底へ合わせる ④ 事後に寄せない。出隅の隅の駒は呼び手が <see cref="PlaceRunCorners"/> に下段の端(<paramref name="endsOut"/>)を渡して据える。</para>
    /// <para>硬い条件(許容0): 下段の底が見え面の前の地盤より上(浮き)なら ⚠ を刷る(駒の丈は変えない ── 丈の違う駒は部材の話)。
    /// 当たる先: 石垣の二段築すべて(山王 回廊の基壇 TW_Kairo_E/N/W。各邸の高い石垣を段に割る所 ── スキル unity-modular-stonewall §3b)。</para></summary>
    public static int PlaceTierBelow(IList<TierUpper> ups, string piecePath, float runLen, float pitchMax, float pieceH,
                                     Func<float, float, float> groundAt, float probe, Transform parent, float eps,
                                     List<RunEnd> endsOut, IDictionary<string, List<GameObject>> segOut,
                                     IDictionary<GameObject, Vector2> faceOut, List<GameObject> made, System.Text.StringBuilder log)
    {
        // ① 控えと上段の底を実測
        float D = float.NaN, dMin = float.MaxValue, dMax = float.MinValue, top = float.MaxValue, topHi = float.MinValue;
        foreach (var u in ups)
            foreach (var g in u.pieces)
            {
                if (g == null) continue;
                // 見え面が外向きの駒だけで測る(駒ごとに低い側を測り直して裏へ向けた駒は、天端の前の縁が背に化ける)
                if (Vector2.Dot(FaceSide(new List<GameObject> { g }, u.outw), u.outw) < 0f) continue;
                float d = CrestToBack(g, u.outw); if (float.IsNaN(d)) continue;
                dMin = Mathf.Min(dMin, d); dMax = Mathf.Max(dMax, d);
                float lo = float.MaxValue; foreach (var v in Body(g.transform, 999999)) lo = Mathf.Min(lo, v.y);
                top = Mathf.Min(top, lo); topHi = Mathf.Max(topHi, lo);
            }
        if (dMin == float.MaxValue) { log?.AppendLine("  ★ 二段築: 上段の駒が無い — 下段を据えない"); return 0; }
        D = dMin;
        log?.AppendLine("  二段築の下段: 駒の控え(実測)" + dMin.ToString("F3") + (dMax - dMin > 0.005f ? "〜" + dMax.ToString("F3") : "") +
                        "m / 天端 = 上段の底(実測)" + top.ToString("F3") + (topHi - top > 0.005f ? "〜" + topHi.ToString("F3") + " ⚠ 上段の底が揃わない" : ""));
        int n = 0;
        // ② 走り: 下段の見え面の前(<paramref name="probe"/> 先 ── 2m 格子の地表が石垣の内の節点に引かれない所)の地盤が下段の天端より低い所。
        //   上段のある走り(上段の区間の射影の内)で見つけ、角で相手の区間の下段が角まで来ていれば角から続ける。
        //   両端は同じ地盤が天端に届く所(小口が地盤の下)まで。
        var As = new Vector2[ups.Count]; var Bs = new Vector2[ups.Count]; var dirs = new Vector2[ups.Count];
        var lows = new bool[ups.Count][]; var Ms = new int[ups.Count]; var lens = new float[ups.Count];
        var nbA = new int[ups.Count]; var nbB = new int[ups.Count];
        // 見え面の外向きは、上段の底より低い地盤がある側で測り直す(基壇は両側が同じ高さの所が長く、区間の低い側の票が割れる
        //   ── 山王 TW_Kairo_W は 4 対 3 で内へ向き、下段が回廊の内へ出た)。票が無ければ渡された向きのまま。
        for (int i = 0; i < ups.Count; i++)
        {
            var u = ups[i]; float l0 = Vector2.Distance(u.a, u.b); if (l0 < 1e-4f) continue;
            Vector2 dd = (u.b - u.a) / l0, nr = new Vector2(dd.y, -dd.x); int vr = 0, vl = 0;
            for (float s0 = 0.25f; s0 < l0; s0 += 0.5f)
            {
                Vector2 p = u.a + dd * s0; float off = D + probe;
                float gR = groundAt(p.x + nr.x * off, p.y + nr.y * off), gL = groundAt(p.x - nr.x * off, p.y - nr.y * off);
                if (float.IsNaN(gR) || float.IsNaN(gL) || Mathf.Min(gR, gL) >= top - eps || Mathf.Abs(gR - gL) <= eps) continue;
                if (gR < gL) vr++; else vl++;
            }
            if (vr == 0 && vl == 0) continue;
            Vector2 o = vr >= vl ? nr : -nr;
            if (Vector2.Dot(o, u.outw) < 0f) { log?.AppendLine("  " + u.run + " の下段: 見え面の外向きを上段の底より低い地盤の側へ直した(" + Mathf.Max(vr, vl) + " 対 " + Mathf.Min(vr, vl) + ")"); u.outw = o; ups[i] = u; }
        }
        for (int i = 0; i < ups.Count; i++)
        {
            var u = ups[i]; nbA[i] = nbB[i] = -1;
            float len0 = Vector2.Distance(u.a, u.b); if (len0 < 1e-4f) { lows[i] = null; continue; }
            Vector2 dir = (u.b - u.a) / len0; dirs[i] = dir;
            // 下段の線の端: 節点で折れる相手の区間があれば、二本の線を控えだけ外へ出した交点
            Func<Vector2, bool, Vector2> endOf = (e, atA) =>
            {
                for (int j = 0; j < ups.Count; j++)
                {
                    if (j == i) continue; var w = ups[j];
                    if (Vector2.Distance(w.a, e) > 0.05f && Vector2.Distance(w.b, e) > 0.05f) continue;
                    Vector2 dj = (w.b - w.a).normalized;
                    float det = dir.x * dj.y - dir.y * dj.x; if (Mathf.Abs(det) < 0.2f) continue;
                    Vector2 p0 = u.a + u.outw * D, p1 = w.a + w.outw * D, r = p1 - p0;
                    float t = (r.x * dj.y - r.y * dj.x) / det;
                    if (atA) nbA[i] = j; else nbB[i] = j;
                    return p0 + dir * t;
                }
                return e + u.outw * D;
            };
            As[i] = endOf(u.a, true); Bs[i] = endOf(u.b, false);
            lens[i] = Vector2.Distance(As[i], Bs[i]);
            int M = Mathf.Max(1, Mathf.CeilToInt(lens[i] / 0.25f)); Ms[i] = M;
            var low = new bool[M + 1];
            for (int k = 0; k <= M; k++)
            {
                Vector2 q = As[i] + dir * (lens[i] * k / M);
                float gl = groundAt(q.x + u.outw.x * probe, q.y + u.outw.y * probe);
                low[k] = !float.IsNaN(gl) && gl < top - eps;
            }
            lows[i] = low;
        }
        var keeps = new bool[ups.Count][];
        for (int pass = 0; pass < 2; pass++)
            for (int i = 0; i < ups.Count; i++)
            {
                if (lows[i] == null) continue;
                var u = ups[i]; int M = Ms[i]; var low = lows[i];
                var keep = keeps[i] ?? new bool[M + 1];
                float sa = Vector2.Dot(u.a - As[i], dirs[i]), sb2 = Vector2.Dot(u.b - As[i], dirs[i]);
                var seed = new bool[M + 1];
                for (int k = 0; k <= M; k++) { float sk = lens[i] * k / M; seed[k] = low[k] && sk >= Mathf.Min(sa, sb2) && sk <= Mathf.Max(sa, sb2); }
                // 角: 相手の下段が角まで来ていれば、この区間も角から始める
                if (pass == 1)
                {
                    if (nbA[i] >= 0 && keeps[nbA[i]] != null && CornerKept(keeps[nbA[i]], ups[nbA[i]], As[i])) seed[0] = true;
                    if (nbB[i] >= 0 && keeps[nbB[i]] != null && CornerKept(keeps[nbB[i]], ups[nbB[i]], Bs[i])) seed[M] = true;
                }
                for (int k = 0; k <= M; k++)
                {
                    if (!seed[k]) continue; keep[k] = true;
                    for (int q = k - 1; q >= 0 && !keep[q]; q--) { keep[q] = true; if (!low[q]) break; }
                    for (int q = k + 1; q <= M && !seed[q]; q++) { keep[q] = true; if (!low[q]) break; }
                }
                keeps[i] = keep;
            }
        for (int i = 0; i < ups.Count; i++)
        {
            if (lows[i] == null) continue;
            var u = ups[i]; var dir = dirs[i]; var keep = keeps[i]; int M = Ms[i]; float len = lens[i]; Vector2 A = As[i];
            int iv = 0;
            for (int k = 0; k <= M; k++)
            {
                if (!keep[k] || (k > 0 && keep[k - 1])) continue;
                int e = k; while (e + 1 <= M && keep[e + 1]) e++;
                float s0 = len * k / M, s1 = len * e / M;
                if (s1 - s0 < 0.2f) { k = e; continue; }
                Vector2 SA = A + dir * s0, SB = A + dir * s1;
                string key = u.run + "_Ge#" + i + "." + iv; iv++;
                var mine = new List<GameObject>(); segOut[key] = mine;
                float L = s1 - s0;
                int N = (L <= runLen) ? 1 : Mathf.CeilToInt((L - runLen) / pitchMax) + 1;
                float pitch = (N > 1) ? (L - runLen) / (N - 1) : 0f;
                float head = (L <= runLen) ? (L + runLen) * 0.5f : runLen;
                Vector2 nrm = new Vector2(dir.y, -dir.x);
                bool fwd = Vector2.Dot(nrm, u.outw) >= 0f;
                Vector2 run = fwd ? dir : -dir, St = fwd ? SA : SB;
                float psi = Mathf.Atan2(run.x, run.y) * Mathf.Rad2Deg;
                int floatN = 0; float floatMax = 0f;
                for (int pI = 0; pI < N; pI++)
                {
                    Vector2 p = St + run * (head + pitch * pI);
                    var g = Place(piecePath, new Vector3(p.x, top - pieceH, p.y), psi, Vector3.one, parent, u.run + "_Ge_" + (n + pI).ToString("000") + "f");
                    if (g == null) continue;
                    FaceWallToLine(g, u.outw, A);
                    float hi = float.MinValue, lo = float.MaxValue;
                    foreach (var v in Body(g.transform, 999999)) { hi = Mathf.Max(hi, v.y); lo = Mathf.Min(lo, v.y); }
                    g.transform.position += Vector3.up * (top - hi); lo += top - hi;       // 天端 = 上段の底(載せ)
                    var c = RB(g).center; Vector2 f = new Vector2(c.x, c.z);
                    float fl = CrestToBack(g, u.outw);
                    Vector2 foot = f + u.outw * (fl * 0.5f + 0.3f);
                    float gf = groundAt(foot.x, foot.y);
                    if (!float.IsNaN(gf) && gf < lo) { floatN++; floatMax = Mathf.Max(floatMax, lo - gf); }
                    mine.Add(g); made?.Add(g); if (faceOut != null) faceOut[g] = u.outw;
                }
                n += N;
                endsOut.Add(new RunEnd { key = key, run = u.run + "_Ge", node = -1, p = SA, outw = u.outw, away = dir });
                endsOut.Add(new RunEnd { key = key, run = u.run + "_Ge", node = -1, p = SB, outw = u.outw, away = -dir });
                log?.AppendLine("  " + u.run + " の下段: 走り " + L.ToString("F2") + "m(下段の線の " + s0.ToString("F2") + "〜" + s1.ToString("F2") + "/" + len.ToString("F2") +
                                ")・駒 " + N + (floatN > 0 ? " / ⛔ 底が見え面の前の地盤より上 " + floatN + " 駒・最大 " + floatMax.ToString("F2") + "m" : ""));
                k = e;
            }
            if (iv == 0) log?.AppendLine("  " + u.run + " の下段: 上段の底が地盤より上に出る所が無い — 建てない");
        }
        return n;
    }
}
