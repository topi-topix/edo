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
    /// ⛔ steal できなかった。⇒ 暫定でここに置く。**空き次第 `EdoAssets.Own` へ移すこと**
    /// (Dan / SakuKoshidaka / SannoShaden の3系統)。目録 `docs/asset-index.tsv` に全点載っている。</summary>
    static class P
    {
        /// <summary>段石。綴りに **蹴上・踏面・幅** が入る(`Tools/Blender/build_sanno_buzai.py -- dan`)。
        /// ⭐ 個体 a/b の2種を **i%2 で振る**(⛔ 片方だけを53段並べない)。</summary>
        public static string Dan(float keri, float fumi, float w, int i)
        {
            return "Assets/Edo/Models/Kaidan/Dan_" + keri.ToString("F3", IC) + "_" +
                   fumi.ToString("F3", IC) + "_" + w.ToString("F3", IC) + "_" + (i % 2 == 0 ? "a" : "b") + ".fbx";
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
                _impl = EdoMiniJson.Parse(File.ReadAllText(Path.Combine(RepoRoot, EdoSannoShaBuilder.ImplRel)))
                        as Dictionary<string, object>;
            return _impl;
        }
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
        return new Vector2(F(g, "x0") + u * ken, F(g, "z0") + v * ken);
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
        int n = 0, skip = 0; float cmax = 0f, fmax = 0f; double cutSum = 0, fillSum = 0;
        float bx0 = float.MaxValue, bx1 = float.MinValue, bz0 = float.MaxValue, bz1 = float.MinValue;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = WX(x0 + x), wz = WZ(z0 + z);
                float y;
                // ⚠ 地形の節点は 2m 刻み・設計面は 1m 刻みなので、**面の縁の節点が丸ごと落ちる**。
                //   ⇒ 4隅がそろわないときは **1セル以内の最寄り**で拾う(縁を1節点だけ延ばす)。
                //   ⛔ それでも無ければ触らない — 設計面の外へ外挿しない。
                if (!gr.Bilinear(wx, wz, out y) && !gr.Near(wx, wz, 1, out y)) { skip++; continue; }
                float cur = H[z, x] * ts.y + tp.y;
                if (y < cur) { cmax = Mathf.Max(cmax, cur - y); cutSum += cur - y; }
                else { fmax = Mathf.Max(fmax, y - cur); fillSum += y - cur; }
                H[z, x] = Mathf.Clamp01((y - tp.y) / ts.y); n++;
                bx0 = Mathf.Min(bx0, wx); bx1 = Mathf.Max(bx1, wx);
                bz0 = Mathf.Min(bz0, wz); bz1 = Mathf.Max(bz1, wz);
            }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format(
            "整地: 書いた {0} 節点 / 設計面が欠けていて触らなかった {1} 節点\n" +
            "  切土 最大 {2:F2}m 体積 {3:F0}m³ / 盛土 最大 {4:F2}m 体積 {5:F0}m³\n" +
            "  触った範囲 x[{6:F1},{7:F1}] z[{8:F1},{9:F1}](算出物 graded の内)",
            n, skip, cmax, cutSum * a, fmax, fillSum * a, bx0, bx1, bz0, bz1);
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
        var sb = new StringBuilder();
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
            if (haveA && haveB && ga > gb) pts.Reverse();
            else if (!(haveA && haveB)) sb.AppendLine("  ⚠ " + name + ": 設計面から上下を決められない(折れ線の順のまま)");

            var grp = Group("Sando/" + GroupNameOf(name)); Clear(grp);
            int made = 0;
            for (int i = 0; i < spans.Count; i++)
            {
                var sp = spans[i] as List<object>; if (sp == null || sp.Count < 3) continue;
                float s0 = Cv(sp[0]), s1 = Cv(sp[1]), face = Cv(sp[2]);
                Vector2 pos, dir; PolyAt(pts, (s0 + s1) * 0.5f, out pos, out dir);
                // 部材の原点 = 踏面の中心・**踏面の天端**。⛔ SeatBottom で据えない(地中の胴がある)。
                float y = face + keri;
                // ローカル +Z = 見え面 = **坂下**。
                EdoBuild.Place(P.Dan(keri, fumi, wM, i), new Vector3(pos.x, y, pos.y),
                               YawZ(-dir), Vector3.one, grp, "Dan_" + i.ToString("00"));
                made++;
            }
            sb.AppendLine("  " + name + ": 段石 " + made + " 段(蹴上 " + keri.ToString("F3") +
                          " / 踏面 " + fumi.ToString("F3") + " / 幅 " + wM.ToString("F3") + ")");
        }
        return "石段\n" + sb;
    }
    /// <summary>指図の名 → シーンの群の名。⛔ 綴りの読み替えだけ(⭐ 対応表が消えるのが正しい終点)。</summary>
    static string GroupNameOf(string designName)
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
        var grp = Group("Dodome"); Clear(grp);
        float probe = WallProbeM;
        var sb = new StringBuilder();
        int total = 0, buried = 0; float buriedM = 0f;

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

        foreach (var o in L(Impl, "runs"))
        {
            var wl = o as Dictionary<string, object>; if (wl == null || S(wl, "of") != "wall") continue;
            string name = S(wl, "name");
            var nodes = Pts(L(wl, "nodes"));
            var prof = L(wl, "profile");
            float step = F(wl, "profileStep");
            int made = 0; float skipM = 0f;

            foreach (var so in L(wl, "segs"))
            {
                var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
                Vector2 a = P2(seg[0]), b = P2(seg[1]);
                float len = Vector2.Distance(a, b); if (len < 0.4f) continue;
                Vector2 dir = (b - a) / len;
                // seg の始点が run の折れ線のどこか(s の原点合わせ)
                float sBase = ArcOf(nodes, a);
                int N = (len <= IG_RUN) ? 1 : Mathf.CeilToInt((len - IG_RUN) / IG_PITCH_MAX) + 1;
                float pitch = (N > 1) ? (len - IG_RUN) / (N - 1) : 0f;
                float head = (len <= IG_RUN) ? (len + IG_RUN) * 0.5f : IG_RUN;

                // 低い側(= 外向き)を seg ごとに多数決で決める。⛔ 建つ区間だけで投票する。
                int voteR = 0, voteL = 0;
                Vector2 nrm = new Vector2(dir.y, -dir.x);      // dir の右手
                for (float ss = 0f; ss <= len; ss += 1f)
                {
                    float top, faceH, backH;
                    if (!ProfileAt(prof, step, sBase + ss, out top, out faceH, out backH)) continue;
                    if (faceH <= BURIED_EPS) continue;
                    Vector2 pp = a + dir * ss;
                    float gR, gL;
                    bool hR = Gr.Near(pp.x + nrm.x * probe, pp.y + nrm.y * probe, 1, out gR);
                    bool hL = Gr.Near(pp.x - nrm.x * probe, pp.y - nrm.y * probe, 1, out gL);
                    bool retR = hR && Mathf.Abs(gR - top) < 0.05f;
                    bool retL = hL && Mathf.Abs(gL - top) < 0.05f;
                    if (retR && !retL) voteL++;                 // 受けているのが右 ⇒ 外は左
                    else if (retL && !retR) voteR++;
                    else if (hR && hL && Mathf.Abs(gR - gL) > 0.05f) { if (gR < gL) voteR++; else voteL++; }
                    else if (hR != hL) { if (!hR) voteR++; else voteL++; }   // 設計面の外 = 自然地形の側
                }
                Vector2 outw;
                if (voteR == 0 && voteL == 0)
                {
                    // 両側が同じ高さ = 基壇。⇒ 同族の壁が囲む中心から外へ。
                    Vector2 mid = (a + b) * 0.5f;
                    Vector2 away = mid - famC[FamilyOf(name)];
                    outw = (Vector2.Dot(nrm, away) >= 0f) ? nrm : -nrm;
                }
                else outw = (voteR >= voteL) ? nrm : -nrm;
                // ローカル +X を外へ・+Z を走りへ。⇒ 走りの向きは外向き法線から決まる
                Vector2 run = (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) >= 0f) ? dir : -dir;
                Vector2 A = (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) >= 0f) ? a : b;
                float psi = Mathf.Atan2(run.x, run.y) * Mathf.Rad2Deg;

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
                    EdoBuild.Place(EdoAssets.JC.CastleWall, new Vector3(p.x, top - IG_H, p.y),
                                   psi, Vector3.one, grp, name + "_" + made.ToString("000") + "f");
                    made++;
                }
            }
            total += made; buriedM += skipM;
            sb.AppendLine("  " + name + ": 駒 " + made + " 枚" +
                          (skipM > 0.05f ? " / ⛔ 埋まっていて建てなかった " + skipM.ToString("F1") + "m" : ""));
        }
        return "土留め: 駒 " + total + " 枚 / ⛔ 埋まっていて建てなかった " + buried + " 枚 ≒ " +
               buriedM.ToString("F1") + "m(裁定 EDO-0182 が未着手のため据え置き)\n" + sb;
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
            { pending += F(r, "lenM"); pendNames.Add(name + "(" + kind + " " + F(r, "lenM").ToString("F1") + "m)"); continue; }

            var grp = Group("Kakoi/" + name); Clear(grp);
            bool hasSeat = HasNum(r, "seat");
            float seat = F(r, "seat");
            int made = 0;
            if (kind == "透塀") { made = Sukibei(r, name, grp, sb); }
            else if (kind == "袖塀") { made = Sodebei(r, name, grp, sb); }
            else foreach (var so in L(r, "segs"))
            {
                var seg = so as List<object>; if (seg == null || seg.Count < 2) continue;
                Vector2 a = P2(seg[0]), b = P2(seg[1]);
                float len = Vector2.Distance(a, b); if (len < 0.25f) continue;
                Vector2 dir = (b - a) / len;
                if (kind == "板塀")
                {
                    // 在庫の板塀(edogoyomi)。⚠ 呼び寸に合わせて走り方向だけ伸縮するのは
                    //   既存の `PanelRun` の流儀(全邸で同じ)。表裏2枚で `_kf`/`_kb` と名づく。
                    var outw = new Vector2(dir.y, -dir.x);
                    var lst = EdoSannoJuboBuilder.PanelRun(grp, a, b, outw, name, EdoAssets.Eg.Itabei5, Vector2.zero, -1);
                    made += lst.Count;
                }
                else
                {
                    // 腰高の柵。部材の原点 = **スパンの中心・地盤レベル**・柱はローカル −X 端。
                    int N = Mathf.Max(1, Mathf.RoundToInt(len / SAKU_SPAN));
                    float pitch = len / N;
                    float sx = pitch / SAKU_SPAN;
                    float ry = YawX(dir);
                    for (int k = 0; k < N; k++)
                    {
                        Vector2 c = a + dir * (pitch * (k + 0.5f));
                        Vector2 e0 = a + dir * (pitch * k), e1 = a + dir * (pitch * (k + 1));
                        float y0 = hasSeat ? seat : SurfaceY(e0), y1 = hasSeat ? seat : SurfaceY(e1);
                        var go = EdoBuild.Place(P.SakuSpan, new Vector3(c.x, (y0 + y1) * 0.5f, c.y),
                                                ry, new Vector3(sx, 1f, 1f), grp, name + "_" + made.ToString("000") + "f");
                        if (!hasSeat && Mathf.Abs(y1 - y0) > 0.02f)
                            go.transform.rotation = Quaternion.Euler(0, ry, 0) *
                                                    Quaternion.Euler(0, 0, Mathf.Atan2(y1 - y0, pitch) * Mathf.Rad2Deg);
                        made++;
                    }
                    // ⛔ run の +X 端に柱を1本足す(足さないと貫が宙で終わる)
                    float yEnd = hasSeat ? seat : SurfaceY(b);
                    EdoBuild.Place(P.SakuPost, new Vector3(b.x, yEnd, b.y), ry, Vector3.one,
                                   grp, name + "_" + made.ToString("000") + "f");
                    made++;
                }
            }
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

    // ---------------------------------------------------------------- 透塀
    /// <summary>部材表の行を名で引く。⛔ 寸法をここに写さない。</summary>
    static Dictionary<string, object> FindBom(string label)
    {
        foreach (var o in L(Doc, "bom"))
        { var b = o as Dictionary<string, object>; if (b != null && S(b, "部材") == label) return b; }
        return null;
    }
    const string BOM_SUKIBEI = "透塀(連子窓の塀)";
    /// <summary>透塀の一辺を据える。**割り付けは指図の規約**(`bom[透塀].spanBaseM` で辺を等分 ──
    /// 本数 = round(辺長 / 基準スパン)・スパン = 辺長 / 本数)で、⛔ 実装は数を持たない。
    /// 端の種類は −X, +X の順: c = 隅部材へ続く / n = 次のスパンへ / t = 中門へ突き付け /
    /// h = 口の縁の柱(南の潜り)。⚠ 部材の原点 = スパンの中心・床(= 基壇の天端 = `seat`)。</summary>
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
        for (int si = 0; si < segs.Count; si++)
        {
            var seg = segs[si] as List<object>; if (seg == null || seg.Count < 2) continue;
            Vector2 a = P2(seg[0]), b = P2(seg[1]);
            float len = Vector2.Distance(a, b); if (len < 0.2f) continue;
            Vector2 dir = (b - a) / len;
            string e0 = (si == 0) ? "c" : eg, e1 = (si == segs.Count - 1) ? "c" : eg;
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
        int made = 0, flipped = 0;
        foreach (var o in L(Doc, "joints"))
        {
            var j = o as Dictionary<string, object>; if (j == null) continue;
            string kind = S(j, "kind"); if (kind == null || kind.IndexOf('隅') < 0) continue;
            string an = RunRef(S(j, "a")), bn = RunRef(S(j, "b"));
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
            if (dezumi != (kind.IndexOf("出隅") >= 0))
            {
                flipped++;
                sb.AppendLine("  ⚠ 隅 " + an + "→" + bn + ": `joints` は「" + kind + "」だが、折れ線の凹凸は **" +
                              (dezumi ? "出隅" : "入隅") + "** ── 折れ線に従って据えた(⛔ 指図方へ差し戻す)");
            }
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
            var grp = Group("Kakoi/" + an);
            EdoBuild.Place(part, new Vector3(node.x, seat, node.y), YawX(-f), Vector3.one, grp,
                           an + "_" + (900 + made).ToString("000") + "f");
            made++;
        }
        sb.AppendLine("  透塀の隅: " + made + " 箇所(出隅・入隅は折れ線の凹凸から)" +
                      (flipped > 0 ? " / ⚠ `joints` の呼び名と食い違った隅 " + flipped + " 箇所" : ""));
        return made;
    }
    /// <summary>`joints` の「透塀 Sukibei_E(北袖)」のような綴りから run 名を取り出す。</summary>
    static string RunRef(string s)
    {
        if (string.IsNullOrEmpty(s)) return null;
        int p = s.IndexOf('(');
        if (p > 0) s = s.Substring(0, p);
        var tok = s.Trim().Split(' ');
        string last = tok[tok.Length - 1].Trim();
        return last.StartsWith("Sukibei_") ? last : null;
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
    static float SurfaceY(Vector2 p)
    {
        float y;
        if (Gr.Bilinear(p.x, p.y, out y)) return y;
        return EdoBuild.Ground(p.x, p.y);
    }

    // ================================================================ Stage 5 門・鳥居
    [MenuItem(MENU + "5 門・鳥居")]
    public static void Stage5Menu() { Debug.Log("[山王] " + Stage5_MonTorii()); }
    /// <summary>算出物 `gates` の芯・yaw・敷居の高さへ据える。
    /// ⚠ **楼門は Japanese Castle の Yaguramon A の代用**(`bom`「遠景では読めるので当面代用」)。
    /// ⛔ 中門・鳥居・木戸は **部材が無い**(`bom` が「無い/新造」優先2)ので建てない。</summary>
    public static string Stage5_MonTorii()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("Keidai/Mon"); Clear(grp);
        var sb = new StringBuilder();
        int made = 0; var pend = new List<string>();
        foreach (var o in L(Impl, "gates"))
        {
            var gt = o as Dictionary<string, object>; if (gt == null) continue;
            string name = S(gt, "name");
            var wp = L(gt, "world"); if (wp.Count < 2) continue;
            Vector2 p = new Vector2(Cv(wp[0]), Cv(wp[1]));
            float yaw = F(gt, "yaw"), sill = F(gt, "sill");
            // 代用が `bom` に書いてある門だけ据える
            string scn = null; float scale = 0f;
            if (name.StartsWith("隨身門")) { scn = "Zuijinmon"; scale = 0.60f; }
            else if (name.StartsWith("坂下の門")) { scn = "Niomon"; scale = 0.55f; }
            if (scn == null) { pend.Add(name); continue; }
            var go = EdoBuild.Place(EdoAssets.JC.YaguramonA, Vector3.zero, yaw, Vector3.one * scale, grp, scn);
            var b = EdoBuild.RB(go);
            go.transform.position += new Vector3(p.x - b.center.x, 0, p.y - b.center.z);
            EdoBuild.SeatBottom(go, sill - 0.22f * scale);   // `bom`: pivot の埋め込み補正
            made++;
            sb.AppendLine("  " + name + " → " + scn + " (" + p.x.ToString("F1") + ", " + p.y.ToString("F1") +
                          ") yaw " + yaw.ToString("F0") + " 敷居 " + sill.ToString("F2") + " ×" + scale.ToString("F2") +
                          " ⚠ 代用(Yaguramon A)");
        }
        foreach (var o in L(Doc, "torii"))
        {
            var tr = o as Dictionary<string, object>; if (tr == null) continue;
            pend.Add(S(tr, "name"));
        }
        if (pend.Count > 0)
            sb.AppendLine("  ★ 部材が無いので建てなかった(bom「無い/新造」優先2): " + string.Join(" / ", pend.ToArray()));
        return "門・鳥居: " + made + " 基\n" + sb;
    }

    // ================================================================ Stage 6 社殿
    [MenuItem(MENU + "6 社殿5棟+木階")]
    public static void Stage6Menu() { Debug.Log("[山王] " + Stage6_Shaden()); }
    /// <summary>社殿。⭐ 部材の**ピボット = その棟の区画 (u0,v0,du,dv) の中心・地盤レベル**で、
    /// **ローカル +X = 東 = 正面**。⇒ `munes` の矩形の中心へ **yaw 0・scale one** のまま置く。
    /// ⛔ SeatBottom で据えない(部材が地盤レベルを原点に持っている)。</summary>
    public static string Stage6_Shaden()
    {
        var gate = Gate(); if (gate != null) return gate;
        var grp = Group("Keidai/Shaden"); Clear(grp);
        var sb = new StringBuilder();
        int made = 0; var pend = new List<string>();
        foreach (var o in L(Doc, "munes"))
        {
            var m = o as Dictionary<string, object>; if (m == null) continue;
            string name = S(m, "name");
            string part = S(m, "partFrom");
            if (string.IsNullOrEmpty(part)) { pend.Add(name); continue; }
            string path = P.Shaden(part);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { pend.Add(name + "(" + part + " が無い)"); continue; }
            Vector2 c = W(F(m, "u0") + F(m, "du") * 0.5f, F(m, "v0") + F(m, "dv") * 0.5f);
            float y;
            if (!Gr.Near(c.x, c.y, 3, out y)) y = EdoBuild.Ground(c.x, c.y);
            EdoBuild.Place(path, new Vector3(c.x, y, c.y), 0f, Vector3.one, grp, ShadenNameOf(name));
            made++;
            sb.AppendLine("  " + name + " → " + ShadenNameOf(name) + " (" + c.x.ToString("F2") + ", " +
                          c.y.ToString("F2") + ") 地盤 " + y.ToString("F2"));
        }
        // 木階(向拝の階)— `kaidans` の a〜b の中点・地盤レベル。⛔ 石段にしない。
        foreach (var o in L(Doc, "kaidans"))
        {
            var k = o as Dictionary<string, object>; if (k == null) continue;
            if (G(k, "kizahashi") == null) continue;
            if (!S(k, "name").StartsWith("向拝")) continue;    // 本殿の木階は本殿の部材に入っている
            Vector2 a = P2(G(k, "a")), b = P2(G(k, "b"));
            Vector2 c = W((a.x + b.x) * 0.5f, a.y);
            string path = P.Shaden("Sanno_Kizahashi_3ken");
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { pend.Add(S(k, "name")); continue; }
            EdoBuild.Place(path, new Vector3(c.x, F(k, "yBot"), c.y), 0f, Vector3.one, grp, "Kizahashi");
            made++;
            sb.AppendLine("  " + S(k, "name") + " → Kizahashi (" + c.x.ToString("F2") + ", " + c.y.ToString("F2") +
                          ") 地盤 " + F(k, "yBot").ToString("F2"));
        }
        if (pend.Count > 0)
            sb.AppendLine("  ★ 部材が無いので建てなかった(bom「無い/新造」): " + string.Join(" / ", pend.ToArray()));
        return "社殿: " + made + " 棟\n" + sb;
    }
    static string ShadenNameOf(string designName)
    {
        if (designName.StartsWith("本殿")) return "Honden";
        if (designName.StartsWith("作り合い")) return "Tsukuriai";
        if (designName.StartsWith("幣殿")) return "Heiden";
        if (designName.StartsWith("拝殿")) return "Haiden";
        if (designName.StartsWith("向拝")) return "Kohai";
        return designName;
    }

    static Dictionary<string, object> FindByName(Dictionary<string, object> src, string key, string name)
    {
        foreach (var o in L(src, key))
        { var m = o as Dictionary<string, object>; if (m != null && S(m, "name") == name) return m; }
        return null;
    }

    // ================================================================ 一括
    [MenuItem(MENU + "一括(0→6。⛔ 社叢は撒かない)")]
    public static void BuildAllMenu() { Debug.Log("[山王] " + BuildAll()); }
    public static string BuildAll()
    {
        var sb = new StringBuilder();
        sb.AppendLine(Stage0_Retire());
        sb.AppendLine(Stage1_Grade());
        sb.AppendLine(Stage2_Kaidan());
        sb.AppendLine(Stage3_Dodome());
        sb.AppendLine(Stage4_Kakoi());
        sb.AppendLine(Stage5_MonTorii());
        sb.AppendLine(Stage6_Shaden());
        return sb.ToString();
    }
}
