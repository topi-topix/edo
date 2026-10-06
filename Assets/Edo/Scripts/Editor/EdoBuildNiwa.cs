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

    // NiwaGateOpening(門の実メッシュの帯の空きで通り口を測る)は 2026-09-29 に廃した ── 通り口は部材の札(EdoPartSpec.passage)が持つ(EDO-0491)。


    /// <summary>門の芯 <paramref name="gateC"/> から駒の**実外形**までの水平の離れ[m](外形の中なら 0)。
    /// ⭐ 前庭が取れているかを**建てる時点で**測るための物(EDO-0372)— 主屋が門の真裏に建つと、参道の
    /// 白洲(門の芯 → 主屋の最近点)は長さ 1.5m 未満になり、地形の 1 texel(4m)にも満たず塗っても見えない。
    /// 参道は門から主屋の**最も近い所**へ引くので、守るべきは向きを問わない離れ(半径)で、真っ直ぐの帯ではない。
    ///
    /// <para>測り方: 駒の頂点(<paramref name="withRoof"/>=true なら屋根・軒込み — 前庭に屋根は架けない)の
    /// XZ 凸包を取り、門の芯から凸包の**辺**までの最短距離を採る。⛔ 頂点までの距離で測らない — 門の正面に
    /// 長い壁が来ると、壁の両端の頂点は遠くても壁の中ほどが門に迫る。⛔ 外接箱で測らない(回った棟で外す)。</para></summary>
    public static float GateClearance(GameObject go, Vector2 gateC, bool withRoof = true)
    {
        if (go == null) return float.PositiveInfinity;
        var body = Body(go.transform, 1200, withRoof);
        if (body.Count < 3) return float.PositiveInfinity;
        var xz = new Vector2[body.Count];
        for (int i = 0; i < body.Count; i++) xz[i] = new Vector2(body[i].x, body[i].z);
        var hi = EdoGeom.HullXZ(xz);
        var hull = new Vector2[hi.Length];
        for (int i = 0; i < hi.Length; i++) hull[i] = xz[hi[i]];
        if (hull.Length >= 3 && EdoGeom.PIP(hull, gateC)) return 0f;
        float best = float.PositiveInfinity;
        for (int i = 0; i < hull.Length; i++)
        {
            var a = hull[i]; var b = hull[(i + 1) % hull.Length];
            var ab = b - a; float t = ab.sqrMagnitude < 1e-8f ? 0f : Mathf.Clamp01(Vector2.Dot(gateC - a, ab) / ab.sqrMagnitude);
            best = Mathf.Min(best, Vector2.Distance(gateC, a + ab * t));
        }
        return best;
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
        public float TrunkEdge;             // >0 なら区画の線からの控えを**幹の芯**で測る[m](EdgeK の樹冠は見ない)。
                                            // ⭐ 施主の規則(2026-09-23・繰り返し指摘): 幹の芯は道(区画の線)から 2.0m・低木も。
                                            //    樹冠は線を越えて張り出してよい(検査も幹で数える ── EdoTypologyBuilder.Inspect)。
        public float Block;                 // **通り抜ける物(飛石)がこの駒を避ける半径**。
                                            //   >0 = その定数(木は幹 0.25)/ 0 = 実測の樹冠(刈込・低木・石)/ <0 = 避けない(下草)
        public bool Tall;                   // 高木・中木か(⭐ 常緑:落葉の**分母はこれだけ**・検分⑦)
        public bool PathMode;               // 通り道の駒(飛石)— 相手は Block で避け、同じ層とだけ Mutual で突き合う
        public string SelfLayer;            // PathMode の「同じ層」の名(NiwaStepPath が差す)
        public float NeireMax;              // >0 = **剛体の据え物**(井戸・灯籠・景石・飛石)。下端の全部が地面に着くまで沈める根入れの上限[m]。
                                            //   ⭐ 坂では上手の 1 点が着いても下手が浮く(Contact は最寄りの 1 点)── 下端の最も浮いた所を測って沈める。
                                            //   上限を超える坂には置かない(硬い制約・DropNeire で数える)。0 = 低木・下草(根で据える物・測らない)
                                            //   ⭐ 2026-09-29 EDO-0488 — **高木・中木も測る**(TREE_NEIRE_MAX)。自作の木に根張りを付けて
                                            //   幹の足が幅 1m 前後の平らな底になり、坂の下手でその縁が浮いて見えた(施主「根元が浮いている」)。
        public float SlopeSinkK;            // >0 = **斜度で沈めを決める**(高木・中木 ── TREE_SLOPE_K)。据えた後、幹の足の**下手の縁**を
                                            //   沈め(SinkLo〜Hi)+ 足の半径 × tanθ × これ だけ地中に入れる(<see cref="FootSlope"/> で θ を測る)。
                                            //   上手の最深は TREE_BURY_MAX まで(越える坂には置かない・DropNeire)。0 = 測らない。

        /// <summary>木・低木・下草の幹の芯から区画の線と囲い・門構えの壁体までの控え[m](2026-09-27・EDO-0477 P5)。
        /// ⭐ 施主の規則: 幹の芯 ↔ 道辺 ≥ 2.0m(全層・低木も)・囲いのある辺は囲いの線から 2m(山王 EDO-0401/0409 の型)。
        /// ⛔ それまで類型の庭は囲いから 高木 1.2 / 中木 0.8 / 低木 0.4 で、区画の線は樹冠 × EdgeK で測っていた。
        /// ⚠ 2m は PC の解像度の都合で将来外し得る(施主注記)── 外すときはこの一行だけ。</summary>
        public const float TREE_KEEP = 2.0f;

        /// <summary>高木・中木の沈め[m]【確度 U】(2026-09-29 EDO-0488)。⭐ 根張りの平らな底と、いちばん張った縁
        /// (地際から幹の太さ 0.2 倍まで)が**地中に入る**深さ。⛔ 旧 0.05〜0.12 では底の縁が地表に出て、
        /// 平地でも「置いただけ」に見えた(観理院のエノキ・施主指摘)。据えは埋めて隠すのが基本(docs/oki-kata.md §4)。</summary>
        public const float TREE_SINK_LO = 0.15f, TREE_SINK_HI = 0.25f;
        /// <summary>高木・中木の根入れの上限[m]【確度 U】。幹の足の下端の全部が地面に着くまで沈める量の上限。
        /// 幹は丈 10m 超なので 1m 埋めても見えは崩れない(埋没の許しも 1.0・Put の急斜面の据え直しと同じ数)。</summary>
        public const float TREE_NEIRE_MAX = 1.0f;
        /// <summary>**斜度で決める沈め**の係数【確度 U】(2026-09-29 EDO-0488 施主「斜面の斜度に合わせてどれだけ埋めるかを決める仕組み」)。
        /// 下手の縁の埋まり = 沈め(TREE_SINK_LO〜HI)+ 足の半径 R × tanθ × これ。⭐ 坂では根張りの平らな底が地表と θ で開くので、
        /// 下手ほど縁の上の膨らみまで地表に出る ── 0.5 は「下手の縁が、足の芯を通る地表の面から R·tanθ/2 下」= 底の傾きの半分を下手でも埋める量。
        /// ⛔ 2026-09-29 まで下手の縁は**ちょうど地表**で止まり(根入れが沈めを食った)、斜面林のエノキの根元が浮いて見えた。</summary>
        public const float TREE_SLOPE_K = 0.5f;
        /// <summary>**植栽の埋没の上限**[m](硬い・完成の表の線 ── 普請検査の「植栽の埋没 &gt; 1.0」と同じ数・<see cref="SeatPlant"/> の buryMax 既定と同じ)。
        /// 測りは<see cref="LowestGap"/>(全ての当たりの最小の隙)。⛔ 建てる側の上限を検査より緩くしない(検査で捕まえず建てる時点で防ぐ)。</summary>
        public const float PLANT_BURY_MAX = 1.0f;
        /// <summary>高木・中木の上手の最深の埋まり[m](硬い)。斜度の沈めを足した後の、幹の足の下端と枝葉の最も深い所。越える坂には置かない。
        /// ⛔ 2026-10-05 まで 1.5(「丈 10m 超の幹なので」U)で、検査の線 1.0 より緩く、土井の泉水の松 4 本が 1.15〜1.49m 埋まったまま建った(EDO-0533)。
        /// 斜度の沈め(<see cref="TREE_SLOPE_K"/>)は**柔らかい狙い**なので、この上限で頭打ちにする(⛔ 狙いのために木を落とさない)。</summary>
        public const float TREE_BURY_MAX = PLANT_BURY_MAX;
        /// <summary>低木・刈込・下草の根元の帯の最深の埋まり[m]【確度 U】(2026-10-04 EDO-0533 普請検査 第1回)。根元の帯の最も浮いた所を
        /// 地表まで沈め切った(浮き 0・硬い)後の、帯の最も深い所の上限。株の丈 0.5〜1.5m の半分を越えて埋めない目安。越える坂には置かない(DropNeire)。</summary>
        public const float SHRUB_BURY_MAX = 0.40f;
        /// <summary>**高木**(囲いから幹で 2.0 / 軒から樹冠で 0.3)。塊の芯々は樹冠半径の和×0.45〜0.75 —
        /// ⭐ 三本の松が**株**に見える寄り(⛔ 0.7〜1.1 では芯々8〜11m で孤立木3本になる・検分⑥)。</summary>
        public static NiwaSet Tree
        {
            get
            {
                return new NiwaSet { ClearWall = TREE_KEEP, PadEave = 0.3f, SinkLo = TREE_SINK_LO, SinkHi = TREE_SINK_HI,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.45f, SpaceHi = 0.75f,
                                     Mutual = 0.42f, EdgeK = -1f, TrunkEdge = TREE_KEEP, Block = 0.25f, Tall = true,
                                     NeireMax = TREE_NEIRE_MAX, SlopeSinkK = TREE_SLOPE_K };
            }
        }
        /// <summary>**中木**(囲いから幹で 2.0 / 軒から樹冠で 0.3)。芯々 0.6〜0.9・Mutual 0.55(検分⑥)。</summary>
        public static NiwaSet Chuboku
        {
            get
            {
                var o = Tree; o.SpaceLo = 0.6f; o.SpaceHi = 0.9f; o.Mutual = 0.55f;
                return o;
            }
        }
        /// <summary>低木・刈込(囲いから幹で 2.0 / 軒から樹冠で 0.2)。芯々は現行のまま(検分⑥)。</summary>
        public static NiwaSet Shrub
        {
            get
            {
                return new NiwaSet { ClearWall = TREE_KEEP, PadEave = 0.2f, SinkLo = 0.03f, SinkHi = 0.08f,
                                     ScaleLo = 0.88f, ScaleHi = 1.12f, SpaceLo = 0.8f, SpaceHi = 1.3f,
                                     Mutual = 0.65f, EdgeK = -1f, TrunkEdge = TREE_KEEP, Block = 0f, Tall = false };
            }
        }
        /// <summary>下草(シダ)。⭐ 低木と同じ据えだが **踏める**(Block &lt; 0)— 飛石は下草を避けない
        /// (避ける物は幹と刈込の実メッシュだけ・検分①)。</summary>
        public static NiwaSet Kusa { get { var o = Shrub; o.Block = -1f; return o; } }
        /// <summary>剛体の据え物を坂で沈めてよい上限[m]【確度 U】。井筒・灯籠の台石の見えが半分を切らない深さ
        /// (井筒の丈 ≈0.7m・雪見灯籠の脚 ≈0.4m)。2026-09-29 EDO-0472: 十坊 8・9 の井戸が坂の下手で 0.75m 浮いていた。</summary>
        public const float STONE_NEIRE_MAX = 0.30f;
        /// <summary>景石・飛石・灯籠・井戸(囲いから 0.4 / 軒から樹冠で 0.4)。⭐ 沈めは呼び手が上書きする(景石は石高÷3)。</summary>
        public static NiwaSet Stone
        {
            get
            {
                return new NiwaSet { ClearWall = 0.4f, PadEave = 0.4f, SinkLo = 0.06f, SinkHi = 0.10f,
                                     ScaleLo = 0.90f, ScaleHi = 1.15f, SpaceLo = 0.9f, SpaceHi = 1.4f,
                                     Mutual = 0.8f, EdgeK = 0.8f, Block = 0f, Tall = false, NeireMax = STONE_NEIRE_MAX };
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

    /// <summary>壁体の足元の外形を取る帯の高さ[m]: 地表から この高さまでの頂点だけを壁体に数える(軒先の垂れ 2.3m 前後を入れない ──
    /// 附属屋の背の取り合い・塀の芯の離れが壁体の面を測る帯 0.15〜1.8m と同じ上端)。</summary>
    public const float BODY_FOOT_BAND = 1.8f;

    /// <summary>**建物・塀・門の壁体の足元の外形**(世界 XZ の凸包の列 ── メッシュ一枚ごとに一つ)。屋根系の名(<see cref="IsRoofName"/>・"roof")の
    /// メッシュを除き、残りの頂点のうち**その点の地表から <see cref="BODY_FOOT_BAND"/> m まで**の物だけで包む(軒・屋根の張り出しは入れない ──
    /// 区域侵犯は壁体で数える・docs/oki-kata.md §4)。縁・廊下の床と束(地面に立つ)は入る。凸包の候補は局所 XZ の凸包(<see cref="HullXZIndices"/>)。
    /// ⛔ 外接箱・ピボットで取らない(規則21)。⚠ 一枚の凸メッシュに凹みがあれば凹みも外形に入る(保守側 ── 退ける側へ外れる)。
    /// 当たる先: 植物の幹を壁体に立てない硬い条件の全て(<see cref="NiwaField.Bodies"/>・<see cref="PlantInBody"/> ── 土井 Stage8・泉水・奥庭)。</summary>
    public static List<Vector2[]> BodyHulls(IEnumerable<Transform> groups)
    {
        var res = new List<Vector2[]>();
        foreach (var g in groups)
        {
            if (g == null) continue;
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                var m = mf.sharedMesh; if (m == null) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
                var root = PrefabUtility.GetNearestPrefabInstanceRoot(mf.gameObject);
                string pn = PartName(root != null ? root.transform : mf.transform, mf);
                if (IsRoofName(pn) || pn.ToLower().Contains("roof")) continue;
                var vs = m.vertices; var l2w = mf.transform.localToWorldMatrix;
                var low = new List<Vector2>();
                foreach (int i in HullXZIndices(m))
                {
                    var w = l2w.MultiplyPoint3x4(vs[i]);
                    float gy = Ground(w.x, w.z);
                    if (float.IsNaN(gy) || w.y <= gy + BODY_FOOT_BAND) low.Add(new Vector2(w.x, w.z));
                }
                if (low.Count < 3) continue;
                var arr = low.ToArray(); var hi = EdoGeom.HullXZ(arr);
                if (hi.Length < 3) continue;
                var P = new Vector2[hi.Length];
                for (int k = 0; k < hi.Length; k++) P[k] = arr[hi[k]];
                res.Add(P);
            }
        }
        return res;
    }

    /// <summary>点が <see cref="BodyHulls"/> のどれかの内なら、その添字。無ければ −1。</summary>
    public static int BodyHullHit(IList<Vector2[]> hulls, Vector2 p)
    {
        if (hulls == null) return -1;
        for (int i = 0; i < hulls.Count; i++) if (EdoGeom.PIP(hulls[i], p)) return i;
        return -1;
    }

    /// <summary>**据えた植物の幹の芯が壁体の足元の外形の内か**(硬い・許容0 ── 区域侵犯)。幹の芯は <see cref="NiwaTrunk"/>(地際の頂点の重心)、
    /// 測れなければ実バウンズの芯(呼び手が数える)。<paramref name="trunk"/> = 測った芯。
    /// 当たる先: 算出物の撒いた点を据える全邸(土井 Stage8 ── <see cref="PlantAtPoint"/> の後に呼ぶ)。</summary>
    public static bool PlantInBody(GameObject go, IList<Vector2[]> hulls, out Vector2 trunk)
    {
        if (!NiwaTrunk(go, out trunk)) { var b = RB(go); trunk = new Vector2(b.center.x, b.center.z); }
        return BodyHullHit(hulls, trunk) >= 0;
    }

    /// <summary>**幹の足の下の地表の傾き tanθ** と、足の半径 <paramref name="footR"/>[m](2026-09-29 EDO-0488)。
    /// 足 = 下端から <see cref="ROOT_TOUCH"/> 以内の頂点(<see cref="RootToBed"/> が当たりに数える所と同じ)。その芯のまわりの
    /// 半径 max(R, 0.5) の輪の 16 点と芯で <paramref name="bedAt"/> を引き、最小二乗の面の勾配を返す。
    /// ⛔ ピボット・bounds の中心で芯を取らない(規則21)。足が測れない・地表が NaN なら NaN(呼び手は斜度の沈めを掛けない)。
    /// 当たる先: <see cref="NiwaSet.SlopeSinkK"/> を持つ駒(高木・中木)の据え。</summary>
    public static float FootSlope(GameObject go, Func<float, float, float> bedAt, out float footR)
    {
        footR = 0f;
        var pts = new List<Vector3>(); float yb = float.MaxValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var t = mf.transform;
            foreach (var v in mf.sharedMesh.vertices) { var w = t.TransformPoint(v); pts.Add(w); if (w.y < yb) yb = w.y; }
        }
        if (pts.Count == 0) return float.NaN;
        var sum = Vector2.zero; int n = 0;
        foreach (var w in pts) if (w.y <= yb + ROOT_TOUCH) { sum += new Vector2(w.x, w.z); n++; }
        if (n == 0) return float.NaN;
        var c = sum / n;
        foreach (var w in pts) if (w.y <= yb + ROOT_TOUCH) footR = Mathf.Max(footR, Vector2.Distance(c, new Vector2(w.x, w.z)));
        float r = Mathf.Max(footR, 0.5f);
        // 輪は芯に対して対称なので、面の勾配は Σ h·d / Σ d² で解ける(芯の高さは切片に入るだけ)
        float sx = 0f, sz = 0f, dd = 0f;
        for (int k = 0; k < 16; k++)
        {
            float a = k * Mathf.PI / 8f, dx = r * Mathf.Cos(a), dz = r * Mathf.Sin(a);
            float h = bedAt(c.x + dx, c.y + dz);
            if (float.IsNaN(h)) return float.NaN;
            sx += h * dx; sz += h * dz; dd += dx * dx;
        }
        float gx = sx / dd, gz = sz / dd;   // Σdx² = Σdz²(対称な輪)
        return Mathf.Sqrt(gx * gx + gz * gz);
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
        public List<Vector2[]> Fields = new List<Vector2[]>(); // 菜園・段石(庭域にせず木も下草も入れない ── EDO-0532)
        /// <summary>建物・塀・門の**壁体の足元の外形**(<see cref="BodyHulls"/> ── 屋根・軒を除く実メッシュの XZ 凸包)。
        /// ⭐ **硬い・許容0**: 木・刈込・下草の幹の芯をこの内に置かない(区域侵犯)。⛔ 軒の下は退けない(軒は <see cref="Eaves"/> の柔らかい離れ)。
        /// ⛔ 2026-10-05 EDO-0533 普請検査 第9巡: 土井の庭の地(EdoDoiBuilder.Niwa)は Eaves も Walls も撒かず、刈込玉 Oku_Tsuge_2 の幹が
        /// 長局の縁桁の下(足元の外形の内 0.102m)に立った。Walls は頂点までの距離なので、大きな棟の内の点は頂点から遠く拾えない ── 内外で測る。
        /// 当たる先: NiwaField.Put で据える全ての駒(呼び手が Bodies を撒いた庭 ── 土井の泉水・奥庭)。</summary>
        public List<Vector2[]> Bodies = new List<Vector2[]>();
        /// <summary>**根元が水面の下か**(x, z → true = 水に浸かる)。null なら測らない。⭐ 硬い・許容0(下草・木を水に入れない)。
        /// 呼び手が見えている水面の多角形と描かれた地表で組む(土井: 水面メッシュの縁 PondEdge の内で、地表 &lt; waterY)。</summary>
        public Func<float, float, bool> WetAt;
        /// <summary><c>DropBody</c> = 幹の芯が壁体の足元の外形の内で置かなかった数 / <c>DropWet</c> = 根元が水面の下で置かなかった数。</summary>
        public int DropBody, DropWet;
        public float Cell = 2f;

        // 参道の帯(白洲)— ⛔ ここに木・石・刈込・灯籠を置かない(§5-0 c)
        public List<Vector2> BandA = new List<Vector2>(), BandB = new List<Vector2>();
        public List<float> BandHalf = new List<float>();
        public List<bool> BandWalk = new List<bool>();   // true = 歩く参道 / false = 白洲(木を入れない帯。献灯・手水は立つ)

        // 検査のための控え(§5-2)
        public int Refused, InBand;
        /// <summary>据えてから落とした駒 — 理由別(⛔ 「置けなかった」を一山にしない・規則19)。
        /// <c>DropEave</c> = 実バウンズで軒へ食い込んだ / <c>DropEdge</c> = 実バウンズが区画の線を越えた /
        /// <c>DropSteep</c> = 急斜面で据わらなかった(間引かずに据え直しても埋没>1.0 か 浮き>0.7)。
        /// <c>Reseat</c> = 足元の起伏が大きいので間引かずに据え直した数・<c>TrunkNaN</c> = 幹の芯が測れなかった数。</summary>
        public int DropEave, DropEdge, DropSteep, Reseat, TrunkNaN, Nudged, DropBand;
        /// <summary><c>Neire</c> = 剛体の据え物を下端の全部が着くまで沈めた数(最深 <c>MaxNeire</c>)/
        /// <c>DropNeire</c> = 沈める量が <see cref="NiwaSet.NeireMax"/> を超えて置かなかった数(最悪 <c>WorstNeire</c>)。</summary>
        public int Neire, DropNeire;
        public float MaxNeire, WorstNeire;
        /// <summary><c>SlopeSink</c> = 斜度で沈めを足した高木・中木の数(<see cref="NiwaSet.SlopeSinkK"/>)・<c>MaxSlopeTan</c> = そのうち最も急な足元の tanθ。
        /// 木の沈めは <c>Neire</c>/<c>MaxNeire</c>(上手の最深)にも数え、置けなかった木は <c>DropNeire</c>(上限は TREE_BURY_MAX)に入る。</summary>
        public int SlopeSink;
        public float MaxSlopeTan;
        /// <summary><c>SlopeShort</c> = 斜度の沈め(柔らかい狙い)を埋まりの上限(TREE_BURY_MAX)で頭打ちにした木の数・<c>MaxSlopeShort</c> = 狙いに届かなかった量の最大[m]
        /// (△ 狙い未達 ── 不合格に数えない・2026-10-05 EDO-0533)。</summary>
        public int SlopeShort;
        public float MaxSlopeShort;
        /// <summary><c>RootSunk</c> = 根元の帯の最も浮いた当たりを地表まで沈め切った木・低木・下草の数(最大 <c>MaxRootSunk</c>[m])
        /// ── 2026-10-04 EDO-0533 普請検査 第1回(下草・刈込は根入れを測らず、坂の下手の根元が 0.02〜0.16 浮いた)。</summary>
        public int RootSunk;
        public float MaxRootSunk;
        /// <summary>**据わる床**(相手の地表)。null なら地形(<see cref="Ground"/>)。⭐ 縁の皮を起こした邸は描かれた地表
        /// (<see cref="Drawn"/>().At)を渡す ── 地形の格子で据えると皮の升で根元が浮く(土井 Kari_Oku_4 +0.016・2026-10-04)。</summary>
        public Func<float, float, float> BedAt;
        Func<float, float, float> Bed { get { return BedAt ?? (Func<float, float, float>)Ground; } }
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
                if (InBandFor(k.c, k.tall || k.clump > 0)) InBand++;
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

        public void AddBand(Vector2 a, Vector2 b, float half, bool walk = true)
        { BandA.Add(a); BandB.Add(b); BandHalf.Add(half); BandWalk.Add(walk); }

        /// <summary>検査の「参道の帯に入った駒」に数えるか。⭐ 歩く参道は全ての駒を、白洲の帯は**木だけ**を数える
        /// (2026-09-28 EDO-0477 ── 本堂の前の白洲に立つ献灯の一対が「帯に入った駒 2」と数えられていた。献灯は白洲の参道の左右に立つ物)。</summary>
        bool InBandFor(Vector2 c, bool plant)
        {
            for (int i = 0; i < BandA.Count; i++)
                if ((BandWalk[i] || plant) && EdoGeom.DistToEdge(c, BandA[i], BandB[i]) <= BandHalf[i]) return true;
            return false;
        }

        /// <summary>参道の帯の中か。<paramref name="extra"/> は駒の樹冠半径(帯へ**枝も差し込まない**)。</summary>
        public bool InSando(Vector2 p, float extra)
        {
            for (int i = 0; i < BandA.Count; i++)
                if (EdoGeom.DistToEdge(p, BandA[i], BandB[i]) <= BandHalf[i] + extra) return true;
            return false;
        }

        /// <summary>菜園・段石の外形の中か、縁から <paramref name="m"/> 以内か。</summary>
        public bool InField(Vector2 p, float m)
        {
            for (int i = 0; i < Fields.Count; i++) if (EdoGeom.PIP(Fields[i], p) || EdoGeom.DistToPolyEdge(Fields[i], p) < m) return true;
            return false;
        }

        /// <summary>植物の組か(高木・中木・低木・刈込・下草 ── 剛体の据え物 NeireMax &gt; 0 の石・灯籠・井戸を除く。PutOnce の plant と同じ分け)。</summary>
        static bool IsPlantSet(NiwaSet o) { return o.Tall || o.NeireMax <= 0f; }

        /// <summary>据えた植物の根元が水面の下か ── 幹の芯と、芯のまわり半径 min(樹冠, 0.6)/2 の 8 点(根元の帯の広がり)を <see cref="WetAt"/> で引く。</summary>
        bool RootWet(Vector2 trunk, float rr)
        {
            if (WetAt == null) return false;
            if (WetAt(trunk.x, trunk.y)) return true;
            float r = 0.5f * Mathf.Min(rr, 0.6f);
            for (int k = 0; k < 8; k++)
            {
                float a = k * Mathf.PI / 4f;
                if (WetAt(trunk.x + r * Mathf.Cos(a), trunk.y + r * Mathf.Sin(a))) return true;
            }
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
                    if (InField(p, 1.0f)) continue;
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
            if (o.TrunkEdge > 0f) { if (EdoGeom.DistToPolyEdge(Poly, p) < o.TrunkEdge) return false; }   // 幹の芯で
            else if (EdoGeom.DistToPolyEdge(Poly, p) < r * o.EdgeK) return false;
            if (InSando(p, r)) return false;
            if (!voidOk && InVoid(p)) return false;
            if (InField(p, 0.5f)) return false;                                                // 菜園・段石(幹の芯で)
            if (IsPlantSet(o) && BodyHullHit(Bodies, p) >= 0) return false;                    // 植物: 壁体の足元の外形の内(硬い・幹の芯で)
            if (IsPlantSet(o) && WetAt != null && WetAt(p.x, p.y)) return false;               // 植物: 水面の下(硬い)
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
                // ⭐ 浮きの線は地面との間の +0.01m(2026-09-27 施主・docs/oki-kata.md §4 ── 旧の浮 0.7 は根拠の無い目安で廃止)。
                //    木・下草・景石は根入れで据える物なので、埋まりは下限を広く取ったまま(沈めは意図・§0a)。
                if (float.IsNaN(dy) || dy < -1.0f || dy > 0.01f)
                {
                    WorstSteep = Mathf.Max(WorstSteep, float.IsNaN(dy) ? 0f : Mathf.Abs(dy));
                    UnityEngine.Object.DestroyImmediate(go); DropSteep++; return null;
                }
                rb = RB(go);
            }
            // ⭐ **剛体の据え物は下端の全部を地面へ着ける**(根入れ・docs/oki-kata.md §0a)。SeatOnGround は最寄りの 1 点
            //    (坂の上手)を着けるだけなので、下手は足元の起伏ぶん浮く ── 下端の足跡(RootToBed)で最も浮いた所を測り、
            //    その量だけ沈めて上手を埋める。上限を超える坂には置かない(浮きは許容0・§4a の硬い制約)。
            //    ⛔ 2026-09-29 まで井戸・灯籠は 1 点の接地だけを見て、十坊 8・9 の井戸が坂の下手で 0.75m 浮いていた(EDO-0472)。
            //    当たる先: NiwaSet.Stone を使う全駒(井戸・灯籠・景石・飛石・手水鉢)── 類型の全区画と山王の境内。
            // ⭐ 木・低木・下草(plant)は**根元の帯の当たり**(<see cref="RootBandGap"/>)で測る ── 足跡の外接の箱(RootToBed)は放射の根張りの
            //    隅の根の無い所まで測り、坂の下手の浮きを過大に取って沈め過ぎた(2026-10-04 土井 Matsu_Naka_0 幹の足 1.24m 埋まり)。剛体の据え物は従前どおり箱。
            bool plant = o.Tall || o.NeireMax <= 0f;
            var bed = Bed;
            if (o.NeireMax > 0f)
            {
                var nr = plant ? RootBandGap(go, bed) : RootToBed(go, bed, 0.05f);
                if (!float.IsNaN(nr.hi) && nr.hi > 0.005f)
                {
                    if (nr.hi > o.NeireMax)
                    {
                        WorstNeire = Mathf.Max(WorstNeire, nr.hi);
                        UnityEngine.Object.DestroyImmediate(go); DropNeire++; return null;
                    }
                    go.transform.position -= new Vector3(0f, nr.hi, 0f);
                    Neire++; MaxNeire = Mathf.Max(MaxNeire, nr.hi);
                    rb = RB(go);
                }
            }
            // ⭐ **斜度で沈めを決める**(高木・中木 ── 2026-09-29 EDO-0488 施主)。上の根入れは下手の縁を**ちょうど地表**へ合わせる
            //    だけなので、決めた沈め(sink)は坂の下手で消え、根張りの縁が地表に出て浮いて見えた(斜面林のエノキ)。
            //    足の下の地表の傾き θ を測り、下手の縁を 沈め + R·tanθ·K だけ地中へ入れる。上手の最深が TREE_BURY_MAX を越える坂には置かない。
            //    当たる先: NiwaSet.Tree / Chuboku を使う全駒(類型の庭・屋敷林・斜面の林・明地の木立・縁の帯)。
            if (o.SlopeSinkK > 0f)
            {
                float footR;
                float tan = FootSlope(go, bed, out footR);
                var nr = plant ? RootBandGap(go, bed) : RootToBed(go, bed, 0.05f);
                if (!float.IsNaN(tan) && !float.IsNaN(nr.hi))
                {
                    float want = sink + footR * tan * o.SlopeSinkK;            // 下手の縁の埋まり(柔らかい狙い)
                    float more = nr.hi + want;                                   // nr.hi = 下手の縁 − 地表(≤0 で既に埋まっている)
                    // ⭐⭐ 2026-10-05 EDO-0533(土井 Matsu_Soeyama_0 1.34m・Matsu_Shukei_0 1.49m 埋没): 沈めの狙いは**柔らかい**。上手の最深
                    //    (根元の帯の最深と全ての当たりの最深の大きい方)が TREE_BURY_MAX に届く所で頭打ちにし、未達は ⚠ で数える(SlopeShort)。
                    //    footR は根元の帯(下端から ROOT_TOUCH)の半径で、放射に根を張る松(JG.Pine*)では 2m 前後ある ── 狙いがそのまま
                    //    上手の埋まりになり、旧は 1.5m まで埋めて建てていた。⛔ 狙いのために木を落とさない(落とすのは硬い上限だけ・下の plant の節)。
                    float gAll = LowestGap(go, bed);
                    float low = float.IsNaN(gAll) ? nr.lo : Mathf.Min(nr.lo, gAll);
                    float room = NiwaSet.TREE_BURY_MAX + low;                    // 硬い上限までの余地(low = 最も低い当たりの隙・負 = 埋まり)
                    float give = Mathf.Max(0f, Mathf.Min(more, room));
                    if (more > give + 0.005f) { SlopeShort++; MaxSlopeShort = Mathf.Max(MaxSlopeShort, more - give); }
                    if (give > 0.005f)
                    {
                        go.transform.position -= new Vector3(0f, give, 0f);
                        SlopeSink++; MaxSlopeTan = Mathf.Max(MaxSlopeTan, tan);
                        Neire++; MaxNeire = Mathf.Max(MaxNeire, give - low);
                        rb = RB(go);
                    }
                }
            }
            // ⭐⭐ **硬い・根元の浮き 0**(2026-10-04 EDO-0533 普請検査 第1回 ── 下草 Sk_Juka_0 +0.158・Sk_Juka_14 +0.114・刈込 Kari_Oku_4 +0.016)。
            //    SeatOnGround は最も地面に近い 1 点(坂の上手)を着けるだけで、低木・下草(NeireMax 0)は根入れを測らず、坂の下手の根元が浮いた。
            //    全ての木・低木・下草で根元の帯の最も浮いた当たり(検査と同じ測り)を据わる床まで沈め切る。帯の最深が上限
            //    (高木・中木 TREE_BURY_MAX・低木/下草 SHRUB_BURY_MAX)を越える坂には置かない(DropNeire)。
            //    当たる先: NiwaField.Put で据える全ての植物 ── 類型の庭(EdoTypologyBuilder.Niwa)・土井の泉水と奥庭・NiwaClump・NiwaPutNear。
            if (plant)
            {
                var fr = RootBandGap(go, bed);
                float sinkFr = (!float.IsNaN(fr.hi) && fr.hi > 0f) ? fr.hi : 0f;
                if (sinkFr > 0f)
                {
                    float deepest = fr.hi - fr.lo;                               // 沈め切った後の帯の最深の埋まり
                    float lim = o.Tall ? NiwaSet.TREE_BURY_MAX : NiwaSet.SHRUB_BURY_MAX;
                    if (deepest > lim)
                    {
                        WorstNeire = Mathf.Max(WorstNeire, deepest);
                        UnityEngine.Object.DestroyImmediate(go); DropNeire++; return null;
                    }
                }
                // ⭐ 硬い・全ての当たり(幹の芯・山側の枝葉を含む)の埋まり ≤ PLANT_BURY_MAX(検査と同じ測り・2026-10-05 EDO-0533)。
                //    根元の帯の最深だけでは、帯の外の幹の芯・枝葉の埋まり(土井 Matsu_Shukei_0 帯 −1.443・全体 −1.492)を見落とした。
                float gAll2 = LowestGap(go, bed);
                if (!float.IsNaN(gAll2) && sinkFr - gAll2 > NiwaSet.PLANT_BURY_MAX + 1e-4f)
                {
                    WorstNeire = Mathf.Max(WorstNeire, sinkFr - gAll2);
                    UnityEngine.Object.DestroyImmediate(go); DropNeire++; return null;
                }
                if (sinkFr > 0f)
                {
                    go.transform.position -= new Vector3(0f, sinkFr, 0f);
                    RootSunk++; MaxRootSunk = Mathf.Max(MaxRootSunk, sinkFr);
                    rb = RB(go);
                }
            }
            float rr = Mathf.Max(rb.size.x, rb.size.z) * 0.5f;      // ⭐ 実バウンズで測り直す
            var c = new Vector2(rb.center.x, rb.center.z);
            Vector2 trunk;
            if (!NiwaTrunk(go, out trunk)) { TrunkNaN++; trunk = c; }   // ⛔ 黙って埋めない — 数えて刷る
            // ⭐⭐ 硬い・許容0(2026-10-05 EDO-0533 普請検査 第9巡 ── 刈込玉 Oku_Tsuge_2 が長局の足元の外形の内 0.102m・水際の草 5 株が水面の下 最大 0.160m):
            //    据えた後の**実の幹の芯**で、壁体の足元の外形(Bodies)の内と、根元の水面の下(WetAt)を退ける。狙いの点(Free)でなく現物で測る
            //    (幹は部材の芯からずれる)。⛔ 寄せ直さない ── どこへ寄せるかは呼び手の欄(狙いの半径 atSoft を持つ行は NiwaPutNear が次の候補を試す)。
            //    当たる先: NiwaField.Put / NiwaPutNear / NiwaClump で据える全ての植物のうち、呼び手が Bodies・WetAt を撒いた庭(土井の泉水・奥庭)。
            if (plant && BodyHullHit(Bodies, trunk) >= 0) { UnityEngine.Object.DestroyImmediate(go); DropBody++; return null; }
            if (plant && RootWet(trunk, rr)) { UnityEngine.Object.DestroyImmediate(go); DropWet++; return null; }
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
            // ⭐ 幹の芯で区画の線からの控えを守る(TrunkEdge・据えた後の実の幹で検め直す)
            if (o.TrunkEdge > 0f)
            {
                bool tin = EdoGeom.PIP(Poly, trunk);
                float td0 = EdoGeom.DistToPolyEdge(Poly, trunk);
                if (!tin || td0 < o.TrunkEdge)
                {
                    _edgeNeed = o.TrunkEdge + (tin ? -td0 : td0);
                    _lastRR = rr;
                    UnityEngine.Object.DestroyImmediate(go);
                    return null;
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
            // ⭐ 参道の帯も据えた後の実の芯で検め直す(2026-09-28 EDO-0477 観理院 ── 区画を寄せたら 1 駒が帯へ入った。
            //    Free は据える前の狙いの点で判じ、実の芯が帯へずれた)。許容0 は建てる時点で退ける(検査で捕まえない)。
            if (InBandFor(c, o.Tall || CurClump > 0)) { UnityEngine.Object.DestroyImmediate(go); DropBand++; return null; }
            Komas.Add(new NiwaKoma { c = c, r = rr, trunk = trunk, path = path, layer = layer, clump = CurClump,
                                     block = o.Block, tall = o.Tall,
                                     dw = dw, de = de, clearWall = o.ClearWall, padEave = o.PadEave });
            if (float.IsNaN(MinWall) || dw < MinWall) MinWall = dw;
            if (float.IsNaN(MinEave) || de < MinEave) MinEave = de;
            if (InBandFor(c, o.Tall || CurClump > 0)) InBand++;       // 0 でなければ実装の誤り(§5-2 ②)
            return go;
        }

        /// <summary>被覆率から除く層の語幹(庭方 2026-09-22 の裁定2)。⭐ この5つ**だけ**を除く —
        /// 低木・刈込は**含める**(常緑比の分母=高木+中木とは揃えない)。⛔ 半径の閾値で切らない。
        /// 語幹で見るのは「坪庭の下草」「坪庭の飛石」のような変種を名指しのまま拾うため。</summary>
        static readonly string[] CovSkip = { "下草", "飛石", "景石", "灯籠", "井戸" };

        /// <summary>樹冠の投影の被覆率(庭域に対する)。不合格は 50%超=林 / 5%未満=禿げ。
        /// ⭐ 面積は **union**(重なりを1回だけ)。⛔ πr² の単純和で数えない — 塊は芯々が樹冠半径の
        ///    和の 0.42〜0.75 で寄るので、株に見えるほど二重に数える(実測 toranomonuchi_1 で 58%)。
        /// ⭐ 数えるのは **1m 格子**で、**庭域の内側だけ**(区画の線を越えた樹冠は自動で外れる)。
        ///    ⛔ 2m 格子で数えない — 低木の樹冠(r≈1.0m)を丸ごと拾うか丸ごと落とす。
        /// ⚠ <c>Cells</c> は世界座標の 2 の倍数ではない(<see cref="Solve"/> が Poly の最小角から
        ///    刻む)ので、庭域の番地は**自分の最小の格子点**を原点にして採る。</summary>
        public float Coverage(params string[] layers)
        {
            if (Cells.Count == 0 || Area <= 1f) return 0f;
            // ⭐ 1m の升が 2m の升をちょうど 2×2 に割るように原点を半升ずらす(番地は floor で一致する)
            float ox = float.MaxValue, oz = float.MaxValue;
            for (int i = 0; i < Cells.Count; i++)
            {
                if (Cells[i].x < ox) ox = Cells[i].x;
                if (Cells[i].y < oz) oz = Cells[i].y;
            }
            float bx = ox - Cell * 0.5f, bz = oz - Cell * 0.5f;
            var dom = new HashSet<long>();
            for (int i = 0; i < Cells.Count; i++)
                dom.Add(((long)Mathf.FloorToInt((Cells[i].x - bx) / Cell) << 32)
                        ^ (uint)Mathf.FloorToInt((Cells[i].y - bz) / Cell));

            var sel = new List<NiwaKoma>();
            foreach (var k in Komas)
            {
                if (k.r <= 0f || k.layer == null) continue;
                bool skip = false;
                for (int i = 0; i < CovSkip.Length; i++)
                    if (k.layer.Contains(CovSkip[i])) { skip = true; break; }
                if (skip) continue;                          // ⛔ 下草・飛石・景石・灯籠・井戸だけを除く
                bool take = layers == null || layers.Length == 0;
                if (!take) foreach (var l in layers) if (k.layer == l) { take = true; break; }
                if (take) sel.Add(k);
            }
            if (sel.Count == 0) return 0f;

            // union は格子の数え上げで解く ⭐ 3つ以上の円の union は解析では閉じない。
            // 円ごとに自分の bbox だけを塗るので、手間は「被覆した面積 ÷ 1m²」で済む(全域を舐めない)
            const float q = 1f;
            var hit = new HashSet<long>();
            for (int i = 0; i < sel.Count; i++)
            {
                var k = sel[i]; float r2 = k.r * k.r;
                int x0 = Mathf.FloorToInt((k.c.x - k.r - bx) / q), x1 = Mathf.CeilToInt((k.c.x + k.r - bx) / q);
                int z0 = Mathf.FloorToInt((k.c.y - k.r - bz) / q), z1 = Mathf.CeilToInt((k.c.y + k.r - bz) / q);
                for (int ix = x0; ix <= x1; ix++)
                {
                    float x = bx + (ix + 0.5f) * q, dx = x - k.c.x;
                    if (dx * dx > r2) continue;
                    for (int iz = z0; iz <= z1; iz++)
                    {
                        float z = bz + (iz + 0.5f) * q, dz = z - k.c.y;
                        if (dx * dx + dz * dz > r2) continue;
                        long dk = ((long)Mathf.FloorToInt((x - bx) / Cell) << 32)
                                  ^ (uint)Mathf.FloorToInt((z - bz) / Cell);
                        if (!dom.Contains(dk)) continue;     // ⭐ 庭域の外(区画の線を越えた樹冠)は数えない
                        hit.Add(((long)ix << 32) ^ (uint)iz);
                    }
                }
            }
            return (hit.Count * q * q) / Area;
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
                // ⭐ 乱れは step×0.7(裁定6B)。⛔ 0.4 では等間隔の並木に見える — 塊が据わらず
                //    単木になった箇所ほど、揺れ幅が刻みに対して小さいと定規で引いたように並ぶ
                var foot = a + dir * (s + ((float)rnd.NextDouble() - 0.5f) * step * 0.7f);
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

    // ═══════════════════════ 指図の庭 ── 座標を持つ駒の据え(EDO-0533) ═══════════════════════
    //
    // 庭方が石・木を一つずつ (u,v) で設計した庭(土井邸の泉水・奥庭)の据え。類型の庭(NiwaField.Put の散らし)と違い、
    // 位置・丈・見付の向きは指図が持つ。ここは「置く・測る・据える」だけ(規則21)── 欄を読むのは邸ビルダー。
    // ⛔ 部材の基準点(ピボット・bounds の中心)で位置を決めない。平面は**足(下端の当たり)の重心**、高さは**実メッシュの
    //    天端/下端**か**当たり(RootToBed)**で決める(docs/oki-kata.md §0・§0a)。
    // 当たる先(この節の全関数): EdoDoiBuilder.Niwa 6b〜6h(泉水・奥庭)。以後、指図が石・木を座標で持つ庭の全て。

    /// <summary>水中の石の底を池床より沈める量の帯[m](指図 top-level `gardenFields.seatToBed`「−0.10〜−0.15m」・庭方 2026-10-04)。
    /// **硬い**: 水中の当たりが池床 −LO より上に残る据えは退けず、沈めて直す(浮かせない)。</summary>
    public const float SEAT_TO_BED_LO = 0.10f, SEAT_TO_BED_HI = 0.15f;

    /// <summary>実メッシュの丈を <paramref name="h"/>[m] にする等方スケール(⛔ 名前・呼び寸法から推さない)。部材が無ければ NaN。
    /// 当たる先: 景石・荒磯・岩島・橋挟み石(全丈 H = hExpose/(1−buryRatio))・刈込・刈込玉・中木の丈 h。</summary>
    public static float NiwaScaleForHeight(string path, float h)
    {
        var s = PartSize(path);
        return s.y > 1e-4f ? h / s.y : float.NaN;
    }

    /// <summary>実メッシュの平面の長い方を <paramref name="L"/>[m] にする等方スケール。部材が無ければ NaN。
    /// 当たる先: 護岸の地の石・役石(長軸 lenMin〜lenMax)・飛石(stones の長軸)。</summary>
    public static float NiwaScaleForLong(string path, float L)
    {
        var s = PartSize(path);
        float m = Mathf.Max(s.x, s.z);
        return m > 1e-4f ? L / m : float.NaN;
    }

    /// <summary>**平面の長さ L で、鉛直の丈の下限 hMin を満たす等方スケール**(指図 護岸 `hMin`・押さえ石 `osae.hMin` ── 庭方 2026-10-05)。
    /// 長さ L の倍率と丈 hMin の倍率の大きい方を採る。ただしその倍率で平面の長さが <paramref name="lenCap"/> を越えるなら lenCap の倍率で止め、
    /// <paramref name="hOk"/> = false(丈は下限に届かない)。hMin が NaN なら長さ L の倍率のまま(hOk = true)。部材が無ければ NaN。
    /// **柔らかい**(建てる丈の狙い ── 硬いのは呼び手の「天端が水面より上」)。実寸は <see cref="PartSize"/>(⛔ 名前から推さない)。
    /// 当たる先: 土井の泉水の護岸の地の石・役石・玉石と呑口の押さえ石。以後、汀の石に丈の下限を持つ指図の庭の全て。</summary>
    public static float NiwaScaleForLongHMin(string path, float L, float hMin, float lenCap, out bool hOk)
    {
        hOk = true;
        var s = PartSize(path);
        float m = Mathf.Max(s.x, s.z);
        if (m <= 1e-4f || s.y <= 1e-4f) return float.NaN;
        float sc = L / m;
        if (float.IsNaN(hMin) || sc * s.y >= hMin - 1e-4f) return sc;
        float scH = hMin / s.y, scCap = float.IsNaN(lenCap) ? float.PositiveInfinity : Mathf.Max(sc, lenCap / m);
        if (scH <= scCap + 1e-6f) return scH;
        hOk = false; return scCap;
    }

    /// <summary>石の鉛直の丈のうち**足の芯の地表(池床)より下の割合**(指図 護岸 `buryRatio` の測り ── (足の芯の地表 − 下端) / 丈・0〜1)。測れなければ NaN。</summary>
    public static float NiwaBuryFrac(GameObject go)
    {
        float lo, hi; Vector3 ft;
        if (go == null || !NiwaSpanY(go, out lo, out hi) || hi - lo <= 1e-4f || !NiwaFootPoint(go, out ft)) return float.NaN;
        float g = Ground(ft.x, ft.z);
        return float.IsNaN(g) ? float.NaN : Mathf.Clamp01((g - lo) / (hi - lo));
    }

    // Unity の yaw ry で local +X → (cos ry, −sin ry)・local +Z → (sin ry, cos ry)。
    static float YawLocalAxisTo(bool axisIsX, Vector2 d)
    {
        return axisIsX ? Mathf.Atan2(-d.y, d.x) * Mathf.Rad2Deg : Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
    }

    /// <summary>**見付(広い面)を的へ向ける yaw**。広い面の法線 = 実メッシュの平面で**薄い方の軸**(PartSize で測る)。
    /// 石に表裏は無いので、法線の ± のうち的を向く側を採る。⛔ 部材の名前や指図の注記(「±X」)から軸を推さない。
    /// 当たる先: 景石(faceTo)・荒磯の立石・岩島。</summary>
    public static float NiwaBroadFaceYaw(string path, Vector2 fromXZ, Vector2 toXZ)
    {
        var s = PartSize(path);
        var d = toXZ - fromXZ;
        if (d.sqrMagnitude < 1e-8f) return 0f;
        return YawLocalAxisTo(s.x < s.z, d.normalized);
    }

    /// <summary>実メッシュの平面の**長い方の軸**を <paramref name="dirXZ"/> に沿わせる yaw。
    /// 当たる先: 水尻の閾(長手を汀の接線に)・沓脱石(長手を縁と平行)・橋(長手を袂から袂へ)・延段。</summary>
    public static float NiwaLongAlongYaw(string path, Vector2 dirXZ)
    {
        var s = PartSize(path);
        if (dirXZ.sqrMagnitude < 1e-8f) return 0f;
        return YawLocalAxisTo(s.x >= s.z, dirXZ.normalized);
    }

    /// <summary>駒の実メッシュの全頂点の高さの範囲(世界)。⛔ Renderer.bounds は傾けた駒で膨らむので使わない。</summary>
    public static bool NiwaSpanY(GameObject go, out float yLo, out float yHi)
    {
        yLo = float.MaxValue; yHi = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices) { float y = l2w.MultiplyPoint3x4(v).y; if (y < yLo) yLo = y; if (y > yHi) yHi = y; }
        }
        return yLo <= yHi;
    }

    /// <summary>**足の芯** ── 下端から ROOT_TOUCH 以内の頂点の重心(XZ)と下端の高さ。⛔ ピボット・bounds の中心で代えない。</summary>
    public static bool NiwaFootPoint(GameObject go, out Vector3 foot)
    {
        foot = go.transform.position;
        var pts = new List<Vector3>(); float yb = float.MaxValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices) { var w = l2w.MultiplyPoint3x4(v); pts.Add(w); if (w.y < yb) yb = w.y; }
        }
        if (pts.Count == 0) return false;
        var sum = Vector2.zero; int n = 0;
        foreach (var w in pts) if (w.y <= yb + ROOT_TOUCH) { sum += new Vector2(w.x, w.z); n++; }
        if (n == 0) return false;
        sum /= n;
        foot = new Vector3(sum.x, yb, sum.y);
        return true;
    }

    /// <summary>**平面の位置を足の芯で合わせる**(指図の (u,v) = 石・灯籠の据え位置)。足が測れなければ false(動かさない・呼び手が数える)。</summary>
    public static bool NiwaFootOn(GameObject go, Vector2 xz)
    {
        Vector3 f;
        if (!NiwaFootPoint(go, out f)) return false;
        go.transform.position += new Vector3(xz.x - f.x, 0f, xz.y - f.z);
        return true;
    }

    /// <summary>**足の芯を軸に、頭を <paramref name="towardXZ"/> の向きへ <paramref name="deg"/>° 倒す**(荒磯の立石の tilt・
    /// 木の lean・乱杭の傾き)。足の芯は動かない。⭐ 倒した後の据え直しは呼び手(当たりで測り直す)。</summary>
    public static void NiwaTilt(GameObject go, Vector2 towardXZ, float deg)
    {
        if (Mathf.Abs(deg) < 1e-4f || towardXZ.sqrMagnitude < 1e-8f) return;
        Vector3 f;
        if (!NiwaFootPoint(go, out f)) f = go.transform.position;
        var d = new Vector3(towardXZ.x, 0f, towardXZ.y).normalized;
        float r = deg * Mathf.Deg2Rad;
        var up2 = Vector3.up * Mathf.Cos(r) + d * Mathf.Sin(r);
        var q = Quaternion.FromToRotation(Vector3.up, up2);
        go.transform.position = f + q * (go.transform.position - f);
        go.transform.rotation = q * go.transform.rotation;
    }

    /// <summary>実メッシュの天端を <paramref name="y"/> へ。返り値 = 動かした量[m]。
    /// **柔らかい**狙いの高さ(護岸の天端 waterY+cap・乱杭の頭 waterY+topAbove・閾の sill・橋の topY)を当てるのに使う。</summary>
    public static float NiwaTopTo(GameObject go, float y)
    {
        float lo, hi;
        if (!NiwaSpanY(go, out lo, out hi)) return float.NaN;
        float dy = y - hi;
        go.transform.position += new Vector3(0f, dy, 0f);
        return dy;
    }

    /// <summary>**硬い・池床へ沈める**(全ての当たり): 下端の当たり(<see cref="RootToBed"/>)のうち最も浅い所を
    /// 池床(描かれた地表 = 6a で掘った池床)− <paramref name="sink"/> に据える。他の当たりはそれより深く入る(埋めて隠す)。
    /// 返り値 = 動かした量[m]。当たりが測れなければ NaN。<paramref name="deepest"/> = 最も深い当たりの埋まり(負)。
    /// 当たる先: 岩島の大石・肩石(全身が水中の石)。</summary>
    public static float NiwaSeatToBed(GameObject go, float sink, out float deepest)
    {
        deepest = float.NaN;
        var rt = RootToBed(go, Ground, 0.05f);
        if (float.IsNaN(rt.hi)) return float.NaN;
        float dy = -sink - rt.hi;
        go.transform.position += new Vector3(0f, dy, 0f);
        deepest = rt.lo + dy;
        return dy;
    }

    /// <summary>**硬い・水中の足を池床より沈める**: 下端の当たりのうち**池床が水面より下の所だけ**を測り
    /// (陸の上の当たりは跨ぎ ── 測らない)、そのどれかが池床 −<paramref name="sink"/> より上なら、全部がそこへ入るまで沈める。
    /// ⛔ 上げはしない(陸の側の据えを崩さない)。返り値 = 沈めた量[m](≤0)。<paramref name="wetN"/> = 水中の当たりの標本数(0 = 陸だけの石)。
    /// 当たる先: 護岸の石・玉石・荒磯・州浜の玉石・水落石(汀に半ば掛かる)・乱杭・閾・呑口・橋挟み石。</summary>
    public static float NiwaSinkWetFeet(GameObject go, float waterY, float sink, out int wetN)
    {
        Func<float, float, float> wetBed = (x, z) => { float g = Ground(x, z); return g < waterY ? g : float.NaN; };
        var rt = RootToBed(go, wetBed, 0.05f);
        wetN = rt.atariN;
        if (float.IsNaN(rt.hi) || rt.hi <= -sink) return 0f;
        float dy = -(rt.hi + sink);
        go.transform.position += new Vector3(0f, dy, 0f);
        return dy;
    }

    /// <summary>**天端を地表 + <paramref name="above"/> に据える**(飛石・踏分石・沓脱石の「地盤 +0.03〜0.05」)。
    /// 天端の面(最高点から 0.02m 以内の頂点)の真下の地表の**最も高い所**へ合わせる ── 天端のどこも地中に入れない(硬い)。
    /// <paramref name="floatWorst"/> = 据えた後の下端の当たりの最大の浮き[m](&gt; 0.01 は浮き ── 硬い・呼び手が数えて刷る)。</summary>
    public static float NiwaTopAboveGround(GameObject go, float above, out float floatWorst)
    {
        floatWorst = float.NaN;
        float lo, hi;
        if (!NiwaSpanY(go, out lo, out hi)) return float.NaN;
        float gMax = NiwaGroundUnderTop(go);
        if (float.IsNaN(gMax)) return float.NaN;
        float dy = gMax + above - hi;
        go.transform.position += new Vector3(0f, dy, 0f);
        floatWorst = RootToBed(go, Ground, 0.05f).hi;
        return dy;
    }

    /// <summary>**橋を袂から袂へ架ける**。長手(実メッシュの平面の長い方)を a→b に沿わせ、**両端の端面を測って**
    /// a・b の外へ等しく掛かるよう寄せ(掛かり = (実長 − 径間)/2)、両側面を測って芯を a–b の線に通す。
    /// 高さは実メッシュの天端(<paramref name="topAtEnds"/> なら両端 0.10m の帯の天端 ── 反りのある土橋の endTopY)を <paramref name="topY"/> へ。
    /// 返り値 = 掛かりの小さい方[m](負 = 径間に足りない ── **硬い**: 呼び手は退ける)。
    /// <paramref name="endGap"/> = 掛かりの帯の下端 − 地表 の大きい方[m](&gt; 0 = 橋台の上で版が浮く ── 指図 `abut`「版の下面は橋台石の天端に接する(硬い)」)。
    /// 当たる先: 泉水の石橋・土橋(hashi[])。</summary>
    public static float NiwaSpanBridge(GameObject go, string path, Vector2 aXZ, Vector2 bXZ, float topY, bool topAtEnds, out float endGap)
    {
        endGap = float.NaN;
        var ab = bXZ - aXZ; float span = ab.magnitude;
        if (span < 1e-4f) return float.NaN;
        var dir = ab / span; var perp = new Vector2(-dir.y, dir.x);
        go.transform.rotation = Quaternion.Euler(0f, NiwaLongAlongYaw(path, dir), 0f);
        var pts = new List<Vector3>();
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices) pts.Add(l2w.MultiplyPoint3x4(v));
        }
        if (pts.Count == 0) return float.NaN;
        float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue;
        foreach (var w in pts)
        {
            var q = new Vector2(w.x, w.z) - aXZ;
            float s = Vector2.Dot(q, dir), t = Vector2.Dot(q, perp);
            s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); t0 = Mathf.Min(t0, t); t1 = Mathf.Max(t1, t);
        }
        float ds = (span - s1 - s0) * 0.5f, dt = -(t0 + t1) * 0.5f;
        var shift = dir * ds + perp * dt;
        go.transform.position += new Vector3(shift.x, 0f, shift.y);
        float bear = (s1 - s0 - span) * 0.5f;
        // 天端
        float top = float.MinValue;
        foreach (var w0 in pts)
        {
            var w = w0 + new Vector3(shift.x, 0f, shift.y);
            float s = Vector2.Dot(new Vector2(w.x, w.z) - aXZ, dir);
            if (topAtEnds && s > -bear + 0.10f && s < span + bear - 0.10f) continue;
            top = Mathf.Max(top, w.y);
        }
        float dy = topY - top;
        go.transform.position += new Vector3(0f, dy, 0f);
        // 掛かりの帯の下端 − 地表(両端それぞれの最小を取り、その大きい方)
        float gA = float.MaxValue, gB = float.MaxValue;
        foreach (var w0 in pts)
        {
            var w = w0 + new Vector3(shift.x, dy, shift.y);
            float s = Vector2.Dot(new Vector2(w.x, w.z) - aXZ, dir);
            float d = w.y - Ground(w.x, w.z);
            if (s <= 0f) gA = Mathf.Min(gA, d); else if (s >= span) gB = Mathf.Min(gB, d);
        }
        if (gA < float.MaxValue && gB < float.MaxValue) endGap = Mathf.Max(gA, gB);
        return bear;
    }

    /// <summary>**多角形の内を株間で埋める点**(刈込の「多角形」── 指図 `karikomiCommon`: 株間 = 部材の実寸 × 0.8・株は奇数で止める)。
    /// 株間の格子を ±25% 散らし(⛔ 格子のまま並べない)、内の点だけ残し、偶数なら最後の 1 点を落とす。
    /// 当たる先: 泉水の刈込 Kari_1〜3・奥庭の大刈込 Kari_Oku。</summary>
    public static List<Vector2> NiwaFillPoly(Vector2[] polyXZ, float pitch, System.Random rnd)
    {
        var res = new List<Vector2>();
        if (polyXZ == null || polyXZ.Length < 3 || pitch <= 1e-3f) return res;
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var p in polyXZ) { x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); z0 = Mathf.Min(z0, p.y); z1 = Mathf.Max(z1, p.y); }
        for (float x = x0 + pitch * 0.5f; x <= x1; x += pitch)
            for (float z = z0 + pitch * 0.5f; z <= z1; z += pitch)
            {
                var q = new Vector2(x + ((float)rnd.NextDouble() - 0.5f) * pitch * 0.5f,
                                    z + ((float)rnd.NextDouble() - 0.5f) * pitch * 0.5f);
                if (EdoGeom.PIP(polyXZ, q)) res.Add(q);
            }
        if (res.Count == 0)
        {
            // 株間より細い多角形 ── 重心に 1 株(内にあれば)
            var c = Vector2.zero; foreach (var p in polyXZ) c += p; c /= polyXZ.Length;
            if (EdoGeom.PIP(polyXZ, c)) res.Add(c);
        }
        if (res.Count > 1 && res.Count % 2 == 0) res.RemoveAt(res.Count - 1);
        return res;
    }

    /// <summary>**据えた木を傾ける**(指図 `lean: {deg, to}`)。足の芯を軸に頭を倒し(<see cref="NiwaTilt"/>)、倒して浮いた根張りの縁を
    /// 根元の帯の当たり(<see cref="RootBandGap"/>)で測って地面まで沈める(**硬い**: 浮き 0)。返り値 = 沈めた量[m]。
    /// <paramref name="deepest"/> = 沈めた後の最も深い埋まり[m](根元の帯と全ての当たり <see cref="LowestGap"/> の深い方 ── 検査と同じ測り)。</summary>
    /// <param name="bedAt">据わる床(null なら地形)。⭐ 根元は<see cref="RootBandGap"/>(根元の帯の当たり)で測る ── 傾けた木の足跡の外接の箱は
    /// 根の無い隅を測って沈め過ぎた(2026-10-04 土井 Matsu_Naka_0)。当たる先: 庭の傾けた木(土井の泉水の松・以後の lean の全て)。</param>
    public static float NiwaLeanTree(GameObject go, Vector2 towardXZ, float deg, out float deepest, Func<float, float, float> bedAt = null)
    {
        float used; return NiwaLeanTree(go, towardXZ, deg, out deepest, out used, bedAt);
    }

    /// <summary>傾けの角は**柔らかい狙い**、埋まりの上限 <see cref="NiwaSet.TREE_BURY_MAX"/> は**硬い**(docs/oki-kata.md §4a・2026-10-05 EDO-0533)。
    /// 狙いの角で倒して沈めた後の最深が上限を越えるなら、角を 1° ずつ(角の 1/8 が大きければそれ)起こして試し、上限に収まる最も大きい角で据える。
    /// 0° は Put が上限の内で据えた姿なので必ず収まる。<paramref name="degUsed"/> = 据えた角(&lt; <paramref name="deg"/> なら呼び手が ⚠ と実測で名乗る)。
    /// ⛔ 2026-10-05 まで角を固定して上限を見ずに沈め、土井 Matsu_Naka_0(12°)1.26m・Matsu_Misaki_0(10°)1.15m・Matsu_Shukei_0(5°)1.49m が埋まったまま建った
    /// ── 放射に根を張る松は倒すと根の先が 根の半径 × sin(角) だけ浮き、その分を沈めて上手と幹の芯が埋まった。</summary>
    public static float NiwaLeanTree(GameObject go, Vector2 towardXZ, float deg, out float deepest, out float degUsed, Func<float, float, float> bedAt = null)
    {
        var bed = bedAt ?? (Func<float, float, float>)Ground;
        var p0 = go.transform.position; var r0 = go.transform.rotation;
        float step = Mathf.Max(1f, Mathf.Abs(deg) / 8f), d = deg;
        while (true)
        {
            go.transform.SetPositionAndRotation(p0, r0);
            NiwaTilt(go, towardXZ, d);
            var rt = RootBandGap(go, bed);
            float sunk = (!float.IsNaN(rt.hi) && rt.hi > 0.005f) ? rt.hi : 0f;
            if (sunk > 0f) go.transform.position -= new Vector3(0f, sunk, 0f);
            float g = LowestGap(go, bed);
            float lo = float.IsNaN(rt.lo) ? float.NaN : rt.lo - sunk;
            float low = float.IsNaN(g) ? lo : (float.IsNaN(lo) ? g : Mathf.Min(lo, g));
            deepest = float.IsNaN(low) ? 0f : Mathf.Max(0f, -low);
            if (deepest <= NiwaSet.TREE_BURY_MAX + 1e-4f || Mathf.Abs(d) < 1e-4f) { degUsed = d; return sunk; }
            d = Mathf.Abs(d) <= step ? 0f : d - Mathf.Sign(d) * step;
        }
    }

    /// <summary>指図の石一つの据えの記録(邸ビルダーが刷る)。</summary>
    public struct NiwaIshiRep
    {
        /// <summary>据えた丈(実メッシュ)・見え高(天端 − max(地表, 水面))・狙いの天端からの不足(柔らかい・正 = 低い)・
        /// 水中の足で沈めた量(≤0)・陸の根入れ(下手の浮きを沈めた量)。</summary>
        public float H, expose, topShort, wetSink, neire;
        /// <summary>天端 − 天端の面の下の地表の最も高い所[m](<see cref="NiwaGroundUnderTop"/> ── 検査の「天端まで埋没」と同じ測り。≤ 0 = 天端まで埋まる ✗)・
        /// 埋まりを解くため硬い条件の余地の内で持ち上げた量[m](2026-10-04 EDO-0533 普請検査 第1回)。</summary>
        public float topAbove, topLift;
        /// <summary>水中の当たりの標本数・陸の根入れが NiwaSet.STONE_NEIRE_MAX を越えたか(越えても沈める ── 埋めて隠す・⚠ で刷る)。</summary>
        public int wetN; public bool neireOver;
    }

    /// <summary>**指図の石を一つ据える**(景石・護岸の石・玉石・荒磯・岩島・州浜の玉石・橋挟み石・乱杭)。順は
    /// 置く → 倒す(<paramref name="tiltDeg"/>)→ **足の芯**を (u,v) へ → 高さ → 水中の足を沈める。高さは次のどれか一つ:
    /// <list type="bullet">
    /// <item><paramref name="fromBed"/>: 全身が水中の石 ── 当たりの最も浅い所を池床 −<paramref name="bedSink"/>(<see cref="NiwaSeatToBed"/>・硬い)。</item>
    /// <item><paramref name="aimTop"/> が数: 天端をそこへ(護岸の天端 waterY+cap・乱杭の頭 ── **柔らかい**。水中の足の硬い条件で沈めたら topShort に刷る)。</item>
    /// <item>足の芯の下が水中: 天端 = 水面 + 丈 ×(1 − <paramref name="bury"/>)(hExpose は水上の丈 ── gardenFields.hExpose)。</item>
    /// <item>陸: 丈 × <paramref name="bury"/> を地中へ(<see cref="SeatOnGround"/>)。</item>
    /// </list>
    /// fromBed 以外は続けて、下端の当たりの浮きを根入れで沈める(**硬い**・浮き 0 ── 坂の下手・陸に掛かった護岸の石)。
    /// 最後に水面が数なら <see cref="NiwaSinkWetFeet"/>(硬い・池床 −<paramref name="bedSink"/>)。測れない駒は取り除いて null(黙って浮かせない)。</summary>
    public static GameObject NiwaIshiSueru(Transform parent, string name, string path, Vector2 xz, float yaw, float scale,
                                           float bury, float waterY, float bedSink, out NiwaIshiRep rep,
                                           float aimTop = float.NaN, bool fromBed = false,
                                           Vector2 tiltTo = default(Vector2), float tiltDeg = 0f)
    {
        rep = new NiwaIshiRep { H = float.NaN, expose = float.NaN, topShort = float.NaN, wetSink = 0f, neire = 0f, topAbove = float.NaN, topLift = 0f };
        if (string.IsNullOrEmpty(path) || float.IsNaN(scale) || scale <= 0f) return null;
        var go = Place(path, new Vector3(xz.x, Ground(xz.x, xz.y), xz.y), yaw, Vector3.one * scale, parent, name);
        if (go == null) return null;
        if (tiltDeg != 0f) NiwaTilt(go, tiltTo, tiltDeg);
        if (!NiwaFootOn(go, xz)) { UnityEngine.Object.DestroyImmediate(go); return null; }
        float lo, hi;
        if (!NiwaSpanY(go, out lo, out hi)) { UnityEngine.Object.DestroyImmediate(go); return null; }
        rep.H = hi - lo;
        bool hasWater = !float.IsNaN(waterY);
        float g0 = Ground(xz.x, xz.y);
        if (fromBed)
        {
            float deep;
            if (float.IsNaN(NiwaSeatToBed(go, bedSink, out deep))) { UnityEngine.Object.DestroyImmediate(go); return null; }
        }
        else if (!float.IsNaN(aimTop)) NiwaTopTo(go, aimTop);
        else if (hasWater && g0 < waterY) NiwaTopTo(go, waterY + rep.H * (1f - Mathf.Clamp01(bury)));
        else
        {
            try { SeatOnGround(go, rep.H * Mathf.Clamp01(bury), 4000); }
            catch (Exception) { UnityEngine.Object.DestroyImmediate(go); return null; }
        }
        if (!fromBed)
        {
            // 硬い・浮き 0: どの据え方でも、下端の当たりのどこかが地表(陸・池床)から浮いていれば沈める(坂の下手・陸に掛かった護岸の石・乱杭の足)
            var rt = RootToBed(go, Ground, 0.05f);
            if (!float.IsNaN(rt.hi) && rt.hi > 0.005f)
            {
                go.transform.position -= new Vector3(0f, rt.hi, 0f);
                rep.neire = rt.hi; rep.neireOver = rt.hi > NiwaSet.STONE_NEIRE_MAX;
            }
        }
        if (hasWater) { int wn; rep.wetSink = NiwaSinkWetFeet(go, waterY, bedSink, out wn); rep.wetN = wn; }
        NiwaSpanY(go, out lo, out hi);
        // ⭐ 硬い・天端まで埋めない(2026-10-04 EDO-0533 普請検査 第1回 ── 護岸の石 13 が天端まで埋まった): 天端の面の下の地表の最も高い所より
        //    天端が低ければ、**硬い条件の余地の内だけ**持ち上げる ── 陸の当たりは浮かない(最も浮いた当たり ≤ 0)・水中の足は池床 −bedSink より下。
        //    余地が無ければ動かさず topAbove ≤ 0 を刷る(⛔ 浮かせて辻褄を合わせない ── 石の大きさ・汀の地形の欄の問題として呼び手が名指す)。
        //    当たる先: NiwaIshiSueru で据える全ての石(護岸・玉石・荒磯・州浜の玉石・岩島・橋挟み石・乱杭・景石)── 土井の泉水・以後の指図の庭。
        if (!fromBed)
        {
            float gTop = NiwaGroundUnderTop(go);
            if (!float.IsNaN(gTop) && hi < gTop + 0.02f)
            {
                var ra = RootToBed(go, Ground, 0.05f);
                float room = float.IsNaN(ra.hi) ? 0f : Mathf.Max(0f, -ra.hi);
                if (hasWater)
                {
                    Func<float, float, float> wetBed = (x, z) => { float g = Ground(x, z); return g < waterY ? g : float.NaN; };
                    var rw = RootToBed(go, wetBed, 0.05f);
                    if (!float.IsNaN(rw.hi)) room = Mathf.Min(room, Mathf.Max(0f, -bedSink - rw.hi));
                }
                float lift = Mathf.Min(gTop + 0.02f - hi, room);
                if (lift > 0.001f) { go.transform.position += new Vector3(0f, lift, 0f); rep.topLift = lift; NiwaSpanY(go, out lo, out hi); }
            }
            float gTop2 = NiwaGroundUnderTop(go);
            rep.topAbove = float.IsNaN(gTop2) ? float.NaN : hi - gTop2;
        }
        if (!float.IsNaN(aimTop)) rep.topShort = aimTop - hi;
        float refY = hasWater ? Mathf.Max(g0, waterY) : g0;
        rep.expose = hi - refY;
        return go;
    }

    /// <summary>汀の石の一つの置き場の候補(<see cref="NiwaIshiSueruAbove"/>)── 部材・足の芯・等方の倍率・狙いの天端(NaN = 無し)・何を変えたか。</summary>
    public struct NiwaIshiSpot { public string path; public Vector2 xz; public float scale, aimTop; public string why; }

    /// <summary>天端が水面より上と数える余裕[m](丸めの誤差だけ ── 検査の「天端が水面の下」の線は水面そのもの)。</summary>
    public const float NIWA_TOP_OVER_WATER = 0.005f;

    /// <summary>**汀の石を、天端を水面より上に据える**(硬い・許容0 ── 護岸・玉石・押さえ石・州浜の玉石など見せる石)。
    /// <paramref name="spots"/> を順に <see cref="NiwaIshiSueru"/> で据え、天端 ≥ <paramref name="waterY"/> + <see cref="NIWA_TOP_OVER_WATER"/> の最初の物を残す
    /// (<see cref="PlaceBest{T}"/> の Hard)。候補の順 = 狙いに近い順で、候補は**呼び手が指図の欄の帯の内だけで**組む(inset の帯・石の長さの帯 ──
    /// ⛔ 帯の外の値を発明しない)。どれも水面の下なら**建てない**(null)── 呼び手が名指す(<paramref name="bestTop"/> = 試した中の最も高い天端)。
    /// ⭐ 水面の下に沈むのは、狙いの天端(waterY + cap)で据えた後に**水中の足を池床 −seatToBed へ沈める硬い条件**(<see cref="NiwaSinkWetFeet"/>)が
    /// 石を引き下げるため ── 石の丈 &lt; cap + 足の下の水深 + seatToBed。浅い所(汀へ寄せる)か丈のある石(長さの帯の上)で解く。
    /// ⛔ 2026-10-05 EDO-0533 普請検査 第9巡まで天端の下限を持たず、汀の石 14 が天端 25.91〜25.996(水面 26.00)で建っていた。
    /// <paramref name="usedSpot"/> = 残した候補の添字(0 = 狙いのまま・−1 = 建てない)。
    /// 当たる先: 土井の泉水の護岸(Gogan_*・中島 Gogan_Naka_N)・呑口の押さえ石・州浜の玉石。以後、指図が汀の石を持つ庭の全て。</summary>
    public static GameObject NiwaIshiSueruAbove(Transform parent, string name, IList<NiwaIshiSpot> spots, float yaw, float bury,
                                                float waterY, float bedSink, SeiyakuTally tally, out NiwaIshiRep rep, out int usedSpot, out float bestTop,
                                                Vector2 tiltTo = default(Vector2), float tiltDeg = 0f)
    {
        float bta;
        return NiwaIshiSueruAbove(parent, name, spots, yaw, bury, waterY, bedSink, tally, false, out rep, out usedSpot, out bestTop, out bta, tiltTo, tiltDeg);
    }

    /// <summary><see cref="NiwaIshiSueruAbove(Transform, string, IList{NiwaIshiSpot}, float, float, float, float, SeiyakuTally, out NiwaIshiRep, out int, out float, Vector2, float)"/> に、
    /// <paramref name="topOverGround"/> = true で**天端が地表より上**(<see cref="NiwaIshiRep.topAbove"/> &gt; 0 ── 検査の「天端まで埋没」と同じ測り)も硬い制約に足す版
    /// (2026-10-05 EDO-0533 第11巡 ── 汀の石 6 個が天端まで埋まったまま建った: NiwaIshiSueru は余地の内でしか持ち上げず、帯の他の置き場を試さなかった)。
    /// 帯の内の候補(寄せ・大きさ・個体)を同じ順で試し、どれも埋まるなら建てない。<paramref name="bestTopAbove"/> = 試した中の最も大きい topAbove[m](名指しに使う)。
    /// 当たる先: 土井の泉水の護岸・押さえ石・州浜の玉石(EdoDoiBuilder.Niwa が true で呼ぶ)。他邸は既定の版のまま。
    /// <para>⭐ <paramref name="buryLo"/>〜<paramref name="buryHi"/>(指図 護岸 `buryRatio`・庭方 2026-10-05)を渡すと、丈のうち池床より下の割合
    /// (<see cref="NiwaBuryFrac"/>)をその帯へ入れる**柔らかい**狙いを足す ── 硬い条件を通った候補のうち帯の内の最初の物、無ければ帯から最も近い物を建てる
    /// (<see cref="PlaceBest{T}"/> の Soft・⚠ は tally の「狙い未達」に数える)。NaN = 狙わない(既定)。</para></summary>
    public static GameObject NiwaIshiSueruAbove(Transform parent, string name, IList<NiwaIshiSpot> spots, float yaw, float bury,
                                                float waterY, float bedSink, SeiyakuTally tally, bool topOverGround,
                                                out NiwaIshiRep rep, out int usedSpot, out float bestTop, out float bestTopAbove,
                                                Vector2 tiltTo = default(Vector2), float tiltDeg = 0f, float buryLo = float.NaN, float buryHi = float.NaN)
    {
        var reps = new NiwaIshiRep[spots.Count];
        float bt = float.NegativeInfinity, bta = float.NegativeInfinity; int cur = -1;
        var idx = new List<int>(); for (int i = 0; i < spots.Count; i++) idx.Add(i);
        var hard = new List<Hard> { new Hard("汀の石の天端が水面より上", g => { float lo, hi; return NiwaSpanY(g, out lo, out hi) && hi >= waterY + NIWA_TOP_OVER_WATER; }) };
        if (topOverGround)
            hard.Add(new Hard("汀の石の天端が地表より上", g => cur < 0 || float.IsNaN(reps[cur].topAbove) || reps[cur].topAbove > 0f));
        var softs = new List<Soft>();
        if (!float.IsNaN(buryLo) && !float.IsNaN(buryHi))
            softs.Add(new Soft("汀の石の丈の池床より下の割合 " + buryLo.ToString("F1") + "〜" + buryHi.ToString("F1") + "(帯からの外れ ×−1)", 0f, g =>
            {
                float f = NiwaBuryFrac(g); if (float.IsNaN(f)) return -1f;
                return f < buryLo ? f - buryLo : (f > buryHi ? buryHi - f : 0f);
            }));
        var go = PlaceBest<int>(idx, idx.Count, i =>
        {
            cur = i; var s = spots[i];
            var g = NiwaIshiSueru(parent, name, s.path, s.xz, yaw, s.scale, bury, waterY, bedSink, out reps[i], s.aimTop, false, tiltTo, tiltDeg);
            float lo, hi; if (g != null && NiwaSpanY(g, out lo, out hi)) bt = Mathf.Max(bt, hi);
            if (g != null && !float.IsNaN(reps[i].topAbove)) bta = Mathf.Max(bta, reps[i].topAbove);
            return g;
        }, hard, softs, tally);
        usedSpot = go != null ? cur : -1;
        rep = go != null ? reps[cur] : (spots.Count > 0 ? reps[0] : default(NiwaIshiRep));
        bestTop = float.IsNegativeInfinity(bt) ? float.NaN : bt;
        bestTopAbove = float.IsNegativeInfinity(bta) ? float.NaN : bta;
        return go;
    }

    // ─────────── 指図の庭 ── 縁・段・生垣・腰掛の据え(EDO-0533 第7巡) ───────────
    //
    // 当たる先(この小節の全関数): EdoDoiBuilder.Niwa 6d(沓脱 Shoin/Naga・縁先手水鉢・腰掛)・6e(丸太段)・6h(奥庭の生垣)。
    // 以後、御殿(EdoGotenKit が組む棟)の縁へ据える庭の物(沓脱・手水鉢・踏石)・園路の土留め段・塀の内に沿う生垣の全て。

    /// <summary>Village Kit の倍率(vklib.S = 2.0m/間 → 江戸間 1.818m/間)。CLAUDE.md の寸法表と同じ値。</summary>
    public const float VK_S = 0.909f;

    /// <summary><see cref="EngawaTopNear"/> の返り。y = 縁板の天端[m](NaN = 届く所に縁が無い)・dist = 点から天端の面までの平面距離[m]
    /// (0 = 点が縁板の真下)・on = 天端の面の最寄りの点(XZ)・piece = 当たった縁の駒・mune = その駒を持つ棟(建物の群の直下の子)の名。</summary>
    public struct EngawaHit { public float y, dist; public Vector2 on; public GameObject piece; public string mune; }

    static bool IsEngawaPiece(GameObject go)
    {
        string p = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        if (string.IsNullOrEmpty(p)) return false;
        return p == EdoAssets.Goten.Nureen || p == EdoAssets.Goten.NureenCorner
            || p == EdoAssets.Goten.RokaEnita || p == EdoAssets.Goten.FloorBoard;
    }

    static Vector2 NiwaClosestOnSeg(Vector2 p, Vector2 a, Vector2 b)
    {
        var ab = b - a; float l2 = ab.sqrMagnitude;
        if (l2 < 1e-12f) return a;
        return a + ab * Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2);
    }

    static float DistPointTri2(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
    {
        float d1 = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x);
        float d2 = (c.x - b.x) * (p.y - b.y) - (c.y - b.y) * (p.x - b.x);
        float d3 = (a.x - c.x) * (p.y - c.y) - (a.y - c.y) * (p.x - c.x);
        bool neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0;
        if (!(neg && pos)) return 0f;
        return Mathf.Min((NiwaClosestOnSeg(p, a, b) - p).magnitude, Mathf.Min((NiwaClosestOnSeg(p, b, c) - p).magnitude, (NiwaClosestOnSeg(p, c, a) - p).magnitude));
    }

    /// <summary>**縁板の天端を測る**(沓脱石の天端 = 縁板の天端 −0.40 など、縁に取り合う庭の物の高さの相手)。
    /// <paramref name="buildings"/> の下の御殿の縁の駒(<see cref="EdoAssets.Goten.Nureen"/>・NureenCorner・RokaEnita・FloorBoard ──
    /// プレハブの資産の名で見分ける)の実メッシュから、**上向きの面**(世界の法線 y &gt; 0.95)を拾い、駒ごとに**面積の最も大きい高さ**を
    /// 縁板の天端とする(高欄の笠木・束石の天端など上向きの小面を拾わない)。点 <paramref name="at"/> に平面で最も近い天端の面の
    /// 高さを返す(<paramref name="reach"/>[m] より遠ければ y = NaN)。<paramref name="mune"/> を渡せばその棟の縁だけを見る。
    /// ⛔ 駒の基準点・<c>EdoGotenKit.NUREEN_DROP</c> の床高の式から推さない(棟の面は造成で動き、縁の足は伸ばされる)。
    /// 測るだけで何も動かさない。**硬い・柔らかいの別は呼び手**(沓脱の「縁板の天端 −0.40」は狙い、届く縁が無いのは据えない理由)。</summary>
    public static EngawaHit EngawaTopNear(Vector2 at, Transform buildings, float reach, string mune = null)
    {
        var res = new EngawaHit { y = float.NaN, dist = float.PositiveInfinity };
        if (buildings == null) return res;
        foreach (var mf in buildings.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh;
            if (mesh == null || !mf.gameObject.activeInHierarchy) continue;
            if (!IsEngawaPiece(mf.gameObject)) continue;
            var root = PrefabUtility.GetNearestPrefabInstanceRoot(mf.gameObject);
            string muneName = null;
            for (var t = mf.transform; t != null; t = t.parent) if (t.parent == buildings) { muneName = t.name; break; }
            if (mune != null && muneName != mune) continue;
            var v = mesh.vertices; var tri = mesh.triangles; var l2w = mf.transform.localToWorldMatrix;
            var w = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++) w[i] = l2w.MultiplyPoint3x4(v[i]);
            // 上向きの面を 5mm の高さの升に束ね、面積の最も大きい升 = 縁板の天端
            var area = new Dictionary<int, float>();
            for (int k = 0; k + 2 < tri.Length; k += 3)
            {
                Vector3 a = w[tri[k]], b = w[tri[k + 1]], c = w[tri[k + 2]];
                var nrm = Vector3.Cross(b - a, c - a); float m2 = nrm.magnitude;
                if (m2 < 1e-9f || nrm.y / m2 <= 0.95f) continue;
                int key = Mathf.RoundToInt((a.y + b.y + c.y) / 3f / 0.005f);
                float s; area.TryGetValue(key, out s); area[key] = s + m2 * 0.5f;
            }
            if (area.Count == 0) continue;
            int best = 0; float bestA = -1f;
            foreach (var kv in area) if (kv.Value > bestA) { bestA = kv.Value; best = kv.Key; }
            float topY = best * 0.005f;
            for (int k = 0; k + 2 < tri.Length; k += 3)
            {
                Vector3 a = w[tri[k]], b = w[tri[k + 1]], c = w[tri[k + 2]];
                var nrm = Vector3.Cross(b - a, c - a); float m2 = nrm.magnitude;
                if (m2 < 1e-9f || nrm.y / m2 <= 0.95f) continue;
                if (Mathf.Abs((a.y + b.y + c.y) / 3f - topY) > 0.006f) continue;
                Vector2 A2 = new Vector2(a.x, a.z), B2 = new Vector2(b.x, b.z), C2 = new Vector2(c.x, c.z);
                float d = DistPointTri2(at, A2, B2, C2);
                if (d >= res.dist) continue;
                res.dist = d; res.y = (a.y + b.y + c.y) / 3f; res.piece = root != null ? root : mf.gameObject; res.mune = muneName;
                // 最寄りの点(三角形の内なら at そのもの・外なら最寄りの辺の上)
                if (d == 0f) res.on = at;
                else
                {
                    Vector2 q = NiwaClosestOnSeg(at, A2, B2), q2 = NiwaClosestOnSeg(at, B2, C2), q3 = NiwaClosestOnSeg(at, C2, A2);
                    res.on = q; if ((q2 - at).sqrMagnitude < (res.on - at).sqrMagnitude) res.on = q2; if ((q3 - at).sqrMagnitude < (res.on - at).sqrMagnitude) res.on = q3;
                }
            }
        }
        if (res.dist > reach) { res.y = float.NaN; res.piece = null; res.mune = null; }
        return res;
    }

    /// <summary>天端の面(最高点から 0.02m 以内の頂点)の真下の地表の**最も高い所**[m](<see cref="NiwaTopAboveGround"/> と同じ測り)。
    /// 「地盤 +0.25 以上」のような天端の下限を当てるのに使う。測れなければ NaN。</summary>
    public static float NiwaGroundUnderTop(GameObject go)
    {
        float lo, hi;
        if (!NiwaSpanY(go, out lo, out hi)) return float.NaN;
        float gMax = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices)
            {
                var w = l2w.MultiplyPoint3x4(v);
                if (w.y < hi - 0.02f) continue;
                gMax = Mathf.Max(gMax, Ground(w.x, w.z));
            }
        }
        return gMax == float.MinValue ? float.NaN : gMax;
    }

    /// <summary>腰掛一つの据えの記録。seat = 座面(実メッシュの天端)− 足の芯の地表[m]・floatWorst = 据えた後の脚の当たりの最大の浮き
    /// (&gt; 0.01 = ✗)・bury = 最も深い脚の埋まり[m](負)・lenAlong = 据えた長手の実長[m]。</summary>
    public struct NiwaKoshikakeRep { public float seat, floatWorst, bury, lenAlong; }

    /// <summary>**腰掛(床几)を据える**。実メッシュの平面の長い方を <paramref name="longDirXZ"/> に沿わせ(<see cref="NiwaLongAlongYaw"/>)、
    /// 脚の**足の芯**を (x,z) へ(<see cref="NiwaFootOn"/>)、脚の当たりを地面へ据える(**硬い**: 最も浮いた脚が地表に触れ、他の脚は埋める ──
    /// <see cref="SinkToBed"/>)。座面の高さは部材の丈そのもの(倍率 <paramref name="scale"/> の後)で、斜面では脚の埋まりの分だけ下がる ──
    /// 狙いは持たない(**柔らかい**: 座面の高さは刷るだけ)。測れなければ取り除いて null。
    /// <paramref name="faceToXZ"/> が数なら、長手に直交する二つの向きのうち local +Z が的を向く方を採る(床几に表裏があれば)。</summary>
    public static GameObject NiwaKoshikake(Transform parent, string name, string path, Vector2 xz, Vector2 longDirXZ, float scale,
                                           Vector2 faceToXZ, out NiwaKoshikakeRep rep)
    {
        rep = new NiwaKoshikakeRep { seat = float.NaN, floatWorst = float.NaN, bury = float.NaN, lenAlong = float.NaN };
        if (string.IsNullOrEmpty(path) || longDirXZ.sqrMagnitude < 1e-8f) return null;
        float yaw = NiwaLongAlongYaw(path, longDirXZ);
        if (!float.IsNaN(faceToXZ.x))
        {
            float r = yaw * Mathf.Deg2Rad; var z = new Vector2(Mathf.Sin(r), Mathf.Cos(r));
            if (Vector2.Dot(z, faceToXZ - xz) < 0f) yaw += 180f;
        }
        var go = Place(path, new Vector3(xz.x, Ground(xz.x, xz.y), xz.y), yaw, Vector3.one * scale, parent, name);
        if (go == null) return null;
        if (!NiwaFootOn(go, xz)) { UnityEngine.Object.DestroyImmediate(go); return null; }
        var rt = SinkToBed(go, Ground, 0.05f);
        if (float.IsNaN(rt.hi)) { UnityEngine.Object.DestroyImmediate(go); return null; }
        float lo, hi; NiwaSpanY(go, out lo, out hi);
        float mn, mx; var d = longDirXZ.normalized; ProjExtent(go, d, float.MinValue, float.MaxValue, null, out mn, out mx);
        rep.seat = hi - Ground(xz.x, xz.y); rep.floatWorst = rt.hi; rep.bury = rt.lo; rep.lenAlong = mx - mn;
        return go;
    }

    /// <summary>丸太段の割り付けの記録(区間ごと)。</summary>
    public struct NiwaDanSec { public float s0, s1, drop, rise, tread, slope; public int n, made, sunk; public float worstSink, exposeMin, exposeMax; public string why; }

    /// <summary>**園路の勾配から丸太の土留め段を割り付けて据える**(指図 `dan`「主路の勾配が 1:6 を超える区間にだけ・蹴上 0.12〜0.15・踏面 ≥0.60」)。
    /// <para>① 路の折れ線 <paramref name="pathXZ"/> を 0.25m 刻みに地表(<see cref="Ground"/> ── 描かれた地形)を測り、1.0m の窓の勾配が
    /// <paramref name="slopeMax"/> を超える所を区間に束ねる(0.6m 未満の切れ目は繋ぐ)。② 区間の落差 H を段数 n で割り、蹴上 H/n が
    /// [<paramref name="riseLo"/>, <paramref name="riseHi"/>] に入る n を採る(入らなければ据えない ── 落差が蹴上に足りない区間は ⚠ で刷る)。
    /// ③ 段の丸太は踏面の幅 L/n の中ほどの線(区間の上端から (k−½)·L/n)へ、**天端 = 上の段の踏面**(上端の地表 − (k−1)·蹴上)で据える。
    /// 丸太の芯は実メッシュの**天端の稜(最高点から 0.03m 以内の頂点)の外形の中央**で路の線と段の線へ合わせ、local +Z(杭の側)を下手へ向ける。
    /// ⛔ ピボット(丸太の芯の平面)で位置を決めない。</para>
    /// <para>**硬い**: 丸太の当たりが地表から浮かない(浮けば沈め、沈めた段を数えて最大を刷る)・<paramref name="forbid"/> が真の所(水の中)に据えない。
    /// **柔らかい**: 蹴上・踏面 ≥ <paramref name="treadMin"/>(足りなければ ⚠ で刷る)・丸太の見え(天端 − 下手の地表)。
    /// ⚠ 踏面の土は地形のまま(段ごとの均しは造成の工程 ── ここは地形を触らない)。</para>
    /// 返り値 = 据えた駒。<paramref name="secs"/> = 区間ごとの記録(区間の s は路の道のり[m])。</summary>
    public static List<GameObject> NiwaMarutaDan(Transform parent, string prefix, string path, IList<Vector2> pathXZ,
                                                 float slopeMax, float riseLo, float riseHi, float treadMin,
                                                 Func<Vector2, bool> forbid, out List<NiwaDanSec> secs)
    {
        var made = new List<GameObject>(); secs = new List<NiwaDanSec>();
        if (pathXZ == null || pathXZ.Count < 2 || string.IsNullOrEmpty(path)) return made;
        var segL = new List<float>(); float total = 0f;
        for (int i = 0; i + 1 < pathXZ.Count; i++) { float l = Vector2.Distance(pathXZ[i], pathXZ[i + 1]); segL.Add(l); total += l; }
        Func<float, Vector2> at = s => ChainAt(pathXZ, segL, Mathf.Clamp(s, 0f, total));
        Func<float, Vector2> dirAt = s =>
        {
            for (int i = 0; i < segL.Count; i++) { if (s <= segL[i] || i == segL.Count - 1) return (pathXZ[i + 1] - pathXZ[i]).normalized; s -= segL[i]; }
            return (pathXZ[pathXZ.Count - 1] - pathXZ[pathXZ.Count - 2]).normalized;
        };
        Func<float, float> g = s => { var p = at(s); return Ground(p.x, p.y); };
        const float STEP = 0.25f, WIN = 0.5f;
        int ns = Mathf.Max(1, Mathf.FloorToInt(total / STEP));
        var steep = new bool[ns + 1];
        for (int i = 0; i <= ns; i++)
        {
            float s = i * STEP;
            float a = Mathf.Max(0f, s - WIN), b = Mathf.Min(total, s + WIN);
            steep[i] = b - a > 0.2f && Mathf.Abs(g(b) - g(a)) / (b - a) > slopeMax;
        }
        // 区間に束ねる(0.6m 未満の切れ目は繋ぐ)
        var raw = new List<Vector2>();
        for (int i = 0; i <= ns; i++)
        {
            if (!steep[i]) continue;
            int j = i; while (j + 1 <= ns && steep[j + 1]) j++;
            raw.Add(new Vector2(i * STEP, Mathf.Min(total, j * STEP))); i = j;
        }
        var spans = new List<Vector2>();
        foreach (var r in raw)
        {
            if (spans.Count > 0 && r.x - spans[spans.Count - 1].y < 0.6f) spans[spans.Count - 1] = new Vector2(spans[spans.Count - 1].x, r.y);
            else spans.Add(r);
        }
        float crownTol = 0.03f;
        int idx = 0;
        foreach (var sp in spans)
        {
            var sec = new NiwaDanSec { s0 = sp.x, s1 = sp.y, exposeMin = float.NaN, exposeMax = float.NaN };
            float L = sp.y - sp.x, gA = g(sp.x), gB = g(sp.y);
            sec.drop = Mathf.Abs(gA - gB); sec.slope = L > 1e-3f ? sec.drop / L : 0f;
            int n = Mathf.CeilToInt(sec.drop / riseHi - 1e-4f);
            if (n >= 1 && sec.drop / n < riseLo) n = 0;
            if (n < 1) { sec.why = "落差 " + sec.drop.ToString("F2") + "m が蹴上 " + riseLo.ToString("F2") + "〜" + riseHi.ToString("F2") + " に割れない ── 据えない"; secs.Add(sec); continue; }
            sec.n = n; sec.rise = sec.drop / n; sec.tread = L / n;
            bool upAtS0 = gA >= gB;
            float sTop = upAtS0 ? sp.x : sp.y, sgn = upAtS0 ? 1f : -1f, gTop = Mathf.Max(gA, gB);
            for (int k = 1; k <= n; k++)
            {
                float s = sTop + sgn * (k - 0.5f) * sec.tread;
                var p = at(s); var down = dirAt(s) * sgn;   // 下手の向き(路の向き × 上手の側)
                if (forbid != null && forbid(p)) { sec.why = (sec.why == null ? "" : sec.why + "・") + "段" + k + " は禁じた所(水の中)── 据えない"; continue; }
                float topY = gTop - (k - 1) * sec.rise;
                var go = Place(path, new Vector3(p.x, topY, p.y), Mathf.Atan2(down.x, down.y) * Mathf.Rad2Deg, Vector3.one, parent, prefix + "_" + (idx++));
                if (go == null) continue;
                // 丸太の芯 = 天端の稜の外形の中央(下手の向き・横の向きそれぞれ)
                float lo, hi; NiwaSpanY(go, out lo, out hi);
                var perp = new Vector2(-down.y, down.x);
                float d0 = float.MaxValue, d1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue;
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var l2w = mf.transform.localToWorldMatrix;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = l2w.MultiplyPoint3x4(v); if (w.y < hi - crownTol) continue;
                        var q = new Vector2(w.x, w.z) - p;
                        float dd = Vector2.Dot(q, down), tt = Vector2.Dot(q, perp);
                        d0 = Mathf.Min(d0, dd); d1 = Mathf.Max(d1, dd); t0 = Mathf.Min(t0, tt); t1 = Mathf.Max(t1, tt);
                    }
                }
                if (d0 > d1) { UnityEngine.Object.DestroyImmediate(go); continue; }
                var sh = down * (-(d0 + d1) * 0.5f) + perp * (-(t0 + t1) * 0.5f);
                go.transform.position += new Vector3(sh.x, 0f, sh.y);
                NiwaTopTo(go, topY);
                // 硬い: 浮き 0(浮けば沈める ── 蹴上の狙いは柔らかい)
                var rt = RootToBed(go, Ground, 0.05f);
                if (!float.IsNaN(rt.hi) && rt.hi > 0.005f)
                {
                    go.transform.position -= new Vector3(0f, rt.hi, 0f);
                    sec.sunk++; sec.worstSink = Mathf.Max(sec.worstSink, rt.hi);
                }
                // 見え = 天端 − 下手の地表(丸太の下手の外形の 0.05m 先)
                NiwaSpanY(go, out lo, out hi);
                float mn, mx; ProjExtent(go, down, hi - 0.2f, float.MaxValue, null, out mn, out mx);
                var c3 = go.transform.position; float c = c3.x * down.x + c3.z * down.y;
                var pd = new Vector2(c3.x, c3.z) + down * (mx - c + 0.05f);
                float ex = hi - Ground(pd.x, pd.y);
                sec.exposeMin = float.IsNaN(sec.exposeMin) ? ex : Mathf.Min(sec.exposeMin, ex);
                sec.exposeMax = float.IsNaN(sec.exposeMax) ? ex : Mathf.Max(sec.exposeMax, ex);
                made.Add(go); sec.made++;
            }
            if (sec.tread < treadMin) sec.why = (sec.why == null ? "" : sec.why + "・") + "⚠ 踏面 " + sec.tread.ToString("F2") + "m < " + treadMin.ToString("F2") + "(柔らかい ── 路が急すぎる)";
            secs.Add(sec);
        }
        return made;
    }

    /// <summary>生垣を塀から引いた記録。faceMin/faceMax = 塀の内面の、案内線からの出[m](内へ正・測った駒の範囲)・noFace = 内面が測れず
    /// 植えなかった駒の座の数・sx = 走りの倍率・floatWorst/buryWorst = 据えた後の当たりの最大の浮き/最も深い埋まり・
    /// wallGap = 生垣の葉の外形と塀の内面の隙の最小[m](負 = 葉が塀に入る)・h = 生垣の実の丈。</summary>
    public struct NiwaHedgeRep { public int made, noFace; public float faceMin, faceMax, sx, floatWorst, buryWorst, wallGap, h, pitchMin, pitchMax; public string why; }

    /// <summary>**塀の内面から離れを取って生垣の芯を引き、生垣の駒を並べる**(指図 `ikegaki.line`「奥の塀の内面から 0.5間を芯に」)。
    /// <para>① 塀の駒 <paramref name="wall"/>(布石を除いた塀の本体)のうち、案内線 a→b と**平行な駒だけ**(駒の頂点の外形が線に沿って
    /// 長い)の実メッシュを、各駒の丈の 0.3〜0.6 の帯(笠木と腰を外す)で拾い、0.5m ごとの座で**内(<paramref name="inward"/> の側)へ
    /// 最も出た頂点** = 塀の内面を測る。② 芯 = 内面 + <paramref name="offset"/>。③ 走りを駒の実長(葉の外形)で n 駒に割り(倍率は
    /// 0.85〜1.15 に収める)、両端は端の駒(葉で閉じた小口 = local +X)を外へ向け、各駒の**葉の外形**の走りの端を前の駒に触れさせ、
    /// 奥行の外形の中央を芯へ合わせる。④ 地面へ据える(**硬い**: 浮き 0 ── <see cref="SinkToBed"/>、他の当たりは埋める)。</para>
    /// <para>**硬い**: 内面が測れない座には植えない(塀の無い所・口)・浮き 0。**柔らかい**: 丈(部材の丈のまま・刷るだけ)・
    /// 葉と塀の隙(刷るだけ ── 部材どうしのめり込みは数えない)。⛔ 塀の基準点・指図の線の座標で芯を決めない。</para></summary>
    public static List<GameObject> NiwaHedgeFromWall(Transform parent, string prefix, IList<GameObject> wall, Vector2 aXZ, Vector2 bXZ,
                                                     Vector2 inward, float offset, string bodyPath, string endPath, out NiwaHedgeRep rep)
    {
        var made = new List<GameObject>();
        rep = new NiwaHedgeRep { faceMin = float.NaN, faceMax = float.NaN, floatWorst = float.NaN, buryWorst = float.NaN, wallGap = float.NaN, h = float.NaN };
        var ab = bXZ - aXZ; float len = ab.magnitude;
        if (len < 0.5f || wall == null || wall.Count == 0) { rep.why = "案内線が短いか塀の駒が無い"; return made; }
        var dir = ab / len; var nrm = new Vector2(-dir.y, dir.x); if (Vector2.Dot(nrm, inward) < 0f) nrm = -nrm;
        // ① 塀の内面(平行な駒だけ・丈の 0.3〜0.6 の帯)
        var sv = new List<Vector2>();   // (s, t)
        foreach (var go in wall)
        {
            if (go == null || !go.activeInHierarchy) continue;
            var pts = new List<Vector3>(); float y0 = float.MaxValue, y1 = float.MinValue;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                var l2w = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices) { var w = l2w.MultiplyPoint3x4(v); pts.Add(w); y0 = Mathf.Min(y0, w.y); y1 = Mathf.Max(y1, w.y); }
            }
            if (pts.Count == 0) continue;
            float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue;
            foreach (var w in pts) { var q = new Vector2(w.x, w.z) - aXZ; float s = Vector2.Dot(q, dir), t = Vector2.Dot(q, nrm); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); t0 = Mathf.Min(t0, t); t1 = Mathf.Max(t1, t); }
            if (s1 - s0 <= t1 - t0) continue;                       // 線と平行でない駒(折れの先の区の駒)
            if (s1 < -0.5f || s0 > len + 0.5f || t0 > 3f || t1 < -3f) continue;   // 案内線の脇に無い
            float bLo = y0 + 0.3f * (y1 - y0), bHi = y0 + 0.6f * (y1 - y0);
            foreach (var w in pts)
            {
                if (w.y < bLo || w.y > bHi) continue;
                var q = new Vector2(w.x, w.z) - aXZ; sv.Add(new Vector2(Vector2.Dot(q, dir), Vector2.Dot(q, nrm)));
            }
        }
        Func<float, float> faceAt = s =>
        {
            float best = float.NaN;
            foreach (var q in sv) if (Mathf.Abs(q.x - s) <= 0.5f && (float.IsNaN(best) || q.y > best)) best = q.y;
            return best;
        };
        // ③ 割り付け(葉の外形の実長)
        float bw = RunMeasure(bodyPath).W, ew = RunMeasure(endPath).W;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / bw));
        float sx = len / (n * bw);
        if (sx < 0.85f && n > 1) { n--; sx = len / (n * bw); }
        if (sx > 1.15f) { n++; sx = len / (n * bw); }
        rep.sx = sx;
        float cursor = 0f;
        for (int i = 0; i < n; i++)
        {
            bool first = i == 0, last = i == n - 1; bool isEnd = first || last;
            string path = isEnd ? endPath : bodyPath;
            float pieceW = (isEnd ? ew : bw) * sx;
            float sMid = cursor + pieceW * 0.5f;
            float f = faceAt(sMid);
            if (float.IsNaN(f)) { rep.noFace++; cursor += pieceW; continue; }
            rep.faceMin = float.IsNaN(rep.faceMin) ? f : Mathf.Min(rep.faceMin, f);
            rep.faceMax = float.IsNaN(rep.faceMax) ? f : Mathf.Max(rep.faceMax, f);
            float core = f + offset;
            // 端の駒は葉で閉じた小口(local +X)を外へ: 頭の駒は −dir、尻の駒は +dir。中の駒と n=1 は +dir
            var xDir = (first && n > 1) ? -dir : dir;
            float yaw = YawLocalAxisTo(true, xDir);
            var c0 = aXZ + dir * sMid + nrm * core;
            var go = Place(path, new Vector3(c0.x, Ground(c0.x, c0.y), c0.y), yaw, new Vector3(sx, 1f, 1f), parent, prefix + "_" + i);
            if (go == null) { cursor += pieceW; continue; }
            // 葉の外形で走りの端を cursor へ・奥行の中央を芯へ
            float mn, mx, pn, px;
            ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
            ProjExtent(go, nrm, float.MinValue, float.MaxValue, null, out pn, out px);
            float baseS = Vector2.Dot(aXZ, dir), baseT = Vector2.Dot(aXZ, nrm);
            float ds = (baseS + cursor) - mn, dt = (baseT + core) - (pn + px) * 0.5f;
            var shv = dir * ds + nrm * dt;
            go.transform.position += new Vector3(shv.x, 0f, shv.y);
            cursor += mx - mn;
            var rt = SinkToBed(go, Ground, 0.05f);
            if (float.IsNaN(rt.hi)) { UnityEngine.Object.DestroyImmediate(go); rep.noFace++; continue; }
            rep.floatWorst = float.IsNaN(rep.floatWorst) ? rt.hi : Mathf.Max(rep.floatWorst, rt.hi);
            rep.buryWorst = float.IsNaN(rep.buryWorst) ? rt.lo : Mathf.Min(rep.buryWorst, rt.lo);
            // 葉と塀の内面の隙(塀の側の葉の外形 − 内面)
            float gap = (pn + dt - baseT) - f;
            rep.wallGap = float.IsNaN(rep.wallGap) ? gap : Mathf.Min(rep.wallGap, gap);
            float lo, hi; if (NiwaSpanY(go, out lo, out hi)) rep.h = float.IsNaN(rep.h) ? hi - lo : Mathf.Max(rep.h, hi - lo);
            made.Add(go); rep.made++;
        }
        if (sv.Count == 0) rep.why = "案内線の脇に線と平行な塀の駒が無い(塀が未建か名が違う)";
        return made;
    }

    // ─────────── 指図の庭 ── 橋台石・延段・寄せて植える木・株を並べる生垣・据え土の外形(EDO-0533 第6巡 庭方の欄の埋め) ───────────
    //
    // 当たる先(この小節の全関数): EdoDoiBuilder.Niwa 6b(呑口の据え土の外形)・6e(石橋の橋台石・奥庭の延段)・6h(松の atSoft・奥庭の生垣)。
    // 以後、指図が座標で石・木・延段を持つ庭の全て(石橋の掛かる庭・塀の内に株立ちを並べる刈込垣・狙いの点の柔らかい植栽)。

    /// <summary>**島の見えている汀**(描かれた地表が水面を切る線)を、設計の島の輪郭 <paramref name="lineW"/>(世界・島の芯 <paramref name="isleW"/> の周り)から測る。
    /// 輪郭を <paramref name="step"/> m ごとに割り、各点で島の外向きの法線(芯から離れる向き)に ±<paramref name="reach"/> m を 0.02m 刻みに引いて、
    /// 外へ向かって地表が水面より上 → 下へ変わる所のうち輪郭に最も近い所(線形の内挿)を採る。切る所が無い点は輪郭のまま(<paramref name="fallback"/> に数える)。
    /// ⭐ 掘り残しの島は地形の格子(2m)で輪郭より丸く小さく出る ── 輪郭の外へ inset で寄せた護岸の石が水中の斜面に載り、水中の足の硬い条件
    /// (池床 −seatToBed)で天端が水面の下まで沈んだ(2026-10-04 EDO-0533 普請検査 第1回 Gogan_Naka_N 19 石・最深 −0.41)。
    /// ⛔ 設計の輪郭の線で汀の物を据えない(池の汀の PondEdge と同じ作法 ── 「見えている水際に取り合わせる」)。
    /// <paramref name="worstShift"/> = 輪郭から測った汀までの最大のずれ[m](± ── 正 = 輪郭の外)。当たる先: 中島・岩島の護岸と州浜(土井 Gogan_Naka_N)。</summary>
    public static List<Vector2> NiwaIsleShore(IList<Vector2> lineW, Vector2 isleW, float waterY, float reach, float step,
                                              Func<float, float, float> bedAt, out int fallback, out float worstShift)
    {
        fallback = 0; worstShift = 0f;
        var res = new List<Vector2>();
        if (lineW == null || lineW.Count < 2) return res;
        var bed = bedAt ?? (Func<float, float, float>)Ground;
        // 割った点と接線
        var P = new List<Vector2>(); var Tn = new List<Vector2>();
        for (int i = 0; i + 1 < lineW.Count; i++)
        {
            Vector2 a = lineW[i], b = lineW[i + 1]; float L = Vector2.Distance(a, b);
            if (L < 1e-5f) continue;
            int n = Mathf.Max(1, Mathf.CeilToInt(L / Mathf.Max(0.02f, step)));
            for (int k = 0; k < n; k++) { P.Add(Vector2.Lerp(a, b, (float)k / n)); Tn.Add((b - a) / L); }
        }
        P.Add(lineW[lineW.Count - 1]); Tn.Add(Tn.Count > 0 ? Tn[Tn.Count - 1] : Vector2.right);
        const float ds = 0.02f;
        for (int i = 0; i < P.Count; i++)
        {
            var t = (i > 0 && i < P.Count - 1) ? (Tn[i - 1] + Tn[i]).normalized : Tn[i];
            if (t.sqrMagnitude < 1e-8f) t = Tn[i];
            var nrm = new Vector2(t.y, -t.x);
            if (Vector2.Dot(nrm, P[i] - isleW) < 0f) nrm = -nrm;            // 島の外向き
            float best = float.NaN;
            float hPrev = bed(P[i].x - nrm.x * reach, P[i].y - nrm.y * reach) - waterY;
            for (float sv = -reach + ds; sv <= reach + 1e-5f; sv += ds)
            {
                var q = P[i] + nrm * sv;
                float h = bed(q.x, q.y) - waterY;
                if (!float.IsNaN(h) && !float.IsNaN(hPrev) && hPrev >= 0f && h < 0f)
                {
                    float sc = sv - ds + ds * hPrev / Mathf.Max(1e-6f, hPrev - h);
                    if (float.IsNaN(best) || Mathf.Abs(sc) < Mathf.Abs(best)) best = sc;
                }
                hPrev = h;
            }
            if (float.IsNaN(best)) { fallback++; res.Add(P[i]); continue; }
            if (Mathf.Abs(best) > Mathf.Abs(worstShift)) worstShift = best;
            res.Add(P[i] + nrm * best);
        }
        return res;
    }

    /// <summary>橋台石一つの据えの記録。deckUnder = 測った版の下面[m]・stoneTop = 版の下面の範囲の内の石の天端・gapGround = 版の下面 − 石の位置の地表
    /// (≤ 0 = 版が地表に載る ── 石は全身が埋まるので据えない = buried)・longGot = 据えた石の平面の長い方の実長(狙い long ── 柔らかい)・
    /// footFloat = 下端の当たりの最大の浮き(陸 ≤ 0・水中 ≤ −seatToBed が硬い)・wet = 足元が水中・grew = 足が届かず丈を増した・
    /// inside = 石の平面が版の下面の範囲に収まった・pokeOut = 版の下面の範囲の外の石の頂点の、版の下面からの最大の出[m](&gt; 0 = 版の脇で下面より上に出る ── 柔らかい ⚠)・
    /// shrunk = 版の幅に収めるため長さを縮めた。</summary>
    public struct NiwaAbutRep
    {
        public float deckUnder, stoneTop, gapGround, longGot, footFloat, pokeOut; public bool wet, buried, grew, inside, shrunk; public string why;
        // ↓ 据えの作法(NiwaAbutSeatSpec)を渡したときだけ埋まる。relief = 受ける範囲の内の天端の高い atariFrac の面の起伏[m]・
        //   umeDeep = 最も高い一点の版への埋め[m](硬い ≤ umeMax)・atariGap = その面の最も低い点の隙[m](柔らかい ≤ atariHi が狙い)・
        //   sukiMax / sukiVis = 受ける範囲の内 / 範囲の縁(見える側)の隙の最大・sukiOver = 隙 > sukiMax の点の割合(飼石と土で塞いだ扱い)・
        //   cover = 受ける範囲のうち石が下にある割合・yawDeg = 選んだ向き(広い面を橋軸に直交した向きからの回し)・flip = 表裏を返した・
        //   atariMet = 当たりの狙い(面が版の下面から atariLo〜atariHi)を満たした・reliefOver = 起伏が reliefMax を超えた(石の版を替える指示)。
        public bool seated, atariMet, flip, reliefOver; public float relief, umeDeep, atariGap, sukiMax, sukiVis, sukiOver, cover, yawDeg;
        // ↓ 起伏の手当て(NiwaAbutSeatSpec.alts / neiriMax)── pathGot = 据えた石の版(替えたなら替えた先)・swapped = 版を替えた・
        //   reliefFirst = 名指しの版の最良の起伏[m]・sinkScale = 起伏を下げるため石を大きくして沈めた縮尺(1 = しない)・sinkDeep = それで増した根入れ[m]。
        public string pathGot; public bool swapped; public float reliefFirst, sinkScale, sinkDeep;
        // ↓ 地中に入る深さの合計(NiwaAbutSeatSpec.neiriFrac)── embedFrac = 据えた石の (足の芯の地表 − 下端) / 丈(NaN = 測れない)・
        //   embedCapHit = 沈めをこの上限で止めた(硬い ── 起伏はそこまでの最良で残る)。
        public float embedFrac; public bool embedCapHit;
        // ↓ 丈の下限(NiwaAbutSeatSpec.hMin ── 柔らかい)── hGot = 据えた石の丈[m]・hMinScale = 下限へ届かせるため大きくした縮尺(1 = しない)・
        //   hMinMet = 丈 ≥ hMin(false なら ⚠ 狙い未達 ── 地中の深さの上限 neiriFrac で止めたか、測れなかった)。
        public float hGot, hMinScale; public bool hMinMet;
    }

    /// <summary>**石橋の版と橋台石の据えの作法**(指図 `hashi[].abutSeat` ── 邸ビルダーが欄を読んで埋める。⛔ ここに既定の値を持たない)。
    /// kakari・inner = 石が受けるのは版の端から inner〜kakari の帯(橋軸の向き)・umeMax = 版の下面へ石が入る深さの上限(硬い)・
    /// atariFrac = 当たりの面(受ける範囲の内の天端の高い方からの面積の割合)・atariLo〜atariHi = その面を入れる版の下面からの高さ(柔らかい)・
    /// sukiMax = これを超える隙は飼石と土で塞いだ扱い(刷るだけ)・reliefMax = 天端の起伏がこれを超えたら石の版を替える(刷るだけ)・
    /// turns = 向きの候補の数(360/turns 度ずつ)・flips = 表裏を返す候補も試す。
    /// ⭐ 起伏の手当て(指図「起伏 &gt; reliefMax なら石の版を替え、なお合わなければ石を沈めて根入れを深く」の後ろ2手 ── 2026-10-05 第11巡 EDO-0533):
    /// alts = 替えの版(部材のパス・邸ビルダーが欄から解く。空 = 替えない)── 名指しの版の最良の起伏が reliefMax を超えたときだけ、同じ向き×表裏で試し、
    /// 起伏 ≤ reliefMax のうち受ける範囲を最も広く覆う版(無ければ起伏の最小)を採る(受ける範囲の 5 割を覆わない版は採らない)。
    /// neiriMax = 石を大きくして沈め、根入れを深くしてよい量の上限[m](0 = しない)── なお起伏が reliefMax を超えるとき、石を等方に大きくして
    /// (天端の丸みが受ける範囲の内で緩む)天端は版の下面のまま足を深く沈める。増す根入れ ≤ neiriMax(硬い)。
    /// neiriFrac = 地中に入る深さの合計の上限(石の丈に対する割合 ── 指図 neiriNote「丈の 0.6 まで」・2026-10-05 庭方)。沈めのどの段でも
    /// (足の芯の地表 − 下端) ≤ neiriFrac × 丈 を守る(硬い ── 越える段は採らない)。NaN = 上限の欄が無い(沈めない)。
    /// 天端の当たり(最も高い一点の埋め ≤ umeMax)は沈めても硬いまま ── ③ が版の下面に着けてから足を測る。</summary>
    public class NiwaAbutSeatSpec
    {
        public float kakari, inner, umeMax, atariFrac, atariLo, atariHi, sukiMax, reliefMax; public int turns; public bool flips;
        public List<string> alts = new List<string>(); public float neiriMax, neiriFrac = float.NaN;
        /// <summary>石の丈の下限[m](指図 `abutStone[].hMin` ── **柔らかい**。NaN = 欄が無い)。②'' の後、丈が足りなければ石を等方に大きくして
        /// (天端は ③ で版の下面のまま・増した分は足が地中へ沈む)下限へ届かせる。地中に入る深さの合計 ≤ neiriFrac × 丈(硬い)は守る ──
        /// 越える所は届く限りで止めて ⚠(hMinMet = false)。2026-10-05 EDO-0533 庭方: 汀の保証で袂が掘られ、丈の短い石では足が届かなかった。</summary>
        public float hMin = float.NaN;
        /// <summary>石が受ける帯(版の端から inner〜kakari)より長い石の余りを**陸の側へ**出す(2026-10-05 EDO-0533 第14巡)。帯の径間の側の縁
        /// (a 端 = 版の端 + kakari・b 端 = 版の端 − kakari)に石の径間の側の面を揃え、余りは版の端の外(袂の地盤の上)へ。⛔ false(従来)は帯の中ほどに
        /// 置き、丈を増して大きくした石の足が汀の先(池床が下がる側)へ出て、増すほど足元が下がり届かなかった(a 端 浮き 0.39→0.10・座 26.07)。
        /// 天端の当たり(受ける範囲の内)は変わらない。当たる先: 袂が陸で石が受ける帯の先が水の石橋(土井 Hashi_Ishi)。</summary>
        public bool landward;
    }

    // ──────────────────────────────────────────────── 石橋の袂(汀の保証を掛けない・座を盛る ── 6a の地形の段・2026-10-05 EDO-0533)
    /// <summary>石橋の**袂** = 版の下の陸の帯(版の端 end 〜 汀の点 shore・幅 2 × halfW)。指図 `migiwa.shoreRule.guarantee.exceptAbut` / `shoreRule.abutPad`。</summary>
    public struct NiwaTamoto { public Vector2 end, shore; public float halfW; }

    /// <summary>橋 a→b(世界 xz・汀の点)・版の長さ <paramref name="L"/>・幅 <paramref name="W"/> から両端の袂を返す。版は径間の芯に据わる
    /// (<see cref="NiwaSpanBridge"/> と同じ ── 径間 = |b − a|)ので、端 = 汀の点から外へ (L − 径間)/2。幅 = W + <paramref name="widen"/>。
    /// 版が径間より長くなければ袂は無い(空)。⛔ 版の実メッシュはまだ無い(6a は橋を架ける 6e より前)── 指図の L・W から引く。
    /// 当たる先: 土井の石橋 Hashi_Ishi。以後、汀に架ける版橋・土橋の袂の全て。</summary>
    public static List<NiwaTamoto> NiwaTamotoOfBridge(Vector2 aW, Vector2 bW, float L, float W, float widen)
    {
        var res = new List<NiwaTamoto>();
        var ab = bW - aW; float span = ab.magnitude;
        if (span < 1e-4f || float.IsNaN(L) || L <= span + 1e-4f || float.IsNaN(W)) return res;
        var d = ab / span; float over = 0.5f * (L - span), hw = 0.5f * (W + widen);
        res.Add(new NiwaTamoto { end = aW - d * over, shore = aW, halfW = hw });
        res.Add(new NiwaTamoto { end = bW + d * over, shore = bW, halfW = hw });
        return res;
    }

    /// <summary>格子の節点 <paramref name="w"/> の高さが袂の内の地表に効くか ── 節点のまわり ±<paramref name="cell"/> の正方形(地形の三角形の補間が届く範囲)が
    /// 袂の矩形に掛かる(分離軸で判定)。⚠ 格子 2.0m に袂は 0.3 × 1.05m しか無く、節点の中心で判定すると一つも入らない。</summary>
    public static bool NiwaTamotoReach(IList<NiwaTamoto> ts, Vector2 w, float cell)
    {
        if (ts == null) return false;
        float h = cell * 0.999f;
        foreach (var t in ts)
        {
            var ax = t.shore - t.end; float len = ax.magnitude; if (len < 1e-5f) continue;
            var u = ax / len; var v = new Vector2(-u.y, u.x); var c = 0.5f * (t.end + t.shore); float hu = 0.5f * len, hv = t.halfW;
            var dc = w - c; bool sep = false;
            // 軸 x・z(正方形の軸)
            float rx = hu * Mathf.Abs(u.x) + hv * Mathf.Abs(v.x), rz = hu * Mathf.Abs(u.y) + hv * Mathf.Abs(v.y);
            if (Mathf.Abs(dc.x) > h + rx || Mathf.Abs(dc.y) > h + rz) sep = true;
            // 軸 u・v(矩形の軸)
            if (!sep && Mathf.Abs(Vector2.Dot(dc, u)) > hu + h * (Mathf.Abs(u.x) + Mathf.Abs(u.y))) sep = true;
            if (!sep && Mathf.Abs(Vector2.Dot(dc, v)) > hv + h * (Mathf.Abs(v.x) + Mathf.Abs(v.y))) sep = true;
            if (!sep) return true;
        }
        return false;
    }

    /// <summary>汀の式の値 <paramref name="y"/> に、袂の除外と座の下限を掛ける(6a の地形の段で節点ごとに呼ぶ)。
    /// reach = 節点が袂に効く(<see cref="NiwaTamotoReach"/>)・guarantee = 保証(橋の軸・水口)が掛かる節点・gY = 保証の高さ(水面 − sub)・
    /// padY = 袂の座の下限(水面 + keepAbove ── **硬い**。NaN = 掛けない)・wet = 節点が見えている汀の内・padWet = 汀の内の節点も盛る(二巡目)。
    /// ⭐ 袂に効く節点には保証を掛けない(exceptAbut)。座の下限は一巡目は陸の節点だけに掛け(池の形を崩さない)、それで座の最低が下限に届かなければ
    /// 呼び手が padWet = true で二巡目を流す(硬い条件を池の形より先に立てる ── 汀の内へ出た土は呼び手が数えて刷る)。</summary>
    public static float NiwaShoreTamoto(float y, bool reach, bool guarantee, float gY, float padY, bool wet, bool padWet)
    {
        if (!reach) return guarantee ? Mathf.Min(y, gY) : y;
        if (!float.IsNaN(padY) && (!wet || padWet)) y = Mathf.Max(y, padY);
        return y;
    }

    /// <summary>袂の座の地表の最低(袂の矩形を <paramref name="step"/> 刻みで <paramref name="groundAt"/> に引く)と、その点。袂が無ければ NaN。</summary>
    public static float NiwaTamotoSeatMin(IList<NiwaTamoto> ts, Func<float, float, float> groundAt, out Vector2 at, float step = 0.05f)
    {
        at = Vector2.zero; float mn = float.NaN;
        if (ts == null) return mn;
        foreach (var t in ts)
        {
            var ax = t.shore - t.end; float len = ax.magnitude; if (len < 1e-5f) continue;
            var u = ax / len; var v = new Vector2(-u.y, u.x);
            int ni = Mathf.Max(1, Mathf.CeilToInt(len / step)), nj = Mathf.Max(1, Mathf.CeilToInt(2f * t.halfW / step));
            for (int i = 0; i <= ni; i++)
                for (int j = 0; j <= nj; j++)
                {
                    var q = t.end + u * (len * i / ni) + v * (-t.halfW + 2f * t.halfW * j / nj);
                    float g = groundAt(q.x, q.y); if (float.IsNaN(g)) continue;
                    if (float.IsNaN(mn) || g < mn) { mn = g; at = q; }
                }
        }
        return mn;
    }

    /// <summary>点 (x, z) の鉛直線と駒の三角形の交わりのうち**最も高い高さ** = その点の天端。交わらなければ NaN(LowestSurfaceAt の対)。</summary>
    public static float HighestSurfaceAt(SurfaceSet s, Vector2 q)
    {
        float best = float.MinValue;
        foreach (var t in s.tris)
        {
            Vector3 a = t[0], b = t[1], c = t[2];
            if (q.x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || q.x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || q.y < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || q.y > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue;
            float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue;
            float u = ((b.z - c.z) * (q.x - c.x) + (c.x - b.x) * (q.y - c.z)) / d, v = ((c.z - a.z) * (q.x - c.x) + (a.x - c.x) * (q.y - c.z)) / d, w = 1f - u - v;
            if (u < -1e-5f || v < -1e-5f || w < -1e-5f) continue;
            best = Mathf.Max(best, u * a.y + v * b.y + w * c.y);
        }
        return best == float.MinValue ? float.NaN : best;
    }

    /// <summary>**石橋の版の端に見える橋台石を据える**(指図 `hashi[].abutStone`)。
    /// <para>① 版 <paramref name="deck"/> の実メッシュを橋軸 a→b に射影して版の端(<paramref name="atA"/> なら a 側の端)を測り、端から
    /// <paramref name="inFromEnd"/> m 内の帯(±0.20m)の頂点の最も低い所 = **版の下面**を測る(⛔ topY − T の算術で代えない)。
    /// ② **版の下面の平面の範囲**(下面から 0.02m 以内の頂点の、橋軸 s・幅 t の範囲)を測る。
    /// ③ 石の平面の長い方を <paramref name="longM"/> に縮尺し、**広い面を橋軸に直交**(<see cref="NiwaBroadFaceYaw"/>)。石の実メッシュの
    /// s・t の範囲を測り、**版の下面の範囲の内**へ寄せる(s の芯は端から inFromEnd ── 柔らかい・範囲に収まるよう詰める/t の芯は版の幅の芯)。
    /// 石の幅が版の下面の幅を越えるなら長さを縮める(狙い long は柔らかい ── shrunk に刷る)。⛔ 足の芯・ピボットで平面を決めない。
    /// ④ **版の下面の範囲の内の石の最も高い頂点 = 版の下面**(硬い: 接する・隙 0)。⑤ 足の当たりが陸なら地表から浮かない・水中なら池床
    /// −<paramref name="seatToBed"/> まで届く(硬い)。届かなければ天端を動かさず丈を増して据え直す(石の長さの狙いは柔らかい ── longGot に刷る)。</para>
    /// ⛔ 2026-10-04 EDO-0533 普請検査 第1回: 石を足の芯で端から inFromEnd の点へ置き、**石の全体の最も高い頂点**を版の下面に合わせていた ──
    /// 石の頂点が版の外(端の先)にあり、版の下の石の面は 0.15/0.36m 下がって隙が開いた(重なる升 1)。
    /// 版の下面が石の位置の地表以下なら石は全身が埋まるので据えない(rep.buried ── 指図「地表が高ければ埋めて可」)。測れなければ null。
    /// 当たる先: 石橋の橋台石(土井 Hashi_Ishi)。以後、版の下に据えて版を受ける石・束石の全て(土橋の橋台・縁の下の束石の受け)。
    /// ⭐ <paramref name="seat"/>(指図 `abutSeat`)を渡すと ④ を「最も高い一点」でなく**天端の高い面で受ける**据えに替える(<see cref="NiwaAbutSeatPlace"/>)。
    /// ⛔ 2026-10-05 EDO-0533 普請検査 第4回: 一点で当てた石橋が橋台 a を相手にしても 0.160 浮いた(石の天端の頂が版の下面の範囲の際の一点だった)。</summary>
    public static GameObject NiwaAbutStone(Transform parent, string name, string path, GameObject deck, Vector2 aXZ, Vector2 bXZ, bool atA,
                                           float inFromEnd, float longM, float waterY, float seatToBed, out NiwaAbutRep rep,
                                           NiwaAbutSeatSpec seat = null)
    {
        rep = new NiwaAbutRep { deckUnder = float.NaN, stoneTop = float.NaN, gapGround = float.NaN, longGot = float.NaN, footFloat = float.NaN, pokeOut = float.NaN };
        if (deck == null || string.IsNullOrEmpty(path)) { rep.why = "版か部材が無い"; return null; }
        var ab = bXZ - aXZ; if (ab.sqrMagnitude < 1e-8f) { rep.why = "橋軸が引けない"; return null; }
        var dir = ab.normalized; var perp = new Vector2(-dir.y, dir.x);
        var pts = MeshPointsW(deck);
        if (pts.Count == 0) { rep.why = "版の実メッシュが無い"; return null; }
        Func<Vector3, float> S = w => Vector2.Dot(new Vector2(w.x, w.z) - aXZ, dir);
        Func<Vector3, float> T = w => Vector2.Dot(new Vector2(w.x, w.z) - aXZ, perp);
        float s0 = float.MaxValue, s1 = float.MinValue;
        foreach (var w in pts) { float s = S(w); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); }
        float sPos = atA ? s0 + inFromEnd : s1 - inFromEnd, sMid = 0.5f * (s0 + s1);
        float under = float.MaxValue;
        foreach (var w in pts) if (Mathf.Abs(S(w) - sPos) <= 0.20f) under = Mathf.Min(under, w.y);
        if (under == float.MaxValue) { rep.why = "版の端の帯に頂点が無い"; return null; }
        rep.deckUnder = under;
        // ② 版の下面の平面の範囲(この端の側の半分 ── 反りのある版でも端の下面だけを採る)
        float us0 = float.MaxValue, us1 = float.MinValue, ut0 = float.MaxValue, ut1 = float.MinValue;
        foreach (var w in pts)
        {
            if (w.y > under + 0.02f) continue;
            float s = S(w); if (atA ? s > sMid : s < sMid) continue;
            float t = T(w);
            us0 = Mathf.Min(us0, s); us1 = Mathf.Max(us1, s); ut0 = Mathf.Min(ut0, t); ut1 = Mathf.Max(ut1, t);
        }
        if (us0 > us1 || ut0 > ut1) { rep.why = "版の下面の範囲が測れない"; return null; }
        float tc = 0.5f * (ut0 + ut1);
        var pos = aXZ + dir * sPos + perp * tc;
        float g0 = Ground(pos.x, pos.y);
        rep.gapGround = under - g0;
        if (rep.gapGround <= 0f) { rep.buried = true; rep.why = "版の下面が地表以下(" + rep.gapGround.ToString("+0.00;-0.00") + "m)── 石は全身が埋まる"; return null; }
        rep.wet = !float.IsNaN(waterY) && g0 < waterY;
        float need = rep.wet ? -seatToBed : 0f;
        float yaw = NiwaBroadFaceYaw(path, pos, pos + dir);
        float sc = NiwaScaleForLong(path, longM);
        if (float.IsNaN(sc)) { rep.why = "部材の実寸が測れない"; return null; }
        if (seat != null) return NiwaAbutSeatPlace(parent, name, path, deck, aXZ, dir, perp, atA, s0, s1, sPos, tc, ut0, ut1, under, g0, need, yaw, sc, longM, seat, ref rep);
        GameObject go = null;
        // 石の平面を版の下面の範囲の内へ寄せ、範囲の内の最も高い頂点を版の下面へ。返り値 = 範囲に収まったか
        Func<GameObject, bool> fit = g =>
        {
            var sp = MeshPointsW(g);
            float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
            foreach (var w in sp) { float s = S(w), t = T(w); a0 = Mathf.Min(a0, s); a1 = Mathf.Max(a1, s); b0 = Mathf.Min(b0, t); b1 = Mathf.Max(b1, t); }
            float hd = 0.5f * (a1 - a0), hw = 0.5f * (b1 - b0);
            float cs = (us1 - us0) >= 2f * hd ? Mathf.Clamp(sPos, us0 + hd, us1 - hd) : 0.5f * (us0 + us1);
            float ct = tc;
            var sh = dir * (cs - 0.5f * (a0 + a1)) + perp * (ct - 0.5f * (b0 + b1));
            g.transform.position += new Vector3(sh.x, 0f, sh.y);
            bool inside = (us1 - us0) >= 2f * hd - 1e-4f && (ut1 - ut0) >= 2f * hw - 1e-4f;
            float topIn = float.MinValue;
            foreach (var w0 in sp)
            {
                var w = w0 + new Vector3(sh.x, 0f, sh.y);
                float s = S(w), t = T(w);
                if (s >= us0 - 1e-4f && s <= us1 + 1e-4f && t >= ut0 - 1e-4f && t <= ut1 + 1e-4f) topIn = Mathf.Max(topIn, w.y);
            }
            if (topIn == float.MinValue) return false;
            g.transform.position += new Vector3(0f, under - topIn, 0f);       // 硬い: 版の下面の範囲の内の天端 = 版の下面
            return inside;
        };
        for (int it = 0; it < 6; it++)
        {
            if (go != null) UnityEngine.Object.DestroyImmediate(go);
            go = Place(path, new Vector3(pos.x, g0, pos.y), yaw, Vector3.one * sc, parent, name);
            if (go == null) { rep.why = "置けない"; return null; }
            // 石の幅(t)が版の下面の幅を越えるなら長さを縮める(柔らかい)── 丈を増した後は縮めない(足の硬い条件が先)
            if (!rep.grew)
            {
                float pn, px; ProjExtent(go, perp, float.MinValue, float.MaxValue, null, out pn, out px);
                float uw = ut1 - ut0;
                if (px - pn > uw + 1e-4f && px - pn > 1e-4f)
                {
                    sc *= uw / (px - pn) * 0.999f; rep.shrunk = true;          // 等方の縮尺なので幅は一度で収まる
                    UnityEngine.Object.DestroyImmediate(go);
                    go = Place(path, new Vector3(pos.x, g0, pos.y), yaw, Vector3.one * sc, parent, name);
                    if (go == null) { rep.why = "置けない"; return null; }
                }
            }
            rep.inside = fit(go);
            var rt = RootToBed(go, Ground, 0.05f);
            if (float.IsNaN(rt.hi)) { UnityEngine.Object.DestroyImmediate(go); rep.why = "当たりが測れない"; return null; }
            rep.footFloat = rt.hi;
            if (rt.hi <= need + 0.005f) break;
            // 硬い: 足が届かない ── 天端は動かさず丈を増す(長さの狙いは柔らかい)
            float lo, hi; NiwaSpanY(go, out lo, out hi);
            float H = (hi - lo) + (rt.hi - need) + 0.02f;
            float sc2 = sc * H / Mathf.Max(1e-4f, hi - lo);
            if (sc2 <= sc * 1.0001f) break;
            sc = sc2; rep.grew = true;
        }
        if (go == null) { rep.why = "置けない"; return null; }
        if (rep.footFloat > need + 0.005f) { UnityEngine.Object.DestroyImmediate(go); rep.why = "丈を増しても足が届かない(浮き " + rep.footFloat.ToString("F2") + "m)"; return null; }
        // 測り直し: 範囲の内の天端・範囲の外の出
        float topIn2 = float.MinValue, poke = float.MinValue;
        foreach (var w in MeshPointsW(go))
        {
            float s = S(w), t = T(w);
            bool inR = s >= us0 - 1e-4f && s <= us1 + 1e-4f && t >= ut0 - 1e-4f && t <= ut1 + 1e-4f;
            if (inR) topIn2 = Mathf.Max(topIn2, w.y); else poke = Mathf.Max(poke, w.y - under);
        }
        rep.stoneTop = topIn2 == float.MinValue ? float.NaN : topIn2;
        rep.pokeOut = poke == float.MinValue ? float.NaN : poke;
        float mn, mx, pn2, px2; ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx); ProjExtent(go, perp, float.MinValue, float.MaxValue, null, out pn2, out px2);
        rep.longGot = Mathf.Max(mx - mn, px2 - pn2);
        return go;
    }

    /// <summary>**橋台石を据えの作法どおりに据える**(<see cref="NiwaAbutStone"/> に <see cref="NiwaAbutSeatSpec"/> を渡したとき ── 指図 `hashi[].abutSeat`)。
    /// <para>当たり = **版の下面 × 受ける範囲の内の石の天端の高い方から面積 atariFrac の面**(面で受ける ── ⛔ 最も高い一点に当てない)。
    /// 跨ぎ = 範囲の内のそれより低い天端(隙は飼石と土で塞いだ扱い ── sukiMax を超える点の割合と、範囲の縁 = 見える側の隙の最大を刷る)。</para>
    /// <para>① 受ける範囲 = 版の端から inner〜kakari(橋軸)× 版の下面の幅。版の下面は点ごとに実メッシュの三角形を鉛直に引く(<see cref="LowestSurfaceAt"/>)。
    /// ② 天端の選び: 向き turns 通り × 表裏を試し、石の平面を範囲へ寄せ(s の芯は inFromEnd の点 ── 範囲より長ければ範囲の芯・t の芯は版の幅の芯)、
    /// 範囲の内の天端(<see cref="HighestSurfaceAt"/>)の高い atariFrac の面の起伏が最小のものを採る(同点は広い面を橋軸に直交した向きを先に)。
    /// ③ 高さ: atariFrac の面の最も低い点を版の下面に着ける(= 面の全体が下面から −起伏〜0)。最も高い一点の埋めが umeMax を超えるなら umeMax で止める
    /// (硬い ── 当たりの狙いは柔らかいので未達を atariMet=false で刷る)。④ 足: 陸は地表から浮かない・水中は池床 −seatToBed(硬い)。届かなければ丈を増して ②③ をやり直す。</para>
    /// ⛔ 版の topY は動かさない ── 合わせるのは石の側。
    /// 当たる先: 土井の石橋 Hashi_Ishi の橋台石。以後、版を面で受ける石の全て(土橋の橋台・縁束の束石の受け)が同じ欄の形で使える。</summary>
    static GameObject NiwaAbutSeatPlace(Transform parent, string name, string path, GameObject deck, Vector2 aXZ, Vector2 dir, Vector2 perp, bool atA,
                                        float s0, float s1, float sPos, float tc, float ut0, float ut1, float under, float g0, float need, float yaw0, float sc0, float longM,
                                        NiwaAbutSeatSpec seat, ref NiwaAbutRep rep)
    {
        Func<Vector3, float> S = w => Vector2.Dot(new Vector2(w.x, w.z) - aXZ, dir);
        Func<Vector3, float> T = w => Vector2.Dot(new Vector2(w.x, w.z) - aXZ, perp);
        float r0 = atA ? s0 + seat.inner : s1 - seat.kakari, r1 = atA ? s0 + seat.kakari : s1 - seat.inner;
        if (r1 - r0 < 0.02f || ut1 - ut0 < 0.02f) { rep.why = "受ける範囲が引けない(版の端から " + seat.inner.ToString("F2") + "〜" + seat.kakari.ToString("F2") + ")"; return null; }
        var deckSS = SurfaceOf(deck);
        if (deckSS == null) { rep.why = "版の三角形が測れない"; return null; }
        const float STEP = 0.02f;
        var gq = new List<Vector2>(); var gEdge = new List<bool>(); var gDeck = new List<float>();
        int ns = Mathf.Max(1, Mathf.CeilToInt((r1 - r0) / STEP)), nt = Mathf.Max(1, Mathf.CeilToInt((ut1 - ut0) / STEP));
        for (int i = 0; i <= ns; i++)
            for (int j = 0; j <= nt; j++)
            {
                float s = r0 + (r1 - r0) * i / ns, t = ut0 + (ut1 - ut0) * j / nt;
                var q = aXZ + dir * s + perp * t;
                float yd = LowestSurfaceAt(deckSS, q); if (float.IsNaN(yd)) continue;
                gq.Add(q); gDeck.Add(yd); gEdge.Add(i == 0 || i == ns || j == 0 || j == nt);
            }
        if (gq.Count == 0) { rep.why = "受ける範囲に版の下面が無い"; return null; }
        float rc = 0.5f * (r0 + r1);
        var pos = aXZ + dir * sPos + perp * tc;
        int turns = Mathf.Max(1, seat.turns);
        // 置いて範囲へ寄せ、範囲の内の (隙 d = 版の下面 − 石の天端, 縁か) を返す。石の高さは置いたまま(③で動かす)
        Func<GameObject, List<KeyValuePair<float, bool>>> eval = g =>
        {
            var sp = MeshPointsW(g);
            float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
            foreach (var w in sp) { float s = S(w), t = T(w); a0 = Mathf.Min(a0, s); a1 = Mathf.Max(a1, s); b0 = Mathf.Min(b0, t); b1 = Mathf.Max(b1, t); }
            float hd = 0.5f * (a1 - a0);
            float cs = (r1 - r0) >= 2f * hd ? Mathf.Clamp(sPos, r0 + hd, r1 - hd)
                     : seat.landward ? (atA ? r1 - hd : r0 + hd)   // 帯より長い石: 径間の側の面を帯の径間の側の縁へ・余りは陸の側(landward)
                     : rc;
            var sh = dir * (cs - 0.5f * (a0 + a1)) + perp * (tc - 0.5f * (b0 + b1));
            g.transform.position += new Vector3(sh.x, 0f, sh.y);
            var ss = SurfaceOf(g); var res = new List<KeyValuePair<float, bool>>();
            if (ss == null) return res;
            for (int k = 0; k < gq.Count; k++)
            {
                float ys = HighestSurfaceAt(ss, gq[k]); if (float.IsNaN(ys)) continue;
                res.Add(new KeyValuePair<float, bool>(gDeck[k] - ys, gEdge[k]));
            }
            res.Sort((x, y) => x.Key.CompareTo(y.Key));
            return res;
        };
        Func<List<KeyValuePair<float, bool>>, int> k30 = d => Mathf.Clamp(Mathf.CeilToInt(seat.atariFrac * d.Count) - 1, 0, Mathf.Max(0, d.Count - 1));
        // 置く(向き・表裏・縮尺)── 石の幅が版の下面の幅を越えるなら縮める(柔らかい)。返り値の sc は縮めた後
        string curPath = path; float curYaw0 = yaw0;                         // 試している版(替えの版を試すときに入れ替える)
        Func<int, bool, float, bool, KeyValuePair<GameObject, float>> put = (turn, flip, scIn, mayShrink) =>
        {
            float yw = curYaw0 + 360f / turns * turn, s2 = scIn;
            GameObject g = null;
            for (int pass = 0; pass < 2; pass++)
            {
                if (g != null) UnityEngine.Object.DestroyImmediate(g);
                g = Place(curPath, new Vector3(pos.x, g0, pos.y), yw, Vector3.one * s2, parent, name);
                if (g == null) return new KeyValuePair<GameObject, float>(null, s2);
                if (flip) g.transform.rotation = Quaternion.Euler(0f, yw, 0f) * Quaternion.Euler(0f, 0f, 180f);
                if (!mayShrink || pass == 1) break;
                float pn, px; ProjExtent(g, perp, float.MinValue, float.MaxValue, null, out pn, out px);
                float uw = ut1 - ut0;
                if (!(px - pn > uw + 1e-4f)) break;
                s2 *= uw / (px - pn) * 0.999f;
            }
            return new KeyValuePair<GameObject, float>(g, s2);
        };
        // ② 天端の選び(版 = curPath の向き×表裏)
        int bestTurn = -1; bool bestFlip = false; float bestRelief = float.MaxValue, bestCover = 0f, bestSc = sc0;
        Action chooseFace = () =>
        {
        bestTurn = -1; bestFlip = false; bestRelief = float.MaxValue; bestCover = 0f;
        for (int f = 0; f < (seat.flips ? 2 : 1); f++)
            for (int turn = 0; turn < turns; turn++)
            {
                var pr = put(turn, f == 1, sc0, true); if (pr.Key == null) continue;
                var d = eval(pr.Key); UnityEngine.Object.DestroyImmediate(pr.Key);
                if (d.Count == 0) continue;
                float relief = d[k30(d)].Key - d[0].Key, cover = (float)d.Count / gq.Count;
                bool upright = (360f / turns * turn) % 180f < 1e-3f && f == 0;   // 広い面を橋軸に直交したまま
                bool bestUpright = bestTurn >= 0 && !bestFlip && (360f / turns * bestTurn) % 180f < 1e-3f;
                bool better;
                if (bestTurn < 0 || relief < bestRelief - 0.005f) better = true;
                else if (relief > bestRelief + 0.005f) better = false;
                else if (upright != bestUpright) better = upright;
                else better = cover > bestCover + 0.05f || (cover >= bestCover - 0.05f && relief < bestRelief);
                if (better) { bestTurn = turn; bestFlip = f == 1; bestRelief = relief; bestCover = cover; bestSc = pr.Value; }
            }
        };
        float scPath0 = sc0;
        chooseFace();
        if (bestTurn < 0) { rep.why = "どの向きでも受ける範囲の下に石が来ない"; return null; }
        rep.reliefFirst = bestRelief; rep.pathGot = path; rep.sinkScale = 1f; rep.sinkDeep = 0f;
        // ②' 版の替え(指図「起伏 > reliefMax なら石の版を替え」)── 名指しの版で起伏が収まらないときだけ。
        //     起伏 ≤ reliefMax のうち覆いの最も広い版、無ければ起伏の最小の版。覆いが 5 割に満たない版は採らない(細い稜で受けない)
        if (bestRelief > seat.reliefMax + 1e-4f && seat.alts != null && seat.alts.Count > 0)
        {
            string kPath = path; float kYaw = yaw0, kSc0 = sc0; int kTurn = bestTurn; bool kFlip = bestFlip; float kRel = bestRelief, kCov = bestCover, kSc = bestSc;
            foreach (var ap in seat.alts)
            {
                if (string.IsNullOrEmpty(ap) || ap == path) continue;
                float aSc = NiwaScaleForLong(ap, longM); if (float.IsNaN(aSc)) continue;
                curPath = ap; curYaw0 = NiwaBroadFaceYaw(ap, pos, pos + dir); sc0 = aSc;
                chooseFace();
                if (bestTurn < 0 || bestCover < 0.5f) continue;
                bool okNew = bestRelief <= seat.reliefMax + 1e-4f, okOld = kRel <= seat.reliefMax + 1e-4f;
                bool take = okNew && okOld ? bestCover > kCov + 1e-3f : okNew || (!okOld && bestRelief < kRel - 1e-4f);
                if (take) { kPath = ap; kYaw = curYaw0; kSc0 = aSc; kTurn = bestTurn; kFlip = bestFlip; kRel = bestRelief; kCov = bestCover; kSc = bestSc; }
            }
            curPath = kPath; curYaw0 = kYaw; sc0 = kSc0; bestTurn = kTurn; bestFlip = kFlip; bestRelief = kRel; bestCover = kCov; bestSc = kSc;
            rep.swapped = kPath != path; rep.pathGot = kPath;
        }
        // ②'' なお合わなければ石を沈めて根入れを深く(指図の後ろの手)── 石を等方に大きくすると受ける範囲の内の天端の丸みが緩む。
        //     天端は ③ で版の下面へ着けるので、大きくした分だけ足が沈む(増す根入れ ≈ 丈の増し ≤ neiriMax・硬い)。版の幅に収める縮めはしない(柔らかい inside に刷る)
        // ③ と同じ高さの決め(3 割の面の最も低い点を版の下面へ・最も高い一点の埋め ≤ umeMax)で仮に据え、地中に入る深さ ÷ 丈を返す(NaN = 測れない)
        Func<float, float> embedFracAt = scl =>
        {
            var g = put(bestTurn, bestFlip, scl, false).Key; if (g == null) return float.NaN;
            var d = eval(g);
            float res = float.NaN;
            if (d.Count > 0)
            {
                float dzz = d[k30(d)].Key; if (dzz - d[0].Key > seat.umeMax) dzz = d[0].Key + seat.umeMax;
                g.transform.position += new Vector3(0f, dzz, 0f);
                float lo3, hi3; Vector3 ft;
                if (NiwaSpanY(g, out lo3, out hi3) && hi3 - lo3 > 1e-4f && NiwaFootPoint(g, out ft))
                {
                    float gy = Ground(ft.x, ft.z);
                    if (!float.IsNaN(gy)) res = Mathf.Max(0f, gy - lo3) / (hi3 - lo3);
                }
            }
            UnityEngine.Object.DestroyImmediate(g);
            return res;
        };
        rep.embedFrac = float.NaN;
        if (bestRelief > seat.reliefMax + 1e-4f && seat.neiriMax > 1e-4f && !float.IsNaN(seat.neiriFrac))
        {
            var g1 = put(bestTurn, bestFlip, bestSc, false).Key;
            float lo1 = 0f, hi1 = 0f; bool okSpan = g1 != null && NiwaSpanY(g1, out lo1, out hi1);
            if (g1 != null) UnityEngine.Object.DestroyImmediate(g1);
            float h1 = hi1 - lo1;
            if (okSpan && h1 > 1e-3f)
            {
                float kMax = 1f + seat.neiriMax / h1, kGot = 1f, rGot = bestRelief, cGot = bestCover;
                for (int st = 1; st <= 8; st++)
                {
                    float k = 1f + (kMax - 1f) * st / 8f;
                    var g2 = put(bestTurn, bestFlip, bestSc * k, false).Key; if (g2 == null) break;
                    var d2 = eval(g2); UnityEngine.Object.DestroyImmediate(g2);
                    if (d2.Count == 0) continue;
                    // 硬い: 地中に入る深さの合計 ≤ neiriFrac × 丈 ── 大きくするほど深くなるので、越えた段で止める
                    float ef = embedFracAt(bestSc * k);
                    if (float.IsNaN(ef) || ef > seat.neiriFrac + 1e-4f) { rep.embedCapHit = true; break; }
                    float r2 = d2[k30(d2)].Key - d2[0].Key;
                    if (r2 < rGot - 1e-4f) { kGot = k; rGot = r2; cGot = (float)d2.Count / gq.Count; }
                    if (r2 <= seat.reliefMax + 1e-4f) break;
                }
                if (kGot > 1f + 1e-4f) { bestSc *= kGot; bestRelief = rGot; bestCover = cGot; rep.sinkScale = kGot; rep.sinkDeep = (kGot - 1f) * h1; }
            }
        }
        // ②''' 丈の下限(hMin ── 柔らかい)。天端は ③ で版の下面へ着けるので、大きくした分は足が沈む。地中の深さの上限(neiriFrac ── 硬い)を越える段は採らない
        rep.hMinScale = 1f; rep.hMinMet = true; rep.hGot = float.NaN;
        if (!float.IsNaN(seat.hMin) && seat.hMin > 1e-4f)
        {
            var gh = put(bestTurn, bestFlip, bestSc, false).Key;
            float loH = 0f, hiH = 0f; bool okH = gh != null && NiwaSpanY(gh, out loH, out hiH);
            if (gh != null) UnityEngine.Object.DestroyImmediate(gh);
            float h0 = hiH - loH;
            if (!okH || h0 < 1e-3f) rep.hMinMet = false;
            else if (h0 < seat.hMin - 1e-3f)
            {
                float kWant = seat.hMin / h0, kGot = 1f;
                if (float.IsNaN(seat.neiriFrac)) kGot = kWant;
                else
                {
                    float efW = embedFracAt(bestSc * kWant);
                    if (!float.IsNaN(efW) && efW <= seat.neiriFrac + 1e-4f) kGot = kWant;
                    else
                    {
                        // 届く限り: 1〜kWant を二分して地中の深さの上限に収まる最大の縮尺
                        float lo = 1f, hi = kWant;
                        for (int it = 0; it < 10; it++) { float mid = 0.5f * (lo + hi); float ef = embedFracAt(bestSc * mid); if (!float.IsNaN(ef) && ef <= seat.neiriFrac + 1e-4f) lo = mid; else hi = mid; }
                        kGot = lo; rep.embedCapHit = true;
                    }
                }
                if (kGot > 1f + 1e-4f) { bestSc *= kGot; rep.hMinScale = kGot; }
                rep.hMinMet = h0 * kGot >= seat.hMin - 1e-3f;
            }
        }
        rep.yawDeg = 360f / turns * bestTurn; rep.flip = bestFlip; rep.shrunk = bestSc < scPath0 - 1e-6f && !rep.swapped;
        // ③④ 高さ・足(足が届かなければ丈を増してやり直す)
        GameObject go = null; float sc = bestSc; List<KeyValuePair<float, bool>> dd = null; float dz = 0f; Vector3 floatAt = Vector3.zero; float footLo = float.NaN;
        for (int it = 0; it < 6; it++)
        {
            if (go != null) UnityEngine.Object.DestroyImmediate(go);
            go = put(bestTurn, bestFlip, sc, false).Key;
            if (go == null) { rep.why = "置けない"; return null; }
            dd = eval(go);
            if (dd.Count == 0) { UnityEngine.Object.DestroyImmediate(go); rep.why = "丈を増したら受ける範囲の下に石が来ない"; return null; }
            float dmin = dd[0].Key, d30 = dd[k30(dd)].Key;
            dz = d30;                                                          // 3 割の面の最も低い点を版の下面へ
            if (dz - dmin > seat.umeMax) dz = dmin + seat.umeMax;              // 硬い: 最も高い一点の埋め ≤ umeMax
            go.transform.position += new Vector3(0f, dz, 0f);
            var rt = RootToBed(go, Ground, 0.05f);
            if (float.IsNaN(rt.hi)) { UnityEngine.Object.DestroyImmediate(go); rep.why = "当たりが測れない"; return null; }
            rep.footFloat = rt.hi; floatAt = rt.hiAt; footLo = rt.lo;
            if (rt.hi <= need + 0.005f) break;
            float lo, hi; NiwaSpanY(go, out lo, out hi);
            float H = (hi - lo) + (rt.hi - need) + 0.02f;
            float sc2 = sc * H / Mathf.Max(1e-4f, hi - lo);
            if (sc2 <= sc * 1.0001f) break;
            sc = sc2; rep.grew = true;
        }
        //   退けるときは、最も浮いた当たりの位置と地面の高さ・版の端からの橋軸の向きの距離(+ = 径間の側)・最も深い当たりも刷る
        //   (どの向きへ足が逃げたかが分かる ── 2026-10-06 EDO-0533 第17巡: 土井 Hashi_Ishi の a 端 浮き 0.13 の元を測る)
        if (rep.footFloat > need + 0.005f)
        {
            float loF, hiF; bool spanF = NiwaSpanY(go, out loF, out hiF);
            UnityEngine.Object.DestroyImmediate(go);
            var fa = new Vector2(floatAt.x, floatAt.z) - aXZ;
            rep.why = "丈を増しても足が届かない(浮き " + rep.footFloat.ToString("F2") + "m・その当たり (" + floatAt.x.ToString("F2") + "," + floatAt.z.ToString("F2")
                    + ") 地面 " + floatAt.y.ToString("F3") + "・橋軸 " + Vector2.Dot(fa, dir).ToString("+0.00;-0.00") + "m・横 " + Vector2.Dot(fa, perp).ToString("+0.00;-0.00")
                    + "m・最も深い当たり " + footLo.ToString("+0.00;-0.00") + "m・縮尺 " + sc.ToString("F2") + "・版の下面 " + under.ToString("F3")
                    + (spanF ? "・石の下端 " + loF.ToString("F3") + "・天端 " + hiF.ToString("F3") : "") + "・版の端の芯の地面 " + g0.ToString("F3") + ")";
            return null;
        }
        // 刷る値(据えた後の隙 d' = d − dz)
        { float lo4, hi4; Vector3 ft4; if (NiwaSpanY(go, out lo4, out hi4) && hi4 - lo4 > 1e-4f) { rep.hGot = hi4 - lo4; if (!float.IsNaN(seat.hMin)) rep.hMinMet = rep.hGot >= seat.hMin - 1e-3f; if (NiwaFootPoint(go, out ft4)) { float gy4 = Ground(ft4.x, ft4.z); if (!float.IsNaN(gy4)) rep.embedFrac = Mathf.Max(0f, gy4 - lo4) / (hi4 - lo4); } } }
        float dmin2 = dd[0].Key - dz, d302 = dd[k30(dd)].Key - dz;
        rep.seated = true;
        rep.relief = d302 - dmin2; rep.umeDeep = -dmin2; rep.atariGap = d302;
        rep.atariMet = d302 <= seat.atariHi + 1e-4f && dmin2 >= seat.atariLo - 1e-4f;
        rep.reliefOver = rep.relief > seat.reliefMax + 1e-4f;
        rep.cover = (float)dd.Count / gq.Count;
        float smax = float.MinValue, svis = float.MinValue; int over = 0;
        foreach (var kv in dd)
        {
            float g2 = kv.Key - dz;
            smax = Mathf.Max(smax, g2); if (kv.Value) svis = Mathf.Max(svis, g2);
            if (g2 > seat.sukiMax) over++;
        }
        rep.sukiMax = smax; rep.sukiVis = svis == float.MinValue ? float.NaN : svis; rep.sukiOver = (float)over / dd.Count;
        rep.stoneTop = under + rep.umeDeep;
        // 版の外(端の先・版の幅の外)で版の下面より上に出る所
        float poke = float.MinValue, sEnd = atA ? s0 : s1;
        foreach (var w in MeshPointsW(go))
        {
            float s = S(w), t = T(w);
            bool outDeck = (atA ? s < sEnd : s > sEnd) || t < ut0 - 1e-4f || t > ut1 + 1e-4f;
            if (outDeck) poke = Mathf.Max(poke, w.y - under);
        }
        rep.pokeOut = poke == float.MinValue ? float.NaN : poke;
        float pn2, px2; ProjExtent(go, perp, float.MinValue, float.MaxValue, null, out pn2, out px2);
        rep.inside = px2 - pn2 <= (ut1 - ut0) + 1e-3f;
        float mn, mx; ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
        rep.longGot = Mathf.Max(mx - mn, px2 - pn2);
        return go;
    }

    /// <summary>駒の実メッシュの全頂点(世界)。</summary>
    static List<Vector3> MeshPointsW(GameObject go)
    {
        var pts = new List<Vector3>();
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices) pts.Add(l2w.MultiplyPoint3x4(v));
        }
        return pts;
    }

    /// <summary>延段の並べの記録。made = 据えた駒・gapEnds = 走りの両端に残った長さ(片側・m ── 駒は伸縮しないので柔らかい)・
    /// aboveMin/aboveMax = 天端 − 地表(天端の面の下の最も高い所)の実測・sunk = 浮きを消すため沈めた駒(最大 worstSink ── 天端の狙いから下がる)。</summary>
    public struct NiwaNobedanRep { public int made, sunk; public float gapEnds, aboveMin, aboveMax, worstSink, moduleLen; public string why; }

    /// <summary>**延段を a→b に並べ、地表に沿わせて据える**(指図 `nobedan` の topAbove・follow「地表に沿う(段を付けない)」)。
    /// <para>① 駒の長手(実メッシュの平面の長い方)の実長 L で走りを n = round(走り/L) 枚に割り、余りは両端に等しく残す(⛔ 駒を伸縮しない)。
    /// ② 各駒の両端の座で、幅の 3 点の地表の最も高い所 + above を天端の狙いにし、駒を長手の向きに**勾配なりに傾けて**(段を付けない ──
    /// 隣の駒と端の天端が揃う)、実メッシュの外形の中央を座の芯へ・天端の高い端をその狙いへ合わせる。above は走りで一つ(⛔ 駒ごとに振ると段が付く)。
    /// ③ **硬い**: 浮き 0(当たりが地表から浮けば沈める ── 天端の狙いは柔らかい・沈めた駒を数えて刷る)。</para></summary>
    public static List<GameObject> NiwaNobedan(Transform parent, string prefix, string path, Vector2 aXZ, Vector2 bXZ,
                                               float aboveLo, float aboveHi, System.Random rnd, out NiwaNobedanRep rep)
    {
        var made = new List<GameObject>();
        rep = new NiwaNobedanRep { aboveMin = float.NaN, aboveMax = float.NaN, gapEnds = float.NaN, moduleLen = float.NaN };
        var ab = bXZ - aXZ; float len = ab.magnitude;
        if (len < 0.1f || string.IsNullOrEmpty(path)) { rep.why = "走りが短いか部材が無い"; return made; }
        var dir = ab / len; var perp = new Vector2(-dir.y, dir.x);
        var sz = PartSize(path); float L = Mathf.Max(sz.x, sz.z), W = Mathf.Min(sz.x, sz.z);
        if (L < 0.05f) { rep.why = "部材の実寸が測れない"; return made; }
        rep.moduleLen = L;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / L));
        rep.gapEnds = (len - n * L) * 0.5f;
        float above = aboveLo + (float)rnd.NextDouble() * (aboveHi - aboveLo);
        Func<float, float> gAt = s =>
        {
            float m = float.MinValue;
            for (int k = -1; k <= 1; k++) { var q = aXZ + dir * s + perp * (k * 0.5f * W); m = Mathf.Max(m, Ground(q.x, q.y)); }
            return m;
        };
        float yawL = NiwaLongAlongYaw(path, dir);
        for (int i = 0; i < n; i++)
        {
            float sa = rep.gapEnds + i * L, sb = sa + L, sm = 0.5f * (sa + sb);
            float yA = gAt(sa) + above, yB = gAt(sb) + above;
            var c = aXZ + dir * sm;
            var go = Place(path, new Vector3(c.x, 0.5f * (yA + yB), c.y), yawL, Vector3.one, parent, prefix + "_" + i);
            if (go == null) continue;
            // 勾配なりに傾ける(頭を上手へ)── 長手の水平の向き dir のまま、上り yB−yA
            float deg = Mathf.Atan2(yB - yA, L) * Mathf.Rad2Deg;
            if (Mathf.Abs(deg) > 1e-3f)
            {
                var axis = new Vector3(perp.x, 0f, perp.y);
                var q = Quaternion.AngleAxis(-deg, axis);
                // 上り(yB>yA)で b の側が上がる向き: dir を軸 perp まわりに回すと dir×perp の符号で決まる ── 検めて逆なら反す
                var d3 = q * new Vector3(dir.x, 0f, dir.y);
                if ((d3.y > 0f) != (yB > yA)) q = Quaternion.AngleAxis(deg, axis);
                go.transform.rotation = q * go.transform.rotation;
            }
            // 外形の中央を座の芯へ(⛔ ピボットで合わせない)
            float mn, mx, pn, px;
            ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
            ProjExtent(go, perp, float.MinValue, float.MaxValue, null, out pn, out px);
            float ds = Vector2.Dot(c, dir) - 0.5f * (mn + mx), dt = Vector2.Dot(c, perp) - 0.5f * (pn + px);
            var shv = dir * ds + perp * dt;
            go.transform.position += new Vector3(shv.x, 0f, shv.y);
            NiwaTopTo(go, Mathf.Max(yA, yB));
            var rt = RootToBed(go, Ground, 0.05f);
            if (!float.IsNaN(rt.hi) && rt.hi > 0.005f)
            {
                go.transform.position -= new Vector3(0f, rt.hi, 0f);
                rep.sunk++; rep.worstSink = Mathf.Max(rep.worstSink, rt.hi);
            }
            float lo, hi; NiwaSpanY(go, out lo, out hi);
            float gU = NiwaGroundUnderTop(go);
            if (!float.IsNaN(gU))
            {
                float a2 = hi - gU;
                rep.aboveMin = float.IsNaN(rep.aboveMin) ? a2 : Mathf.Min(rep.aboveMin, a2);
                rep.aboveMax = float.IsNaN(rep.aboveMax) ? a2 : Mathf.Max(rep.aboveMax, a2);
            }
            made.Add(go); rep.made++;
        }
        return made;
    }

    /// <summary>**狙いの点 <paramref name="aim"/> に植え、据わらなければ半径 <paramref name="radius"/>[m] の内で硬い条件(<see cref="NiwaField.Put"/> が
    /// 退ける物 ── 区画の線・坂の根入れ・軒・帯)を満たす最も近い所へ寄せて植える**(指図 `shokusai[].atSoft`)。狙いは**柔らかい**:
    /// 置き場は <see cref="PlaceBest"/>(docs/oki-kata.md §4a)で、狙いから近い順に試し最初に据わった所で止める。
    /// <paramref name="moved"/> = 据えた幹の芯と狙いの距離[m](⚠ で刷る)。どこも据わらなければ null(⛔ 建てない)。
    /// ⚠ 寄せる途中で退けた試しは <paramref name="f"/> の落とした数へ数えない(据わったら一つも・据わらなければ狙いで退けた理由だけ残す)。</summary>
    public static GameObject NiwaPutNear(NiwaField f, Transform parent, string path, Vector2 aim, float radius, float yaw, float scale, float sink,
                                         string name, string layer, NiwaSet o, out float moved)
    {
        moved = float.NaN;
        int pEave = f.DropEave, pEdge = f.DropEdge, pSteep = f.DropSteep, pNeire = f.DropNeire, pRef = f.Refused, pBand = f.DropBand, pBody = f.DropBody, pWet = f.DropWet;
        var go0 = f.Put(parent, path, aim, yaw, scale, sink, name, layer, o);
        if (go0 != null) { Vector2 c0; moved = NiwaTrunk(go0, out c0) ? Vector2.Distance(c0, aim) : 0f; return go0; }
        int dEave = f.DropEave, dEdge = f.DropEdge, dSteep = f.DropSteep, dNeire = f.DropNeire, dRef = f.Refused, dBand = f.DropBand, dBody = f.DropBody, dWet = f.DropWet;
        var spots = new List<Vector2>();
        const float RING = 0.2f, ARC = 0.25f;
        for (float r = RING; r <= radius + 1e-4f; r += RING)
        {
            int k = Mathf.Max(8, Mathf.CeilToInt(2f * Mathf.PI * r / ARC));
            for (int j = 0; j < k; j++) { float a = (j + 0.5f * ((int)(r / RING) % 2)) * 2f * Mathf.PI / k; spots.Add(aim + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r); }
        }
        var tally = new SeiyakuTally();
        var go = PlaceBest(spots, spots.Count, p => f.Put(parent, path, p, yaw, scale, sink, name, layer, o), new List<Hard>(), new List<Soft>(), tally);
        // 落とした数: 据わったなら試しを全部数えない・どこも据わらなければ狙いで退けた理由だけ残す
        if (go != null) { f.DropEave = pEave; f.DropEdge = pEdge; f.DropSteep = pSteep; f.DropNeire = pNeire; f.Refused = pRef; f.DropBand = pBand; f.DropBody = pBody; f.DropWet = pWet; }
        else { f.DropEave = dEave; f.DropEdge = dEdge; f.DropSteep = dSteep; f.DropNeire = dNeire; f.Refused = dRef; f.DropBand = dBand; f.DropBody = dBody; f.DropWet = dWet; }
        if (go == null) return null;
        Vector2 c; moved = NiwaTrunk(go, out c) ? Vector2.Distance(c, aim) : float.NaN;
        return go;
    }

    /// <summary>株を並べる生垣の一株(<see cref="NiwaHedgeRow"/> へ渡す)。scale = 等方の倍率・yawOff = 走りの向きからの yaw[°]・
    /// row = 芯からの前後の振り[m](内へ正)・pitchRatio = 芯々 = 株の実幅 × これ・darken = 色を暗く寄せる(<see cref="TintFoliage"/>)。</summary>
    public struct NiwaHedgeKoma { public string path; public float scale, yawOff, row, pitchRatio; public bool darken; }

    /// <summary>塀の駒の内面を測る(<see cref="NiwaHedgeFromWall"/> と <see cref="NiwaHedgeRow"/> の共通)。返り値 f(s) = 座 s の内面の、案内線からの出[m](内へ正・測れなければ NaN)。</summary>
    static Func<float, float> HedgeWallFace(IList<GameObject> wall, Vector2 aXZ, Vector2 dir, Vector2 nrm, float len, out int samples)
    {
        var sv = new List<Vector2>();
        foreach (var go in wall)
        {
            if (go == null || !go.activeInHierarchy) continue;
            var pts = new List<Vector3>(); float y0 = float.MaxValue, y1 = float.MinValue;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                var l2w = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices) { var w = l2w.MultiplyPoint3x4(v); pts.Add(w); y0 = Mathf.Min(y0, w.y); y1 = Mathf.Max(y1, w.y); }
            }
            if (pts.Count == 0) continue;
            float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue;
            foreach (var w in pts) { var q = new Vector2(w.x, w.z) - aXZ; float s = Vector2.Dot(q, dir), t = Vector2.Dot(q, nrm); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); t0 = Mathf.Min(t0, t); t1 = Mathf.Max(t1, t); }
            if (s1 - s0 <= t1 - t0) continue;
            if (s1 < -0.5f || s0 > len + 0.5f || t0 > 3f || t1 < -3f) continue;
            float bLo = y0 + 0.3f * (y1 - y0), bHi = y0 + 0.6f * (y1 - y0);
            foreach (var w in pts)
            {
                if (w.y < bLo || w.y > bHi) continue;
                var q = new Vector2(w.x, w.z) - aXZ; sv.Add(new Vector2(Vector2.Dot(q, dir), Vector2.Dot(q, nrm)));
            }
        }
        samples = sv.Count;
        return s =>
        {
            float best = float.NaN;
            foreach (var q in sv) if (Mathf.Abs(q.x - s) <= 0.5f && (float.IsNaN(best) || q.y > best)) best = q.y;
            return best;
        };
    }

    /// <summary>**塀の内面から離れを取って芯を引き、株立ちの駒を一列に並べる生垣**(指図 `ikegaki` の asset・endAsset・scale・pitchRatio・
    /// yawJitter・rowJitter ── 株の列は呼び手が <paramref name="koma"/>(i, 端か)で渡す)。
    /// <para>① 塀の内面を <see cref="HedgeWallFace"/> で測り、芯 = 内面 + <paramref name="offset"/>(+ 株ごとの row)。② 両端の株を先に置き、
    /// **葉の外形の端**を走りの端(0・len)へ突き付ける。③ 中の株を頭の端の株から順に、芯々 = ½(前の株の実幅 + この株の実幅)× pitchRatio で
    /// 置き(⛔ 等間隔にしない)、尻の端の株との間が半ピッチより詰まる株は置かない。最後に残った隙を中の間へ比例で配る(穴を残さない)。
    /// 平面は葉の外形の中央で合わせる(⛔ ピボットで合わせない)。④ 地面へ据える(**硬い**: 浮き 0 ── <see cref="SinkToBed"/>)。</para>
    /// <para>**硬い**: 内面が測れない座には植えない・浮き 0。**柔らかい**: 丈(倍率の従属・刷るだけ)・葉と塀の隙(刷るだけ)・芯々(刷るだけ)。</para></summary>
    public static List<GameObject> NiwaHedgeRow(Transform parent, string prefix, IList<GameObject> wall, Vector2 aXZ, Vector2 bXZ,
                                                Vector2 inward, float offset, Func<int, bool, NiwaHedgeKoma> koma, out NiwaHedgeRep repOut)
    {
        var made = new List<GameObject>();
        var rep = new NiwaHedgeRep { faceMin = float.NaN, faceMax = float.NaN, sx = 1f, floatWorst = float.NaN, buryWorst = float.NaN, wallGap = float.NaN, h = float.NaN, pitchMin = float.NaN, pitchMax = float.NaN };
        var ab = bXZ - aXZ; float len = ab.magnitude;
        if (len < 0.5f || wall == null || wall.Count == 0 || koma == null) { rep.why = "案内線が短いか塀の駒が無い"; { repOut = rep; return made; } }
        var dir = ab / len; var nrm = new Vector2(-dir.y, dir.x); if (Vector2.Dot(nrm, inward) < 0f) nrm = -nrm;
        int samples; var faceAt = HedgeWallFace(wall, aXZ, dir, nrm, len, out samples);
        if (samples == 0) { rep.why = "案内線の脇に線と平行な塀の駒が無い(塀が未建か名が違う)"; { repOut = rep; return made; } }
        float baseS = Vector2.Dot(aXZ, dir), baseT = Vector2.Dot(aXZ, nrm);
        float yaw0 = YawLocalAxisTo(true, dir);
        // 一株を座 s(芯)へ。⛔ 内面が測れなければ置かない。返り値 = 駒・w = 葉の外形の走りの実幅
        Func<NiwaHedgeKoma, float, int, KeyValuePair<GameObject, float>> put = (k, s, i) =>
        {
            float f = faceAt(Mathf.Clamp(s, 0f, len));
            if (float.IsNaN(f)) { rep.noFace++; return new KeyValuePair<GameObject, float>(null, 0f); }
            rep.faceMin = float.IsNaN(rep.faceMin) ? f : Mathf.Min(rep.faceMin, f);
            rep.faceMax = float.IsNaN(rep.faceMax) ? f : Mathf.Max(rep.faceMax, f);
            float core = f + offset + k.row;
            var c0 = aXZ + dir * s + nrm * core;
            var go = Place(k.path, new Vector3(c0.x, Ground(c0.x, c0.y), c0.y), yaw0 + k.yawOff, Vector3.one * k.scale, parent, prefix + "_" + i);
            if (go == null) return new KeyValuePair<GameObject, float>(null, 0f);
            float mn, mx, pn, px;
            ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
            ProjExtent(go, nrm, float.MinValue, float.MaxValue, null, out pn, out px);
            float ds = (baseS + s) - 0.5f * (mn + mx), dt = (baseT + core) - 0.5f * (pn + px);
            go.transform.position += new Vector3(dir.x * ds + nrm.x * dt, 0f, dir.y * ds + nrm.y * dt);
            if (k.darken) TintFoliage(go, IKE_TINT_FRONT);
            float gap = (pn + dt - baseT) - f;
            rep.wallGap = float.IsNaN(rep.wallGap) ? gap : Mathf.Min(rep.wallGap, gap);
            return new KeyValuePair<GameObject, float>(go, mx - mn);
        };
        Action<GameObject, float> slide = (go, d) => go.transform.position += new Vector3(dir.x * d, 0f, dir.y * d);
        // ② 両端の株(葉の外形の端を 0 と len へ)
        var kA = koma(0, true); var pA = put(kA, 0f, 0);
        float cA = float.NaN, wA = 0f;
        if (pA.Key != null) { wA = pA.Value; slide(pA.Key, wA * 0.5f); cA = wA * 0.5f; }
        var kB = koma(9999, true); var pB = put(kB, len, 9999);
        float cB = float.NaN, wB = 0f;
        if (pB.Key != null) { wB = pB.Value; slide(pB.Key, -wB * 0.5f); cB = len - wB * 0.5f; pB.Key.name = prefix + "_End"; }
        if (float.IsNaN(cA)) { cA = 0f; wA = 0f; }
        if (float.IsNaN(cB)) { cB = len; wB = 0f; }
        // ③ 中の株
        var mids = new List<GameObject>(); var cs = new List<float>(); var ws = new List<float>();
        float cPrev = cA, wPrev = wA;
        for (int i = 1; i < 2000; i++)
        {
            var k = koma(i, false);
            var pk = put(k, cPrev + 0.5f, i);
            if (pk.Key == null) { cPrev += 0.5f; if (cPrev > cB) break; continue; }
            float w = pk.Value, pitch = 0.5f * ((wPrev > 0f ? wPrev : w) + w) * k.pitchRatio, c = cPrev + pitch;
            if (c > cB - 0.5f * (0.5f * (w + (wB > 0f ? wB : w)) * k.pitchRatio)) { UnityEngine.Object.DestroyImmediate(pk.Key); break; }
            slide(pk.Key, c - (cPrev + 0.5f));
            mids.Add(pk.Key); cs.Add(c); ws.Add(w);
            rep.pitchMin = float.IsNaN(rep.pitchMin) ? pitch : Mathf.Min(rep.pitchMin, pitch);
            rep.pitchMax = float.IsNaN(rep.pitchMax) ? pitch : Mathf.Max(rep.pitchMax, pitch);
            cPrev = c; wPrev = w;
        }
        // 残った隙(尻の端の株までの間 − 狙いの芯々)を中の間へ比例で配る
        if (mids.Count > 0)
        {
            var kLast = koma(mids.Count + 1, false);
            float want = 0.5f * (ws[ws.Count - 1] + (wB > 0f ? wB : ws[ws.Count - 1])) * kLast.pitchRatio;
            float resid = (cB - cs[cs.Count - 1]) - want;
            for (int j = 0; j < mids.Count; j++) slide(mids[j], resid * (j + 1) / (mids.Count + 1));
        }
        var all = new List<GameObject>();
        if (pA.Key != null) all.Add(pA.Key);
        all.AddRange(mids);
        if (pB.Key != null) all.Add(pB.Key);
        // ④ 据え(硬い: 浮き 0)
        foreach (var go in all)
        {
            var rt = SinkToBed(go, Ground, 0.05f);
            if (float.IsNaN(rt.hi)) { UnityEngine.Object.DestroyImmediate(go); rep.noFace++; continue; }
            rep.floatWorst = float.IsNaN(rep.floatWorst) ? rt.hi : Mathf.Max(rep.floatWorst, rt.hi);
            rep.buryWorst = float.IsNaN(rep.buryWorst) ? rt.lo : Mathf.Min(rep.buryWorst, rt.lo);
            float lo, hi; if (NiwaSpanY(go, out lo, out hi)) rep.h = float.IsNaN(rep.h) ? hi - lo : Mathf.Max(rep.h, hi - lo);
            made.Add(go); rep.made++;
        }
        { repOut = rep; return made; }
    }

    /// <summary>駒の**平面の外形**を、駒の向き(local X・Z の水平の向き)の矩形で測る(全頂点の射影の範囲)。c = 矩形の芯(XZ)・ax/az = 向き・
    /// hx/hz = 半幅[m]。⛔ ピボット・bounds の中心で代えない。当たる先: 呑口の据え土の外形(6b)。</summary>
    public static bool NiwaPlanBox(GameObject go, out Vector2 c, out Vector2 ax, out Vector2 az, out float hx, out float hz)
    {
        var r = go.transform.rotation;
        var x3 = r * Vector3.right; var z3 = r * Vector3.forward;
        ax = new Vector2(x3.x, x3.z); az = new Vector2(z3.x, z3.z);
        if (ax.sqrMagnitude < 1e-6f) ax = Vector2.right; if (az.sqrMagnitude < 1e-6f) az = Vector2.up;
        ax.Normalize(); az.Normalize();
        float a0, a1, b0, b1;
        ProjExtent(go, ax, float.MinValue, float.MaxValue, null, out a0, out a1);
        ProjExtent(go, az, float.MinValue, float.MaxValue, null, out b0, out b1);
        c = Vector2.zero; hx = hz = 0f;
        if (a0 > a1 || b0 > b1) return false;
        hx = 0.5f * (a1 - a0); hz = 0.5f * (b1 - b0);
        // 芯 = ax·c = (a0+a1)/2, az·c = (b0+b1)/2 を解く
        float det = ax.x * az.y - ax.y * az.x;
        if (Mathf.Abs(det) < 1e-6f) return false;
        float pa = 0.5f * (a0 + a1), pb = 0.5f * (b0 + b1);
        c = new Vector2((pa * az.y - ax.y * pb) / det, (ax.x * pb - pa * az.x) / det);
        return true;
    }

    // ─────────── 池の水面の映り(反射プローブ)── EDO-0533 ───────────
    //
    // ⛔ 2026-10-05 EDO-0533: 場面に反射プローブが無く、Edo/Water の GlossyEnvironmentReflection(EdoWater.shader の「反射(空/環境)」)が
    //    Default-Skybox の地面側(灰茶)を映して、泉水の水面が低い角度で茶色く見えた。⇒ 池ごとに一つ、水面の上に焼いたプローブを置く。
    // ⭐ 焼きの方式(Unity の定石): 静かな景色なので**焼き**(realtime にしない)。プローブは邸のプレハブの中に入るので、場面の照明データに
    //    焼き込む Baked でなく **Custom + 焼いたキューブマップの資産**(Lighting の Bake と同じ Lightmapping.BakeReflectionProbe ── 資産を参照するので
    //    プレハブを解き直しても失わない)。庭の石・木は Static でないので renderDynamicObjects を立てて写す。焼く間は水面そのものを隠す(自分を映さない)。
    // ⛔ 水の材質は触らない(見え方は WaterBaker.ApplyLook の式)。焼いた絵の置き場は水面の材質(無ければメッシュ)の資産の隣・名は水域の名から
    //    (⛔ パスの文字列を書かない ── 規則12)。
    // 当たる先: 土井の泉水(EdoDoiBuilder.Niwa 6i)。同じ型で岡部・松江松平・山王の池にも効く(WaterBody を渡すだけ ── 呼び出しは各邸の庭の工程へ)。

    /// <summary>反射プローブの範囲の余裕(水面の外接箱の外へ水平に)・水面から上の高さ・下の深さ・写す点の水面からの高さ[m]・キューブマップの一辺[px]。
    /// 描画の都合の値で、指図の設計値ではない(邸ごとに変えない)。</summary>
    public const float MIZU_KAGAMI_MARGIN = 3f, MIZU_KAGAMI_ABOVE = 8f, MIZU_KAGAMI_BELOW = 1f, MIZU_KAGAMI_EYE = 1f;
    public const int MIZU_KAGAMI_RES = 128;

    /// <summary><see cref="MizuKagami"/> の記録。baked = 焼けた・texPath = 焼いた絵の資産・size = 範囲の箱・eyeY = 写した点の高さ・why = 置けない/焼けない理由。</summary>
    public struct MizuKagamiRep { public bool baked; public string texPath, why; public Vector3 size; public float eyeY; }

    /// <summary>**池の水面の上に反射プローブを一つ置いて焼く**(水面が空の地面側を映して茶色く見えるのを、周りの庭を映すように直す)。
    /// <para>範囲 = 水面の実メッシュの外接箱(世界)の外へ <paramref name="margin"/>・高さは水面 −<see cref="MIZU_KAGAMI_BELOW"/>〜+<paramref name="above"/>
    /// (水面の描画の箱を必ず含む ── プローブはこの箱で水面に割り当たる)。写す点 = 箱の平面の芯・水面 +<see cref="MIZU_KAGAMI_EYE"/>。
    /// Custom・renderDynamicObjects・HDR・一辺 <see cref="MIZU_KAGAMI_RES"/>・空で消す。水面の描画は BlendProbes にする(Off なら映らない)。</para>
    /// 置いた GameObject は <paramref name="parent"/> の下(名 = 水域の名 + "_Kagami")。焼けなければプローブは残し baked = false と理由を返す。
    /// ⚠ 庭の物を全部建てた後に呼ぶ(焼いた後に建てた物は映らない ── 建て直したら焼き直す)。</summary>
    public static ReflectionProbe MizuKagami(Transform parent, WaterBody wb, out MizuKagamiRep rep, float margin = MIZU_KAGAMI_MARGIN, float above = MIZU_KAGAMI_ABOVE)
    {
        rep = new MizuKagamiRep { eyeY = float.NaN };
        if (wb == null) { rep.why = "水域(WaterBody)が無い"; return null; }
        var mr = wb.GetComponent<MeshRenderer>(); var mf = wb.GetComponent<MeshFilter>();
        if (mr == null || mf == null || mf.sharedMesh == null) { rep.why = "水面のメッシュが無い(WaterBaker.RebuildSurface の前)"; return null; }
        string src = mr.sharedMaterial != null ? AssetDatabase.GetAssetPath(mr.sharedMaterial) : null;
        if (string.IsNullOrEmpty(src)) src = AssetDatabase.GetAssetPath(mf.sharedMesh);
        if (string.IsNullOrEmpty(src)) { rep.why = "水面の材質にもメッシュにも資産のパスが無い ── 焼いた絵の置き場が決まらない"; return null; }
        rep.texPath = System.IO.Path.GetDirectoryName(src).Replace('\\', '/') + "/" + wb.name + "_Kagami.exr";
        var b = mr.bounds;
        float y0 = wb.waterY - MIZU_KAGAMI_BELOW, y1 = wb.waterY + above;
        var bmin = new Vector3(b.min.x - margin, Mathf.Min(y0, b.min.y - 0.1f), b.min.z - margin);
        var bmax = new Vector3(b.max.x + margin, Mathf.Max(y1, b.max.y + 0.1f), b.max.z + margin);
        var eye = new Vector3(0.5f * (bmin.x + bmax.x), wb.waterY + MIZU_KAGAMI_EYE, 0.5f * (bmin.z + bmax.z));
        rep.size = bmax - bmin; rep.eyeY = eye.y;
        var go = new GameObject(wb.name + "_Kagami");
        Undo.RegisterCreatedObjectUndo(go, "mizu kagami");
        if (parent != null) go.transform.SetParent(parent, true);
        go.transform.position = eye; go.transform.rotation = Quaternion.identity; go.transform.localScale = Vector3.one;
        var pr = go.AddComponent<ReflectionProbe>();
        pr.mode = UnityEngine.Rendering.ReflectionProbeMode.Custom;
        pr.renderDynamicObjects = true;
        pr.refreshMode = UnityEngine.Rendering.ReflectionProbeRefreshMode.ViaScripting;
        pr.boxProjection = true;
        pr.size = rep.size; pr.center = 0.5f * (bmin + bmax) - eye;
        pr.resolution = MIZU_KAGAMI_RES; pr.hdr = true;
        pr.clearFlags = UnityEngine.Rendering.ReflectionProbeClearFlags.Skybox;
        pr.nearClipPlane = 0.1f; pr.farClipPlane = 1000f;
        pr.importance = 1; pr.intensity = 1f; pr.blendDistance = 1f; pr.cullingMask = ~0;
        if (mr.reflectionProbeUsage == UnityEngine.Rendering.ReflectionProbeUsage.Off) mr.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.BlendProbes;
        bool was = mr.enabled; bool ok = false;
        try { mr.enabled = false; ok = Lightmapping.BakeReflectionProbe(pr, rep.texPath); }
        catch (Exception e) { rep.why = "焼けない: " + e.Message; }
        finally { mr.enabled = was; }
        if (!ok) { if (rep.why == null) rep.why = "Lightmapping.BakeReflectionProbe が false を返した"; return pr; }
        AssetDatabase.ImportAsset(rep.texPath, ImportAssetOptions.ForceUpdate);
        var ti = AssetImporter.GetAtPath(rep.texPath) as TextureImporter;
        if (ti != null && ti.textureShape != TextureImporterShape.TextureCube) { ti.textureShape = TextureImporterShape.TextureCube; ti.SaveAndReimport(); }
        var tex = AssetDatabase.LoadAssetAtPath<Texture>(rep.texPath);
        if (tex == null) { rep.why = "焼いた絵が読めない: " + rep.texPath; return pr; }
        pr.customBakedTexture = tex;
        EditorUtility.SetDirty(pr);
        rep.baked = true;
        return pr;
    }
}
