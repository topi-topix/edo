// 配置・資産系の共有基盤 (Phase 2c, 2026-08-26)
//   EdoNishiTameikeBuilder (1305行の屋敷ビルダー) に埋まっていた共有ヘルパの本体をここへ移した。
//   NT 側はシグネチャ温存の1行委譲を残しており、NT を参照する既存16ファイルは無変更で動く。
//   各ビルダーの Ground 委譲チェーン (Shinmachi→Tamachi→TameikeKita 等) はここへ1段化済み。
//   2026-09-21 (EDO-0299): NagayaRun / DobeiRun / PanelRun / MoveToObb / NaturalMode も
//   ここへ引き取り、EdoNishiTameikeBuilder・EdoSannoJuboBuilder・EdoSannoKitaBuilder を廃止した。
//   囲いの run は EdoBuildRun.cs (同じ partial class) にある。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>edogoyomi の倍率 = 江戸間 1 間 = 6 尺 (CLAUDE.md 座標系の表)。
    /// ⚠ 各ビルダーが持つ `const float ES = 1.818f` の写しはここへ寄せること。</summary>
    public const float ES = 1.818f;

    // ⚠ 2026-09-21 — `Ground`/`GroundGrid` は **1 頂点につき 1 回**呼ばれる(接地の測りは駒の全頂点を引く)。
    //   そこで `T()` が毎回 `FindObjectsByType<Terrain>` でシーンを全走査していたため、松江松平の普請検査
    //   (植栽 1278 点・駒あたり最大 4000 頂点)が 40 分を超えた。⭐ `Terrain.SampleHeight` 自体は速い —
    //   遅かったのは**その手前の Terrain の探し直し**。⇒ 掴んだ物が失効したときだけ探し直す。
    //   ⛔ 掴むのは Terrain の参照だけで、**原点の y は掴まない**(`Ground` は毎回 transform から読む)。
    //      造成やジオリファレンスで Terrain が動いたとき、古い y を返して全部の高さを静かに狂わせない為。
    static Terrain _terrain;

    /// <summary>掴んでいる Terrain を捨てる。⚠ **Terrain を差し替えたのに古い物が active のまま残る**
    /// 差し替え方をしたときだけ要る(active が落ちる差し替えなら <see cref="T"/> が自分で拾い直す)。</summary>
    public static void InvalidateTerrain() { _terrain = null; }

    /// <summary>アクティブな Terrain (最初の1枚)。無ければ例外。⭐ 掴んだ物が生きていれば再走査しない。</summary>
    public static Terrain T()
    {
        var c = _terrain;
        if (c != null && c.gameObject.activeInHierarchy) return c;
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy) { _terrain = t; return t; }
        throw new Exception("no active terrain");
    }

    /// <summary>**地表を何度も引くための掴み。**Terrain と原点の y を一度だけ掴み、以後は `SampleHeight` だけを叩く。
    /// ⭐ 駒の全頂点を引く所(<see cref="Contact(GameObject,out Vector3,out int,float,int)"/>)で使う。
    /// ⛔ 1 巡のあいだに Terrain を動かす所では使わない(掴んだ原点の y が古くなる)。</summary>
    public struct GroundProbe
    {
        readonly Terrain t; readonly float y0;
        public GroundProbe(Terrain terrain) { t = terrain; y0 = terrain.transform.position.y; }
        public float At(float x, float z) { return t.SampleHeight(new Vector3(x, 0f, z)) + y0; }
    }

    /// <summary>地表の引き手を一つ作る。<see cref="GroundProbe"/> を見よ。</summary>
    public static GroundProbe Probe() { return new GroundProbe(T()); }

    /// <summary>live terrain の標高 (m)。⚠ 造成が乗る作業面 — 造成前の地盤は docs/Sashizu/base_dem.json が正典。</summary>
    public static float Ground(float x, float z) { var t = T(); return t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y; }

    static GameObject Load(string path)
    {
        var a = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (a == null) throw new Exception("asset not found: " + path);
        return a;
    }

    /// <summary>プレハブを実体化して置く。パスは EdoAssets 経由で渡すこと (規則11)。</summary>
    public static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = scale;
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }

    /// <summary>子孫 Renderer 全体のワールド Bounds。</summary>
    public static Bounds RB(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }

    /// <summary>Bounds の底面を y に据える。</summary>
    public static void SeatBottom(GameObject go, float y)
    {
        var b = RB(go);
        go.transform.position += new Vector3(0, y - b.min.y, 0);
    }

    /// <summary>it のローカル座標系での mesh 頂点 footprint (OBB)。Jubo/ToranomonUchi/TodaBlock のバイト同一実装を移設。</summary>
    public static void ObbFootprint(Transform it, out float mnx, out float mxx, out float mnz, out float mxz, out float mny)
    {
        mnx = float.MaxValue; mxx = float.MinValue; mnz = float.MaxValue; mxz = float.MinValue; mny = float.MaxValue;
        foreach (var mf in it.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var vts = mesh.vertices;
            for (int i = 0; i < vts.Length; i++)
            {
                var lp = it.InverseTransformPoint(mf.transform.TransformPoint(vts[i]));
                mnx = Mathf.Min(mnx, lp.x); mxx = Mathf.Max(mxx, lp.x);
                mnz = Mathf.Min(mnz, lp.z); mxz = Mathf.Max(mxz, lp.z);
                mny = Mathf.Min(mny, lp.y);
            }
        }
    }

    // ================================================================ 据え付けの技法(2026-09-20)
    // ⭐ **置いた時点で隙・穴・浮きが起きない置き方**の道具。施主指示(2026-09-20)「検査を足すな。
    //   Unity で部材を置く技法として取り込め」。原則は三つ —
    //   ① 固定側(門構え・隅)を先に置く ② 可動側は**置いた駒の実メッシュの面**を測って相手の面へ寄せる
    //   ③ 高さは**その下の実物**(石垣の天端・段の格子点の中央値)を測って据える。
    //   ⛔ 指図の s・y を座標として使わない。⛔ 事後に寄せる関数(CloseKadoSeams 型)を足さない —
    //   寄せる関数があるほど置き方の欠陥が隠れる(松江松平 2026-09-20: 門の隙 0.42m・隅の穴 1.18m・御殿の浮き 0.93m)。
    //   松江松平の `MeshBody` / `ProjBand` / `EdgeAlong` / `CloseKadoSeams` の伸縮を共通へ移した物。
    //   → スキル unity-buke-yashiki/references/sashizu.md §3f「置き方の4手」

    /// <summary>屋根系のメッシュ名か(yane / noki / taruki / mune / keta)。⛔ 軒は壁より先に触れるので
    /// 取り合いの面に使わない。</summary>
    public static bool IsRoofName(string name)
    {
        string n = name.ToLower();
        // ⛔ 棟割長屋(munewari)の "mune" は棟ではなく「棟を割る」の意。単一メッシュの駒がこれで丸ごと屋根扱いになり、
        //    壁体の頂点が 0 になった — 区域侵犯も隣とのめり込みも**棟割だけ素通り**していた(EDO-0355・
        //    新町 ra で表店の5間の駒が棟割へ −7.9m めり込んだのに Clashes が NaN を返した)。
        //    ⚠ 部分文字列の篩なので同じ型は他にも起きうる(Enoki / Mukunoki の "noki")。駒を焼いたら壁体の頂点が
        //    0 でないことを確かめる。
        if (n.Contains("munewari")) return false;
        return n.Contains("yane") || n.Contains("noki") || n.Contains("taruki") || n.Contains("mune") || n.Contains("keta");
    }

    /// <summary>屋根名の篩に掛ける**部材の素性の名**。⛔ **手渡された根の GameObject 名は使わない** —
    /// 根の名は <see cref="Place"/> が付けた**呼び名**(「Mon_munemon」「Bansho_L」など)で、部材の素性ではない。
    ///
    /// <para>⛔ 2026-09-21 に踏んだ(EDO-0318 ①): 部材方が焼いた駒は**単一メッシュが根に載る**ので、
    /// `Place()` が根を "Mon_munemon" へ改名した瞬間に <see cref="IsRoofName"/> が "**mune**" を拾い、
    /// 壁体の頂点が 0 になって <see cref="SeatOnGround"/> が「測れる頂点が無い」を投げた。
    /// 棟門が一基も据わらない。⚠ 同じ型は "…keta…" "…noki…" を含む呼び名でも起きる。</para>
    ///
    /// <para>根に載っているメッシュは**メッシュ資産の名**で判ずる(FBX 由来なので改名されない)。
    /// 子の GameObject は部材の中の名前がそのまま残っているので従来どおり。</para></summary>
    static string PartName(Transform root, MeshFilter mf)
    {
        if (mf.transform != root) return mf.name;
        return mf.sharedMesh != null ? mf.sharedMesh.name : mf.name;
    }

    /// <summary>**壁体**(屋根・軒・垂木・棟・桁を除く、見えているメッシュ)の頂点を世界座標で。
    /// <paramref name="maxSamples"/> は一様な添字間引きの上限(既定 900・性能優先)。
    /// ⚠ 一様な間引きは極値を落とすことがある — 隅部材(単一メッシュ 1.6〜1.8 万頂点)は 999999 を渡して
    /// 間引かない(松江松平 2026-09-08: 留め継ぎの先端の疎な頂点が落ちて隙間を 0.46m と過大に出した)。
    /// ⛔ **接地(地面との隙)を測るなら這って使わない** — <see cref="Contact(GameObject,out Vector3,out int,float,int)"/>
    /// は格子ごとの最下点だけを拾う専用の集め方(<see cref="GroundCandidates"/>)を使う(EDO-0357)。
    /// ⛔ **区域侵犯・軸方向の伸び(境界系)を測るなら這って使わない** — <see cref="KeepInsidePoly"/> /
    /// <see cref="EdgeAlong"/> / <see cref="LocalSpan"/> / <see cref="StretchEnd"/> は局所XZの凸包だけを拾う
    /// 専用の集め方(<see cref="EdgeCandidates"/>)を使う — 一様な間引きは境界側では極値を落として
    /// 区域侵犯を見逃す方向になり危険(EDO-0383)。</summary>
    /// <param name="withRoof">true なら屋根系のメッシュも含める。⭐ 屋根と屋根・軒と塀のように
    /// **屋根そのものが触れる取り合い**を測るときに使う(既定の false は壁の面を測るため)。</param>
    public static List<Vector3> Body(Transform tr, int maxSamples = 900, bool withRoof = false)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (!withRoof && IsRoofName(PartName(tr, mf))) continue;
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            int step = Mathf.Max(1, vs.Length / Mathf.Max(1, maxSamples));
            for (int i = 0; i < vs.Length; i += step) L.Add(l2w.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    /// <summary>接地(<see cref="Contact(GameObject,out Vector3,out int,float,int)"/>)専用の頂点集め。
    /// <see cref="Body"/> の一様な添字間引き・単純な Y 昇順間引きのどちらも、**根元から離れた場所で
    /// 先に着く駒**を落とす — 屋敷林は根元(局所Y最小)が地面と離れていて、斜面へ垂れた枝の方が先に
    /// 着いていた(EDO-0357・2026-09-22 実測: 800 点で +1.05m「浮き」、全頂点では −0.06m。
    /// 着いていた頂点は局所Yの下から 437/8432 番目で、根元でも樹冠でもない中腹だった)。
    ///
    /// <para>そこで局所 XZ を粗い格子(既定 <paramref name="maxSamples"/> の平方根角)に割り、
    /// **格子ごとに局所Yが最小の頂点だけ**を残す。同じ(x,z)付近では地面の高さはほぼ一定なので、
    /// 同じ格子内でそれより高い頂点は地面までの隙が必ずそれ以上になり、捨ててよい
    /// (`docs/oki-kata.md` の部材どうしの Contact が使う「0.25m角の筋」と同じ考え方)。
    /// 格子は局所 XZ で割る(据え付けは Y 軸まわりの回転のみという慣行なので、世界 XZ の格子と
    /// ほぼ相似になる)。メッシュ資産ごとに 1 度だけ計算してキャッシュする(同じ部材を 79 区画へ
    /// 量産で置く負荷を増やさないため)。</para></summary>
    static readonly Dictionary<(Mesh, int), int[]> _groundCellCache = new Dictionary<(Mesh, int), int[]>();
    static int[] LowestPerCell(Mesh m, int maxSamples)
    {
        var key = (m, maxSamples);
        int[] keep;
        if (_groundCellCache.TryGetValue(key, out keep)) return keep;
        var vs = m.vertices;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        for (int i = 0; i < vs.Length; i++)
        {
            if (vs[i].x < mnx) mnx = vs[i].x; if (vs[i].x > mxx) mxx = vs[i].x;
            if (vs[i].z < mnz) mnz = vs[i].z; if (vs[i].z > mxz) mxz = vs[i].z;
        }
        int gridN = Mathf.Max(1, Mathf.CeilToInt(Mathf.Sqrt(maxSamples)));
        float sx = mxx - mnx, sz = mxz - mnz;
        var best = new Dictionary<long, int>();
        for (int i = 0; i < vs.Length; i++)
        {
            int ix = sx > 1e-6f ? Mathf.Clamp((int)((vs[i].x - mnx) / sx * gridN), 0, gridN - 1) : 0;
            int iz = sz > 1e-6f ? Mathf.Clamp((int)((vs[i].z - mnz) / sz * gridN), 0, gridN - 1) : 0;
            long cell = (long)ix * gridN + iz;
            int cur;
            if (!best.TryGetValue(cell, out cur) || vs[i].y < vs[cur].y) best[cell] = i;
        }
        keep = new int[best.Count]; best.Values.CopyTo(keep, 0);
        _groundCellCache[key] = keep;
        return keep;
    }
    static List<Vector3> GroundCandidates(Transform tr, int maxSamples)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (IsRoofName(PartName(tr, mf))) continue;         // 接地は壁体で測る(屋根は除く・Body と同じ篩)
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            if (vs.Length <= maxSamples) { foreach (var v in vs) L.Add(l2w.MultiplyPoint3x4(v)); continue; }
            foreach (var i in LowestPerCell(mf.sharedMesh, maxSamples)) L.Add(l2w.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    /// <summary>境界系(<see cref="OutsideBy"/> 経由の <see cref="KeepInsidePoly"/> / <see cref="EdgeAlong"/> /
    /// <see cref="LocalSpan"/> / <see cref="StretchEnd"/>)専用の頂点集め。これらはみな**局所 XZ(水平)の
    /// 軸か多角形**しか扱わないので、局所 XZ の凸包(<see cref="EdoGeom.HullXZ"/>)だけを候補にすれば足りる —
    /// 凸包の外の頂点は、その頂点集合のどの向きへの投影でも凸包上のいずれかの頂点以下にしかならない
    /// (凸性の定義そのもの)。<see cref="Body"/> の一様な添字間引きは区画の外へ最も出ている頂点や軸方向の
    /// 端の頂点を間引きで落とすことがあり、境界側は**過小評価**(区域侵犯の見逃し・軸の伸びの過小算定)に
    /// なって規則4の許容0に反する危険があった(EDO-0383・2026-09-22。実測はしていない・設計上の危険として
    /// 間引きでなく正確な絞り込みへ直した)。メッシュ資産ごとに1度だけ計算してキャッシュする。
    /// ⚠ ax/localAxis に鉛直成分がある使い方は想定していない(これらの関数はいずれも水平の走り・伸縮にしか
    /// 使われていない)。</summary>
    static readonly Dictionary<Mesh, int[]> _hullXZCache = new Dictionary<Mesh, int[]>();
    static int[] HullXZIndices(Mesh m)
    {
        int[] keep;
        if (_hullXZCache.TryGetValue(m, out keep)) return keep;
        var vs = m.vertices;
        var pts2 = new Vector2[vs.Length];
        for (int i = 0; i < vs.Length; i++) pts2[i] = new Vector2(vs[i].x, vs[i].z);
        keep = EdoGeom.HullXZ(pts2);
        _hullXZCache[m] = keep;
        return keep;
    }
    static List<Vector3> EdgeCandidates(Transform tr)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (IsRoofName(PartName(tr, mf))) continue;         // 境界は壁体で測る(屋根は除く・Body と同じ篩)
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            foreach (var i in HullXZIndices(mf.sharedMesh)) L.Add(l2w.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    /// <summary>駒の壁体の、世界軸 <paramref name="ax"/> 方向の端の座標(<paramref name="sgn"/> ≥ 0 なら最大側)。
    /// 頂点が無ければ NaN。候補は <see cref="EdgeCandidates"/>(局所XZの凸包・EDO-0383)— 間引きでなく
    /// 正確な絞り込みなので maxSamples は無い。</summary>
    public static float EdgeAlong(Transform tr, Vector3 ax, float sgn)
    {
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in EdgeCandidates(tr)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
        if (mx < mn) return float.NaN;
        return sgn >= 0 ? mx : mn;
    }

    /// <summary>高さの帯 [<paramref name="yLo"/>, <paramref name="yHi"/>] にある見えている頂点を、
    /// 走り方向 <paramref name="dir"/>(xz)へ投影した min/max。頂点が無ければ mn &gt; mx。
    /// ⭐ **「指図が名指しした面」を測る道具** — 部材には躯体のほかに基壇・軒・庇・出格子が付いていて、
    /// 全メッシュの最大投影はそれらを拾う(番所で 0.40m 過大)。帯は**その面が存在する高さ**から取る。
    /// <paramref name="perpMax"/> &gt; 0 なら、<paramref name="origin"/> からの奥行(<paramref name="perpDir"/>)が
    /// ±perpMax を超える頂点も落とす(同じ高さに腰壁の底と基壇の天端が並ぶ部材のため)。</summary>
    public static void FaceSpan(GameObject go, Vector2 dir, float yLo, float yHi, out float mn, out float mx,
                                Vector2 perpDir = default(Vector2), Vector2 origin = default(Vector2), float perpMax = 0f)
    {
        mn = float.MaxValue; mx = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>();
            if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices)
            {
                var wv = l2w.MultiplyPoint3x4(v);
                if (wv.y < yLo || wv.y > yHi) continue;
                if (perpMax > 0f)
                {
                    float d = (wv.x - origin.x) * perpDir.x + (wv.z - origin.y) * perpDir.y;
                    if (Mathf.Abs(d) > perpMax) continue;
                }
                float t = wv.x * dir.x + wv.z * dir.y;
                if (t < mn) mn = t; if (t > mx) mx = t;
            }
        }
    }

    /// <summary>駒の**実メッシュ**(見えている物だけ)を走り方向 <paramref name="dir"/>(xz)へ投影した伸び[m]。
    /// ⛔ 外接箱の x/z の大きい方で代用しない — 斜めのグリッドでは箱が膨らむ。
    /// ⛔ **躯体の面**を測る用途に使わない — 基壇・軒・出格子が混ざる。そちらは <see cref="FaceSpan"/>(高さの帯)。
    /// ⛔ 見えないメッシュは数えない(冠木門のプレハブには Renderer の無い/切ってある駒が入っていて、
    /// 素で走ると 1.17m の門が 2.38m と出て開口が広がる。2026-09-06)。</summary>
    public static float ProjSpan(GameObject go, Vector2 dir)
    {
        float mn, mx; FaceSpan(go, dir, float.MinValue, float.MaxValue, out mn, out mx);
        return mx > mn ? mx - mn : 0f;
    }

    /// <summary>駒の**壁体**を、駒の局所軸 <paramref name="localAxis"/> へ投影した伸び[m](世界の尺度)。無ければ 0。
    /// 候補は <see cref="EdgeCandidates"/>(局所XZの凸包・EDO-0383)。</summary>
    public static float LocalSpan(Transform tr, Vector3 localAxis)
    {
        Vector3 ax = tr.rotation * localAxis;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in EdgeCandidates(tr)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
        return mx > mn ? mx - mn : 0f;
    }

    /// <summary><see cref="FaceSpan"/> の片側。<paramref name="maxSide"/> なら dir の正の側の面。無ければ NaN。</summary>
    public static float Face(GameObject go, Vector2 dir, float yLo, float yHi, bool maxSide,
                             Vector2 perpDir = default(Vector2), Vector2 origin = default(Vector2), float perpMax = 0f)
    {
        float mn, mx; FaceSpan(go, dir, yLo, yHi, out mn, out mx, perpDir, origin, perpMax);
        if (mx < mn) return float.NaN;
        return maxSide ? mx : mn;
    }

    /// <summary>線(点 <paramref name="a"/>・外向き法線 <paramref name="n"/>)からの、帯内の頂点の**最大の張り出し**[m]
    /// (= その駒の外面の位置。負なら線より内)。頂点が無ければ NaN。岡部 `FaceOut` に帯を足した物。
    /// <paramref name="pick"/> があれば、それが true のメッシュだけで測る(壁面だけを名指しする用。null なら全部)。</summary>
    public static float FaceOut(GameObject go, Vector2 a, Vector2 n, float yLo, float yHi,
                                Predicate<MeshFilter> pick = null)
    {
        float best = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>();
            if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (pick != null && !pick(mf)) continue;      // 名指しした面のメッシュだけで測る(岡部の壁面名)
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices)
            {
                var w = l2w.MultiplyPoint3x4(v);
                if (w.y < yLo || w.y > yHi) continue;
                float d = (w.x - a.x) * n.x + (w.z - a.y) * n.y;
                if (d > best) best = d;
            }
        }
        return best == float.MinValue ? float.NaN : best;
    }

    /// <summary>外面(<see cref="FaceOut"/>)が <paramref name="target"/> へ来るよう、法線 <paramref name="n"/> 方向に
    /// 平行移動する。返り値 = 移動量[m](測れなければ NaN)。犬走り合わせ(target = −0.30)や
    /// 番所の張り出し(target = +protrude)に使う。⛔ 定数で寄せない — 部材を替えた瞬間に破れる。</summary>
    public static float AlignFace(GameObject go, Vector2 a, Vector2 n, float target, float yLo, float yHi,
                                  Predicate<MeshFilter> pick = null)
    {
        float f = FaceOut(go, a, n, yLo, yHi, pick);
        if (float.IsNaN(f)) return float.NaN;
        float shift = target - f;
        go.transform.position += new Vector3(n.x * shift, 0f, n.y * shift);
        return shift;
    }

    /// <summary>**突き付け。**可動側 <paramref name="mover"/> の面(帯で測る)を、走り方向 <paramref name="dir"/> 上の
    /// 相手の面の投影値 <paramref name="targetProj"/> へ寄せる。<paramref name="moverMaxSide"/> は
    /// 「mover の dir 正の側の面が相手に当たる」(相手は dir の先にある)。
    /// <paramref name="gap"/> は指図 `joints[].gap`(+ = 隙間 / − = 差し込み)。返り値 = 移動量[m](測れなければ NaN)。
    /// ⭐ 使い方: 固定側を置く → 固定側の面を <see cref="Face"/> で測る → 可動側を仮置き → Abut。
    /// 次の駒はこの駒の反対側の面を測って同じ手を繰り返す(連鎖)。</summary>
    public static float Abut(GameObject mover, Vector2 dir, float yLo, float yHi, bool moverMaxSide, float targetProj,
                             float gap = 0f, Vector2 perpDir = default(Vector2), Vector2 origin = default(Vector2), float perpMax = 0f)
    {
        float f = Face(mover, dir, yLo, yHi, moverMaxSide, perpDir, origin, perpMax);
        if (float.IsNaN(f)) return float.NaN;
        float want = moverMaxSide ? targetProj - gap : targetProj + gap;
        float shift = want - f;
        mover.transform.position += new Vector3(dir.x * shift, 0f, dir.y * shift);
        return shift;
    }

    /// <summary>**駒の端を目標へ伸縮させる**(敷設の最後の一手。⛔ 事後修正に使わない)。
    /// 世界軸 <paramref name="ax"/> に沿う駒の壁体の端(<paramref name="sgn"/> の側)が <paramref name="target"/>
    /// (ax への投影値)へ来るよう、ax に最も近い局所軸で localScale を掛け、**伸ばした後に実測して**平行移動する
    /// (ピボットが中心とは限らない)。<paramref name="pair"/>(練塀の裏の駒)があれば同じ係数・同じ移動量。
    /// 返り値 = 伸ばした量[m](負 = 縮めた。測れなければ NaN)。上限は呼び出し側が決める。
    /// 候補は <see cref="EdgeCandidates"/>(局所XZの凸包・EDO-0383)。</summary>
    public static float StretchEnd(Transform piece, Transform pair, Vector3 ax, float sgn, float target)
    {
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in EdgeCandidates(piece)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
        if (mx < mn) return float.NaN;
        float len = mx - mn; if (len < 0.2f) return float.NaN;
        float near = sgn >= 0 ? mx : mn;
        float gap = sgn >= 0 ? target - near : near - target;      // 正 = 伸ばす
        float k = (len + gap) / len; if (k <= 0.05f) return float.NaN;
        float ax_x = Mathf.Abs(Vector3.Dot(piece.rotation * Vector3.right, ax));
        float ax_z = Mathf.Abs(Vector3.Dot(piece.rotation * Vector3.forward, ax));
        bool useX = ax_x >= ax_z;
        var ls = piece.localScale;
        piece.localScale = useX ? new Vector3(ls.x * k, ls.y, ls.z) : new Vector3(ls.x, ls.y, ls.z * k);
        float after = EdgeAlong(piece, ax, sgn);
        Vector3 delta = ax * (target - after);
        piece.position += delta;
        if (pair != null)
        {
            var lsb = pair.localScale;
            pair.localScale = useX ? new Vector3(lsb.x * k, lsb.y, lsb.z) : new Vector3(lsb.x, lsb.y, lsb.z * k);
            pair.position += delta;
        }
        return gap;
    }

    /// <summary>ハイトマップの**格子点**の世界座標と高さ。⛔ `Ground`(双一次)は格子の間で縁の擦り付けを拾い
    /// 0.1m が 2m に化ける(岡部 GradeQA)— 面の高さは格子点で測る。</summary>
    public static float GroundGrid(float x, float z)
    {
        var t = T(); var td = t.terrainData; int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        int ix = Mathf.Clamp(Mathf.RoundToInt((x - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        int iz = Mathf.Clamp(Mathf.RoundToInt((z - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        return td.GetHeight(ix, iz) + tp.y;
    }

    /// <summary>多角形(世界 xz)の内側、縁から <paramref name="edgeMargin"/> 以上離れたハイトマップ格子点の高さの**中央値**。
    /// 造成後の段の面をそのまま据え付け高に採るための物(CLAUDE.md 規則3「面の高さは地形が決める」)。
    /// <paramref name="spread"/> = 最大−最小、<paramref name="n"/> = 標本数。⛔ 標本が無ければ例外(黙って 0 を返さない)。
    /// ⚠ 地形を書く Stage の**後**に呼ぶ(設計面 `DesignY` は冪等性のため live terrain を読まない — 読んでよいのは
    /// 地形を書かない Stage だけ)。</summary>
    public static float PadY(Vector2[] polyWorld, float edgeMargin, out float spread, out int n)
    {
        var t = T(); var td = t.terrainData; int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in polyWorld) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        int z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int z1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        var hs = new List<float>();
        for (int iz = z0; iz <= z1; iz++)
            for (int ix = x0; ix <= x1; ix++)
            {
                var p = new Vector2(tp.x + ix * ts.x / (hres - 1), tp.z + iz * ts.z / (hres - 1));
                if (!EdoGeom.PIP(polyWorld, p)) continue;
                if (edgeMargin > 0f && EdoGeom.DistToPolyEdge(polyWorld, p) < edgeMargin) continue;
                hs.Add(td.GetHeight(ix, iz) + tp.y);
            }
        n = hs.Count;
        if (n == 0) throw new Exception("PadY: 多角形の内側に格子点が無い(縁の控え " + edgeMargin + "m を狭めるか、多角形を確かめる)");
        hs.Sort();
        spread = hs[n - 1] - hs[0];
        return hs[n / 2];
    }

    /// <summary>点 <paramref name="at"/>(世界 xz)を xz で含む(<paramref name="radius"/> だけ広げた)石垣の駒の
    /// **天端の最大**[m]。<paramref name="stones"/> の下の見えている Renderer の bounds で測る。無ければ NaN。</summary>
    public static float CrestY(Transform stones, Vector2 at, float radius)
    {
        float crest = float.MinValue;
        foreach (var r in stones.GetComponentsInChildren<Renderer>())
        {
            if (!r.enabled) continue;
            var b = r.bounds;
            if (at.x < b.min.x - radius || at.x > b.max.x + radius || at.y < b.min.z - radius || at.y > b.max.z + radius) continue;
            if (b.max.y > crest) crest = b.max.y;
        }
        return crest == float.MinValue ? float.NaN : crest;
    }

    /// <summary>**二つの駒が実際に触れている箇所を測る。**<paramref name="dir"/> は
    /// 「<paramref name="a"/> を押し付ける向き」(a から b へ向かう向き)。返り値 = その取り合いの
    /// **最小の隙**[m](正 = 隙間 / 負 = めり込み / 0 = 接触)。<paramref name="at"/> = 触れている所の世界座標、
    /// <paramref name="count"/> = 最小から <paramref name="tol"/> 以内にある筋の数(**接触が複数か**の検め)。
    /// どちらかに測れる頂点が無ければ NaN。
    ///
    /// <para>⭐ **面ではなく、触れている所を測る。**dir に直交する面を <paramref name="cell"/> 角の筋に割り、
    /// **両方の駒がいる筋だけ**で「a の前面 − b の背面」を取り、その最小を触れている箇所とする。
    /// こうすると、①名指しした面の外(留め継ぎの先端・庇の裏・沓石の縁)で当たっていても捕まり、
    /// ②当たりが何筋あるか(1点当たりか、面で当たっているか)が分かる。
    /// ⛔ 外接箱どうしの差で測らない — 回った駒・斜めの駒で必ず外す。</para>
    ///
    /// <para>⛔ **接するのは地面とだけではない**(2026-09-21 施主指摘「何かと何かが接する場合は接触している
    /// 箇所を測ってほしい」)。部材どうし・屋根と塀・隅と塀・石と土台も同じで、**どこで触れるかは
    /// 部材の基準点からも名指しした面からも分からない** — 測る。</para></summary>
    public static float Contact(GameObject a, GameObject b, Vector3 dir, out Vector3 at, out int count,
                                float tol = 0.01f, float cell = 0.25f, int maxSamples = 4000, bool withRoof = true)
    {
        at = a.transform.position; count = 0;
        var pa = Body(a.transform, maxSamples, withRoof);
        var pb = Body(b.transform, maxSamples, withRoof);
        float c = ContactPts(pa, pb, dir, out Vector3 at2, out count, tol, cell);
        if (!float.IsNaN(c)) at = at2;
        return c;
    }

    /// <summary>**触れている箇所で突き付ける。**<paramref name="mover"/> を <paramref name="dir"/> へ動かし、
    /// <paramref name="other"/> との**実際の接触**(<see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>)が
    /// <paramref name="gap"/>(+ = 残す隙 / − = 差し込む量)になる所で止める。返り値 = 動かした量[m]
    /// (向き合っていなければ NaN)。<paramref name="at"/> と <paramref name="count"/> は動かした後の接触の箇所と筋数。
    ///
    /// <para>⭐ 帯と投影で面を測る <see cref="Abut(GameObject,Vector2,float,float,bool,float,float,Vector2,Vector2,float)"/> と違い、
    /// **相手の駒そのもの**を相手に取る。名指しした面の外で当たっていればそこで止まるので、
    /// 「面は合っているのに軒が刺さっている」が起きない。</para></summary>
    public static float Abut(GameObject mover, GameObject other, Vector3 dir, float gap, out Vector3 at, out int count,
                             float cell = 0.25f, int maxSamples = 4000, bool withRoof = true)
    {
        float c = Contact(mover, other, dir, out at, out count, 0.01f, cell, maxSamples, withRoof);
        if (float.IsNaN(c)) return float.NaN;
        float shift = c - gap;                                   // 隙が gap になるまで dir へ進める
        mover.transform.position += dir.normalized * shift;
        Contact(mover, other, dir, out at, out count, 0.01f, cell, maxSamples, withRoof);
        return shift;
    }

    /// <summary>**地面と触れている箇所を測る。**(相手が地形のときの <see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>。)
    /// 駒の実メッシュの全頂点について「頂点の高さ − **その真下の地表**」を取り、最小の物が触れている箇所。
    ///
    /// <para>⭐ **地表は <see cref="Ground"/>(描かれている面)で引く。⛔ <see cref="GroundGrid"/>(最寄りの格子点)で引かない。**
    /// 格子は 2.0 m/px なので、最寄り点へ丸めると**斜面では ±(1m × 勾配)** の嘘が乗る。2026-09-21 松江松平の実測:
    /// 滝見の石段(勾配 1:2.5)が格子では 埋 1.576m・地表では 0.850m と出て **12駒が嘘で不合格**になり、
    /// 逆に岩屋の天井石は格子では 0.148m(合格に見える)・地表では **浮き 1.083m** で **嘘で合格**していた。
    /// 接地は「駒が実際に載っている面」との差であって、面の設計高(`PadY` / `GroundGrid` の役目)ではない。</para>
    ///
    /// 返り値 = その隙[m](正=浮き・負=埋没・0=接触)。<paramref name="at"/> = 触れている所の世界座標、
    /// <paramref name="count"/> = 最小から <paramref name="tol"/> 以内にある頂点の数(**接触が複数か**の検め)。
    /// 頂点が無ければ NaN。
    ///
    /// <para>⚠ <paramref name="maxSamples"/> は頂点の間引きの上限。**1 頂点につき地形を 1 回引く**ので、
    /// 79 区画を一度に建てる類型の車線では 600〜800 に絞る(既定 4000 は一邸を精密に据えるとき)。
    /// ⛔ 間引きすぎると接地の頂点そのものを落とす — 留め継ぎの隅部材のような疎な先端は 999999 を渡す。</para>
    ///
    /// <para>⛔ **触れる所は「底(bounds.min.y)」ではない。**斜面では上手側の頂点が先に着き、据え面のある石はその縁が、
    /// 木は根張りの端が着く。底の一点で据えると、着くべき所が浮くか埋まる。
    /// ⛔ **相手は地面だけではない** — 部材どうしの取り合いは <see cref="Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/> で測る
    /// (2026-09-21 施主指摘)。⛔ **部材の基準点(ピボット・原点・
    /// bounds の中心)で位置を決めない。絶対に。**(2026-09-20 施主指摘「実物の底や地面では漏れる。接地箇所を測れ」)</para></summary>
    public static float Contact(GameObject go, out Vector3 at, out int count, float tol = 0.01f, int maxSamples = 4000)
    {
        var pts = GroundCandidates(go.transform, maxSamples);
        float best = float.NaN; at = go.transform.position; count = 0;
        if (pts.Count == 0) return best;
        var probe = Probe();                       // ⭐ 掴みは駒ごとに一つ(⛔ 頂点ごとに Ground を呼ばない)
        var cs = new float[pts.Count];
        for (int i = 0; i < pts.Count; i++)
        {
            var p = pts[i];
            float c = p.y - probe.At(p.x, p.z); cs[i] = c;
            if (float.IsNaN(best) || c < best) { best = c; at = p; }
        }
        if (float.IsNaN(best)) return best;
        for (int i = 0; i < cs.Length; i++) if (cs[i] - best <= tol) count++;
        return best;
    }

    /// <summary>床下の開きの合否閾値[m](縁の下 0.45m + 規則3 の系統差 ±0.25m = 0.70m。2026-09-22 §4.4)。
    /// ⭐ ビルダーの合否は検査(Inspect の浮きの閾値)と同じ数にする — 通したのに赤にしない。</summary>
    public const float UNDERFLOOR_MAX = 0.70f;

    /// <summary>**床下の開き[m]。**駒の接地候補点のうち、地面から最も離れた点(浮きの最悪。埋没側は 0)。
    /// <para>⛔ <see cref="Contact(GameObject,out Vector3,out int,float,int)"/> が返す**最小**(=据えるための
    /// 最寄りの接地点)と混同しない。<see cref="SeatOnGround"/> は最寄りの1点が触れる高さへ据えるので、
    /// その点が着いていても、足元の地形が傾いていれば駒の反対側の隅は大きく浮く。それが床下の開き
    /// (2026-09-22 施主指摘 EDO-0370: 松平大和守 B4_Typ_Umaya は Contact=0.00m(隅が接地)と出たが、
    /// 対角の隅は実測 6.59m 浮いていた)。</para>
    /// <para>⭐ **棟種を問わない**(規則19「検査の文言と実装の集合を突き合わせる」)。御殿の棟・
    /// 付属屋(蔵・厩・米蔵)・長屋・門、床を持つ駒ならどれでもこの一つの関数で測る。</para></summary>
    public static float UnderfloorGap(GameObject go, out Vector3 at, int maxSamples = 4000)
    {
        var pts = GroundCandidates(go.transform, maxSamples);
        at = go.transform.position;
        if (pts.Count == 0) return float.NaN;
        var probe = Probe();
        float worst = 0f;
        foreach (var p in pts)
        {
            float c = p.y - probe.At(p.x, p.z);
            if (c > worst) { worst = c; at = p; }
        }
        return worst;
    }

    /// <summary>複数駒の床下の開きの最悪[m]と、その駒名。<see cref="UnderfloorGap(GameObject,out Vector3,int)"/> を
    /// 駒ごとに呼ぶだけ — 御殿の棟の並びでも、付属屋・長屋・門の並びでも同じに使える。</summary>
    public static float UnderfloorGap(IEnumerable<GameObject> pieces, out string worstName, int maxSamples = 4000)
    {
        float worst = 0f; worstName = "";
        foreach (var g in pieces)
        {
            Vector3 at;
            float d = UnderfloorGap(g, out at, maxSamples);
            if (float.IsNaN(d)) continue;
            if (d > worst) { worst = d; worstName = g.name; }
        }
        return worst;
    }

    /// <summary>**地面に据える。**<see cref="Contact(GameObject,out Vector3,out int,float,int)"/> で測った
    /// **地面と触れる箇所**が地形(格子点)に着く高さへ動かし、
    /// <paramref name="sink"/> だけ沈める。返り値 = 動かした量[m]。測れる頂点が無ければ例外(黙って置かない)。
    ///
    /// <para>⛔ **部材の基準点(ピボット)を信用して座標へ置かない。**ピボットの位置は部材ごとに違う
    /// (床 / 軒先 / 小口 / 中心 / 天端)。座標へ直に置くと、メッシュがピボットより下へ伸びている部材は
    /// その分だけ地中へ潜り、上へ伸びている部材は浮く。⚠ 2026-09-20 松江松平: 下草を「設計面へピボットを置く」
    /// だけで据えていたため、実メッシュの底が地面から **1.90m** 下にあった(葉は地表に見えているので
    /// レンダでは気づけない)。景石も沈める量を 0.34m の決め打ちにしていた。</para>
    ///
    /// <para>⚠ <paramref name="sink"/> は**意図して埋める量**(景石の 1/3 埋め・下草の根元)。
    /// ⛔ 部材のピボットのずれを吸わせる目的で使わない — それは測って消す物で、決め打ちで隠す物ではない。</para></summary>
    public static float SeatOnGround(GameObject go, float sink = 0f, int maxSamples = 4000)
    {
        float c = Contact(go, out _, out _, 0.01f, maxSamples);
        if (float.IsNaN(c)) throw new System.InvalidOperationException($"SeatOnGround: {go.name} に測れる頂点が無い(MeshFilter 無し・全て屋根名・非表示)");
        float dy = -sink - c;
        go.transform.position += new Vector3(0f, dy, 0f);
        return dy;
    }

    /// <summary>**丈の <paramref name="fraction"/> だけ埋めて据える。**景石の「1/3 埋め」のような、
    /// 部材の大きさに比例して沈める据え方。丈は実メッシュの高さから測るので、
    /// 個体差のある石をスケールで散らしても埋まり方が揃う。返り値 = 埋めた量[m]。
    /// ⛔ 決め打ちの沈め量(0.34m など)を全個体へ当てない — 大きい石は浮き、小さい石は沈む。</summary>
    public static float SeatBuried(GameObject go, float fraction, int maxSamples = 4000)
    {
        var b = RB(go);
        float h = b.size.y;
        float sink = h * Mathf.Clamp01(fraction);
        SeatOnGround(go, sink, maxSamples);
        return sink;
    }

    /// <summary>駒の底を、その真下の石垣の天端(<see cref="CrestY"/>)から <paramref name="sink"/> だけ沈めた高さに据える。
    /// 石垣が無ければ動かさず false(呼び出し側は設計の座で据えて「石垣なし」と報告する)。
    /// ⭐ 天端 = 指図の seat のはずだが、**測って据えれば** Stage3 や指図の seat が動いても囲いが黙って浮かない。</summary>
    public static bool SeatOnCrest(GameObject go, Transform stones, float sink, out float crest)
    {
        crest = CrestY(stones, new Vector2(go.transform.position.x, go.transform.position.z), 0.5f);
        if (float.IsNaN(crest)) return false;
        SeatBottom(go, crest - sink);
        return true;
    }

    /// <summary>**段(石段)の一連を、地表の落ち際へ合わせて走り方向に滑らせる。**剛体のまま
    /// <paramref name="up"/> へ動かし、各段の天端 <paramref name="treadTop"/> と**その段の下の地表**との差の
    /// 最悪値が最小になる寄せ量[m]を返す(± は <paramref name="up"/> 向き)。<paramref name="treadS"/> は
    /// <paramref name="foot"/> から測った各段の弧長。同じ悪さなら**動かさない方**を採る。
    ///
    /// <para>⛔ **指図の `pos` を座標として信じない。**造成した段の落ち際は擦り付けで 2〜4.5m に広がるのに、
    /// 段の走りは 1〜1.5m しかない。2026-09-21 松江松平の実測: 東小門の段(走り 1.35m・落差 0.9m)は
    /// 落ち際から 1.75m 内へ外れ、**3段とも平場 27.00 の下に丸ごと埋まっていた**(天端 −0.601m)。
    /// 表門の段も 0.28m ずれていた。⇒ 段の**位置は地表から解く従属値**。
    /// ⚠ 段数・落差・幅・向きは指図の意図なので動かさない — 動かすのは走りに沿った位置だけ。</para>
    ///
    /// <para>⚠ 両端を地形から取っている段(`kind: 庭の段`)には要らない — すでに従属値で解けている。
    /// 要るのは**足元/天端を literal(門の敷居・面の設計高)で持つ段**。</para></summary>
    /// <param name="accept">この差[m]までなら**動かさない**。段の蹴上を渡す — 天端が一蹴上ぶん以内の
    /// 沈み/浮きなら段は段として読めるので、位置を解き直す理由がない。⛔ 0 を渡すと「よりましな所」を
    /// 求めて段が何 m でも歩き出す(2026-09-21: 差 0.153m の一枚段が 1.10m も動いた)。</param>
    public static float FitRunAlongAxis(Vector2 foot, Vector2 up, float[] treadS, float[] treadTop,
                                        float searchHalf, float step, float accept,
                                        out float devBefore, out float devAfter)
    {
        if (treadS == null || treadTop == null || treadS.Length != treadTop.Length || treadS.Length == 0)
            throw new Exception("FitRunAlongAxis: 段の弧長と天端の数が合わない");
        up = up.normalized;
        if (step <= 1e-4f) step = 0.05f;
        devBefore = RunDev(foot, up, treadS, treadTop, 0f);
        devAfter = devBefore;
        if (devBefore <= accept) return 0f;               // 段として読める — 動かさない
        float bestDev = devBefore;
        for (float d = -searchHalf; d <= searchHalf + 1e-4f; d += step)
        {
            float dv = RunDev(foot, up, treadS, treadTop, d);
            if (dv < bestDev - 1e-4f) bestDev = dv;
        }
        if (bestDev >= devBefore - 1e-4f) return 0f;
        // 同じくらい良い寄せ方が幅を持つので、**いちばん動かさずに済む**位置を採る。
        // ⛔ ここに `accept` を混ぜない — 一度動かすと決めた段は**いちばん良く納まる所**まで寄せる
        //   (混ぜると許容ぎりぎり 0.285m で止まり、最下段がほとんど見えないまま残る)
        float tol = bestDev + 0.02f;
        float best = 0f; bool found = false;
        for (float d = -searchHalf; d <= searchHalf + 1e-4f; d += step)
        {
            if (RunDev(foot, up, treadS, treadTop, d) > tol) continue;
            if (!found || Mathf.Abs(d) < Mathf.Abs(best)) { best = d; found = true; }
        }
        if (!found) return 0f;
        devAfter = RunDev(foot, up, treadS, treadTop, best);
        return best;
    }

    /// <summary>各段の天端と地表の差の最悪値(<see cref="FitRunAlongAxis"/> の目的関数)。</summary>
    static float RunDev(Vector2 foot, Vector2 up, float[] s, float[] top, float d)
    {
        float w = 0f;
        for (int i = 0; i < s.Length; i++)
        {
            Vector2 p = foot + up * (s[i] + d);
            w = Mathf.Max(w, Mathf.Abs(Ground(p.x, p.y) - top[i]));
        }
        return w;
    }

    /// <summary>**壁体を区画の多角形の内へ収める。**置いた駒の実メッシュ(屋根を除く)が
    /// <paramref name="poly"/> の外へ出ていたら、走り <paramref name="runDir"/> に沿って
    /// **最小量だけ**引いて収める。返り値 = 動かした量[m](+ は runDir 向き・0 = 元から内側)。
    /// <paramref name="maxPull"/> まで引いても収まらなければ**動かさず NaN**(呼び出し側が「置かない」を選べる)。
    /// <paramref name="before"/> = 動かす前に区画の外へ出ていた最大量[m]。
    ///
    /// <para>⛔ **辺の線で測らない** — 奥行のある駒は角で隣の辺を跨ぐ(`docs/oki-kata.md` §4)。
    /// 2026-09-21 松江松平の実測: 石垣の留め継ぎの腕 3 駒が、自分の辺には載っているのに
    /// 頂点の先で隣の辺を 0.0397 / 0.0388 / 0.0016m 跨いでいた(走りに沿って 0.04m 引けば収まる)。
    /// 走りに沿って引くので**犬走りの控え(面に直交する量)は動かない**し、駒どうしは 0.20m 以上
    /// 重ねてあるので隙も開かない。</para>
    ///
    /// <para>⚠ 長屋のような**一体で端の動かせない駒**には使わない(`NagayaRun.keepInside` のように
    /// 「出る駒は置かない」を選ぶ)。これは重ねて並べる駒(石垣・塀)のための物。</para>
    ///
    /// <para>候補は <see cref="EdgeCandidates"/>(局所XZの凸包・EDO-0383)— 以前の一様な添字間引きは
    /// 区画の外へ最も出ている頂点を間引きで落とすことがあり、区域侵犯を見逃す方向で危険だった。</para></summary>
    public static float KeepInsidePoly(GameObject go, Vector2[] poly, Vector2 runDir, float maxPull,
                                       out float before, float step = 0.01f)
    {
        var pts = EdgeCandidates(go.transform);
        before = OutsideBy(pts, poly, Vector2.zero);
        if (before <= 0f) return 0f;
        runDir = runDir.normalized;
        for (float d = step; d <= maxPull + 1e-4f; d += step)
        {
            if (OutsideBy(pts, poly, -runDir * d) <= 0f)
            { go.transform.position += new Vector3(-runDir.x * d, 0f, -runDir.y * d); return -d; }
            if (OutsideBy(pts, poly, runDir * d) <= 0f)
            { go.transform.position += new Vector3(runDir.x * d, 0f, runDir.y * d); return d; }
        }
        return float.NaN;
    }

    /// <summary>点群を <paramref name="off"/> だけずらしたとき、多角形の外へ出る最大距離[m](0 = 全部内側)。</summary>
    static float OutsideBy(List<Vector3> pts, Vector2[] poly, Vector2 off)
    {
        float worst = 0f;
        foreach (var p in pts)
        {
            var q = new Vector2(p.x + off.x, p.z + off.y);
            if (EdoGeom.PIP(poly, q)) continue;
            float d = EdoGeom.DistToPolyEdge(poly, q);
            if (d > worst) worst = d;
        }
        return worst;
    }

    /// <summary>**足あとの下の地形**(格子点)の最小と最大。中心 <paramref name="c"/>・
    /// 軸 <paramref name="axisA"/>/<paramref name="axisB"/>(単位ベクトル)の半寸 <paramref name="halfA"/>/
    /// <paramref name="halfB"/> の矩形を <paramref name="n"/>×<paramref name="n"/> で標本する。
    /// ⭐ **据える前に「その駒が本当にその面へ載るか」を検める道具。**段の際では設計の段の線と
    /// 造成した地形の段が格子1マスぶんずれるので、線だけで寄せると駒の片側が下の面の上に残る
    /// (松江松平の勝手井戸 2026-09-21: 設計の線 v=29 に対し地形の段は v≒29.6・片側が 0.24m 浮いた)。</summary>
    public static void GroundUnder(Vector2 c, Vector2 axisA, float halfA, Vector2 axisB, float halfB,
                                   int n, out float mn, out float mx)
    {
        mn = float.MaxValue; mx = float.MinValue;
        n = Mathf.Max(2, n);
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
            {
                float a = Mathf.Lerp(-halfA, halfA, i / (float)(n - 1));
                float b = Mathf.Lerp(-halfB, halfB, j / (float)(n - 1));
                Vector2 p = c + axisA * a + axisB * b;
                float g = GroundGrid(p.x, p.y);
                if (g < mn) mn = g; if (g > mx) mx = g;
            }
    }

    // ============================================================ 隅の駒と塀の取り合い(2026-09-21)
    // ⭐ **斜めに据わる駒(隅櫓・門構え・番所)の脇で塀の run をどこで止めるか**を実メッシュから解く道具。
    //   ⛔ **駒の全頂点を辺の向きへ射影して端を採らない。** 斜めに据わった駒は**回廊の外**
    //   (区画の内側へ深く入った所)の頂点が極値になるので、そこへ塀の端を合わせると
    //   塀と駒の間に口が残る — 松江松平の隅櫓 Y_NE で **1.13m**(2026-09-21 実測)。
    //   ⭕ **塀が通る回廊**(辺の線からの奥行の範囲 × 塀の高さの帯)に居る頂点だけを射影する。
    //   → docs/oki-kata.md §2「可動側は前の相手と触れる所まで寄せる」/ §3「触れている箇所を測る」

    /// <summary>プレハブ資産を <paramref name="pos"/> / <paramref name="yaw"/> に据えたと仮定したときの
    /// 世界頂点。**実体化しない**ので、その駒を建てるより前の Stage(囲いの run)でも測れる。
    /// <paramref name="withRoof"/> = false なら屋根系のメッシュ(<see cref="IsRoofName"/>)を落とす。</summary>
    public static List<Vector3> BodyAt(string prefabPath, Vector3 pos, float yaw, bool withRoof = true)
    {
        var L = new List<Vector3>();
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (asset == null) return L;
        var pose = Matrix4x4.TRS(pos, Quaternion.Euler(0f, yaw, 0f), Vector3.one)
                 * asset.transform.worldToLocalMatrix;
        foreach (var mf in asset.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            if (!withRoof && IsRoofName(mf.name)) continue;
            var m = pose * mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            for (int i = 0; i < vs.Length; i++) L.Add(m.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    /// <summary>**部材を据えたときの、高さ <paramref name="y"/> の水平断面**(世界座標・実体化しない)。
    /// メッシュの**三角形**を水平面で切った交点を返す。
    /// <para>⭐ **柱で立つ駒は「帯の頂点」では測れない**(2026-09-23・EDO-0398 で二度目)。箱で作った柱は
    /// 頂点が上下の端にしかないので、腰の高さの帯には頂点が一つも入らない ── 山王の勝手口では、帯に
    /// 入ったのは柱の間の貫と**礎石の天端**だけで、そこから採った脇柱の位置が実際の柱より 0.105m 外に出た
    /// (礎石は柱より大きい)。⇒ **断面(三角形と水平面の交わり)で測れば、頂点の無い高さでも柱の実形が出る。**
    /// 同じ穴は <see cref="ModuleMeasure"/>/<see cref="FaceOut"/> の帯にもある(`docs/oki-kata.md` §3)。</para></summary>
    public static List<Vector3> SectionAt(string prefabPath, Vector3 pos, float yaw, float y, bool withRoof = true)
    {
        var L = new List<Vector3>();
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (asset == null) return L;
        var pose = Matrix4x4.TRS(pos, Quaternion.Euler(0f, yaw, 0f), Vector3.one)
                 * asset.transform.worldToLocalMatrix;
        foreach (var mf in asset.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            if (!withRoof && IsRoofName(mf.name)) continue;
            var m = pose * mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
            var tri = mf.sharedMesh.triangles;
            for (int i = 0; i + 2 < tri.Length; i += 3)
                for (int e = 0; e < 3; e++)
                {
                    Vector3 p = w[tri[i + e]], q = w[tri[i + (e + 1) % 3]];
                    if ((p.y - y) * (q.y - y) > 0f) continue;
                    float dy = q.y - p.y;
                    if (Mathf.Abs(dy) < 1e-7f) continue;
                    L.Add(Vector3.Lerp(p, q, (y - p.y) / dy));
                }
        }
        return L;
    }

    /// <summary>材やサブメッシュの名で屋根を見分ける。<see cref="IsRoofName"/>(和名)に
    /// 英名の roof / 屋根 を足したもの。⛔ <see cref="IsRoofName"/> 自体は広げない —
    /// あれは `Body()` が壁体を選ぶのに使っていて、広げると他邸の実測値が黙って動く。</summary>
    public static bool IsRoofLabel(string name)
    {
        if (string.IsNullOrEmpty(name)) return false;
        string n = name.ToLower();
        return IsRoofName(n) || n.Contains("roof") || n.Contains("屋根");
    }

    /// <summary>**一体メッシュの駒の「一層目の躯体」**の世界頂点(実体化しない)。
    /// <para>⭐ 一体で焼いた部材(隅櫓・門・祠)は屋根も壁も**ひとつの MeshFilter** に入っていて、
    /// メッシュの名では屋根を落とせない。⇒ **材(サブメッシュ)の名**で屋根を見分け、
    /// **屋根の最も低い点より下に居る頂点**だけを返す。これが「軒より下の躯体」。</para>
    /// <para>⛔ 高さの帯を数で決め打ちしない(`座+2.0m` のような数)— 屋根の高さは部材が決める。
    /// 松江松平の隅櫓 Y_NE: 屋根の最下点 32.67 ⇒ 一層目の躯体 = 板壁 Fence_B_01 + 漆喰壁
    /// Wall Exterior Defence(y29.40‥32.67)。⚠ 二層目の妻壁 `wall C`(33.11‥)と柱 `wood`(32.76‥)は
    /// **この上に居るので入らない** — 入れたいときは <see cref="BodyAt"/> を使う。</para>
    /// <para>屋根のサブメッシュが無ければ <see cref="BodyAt"/>(withRoof:false)と同じ物を返す。</para></summary>
    public static List<Vector3> BodyBelowRoofAt(string prefabPath, Vector3 pos, float yaw)
    {
        var L = new List<Vector3>();
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (asset == null) return L;
        var pose = Matrix4x4.TRS(pos, Quaternion.Euler(0f, yaw, 0f), Vector3.one)
                 * asset.transform.worldToLocalMatrix;
        float roofLo = float.MaxValue;
        var keep = new List<Vector3>();
        foreach (var mf in asset.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            var m = pose * mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            var W = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) W[i] = m.MultiplyPoint3x4(vs[i]);
            var mats = rr.sharedMaterials;
            bool meshIsRoof = IsRoofLabel(mf.gameObject.name) || IsRoofLabel(mf.sharedMesh.name);
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mat = s < mats.Length && mats[s] != null ? mats[s].name : "";
                bool isRoof = meshIsRoof || IsRoofLabel(mat);
                var tri = mf.sharedMesh.GetTriangles(s);
                for (int i = 0; i < tri.Length; i++)
                {
                    var w = W[tri[i]];
                    if (isRoof) { if (w.y < roofLo) roofLo = w.y; }
                    else keep.Add(w);
                }
            }
        }
        if (roofLo == float.MaxValue) return keep;               // 屋根が見分けられない = 壁体そのまま
        foreach (var w in keep) if (w.y < roofLo) L.Add(w);
        return L;
    }

    /// <summary>**一体メッシュの駒の「躯体」全部**(屋根の材を除いた**すべての材**)の世界頂点(実体化しない)。
    /// <para>⭐ <see cref="BodyBelowRoofAt"/> は「屋根の最下点より下」= **一層目だけ**を返すので、
    /// 二層・三層の櫓では**二層目の妻壁・柱が落ちる**。区域侵犯のように「躯体が線を越えないこと」を
    /// 解くときは**層を問わず躯体を数える**必要がある ⇒ こちらを使う。
    /// 松江松平の隅櫓 Y_NE(2026-09-21): `BodyBelowRoofAt` で一層目を収めたあと、二層目の妻壁
    /// `wall C` 0.292m・柱 `wood` 0.562m が区画線を越えたまま残っていた。</para>
    /// <para>数え方は材(サブメッシュ)の名 — <see cref="IsRoofLabel"/> に当たる材(roof / roof ornaments /
    /// yane / noki / taruki / mune / keta / 屋根)を**落とし**、残りを躯体とする。
    /// ⭐ **何を躯体と数えたか**は <paramref name="bodyParts"/> / <paramref name="roofParts"/> に
    /// 材の名で返る — ⛔ 「躯体」の中身を言わずに数だけ報告しない(指図の欄へ列挙するため)。</para>
    /// <para>⛔ 高さの帯で層を切り分けない(層の高さは部材が決める)。⛔ 軒の出を躯体に数えない
    /// (軒の張り出しは許容 — CLAUDE.md 規則・2026-09-21 施主裁定A)。</para></summary>
    public static List<Vector3> BodyExRoofAt(string prefabPath, Vector3 pos, float yaw,
                                             List<string> bodyParts = null, List<string> roofParts = null)
    {
        var L = new List<Vector3>();
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (asset == null) return L;
        var pose = Matrix4x4.TRS(pos, Quaternion.Euler(0f, yaw, 0f), Vector3.one)
                 * asset.transform.worldToLocalMatrix;
        foreach (var mf in asset.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            var m = pose * mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            var W = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) W[i] = m.MultiplyPoint3x4(vs[i]);
            var mats = rr.sharedMaterials;
            bool meshIsRoof = IsRoofLabel(mf.gameObject.name) || IsRoofLabel(mf.sharedMesh.name);
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mat = s < mats.Length && mats[s] != null ? mats[s].name : "";
                bool isRoof = meshIsRoof || IsRoofLabel(mat);
                string label = string.IsNullOrEmpty(mat) ? mf.gameObject.name : mat;
                if (isRoof) { if (roofParts != null && !roofParts.Contains(label)) roofParts.Add(label); continue; }
                if (bodyParts != null && !bodyParts.Contains(label)) bodyParts.Add(label);
                var tri = mf.sharedMesh.GetTriangles(s);
                for (int i = 0; i < tri.Length; i++) L.Add(W[tri[i]]);
            }
        }
        return L;
    }

    /// <summary>メッシュ内の頂点添字を局所 Y 昇順に並べ替えた添字表(メッシュ資産ごとに 1 度だけ作ってキャッシュ)。
    /// <see cref="BodyExRoof"/> の単一メッシュ間引きが使う下ごしらえ。</summary>
    static readonly Dictionary<Mesh, int[]> _yOrderCache = new Dictionary<Mesh, int[]>();
    static int[] YOrder(Mesh m)
    {
        int[] order;
        if (_yOrderCache.TryGetValue(m, out order)) return order;
        var vs = m.vertices;
        order = new int[vs.Length];
        for (int i = 0; i < order.Length; i++) order[i] = i;
        Array.Sort(order, (i, j) => vs[i].y.CompareTo(vs[j].y));
        _yOrderCache[m] = order;
        return order;
    }

    /// <summary><see cref="Body"/> 相当だが、**単一メッシュに焼かれた駒**(庫裏・墓地・鐘楼・山門など、
    /// Blender 側で屋根まで join した部材)も**材(サブメッシュ)の名**で屋根を見分けて落とす
    /// (<see cref="BodyExRoofAt"/> の、実体化済み Transform 版)。
    /// <para>⭐ 何を直したか(EDO-0358・2026-09-22): `Body(withRoof:false)` は駒の名前(<see cref="IsRoofName"/>)
    /// でしか屋根を見分けないので、庫裏(VK.SmallHouse)・墓地・鐘楼・山門は一枚メッシュ(または屋根の子が
    /// 篩の語に掛からない)で `Body(true)` と `Body(false)` の頂点数が同じだった。壁体だけを測るはずの判定
    /// (境域侵犯の `OutsideBy` / 寺社境内の壁体マージン `JExt`)が軒先込みの外形にかかり、軒の越境が
    /// 許容されず(裁定A)、狭い敷地で棟が入らない一因になっていた。</para>
    /// <para>⛔ <see cref="Body"/> 自体は広げない — 接地(<see cref="Contact"/>)や取り合いなど他の用途が
    /// 使っていて、篩を広げると他邸の実測値が黙って動く(<see cref="IsRoofLabel"/> の注記に同じ)。
    /// 壁体と軒を厳密に分けたい呼び出し側だけ、こちらへ切り替える。</para></summary>
    public static List<Vector3> BodyExRoof(Transform tr, int maxSamples = 900)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            // ⛔ 根の GameObject 名は使わない(Place() の呼び名で "mune" 等を誤検知する — PartName と同じ理由)。
            if (IsRoofLabel(PartName(tr, mf)) || IsRoofLabel(mf.sharedMesh.name)) continue;
            var l2w = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            var mats = rr.sharedMaterials;
            if (mf.sharedMesh.subMeshCount <= 1)
            {
                if (vs.Length <= maxSamples) { foreach (var v in vs) L.Add(l2w.MultiplyPoint3x4(v)); }
                else
                {
                    var order = YOrder(mf.sharedMesh);
                    int step = Mathf.Max(1, order.Length / Mathf.Max(1, maxSamples));
                    for (int i = 0; i < order.Length; i += step) L.Add(l2w.MultiplyPoint3x4(vs[order[i]]));
                }
                continue;
            }
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                string mat = s < mats.Length && mats[s] != null ? mats[s].name : "";
                if (IsRoofLabel(mat)) continue;
                var tri = mf.sharedMesh.GetTriangles(s);
                for (int i = 0; i < tri.Length; i++) L.Add(l2w.MultiplyPoint3x4(vs[tri[i]]));
            }
        }
        return L;
    }

    /// <summary>**塀の通り道(回廊)を、その駒がどこからどこまで塞いでいるか。**
    /// <paramref name="pts"/> の世界頂点のうち、辺 <paramref name="A"/>→<paramref name="B"/> の線からの奥行
    /// (<paramref name="perpDir"/> 方向で <paramref name="perpLo"/>‥<paramref name="perpHi"/>)と
    /// 高さ(<paramref name="yLo"/>‥<paramref name="yHi"/>)の**両方**に入る物だけを走り方向へ射影した区間。
    /// s は A からの距離[m]。回廊に頂点が無ければ false(= その辺では塞いでいない)。
    /// <para>⭕ 使い方: 塀の断面を <see cref="DobeiProfile"/> で実測 → 隅の駒の頂点を
    /// <see cref="BodyAt"/>(まだ建てていない)か <see cref="Body"/>(建ててある)で採る → ここへ渡す →
    /// **返った <paramref name="s0"/>/<paramref name="s1"/> が run の端そのもの**(塞いでいる所まで塀を通す)。</para>
    /// <para>⛔⛔ **返り値に犬走りを足し引きしない。**犬走りは「塀と郭(地面)の間」= **断面**の控えで、
    /// 「隅の駒と塀の間」= **走り方向**の話ではない。松江松平 2026-09-21: ここで 0.30 を引いて
    /// 隅櫓 Y_NE と袖塀の間に **0.300/0.299m の穴**を二つ開けた(普請検査が実測)。
    /// 走り方向は**触れるまで**寄せる — 閉じない案と浅く刺さる案が並んだら刺すほうを採る
    /// (メモリ `gate-wall-closure-rule`「隙間 > めり込み」)。同じ形は
    /// 岡部の隅部材・山王の楼門脇の透塀・土井の隅にも当たる。</para></summary>
    public static bool CorridorSpan(List<Vector3> pts, Vector2 A, Vector2 B, Vector2 perpDir,
                                    float perpLo, float perpHi, float yLo, float yHi,
                                    out float s0, out float s1)
    {
        Vector2 q0, q1;
        return CorridorJambs(pts, A, B, perpDir, perpLo, perpHi, yLo, yHi, out q0, out q1, out s0, out s1);
    }

    /// <summary>**回廊を塞ぐ駒の「塞ぎ始め・塞ぎ終わりの点」**(<see cref="CorridorSpan"/> の点版)。
    /// 同じ篩(回廊 × 高さの帯)を通した頂点のうち、走り方向の射影が**最小/最大になった頂点そのもの**を
    /// <paramref name="p0"/>/<paramref name="p1"/>(世界の xz)で返す。<paramref name="s0"/>/<paramref name="s1"/>
    /// はその射影(= <see cref="CorridorSpan"/> の返り値と同一)。
    /// <para>⭐ **射影だけを受け取ると横のずれが落ちる。**駒が走りに対して**傾いて・横へずれて**据わるとき
    /// (門・隅櫓)、走りの線の上で s へ端を取っても、駒の実体はそこに無い ── 2026-09-23 実測(EDO-0398):
    /// 山王の勝手口は走りと 39°・線から 0.45m 外に据わり、射影で端を取った柵の柱と門の実メッシュの間に
    /// **0.822m の口**が残っていた。⇒ **端は「射影が極値になった頂点の居場所」へ取る**(= 走りの向きに
    /// 光を当てたときの駒の影が始まる角 = 門の脇柱の角)。走りはそこで折れて門へ取り付く。</para></summary>
    public static bool CorridorJambs(List<Vector3> pts, Vector2 A, Vector2 B, Vector2 perpDir,
                                     float perpLo, float perpHi, float yLo, float yHi,
                                     out Vector2 p0, out Vector2 p1, out float s0, out float s1)
    {
        s0 = float.NaN; s1 = float.NaN; p0 = Vector2.zero; p1 = Vector2.zero;
        Vector2 d = (B - A).normalized;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var w in pts)
        {
            if (w.y < yLo || w.y > yHi) continue;
            float p = (w.x - A.x) * perpDir.x + (w.z - A.y) * perpDir.y;
            if (p < perpLo || p > perpHi) continue;
            float s = (w.x - A.x) * d.x + (w.z - A.y) * d.y;
            if (s < mn) { mn = s; p0 = new Vector2(w.x, w.z); }
            if (s > mx) { mx = s; p1 = new Vector2(w.x, w.z); }
        }
        if (mx < mn) return false;
        s0 = mn; s1 = mx; return true;
    }

    /// <summary>**口に建つ駒(門)の脇柱へ、囲いの run の終端を取り付ける点を測る。**
    /// 返るのは口の両側の取り付け点 <paramref name="j0"/>(A 側)/ <paramref name="j1"/>(B 側)の
    /// 世界 xz と、その走りへの射影 <paramref name="s0"/>/<paramref name="s1"/>(s は A からの距離[m])。
    /// 駒は**まだ建っていなくてよい**(資産から測る)ので、門より先に流れる囲いの Stage からも呼べる。
    /// <paramref name="how"/> には何で測ったかが返る(⛔ 黙って代用しない・規則7)。
    ///
    /// <para>⭐ **run の端は開口の縁に取る**(2026-09-19 施主裁定)。⛔ 算出物の seg の端(= 紙の上の
    /// 口の幅)をそのまま run の端にしない — 門は走りに対して**傾いて・ずれて**据わることがあり
    /// (山王の勝手口は 39°傾き・線から 0.45m 外)、その差がそのまま素通しの空隙になる
    /// (2026-09-22 実測: 口 2.909m に対し門の投影 1.992m ⇒ 南 0.457 / 北 0.460m が素通し)。
    /// ⛔ 門の芯と「口の幅(`monguchiKen`)」の引き算で出さない — 傾きと控えを落とす。</para>
    ///
    /// <para>⭐ **端は走りの線の上ではなく、門の実メッシュの角そのものへ取る**(2026-09-23・EDO-0398)。
    /// 射影 s だけを受け取ると**横のずれが落ちる** — 線上の s には門の実体が無く、柵の端の柱と門の間に
    /// **0.822m の口**が残った。走りはその角で折れて門へ取り付く。</para>
    ///
    /// <para>⭐ **測るのは頂点ではなく断面**(<see cref="SectionAt"/>)。箱で作った柱は頂点が上下の端にしか
    /// 無いので、腰の帯に入るのは貫と**礎石の天端**だけ ── そこから採った脇柱は実際の柱より 0.105m 外に
    /// 出て、閉じが 0.085m 足りなかった(2026-09-23 実測)。⇒ 囲いの丈の帯を 5 段に割って**各段の断面**を
    /// 採り、**いちばん内へ引っ込む段**(= どの高さにも隙が残らない位置)へ端を取る。礎石のように外へ
    /// 張り出す部分へは、そのぶん食い込む(めり込みは隙より良い)。</para>
    ///
    /// <para>⚠ <paramref name="perpHalf"/> は**控えの帯**。⛔ 塀の半厚を渡さない — 細い帯では傾いた門の
    /// 実体が1つも入らず「塞いでいない」と出て口が素通しで残る(2026-09-22 実測)。⇒ **その口の幅**を
    /// 渡す(帯は「この口に建つ駒か」を選ぶためだけの物)。</para>
    ///
    /// <para><paramref name="bite"/> は門へ**食い込ませる量**[m](閉じは「隙間 &gt; めり込み」──
    /// メモリ `gate-wall-closure-rule`)。呼び手は**その run の半厚**を実測して渡すこと ── 端の駒の木口は
    /// 走りに直角、門の脇柱の面は門の向きなので、角で合わせるだけだと半厚 × tan(食い違い角)の楔が残る。
    /// ⛔ 控え・犬走りを足し引きしない(<see cref="CorridorSpan"/> の註と同じ)。</para></summary>
    public static bool OpeningJambs(string prefabPath, Vector3 pos, float yaw,
                                    Vector2 A, Vector2 B, float perpHalf, float yLo, float yHi,
                                    float bite, out Vector2 j0, out Vector2 j1,
                                    out float s0, out float s1, out string how)
    {
        j0 = Vector2.zero; j1 = Vector2.zero; s0 = float.NaN; s1 = float.NaN; how = "";
        Vector2 d = (B - A);
        if (d.sqrMagnitude < 1e-8f) return false;
        d.Normalize();
        Vector2 nrm = new Vector2(-d.y, d.x);
        const int STEPS = 5;
        int used = 0;
        float lo = float.MinValue, hi = float.MaxValue;   // 内へいちばん引っ込む段を採る
        for (int k = 0; k < STEPS; k++)
        {
            float y = Mathf.Lerp(yLo, yHi, (k + 0.5f) / STEPS);
            var sec = SectionAt(prefabPath, pos, yaw, y, true);
            float mn = float.MaxValue, mx = float.MinValue;
            Vector2 pmn = Vector2.zero, pmx = Vector2.zero;
            foreach (var w in sec)
            {
                float p = (w.x - A.x) * nrm.x + (w.z - A.y) * nrm.y;
                if (p < -perpHalf || p > perpHalf) continue;
                float s = (w.x - A.x) * d.x + (w.z - A.y) * d.y;
                if (s < mn) { mn = s; pmn = new Vector2(w.x, w.z); }
                if (s > mx) { mx = s; pmx = new Vector2(w.x, w.z); }
            }
            if (mx < mn) continue;                        // この高さには駒の実体が無い
            used++;
            if (mn > lo) { lo = mn; j0 = pmn; }
            if (mx < hi) { hi = mx; j1 = pmx; }
        }
        if (used > 0) { s0 = lo; s1 = hi; how = "断面 " + used + "/" + STEPS + " 段"; }
        else
        {
            // 断面が一段も採れない(水平な板だけの駒など)。⛔ 黙って諦めない — 帯の頂点で測って報せる。
            var pts = BodyAt(prefabPath, pos, yaw, true);
            if (pts.Count == 0) return false;
            if (!CorridorJambs(pts, A, B, nrm, -perpHalf, perpHalf, yLo, yHi,
                               out j0, out j1, out s0, out s1)) return false;
            how = "⚠ 断面が採れず帯の頂点で代用";
        }
        // 食い込みは影の幅の 1/4 を超えない(門が細いときに両端が行き違うのを防ぐ)。
        float bt = Mathf.Max(0f, Mathf.Min(bite, (s1 - s0) * 0.25f));
        j0 += d * bt; j1 -= d * bt;
        return true;
    }

    /// <summary>**その辺に建てる練塀の断面を、駒を1枚仮に据えて実測する。**
    /// 返るのは辺の線からの奥行の範囲(<paramref name="perpDir"/> = <c>−outward</c> の向きで
    /// <paramref name="perpLo"/>‥<paramref name="perpHi"/>)と、高さの帯 <paramref name="yLo"/>‥<paramref name="yHi"/>。
    /// ⛔ 指図の厚み(`const.dobeiT`)や座の数で代用しない — <see cref="DobeiRun"/> は裏板を 0.20m 下げ、
    /// 底を座より 0.10m 下げて据えるので、紙の数と実寸は必ずずれる。仮置きした駒はこの場で消す。
    /// <para>⚠ <paramref name="outerAt"/> を渡すと、**実測した奥行の幅を保ったまま**外面がそこへ来るよう
    /// 断面を置き直す。囲いは据えたあと犬走り(外面 = 線から内へ 0.30m)へ寄るので、仮置きの駒の
    /// 位置をそのまま信じると回廊が 0.3〜0.4m ずれる(松江松平 2026-09-21 実測)。
    /// <paramref name="pad"/> は両側の余裕[m]。</para></summary>
    public static bool DobeiProfile(Vector2 A, Vector2 B, Vector2 outward, float seat,
                                    out Vector2 perpDir, out float perpLo, out float perpHi,
                                    out float yLo, out float yHi,
                                    float outerAt = float.NaN, float pad = 0f)
    {
        perpDir = -outward; perpLo = 0f; perpHi = 0f; yLo = 0f; yHi = 0f;
        var probe = new GameObject("__dobei_profile_probe__");
        try
        {
            Vector2 d = (B - A).normalized;
            var made = DobeiRun(probe.transform, A, A + d * 3f, outward, "probe", false, seat, Vector2.zero, -1);
            if (made.Count == 0) return false;
            float pmn = float.MaxValue, pmx = float.MinValue, ymn = float.MaxValue, ymx = float.MinValue;
            foreach (var g in made)
                foreach (var w in Body(g.transform, 999999, true))
                {
                    float p = (w.x - A.x) * perpDir.x + (w.z - A.y) * perpDir.y;
                    if (p < pmn) pmn = p; if (p > pmx) pmx = p;
                    if (w.y < ymn) ymn = w.y; if (w.y > ymx) ymx = w.y;
                }
            if (pmx < pmn) return false;
            if (!float.IsNaN(outerAt)) { pmx = outerAt + (pmx - pmn); pmn = outerAt; }
            perpLo = pmn - pad; perpHi = pmx + pad; yLo = ymn; yHi = ymx;
            return true;
        }
        finally { UnityEngine.Object.DestroyImmediate(probe); }
    }
}
