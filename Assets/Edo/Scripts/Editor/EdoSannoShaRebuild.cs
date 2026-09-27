// 山王権現社 — **指図どおりに建て直す**ビルダー (2026-09-10 棟梁)
//
// 【なぜ新しい入口を建てたか】
//   旧 `EdoSannoShaBuilder` の Stage1/2 は **参道軸 z=857 を直書き**しており
//   (:60,61,62,67,234,236,238,277,289,362,737,825)、指図の `grid.keidai.z0` = 847.0 と
//   **10m ずれた別物**を建てる。しかも `Keidai` が在ると黙って `"SKIP"` を返すので、
//   ⛔ **古い Stage を流し直すと z=857 の実装を建て直すだけ**になる(掲示板 EDO-0181)。
//   ⇒ ここでは **座標を一つも持たず**、すべて
//        設計値 … docs/Sashizu/sanno_sashizu.json   (EdoSannoShaBuilder.SashizuRel)
//        算出物 … docs/Sashizu/sanno_impl.json      (EdoSannoShaBuilder.ImplRel)
//   から読む。⛔ **定数を 847 に書き換えるだけにしない** — また次の巡でずれる。
//
// 【この本が持ってよい物】部材のパス・据え付けの規約(部材の原点がどこか)・許容差。
//   ⛔ 寸法・座標・段数・天端の高さは一つも持たない。
//
// 【建てない物(この巡)】
//   ・**社叢の木 1,794本** … 三角数が未決(`_pending` 中10/D-1)。別の巡で低ポリ版か
//     TerrainTree を決める。
//   ・**土に埋まっている土留めの区間** … `runs[].profile` の 見付高 ≤ 0 かつ 受け高 > 0。
//     ⛔ 土に埋まった石垣を積まない・⛔ 壁を上げて誤魔化さない(裁定 EDO-0182 が未着手)。
//   ・**部材が在庫にも新造にも無い物** … 中門・鳥居・透塀・回廊・木戸(`bom` が「無い/新造」)。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class EdoSannoShaRebuild
{
    const string MENU = "Edo/山王社/建て直し/";
    const string GROUP = "Edo_Sanno_Sha";
    /// <summary>旧実装(z=857)の退避先。⛔ **削除しない**(規則1の趣旨) — ルートの子として
    /// 束ねて **非活性**にする。⚠ 突き合わせ(`EdoSannoSashizuCheck`)はこの名の下を数えない。</summary>
    public const string GROUP_OLD = "Kyu_z857";
    /// <summary>退避する旧実装の群。⚠ **`Keidairin`(境内林)は退避しない** — 社叢の建て直しは
    /// この巡では**しない**(木 1,794本の三角数が未決・`_pending` 中10/D-1)ので、
    /// ⛔ 退避すると山が丸裸になる。⇒ 旧の松・竹をそのまま残す。</summary>
    static readonly string[] RETIRE = { "Keidai", "Sando" };

    // ---------------------------------------------------------------- 部材のパス
    /// <summary>⚠ **規則12 の例外の申し送り。** パスの literal は `EdoAssets.cs` に置くのが正典だが、
    /// 2026-09-10 の時点で `EdoAssets.cs` は**別セッションが門番の claim で押さえて**おり、
    /// ⛔ steal できなかった。⇒ 暫定でここに置く。**空き次第 `EdoAssets.Own` へ移すこと**。
    /// ⭕ **Dan は 2026-09-20 に移した**(`EdoAssets.Own.SannoDan`)。**残るは SakuKoshidaka / Shaden の2系統**。
    /// 目録 `docs/asset-index.tsv` に全点載っている。</summary>
    static class P
    {
        /// <summary>段石。綴りに **蹴上・踏面・幅** が入る(`Tools/Blender/build_sanno_buzai.py -- dan`)。
        /// ⭐ 個体 a/b の2種を **i%2 で振る**(⛔ 片方だけを53段並べない)。
        /// ⭕ **2026-09-20 に正典を `EdoAssets.Own.SannoDan` へ移した**(規則12 ── claim が空いた)。
        /// ここは呼び出し元を壊さないための受け渡しだけ。⛔ ここに綴りを書き戻さない。</summary>
        public static string Dan(float keri, float fumi, float w, int i)
        {
            return EdoAssets.Own.SannoDan(keri, fumi, w, i);
        }
        public const string SakuSpan = "Assets/Edo/Models/Hei/Saku_Koshidaka_1.818.fbx";
        public const string SakuPost = "Assets/Edo/Models/Hei/Saku_Koshidaka_Post.fbx";
        public static string Shaden(string n) { return "Assets/Edo/Models/Sanno/" + n + ".fbx"; }
    }

    // ---- 部材の据え付けの規約(部材の生成器の註が正典。⛔ 寸法ではない)-----------
    /// <summary>腰高柵 1スパンの呼び寸[m]。⭐ **綴りに入っている値**であってここが出所ではない
    /// (`P.SakuSpan` の綴りと同じ数)。⛔ 柵の丈・柱径はここに持たない。</summary>
    const float SAKU_SPAN = 1.818f;
    /// <summary>Castle Wall の実メッシュ(2026-09-06 土井で実測): local X∈[−2.4,0] / Y∈[0,4] / Z∈[−2,0]。
    /// ⇒ **ピボットは走りの「頭」ではなく「尻」**。走りの始点に置くと 2.0m 手前へはみ出す。</summary>
    const float IG_RUN = 2.00f, IG_H = 4.00f, IG_PITCH_MAX = 1.80f;
    /// <summary>「埋まっている壁」の判定の閾[m]。⛔ 設計値ではない — 見付高 0 の丸めの幅。</summary>
    const float BURIED_EPS = 0.02f;
    /// <summary>低い側を測る左右のオフセット。**指図の `const.wallProbeM` を読む**(⛔ 写さない)。</summary>
    static float WallProbeM { get { return F(D(Doc, "const"), "wallProbeM"); } }

    static readonly CultureInfo IC = CultureInfo.InvariantCulture;

    // ================================================================ 検図関門
    /// <summary>⛔ **既定では止まる。**2026-09-10 に普請奉行が明示的に迂回を指示したときだけ
    /// `BypassReviewGate` を立てて流す。⛔ `EdoSashizuExport.ReviewGate` 自体は書き換えない
    /// (黙らせたら次の邸で効かなくなる)。</summary>
    public static bool BypassReviewGate = false;
    static string Gate()
    {
        var g = EdoSashizuExport.ReviewGate(EdoSannoSashizuCheck.Id);
        if (g == null) return null;
        if (!BypassReviewGate) return g;
        Debug.LogWarning("[山王 建て直し] ⛔ **検図関門は赤のまま迂回した**(普請奉行の明示指示 2026-09-10)。\n"
            + "  理由: 三役の指摘は全件書き起こし済み(65118191)で、赤は『直した版を誰も検め直していない』ため。\n"
            + "  いまシーンに建っている物のほうが指図と別物(対照表 一致0/不一致12・女坂が鏡像 = 掲示板 EDO-0181)。\n"
            + "  ⇒ 建て直すほうが差が縮む。⛔ 検分に出し直すまでユーザーへ見せないこと。\n" + g);
        return null;
    }

    // ================================================================ 指図・算出物
    static Dictionary<string, object> _doc, _impl;
    static string RepoRoot { get { return Directory.GetParent(Application.dataPath).FullName; } }
    static Dictionary<string, object> Doc
    {
        get
        {
            if (_doc == null)
                _doc = EdoMiniJson.Parse(File.ReadAllText(Path.Combine(RepoRoot, EdoSannoShaBuilder.SashizuRel)))
                       as Dictionary<string, object>;
            return _doc;
        }
    }
    static Dictionary<string, object> Impl
    {
        get
        {
            if (_impl == null)
            {
                _impl = EdoMiniJson.Parse(File.ReadAllText(Path.Combine(RepoRoot, EdoSannoShaBuilder.ImplRel)))
                        as Dictionary<string, object>;
                VerifyImplFingerprint();
            }
            return _impl;
        }
    }

    /// <summary>算出物が**いまの指図**から焼かれた物か。⚠ 古い焼きで建てると、指図では直った
    /// はずの物が黙って復活する(2026-09-01 に松江松平の Stage7 で起きた型・EdoOkabeYashikiBuilder
    /// と同じ照合。⛔ 山王はこの照合を持たずに黙って古い焼きで建てていた ── EDO-0389)。</summary>
    static void VerifyImplFingerprint()
    {
        var src = D(_impl, "src");
        if (src == null || !src.ContainsKey("sha256"))
        { Debug.LogWarning("[山王] 算出物に src.sha256 が無い — 指図との対応を機械で確かめられない"); return; }
        string want = Convert.ToString(src["sha256"]);
        string got = EdoQaVerdict.Sha256Hex(Path.Combine(RepoRoot, EdoSannoShaBuilder.SashizuRel));
        if (!EdoQaVerdict.FingerprintMatches(want, got))
            throw new Exception("⛔ 算出物が**いまの指図から焼かれていない**"
                + "\n   指図 " + got.Substring(0, 16) + "… / 算出物が名乗る元 " + want.Substring(0, Math.Min(16, want.Length)) + "…"
                + "\n   `python3 Tools/Sashizu/bake_impl.py sanno --write` を回し直すこと"
                + "\n   ⚠ 焼き直せるのは `baked.columns` の欄だけ。`baked.carried` の欄は焼き手が main に無く"
                + "**当時の指図のまま**(その指紋は `baked.carriedSrc`)── 指図でそこを動かしたのなら、"
                + "焼き手を起こすまで現物は古い値で建つ(EDO-0386 / EDO-0261 ①)。掲示板へ起票すること");
    }
    [MenuItem(MENU + "指図を読み直す(キャッシュを捨てる)")]
    public static void Reload() { _doc = null; _impl = null; _gr = null; Debug.Log("[山王] 指図・算出物のキャッシュを捨てた"); }

    // ---- json の小道具 ---------------------------------------------------
    static float Cv(object o) { return o == null ? 0f : Convert.ToSingle(o, IC); }
    static object G(Dictionary<string, object> d, string k)
    { object v; return d != null && d.TryGetValue(k, out v) ? v : null; }
    static float F(Dictionary<string, object> d, string k) { return Cv(G(d, k)); }
    static bool HasNum(Dictionary<string, object> d, string k) { return G(d, k) != null; }
    static Dictionary<string, object> D(Dictionary<string, object> d, string k) { return G(d, k) as Dictionary<string, object>; }
    static List<object> L(Dictionary<string, object> d, string k) { return G(d, k) as List<object> ?? new List<object>(); }
    static string S(Dictionary<string, object> d, string k) { var o = G(d, k); return o == null ? null : o.ToString(); }
    static Vector2 P2(object o)
    { var p = o as List<object>; return p == null || p.Count < 2 ? Vector2.zero : new Vector2(Cv(p[0]), Cv(p[1])); }
    static List<Vector2> Pts(List<object> l)
    { var r = new List<Vector2>(); foreach (var o in l) r.Add(P2(o)); return r; }

    /// <summary>境内グリッド (u,v)[間] → 世界。**算出物の `grid` が正典**(x = x0 + u×ken / z = z0 + v×ken)。
    /// ⛔ ここに 847 も −484 も書かない。</summary>
    static Vector2 W(float u, float v)
    {
        var g = D(Impl, "grid");
        float ken = F(g, "ken");
        // ⭐ 境内の軸は世界軸から回っている(2026-09-23 施主裁定 5.5°)── 基底 ux/uz/vx/vz を必ず掛ける。
        //   ⛔ x0 + u×ken と書かない(回りを落とすと社殿だけが元の軸に取り残される・EDO-0430)。
        return new Vector2(F(g, "x0") + (u * F(g, "ux") + v * F(g, "vx")) * ken,
                           F(g, "z0") + (u * F(g, "uz") + v * F(g, "vz")) * ken);
    }

    // ================================================================ 造成の設計面
    /// <summary>算出物 `graded` — 生成器が焼いた**造成後の設計面**(1m 刻み・未造成のセルは null)。
    /// ⛔ 実装が `design_y` を引き直さない(切盛図・断面・動線と別の答えになる)。</summary>
    class Graded
    {
        public float x0, z0, step; public int nx, nz;
        public float[] h; public bool[] ok;
        public bool Cell(int i, int j, out float y)
        {
            y = 0f;
            if (i < 0 || j < 0 || i >= nx || j >= nz) return false;
            int k = j * nx + i; if (!ok[k]) return false; y = h[k]; return true;
        }
        /// <summary>4隅がそろっているときだけ双一次で返す。⛔ **欠けている所は触らない**
        /// (設計面の外へ勝手に外挿すると社地の外の地形を動かす)。</summary>
        public bool Bilinear(float x, float z, out float y)
        {
            y = 0f;
            float fx = (x - x0) / step, fz = (z - z0) / step;
            int i = Mathf.FloorToInt(fx), j = Mathf.FloorToInt(fz);
            float tx = fx - i, tz = fz - j;
            float a, b, c, d2;
            if (!Cell(i, j, out a) || !Cell(i + 1, j, out b) || !Cell(i, j + 1, out c) || !Cell(i + 1, j + 1, out d2))
                return false;
            y = Mathf.Lerp(Mathf.Lerp(a, b, tx), Mathf.Lerp(c, d2, tx), tz);
            return true;
        }
        /// <summary>**地形の節点へ写す値。**4隅の差が <paramref name="cliff"/> を超える所(= 設計の法では作れない段 ── 石垣の見え面)は
        /// 双一次で跨がず、節点が高い側の面(<paramref name="onHigh"/>: 面の多角形の中で面の高さが段の中ほどより上)に居なければ**低い側**を採る。
        /// 欠けている所は半径 1 セルの最寄り(同じく段を跨ぐなら同じ判定)。⚠ 高い側の判定を外すと、回廊の基壇(幅 5m)の内の節点が
        /// 外の低い地盤へ引かれ、土留めの見え面の向きの票が割れて裏返った(2026-09-25 実測)。
        /// ⭐ 設計面の石垣の外形の中のセルは石垣の天端(地盤でない)で、跨いで補間すると見え面の外の節点が天端へ引かれ、
        ///   石垣の前(二段築の下段の天端・法の足)を 2.8m 埋めた(2026-09-25 山王 回廊の北東・EDO-0430)。石垣の中は石垣が描く。
        /// 当たる先: 設計面(算出物 graded)を地形へ写す全ての造成 ── 山王 Stage1(土留め・回廊の基壇・郭の石垣の見え面の際)。</summary>
        /// <para>⭐ <paramref name="baseAt"/>(造成前の地盤・無い所は NaN)を渡すと、4 隅の欠けた縁の節点は**そろっている隅の設計面と
        /// 欠けた隅の造成前の地盤を重みで混ぜる**(2026-09-25・EDO-0430)。⛔ 最寄りのセルの値を 1 セル外へ平らに延ばさない ── 回廊の基壇の
        /// 東の見え面の前で、1m 先のセルの値が斜面(0.3〜0.5m/m)の節点へ写り +0.3〜+0.75m の山形の裾になった(設計面の外 = 造成しない地盤)。</para>
        public bool NodeY(float x, float z, float cliff, Func<Vector2, float, bool> onHigh, out float y, out bool atCliff,
                          Func<float, float, float> baseAt = null)
        {
            y = 0f; atCliff = false;
            float fx = (x - x0) / step, fz = (z - z0) / step;
            int i = Mathf.FloorToInt(fx), j = Mathf.FloorToInt(fz);
            float a, b, c, d2;
            if (Cell(i, j, out a) && Cell(i + 1, j, out b) && Cell(i, j + 1, out c) && Cell(i + 1, j + 1, out d2))
            {
                float mn = Mathf.Min(Mathf.Min(a, b), Mathf.Min(c, d2)), mx = Mathf.Max(Mathf.Max(a, b), Mathf.Max(c, d2));
                if (mx - mn > cliff && !onHigh(new Vector2(x, z), (mn + mx) * 0.5f)) { y = mn; atCliff = true; return true; }
                float tx = fx - i, tz = fz - j;
                y = Mathf.Lerp(Mathf.Lerp(a, b, tx), Mathf.Lerp(c, d2, tx), tz); return true;
            }
            if (!Near(x, z, 1, out y)) return false;
            int i0 = Mathf.RoundToInt(fx), j0 = Mathf.RoundToInt(fz); float lo = float.MaxValue, hi = float.MinValue;
            for (int dj = -1; dj <= 1; dj++) for (int di = -1; di <= 1; di++)
                { float v; if (!Cell(i0 + di, j0 + dj, out v)) continue; lo = Mathf.Min(lo, v); hi = Mathf.Max(hi, v); }
            if (hi - lo > cliff && !onHigh(new Vector2(x, z), (lo + hi) * 0.5f)) { y = lo; atCliff = true; return true; }
            if (baseAt != null)
            {
                float bv = baseAt(x, z);
                if (!float.IsNaN(bv))
                {
                    // 混ぜるのは「設計面 − 造成前の地盤」の差(欠けた隅は差 0)。値そのものを混ぜると 1m 先のセルの高さが斜面(〜0.9m/m)の
                    // 節点へ写り、造成しない地盤の上に +0.1〜0.2m の段が残った(2026-09-25 実測)。
                    float tx = fx - i, tz = fz - j; double dsum = 0;
                    for (int di = 0; di <= 1; di++)
                        for (int dj = 0; dj <= 1; dj++)
                        {
                            float w = (di == 1 ? tx : 1f - tx) * (dj == 1 ? tz : 1f - tz); float v;
                            if (!Cell(i + di, j + dj, out v)) continue;
                            float bc = baseAt(x0 + (i + di) * step, z0 + (j + dj) * step); if (float.IsNaN(bc)) continue;
                            dsum += w * (v - bc);
                        }
                    y = bv + (float)dsum;
                }
            }
            return true;
        }
        /// <summary>最寄りのセル(半径 r セル以内)。無ければ false。</summary>
        public bool Near(float x, float z, int r, out float y)
        {
            y = 0f;
            int i0 = Mathf.RoundToInt((x - x0) / step), j0 = Mathf.RoundToInt((z - z0) / step);
            int best = int.MaxValue; float bv = 0f;
            for (int dj = -r; dj <= r; dj++)
                for (int di = -r; di <= r; di++)
                {
                    float v; if (!Cell(i0 + di, j0 + dj, out v)) continue;
                    int dd = di * di + dj * dj;
                    if (dd < best) { best = dd; bv = v; }
                }
            if (best == int.MaxValue) return false;
            y = bv; return true;
        }
    }
    static Graded _gr;
    static Graded Gr
    {
        get
        {
            if (_gr != null) return _gr;
            var g = D(Impl, "graded");
            var gg = new Graded();
            gg.x0 = F(g, "x0"); gg.z0 = F(g, "z0"); gg.step = F(g, "step");
            gg.nx = (int)F(g, "nx"); gg.nz = (int)F(g, "nz");
            gg.h = new float[gg.nx * gg.nz]; gg.ok = new bool[gg.nx * gg.nz];
            var rows = L(g, "h");
            for (int j = 0; j < rows.Count && j < gg.nz; j++)
            {
                var row = rows[j] as List<object>; if (row == null) continue;
                for (int i = 0; i < row.Count && i < gg.nx; i++)
                {
                    if (row[i] == null) continue;
                    gg.h[j * gg.nx + i] = Cv(row[i]); gg.ok[j * gg.nx + i] = true;
                }
            }
            _gr = gg; return _gr;
        }
    }

    // ================================================================ 置く道具
    static Transform Group(string child)
    {
        var r = GameObject.Find(GROUP);
        if (r == null) { r = new GameObject(GROUP); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var g = new GameObject(seg); Undo.RegisterCreatedObjectUndo(g, "grp");
                g.transform.SetParent(cur, false); nx = g.transform;
            }
            cur = nx;
        }
        return cur;
    }
    static void Clear(Transform t)
    { for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(t.GetChild(i).gameObject); }

    // 折れ線の道具 ---------------------------------------------------------
    static float PolyLen(List<Vector2> p)
    { float s = 0f; for (int i = 1; i < p.Count; i++) s += Vector2.Distance(p[i - 1], p[i]); return s; }
    /// <summary>折れ線上の弧長 s の点と、その場の進行方向。</summary>
    static void PolyAt(List<Vector2> p, float s, out Vector2 pos, out Vector2 dir)
    {
        float acc = 0f;
        for (int i = 1; i < p.Count; i++)
        {
            float l = Vector2.Distance(p[i - 1], p[i]); if (l < 1e-6f) continue;
            if (s <= acc + l || i == p.Count - 1)
            {
                float t = Mathf.Clamp01((s - acc) / l);
                pos = Vector2.Lerp(p[i - 1], p[i], t); dir = (p[i] - p[i - 1]) / l; return;
            }
            acc += l;
        }
        pos = p[p.Count - 1]; dir = Vector2.right;
    }
    /// <summary>ローカル +Z を <paramref name="d"/> へ向ける yaw[deg]。</summary>
    static float YawZ(Vector2 d) { return Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg; }
    /// <summary>ローカル +X を <paramref name="d"/> へ向ける yaw[deg]。</summary>
    static float YawX(Vector2 d) { return Mathf.Atan2(-d.y, d.x) * Mathf.Rad2Deg; }

    // ================================================================ Stage 0 退避
    [MenuItem(MENU + "0 旧実装を退避する(z=857 の物)")]
    public static void Stage0Menu() { Debug.Log("[山王] " + Stage0_Retire()); }
    /// <summary>いま建っている `Edo_Sanno_Sha`(z=857 の旧実装)を **`Edo_Sanno_Sha_Kyu` へ改名して
    /// 非活性のままプレハブへ切り出す**。⛔ 削除しない。⛔ `Edo_Sanno_Sha.prefab` も消さない
    /// (git に残る + 退避先が別プレハブとして立つので、二重に残る)。</summary>
    public static string Stage0_Retire()
    {
        var root = GameObject.Find(GROUP);
        if (root == null) return "SKIP: " + GROUP + " が無い(退避する物が無い)";
        EdoYashikiPrefab.EnsureEditable(root);   // ⛔ 解かないと再親子付けが**黙って**失敗する
        var kyu = root.transform.Find(GROUP_OLD);
        if (kyu == null)
        {
            var g = new GameObject(GROUP_OLD); Undo.RegisterCreatedObjectUndo(g, "kyu");
            g.transform.SetParent(root.transform, false); kyu = g.transform;
        }
        var sb = new StringBuilder(); int moved = 0;
        foreach (var nm in RETIRE)
        {
            var t = root.transform.Find(nm);
            if (t == null) { sb.AppendLine("  " + nm + ": 無い(既に退避済みか未生成)"); continue; }
            int n = t.GetComponentsInChildren<Transform>(true).Length;
            t.SetParent(kyu, true); moved++;
            sb.AppendLine("  " + nm + " を退避(transform " + n + ")");
        }
        kyu.gameObject.SetActive(false);
        return "旧実装(z=857)の退避: " + moved + " 群 → " + GROUP + "/" + GROUP_OLD + "(非活性)\n" +
               "  ⛔ 削除していない。⭐ 境内林 Keidairin は社叢の建て直しがこの巡に無いので残した。\n" + sb;
    }

    // ================================================================ Stage 1 造成
    [MenuItem(MENU + "1 整地(算出物の設計面へ)")]
    public static void Stage1Menu() { Debug.Log("[山王] " + Stage1_Grade()); }
    /// <summary>算出物 `graded` の設計面へ地形を寄せる。⛔ 設計面が欠けているセルは触らない。
    /// ⚠ 地形の編集は Undo の外 — 呼ぶ前に heightmap を退避しておくこと。</summary>
    public static string Stage1_Grade()
    {
        var gate = Gate(); if (gate != null) return gate;
        { var us = UnSkin(); if (us.Length > 0) Debug.Log("[山王] " + us); }
        var gr = Gr;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);

        float mnx = gr.x0, mxx = gr.x0 + (gr.nx - 1) * gr.step;
        float mnz = gr.z0, mxz = gr.z0 + (gr.nz - 1) * gr.step;
        int x0 = IX(mnx), x1 = IX(mxx), z0 = IZ(mnz), z1 = IZ(mxz);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0, skip = 0, cliffN = 0; float cmax = 0f, fmax = 0f; double cutSum = 0, fillSum = 0;
        // 段の閾: 設計の最も急な法(1:batterCut / batterFill の小さい方)がセルの対角で作る差の 2 倍。これを超える隅の差は石垣の見え面。
        float steep = Mathf.Min(F(D(Doc, "const"), "batterCut"), F(D(Doc, "const"), "batterFill"));
        float cliff = 2f * gr.step * Mathf.Sqrt(2f) / Mathf.Max(0.1f, steep);
        var tPoly = new List<Vector2[]>(); var tY = new List<float>();
        foreach (var o in L(Impl, "terraces"))
        {
            var tc = o as Dictionary<string, object>; var wl = L(tc, "world"); if (wl.Count < 3) continue;
            var poly = new Vector2[wl.Count];
            for (int i = 0; i < wl.Count; i++) { var q = wl[i] as List<object>; poly[i] = new Vector2(Cv(q[0]), Cv(q[1])); }
            tPoly.Add(poly); tY.Add(F(tc, "y"));
        }
        Func<Vector2, float, bool> onHigh = (p, mid) =>
        {
            for (int k = 0; k < tPoly.Count; k++) if (tY[k] >= mid && EdoGeom.PIP(tPoly[k], p)) return true;
            return false;
        };
        // 設計面の縁の外の隅は造成前の地盤(社地の区画の中だけ ── 区画の外は他の造成が地形を持つので混ぜない)
        var precB = EdoParcels.Get("sannosha_prec"); var demB = DemAt();
        Func<float, float, float> baseIn = (bx, bz) =>
            precB != null && EdoGeom.PIP(precB, new Vector2(bx, bz)) ? demB(bx, bz) : float.NaN;
        var dodomeSegs = new List<Vector2[]>();
        foreach (var o in L(Impl, "runs"))
        {
            var rn = o as Dictionary<string, object>; if (rn == null || S(rn, "kind") != "土留め") continue;
            var nl = L(rn, "nodes"); for (int k = 1; k < nl.Count; k++) dodomeSegs.Add(new[] { P2(nl[k - 1]), P2(nl[k]) });
        }
        int restN = 0; float restMax = 0f, outMax = 0f; int outN = 0;
        float bx0 = float.MaxValue, bx1 = float.MinValue, bz0 = float.MaxValue, bz1 = float.MinValue;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = WX(x0 + x), wz = WZ(z0 + z);
                float y;
                // ⚠ 地形の節点は 2m 刻み・設計面は 1m 刻みなので、**面の縁の節点が丸ごと落ちる**。
                //   ⇒ 4隅がそろわないときは **1セル以内の最寄り**で拾う(縁を1節点だけ延ばす)。
                //   ⛔ それでも無ければ触らない — 設計面の外へ外挿しない。
                bool atCliff;
                // ⭐ 社地の区画の外の節点は設計面へ寄せない ── 造成前の地盤(DEM)のまま(2026-09-25・EDO-0430)。
                //   ⛔ 1 セルの最寄り・双一次の縁の拾いで区画の外へ波及させない ── 参道の階の坂下の道で区画の外の 4 節点が
                //   石段の足元の設計面へ最大 0.156m 引かれた。設計面が届く所だけ DEM へ戻す(届かない所は触らない)。
                if (precB != null && !EdoGeom.PIP(precB, new Vector2(wx, wz)))
                {
                    float yo; bool co;
                    if (gr.NodeY(wx, wz, cliff, onHigh, out yo, out co))
                    {
                        float dv = demB(wx, wz), cur0 = H[z, x] * ts.y + tp.y;
                        if (!float.IsNaN(dv) && Mathf.Abs(cur0 - dv) > 0.005f)
                        { H[z, x] = Mathf.Clamp01((dv - tp.y) / ts.y); outN++; outMax = Mathf.Max(outMax, Mathf.Abs(cur0 - dv)); }
                    }
                    skip++; continue;
                }
                if (!gr.NodeY(wx, wz, cliff, onHigh, out y, out atCliff, baseIn))
                {
                    skip++;
                    // ⭐ 土留めの見え面の前(FRONT_REACH 以内)で設計面の外の節点は、造成前の地盤へ戻す(2026-09-25・EDO-0430)。
                    //   前の巡・旧実装が残した値(回廊の基壇の東の見え面の 3m 前に +0.27〜+0.75m)が、見え面の前の帯に小さな山と筋を立てた。
                    //   ⛔ 社地の区画の外と、土留めから離れた所(板塀 Ita_Keidai の足元の切土など)は触らない。
                    var wp = new Vector2(wx, wz); float bv = baseIn(wx, wz);
                    if (!float.IsNaN(bv) && NearSeg(dodomeSegs, wp, FRONT_REACH))
                    {
                        float cur0 = H[z, x] * ts.y + tp.y;
                        if (Mathf.Abs(cur0 - bv) > 0.005f)
                        { H[z, x] = Mathf.Clamp01((bv - tp.y) / ts.y); restN++; restMax = Mathf.Max(restMax, Mathf.Abs(cur0 - bv)); }
                    }
                    continue;
                }
                if (atCliff) cliffN++;
                float cur = H[z, x] * ts.y + tp.y;
                if (y < cur) { cmax = Mathf.Max(cmax, cur - y); cutSum += cur - y; }
                else { fmax = Mathf.Max(fmax, y - cur); fillSum += y - cur; }
                H[z, x] = Mathf.Clamp01((y - tp.y) / ts.y); n++;
                bx0 = Mathf.Min(bx0, wx); bx1 = Mathf.Max(bx1, wx);
                bz0 = Mathf.Min(bz0, wz); bz1 = Mathf.Max(bz1, wz);
            }
        // ---- 面の輪郭の縁の残差について(2026-09-23 実測・⛔ ここで均さない)-------
        // 突き合わせの「造成の面」は算出物 `terraces[].world` の輪郭を **2m 刻みで標本**して
        // 設計の丈と比べる。2026-09-22 の残差(面 Keidai 2228点中9点・最大 −0.42m / 面 Zentei
        // 121点中9点・最大 +0.74m)は**全点が輪郭から 0.28m 以内**(Zentei の5点は輪郭の線の上)で、
        // 法面の始まりを標本していた。地形は **2 m/px** なので、輪郭ちょうどに面の縁を置くことは
        // できない(`EdoBuild.PadY` が `edgeMargin` を要求するのと同じ理由)。
        // ⛔ **輪郭の中の節点を丈へ均して逃げない** — 一度そう書いて測った:
        //     ・輪郭の中の節点だけ(49節点・最大0.28m)⇒ 残差は 9/9 → 9/8 でほぼ変わらず、
        //       女坂 Dan_41 の埋没が 1.565 → 1.680m に**悪化**した(面の輪郭が段の脇に掛かる)。
        //     ・1セル外まで広げる(350節点)⇒ 面の東の崖 x≈−478 で **6.66m の盛土**が斜面に張り出した。
        //   ⇒ どちらも戻した。残差は**物差しの側**(標本に一辺の控えが無い)で、造成の欠陥ではない。
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format(
            "整地: 書いた {0} 節点 / 設計面が欠けていて触らなかった {1} 節点 / 石垣の見え面を跨ぐので低い側を採った {10} 節点(隅の差 > {11:F2}m)\n" +
            "  切土 最大 {2:F2}m 体積 {3:F0}m³ / 盛土 最大 {4:F2}m 体積 {5:F0}m³\n" +
            "  触った範囲 x[{6:F1},{7:F1}] z[{8:F1},{9:F1}](算出物 graded の内)\n" +
            "  土留めの見え面の前 {12:F1}m 以内で設計面の外の節点を造成前の地盤へ戻した {13} 節点(最大 {14:F2}m)\n" +
            "  社地の区画の外で設計面が届く節点は造成前の地盤のまま(戻した {15} 節点・最大 {16:F3}m)",
            n, skip, cmax, cutSum * a, fmax, fillSum * a, bx0, bx1, bz0, bz1, cliffN, cliff, FRONT_REACH, restN, restMax, outN, outMax);
    }

    /// <summary>点 <paramref name="p"/> が**造成の持ち主が居ない区画**(類型表 typology.json に載り built:hand でない区画 ──
    /// 類型ビルダーは造成しない)の中か。社地(sannosha_prec)自身は含めない。</summary>
    static bool InUngradedParcel(Vector2 p)
    {
        if (_ungraded == null)
        {
            _ungraded = new List<Vector2[]>();
            foreach (var kv in EdoTypologyBuilder.Table)
            {
                if (kv.Value.Hand || kv.Key == "sannosha_prec") continue;
                var poly = EdoParcels.Get(kv.Key); if (poly != null && poly.Length >= 3) _ungraded.Add(poly);
            }
        }
        foreach (var poly in _ungraded) if (EdoGeom.PIP(poly, p)) return true;
        return false;
    }
    static List<Vector2[]> _ungraded;

    /// <summary>土留めの見え面の前で「造成しない地盤」を造成前の地盤へ戻す幅[m](見え面の前の検査の帯 3m + 地形の節点 1 つ分の半ば)。</summary>
    const float FRONT_REACH = 4f;
    static bool NearSeg(List<Vector2[]> segs, Vector2 p, float r)
    {
        foreach (var sg in segs)
        {
            Vector2 ab = sg[1] - sg[0]; float t = Mathf.Clamp01(Vector2.Dot(p - sg[0], ab) / Mathf.Max(1e-6f, ab.sqrMagnitude));
            if ((sg[0] + ab * t - p).sqrMagnitude <= r * r) return true;
        }
        return false;
    }
    /// <summary>造成前の地盤(`sanno_dem.json`・2m 格子の双一次)。欠けは NaN。</summary>
    static Func<float, float, float> DemAt()
    {
        var dem = EdoMiniJson.Parse(File.ReadAllText(Path.Combine(RepoRoot, EdoSannoShaBuilder.DemRel))) as Dictionary<string, object>;
        float dx0 = F(dem, "x0"), dz0 = F(dem, "z0"), dst = F(dem, "step"); var drows = L(dem, "h");
        Func<int, int, float> DV = (i, j) =>
        {
            if (j < 0 || j >= drows.Count) return float.NaN; var r = drows[j] as List<object>;
            return r == null || i < 0 || i >= r.Count || r[i] == null ? float.NaN : Cv(r[i]);
        };
        return (x, z) =>
        {
            float fi = (x - dx0) / dst, fj = (z - dz0) / dst; int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj); float tx = fi - i, tz = fj - j;
            return Mathf.Lerp(Mathf.Lerp(DV(i, j), DV(i + 1, j), tx), Mathf.Lerp(DV(i, j + 1), DV(i + 1, j + 1), tx), tz);
        };
    }

    /// <summary>**設計面から外れた節点を造成前の地盤へ戻して整地する。**<paramref name="prevImplPath"/> は前の巡で流した算出物
    /// (git の前の版を書き出した物)。前の算出物では設計面があり、いまの算出物では無い節点(= 造成をやめた所)は、`Stage1_Grade`
    /// が触らない(設計面の外へ外挿しない)ので**前の巡の切土・盛土がそのまま残る**。区画(`sannosha_prec`)の中のその節点だけを
    /// 造成前の地盤(`DemRel`)へ戻す。⚠ 区画の中でも前の算出物に無かった所(旧実装の手・柵の据え)は触らない。
    /// 2026-09-25 実測(EDO-0430): 回廊の基壇の東の斜面に前巡の犬走りの切土の法が 9 節点残り、−1.25〜+0.85m の段状の窪みになっていた。
    /// 当たる先: 設計面の範囲を縮めて流し直す全ての整地(山王 Stage1。他邸の整地も同じ型 ── 造成は毎回造成前の地盤から起こす)。</summary>
    public static string Stage1_Grade(string prevImplPath)
    {
        string head = Stage1_Grade();
        var prevG = D(EdoMiniJson.Parse(File.ReadAllText(prevImplPath)) as Dictionary<string, object>, "graded");
        var pg = new Graded();
        pg.x0 = F(prevG, "x0"); pg.z0 = F(prevG, "z0"); pg.step = F(prevG, "step");
        pg.nx = (int)F(prevG, "nx"); pg.nz = (int)F(prevG, "nz");
        pg.h = new float[pg.nx * pg.nz]; pg.ok = new bool[pg.nx * pg.nz];
        var rows = L(prevG, "h");
        for (int j = 0; j < rows.Count && j < pg.nz; j++)
        {
            var row = rows[j] as List<object>; if (row == null) continue;
            for (int i = 0; i < row.Count && i < pg.nx; i++) { if (row[i] == null) continue; pg.h[j * pg.nx + i] = Cv(row[i]); pg.ok[j * pg.nx + i] = true; }
        }
        var dem = EdoMiniJson.Parse(File.ReadAllText(Path.Combine(RepoRoot, EdoSannoShaBuilder.DemRel))) as Dictionary<string, object>;
        float dx0 = F(dem, "x0"), dz0 = F(dem, "z0"), dst = F(dem, "step"); var drows = L(dem, "h");
        Func<int, int, float> DV = (i, j) => { var r = drows[j] as List<object>; return r == null || r[i] == null ? float.NaN : Cv(r[i]); };
        Func<float, float, float> Dem = (x, z) =>
        {
            float fi = (x - dx0) / dst, fj = (z - dz0) / dst; int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj); float tx = fi - i, tz = fj - j;
            return Mathf.Lerp(Mathf.Lerp(DV(i, j), DV(i + 1, j), tx), Mathf.Lerp(DV(i, j + 1), DV(i + 1, j + 1), tx), tz);
        };
        var prec = EdoParcels.Get("sannosha_prec");
        var gr = Gr; var t = Terrain.activeTerrain; var td = t.terrainData; int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        int x0 = Mathf.Clamp(Mathf.RoundToInt((gr.x0 - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.RoundToInt((gr.x0 + (gr.nx - 1) * gr.step - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        int z0 = Mathf.Clamp(Mathf.RoundToInt((gr.z0 - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int z1 = Mathf.Clamp(Mathf.RoundToInt((gr.z0 + (gr.nz - 1) * gr.step - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1; var H = td.GetHeights(x0, z0, w, h);
        int n = 0; float mx = 0f; var sbx = new StringBuilder();
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = tp.x + (x0 + x) * ts.x / (hres - 1), wz = tp.z + (z0 + z) * ts.z / (hres - 1), y;
                if (gr.Bilinear(wx, wz, out y) || gr.Near(wx, wz, 1, out y)) continue;      // いまの設計面がある ── Stage1 が描いた
                if (!pg.Bilinear(wx, wz, out y) && !pg.Near(wx, wz, 1, out y)) continue;     // 前の巡も設計面の外 ── 触らない
                // ⭐ 社地の区画の外でも、**造成の持ち主が居ない区画**(類型で建てた区画 ── 類型ビルダーは造成しない)の節点は戻す
                //   (2026-09-26・EDO-0430)。区画の線を動かした後(施主裁定 2026-09-23 観理院との境)、前の巡の設計面が隣の区画
                //   sannosha_kanri の中に +0.29〜+1.07m 残っていた。⛔ 図を起こして建てた区画(built:hand)と道は触らない(他の造成が持つ)。
                var wp2 = new Vector2(wx, wz);
                if (prec == null || !(EdoGeom.PIP(prec, wp2) || InUngradedParcel(wp2))) continue;
                float g = Dem(wx, wz); if (float.IsNaN(g)) continue;
                float cur = H[z, x] * ts.y + tp.y; mx = Mathf.Max(mx, Mathf.Abs(g - cur));
                if (n < 12) sbx.Append(string.Format(" ({0:F1},{1:F1}) {2:+0.00;-0.00}", wx, wz, g - cur));
                H[z, x] = Mathf.Clamp01((g - tp.y) / ts.y); n++;
            }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return head + "\n  設計面から外れた節点を造成前の地盤へ戻した " + n + " 節点(最大 " + mx.ToString("F2") + "m)" + sbx;
    }

    // ================================================================ Stage 2 石段
    [MenuItem(MENU + "2 石段(男坂・女坂・参道の階)")]
    public static void Stage2Menu() { Debug.Log("[山王] " + Stage2_Kaidan()); }
    /// <summary>算出物 `stairs` の `spans`(= 生成器の `stair_spans`)から段石を据える。
    /// ⛔ **実装が段を割り直さない**(二つの式で割ると蹴上1段ぶんずれる)。
    /// ⚠ **木階(向拝の階・本殿の木階)は石段ではない** — 社殿の部材(Stage6)。</summary>
    public static string Stage2_Kaidan()
    {
        var gate = Gate(); if (gate != null) return gate;
        { var us = UnSkin(); if (us.Length > 0) Debug.Log("[山王] " + us); }
        var sb = new StringBuilder();
        // ⭐ 算出物から消えた石段の群を掃く(指図から外した段の階が残ると、面の上に浮いた段石が残る ── 2026-09-25 透塀の内を一つの面にした巡)
        {
            var want = new HashSet<string>();
            foreach (var o in L(Impl, "stairs")) { var st = o as Dictionary<string, object>; if (st != null) want.Add(GroupNameOf(S(st, "name"))); }
            var sg = Group("Sando");
            for (int i = sg.childCount - 1; i >= 0; i--)
            {
                var c = sg.GetChild(i); if (want.Contains(c.name)) continue;
                sb.AppendLine("  算出物に無い石段の群を外した: " + c.name + "(" + c.childCount + " 駒)");
                UnityEngine.Object.DestroyImmediate(c.gameObject);
            }
        }
        foreach (var o in L(Impl, "stairs"))
        {
            var st = o as Dictionary<string, object>; if (st == null) continue;
            string name = S(st, "name");
            var doc = FindByName(Doc, "kaidans", name);
            // ⭐ 木階は `kaidans[].kizahashi` が立っている。⛔ 段石を当てない(`bom` の別行)。
            if (doc != null && G(doc, "kizahashi") != null) { sb.AppendLine("  " + name + ": 木階なので石段では建てない(社殿の部材)"); continue; }
            var spans = L(st, "spans"); if (spans.Count == 0) { sb.AppendLine("  " + name + ": spans が無い"); continue; }
            float keri = F(st, "keri"), fumi = F(st, "fumi"), wM = F(st, "wM");
            string part = P.Dan(keri, fumi, wM, 0);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(part) == null)
            { sb.AppendLine("  ★ " + name + ": 段石 " + part + " が無い(部材方へ)"); continue; }

            // 折れ線を **坂下 → 山上** の向きに揃える(s は坂下からの展開長)。
            //   ⛔ 向きを決め打ちしない — 算出物の設計面が高いほうが山上。
            var pts = Pts(L(st, "nodes"));
            float ga, gb;
            bool haveA = Gr.Near(pts[0].x, pts[0].y, 3, out ga);
            bool haveB = Gr.Near(pts[pts.Count - 1].x, pts[pts.Count - 1].y, 3, out gb);
            // ⭐ 取り合いの欄(joints)が最上段の相手の面を名指ししていれば、その面に近い端が山上(EDO-0430)。
            //   ⛔ 2m 格子の設計面は面の境の上の端で上下を取り違える(段の階・幣殿の北が逆向きに建ち、背が下の段の面へ出た)。
            Vector2[] topPoly; float topY; string topFace, topKind;
            if (TopFaceOf(name, out topFace, out topPoly, out topY, out topKind))
            {
                float d0 = EdoGeom.PIP(topPoly, pts[0]) ? 0f : DistToPoly(new List<Vector2>(topPoly) { topPoly[0] }, pts[0]);
                float d1 = EdoGeom.PIP(topPoly, pts[pts.Count - 1]) ? 0f : DistToPoly(new List<Vector2>(topPoly) { topPoly[0] }, pts[pts.Count - 1]);
                if (d0 < d1) pts.Reverse();
                if (Mathf.Abs(d0 - d1) > 1e-3f && ((d0 < d1) != (haveA && haveB && ga > gb)))
                    sb.AppendLine("  " + name + ": 上下を取り合いの欄(最上段の相手 = 面 " + topFace + ")で決めた ── 設計面の読みと逆");
            }
            else if (haveA && haveB && ga > gb) pts.Reverse();
            else if (!(haveA && haveB)) sb.AppendLine("  ⚠ " + name + ": 設計面から上下を決められない(折れ線の順のまま)");

            var grp = Group("Sando/" + GroupNameOf(name)); Clear(grp);
            int made = 0;
            // ⭐ 石段の組(EDO-0415): この石段に沿う土留め(`terraceWalls` の coping:"stair")は**袖**として
            //   段ごとに据える(`EdoBuild.PlaceIshidanSode`)。⛔ Stage3 の城の石垣では積まない。
            var sodeWalls = SodeWallsOf(name);
            int sodeMade = 0, sodeMiter = 0, sodeLifted = 0, sodeRefused = 0; var sodeWarn = new List<string>();
            float sodeLiftMax = 0f, sodeProudMax = 0f, sodeDigMax = 0f; int sodeDug = 0; var sodeFace = new Dictionary<GameObject, Vector3>();
            var dans = new GameObject[spans.Count];
            var sodeRow = new Dictionary<string, GameObject[]>(); var sodeSide = new Dictionary<string, int>();
            var sodeDepth = new Dictionary<string, float[]>(); int sodeDeep = 0;
            foreach (var k in sodeWalls.Keys) { sodeRow[k] = new GameObject[spans.Count]; sodeDepth[k] = new float[spans.Count]; }
            for (int i = 0; i < spans.Count; i++)
            {
                var sp = spans[i] as List<object>; if (sp == null || sp.Count < 3) continue;
                float s0 = Cv(sp[0]), s1 = Cv(sp[1]), face = Cv(sp[2]);
                // ⭐ 段石は**段の両端(段の境)を結ぶ弦**で据える(EDO-0415 ③)。⛔ 段の中ほどの点の向きで据えない —
                //   折れ点が段の中にあると、隣の段と境の点を共有せず、曲がりで段石の小口と袖が継ぎ目の線に沿って
                //   最大 0.036m 目違う(2026-09-23 女坂の実測)。弦なら隣の段と境の点を共有し、留めの軸と一致する。
                //   折れの角は前後二つの継ぎ目に分かれる(`EdoBuild.MiterIshidanSode` が両端を切る)。
                Vector2 p0, p1, d0, d1; PolyAt(pts, s0, out p0, out d0); PolyAt(pts, s1, out p1, out d1);
                Vector2 pos = (p0 + p1) * 0.5f, dir = (p1 - p0).sqrMagnitude > 1e-8f ? (p1 - p0).normalized : d0;
                // 部材の原点 = 踏面の中心・**踏面の天端**。⛔ SeatBottom で据えない(地中の胴がある)。
                float y = face + keri;
                // ローカル +Z = 見え面 = **坂下**。
                var dg = EdoBuild.Place(P.Dan(keri, fumi, wM, i), new Vector3(pos.x, y, pos.y),
                               YawZ(-dir), Vector3.one, grp, "Dan_" + i.ToString("00"));
                made++;
                if (dg == null) continue;
                dans[i] = dg;
                foreach (var kv in sodeWalls)
                {
                    // 土留めの線がこの段の脇に来ていなければ据えない(線の外の段)
                    Vector2 c = new Vector2(pos.x, pos.y);
                    if (DistToPoly(kv.Value, c) > wM * 0.5f + 1.0f) continue;
                    // ⭐ 袖の run が走る段だけ(EdoBuild.OverlapAlong)── 切り込みの中は返しの土留めが持つ(EDO-0442「1=B」)
                    if (EdoBuild.OverlapAlong(p0, p1, kv.Value) < 0.02f) continue;
                    int side = EdoBuild.IshidanSodeSide(dg, kv.Value);
                    // ⭐ `copingRise:"groundHi"`(裁定 EDO-0182 (a))の袖は天端を脇の地盤まで上げて据える
                    //   (`EdoBuild.PlaceIshidanSode` が袖の背の線で地表を測って上げる)。
                    // ⛔ 袖は段の脇に途切れなく建てる(EDO-0421)。外の1点の地盤で「切通しだから建てない」と決めない —
                    //   袖が抜けた段は 2m 格子の地形が段を描けず、段石の端が三角に出る。宣言の無い袖は `"line"` として扱う。
                    var twd = FindByName(Doc, "terraceWalls", kv.Key);
                    // ⭐ `copingRise:"line"`(施主 2026-09-25): 天端は段の線に置き、背の地盤は Stage9 の皮で天端 − 0.05 から法で下げる
                    string cr = twd != null ? S(twd, "copingRise") : null;
                    bool line = cr != "groundHi", gHi = true;
                    string w; EdoBuild.SodeRise rz;
                    //   ⭐ 丈は上げの上限に足りる最小を選ぶ(`EdoBuild.PlaceIshidanSodeByDepth`・足りなければ退ける)
                    int ic = i;
                    // ⭐ 積みが野面の乱積みの袖(`masonry`)は野面の袖 `IshidanSodeNozura`(同じ局所座標・接する面 ── 差し替えだけ。丈は標準の一種)
                    bool nozura = twd != null && (S(twd, "masonry") ?? "").Contains("野面");
                    System.Func<float, string> sodePath = d => EdoAssets.Own.IshidanSode(keri, fumi, ic, d);
                    if (nozura) sodePath = d => EdoAssets.Own.IshidanSodeNozura(keri, fumi, ic);
                    var sg = EdoBuild.PlaceIshidanSodeByDepth(dg, sodePath,
                                                              nozura ? new[] { EdoAssets.Own.ISHIDAN_SODE_DEPTH_STD } : EdoAssets.Own.IshidanSodeDepths, side, grp,
                                                              kv.Key + "_" + i.ToString("000") + "f", gHi, out w, out rz, line,
                                                              SodeFootAt, SODE_NEIRI);
                    if (rz.dig > 0f) { sodeDug++; sodeDigMax = Mathf.Max(sodeDigMax, rz.dig); }
                    if (w != null) sodeWarn.Add(w);
                    if (rz.refused) { sodeRefused++; continue; }
                    if (rz.lift > 0f) { sodeLifted++; sodeLiftMax = Mathf.Max(sodeLiftMax, rz.lift); sodeProudMax = Mathf.Max(sodeProudMax, rz.proud); }
                    if (sg != null && rz.depth > EdoAssets.Own.ISHIDAN_SODE_DEPTH_STD + 1e-3f) sodeDeep++;
                    if (sg != null) { sodeMade++; sodeRow[kv.Key][i] = sg; sodeDepth[kv.Key][i] = rz.depth; sodeSide[kv.Key] = side; sodeFace[sg] = -dg.transform.right * side; }
                }
            }
            string topLine = null;
            if (topFace != null && dans.Length > 0 && dans[dans.Length - 1] != null)
            {
                float tr = float.MinValue; foreach (var v in EdoBuild.Body(dans[dans.Length - 1].transform, 999999)) tr = Mathf.Max(tr, v.y);
                float dd = tr - topY;
                topLine = "    " + (Mathf.Abs(dd) > 0.005f ? "⛔ " : "") + "最上段の踏面 − 面 " + topFace + " = " + dd.ToString("+0.000;-0.000") + "m(" + topKind + ")";
            }
            // ⭐ 曲がる石段(女坂)は折れの前後の袖を留めに切る(`EdoBuild.MiterIshidanSode`)
            foreach (var kv in sodeRow)
                if (sodeSide.ContainsKey(kv.Key))
                    sodeMiter += EdoBuild.MiterIshidanSode(dans, kv.Value, sodeSide[kv.Key], keri, fumi, wM, sodeWarn, sodeDepth[kv.Key]);
            // ⭐ 天端が水平な袖(指図 terraceWalls[].part「段k = 天端が水平な袖」── 参道の階の段4・施主裁定 2026-09-27 EDO-0437)。
            //   段 k の斜めの袖を、走りを踏面の実長で焼いた水平の袖へ差し替え、段 k−1 の斜めの袖の坂上の端に天端・脇の面・小口を揃え(EdoBuild.LayFlatSode)、
            //   坂上の小口は段 k の上の端と同じ通りに揃える(見切り・joints「段4 の上の端」)。⛔ ピボットで合わせない。
            //   ⚠ 男坂の最上段の水平な袖は踏み止め(Stage5b)が持つ ── 指図 part に宣言の無い袖はここで触らない。
            foreach (var key in new List<string>(sodeRow.Keys))
            {
                var twdF = FindByName(Doc, "terraceWalls", key); string partDecl = twdF != null ? (S(twdF, "part") ?? "") : "";
                var mk = System.Text.RegularExpressions.Regex.Match(partDecl, @"段(\d+) = \**天端が水平な袖");
                int k; if (!mk.Success || !int.TryParse(mk.Groups[1].Value, out k)) continue;
                var row = sodeRow[key];
                if (k < 1 || k >= row.Length || row[k] == null || row[k - 1] == null || dans[k] == null) { sodeWarn.Add(key + ": ⛔ 段" + k + " の水平な袖 ── 段 " + k + " か一つ下の袖が据わっていない"); continue; }
                EdoBuild.FlatSode fr; string fw;
                // 走りは段 k の踏面の**見えている実長**(段鼻 → 上の端 ── 最上段は胴の 0.1 も見える ⇒ 0.642)で焼いた版を引き、伸縮 ≈1 で据える
                //   (2026-09-27 EDO-0437 ── fumi 0.542 の版は 1.184 倍に伸びた)。焼いていなければ fumi の版(伸ばして据える・⚠)。
                float runLen = fumi;
                {
                    Vector3 upR = -dans[k].transform.forward; var fv = EdoBuild.Body(dans[k].transform, 999999, true); float fTop = float.MinValue;
                    foreach (var p in fv) fTop = Mathf.Max(fTop, p.y);
                    float a0 = float.MaxValue, a1 = float.MinValue; foreach (var p in fv) if (p.y >= fTop - 0.02f) { float a = Vector3.Dot(p, upR); a0 = Mathf.Min(a0, a); a1 = Mathf.Max(a1, a); }
                    float meas = Mathf.Round((a1 - a0) * 1000f) / 1000f;
                    if (a1 > a0 && AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Own.IshidanSodeFlat(EdoAssets.Own.ISHIDAN_SODE_DEPTH_STD, meas)) != null) runLen = meas;
                    else sodeWarn.Add(key + ": ⚠ 段" + k + " の踏面の見え " + meas.ToString("F3") + " の水平な袖が焼けていない ── " + fumi.ToString("F3") + " の版を伸ばして据える");
                }
                float runL = runLen;
                var flat = EdoBuild.LayFlatSode(row[k], row[k - 1], d => EdoAssets.Own.IshidanSodeFlat(d, runL), EdoAssets.Own.IshidanSodeDepths,
                                                -dans[k].transform.forward, null, float.NaN, 0f, out fr, out fw, dans[k]);
                if (flat == null) { sodeWarn.Add(key + ": ⛔ 段" + k + " の水平な袖を据えられない ── " + fw); continue; }
                row[k] = flat;
                sb.AppendLine("    " + flat.name + " ── 天端が水平な袖(丈 " + fr.depth.ToString("F2") + ")天端 " + fr.topLo.ToString("F3") + "〜" + fr.topHi.ToString("F3") +
                              "(下の袖の坂上の端 " + fr.topBelow.ToString("F3") + "・段差 " + fr.step.ToString("+0.000;-0.000") + ")/ 脇の面の食い違い " + fr.sideIn.ToString("+0.000;-0.000") + "・" + fr.sideOut.ToString("+0.000;-0.000") +
                              " / 下の袖との口 " + (float.IsNaN(fr.gapBelow) ? "—" : fr.gapBelow.ToString("+0.000;-0.000")) +
                              " / 坂上の小口 − 段" + k + " の上の端 " + (float.IsNaN(fr.gapMate) ? "—" : fr.gapMate.ToString("+0.000;-0.000")) + "(伸縮 " + (float.IsNaN(fr.ext) ? "—" : fr.ext.ToString("+0.000;-0.000")) + ")" +
                              (fw != null ? " / " + fw : ""));
            }
            // ⭐ 袖の天端は外の地盤と同じ高さ ── 天端の下の節点と芝を納める(EDO-0414・⛔ 地形の編集は Undo の外)
            var sodeAll = new List<GameObject>(); var faceAll = new Dictionary<GameObject, Vector3>();
            foreach (var kv in sodeRow)
                foreach (var g in kv.Value)
                {
                    if (g == null) continue;
                    sodeAll.Add(g);
                    // 留めへ差し替えた駒は別の GameObject ⇒ 見え面は同じ側(段石の方)を名から引き直す
                    Vector3 f;
                    if (!sodeFace.TryGetValue(g, out f))
                    {
                        int ii; string nm = g.name; int us = nm.LastIndexOf('_');
                        if (us > 0 && int.TryParse(nm.Substring(us + 1).TrimEnd('f'), out ii) && ii < dans.Length && dans[ii] != null
                            && sodeSide.ContainsKey(kv.Key))
                            f = -dans[ii].transform.right * sodeSide[kv.Key];
                    }
                    if (f != Vector3.zero) faceAll[g] = f;
                }
            string sodeTuck = null;
            if (sodeAll.Count > 0)
            {
                var tk = EdoBuild.TuckUnderCrest(sodeAll, null, faces: faceAll);
                sodeTuck = (tk.thin > 0 ? "⛔ " : "") + "袖の天端の下の地形: " + tk;
                EditorUtility.SetDirty(EdoBuild.T().terrainData);
            }
            sb.AppendLine("  " + name + ": 段石 " + made + " 段(蹴上 " + keri.ToString("F3") +
                          " / 踏面 " + fumi.ToString("F3") + " / 幅 " + wM.ToString("F3") + ")" +
                          (sodeWalls.Count > 0 ? " / 袖 " + sodeMade + " 駒(" + string.Join("・", sodeWalls.Keys) + ")" +
                           (sodeLifted > 0 ? " / 天端を地盤まで上げた " + sodeLifted + " 駒(最大 " + sodeLiftMax.ToString("F2") +
                                             "m・背で地表より出る 最大 " + sodeProudMax.ToString("F2") + "m)" : "") +
                           (sodeDeep > 0 ? " / 深い丈の袖 " + sodeDeep + " 駒" : "") +
                           (sodeDug > 0 ? " / 天端を段の線に置き背を下げる " + sodeDug + " 駒(最大 " + sodeDigMax.ToString("F2") + "m・Stage9 の皮)" : "") +
                           (sodeRefused > 0 ? " / ⛔ 丈が足りず据えなかった " + sodeRefused : "") +
                           (sodeMiter > 0 ? " / 留めの継ぎ目 " + sodeMiter : "") : ""));
            if (topLine != null) sb.AppendLine(topLine);
            foreach (var w in sodeWarn) sb.AppendLine("    ⚠ " + w);
            if (sodeTuck != null) sb.AppendLine("    " + sodeTuck);
        }
        AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        return "石段\n" + sb;
    }
    /// <summary>石段 <paramref name="kaidan"/> に沿う袖の土留め(`terraceWalls` の coping:"stair" で
    /// `vFrom.kaidan` か `copingFrom.kaidan` がこの石段)→ 算出物の折れ線。</summary>
    static Dictionary<string, List<Vector2>> SodeWallsOf(string kaidan)
    {
        var r = new Dictionary<string, List<Vector2>>();
        foreach (var o in L(Doc, "terraceWalls"))
        {
            var tw = o as Dictionary<string, object>; if (tw == null || !IsSodeWall(tw)) continue;
            var vf = G(tw, "vFrom") as Dictionary<string, object>;
            var cf = G(tw, "copingFrom") as Dictionary<string, object>;
            if (!((vf != null && S(vf, "kaidan") == kaidan) || (cf != null && S(cf, "kaidan") == kaidan))) continue;
            var run = FindByName(Impl, "runs", S(tw, "name"));
            if (run != null) r[S(tw, "name")] = Pts(L(run, "nodes"));
        }
        return r;
    }
    /// <summary>取り合いの欄(`joints`)で石段 <paramref name="stair"/> の最上段の相手になっている面(`平場 <名>`)。
    /// kind = 納めの種類の頭(差し込み / 被せ)。無ければ false。</summary>
    static bool TopFaceOf(string stair, out string face, out Vector2[] poly, out float y, out string kind)
    {
        face = null; poly = null; y = 0f; kind = null;
        foreach (var o in L(Doc, "joints"))
        {
            var j = o as Dictionary<string, object>; if (j == null) continue;
            string a = S(j, "a"), b = S(j, "b"), af = S(j, "aFace");
            if (a == null || b == null || af == null || !a.StartsWith("石段 ") || !b.StartsWith("平場 ") || !af.Contains("最上段")) continue;
            if (a.Substring(3) != stair) continue;
            // 面の名 = `terraces` の名のうち b に現れる物(「平場 中の段 Shaden_Chu(…)」の形もある)
            Dictionary<string, object> tc = null; string fn = null;
            foreach (var to in L(Impl, "terraces"))
            {
                var t0 = to as Dictionary<string, object>; string n0 = t0 == null ? null : S(t0, "name");
                if (n0 == null || !System.Text.RegularExpressions.Regex.IsMatch(b, "(^|[^A-Za-z_])" + n0 + "([^A-Za-z_]|$)")) continue;
                if (fn == null || n0.Length > fn.Length) { fn = n0; tc = t0; }
            }
            if (tc == null) continue;
            var wl = L(tc, "world"); poly = new Vector2[wl.Count];
            for (int i = 0; i < wl.Count; i++) { var q = wl[i] as List<object>; poly[i] = new Vector2(Cv(q[0]), Cv(q[1])); }
            face = fn; y = F(tc, "y"); string k = S(j, "kind") ?? ""; int c2 = k.IndexOf('('); kind = c2 > 0 ? k.Substring(0, c2) : k;
            return true;
        }
        return false;
    }
    /// <summary>袖の底の根入れ[m](取り合いの欄 joints[69]「底は面より 0.05 下」)。</summary>
    const float SODE_NEIRI = 0.05f;
    /// <summary>袖の見え面の足元の**設計面**(算出物 graded の双一次。設計面の外 = 造成しない所は地形)。
    /// ⛔ 皮(描かれた地表)で測らない ── 皮は袖の底へ寄せて持ち上がる(男坂の下り側の端で +0.25 の小山)。</summary>
    static float SodeFootAt(float x, float z) { float y; return Gr.Bilinear(x, z, out y) ? y : EdoBuild.Ground(x, z); }

    /// <summary>石段に沿う土留め = 袖(石段の組で据える)か。</summary>
    static bool IsSodeWall(Dictionary<string, object> tw) { return S(tw, "coping") == "stair"; }
    static float DistToPoly(List<Vector2> p, Vector2 c)
    {
        float bd = float.MaxValue;
        for (int i = 1; i < p.Count; i++)
        {
            Vector2 a = p[i - 1], ab = p[i] - a; float l2 = ab.sqrMagnitude;
            float u = l2 < 1e-9f ? 0f : Mathf.Clamp01(Vector2.Dot(c - a, ab) / l2);
            bd = Mathf.Min(bd, Vector2.Distance(a + ab * u, c));
        }
        return bd;
    }
    /// <summary>指図の名 → シーンの群の名。⛔ 綴りの読み替えだけ(⭐ 対応表が消えるのが正しい終点)。</summary>
    public static string GroupNameOf(string designName)
    {
        if (designName.StartsWith("男坂")) return "Otokozaka";
        if (designName.StartsWith("女坂")) return "Onnazaka";
        if (designName.StartsWith("参道の階")) return "SandoKai";
        return designName;
    }

    // ================================================================ Stage 3 土留め
    [MenuItem(MENU + "3 土留め(13本。⛔ 埋まっている区間は建てない)")]
    public static void Stage3Menu() { Debug.Log("[山王] " + Stage3_Dodome()); }
    /// <summary>算出物 `runs` の `of=="wall"` を石垣で積む。天端は `profile` の第2列
    /// (⛔ 実装が引き直さない — `coping:"stair"` の4本は石段の割付から引いてある)。
    /// ⛔ **見付高 ≤ 0 かつ 受け高 > 0 の区間は建てない**(土に埋まった石垣を積まない・裁定 EDO-0182 が未着手)。</summary>
    public static string Stage3_Dodome()
    {
        var gate = Gate(); if (gate != null) return gate;
        { var us = UnSkin(); if (us.Length > 0) Debug.Log("[山王] " + us); }
        var grp = Group("Dodome"); Clear(grp);
        float probe = WallProbeM;
        var sb = new StringBuilder();
        int total = 0, buried = 0, buriedWhole = 0, buriedKept = 0; float buriedM = 0f;
        var placed = new List<GameObject>();
        // 出隅の隅の駒のため: run ごとの駒と、端点ごとの外向き(EdoBuild.PlaceRunKado)
        var runPieces = new Dictionary<string, List<GameObject>>();
        var segPieces = new Dictionary<string, List<GameObject>>();                         // run#区間 → 駒(折れ線の途中の角も隅にする)
        var runEnds = new List<EdoBuild.RunEnd>();                                            // 区間の端ごとの外向きと走り
        var faceOf = new Dictionary<GameObject, Vector2>();                                  // 駒 → 見え面の向き(低い側)
        var segLine = new Dictionary<string, Vector2[]>();                                   // run#区間 → [a, b, 外向き](二段築の下段が測る)
        var dgS = EdoBuild.Drawn();
        float wallDepth; { var bv = EdoBuild.BodyAt(EdoAssets.JC.CastleWall, Vector3.zero, 0f, true); float x0 = float.MaxValue, x1 = float.MinValue;
            foreach (var v in bv) { x0 = Mathf.Min(x0, v.x); x1 = Mathf.Max(x1, v.x); } wallDepth = bv.Count > 0 ? x1 - x0 : 2.4f; }

        // ⚠ 天端の両側が同じ高さの壁(= 基壇。回廊の 4本)は「低い側」が決まらない。
        //   ⇒ **同じ接頭辞の壁が囲む矩形の外**を外向きとする(名から導く群 = TW_Kairo など)。
        var famC = new Dictionary<string, Vector2>(); var famN = new Dictionary<string, int>();
        foreach (var o in L(Impl, "runs"))
        {
            var w0 = o as Dictionary<string, object>; if (w0 == null || S(w0, "of") != "wall") continue;
            string fam = FamilyOf(S(w0, "name"));
            foreach (var q in Pts(L(w0, "nodes")))
            {
                if (!famC.ContainsKey(fam)) { famC[fam] = Vector2.zero; famN[fam] = 0; }
                famC[fam] = famC[fam] + q; famN[fam] = famN[fam] + 1;
            }
        }
        foreach (var k in new List<string>(famC.Keys)) famC[k] = famC[k] / famN[k];
        // ⭐ 基壇の区間(建つ所の受け高が全て負 = 天端が両側の地盤より上)は、地表でなく端で継ぐ基壇の壁の走りで向きを決める
        //   (EdoBuild.BlockOutward・2026-09-25)。⛔ 同族の重心から外へ、は門で割れた基壇で妻の石垣を塊の内へ向けた。
        var baseSegs = new List<Vector2[]>();
        foreach (var o in L(Impl, "runs"))
        {
            var w0 = o as Dictionary<string, object>; if (w0 == null || S(w0, "of") != "wall") continue;
            var tw0 = FindByName(Doc, "terraceWalls", S(w0, "name"));
            if (tw0 != null && (IsSodeWall(tw0) || !string.IsNullOrEmpty(S(tw0, "masonry")))) continue;
            var nd0 = Pts(L(w0, "nodes")); var pr0 = L(w0, "profile"); float st0 = F(w0, "profileStep");
            foreach (var so in L(w0, "segs"))
            {
                var sg = so as List<object>; if (sg == null || sg.Count < 2) continue;
                Vector2 a0 = P2(sg[0]), b0 = P2(sg[1]);
                if (SegIsBase(pr0, st0, ArcOf(nd0, a0), Vector2.Distance(a0, b0))) baseSegs.Add(new[] { a0, b0 });
            }
        }
        var nozuraRuns = new List<Dictionary<string, object>>();
        int flipLocal = 0;
        // ⭐ 駒より短い区間の出隅を測るため、全ての土留めの区間(EdoBuild.ShortSegConvexEnd)
        var allWallSegs = new List<Vector2[]>();
        foreach (var o in L(Impl, "runs"))
        {
            var w0 = o as Dictionary<string, object>; if (w0 == null || S(w0, "of") != "wall") continue;
            foreach (var so in L(w0, "segs")) { var sg = so as List<object>; if (sg != null && sg.Count >= 2) allWallSegs.Add(new[] { P2(sg[0]), P2(sg[1]) }); }
        }
        var flushLog = new List<string>();
        // ⭐ 石段の口で切れる土留めの端は、袖の外面で止める(EdoBuild.RunEndAtFace・指図 joints「土留めは袖の外面で止め、端に隅の塊を置かない」
        //   2026-09-26 EDO-0430)。袖は Stage2 が据えた実メッシュで測る ── **据える前に**区間の端を決め、駒の割りはその長さで取る。
        var sodeEnds = new List<KeyValuePair<Vector2, string>>();     // 袖の run の端点 → 袖の名
        var sodeDir = new Dictionary<Vector2, Vector2>();               // 袖の run の端点 → その端の区間の走り
        foreach (var o in L(Impl, "runs"))
        {
            var w0 = o as Dictionary<string, object>; if (w0 == null || S(w0, "of") != "wall") continue;
            var tw0 = FindByName(Doc, "terraceWalls", S(w0, "name")); if (tw0 == null || !IsSodeWall(tw0)) continue;
            var nd0 = Pts(L(w0, "nodes")); if (nd0.Count < 2) continue;
            sodeEnds.Add(new KeyValuePair<Vector2, string>(nd0[0], S(w0, "name")));
            sodeEnds.Add(new KeyValuePair<Vector2, string>(nd0[nd0.Count - 1], S(w0, "name")));
            sodeDir[nd0[0]] = (nd0[1] - nd0[0]).normalized; sodeDir[nd0[nd0.Count - 1]] = (nd0[nd0.Count - 1] - nd0[nd0.Count - 2]).normalized;
        }
        var sodeStopLog = new List<string>();

        foreach (var o in L(Impl, "runs"))
        {
            var wl = o as Dictionary<string, object>; if (wl == null || S(wl, "of") != "wall") continue;
            string name = S(wl, "name");
            // ⭐ 石段の袖は Stage2 が段ごとに石段と同じ材で据える(EDO-0415)。⛔ 城の石垣で積まない。
            var twDoc = FindByName(Doc, "terraceWalls", name);
            if (twDoc != null && IsSodeWall(twDoc)) { sb.AppendLine("  " + name + ": 石段の袖 — Stage2 で据えた"); continue; }
            // ⛔ 積みが城の石垣でない土留め(`masonry` = 野面の乱積み ほか)は城の石垣の駒で積まない ── 別の部材で据える
            //   ⭐ 野面の乱積みは城の石垣と隅の駒を据えた後に、隣の石垣の実面を測って据える(下の EdoBuild.PlaceNozuraRun)
            if (twDoc != null && !string.IsNullOrEmpty(S(twDoc, "masonry")))
            { nozuraRuns.Add(wl); continue; }
            var nodes = Pts(L(wl, "nodes"));
            var prof = L(wl, "profile");
            float step = F(wl, "profileStep");
            int made = 0; float skipM = 0f;
            var mine = new List<GameObject>(); runPieces[name] = mine;
            Vector2 n0 = nodes.Count > 0 ? nodes[0] : Vector2.zero, n1 = nodes.Count > 0 ? nodes[nodes.Count - 1] : Vector2.zero;

            // ⭐ 一本の run の低い側の手(EdoBuild.RunLowHand)── 区間の票が割れたときに使う(⛔ 右手に倒さない)
            int runHand;
            {
                var sl = new List<Vector2[]>(); var sb0 = new List<float>();
                foreach (var so in L(wl, "segs")) { var sg0 = so as List<object>; if (sg0 == null || sg0.Count < 2) continue; var q0 = P2(sg0[0]); sl.Add(new[] { q0, P2(sg0[1]) }); sb0.Add(ArcOf(nodes, q0)); }
                runHand = EdoBuild.RunLowHand(sl, (x, z) => dgS.At(x, z), wallDepth + probe, 0.05f, (k, ss) =>
                {
                    float t0, f0, b0; return ProfileAt(prof, step, sb0[k] + ss, out t0, out f0, out b0) && f0 > BURIED_EPS;
                });
            }
            int segI = -1;
            foreach (var so in L(wl, "segs"))
            {
                var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
                segI++;
                Vector2 a = P2(seg[0]), b = P2(seg[1]);
                // 区間の端が石段の袖の端点に重なるなら、袖の外面で止める(EdoBuild.RunEndAtFace)。斜めに当たる端は動かさず ★ で差し戻す。
                bool stopA = false, stopB = false;
                for (int e2 = 0; e2 < 2; e2++)
                {
                    Vector2 ep = e2 == 0 ? a : b, other = e2 == 0 ? b : a;
                    string sode = null; Vector2 sdir = Vector2.zero;
                    foreach (var kv in sodeEnds) if (Vector2.Distance(kv.Key, ep) < 0.05f) { sode = kv.Value; sdir = sodeDir[kv.Key]; break; }
                    if (sode == null || Vector2.Distance(ep, other) < 1e-3f) continue;
                    // ⛔ 袖が土留めの通りをそのまま続ける端(一直線の継ぎ ── 御供所の郭 EK × 郭の階の南の袖・前庭の切り込み × 参道の階の袖)は
                    //   ここで止めない ── その取り合いは段石・袖の端の切り(CutStairEndsToBatter)が受け持つ。止めると参道の階の段1 の切りが焼いていない形に変わった(2026-09-26)。
                    if (Mathf.Abs(Vector2.Dot(sdir, (ep - other).normalized)) > 0.9f) continue;
                    var sps = new List<GameObject>();
                    foreach (var t in Group("Sando").GetComponentsInChildren<Transform>())
                        if (t.name.StartsWith(sode + "_") && t.gameObject.activeInHierarchy && Vector2.Distance(new Vector2(t.position.x, t.position.z), ep) < 4f) sps.Add(t.gameObject);
                    var st = EdoBuild.RunEndAtFace(ep, (ep - other).normalized, sps);
                    if (!st.found) { sodeStopLog.Add("⚠ " + name + " の端 " + ep.ToString("F2") + ": 袖 " + sode + " の駒が無い(Stage2 が先)"); continue; }
                    if (st.oblique)
                    {
                        sodeStopLog.Add("★ " + name + " の端 " + ep.ToString("F2") + " × 袖 " + sode + "(" + st.with + "): 袖の外面が走りに " + (90f - st.angleDeg).ToString("F1") +
                                        "° で斜めに交わる ── 直の小口では面で当たらない。端を切った駒が要る(部材の話・差し戻し)。端は動かしていない");
                        continue;
                    }
                    if (st.move > 0.15f) { sodeStopLog.Add("⚠ " + name + " の端: 袖の外面まで " + st.move.ToString("F3") + "m 足りない ── 延ばさない(継ぎ目が開く)"); continue; }
                    if (e2 == 0) { a = st.end; stopA = true; } else { b = st.end; stopB = true; }
                    sodeStopLog.Add(name + " の端を袖 " + sode + " の外面(" + st.with + ")で止めた: " + st.move.ToString("+0.000;-0.000") + "m(角 " + st.angleDeg.ToString("F1") + "°)");
                }
                float len = Vector2.Distance(a, b); if (len < 0.4f) continue;
                string segKey = name + "#" + segI; var segMine = new List<GameObject>(); segPieces[segKey] = segMine;
                Vector2 dir = (b - a) / len;
                // seg の始点が run の折れ線のどこか(s の原点合わせ)
                float sBase = ArcOf(nodes, a);
                int N = (len <= IG_RUN) ? 1 : Mathf.CeilToInt((len - IG_RUN) / IG_PITCH_MAX) + 1;
                float pitch = (N > 1) ? (len - IG_RUN) / (N - 1) : 0f;
                float head = (len <= IG_RUN) ? (len + IG_RUN) * 0.5f : IG_RUN;

                // ⭐ 見え面 = 低い側。**描かれた地表を線の両側で測って**決める(EdoBuild.LowSide・普請奉行の決め 2026-09-25)。
                //   測る所は駒の奥行(実メッシュ)+ wallProbeM だけ線から離す(据えていた駒の天端の下を下げた節点を拾わない)。
                //   ⛔ 建つ区間だけで投票する。
                Vector2 nrm = new Vector2(dir.y, -dir.x);      // dir の右手
                int voteN = 0, voteX = 0;
                float sB = sBase;
                bool isBase = SegIsBase(prof, step, sBase, len);
                Vector2 lowN = isBase ? Vector2.zero : EdoBuild.LowSide(a, b, (x, z) => dgS.At(x, z), wallDepth + probe, 0.05f, ss =>
                {
                    float t0, f0, b0; return ProfileAt(prof, step, sB + ss, out t0, out f0, out b0) && f0 > BURIED_EPS;
                }, out voteN, out voteX);
                Vector2 outw;
                if (isBase && EdoBuild.BlockOutward(a, b, baseSegs) != Vector2.zero) outw = EdoBuild.BlockOutward(a, b, baseSegs);
                else if ((lowN == Vector2.zero || voteN == voteX) && runHand != 0)
                {   // 票が無い・割れた区間は同じ run の手で(EdoBuild.RunLowHand)
                    outw = runHand > 0 ? nrm : -nrm;
                    if (voteX > 0) sb.AppendLine("  ⚠ " + name + " の区間で低い側が割れた(" + voteN + " 対 " + voteX + ")— run の手(" + (runHand > 0 ? "右" : "左") + ")で決めた");
                    voteX = 0;
                }
                else if (lowN == Vector2.zero)
                {
                    // 両側が同じ高さで継ぐ基壇の壁も無い ⇒ 同族の壁が囲む中心から外へ(最後の手)。
                    Vector2 mid = (a + b) * 0.5f;
                    Vector2 away = mid - famC[FamilyOf(name)];
                    outw = (Vector2.Dot(nrm, away) >= 0f) ? nrm : -nrm;
                }
                else outw = lowN;
                if (voteX > 0) sb.AppendLine("  ⚠ " + name + " の区間で低い側が割れた(" + voteN + " 対 " + voteX + ")— 多い方へ向けた");
                // ローカル +X を外へ・+Z を走りへ。⇒ 走りの向きは外向き法線から決まる
                Vector2 run = (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) >= 0f) ? dir : -dir;
                Vector2 A = (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) >= 0f) ? a : b;
                float psi = Mathf.Atan2(run.x, run.y) * Mathf.Rad2Deg;
                // ⭐ 駒より短い区間は駒を出隅の側へ突き付け、余りを入隅の側で重ねる(EdoBuild.ShortSegConvexEnd・FlushRunEnd)。
                //   ⛔ 芯に置かない ── 切り込みの返し(1.7m)で出隅の駒が前庭の北の天端の線より 0.146m 前へ出た(2026-09-25)。
                Vector2 flushEnd = Vector2.zero, flushToward = Vector2.zero;
                if (N == 1 && len < IG_RUN - 1e-3f)
                {
                    int ce = EdoBuild.ShortSegConvexEnd(a, b, outw, allWallSegs);
                    // ⭐ 袖の外面で止めた端は必ず面一に(余りをそこから出すと袖へめり込む ── 前庭の西 1.35m の区間で 0.32・2026-09-26)。
                    //   余りは反対の端(入隅なら相手の土留めの中・出隅なら隅の駒の腕の中)で重ねる。
                    if (stopA != stopB) ce = stopA ? 1 : -1;
                    if (ce != 0)
                    {
                        flushEnd = ce > 0 ? a : b;
                        flushToward = (flushEnd - (ce > 0 ? b : a)) / len;
                        head = Vector2.Distance(A, flushEnd) < 1e-3f ? IG_RUN : len;
                    }
                }
                segLine[segKey] = new Vector2[] { a, b, outw };
                // 区間の両端(run の端も折れ線の途中の節点も)── 出隅と一直線の継ぎ目は EdoBuild.PlaceRunCorners が見分ける
                foreach (var ep in new Vector2[] { a, b })
                {
                    int node = -1; for (int k = 0; k < nodes.Count; k++) if (Vector2.Distance(nodes[k], ep) < 0.05f) { node = k; break; }
                    runEnds.Add(new EdoBuild.RunEnd { key = segKey, run = name, node = node, p = ep, outw = outw, away = (ep == a ? dir : -dir) });
                }

                for (int i = 0; i < N; i++)
                {
                    float sMid = head + pitch * i - IG_RUN * 0.5f;      // 駒の芯(pivot から −Z へ 2m)
                    Vector2 p = A + run * (head + pitch * i);
                    Vector2 c = A + run * sMid;
                    float sRun = sBase + Vector2.Distance(a, c);
                    float top, faceH, backH;
                    if (!ProfileAt(prof, step, sRun, out top, out faceH, out backH)) continue;
                    // ⛔ 埋まっている区間は建てない(見付 ≤ 0 かつ 受け > 0)
                    if (faceH <= BURIED_EPS && backH > BURIED_EPS)
                    { buried++; skipM += (N > 1 ? pitch : len); continue; }
                    if (faceH <= BURIED_EPS) { buried++; skipM += (N > 1 ? pitch : len); continue; }
                    var wg = EdoBuild.Place(EdoAssets.JC.CastleWall, new Vector3(p.x, top - IG_H, p.y),
                                   psi, Vector3.one, grp, name + "_" + made.ToString("000") + "f");
                    if (wg != null)
                    {   // 見え面を低い側へ回し、天端の前の縁を線(面の縁)へ寄せる ── 実メッシュで測る
                        // ⭐ 区間を駒ごとに割って低い側を測り直す(高低が区間の途中で入れ替わる所・2026-09-25)。
                        //   駒の走り ±1m で票が出て、区間の向きと逆なら駒の向きを採る。
                        Vector2 ow = outw; int pn = 0, px = 0;
                        //   ⚠ 窓は区間の中に切る ── 短い区間で駒を出隅の側へ寄せると ±1m が入隅の先(奥の辺の裏)へ出て、返しが裏返った(2026-09-25)。
                        float sLo = Mathf.Max(0f, sMid - 1.0f), sHi = Mathf.Min(len, sMid + 1.0f);
                        //   ⚠ 駒一つの区間(N = 1)は測り直さない ── 窓が区間そのもので、区間の票(建つ所だけ・run の手)と違う票になるだけ
                        //     (切り込みの東の返しが前庭の東の土留めの外の低い地盤を拾って裏返った)。
                        //   ⭐ 測り点が他の壁の体の上に落ちる走りは数えない(EdoBuild.LowSideAwayFromWalls・2026-09-26 EDO-0437)── 体の上の地表は
                        //     天端の下へ納めた皮で、出隅の端の駒 `TW_Koshi_W_009f` がとなりの SW の体の皮を「低い」と読んで裏返った。
                        Vector2 lowP = isBase || N == 1 || sHi - sLo < 0.2f ? Vector2.zero : EdoBuild.LowSide(A + run * sLo, A + run * sHi, (x, z) => dgS.At(x, z), wallDepth + probe, 0.05f,
                            EdoBuild.LowSideAwayFromWalls(A + run * sLo, A + run * sHi, wallDepth + probe, allWallSegs, new[] { a, b }, wallDepth), out pn, out px);
                        if (lowP != Vector2.zero && pn > px && Vector2.Dot(lowP, outw) < 0f) { ow = lowP; flipLocal++; }
                        EdoBuild.FaceWallToLine(wg, ow, a);
                        if (flushToward != Vector2.zero)
                        {
                            float mv = EdoBuild.FlushRunEnd(wg, flushEnd, flushToward);
                            flushLog.Add(wg.name + " 出隅の端へ " + mv.ToString("+0.000;-0.000") + "m(区間 " + len.ToString("F2") + "m・余りは入隅の側)");
                        }
                        placed.Add(wg); mine.Add(wg); segMine.Add(wg); faceOf[wg] = ow;
                    }
                    made++;
                }
                // ⭐ 硬い条件(許容0 の埋没・joints[68]): 天端が見え面の前の地表の下に来る駒 = 全体が埋まる駒は置かない
                //   (EdoBuild.CrestAboveGround)。退けると隣の駒の小口が地表より上に出るなら、その駒は残す ──
                //   端は小口が地表の下へ入る所で止める(EdoBuild.EndAboveGround・joints[67])。
                {
                    var bur = new List<GameObject>();
                    foreach (var g in segMine)
                    { float ea = EdoBuild.CrestAboveGround(g, faceOf[g], (x, z) => dgS.At(x, z)); if (!float.IsNaN(ea) && ea <= 0f) bur.Add(g); }
                    foreach (var g in bur)
                    {
                        int j = segMine.IndexOf(g); bool keep = false;
                        foreach (int nj in new[] { j - 1, j + 1 })
                        {
                            if (nj < 0 || nj >= segMine.Count || bur.Contains(segMine[nj])) continue;
                            var nb = segMine[nj]; var bc = EdoBuild.RB(g).center; var nc = EdoBuild.RB(nb).center;
                            float ex = EdoBuild.EndAboveGround(nb, new Vector2(bc.x - nc.x, bc.z - nc.z), (x, z) => dgS.At(x, z));
                            if (!float.IsNaN(ex) && ex > 0.01f) keep = true;
                        }
                        if (keep) { buriedKept++; continue; }
                        segMine.Remove(g); mine.Remove(g); placed.Remove(g); faceOf.Remove(g);
                        UnityEngine.Object.DestroyImmediate(g); made--; buriedWhole++;
                    }
                }
            }
            total += made; buriedM += skipM;
            sb.AppendLine("  " + name + ": 駒 " + made + " 枚" +
                          (skipM > 0.05f ? " / ⛔ 埋まっていて建てなかった " + skipM.ToString("F1") + "m" : ""));
        }
        // ⭐ 石段の最上段を受ける土留めの区間(指図 joints の「石段の最上段」への突き付け)── 天端の前の縁を最上段の背の端へ(EdoBuild.AbutCrestToStep)
        foreach (var o in L(Doc, "joints"))
        {
            var j = o as Dictionary<string, object>; if (j == null) continue;
            string ja = S(j, "a") ?? "", jb = S(j, "b") ?? "", jk = S(j, "kind") ?? "";
            if (!jk.StartsWith("突き付け") || !jb.EndsWith("の最上段")) continue;
            string stair = jb.Substring(0, jb.Length - "の最上段".Length);
            var sgrp = Group("Sando/" + GroupNameOf(stair)); GameObject topStep = null; float tsY = float.MinValue;
            foreach (Transform c in sgrp) if (c.name.StartsWith("Dan_")) { var bb = EdoBuild.RB(c.gameObject); if (bb.max.y > tsY) { tsY = bb.max.y; topStep = c.gameObject; } }
            if (topStep == null) { sb.AppendLine("  ⚠ " + ja + " × " + jb + ": 最上段の段石が無い(Stage2 が先)"); continue; }
            Vector2 sf = new Vector2(topStep.transform.forward.x, topStep.transform.forward.z).normalized;   // 段石の +Z = 坂下
            Vector2 sc = new Vector2(topStep.transform.position.x, topStep.transform.position.z);
            foreach (var kv in segLine)
            {
                string rn = kv.Key.Substring(0, kv.Key.LastIndexOf('#'));
                if (!System.Text.RegularExpressions.Regex.IsMatch(ja, "(^|[^A-Za-z_])" + rn + "([^A-Za-z_]|$)")) continue;
                Vector2 ow = kv.Value[2];
                if (Vector2.Dot(ow, sf) < 0.9f) continue;                                        // 見え面が坂下を向く区間(= 奥の辺)
                if (EdoBuild.OverlapAlong(kv.Value[0], kv.Value[1], new List<Vector2> { sc - new Vector2(sf.y, -sf.x) * 2f, sc + new Vector2(sf.y, -sf.x) * 2f }) < 0.5f) continue;
                List<GameObject> ps; if (!segPieces.TryGetValue(kv.Key, out ps) || ps.Count == 0) continue;
                float mv = EdoBuild.AbutCrestToStep(ps, ow, topStep);
                sb.AppendLine("  " + kv.Key + " の天端の前の縁を " + stair + " の最上段 " + topStep.name + " の背へ突き付けた(" + (float.IsNaN(mv) ? "測れず" : mv.ToString("+0.000;-0.000") + "m") + ")");
            }
        }
        // ⭐ 二段築の下段(指図 `terraceWalls[].tierPlan`)── 据わった上段の駒の実メッシュから測って据える(EdoBuild.PlaceTierBelow)。
        //   ⛔ 読み方の決まり(stepOut / benchM / lowerSpan)が実装の知る値でなければ建てずに差し戻す(発明しない)。
        {
            var ups = new List<EdoBuild.TierUpper>(); string refuse = null; float designTop = float.NaN;
            foreach (var o in L(Doc, "terraceWalls"))
            {
                var tw = o as Dictionary<string, object>; if (tw == null) continue;
                var tp = D(tw, "tierPlan"); if (tp == null) continue;
                string tn = S(tw, "name");
                if (S(tp, "stepOut") != "pieceDepth" || !HasNum(tp, "benchM") || Mathf.Abs(F(tp, "benchM")) > 1e-4f || S(tp, "lowerSpan") != "upperFootExposed")
                { refuse = tn; continue; }
                var tiersL = L(tp, "tiers"); if (tiersL.Count >= 2) { var t1 = tiersL[1] as Dictionary<string, object>; if (t1 != null && HasNum(t1, "coping")) designTop = F(t1, "coping"); }
                foreach (var kv in segPieces)
                {
                    if (!kv.Key.StartsWith(tn + "#")) continue;
                    Vector2[] ln; if (!segLine.TryGetValue(kv.Key, out ln)) continue;
                    kv.Value.RemoveAll(g => g == null);
                    ups.Add(new EdoBuild.TierUpper { run = tn, a = ln[0], b = ln[1], outw = ln[2], pieces = kv.Value });
                }
            }
            if (refuse != null) sb.AppendLine("  ★ " + refuse + ": tierPlan の stepOut/benchM/lowerSpan が実装の読める値でない — 下段を据えない(指図方へ)");
            if (ups.Count > 0)
            {
                var geMade = new List<GameObject>();
                int ng = EdoBuild.PlaceTierBelow(ups, EdoAssets.JC.CastleWall, IG_RUN, IG_PITCH_MAX, IG_H, (x, z) => dgS.At(x, z), probe, grp, 0.05f,
                                                 runEnds, segPieces, faceOf, geMade, sb);
                placed.AddRange(geMade);
                foreach (var g in geMade) { string rn = g.name.Substring(0, g.name.LastIndexOf('_')); List<GameObject> lst; if (!runPieces.TryGetValue(rn, out lst)) { lst = new List<GameObject>(); runPieces[rn] = lst; } lst.Add(g); }
                sb.AppendLine("  二段築の下段: 駒 " + ng + (float.IsNaN(designTop) ? "" : "(指図の下段の天端 " + designTop.ToString("F2") + ")"));
            }
        }
        // ⭐ 出隅: run の端・折れ線の途中の角が外へ凸に折れる所へ隅の駒を据える。継ぎ目が一直線の所は隅を置かない
        //   (EdoBuild.PlaceRunCorners → PlaceRunKado・両脇の実メッシュで測る)
        {
            var dg = EdoBuild.Drawn(); var kcs = new List<GameObject>();
            //   隅の腕の中へ入る石段の袖(Sando の各石段の TW_*)を渡し、腕の長さを袖の端の実測から焼いた組の中で選ぶ(EdoBuild.KadoShortArm・EDO-0437)
            var sodeAbut = new List<GameObject>();
            { var sd = Group("Sando"); foreach (Transform st in sd) foreach (Transform c in st) if (c.name.StartsWith("TW_") && c.gameObject.activeInHierarchy) sodeAbut.Add(c.gameObject); }
            int kn = EdoBuild.PlaceRunCorners(runEnds, segPieces, EdoAssets.Own.IshigakiKado, (x, z) => dg.At(x, z), grp, 0.02f, sb, kcs,
                                              sodeAbut, EdoAssets.Own.IshigakiKado);
            placed.RemoveAll(g => g == null); placed.AddRange(kcs);
            total = 0; foreach (var kv in runPieces) { kv.Value.RemoveAll(g => g == null); total += kv.Value.Count; } total += kn;
        }
        if (flipLocal > 0) sb.AppendLine("  駒ごとに測り直して見え面を区間と逆へ向けた駒 " + flipLocal + "(高低が区間の途中で入れ替わる所)");
        foreach (var fl in flushLog) sb.AppendLine("  短い区間: " + fl);
        foreach (var sl in sodeStopLog) sb.AppendLine("  袖で止める端: " + sl);
        sb.AppendLine("  天端が見え面の前の地表の下に来る駒(全体が埋まる): 退けた " + buriedWhole + " / 隣の小口を地表の下へ入れるため残した " + buriedKept);
        // ⭐ 野面の乱積みの土留め(`masonry`)── 端の揃う run を一本に継ぎ、隣の石垣の実面を測って据える(EdoBuild.PlaceNozuraRun)
        total += Nozura(nozuraRuns, grp, placed, faceOf, dgS, wallDepth + probe, sb);
        // ⭐ 石段の段石の小口・袖の背の小口を、脇の土留めの法の面へ突き付ける(EDO-0430 施主指示 2026-09-25)。⭐ 出隅の隅の駒と
        //   野面の土留めを据えた後(袖の背は隅の駒の法に当たる・野面も相手になる ── 前に流すと Clear の後で相手が群に居ない・2026-09-26)。
        //   段石・袖は鉛直、野面の土留めは法 1:0.25 ── 焼いた「端を法で切った駒」が在れば差し替え、無ければ見える高さの中ほどで
        //   実メッシュの面を光線で測って駒の長さを詰める/伸ばす(EdoBuild.CutStairEndsToBatter / AbutStepEndsToWalls)。⛔ 土留めの法は変えない。
        sb.Append(AbutStairsToWalls());
        foreach (var kv in LastWallSwap)
        {
            int k = placed.IndexOf(kv.Key); if (k >= 0) placed[k] = kv.Value;
            Vector2 fo; if (faceOf.TryGetValue(kv.Key, out fo)) { faceOf.Remove(kv.Key); faceOf[kv.Value] = fo; }
        }
        // ⭐ 天端を高い側の地盤に揃えた土留め(`copingRise:"groundHi"`)は天端の面と地形が重なる ──
        //   天端の下の節点を天端より下げ、芝を消す(EDO-0414・⛔ 地形の編集は Undo の外)。
        //   ⚠ Stage1(整地)を流し直すと節点が天端へ戻るので、Stage3 を必ず後に流す。
        //   ⭐ 埋没は**見える天端の帯**で数える(普請奉行の決め 2026-09-24): 見え面 = 低い側(EdoBuild.LowSide で測った向き)。
        //   帯の奥で上の段の土・上の壁に覆われる控えは石垣として正しい納め(数えない)。
        var faces = new Dictionary<GameObject, Vector3>();
        foreach (var g in placed) if (g != null)
        {
            Vector2 fv; if (!faceOf.TryGetValue(g, out fv)) fv = EdoBuild.FaceSide(new List<GameObject> { g }, new Vector2(g.transform.right.x, g.transform.right.z).normalized);
            faces[g] = new Vector3(fv.x, 0f, fv.y);
        }
        // ⭐ 天端の帯(EdoBuild.CREST_BAND)の下だけを納める ── 法の足の前の面を掘らない(野面の土留め・2026-09-25)
        var tk = EdoBuild.TuckUnderCrest(placed, null, faces: faces, crestBand: EdoBuild.CREST_BAND);
        EditorUtility.SetDirty(EdoBuild.T().terrainData); AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        sb.AppendLine("  " + (tk.thin > 0 ? "⛔ " : "") + "天端の下の地形: " + tk);
        return "土留め: 駒 " + total + " 枚 / ⛔ 埋まっていて建てなかった " + buried + " 枚 ≒ " +
               buriedM.ToString("F1") + "m(裁定 EDO-0182 が未着手のため据え置き)\n" + sb;
    }
    /// <summary>見え面を石段の袖の背の面に揃える土留めの区間(紙)と、袖の実メッシュの背の面へ移した区間。</summary>
    struct FaceFlushSeg { public string run; public Vector2[] paper, moved; public float off; }
    /// <summary>**見え面を石段の袖の背の面に揃える土留め**(指図 joints: a = その run・kind「面一」・bFace「袖の背の面」── 前庭の切り込みの返し
    /// 施主裁定 2026-09-27 EDO-0437)の区間ごとに、紙の通りを袖の実メッシュの背の面の上へ移した線(EdoBuild.SegOntoOuterFace)。
    /// Stage3(返しと継ぐ run の端)と Stage4(返しから離れを取る板塀の端)が同じ関数で引く ── ⛔ 片方だけ紙の線で測らない。</summary>
    static List<FaceFlushSeg> FaceFlushSegs(IEnumerable<Dictionary<string, object>> runs, List<GameObject> sandoPieces, StringBuilder sb)
    {
        var res = new List<FaceFlushSeg>();
        foreach (var r in runs)
        {
            string name = S(r, "name"); var twd = FindByName(Doc, "terraceWalls", name); if (twd == null) continue;
            bool flush = false;
            foreach (var o in L(Doc, "joints"))
            { var j = o as Dictionary<string, object>; if (j == null) continue;
              if ((S(j, "a") ?? "").Contains(name) && (S(j, "kind") ?? "").StartsWith("面一") && (S(j, "bFace") ?? "").Contains("袖の背の面")) flush = true; }
            var gf = D(twd, "gapFrom"); string kai = gf == null ? null : S(gf, "kaidan");
            if (!flush || kai == null) continue;
            var sw = SodeWallsOf(kai); var stg = Group("Sando").Find(GroupNameOf(kai));
            Vector2 sc = Vector2.zero; int ns0 = 0;
            if (stg != null) foreach (Transform c in stg) if (c.name.StartsWith("Dan_")) { var cc = EdoBuild.RB(c.gameObject).center; sc += new Vector2(cc.x, cc.z); ns0++; }
            if (ns0 == 0 || sw.Count == 0) { if (sb != null) sb.AppendLine("  ⛔ " + name + ": 袖の背の面に揃える相手(石段 " + kai + " の段・袖)が据わっていない"); continue; }
            sc /= ns0;
            foreach (var so in L(r, "segs"))
            {
                var sg = so as List<object>; if (sg == null || sg.Count < 2) continue; Vector2 a = P2(sg[0]), b = P2(sg[1]); Vector2 mid = (a + b) * 0.5f;
                string best = null; float bd = float.MaxValue; foreach (var kv in sw) { float dd = DistToPoly(kv.Value, mid); if (dd < bd) { bd = dd; best = kv.Key; } }
                var bodies = new List<GameObject>(); foreach (var g in sandoPieces) if (g.name.StartsWith(best + "_")) bodies.Add(g);
                float off; string w;
                var ln = EdoBuild.SegOntoOuterFace(a, b, bodies, mid - sc, out off, out w);
                if (ln == null) { if (sb != null) sb.AppendLine("  ⛔ " + name + ": 袖 " + best + " の背の面を測れない ── " + w); continue; }
                if (sb != null) sb.AppendLine("  " + name + " の区間 " + a.ToString("F2") + "→" + b.ToString("F2") + ": 通りを袖 " + best + " の背の面へ " + off.ToString("+0.000;-0.000") + "m 移した(駒 " + bodies.Count + ")" + (w != null ? " ⚠ " + w : ""));
                res.Add(new FaceFlushSeg { run = name, paper = new[] { a, b }, moved = ln, off = off });
            }
        }
        return res;
    }
    /// <summary>**板塀・柵の端が、見え面を袖の背へ移した土留めから紙の離れを保つ**(2026-09-27・EDO-0437 普請検査 r15 ── 返しが外へ 0.60 移ったのに
    /// 板塀 Ita_ZN・Ita_ZNE の端が紙のまま残り、最後の柱が袖の天端に載った)。指図 joints の a がこの run・kind「見切り(離れ …)」・b が
    /// <see cref="FaceFlushSegs"/> で移る土留めのとき、端を走りに沿って動かし、**移した線からの離れ = 紙の端と紙の線の離れ**にする(離れの値は紙のまま・発明しない)。
    /// 当たる先: 石段の袖の背へ移した返しに見切りで取り付く板塀・柵・玉垣の端(山王 前庭の北の縁 Ita_ZN・Ita_ZNE)。</summary>
    static void KeepClearOfFlushWalls(List<Vector2> sa, List<Vector2> sbb, string name, StringBuilder sb)
    {
        var walls = new HashSet<string>();
        foreach (var o in L(Doc, "joints"))
        { var j = o as Dictionary<string, object>; if (j == null) continue;
          if (!System.Text.RegularExpressions.Regex.IsMatch(S(j, "a") ?? "", "(^|[^A-Za-z_])" + name + "([^A-Za-z_]|$)") || !(S(j, "kind") ?? "").StartsWith("見切り")) continue;
          var m = System.Text.RegularExpressions.Regex.Match(S(j, "b") ?? "", "TW_[A-Za-z0-9_]+"); if (m.Success) walls.Add(m.Value); }
        if (walls.Count == 0) return;
        var wr = new List<Dictionary<string, object>>();
        foreach (var o in L(Impl, "runs")) { var r = o as Dictionary<string, object>; if (r != null && walls.Contains(S(r, "name"))) wr.Add(r); }
        var sandoPieces = new List<GameObject>();
        foreach (var t in Group("Sando").GetComponentsInChildren<Transform>())
            if (t.name.StartsWith("TW_") && t.gameObject.activeInHierarchy && t.GetComponentInChildren<MeshFilter>() != null && t.parent != null && !t.parent.name.StartsWith("TW_")) sandoPieces.Add(t.gameObject);
        var fms = FaceFlushSegs(wr, sandoPieces, null); if (fms.Count == 0) return;
        for (int i = 0; i < sa.Count; i++)
            foreach (bool atB in new[] { false, true })
            {
                Vector2 e = atB ? sbb[i] : sa[i], o2 = atB ? sa[i] : sbb[i]; Vector2 dir = (e - o2); float L0 = dir.magnitude; if (L0 < 1e-4f) continue; dir /= L0;
                FaceFlushSeg best = default(FaceFlushSeg); float bd = float.MaxValue; bool has = false;
                foreach (var fm in fms) { float d = EdoGeom.DistToEdge(e, fm.paper[0], fm.paper[1]); if (d < bd) { bd = d; best = fm; has = true; } }
                if (!has || bd > 1.5f) continue;
                Vector2 pd = (best.paper[1] - best.paper[0]).normalized, n = new Vector2(-pd.y, pd.x);
                float s0 = Vector2.Dot(e - best.paper[0], n), s1 = Vector2.Dot(e - best.moved[0], n), dn = Vector2.Dot(dir, n);
                if (Mathf.Abs(dn) < 0.2f) continue;
                float t = (s0 - s1) / dn; if (Mathf.Abs(t) < 1e-3f) continue;
                Vector2 ne = e + dir * t;
                if (atB) sbb[i] = ne; else sa[i] = ne;
                if (sb != null) sb.AppendLine("  " + name + " の端 " + e.ToString("F3") + " → " + ne.ToString("F3") + "(" + best.run + " を袖の背へ移した線から紙の離れ " + Mathf.Abs(s0).ToString("F3") + "m を保つ・走りに沿って " + t.ToString("+0.000;-0.000") + "m)");
            }
    }
    /// <summary>野面の乱積みの土留め(`terraceWalls[].masonry`)を据える。指図の run を口で割った区間(算出物 `segs`)を
    /// <see cref="EdoBuild.NozuraSeg"/> に読み替えて <see cref="EdoBuild.PlaceNozuraNet"/> へ渡すだけ(継ぎ方・端の納め・置き方は EdoBuild)。
    /// 読むもの: 区間ごとの天端 = `profile` のうち区間の中の行(口の中の行 = 地表を拾わない)/ 足元の平場 = `foot.terrace` /
    /// 入隅の可動側 = `joints` の kind「入隅」で moves がこの run / 見切り石 = `corners.gap` が見切り石を名指す run の口の縁。</summary>
    static int Nozura(List<Dictionary<string, object>> runs, Transform grp, List<GameObject> placed,
                      Dictionary<GameObject, Vector2> faceOf, EdoBuild.DrawnGround dg, float probe, StringBuilder sb)
    {
        var segs = new List<EdoBuild.NozuraSeg>();
        // 袖・段の駒(石段の口の相手)
        var sandoPieces = new List<GameObject>();
        foreach (var t in Group("Sando").GetComponentsInChildren<Transform>())
            if (t.name.StartsWith("TW_") && t.gameObject.activeInHierarchy && t.GetComponentInChildren<MeshFilter>() != null && t.parent != null && !t.parent.name.StartsWith("TW_")) sandoPieces.Add(t.gameObject);
        // ⭐ 見え面を石段の袖の背の面に揃える土留め(指図 joints: a = この run・kind「面一」・bFace「袖の背の面」── 前庭の切り込みの返し
        //   施主裁定 2026-09-27 EDO-0437)は、紙の通りを袖の実メッシュの背の面の上へ移す(EdoBuild.SegOntoOuterFace)。その区間の端で継ぐ
        //   他の run の端は、その run の線と移した線の交点へ(出隅の稜線 = 二本の天端の線の交点 ── joints「出隅」)。⛔ 紙の座標で置かない。
        var faceLine = new List<KeyValuePair<Vector2, Vector2[]>>();   // 紙の端点 → 移した線
        var segMoved = new Dictionary<string, Vector2[]>();              // run#区間の紙の端 → 移した区間
        foreach (var fm in FaceFlushSegs(runs, sandoPieces, sb))
        {
            Vector2 a = fm.paper[0], b = fm.paper[1];
            segMoved[fm.run + "#" + a.ToString("F3") + b.ToString("F3")] = fm.moved;
            faceLine.Add(new KeyValuePair<Vector2, Vector2[]>(a, fm.moved)); faceLine.Add(new KeyValuePair<Vector2, Vector2[]>(b, fm.moved));
        }
        // 紙の端 e を持つ区間 (e, other) の端を動かす: 自分が移した区間なら、他の run と継ぐ端は交点・継がない端は移した線の上 / 他の run なら交点
        Func<string, Vector2, Vector2, Vector2> endOf = (nm, e, other) =>
        {
            Vector2[] mine = null; segMoved.TryGetValue(nm + "#" + e.ToString("F3") + other.ToString("F3"), out mine);
            if (mine == null) segMoved.TryGetValue(nm + "#" + other.ToString("F3") + e.ToString("F3"), out mine);
            foreach (var kv in faceLine)
            {
                if (Vector2.Distance(kv.Key, e) > 0.05f || kv.Value == mine) continue;
                // e で継ぐ別の区間の線(mine が在れば自分の線と相手の線の交点)
                if (mine != null)
                {   // 相手 = e で継ぐ他の run の紙の区間 ── 移した線ではない(相手も移したなら二本の移した線の交点)
                    var q = EdoBuild.LineMeet(mine[0], mine[1], kv.Value[0], kv.Value[1]); if (!float.IsNaN(q.x)) return q;
                }
                else { var q = EdoBuild.LineMeet(e, other, kv.Value[0], kv.Value[1]); if (!float.IsNaN(q.x)) return q; }
            }
            if (mine != null)
            {   // 自分の端: 他の run の紙の区間と継ぐなら交点、継がなければ移した線への射影
                foreach (var r2 in runs)
                {
                    string n2 = S(r2, "name");
                    foreach (var so2 in L(r2, "segs"))
                    {
                        var s2 = so2 as List<object>; if (s2 == null || s2.Count < 2) continue; Vector2 p0 = P2(s2[0]), p1 = P2(s2[1]);
                        if (n2 == nm) continue;
                        Vector2 near = Vector2.Distance(p0, e) < 0.05f ? p0 : Vector2.Distance(p1, e) < 0.05f ? p1 : new Vector2(float.NaN, float.NaN);
                        if (float.IsNaN(near.x)) continue;
                        var q = EdoBuild.LineMeet(p0, p1, mine[0], mine[1]); if (!float.IsNaN(q.x)) return q;
                    }
                }
                Vector2 dd2 = (mine[1] - mine[0]).normalized; return mine[0] + dd2 * Vector2.Dot(e - mine[0], dd2);
            }
            return e;
        };
        foreach (var r in runs)
        {
            string name = S(r, "name"); var nodes = Pts(L(r, "nodes")); var prof = L(r, "profile"); float step = F(r, "profileStep");
            var twd = FindByName(Doc, "terraceWalls", name);
            Func<float, float, float> footAt = null;
            { var ft = twd == null ? null : D(twd, "foot"); string fname = ft == null ? null : S(ft, "terrace");
              var tc = fname == null ? null : FindByName(Impl, "terraces", fname);
              if (tc != null)
              { var wl2 = L(tc, "world"); var poly = new Vector2[wl2.Count]; float fy = F(tc, "y");
                for (int i = 0; i < wl2.Count; i++) { var q = wl2[i] as List<object>; poly[i] = new Vector2(Cv(q[0]), Cv(q[1])); }
                footAt = (x, z) => EdoGeom.PIP(poly, new Vector2(x, z)) ? fy : float.NaN; } }
            bool moves = false;
            foreach (var o in L(Doc, "joints"))
            { var j = o as Dictionary<string, object>; if (j == null) continue;
              string kind = S(j, "kind") ?? "", mv = S(j, "moves") ?? "";
              if (kind.Contains("入隅") && System.Text.RegularExpressions.Regex.IsMatch(mv, "(^|[^A-Za-z_])" + name + "([^A-Za-z_]|$)")) moves = true; }
            var cor = twd == null ? null : D(twd, "corners");
            bool mikiri = cor != null && (S(cor, "gap") ?? "").Contains("SannoNozuraMikiri");
            var segL = new List<Vector2[]>();
            foreach (var so in L(r, "segs")) { var sg = so as List<object>; if (sg != null && sg.Count >= 2) segL.Add(new[] { P2(sg[0]), P2(sg[1]) }); }
            if (segL.Count == 0) for (int i = 1; i < nodes.Count; i++) segL.Add(new[] { nodes[i - 1], nodes[i] });
            foreach (var sg in segL)
            {
                var ns = new EdoBuild.NozuraSeg { name = name, a = endOf(name, sg[0], sg[1]), b = endOf(name, sg[1], sg[0]), footAt = footAt, movesAtConcave = moves };
                if (Vector2.Distance(ns.a, sg[0]) > 1e-3f || Vector2.Distance(ns.b, sg[1]) > 1e-3f)
                    sb.AppendLine("  " + name + " の区間の端(実測の面へ): " + sg[0].ToString("F3") + "→" + ns.a.ToString("F3") + " / " + sg[1].ToString("F3") + "→" + ns.b.ToString("F3"));
                float sOff = ArcOf(nodes, sg[0]), len = Vector2.Distance(sg[0], sg[1]);
                // 天端 = 区間の中の行だけを線形に(口の中の行は地表を拾う ⇒ 使わない)
                //   ⚠ 見付も受け高も 0 の行(両側の地表 = 天端)は壁の無い所の標本 ── 区間の端の行が石段・口の地表を拾い、
                //   天端が端で 1.7m 落ちた(前庭の SW の東の端 16.2 → 14.5・2026-09-26)。壁の在る行が一つでもあれば使わない。
                var rows = new List<Vector2>(); var flat = new List<Vector2>(); var sides = new List<Vector3>();
                foreach (var ro in prof) { var row = ro as List<object>; if (row == null || row.Count < 2) continue;
                    float rs = Cv(row[0]); if (rs < sOff - 0.01f || rs > sOff + len + 0.01f) continue;
                    bool none = row.Count >= 6 && Mathf.Abs(Cv(row[4])) < 0.01f && Mathf.Abs(Cv(row[5])) < 0.01f;
                    (none ? flat : rows).Add(new Vector2(rs - sOff, Cv(row[1])));
                    if (!none && row.Count >= 4) sides.Add(new Vector3(rs - sOff, Cv(row[2]), Cv(row[3]))); }
                // 縦断の低い側・高い側の地盤(駒ごとの見え面を決める ── EdoBuild.NozuraWall.sidesAt)
                var sidesL = sides;
                if (sidesL.Count > 0) ns.sidesAt = ls =>
                {
                    int best = 0; for (int i = 1; i < sidesL.Count; i++) if (Mathf.Abs(sidesL[i].x - ls) < Mathf.Abs(sidesL[best].x - ls)) best = i;
                    if (Mathf.Abs(sidesL[best].x - ls) > 1.5f) return new Vector2(float.NaN, float.NaN);
                    return new Vector2(sidesL[best].y, sidesL[best].z);
                };
                if (rows.Count == 0) rows = flat;
                if (rows.Count == 0) { float t0, f0, b0; if (ProfileAt(prof, step, sOff + len * 0.5f, out t0, out f0, out b0)) rows.Add(new Vector2(0f, t0)); }
                var rowsL = rows;
                ns.crestAt = ls =>
                {
                    if (rowsL.Count == 0) return float.NaN;
                    if (ls <= rowsL[0].x) return rowsL[0].y; if (ls >= rowsL[rowsL.Count - 1].x) return rowsL[rowsL.Count - 1].y;
                    for (int i = 1; i < rowsL.Count; i++) if (ls <= rowsL[i].x)
                        return Mathf.Lerp(rowsL[i - 1].y, rowsL[i].y, (ls - rowsL[i - 1].x) / Mathf.Max(1e-4f, rowsL[i].x - rowsL[i - 1].x));
                    return rowsL[rowsL.Count - 1].y;
                };
                // 口の縁(run の端点でなく、同じ run の他の区間の端とも重ならない端)に見切り石
                if (mikiri)
                    for (int e = 0; e < 2; e++)
                    {
                        Vector2 ep = sg[e];
                        if (Vector2.Distance(ep, nodes[0]) < 0.05f || Vector2.Distance(ep, nodes[nodes.Count - 1]) < 0.05f) continue;
                        bool shared = false; foreach (var o2 in segL) if (o2 != sg && (Vector2.Distance(o2[0], ep) < 0.05f || Vector2.Distance(o2[1], ep) < 0.05f)) shared = true;
                        if (shared) continue;
                        var to = new List<GameObject>();
                        foreach (var g in sandoPieces) foreach (var v in EdoBuild.Body(g.transform, 400)) if (Vector2.Distance(new Vector2(v.x, v.z), ep) < 2.0f) { to.Add(g); break; }
                        ns.mikiriTo[e] = to;
                    }
                segs.Add(ns);
            }
        }
        var pool = new List<GameObject>(placed); pool.AddRange(sandoPieces);
        // 見え面は設計面で測る(据えた土留めの際は Tuck・皮で描かれた地表が下がっていて低い側を取り違える)
        var got = EdoBuild.PlaceNozuraNet(segs, (x, z) => dg.At(x, z), SodeFootAt, probe, grp,
            (h, g, i) => EdoAssets.Own.SannoNozura(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),
            (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
            EdoAssets.Own.SannoNozuraMikiriH, new[] { 0.30f, 0.60f, 0.90f, 1.20f, 1.50f, 1.80f, 2.10f, 2.40f }, pool, sb,
            EdoAssets.Own.SannoNozuraKiriEnd, EdoAssets.Own.SannoNozuraNoriEnd, sandoPieces);
        // ⭐ 袖の背に取り付く出隅は、腕を袖の背の面で一辺だけ切った版を引く(EdoBuild.CutKadoArmsToFaces・EDO-0437 2026-09-27 施主
        //   「袖に当たる石は袖の背に沿った一辺だけ切る」)。相手 = 石段の袖。据えは元の隅と同じ・硬い(焼けていなければ ⛔ と焼く値)。
        {
            var kados = new List<GameObject>();
            foreach (var kv in got)
            { var mf = kv.Key.GetComponentInChildren<MeshFilter>();
              if (mf != null && mf.sharedMesh != null && System.IO.Path.GetFileName(AssetDatabase.GetAssetPath(mf.sharedMesh)).StartsWith("Sanno_Nozura_Kado90_")) kados.Add(kv.Key); }
            var cm = EdoBuild.CutKadoArmsToFaces(kados, sandoPieces, (g, ax, at, arm) =>
            {
                var mf = g.GetComponentInChildren<MeshFilter>(); string mp = System.IO.Path.GetFileNameWithoutExtension(AssetDatabase.GetAssetPath(mf.sharedMesh));
                var m = System.Text.RegularExpressions.Regex.Match(mp, @"^Sanno_Nozura_Kado90_H(\d{4})_([ab])$"); if (!m.Success) return null;
                return EdoAssets.Own.SannoNozuraKadoCut(int.Parse(m.Groups[1].Value) / 1000f, m.Groups[2].Value == "a" ? 0 : 1, ax, at, arm);
            }, sb);
            for (int i = 0; i < got.Count; i++)
            { GameObject ng; if (cm.TryGetValue(got[i].Key, out ng)) got[i] = new KeyValuePair<GameObject, Vector2>(ng, got[i].Value); }
        }
        foreach (var kv in got) { placed.Add(kv.Key); faceOf[kv.Key] = kv.Value; }
        return got.Count;
    }
    /// <summary>区間が基壇か ── 建つ所(見付 &gt; 0)の受け高が全て負(天端が両側の地盤より上)。</summary>
    static bool SegIsBase(List<object> prof, float step, float sBase, float len)
    {
        int n = 0;
        for (float ss = Mathf.Min(0.5f, len * 0.5f); ss <= len; ss += 1f)
        {
            float t0, f0, b0; if (!ProfileAt(prof, step, sBase + ss, out t0, out f0, out b0) || f0 <= BURIED_EPS) continue;
            n++; if (b0 > -BURIED_EPS) return false;
        }
        return n > 0;
    }
    /// <summary>袖の駒が野面の乱積みの袖(`IshidanSodeNozura*`)か(メッシュの資産名で)。</summary>
    static bool IsNozuraSode(GameObject g)
    {
        var mf = g == null ? null : g.GetComponentInChildren<MeshFilter>();
        string mp = mf != null && mf.sharedMesh != null ? AssetDatabase.GetAssetPath(mf.sharedMesh) : "";
        return System.IO.Path.GetFileName(mp).StartsWith("IshidanSodeNozura");
    }
    static string FamilyOf(string n)
    { int i = n.LastIndexOf('_'); return i <= 0 ? n : n.Substring(0, i); }
    /// <summary>折れ線 <paramref name="poly"/> 上での点 p の弧長。</summary>
    static float ArcOf(List<Vector2> poly, Vector2 p)
    {
        float acc = 0f, best = 0f, bd = float.MaxValue;
        for (int i = 1; i < poly.Count; i++)
        {
            Vector2 a = poly[i - 1], b = poly[i];
            float l = Vector2.Distance(a, b); if (l < 1e-6f) continue;
            float t = Mathf.Clamp01(Vector2.Dot(p - a, (b - a) / l) / l);
            float d = Vector2.Distance(p, Vector2.Lerp(a, b, t));
            if (d < bd) { bd = d; best = acc + l * t; }
            acc += l;
        }
        return best;
    }
    /// <summary>`profile` = [走り s, 天端 y, 低い側の地盤, 高い側の地盤, 見付高, 受け高] を s で線形補間。</summary>
    static bool ProfileAt(List<object> prof, float step, float s, out float top, out float faceH, out float backH)
    {
        top = faceH = backH = 0f;
        if (prof.Count == 0) return false;
        List<object> lo = null, hi = null; float slo = 0f, shi = 0f;
        for (int i = 0; i < prof.Count; i++)
        {
            var r = prof[i] as List<object>; if (r == null || r.Count < 6) continue;
            float ss = Cv(r[0]);
            if (ss <= s && (lo == null || ss > slo)) { lo = r; slo = ss; }
            if (ss >= s && (hi == null || ss < shi)) { hi = r; shi = ss; }
        }
        if (lo == null && hi == null) return false;
        if (lo == null) { lo = hi; slo = shi; }
        if (hi == null) { hi = lo; shi = slo; }
        float t = (shi - slo) < 1e-6f ? 0f : (s - slo) / (shi - slo);
        top = Mathf.Lerp(Cv(lo[1]), Cv(hi[1]), t);
        faceH = Mathf.Lerp(Cv(lo[4]), Cv(hi[4]), t);
        backH = Mathf.Lerp(Cv(lo[5]), Cv(hi[5]), t);
        return true;
    }

    // ================================================================ Stage 4 囲い
    /// <summary>Stage3 の後段: 全ての石段について、段石の両の小口と袖の背の小口を脇の土留めの面へ突き付ける(EDO-0430)。
    /// 相手 = Dodome の土留めの駒(段石には同じ群の袖も)。報告 = 石段ごとに 動かした段・跨いで動かさなかった段・上端の口と下端のめり込みの最大。</summary>
    /// <summary>AbutStairsToWalls が差し替えた土留めの駒(旧 → 新)── Stage3 が placed・faceOf を差し替えるため。</summary>
    static readonly Dictionary<GameObject, GameObject> LastWallSwap = new Dictionary<GameObject, GameObject>();
    public static string AbutStairsToWalls()
    {
        LastWallSwap.Clear();
        var sb = new StringBuilder();
        var dod = Group("Dodome"); var walls = new List<GameObject>();
        foreach (Transform c in dod) if (c.gameObject.activeInHierarchy) walls.Add(c.gameObject);
        foreach (var o in L(Impl, "stairs"))
        {
            var st = o as Dictionary<string, object>; if (st == null) continue;
            string name = S(st, "name"); var grp = Group("Sando").Find(GroupNameOf(name)); if (grp == null) continue;
            float keri = F(st, "keri"), fumi = F(st, "fumi");
            var dans = new List<GameObject>(); var sodes = new List<GameObject>();
            foreach (Transform c in grp) { if (c.name.StartsWith("Dan_")) dans.Add(c.gameObject); else if (c.name.StartsWith("TW_")) sodes.Add(c.gameObject); }
            if (dans.Count == 0) continue;
            // ⭐ 端を法で切った駒が焼けている段石・袖の背は差し替える(口・めり込み 0 ── EDO-0430 2026-09-26・EdoBuild.CutStairEndsToBatter)。
            //   差し替えた駒には中ほどの突き付け(下の AbutStepEndsToWalls / AbutEndToFace)を掛けない。
            float wM = F(st, "wM");
            // ⭐ 見える当たりは**描かれた地表**で決める(2026-09-26・EDO-0437 第5巡・普請奉行の決め)── 1m 格子の設計面(SodeFootAt)は段の端で
            //   描かれた地表より 0.3〜0.5 高く、その間の隅の石の入り(0.03〜0.11)を「地表の下」と読んで切らずに残した。
            //   ⚠ 皮(Stage9)は後で建つので、ここで引くのは前の巡の皮 ── 皮が動いた巡は石段から流し直して揃える(Jun)。
            //   ⚠ 当たった点は相手(土留め)の外形の中で、そこの皮は天端の下へ納めてある(= 天端の高さ・見えない皮)── 描かれた地表だけで引くと
            //   隅の石の当たりを全部「地表の下」と読み、参道の階の段 1・2 の −X が「当たらず」になった(第5巡の実測)。⇒ 設計面と描かれた地表の
            //   **低い方**(開いた地表では描かれた地表・外形の中では設計面)。
            var drawnVis = EdoBuild.Drawn();
            Func<float, float, float> visAt = (x, z) => { float dsg = SodeFootAt(x, z), g = drawnVis.At(x, z); return float.IsNaN(g) ? dsg : float.IsNaN(dsg) ? g : Mathf.Min(dsg, g); };
            var cut = EdoBuild.CutStairEndsToBatter(name, dans, sodes, keri, fumi, walls,
                i => P.Dan(keri, fumi, wM, i),
                (i, l, r) => EdoAssets.Own.SannoDanKiri(keri, fumi, wM, i, l, r),
                (g, i) =>
                {
                    var mf = g.GetComponentInChildren<MeshFilter>(); string mp = mf != null && mf.sharedMesh != null ? AssetDatabase.GetAssetPath(mf.sharedMesh) : "";
                    // 平らな袖(丈は既定)か、前の巡で背を切った袖だけ。⛔ 留めの駒・丈の深い駒は焼いていない
                    var inv = System.Globalization.CultureInfo.InvariantCulture; string kf = keri.ToString("F3", inv) + "_" + fumi.ToString("F3", inv);
                    if (mp == EdoAssets.Own.IshidanSode(keri, fumi, i) || System.IO.Path.GetFileName(mp).StartsWith("IshidanSodeNori_" + kf + "_E")) return EdoAssets.Own.IshidanSode(keri, fumi, i);
                    // 野面の袖(平らな物か、前の巡で背を切った物)── 2026-09-26 EDO-0437 第3巡
                    if (mp == EdoAssets.Own.IshidanSodeNozura(keri, fumi, i) || System.IO.Path.GetFileName(mp).StartsWith("IshidanSodeNozuraNori_" + kf + "_E")) return EdoAssets.Own.IshidanSodeNozura(keri, fumi, i);
                    return null;
                },
                (g, i, e) => IsNozuraSode(g) ? EdoAssets.Own.IshidanSodeNozuraNori(keri, fumi, e, i) : EdoAssets.Own.IshidanSodeNori(keri, fumi, e, i), sb,
                // ⭐ 相手が野面の乱積み(法 1:0.3)の端・袖の背は石の出の包絡で切る(EDO-0437 第3巡)。野面の袖だけ ── 切石の袖は従来の中央値
                envNori: EdoAssets.Own.SannoNozuraNori, sodeEnvNori: g => IsNozuraSode(g) ? EdoAssets.Own.SannoNozuraNori : float.NaN, envVisAt: visAt,
                envWall: g => { var mf = g.GetComponentInChildren<MeshFilter>(); return mf != null && mf.sharedMesh != null && EdoAssets.Own.IsSannoNozura(AssetDatabase.GetAssetPath(mf.sharedMesh)); });
            // ⛔ 相手の石の形に沿わせて焼いた合わせ駒(DanFit・IshidanSodeNozuraFit・SannoNozuraFill*)へは差し替えない
            //   (施主裁定 2026-09-27 EDO-0437「段も袖も削らない」── 段は SannoDan・袖は IshidanSode のまま、取り合いは据えで決める)。
            var fitted = new List<GameObject>();
            dans.Clear(); sodes.Clear();
            foreach (Transform c in grp)
            {
                if (cut.Contains(c.gameObject)) continue;
                if (c.name.StartsWith("Dan_")) dans.Add(c.gameObject); else if (c.name.StartsWith("TW_")) sodes.Add(c.gameObject);
            }
            var sodesAll = new List<GameObject>(sodes); foreach (var g in cut) if (g.name.StartsWith("TW_")) sodesAll.Add(g);
            var wS = new List<GameObject>(walls); wS.AddRange(sodesAll);
            var rs = EdoBuild.AbutStepEndsToWalls(dans, keri, fumi, wS);
            // ⭐ 段石の端に被さる隅の駒・土留めは段の外へ退ける(EdoBuild.YieldWallsToSteps・2026-09-26 EDO-0437 第9巡)── 段は動かさない
            //   (蹴上・踏面は段数からの従属値)。見える所の重なりだけ・硬い(許容0)。当たる先: 全ての石段 × Dodome の駒。
            {
                var allDan = new List<GameObject>(); foreach (Transform c in grp) if (c.name.StartsWith("Dan_") && c.gameObject.activeInHierarchy) allDan.Add(c.gameObject);
                var visExp = EdoBuild.DrawnExpected();   // ⭐ 皮を外している間も外す前の皮で見える地表を読む(段 0 の端の当たりを造成前の地形の下と読んだ)
                foreach (var yv in EdoBuild.YieldWallsToSteps(allDan, walls, (x, z) => visExp.At(x, z), keri, 0.15f, fitted))
                    sb.AppendLine("    " + (yv.refused || yv.after > 0.003f ? "⛔ " : "") + yv.wall.name + " が段 " + yv.steps + " の端に見える所で被る " + yv.need.ToString("F3") +
                                  (yv.refused ? " ── 動かさない(" + yv.why + ")" : " → 段の外へ " + yv.moved.ToString("F3") + "m 退けた・残り " + yv.after.ToString("F3")));
            }
            int moved = 0, mixed = 0; float gap = 0f, bite = 0f, mvMax = 0f; var mixedNames = new List<string>();
            foreach (var kv in rs)
            {
                if (kv.Value.mixed) { mixed++; mixedNames.Add(kv.Key + "(幅 " + kv.Value.spread.ToString("F3") + ")"); continue; }
                if (kv.Value.moved != 0f) { moved++; mvMax = Mathf.Max(mvMax, Mathf.Abs(kv.Value.moved)); }
                gap = Mathf.Max(gap, kv.Value.gapHi); bite = Mathf.Max(bite, kv.Value.biteLo);
            }
            // 袖の背の小口(坂上の端)× 土留めの面 ── 見える高さ = その段の踏面 〜 袖の天端
            //   ⭐ 坂上の端の駒だけ(袖の run の端 = 指図の corners.a「突き付け」)。途中の駒の背は次の袖の駒が受ける ──
            //   途中の駒の背に土留めが来ていれば、それは袖が土留めに埋まっている別の欠陥で、駒を詰めて消さない(郭の階で 0.41m 詰めかけた)。
            int sMoved = 0, sMixed = 0; float sGap = 0f, sBite = 0f, sMv = 0f;
            var topIdx = new Dictionary<string, int>();
            foreach (var sg in sodesAll)   // ⭐ 差し替えた駒も数える(坂上の端を一つ下の駒と取り違えない)
            {
                int us = sg.name.LastIndexOf('_'); int ii;
                if (us < 0 || !int.TryParse(sg.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
                string row = sg.name.Substring(0, us); int cur;
                if (!topIdx.TryGetValue(row, out cur) || ii > cur) topIdx[row] = ii;
            }
            foreach (var sg in sodes)
            {
                int us = sg.name.LastIndexOf('_'); int ii;
                if (us < 0 || !int.TryParse(sg.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
                if (topIdx[sg.name.Substring(0, us)] != ii) continue;
                var dg = grp.Find("Dan_" + ii.ToString("00")); if (dg == null) continue;
                float dTop = float.MinValue; foreach (var v in EdoBuild.Body(dg, 999999, true)) dTop = Mathf.Max(dTop, v.y);
                float sTop = float.MinValue; foreach (var v in EdoBuild.Body(sg.transform, 999999, true)) sTop = Mathf.Max(sTop, v.y);
                var r = EdoBuild.AbutEndToFace(sg, -sg.transform.forward, sg.transform.right, new[] { -0.2f, 0f, 0.2f },
                                               dTop + 0.02f, sTop - 0.02f, walls, 0.5f, 0.10f, 0.031f);
                if (!r.touched) continue;
                if (r.mixed) { sMixed++; continue; }
                if (r.moved != 0f) { sMoved++; sMv = Mathf.Max(sMv, Mathf.Abs(r.moved)); }
                sGap = Mathf.Max(sGap, r.gapHi); sBite = Mathf.Max(sBite, r.biteLo);
                sb.AppendLine("    " + sg.name + " の背の小口 × 土留めの面: " + r.moved.ToString("+0.000;-0.000") + "m(見える高さ " + (dTop).ToString("F2") + "〜" + sTop.ToString("F2") +
                              " の中ほど)/ 上端の口 " + r.gapHi.ToString("F3") + " / 下端のめり込み " + r.biteLo.ToString("F3"));
            }
            // ⭐ 袖の坂下の端(一番下の駒の前の小口)× 土留めの背(2026-09-26・EDO-0437 第6巡)── 中門の内の階の袖 `TW_ChumonKai_N/S_000f` は
            //   坂下の端が腰の土留め `TW_Koshi_E_007f/008f` の背へ 0.13 入っていた(段石 Dan_00 は土留めの口の中なので当たらない)。
            //   見える高さ = 端の描かれた地表 〜 袖の天端と土留めの天端(端の先 0.1m で測る)の低い方。**詰めるだけ**(伸ばさない ── maxOut 0)。
            //   ⛔ 男坂の袖(TW_Otoko_*)は部材待ち(EDO-0459)で触らない。当たる先: 石段の袖の坂下の端が土留め・石垣の背に届く所すべて。
            var botIdx = new Dictionary<string, int>();
            foreach (var sg in sodesAll)
            {
                int us = sg.name.LastIndexOf('_'); int ii;
                if (us < 0 || !int.TryParse(sg.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
                string row = sg.name.Substring(0, us); int cur;
                if (!botIdx.TryGetValue(row, out cur) || ii < cur) botIdx[row] = ii;
            }
            foreach (var sg in sodes)
            {
                if (sg.name.StartsWith("TW_Otoko")) continue;
                int us = sg.name.LastIndexOf('_'); int ii;
                if (us < 0 || !int.TryParse(sg.name.Substring(us + 1).TrimEnd('f'), out ii)) continue;
                if (botIdx[sg.name.Substring(0, us)] != ii) continue;
                Vector3 fw = sg.transform.forward; fw.y = 0f; fw.Normalize();
                float sTop = float.MinValue; foreach (var v in EdoBuild.Body(sg.transform, 999999, true)) sTop = Mathf.Max(sTop, v.y);
                var ez = EdoBuild.ExtentAlong(sg, fw); var rbS = EdoBuild.RB(sg);
                Vector3 cenS = new Vector3(rbS.center.x, 0f, rbS.center.z), p0S = sg.transform.position; p0S.y = 0f;
                Vector3 endC = cenS + fw * (ez.y - Vector3.Dot(cenS - p0S, fw));   // 前の小口(実メッシュの端)の、駒の幅の中ほど ── 地表を引く点(位置合わせではない)
                float gEnd = drawnVis.At(endC.x, endC.z);
                Vector3 past = endC + fw * 0.1f;
                float crest = EdoBuild.BedTopAt(new Vector2(past.x, past.z), walls, sTop + 2f);
                if (float.IsNaN(gEnd) || float.IsNaN(crest)) continue;
                float yHi = Mathf.Min(sTop, crest) - 0.02f, yLo = gEnd + 0.02f; if (yHi <= yLo + 0.02f) continue;
                var r = EdoBuild.AbutEndToFace(sg, fw, sg.transform.right, new[] { -0.2f, 0f, 0.2f }, yLo, yHi, walls, 0.5f, 0f, 0.031f);
                if (!r.touched) continue;
                if (r.mixed) { sMixed++; continue; }
                if (r.moved != 0f) { sMoved++; sMv = Mathf.Max(sMv, Mathf.Abs(r.moved)); }
                sGap = Mathf.Max(sGap, r.gapHi); sBite = Mathf.Max(sBite, r.biteLo);
                sb.AppendLine("    " + sg.name + " の前の小口 × 土留めの背: " + r.moved.ToString("+0.000;-0.000") + "m(見える高さ " + yLo.ToString("F2") + "〜" + yHi.ToString("F2") +
                              " の中ほど)/ 上端の口 " + r.gapHi.ToString("F3") + " / 下端のめり込み " + r.biteLo.ToString("F3"));
            }
            // ⭐ 袖の脇の面 × 隅の駒・土留めの法の足(2026-09-26・EDO-0437 第8巡・普請奉行の決め「袖が譲る」)── 回廊の出隅 E×S の法の足が
            //   女坂の北の袖 039f の脇へ入る。袖の脇を相手の法で切った駒へ差し替える型(焼く値 d・deg・nori・za を刷る)。⛔ 隅の駒は動かさない。
            //   測りは EdoBuild.MeasureSodeSideBites(面で測る)。焼いた駒が無ければ差し替えず、焼く値を刷る。当たる先: 全ての石段の袖 × Dodome の駒。
            foreach (var bt in EdoBuild.MeasureSodeSideBites(sodesAll, walls, visAt))
            {
                var inv2 = System.Globalization.CultureInfo.InvariantCulture;
                sb.AppendLine("    " + (bt.biteVis > 0.005f ? "⛔ " : "⚠ ") + bt.sode.name + " の脇(" + (bt.side < 0 ? "−X" : "+X") + ")× " + bt.wall.name +
                              ": 入り 最大 " + bt.bite.ToString("F3", inv2) + "(見える所 " + bt.biteVis.ToString("F3", inv2) + ")・高さ " + bt.yLo.ToString("F2", inv2) + "〜" + bt.yHi.ToString("F2", inv2) +
                              "・走り " + bt.aLo.ToString("+0.00;-0.00", inv2) + "〜" + bt.aHi.ToString("+0.00;-0.00", inv2) + "(当たり " + bt.n + ")" +
                              " ⟶ 焼く値 d " + bt.bite.ToString("F3", inv2) + " 角 " + bt.deg.ToString("+0.0;-0.0", inv2) + "° 法 " + bt.nori.ToString("F3", inv2) +
                              (float.IsNaN(bt.za) ? " 全長" : " za " + bt.za.ToString("+0.000;-0.000", inv2) + (bt.uphill ? "(坂上側を欠く)" : "(坂下側を欠く)")) +
                              " ── 袖の脇を法で切った駒は焼いていない・差し替えない");
            }
            if (rs.Count == 0 && sMoved + sMixed == 0) continue;
            sb.AppendLine("  " + name + ": 段石の小口が土留め・袖に接する " + rs.Count + " 端 / 詰めた・伸ばした " + moved + "(最大 " + mvMax.ToString("F3") + "m)" +
                          " / 上端の口 最大 " + gap.ToString("F3") + " / 下端のめり込み 最大 " + bite.ToString("F3") +
                          (mixed > 0 ? " / ⚠ 二つの面に跨り動かさない " + mixed + ":" + string.Join("・", mixedNames) : "") +
                          (sMoved + sMixed > 0 ? " / 袖の背 " + sMoved + " 駒(最大 " + sMv.ToString("F3") + "m・上端の口 " + sGap.ToString("F3") + "・下端のめり込み " + sBite.ToString("F3") + (sMixed > 0 ? "・跨ぐ " + sMixed : "") + ")" : ""));
        }
        return sb.ToString();
    }

    // ⚠ 2026-09-26: メニューの属性が上の AbutStairsToWalls に付いていて、「4 囲い」が柵を建てずに石段の突き付けだけを流していた(0c28b9d9 から)。
    [MenuItem(MENU + "4 囲い(腰高の柵・板塀)")]
    public static void Stage4Menu() { Debug.Log("[山王] " + Stage4_Kakoi()); }
    /// <summary>算出物 `runs` の `of=="run"` を建てる。`segs` は**開口を抜いた実長の区間**なので
    /// ⛔ 実装が辺を割り直さない。
    ///   ・`kind=="柵"` … 腰高の柵(⛔ 土塀ではない。2026-09-07 の裁定)
    ///   ・`kind=="板塀"` … edogoyomi の板塀 ×ES
    ///   ・`kind=="透塀"` … 新造のスパン + 隅部材(⭐ 2026-09-16 に部材が揃ったので建てる)
    ///   ・`kind=="袖塀"` … 新造の袖塀(足元二段。⛔ 柵で代用しない)
    ///   ・`kind=="回廊"` … **部材が無い**(`bom[回廊…]`「無い/新造依頼」)⇒ 建てずに数える</summary>
    public static string Stage4_Kakoi()
    {
        var gate = Gate(); if (gate != null) return gate;
        var sb = new StringBuilder();
        int pieces = 0; float pending = 0f; var pendNames = new List<string>();
        foreach (var o in L(Impl, "runs"))
        {
            var r = o as Dictionary<string, object>; if (r == null || S(r, "of") != "run") continue;
            string name = S(r, "name"), kind = S(r, "kind");
            if (kind == "回廊")
            {
                // ⭐ 2026-09-20: 部材が焼けたので建てる(`bom[回廊(屋根付きの廊)].在庫`)。
                var kg = Group("Kakoi/" + name); Clear(kg);
                int nk = Kairo(r, name, kg, sb);
                if (nk == 0) { pending += F(r, "lenM"); pendNames.Add(name + "(" + kind + " " + F(r, "lenM").ToString("F1") + "m)"); }
                pieces += nk;
                continue;
            }

            var grp = Group("Kakoi/" + name); Clear(grp);
            bool hasSeat = HasNum(r, "seat");
            float seat = F(r, "seat");
            int made = 0;
            if (kind == "透塀") { made = Sukibei(r, name, grp, sb); }
            else if (kind == "袖塀") { made = Sodebei(r, name, grp, sb); }
            else if (kind == "板塀")
            {
                // ⭐ 柵と**同じ物差しで口を閉じる**(2026-09-23・EDO-0398)── 口に門が建つなら
                //   seg の端は門の脇柱の角へ取り付ける。今の山王では板塀の口に門は無い(= 無為)が、
                //   閉じ方を種別ごとに分けると同じ欠陥がまた片側にだけ残る(規則21)。
                var pa = new List<Vector2>(); var pb = new List<Vector2>();
                foreach (var so in L(r, "segs"))
                {
                    var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
                    pa.Add(P2(seg[0])); pb.Add(P2(seg[1]));
                }
                float pHalfT, pHgt; PanelProfile(EdoAssets.Eg.Itabei5, out pHalfT, out pHgt);
                ClipRunEndsToGates(pa, pb, pHgt, pHalfT, hasSeat, seat, name, sb);
                KeepClearOfFlushWalls(pa, pb, name, sb);
                RetractRunEndsFromWalls(pa, pb, pHalfT, pHgt, hasSeat, seat, name, sb);
                ShiftRunToCutShoulder(pa, pb, pHalfT, pHgt, hasSeat, name, sb);
                var dgB = hasSeat ? null : EdoBuild.Drawn();
                Func<float, float, float> drawnBed = dgB == null ? (Func<float, float, float>)null : (x, z) => dgB.At(x, z);
                for (int i = 0; i < pa.Count; i++)
                {
                    Vector2 a = pa[i], b = pb[i];
                    float len = Vector2.Distance(a, b); if (len < 0.25f) continue;
                    Vector2 dir = (b - a) / len;
                    // 在庫の板塀(edogoyomi)。⚠ 呼び寸に合わせて走り方向だけ伸縮するのは
                    //   既存の `PanelRun` の流儀(全邸で同じ)。表裏2枚で `_kf`/`_kb` と名づく。
                    var outw = new Vector2(dir.y, -dir.x);
                    var beds = new List<GameObject>(); foreach (Transform c in Group("Dodome")) if (c.gameObject.activeInHierarchy) beds.Add(c.gameObject);
                    // ⭐ 座の無い run(地表なり)は描かれた地表の弦に張る(EdoBuild.SeatPanelOnBed・EDO-0437 第5巡)── Stage4 は皮(Stage9)の後に流す
                    //   ⭐ 足が土留めの天端に載る所は、床 = 描かれた地表と天端(触れている箇所)の高い方(第6巡)── 地表だけの弦は天端の下の皮へ傾き、
                    //   天端へ上げた後に反対の端が 0.46 浮いた(前庭の南西の板塀 `Ita_ZSW`)。受けは走りの近くの駒だけ(光線の数を抑える)
                    Func<float, float, float> bedFn = null;
                    if (!hasSeat)
                    {
                        var nearBeds = new List<GameObject>();
                        foreach (var bd in beds) { var rb = EdoBuild.RB(bd); Vector2 cc = new Vector2(rb.center.x, rb.center.z); if (EdoGeom.DistToEdge(cc, a, b) < 3f + rb.extents.magnitude) nearBeds.Add(bd); }
                        bedFn = nearBeds.Count == 0 ? drawnBed : (x, z) =>
                        {
                            float g = drawnBed(x, z), t = EdoBuild.BedTopAt(new Vector2(x, z), nearBeds, (float.IsNaN(g) ? 30f : g) + 8f);
                            return float.IsNaN(t) ? g : float.IsNaN(g) ? t : Mathf.Max(g, t);
                        };
                    }
                    var lst = EdoBuild.PanelRun(grp, a, b, outw, name, EdoAssets.Eg.Itabei5, Vector2.zero, -1, beds: beds, bedAt: hasSeat ? null : bedFn,
                        splitPost: EdoAssets.Own.ItabeiHashira, splitBoard: EdoAssets.Own.ItabeiIta);
                    made += lst.Count;
                }
            }
            else made = SakuRun(r, name, grp, hasSeat, seat, sb);
            pieces += made;
            sb.AppendLine("  " + name + "(" + kind + " " + F(r, "lenM").ToString("F1") + "m): 部材 " + made + " 枚" +
                          (hasSeat ? " / 天端 " + seat.ToString("F2") : " / 天端は地形なり"));
        }
        pieces += SukibeiKado(sb);
        if (pendNames.Count > 0)
            sb.AppendLine("  ★ 部材が無いので建てなかった(bom が「無い/新造」): " +
                          string.Join(" / ", pendNames.ToArray()) + " = 計 " + pending.ToString("F1") + "m");
        return "囲い: 部材 " + pieces + " 枚\n" + sb;
    }

    // ---------------------------------------------------------------- 腰高の柵
    /// <summary>腰高の柵の run。部材の原点 = **スパンの中心・地盤レベル**・柱はローカル −X 端。
    /// <para>⭐ **口(門の立つ開口)の縁は門の実メッシュから測る**(<see cref="EdoBuild.OpeningJambs"/>)。
    /// ⛔ 算出物の `segs` の端(= 紙の上の口の幅)をそのまま run の端にしない — 2026-09-22 実測で
    /// 勝手口の口 2.909m に対し門は走りへ 1.992m しか投影されず(39°傾き)、南 0.457 / 北 0.460m が
    /// 素通しだった。⭐ さらに 2026-09-23、**端は走りの線の上ではなく門の脇柱の角へ取る**ように改めた —
    /// 射影だけでは横のずれ(勝手口は線から 0.45m 外)が落ち、柵の端の柱と門の間に **0.822m の口**が
    /// 残っていた(EDO-0398)。</para>
    /// <para>⚠ **口の向こう側の縁に柱を足さない** — スパンの部材が −X 端に柱を持っている。
    /// 足すと二重になり、柱の原点が +X の木口なので設計の線の外へ 0.115m はみ出す
    /// (2026-09-22 に一度そう建て、`Saku_SW` / `Saku_Sando` の芯が 0.04〜0.05m 鳴った)。</para>
    /// <para>⭐ **斜面は地表の道のりで割る**(2026-09-23・EDO-0398)。継ぎ目は <see cref="EdoBuild.GroundPolyline"/>、
    /// 駒は <see cref="EdoBuild.PlaceOnChord"/> で弦に張る(継ぎ目は駒の丈の中ほどで合う)。
    /// ⛔ 水平の長さで割って駒を傾け直さない — 傾けた駒の水平の張り出しは pitch·cosθ に縮むので、
    /// 継ぎ目が毎回 pitch(1−cosθ) 開く(実測: `Saku_SW` の末尾 30° 区間で 0.19〜0.31m の素通し 4 箇所、
    /// 折れ目では逆に頭が 0.31〜0.40m 重なっていた)。</para>
    /// <para>⛔ **部材として建たない切れ端**(1スパンの 1/4 未満)はスパンを据えず、**外側の端に柱を
    /// 1本だけ**立てる。据えないと run が設計の線の端まで届かず、突き合わせが芯のずれとして出る
    /// (2026-09-22 実測: `Ita_Keidai` の 0.144m の切れ端で芯が 0.48m 寄っていた)。</para></summary>
    static int SakuRun(Dictionary<string, object> r, string name, Transform grp,
                       bool hasSeat, float seat, StringBuilder sb)
    {
        var sa = new List<Vector2>(); var sbb = new List<Vector2>();
        foreach (var so in L(r, "segs"))
        {
            var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
            sa.Add(P2(seg[0])); sbb.Add(P2(seg[1]));
        }
        if (sa.Count == 0) return 0;
        float halfT, hgt, postL; SakuProfile(out halfT, out hgt, out postL);
        ClipRunEndsToGates(sa, sbb, hgt, halfT, hasSeat, seat, name, sb);
        // ⭐ 座(`seat`)は**上限**。継ぎ目で駒の足元が床から浮くなら床へ(<see cref="EdoBuild.SeatOrBed"/>・2026-09-25・EDO-0430)──
        //   `Ita_Keidai` は座 28.30 の一本で、御供所の郭(27.35)の縁の区間が 0.8m 浮いていた。
        var bed = hasSeat ? GateBed() : null;
        var rootSpan = EdoBuild.RunMeasureY(P.SakuSpan).Root; var rootPost = EdoBuild.RunMeasureY(P.SakuPost).Root;
        int lowered = 0;
        Func<Vector2, float, float> SeatAt = (q, root) =>
        {
            float y = EdoBuild.SeatOrBed(q.x, q.y, seat, root, bed.At);
            if (y < seat) lowered++;
            return y;
        };
        // ⭐ 口の端を土留めの小口へ突き付ける(`kuchiAbut` = [柵の端, 土留めの最寄り] の対・2026-09-25)。
        //   土留めの**据わった駒の実メッシュ**まで、柵の丈の帯・半厚の幅で測って端を延ばす(⛔ 紙の点で止めない)。
        foreach (var ko in L(r, "kuchiAbut"))
        {
            var pr = ko as List<object>; if (pr == null || pr.Count < 2) continue;
            Vector2 fe = P2(pr[0]), wp = P2(pr[1]);
            var bodies = new List<GameObject>();
            foreach (Transform c in Group("Dodome")) if (Vector2.Distance(new Vector2(EdoBuild.RB(c.gameObject).center.x, EdoBuild.RB(c.gameObject).center.z), wp) < 4f) bodies.Add(c.gameObject);
            for (int i = 0; i < sa.Count; i++)
                foreach (bool atB in new[] { true, false })
                {
                    Vector2 e = atB ? sbb[i] : sa[i]; if (Vector2.Distance(e, fe) > 0.1f) continue;
                    float gy = hasSeat ? SeatAt(e, rootSpan) : SurfaceY(e);
                    // 走りの向きのまま延ばす(⛔ 紙の最寄りへ折らない ── 線から横へ 0.21m ずれた・2026-09-25 突き合わせ)
                    Vector2 run = atB ? (sbb[i] - sa[i]).normalized : (sa[i] - sbb[i]).normalized;
                    float reach = EdoBuild.ReachToBodies(e, run, bodies, halfT, gy, gy + hgt, Vector2.Distance(e, wp) + 2f);
                    if (float.IsNaN(reach)) { sb.AppendLine("    ⚠ " + name + ": 口の端 " + e.ToString("F2") + " の先に土留めの駒が無い — 延ばさない"); continue; }
                    Vector2 ne = e + run * reach;
                    if (atB) sbb[i] = ne; else sa[i] = ne;
                    sb.AppendLine("    " + name + ": 口の端を土留めの実面へ " + reach.ToString("F2") + "m 延ばした(紙の最寄りまで " + Vector2.Distance(e, wp).ToString("F2") + ")");
                }
        }
        RetractRunEndsFromWalls(sa, sbb, halfT, hgt, hasSeat, seat, name, sb);

        // ⭐ 座で据える走りは床の段(土留めの天端の縁)で割る(EdoBuild.SplitAtBedSteps・2026-09-26 EDO-0430)──
        //   割らないと落ちを跨ぐ弦が一本の斜めの駒になり、足元が前後の駒へめり込み反対の足が浮く(`Ita_Keidai_149f` 0.95m 落ち・26°)。
        if (hasSeat)
        {
            var na = new List<Vector2>(); var nb = new List<Vector2>(); int nSplit = 0;
            for (int i = 0; i < sa.Count; i++)
            {
                var parts = EdoBuild.SplitAtBedSteps(sa[i], sbb[i], (x, z) => EdoBuild.SeatOrBed(x, z, seat, rootSpan, bed.At), rootSpan);
                if (parts.Count > 1 || Vector2.Distance(parts[0][0], sa[i]) > 1e-4f || Vector2.Distance(parts[0][1], sbb[i]) > 1e-4f) nSplit++;
                foreach (var pr in parts) { na.Add(pr[0]); nb.Add(pr[1]); }
            }
            if (nSplit > 0) sb.AppendLine("    " + name + ": 床の段(土留めの天端の縁)で割った区間 " + nSplit + "(→ " + na.Count + " 区間)");
            sa = na; sbb = nb;
        }
        // 斜面なりに連ねるための実測(⛔ 定数で持たない) — 根入れが均しの縛り、丈の中ほどが継ぎ目の高さ。
        var rhy = EdoBuild.RunMeasureY(P.SakuSpan);
        float minSpan = SAKU_SPAN * 0.25f;   // これ未満は部材として建たない切れ端
        int made = 0, stubs = 0;
        for (int i = 0; i < sa.Count; i++)
        {
            Vector2 a = sa[i], b = sbb[i];
            float len = Vector2.Distance(a, b);
            Vector2 dir = len > 1e-6f ? (b - a) / len : Vector2.right;
            float ry = YawX(dir);
            if (len < minSpan)
            {
                // 切れ端 — スパンは据えず、**外側の端**(run の走りの先)に柱を1本だけ。
                // ⚠ 柱の部材は原点が **+X の木口**(局所 x ∈ [−postL, 0])なので、走りの先の端では
                //   節点にそのまま置けば run の内へ収まる。始まりの端だけ postL だけ送る。
                //   ⛔ 送らないと run が設計の線の外へ postL はみ出し、突き合わせが芯のずれで鳴る。
                Vector2 p = (i == 0) ? a + dir * postL : b;
                EdoBuild.Place(P.SakuPost, new Vector3(p.x, hasSeat ? SeatAt(p, rootPost) : SurfaceY(p), p.y), ry,
                               Vector3.one, grp, name + "_" + made.ToString("000") + "f");
                made++; stubs++;
                continue;
            }
            // ⛔ run の始まり・口の向こう側に柱を足さない — **スパンの部材が −X 端に柱を持っている**
            //   (`Saku_Koshidaka_1.818` の局所 x ∈ [−0.909, +0.909]・柱は −X 端)。足すと二重になり、
            //   しかも柱の原点が +X 木口なので設計の線の外へ 0.115m はみ出す(2026-09-22 に一度そう建てた)。
            // ⭐ **継ぎ目は地表の道のりで割る**(EdoBuild.GroundPolyline)。⛔ 水平の長さで割って駒を
            //    傾けない — 水平の張り出しが pitch·cosθ に縮んで継ぎ目が毎回開く(2026-09-23 実測:
            //    30° の斜面で 0.19〜0.31m の素通しが 4 箇所・EDO-0398)。
            List<Vector3> js;
            if (hasSeat)
            {
                int N = Mathf.Max(1, Mathf.RoundToInt(len / SAKU_SPAN));
                js = new List<Vector3>();
                for (int k = 0; k <= N; k++)
                {
                    Vector2 p = a + dir * (len * k / N);
                    // ⭐ 継ぎ目の高さは柱の足元の前後 0.25m(区間の中だけ)の床の低い方 ── 土留めの足の皮の擦り付け(0.11m の盛り上がり)を
                    //   拾うと落ちの直後の駒が 3.5° 傾き、丈の中ほどで継ぐので足元が土留めへ 0.03 下がり込んで天端の下へ 0.99m めり込んだ
                    //   (2026-09-26 `Ita_Keidai_149f`)。低い方へ取れば柱は浮かず、根入れが擦り付けに埋まるだけ。
                    float y = SeatAt(p, rootSpan);
                    foreach (float o in new[] { -0.25f, 0.25f })
                    {
                        float so = len * k / N + o; if (so < 0f || so > len) continue;
                        Vector2 q = a + dir * so; y = Mathf.Min(y, EdoBuild.SeatOrBed(q.x, q.y, seat, rootSpan, bed.At));
                    }
                    js.Add(new Vector3(p.x, y, p.y));
                }
            }
            else js = EdoBuild.GroundPolyline(a, b, SAKU_SPAN, rhy.Root, rhy.Root * 2f);
            for (int k = 0; k + 1 < js.Count; k++)
            {
                EdoBuild.PlaceOnChord(P.SakuSpan, js[k], js[k + 1], grp, name + "_" + made.ToString("000") + "f");
                made++;
            }
            // +X 端の柱(次の seg が続いていれば、その seg の始まりの柱を兼ねる)。
            // ⚠ 高さは**折れ線の末の継ぎ目**に合わせる(地表を引き直すと最後の駒と段が付く)。
            var jend = js[js.Count - 1];
            EdoBuild.Place(P.SakuPost, new Vector3(b.x, jend.y, b.y), ry, Vector3.one,
                           grp, name + "_" + made.ToString("000") + "f");
            made++;
        }
        if (stubs > 0)
            sb.AppendLine("    " + name + ": 切れ端に立てた柱 " + stubs + " 本(スパンにならない区間の端を設計の線まで通した)");
        if (lowered > 0)
            sb.AppendLine("    ⚠ " + name + ": 座 " + seat.ToString("F2") + " では足元が床から浮く継ぎ目 " + lowered + " 点を床へ下ろした(指図の seat は据わる面と食い違う)");
        return made;
    }
    /// <summary>腰高の柵の部材の**半厚**・**丈**・**柱の長さ**[m]を資産から測る。⛔ 定数で持たない
    /// (部材を替えた瞬間に口の縁が破れる)。走り = ローカル X・厚み = Z・原点 = 地盤。</summary>
    static void SakuProfile(out float halfT, out float hgt, out float postL)
    {
        halfT = 0f; hgt = 0f;
        var pts = EdoBuild.BodyAt(P.SakuSpan, Vector3.zero, 0f, true);
        if (pts.Count == 0) throw new Exception("⛔ 腰高の柵の部材 " + P.SakuSpan + " が測れない(半厚と丈を発明しない)");
        float mnY = float.MaxValue, mxY = float.MinValue;
        foreach (var v in pts)
        { halfT = Mathf.Max(halfT, Mathf.Abs(v.z)); mnY = Mathf.Min(mnY, v.y); mxY = Mathf.Max(mxY, v.y); }
        hgt = mxY - mnY;
        var pp = EdoBuild.BodyAt(P.SakuPost, Vector3.zero, 0f, true);
        if (pp.Count == 0) throw new Exception("⛔ 柵の柱の部材 " + P.SakuPost + " が測れない");
        float pmn = float.MaxValue, pmx = float.MinValue;
        foreach (var v in pp) { pmn = Mathf.Min(pmn, v.x); pmx = Mathf.Max(pmx, v.x); }
        postL = pmx - pmn;
    }
    /// <summary>板塀(edogoyomi の片面 obj)の**半厚**・**丈**[m]を資産から測る。⛔ 定数で持たない。
    /// ⚠ <see cref="EdoBuild.PanelRun"/> は既定で **ES 倍**して据えるので、測った局所寸へ ES を掛ける
    /// (走り方向だけは呼び寸へ伸縮するので、ここでは見ない)。</summary>
    static void PanelProfile(string path, out float halfT, out float hgt)
    {
        halfT = 0f; hgt = 0f;
        var pts = EdoBuild.BodyAt(path, Vector3.zero, 0f, true);
        if (pts.Count == 0) throw new Exception("⛔ 板塀の部材 " + path + " が測れない(半厚と丈を発明しない)");
        float mnY = float.MaxValue, mxY = float.MinValue;
        foreach (var v in pts)
        { halfT = Mathf.Max(halfT, Mathf.Abs(v.z)); mnY = Mathf.Min(mnY, v.y); mxY = Mathf.Max(mxY, v.y); }
        halfT *= EdoBuild.ES; hgt = (mxY - mnY) * EdoBuild.ES;
    }
    /// <summary>口(seg と seg の間)に門が建つなら、**両脇の seg の端を門の脇柱の角へ取り付ける**。
    /// <para>⭐ 2026-09-23(EDO-0398)**端は走りの線の上ではなく、門の実メッシュの角そのものへ取る**
    /// (<see cref="EdoBuild.OpeningJambs"/>)。⛔ 射影 s だけを線の上に取らない — 門は走りに対して
    /// 傾いて・横へずれて据わるので(勝手口は 39°・線から 0.45m 外)、線上の点には門の実体が無く、
    /// 柵の端の柱と門の間に **0.822m の口**が残っていた。角へ取り付ければ走りはそこで折れて門に当たる。
    /// 食い込み(<paramref name="halfT"/> = run の半厚)は「隙間 &gt; めり込み」の作法。</para>
    /// <para>⛔ 門が引けない口・門が塞いでいない口・端が seg を裏返す口は触らない(★ で報せる)。</para></summary>
    static void ClipRunEndsToGates(List<Vector2> a, List<Vector2> b, float hgt, float halfT,
                                   bool hasSeat, float seat, string name, StringBuilder sb)
    {
        for (int i = 0; i + 1 < a.Count; i++)
        {
            Vector2 A = b[i], B = a[i + 1];
            float gap = Vector2.Distance(A, B);
            if (gap < 0.20f) continue;                       // 折れ点(口ではない)
            Vector2 d = (B - A) / gap;
            foreach (var o in L(Impl, "gates"))
            {
                var gt = o as Dictionary<string, object>; if (gt == null) continue;
                var wp = L(gt, "world"); if (wp.Count < 2) continue;
                Vector2 c = new Vector2(Cv(wp[0]), Cv(wp[1]));
                float s = Vector2.Dot(c - A, d);
                if (s < -0.5f || s > gap + 0.5f) continue;    // この口の中に居ない
                if (Mathf.Abs(Vector2.Dot(c - A, new Vector2(-d.y, d.x))) > gap) continue;
                string path; Vector3 pos; float yaw;
                if (!GatePlacement(gt, out path, out pos, out yaw))
                { sb.AppendLine("  ★ " + name + ": 口の門 " + S(gt, "name") + " が引けない — 口の縁を測れない"); continue; }
                float y0 = hasSeat ? seat : SurfaceY((A + B) * 0.5f);
                Vector2 j0, j1; float s0, s1; string how;
                // ⚠ 控えの帯は**口の幅**を渡す。⛔ 塀の半厚(山王の柵で 0.062m)を渡さない —
                //   門は走りに対して傾いて・ずれて据わる(勝手口は 39°・線から 0.446m)ので、
                //   細い帯では門の頂点が1つも入らず「塞いでいない」と出て、口がそのまま素通しで残る。
                if (!EdoBuild.OpeningJambs(path, pos, yaw, A, B, gap, y0, y0 + hgt, halfT,
                                           out j0, out j1, out s0, out s1, out how))
                { sb.AppendLine("  ★ " + name + ": " + S(gt, "name") + " が走りの線を塞いでいない(口 " +
                                gap.ToString("F2") + "m は素通しのまま)"); continue; }
                if (s1 - s0 < 0.05f) continue;
                // ⛔ seg を裏返す端は採らない(門が口を丸ごと呑む/端が seg の始まりを越える)。
                Vector2 d0 = b[i] - a[i], d1 = b[i + 1] - a[i + 1];
                bool ok0 = d0.sqrMagnitude > 1e-6f && Vector2.Dot(j0 - a[i], d0.normalized) > 0.05f;
                bool ok1 = d1.sqrMagnitude > 1e-6f && Vector2.Dot(b[i + 1] - j1, d1.normalized) > 0.05f;
                if (!ok0 || !ok1)
                { sb.AppendLine("  ★ " + name + ": " + S(gt, "name") + " の脇柱が seg を裏返す(手前 " +
                                (ok0 ? "可" : "不可") + " / 先 " + (ok1 ? "可" : "不可") + ")— 端を動かさない"); continue; }
                float mv0 = Vector2.Distance(b[i], j0), mv1 = Vector2.Distance(a[i + 1], j1);
                b[i] = j0; a[i + 1] = j1;
                sb.AppendLine("    " + name + ": 口 " + gap.ToString("F3") + "m に " + S(gt, "name") +
                              " — 脇柱の角へ取り付けた 手前 (" + j0.x.ToString("F3") + ", " + j0.y.ToString("F3") +
                              ")(寄せ " + mv0.ToString("F3") + "m)/ 先 (" + j1.x.ToString("F3") + ", " +
                              j1.y.ToString("F3") + ")(寄せ " + mv1.ToString("F3") + "m)" +
                              " / 走りへの射影は [" + s0.ToString("F3") + ", " + s1.ToString("F3") + "](" + how + ")");
                break;
            }
        }
    }
    /// <summary>柵・板塀の run の端(始まり・終わり・口の両脇)が土留め・基壇の駒の中に在るなら、その実面まで詰める
    /// (<see cref="EdoBuild.RetractEndFromBodies"/>・2026-09-26 EDO-0430)── `Ita_Keidai` の始まりが回廊の基壇の隅の駒の中 0.85m まで入っていた。
    /// ⛔ 折れ点(次の区間が続く端)は触らない。Stage4 と突き合わせ(<see cref="BuiltSegs"/>)が同じ関数で引く。</summary>
    static void RetractRunEndsFromWalls(List<Vector2> sa, List<Vector2> sbb, float halfT, float hgt, bool hasSeat, float seat, string name, StringBuilder sb)
    {
        var dodAll = new List<GameObject>(); foreach (Transform c in Group("Dodome")) if (c.gameObject.activeInHierarchy) dodAll.Add(c.gameObject);
        for (int i = 0; i < sa.Count; i++)
            foreach (bool atB in new[] { false, true })
            {
                Vector2 e = atB ? sbb[i] : sa[i];
                bool fold = atB ? (i + 1 < sa.Count && Vector2.Distance(sa[i + 1], e) < 0.2f) : (i > 0 && Vector2.Distance(sbb[i - 1], e) < 0.2f);
                if (fold) continue;
                Vector2 inward = atB ? sa[i] - sbb[i] : sbb[i] - sa[i]; float sl = inward.magnitude; if (sl < 0.3f) continue;
                var near = new List<GameObject>();
                foreach (var g in dodAll) { var c = EdoBuild.RB(g).center; if (Vector2.Distance(new Vector2(c.x, c.z), e) < 5f) near.Add(g); }
                if (near.Count == 0) continue;
                float gy = hasSeat ? seat : SurfaceY(e);
                if (!hasSeat)
                {
                    // ⭐ 足が土留めの天端に載る端は、帯を天端(触れている箇所)から測る(2026-09-26・EDO-0437 第6巡)── 設計面から測ると
                    //   載っている天端の駒の小口を「端が駒の中」と読み、前庭の南西の板塀 `Ita_ZSW` を土留めの上から 2.05m 詰めて袖の上に残した
                    float bt = EdoBuild.BedTopAt(e, near, gy + 8f); if (!float.IsNaN(bt) && bt > gy) gy = bt;
                    // 走りの中ほどが受けの天端に載る run は、受けの駒が足の下に在る所まで端を詰める(受けの外=低い袖・地面の上へ延ばさない)
                    Vector2 mid = (sa[i] + sbb[i]) * 0.5f; float mt = EdoBuild.BedTopAt(mid, dodAll, gy + 8f);
                    if (!float.IsNaN(mt) && mt >= SurfaceY(mid) - 0.01f)
                    {
                        //   帯の下端は走りに沿う天端の最も高い所(割肌の天端は 0.2 出入りする ── 足は最も高い石に載る = RestOnBeds と同じ物差し)
                        for (float u = 0f; u <= sl + 1e-4f; u += 0.1f)
                        { float tb = EdoBuild.BedTopAt(e + inward.normalized * u, dodAll, gy + 8f); if (!float.IsNaN(tb) && tb > gy) gy = tb; }
                        var dgE = EdoBuild.Drawn();
                        float edge = EdoBuild.RetractEndToBedEdge(e, inward, dodAll, halfT, gy + 8f, sl * 0.5f, (x, z) => Mathf.Min(dgE.At(x, z), SurfaceY(new Vector2(x, z))));
                        if (edge > 0.002f)
                        {
                            e = e + inward.normalized * edge; if (atB) sbb[i] = e; else sa[i] = e;
                            inward = atB ? sa[i] - sbb[i] : sbb[i] - sa[i]; sl = inward.magnitude;
                            sb.AppendLine("    " + name + ": " + (atB ? "終わり" : "始まり") + "の端を受けの土留めの天端が足の下に在る所まで " + edge.ToString("F3") + "m 詰めた");
                        }
                    }
                }
                // 測る帯は地表から上(`kuchiAbut` と同じ物差し)。⚠ 根入れまで測ると法 1:0.25 の面では見える帯の全高で口が 0.07 広がる
                //   (口の端 2 箇所で 0.038/0.063 詰めて許容 0.05 を超えた・2026-09-26)。土の中の根が法の足へ触れる 0.02 は数に残す。
                float back = EdoBuild.RetractEndFromBodies(e, inward, near, halfT, gy, gy + hgt, Mathf.Min(3f, sl * 0.9f));
                if (back <= 0.002f) continue;
                Vector2 ne = e + inward.normalized * back;
                if (atB) sbb[i] = ne; else sa[i] = ne;
                sb.AppendLine("    " + name + ": 端 " + e.ToString("F2") + " が土留めの駒の中 ── 実面まで " + back.ToString("F3") + "m 詰めた");
            }
    }
    /// <summary>**切土の法に沿う板塀の走りを法肩の上へ移す**(2026-09-26・EDO-0437 施主裁定イ)。座(`seat`)の無い run の区間が、郭の
    /// `terraces[].cutSlopes` の法尻の線と平行(3°以内)で 1 間以内・走りが重なるなら、その区間は法の上(面の外の地山)に建てる:
    /// 法尻から面の外へ、区間の 13 点で法肩(<see cref="EdoBuild.CutShoulder"/> ── 法の面 × 造成前の地山 base_dem)を測り、
    /// **最も遠い法肩 + 離れ**の平行線へ移す(一直線を保つ・全長が法肩の背の側)。離れ = 移す前の走りと法尻の線の離れ(板塀が縁から取る離れを法肩から取る)。
    /// 端が相手の駒(郭の縁の土留め・石段の袖)に届くなら、その**外面から同じ離れ**へ端を取り直す(面を光線で測る・<see cref="EdoBuild.ReachToBodies"/>)。
    /// 当たらない端は移したまま。⛔ json の a・b(紙の点)のまま前庭の面の上に建てない。硬い条件: 塀の走りが法の面・法肩の内に入らない。
    /// 当たる先: 山王 前庭の南の板塀 `Ita_ZSE`。切土の法の上に座の無い柵・板塀を建てる区間すべて(Stage4 と突き合わせの <see cref="BuiltSegs"/> が同じ関数を通る)。</summary>
    static void ShiftRunToCutShoulder(List<Vector2> sa, List<Vector2> sbb, float halfT, float hgt, bool hasSeat, string name, StringBuilder sb)
    {
        if (hasSeat || sa.Count == 0) return;
        float batter = F(D(Doc, "const"), "batterCut"); if (batter <= 0f) batter = 1f;
        float ken = F(D(Impl, "grid"), "ken");
        for (int i = 0; i < sa.Count; i++)
        {
            Vector2 a = sa[i], b = sbb[i]; float len = Vector2.Distance(a, b); if (len < 0.3f) continue;
            Vector2 dr = (b - a) / len;
            foreach (var to in L(Doc, "terraces"))
            {
                var t = to as Dictionary<string, object>; if (t == null) continue;
                var polyUv = Pts(L(t, "poly")); if (polyUv.Count < 3) continue;
                var poly = new Vector2[polyUv.Count]; for (int k = 0; k < poly.Length; k++) poly[k] = W(polyUv[k].x, polyUv[k].y);
                float floorY = F(t, "y");
                foreach (var co in L(t, "cutSlopes"))
                {
                    var cs = co as Dictionary<string, object>; if (cs == null) continue;
                    Vector2 A = P2(G(cs, "a")), B = P2(G(cs, "b")); A = W(A.x, A.y); B = W(B.x, B.y);
                    float cl = Vector2.Distance(A, B); if (cl < 0.3f) continue; Vector2 dc = (B - A) / cl;
                    if (Mathf.Abs(dr.x * dc.y - dr.y * dc.x) > Mathf.Sin(3f * Mathf.Deg2Rad)) continue;
                    Vector2 nc = new Vector2(dc.y, -dc.x);
                    Vector2 mid = (A + B) * 0.5f;
                    if (EdoGeom.PIP(poly, mid + nc * 0.3f)) nc = -nc;             // 面の外(地山)の側
                    if (EdoGeom.PIP(poly, mid + nc * 0.3f) || !EdoGeom.PIP(poly, mid - nc * 0.3f)) continue;
                    float offA = Vector2.Dot(a - A, nc), offB = Vector2.Dot(b - A, nc);
                    if (Mathf.Abs(offA) > ken || Mathf.Abs(offB) > ken) continue;
                    float pa0 = Vector2.Dot(a - A, dc), pb0 = Vector2.Dot(b - A, dc);
                    if (Mathf.Max(pa0, pb0) < 0.1f || Mathf.Min(pa0, pb0) > cl - 0.1f) continue;   // 走りが重ならない
                    if (_dem == null) _dem = DemAt();
                    // 離れ: 移す前の走りと法尻の線の離れ(面の側でも外の側でも大きさで)
                    float clr = Mathf.Abs((offA + offB) * 0.5f);
                    float tMax = 0f; int nMeas = 0;
                    for (int k = 0; k <= 12; k++)
                    {
                        float s = Mathf.Clamp(Mathf.Lerp(pa0, pb0, k / 12f), 0f, cl);
                        float tt = EdoBuild.CutShoulder(A + dc * s, nc, floorY, batter, _dem);
                        if (float.IsNaN(tt)) continue; nMeas++; tMax = Mathf.Max(tMax, tt);
                    }
                    if (nMeas == 0) { sb.AppendLine("    ⚠ " + name + ": 法「" + S(cs, "name") + "」の法肩が地山で測れない ── 移さない"); continue; }
                    float off = tMax + clr;
                    Vector2 na = A + dc * pa0 + nc * off, nb = A + dc * pb0 + nc * off;
                    sb.AppendLine("    " + name + ": 法「" + S(cs, "name") + "」の法肩の上へ移す(法肩 最遠 " + tMax.ToString("F3") + "m・測った " + nMeas +
                                  " 点 + 離れ " + clr.ToString("F3") + "m ⇒ 法尻から " + off.ToString("F3") + "m 背の側)");
                    // 端: 相手の駒(土留め・石段の袖)の外面から同じ離れへ取り直す
                    var bodies = new List<GameObject>();
                    foreach (Transform c in Group("Dodome")) if (c.gameObject.activeInHierarchy) bodies.Add(c.gameObject);
                    foreach (Transform g in Group("Sando")) foreach (Transform c in g) if (c.gameObject.activeInHierarchy && c.name.StartsWith("TW_")) bodies.Add(c.gameObject);
                    foreach (bool atB in new[] { false, true })
                    {
                        Vector2 e = atB ? nb : na, outRun = atB ? dr : -dr;
                        var near = new List<GameObject>();
                        foreach (var g in bodies) { var c = EdoBuild.RB(g).center; if (Vector2.Distance(new Vector2(c.x, c.z), e) < len + 2f) near.Add(g); }
                        if (near.Count == 0) continue;
                        float back = Mathf.Min(1.5f, len * 0.4f); Vector2 from = e - outRun * back;
                        float gy = SurfaceY(e);
                        //   届く先は走りの長さまで(相手の駒の外面が端より先に在れば延ばす ── `Ita_ZSE` の西の端は女坂の袖まで 3.4m)
                        float h = EdoBuild.ReachToBodies(from, outRun, near, halfT, gy, gy + hgt, back + len);
                        string how = "相手の駒の外面から離れ";
                        if (float.IsNaN(h))
                        {
                            // ⭐ 塀の高さに相手の面が無い(相手の天端が塀の足元より低い)端は、**法肩の線**が相手の駒に突き当たる所から
                            //   離れ(0.25 間)手前で打ち切る(2026-09-26・EDO-0437 第5巡・指図 Ita_ZSE の西の端)。法肩の線(塀の線から法尻へ
                            //   離れだけ戻した線)に沿って、地表から 2m 下までの帯で相手の駒の面を光線で測る(面で測る・紙の点で打ち切らない)。
                            //   塀は相手へ向けて下りず、相手に触れない。当たる先: 切土の法の法肩に建てる板塀・柵の端が石段の袖・土留めに届く所。
                            Vector2 fromS = from - nc * clr; float gs = SurfaceY(fromS + outRun * back);
                            h = EdoBuild.ReachToBodies(fromS, outRun, near, 0f, gs - 2.0f, gs + 0.05f, back + len);
                            if (float.IsNaN(h)) continue;
                            // ⭐ 端は**法肩の線が相手へ向けて下り始める所**(2026-09-26・EDO-0437 第6巡・指図 Ita_ZSE の西の端)。
                            //   突き当たる所の手前まで法肩の高さを測り、最高から 0.05m(測りの刻み)を超えて落ちる一つ手前で止める。
                            //   塀は相手へ向けて下りず、相手に触れない(突き当たりから離れを取った所より先へは出ない)。硬い条件。
                            Vector2 toe0 = fromS - nc * tMax; var prof = new StringBuilder(); var dgS = EdoBuild.Drawn();
                            float lev = EdoBuild.ShoulderLevelEnd(toe0, outRun, nc, floorY, batter, _dem, Mathf.Max(0f, h - clr), 0.05f, prof, (x, z) => dgS.At(x, z));
                            sb.AppendLine("    " + name + ": 法肩の高さ(端から内へ " + back.ToString("F2") + "m の所から外へ)" + prof);
                            float hitAt = h - clr; h = lev + clr;
                            how = "法肩の線が相手へ向けて下り始める所(突き当たりから離れを取った所まで " + (hitAt - lev).ToString("F3") + "m 手前)── 端からの寸法";
                        }
                        Vector2 ne = from + outRun * (h - clr);
                        sb.AppendLine("    " + name + ": " + (atB ? "終わり" : "始まり") + "の端を" + how + " " + clr.ToString("F3") + "m へ取り直す(" +
                                      (Vector2.Dot(ne - e, outRun) >= 0 ? "延ばす " : "詰める ") + Vector2.Distance(ne, e).ToString("F3") + "m)");
                        if (atB) nb = ne; else na = ne;
                    }
                    sa[i] = na; sbb[i] = nb; goto nextSeg;
                }
            }
            nextSeg:;
        }
    }
    static Func<float, float, float> _dem;

    /// <summary>run の `segs` を、**Stage4 が実際に建てる区間**へ直して返す(口に門が建つなら、その縁を
    /// 門の脇柱の角へ取り付けた後の端)。⭐ 突き合わせ(<see cref="EdoSannoSashizuCheck"/>)が同じ物差しで
    /// 線を引くための入口(2026-09-23・EDO-0413)── ⛔ 検査が口の閉じ方を別に持たない。持つと、
    /// 脇柱へ折れて取り付いた駒(勝手口の脇の `Ita_Keidai_172f`)が線から 0.49m 外れていると出る。
    /// 門が建たない種別(透塀・袖塀・回廊)は `segs` のまま。</summary>
    public static void BuiltSegs(Dictionary<string, object> r, List<Vector2> a, List<Vector2> b)
    {
        a.Clear(); b.Clear();
        foreach (var so in L(r, "segs"))
        {
            var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
            a.Add(P2(seg[0])); b.Add(P2(seg[seg.Count - 1]));
        }
        string kind = S(r, "kind");
        if (kind == "透塀" || kind == "袖塀" || kind == "回廊") return;
        bool hasSeat = HasNum(r, "seat"); float seat = F(r, "seat");
        float halfT, hgt;
        if (kind == "板塀") PanelProfile(EdoAssets.Eg.Itabei5, out halfT, out hgt);
        else { float postL; SakuProfile(out halfT, out hgt, out postL); }
        ClipRunEndsToGates(a, b, hgt, halfT, hasSeat, seat, S(r, "name"), new StringBuilder());
        KeepClearOfFlushWalls(a, b, S(r, "name"), null);
        RetractRunEndsFromWalls(a, b, halfT, hgt, hasSeat, seat, S(r, "name"), new StringBuilder());
        if (kind == "板塀") ShiftRunToCutShoulder(a, b, halfT, hgt, hasSeat, S(r, "name"), new StringBuilder());
    }
    /// <summary>算出物の `gates[]` の行から、据える部材のパス・座・向きを引く(Stage5 と同じ物差し)。
    /// ⛔ ここで向きを作らない — `gates[].yaw` は焼いた従属値。引けなければ false。</summary>
    static bool GatePlacement(Dictionary<string, object> gt, out string path, out Vector3 pos, out float yaw)
    {
        path = null; pos = Vector3.zero; yaw = 0f;
        if (!HasNum(gt, "yaw")) return false;
        var wp = L(gt, "world"); if (wp.Count < 2) return false;
        path = BomPartPath(S(gt, "bom"));
        if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) return false;
        pos = new Vector3(Cv(wp[0]), F(gt, "sill"), Cv(wp[1]));
        yaw = F(gt, "yaw");
        return true;
    }

    // ---------------------------------------------------------------- 回廊
    /// <summary>回廊の翼を1本据える(2026-09-20 に建てはじめた)。
    /// **部材の規約は `EdoAssets.Own.SannoKairo` の註が正典** ── 走り = ローカル X・高さ = Y・梁間 = Z、
    /// **見え面(腰板+連子窓の閉じた壁)= +Z = 外(東)**、ピボット = 柱芯の矩形の中心・**床(= 基壇の天端 `seat`)**。
    /// ⛔ `SeatBottom` しない(部材は基壇を持たない ── 石垣が受ける)。
    /// ⛔ **実装は寸法を一つも持たない** ── 綴りは 指図 `runs[].bays`/`bariBays`/`bari`(間)と
    /// 算出物 `runs[].lenM` からの従属値。引けなければ据えずに差し戻す。
    /// ⭐ 走り X について軸部は鏡像対称なので、+Z を東へ向けるために走りを **−dir** に取ってよい。</summary>
    static int Kairo(Dictionary<string, object> r, string name, Transform grp, StringBuilder sb)
    {
        var doc = FindByName(Doc, "runs", name);
        if (doc == null) { sb.AppendLine("  ★ " + name + ": 指図の run が引けない"); return 0; }
        if (!HasNum(doc, "bays") || !HasNum(doc, "bariBays") || !HasNum(doc, "bari"))
        { sb.AppendLine("  ★ " + name + ": `bays`/`bariBays`/`bari` が指図に無い(⛔ 発明しない)"); return 0; }
        if (!HasNum(r, "seat")) { sb.AppendLine("  ★ " + name + ": `seat`(基壇の天端)が算出物に無い"); return 0; }
        float ken = F(D(Impl, "grid"), "ken");
        string path = EdoAssets.Own.SannoKairo(
            Mathf.RoundToInt(F(doc, "bays")), Mathf.RoundToInt(F(doc, "bariBays")),
            Mathf.RoundToInt(F(r, "lenM") * 1000f), Mathf.RoundToInt(F(doc, "bari") * ken * 1000f));
        if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
        { sb.AppendLine("  ★ " + name + ": 部材 " + path + " が無い(部材方へ)"); return 0; }
        var pts = Pts(L(r, "nodes"));
        if (pts.Count < 2) { sb.AppendLine("  ★ " + name + ": nodes が無い"); return 0; }
        Vector2 a = pts[0], b = pts[pts.Count - 1];
        Vector2 dir = (b - a).normalized;
        Vector2 c = (a + b) * 0.5f;
        float seat = F(r, "seat");
        // ⭐ YawX(d) はローカル +X を d へ向ける ⇒ そのとき +Z は d の**左手**(−dir を取れば東)。
        var go = EdoBuild.Place(path, new Vector3(c.x, seat, c.y), YawX(-dir), Vector3.one,
                                grp, name + "_000f");
        var bb = EdoBuild.RB(go);
        sb.AppendLine("  " + name + "(回廊 " + F(r, "lenM").ToString("F2") + "m): " +
                      System.IO.Path.GetFileNameWithoutExtension(path) +
                      " 芯 (" + c.x.ToString("F2") + ", " + c.y.ToString("F2") + ") yaw " +
                      YawX(-dir).ToString("F1") + " 床 " + seat.ToString("F2") +
                      " / 実メッシュ 芯 (" + bb.center.x.ToString("F2") + ", " + bb.center.z.ToString("F2") +
                      ") 下端 " + (bb.center.y - bb.extents.y).ToString("F2") +
                      " 上端 " + (bb.center.y + bb.extents.y).ToString("F2"));
        return 1;
    }

    // ---------------------------------------------------------------- 透塀
    /// <summary>部材表の行を名で引く。⛔ 寸法をここに写さない。</summary>
    static Dictionary<string, object> FindBom(string label)
    {
        foreach (var o in L(Doc, "bom"))
        { var b = o as Dictionary<string, object>; if (b != null && S(b, "部材") == label) return b; }
        return null;
    }
    const string BOM_SUKIBEI = "透塀(連子窓の塀)";
    /// <summary>`bom[<label>].手当` が名指す**部材のパス**を引く(「… → `Assets/….fbx`」の最初の一つ)。
    /// ⭐ **パスの出所は指図**で、実装は綴りを持たない(規則12 の趣旨)。
    /// ⛔ 「⛔ 旧 `Assets/…` は据えない」と続く後ろのパスを拾わない ── **最初の一つだけ**。</summary>
    static string BomPartPath(string label)
    {
        var b = label == null ? null : FindBom(label); if (b == null) return null;
        string te = S(b, "手当"); if (te == null) return null;
        int arrow = te.IndexOf('→'); if (arrow < 0) return null;
        int i = te.IndexOf("Assets/", arrow, StringComparison.Ordinal); if (i < 0) return null;
        int e = te.IndexOf(".fbx", i, StringComparison.Ordinal); if (e < 0) return null;
        return te.Substring(i, e + 4 - i);
    }
    /// <summary>門の名 → シーンの名(⛔ 部材のパスではない)。
    /// ⭐ **突き合わせ(`EdoSannoSashizuCheck`)も同じ物差しで引く ⇒ public**。</summary>
    public static string GateNameOf(string designName)
    {
        if (designName == null) return "Mon";
        if (designName.StartsWith("隨身門")) return "Romon";
        if (designName.StartsWith("中門")) return "Chumon";
        if (designName.StartsWith("坂下の門")) return "Sakashitamon";
        if (designName.StartsWith("勝手口")) return "Kido";
        return designName;
    }
    /// <summary>透塀の一辺を据える。**割り付けは指図の規約**(`bom[透塀].spanBaseM` で辺を等分 ──
    /// 本数 = round(辺長 / 基準スパン)・スパン = 辺長 / 本数)で、⛔ 実装は数を持たない。
    /// 端の種類は −X, +X の順: c = 隅部材へ続く / n = 次のスパンへ / t = 中門へ突き付け /
    /// h = 口の縁の柱(南の潜り)。⚠ 部材の原点 = スパンの中心・床(= 基壇の天端 = `seat`)。</summary>
    /// <summary>透塀の丈(棟の天端・床から)[m]。⚠ 部材の設計値の写し(正典は `EdoAssets.Own.SannoSukibei` の註)。
    /// 口の縁を門の実メッシュで測る高さの帯にだけ使う(⛔ 位置合わせの基準点ではない)。</summary>
    const float SUKIBEI_H = 2.25f;
    static int Sukibei(Dictionary<string, object> r, string name, Transform grp, StringBuilder sb)
    {
        var bom = FindBom(BOM_SUKIBEI);
        if (bom == null || !HasNum(bom, "spanBaseM"))
        { sb.AppendLine("  ★ " + name + ": `bom[" + BOM_SUKIBEI + "].spanBaseM` が無い(割り付けを決められない)"); return 0; }
        float baseM = F(bom, "spanBaseM");
        var dr = FindByName(Doc, "runs", name);
        // 口の端の種類 ── 中門へ突き付けるなら "t"(`gapFrom`)、宣言があれば `gapEnd`。⛔ 無ければ据えない。
        string eg = (dr != null && D(dr, "gapFrom") != null) ? "t" : (dr == null ? null : S(dr, "gapEnd"));
        var segs = L(r, "segs");
        float seat = F(r, "seat");
        int made = 0;
        // ⭐ 中門へ突き付ける端(t)は**門の実メッシュで測った本柱の外面**へ取る(柵・板塀と同じ物差し
        //   `ClipRunEndsToGates` → `EdoBuild.OpeningJambs`)。⛔ 算出物の seg の端(紙の上の本柱の外面)のまま据えない ──
        //   2026-09-24 実測で Sukibei_E の t の端と中門の本柱に 0.006/0.007m の隙が残った。等分はその後の実長で割る。
        var pa = new List<Vector2>(); var pb = new List<Vector2>();
        foreach (var so in segs)
        {
            var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
            pa.Add(P2(seg[0])); pb.Add(P2(seg[1]));
        }
        //   食い込み(bite)は 0 ── t の木口は走りに直角の破風板で、中門は同じ軸(境内の軸)に据わるので楔が残らない。
        //   ⛔ 柵・板塀と同じく半厚を食い込ませると 0.30m 門の中へ入る(2026-09-24 に一度そう流して 1725 の部材を探した)。
        //   端は**走りの線の上**へ戻す(射影だけ採る)── `ClipRunEndsToGates` は傾いた門のために脇柱の角の点を返すが、
        //   透塀は境内の軸の一直線(隅部材と中門の間)で、角の点を採ると走りが 0.06° 振れて隅の側で目違う。
        if (eg == "t")
        {
            var qa = new List<Vector2>(pa); var qb = new List<Vector2>(pb);
            ClipRunEndsToGates(pa, pb, SUKIBEI_H, 0f, true, seat, name, sb);
            for (int si = 0; si < pa.Count; si++)
            {
                Vector2 dd = (qb[si] - qa[si]).normalized;
                pa[si] = qa[si] + dd * Vector2.Dot(pa[si] - qa[si], dd);
                pb[si] = qa[si] + dd * Vector2.Dot(pb[si] - qa[si], dd);
            }
        }
        // ⭐ run の端の先へ別の透塀が一直線に続く(同じ座・隅が立たない継ぎ目)なら、その端は c でなく n(次のスパンへ・柱は +X の端)。
        //   ⛔ 一律に c で閉じると継ぎ目に 0.18m の口が開き柱も立たない(EdoBuild.ContinuesStraight・2026-09-25)。
        var others = new List<Vector2[]>();
        foreach (var o in L(Impl, "runs"))
        {
            var ro = o as Dictionary<string, object>; if (ro == null || ro == r || S(ro, "kind") != "透塀") continue;
            if (Mathf.Abs(F(ro, "seat") - seat) > 0.01f) continue;
            var nd = Pts(L(ro, "nodes")); if (nd.Count >= 2) others.Add(new Vector2[] { nd[0], nd[nd.Count - 1] });
        }
        for (int si = 0; si < pa.Count; si++)
        {
            Vector2 a = pa[si], b = pb[si];
            float len = Vector2.Distance(a, b); if (len < 0.2f) continue;
            Vector2 dir = (b - a) / len;
            string e0 = (si == 0) ? (EdoBuild.ContinuesStraight(a, -dir, others) ? "n" : "c") : eg,
                   e1 = (si == pa.Count - 1) ? (EdoBuild.ContinuesStraight(b, dir, others) ? "n" : "c") : eg;
            if (si == 0 && e0 == "n") sb.AppendLine("  " + name + ": 始まりの端は一直線に続く透塀の継ぎ目 — 端 n");
            if (si == pa.Count - 1 && e1 == "n") sb.AppendLine("  " + name + ": 終わりの端は一直線に続く透塀の継ぎ目 — 端 n(柱)");
            if (e0 == null || e1 == null)
            { sb.AppendLine("  ★ " + name + ": 口の端の種類(`gapEnd`)が指図に無い — この辺は据えない"); continue; }
            int N = Mathf.Max(1, Mathf.RoundToInt(len / baseM));
            float span = len / N;
            for (int k = 0; k < N; k++)
            {
                string ends = (N == 1) ? (e0 + e1) : (k == 0 ? e0 + "n" : (k == N - 1 ? "n" + e1 : "nn"));
                string part = SukibeiPart(span, ends, name, sb);
                if (part == null) continue;
                Vector2 c = a + dir * (span * (k + 0.5f));
                EdoBuild.Place(part, new Vector3(c.x, seat, c.y), YawX(dir), Vector3.one, grp,
                               name + "_" + made.ToString("000") + "f");
                made++;
            }
        }
        return made;
    }
    /// <summary>スパンの呼び寸[m]と端の種類から部材を引く。⚠ 算出物の座標は小数4桁で丸まっているので
    /// **1mm 級の食い違いが出る**(`Sukibei_S` の 2530 ⇔ 焼いた 2531)。⇒ ±2mm まで探し、
    /// 拾ったら**そう名乗る**。⛔ 似た寸法の別部材で代用しない(見つからなければ据えない)。</summary>
    static string SukibeiPart(float spanM, string ends, string name, StringBuilder sb)
    {
        int mm = Mathf.RoundToInt(spanM * 1000f);
        int[] cand = new int[] { mm, mm + 1, mm - 1, mm + 2, mm - 2 };
        for (int i = 0; i < cand.Length; i++)
        {
            string p = EdoAssets.Own.SannoSukibei(cand[i], ends);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) continue;
            if (i > 0) sb.AppendLine("  ⚠ " + name + ": スパン " + mm + "mm の部材が無いので " + cand[i] +
                                     "mm(端 " + ends + ")を据えた ── 差 " + (cand[i] - mm) + "mm(算出物の丸め)");
            return p;
        }
        sb.AppendLine("  ★ " + name + ": 透塀のスパン部材 " + mm + "_" + ends + " が無い(部材方へ)");
        return null;
    }
    /// <summary>透塀の隅部材を据える。**隅は `joints` が名指す run の対**(8箇所)で、
    /// 出隅・入隅の別は**折れ線の凹凸から測る**(⛔ 決め打ちしない)。
    /// 部材の註: 出隅 = 脚が −X と −Z / 入隅 = 脚が −X と +Z・ピボット = 隅の柱の芯・床。
    /// ⚠ `joints` の呼び名(「北の段の入隅」など)と折れ線の凹凸が食い違う隅は**名指しで刷る**
    /// (⛔ 黙って直さない — 指図方へ差し戻す材料)。</summary>
    static int SukibeiKado(StringBuilder sb)
    {
        // 透塀の折れ線の向き(反時計回りか)を測る ── 凹凸の符号の基準。
        float area = 0f; Vector2 prev = Vector2.zero; bool first = true; Vector2 head = Vector2.zero;
        foreach (var o in L(Impl, "runs"))
        {
            var r = o as Dictionary<string, object>; if (r == null || S(r, "kind") != "透塀") continue;
            var nd = Pts(L(r, "nodes")); if (nd.Count < 2) continue;
            if (first) { head = nd[0]; prev = nd[0]; first = false; }
            for (int i = 1; i < nd.Count; i++) { area += prev.x * nd[i].y - nd[i].x * prev.y; prev = nd[i]; }
        }
        if (first) return 0;
        area += prev.x * head.y - head.x * prev.y;
        float orient = Mathf.Sign(area);

        var bom = FindBom(BOM_SUKIBEI);
        // ⛔ 隅の群は **一度だけ**掃く(run の群は Stage4 の輪の中で掃かれるが、ここは輪の外)。
        var kgrp = Group("Kakoi/Sukibei_Kado"); Clear(kgrp);
        int made = 0;
        foreach (var o in L(Doc, "joints"))
        {
            var j = o as Dictionary<string, object>; if (j == null) continue;
            // ⭐ **隅は `kadoFrom` が名指す**(`in` = 入る辺 / `out` = 出る辺 / `name` = 呼び名)。
            //   ⛔ `kind` に「隅」を探さない ── 2026-09-16(K059)に凹凸が折れ線からの従属値へ
            //   改まって `kind` が null になり、⛔ **隅が 0 箇所**になっていた(棟梁 2026-09-20)。
            var kf = D(j, "kadoFrom"); if (kf == null) continue;
            string an = S(kf, "in"), bn = S(kf, "out"), kadoName = S(kf, "name");
            if (an == null || bn == null) continue;
            var ra = FindByName(Impl, "runs", an); var rb = FindByName(Impl, "runs", bn);
            if (ra == null || rb == null || S(ra, "kind") != "透塀") continue;
            var na = Pts(L(ra, "nodes")); var nb = Pts(L(rb, "nodes"));
            if (na.Count < 2 || nb.Count < 2) continue;
            Vector2 node = na[na.Count - 1];
            if (Vector2.Distance(node, nb[0]) > 0.05f)
            { sb.AppendLine("  ★ 隅 " + an + "→" + bn + ": 折れ線の端が一致しない — 据えない"); continue; }
            Vector2 e1 = (na[na.Count - 2] - node).normalized;   // 隅から a の辺へ
            Vector2 e2 = (nb[1] - node).normalized;              // 隅から b の辺へ
            float turn = ((-e1.x) * e2.y - (-e1.y) * e2.x) * orient;   // > 0 なら出隅(凸)
            bool dezumi = turn > 0f;
            // 脚を辺へ合わせる: 出隅は Z = rot(X)・入隅は Z = −rot(X)(rot(v) = (−v.y, v.x))。
            //   ⇒ −X = f・(出隅) −Z = g / (入隅) +Z = g となる (f, g) の組を二通りから選ぶ。
            Vector2 f = e1, g = e2;
            Vector2 want = dezumi ? new Vector2(-e1.y, e1.x) : new Vector2(e1.y, -e1.x);
            if (Vector2.Dot(want, e2) < 0.9f)
            {
                f = e2; g = e1;
                Vector2 want2 = dezumi ? new Vector2(-e2.y, e2.x) : new Vector2(e2.y, -e2.x);
                if (Vector2.Dot(want2, e1) < 0.9f)
                { sb.AppendLine("  ★ 隅 " + an + "→" + bn + ": 直角でないので隅部材を向けられない — 据えない"); continue; }
            }
            string part = EdoAssets.Own.SannoSukibeiKado(dezumi ? "Dezumi" : "Irizumi");
            if (AssetDatabase.LoadAssetAtPath<GameObject>(part) == null)
            { sb.AppendLine("  ★ 隅 " + an + "→" + bn + ": 隅部材 " + part + " が無い(部材方へ)"); continue; }
            float seat = F(ra, "seat");
            // ⭐ 隅は **run の群に入れない**。⛔ `<run名>_NNNf` と名づけると突き合わせが
            //   隅を run の外接矩形に混ぜ、run ごとに 0.29m の**偽の芯ずれ**を 8 本出す
            //   (2026-09-20 棟梁の実測)。隅は `joints[].kadoFrom` が立てる別の物なので
            //   群も名も別に取る(名 = `Kado_<in>_<out>`。⚠ `kadoFrom.name` は「北の段」が
            //   2 箇所あって一意にならない)。
            EdoBuild.Place(part, new Vector3(node.x, seat, node.y), YawX(-f), Vector3.one, kgrp,
                           "Kado_" + an + "_" + bn);
            sb.AppendLine("    隅 " + (kadoName ?? (an + "→" + bn)) + ": " + (dezumi ? "出隅" : "入隅") +
                          " (" + node.x.ToString("F2") + ", " + node.y.ToString("F2") + ") 床 " + seat.ToString("F2"));
            made++;
        }
        sb.AppendLine("  透塀の隅: " + made + " 箇所(出隅・入隅は折れ線の凹凸から = `kadoFrom` の従属値)");
        return made;
    }

    // ---------------------------------------------------------------- 袖塀
    /// <summary>袖塀(楼門と回廊の翼の間)を据える。部材の註: 走り = X・**門側 = −X**・
    /// ピボット = 走りの中心・門側の足元(= 楼門の敷居)。⛔ 柵や築地塀で代用しない。
    /// ⚠ **門側の木口は据えた楼門の側柱の外面へ寄せる**のが `joints` の指定だが、
    /// 門はこの巡の範囲外(Stage 5)なので**設計の線のまま**据えてある(→ 報告)。</summary>
    static int Sodebei(Dictionary<string, object> r, string name, Transform grp, StringBuilder sb)
    {
        var dr = FindByName(Doc, "runs", name);
        var bom = dr == null ? null : FindBom(S(dr, "bom"));
        var ax = bom == null ? null : D(bom, "axis");
        var fa = ax == null ? null : D(ax, "footAt");
        var st = fa == null ? null : D(fa, "step");
        if (st == null) { sb.AppendLine("  ★ " + name + ": `bom[…].axis.footAt.step` が無い(部材を引けない)"); return 0; }
        if (S(ax, "gateSide") != "-X")
        { sb.AppendLine("  ★ " + name + ": 部材の門側が `-X` でない(" + S(ax, "gateSide") + ")— 向きを決められない"); return 0; }
        var nodes = Pts(L(r, "nodes")); if (nodes.Count < 2) return 0;
        Vector2 a = nodes[0], b = nodes[nodes.Count - 1];
        float len = Vector2.Distance(a, b);
        // ⚠ 算出物の座標は小数4桁で丸まっているので**1mm 級の食い違いが出る**(4201 ⇔ 焼いた 4200)。
        //   ⇒ 透塀のスパンと同じく ±2mm まで探し、拾ったらそう名乗る。⛔ 別寸法で代用しない。
        int lenMm = Mathf.RoundToInt(len * 1000f);
        int atMm = Mathf.RoundToInt(F(st, "atM") * 1000f), riseMm = Mathf.RoundToInt(F(st, "riseM") * 1000f);
        int[] cand = new int[] { lenMm, lenMm + 1, lenMm - 1, lenMm + 2, lenMm - 2 };
        string part = null;
        for (int i = 0; i < cand.Length; i++)
        {
            string p = EdoAssets.Own.SannoSodebei(cand[i], atMm, riseMm);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) continue;
            if (i > 0) sb.AppendLine("  ⚠ " + name + ": 長さ " + lenMm + "mm の部材が無いので " + cand[i] +
                                     "mm を据えた ── 差 " + (cand[i] - lenMm) + "mm(算出物の丸め)");
            part = p; break;
        }
        if (part == null)
        { sb.AppendLine("  ★ " + name + ": 袖塀の部材 " + EdoAssets.Own.SannoSodebei(lenMm, atMm, riseMm) + " が無い(部材方へ)"); return 0; }
        // 門側の端 = `runs[].endFrom.end`(門を指す側)。
        var ef = D(dr, "endFrom");
        string gateEnd = ef == null ? null : S(ef, "end");
        if (gateEnd != "a" && gateEnd != "b")
        { sb.AppendLine("  ★ " + name + ": `endFrom.end` が無い — 門側を決められない"); return 0; }
        Vector2 gp = (gateEnd == "a") ? a : b, fp = (gateEnd == "a") ? b : a;
        // 足元 Y0 = 門の敷居(`bom.axis.footAt.gate` / `at`)。⛔ run の座(= 回廊の基壇)ではない。
        var gt = FindByName(Impl, "gates", S(fa, "gate"));
        if (gt == null || S(fa, "at") != "sill")
        { sb.AppendLine("  ★ " + name + ": 門 " + S(fa, "gate") + " の敷居が引けない"); return 0; }
        float y0 = F(gt, "sill");
        Vector2 c = (a + b) * 0.5f;
        EdoBuild.Place(part, new Vector3(c.x, y0, c.y), YawX((fp - gp).normalized), Vector3.one, grp,
                       name + "_000f");
        sb.AppendLine("  ⚠ " + name + ": 門側の木口は**楼門の実メッシュへ寄せていない**(門はこの巡の範囲外)" +
                      " ── 足元 Y0 = " + y0.ToString("F2") + "(" + S(fa, "gate") + " の敷居)");
        return 1;
    }
    /// <summary>設計面(算出物)を優先し、無ければ live terrain。⚠ 造成の後に呼ぶこと。</summary>
    /// <summary>門・柵が触れる床(<see cref="EdoBuild.Bed"/>)── 描かれた地表と、据えた土留め・石段・袖の上面。
    /// ⭐ 突き合わせ・検査も同じ床で測る(⛔ 地形だけで測ると土留めの天端に載る門の隅が嘘の浮きになる)。</summary>
    public static EdoBuild.Bed GateBed()
    {
        var parts = new List<GameObject>();
        foreach (Transform g in Group("Sando")) foreach (Transform c in g) parts.Add(c.gameObject);
        foreach (Transform c in Group("Dodome")) parts.Add(c.gameObject);
        return new EdoBuild.Bed(parts);
    }

    static float SurfaceY(Vector2 p)
    {
        float y;
        if (Gr.Bilinear(p.x, p.y, out y)) return y;
        return EdoBuild.Ground(p.x, p.y);
    }

    // ================================================================ Stage 5 門・鳥居
    [MenuItem(MENU + "5 門・鳥居")]
    public static void Stage5Menu() { Debug.Log("[山王] " + Stage5_MonTorii()); }
    /// <summary>算出物 `gates` の芯・yaw・敷居の高さへ据える。⭐ 部材は **`bom[<gates[].bom>].手当` が
    /// 名指す物**を据える(2026-09-20 に代用をやめた ── 楼門・坂下の門・中門は専用部材が焼けている)。
    /// 部材の規約(`bom[].axis`): ピボット = 門の芯・敷居の高さ。⚠ **正面のローカル軸は部材ごとに違う**
    /// (既存3門 = `+X` / 勝手口の木戸 = `+Z`)⇒ <see cref="EdoBuild.FaceYaw"/> で検算する。
    /// ⇒ `gates[].yaw` のまま・scale one・⛔ **SeatBottom しない**・⛔ **実メッシュの芯で寄せ直さない**
    /// (ピボットが芯なので寄せ直すと基壇の張り出しのぶんだけ門口がずれる)。
    /// ⛔ 向き(`yaw`)が指図に無い門は据えない ── 発明せず差し戻す。⛔ 鳥居は部材が無い(`bom`「無い」)。</summary>
    public static string Stage5_MonTorii()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("Keidai/Mon"); Clear(grp);
        var sb = new StringBuilder();
        int made = 0; var pend = new List<string>();
        EdoBuild.Bed bed = null;
        foreach (var o in L(Impl, "gates"))
        {
            var gt = o as Dictionary<string, object>; if (gt == null) continue;
            string name = S(gt, "name");
            var wp = L(gt, "world"); if (wp.Count < 2) continue;
            Vector2 p = new Vector2(Cv(wp[0]), Cv(wp[1]));
            if (!HasNum(gt, "yaw"))
            { pend.Add(name + "(`gates[].yaw` が null ── 向きが指図に無い)"); continue; }
            float yaw = F(gt, "yaw"), sill = F(gt, "sill");
            string label = S(gt, "bom");
            var bm = label == null ? null : FindBom(label);
            string path = BomPartPath(label);
            if (path == null) { pend.Add(name + "(`bom[" + label + "].手当` に部材のパスが無い)"); continue; }
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { pend.Add(name + "(" + path + " が無い)"); continue; }
            var ax = bm == null ? null : D(bm, "axis");
            string front = ax == null ? null : S(ax, "front");
            if (front == null)
            { pend.Add(name + "(`bom[" + label + "].axis.front` が無い ── 向きの規約が引けない)"); continue; }
            // ⭐ **部材の「正面はローカルのどの軸か」は門ごとに違う**(2026-09-22・EDO-0398)──
            //   既存3門(楼門・中門・坂下の門)は **走り=X・正面=+X**、勝手口の木戸だけ
            //   **走り=X・通り抜け=Z・正面=+Z** で流儀が 90° 違う。⛔ 実装が「+X が正面」と決め打ちしない(規則21)。
            //   焼いた `yaw` は `bake_impl.py::gate_yaw` が **図の `front` − 部材の `axis.front`**(+ 枠の傾き)
            //   で出した従属値 ⇒ ここでは同じ引き算(<see cref="EdoBuild.FaceYaw"/>)で**検算**してから据える。
            //   ⛔ 別の式を作らない・⛔ 食い違ったら据えずに差し戻す(焼き直しが要るということ)。
            float baseYaw;
            if (!EdoBuild.FaceYaw(S(gt, "front"), front, GridDeg, out baseYaw))
            { pend.Add(name + "(向きが解けない: front=" + S(gt, "front") + " / axis.front=" + front + ")"); continue; }
            var gdoc = FindByName(Doc, "gates", name);
            bool framed = gdoc != null && S(gdoc, "frame") != null;   // 郭の辺の傾きを載せた門(楼門)
            if (!framed && Mathf.Abs(Mathf.DeltaAngle(baseYaw, yaw)) > 0.05f)
            { pend.Add(name + "(焼いた yaw " + yaw.ToString("F1") + "° と 部材の軸から出る yaw " +
                       baseYaw.ToString("F1") + "° が食い違う ⇒ `bake_impl.py sanno --write` が要る)"); continue; }
            var go = EdoBuild.Place(path, new Vector3(p.x, sill, p.y), yaw, Vector3.one, grp, GateNameOf(name));
            // ⭐ 敷居(`sill`)は**上限**。床(描かれた地表と土留め・石段の上面の高い方)から浮いていれば触れる所まで下ろす
            //   (硬い条件: 浮き 0・2026-09-25・EDO-0430)。勝手口の木戸は sill 28.30 のまま御供所の郭 27.35 の縁に建ち
            //   0.81〜0.88m 浮いていた。根入れで埋まる門(楼門・中門・坂下の門の基壇)は動かない。
            if (bed == null) bed = GateBed();
            float before; float down = EdoBuild.SettleOnBed(go, bed.At, out before);
            if (down > 0f)
                sb.AppendLine("  ⚠ " + name + ": 敷居 " + sill.ToString("F2") + " では床から " + before.ToString("F2") +
                              "m 浮く ⇒ 触れる所まで下ろした(敷居 " + (sill - down).ToString("F2") + ")── 指図の sill は据わる面と食い違う");
            var bb = EdoBuild.RB(go);
            made++;
            sb.AppendLine("  " + name + " → " + System.IO.Path.GetFileNameWithoutExtension(path) +
                          " 芯 (" + p.x.ToString("F2") + ", " + p.y.ToString("F2") + ") yaw " + yaw.ToString("F1") +
                          "(正面 " + S(gt, "front") + " × axis.front " + front + ")" +
                          " 敷居 " + sill.ToString("F2") + " / 実メッシュ W" + bb.size.x.ToString("F2") +
                          " H" + bb.size.y.ToString("F2") + " D" + bb.size.z.ToString("F2") +
                          " 下端 " + (bb.center.y - bb.extents.y).ToString("F2") +
                          "(敷居との差 " + (bb.center.y - bb.extents.y - sill).ToString("F3") + "m)");
        }
        // ---- 鳥居(2026-09-20 に部材が焼けたので建てる)------------------------
        foreach (var o in L(Doc, "torii"))
        {
            var tr = o as Dictionary<string, object>; if (tr == null) continue;
            string nm = S(tr, "name");
            // ⭐ 座が**棟の実メッシュからの従属値**の鳥居(`posFrom`)は Stage6 の受け持ち
            //   ── その棟が建った後でなければ測れない(2026-09-22・末社の小鳥居)。
            if (G(tr, "posFrom") != null) continue;
            string path = ToriiPart();
            if (path == null) { pend.Add(nm + "(石造明神鳥居の部材が引けない)"); continue; }
            Vector2 pp = P2(G(tr, "pos"));
            Vector2 face;
            if (!ToriiFacing(pp, out face))
            { pend.Add(nm + "(座が道の芯線に載っていない ── ⛔ 向きを発明しない)"); continue; }
            float gy = EdoBuild.Ground(pp.x, pp.y);
            var tg = EdoBuild.Place(path, new Vector3(pp.x, gy, pp.y), YawZ(face), Vector3.one,
                                    grp, ToriiNameOf(nm));
            var tb = EdoBuild.RB(tg);
            made++;
            sb.AppendLine("  " + nm + " → " + ToriiNameOf(nm) + " 芯 (" + pp.x.ToString("F2") + ", " +
                          pp.y.ToString("F2") + ") 地盤 " + gy.ToString("F2") + " yaw " +
                          YawZ(face).ToString("F1") + "(正面 = 道の芯線の境内から遠い側)" +
                          " / 実メッシュ W" + tb.size.x.ToString("F2") + " H" + tb.size.y.ToString("F2") +
                          " 下端 " + (tb.center.y - tb.extents.y).ToString("F2"));
        }
        if (pend.Count > 0)
            sb.AppendLine("  ★ 部材が無いので建てなかった(bom「無い/新造」優先2): " + string.Join(" / ", pend.ToArray()));
        return "門・鳥居: " + made + " 基\n" + sb;
    }

    /// <summary>石造明神鳥居の部材。⭐ まず `bom[鳥居].手当` を見る(正典は指図)。
    /// ⚠ **2026-09-20 時点で bom の行が「新造依頼」のまま**でパスを名指していないので、
    /// そのときだけ `Models/Sanno` に焼けている `Sanno_Torii_*.fbx` を引く(**1点だけのとき**)。
    /// ⛔ 綴りに寸法を書かない・⛔ 2点以上あったらどれか選ばない(差し戻す)。</summary>
    static string ToriiPart()
    {
        string fromBom = BomPartPath("鳥居");
        if (fromBom != null && AssetDatabase.LoadAssetAtPath<GameObject>(fromBom) != null) return fromBom;
        // ⭐ **別の行が名指している部材は候補から外す**(2026-09-22)── 末社の小鳥居の
        //   `torii[].partFrom` が `Sanno_Torii_Massha_*` を名指すので、綴りだけで拾うと 2 点になり
        //   「どれか選ばない」で一ノ・二ノ鳥居まで建たなくなる。⛔ 綴りで除外しない(**名指し**で除外する)。
        var named = new List<string>();
        foreach (var o in L(Doc, "torii"))
        {
            var t = o as Dictionary<string, object>; if (t == null) continue;
            string pf = S(t, "partFrom"); if (string.IsNullOrEmpty(pf)) continue;
            string np = PartFromPath(pf); if (np != null) named.Add(np);
        }
        string found = null;
        foreach (var guid in AssetDatabase.FindAssets("Sanno_Torii t:Model", new[] { "Assets/Edo/Models/Sanno" }))
        {
            string p = AssetDatabase.GUIDToAssetPath(guid);
            if (!System.IO.Path.GetFileName(p).StartsWith("Sanno_Torii_")) continue;
            if (named.Contains(p)) continue;     // 別の行の受け持ち(末社の小鳥居)
            if (found != null) return null;      // ⛔ 2点あったら選ばない
            found = p;
        }
        return found;
    }
    /// <summary>道の芯線(算出物 `routes[].world` と指図 `fumotomichi[].pts`)を集める。</summary>
    static List<List<Vector2>> Michi()
    {
        var r = new List<List<Vector2>>();
        foreach (var o in L(Impl, "routes"))
        { var d = o as Dictionary<string, object>; if (d != null) r.Add(Pts(L(d, "world"))); }
        foreach (var o in L(Doc, "fumotomichi"))
        { var d = o as Dictionary<string, object>; if (d != null) r.Add(Pts(L(d, "pts"))); }
        return r;
    }
    /// <summary>鳥居の正面(部材の +Z)の向き。⭐ **指図は鳥居の yaw を書かない**(座だけ)ので、
    /// **鳥居が載っている道の芯線の接線**から引く ── 正面は**境内から遠い側**(参詣者が来る方)。
    /// ⛔ 角度を実装が持たない。座が道の芯線から 1.0m 以上離れていたら false を返して差し戻す。</summary>
    static bool ToriiFacing(Vector2 p, out Vector2 face)
    {
        face = Vector2.right;
        float best = float.MaxValue; Vector2 tan = Vector2.right;
        foreach (var poly in Michi())
            for (int i = 1; i < poly.Count; i++)
            {
                Vector2 a = poly[i - 1], b = poly[i];
                Vector2 d = b - a; float l2 = d.sqrMagnitude; if (l2 < 1e-6f) continue;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, d) / l2);
                float dd = Vector2.Distance(p, a + d * t);
                if (dd < best) { best = dd; tan = d / Mathf.Sqrt(l2); }
            }
        if (best > 1.0f) return false;
        Vector2 keidai = W(0f, 0f);                       // 境内グリッドの原点(算出物 `grid`)
        if (Vector2.Dot(tan, p - keidai) < 0f) tan = -tan;
        face = tan; return true;
    }
    /// <summary>鳥居の名 → シーンの名(⛔ 部材のパスではない)。</summary>
    /// <summary>⭐ 突き合わせも同じ物差しで引く ⇒ public。</summary>
    public static string ToriiNameOf(string designName)
    {
        if (designName == null) return "Torii";
        if (designName.StartsWith("一ノ")) return "IchinoTorii";
        if (designName.StartsWith("二ノ")) return "NinoTorii";
        return designName;
    }

    // ================================================================ Stage 6 社殿
    [MenuItem(MENU + "6 社殿5棟+木階")]
    public static void Stage6Menu() { Debug.Log("[山王] " + Stage6_Shaden()); }
    /// <summary>社殿。⭐ 部材の**ピボット = その棟の区画 (u0,v0,du,dv) の中心・地盤レベル**。
    /// ⇒ `munes` の矩形の中心へ **scale one** のまま置く。
    /// ⛔ SeatBottom で据えない(部材が地盤レベルを原点に持っている)。
    ///
    /// <para>⭐ **向きは二つの宣言の引き算**(2026-09-22・EDO-0261 ③): 図の `munes[].front`(東/西/南/北)と
    /// 部材の `axis.front`(ローカルのどの軸が正面か)から <see cref="EdoBuild.FaceYaw"/> が出す。
    /// ⛔ **「この社は +X が正面」と実装が決め打ちしない** ── 社殿5棟の部材は +X が正面、2026-09-22 に
    /// 焼けた堂宇10棟は **+Z が正面**で、揃えて yaw 0 で据えると後の10棟だけ 90° 北を向く。
    /// ⚠ どちらかの宣言が欠けている棟は **yaw 0 のまま据えて「向きが宣言されていない」と刷る**
    /// (= これまでの5棟と同じ挙動。⛔ 0 を「合格」と読ませない ── 突き合わせに立てる)。</para></summary>
    public static string Stage6_Shaden()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("Keidai/Shaden"); Clear(grp);
        var sb = new StringBuilder();
        int made = 0; var pend = new List<string>(); var muki = new List<string>();
        foreach (var o in L(Doc, "munes"))
        {
            var m = o as Dictionary<string, object>; if (m == null) continue;
            string name = S(m, "name");
            string part = S(m, "partFrom");
            string label = BomLabelFor(name);
            // ⭐ `partFrom` を持たない棟は **`bom` の行が名指す部材**を据える(2026-09-20 ── 御供所)。
            //   ⛔ 綴りを実装が持たない: 行は「棟の名」か「棟の名(…)」で引く。
            string path = string.IsNullOrEmpty(part) ? BomPartPath(label) : PartFromPath(part);
            if (path == null)
            { pend.Add(name + (string.IsNullOrEmpty(part) ? "" : "(`partFrom`『" + part + "』を解けない)")); continue; }
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { pend.Add(name + "(" + path + " が無い)"); continue; }
            float yaw; string how;
            if (!Muki(m, label, name, path, out yaw, out how)) { pend.Add(how); continue; }
            if (how != null) muki.Add(how);
            Vector2 c = W(F(m, "u0") + F(m, "du") * 0.5f, F(m, "v0") + F(m, "dv") * 0.5f);
            float y;
            if (!Gr.Near(c.x, c.y, 3, out y)) y = EdoBuild.Ground(c.x, c.y);
            EdoBuild.Place(path, new Vector3(c.x, y, c.y), yaw, Vector3.one, grp, ShadenNameOf(name));
            made++;
            sb.AppendLine("  " + name + " → " + ShadenNameOf(name) + " (" + c.x.ToString("F2") + ", " +
                          c.y.ToString("F2") + ") 地盤 " + y.ToString("F2") + " yaw " + yaw.ToString("F1") +
                          (how == null ? "(正面 " + S(m, "front") + ")" : "(⚠ 向きが未宣言)"));
        }
        // 木階(向拝の階)— `kaidans` の a〜b の中点・地盤レベル。⛔ 石段にしない。
        foreach (var o in L(Doc, "kaidans"))
        {
            var k = o as Dictionary<string, object>; if (k == null) continue;
            if (G(k, "kizahashi") == null) continue;
            if (!S(k, "name").StartsWith("向拝")) continue;    // 本殿の木階は本殿の部材に入っている
            Vector2 a = P2(G(k, "a")), b = P2(G(k, "b"));
            Vector2 c = W((a.x + b.x) * 0.5f, a.y);
            // ⭐ 部材の綴りは `kaidans` の 幅(wKen)・出(a〜b)・丈(yTop−yBot)からの**従属値**。
            //   ⛔ "Sanno_Kizahashi_3ken" のような名を書かない(旧部材を拾って寸法が化ける)。
            float ken = F(D(Impl, "grid"), "ken");
            int wMm = Mathf.RoundToInt(F(k, "wKen") * ken * 1000f);
            int runMm = Mathf.RoundToInt(Mathf.Abs(b.x - a.x) * ken * 1000f);
            int riseMm = Mathf.RoundToInt((F(k, "yTop") - F(k, "yBot")) * 1000f);
            string path = EdoAssets.Own.SannoKizahashi(wMm, runMm, riseMm);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { pend.Add(S(k, "name") + "(" + path + " が無い)"); continue; }
            EdoBuild.Place(path, new Vector3(c.x, F(k, "yBot"), c.y), GridDeg, Vector3.one, grp, "Kizahashi");   // ⭐ 階は境内の軸に沿う(枠の回り)
            made++;
            sb.AppendLine("  " + S(k, "name") + " → Kizahashi (" + c.x.ToString("F2") + ", " + c.y.ToString("F2") +
                          ") 地盤 " + F(k, "yBot").ToString("F2"));
        }
        made += ToriiFromMune(grp, sb, pend);
        if (pend.Count > 0)
            sb.AppendLine("  ★ 建てなかった(部材が無い/宣言が足りない): " + string.Join(" / ", pend.ToArray()));
        if (muki.Count > 0)
            sb.AppendLine("  ⚠ **向きが宣言されていない** " + muki.Count + " 件 ── 境内の軸に沿う既定の姿(yaw = 枠の回り)で据えた"
                          + "(⛔ 合格ではない ── 指図に `munes[].front` と部材の `axis.front` が要る): "
                          + string.Join(" / ", muki.ToArray()));
        return "社殿: " + made + " 棟\n" + sb;
    }

    /// <summary>棟・鳥居の `partFrom` を**部材のパス**へ解く。⭐ `EdoAssets.Own.…` の呼び名は
    /// <see cref="EdoAssets.OwnPath"/> が解く(⛔ 実装がフォルダを決め打ちしない ── 鐘楼・鼓楼は
    /// `Models/Jisha/` に在って `Models/Sanno/` ではない)。⚠ 呼び名でない `partFrom` は**旧い書式**の
    /// 部材の stem(`Models/Sanno/<stem>.fbx`)── 社殿5棟がこれ。</summary>
    static string PartFromPath(string partFrom)
    {
        if (string.IsNullOrEmpty(partFrom)) return null;
        if (partFrom.IndexOf("Own.", StringComparison.Ordinal) >= 0) return EdoAssets.OwnPath(partFrom);
        return P.Shaden(partFrom);
    }

    /// <summary>**部材の「正面はローカルのどの軸か」の宣言**を引く。
    /// ① その行自身の `axis.front`(棟・鳥居ごと)→ ② `bom[<label>].axis.front`(門が使っている綴り)。
    /// ⛔ 無ければ null を返す ── **実装が「+X が正面」と決め打ちしない**。</summary>
    static string FrontAxisOf(Dictionary<string, object> row, string label, string name = null, string path = null)
    {
        // ⭐ 引き方は EdoBuild の一つ(`bom[].parts[<棟>].axis.front` も読む ── 社殿5棟はこの書式)
        return EdoBuild.BomFrontAxis(L(Doc, "bom"), row, label, name, path);
    }

    /// <summary>棟・鳥居の **yaw** を、図の `front`(方位)と部材の `axis.front`(ローカル軸)から出す。
    /// 返り false = 宣言はあるのに解けない(⇒ 据えない・<paramref name="why"/> が理由)。
    /// 返り true で <paramref name="why"/> が非 null = **向きが宣言されていない**(⇒ yaw 0 で据えて刷る)。
    /// ⛔ 向きを発明しない(規則5・EDO-0261 ③)。</summary>
    static bool Muki(Dictionary<string, object> row, string label, string name, out float yaw, out string why)
    { return Muki(row, label, name, null, out yaw, out why); }
    static bool Muki(Dictionary<string, object> row, string label, string name, string path, out float yaw, out string why)
    {
        // ⭐ 向きが未宣言のときの既定の姿は「**枠の軸に沿う**」(= 回る前の yaw 0 と同じ姿)。
        //   ⛔ 世界の yaw 0 にしない ── 境内の軸が回ったので、世界の 0 は枠から 5.5° ずれた発明になる。
        yaw = GridDeg; why = null;
        string front = S(row, "front");
        string axf = FrontAxisOf(row, label, name, path);
        if (front == null || axf == null)
        {
            why = name + "(" + (front == null ? "図に `front`(正面の方位)が無い"
                                              : "部材の `axis.front`(正面のローカル軸)が無い") + ")";
            return true;
        }
        if (!EdoBuild.FaceYaw(front, axf, GridDeg, out yaw))
        { why = name + "(向きが解けない: front=" + front + " / axis.front=" + axf + ")"; return false; }
        return true;
    }

    /// <summary>**棟に寄る鳥居**(`torii[].posFrom`)を据える。現物は末社(稲荷社)の前の小鳥居。
    ///
    /// <para>⭐ **Stage5(門・鳥居)ではなく此処**で据えるのが要 ── 座が**寄る棟の実メッシュからの
    /// 従属値**なので、その棟が建った後でなければ測れない(置き方の4手: 固定側=棟を先に置く →
    /// 可動側=鳥居を実際に触れる所まで寄せる)。群も社殿と同じ(棟を消す巡では一緒に消えるのが正しい)。</para>
    ///
    /// <para>⛔ **離れを発明しない。**図は「稲荷社の正面の前」という関係だけを宣言していて、
    /// 出(離れ)は未決【?】(`sanno_notes/torii.json`)。⇒ `posFrom.clearanceM`
    /// (棟の正面の実面 → 鳥居の実メッシュの隙[m])が宣言されるまで据えない。
    /// ⛔ 棟の向きも同じ ── `munes[].front` が無ければ「前」がどちらか決まらない。</para></summary>
    static int ToriiFromMune(Transform grp, StringBuilder sb, List<string> pend)
    {
        int made = 0;
        foreach (var o in L(Doc, "torii"))
        {
            var tr = o as Dictionary<string, object>; if (tr == null) continue;
            var pf = D(tr, "posFrom"); if (pf == null) continue;      // 座を持つ鳥居は Stage5 の受け持ち
            string nm = S(tr, "name");
            string path = PartFromPath(S(tr, "partFrom"));
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { pend.Add(nm + "(`torii[].partFrom`『" + S(tr, "partFrom") + "』の部材が引けない)"); continue; }
            string mn = S(pf, "mune");
            var mm = FindByName(Doc, "munes", mn);
            var host = grp == null || mn == null ? null : grp.Find(ShadenNameOf(mn));
            if (mm == null || host == null)
            { pend.Add(nm + "(寄る棟『" + mn + "』が建っていない ⇒ 実メッシュを測れない)"); continue; }
            // ---- ① 寄る棟の正面の向き(= 「前」がどちらか)
            string front = S(mm, "front");
            Vector2 dir;
            if (!EdoBuild.DirVec(front, GridDeg, out dir))
            { pend.Add(nm + "(寄る棟『" + mn + "』の `front` が無い ⇒ 『前』が決まらない ── ⛔ 向きを発明しない)"); continue; }
            // ---- ② 鳥居自身の向き ── ⭐ **図は鳥居の `front` を書かない**(「向き=稲荷社に従属」と
            //   宣言してある)⇒ **寄る棟の `front`** と鳥居の部材の `axis.front` から引く。
            //   正面は棟と同じ方位(= 参詣者に正対)。⛔ 方位を実装が決め打ちしない。
            string tax = FrontAxisOf(tr, null);
            if (tax == null)
            { pend.Add(nm + "(部材の `axis.front`(正面のローカル軸)が図に無い)"); continue; }
            float yaw;
            if (!EdoBuild.FaceYaw(front, tax, GridDeg, out yaw))
            { pend.Add(nm + "(向きが解けない: 寄る棟の front=" + front + " / axis.front=" + tax + ")"); continue; }
            // ---- ③ 離れ(⛔ 発明しない)
            if (!HasNum(pf, "clearanceM"))
            { pend.Add(nm + "(`torii[].posFrom.clearanceM`(棟の正面の面からの離れ[m])が図に無い)"); continue; }
            float clr = F(pf, "clearanceM");
            // ---- ④ 据える: 前方の余地へ置いてから、棟の実メッシュへ**触れている箇所**で寄せる
            Vector3 hp = host.position;
            var go = EdoBuild.Place(path, new Vector3(hp.x + dir.x * (clr + 12f), hp.y,
                                                      hp.z + dir.y * (clr + 12f)),
                                    yaw, Vector3.one, grp, ToriiNameOf(nm));
            Vector3 at; int cnt;
            float mv = EdoBuild.Abut(go, host.gameObject, new Vector3(-dir.x, 0f, -dir.y), clr, out at, out cnt);
            if (float.IsNaN(mv))
            { UnityEngine.Object.DestroyImmediate(go); pend.Add(nm + "(棟『" + mn + "』と向き合っていない ⇒ 寄せられない)"); continue; }
            Vector3 p = go.transform.position;
            p.y = EdoBuild.Ground(p.x, p.z);           // ピボット = 柱芯の中央・地盤(⛔ SeatBottom しない)
            go.transform.position = p;
            made++;
            sb.AppendLine("  " + nm + " → " + ToriiNameOf(nm) + " (" + p.x.ToString("F2") + ", " +
                          p.z.ToString("F2") + ") 地盤 " + p.y.ToString("F2") + " yaw " + yaw.ToString("F1") +
                          " / 『" + mn + "』の正面(" + front + ")の面から 隙 " + clr.ToString("F2") +
                          "m・当たり " + cnt + " 筋");
        }
        return made;
    }
    /// <summary>棟の名 → `bom` の行の名。⭐ 行は「棟の名」そのものか「棟の名(役)」で立っている
    /// (例 `御供所` → `御供所(供の棟)`)。⛔ 部材のパスを実装が持たない。</summary>
    static string BomLabelFor(string mune)
    {
        if (mune == null) return null;
        foreach (var o in L(Doc, "bom"))
        {
            var b = o as Dictionary<string, object>; if (b == null) continue;
            string lbl = S(b, "部材"); if (lbl == null) continue;
            if (lbl == mune || lbl.StartsWith(mune + "(")) return lbl;
        }
        return null;
    }
    /// <summary>棟の名 → シーンの名。⭐ **突き合わせ(`EdoSannoShaCheck`)も同じ物差しを使う**
    /// ⇒ public(⛔ 検査が別の名簿を持たない・規則19)。</summary>
    public static string ShadenNameOf(string designName)
    {
        if (designName.StartsWith("御供所")) return "Gokusho";
        if (designName.StartsWith("本殿")) return "Honden";
        if (designName.StartsWith("作り合い")) return "Tsukuriai";
        if (designName.StartsWith("幣殿")) return "Heiden";
        if (designName.StartsWith("拝殿")) return "Haiden";
        if (designName.StartsWith("向拝")) return "Kohai";
        return designName;
    }

    // ================================================================ Stage 7 社叢
    /// <summary>旧 `EdoSannoShaBuilder.Stage7_Keidairin` が**直書きで撒いた木**(竹を含む)を退避する。
    /// ⛔ 削除しない ── `Kyu_Shaso` の下へ移して非活性にする。⭐ **群ごと移す**のが要で、
    /// `Keidairin` のまま非活性にしても突き合わせは中身を数える(active を見ない)。</summary>
    public const string GROUP_OLD_SHASO = "Kyu_Shaso";
    static string RetireKeidairin()
    {
        var root = GameObject.Find(GROUP);
        if (root == null) return "  退避: ルートが無い\n";
        EdoYashikiPrefab.EnsureEditable(root);
        var old = root.transform.Find("Keidairin");
        if (old == null) return "  退避: Keidairin は無い(既に退避済み)\n";
        var kyu = root.transform.Find(GROUP_OLD_SHASO);
        if (kyu == null)
        {
            var g = new GameObject(GROUP_OLD_SHASO); Undo.RegisterCreatedObjectUndo(g, "kyu");
            g.transform.SetParent(root.transform, false); kyu = g.transform;
        }
        int n = old.childCount, bam = 0;
        for (int i = 0; i < old.childCount; i++) if (old.GetChild(i).name.StartsWith("Bam_")) bam++;
        old.SetParent(kyu, true);
        old.gameObject.SetActive(false);
        kyu.gameObject.SetActive(false);
        return "  退避: Keidairin の木 " + n + " 本(うち竹 " + bam + " 本)を " + GROUP_OLD_SHASO +
               " へ移して非活性(⛔ 削除していない)\n";
    }

    [MenuItem(MENU + "7 社叢(算出物の点をそのまま置く)")]
    public static void Stage7Menu() { Debug.Log("[山王] " + Stage7_Shaso()); }
    /// <summary>社叢。⛔ **撒き直さない・乱数を振らない** ── 算出物 `planting.points` の 1点 1本を
    /// そのまま置くだけ。⭐ 入れ物は点の `place` が決める:
    ///   ・`TerrainTree` … 地形の tree instance(GameObject では**ない**)
    ///   ・`DetailMesh`  … ⚠ Unity の詳細メッシュは**密度の升目**で、点の座標を持てない
    ///     ⇒ 焼き出しの点をそのまま活かすため**地形の tree instance** で植える(施主 2026-09-23・EDO-0401)。
    ///     地表への据えは地形に任せる。⛔ 崖の斜面に低木の葉が掛かるのは欠陥と数えない(同じ施主裁定)。
    ///     (旧: GameObject で据え、崖で山側が埋まった → SeatPlant でも 850 本を1本ずつ測る重さが残った)
    ///   ・`GameObject`  … 名指しの木(群 `Keidai/Meiboku` ── 突き合わせは名で引く)
    /// ⭐ 丈は `scaleY` / 太りは `scaleXZ` をそのまま使う。地盤は **地形を実測**して据え、
    /// 焼き出しの `y` との差は数えて報告する(⛔ 浮き・埋没を作らない)。
    /// ⛔ **向き(yaw)は焼き出しに無い**ので 0 のまま ── 乱数を振らない(振るなら指図方の持ち分)。</summary>
    public static string Stage7_Shaso()
    {
        var gate = Gate(); if (gate != null) return gate;
        var sb = new StringBuilder();
        sb.Append(RetireKeidairin());
        var pts = L(D(Impl, "planting"), "points");
        if (pts.Count == 0) return "社叢: 算出物に points が無い\n" + sb;

        var trees = Group("Keidai/Trees"); Clear(trees);
        var meiboku = Group("Keidai/Meiboku"); Clear(meiboku);

        var ter = EdoBuild.T(); var td = ter.terrainData; Vector3 tp = ter.transform.position, ts = td.size;
        // 樹種の原型(prototype)を要るだけ足す。⛔ 既にある原型を作り直さない。
        var protos = new List<TreePrototype>(td.treePrototypes);
        var idxOf = new Dictionary<string, int>();
        for (int i = 0; i < protos.Count; i++)
        {
            string ap = protos[i].prefab == null ? null : AssetDatabase.GetAssetPath(protos[i].prefab);
            if (ap != null && !idxOf.ContainsKey(ap)) idxOf[ap] = i;
        }
        int addedProto = 0;
        var missing = new List<string>();
        float bx0 = float.MaxValue, bx1 = float.MinValue, bz0 = float.MaxValue, bz1 = float.MinValue;
        foreach (var o in pts)
        {
            var q = o as Dictionary<string, object>; if (q == null) continue;
            var w = L(q, "world"); if (w.Count < 2) continue;
            float wx = Cv(w[0]), wz = Cv(w[1]);
            bx0 = Mathf.Min(bx0, wx); bx1 = Mathf.Max(bx1, wx);
            bz0 = Mathf.Min(bz0, wz); bz1 = Mathf.Max(bz1, wz);
            if (S(q, "place") == "GameObject") continue;       // 地形の木と下層(DetailMesh)は地形の tree instance
            string path = TreePath(q); if (path == null) continue;
            if (idxOf.ContainsKey(path)) continue;
            var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (pf == null) { if (!missing.Contains(path)) missing.Add(path); continue; }
            var np = new TreePrototype(); np.prefab = pf; np.bendFactor = 0f;
            idxOf[path] = protos.Count; protos.Add(np); addedProto++;
        }
        // ⛔ **描けない原型に植えない**(EDO-0401・2026-09-23 実測)── 根に Renderer も LODGroup も無い原型は
        //    地形が黙って描かない(社叢 1,030 本が一本も写っていなかった・コンソールは無言)。〔硬い制約〕
        {
            var bad = new List<string>(); var seen = new HashSet<string>();
            foreach (var o in pts)                      // 社叢の点が使う原型だけ(⛔ 他の敷地の原型で止めない)
            {
                var q = o as Dictionary<string, object>;
                if (q == null || S(q, "place") == "GameObject") continue;
                string path = TreePath(q);
                if (path == null || !idxOf.ContainsKey(path) || !seen.Add(path)) continue;
                // 地形が木として描けるのは、原型の**根**に LODGroup か MeshFilter+MeshRenderer が在るときだけ
                var pf = protos[idxOf[path]].prefab;
                bool ok = pf != null && (pf.GetComponent<LODGroup>() != null ||
                          (pf.GetComponent<MeshFilter>() != null && pf.GetComponent<MeshRenderer>() != null));
                if (!ok) bad.Add(path + "(根に LODGroup も MeshRenderer も無い)");
            }
            if (bad.Count > 0)
                return "社叢: ⛔ 植えない ── 地形の木として描けない原型 " + bad.Count + " 種: " +
                       string.Join(" / ", bad.ToArray()) + "\n" + sb;
        }
        if (addedProto > 0) td.treePrototypes = protos.ToArray();

        // 焼き出しの外接矩形の内に在る**自分の原型の**木を外す(⛔ 他の敷地の木を消さない)。
        var mine = new HashSet<int>(); foreach (var kv in idxOf) if (kv.Key.StartsWith("Assets/Edo/Models/Trees/")) mine.Add(kv.Value);
        var keep = new List<TreeInstance>(); int removed = 0;
        var prec = EdoParcels.Get("sannosha_prec");
        foreach (var ti in td.treeInstances)
        {
            float wx = tp.x + ti.position.x * ts.x, wz = tp.z + ti.position.z * ts.z;
            // ⚠ 辺の上の点は正規化座標の往復で外へ落ちる(流し直すたびに 11 本が積み重なった・EDO-0401)⇒ 5cm の余白
            const float eps = 0.05f;
            bool inBox = wx >= bx0 - eps && wx <= bx1 + eps && wz >= bz0 - eps && wz <= bz1 + eps;
            // ⚠ 焼き直しで点の外接矩形が縮むと、前の植え付けの木が矩形の外に取り残される(柵の外に3本・EDO-0401 実測)
            //    ⇒ **社地(区画 sannosha_prec)の内**も外す。⛔ 他の敷地の木は区画の外なので触れない。
            bool inPrec = prec != null && EdoGeom.PIP(prec, new Vector2(wx, wz));
            if ((inBox || inPrec) && mine.Contains(ti.prototypeIndex)) { removed++; continue; }
            keep.Add(ti);
        }

        int nTree = 0, nGo = 0, nMei = 0, skipped = 0;
        float dyMax = 0f; double dySum = 0; int dyN = 0;
        var unseated = new List<string>(); float buryMax = 0f, floatMax = 0f;
        foreach (var o in pts)
        {
            var q = o as Dictionary<string, object>; if (q == null) continue;
            var w = L(q, "world"); if (w.Count < 2) { skipped++; continue; }
            float wx = Cv(w[0]), wz = Cv(w[1]);
            string path = TreePath(q);
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { skipped++; if (path != null && !missing.Contains(path)) missing.Add(path); continue; }
            float sy = HasNum(q, "scaleY") ? F(q, "scaleY") : 1f; if (sy <= 0f) sy = 1f;
            float sxz = HasNum(q, "scaleXZ") ? F(q, "scaleXZ") : 1f; if (sxz <= 0f) sxz = 1f;
            float gy = EdoBuild.Ground(wx, wz);
            if (HasNum(q, "y")) { float d = Mathf.Abs(gy - F(q, "y")); dyMax = Mathf.Max(dyMax, d); dySum += d; dyN++; }
            string place = S(q, "place");
            if (place != "GameObject")
            {
                var ti = new TreeInstance();
                // ⭐ 点に来るのは**幹の足の中心**(⛔ ピボットではない・規則21・EDO-0409)
                ti.rotation = 0f;
                var piv = EdoBuild.TreePivotForTrunk(new Vector2(wx, wz), EdoBuild.TrunkFootLocal(path), sxz, ti.rotation);
                ti.position = new Vector3((piv.x - tp.x) / ts.x, 0f, (piv.y - tp.z) / ts.z);
                ti.prototypeIndex = idxOf[path];
                ti.widthScale = sxz; ti.heightScale = sy;
                ti.color = Color.white; ti.lightmapColor = Color.white;
                keep.Add(ti); nTree++;
            }
            else
            {
                bool named = place == "GameObject";
                var g = EdoBuild.Place(path, new Vector3(wx, gy, wz), 0f, new Vector3(sxz, sy, sxz),
                                       named ? meiboku : trees, S(q, "name"));
                // ⭐ 傾ける木は `leanDeg`(範囲)と `leanToward`(向き)を持つ ── 範囲の**中**を採る。
                if (g != null && G(q, "leanDeg") != null)
                {
                    var ld = G(q, "leanDeg") as List<object>;
                    float deg = ld == null ? 0f : (ld.Count >= 2 ? (Cv(ld[0]) + Cv(ld[1])) * 0.5f : Cv(ld[0]));
                    Vector2 to = P2(G(q, "leanToward"));
                    if (deg != 0f && to.sqrMagnitude > 1e-6f)
                    {
                        to = to.normalized;
                        g.transform.rotation = Quaternion.AngleAxis(deg, new Vector3(to.y, 0f, -to.x));
                    }
                }
                // ⭐ **足元の当たりで据える**(EDO-0401)── ⛔ ピボットを点の地表へ置いたままにしない
                //    (崖の低木の山側が 1.0〜1.8m 潜っていた)。据わらない木は数えて名指しで刷る。
                if (g != null)
                {
                    float bu, fl;
                    if (!EdoBuild.SeatPlantAt(g, new Vector2(wx, wz), 0f, out bu, out fl))   // 幹の足を点へ(EDO-0409)
                        unseated.Add(string.Format("{0}(埋 {1:F2} / 浮 {2:F2})", g.name, bu, fl));
                    buryMax = Mathf.Max(buryMax, float.IsNaN(bu) ? 0f : bu);
                    floatMax = Mathf.Max(floatMax, float.IsNaN(fl) ? 0f : fl);
                }
                if (named) nMei++; else nGo++;
            }
        }
        td.SetTreeInstances(keep.ToArray(), true);
        EditorUtility.SetDirty(td);

        sb.AppendLine("  地形の木 " + nTree + " 本(外した " + removed + " 本 / 原型を " + addedProto + " 足した)");
        sb.AppendLine("  (下層の低木も地形の木に含む ── 焼き出しの `place` は `DetailMesh` だが、詳細メッシュは" +
                      "密度の升目で**点の座標を持てない**ので地形の tree instance で植えた)");
        if (nGo > 0) sb.AppendLine("  ★ 下層を GameObject で据えた木 " + nGo + " 本(0 のはず)");
        sb.AppendLine("  名指しの木(群 Keidai/Meiboku) " + nMei + " 本");
        if (dyN > 0)
            sb.AppendLine("  地盤: 実測と焼き出しの `y` の差 平均 " + (dySum / dyN).ToString("F3") +
                          "m / 最大 " + dyMax.ToString("F3") + "m(据えたのは**実測**の地盤)");
        sb.AppendLine("  据え(GameObject の木 " + (nGo + nMei) + " 本・足元の当たりで): 埋没 最大 " + buryMax.ToString("F2") +
                      "m / 浮き 最大 " + floatMax.ToString("F2") + "m");
        if (unseated.Count > 0)
            sb.AppendLine("  ★ 埋没≤1.0・浮き≤0.7 で据わらない木 " + unseated.Count + " 本: " +
                          string.Join(" / ", unseated.GetRange(0, Mathf.Min(20, unseated.Count)).ToArray()));
        if (skipped > 0) sb.AppendLine("  ★ 据えられなかった点 " + skipped + " 点");
        if (missing.Count > 0) sb.AppendLine("  ★ 部材が無い: " + string.Join(" / ", missing.ToArray()));
        sb.AppendLine("  ⛔ 向き(yaw)は焼き出しに無いので 0 のまま ── 乱数を振っていない");
        return "社叢: " + (nTree + nGo + nMei) + " 本 / " + pts.Count + " 点\n" + sb;
    }
    /// <summary>点の `part`(例 `Own.Matsu("Mid", 3)`)を部材のパスへ解く。
    /// ⛔ 綴りを実装が持たない ── `EdoAssets.Own` の関数へ渡すだけ。解けない族は null。</summary>
    static string TreePath(Dictionary<string, object> q)
    {
        string api = S(q, "part"); if (api == null) return null;
        int lp = api.IndexOf('('), rp = api.LastIndexOf(')');
        if (lp < 0 || rp < lp) return null;
        string fn = api.Substring(0, lp);
        if (fn.StartsWith("Own.")) fn = fn.Substring(4);
        var args = api.Substring(lp + 1, rp - lp - 1).Split(',');
        // ⭐ 丈は**点の `size` の欄**が正典(`part` の第1引数は `"{size}"` の差し込みのままの点がある)。
        string size = S(q, "size");
        if (string.IsNullOrEmpty(size)) size = args[0].Trim().Trim('"');
        int i = 1;
        if (args.Length > 1) int.TryParse(args[1].Trim(), out i);
        if (i < 1) i = 1;
        // ⚠ **焼き出しの綻び**(2026-09-20 実測): 一本立ちの 7 点は `part` が `"{size}"` の差し込みのまま
        //   で `size` の欄も空。⇒ **同じ点の `prefab` の欄**(`Tree_<族>_<丈>[_NN]`)から丈と個体を読む。
        //   ⛔ 丈を発明しない・⛔ パスの綴りをここに書かない(解いた丈を `EdoAssets.Own` へ渡すだけ)。
        if (string.IsNullOrEmpty(size) || size.IndexOf('{') >= 0)
        {
            string pre = S(q, "prefab");
            var seg = pre == null ? null : pre.Split('_');
            if (seg != null && seg.Length >= 3)
            {
                size = seg[2];
                if (seg.Length >= 4) int.TryParse(seg[3], out i);
                if (i < 1) i = 1;
            }
        }
        if (string.IsNullOrEmpty(size) || size.IndexOf('{') >= 0) return null;
        if (fn == "Matsu") return EdoAssets.Own.Matsu(size, i);
        if (fn == "Jouryoku") return EdoAssets.Own.Jouryoku(size, i);
        if (fn == "Teiboku") return EdoAssets.Own.Teiboku(size, i);
        if (fn == "Keyaki") return EdoAssets.Own.Keyaki(size, i);
        if (fn == "Enoki") return EdoAssets.Own.Enoki(size, i);
        if (fn == "Mukunoki") return EdoAssets.Own.Mukunoki(size, i);
        return null;
    }

    static Dictionary<string, object> FindByName(Dictionary<string, object> src, string key, string name)
    {
        foreach (var o in L(src, key))
        { var m = o as Dictionary<string, object>; if (m != null && S(m, "name") == name) return m; }
        return null;
    }

    // ================================================================ Stage 8 前庭の井戸
    [MenuItem(MENU + "8 前庭の井戸(板石敷・井筒+井桁・井戸屋形)")]
    public static void Stage8Menu() { Debug.Log("[山王] " + Stage8_Ido()); }

    /// <summary>境内グリッド (u,v)[間] → 世界。**指図の `grid.keidai` と `const.ken`** から引く。
    /// ⭐ <see cref="W"/> と同じ式・同じ値(算出物の `grid` は指図の `grid.keidai` を写した物)。
    /// 井戸の段は造成面も算出物の欄も使わない(高さは実地表と実メッシュで測る)ので、算出物の指紋の照合
    /// (<see cref="VerifyImplFingerprint"/>)に掛けない ── 別の欄(munes)を直している最中でも井戸は建て直せる。</summary>
    static Vector2 WKeidai(float u, float v)
    {
        var g = D(D(Doc, "grid"), "keidai");
        float ken = F(D(Doc, "const"), "ken");
        return new Vector2(F(g, "x0") + (u * F(g, "ux") + v * F(g, "vx")) * ken,
                           F(g, "z0") + (u * F(g, "uz") + v * F(g, "vz")) * ken);
    }

    /// <summary>**境内グリッドの回り[°・上から見て時計回り]**(2026-09-23 施主裁定 5.5°)。図の方位の語
    /// (`front` = 東/西/南/北)は**この枠の軸**で書かれているので、向きを出すときは必ずこれを足す
    /// (<see cref="EdoBuild.FaceYaw(string,string,float,out float)"/>)。⭐ 基底 `grid.keidai` の u 軸から出す
    /// ── 焼き手 `impl_sanno.py::grid_deg` と同じ式。⛔ 角を数で持たない。</summary>
    public static float GridDeg
    {
        get
        {
            var g = D(D(Doc, "grid"), "keidai");
            return Mathf.Atan2(-F(g, "uz"), F(g, "ux")) * Mathf.Rad2Deg;
        }
    }

    /// <summary>**前庭の井戸** — 指図 `ido` の3点を据える(2026-09-23・EDO-0274)。
    /// 部材はどれも**同じ原点(井戸の芯・石敷天端)**で焼いてあるが、⛔ その原点で位置を決めない(規則21):
    /// <list type="number">
    /// <item>**板石敷**(固定側) … 平面は指図の石敷の矩形(`uv` ± `ishikiKen`/2)へ**実メッシュの西縁と南縁**を
    ///   合わせる(<see cref="EdoBuild.EdgeAlong"/>)。高さは**切石の天端**が地表と面一になる所
    ///   (<see cref="EdoBuild.SeatFlush"/> ── 触れるのは割栗の底ではなく天端の縁)。⛔ yaw を振らない(水勾配と枡が東)。</item>
    /// <item>**井筒+井桁** … 井筒(材 Foundation)の外周を石敷の穴の壁へ芯出し(<see cref="EdoBuild.CenterInOpening"/>)、
    ///   井桁(材 wood)の下端を縁石(材 Kirishi)の天端へ下ろす(<see cref="EdoBuild.RestOn"/>)。</item>
    /// <item>**井戸屋形** … 棟の向きは `muneDir`(部材の棟はローカル Z)。柱の根を礎石(材 Kirishi)の天端へ下ろし、
    ///   柱の断面を礎石の断面へ芯出し(<see cref="EdoBuild.CenterOnBed"/>)。</item>
    /// <item>**駒の下の地形** … 石敷の外形に掛かる芝を消し(<see cref="EdoBuild.ClearDetailIn"/>)、井筒の口の下の地形を
    ///   抜く(<see cref="EdoBuild.CutHole"/> ── 口の外は石敷・井筒が覆っていることを検めてから)。⛔ Undo の外。</item>
    /// </list>
    /// 「寄せる → 据える」を2巡する(`docs/oki-kata.md` §2)。⛔ 部材の綴りの数は `ido` からの従属値。</summary>
    public static string Stage8_Ido()
    {
        var gate = Gate(); if (gate != null) return gate;
        var io = D(Doc, "ido");
        if (io == null) return "井戸: ⛔ 指図に `ido` が無い";
        var iz = D(io, "izutsu");
        float ken = F(D(Doc, "const"), "ken");
        string muneDir = S(io, "muneDir");
        var slope = L(io, "ishikiSlope");
        if (iz == null || slope.Count < 2 || !HasNum(io, "ishikiKen") || !HasNum(io, "igetaMitsukeM") ||
            !HasNum(io, "igetaDanN") || !HasNum(io, "hashiraPitchKen") || !HasNum(io, "nokiH") || !HasNum(io, "muneH"))
            return "井戸: ⛔ 指図 `ido` の欄が足りない(ishikiKen/ishikiSlope/izutsu/igeta*/hashiraPitchKen/nokiH/muneH)";
        float yaw;
        if (muneDir == "南北") yaw = 0f;            // 部材の棟 = ローカル Z
        else if (muneDir == "東西") yaw = 90f;
        else return "井戸: ⛔ `ido.muneDir` が南北/東西でない(『" + muneDir + "』)── 屋形は建てない";

        string pIshiki = EdoAssets.Own.SannoIdoIshiki(Mathf.RoundToInt(F(io, "ishikiKen") * ken * 1000f),
                                                      Mathf.RoundToInt(Cv(slope[1]) / Mathf.Max(1e-6f, Cv(slope[0]))));
        string pIgeta = EdoAssets.Own.SannoIdoIgeta(Mathf.RoundToInt(F(iz, "naikeiShaku") / 6f * ken * 1000f),
                                                    Mathf.RoundToInt(F(io, "igetaMitsukeM") * F(io, "igetaDanN") * 1000f));
        string pYakata = EdoAssets.Own.SannoIdoYakata(Mathf.RoundToInt(F(io, "hashiraPitchKen") * ken * 1000f),
                                                      Mathf.RoundToInt(F(io, "nokiH") * 1000f),
                                                      Mathf.RoundToInt(F(io, "muneH") * 1000f));
        foreach (var p in new[] { pIshiki, pIgeta, pYakata })
            if (AssetDatabase.LoadAssetAtPath<GameObject>(p) == null) return "井戸: ⛔ 部材が無い " + p;

        const string STONE = "Kirishi", WOOD = "wood", RUBBLE = "Foundation";
        var uv = P2(G(io, "uv"));
        float h = F(io, "ishikiKen") * 0.5f;
        Vector2 sw = WKeidai(uv.x - h, uv.y - h), ne = WKeidai(uv.x + h, uv.y + h), c = WKeidai(uv.x, uv.y);
        var grp = Group("Keidai/Ido"); Clear(grp);
        var sb = new StringBuilder();

        // 1 板石敷 ─ 固定側
        var ishiki = EdoBuild.Place(pIshiki, new Vector3(c.x, EdoBuild.Ground(c.x, c.y), c.y), 0f, Vector3.one, grp, "Ido_Ishiki");
        float rise = 0f;
        for (int pass = 0; pass < 2; pass++)
        {
            float dx = sw.x - EdoBuild.EdgeAlong(ishiki.transform, Vector3.right, -1f);
            float dz = sw.y - EdoBuild.EdgeAlong(ishiki.transform, Vector3.forward, -1f);
            ishiki.transform.position += new Vector3(dx, 0f, dz);
            EdoBuild.SeatFlush(ishiki, STONE, 0f, out rise);
        }
        float resE = EdoBuild.EdgeAlong(ishiki.transform, Vector3.right, 1f) - ne.x;
        float resN = EdoBuild.EdgeAlong(ishiki.transform, Vector3.forward, 1f) - ne.y;

        // 2 井筒+井桁 ─ 穴へ差し、縁石へ載せる
        var igeta = EdoBuild.Place(pIgeta, ishiki.transform.position, 0f, Vector3.one, grp, "Ido_Igeta");
        float yCut = ishiki.transform.position.y;   // 仮の高さ(下で測り直す)
        float clrMin = float.NaN, clrMax = float.NaN; Vector3 at; int nTouch = 0; float dropIg = float.NaN;
        for (int pass = 0; pass < 2; pass++)
        {
            float top; float r2; Vector3 a2; int n2;
            top = EdoBuild.FlushGap(ishiki, STONE, out r2, out a2, out n2);   // 天端 − 地表の最小(据えた後 ≈0)
            yCut = a2.y - 0.10f;                                             // 天端の下 0.10m ── 板石の層の中
            var sh = EdoBuild.CenterInOpening(igeta, RUBBLE, ishiki, null, yCut, 0.02f, out clrMin, out clrMax);
            if (float.IsNaN(sh.x)) return "井戸: ⛔ 井筒の外周か石敷の穴が測れない(断面 y=" + yCut.ToString("F2") + ")";
            dropIg = EdoBuild.RestOn(igeta, WOOD, ishiki, STONE, 0f, out at, out nTouch);
            if (float.IsNaN(dropIg)) return "井戸: ⛔ 井桁と縁石が向き合わない";
        }

        // 3 井戸屋形 ─ 柱の根を礎石へ
        var yakata = EdoBuild.Place(pYakata, ishiki.transform.position + Vector3.up, yaw, Vector3.one, grp, "Ido_Yakata");
        float worstFoot = float.NaN; int nPost = 0; float dropYk = float.NaN;
        for (int pass = 0; pass < 2; pass++)
        {
            dropYk = EdoBuild.RestOn(yakata, null, ishiki, STONE, 0f, out at, out nPost);
            if (float.IsNaN(dropYk)) return "井戸: ⛔ 屋形の柱と礎石が向き合わない";
            float yFoot = at.y;                                              // 柱の根 = 礎石の天端
            var sh = EdoBuild.CenterOnBed(yakata, null, yFoot + 0.05f, ishiki, STONE, yFoot - 0.02f, 0.5f, out worstFoot);
            if (float.IsNaN(sh.x)) return "井戸: ⛔ 柱か礎石の断面が測れない";
        }
        EdoBuild.RestOn(yakata, null, ishiki, STONE, 0f, out at, out nPost);

        // 4 駒の下の地形 ─ 石敷の外形の中の芝を消し、井筒の口の下を抜く(⛔ 地形の編集は Undo の外)
        //   範囲は**据えた駒の実メッシュ**から: 石敷の平面の外形・井筒(割栗の材)の内周。
        var td = EdoBuild.T().terrainData;
        var pave = EdoBuild.HullOfMat(ishiki.transform);
        var det = EdoBuild.ClearDetailIn(pave);
        float r2x; Vector3 a3; int n3;
        EdoBuild.FlushGap(ishiki, STONE, out r2x, out a3, out n3);
        var mouth = EdoBuild.OpeningOf(igeta.transform, RUBBLE, a3.y - 0.10f);
        string holeWhy = null; var hole = new EdoBuild.TerrainCells();
        if (mouth == null) holeWhy = "井筒の口が測れない";
        else hole = EdoBuild.CutHole(mouth, new[] { ishiki, igeta }, out holeWhy);
        EditorUtility.SetDirty(td);
        AssetDatabase.SaveAssetIfDirty(td);

        Func<GameObject, string> P3 = g => "(" + g.transform.position.x.ToString("F3") + ", " +
            g.transform.position.y.ToString("F3") + ", " + g.transform.position.z.ToString("F3") + ") yaw " +
            g.transform.eulerAngles.y.ToString("F1");
        sb.AppendLine("  板石敷 " + P3(ishiki) + " ── 西縁・南縁を指図の矩形へ / 東縁の残差 " + resE.ToString("+0.000;-0.000") +
                      " 北縁 " + resN.ToString("+0.000;-0.000") + " / 天端の出の最大 " + rise.ToString("F3") + "m(勾配+起伏)");
        sb.AppendLine("  井筒+井桁 " + P3(igeta) + " ── 穴との離れ " + clrMin.ToString("F3") + "〜" + clrMax.ToString("F3") +
                      "m / 井桁と縁石の当たり " + nTouch + " 点");
        sb.AppendLine("  井戸屋形 " + P3(yakata) + "(棟 " + muneDir + ")── 柱と礎石の当たり " + nPost + " 点 / 足ごとの芯ずれ最大 " +
                      worstFoot.ToString("F3") + "m");
        sb.AppendLine("  地形の芝(detail): " + det + " ── 石敷の外形に掛かるセル");
        sb.AppendLine("  地形の穴(holes): " + (holeWhy != null ? "⛔ 抜かなかった ── " + holeWhy : hole.ToString()) + " ── 井筒の口の下");
        return "井戸: 3 点\n" + sb;
    }

    // ================================================================ Stage 9 縁の皮
    //   ⭐ 2m 格子の地形は切通しの石段の脇・土留めの天端の奥・面の縁の縦の切れ目を描けない(外の高さを混ぜる)。
    //   その升だけ地形に穴を開け、0.25m の皮で描く(<see cref="EdoBuild.CutEdgeSkin"/>・普請奉行の決め 2026-09-24・EDO-0430)。
    //   ⚠ 整地・石段・土留め(Stage1〜3)は冒頭で皮を外すので、流したら必ずこれを最後に流し直す。
    [MenuItem(MENU + "9 縁の皮(段石・袖・土留め・面の縁の升に穴を開けて皮で描く)")]
    public static void Stage9Menu() { Debug.Log("[山王] " + Stage9_Hifu()); }
    public static string Stage9_Hifu()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("EdgeSkin");
        int filled = EdoBuild.ClearEdgeSkins(grp);
        var parts = new List<GameObject>();
        foreach (Transform g in Group("Sando")) foreach (Transform c in g) parts.Add(c.gameObject);
        foreach (Transform c in Group("Dodome")) parts.Add(c.gameObject);
        foreach (Transform c in Group("Keidai/Fumiishi")) parts.Add(c.gameObject);   // 踏石・踏み止め(EDO-0428)
        // ⭐ 床を覆う部材 = 門(基壇の床の帯だけ・EdoBuild.FloorTris)── 楼門の基壇の天端 28.30 に皮・地形が同じ高さで斑に出た(EDO-0428 ⑤)
        var floors = new List<GameObject>(); foreach (Transform c in Group("Keidai/Mon")) floors.Add(c.gameObject);
        var faces = SkinFaces(null);
        float tol = F(D(Impl, "checks"), "gradeTol");
        // ⭐ 面の外は算出物 `graded`(法面を含む設計の地盤)を皮で写し、縁は多角形の線で切る。
        //   ⛔ 裏込めの盛土(backfill)は使わない ── 石垣の継ぎ目から草の筋が覗き、回廊の隅から楔が漏れ、東に縞が出た
        //   (普請奉行の決め 2026-09-25・EDO-0430)。背の隙は面の高さの皮で塞ぎ(sealFace)、残りは駒と取り合いの一覧へ。
        var gr = Gr; var cst = D(Doc, "const");
        var design = new EdoBuild.SkinDesign
        {
            x0 = gr.x0, z0 = gr.z0, step = gr.step, nx = gr.nx, nz = gr.nz, h = gr.h, ok = gr.ok,
            batterCut = F(cst, "batterCut"), batterFill = F(cst, "batterFill"),
            baseAt = DemAt()   // 駒の下に落ちた節点は造成前の地盤で引く(見え面の足元の山形・2026-09-25)
        };
        // ⭐ `copingRise:"line"` の袖(宣言の無い石段の袖も同じ・EDO-0421)は背を天端 − 0.05 から法(batterCut)で元の地形へ下げる(施主 2026-09-25)
        var dig = new List<GameObject>(); var lineWalls = new List<string>();
        foreach (var o in L(Doc, "terraceWalls")) { var tw = o as Dictionary<string, object>; if (tw != null && S(tw, "coping") == "stair" && S(tw, "copingRise") != "groundHi") lineWalls.Add(S(tw, "name") + "_"); }
        foreach (var g in parts) foreach (var lw in lineWalls) if (g.name.StartsWith(lw, StringComparison.Ordinal)) { dig.Add(g); break; }
        // ⭐ 土留めは天端の帯で篩う(法の面の点では天端の下へ納める cap を足元の面より下げない ── 法の足の前を溝にしない・2026-09-25)
        var band = new List<GameObject>(); foreach (Transform c in Group("Dodome")) band.Add(c.gameObject);
        // ⛔ 地形の木として植える植栽の点(planting.points の place ≠ GameObject)の升には穴を開けない ── Unity は穴の升の地形の木を
        //   黙って落とす。Stage7 が後から焼き直しても落ちないよう、今の treeInstances でなく算出物の点で守る(2026-09-25・EDO-0430)。
        var plant = new List<Vector2>();
        foreach (var o in L(D(Impl, "planting"), "points"))
        {
            var pt = o as Dictionary<string, object>; if (pt == null || S(pt, "place") == "GameObject") continue;
            var wp = L(pt, "world"); if (wp.Count >= 2) plant.Add(new Vector2(Cv(wp[0]), Cv(wp[1])));
        }
        var rep = EdoBuild.CutEdgeSkin("Sanno", grp, parts, faces, tol, design: design, backfill: 0f, sealFace: true,
                                       digParts: dig, digUnder: 0.05f, digBatter: Mathf.Max(1f, F(cst, "batterCut")),
                                       crestBandParts: band, plantPoints: plant, floorParts: floors);
        AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        var sb = new StringBuilder();
        sb.AppendLine("縁の皮: 古い皮を外して塞いだ升 " + filled + " / 部材 " + rep.parts + " / 面 " + faces.Count);
        sb.AppendLine("  " + rep);
        sb.Append(EdoBuild.SkinGapTable(parts, faces, tol));
        sb.Append(HifuMeasure());
        return sb.ToString();
    }

    /// <summary>皮が高さを揃える面 = 算出物 `terraces` + 取り合いの欄の「被せ」(面の輪郭が石段の最上段の外形を包む ──
    /// `EdoBuild.WrapTopStep` で最上段の実メッシュから輪郭を測って足す・joints[71] 女坂 × Keidai)。</summary>
    static List<EdoBuild.SkinFace> SkinFaces(StringBuilder sb)
    {
        var faces = new List<EdoBuild.SkinFace>();
        foreach (var o in L(Impl, "terraces"))
        {
            var tc = o as Dictionary<string, object>; if (tc == null) continue;
            // ⭐ 盛土の床(指図 terraces[].fillOnly)は皮の「面」にしない ── 面の高さは下限で、地山が高ければ地山(算出物 graded が
            //   max(面, 地山) を持つ)。面にすると皮が床の多角形の中を面の高さへ平らに削り、回廊の基壇の東で地山との境に
            //   高さ 1.2m の垂直な土の面が立った(2026-09-25・EDO-0430)。床は設計の地盤として描く。
            var tdoc = FindByName(Doc, "terraces", G(tc, "name") as string);
            if (tdoc != null && G(tdoc, "fillOnly") is bool && (bool)G(tdoc, "fillOnly")) { if (sb != null) sb.AppendLine("  盛土の床 " + G(tc, "name") + " は面にせず設計の地盤で描く"); continue; }
            var wl = L(tc, "world"); var poly = new Vector2[wl.Count];
            for (int i = 0; i < wl.Count; i++) { var a = wl[i] as List<object>; poly[i] = new Vector2(Cv(a[0]), Cv(a[1])); }
            if (poly.Length >= 3) faces.Add(new EdoBuild.SkinFace(G(tc, "name") as string, poly, F(tc, "y")));
        }
        var sando = Group("Sando");
        foreach (var o in L(Impl, "stairs"))
        {
            var st = o as Dictionary<string, object>; if (st == null) continue;
            string nm = S(st, "name"); string fn, kind; Vector2[] poly; float y;
            if (!TopFaceOf(nm, out fn, out poly, out y, out kind) || !kind.StartsWith("被せ")) continue;
            var g = sando.Find(GroupNameOf(nm)); if (g == null) continue;
            Transform top = null; int best = -1;
            foreach (Transform c in g) { int k; if (c.name.StartsWith("Dan_") && int.TryParse(c.name.Substring(4), out k) && k > best) { best = k; top = c; } }
            if (top == null) continue;
            var wrap = EdoBuild.WrapTopStep(top.gameObject, 0.30f);
            if (wrap != null) { faces.Add(new EdoBuild.SkinFace(fn, wrap, y)); if (sb != null) sb.AppendLine("  面 " + fn + " の輪郭を " + nm + " の最上段 " + top.name + " の外形まで寄せた(被せ)"); }
        }
        return faces;
    }

    /// <summary>皮と部材の隙の内訳(A 面の高さで塞がる / B 駒が浮く / C 面の外の取り合い)を皮を起こし直さずに刷る。</summary>
    public static string HifuGapTable()
    {
        var parts = new List<GameObject>();
        foreach (Transform g in Group("Sando")) foreach (Transform c in g) parts.Add(c.gameObject);
        foreach (Transform c in Group("Dodome")) parts.Add(c.gameObject);
        var faces = SkinFaces(null);
        return EdoBuild.SkinGapTable(parts, faces, F(D(Impl, "checks"), "gradeTol"));
    }

    /// <summary>描かれた地表(皮)で測る: 男坂・女坂の踏面の埋没・袖と土留めの天端の埋没。</summary>
    public static string HifuMeasure()
    {
        var sb = new StringBuilder();
        var dg = EdoBuild.Drawn();
        sb.AppendLine("  描かれた地表で測る(皮 " + dg.skins + " 枚):");
        var sando = Group("Sando");
        var all = new List<GameObject>();
        foreach (Transform g in sando) foreach (Transform c in g) all.Add(c.gameObject);
        foreach (Transform c in Group("Dodome")) all.Add(c.gameObject);
        var over = new EdoBuild.PartTops(all);
        foreach (var gname in new[] { "Otokozaka", "Onnazaka" })
        {
            var g = sando.Find(gname); if (g == null) { sb.AppendLine("    " + gname + ": 無い"); continue; }
            int n = 0, bur = 0, hid = 0; float mx = 0f; string at = "";
            foreach (Transform d in g)
            {
                if (!d.name.StartsWith("Dan_", StringComparison.Ordinal)) continue;
                int sn, hn; float w; Vector3 wa;
                int b = EdoBuild.TopBurial(d, dg, over, out sn, out hn, out w, out wa);
                n += sn; bur += b; hid += hn; if (w > mx) { mx = w; at = d.name + " (" + wa.x.ToString("F1") + ", " + wa.z.ToString("F1") + ")"; }
            }
            sb.AppendLine("    " + gname + " 踏面: 埋没 " + bur + " / " + (n - hid) + " 点(袖・土留めの中へ入る端 " + hid + " 点は見えないので数えない)" +
                          (bur > 0 ? " 最大 " + mx.ToString("F2") + "m @ " + at : ""));
        }
        // 袖(見え面 = 最寄りの段石へ向く向き)
        var sode = new List<GameObject>(); var sodeFace = new Dictionary<GameObject, Vector3>();
        foreach (Transform g in sando)
        {
            var dans = new List<Transform>();
            foreach (Transform c in g) if (c.name.StartsWith("Dan_", StringComparison.Ordinal)) dans.Add(c);
            foreach (Transform c in g)
            {
                if (!c.name.StartsWith("TW_", StringComparison.Ordinal) || dans.Count == 0) continue;
                Transform best = null; float bd = float.MaxValue;
                foreach (var d in dans) { float dd = (d.position - c.position).sqrMagnitude; if (dd < bd) { bd = dd; best = d; } }
                var rt = best.right; rt.y = 0f; rt.Normalize();
                var to = best.position - c.position; to.y = 0f;
                sode.Add(c.gameObject); sodeFace[c.gameObject] = Vector3.Dot(to, rt) >= 0f ? rt : -rt;
            }
        }
        if (sode.Count > 0) sb.AppendLine("    袖の天端: " + EdoBuild.TuckUnderCrest(sode, null, faces: sodeFace, measureOnly: true));
        {   // 踏石・踏み止めの天端(EDO-0428)
            int n = 0, bur = 0, hid = 0; float mx = 0f; string at = "";
            foreach (Transform d in Group("Keidai/Fumiishi"))
            {
                int sn, hn; float w; Vector3 wa;
                int b = EdoBuild.TopBurial(d, dg, over, out sn, out hn, out w, out wa);
                n += sn; bur += b; hid += hn; if (w > mx) { mx = w; at = d.name + " (" + wa.x.ToString("F1") + ", " + wa.z.ToString("F1") + ")"; }
            }
            if (n > 0) sb.AppendLine("    踏石・踏み止めの天端: 埋没 " + bur + " / " + (n - hid) + " 点" + (bur > 0 ? " 最大 " + mx.ToString("F2") + "m @ " + at : ""));
        }
        var dodome = new List<GameObject>(); var face = new Dictionary<GameObject, Vector3>();
        foreach (Transform c in Group("Dodome"))
        {   // 見え面は実メッシュで測る(法の出の大きい軸 = EdoBuild.WallFace ── 野面の駒は局所 +Z・城の石垣は −X)。
            //   野面の隅の駒(…_kado<番>)は見え面が二つ ⇒ 両面の間の対角を渡す(列が稜線の天端を通る・Stage3 と同じ)
            dodome.Add(c.gameObject);
            Vector2 fv;
            if (System.Text.RegularExpressions.Regex.IsMatch(c.name, "_kado\\d+$")) { Vector2 f1, f2; EdoBuild.KadoFaces(c.gameObject, out f1, out f2); fv = (f1 + f2).normalized; }
            else fv = EdoBuild.WallFace(c.gameObject);
            face[c.gameObject] = new Vector3(fv.x, 0f, fv.y);
        }
        if (dodome.Count > 0) sb.AppendLine("    土留めの天端: " + EdoBuild.TuckUnderCrest(dodome, null, faces: face, measureOnly: true, crestBand: EdoBuild.CREST_BAND));
        // 見え面(法の面)の向き: 低い側を向くか(EdoBuild.WallFaceRise)。+0.05 を超えて高い側を向く駒を run ごとに刷る
        {
            var fam = new SortedDictionary<string, int[]>(); int nAll = 0, nRev = 0, nLvl = 0;
            foreach (var g in dodome)
            {
                if (g.name.EndsWith("_kado", StringComparison.Ordinal)) continue;
                // 野面の隅の駒(名 …_kado<番>)は見え面が二つ ⇒ 対角の内と両面の前で測る(EdoBuild.WallFaceRiseKado)
                bool kado = System.Text.RegularExpressions.Regex.IsMatch(g.name, "_kado\\d+$");
                float d = kado ? EdoBuild.WallFaceRiseKado(g, (x, z) => dg.At(x, z)) : EdoBuild.WallFaceRise(g, (x, z) => dg.At(x, z));
                if (float.IsNaN(d)) continue;
                int us = g.name.LastIndexOf('_'); string k = us > 0 ? g.name.Substring(0, us) : g.name;
                int[] c; if (!fam.TryGetValue(k, out c)) { c = new int[3]; fam[k] = c; }
                c[0]++; nAll++;
                if (d > 0.05f) { c[1]++; nRev++; } else if (d >= -0.05f) { c[2]++; nLvl++; }
            }
            var rl = new List<string>(); foreach (var kv in fam) if (kv.Value[1] > 0) rl.Add(kv.Key.Replace("TW_", "") + " " + kv.Value[1] + "/" + kv.Value[0]);
            sb.AppendLine("    土留めの見え面の向き: 駒 " + nAll + " のうち 高い側を向く " + nRev + "・両側が同じ高さ " + nLvl +
                          (rl.Count > 0 ? "〔" + string.Join("・", rl) + "〕" : ""));
        }
        return sb.ToString();
    }

    // ================================================================ Stage 5b 踏石・踏み止め(EDO-0428)
    /// <summary>算出物 `setae.fumiishi`(二ノ鳥居の足元・仁王門の敷居前・参道の階の上端・石段の頭の踏み止め)を敷く。
    /// ⭐ 縁は相手の実メッシュの面(`EdoBuild.LayShikiishi` が天端の帯へ光線を打つ)── 四角の座標は相手の無い縁と幅の目安だけ。
    /// ⭐ 踏み止め(指図 `kaidans[].fumitome`)の脇は、その石段の袖の最上段の駒を**天端が水平な袖**へ差し替えて相手(基壇・腰石垣)の面まで
    /// 延ばしてから敷く(`EdoBuild.LayFlatSode` ── 天端・脇の面は一つ下の斜めの袖の坂上の端に揃え、端は `ExtendEndToFace`。EDO-0459 施主裁定A)。
    /// 天端: 踏み止め = 指図の `top` / 面(`terraces[].surface.fumiishi`)= その面の高さ / 沿道(`sando.roadside.fumiishi`)= 地表(外形の中の最大)。</summary>
    [MenuItem(MENU + "5b 踏石・踏み止め(門・石段の頭の敷石)")]
    public static void Stage5bMenu() { Debug.Log("[山王] " + Stage5b_Fumiishi()); }
    public static string Stage5b_Fumiishi()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("Keidai/Fumiishi"); Clear(grp);
        var sb = new StringBuilder();
        var mon = Group("Keidai/Mon"); var sando = Group("Sando");
        var dod = new List<GameObject>(); foreach (Transform c in Group("Dodome")) if (c.gameObject.activeInHierarchy) dod.Add(c.gameObject);
        var gates = new List<GameObject>(); foreach (Transform c in mon) if (c.gameObject.activeInHierarchy) gates.Add(c.gameObject);
        // ⭐ 門の上向きの面と同じ高さで重なる土留め・腰の駒は下の側を 0.01 下げる(普請奉行の決め 2026-09-26・EDO-0428 二巡目)。
        //   ⛔ 上げない・門は動かさない。敷石はこの後に敷くので、敷石との重なりは敷いた後にもう一度測る。
        { string rp; EdoBuild.SinkCoplanarUnder(dod, gates, out rp); sb.AppendLine("  " + rp); }
        // 出どころ(指図): 名 → (種類, 相手の名, 面)
        var roadside = new Dictionary<string, Dictionary<string, object>>(); var surf = new Dictionary<string, Dictionary<string, object>>();
        foreach (var o in L(D(D(Doc, "sando"), "roadside"), "fumiishi")) { var q = o as Dictionary<string, object>; if (q != null) roadside[S(q, "name")] = q; }
        var ters = L(Doc, "terraces"); Dictionary<string, object> surfTer = null;
        foreach (var to in ters)
        {
            var t = to as Dictionary<string, object>; if (t == null) continue;
            foreach (var o in L(D(t, "surface"), "fumiishi")) { var q = o as Dictionary<string, object>; if (q != null) { surf[S(q, "name")] = q; surfTer = t; } }
        }
        Func<Vector2[], Vector2, Vector2> Snap = (quad, d) =>
        {   // 四角の辺の向きのうち d に最も沿う物(±)
            Vector2 best = d.normalized; float bd = -2f;
            for (int i = 0; i < 2 && quad.Length >= 3; i++)
            {
                var e = (quad[i + 1] - quad[i]).normalized;
                foreach (var c in new[] { e, -e }) { float dd = Vector2.Dot(c, d.normalized); if (dd > bd) { bd = dd; best = c; } }
            }
            return best;
        };
        Func<Vector2[], Vector2> Cen = quad => { Vector2 c = Vector2.zero; foreach (var q in quad) c += q; return c / Mathf.Max(1, quad.Length); };
        Func<Transform, Transform> TopDan = g =>
        {
            Transform top = null; int best = -1;
            if (g != null) foreach (Transform c in g) { int k; if (c.name.StartsWith("Dan_") && int.TryParse(c.name.Substring(4), out k) && k > best) { best = k; top = c; } }
            return top;
        };
        int made = 0, refused = 0;
        foreach (var o in L(D(Impl, "setae"), "fumiishi"))
        {
            var fi = o as Dictionary<string, object>; if (fi == null) continue;
            string nm = S(fi, "name"); var wl = L(fi, "world"); var quad = new Vector2[wl.Count];
            for (int i = 0; i < wl.Count; i++) { var a = wl[i] as List<object>; quad[i] = new Vector2(Cv(a[0]), Cv(a[1])); }
            if (quad.Length < 4) { sb.AppendLine("  ⛔ " + nm + ": 四角が無い"); refused++; continue; }
            Vector2 front; float top = float.NaN; Func<int, string> pathOf = null;
            var back = new List<GameObject>(); var fwd = new List<GameObject>(); var side = new List<GameObject>(dod);
            string how;
            Dictionary<string, object> kd = null;
            foreach (var ko in L(Doc, "kaidans")) { var k = ko as Dictionary<string, object>; if (k != null && D(k, "fumitome") != null && nm == S(k, "name") + "の頭の踏み止め") kd = k; }
            if (kd != null)
            {   // ---- 石段の頭の踏み止め: 背 = 門の基壇・腰石垣 / 前 = 最上段 / 脇 = 袖
                var st = FindByName(Impl, "stairs", S(kd, "name")); var g = sando.Find(GroupNameOf(S(kd, "name"))); var td = TopDan(g);
                if (st == null || td == null) { sb.AppendLine("  ⛔ " + nm + ": 石段(" + S(kd, "name") + ")が建っていない"); refused++; continue; }
                var fwd3 = td.forward; front = Snap(quad, new Vector2(fwd3.x, fwd3.z));
                top = F(D(kd, "fumitome"), "top");
                float keri = F(st, "keri"), fumi = F(st, "fumi"), wM = F(st, "wM");
                pathOf = i => P.Dan(keri, fumi, wM, i);
                back.AddRange(gates); back.AddRange(dod); fwd.Add(td.gameObject);
                // 袖の最上段の駒を相手の面まで延ばす(袖の run の頭は相手の面)
                foreach (var w in SodeWallsOf(S(kd, "name")).Keys)
                {
                    Transform sp = null; int bi = -1;
                    foreach (Transform c in g)
                    {
                        if (!c.name.StartsWith(w + "_", StringComparison.Ordinal)) continue;
                        int k; if (int.TryParse(c.name.Substring(w.Length + 1).TrimEnd('f'), out k) && k > bi) { bi = k; sp = c; }
                    }
                    if (sp == null) { sb.AppendLine("  ⚠ " + nm + ": 袖 " + w + " の駒が無い"); continue; }
                    // ⭐ 最上段の駒は天端が水平な袖へ差し替え、下の斜めの袖(一つ下の駒)の実メッシュに揃えて相手の面まで伸ばす
                    //   (EDO-0459 施主裁定A 2026-09-26 ── 斜めの袖を延ばすと天端が勾配のまま腰の天端より 0.6m 上がる)。
                    Transform below = g.Find(w + "_" + (bi - 1).ToString("000") + "f");
                    if (below == null) { sb.AppendLine("  ⚠ " + nm + ": 袖 " + w + " の一つ下の駒が無い"); continue; }
                    EdoBuild.FlatSode fr; string fw;
                    var flat = EdoBuild.LayFlatSode(sp.gameObject, below.gameObject, EdoAssets.Own.IshidanSodeFlatNori, EdoAssets.Own.IshidanSodeDepths,
                                                    -new Vector3(front.x, 0f, front.y), back, top, 1.5f, out fr, out fw);
                    if (flat == null) { sb.AppendLine("  ⛔ " + nm + ": " + fw); continue; }
                    side.Add(flat);
                    sb.AppendLine("  " + nm + ": 袖 " + flat.name + " ── 水平の袖(丈 " + fr.depth.ToString("F2") + ")天端 " + fr.topLo.ToString("F3") + "〜" + fr.topHi.ToString("F3") +
                                  "(下の袖の段鼻 " + fr.topBelow.ToString("F3") + "・段差 " + fr.step.ToString("+0.000;-0.000") + ")/ 脇の面の食い違い " + fr.sideIn.ToString("+0.000;-0.000") + "・" + fr.sideOut.ToString("+0.000;-0.000") +
                                  " / 下の袖との口 " + (float.IsNaN(fr.gapBelow) ? "—" : fr.gapBelow.ToString("+0.000;-0.000")) +
                                  " / 相手の面まで " + (float.IsNaN(fr.ext) ? "⛔ 当たらず" : fr.ext.ToString("+0.000;-0.000") + "m(当たり " + fr.hits + "・割れ " + fr.spread.ToString("F3") + ")") +
                                  "・見える口 " + (float.IsNaN(fr.gapMate) ? "—" : fr.gapMate.ToString("+0.000;-0.000")) +
                                  " / 高さ方向 " + (float.IsNaN(fr.profMin) ? "—" : fr.profMin.ToString("+0.000;-0.000") + "〜" + fr.profMax.ToString("+0.000;-0.000")) + "(詰めた " + fr.pulled.ToString("F3") + ")" + (fw != null ? " / " + fw : ""));
                }
                how = "踏み止め(天端 " + top.ToString("F2") + "・部材 = " + S(kd, "name") + "の段石)";
            }
            else if (roadside.ContainsKey(nm))
            {   // ---- 沿道の踏石(鳥居の足元): 相手なし・向きは鳥居の実の軸・天端は地表
                var src = S(roadside[nm], "from") ?? ""; string tn = src.StartsWith("torii:") ? src.Substring(6) : src;
                var tr = mon.Find(ToriiNameOf(tn));
                if (tr == null) { sb.AppendLine("  ⛔ " + nm + ": 鳥居(" + tn + ")が建っていない"); refused++; continue; }
                var f3 = tr.forward; front = new Vector2(f3.x, f3.z).normalized; var s2 = new Vector2(front.y, -front.x);
                float ha = (quad[1] - quad[0]).magnitude * 0.5f, hb = (quad[2] - quad[1]).magnitude * 0.5f; var c0 = Cen(quad);
                // ⭐ 四角を鳥居の軸へ(芯 = 算出物の四角の芯・辺長はそのまま)── 算出物の四角は境内の格子の向き(鳥居と 46° ずれる)
                quad = new[] { c0 - front * ha - s2 * hb, c0 + front * ha - s2 * hb, c0 + front * ha + s2 * hb, c0 - front * ha + s2 * hb };
                pathOf = i => EdoAssets.Own.SannoDanNearest(2f * hb, i);
                side.Clear();
                how = "沿道(相手なし・鳥居の軸・天端 = 地表)";
            }
            else if (surf.ContainsKey(nm))
            {   // ---- 面の踏石: 背 = 門 / 石段の最上段、天端 = 面の高さ
                var q = surf[nm]; string src = S(q, "from") ?? "";
                var tc = surfTer != null ? FindByName(Impl, "terraces", S(surfTer, "name")) : null;
                top = tc != null ? F(tc, "y") : float.NaN;
                var c0 = Cen(quad);
                if (src.StartsWith("gate:"))
                {
                    var gt = mon.Find(GateNameOf(src.Substring(5)));
                    if (gt == null) { sb.AppendLine("  ⛔ " + nm + ": 門が建っていない"); refused++; continue; }
                    var gc = EdoBuild.RB(gt.gameObject).center; front = Snap(quad, c0 - new Vector2(gc.x, gc.z));
                    back.Add(gt.gameObject);
                }
                else if (src.StartsWith("kaidan:"))
                {
                    string kn = src.Substring(7); var st = FindByName(Impl, "stairs", kn); var td = TopDan(sando.Find(GroupNameOf(kn)));
                    if (st == null || td == null) { sb.AppendLine("  ⛔ " + nm + ": 石段(" + kn + ")が建っていない"); refused++; continue; }
                    front = Snap(quad, c0 - new Vector2(td.position.x, td.position.z));
                    back.Add(td.gameObject);
                }
                else { sb.AppendLine("  ⛔ " + nm + ": 出どころ " + src + " を読めない"); refused++; continue; }
                float wAcross = 0f; { var s2 = new Vector2(front.y, -front.x); float lo = float.MaxValue, hi = float.MinValue; foreach (var p in quad) { float d = Vector2.Dot(p, s2); lo = Mathf.Min(lo, d); hi = Mathf.Max(hi, d); } wAcross = hi - lo; }
                if (src.StartsWith("kaidan:"))
                {
                    var st = FindByName(Impl, "stairs", src.Substring(7)); float keri = F(st, "keri"), fumi = F(st, "fumi"), wM = F(st, "wM");
                    pathOf = i => P.Dan(keri, fumi, wM, i);
                }
                else pathOf = i => EdoAssets.Own.SannoDanNearest(wAcross, i);
                how = "面 " + (surfTer != null ? S(surfTer, "name") : "?") + "(天端 " + top.ToString("F2") + "・" + src + ")";
            }
            else { sb.AppendLine("  ⛔ " + nm + ": 指図に出どころが無い(踏み止め・沿道・面のどれでもない)"); refused++; continue; }
            if (pathOf(0) == null || AssetDatabase.LoadAssetAtPath<GameObject>(pathOf(0)) == null) { sb.AppendLine("  ⛔ " + nm + ": 段石の部材が無い(" + pathOf(0) + ")"); refused++; continue; }
            EdoBuild.Shiki rep;
            var laid = EdoBuild.LayShikiishi(pathOf, quad, front, top, grp, "Fumiishi_" + nm, back, fwd, side, out rep);
            made += laid.Count;
            sb.AppendLine("  " + nm + " ── " + how + ": " + rep);
        }
        { var laidAll = new List<GameObject>(); foreach (Transform c in grp) laidAll.Add(c.gameObject);
          string rp; EdoBuild.SinkCoplanarUnder(dod, laidAll, out rp); sb.AppendLine("  敷石と " + rp); }
        return "踏石・踏み止め: 敷いた " + made + " 枚" + (refused > 0 ? " / ⛔ 敷けない " + refused : "") + "\n" + sb;
    }

    /// <summary>据え直す Stage の冒頭で縁の皮を外す(穴を塞ぐ)。据え直した後で Stage9 を流し直すこと。</summary>
    static string UnSkin()
    {
        var r = GameObject.Find(GROUP); if (r == null) return "";
        var g = r.transform.Find("EdgeSkin"); if (g == null) return "";
        EdoYashikiPrefab.EnsureEditable(r);
        int n = EdoBuild.ClearEdgeSkins(g);
        return n > 0 ? "  縁の皮を外した(塞いだ升 " + n + ")── ⚠ 最後に Stage9 を流し直すこと\n" : "";
    }

    // ================================================================ 解く順・一括
    /// <summary>**Stage の依存**(EdoBuild.Jun・EDO-0455)。`after` = その Stage が読む物を作る Stage:
    /// 整地(地形)→ 石段 → 土留め(袖の外面・段石の床)→ 囲い・門(GateBed = 石段+土留めの床)/ 縁の皮(石段+土留めの背)。
    /// 社殿・井戸は地形だけに据わるので整地の下流。⭐ 石段・土留めが社殿・井戸の足元の地形を動かしたら、測って引き込む。
    /// ⛔ 社叢(Stage7)は一括に入れない(従前どおり)。⛔ 順はここにだけ書く(一括もこれで流す)。</summary>
    static EdoBuild.Jun Order
    {
        get
        {
            Func<string, Func<Transform>> at = p => () => { var r = GameObject.Find(GROUP); return r != null ? r.transform.Find(p) : null; };
            return new EdoBuild.Jun("山王社")
                .Add("Retire", "0 退避", Stage0_Retire)
                .Add("Grade", "1 整地", Stage1_Grade)
                .Add("Kaidan", "2 石段", Stage2_Kaidan, new[] { "Grade" }, at("Sando"))
                .Add("Dodome", "3 土留め", Stage3_Dodome, new[] { "Grade", "Kaidan" }, at("Dodome"))
                .Add("Mon", "5 門・鳥居", Stage5_MonTorii, new[] { "Grade", "Kaidan", "Dodome" }, at("Keidai/Mon"))
                .Add("Fumiishi", "5b 踏石・踏み止め", Stage5b_Fumiishi, new[] { "Kaidan", "Dodome", "Mon" }, at("Keidai/Fumiishi"))
                .Add("Shaden", "6 社殿", Stage6_Shaden, new[] { "Grade" }, at("Keidai/Shaden"))
                .Add("Ido", "8 井戸", Stage8_Ido, new[] { "Grade" }, at("Keidai/Ido"))
                .Add("Hifu", "9 縁の皮", Stage9_Hifu, new[] { "Grade", "Kaidan", "Dodome", "Mon", "Fumiishi" })
                // ⭐ 囲いは皮の後(2026-09-26・EDO-0437 第5巡)── 座の無い板塀は描かれた地表(皮)に据わる。皮は囲いを部材に数えない。
                .Add("Kakoi", "4 囲い", Stage4_Kakoi, new[] { "Grade", "Kaidan", "Dodome", "Hifu" }, at("Kakoi"));
        }
    }

    /// <summary>**変えた Stage から後だけ流す**(key: Retire・Grade・Kaidan・Dodome・Kakoi・Mon・Fumiishi・Shaden・Ido・Hifu)。
    /// 例: 石段だけ直した ⇒ `RunFrom("Kaidan")` = 石段 → 土留め → 囲い → 門 → 縁の皮(整地・社殿・井戸は流さない)。</summary>
    public static string RunFrom(params string[] changed) { var g = Gate(); return g ?? Order.RunFrom(changed); }
    /// <summary>流さずに、流れる Stage だけを見積もる。</summary>
    public static string PlanFrom(params string[] changed) { return Order.Plan(changed); }

    [MenuItem(MENU + "ここから後だけ流す/2 石段から")] static void FromKaidanMenu() { Debug.Log("[山王] " + RunFrom("Kaidan")); }
    [MenuItem(MENU + "ここから後だけ流す/3 土留めから")] static void FromDodomeMenu() { Debug.Log("[山王] " + RunFrom("Dodome")); }
    [MenuItem(MENU + "ここから後だけ流す/4 囲いから")] static void FromKakoiMenu() { Debug.Log("[山王] " + RunFrom("Kakoi")); }
    [MenuItem(MENU + "ここから後だけ流す/5 門・鳥居から")] static void FromMonMenu() { Debug.Log("[山王] " + RunFrom("Mon")); }

    [MenuItem(MENU + "一括(0→6・8・9。⛔ 社叢は撒かない)")]
    public static void BuildAllMenu() { Debug.Log("[山王] " + BuildAll()); }
    public static string BuildAll() { var g = Gate(); return g ?? Order.RunAll(); }
}
