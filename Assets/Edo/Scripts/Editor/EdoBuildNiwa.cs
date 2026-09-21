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

    /// <summary>据えるときの作法ひと組。⭐ 退避は**樹冠半径 + pad** で測る(庭方 §5-0)。</summary>
    public struct NiwaSet
    {
        public float PadWall, PadEave;      // 囲い / 軒からの余裕(樹冠半径に足す)
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

        /// <summary>高木・中木(囲い 樹冠+0.5 / 軒 樹冠+1.0)。</summary>
        public static NiwaSet Tree
        {
            get
            {
                return new NiwaSet { PadWall = 0.5f, PadEave = 1.0f, SinkLo = 0.05f, SinkHi = 0.12f,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.7f, SpaceHi = 1.1f, Mutual = 0.7f, EdgeK = 1.0f };
            }
        }
        /// <summary>低木・刈込(0.6/0.6)。</summary>
        public static NiwaSet Shrub
        {
            get
            {
                return new NiwaSet { PadWall = 0.6f, PadEave = 0.6f, SinkLo = 0.03f, SinkHi = 0.08f,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.8f, SpaceHi = 1.3f, Mutual = 0.65f, EdgeK = 0.9f };
            }
        }
        /// <summary>景石・飛石・灯籠(0.4/0.4)。⭐ 沈めは呼び手が上書きする(景石は石高÷3)。</summary>
        public static NiwaSet Stone
        {
            get
            {
                return new NiwaSet { PadWall = 0.4f, PadEave = 0.4f, SinkLo = 0.06f, SinkHi = 0.10f,
                                     ScaleLo = 0.90f, ScaleHi = 1.15f, SpaceLo = 0.9f, SpaceHi = 1.4f, Mutual = 0.8f, EdgeK = 0.8f };
            }
        }
    }

    /// <summary>据えた駒ひとつ(**実バウンズで測り直した**平面の半径つき)。</summary>
    public struct NiwaKoma { public Vector2 c; public float r; public string path; public string layer; }

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
        public float MinWall = float.NaN, MinEave = float.NaN;

        public NiwaField(Vector2[] poly) { Poly = poly; }

        public float Area { get { return Cells.Count * Cell * Cell; } }

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
        /// 中心点だけの判定ではない(§5-4 ④)。⛔ 帯と池代地は拒む。</summary>
        public bool Free(Vector2 p, float r, NiwaSet o, bool voidOk = false)
        {
            if (!EdoGeom.PIP(Poly, p)) return false;
            if (EdoGeom.DistToPolyEdge(Poly, p) < r * o.EdgeK) return false;
            if (InSando(p, r)) return false;
            if (!voidOk && InVoid(p)) return false;
            float cw = r + o.PadWall, ce = r + o.PadEave;
            if (Walls.Dist(p, cw) < cw) return false;
            if (Eaves.Dist(p, ce) < ce) return false;
            for (int i = 0; i < Komas.Count; i++)
            {
                var k = Komas[i];
                if (Vector2.Distance(p, k.c) < (r + k.r) * o.Mutual) return false;
            }
            return true;
        }

        /// <summary>1駒据える。⭐ 順は **置く → 接地箇所で据える → 実バウンズで樹冠を測り直す**。
        /// ⛔ ピボットの座に置き去りにしない。据えられなければ取り除いて null を返す(黙って浮かせない)。</summary>
        public GameObject Put(Transform parent, string path, Vector2 p, float yaw, float scale, float sink,
                              string name, string layer)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var go = Place(path, new Vector3(p.x, Ground(p.x, p.y), p.y), yaw, Vector3.one * scale, parent, name);
            if (go == null) { Refused++; return null; }
            try { SeatOnGround(go, sink, 600); }
            catch (Exception) { UnityEngine.Object.DestroyImmediate(go); Refused++; return null; }
            var rb = RB(go);
            float rr = Mathf.Max(rb.size.x, rb.size.z) * 0.5f;      // ⭐ 実バウンズで測り直す
            var c = new Vector2(rb.center.x, rb.center.z);
            Komas.Add(new NiwaKoma { c = c, r = rr, path = path, layer = layer });
            // 検査の控え — 実測の離れ(⛔ 「置けた」だけを合格にしない・規則19)
            // ⚠ 打ち切り 12m — ここで採るのは**最小値**なので、遠い側の実距離は要らない
            //    (cap を上げると升の走査が二乗で効いて 79 区画の再生成が重くなる)。
            float dw = Walls.Dist(c, 12f) - rr, de = Eaves.Dist(c, 12f) - rr;
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
        for (int i = 0; i < n; i++)
        {
            // 個体を混ぜる(同じ物を2本続けない)
            string path = pick != null ? pick(last) : palette[rnd.Next(palette.Length)];
            if (pick == null)
                for (int t = 0; t < 4 && path == last && palette.Length > 1; t++) path = palette[rnd.Next(palette.Length)];
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
            var go = f.Put(parent, path, p, yaw, sc, sink, prefix + "_" + i, layer);
            if (go == null) continue;
            made.Add(go); last = path; at = p; lastR = r;
        }
        return made;
    }

    /// <summary>散らしではなく**帯**。区画の辺の内側 <paramref name="insetLo"/>〜<paramref name="insetHi"/> に、
    /// 周長を <paramref name="k"/> 等分した箇所を返す。⛔ 等間隔に見せないため寄せ幅と位相に乱れを掛ける。
    /// <paramref name="skip"/> が true を返す辺(表門の辺など)は飛ばす。</summary>
    public static List<Vector2> NiwaBandSites(Vector2[] poly, float insetLo, float insetHi, int k,
                                              System.Random rnd, Func<Vector2, bool> skip)
    {
        var sites = new List<Vector2>();
        if (k <= 0) return sites;
        float per = 0f;
        for (int i = 0; i < poly.Length; i++) per += Vector2.Distance(poly[i], poly[(i + 1) % poly.Length]);
        if (per < 1f) return sites;
        float step = per / k, phase = step * (float)rnd.NextDouble();
        float acc = 0f;
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
                float ins = Mathf.Lerp(insetLo, insetHi, (float)rnd.NextDouble());
                var p = a + dir * (s + ((float)rnd.NextDouble() - 0.5f) * step * 0.4f) + inward * ins;
                if (skip != null && skip(p)) continue;
                sites.Add(p);
            }
            acc += len;
        }
        return sites;
    }

    /// <summary>飛石1条。<paramref name="way"/> の折れ線に沿って <paramref name="n"/> 枚を
    /// **芯々を実寸から出して**並べる(⛔ 2〜3m 間隔で置かない — 歩幅の石である)。
    /// 天端がピボットの部材(`Own.Tobiishi`)でも、据えるのは接地箇所を測る SeatOnGround に任せる。</summary>
    public static List<GameObject> NiwaStepPath(Transform parent, string prefix, NiwaField f, List<Vector2> way,
                                                string[] palette, int n, System.Random rnd, float stoneLong,
                                                NiwaSet o, string layer)
    {
        var made = new List<GameObject>();
        if (way == null || way.Count < 2 || n <= 0 || palette.Length == 0) return made;
        float total = 0f;
        for (int i = 1; i < way.Count; i++) total += Vector2.Distance(way[i - 1], way[i]);
        if (total < 0.5f) return made;
        float pitch = total / Mathf.Max(1, n - 1);
        string last = null;
        for (int i = 0; i < n; i++)
        {
            float s = pitch * i, acc = 0f; Vector2 p = way[0], dir = Vector2.right;
            for (int j = 1; j < way.Count; j++)
            {
                float seg = Vector2.Distance(way[j - 1], way[j]);
                if (acc + seg >= s || j == way.Count - 1)
                {
                    dir = (way[j] - way[j - 1]).normalized;
                    p = way[j - 1] + dir * Mathf.Min(s - acc, seg);
                    break;
                }
                acc += seg;
            }
            var perp = new Vector2(-dir.y, dir.x);
            p += perp * ((float)rnd.NextDouble() - 0.5f) * 0.12f;          // 一直線に並べない
            string path = palette[rnd.Next(palette.Length)];
            for (int t = 0; t < 3 && path == last && palette.Length > 1; t++) path = palette[rnd.Next(palette.Length)];
            float baseL = Mathf.Max(PartSize(path).x, PartSize(path).z);
            if (baseL <= 0.001f) { f.Refused++; continue; }
            float sc = stoneLong / baseL * Mathf.Lerp(0.92f, 1.08f, (float)rnd.NextDouble());
            float r = CrownR(path) * sc;
            if (!f.Free(p, r, o)) { f.Refused++; continue; }
            float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg + ((float)rnd.NextDouble() - 0.5f) * 40f;
            float sink = Mathf.Lerp(o.SinkLo, o.SinkHi, (float)rnd.NextDouble());
            var go = f.Put(parent, path, p, yaw, sc, sink, prefix + "_" + i, layer);
            if (go == null) continue;
            made.Add(go); last = path;
        }
        return made;
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
