// 稲荷 — 小祠と鳥居を据える (EdoBuild の partial・2026-09-21・EDO-0326)
//
// ⭐ **何が狂っていたか**: 類型表の `inari` は Spec へ読み込まれるのに**一度も参照されていなかった**。
//    表で true なのは町屋2区画(赤坂田町三丁目=三丁目稲荷 / 四丁目=西行稲荷)で、小祠も鳥居も在庫に
//    在るのに、江戸の町に稲荷が一社も建っていなかった。
//
// ⛔ 部材の基準点(ピボット・bounds の中心)で位置を決めない(規則21・docs/oki-kata.md)。
//    祠は**接地箇所**で据え、鳥居は**祠の正面の実面**から参道のぶん離して据える。
// ⛔ 祠と鳥居を突き付けない — 参道は「間を空ける」ことそのもので、突き付けたら参道が消える。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>稲荷を据えた結果。⛔ 呼び手は**必ず全部刷る**(規則19)— とくに
    /// <see cref="cands"/> が 0 のときは「置かなかった」であって「合格」ではない。</summary>
    public struct InariTally
    {
        public int cands;                         // 祠と鳥居が両方入る候補の格子点
        public int tried;                         // 据えてみて退けた座(めり込み・区画外・据えられない)
        public Vector2 shrine, torii;             // 据わった位置(実バウンズの中心)
        public float faceYaw;                     // 祠の正面の方位[deg]
        public float wantSandoM, sandoM, sandoEaveM;  // 参道: 指定・躯体どうしの実測・軒込みの実測
        public float clearShrine, clearTorii;     // 既に建った駒の軒込み外形までの実測の離れ
        public float gapShrine, gapTorii;         // 接地の隙(+ = 浮き / − = 埋没)
        public int touchShrine, touchTorii;       // 同じ高さで着く頂点の数
        public float sinkShrine, sinkTorii;       // 意図して埋めた量(台石・根巻石)
        public string why;                        // 建たなかった理由
    }

    static readonly Dictionary<string, float> _pivotSink = new Dictionary<string, float>();

    /// <summary>**地盤レベルのピボット規約で焼かれた駒が、ピボットより下へ出している量**[m]。
    /// 鳥居の根巻石のように「地盤より下に埋まっているのが正しい姿」の部位がこれにあたる
    /// (`Own.Torii` は実寸 2.000×2.320×0.300 で**底 −0.100**)。
    /// ⛔ 0.10 のような数字を呼び手へ書かない — 部材を焼き直した日に浮く(規則8)。駒を仮置きして測る。
    /// ⚠ これは<see cref="SeatOnGround"/> の sink が言う「**意図して埋める量**」であって、
    /// ピボットのずれを吸う目的で使う物ではない。</summary>
    public static float PivotSink(string path, float scale)
    {
        float v;
        string key = path + "@" + scale.ToString("F3");
        if (_pivotSink.TryGetValue(key, out v)) return v;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one * scale;
        var rb = RB(go);
        v = Mathf.Max(0f, -rb.min.y);                 // ピボット(y=0)より下の実メッシュ
        UnityEngine.Object.DestroyImmediate(go);
        _pivotSink[key] = v;
        return v;
    }

    /// <summary>駒の**壁体**(屋根を外した実メッシュ)の、点 <paramref name="a"/> から向き
    /// <paramref name="n"/> への最大の張り出し[m]。= その駒のその向きの実面。
    /// ⛔ <see cref="FaceOut"/> のように y の帯で切らない — 柱・鳥居のように**頂点が上下の端にしか
    /// 無い**駒は帯から丸ごと漏れる(2026-09-21 実測: 鳥居は <see cref="ModuleMeasure"/> の帯に
    /// 頂点が 1 つも無く「帯に頂点が無い」で落ちた)。⛔ 外接箱で代用しない(回った駒で嘘が出る)。</summary>
    public static float BodyOut(GameObject go, Vector2 a, Vector2 n)
    {
        float best = float.NaN;
        foreach (var w in Body(go.transform, 1200, false))
        {
            float d = (w.x - a.x) * n.x + (w.z - a.y) * n.y;
            if (float.IsNaN(best) || d > best) best = d;
        }
        return best;
    }

    /// <summary>**稲荷を一社据える。**小祠を <paramref name="anchor"/> に一番近い空き地へ据え、
    /// その**正面の実面**から <paramref name="sandoM"/> 離して鳥居を立てる。
    ///
    /// <para>置き方(docs/oki-kata.md §2):
    /// ①候補は 1m 格子のうち、区画の内で、既に建った駒の**軒込み外形**から
    /// <paramref name="clear"/> 以上離れ、**鳥居の座も同じだけ空いている**点だけ。
    /// ②祠を据える(接地箇所で据え、台石が地盤より下へ出るぶんだけ沈める)。
    /// ③祠の正面の実面を測り、その先へ鳥居を立てる。⛔ ピボットどうしの距離で離さない。
    /// ④めり込み・区画外なら**退けて次の候補へ**(黙って残さない)。</para>
    ///
    /// <param name="face">祠の正面の向き(ローカル +Z をここへ向ける)。鳥居はこの先に立つ。</param>
    /// <param name="avoid">既に建った駒。軒込みで避け、触れている箇所でめり込みを見る。</param>
    /// <returns>据わった駒(祠・鳥居)。据えられなければ空で、理由は <paramref name="t"/>.why。</returns>
    public static List<GameObject> InariSet(Transform parent, string prefix, Vector2[] poly,
        string hokoraPath, string toriiPath, Vector2 face, Vector2 anchor, float sandoM,
        List<GameObject> avoid, float clear, out InariTally t)
    {
        var made = new List<GameObject>();
        t = new InariTally
        {
            wantSandoM = sandoM, sandoM = float.NaN, sandoEaveM = float.NaN,
            clearShrine = float.NaN, clearTorii = float.NaN,
            gapShrine = float.NaN, gapTorii = float.NaN, why = ""
        };
        if (poly == null || poly.Length < 3) { t.why = "区画の多角形が無い"; return made; }
        face = face.normalized;
        if (face.sqrMagnitude < 0.5f) { t.why = "正面の向きが採れない"; return made; }
        float yaw = Mathf.Atan2(face.x, face.y) * Mathf.Rad2Deg;      // ローカル +Z を face へ
        t.faceYaw = yaw;

        // ⛔ ModuleMeasure(帯で測る)を使わない — 鳥居のように**頂点が上下の端にしかない**駒は
        //    帯に頂点が 1 つも無く「帯に頂点が無い」で落ちる(2026-09-21 実測)。外形は PartSize。
        var sh = PartSize(hokoraPath);                 // yaw=0 の実メッシュの外形(祠は +Z = 正面)
        var st = PartSize(toriiPath);
        if (sh == Vector3.zero || st == Vector3.zero) { t.why = "部材が引けない(祠か鳥居)"; return made; }
        float rh = Mathf.Max(sh.x, sh.z) * 0.5f;
        float rt = Mathf.Max(st.x, st.z) * 0.5f;

        // 既に建った駒の**軒込み外形**を点群で持つ(⛔ 外接箱で膨らませない)
        var occ = new NiwaOcc();
        if (avoid != null) foreach (var o in avoid) if (o != null) occ.AddBody(o.transform, 400, true);

        // ── ① 候補 ──
        float needH = rh + clear, needT = rt + clear;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in poly)
        {
            mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x);
            mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y);
        }
        var cands = new List<Vector2>();
        for (float x = mnx; x <= mxx; x += 1f)
            for (float z = mnz; z <= mxz; z += 1f)
            {
                var p = new Vector2(x, z);
                if (!EdoGeom.PIP(poly, p)) continue;
                if (EdoGeom.DistToPolyEdge(poly, p) < rh + 0.5f) continue;
                if (occ.Dist(p, needH + 2f) < needH) continue;
                var q = p + face * (sh.z * 0.5f + sandoM);             // 鳥居の座(下読み)
                if (!EdoGeom.PIP(poly, q)) continue;
                if (EdoGeom.DistToPolyEdge(poly, q) < rt + 0.3f) continue;
                if (occ.Dist(q, needT + 2f) < needT) continue;
                cands.Add(p);
            }
        t.cands = cands.Count;
        if (cands.Count == 0)
        {
            t.why = string.Format("祠(半径 {0:F2}m)と鳥居(半径 {1:F2}m)が離れ {2:F1}m を取って入る空き地が"
                                + "区画に 1 点も無い", rh, rt, clear);
            return made;
        }
        cands.Sort((a, b) => (a - anchor).sqrMagnitude.CompareTo((b - anchor).sqrMagnitude));

        // ── ②〜④ 拠り所に近い候補から順に据えてみる ──
        float sinkH = PivotSink(hokoraPath, 1f), sinkT = PivotSink(toriiPath, 1f);
        int limit = Mathf.Min(cands.Count, 60);
        for (int i = 0; i < limit; i++)
        {
            var p = cands[i];
            var go = Place(hokoraPath, new Vector3(p.x, Ground(p.x, p.y), p.y), yaw, Vector3.one, parent, prefix + "_Hokora");
            try { SeatOnGround(go, sinkH, 800); }
            catch (Exception) { UnityEngine.Object.DestroyImmediate(go); t.tried++; continue; }
            if (OutsideParcelStrict(go.transform, poly) || (avoid != null && Clashes(go, avoid)))
            { UnityEngine.Object.DestroyImmediate(go); t.tried++; continue; }

            // ③ 鳥居 — **祠の正面の実面**から参道のぶん先へ(⛔ ピボットの距離で離さない)
            var rbH = RB(go);
            float frontProj = BodyOut(go, p, face);
            if (float.IsNaN(frontProj)) frontProj = sh.z * 0.5f;
            var q2 = p + face * (frontProj + sandoM);
            var tg = Place(toriiPath, new Vector3(q2.x, Ground(q2.x, q2.y), q2.y), yaw, Vector3.one, parent, prefix + "_Torii");
            try { SeatOnGround(tg, sinkT, 800); }
            catch (Exception)
            {
                UnityEngine.Object.DestroyImmediate(tg); UnityEngine.Object.DestroyImmediate(go);
                t.tried++; continue;
            }
            if (OutsideParcelStrict(tg.transform, poly) || (avoid != null && Clashes(tg, avoid)))
            {
                UnityEngine.Object.DestroyImmediate(tg); UnityEngine.Object.DestroyImmediate(go);
                t.tried++; continue;
            }

            // ── 実測(0 件でも刷る・規則19)──
            Vector3 at; int nc;
            var back = new Vector3(-face.x, 0f, -face.y);
            t.sandoM = Contact(tg, go, back, out at, out nc, 0.01f, 0.25f, 1200, false);   // 躯体どうし
            t.sandoEaveM = Contact(tg, go, back, out at, out nc, 0.01f, 0.25f, 1200, true); // 軒込み
            t.gapShrine = Contact(go, out at, out nc, 0.01f, 1200); t.touchShrine = nc;
            t.gapTorii = Contact(tg, out at, out nc, 0.01f, 1200); t.touchTorii = nc;
            t.sinkShrine = sinkH; t.sinkTorii = sinkT;
            var cH = new Vector2(rbH.center.x, rbH.center.z);
            var rbT = RB(tg); var cT = new Vector2(rbT.center.x, rbT.center.z);
            t.shrine = cH; t.torii = cT;
            t.clearShrine = occ.Dist(cH, 12f) - rh;
            t.clearTorii = occ.Dist(cT, 12f) - rt;
            made.Add(go); made.Add(tg);
            return made;
        }
        t.why = string.Format("候補 {0} 点のうち {1} 点を試したが、据えると区画を出るか既に建った駒へめり込む",
                              t.cands, t.tried);
        return made;
    }
}
