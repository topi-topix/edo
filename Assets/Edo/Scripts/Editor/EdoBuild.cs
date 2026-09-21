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

    /// <summary>アクティブな Terrain (最初の1枚)。無ければ例外。</summary>
    public static Terrain T()
    {
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy) return t;
        throw new Exception("no active terrain");
    }

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
        return n.Contains("yane") || n.Contains("noki") || n.Contains("taruki") || n.Contains("mune") || n.Contains("keta");
    }

    /// <summary>**壁体**(屋根・軒・垂木・棟・桁を除く、見えているメッシュ)の頂点を世界座標で。
    /// <paramref name="maxSamples"/> は一様な添字間引きの上限(既定 900・性能優先)。
    /// ⚠ 一様な間引きは極値を落とすことがある — 隅部材(単一メッシュ 1.6〜1.8 万頂点)は 999999 を渡して
    /// 間引かない(松江松平 2026-09-08: 留め継ぎの先端の疎な頂点が落ちて隙間を 0.46m と過大に出した)。</summary>
    /// <param name="withRoof">true なら屋根系のメッシュも含める。⭐ 屋根と屋根・軒と塀のように
    /// **屋根そのものが触れる取り合い**を測るときに使う(既定の false は壁の面を測るため)。</param>
    public static List<Vector3> Body(Transform tr, int maxSamples = 900, bool withRoof = false)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (!withRoof && IsRoofName(mf.name)) continue;
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            int step = Mathf.Max(1, vs.Length / Mathf.Max(1, maxSamples));
            for (int i = 0; i < vs.Length; i += step) L.Add(l2w.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    /// <summary>駒の壁体の、世界軸 <paramref name="ax"/> 方向の端の座標(<paramref name="sgn"/> ≥ 0 なら最大側)。
    /// 頂点が無ければ NaN。</summary>
    public static float EdgeAlong(Transform tr, Vector3 ax, float sgn, int maxSamples = 900)
    {
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in Body(tr, maxSamples)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
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

    /// <summary><see cref="FaceSpan"/> の片側。<paramref name="maxSide"/> なら dir の正の側の面。無ければ NaN。</summary>
    public static float Face(GameObject go, Vector2 dir, float yLo, float yHi, bool maxSide,
                             Vector2 perpDir = default(Vector2), Vector2 origin = default(Vector2), float perpMax = 0f)
    {
        float mn, mx; FaceSpan(go, dir, yLo, yHi, out mn, out mx, perpDir, origin, perpMax);
        if (mx < mn) return float.NaN;
        return maxSide ? mx : mn;
    }

    /// <summary>線(点 <paramref name="a"/>・外向き法線 <paramref name="n"/>)からの、帯内の頂点の**最大の張り出し**[m]
    /// (= その駒の外面の位置。負なら線より内)。頂点が無ければ NaN。岡部 `FaceOut` に帯を足した物。</summary>
    public static float FaceOut(GameObject go, Vector2 a, Vector2 n, float yLo, float yHi)
    {
        float best = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>();
            if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
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
    public static float AlignFace(GameObject go, Vector2 a, Vector2 n, float target, float yLo, float yHi)
    {
        float f = FaceOut(go, a, n, yLo, yHi);
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
    /// 返り値 = 伸ばした量[m](負 = 縮めた。測れなければ NaN)。上限は呼び出し側が決める。</summary>
    public static float StretchEnd(Transform piece, Transform pair, Vector3 ax, float sgn, float target)
    {
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var v in Body(piece)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
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
        var d = dir.normalized;
        var u = Vector3.Cross(d, Mathf.Abs(d.y) < 0.9f ? Vector3.up : Vector3.right).normalized;
        var v = Vector3.Cross(d, u).normalized;
        var pa = Body(a.transform, maxSamples, withRoof);
        var pb = Body(b.transform, maxSamples, withRoof);
        if (pa.Count == 0 || pb.Count == 0) return float.NaN;
        var fa = new Dictionary<long, float>();   // 筋ごと: a の前面(dir の最大)
        var fb = new Dictionary<long, float>();   // 筋ごと: b の背面(dir の最小)
        var pt = new Dictionary<long, Vector3>();
        System.Func<Vector3, long> key = w =>
            ((long)Mathf.RoundToInt(Vector3.Dot(w, u) / cell) << 32) ^ (uint)Mathf.RoundToInt(Vector3.Dot(w, v) / cell);
        foreach (var w in pa)
        {
            long k = key(w); float q = Vector3.Dot(w, d);
            float cur; if (!fa.TryGetValue(k, out cur) || q > cur) { fa[k] = q; pt[k] = w; }
        }
        foreach (var w in pb)
        {
            long k = key(w); float q = Vector3.Dot(w, d);
            float cur; if (!fb.TryGetValue(k, out cur) || q < cur) fb[k] = q;
        }
        float best = float.NaN;
        foreach (var kv in fa)
        {
            float qb; if (!fb.TryGetValue(kv.Key, out qb)) continue;
            float g = qb - kv.Value;
            if (float.IsNaN(best) || g < best) { best = g; at = pt[kv.Key]; }
        }
        if (float.IsNaN(best)) return best;                      // 筋が重ならない = 向き合っていない
        foreach (var kv in fa)
        {
            float qb; if (!fb.TryGetValue(kv.Key, out qb)) continue;
            if (qb - kv.Value - best <= tol) count++;
        }
        return best;
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
    /// 駒の実メッシュの全頂点について「頂点の高さ − その真下の地形(格子点)」を取り、最小の物が触れている箇所。
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
        var pts = Body(go.transform, maxSamples);
        float best = float.NaN; at = go.transform.position; count = 0;
        var cl = new List<float>(pts.Count);
        foreach (var p in pts)
        {
            float c = p.y - GroundGrid(p.x, p.z); cl.Add(c);
            if (float.IsNaN(best) || c < best) { best = c; at = p; }
        }
        if (float.IsNaN(best)) return best;
        foreach (var c in cl) if (c - best <= tol) count++;
        return best;
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
        s0 = float.NaN; s1 = float.NaN;
        Vector2 d = (B - A).normalized;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var w in pts)
        {
            if (w.y < yLo || w.y > yHi) continue;
            float p = (w.x - A.x) * perpDir.x + (w.z - A.y) * perpDir.y;
            if (p < perpLo || p > perpHi) continue;
            float s = (w.x - A.x) * d.x + (w.z - A.y) * d.y;
            if (s < mn) mn = s; if (s > mx) mx = s;
        }
        if (mx < mn) return false;
        s0 = mn; s1 = mx; return true;
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
