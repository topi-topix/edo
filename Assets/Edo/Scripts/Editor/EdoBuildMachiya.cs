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
// ⚠ **在庫の表店は `Eg.Shop01` 軒幅 ≒4.9m(2.7間)と `Eg.Shop02` ≒7.1m(3.9間)の2点だけ**で、5間(9.09m)の
//    1軒は1枚で埋まらない。⛔ 非等方に伸ばして 5 間へ合わせない(軒の出と格子の目が伸びる)。
//    そこで **継ぐ**(1軒を駒1〜2枚の組で埋め、表の間口との差を <see cref="EdoBuild.MachiyaTally"/> に載せて
//    呼び手に刷らせる)のと並べて、**当方で起こした 5間の駒**(`EdoAssets.Own.Typ.Omotedana`・EDO-0348)を
//    候補へ足せる(EDO-0355)。⚠ **在庫の駒は ES 倍・当方の駒は実寸(倍率 1)** なので、駒ごとに
//    <see cref="ShopPiece"/>(パス+倍率)を持ち、測る手も置く手も同じ倍率で通す。
//
// 作法は docs/oki-kata.md(触れている箇所を測る)/ 置き方の4手は
// unity-buke-yashiki/references/sashizu.md §3f。

using System;
using System.Collections.Generic;
using System.Linq;
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

    /// <summary>表店の駒 1 種 = パス+倍率。⭐ **測る倍率と置く倍率を分けて持てない形にした** — edogoyomi は ES 倍、
    /// 当方で起こした駒は実寸(1 倍)で、片方だけ取り違えると 1.8 倍(または 0.55 倍)の町屋が建つ(EDO-0355)。
    /// ⛔ 呼び手が `ShopMeasure` / `OwnMeasure` を選ばない — <see cref="Measure"/> が倍率を通す。</summary>
    public struct ShopPiece
    {
        public string path; public float scale;
        public static ShopPiece Kit(string path) { return new ShopPiece { path = path, scale = ES }; }      // 在庫の駒(ES 倍)
        public static ShopPiece Ours(string path) { return new ShopPiece { path = path, scale = 1f }; }     // 当方の駒(実寸)
        public ShopModule Measure() { return ModuleMeasure(path, scale); }
        public Vector3 Scale3 { get { return Vector3.one * scale; } }
        public string Name { get { return System.IO.Path.GetFileNameWithoutExtension(path); } }
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
    /// の触れている箇所。
    ///
    /// <para>⭐ **退ける門は、建った後の検査とまったく同じ測りでなければならない**(2026-09-22・EDO-0355)。
    /// ここは 2026-09-22 まで「基準点どうしの向き・頂点400・屋根を外す」で測っていて、区画の検査
    /// (<c>EdoTypologyBuilder</c> の `Kensa`)は「**外形の中心どうし**の向き・頂点800・**屋根込み**」で
    /// 測っていた。門の方が緩いので、門を通った棟が検査で ⛔ になる(実測: 新町 rb −0.12m /
    /// 田町 chos_0 −0.63m)。⛔ 検査を緩めて合わせない — **門を検査へ揃える**(規則19・許容0)。</para>
    ///
    /// <para>⛔ 向きを駒の基準点どうしから採らない — 基準点は部材ごとに端・角・中心とばらばらで、
    /// 長い駒では軸に沿った嘘のめり込みが出る(規則21)。**外形の中心どうし**で向ける。</para></summary>
    static bool Clashes(GameObject go, List<GameObject> others)
    {
        foreach (var o in others)
        {
            var d3 = RB(o).center - RB(go).center; d3.y = 0f;
            if (d3.sqrMagnitude < 1e-4f) return true;
            Vector3 at; int nc;
            float g = Contact(go, o, d3.normalized, out at, out nc, 0.01f, 0.5f, 800);
            if (!float.IsNaN(g) && g < 0f) return true;
        }
        return false;
    }

    /// <summary>**表店の辺の端の空き**(EDO-0503)── 辺 A→B のうち、店の**壁体**(屋根を外した実メッシュ)が店先の帯
    /// (線から内へ <paramref name="band"/> m)に掛かっていない**両端**の区間を、走りの座標 [t0, t1] で返す。
    /// 店の側の端は <paramref name="embed"/> だけ店へ食い込ませる(閉じは「隙間 &gt; めり込み」)。<paramref name="minGap"/> 以下の空きは返さない。
    /// どの店も掛からない辺は辺全部を返す。⛔ 列の中の路地(軒と軒の間)は返さない ── 路地口は町の型。
    /// ⭐ 測る相手は辺を問わず渡された店の全部(角では隣の辺の列の妻が端を受ける)。
    /// 当たる先: 類型ビルダーの囲い(表店の辺の端を建仁寺垣で閉じる)── 町屋の全区画。</summary>
    public static List<float[]> FrontEndGaps(Vector2 A, Vector2 B, Vector2 outward, List<GameObject> shops,
                                             float band = 2.0f, float minGap = 0.3f, float embed = 0.10f)
    {
        var dir = (B - A).normalized; float len = (B - A).magnitude; var inw = -outward;
        float lo = float.PositiveInfinity, hi = float.NegativeInfinity;
        foreach (var g in shops)
        {
            if (g == null) continue;
            foreach (var w in Body(g.transform, 800, false))
            {
                var q = new Vector2(w.x, w.z) - A;
                float d = Vector2.Dot(q, inw); if (d < -0.3f || d > band) continue;
                float t = Vector2.Dot(q, dir); if (t < -0.5f || t > len + 0.5f) continue;
                lo = Mathf.Min(lo, t); hi = Mathf.Max(hi, t);
            }
        }
        var r = new List<float[]>();
        if (float.IsInfinity(lo)) { r.Add(new[] { 0f, len }); return r; }
        if (lo > minGap) r.Add(new[] { 0f, Mathf.Min(len, lo + embed) });
        if (len - hi > minGap) r.Add(new[] { Mathf.Max(0f, hi - embed), len });
        return r;
    }

    static void Seat2(GameObject go, Vector2 at)
    {
        try { SeatOnGround(go, 0.05f, 600); }
        catch (Exception) { SeatBottom(go, Ground(at.x, at.y) - 0.05f); }
    }

    /// <summary>表店を建ててよい道の縦の勾配の上限【U】(EDO-0503)。考証の実測で山王坂の門前は平均 7.8%・最急 約 10% ──
    /// その坂には軒ごとの段で建つ。これを超える列の端は詰める。</summary>
    public const float MACHIYA_MAX_GRADE = 0.15f;

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
    /// 塀と違って建物は境界線の上に立つ物ではない(規則4「区域侵犯は許容0」)。
    /// ⭐ 測り方は類型ビルダーの検査(<c>EdoTypologyBuilder.OutsideBy</c>)と同じ <see cref="BodyExRoof"/>・600 点。
    /// ⛔ 2026-10-02 まで Body(400, false) で測っていて、検査だけが 0.07m の侵犯を拾った(門前1 の平屋の小店・EDO-0503)。</summary>
    static bool OutsideParcelStrict(Transform t, Vector2[] poly)
    {
        foreach (var w in BodyExRoof(t, 600))
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
        public float shopD;        // 据えた表店の**壁体**が境界線から奥へ食った最大[m](⛔ 在庫の駒の寸法で代用しない)
        public int clashed;        // 先に建った列にめり込むので退けた駒(両側町の角)
        public int abutted;        // 先に建った列の駒へ区間の端を突き付けた数(角を空けない・EDO-0503)
        public int tucked;         // 区画の内へ折り込んだ駒
        public float tuckedM;      // 同・最大の折り込み量[m]
        public float steepCutM;    // 道が急で列の端を詰めた長さ[m](EDO-0503・MACHIYA_MAX_GRADE)
        public List<List<GameObject>> houseList;   // 据えた軒ごとの駒(1 軒 = 1〜2 枚)── 暖簾を軒ごとに掛ける(EDO-0503 HangNoren)
        public string oursKind;    // 当方の駒を候補へ足したときのその名前(足さなければ null)
    }

    /// <summary>1 軒の間口 <paramref name="maguchiM"/> を、在庫の駒 1〜2 枚の組で埋める候補。
    /// 誤差の小さい順に返す。⭐ **1 種に決め打たない** — 全部おなじ組で埋めると、24 区画の通りが
    /// 同じ駒の等間隔の並びになる(`docs/typology-builder.md` の「⛔ 等間隔・同一個体」)。
    /// 採るのは「最良の誤差 + 0.5m」か「間口の 1/4」のどちらか広い方に入る組だけ。</summary>
    static List<ShopPiece[]> ShopCombos(ShopPiece[] stock, float maguchiM)
    {
        var cand = new List<ShopPiece[]>();
        foreach (var a in stock) cand.Add(new[] { a });
        foreach (var a in stock) foreach (var b in stock) cand.Add(new[] { a, b });
        Func<ShopPiece[], float> wid = c => { float w = 0f; foreach (var p in c) w += p.Measure().W; return w; };
        cand.Sort((x, y) => Mathf.Abs(wid(x) - maguchiM).CompareTo(Mathf.Abs(wid(y) - maguchiM)));
        float best = Mathf.Abs(wid(cand[0]) - maguchiM);
        float tol = Mathf.Max(best + 0.5f, maguchiM * 0.25f);
        var keep = new List<ShopPiece[]>();
        foreach (var c in cand)
        {
            if (Mathf.Abs(wid(c) - maguchiM) > tol) continue;
            // 同じ幅の組(S1+S2 と S2+S1)は並びの見た目が変わるので両方残す
            keep.Add(c);
        }
        return keep;
    }

    /// <summary>**列の残り長さを、繰り返し使える棟の実寸の組合せで埋める計画(掲示板 EDO-0362 §1d の型)。</summary>
    /// <remarks>
    /// <para>⛔ 「一番長い棟から順に試し、入らなくなったら一段短い棟へ落とす」(旧実装)では、
    /// 棟の桁行を九尺(1.5間)ピッチの戸数で揃えていても**端数がちょうど1戸ぶん残る**組合せを見落とす —
    /// 例えば残り9間に12間を先に置くと1間の穴が残るが、9間+4.5間なら丁度埋まる。EDO-0348→0355→0362 と
    /// 「無い寸法を一つ焼く」対症療法を3度繰り返したので、**組合せそのもの**を動的計画法で汎用に探す形にした。</para>
    /// <para>動的計画法(容量 <paramref name="target"/> を <paramref name="res"/> 刻みに量子化した
    /// 「無制限ナップサック・到達長の最大化」)。優先順位は ①埋まる長さがいちばん長い ②枚数がいちばん少ない
    /// ③(同数なら)大きい棟を使う — 裏店は同じ割りの棟を続けて建てた物なので、寸法を細切れに混ぜない
    /// (<see cref="UraNagayaRun"/> のコメント)。</para>
    /// <para><paramref name="widths"/> の各要素は継ぎ目を含まない実寸。<paramref name="joint"/> は
    /// 1枚ごとに足す(最後の1枚にも足す — 呼び手側の cursor の進め方と揃える)。戻り値は
    /// <paramref name="widths"/> の添字の列(置く順・sA に近い方から)。空配列 = 1枚も入らない
    /// (target が最小の棟より短い — その端数は呼び手が実測して gapM へ足すこと・規則19)。</para>
    /// </remarks>
    public static int[] TileWidths(float target, float[] widths, float joint, float res = 0.01f)
    {
        if (widths == null || widths.Length == 0 || target <= 0f) return new int[0];
        int n = Mathf.Max(0, Mathf.FloorToInt(target / res + 1e-4f));
        if (n <= 0) return new int[0];
        var step = new int[widths.Length];
        for (int i = 0; i < widths.Length; i++)
            step[i] = Mathf.Max(1, Mathf.RoundToInt((widths[i] + joint) / res));
        var dp = new int[n + 1];     // dp[c] = 容量 c 以下でいちばん埋まる長さ(コマ単位)
        var cnt = new int[n + 1];    // その枚数
        var pick = new int[n + 1];   // c で最後に置いた widths の添字(−1 = このコマには置かない=繰り越し)
        pick[0] = -1;
        for (int c = 1; c <= n; c++)
        {
            dp[c] = dp[c - 1]; cnt[c] = cnt[c - 1]; pick[c] = -1;      // 既定は繰り越し
            for (int i = 0; i < step.Length; i++)
            {
                if (step[i] > c) continue;
                int cand = step[i] + dp[c - step[i]];
                int candCnt = cnt[c - step[i]] + 1;
                bool better = cand > dp[c]
                    || (cand == dp[c] && candCnt < cnt[c])
                    || (cand == dp[c] && candCnt == cnt[c] && pick[c] >= 0 && widths[i] > widths[pick[c]]);
                if (better) { dp[c] = cand; cnt[c] = candCnt; pick[c] = i; }
            }
        }
        var rev = new List<int>();
        int cc = n;
        while (cc > 0)
        {
            if (pick[cc] < 0) { cc--; continue; }
            rev.Add(pick[cc]);
            cc -= step[pick[cc]];
        }
        rev.Reverse();
        return rev.ToArray();
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
    /// <param name="ours">当方で起こした表店の駒(実寸・**深い順**)。null なら在庫の 2 点だけ。
    /// ⭐ **奥行に収まる最初の 1 枚だけ**を候補へ足す(深い版が入らない辺では詰めた版へ落ちる)。
    /// 在庫の駒と同じ候補として <see cref="ShopCombos"/> に載るので、間口に合う駒が先に採られ、
    /// 合わなければ従来どおり在庫の駒を継ぐ。</param>
    /// <param name="keepInside">壁体がここから出る駒は置かない(区域侵犯は許容0・規則4)。null なら検めない。</param>
    /// <param name="seed">1 軒の埋め方を引く乱数の種(区画ごと・EDO-0476)。負なら列の名から。</param>
    /// <param name="maguchiMix">軒ごとに引く間口[m]の候補(表の `maguchi_mix`・EDO-0503)。null か 1 つ以下なら
    /// 全軒 <paramref name="maguchiM"/>。⭐ 間口が一つだと候補の組が 1 通りに縮み**同じ駒が等間隔に並ぶ**
    /// (山王門前の 4間 は Shop02 だけになっていた)。軒ごとに間口を引き、その間口の組から駒を引く。</param>
    public static List<GameObject> MachiyaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, float baseY,
        float maguchiM, float maxDepthM, Vector2 gapC, float gapHalf, string prefix,
        string leadPath, string[] ours, Vector2[] keepInside, List<GameObject> avoid, out MachiyaTally tally,
        int seed = -1, float[] maguchiMix = null)
    {
        float[] targets = (maguchiMix != null && maguchiMix.Length > 1) ? maguchiMix : new[] { maguchiM };
        if (targets.Length > 1) maguchiM = targets.Average();     // 軒数の見込み(wantHouses)は平均の間口で割る
        var made = new List<GameObject>();
        tally = new MachiyaTally();
        tally.houseList = new List<List<GameObject>>();
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
        var stock = new List<ShopPiece>();
        foreach (var p in new[] { EdoAssets.Eg.Shop01, EdoAssets.Eg.Shop02 })
        {
            var pc = ShopPiece.Kit(p);
            if (room > 0f && pc.Measure().D > room - 0.3f) continue;
            stock.Add(pc);
        }
        // 当方の駒: **幅と丈の組ごとに**奥行に収まる**最初の 1 枚**(深い版 → 詰めた版)。収まる版が無ければ足さない。
        // ⭐ 幅と丈で組を分ける(EDO-0503)— 間口を混ぜる区画では 2間・3間・5間の駒が同時に要り、
        //    同じ幅でも厨子二階と平屋(丈が違う)は**別の駒**として両方を候補に残す(軒線を揺らすため)。
        if (ours != null)
        {
            var oursW = new HashSet<int>(); var oursNames = new List<string>();
            foreach (var p in ours)
            {
                var pc = ShopPiece.Ours(p);
                var pm = pc.Measure();
                int wk = Mathf.RoundToInt(pm.W / 0.05f) * 1000 + Mathf.RoundToInt(pm.height / 0.25f);
                if (oursW.Contains(wk)) continue;
                if (room > 0f && pm.D > room - 0.3f) continue;
                stock.Add(pc); oursW.Add(wk); oursNames.Add(pc.Name);
            }
            if (oursNames.Count > 0) tally.oursKind = string.Join(" / ", oursNames.ToArray());
        }
        if (stock.Count == 0) stock.Add(ShopPiece.Kit(EdoAssets.Eg.Shop01));   // 奥行が足りなくても 1 種は残す(呼び手が刷る)
        var combosBy = new List<List<ShopPiece[]>>();
        var comboNames = new HashSet<string>();
        foreach (var tm in targets)
        {
            var cs = ShopCombos(stock.ToArray(), tm);
            combosBy.Add(cs);
            foreach (var c in cs) comboNames.Add(string.Join("+", c.Select(x => x.Name).ToArray()));
        }
        tally.comboKinds = comboNames.Count;

        // 木戸の開口で区間を割る(NagayaRun と同じ割り方)
        var segs = new List<float[]>();
        if (gapHalf > 0f)
        {
            float gT = Vector2.Dot(gapC - sA, rdir);
            if (gT - gapHalf > 0f) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });

        // ⭐ 列の両端は**側の辺が鋭角に入る所**で、店の奥の隅が区画の外へ出る。先に端を内へ詰めておく(硬い: 区域侵犯 許容0)。
        //    ⛔ 2026-10-02 まで詰めずに並べ、端の 1 枚が側の辺から 0.7m 出て(折り込みの上限 0.6m 超)丸ごと退けられ、
        //    門前1 の木戸の脇に 7m の空きが残った(施主指摘)。詰める量 = 奥行いちばん深い駒の矩形が入るまで(0.05m 刻み・上限 4m)。
        if (keepInside != null && stock.Count > 0)
        {
            float dMax = stock.Max(p => p.Measure().D);
            var inw = -outward;
            Func<float, float, bool> fits = (t0, t1) =>
            {
                foreach (var t in new[] { t0, t1 })
                    foreach (var d in new[] { 0.05f, dMax * 0.5f, dMax })
                        if (!EdoGeom.PIP(keepInside, sA + rdir * t + inw * d)) return false;
                return true;
            };
            foreach (var sg in segs)
            {
                if (sg[0] <= 0.01f) { float k = 0f; while (k < 4f && !fits(sg[0] + k, sg[0] + k + 0.5f)) k += 0.05f; if (k > 0f && k < 4f) sg[0] += k + 0.02f; }
                if (sg[1] >= len - 0.01f) { float k = 0f; while (k < 4f && !fits(sg[1] - k - 0.5f, sg[1] - k)) k += 0.05f; if (k > 0f && k < 4f) sg[1] -= k + 0.02f; }
            }
        }
        // ⭐ 列の端で**道が急に落ちる所**には店を建てない(柔らかい: 列を詰めて ⚠ で刷る)── 店先の土間は軒ごとに道へ合わせるので、
        //    道の縦の勾配が MACHIYA_MAX_GRADE を超える所では一軒の中で段が付けられない。急坂は町家の型ではない(EDO-0503 考証【B】:
        //    石段・石垣の上の長屋は九段坂のような急坂の型で、8〜10% の坂には当てない)。
        //    ⛔ 2026-10-02 まで詰めず、門前4 の東の端(道が 4m で 2m 落ちる)の店が布石 1.6m の上に載った。
        {
            Func<float, float> roadAt = tt => { var q = sA + rdir * tt + outward * 0.5f; return RoadY(q.x, q.y); };
            Func<float, float, bool> steep = (t0, t1) =>
            {
                float y0 = roadAt(t0), y1 = roadAt(t1);
                return !float.IsNaN(y0) && !float.IsNaN(y1) && Mathf.Abs(y1 - y0) / Mathf.Max(0.1f, t1 - t0) > MACHIYA_MAX_GRADE;
            };
            foreach (var sg in segs)
            {
                float k = 0f; while (sg[0] + k + 2f < sg[1] && steep(sg[0] + k, sg[0] + k + 2f)) k += 0.25f;
                if (k > 0f) { sg[0] += k; tally.steepCutM += k; }
                k = 0f; while (sg[1] - k - 2f > sg[0] && steep(sg[1] - k - 2f, sg[1] - k)) k += 0.25f;
                if (k > 0f) { sg[1] -= k; tally.steepCutM += k; }
            }
        }

        // ⭐ 後に建てる列(両側町・辻の角の extra_front)は、**先に建った列の駒が占める所**まで区間を詰め、
        //    その端へ軒を突き付けて並べる(柔らかい: 狙いは隙0・軒の出の分は残る)。測るのは先の駒の**実メッシュ**
        //    (屋根込み=軒の出まで)を、この辺の店の奥行の帯に落とした走りの座標。⛔ 外接箱・ピボットで測らない(規則21)。
        //    ⛔ 2026-10-02 まで詰めずに中寄せで並べ、角の 1 軒が先の列にめり込んで退けられ、残った軒との間に
        //    2.4m の空きが残った(門前1 の辻の角・施主指摘「東側に変なすき間」)。
        var abutLo = new bool[segs.Count]; var abutHi = new bool[segs.Count];
        if (avoid != null && avoid.Count > 0 && stock.Count > 0)
        {
            float band = stock.Max(p => p.Measure().D) + 0.3f;
            var inw = -outward;
            var pts = new List<Vector2>();
            foreach (var o in avoid)
                if (o != null)
                    foreach (var w in Body(o.transform, 800, true))
                    {
                        var q = new Vector2(w.x, w.z) - sA;
                        float dd = Vector2.Dot(q, inw);
                        if (dd >= -0.5f && dd <= band) pts.Add(new Vector2(Vector2.Dot(q, rdir), dd));
                    }
            for (int si = 0; si < segs.Count; si++)
            {
                var sg = segs[si]; float mid = (sg[0] + sg[1]) * 0.5f;
                float lo = float.NaN, hi = float.NaN;
                foreach (var p in pts)
                {
                    if (p.x < sg[0] - 1f || p.x > sg[1] + 1f) continue;
                    if (p.x < mid) lo = float.IsNaN(lo) ? p.x : Mathf.Max(lo, p.x);
                    else hi = float.IsNaN(hi) ? p.x : Mathf.Min(hi, p.x);
                }
                if (!float.IsNaN(hi)) { sg[1] = Mathf.Min(sg[1], hi - 0.05f); abutHi[si] = true; tally.abutted++; }
                if (!float.IsNaN(lo)) { sg[0] = Mathf.Max(sg[0], lo + 0.05f); abutLo[si] = true; tally.abutted++; }
            }
        }

        // ⭐ 種は呼び手が区画ごとに渡す(EDO-0476)。⛔ 列の名(prefix)だけで種を作らない ── 2026-09-29 まで
        //    `prefix.GetHashCode()` で、名が "Omotedana0" の 24 区画が同じ順で同じ組を引いていた。
        var rnd = new System.Random(seed >= 0 ? seed : Seed(prefix));
        var kinds = new Dictionary<string, int>();
        int idx = 0;
        ShopPiece? lead = leadPath != null ? (ShopPiece?)ShopPiece.Kit(leadPath) : null;   // 頭の 1 枚は最初の区間の最初の軒でだけ使う

        for (int si = 0; si < segs.Count; si++)
        {
            var seg = segs[si];
            float segLen = seg[1] - seg[0];
            if (segLen < 1.0f) continue;

            // ── 下読み: この区間に何軒が何枚で入るか(まだ置かない)──
            var rows = new List<List<ShopPiece>>();
            float total = 0f;
            while (true)
            {
                var row = new List<ShopPiece>();
                float w = 0f;
                bool usedLead = lead != null;
                if (usedLead)
                {
                    row.Add(lead.Value); w += lead.Value.Measure().W;
                    // 残りを在庫の駒で埋める(1 枚だけ・入らなければ番屋 1 枚で 1 軒とする)
                    ShopPiece? fill = null; float bestErr = float.MaxValue;
                    foreach (var p in stock)
                    {
                        float err = Mathf.Abs(w + p.Measure().W - maguchiM);
                        if (err < bestErr) { bestErr = err; fill = p; }
                    }
                    if (fill != null && Mathf.Abs(w - maguchiM) > bestErr) { row.Add(fill.Value); w += fill.Value.Measure().W; }
                }
                else
                {
                    // ⛔ 間口が一つのときは乱数を余計に引かない — 引けば他の区画の並びまで変わる
                    var combos = combosBy[targets.Length > 1 ? rnd.Next(targets.Length) : 0];
                    var c = combos[rnd.Next(combos.Count)];
                    foreach (var p in c) { row.Add(p); w += p.Measure().W; }
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

            // 先の列へ突き付ける端には路地も余りも置かない(片端だけ突き付けるとき、余りは反対の端へ寄せる)
            float cursor = (abutHi[si] && !abutLo[si]) ? seg[0] + rest + 2f * roji
                         : (abutLo[si] && !abutHi[si]) ? seg[0]
                         : seg[0] + rest * 0.5f + roji;
            foreach (var row in rows)
            {
                var houseGo = new List<GameObject>();
                foreach (var pc in row)
                {
                    var m = pc.Measure();
                    // ローカル +X ∥ rdir なので、軒の低い端が cursor に来るピボットの走り座標
                    var c2 = sA + rdir * (cursor - m.lo);
                    var go = Place(pc.path, new Vector3(c2.x, baseY, c2.y), psi, pc.Scale3, parent,
                                   prefix + "_" + idx + "_" + pc.Name);
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
                    // ⭐ **据えた駒が奥へ何 m 食ったか**を実測する(2026-09-22・EDO-0355)。裏長屋の列の
                    //    引きはこれと路地から決まる。⛔ 在庫の Shop01/02 の寸法で代用しない —
                    //    当方の 5 間の駒は Shop02 より 0.36m 深く、その分だけ路地が痩せて棟へめり込む。
                    foreach (var w in Body(go.transform, 400, false))
                    {
                        float dd = -((w.x - A.x) * outward.x + (w.z - A.y) * outward.y);
                        if (dd > tally.shopD) tally.shopD = dd;
                    }
                    int cnt; string nm = pc.Name;
                    kinds.TryGetValue(nm, out cnt); kinds[nm] = cnt + 1;
                    tally.builtM += m.W;
                    // 軒の出のぶん、界壁には必ず隙が残る(閉じは「隙間 > めり込み」)。実寸から出して刷る。
                    tally.wallGapM = Mathf.Max(tally.wallGapM, (m.hi - m.wHi) + (m.wLo - m.lo));
                    cursor += m.W + JOINT;            // 継ぎ目は軒の実寸 + 髪一筋
                }
                if (houseGo.Count > 0) { tally.houses++; tally.houseList.Add(houseGo); }
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
    /// 高さは**触れている箇所**を測って据える。桁行は 12/9/6/4.5/3 間の中から<see cref="TileWidths"/>
    /// (EDO-0362 §1d の型)が組合せで決める — 一番長い棟から機械的に試す旧実装は、1.5間(1戸)ぶんだけ
    /// 残って埋まらない端数を見落とすことがあった。</para>
    ///
    /// <param name="cap">置く棟数の上限(表の `ura_nagaya` が数で書いてあるとき)。0 以下なら上限なし。</param>
    /// <param name="wallGap">返り: 棟どうしの**触れている箇所**の隙の最小[m](負 = めり込み)。</param>
    /// <param name="gapM">返り: 据わる棟が無くて**歯抜けのまま残した走り**の合計[m](EDO-0355)。
    /// ⭐ 2026-09-22(EDO-0362)から**列の末尾で TileWidths がどの組合せも見つけられなかった端数**
    /// (1.5間=1戸ぶん未満。理屈のうえで必ず残りうる)も同じ変数に足す — 以前はこの端数が黙って
    /// 素通りしていた(規則19)。⛔ 0 でない値を呼び手が黙って飲まない — 通りの裏に空いた穴の実測。</param>
    /// <param name="munewari">⭐ **棟割長屋**(奥行4間・大棟を挟んで ±Z の両面に戸)で積む
    /// (<see cref="EdoAssets.Own.UraNagayaMunewari(float)"/>)。**路地が前後にある列**はこちらが正しい姿で、
    /// 1棟が路地2本ぶんを受け持つ。⛔ 割長屋を2棟背中合わせに置いて代用しない(部材の注記)。
    /// ⚠ 列の**いちばん奥**(背が隣地の境に向く列)は盲面が要るので false = 割長屋のまま。</param>
    public static List<GameObject> UraNagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward,
        float baseY, float insetM, int cap, string prefix, Vector2[] keepInside,
        List<GameObject> avoid, out int dropped, out float wallGap, out float gapM, bool munewari = false)
    {
        var made = new List<GameObject>();
        dropped = 0; wallGap = float.NaN; gapM = 0f;
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;   // 戸の面(+Z)を路地へ
        Vector2 xdirW = new Vector2(outward.y, -outward.x);
        Vector2 sA = A, rdir = dir;
        if (Vector2.Dot(dir, xdirW) < 0f) { sA = B; rdir = -dir; }
        // 線を敷地の内へ下げる(内向き = −outward)
        Vector2 inw = -outward;
        sA += inw * insetM;

        // 桁行の候補(降順)。⭐ 表店と違って乱さない — 裏店は同じ割りの棟を続けて建てた物で、
        //    長さを混ぜるほど棟の天端が刻まれて長屋らしさが消える(TileWidths の③大きい棟を優先、で担保)。
        //    どの組合せでも埋まらない端数(1.5間=1戸ぶん未満)だけが列の終わりに残る。
        //
        // ⭐ **退けた棟の幅だけカーソルを飛ばさない**(2026-09-22・EDO-0355)。飛ばすと、退けた駒の
        //    走り(12 間 = 21.8m にもなる)がそのまま通りの裏の**歯抜け**として残る。退けたら同じ座で
        //    **一段短い棟**へ落として掛け直し、どれも据わらない座だけ 1 間ずつ送る。
        //    送った分は <paramref name="gapM"/> に実測で返す(⛔ 黙って飲まない・規則19)。
        //
        // ⭐ **走りの本体は大きい棟から順に、列末の端数だけ TileWidths の組合せで埋める**
        //    (2026-09-22・EDO-0362 §1d を実測で修正)。端数だけに効かせるのは、掛け直しの段が
        //    大きい順にしか効かないため — 下の while の中の注記が理屈。桁行の寸法をこれ以上
        //    増やさなくても、端数は 12/9/6/4.5/3 間の組合せで 1 戸ぶん未満まで詰まる。
        var lens = new float[] { 12f, 9f, 6f, 4.5f, 3f };
        var lensW = new float[lens.Length];
        for (int i = 0; i < lens.Length; i++)
        {
            var path = munewari ? EdoAssets.Own.UraNagayaMunewari(lens[i]) : EdoAssets.Own.UraNagaya(lens[i]);
            lensW[i] = OwnMeasure(path).W;
        }
        const float STEP = 1.818f;                         // 据わらない座を送る刻み(江戸間 1 間)
        float cursor = 0f;
        int idx = 0;
        int li = -1;                                        // li<0 = 次の反復で TileWidths から引き直す
        int guard = 0;
        while (cursor < len - 0.5f && guard++ < 500)
        {
            if (cap > 0 && made.Count >= cap) break;
            float remaining = len - cursor;
            if (li < 0)
            {
                // ⭐ **走りの本体は大きい棟から**(2026-09-22・EDO-0362 の実測で差し戻し)。
                //    TileWidths は「いちばん埋まる組合せ」を返すので小さい棟を好むが、それを
                //    そのまま座の第一候補にすると**退けたときの掛け直しの段が下に無くなる**。
                //    同じ座では幅の広い棟は狭い棟の走りを覆うので、狭い棟が退けられたなら広い棟も
                //    必ず退けられる ⇒ 掛け直しは**大きい順にしか効かない**。小さい棟から始めると
                //    退けがそのまま 1 間の歯抜けになり、しかも座の数が増えて退けの機会も増える
                //    (実測: 10区画で歯抜け 98.2m → 171.1m・退け 101回 へ悪化した)。
                // ⭐ TileWidths を効かせるのは**列末の端数だけ** — 残りが一番大きい棟に足りなくなって
                //    はじめて組合せを引く(9間+4.5間で埋まる所に6間を置いて 3.5m 余らせない)。
                if (remaining >= lensW[0]) li = 0;
                else
                {
                    var plan = TileWidths(remaining, lensW, JOINT);
                    if (plan.Length == 0) { gapM += remaining; break; }   // どの棟も残り(1.5間未満)に入らない — 列の終わり
                    li = plan[0];
                }
            }
            string pick = null; ShopModule pm = default(ShopModule);
            for (int t = li; t < lens.Length; t++)
            {
                var path = munewari ? EdoAssets.Own.UraNagayaMunewari(lens[t]) : EdoAssets.Own.UraNagaya(lens[t]);
                var m = OwnMeasure(path);
                if (cursor + m.W <= len + 0.01f) { pick = path; pm = m; li = t; break; }
            }
            if (pick == null) { gapM += remaining; break; }  // 一番短い棟も走りに入らない = 列の終わり
            var c2 = sA + rdir * (cursor - pm.lo);
            var go = Place(pick, new Vector3(c2.x, baseY, c2.y), psi, Vector3.one, parent,
                           prefix + "_" + idx + "_" + System.IO.Path.GetFileNameWithoutExtension(pick));
            var rb = RB(go);
            AlignFace(go, sA, outward, 0f, rb.min.y + 0.30f, rb.min.y + rb.size.y * 0.60f);
            try { SeatOnGround(go, 0.05f, 600); }
            catch (Exception) { SeatBottom(go, Ground(c2.x, c2.y) - 0.05f); }
            bool reject = false;
            if (keepInside != null)
            {
                // ⛔ 塀の 0.60m の遊びを建物に使わない(規則4「区域侵犯は許容0」)。
                //    折り込んで収まらない棟だけ退ける。
                float tk = TuckIntoParcel(go, keepInside, -outward, 0.60f);
                if (tk < 0f) reject = true;
                else if (tk > 0f) Seat2(go, c2);
            }
            // ⛔ 両側町は**もう一方の通りの表店が背後まで回り込んでいる**(2026-09-21 実測:
            //    新町三丁目で −5.03m)。先に建った駒とめり込む棟は退ける。
            if (!reject && avoid != null && Clashes(go, avoid)) reject = true;
            if (reject)
            {
                UnityEngine.Object.DestroyImmediate(go);
                dropped++;
                if (li + 1 < lens.Length) { li++; continue; }       // 同じ座で一段短い棟へ掛け直す
                gapM += STEP; cursor += STEP; li = -1; continue;    // どれも据わらない座 — 1 間送って計画を引き直す
            }
            made.Add(go); idx++;
            cursor += pm.W + JOINT; li = -1;                        // 次の座は TileWidths で引き直す
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

    // ───────────────────────── 町木戸(EDO-0503 ②)─────────────────────────
    /// <summary>**道を塞ぐ町木戸を、道の両側の角 <paramref name="a"/>・<paramref name="b"/> の間に据える。**
    /// 置き方は札の**脇の面**(<c>jambL</c>/<c>jambR</c>)が両角に触れるように決める(⛔ ピボットで寄せない・規則21)。
    /// 外(+Z)は <paramref name="away"/>(町の外 = 区画の無い側)へ向ける。高さは <see cref="SeatGamae"/>(札の当たり)。
    /// 【硬い】札の脇の面の間隔と角どうしの距離の差が 0.02m を超えたら**建てない**(隙か区域侵犯になる)── 幅を焼き直す。
    /// 返り値の <paramref name="note"/> に脇の面と角の差・据えた高さ・浮きを刷る(規則19)。</summary>
    /// <summary>町木戸の口の**横断の下がり**[m](木戸の局所 −X 端 → +X 端・正 = +X が低い・0.05 刻み)。
    /// 向きは <see cref="MachiKidoAcross"/> と同じ決め方(X = 角どうしの線・+Z = away の側)。地面は両角から 0.3m 内で採る。
    /// 呼ぶ側はこの値で <c>EdoAssets.Own.MachiKido(haba, keisha)</c> の駒を引く(EDO-0503)。</summary>
    public static float MachiKidoKeisha(Vector2 a, Vector2 b, Vector2 away)
    {
        var ab = (b - a).normalized; var n = new Vector2(-ab.y, ab.x);
        if (Vector2.Dot(n, away) < 0f) n = -n;
        var lx = new Vector2(n.y, -n.x);
        var aL = Vector2.Dot(a - b, lx) < 0f ? a : b; var aR = aL == a ? b : a;
        var pL = aL + lx * 0.3f; var pR = aR - lx * 0.3f;
        float drop = (Ground(pL.x, pL.y) - Ground(pR.x, pR.y)) * (b - a).magnitude / Mathf.Max(0.1f, (pR - pL).magnitude);
        return Mathf.Round(drop / 0.05f) * 0.05f;
    }

    public static GameObject MachiKidoAcross(Transform parent, string path, Vector2 a, Vector2 b, Vector2 away, string name, out string note, float keisha = 0f)
    {
        var sp = EdoPartSpec.Get(path);
        if (sp == null || sp.jambL == null || sp.jambR == null) { note = "⛔ 町木戸: 札が無い/脇の面が無い — " + System.IO.Path.GetFileName(path); return null; }
        float s = sp.unitScale > 0f ? sp.unitScale : 1f;
        float span = (sp.jambR.x - sp.jambL.x) * s, road = (b - a).magnitude;
        if (Mathf.Abs(span - road) > 0.02f)
        { note = string.Format("⛔ 町木戸: 札の脇の面の間隔 {0:F3}m と道の角どうし {1:F3}m が合わない(差 {2:+0.000;-0.000}m)── この幅で焼き直す(建てない)", span, road, span - road); return null; }
        // ⭐ 木戸の X(幅)は**角どうしを結ぶ線**そのもの、+Z はその法線のうち away の側。
        //    ⛔ away から X を起こさない — 二区画の重心から離れる向きは口の線に直交しないので、
        //    片方の親柱が角から 2.555m 離れた(2026-10-02 門前1)。
        var ab = (b - a).normalized;
        var n = new Vector2(-ab.y, ab.x);
        if (Vector2.Dot(n, away) < 0f) n = -n;
        float ry = Mathf.Atan2(n.x, n.y) * Mathf.Rad2Deg;
        var lx = new Vector2(n.y, -n.x);                       // ローカル +X の世界での向き(= ±ab)
        var aL = Vector2.Dot(a - b, lx) < 0f ? a : b;           // jambL(−X)が触れる角
        float zc = (sp.jambL.z0 + sp.jambL.z1) * 0.5f * s;
        var p2 = aL - lx * (sp.jambL.x * s) - n * zc;
        var go = Place(path, new Vector3(p2.x, Ground(p2.x, p2.y), p2.y), ry, Vector3.one * s, parent, name);
        // ⭐ 勾配の版(<paramref name="keisha"/>≠0)は**ピボット = 足形の中心の地面**で焼いてある(柱の足元が勾配なりに伸びる)──
        //    中心の地面へピボットを置く。⛔ SeatGamae(最下点で当てる)を通すと下手の柱の根で当たり、全体が沈む(部材方 2026-10-02)。
        if (Mathf.Abs(keisha) >= 0.025f)
        {
            var c = go.transform.position; go.transform.position = new Vector3(c.x, Ground(c.x, c.z), c.z);
        }
        else SeatGamae(go, 4000);
        var jl = EdoPartSpec.JambWorld(go.transform, sp.jambL); var jr = EdoPartSpec.JambWorld(go.transform, sp.jambR);
        var bL = aL == a ? b : a;
        var r = RootToBed(go, Ground, 0.1f, GamaeContact(go));
        if (!float.IsNaN(r.hi) && r.hi > 0.01f && Mathf.Abs(keisha) >= 0.025f)
        {   // 実際の地面は勾配の直線より上に曲がる所がある(±5cm)── 浮いた分だけ下げる(根入れが深くなるだけ)
            go.transform.position -= new Vector3(0f, r.hi, 0f);
            r = RootToBed(go, Ground, 0.1f, GamaeContact(go));
        }
        note = string.Format("  町木戸: 道幅 {0:F2}m を塞いだ・脇の面と角の差 {1:F3}m / {2:F3}m・敷居 y={3:F2}・当たりの浮き {4:F3}m(硬い ±0.01){5}",
                             road, (jl - aL).magnitude, (jr - bL).magnitude, go.transform.position.y,
                             float.IsNaN(r.hi) ? 0f : Mathf.Max(0f, r.hi), (!float.IsNaN(r.hi) && r.hi > 0.01f) ? " ⛔ 道の傾きで下手が浮く" : "");
        return go;
    }

    // ───────────────────────── 暖簾(EDO-0503)─────────────────────────
    static List<Dictionary<string, object>> _noren;
    /// <summary>`docs/Sashizu/noren.json` の店の一覧(<see cref="EdoAssets.Eg.NorenSpec"/>)。</summary>
    public static List<Dictionary<string, object>> NorenVariants()
    {
        if (_noren != null) return _noren;
        _noren = new List<Dictionary<string, object>>();
        var root = EdoMiniJson.Parse(System.IO.File.ReadAllText(EdoAssets.Eg.NorenSpec)) as Dictionary<string, object>;
        object vs; if (root == null || !root.TryGetValue("variants", out vs)) return _noren;
        foreach (var o in (List<object>)vs) { var d = o as Dictionary<string, object>; if (d != null) _noren.Add(d); }
        return _noren;
    }

    /// <summary>**表店に軒ごとの暖簾を掛ける。**<paramref name="keys"/> は掛けてよい店(noren.json の key・重複は軒数の比)。
    /// 種で並べ替えた順に**一巡ずつ**配り、隣の軒と同じ店は続けない。1 軒(駒 1〜2 枚)は同じ店。
    /// 当たる先: 在庫の表店 shop01・shop02 の駒(画像を焼いた材で**全スロット**を差し替える)と、
    /// 当方の表店(`Own.Typ.Omotedana*`)の**名前が Noren で始まるスロットだけ**(キットの暖簾の材を
    /// 複製して地色を noren.json の color にした材・`NorenMat("kit", key)`)。
    /// 材は `EdoAssets.Eg.NorenMat` に一度だけ起こす。画像が無ければ ⚠ を返して素の材(BareTex)のまま。</summary>
    public static string HangNoren(List<List<GameObject>> houses, string[] keys, int seed)
    {
        if (houses == null || houses.Count == 0 || keys == null || keys.Length == 0) return "暖簾: 掛ける軒が無い";
        var rnd = new System.Random(seed);
        var deck = new List<string>(); string prev = null; int hung = 0; var missing = new HashSet<string>();
        var count = new Dictionary<string, int>();
        foreach (var house in houses)
        {
            if (deck.Count == 0) { deck.AddRange(keys); for (int i = deck.Count - 1; i > 0; i--) { int j = rnd.Next(i + 1); var t = deck[i]; deck[i] = deck[j]; deck[j] = t; } }
            int pick = 0;
            while (pick < deck.Count - 1 && deck[pick] == prev) pick++;   // 隣と同じ店を続けない
            string key = deck[pick]; deck.RemoveAt(pick); prev = key;
            bool any = false;
            foreach (var go in house)
            {
                var src = PrefabUtility.GetCorrespondingObjectFromOriginalSource(go);
                string sp = src != null ? AssetDatabase.GetAssetPath(src) : null;
                string shop = sp == EdoAssets.Eg.Shop01 ? "shop01" : sp == EdoAssets.Eg.Shop02 ? "shop02" : null;
                if (shop == null)
                {
                    // 当方の駒: 暖簾の材スロットだけ地色を替える(EDO-0503 ⑥ — 小店を混ぜると暖簾が全部藍に戻るため)
                    bool ok = false;
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                    {
                        var ms = r.sharedMaterials; bool ch = false;
                        for (int i = 0; i < ms.Length; i++)
                        {
                            if (ms[i] == null || !ms[i].name.StartsWith("Noren")) continue;
                            var km = NorenKitMaterial(ms[i], key);
                            if (km == null) { missing.Add("kit_" + key); continue; }
                            ms[i] = km; ch = true;
                        }
                        if (ch) { r.sharedMaterials = ms; ok = true; }
                    }
                    if (ok) any = true;
                    continue;
                }
                var m = NorenMaterial(shop, key);
                if (m == null) { missing.Add(shop + "_" + key); continue; }
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    var ms = r.sharedMaterials;
                    for (int i = 0; i < ms.Length; i++) ms[i] = m;
                    r.sharedMaterials = ms;
                }
                any = true;
            }
            if (any) { hung++; int c; count.TryGetValue(key, out c); count[key] = c + 1; }
        }
        var parts = new List<string>(); foreach (var kv in count) parts.Add(kv.Key + "×" + kv.Value);
        return "暖簾: " + hung + "/" + houses.Count + " 軒に掛けた(" + string.Join(" ", parts.ToArray()) + ")"
             + (missing.Count > 0 ? " / ⚠ 画像が無い " + string.Join(",", new List<string>(missing).ToArray()) + " ── python3 Tools/Unity/bake_noren.py" : "");
    }

    /// <summary>キットの暖簾の材(<paramref name="kit"/>)を複製し、地色を noren.json の `color` にした材。
    /// ⛔ 材のパスを書かない(規則12)— 複製の元は駒に今付いている材そのもの。</summary>
    static Material NorenKitMaterial(Material kit, string key)
    {
        string mp = EdoAssets.Eg.NorenMat("kit", key);
        var m = AssetDatabase.LoadAssetAtPath<Material>(mp);
        if (m != null) return m;
        Dictionary<string, object> v = null;
        foreach (var nv in NorenVariants()) if (nv["key"].ToString() == key) { v = nv; break; }
        object co; if (v == null || !v.TryGetValue("color", out co) || !(co is List<object>)) return null;
        var cl = (List<object>)co;
        var c = new Color(Convert.ToSingle(cl[0]) / 255f, Convert.ToSingle(cl[1]) / 255f, Convert.ToSingle(cl[2]) / 255f, 0f);
        m = new Material(kit);
        foreach (var prop in new[] { "_ColorB", "_Color_B" }) if (m.HasProperty(prop)) m.SetColor(prop, c);
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(mp));
        AssetDatabase.CreateAsset(m, mp);
        return m;
    }

    static Material NorenMaterial(string shop, string key)
    {
        string mp = EdoAssets.Eg.NorenMat(shop, key);
        var m = AssetDatabase.LoadAssetAtPath<Material>(mp);
        if (m != null) return m;
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(EdoAssets.Eg.NorenTex(shop, key));
        if (tex == null) return null;
        m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        m.SetTexture("_BaseMap", tex); m.mainTexture = tex;
        m.SetFloat("_Smoothness", 0.15f);
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(mp));
        AssetDatabase.CreateAsset(m, mp);
        return m;
    }
}
