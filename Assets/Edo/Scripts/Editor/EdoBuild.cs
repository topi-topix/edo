// 配置・資産系の共有基盤 (Phase 2c, 2026-08-26)
//   EdoNishiTameikeBuilder (1305行の屋敷ビルダー) に埋まっていた共有ヘルパの本体をここへ移した。
//   NT 側はシグネチャ温存の1行委譲を残しており、NT を参照する既存16ファイルは無変更で動く。
//   各ビルダーの Ground 委譲チェーン (Shinmachi→Tamachi→TameikeKita 等) はここへ1段化済み。
//   ⛔ NagayaRun / DobeiRun / NaturalMode は既知の欠陥・状態込みで NT に残す (統一は別 Phase・ユーザー確認付き)。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoBuild
{
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
    public static List<Vector3> Body(Transform tr, int maxSamples = 900)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            if (IsRoofName(mf.name)) continue;
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

    /// <summary>**地面に据える。**駒の**実メッシュの底**を、その真下の地形(格子点)へ置き、
    /// <paramref name="sink"/> だけ沈める。返り値 = 動かした量[m]。
    ///
    /// <para>⛔ **部材の基準点(ピボット)を信用して座標へ置かない。**ピボットの位置は部材ごとに違う
    /// (床 / 軒先 / 小口 / 中心 / 天端)。座標へ直に置くと、メッシュがピボットより下へ伸びている部材は
    /// その分だけ地中へ潜り、上へ伸びている部材は浮く。⚠ 2026-09-20 松江松平: 下草を「設計面へピボットを置く」
    /// だけで据えていたため、実メッシュの底が地面から **1.90m** 下にあった(葉は地表に見えているので
    /// レンダでは気づけない)。景石も沈める量を 0.34m の決め打ちにしていた。</para>
    ///
    /// <para>⚠ <paramref name="sink"/> は**意図して埋める量**(景石の 1/3 埋め・下草の根元)。
    /// ⛔ 部材のピボットのずれを吸わせる目的で使わない — それは測って消す物で、決め打ちで隠す物ではない。</para></summary>
    public static float SeatOnGround(GameObject go, float sink = 0f)
    {
        var b = RB(go);
        float g = GroundGrid(go.transform.position.x, go.transform.position.z);
        float dy = (g - sink) - b.min.y;
        go.transform.position += new Vector3(0f, dy, 0f);
        return dy;
    }

    /// <summary>**丈の <paramref name="fraction"/> だけ埋めて据える。**景石の「1/3 埋め」のような、
    /// 部材の大きさに比例して沈める据え方。丈は実メッシュの高さから測るので、
    /// 個体差のある石をスケールで散らしても埋まり方が揃う。返り値 = 埋めた量[m]。
    /// ⛔ 決め打ちの沈め量(0.34m など)を全個体へ当てない — 大きい石は浮き、小さい石は沈む。</summary>
    public static float SeatBuried(GameObject go, float fraction)
    {
        var b = RB(go);
        float h = b.size.y;
        float sink = h * Mathf.Clamp01(fraction);
        SeatOnGround(go, sink);
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
}
