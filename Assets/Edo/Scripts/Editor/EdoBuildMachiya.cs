// 町屋の表店の run — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは EdoBuild の関数だけ」)。
//
// ⛔ このファイルに「どの区画が何を持つか」を書かない — それは類型表と EdoTypologyBuilder の持ち場。
//    ここに書くのは **置く・測る・突き付ける・据える** だけ。
//
// ⭐ 何を直したか(EDO-0325・2026-09-21): 2026-09-21 まで町屋 24 区画の表店は
//    `EdoTypologyBuilder.Plan()` が `houses/6` を 2〜14 に丸めた棟数だけ積み、`Spot()` が
//    **区画の内側の格子点へばらばらに散らして**いた。町屋は通りに面して軒を接して建つものなので、
//    姿が根本から違った(どの区画も「どこも6軒」で、区画の大小も間口も効いていなかった)。
//
// ⚠ **5間(9.09m)の1軒を埋める駒が在庫に無い。**在庫の表店は `Eg.Shop01` 躯体幅 ≒4.9m(2.7間)と
//    `Eg.Shop02` ≒7.1m(3.9間)の2点だけ。⛔ 非等方に伸ばして 5 間へ合わせない(軒の出と格子の目が伸びる)。
//    採ったのは **継ぐ**方 — 1軒を駒1〜2枚の組で埋め、表の間口との差を <see cref="EdoBuild.MachiyaTally"/> に
//    載せて呼び手に刷らせる。5間専用の駒は EDO-0318 ④(部材方)。
//
// 作法は docs/oki-kata.md(触れている箇所を測る)/ 置き方の4手は
// unity-buke-yashiki/references/sashizu.md §3f。

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>表店の駒の寸法(ES 倍・ピボットからの片寄せ込み)。走りと奥行を**二重に**持つ:
    /// <list type="bullet">
    /// <item><c>lo/hi</c> = 見えているメッシュ全部の端(軒・庇の先)。**突き付けはこちら**。</item>
    /// <item><c>wLo/wHi</c>・<c>dLo/dHi</c> = 「足元 +0.30m 〜 丈の 60%」の帯で拾った**躯体**の端。
    /// 店先の面合わせと、隣の軒との界壁の隙を刷るのに使う。</item>
    /// </list>
    /// ⭐ **突き付けを躯体でなく軒で取る理由**: 町屋の駒は妻側にも軒が出ていて、躯体で突き付けると
    /// 屋根どうしがめり込む。閉じは **「隙間 &gt; めり込み」**(門と塀の閉じと同じ作法)なので、
    /// 軒を接して界壁に隙を残す側へ倒す。残った界壁の隙は <see cref="MachiyaTally"/> に実測で載る。
    /// ⛔ 外接箱(<see cref="RB"/>)の x/z で代用しない — 斜めの通りでは箱が膨らむ。</summary>
    public struct ShopModule
    {
        public float lo, hi;        // 走り(ローカル +X)方向の軒の端(ピボット基準)— 突き付けの基準
        public float wLo, wHi;      // 同・躯体の端
        public float dLo, dHi;      // 奥行(ローカル +Z)方向の躯体の端(+Z が店先)
        public float height;        // 駒の丈(軒・屋根込み)
        public float W { get { return hi - lo; } }        // 軒の幅(= 1 枚が食う走り)
        public float WallW { get { return wHi - wLo; } }  // 躯体の幅
        public float D { get { return dHi - dLo; } }      // 躯体の奥行
    }

    /// <summary>軒どうしの継ぎ目に残す**髪一筋**[m]。⭐ 0 ちょうどで突き付けると、据え直しの丸めで
    /// 触れている箇所が 0.0004m ほど負に落ち、検査が「めり込み」と刷る(2026-09-21 実測)。
    /// 閉じは **「隙間 &gt; めり込み」**なので、見えない幅だけ正の側へ倒す。</summary>
    const float JOINT = 0.005f;

    /// <summary>駒の**壁体**(屋根・軒を外した実頂点)が線 (<paramref name="a"/>, 外向き <paramref name="n"/>)
    /// より外にあれば、その分だけ内へ引く。返り値 = 引いた量[m]。
    /// ⛔ 帯(<see cref="FaceOut"/>)で合わせただけで済ませない — 帯の外の基壇・腰板・下屋が先に越える。</summary>
    static float TuckToLine(GameObject go, Vector2 a, Vector2 n)
    {
        float over = float.MinValue;
        foreach (var w in Body(go.transform, 400, false))
        {
            float dd = (w.x - a.x) * n.x + (w.z - a.y) * n.y;
            if (dd > over) over = dd;
        }
        if (over <= 0f || over == float.MinValue) return 0f;
        go.transform.position -= new Vector3(n.x, 0f, n.y) * over;
        return over;
    }

    /// <summary>**辺の背後に実際に何 m あるか。**辺の上の 9 点から敷地の内へ歩いて、区画の外へ出るまでの
    /// 距離の中央値。⭐ 表の `depth_ken` を鵜呑みにしない — 山王門前の短冊は表が 18 間(32.7m)と言うのに
    /// 実際は **6.8m** しかなく、奥行 6.91m の `Eg.Shop02` が全 12 駒とも背中側の境界を 0.14m 越えた
    /// (2026-09-21 実測)。⛔ 区域侵犯は許容0(規則4)なので、駒を選ぶ前に区画を測る。</summary>
    public static float EdgeDepth(Vector2[] poly, Vector2 A, Vector2 B, Vector2 outward)
    {
        var inw = -outward;
        var ds = new List<float>();
        for (int k = 1; k <= 9; k++)
        {
            var p = Vector2.Lerp(A, B, k / 10f);
            float dd = 0f;
            while (dd < 200f && EdoGeom.PIP(poly, p + inw * (dd + 0.25f))) dd += 0.25f;
            ds.Add(dd);
        }
        ds.Sort();
        return ds[ds.Count / 2];
    }

    /// <summary>**区画の内へ折り込む。**駒の壁体が区画の外にある間、内向きへ刻んで下げる。
    /// 返り値 = 下げた量[m](<paramref name="cap"/> まで下げても収まらなければ −1)。
    /// ⛔ 軒では判定しない — 軒は越えてよい(2026-09-21 施主裁定A)。</summary>
    /// <summary>この駒が既に建った駒のどれかへ**めり込んで**いるか。⛔ 外接箱の重なりで見ない —
    /// 回った駒で必ず外す。測るのは <see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>
    /// の触れている箇所で、軒は許容(裁定A)なので屋根を外した壁体だけで見る。</summary>
    static bool Clashes(GameObject go, List<GameObject> others)
    {
        foreach (var o in others)
        {
            var d3 = o.transform.position - go.transform.position; d3.y = 0f;
            if (d3.sqrMagnitude < 1e-4f) return true;
            Vector3 at; int nc;
            float g = Contact(go, o, d3.normalized, out at, out nc, 0.01f, 0.5f, 400, false);
            if (!float.IsNaN(g) && g < 0f) return true;
        }
        return false;
    }

    static void Seat2(GameObject go, Vector2 at)
    {
        try { SeatOnGround(go, 0.05f, 600); }
        catch (Exception) { SeatBottom(go, Ground(at.x, at.y) - 0.05f); }
    }

    static float TuckIntoParcel(GameObject go, Vector2[] poly, Vector2 inward, float cap)
    {
        float moved = 0f;
        while (OutsideParcelStrict(go.transform, poly) && moved < cap)
        {
            go.transform.position += new Vector3(inward.x, 0f, inward.y) * 0.05f;
            moved += 0.05f;
        }
        return OutsideParcelStrict(go.transform, poly) ? -1f : moved;
    }

    /// <summary>駒の**壁体**が区画の外へ 1 点でも出ているか。遊びは無し —
    /// 塀と違って建物は境界線の上に立つ物ではない(規則4「区域侵犯は許容0」)。</summary>
    static bool OutsideParcelStrict(Transform t, Vector2[] poly)
    {
        foreach (var w in Body(t, 400, false))
            if (!EdoGeom.PIP(poly, new Vector2(w.x, w.z))) return true;
        return false;
    }

    static readonly Dictionary<string, ShopModule> _shopMeasure = new Dictionary<string, ShopModule>();

    /// <summary>在庫の edogoyomi の駒(ES 倍で使う物)を測る。</summary>
    public static ShopModule ShopMeasure(string path) { return ModuleMeasure(path, ES); }

    /// <summary>当方で起こした駒(実寸で使う物 = 倍率 1)を測る。</summary>
    public static ShopModule OwnMeasure(string path) { return ModuleMeasure(path, 1f); }

    /// <summary>駒を <paramref name="scale"/> 倍・無回転で仮置きして軒と躯体の走り・奥行を測る。
    /// ⚠ 倍率は駒の出どころで違う — edogoyomi は ES 倍、当方が Blender で起こした物は実寸(1 倍)。
    /// ⛔ 取り違えると 1.8 倍の町屋が建つので、鍵に倍率を混ぜて別々に覚える。</summary>
    public static ShopModule ModuleMeasure(string path, float scale)
    {
        ShopModule m;
        string key = path + "@" + scale.ToString("F3");
        if (_shopMeasure.TryGetValue(key, out m)) return m;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one * scale;
        var rb = RB(go);
        float yLo = rb.min.y + 0.30f, yHi = rb.min.y + rb.size.y * 0.60f;
        float alo, ahi, xlo, xhi, zlo, zhi;
        FaceSpan(go, new Vector2(1f, 0f), float.MinValue, float.MaxValue, out alo, out ahi);   // 軒込み
        FaceSpan(go, new Vector2(1f, 0f), yLo, yHi, out xlo, out xhi);                          // 躯体
        FaceSpan(go, new Vector2(0f, 1f), yLo, yHi, out zlo, out zhi);
        UnityEngine.Object.DestroyImmediate(go);
        if (ahi <= alo || xhi <= xlo || zhi <= zlo) throw new Exception("ModuleMeasure: 帯に頂点が無い — " + path);
        m = new ShopModule { lo = alo, hi = ahi, wLo = xlo, wHi = xhi, dLo = zlo, dHi = zhi, height = rb.size.y };
        _shopMeasure[key] = m;
        return m;
    }

    /// <summary>表店の run が何を建てたか。⛔ 呼び手は**必ず全部刷る**(規則19)— とくに
    /// <see cref="wantHouses"/> と <see cref="houses"/> の差は「5間の駒が無い」ことの実測の現れで、
    /// 黙って飲むと在庫の宿題(EDO-0318 ④)が見えなくなる。</summary>
    public struct MachiyaTally
    {
        public float edgeLen;      // 辺の実長[m]
        public float maguchiM;     // 表の `maguchi_ken` から出た 1 軒の間口[m]
        public int wantHouses;     // 表の間口で割った軒数(辺長 ÷ 間口)
        public int houses;         // 実際に据えた軒
        public int pieces;         // 据えた駒の枚数
        public int dropped;        // 壁体が区画の外へ出て退けた駒
        public float builtM;       // 据えた駒の走りの実測の合計
        public float rojiM;        // 軒と軒の間に流した路地の幅[m]
        public float restM;        // 路地に流しきれず端に残った走り[m]
        public float minJoint;     // 隣り合う軒の**触れている箇所**の隙の最小[m](負=めり込み)
        public float wallGapM;     // 軒を接したときに界壁に残る隙の最大[m](= 両側の軒の出の和)
        public float frontFace;    // 店先の面が境界線からどれだけ外(+)/内(−)にあるか[m]
        public string combos;      // 1軒を何枚で埋めたか(駒名×枚数 の内訳)
        public int comboKinds;     // 1軒の埋め方の候補が何通りあったか(1 = 同じ駒が並ぶ)
        public float roomM;        // 辺の背後に**実際に**あった奥行[m](表の depth_ken とは別)
        public int clashed;        // 先に建った列にめり込むので退けた駒(両側町の角)
        public int tucked;         // 区画の内へ折り込んだ駒
        public float tuckedM;      // 同・最大の折り込み量[m]
    }

    /// <summary>1 軒の間口 <paramref name="maguchiM"/> を、在庫の駒 1〜2 枚の組で埋める候補。
    /// 誤差の小さい順に返す。⭐ **1 種に決め打たない** — 全部おなじ組で埋めると、24 区画の通りが
    /// 同じ駒の等間隔の並びになる(`docs/typology-builder.md` の「⛔ 等間隔・同一個体」)。
    /// 採るのは「最良の誤差 + 0.5m」か「間口の 1/4」のどちらか広い方に入る組だけ。</summary>
    static List<string[]> ShopCombos(string[] stock, float maguchiM)
    {
        var cand = new List<string[]>();
        foreach (var a in stock) cand.Add(new[] { a });
        foreach (var a in stock) foreach (var b in stock) cand.Add(new[] { a, b });
        Func<string[], float> wid = c => { float w = 0f; foreach (var p in c) w += ShopMeasure(p).W; return w; };
        cand.Sort((x, y) => Mathf.Abs(wid(x) - maguchiM).CompareTo(Mathf.Abs(wid(y) - maguchiM)));
        float best = Mathf.Abs(wid(cand[0]) - maguchiM);
        float tol = Mathf.Max(best + 0.5f, maguchiM * 0.25f);
        var keep = new List<string[]>();
        foreach (var c in cand)
        {
            if (Mathf.Abs(wid(c) - maguchiM) > tol) continue;
            // 同じ幅の組(S1+S2 と S2+S1)は並びの見た目が変わるので両方残す
            keep.Add(c);
        }
        return keep;
    }

    /// <summary>**表店の列。**辺 A→B に、通りへ店先を向けた町屋を軒を接して並べる。
    ///
    /// <para>手順は置き方の4手(`docs/oki-kata.md`): ①走りは駒の**軒の実寸**をカーソルで積む(界壁に残る隙は刷る)
    /// ②奥行は店先の**実面**を境界線へ <see cref="AlignFace"/> で合わせる(⛔ ピボット・外接箱で寄せない)
    /// ③高さは**触れている箇所**を測って <see cref="SeatOnGround"/> で据える
    /// ④端数は軒と軒の間の**路地**へ流す(1 間を超える分だけ端に残す)。</para>
    ///
    /// <param name="maguchiM">表の `maguchi_ken` から出た 1 軒の間口[m]。軒数はこれと辺長から出る
    /// — ⛔ 棟数を呼び手が決めない(「どこも6軒」に戻る)。</param>
    /// <param name="maxDepthM">この辺の背後に使える奥行[m](`depth_ken` 由来)。これより深い駒は
    /// 候補から外す(桐畑の代地は奥行 5 間しかない)。0 以下なら検めない。</param>
    /// <param name="gapC">/<paramref name="gapHalf"/> 木戸(路地口)の開口。列をそこで割る。gapHalf≤0 なら割らない。</param>
    /// <param name="leadPath">列の頭に 1 枚だけ差す駒(自身番屋)。null なら差さない。
    /// その軒の残りは在庫の駒で埋める。</param>
    /// <param name="keepInside">壁体がここから出る駒は置かない(区域侵犯は許容0・規則4)。null なら検めない。</param>
    public static List<GameObject> MachiyaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, float baseY,
        float maguchiM, float maxDepthM, Vector2 gapC, float gapHalf, string prefix,
        string leadPath, Vector2[] keepInside, List<GameObject> avoid, out MachiyaTally tally)
    {
        var made = new List<GameObject>();
        tally = new MachiyaTally();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        tally.edgeLen = len; tally.maguchiM = maguchiM;
        tally.wantHouses = Mathf.FloorToInt(len / Mathf.Max(0.5f, maguchiM));
        tally.minJoint = float.NaN;

        // 店先(+Z)を通りへ。NagayaRun / DobeiRun と同じ向きの採り方。
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        // ローカル +X の世界での向き = outward を −90° 回した向き。走りをこれに揃えるとカーソルが素直になる。
        Vector2 xdirW = new Vector2(outward.y, -outward.x);
        Vector2 sA = A, rdir = dir;
        if (Vector2.Dot(dir, xdirW) < 0f) { sA = B; rdir = -dir; }

        // 在庫の駒 — 奥行が足りない辺では深い駒を外す。
        // ⭐ 効かせるのは**表の奥行と実測の奥行の小さい方**(表が実際より広く言うことがある)。
        float room = maxDepthM;
        if (keepInside != null)
        {
            float real = EdgeDepth(keepInside, A, B, outward);
            tally.roomM = real;
            room = (room > 0f) ? Mathf.Min(room, real) : real;
        }
        var stock = new List<string>();
        foreach (var p in new[] { EdoAssets.Eg.Shop01, EdoAssets.Eg.Shop02 })
        {
            if (room > 0f && ShopMeasure(p).D > room - 0.3f) continue;
            stock.Add(p);
        }
        if (stock.Count == 0) stock.Add(EdoAssets.Eg.Shop01);   // 奥行が足りなくても 1 種は残す(呼び手が刷る)
        var combos = ShopCombos(stock.ToArray(), maguchiM);
        tally.comboKinds = combos.Count;

        // 木戸の開口で区間を割る(NagayaRun と同じ割り方)
        var segs = new List<float[]>();
        if (gapHalf > 0f)
        {
            float gT = Vector2.Dot(gapC - sA, rdir);
            if (gT - gapHalf > 0f) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });

        var rnd = new System.Random(prefix.GetHashCode());
        var kinds = new Dictionary<string, int>();
        int idx = 0;
        string lead = leadPath;                       // 頭の 1 枚は最初の区間の最初の軒でだけ使う

        foreach (var seg in segs)
        {
            float segLen = seg[1] - seg[0];
            if (segLen < 1.0f) continue;

            // ── 下読み: この区間に何軒が何枚で入るか(まだ置かない)──
            var rows = new List<List<string>>();
            float total = 0f;
            while (true)
            {
                var row = new List<string>();
                float w = 0f;
                bool usedLead = lead != null;
                if (usedLead)
                {
                    row.Add(lead); w += ShopMeasure(lead).W;
                    // 残りを在庫の駒で埋める(1 枚だけ・入らなければ番屋 1 枚で 1 軒とする)
                    string fill = null; float bestErr = float.MaxValue;
                    foreach (var p in stock)
                    {
                        float err = Mathf.Abs(w + ShopMeasure(p).W - maguchiM);
                        if (err < bestErr) { bestErr = err; fill = p; }
                    }
                    if (fill != null && Mathf.Abs(w - maguchiM) > bestErr) { row.Add(fill); w += ShopMeasure(fill).W; }
                }
                else
                {
                    var c = combos[rnd.Next(combos.Count)];
                    foreach (var p in c) { row.Add(p); w += ShopMeasure(p).W; }
                }
                if (total + w > segLen + 0.01f) break;   // ⛔ 入らない軒は数えない(区間からはみ出す)
                rows.Add(row); total += w;
                if (usedLead) lead = null;               // ⭐ 頭の駒は**軒が採れたときだけ**使い切る
            }
            if (rows.Count == 0) continue;

            // ── 端数は軒と軒の間の路地へ流す(1 間まで)。残りは区間の両端へ ──
            float slack = segLen - total;
            float roji = Mathf.Clamp(slack / (rows.Count + 1), 0f, ES);   // 路地の上限 = 江戸間 1 間
            float rest = slack - roji * (rows.Count + 1);
            tally.rojiM = Mathf.Max(tally.rojiM, roji); tally.restM += rest;

            float cursor = seg[0] + rest * 0.5f + roji;
            foreach (var row in rows)
            {
                var houseGo = new List<GameObject>();
                foreach (var path in row)
                {
                    var m = ShopMeasure(path);
                    // ローカル +X ∥ rdir なので、軒の低い端が cursor に来るピボットの走り座標
                    var c2 = sA + rdir * (cursor - m.lo);
                    var go = Place(path, new Vector3(c2.x, baseY, c2.y), psi, Vector3.one * ES, parent,
                                   prefix + "_" + idx + "_" + System.IO.Path.GetFileNameWithoutExtension(path));
                    // ② 奥行: 店先の**実面**を境界線へ(⛔ ピボット・外接箱で寄せない)
                    var rb = RB(go);
                    AlignFace(go, A, outward, 0f, rb.min.y + 0.30f, rb.min.y + rb.size.y * 0.60f);
                    // ⭐ 帯で合わせた面より、**帯の外の壁体**(基壇の縁・腰板・下屋)が先に線を越える
                    //    ことがある(2026-09-21 実測: 山王門前で 12 駒が 0.14m・田町で 2 駒が 0.06m)。
                    //    区域侵犯は許容0(規則4)なので、実メッシュの張り出しを測って**その分だけ内へ引く**。
                    //    ⛔ 定数の犬走りで逃げない — 駒を替えた日にまた越える(規則8)。
                    TuckToLine(go, A, outward);
                    // ③ 高さ: **触れている箇所**を測って据える(規則21)
                    try { SeatOnGround(go, 0.05f, 600); }
                    catch (Exception) { SeatBottom(go, Ground(c2.x, c2.y) - 0.05f); }
                    // 壁体が区画の外へ出たら、まず**区画の内へ折り込む**(裁定A の折り込みと同じ手)。
                    // 斜めの側辺を跨ぐ列の端は 0.05〜0.20m 下げれば収まる(2026-09-21 実測 0.06m)。
                    // それでも収まらない駒だけ退ける — ⛔ 区域侵犯は許容0(規則4)。
                    if (keepInside != null)
                    {
                        float tk = TuckIntoParcel(go, keepInside, -outward, 0.60f);
                        if (tk < 0f)
                        {
                            UnityEngine.Object.DestroyImmediate(go);
                            tally.dropped++; idx++; cursor += m.W + JOINT; continue;
                        }
                        if (tk > 0f) { tally.tuckedM = Mathf.Max(tally.tuckedM, tk); tally.tucked++; Seat2(go, c2); }
                    }
                    // 両側町は**角で二つの列が同じ場所を取り合う**(2026-09-21 実測: 新町三丁目で −6.38m)。
                    // 先に建った列の駒と**触れている箇所**を測り、めり込むなら退けて角を空ける。
                    if (avoid != null && Clashes(go, avoid))
                    {
                        UnityEngine.Object.DestroyImmediate(go);
                        tally.clashed++; idx++; cursor += m.W + JOINT; continue;
                    }
                    made.Add(go); houseGo.Add(go); idx++;
                    int cnt; string nm = System.IO.Path.GetFileNameWithoutExtension(path);
                    kinds.TryGetValue(nm, out cnt); kinds[nm] = cnt + 1;
                    tally.builtM += m.W;
                    // 軒の出のぶん、界壁には必ず隙が残る(閉じは「隙間 > めり込み」)。実寸から出して刷る。
                    tally.wallGapM = Mathf.Max(tally.wallGapM, (m.hi - m.wHi) + (m.wLo - m.lo));
                    cursor += m.W + JOINT;            // 継ぎ目は軒の実寸 + 髪一筋
                }
                if (houseGo.Count > 0) tally.houses++;
                cursor += roji;
            }
        }
        tally.pieces = made.Count;

        // ── 軒どうしの**触れている箇所**を実測して刷る(⛔ 設計値の路地幅を「隙」と呼ばない・規則19)──
        // ⛔ 向きをピボットどうしの差から採らない — ピボットは駒ごとに寄っていて、走りと別の向きが出る。
        //    測る向きは**列の走り**そのもの(k は rdir の先にあるので、k から k−1 へは −rdir)。
        var back = new Vector3(-rdir.x, 0f, -rdir.y);
        for (int k = 1; k < made.Count; k++)
        {
            Vector3 at; int nc;
            float g = Contact(made[k], made[k - 1], back, out at, out nc, 0.01f, 0.5f, 600);
            if (!float.IsNaN(g) && (float.IsNaN(tally.minJoint) || g < tally.minJoint)) tally.minJoint = g;
        }
        // ── 店先の面が境界線からどこに来たか(据え直しで動くので**最後に実測**)──
        if (made.Count > 0)
        {
            var rb0 = RB(made[0]);
            tally.frontFace = FaceOut(made[0], A, outward, rb0.min.y + 0.30f, rb0.min.y + rb0.size.y * 0.60f);
        }
        var parts = new List<string>();
        foreach (var kv in kinds) parts.Add(kv.Key + "×" + kv.Value);
        tally.combos = string.Join(" ", parts.ToArray());
        return made;
    }

    /// <summary>**裏長屋(裏店)の列。**表店の列の背後に、路地を挟んで棟を並べる。
    ///
    /// <para>辺 A→B を敷地の内へ <paramref name="insetM"/> 下げた線に沿って積む。戸が並ぶ面(+Z)は
    /// **路地の側**=通りの側へ向ける — ⛔ 逆に向けると盲面が路地を向いて戸が消える
    /// (`EdoAssets.Own.UraNagaya` の注記)。奥行は戸の面を路地の線へ <see cref="AlignFace"/> で合わせ、
    /// 高さは**触れている箇所**を測って据える。桁行は 12→9→6 間の順に、残りへ入る一番長い棟を継ぐ。</para>
    ///
    /// <param name="cap">置く棟数の上限(表の `ura_nagaya` が数で書いてあるとき)。0 以下なら上限なし。</param>
    /// <param name="wallGap">返り: 棟どうしの**触れている箇所**の隙の最小[m](負 = めり込み)。</param>
    public static List<GameObject> UraNagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward,
        float baseY, float insetM, int cap, string prefix, Vector2[] keepInside,
        List<GameObject> avoid, out int dropped, out float wallGap)
    {
        var made = new List<GameObject>();
        dropped = 0; wallGap = float.NaN;
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;   // 戸の面(+Z)を路地へ
        Vector2 xdirW = new Vector2(outward.y, -outward.x);
        Vector2 sA = A, rdir = dir;
        if (Vector2.Dot(dir, xdirW) < 0f) { sA = B; rdir = -dir; }
        // 線を敷地の内へ下げる(内向き = −outward)
        Vector2 inw = -outward;
        sA += inw * insetM;

        // 桁行は**残りへ入る一番長い棟**から。⭐ 表店と違って乱さない — 裏店は同じ割りの棟を
        //    続けて建てた物で、長さを混ぜるほど棟の天端が刻まれて長屋らしさが消える。
        //    残りが 6 間を切ったところが列の終わり(端数は路地の突き当りが受ける)。
        var lens = new float[] { 12f, 9f, 6f };
        float cursor = 0f;
        int idx = 0;
        while (cursor < len - 0.5f)
        {
            string pick = null; ShopModule pm = default(ShopModule);
            foreach (var wk in lens)
            {
                var path = EdoAssets.Own.UraNagaya(wk);
                var m = OwnMeasure(path);
                if (cursor + m.W <= len + 0.01f) { pick = path; pm = m; break; }
            }
            if (pick == null) break;                       // 一番短い棟も入らない = 打ち止め
            if (cap > 0 && made.Count >= cap) break;
            var c2 = sA + rdir * (cursor - pm.lo);
            var go = Place(pick, new Vector3(c2.x, baseY, c2.y), psi, Vector3.one, parent,
                           prefix + "_" + idx + "_" + System.IO.Path.GetFileNameWithoutExtension(pick));
            var rb = RB(go);
            AlignFace(go, sA, outward, 0f, rb.min.y + 0.30f, rb.min.y + rb.size.y * 0.60f);
            try { SeatOnGround(go, 0.05f, 600); }
            catch (Exception) { SeatBottom(go, Ground(c2.x, c2.y) - 0.05f); }
            if (keepInside != null)
            {
                // ⛔ 塀の 0.60m の遊びを建物に使わない(規則4「区域侵犯は許容0」)。
                //    折り込んで収まらない棟だけ退ける。
                float tk = TuckIntoParcel(go, keepInside, -outward, 0.60f);
                if (tk < 0f)
                {
                    UnityEngine.Object.DestroyImmediate(go);
                    dropped++; idx++; cursor += pm.W + JOINT; continue;
                }
                if (tk > 0f) Seat2(go, c2);
            }
            // ⛔ 両側町は**もう一方の通りの表店が背後まで回り込んでいる**(2026-09-21 実測:
            //    新町三丁目で −5.03m)。先に建った駒とめり込む棟は退ける。
            if (avoid != null && Clashes(go, avoid))
            {
                UnityEngine.Object.DestroyImmediate(go);
                dropped++; idx++; cursor += pm.W + JOINT; continue;
            }
            made.Add(go); idx++;
            cursor += pm.W + JOINT;
        }
        var back = new Vector3(-rdir.x, 0f, -rdir.y);
        for (int k = 1; k < made.Count; k++)
        {
            Vector3 at; int nc;
            float g = Contact(made[k], made[k - 1], back, out at, out nc, 0.01f, 0.5f, 600);
            if (!float.IsNaN(g) && (float.IsNaN(wallGap) || g < wallGap)) wallGap = g;
        }
        return made;
    }
}
