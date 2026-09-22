// 庭の置き方 — 類型の庭(Stage 5・EDO-0323)が使う「置く・測る・据える」だけ。
//
// ⛔ ここに「どの類型が何を持つか」を書かない(それは EdoTypologyBuilder.Niwa.cs の持ち場・規則21)。
// ⛔ 部材の基準点(ピボット・bounds の中心)で位置を決めない。据えるのは接地箇所を測る SeatOnGround。
// ⭐ 樹冠の半径は**据えた駒の実バウンズ**で測り直す — 名前や丈から推し量らない・中心点だけで退避を
//    判定しない(樹冠が長屋の屋根と軒を貫く)。庭方 2026-09-21 の設計 §5-0「退避」。
// ⭐ 乱れは4つ全部(芯々・yaw・等方スケール・個体)に掛ける。1つ欠けると並木に見える(§5-0「乱れ」)。
//
// ⭕ Seed / PartSize / CrownR は EDO-0317 の申し送り(未コミットの WIP)から引き取った。
//    ⛔ EdoBuildRun.cs に同じ物を二重に置かないこと(EDO-0324 の担当へ申し送り済)。

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    // ═══════════════════════ 部材を測る ═══════════════════════

    /// <summary>文字列から**版を跨いで同じ**乱数の種を作る。⛔ `string.GetHashCode()` を使わない —
    /// .NET は実行ごとに撹拌するので、同じ区画が開き直すたび別の姿になる(類型は決定的であること)。FNV-1a。</summary>
    public static int Seed(string s)
    {
        unchecked
        {
            uint h = 2166136261u;
            for (int i = 0; i < s.Length; i++) { h ^= s[i]; h *= 16777619u; }
            return (int)(h & 0x7fffffff);
        }
    }

    static readonly Dictionary<string, Vector3> _partSize = new Dictionary<string, Vector3>();

    /// <summary>部材の**実メッシュの外形**(scale=1・yaw=0 の Renderer bounds の大きさ)。一度だけ仮置きして測る。
    /// ⛔ 名前・丈・呼び寸法から推し量らない(規則21)。⛔ 部材が無ければ Vector3.zero(呼び手が声を上げる)。</summary>
    public static Vector3 PartSize(string path)
    {
        Vector3 v;
        if (_partSize.TryGetValue(path, out v)) return v;
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf == null) { _partSize[path] = Vector3.zero; return Vector3.zero; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one;
        v = RB(go).size;
        UnityEngine.Object.DestroyImmediate(go);
        _partSize[path] = v;
        return v;
    }

    /// <summary>**樹冠(や駒)の平面の半径**[m] — 実メッシュの XZ の大きい方の半分(scale=1 のとき)。
    /// ⛔ 名前や丈から推定しない(庭方 §5-0)。⛔ 0 が返ったら部材が無い — 黙って置かない。</summary>
    public static float CrownR(string path)
    {
        var s = PartSize(path);
        return Mathf.Max(s.x, s.z) * 0.5f;
    }

    // ═══════════════════════ 実メッシュの占め — 最近傍の距離を安く問う ═══════════════════════

    /// <summary>実メッシュの標本を 1m の升へ撒いて、「この点から一番近い実メッシュまで何 m か」を
    /// 打ち切り付きで返す。⭐ 軒の外形・囲いの壁体を**点群のまま**持つので、回った棟・L字の棟・
    /// 斜めの塀でも外接箱の膨らましのような嘘が出ない(§5-4 ④)。</summary>
    public class NiwaOcc
    {
        const float C = 1.0f;
        readonly Dictionary<long, List<Vector2>> _g = new Dictionary<long, List<Vector2>>();
        public int Count;

        static long Key(int ix, int iz) { return ((long)ix << 32) ^ (uint)iz; }

        public void Add(Vector2 p)
        {
            long k = Key(Mathf.FloorToInt(p.x / C), Mathf.FloorToInt(p.y / C));
            List<Vector2> L;
            if (!_g.TryGetValue(k, out L)) { L = new List<Vector2>(); _g[k] = L; }
            L.Add(p); Count++;
        }

        /// <summary>駒の実メッシュ(<paramref name="withRoof"/> で軒込み/壁体だけ)を撒く。</summary>
        public void AddBody(Transform t, int maxSamples, bool withRoof)
        {
            foreach (var w in Body(t, maxSamples, withRoof)) Add(new Vector2(w.x, w.z));
        }

        /// <summary>最近傍までの距離[m]。<paramref name="cap"/> を超える分は測らず cap を返す(打ち切り)。
        /// ⭐ 何も撒かれていなければ cap(= 相手が居ない)。</summary>
        public float Dist(Vector2 p, float cap)
        {
            if (_g.Count == 0) return cap;
            int rr = Mathf.CeilToInt(cap / C);
            int cx = Mathf.FloorToInt(p.x / C), cz = Mathf.FloorToInt(p.y / C);
            float best = cap;
            for (int ix = cx - rr; ix <= cx + rr; ix++)
                for (int iz = cz - rr; iz <= cz + rr; iz++)
                {
                    List<Vector2> L;
                    if (!_g.TryGetValue(Key(ix, iz), out L)) continue;
                    for (int i = 0; i < L.Count; i++)
                    {
                        float d = Vector2.Distance(p, L[i]);
                        if (d < best) best = d;
                    }
                }
            return best;
        }
    }

    /// <summary>門の**通り抜けの実開口**を実メッシュから測る[m]。⭐ 参道の帯(白洲)の幅はこれで決まる
    /// (庭方 §5-0 c「門の実開口幅/2 + 1.5」)。⛔ 門構え全体の幅を開口と呼ばない — 長屋門は両翼が
    /// 長屋(壁体)で、全幅を白洲にすると小さい区画では庭域が丸ごと消える。
    ///
    /// <para>測り方: 人の目の高さの帯(底 +0.5〜+1.8m)の実頂点を走り方向へ 0.25m の升で並べ、
    /// **門の芯に最も近い空の連なり**を採る。⛔ 部材の名前や格式から推し量らない(規則21)。
    /// 空きが見つからなければ NaN(呼び手が門構えの幅で代用し、そう刷る)。</para></summary>
    public static float NiwaGateOpening(GameObject mon, Vector2 along, out float centerProj)
    {
        centerProj = float.NaN;
        if (mon == null) return float.NaN;
        var rb = RB(mon);
        float yLo = rb.min.y + 0.5f, yHi = rb.min.y + 1.8f;
        var pts = Body(mon.transform, 2000, true);
        float mn = float.MaxValue, mx = float.MinValue;
        var proj = new List<float>();
        foreach (var w in pts)
        {
            if (w.y < yLo || w.y > yHi) continue;
            float t = Vector2.Dot(new Vector2(w.x, w.z), along);
            proj.Add(t); mn = Mathf.Min(mn, t); mx = Mathf.Max(mx, t);
        }
        if (proj.Count == 0 || mx - mn < 0.5f) return float.NaN;
        const float BIN = 0.25f;
        int n = Mathf.CeilToInt((mx - mn) / BIN) + 1;
        var full = new bool[n];
        foreach (var t in proj) full[Mathf.Clamp(Mathf.FloorToInt((t - mn) / BIN), 0, n - 1)] = true;
        float mid = (mn + mx) * 0.5f;
        float bestW = 0f, bestC = float.NaN, bestD = float.MaxValue;
        int i = 0;
        while (i < n)
        {
            if (full[i]) { i++; continue; }
            int j = i; while (j < n && !full[j]) j++;
            float a = mn + i * BIN, b = mn + j * BIN;
            float w = b - a, c = (a + b) * 0.5f, d = Mathf.Abs(c - mid);
            if (w >= 1.0f && (d < bestD || (Mathf.Abs(d - bestD) < 0.5f && w > bestW)))
            { bestW = w; bestC = c; bestD = d; }
            i = j;
        }
        if (bestW <= 0f) return float.NaN;
        centerProj = bestC;
        return bestW;
    }

    // ═══════════════════════ 庭の地(庭域・帯・空地) ═══════════════════════

    /// <summary>据えるときの作法ひと組。
    /// ⭐ **囲いからの離れは「幹の芯」で、軒からの離れは「樹冠の外接円」で測る**(庭方 2026-09-22 の検分⑧)。
    /// 塀越しに枝が張るのは庭として正しい(囲いの負は是)が、軒へ枝が食い込むのは欠陥。だから
    /// **測る物が2つで違う** — 検査の文言もそう刷ること(規則19「検査の文言と実装の集合を突き合わせる」)。</summary>
    public struct NiwaSet
    {
        public float ClearWall;             // 囲い・長屋の実メッシュからの離れ。⭐ **幹の芯**で測る(⛔ 樹冠ではない)
        public float PadEave;               // 軒の外形からの離れ。⭐ **樹冠の外接円**で測る(樹冠半径に足す)
        public float SinkLo, SinkHi;        // 据えるときの沈め[m]
        public float ScaleLo, ScaleHi;      // 等方スケールの乱れ(⛔ Y だけ伸ばさない)
        public float SpaceLo, SpaceHi;      // 塊の芯々 = 隣り合う2本の樹冠半径の和 ×(この範囲)
        public float Mutual;                // 既に据えた駒との重なりの許し(芯々 ≥ 半径の和 × これ)
        public float SinkByScale;           // >0 なら沈め = スケール × これ(景石の「石高÷3 の1/3埋め」)
        public float EdgeK;                 // 区画の線からの控え = 樹冠半径 × これ
                                            // ⭐ 木は EdgeK=1.0(樹冠を線の内に収める)。⛔ 軒と違い、
                                            //    樹冠のはみ出しは Stage6 の検査で**壁体の区域侵犯**として
                                            //    数えられてしまう(検査は木と軒を見分けない)ので、
                                            //    許容0(規則4)を保つには樹冠ごと内に入れる。
        public float Block;                 // **通り抜ける物(飛石)がこの駒を避ける半径**。
                                            //   >0 = その定数(木は幹 0.25)/ 0 = 実測の樹冠(刈込・低木・石)/ <0 = 避けない(下草)
        public bool Tall;                   // 高木・中木か(⭐ 常緑:落葉の**分母はこれだけ**・検分⑦)
        public bool PathMode;               // 通り道の駒(飛石)— 相手は Block で避け、同じ層とだけ Mutual で突き合う
        public string SelfLayer;            // PathMode の「同じ層」の名(NiwaStepPath が差す)

        /// <summary>**高木**(囲いから幹で 1.2 / 軒から樹冠で 0.3)。塊の芯々は樹冠半径の和×0.45〜0.75 —
        /// ⭐ 三本の松が**株**に見える寄り(⛔ 0.7〜1.1 では芯々8〜11m で孤立木3本になる・検分⑥)。</summary>
        public static NiwaSet Tree
        {
            get
            {
                return new NiwaSet { ClearWall = 1.2f, PadEave = 0.3f, SinkLo = 0.05f, SinkHi = 0.12f,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.45f, SpaceHi = 0.75f,
                                     Mutual = 0.42f, EdgeK = 1.0f, Block = 0.25f, Tall = true };
            }
        }
        /// <summary>**中木**(囲いから幹で 0.8 / 軒から樹冠で 0.3)。芯々 0.6〜0.9・Mutual 0.55(検分⑥)。</summary>
        public static NiwaSet Chuboku
        {
            get
            {
                var o = Tree; o.ClearWall = 0.8f; o.SpaceLo = 0.6f; o.SpaceHi = 0.9f; o.Mutual = 0.55f;
                return o;
            }
        }
        /// <summary>低木・刈込(囲いから幹で 0.4 / 軒から樹冠で 0.2)。芯々は現行のまま(検分⑥)。</summary>
        public static NiwaSet Shrub
        {
            get
            {
                return new NiwaSet { ClearWall = 0.4f, PadEave = 0.2f, SinkLo = 0.03f, SinkHi = 0.08f,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.8f, SpaceHi = 1.3f,
                                     Mutual = 0.65f, EdgeK = 0.9f, Block = 0f, Tall = false };
            }
        }
        /// <summary>下草(シダ)。⭐ 低木と同じ据えだが **踏める**(Block &lt; 0)— 飛石は下草を避けない
        /// (避ける物は幹と刈込の実メッシュだけ・検分①)。</summary>
        public static NiwaSet Kusa { get { var o = Shrub; o.Block = -1f; return o; } }
        /// <summary>景石・飛石・灯籠・井戸(囲いから 0.4 / 軒から樹冠で 0.4)。⭐ 沈めは呼び手が上書きする(景石は石高÷3)。</summary>
        public static NiwaSet Stone
        {
            get
            {
                return new NiwaSet { ClearWall = 0.4f, PadEave = 0.4f, SinkLo = 0.06f, SinkHi = 0.10f,
                                     ScaleLo = 0.90f, ScaleHi = 1.15f, SpaceLo = 0.9f, SpaceHi = 1.4f,
                                     Mutual = 0.8f, EdgeK = 0.8f, Block = 0f, Tall = false };
            }
        }
        /// <summary>飛石の一条(**通り道**)。⭐ 相手は <c>block</c> で避け — 木は幹(0.25m)・刈込と低木と石は
        /// 実メッシュ・下草は踏める。**同じ層の石どうしだけ** 0.9 で突き合う(検分①)。</summary>
        public static NiwaSet Path(string layer)
        { var o = Stone; o.PathMode = true; o.SelfLayer = layer; o.Mutual = 0.9f; return o; }
    }

    /// <summary>据えた駒ひとつ。⭐ **実メッシュで測り直した**樹冠の半径 <c>r</c>(外接円の中心 <c>c</c>)と
    /// **地際から測った幹の芯** <c>trunk</c> を両方持つ — 囲いは幹で、軒は樹冠で検めるため(検分⑧)。
    /// <c>dw</c> = 幹から囲いまでの実測 / <c>de</c> = 樹冠の縁から軒までの実測(負 = 食い込み)。
    /// `clump` = 塊の通し番号(NiwaClump が振る)。0 = 塊でない駒(井戸・灯籠・飛石の列)— 検査は 1 以上だけを塊として数える。</summary>
    public struct NiwaKoma
    {
        public Vector2 c; public float r; public Vector2 trunk;
        public string path; public string layer; public int clump;
        public float block; public bool tall;
        public float dw, de, clearWall, padEave;
    }

    /// <summary>駒の**地際**(実メッシュの底から「丈の12%か0.30mの厚い方」の帯)に入る頂点の重心 = **幹の芯**。
    /// ⛔ ピボット・bounds の中心で幹の位置を決めない(規則21・`docs/oki-kata.md` §0)。
    /// ⛔ 帯に頂点が無いときに黙って bounds の中心で埋めない — false を返し、呼び手が数えて刷る(同 §3)。</summary>
    public static bool NiwaTrunk(GameObject go, out Vector2 c, int maxSamples = 600)
    {
        c = Vector2.zero;
        var pts = Body(go.transform, maxSamples, true);
        if (pts.Count == 0) return false;
        float mny = float.MaxValue, mxy = float.MinValue;
        for (int i = 0; i < pts.Count; i++) { if (pts[i].y < mny) mny = pts[i].y; if (pts[i].y > mxy) mxy = pts[i].y; }
        float band = Mathf.Max(0.30f, (mxy - mny) * 0.12f);
        var sum = Vector2.zero; int n = 0;
        for (int i = 0; i < pts.Count; i++)
            if (pts[i].y <= mny + band) { sum += new Vector2(pts[i].x, pts[i].z); n++; }
        if (n == 0) return false;
        c = sum / n;
        return true;
    }

    /// <summary>庭の地 — 「どこに置けるか」を実メッシュから解いて持つ。
    /// ⭐ 置くのは**帯と塊だけ**(§5-4 ①「庭域へ一様乱数で撒かない」)。この型は撒く役ではなく、
    /// 帯と塊を置こうとしたときに**退避と帯の禁足を実測で拒む**役。</summary>
    public class NiwaField
    {
        public Vector2[] Poly;
        public NiwaOcc Eaves = new NiwaOcc();     // 棟の軒込み外形
        public NiwaOcc Walls = new NiwaOcc();     // 囲い・門構えの壁体
        public List<NiwaKoma> Komas = new List<NiwaKoma>();
        public List<Vector2> Cells = new List<Vector2>();   // 庭域の格子点(2m)
        public List<Vector2[]> Voids = new List<Vector2[]>();  // 池代地(木を置かない空地)
        public float Cell = 2f;

        // 参道の帯(白洲)— ⛔ ここに木・石・刈込・灯籠を置かない(§5-0 c)
        public List<Vector2> BandA = new List<Vector2>(), BandB = new List<Vector2>();
        public List<float> BandHalf = new List<float>();

        // 検査のための控え(§5-2)
        public int Refused, InBand;
        /// <summary>据えてから落とした駒 — 理由別(⛔ 「置けなかった」を一山にしない・規則19)。
        /// <c>DropEave</c> = 実バウンズで軒へ食い込んだ / <c>DropEdge</c> = 実バウンズが区画の線を越えた /
        /// <c>DropSteep</c> = 急斜面で据わらなかった(間引かずに据え直しても埋没>1.0 か 浮き>0.7)。
        /// <c>Reseat</c> = 足元の起伏が大きいので間引かずに据え直した数・<c>TrunkNaN</c> = 幹の芯が測れなかった数。</summary>
        public int DropEave, DropEdge, DropSteep, Reseat, TrunkNaN, Nudged;
        // Put が区画の線で断ったときの控え — 越えた量と実樹冠(呼び手の Put が内へ寄せ直すのに使う)
        float _edgeNeed, _lastRR;
        public float WorstSteep;
        /// <summary>塊の通し番号の採番と、いま据えている塊(0 = 塊の外)。</summary>
        public int ClumpSeq, CurClump;
        /// <summary>⭐ **測った物が違う2つ** — <c>MinWall</c> は囲いから**幹の芯**まで / <c>MinEave</c> は
        /// 軒から**樹冠の外接円の縁**まで(負 = 食い込み)。刷るときも測った物の名を書く(検分⑧)。</summary>
        public float MinWall = float.NaN, MinEave = float.NaN;

        public NiwaField(Vector2[] poly) { Poly = poly; }

        public float Area { get { return Cells.Count * Cell * Cell; } }

        /// <summary>検査の控えを、残っている駒から数え直す。⭐ 実測値は駒が持っているので**測り直さない**
        /// (実メッシュを舐め直すと再生成が重くなる)。</summary>
        public void Recount()
        {
            MinWall = float.NaN; MinEave = float.NaN; InBand = 0;
            foreach (var k in Komas)
            {
                if (float.IsNaN(MinWall) || k.dw < MinWall) MinWall = k.dw;
                if (float.IsNaN(MinEave) || k.de < MinEave) MinEave = k.de;
                if (InSando(k.c, 0f)) InBand++;
            }
        }

        /// <summary>直前に据えた駒を外す(塊を奇数へ戻す用)。</summary>
        public void DropLast(GameObject go)
        {
            if (Komas.Count == 0) return;
            Komas.RemoveAt(Komas.Count - 1);
            UnityEngine.Object.DestroyImmediate(go);
            Recount();
        }

        public void AddBand(Vector2 a, Vector2 b, float half)
        { BandA.Add(a); BandB.Add(b); BandHalf.Add(half); }

        /// <summary>参道の帯の中か。<paramref name="extra"/> は駒の樹冠半径(帯へ**枝も差し込まない**)。</summary>
        public bool InSando(Vector2 p, float extra)
        {
            for (int i = 0; i < BandA.Count; i++)
                if (EdoGeom.DistToEdge(p, BandA[i], BandB[i]) <= BandHalf[i] + extra) return true;
            return false;
        }

        public bool InVoid(Vector2 p)
        {
            for (int i = 0; i < Voids.Count; i++) if (EdoGeom.PIP(Voids[i], p)) return true;
            return false;
        }

        /// <summary>庭域 G を解く(Stage5 の最初に一度だけ)。区画を <paramref name="inset"/> 内へ寄せた
        /// 2m 格子のうち、**軒込み外形から ≥1.0m** で、参道の帯の外にある点(庭方 §5-0 a)。</summary>
        public void Solve(float inset)
        {
            Cells.Clear();
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var p in Poly)
            {
                mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x);
                mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y);
            }
            for (float x = mnx; x <= mxx; x += Cell)
                for (float z = mnz; z <= mxz; z += Cell)
                {
                    var p = new Vector2(x, z);
                    if (!EdoGeom.PIP(Poly, p)) continue;
                    if (EdoGeom.DistToPolyEdge(Poly, p) < inset) continue;
                    if (Eaves.Dist(p, 1.2f) < 1.0f) continue;
                    if (InSando(p, 0f)) continue;
                    Cells.Add(p);
                }
        }

        /// <summary>この点に半径 <paramref name="r"/> の駒を置けるか。⭐ 測るのは**実メッシュまでの距離**で、
        /// 中心点だけの判定ではない(§5-4 ④)。⛔ 帯と池代地は拒む。
        /// <para>⭐ **囲いは幹の芯で・軒は樹冠の外接円で**測り分ける(検分⑧)。塀越しに枝が張るのは
        /// 庭として正しいので、囲いへ樹冠の半径を足さない。軒へは足す(枝が屋根へ食い込むのは欠陥)。</para>
        /// <para>⭐ <c>o.PathMode</c>(飛石)は**相手を樹冠でなく <c>block</c> で避ける** — 木は幹(0.25m)、
        /// 刈込・低木・石は実メッシュ、下草は避けない(検分①)。同じ層(石どうし)だけ Mutual で突き合う。</para></summary>
        public bool Free(Vector2 p, float r, NiwaSet o, bool voidOk = false)
        {
            if (!EdoGeom.PIP(Poly, p)) return false;
            if (EdoGeom.DistToPolyEdge(Poly, p) < r * o.EdgeK) return false;
            if (InSando(p, r)) return false;
            if (!voidOk && InVoid(p)) return false;
            if (o.ClearWall > 0f && Walls.Dist(p, o.ClearWall) < o.ClearWall) return false;   // 幹の芯で
            float ce = r + o.PadEave;
            if (Eaves.Dist(p, ce) < ce) return false;                                          // 樹冠の外接円で
            for (int i = 0; i < Komas.Count; i++)
            {
                var k = Komas[i];
                float need; Vector2 kc = k.c;
                if (o.PathMode)
                {
                    if (k.layer == o.SelfLayer) need = (r + k.r) * o.Mutual;
                    else if (k.block < 0f) need = 0f;                       // 下草は踏める
                    else if (k.block > 0f) { need = r + k.block; kc = k.trunk; }   // 木は幹だけ避ける
                    else need = r + k.r;                                    // 刈込・低木・石は実メッシュ
                }
                else need = (r + k.r) * o.Mutual;
                if (need > 0f && Vector2.Distance(p, kc) < need) return false;
            }
            return true;
        }

        /// <summary>足元の地形の起伏[m](駒の外接箱の四隅+中央)。⭐ **間引いた接地の測りが
        /// どれだけ嘘をつきうるかの上限**でもある — 間引きは接地箇所を落とす側にしか外さないので、
        /// 駒は起伏ぶんまでしか沈まない(浮く側へは外れない)。
        /// ⛔ `GroundGrid`(2m格子の最寄り点)で引かない — 斜面で ±(1m×勾配)の嘘が乗る。
        /// 引くのは `Contact` と同じ**描かれている地表**(`Ground` = SampleHeight)。</summary>
        float ReliefUnder(Bounds b)
        {
            float mn = float.MaxValue, mx = float.MinValue;
            var qs = new[] { new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z),
                             new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z),
                             new Vector2(b.center.x, b.center.z) };
            foreach (var q in qs) { float g = Ground(q.x, q.y); mn = Mathf.Min(mn, g); mx = Mathf.Max(mx, g); }
            return mx - mn;
        }

        /// <summary>1駒据える。⭐ 順は **置く → 接地箇所で据える → 急斜面なら間引かずに据え直す →
        /// 実バウンズで樹冠と幹を測り直す → 軒と区画の線を検め直す**。
        /// ⛔ ピボットの座に置き去りにしない。据えられなければ取り除いて null を返す(黙って浮かせない)。</summary>
        public GameObject Put(Transform parent, string path, Vector2 p, float yaw, float scale, float sink,
                              string name, string layer, NiwaSet o)
        {
            _edgeNeed = 0f;
            var go = PutOnce(parent, path, p, yaw, scale, sink, name, layer, o);
            if (go != null || _edgeNeed <= 0f) return go;
            // ⭐ 区画の線を越えて断られた木は**捨てずに、越えた量だけ内へ寄せて据え直す**(2026-09-22 実測:
            //    坪庭の外周の帯が 1/12・0/6 本まで落ちた — Free の推定樹冠より実物が大きい)。
            //    ⛔ 線を越えてよいことにはしない(許容0・規則4)— 寄せた先も実バウンズで線の内に収め、
            //    Free で壁・軒・他の駒・帯との離れを**実の樹冠半径で**検め直す。⛔ 通り道の駒(飛石)は寄せない。
            if (o.PathMode) { DropEdge++; return null; }
            float need = _edgeNeed, rr = _lastRR;
            for (int attempt = 0; attempt < 2; attempt++)
            {
                var n = InwardAt(p);
                if (n == Vector2.zero) break;
                var p2 = p + n * (need + 0.15f);
                if (!Free(p2, rr, o)) break;                      // 寄せた先が塞がれていれば諦める(数えて刷る)
                _edgeNeed = 0f;
                go = PutOnce(parent, path, p2, yaw, scale, sink, name, layer, o);
                if (go != null) { Nudged++; return go; }
                if (_edgeNeed <= 0f) return null;                  // 別の理由(軒・斜面)は PutOnce が数えた
                p = p2; need = _edgeNeed; rr = _lastRR;
            }
            DropEdge++; return null;
        }

        /// <summary>区画の線から**内へ向かう**単位ベクトル(線までの距離の勾配)。線の外・角の上で 0 なら zero。</summary>
        Vector2 InwardAt(Vector2 p)
        {
            const float h = 0.5f;
            float dx = EdoGeom.DistToPolyEdge(Poly, p + new Vector2(h, 0)) - EdoGeom.DistToPolyEdge(Poly, p - new Vector2(h, 0));
            float dz = EdoGeom.DistToPolyEdge(Poly, p + new Vector2(0, h)) - EdoGeom.DistToPolyEdge(Poly, p - new Vector2(0, h));
            var g = new Vector2(dx, dz);
            if (g.sqrMagnitude < 1e-6f) return Vector2.zero;
            g.Normalize();
            // p が線の外なら距離の勾配は「線へ近づく向き」— 内へ向くよう反転する
            return EdoGeom.PIP(Poly, p) ? g : -g;
        }

        GameObject PutOnce(Transform parent, string path, Vector2 p, float yaw, float scale, float sink,
                           string name, string layer, NiwaSet o)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var go = Place(path, new Vector3(p.x, Ground(p.x, p.y), p.y), yaw, Vector3.one * scale, parent, name);
            if (go == null) { Refused++; return null; }
            try { SeatOnGround(go, sink, 600); }
            catch (Exception) { UnityEngine.Object.DestroyImmediate(go); Refused++; return null; }
            var rb = RB(go);
            // ── 急斜面での埋没 ──────────────────────────────────────────────
            // ⛔ 600点の間引きは**接地箇所そのもの**を落とすことがある(2026-09-22 実測: 三べ坂阿部の
            //    屋敷林が −1.67m・渡辺の常緑中木が −1.15m 埋没)。Stage6 と同じ作法で
            //    「まず粗く、閾値に近い駒だけ細かく」— 足元の起伏が 0.5m を超える駒だけ間引かずに据え直す。
            //    ⭐ 起伏は間引きの嘘の上限なので、これ以下の駒は埋没>1.0 も浮き>0.7 も起こりえない。
            //    ⚠ 閾値が 1.0 でなく 0.5 なのは、起伏を**5点でしか測っていない**ぶんの余裕
            //      (footprint の中の窪みは四隅と中央に現れないことがある)。平らな区画では一度も通らない。
            //    ⛔ 名指しの2本を避ける局所修正にしない — 起伏で選ぶので全層・全区画・全邸に効く。
            if (ReliefUnder(rb) > 0.5f)
            {
                Reseat++;
                try { SeatOnGround(go, sink, 60000); }
                catch (Exception) { UnityEngine.Object.DestroyImmediate(go); Refused++; return null; }
                Vector3 at; int nc;
                float dy = Contact(go, out at, out nc, 0.01f, 60000);
                if (float.IsNaN(dy) || dy < -1.0f || dy > 0.7f)
                {
                    WorstSteep = Mathf.Max(WorstSteep, float.IsNaN(dy) ? 0f : Mathf.Abs(dy));
                    UnityEngine.Object.DestroyImmediate(go); DropSteep++; return null;
                }
                rb = RB(go);
            }
            float rr = Mathf.Max(rb.size.x, rb.size.z) * 0.5f;      // ⭐ 実バウンズで測り直す
            var c = new Vector2(rb.center.x, rb.center.z);
            Vector2 trunk;
            if (!NiwaTrunk(go, out trunk)) { TrunkNaN++; trunk = c; }   // ⛔ 黙って埋めない — 数えて刷る
            // ⭐ 区画の線からの控えは**据えた後の実バウンズ**でも守る。Free は推定の樹冠半径で判定するので、
            //    実バウンズが推定より大きい木は線を越える(Stage6 が区域侵犯として数える)。EdgeK < 0 は検めない。
            if (o.EdgeK >= 0f)
            {
                bool inside = EdoGeom.PIP(Poly, c);
                float dEdge = EdoGeom.DistToPolyEdge(Poly, c);
                if (!inside || dEdge < rr * o.EdgeK)
                {
                    _edgeNeed = rr * o.EdgeK + (inside ? -dEdge : dEdge);   // 内へ寄せるべき量[m]
                    _lastRR = rr;
                    UnityEngine.Object.DestroyImmediate(go);
                    return null;                                            // 数えるのは呼び手の Put(寄せ直しても駄目なときだけ)
                }
            }
            // 検査の控え — 実測の離れ(⛔ 「置けた」だけを合格にしない・規則19)
            // ⚠ 打ち切り 12m — ここで採るのは**最小値**なので、遠い側の実距離は要らない
            //    (cap を上げると升の走査が二乗で効いて 79 区画の再生成が重くなる)。
            float dw = Walls.Dist(trunk, 12f);                       // 囲いから**幹の芯**まで
            float de = Eaves.Dist(c, 12f) - rr;                      // 軒から**樹冠の縁**まで
            // ⭐ 軒は据えた後の実バウンズで検め直す — Free は推定の樹冠で判じるので、実物が大きい木は
            //    屋根へ枝が食い込む(検分⑧「Put の後に実バウンズで軒を検め直し、割ったら落とす」)。
            if (de < o.PadEave) { UnityEngine.Object.DestroyImmediate(go); DropEave++; return null; }
            Komas.Add(new NiwaKoma { c = c, r = rr, trunk = trunk, path = path, layer = layer, clump = CurClump,
                                     block = o.Block, tall = o.Tall,
                                     dw = dw, de = de, clearWall = o.ClearWall, padEave = o.PadEave });
            if (float.IsNaN(MinWall) || dw < MinWall) MinWall = dw;
            if (float.IsNaN(MinEave) || de < MinEave) MinEave = de;
            if (InSando(c, 0f)) InBand++;                            // 0 でなければ実装の誤り(§5-2 ②)
            return go;
        }

        /// <summary>樹冠の投影の被覆率(庭域に対する)。目安 15〜30%・50%超=林・5%未満=禿げ(§5-2 ⑤)。</summary>
        public float Coverage(params string[] layers)
        {
            float a = 0f;
            foreach (var k in Komas)
            {
                bool take = layers == null || layers.Length == 0;
                if (!take) foreach (var l in layers) if (k.layer == l) { take = true; break; }
                if (take) a += Mathf.PI * k.r * k.r;
            }
            return Area > 1f ? a / Area : 0f;
        }
    }

    // ═══════════════════════ 帯と塊 — 置いてよい形はこの二つだけ ═══════════════════════

    /// <summary>塊をひと組据える。⭐ **本数は必ず奇数**・外形は不等辺・乱れは4つ全部(§5-0)。
    /// <paramref name="palette"/> から個体を混ぜ、**同じ個体を2本続けない**。
    /// 返り値は据わった駒。置けなかった分は黙って落とす(呼び手が意図した数との差を刷る・§5-2 ①)。</summary>
    /// <param name="pick">個体の採り方を差し替える(引数 = 直前に採った部材)。null なら palette から等確率。
    /// ⭐ 屋敷林は**常緑:落葉 = 7:3** を守るためにここへ数え合わせの採り方を差す(⛔ 比は意匠・規則17)。</param>
    public static List<GameObject> NiwaClump(Transform parent, string prefix, NiwaField f, Vector2 center,
                                             string[] palette, int n, System.Random rnd, NiwaSet o, string layer,
                                             Func<string, string> pick = null)
    {
        var made = new List<GameObject>();
        if (palette == null || palette.Length == 0 || n <= 0) return made;
        if ((n & 1) == 0) n++;                                   // ⛔ 偶数の塊を作らない(§5-2 ④)
        string last = null;
        var at = center; float lastR = 0f;
        int clumpId = f.CurClump = ++f.ClumpSeq;                 // 検査が「塊ごと」に数えるための札
        for (int i = 0; i < n; i++)
        {
            // 個体を混ぜる(同じ物を2本続けない)
            string path = pick != null ? pick(last) : palette[rnd.Next(palette.Length)];
            if (pick == null)
                for (int t = 0; t < 32 && path == last && palette.Length > 1; t++) path = palette[rnd.Next(palette.Length)];
            if (string.IsNullOrEmpty(path)) { f.Refused++; continue; }
            float baseR = CrownR(path);
            if (baseR <= 0f) { f.Refused++; continue; }
            float sc = Mathf.Lerp(o.ScaleLo, o.ScaleHi, (float)rnd.NextDouble());
            float r = baseR * sc;
            // 位置: 1本目は塊の芯、以降は**芯々 = 隣り合う2本の樹冠半径の和 ×0.7〜1.1** の不等辺
            Vector2 p = center;
            bool ok = false;
            for (int t = 0; t < 10 && !ok; t++)
            {
                if (i == 0) p = center;
                else
                {
                    float ang = (float)rnd.NextDouble() * Mathf.PI * 2f;
                    float d = (lastR + r) * Mathf.Lerp(o.SpaceLo, o.SpaceHi, (float)rnd.NextDouble());
                    p = at + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * d;
                }
                ok = f.Free(p, r, o);
                if (!ok && i == 0) break;                        // 芯が置けない塊は丸ごと諦める
            }
            if (!ok) { f.Refused++; continue; }
            float yaw = (float)rnd.NextDouble() * 360f;          // 乱れ ③ yaw は全周
            float sink = o.SinkByScale > 0f ? sc * o.SinkByScale
                                            : Mathf.Lerp(o.SinkLo, o.SinkHi, (float)rnd.NextDouble());
            var go = f.Put(parent, path, p, yaw, sc, sink, prefix + "_" + i, layer, o);
            if (go == null) continue;
            made.Add(go); last = path; at = p; lastR = r;
        }
        f.CurClump = 0;
        // ⛔ 塊は必ず奇数(§5-2 ④)。置けなかった駒があって偶数で据わったら、
        // ⭐ **落とす前に同じ塊へ1本置き直す**(検分⑥)— 芯々の上限×1.4 まで広げ、16方向を当たる。
        //    ⛔ 意図の奇数へ水増ししない(足すのは1本だけ)。それでも駄目なときだけ最後の1本を下げる。
        if (made.Count > 0 && (made.Count & 1) == 0)
        {
            bool filled = false;
            f.CurClump = clumpId;
            string path = pick != null ? pick(last) : palette[rnd.Next(palette.Length)];
            if (pick == null)
                for (int t = 0; t < 32 && path == last && palette.Length > 1; t++) path = palette[rnd.Next(palette.Length)];
            float baseR = string.IsNullOrEmpty(path) ? 0f : CrownR(path);
            if (baseR > 0f)
            {
                float sc = Mathf.Lerp(o.ScaleLo, o.ScaleHi, (float)rnd.NextDouble());
                float r = baseR * sc;
                float d = (lastR + r) * o.SpaceHi * 1.4f;
                float a0 = (float)rnd.NextDouble() * Mathf.PI * 2f;
                for (int t = 0; t < 16 && !filled; t++)
                {
                    float ang = a0 + Mathf.PI * 2f * t / 16f;
                    var q = at + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * d;
                    if (!f.Free(q, r, o)) continue;
                    float sink = o.SinkByScale > 0f ? sc * o.SinkByScale
                                                    : Mathf.Lerp(o.SinkLo, o.SinkHi, (float)rnd.NextDouble());
                    var go = f.Put(parent, path, q, (float)rnd.NextDouble() * 360f, sc, sink,
                                   prefix + "_" + made.Count, layer, o);
                    if (go == null) continue;
                    made.Add(go); filled = true;
                }
            }
            f.CurClump = 0;
            if (!filled)
            {
                f.DropLast(made[made.Count - 1]);
                made.RemoveAt(made.Count - 1);
            }
        }
        return made;
    }

    /// <summary>散らしではなく**帯**。周長を <paramref name="k"/> 等分した箇所から内へ歩き、
    /// **囲い・長屋の実メッシュからの距離**が <paramref name="lo"/>〜<paramref name="hi"/> に入る点を返す。
    ///
    /// <para>⛔ **区画の線から寄せて採らない**(検分②)。長屋・長屋塀は区画の線から内へ 5〜6m の
    /// 占めを持つので、線からの寄せ 2.5〜7.0m で採ると帯が**棟の上に乗り**、退避で丸ごと落ちる
    /// (2026-09-22 実測: 屋敷林 555→285 本・外周の帯 138→54 本)。帯の基準は**囲いの内側の面**。</para>
    ///
    /// <para>⚠ 囲いが1枚も建っていない区画(<c>f.Walls.Count == 0</c>)では窓が開かないので、
    /// 区画の線からの寄せへ落ちる。そのときは <paramref name="fromWall"/> が false — 呼び手が刷る。
    /// <paramref name="blind"/> = 窓が見つからず捨てた箇所の数(⛔ 黙って減らさない・規則19)。</para>
    ///
    /// <para><paramref name="skip"/> が true を返す箇所(表門の辺など)は飛ばす。</para></summary>
    public static List<Vector2> NiwaWallBandSites(NiwaField f, float lo, float hi, int k,
                                                  System.Random rnd, Func<Vector2, bool> skip,
                                                  out bool fromWall, out int blind)
    {
        var sites = new List<Vector2>();
        var poly = f.Poly;
        fromWall = f.Walls.Count > 0; blind = 0;
        if (k <= 0) return sites;
        float per = 0f;
        for (int i = 0; i < poly.Length; i++) per += Vector2.Distance(poly[i], poly[(i + 1) % poly.Length]);
        if (per < 1f) return sites;
        const float STEP = 0.5f, DEEP = 30f;
        float step = per / k, phase = step * (float)rnd.NextDouble();
        float acc = 0f;
        var window = new List<Vector2>();
        for (int i = 0; i < poly.Length; i++)
        {
            var a = poly[i]; var b = poly[(i + 1) % poly.Length];
            float len = Vector2.Distance(a, b);
            if (len < 0.5f) { acc += len; continue; }
            var dir = (b - a) / len;
            var inward = EdoGeom.InwardNormal(poly, i);
            float s = Mathf.Ceil((acc + phase) / step) * step - phase - acc;   // この辺で最初に当たる位置
            for (; s < len; s += step)
            {
                if (s < 0f) continue;
                var foot = a + dir * (s + ((float)rnd.NextDouble() - 0.5f) * step * 0.4f);
                if (skip != null && skip(foot)) continue;
                if (!fromWall)
                {   // 囲いが無い — 区画の線から寄せる(⚠ 呼び手が「壁が無い」と刷る)
                    sites.Add(foot + inward * Mathf.Lerp(lo, hi, (float)rnd.NextDouble()));
                    continue;
                }
                // 内へ歩いて「壁の実メッシュから lo〜hi」の窓を拾う。⭐ 打ち切りは hi — 窓を抜けたら止める
                //    (cap を上げると升の走査が二乗で効いて 79 区画の再生成が重くなる)。
                window.Clear();
                for (float t = 0f; t <= DEEP; t += STEP)
                {
                    var q = foot + inward * t;
                    if (!EdoGeom.PIP(poly, q)) break;
                    float dw = f.Walls.Dist(q, hi + 0.05f);
                    if (dw >= hi) { if (window.Count > 0) break; else continue; }
                    if (dw >= lo) window.Add(q);
                }
                if (window.Count == 0)
                {   // 窓が開かない = この辺に囲いが無い(共有辺は隣が建てている・Stage1)。
                    // ⭐ 帯は落とさず区画の線からの寄せへ落とし、件数を blind に数えて呼び手が刷る。
                    blind++;
                    sites.Add(foot + inward * Mathf.Lerp(lo, hi, (float)rnd.NextDouble()));
                    continue;
                }
                sites.Add(window[rnd.Next(window.Count)]);         // 寄せの乱れは窓の中から引く
            }
            acc += len;
        }
        return sites;
    }

    /// <summary>飛石の**芯々**[m] = 石の長軸 × 1.05〜1.25(検分①)。⛔ 経路長を石数で割らない —
    /// それは 1.5〜3m の飛び飛びの石になり、一条に見えない(2026-09-22 実測 356→98 枚)。</summary>
    public static float NiwaStepPitch(float stoneLong, System.Random rnd)
    { return stoneLong * Mathf.Lerp(1.05f, 1.25f, (float)rnd.NextDouble()); }

    /// <summary>飛石の**経路**。起点から <paramref name="dir0"/> の向きへ、**折れ2箇所・各15〜40°**で
    /// 総長 <paramref name="total"/> の折れ線を引く(検分①)。⭐ 総長は「(石数−1)×芯々」で呼び手が出す —
    /// ⛔ 庭域の点を2つ拾って結ばない(芯々が経路長の従属値になってしまう)。</summary>
    public static List<Vector2> NiwaStepWay(Vector2 start, Vector2 dir0, float total, System.Random rnd)
    {
        var way = new List<Vector2> { start };
        var d = dir0.sqrMagnitude < 1e-6f ? Vector2.up : dir0.normalized;
        float used = 0f;
        for (int i = 0; i < 2; i++)
        {
            float len = total * (0.28f + (float)rnd.NextDouble() * 0.14f);
            way.Add(way[way.Count - 1] + d * len); used += len;
            float ang = (15f + (float)rnd.NextDouble() * 25f) * (rnd.NextDouble() < 0.5 ? -1f : 1f);
            float ca = Mathf.Cos(ang * Mathf.Deg2Rad), sa = Mathf.Sin(ang * Mathf.Deg2Rad);
            d = new Vector2(d.x * ca - d.y * sa, d.x * sa + d.y * ca);
        }
        way.Add(way[way.Count - 1] + d * Mathf.Max(0.5f, total - used));
        return way;
    }

    /// <summary>飛石の**出だしの向き**を測って決める。<paramref name="n0"/> から ±<paramref name="halfDeg"/> を
    /// 10°刻みで当たり、その向きへ芯々ごとに置いたとき**いちばん多く据わる**向きを採る。
    /// ⛔ 向きを決め打ちしない・庭域の点を2つ拾って結ばない(検分①)。</summary>
    public static Vector2 NiwaStepAim(NiwaField f, Vector2 start, Vector2 n0, float halfDeg,
                                      float total, float pitch, float r, NiwaSet o)
    {
        var b0 = n0.sqrMagnitude < 1e-6f ? Vector2.up : n0.normalized;
        var best = b0; int bestScore = -1;
        if (pitch <= 0.01f) return best;
        for (float a = -halfDeg; a <= halfDeg + 0.01f; a += 10f)
        {
            float ca = Mathf.Cos(a * Mathf.Deg2Rad), sa = Mathf.Sin(a * Mathf.Deg2Rad);
            var d = new Vector2(b0.x * ca - b0.y * sa, b0.x * sa + b0.y * ca);
            int sc = 0;
            for (float s = 0f; s <= total; s += pitch) if (f.Free(start + d * s, r, o)) sc++;
            if (sc > bestScore) { bestScore = sc; best = d; }
        }
        return best;
    }

    /// <summary>折れ線に沿った位置 <paramref name="s"/>[m] の点と向き。端を越えたら false。</summary>
    public static bool NiwaWalk(List<Vector2> way, float s, out Vector2 p, out Vector2 dir)
    {
        p = way[0]; dir = Vector2.up;
        float acc = 0f;
        for (int j = 1; j < way.Count; j++)
        {
            float seg = Vector2.Distance(way[j - 1], way[j]);
            if (seg < 1e-4f) continue;
            dir = (way[j] - way[j - 1]) / seg;
            if (acc + seg >= s) { p = way[j - 1] + dir * (s - acc); return true; }
            acc += seg;
        }
        p = way[way.Count - 1];
        return false;
    }

    /// <summary>飛石1条。<paramref name="way"/> の折れ線に沿って、**芯々を石の実寸から出して**並べる
    /// (⛔ 2〜3m 間隔で置かない — 歩幅の石である)。<paramref name="n"/> は置く枚数で、
    /// 経路が尽きたらそこで止める(呼び手が経路長を芯々から出しておくこと)。
    /// ⭐ 曲がりの外に**踏分石**(長軸 0.6m)を1枚。
    /// 天端がピボットの部材(`Own.Tobiishi`)でも、据えるのは接地箇所を測る SeatOnGround に任せる。</summary>
    public static List<GameObject> NiwaStepPath(Transform parent, string prefix, NiwaField f, List<Vector2> way,
                                                string[] palette, int n, System.Random rnd, float stoneLong,
                                                NiwaSet o, string layer, float pitch)
    {
        var made = new List<GameObject>();
        if (way == null || way.Count < 2 || n <= 0 || palette.Length == 0 || pitch <= 0.01f) return made;
        o.PathMode = true; o.SelfLayer = layer; o.Mutual = 0.9f;   // ⭐ 石どうしだけ 0.9(相手は block で避ける)
        string last = null;
        for (int i = 0; i < n; i++)
        {
            Vector2 p, dir;
            if (!NiwaWalk(way, pitch * i, out p, out dir)) break;          // 経路が尽きた
            var perp = new Vector2(-dir.y, dir.x);
            p += perp * ((float)rnd.NextDouble() - 0.5f) * 0.12f;          // 一直線に並べない
            PutStone(parent, prefix + "_" + i, f, p, dir, palette, ref last, rnd, stoneLong, o, layer, made);
        }
        // ⭐ 踏分石(長軸 0.6m・1枚)を**曲がりの外**へ。⛔ 内側に置かない(曲がりの内は歩かない)
        if (made.Count > 0 && way.Count >= 3)
        {
            int b = 1 + rnd.Next(way.Count - 2);                            // 折れ目のどれか
            Vector2 u = (way[b] - way[b - 1]).normalized, v = (way[b + 1] - way[b]).normalized;
            float cross = u.x * v.y - u.y * v.x;                            // >0 = 左へ曲がる → 外は右
            var outward = cross > 0f ? new Vector2(u.y, -u.x) : new Vector2(-u.y, u.x);
            var q = way[b] + outward * ((0.6f + stoneLong) * 0.5f * 1.1f);
            string dummy = null;
            PutStone(parent, prefix + "_Fumiwake", f, q, u, palette, ref dummy, rnd, 0.6f, o, layer, made);
        }
        return made;
    }

    /// <summary>飛石1枚を据える(長軸を <paramref name="stoneLong"/> へ実寸から合わせる)。据われば true。</summary>
    static bool PutStone(Transform parent, string name, NiwaField f, Vector2 p, Vector2 dir, string[] palette,
                         ref string last, System.Random rnd, float stoneLong, NiwaSet o, string layer,
                         List<GameObject> made)
    {
        string path = palette[rnd.Next(palette.Length)];
        for (int t = 0; t < 3 && path == last && palette.Length > 1; t++) path = palette[rnd.Next(palette.Length)];
        float baseL = Mathf.Max(PartSize(path).x, PartSize(path).z);
        if (baseL <= 0.001f) { f.Refused++; return false; }
        float sc = stoneLong / baseL * Mathf.Lerp(0.92f, 1.08f, (float)rnd.NextDouble());
        float r = CrownR(path) * sc;
        if (!f.Free(p, r, o)) { f.Refused++; return false; }
        float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg + ((float)rnd.NextDouble() - 0.5f) * 40f;
        float sink = Mathf.Lerp(o.SinkLo, o.SinkHi, (float)rnd.NextDouble());
        var go = f.Put(parent, path, p, yaw, sc, sink, name, layer, o);
        if (go == null) return false;
        made.Add(go); last = path;
        return true;
    }

    /// <summary>庭域の格子点のうち、軒からの距離が <paramref name="lo"/>〜<paramref name="hi"/> の
    /// **最大連結成分**(坪庭のポケット)。⭐ 棟と棟の間に自然に生まれた隙だけを拾う(§5-1 tsubo)。
    /// 小さすぎる成分しか無ければ空を返す(⛔ 坪庭を無理に作らない)。</summary>
    public static List<Vector2> NiwaPocket(NiwaField f, float lo, float hi, int minCells)
    {
        var pool = new List<Vector2>();
        foreach (var p in f.Cells)
        {
            float d = f.Eaves.Dist(p, hi + 0.5f);
            if (d >= lo && d <= hi) pool.Add(p);
        }
        return NiwaBlob(f, pool, minCells);
    }

    /// <summary>格子点の部分集合の**最大連結成分**(8近傍)。⭐ 池代地も坪庭もこれで採る —
    /// 「離れ小島をかき集めた領域」を一つの庭と呼ばないため(庭方 §5-1)。</summary>
    public static List<Vector2> NiwaBlob(NiwaField f, List<Vector2> subset, int minCells)
    {
        // ⛔ 格子点を float のまま集合の鍵にしない — 隣を `x ± Cell` で作ると丸め誤差で
        //    同じ点に当たらず、連結成分が砂粒に割れる。整数の升目の番地で引く。
        var pool = new Dictionary<long, Vector2>();
        foreach (var p in subset)
        {
            long k = CellKey(p, f.Cell);
            if (!pool.ContainsKey(k)) pool.Add(k, p);
        }
        var best = new List<Vector2>();
        var seen = new HashSet<long>();
        foreach (var kv in pool)
        {
            if (seen.Contains(kv.Key)) continue;
            var comp = new List<Vector2>();
            var stack = new Stack<long>(); stack.Push(kv.Key); seen.Add(kv.Key);
            while (stack.Count > 0)
            {
                long q = stack.Pop(); comp.Add(pool[q]);
                int qx = (int)(q >> 32), qz = (int)(uint)q;
                for (int dx = -1; dx <= 1; dx++)
                    for (int dz = -1; dz <= 1; dz++)
                    {
                        if (dx == 0 && dz == 0) continue;
                        long nq = ((long)(qx + dx) << 32) ^ (uint)(qz + dz);
                        if (seen.Contains(nq) || !pool.ContainsKey(nq)) continue;
                        seen.Add(nq); stack.Push(nq);
                    }
            }
            if (comp.Count > best.Count) best = comp;
        }
        return best.Count >= minCells ? best : new List<Vector2>();
    }

    /// <summary>格子点の升目の番地。⛔ `Mathf.RoundToInt` は .5 を偶数へ丸める(升の端が
    /// ちょうど .5 の区画で番地が飛ぶ)ので floor(x+0.5) で採る。</summary>
    static long CellKey(Vector2 p, float cell)
    {
        int ix = Mathf.FloorToInt(p.x / cell + 0.5f), iz = Mathf.FloorToInt(p.y / cell + 0.5f);
        return ((long)ix << 32) ^ (uint)iz;
    }

    /// <summary>**不定形**の空地の輪郭(池代地)。⛔ 円・楕円にしない(§5-1 chisen ③)。
    /// 重心 <paramref name="c"/> のまわりに 7〜9 の頂点を、半径を 0.62〜1.18 倍に振って作る。</summary>
    public static Vector2[] NiwaVoidPoly(Vector2 c, float longR, System.Random rnd)
    {
        int n = 7 + rnd.Next(3);
        var pts = new Vector2[n];
        float phase = (float)rnd.NextDouble() * Mathf.PI * 2f;
        for (int i = 0; i < n; i++)
        {
            float a = phase + Mathf.PI * 2f * i / n + ((float)rnd.NextDouble() - 0.5f) * 0.35f;
            float r = longR * Mathf.Lerp(0.62f, 1.18f, (float)rnd.NextDouble());
            pts[i] = c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r;
        }
        return pts;
    }
}
