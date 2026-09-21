// 土井大隅守上屋敷(三河刈谷藩2万3千石・譜代・雁間)ビルダー。
//
// 【正典は指図】docs/Sashizu/doi_sashizu.json を**実行時に読む**。
//   設計値(面の高さ・段の矩形・外周の run・土留め・棟・庭)を C# に書き写さない。
//   区画は docs/Sashizu/parcels.json(`EdoParcels.Get("doi")`)、パスは EdoAssets 経由。
//
// 【グリッド】主郭は回転間グリッド `grid.shukaku`。u=東辺沿い北+ / v=敷地の奥(西)+、単位は間。
//   原点=表門の芯。⚠ (u,v) は世界と同じ向き(u から v へ反時計回り)。
//
// 【造成の考え方】造成後の地盤の式は**生成器の `sashizu_lib.graded_y`(土井式)が正典**で、
//   ここはその移植。順序も同じ:
//     ① 斜路 `ramps` の踏面 → ② 石段 `kaidans` の掘割の踏面 → ③ 段 `terraces` の高さ
//     → ④ 盛土 1:batterFill / 切土 1:batterCut の法面(featherCap 内で着地するものだけ)
//   段の縁に土留め `terraceWalls` が載っている区間からは法面を出さない(壁が垂直に受ける)。
//   外周 run の基壇石垣が受ける区間(v=0 の辺)も同じ。
//
// 【造成前の地盤】**`docs/Sashizu/doi_edo_world.json`(江戸期の復元地盤・世界2m格子)**を双一次で引く。
//   ⛔ live terrain から採らない(CLAUDE.md 規則13)。⛔ 現代の地面(base_dem)も使わない —
//   指図の切盛・断面・§B-1 の合否はすべて江戸期復元地盤に対して立っている
//   (build_doi_sashizu.py の「地盤の面は2つある」の節)。
//
// ⚠ 地形の編集は Undo の外。走らせる前に Stage0_Backup でハイトマップを退避すること。
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static partial class EdoDoiBuilder
{
    public const string SashizuRel = "docs/Sashizu/doi_sashizu.json";
    /// <summary>造成前の地盤の正本(江戸期復元・世界2m格子)。⛔ live terrain を種地にしない。</summary>
    public const string EdoDemRel = "docs/Sashizu/doi_edo_world.json";
    public const string ParcelId = "doi";
    /// <summary>シーンのルート群。⚠ 名前は 2026-08-12 の仮置き(EdoSannoKitaBuilder.Stage2_Doi)由来で、
    /// `EdoSashizuExport.Houses["doi"].root` と一致していなければ突き合わせが動かない。</summary>
    public const string Grp = "Edo_Yashiki_DoiOsumi";
    const string MENU = "Edo/土井大隅守上屋敷/";

    // ---------------------------------------------------------------- 指図の読み込み
    static Dictionary<string, object> _d;
    static string Root { get { return Directory.GetParent(Application.dataPath).FullName; } }
    static string SashizuPath { get { return Path.Combine(Root, SashizuRel); } }

    [MenuItem(MENU + "指図を読み直す")]
    public static void Reload()
    {
        _d = null; _frame = null; _terr = null; _walls = null; _runs = null;
        _nat = null; _walledCache = null; _runEdges = null; _niwa = null;
        // ⚠ **足したキャッシュはここへも足す。**落とすと「指図を読み直したのに古い値で建つ」。
        _boxCache = null; _pondW = null; _pondEdge = null;
        Debug.Log("[Doi] 指図を読み直した");
    }
    static Dictionary<string, object> D
    {
        get
        {
            if (_d == null)
            {
                if (!File.Exists(SashizuPath)) throw new Exception("指図が無い: " + SashizuPath);
                _d = EdoMiniJson.Parse(File.ReadAllText(SashizuPath)) as Dictionary<string, object>;
                if (_d == null) throw new Exception("指図が読めない(JSON): " + SashizuPath);
            }
            return _d;
        }
    }
    static Dictionary<string, object> O(object o) { return o as Dictionary<string, object>; }
    static List<object> A(object o) { return o as List<object>; }
    static float F(object o) { return o == null ? 0f : Convert.ToSingle(o); }
    static string S(object o) { return o as string; }
    static bool Has(Dictionary<string, object> o, string k) { return o != null && o.ContainsKey(k) && o[k] != null; }
    static float C(string k)
    {
        var c = O(D["const"]);
        if (!Has(c, k)) throw new Exception("指図 const." + k + " が無い(⛔ 既定値で埋めない)");
        return F(c[k]);
    }

    // ---------------------------------------------------------------- 回転間グリッド
    public class Frame
    {
        public float x0, z0, ux, uz, vx, vz, ken;
        public Vector2 W(float u, float v)
        { return new Vector2(x0 + (ux * u + vx * v) * ken, z0 + (uz * u + vz * v) * ken); }
        public Vector2 L(Vector2 p)
        {
            float dx = p.x - x0, dz = p.y - z0;
            return new Vector2((dx * ux + dz * uz) / ken, (dx * vx + dz * vz) / ken);
        }
    }
    static Frame _frame;
    public static Frame Grid
    {
        get
        {
            if (_frame == null)
            {
                var g = O(O(D["grid"])["shukaku"]);
                _frame = new Frame
                {
                    x0 = F(g["x0"]), z0 = F(g["z0"]),
                    ux = F(g["ux"]), uz = F(g["uz"]), vx = F(g["vx"]), vz = F(g["vz"]),
                    ken = C("ken")
                };
            }
            return _frame;
        }
    }

    /// <summary>段。`yaw` を持つ段は**回転矩形(OBB)**で、`u0..v1` はその外接矩形にすぎない
    /// (`sashizu_lib.obb_pts` の註)。⛔ 外接矩形で造成すると隅が段の高さで平らになる。</summary>
    public class Terrace
    {
        public string name; public float u0, v0, u1, v1, y;
        public bool rot; public float uc, vc, L, D, yaw;
        public bool In(float u, float v, float pad)
        {
            if (!rot) return u0 - pad <= u && u <= u1 + pad && v0 - pad <= v && v <= v1 + pad;
            float r = yaw * Mathf.Deg2Rad;
            float lu = Mathf.Sin(r), lv = Mathf.Cos(r), du = Mathf.Cos(r), dv = -Mathf.Sin(r);
            float su = u - uc, sv = v - vc;
            return Mathf.Abs(su * lu + sv * lv) <= L / 2f + pad
                && Mathf.Abs(su * du + sv * dv) <= D / 2f + pad;
        }
    }
    static Terrace[] _terr;
    public static Terrace[] Terraces
    {
        get
        {
            if (_terr == null)
            {
                var list = new List<Terrace>();
                foreach (var o in A(D["terraces"]))
                {
                    var t = O(o);
                    // ⛔ 岡部式の「等高線なり多角形」の段(`poly`)には未対応。黙って矩形で読むと
                    //    段の形が別物になるので、出会ったら止める(発明しない)。
                    if (Has(t, "poly")) throw new Exception("段 " + S(t["name"]) + " が poly を持つ — 未対応");
                    var e = new Terrace
                    {
                        name = S(t["name"]),
                        u0 = F(t["u0"]), v0 = F(t["v0"]), u1 = F(t["u1"]), v1 = F(t["v1"]), y = F(t["y"])
                    };
                    if (Has(t, "yaw"))
                    {
                        e.rot = true; e.uc = F(t["uc"]); e.vc = F(t["vc"]);
                        e.L = F(t["L"]); e.D = F(t["D"]); e.yaw = F(t["yaw"]);
                    }
                    list.Add(e);
                }
                _terr = list.ToArray();
            }
            return _terr;
        }
    }

    /// <summary>郭内の土留め。`a`/`b` はグリッド座標(間)、`coping`=天端、`s`=丁場、`drop`=[両端の落差]。
    /// 開口(`gapU`/`gapV` ± `gapHalf`)の区間には壁が無い。</summary>
    public class TWall
    {
        public string name; public Vector2 a, b; public float coping, s; public int tiers;
        public bool hasGapU, hasGapV; public float gapU, gapV, gapHalf;
        public bool hasSode; public float sodeLen, sodeDrop;
        public float dropA, dropB;
    }
    static TWall[] _walls;
    public static TWall[] Walls
    {
        get
        {
            if (_walls == null)
            {
                var list = new List<TWall>();
                foreach (var o in A(D["terraceWalls"]))
                {
                    var w = O(o); var a = A(w["a"]); var b = A(w["b"]);
                    var e = new TWall
                    {
                        name = S(w["name"]),
                        a = new Vector2(F(a[0]), F(a[1])), b = new Vector2(F(b[0]), F(b[1])),
                        coping = F(w["coping"]), s = F(w["s"]),
                        tiers = Has(w, "tiers") ? (int)F(w["tiers"]) : 1,
                        gapHalf = Has(w, "gapHalf") ? F(w["gapHalf"]) : 0f
                    };
                    if (Has(w, "gapU")) { e.hasGapU = true; e.gapU = F(w["gapU"]); }
                    if (Has(w, "gapV")) { e.hasGapV = true; e.gapV = F(w["gapV"]); }
                    if (Has(w, "sode"))
                    {
                        var sd = O(w["sode"]);
                        e.hasSode = true; e.sodeLen = F(sd["len"]); e.sodeDrop = F(sd["drop"]);
                    }
                    var dr = A(w["drop"]);
                    if (dr != null && dr.Count == 2) { e.dropA = F(dr[0]); e.dropB = F(dr[1]); }
                    list.Add(e);
                }
                _walls = list.ToArray();
            }
            return _walls;
        }
    }

    public class Run
    {
        public string name; public int edge; public float s0, s1, seat;
        public bool nagaya, ishigaki; public float s, expose; public int tiers;
    }
    static Run[] _runs;
    public static Run[] Runs
    {
        get
        {
            if (_runs == null)
            {
                var list = new List<Run>();
                foreach (var o in A(D["runs"]))
                {
                    var r = O(o);
                    list.Add(new Run
                    {
                        name = S(r["name"]), edge = (int)F(r["edge"]),
                        s0 = F(r["s0"]), s1 = F(r["s1"]), seat = F(r["seat"]),
                        nagaya = S(r["kind"]) == "Nagaya",
                        ishigaki = Has(r, "base") && S(r["base"]) == "Ishigaki",
                        s = Has(r, "s") ? F(r["s"]) : 0f,
                        expose = Has(r, "expose") ? F(r["expose"]) : 0f,
                        tiers = Has(r, "tiers") ? (int)F(r["tiers"]) : 1
                    });
                }
                _runs = list.ToArray();
            }
            return _runs;
        }
    }

    public static Vector2[] Poly { get { return EdoParcels.Get(ParcelId); } }

    /// <summary>辺 edge の走り s[m] の世界座標。</summary>
    public static Vector2 EdgePt(int edge, float s)
    {
        var P = Poly; int n = P.Length;
        Vector2 a = P[edge % n], b = P[(edge + 1) % n];
        Vector2 d = b - a;
        return a + d / Mathf.Max(1e-5f, d.magnitude) * s;
    }
    public static float EdgeLen(int edge)
    {
        var P = Poly; int n = P.Length;
        return (P[(edge + 1) % n] - P[edge % n]).magnitude;
    }
    static bool PointInPoly(Vector2 p) { return EdoGeom.PIP(Poly, p); }

    /// <summary>辺 e の外向き法線。⛔ 重心では決めない(凹みのある区画で反転する) —
    /// 法線方向へ出た点が区画の外かを内外判定で見る(松平 OutNormal と同じ作法)。</summary>
    public static Vector2 OutNormal(int e)
    {
        var P = Poly; int n = P.Length;
        Vector2 d = (P[(e + 1) % n] - P[e % n]).normalized;
        Vector2 nn = new Vector2(-d.y, d.x);
        Vector2 mid = (P[e % n] + P[(e + 1) % n]) * 0.5f;
        float probe = Mathf.Min(2f, Vector2.Distance(P[e % n], P[(e + 1) % n]) * 0.2f);
        if (PointInPoly(mid + nn * probe)) nn = -nn;
        return nn;
    }

    // ---------------------------------------------------------------- 造成前の地盤(江戸期復元)
    class Dem { public float x0, z0, step; public int nx, nz; public float[] h; public bool[] ok; }
    static Dem _nat;
    static void LoadNat()
    {
        if (_nat != null) return;
        string p = Path.Combine(Root, EdoDemRel);
        if (!File.Exists(p)) throw new Exception("造成前の地盤が無い: " + p);
        var j = EdoMiniJson.Parse(File.ReadAllText(p)) as Dictionary<string, object>;
        var dm = new Dem
        {
            x0 = F(j["x0"]), z0 = F(j["z0"]), step = F(j["step"]),
            nx = (int)F(j["nx"]), nz = (int)F(j["nz"])
        };
        dm.h = new float[dm.nx * dm.nz]; dm.ok = new bool[dm.nx * dm.nz];
        var rows = A(j["h"]);
        for (int iz = 0; iz < dm.nz && iz < rows.Count; iz++)
        {
            var row = A(rows[iz]); if (row == null) continue;
            for (int ix = 0; ix < dm.nx && ix < row.Count; ix++)
            {
                if (row[ix] == null) continue;
                dm.h[iz * dm.nx + ix] = Convert.ToSingle(row[ix]); dm.ok[iz * dm.nx + ix] = true;
            }
        }
        _nat = dm;
    }
    /// <summary>造成前の地盤[m]。無い所は NaN(⛔ live terrain で埋めない — 埋めると
    /// 「造成しない」区間が他家の造成へ寄る)。生成器 `dem_bilinear` と同じ双一次。</summary>
    public static float NaturalY(float x, float z)
    {
        LoadNat();
        float fx = (x - _nat.x0) / _nat.step, fz = (z - _nat.z0) / _nat.step;
        int ix = Mathf.FloorToInt(fx), iz = Mathf.FloorToInt(fz);
        if (ix < 0 || iz < 0 || ix + 1 >= _nat.nx || iz + 1 >= _nat.nz) return float.NaN;
        float tx = fx - ix, tz = fz - iz;
        int i00 = iz * _nat.nx + ix, i10 = i00 + 1, i01 = i00 + _nat.nx, i11 = i01 + 1;
        if (!_nat.ok[i00] || !_nat.ok[i10] || !_nat.ok[i01] || !_nat.ok[i11]) return float.NaN;
        return (_nat.h[i00] * (1 - tx) + _nat.h[i10] * tx) * (1 - tz)
             + (_nat.h[i01] * (1 - tx) + _nat.h[i11] * tx) * tz;
    }

    // ---------------------------------------------------------------- 造成後の地盤(sashizu_lib の移植)
    static bool InParcelUV(float u, float v)
    {
        var w = Grid.W(u, v);
        return PointInPoly(w);
    }

    /// <summary>その (u,v) を覆う段の高さ。無ければ NaN(=造成しない斜面)。区画の外も NaN。</summary>
    public static float DesignY(float u, float v)
    {
        if (!InParcelUV(u, v)) return float.NaN;
        float best = float.NaN;
        foreach (var t in Terraces)
            if (t.In(u, v, 1e-9f)) best = float.IsNaN(best) ? t.y : Mathf.Max(best, t.y);
        return best;
    }

    /// <summary>外周 run(表長屋・練塀)が載っている**表門の辺**のグリッド区間。基壇石垣が受けるので
    /// この区間から法面を出さない。⚠ 表門の開口も run と同じ扱い(門の躯体が受ける)。</summary>
    static List<Vector2> _runEdges;
    static List<Vector2> RunEdges()
    {
        if (_runEdges != null) return _runEdges;
        var g = O(D["gate"]);
        float ken = Grid.ken, sg = F(g["s"]); int ge = (int)F(g["edge"]);
        var outp = new List<Vector2>();
        foreach (var r in Runs)
            if (r.edge == ge) outp.Add(new Vector2((r.s0 - sg) / ken, (r.s1 - sg) / ken));
        float monW = F(O(g["plan"])["monW"]);
        outp.Add(new Vector2(-monW / 2f / ken, monW / 2f / ken));
        _runEdges = outp;
        return outp;
    }

    struct WSeg { public string edge; public float lo, hi; }
    static Dictionary<string, List<WSeg>> _walledCache;
    /// <summary>段 t の四辺のうち土留めが載っている**区間**。⚠ 開口の区間には壁が無いので割って返す
    /// (`sashizu_lib.walled_edges`)。</summary>
    static List<WSeg> WalledEdges(Terrace t)
    {
        if (_walledCache == null) _walledCache = new Dictionary<string, List<WSeg>>();
        List<WSeg> got;
        if (_walledCache.TryGetValue(t.name, out got)) return got;
        var outp = new List<WSeg>();
        Action<string, float, float, bool, float, float> emit = (name, lo, hi, hasGap, g0, g1) =>
        {
            if (!hasGap) { if (hi - lo > 0.4f) outp.Add(new WSeg { edge = name, lo = lo, hi = hi }); return; }
            float a0 = lo, a1 = Mathf.Min(hi, g0);
            if (a1 - a0 > 0.4f) outp.Add(new WSeg { edge = name, lo = a0, hi = a1 });
            float b0 = Mathf.Max(lo, g1), b1 = hi;
            if (b1 - b0 > 0.4f) outp.Add(new WSeg { edge = name, lo = b0, hi = b1 });
        };
        foreach (var w in Walls)
        {
            if (Mathf.Abs(w.coping - t.y) > 0.05f) continue;
            float gh = w.gapHalf;
            if (Mathf.Abs(w.a.x - w.b.x) < 1e-9f)                       // u=const の壁
            {
                float lo = Mathf.Max(Mathf.Min(w.a.y, w.b.y), t.v0), hi = Mathf.Min(Mathf.Max(w.a.y, w.b.y), t.v1);
                bool hg = w.hasGapV; float g0 = w.gapV - gh, g1 = w.gapV + gh;
                if (Mathf.Abs(w.a.x - t.u0) < 1e-6f) emit("u0", lo, hi, hg, g0, g1);
                if (Mathf.Abs(w.a.x - t.u1) < 1e-6f) emit("u1", lo, hi, hg, g0, g1);
            }
            else                                                         // v=const の壁
            {
                float lo = Mathf.Max(Mathf.Min(w.a.x, w.b.x), t.u0), hi = Mathf.Min(Mathf.Max(w.a.x, w.b.x), t.u1);
                bool hg = w.hasGapU; float g0 = w.gapU - gh, g1 = w.gapU + gh;
                if (Mathf.Abs(w.a.y - t.v0) < 1e-6f) emit("v0", lo, hi, hg, g0, g1);
                if (Mathf.Abs(w.a.y - t.v1) < 1e-6f) emit("v1", lo, hi, hg, g0, g1);
            }
        }
        _walledCache[t.name] = outp;
        return outp;
    }
    static bool Walled(List<WSeg> we, string edge, float w)
    {
        if (edge == null) return false;
        foreach (var s in we) if (s.edge == edge && s.lo - 1e-9f <= w && w <= s.hi + 1e-9f) return true;
        return false;
    }

    /// <summary>土の斜路の踏面。無ければ NaN。(`sashizu_lib.ramp_y`)</summary>
    static float RampY(float u, float v)
    {
        var ramps = A(D["ramps"]); if (ramps == null) return float.NaN;
        foreach (var o in ramps)
        {
            var r = O(o); if (!Has(r, "u0")) continue;
            float u0 = Mathf.Min(F(r["u0"]), F(r["u1"])), u1 = Mathf.Max(F(r["u0"]), F(r["u1"]));
            float v0 = Mathf.Min(F(r["v0"]), F(r["v1"])), v1 = Mathf.Max(F(r["v0"]), F(r["v1"]));
            if (!(u0 - 1e-9f <= u && u <= u1 + 1e-9f && v0 - 1e-9f <= v && v <= v1 + 1e-9f)) continue;
            TWall w = null;
            foreach (var x in Walls) if (x.name == S(r["atWall"])) { w = x; break; }
            float drop = F(r["drop"]);
            if (w == null)
            {
                if (!Has(r, "top")) continue;                        // 壁にも付かず top も無い = 地盤を決めない
                float top0 = F(r["top"]);
                float tt = (u1 - u0) > (v1 - v0) ? (u - u0) / Mathf.Max(1e-9f, u1 - u0)
                                                 : (v - v0) / Mathf.Max(1e-9f, v1 - v0);
                if (Has(r, "hiAt") && S(r["hiAt"]) == "lo") tt = 1f - tt;
                return top0 - drop * (1f - Mathf.Clamp01(tt));
            }
            float top = w.coping;
            bool vertW = Mathf.Abs(w.a.x - w.b.x) < 1e-9f;
            bool alongU = (u1 - u0) > (v1 - v0);
            float t2, loA, hiA;
            if (alongU) { t2 = (u - u0) / Mathf.Max(1e-9f, u1 - u0); loA = u0; hiA = u1; }
            else { t2 = (v - v0) / Mathf.Max(1e-9f, v1 - v0); loA = v0; hiA = v1; }
            // 開口の芯(壁が持つ値。無ければ斜路自身の申告)を走行軸へ射影して「上」を決める
            float gc = float.NaN;
            if (vertW) { if (w.hasGapV) gc = w.gapV; else if (Has(r, "gapV")) gc = F(r["gapV"]); }
            else { if (w.hasGapU) gc = w.gapU; else if (Has(r, "gapU")) gc = F(r["gapU"]); }
            if (!float.IsNaN(gc) && Mathf.Abs(hiA - gc) > Mathf.Abs(loA - gc)) t2 = 1f - t2;
            return top - drop * (1f - Mathf.Clamp01(t2));
        }
        return float.NaN;
    }

    /// <summary>石段の掘割(切通し)の踏面。外なら NaN。(`sashizu_lib.stair_y`)</summary>
    static float StairY(float u, float v)
    {
        float K = Grid.ken;
        foreach (var o in A(D["kaidans"]))
        {
            var k = O(o);
            TWall w = null;
            foreach (var x in Walls) if (x.name == S(k["atWall"])) { w = x; break; }
            if (w == null) continue;
            float run = F(k["run"]) / K;
            float hw = F(k["w"]) / 2f / K + 0.25f;
            float t;
            if (Mathf.Abs(w.a.x - w.b.x) < 1e-9f)                       // u=const の壁 → u 方向へ下る
            {
                if (!Has(k, "gapV")) continue;
                if (Mathf.Abs(v - F(k["gapV"])) > hw) continue;
                float probe = DesignY(w.a.x - 0.5f, v);
                float lo = (float.IsNaN(probe) || probe < w.coping) ? -1f : 1f;
                t = (u - w.a.x) / (lo * run);
            }
            else                                                         // v=const の壁 → v 方向へ下る
            {
                if (!Has(k, "gapU")) continue;
                float gu = F(k["gapU"]);
                if (Mathf.Abs(u - gu) > hw) continue;
                float probe = DesignY(gu, w.a.y - 0.5f);
                float lo = (float.IsNaN(probe) || probe < w.coping) ? -1f : 1f;
                t = (v - w.a.y) / (lo * run);
            }
            if (-1e-9f <= t && t <= 1f + 1e-9f) return w.coping - F(k["drop"]) * t;
        }
        return float.NaN;
    }

    /// <summary>**造成後の地盤**(`sashizu_lib.graded_y` の移植)。nat は造成前の地盤。</summary>
    public static float GradedY(float u, float v, float nat)
    {
        if (!InParcelUV(u, v)) return nat;                             // 区画の外は触らない
        float rp = RampY(u, v); if (!float.IsNaN(rp)) return rp;
        float st = StairY(u, v); if (!float.IsNaN(st)) return st;
        float ins = DesignY(u, v); if (!float.IsNaN(ins)) return ins;
        if (float.IsNaN(nat)) return nat;

        float K = Grid.ken, bf = C("batterFill"), bc = C("batterCut"), cap = C("featherCap");
        float g = nat, floor = -1e9f;
        var re = RunEdges();

        // ── 盛土の法面(裾がこぼれる)
        foreach (var t in Terraces)
        {
            if (t.In(u, v, 0f)) continue;
            var we = WalledEdges(t);
            float du, dv; string eu = null, ev = null;
            if (t.rot)
            {
                // ⚠ 回転する段は法面の距離も回転した軸で測る(外接矩形で測ると隅が段の高さで平らになる)
                float r = t.yaw * Mathf.Deg2Rad;
                float lu = Mathf.Sin(r), lv = Mathf.Cos(r), duA = Mathf.Cos(r), dvA = -Mathf.Sin(r);
                float a = (u - t.uc) * lu + (v - t.vc) * lv;
                float b = (u - t.uc) * duA + (v - t.vc) * dvA;
                du = Mathf.Max(0f, Mathf.Abs(a) - t.L / 2f);
                dv = Mathf.Max(0f, Mathf.Abs(b) - t.D / 2f);
                if (du > 1e-9f) eu = a > 0 ? "u1" : "u0";
                if (dv > 1e-9f) ev = b > 0 ? "v1" : "v0";
            }
            else
            {
                if (u < t.u0) { du = t.u0 - u; eu = "u0"; }
                else if (u > t.u1) { du = u - t.u1; eu = "u1"; }
                else du = 0f;
                if (v < t.v0) { dv = t.v0 - v; ev = "v0"; }
                else if (v > t.v1) { dv = v - t.v1; ev = "v1"; }
                else dv = 0f;
            }
            float qv = Mathf.Clamp(v, t.v0, t.v1), qu = Mathf.Clamp(u, t.u0, t.u1);
            if (Walled(we, eu, qv) || Walled(we, ev, qu)) continue;    // 壁が受ける
            if (ev == "v0" && Mathf.Abs(t.v0) < 1e-9f)
            {
                bool onRun = false;
                foreach (var s in re) if (s.x <= qu && qu <= s.y) { onRun = true; break; }
                if (onRun) continue;                                    // 外周 run の基壇石垣が受ける
            }
            float dm = Mathf.Sqrt(du * du + dv * dv) * K;
            if (dm > cap) continue;
            float y2 = t.y - dm / bf;
            if (t.y - cap / bf > nat) continue;                        // cap の内で着地しない = 法面を出さない
            g = Mathf.Max(g, y2);
            floor = Mathf.Max(floor, y2);
        }
        // ── 切土の法面。⚠ 生成器はここで**軸平行**の距離を使う(回転の分岐を持たない)。
        //    合わせないと切盛図と食い違うので、そのまま移す。
        foreach (var t in Terraces)
        {
            if (t.In(u, v, 0f)) continue;
            var we = WalledEdges(t);
            float du, dv; string eu = null, ev = null;
            if (u < t.u0) { du = t.u0 - u; eu = "u0"; }
            else if (u > t.u1) { du = u - t.u1; eu = "u1"; }
            else du = 0f;
            if (v < t.v0) { dv = t.v0 - v; ev = "v0"; }
            else if (v > t.v1) { dv = v - t.v1; ev = "v1"; }
            else dv = 0f;
            float qv = Mathf.Clamp(v, t.v0, t.v1), qu = Mathf.Clamp(u, t.u0, t.u1);
            if (Walled(we, eu, qv) || Walled(we, ev, qu)) continue;
            float dm = Mathf.Sqrt(du * du + dv * dv) * K;
            if (dm > cap) continue;
            if (t.y + cap / bc < nat) continue;
            g = Mathf.Min(g, t.y + dm / bc);
        }
        return Mathf.Max(g, floor);
    }

    /// <summary>世界座標での施工後の地盤。⭕ 奥庭の矩形の中は庭の土工(池床・築山・土手)を重ねる
    /// (生成器 `ground_y`)。⛔ 検査の地盤 `GradedY` は差し替えない。</summary>
    public static float GroundY(float x, float z)
    {
        var g = Grid.L(new Vector2(x, z));
        float nat = NaturalY(x, z);
        var n = NiwaModel;
        if (n != null && n.Inside(g.x, g.y)) return n.Ground(g.x, g.y);
        return GradedY(g.x, g.y, nat);
    }

    // ---------------------------------------------------------------- 群
    /// <summary>
    /// 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 <see cref="EdoYashikiPrefab.Group"/>。
    /// ルートの外側と**辿った先頭の段だけ**を解くので、触っていない段は書き戻しが飛ばせる
    /// (EDO-0282③)。⛔ ここに置き方を書かない(規則21)。
    /// </summary>
    static Transform Group(string child) { return EdoYashikiPrefab.Group(Grp, child); }
    static void Clear(Transform t)
    {
        for (int i = t.childCount - 1; i >= 0; i--)
            UnityEngine.Object.DestroyImmediate(t.GetChild(i).gameObject);
    }
    /// <summary>非冪等の工程の実行済みマーカー(⛔ active にする — `GameObject.Find` は非アクティブを見つけない)。</summary>
    static bool Marked(string stage) { return Group("_markers").Find(stage) != null; }
    static void Mark(string stage, string note)
    {
        var g = Group("_markers");
        var go = new GameObject(stage); go.transform.SetParent(g, false); go.SetActive(true);
        Undo.RegisterCreatedObjectUndo(go, "marker");
        Debug.Log("[Doi] マーカー " + stage + " — " + note);
    }

    /// <summary>据えられなかった部材の控え。⛔ 仮の代用品を置かずここへ積み、報告に出す。</summary>
    static readonly List<string> _wait = new List<string>();
    static void Wait(string s) { if (!_wait.Contains(s)) _wait.Add(s); }

    /// <summary>**指図の欄のうち実装が知らない物**を「未据え付け」へ積む守り。
    ///
    /// ⛔⛔ **指図に欄があるのに実装が読まない、という食い違いは黙って通る。**
    /// 2026-09-06 に護岸の `ishiPick`・荒磯の `asset`・岩島の `assetShoulder` の3か所で起き、
    /// **指図と反対の駒**が据わったまま検図関門を抜けた(見つけたのは人の目)。
    /// ⇒ 据える側が「知っている欄」を名指しし、指図がそれ以外を持っていたらここで鳴らす。
    /// ⚠ **読まない欄も名指しに入れてよい**(石材・確度・註のような、部材では表せない欄)。
    /// 名指しに入れる = 「見て、読まないと決めた」ことの記録であって、⛔ 黙って落とすのとは違う。
    /// ⚠ `_` で始まる欄は註なので数えない。</summary>
    static void AuditKeys(Dictionary<string, object> o, string what, params string[] known)
    {
        if (o == null) return;
        var extra = new List<string>();
        foreach (var k in o.Keys)
        {
            if (string.IsNullOrEmpty(k) || k[0] == '_') continue;
            bool hit = false;
            foreach (var kn in known) if (kn == k) { hit = true; break; }
            if (!hit) extra.Add(k);
        }
        if (extra.Count > 0)
            Wait(what + ": 指図に**実装が読んでいない欄**がある — " + string.Join(", ", extra.ToArray())
               + "(読むか、読まない欄として実装の名指しに加えるか。⛔ 黙って落とさない)");
    }
    static string WaitReport()
    {
        if (_wait.Count == 0) return "未据え付け: 0 件";
        var sb = new System.Text.StringBuilder("未据え付け " + _wait.Count + " 件:");
        foreach (var s in _wait) sb.Append("\n   ⚠ " + s);
        return sb.ToString();
    }
    /// <summary>**未据え付けの一覧**。⚠ `_wait` は「この巡で走らせた Stage が積んだ物」しか持たない —
    /// ドメインリロード後や Stage を走らせていない状態では**空**で、それを「0 件 = 全部据わった」と
    /// 読むと嘘になる(2026-09-06 の普請検査で、指図が沓脱石を足したのに 0 件と出た)。
    /// ⇒ ⭕ **現行の json を読み直し、`asset` / `assetState` を持つ節を全部歩いて組み直す。**</summary>
    /// <summary>`asset` の欄が**機械で引ける単純な呼び出し**か。
    /// ⚠ `bom` の欄は人が読む部材表で「A ／ B」「Ishigaki.* — ピッチ1.80m」のような散文が入る。
    /// ⛔ それを「呼び名が解けない」と数えると、実際は据わっている物が大量に並んで
    /// **本物の欠落が埋もれる**(2026-09-06 に 38 件中 30 件が散文だった)。</summary>
    static bool SimpleApi(string api)
    {
        if (string.IsNullOrEmpty(api) || !api.StartsWith("EdoAssets.")) return false;
        if (api.IndexOf('／') >= 0 || api.IndexOf('＋') >= 0 || api.IndexOf('*') >= 0
         || api.IndexOf('/') >= 0 || api.IndexOf('—') >= 0) return false;
        int a = api.IndexOf('(');
        if (a < 0) return api.IndexOf(' ') < 0;
        int b = api.LastIndexOf(')');
        return b > a && b >= api.TrimEnd().Length - 1;      // 括弧の後ろに文が続かないこと
    }

    [MenuItem(MENU + "未据え付けの一覧")]
    public static void WaitMenu() { Debug.Log("[Doi] " + PendingReport()); }
    public static string PendingReport()
    {
        Reload();
        var hits = new List<string>();
        Action<object, string> walk = null;
        walk = (node, path) =>
        {
            var dd = O(node);
            if (dd != null)
            {
                string nm = Has(dd, "name") ? S(dd["name"]) : null;
                string where = path + (nm != null ? "(" + nm + ")" : "");
                string api0 = (Has(dd, "asset") && dd["asset"] is string) ? S(dd["asset"]) : null;
                string p0 = SimpleApi(api0) ? ResolveNiwaApi(api0, 1) : null;
                if (Has(dd, "assetState"))
                {
                    string st = S(dd["assetState"]);
                    if (st != null && st.IndexOf("未焼成") >= 0)
                    {
                        // ⭕ **申告が古くないかを実物で検める。**指図が「未焼成」と言っていても
                        //   部材方が焼き終えていることがある(指図の改訂漏れ)⇒ それ自体を差し戻す。
                        if (p0 != null && Exists(p0))
                            hits.Add("指図の `assetState` が古い(部材は焼けている): " + where + " → " + p0);
                        else
                            hits.Add("未焼成: " + where + " — " + st);
                    }
                }
                // ⚠ **`asset` は機械で引けるものだけ見る。**`bom` の欄は人が読む部材表で、
                //   「A ／ B」「Ishigaki.* — ピッチ1.80m」のような散文が入る。
                //   ⛔ それを「呼び名が解けない」と数えると、実際は据わっている物が大量に並んで
                //     本物の欠落が埋もれる(2026-09-06 に 38 件中 30 件が散文だった)。
                // ⛔ 解けない = 欠落とは限らない(`ResolveNiwaApi` は庭の語彙しか持たない)。
                //   ⇒ **解けたのに実物が無い**ときだけ鳴らす。
                if (p0 != null && !Exists(p0)) hits.Add("部材が無い: " + where + " → " + p0);
                foreach (var kv in dd)
                    if (!kv.Key.StartsWith("_")) walk(kv.Value, path + "/" + kv.Key);
                return;
            }
            var ll = A(node);
            if (ll != null) for (int i = 0; i < ll.Count; i++) walk(ll[i], path + "[" + i + "]");
        };
        foreach (var kv in D) if (!kv.Key.StartsWith("_")) walk(kv.Value, kv.Key);

        var sb = new System.Text.StringBuilder();
        sb.Append("未据え付け(現行 json を読み直して組み直した): " + hits.Count + " 件");
        foreach (var s in hits) sb.Append("\n   ⚠ " + s);
        if (_wait.Count > 0)
        {
            sb.Append("\n-- この巡の Stage が積んだ控え " + _wait.Count + " 件 --");
            foreach (var s in _wait) sb.Append("\n   ⚠ " + s);
        }
        return sb.ToString();
    }

    static bool Exists(string path)
    { return !string.IsNullOrEmpty(path) && AssetDatabase.LoadAssetAtPath<GameObject>(path) != null; }

    // ---------------------------------------------------------------- 部材の実測(⛔ 呼び寸法で継がない)
    /// <summary>部材の **local** bbox。⛔ 指図の呼び寸法(`komon[].w` / `gate.plan.monW`)で
    /// run を切らない — 部材の実メッシュで切る(CLAUDE.md 規則5)。</summary>
    public struct PartBox { public bool ok; public Vector3 min, max; }
    static Dictionary<string, PartBox> _boxCache;
    static PartBox Box(string path)
    {
        if (_boxCache == null) _boxCache = new Dictionary<string, PartBox>();
        PartBox got;
        if (_boxCache.TryGetValue(path, out got)) return got;
        var pf = string.IsNullOrEmpty(path) ? null : AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var r = new PartBox { ok = false };
        if (pf != null)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
            go.transform.position = Vector3.zero;
            go.transform.rotation = Quaternion.identity;
            go.transform.localScale = Vector3.one;
            var b = EdoBuild.RB(go);
            UnityEngine.Object.DestroyImmediate(go);
            r = new PartBox { ok = true, min = b.min, max = b.max };
        }
        _boxCache[path] = r;
        return r;
    }

    /// <summary>据えた現物の**メッシュの頂点**を軸へ落として範囲を取る。
    /// ⛔ world の AABB で測らない(回転ぶん膨らむ — `qa-and-pitfalls`「寸法と食い込みを
    /// world の AABB で測らない」)。</summary>
    static bool ProjMesh(GameObject go, Vector3 axis, out float lo, out float hi)
    {
        lo = float.MaxValue; hi = float.MinValue;
        axis = axis.normalized;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            var m = mf.sharedMesh; if (m == null) continue;
            var vs = m.vertices; var t = mf.transform;
            for (int i = 0; i < vs.Length; i++)
            {
                float d = Vector3.Dot(t.TransformPoint(vs[i]), axis);
                if (d < lo) lo = d; if (d > hi) hi = d;
            }
        }
        return hi > lo;
    }

    /// <summary>棟の**いちばん高い大棟**が、江戸間格子のどこに載っているかを実測する。
    /// 屋根が棟でいちばん高いので、天端から 0.02m 以内の頂点=最高の帯の大棟の稜線。
    /// <paramref name="acrossIsU"/> = 帯の並ぶ向きが u(=大棟が v に架かる)。</summary>
    static bool TopRidgeGrid(GameObject go, bool acrossIsU, out float lo, out float hi, out float topY)
    {
        lo = 9999f; hi = -9999f; topY = -9999f;
        var mfs = go.GetComponentsInChildren<MeshFilter>();
        foreach (var mf in mfs)
        {
            var m = mf.sharedMesh; if (m == null) continue;
            var vs = m.vertices; var t = mf.transform;
            for (int i = 0; i < vs.Length; i++) { float y = t.TransformPoint(vs[i]).y; if (y > topY) topY = y; }
        }
        if (topY < -9998f) return false;
        var f = Grid;
        foreach (var mf in mfs)
        {
            var m = mf.sharedMesh; if (m == null) continue;
            var vs = m.vertices; var t = mf.transform;
            for (int i = 0; i < vs.Length; i++)
            {
                Vector3 p = t.TransformPoint(vs[i]);
                if (p.y < topY - 0.02f) continue;
                Vector2 uv = f.L(new Vector2(p.x, p.z));
                float a = acrossIsU ? uv.x : uv.y;
                if (a < lo) lo = a; if (a > hi) hi = a;
            }
        }
        return hi >= lo;
    }

    /// <summary>据えた囲いの駒が run の丁場に収まっているかを**実測して**報告する。</summary>
    static void ReportFit(System.Text.StringBuilder sb, GameObject go, int edge, float s0, float s1, string label)
    {
        Vector2 a0 = EdgePt(edge, 0f);
        Vector2 d2 = (EdgePt(edge, 1f) - a0);
        Vector3 ax = new Vector3(d2.x, 0f, d2.y).normalized;
        float lo, hi;
        if (!ProjMesh(go, ax, out lo, out hi)) return;
        float b = Vector3.Dot(new Vector3(a0.x, 0f, a0.y), ax);
        sb.AppendLine("   " + label + " 実測 s[" + (lo - b).ToString("F2") + ".." + (hi - b).ToString("F2")
                    + "] / 指図 s[" + s0.ToString("F2") + ".." + s1.ToString("F2") + "] 差 "
                    + ((lo - b) - s0).ToString("+0.00;-0.00") + " / " + ((hi - b) - s1).ToString("+0.00;-0.00"));
    }

    // ---------------------------------------------------------------- Stage0 退避
    static string BakDir { get { return Path.Combine(Root, "TerrainBackups/doi_20260906_pre_grade"); } }

    [MenuItem(MENU + "0 ハイトマップを退避")]
    public static void Stage0Menu() { Debug.Log("[Doi] " + Stage0_Backup()); }
    public static string Stage0_Backup()
    {
        string bin = Path.Combine(BakDir, "heightmap_full.bin");
        if (File.Exists(bin)) return "退避は既にある(上書きしない): " + bin;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        var H = td.GetHeights(0, 0, hres, hres);
        Directory.CreateDirectory(BakDir);
        using (var w = new BinaryWriter(File.Open(bin, FileMode.Create)))
        {
            w.Write(hres); w.Write(hres);
            for (int z = 0; z < hres; z++) for (int x = 0; x < hres; x++) w.Write(H[z, x]);
        }
        return "退避 " + hres + "x" + hres + " → " + bin;
    }

    // ---------------------------------------------------------------- Stage1 造成
    [MenuItem(MENU + "1 造成(指図の面へ)")]
    public static void Stage1Menu() { Debug.Log("[Doi] " + Stage1_Grade()); }
    public static string Stage1_Grade()
    {
        { var gate = EdoSashizuExport.ReviewGate("doi"); if (gate != null) return gate; }
        Stage0_Backup();
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);

        var P = Poly;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in P)
        {
            mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x);
            mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y);
        }
        int x0 = IX(mnx - 4f), x1 = IX(mxx + 4f), z0 = IZ(mnz - 4f), z1 = IZ(mxz + 4f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0, skip = 0; float cmax = 0f, fmax = 0f; double cutSum = 0, fillSum = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            var p = new Vector2(WX(x0 + x), WZ(z0 + z));
            if (!EdoGeom.PIP(P, p)) continue;                            // ⛔ 敷地の外は一切触らない
            var g = Grid.L(p);
            float nat = NaturalY(p.x, p.y);
            if (float.IsNaN(nat)) { skip++; continue; }                  // 正本が欠けている所は触らない
            float y = GradedY(g.x, g.y, nat);
            if (float.IsNaN(y)) { skip++; continue; }
            float cur = H[z, x] * ts.y + tp.y;
            if (y < cur) { cmax = Mathf.Max(cmax, cur - y); cutSum += cur - y; }
            else { fmax = Mathf.Max(fmax, y - cur); fillSum += y - cur; }
            H[z, x] = (y - tp.y) / ts.y; n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format("造成 cells={0}(正本欠 {1})/ 切土 最大{2:F2}m 体積{3:F0}m³ / 盛土 最大{4:F2}m 体積{5:F0}m³",
                             n, skip, cmax, cutSum * a, fmax, fillSum * a);
    }

    [MenuItem(MENU + "造成を検査 GradeQA")]
    public static void GradeQAMenu() { Debug.Log("[Doi] " + GradeQA()); }
    public static string GradeQA()
    {
        const float TOL = 0.30f;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        var P = Poly;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in P)
        {
            mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x);
            mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y);
        }
        int x0 = IX(mnx - 4f), x1 = IX(mxx + 4f), z0 = IZ(mnz - 4f), z1 = IZ(mxz + 4f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0, bad = 0; float worst = 0f; Vector2 wp = Vector2.zero;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            var p = new Vector2(WX(x0 + x), WZ(z0 + z));
            if (!EdoGeom.PIP(P, p)) continue;
            float want = GroundY(p.x, p.y);
            if (float.IsNaN(want)) continue;
            float cur = H[z, x] * ts.y + tp.y;
            float dif = Mathf.Abs(cur - want);
            n++;
            if (dif > TOL) { bad++; if (dif > worst) { worst = dif; wp = p; } }
        }
        return string.Format("GradeQA: 敷地内 {0} セル / 設計面と {1:F2}m 超ずれ = {2} 件 ({3:P1})。最悪 {4:F2}m at ({5:F1},{6:F1})",
                             n, TOL, bad, n == 0 ? 0f : (float)bad / n, worst, wp.x, wp.y);
    }

    /// <summary>**裏木戸の小壁・瓦の材質を練塀へ明示的に結ぶ。**
    /// ⚠⚠ `Own.Kido(w)` の FBX は材質名 `s_heimap` を名乗るが、**同名で別系統の材質が2つある** —
    /// FBX 自身が抱える `s_heimap`(`_BaseMap` = NULL = 真っ白)と、練塀 `es_dobei/s_hei_center.obj` が
    /// **サブアセットとして**持つ `s_heimap`(`_BaseMap` = `s_hei`)。
    /// ⛔ **名前一致の remap では拾えない** — 一括 remap は .mat の入ったフォルダしか舐めないので、
    /// .obj の中に居る本物に当たらず、FBX 自身の白い方が残る(2026-09-06 の普請検査で実見)。
    /// ⇒ ⭕ **提供元を名指しして結ぶ。**⛔ 新しい .mat を作らない(キットの材質名を保つ規約)。</summary>
    [MenuItem(MENU + "裏木戸の材質を練塀へ明示的に結ぶ")]
    public static void RemapKidoMenu() { Debug.Log("[Doi] " + RemapKido()); }
    public static string RemapKido()
    {
        // 提供元 = 練塀の .obj が抱える `s_heimap`(サブアセット)
        Material donor = null;
        foreach (var a in AssetDatabase.LoadAllAssetsAtPath(EdoAssets.Eg.DobeiCenter))
        {
            var m = a as Material;
            if (m != null && m.name == "s_heimap") { donor = m; break; }
        }
        if (donor == null) return "⚠ 練塀の `s_heimap` が引けない: " + EdoAssets.Eg.DobeiCenter;

        int n = 0; var sb = new System.Text.StringBuilder();
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            string api = Has(k, "asset") ? S(k["asset"]) : null;
            string path = ResolveNiwaApi(api, 1);
            if (path == null || !Exists(path)) continue;
            var imp = AssetImporter.GetAtPath(path) as ModelImporter;
            if (imp == null) continue;
            imp.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "s_heimap"), donor);
            AssetDatabase.WriteImportSettingsIfDirty(path);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            sb.Append(" " + S(k["name"]) + "→" + System.IO.Path.GetFileName(path));
            n++;
        }
        AssetDatabase.SaveAssets();
        return "裏木戸の材質を練塀の `s_heimap`(" + EdoAssets.Eg.DobeiCenter + ")へ結んだ: " + n + " 件" + sb.ToString();
    }

    // ================================================================ 普請検査の常設化(2026-09-06)
    // ⭐ 2026-09-06 の普請検査が **execute_code の使い捨てで** 測った3件を、ここへ常設の関数として
    //   引き取った(規則19「輪に入っていない値は未検査であって合格ではない」)。
    //   ⛔ 使い捨てのまま置くと、次に建て直したとき誰も測らない。

    /// <summary>縁の内外を見る probe の距離[間]。⭐ **指図の `edge_step_check` と同じ 0.06間(0.11m)**。
    /// ⚠⚠ **0.5間(0.909m)にしてはならない** — そこでは設計どおりの法面(盛 1:`batterFill` で 0.61m /
    /// 切 1:`batterCut` で 0.91m)が正当に落ちきっており、そこへ `stepAbsorbMax`(=**段の縁で摺り付け
    /// られる落差**)を当てるのは単位の取り違えになる。法面が在る縁がほぼ全部鳴った
    /// (2026-09-06 指図方の仕分け: 33区間のうち **指図の欠落は 0 件**だった)。</summary>
    const float EdgeProbe = 0.06f;

    /// <summary>グリッド点 (u,v) を土留めが受けているか。⭐ **段に紐づけず幾何で見る。**
    /// ⚠ 段の角では**隣の段の壁**が落差を受けていることがある(2026-09-06 指図方の申し送り④ —
    /// `MonzenE` の u0・v=12.0 は `MonzenE` 自身の壁では受かっておらず、隣の段 `MaeNiwa` の
    /// `TW_MaeS` が同じ線 u=−6 で受けていた。段ごとの `WalledEdges` では見えない)。
    /// `top` は落差の**高い側**の高さ — 土留めの天端はそこに一致する。</summary>
    static bool WalledAt(float u, float v, float top)
    {
        foreach (var w in Walls)
        {
            if (Mathf.Abs(w.coping - top) > 0.12f) continue;
            if (Mathf.Abs(w.a.x - w.b.x) < 1e-6f)                       // u=const の壁
            {
                if (Mathf.Abs(w.a.x - u) > 0.10f) continue;
                float lo = Mathf.Min(w.a.y, w.b.y), hi = Mathf.Max(w.a.y, w.b.y);
                if (v < lo - 1e-6f || v > hi + 1e-6f) continue;
                if (w.hasGapV && Mathf.Abs(v - w.gapV) < w.gapHalf) continue;   // 開口には壁が無い
                return true;
            }
            else                                                         // v=const の壁
            {
                if (Mathf.Abs(w.a.y - v) > 0.10f) continue;
                float lo = Mathf.Min(w.a.x, w.b.x), hi = Mathf.Max(w.a.x, w.b.x);
                if (u < lo - 1e-6f || u > hi + 1e-6f) continue;
                if (w.hasGapU && Mathf.Abs(u - w.gapU) < w.gapHalf) continue;
                return true;
            }
        }
        return false;
    }

    /// <summary>**検査① 段の縁の落差を土留めが受けているか。**
    /// 段の四辺を 0.5間 刻みで歩き、縁の内外 **0.06間(0.11m)** の `GradedY` の差が
    /// `const.stepAbsorbMax` を超えるのに土留めが載っていない区間を出す。
    /// ⚠ **これは実装でなく指図の欠落を捕まえる検査** — 出たら棟梁は壁を発明せず、指図方へ回す。
    /// ⭐ **2026-09-06 に指図方の申し送り4件で直した**(それまで 33区間 出ていたが、仕分けの結果
    /// **指図の欠落 E は 0 件**で、内訳は A 外が別の段 12 / B 区画の外 7 / D 素地=法面 29 / F 角の
    /// 取り違え 1 だった。⛔ **測り方が違うだけの数字を「指図の欠落」として指図方へ回していた**):
    ///   ① **区画の外を除く** — 隣家・道は当家の造成の対象外(`InParcelUV`)
    ///   ② **外が別の段の所を除く** — 段と段の取り合いは `adjacency_check` の担当で、二重に鳴る
    ///   ③ **probe を縁ぎわへ寄せる** — `EdgeProbe` の註
    ///   ④ **角では隣の段の壁も見る** — `WalledAt` の註</summary>
    [MenuItem(MENU + "検査① 段の縁の落差と土留め EdgeStepQA")]
    public static void EdgeStepQAMenu() { Debug.Log("[Doi] " + EdgeStepQA()); }
    public static string EdgeStepQA()
    {
        float lim = C("stepAbsorbMax");
        var sb = new System.Text.StringBuilder();
        int bad = 0, spans = 0, nub = 0;
        // ⭐ **仕分けの内訳を刷る**(規則19 — 落とした点を数えずに 0 件と言わない)。
        //   ⛔ 0 件が「除外を効かせすぎて何も見ていない」から来ていないことは `held`(土留めが
        //      現に受けた点)で分かる — これが 0 なら検査に歯が無い。
        int skipOut = 0, skipOther = 0, held = 0;
        foreach (var t in Terraces)
        {
            if (t.rot) continue;                       // 回転する段(長屋の郭)は別の作法。ここでは見ない
            // 四辺: (edge名, 走る軸の値域, 固定値, 外向き符号)
            string[] en = new string[] { "u0", "u1", "v0", "v1" };
            for (int e = 0; e < 4; e++)
            {
                bool vertEdge = e < 2;                                    // u=const の辺
                float fix = e == 0 ? t.u0 : e == 1 ? t.u1 : e == 2 ? t.v0 : t.v1;
                float sgn = (e == 0 || e == 2) ? -1f : 1f;                // 外へ出る向き
                float q0 = vertEdge ? t.v0 : t.u0, q1 = vertEdge ? t.v1 : t.u1;
                float runLo = float.NaN, runHi = 0f, worst = 0f; string kind = "";
                for (float q = q0; q <= q1 + 1e-6f; q += 0.5f)
                {
                    float ui = vertEdge ? fix - sgn * EdgeProbe : q, vi = vertEdge ? q : fix - sgn * EdgeProbe;
                    float uo = vertEdge ? fix + sgn * EdgeProbe : q, vo = vertEdge ? q : fix + sgn * EdgeProbe;
                    // ① 区画の外は当家の造成の対象外(隣家・道が持つ)— 見ない
                    if (!InParcelUV(uo, vo) || !InParcelUV(ui, vi)) { skipOut++; continue; }
                    var wi = Grid.W(ui, vi); var wo = Grid.W(uo, vo);
                    float yi = GradedY(ui, vi, NaturalY(wi.x, wi.y));
                    float yo = GradedY(uo, vo, NaturalY(wo.x, wo.y));
                    if (float.IsNaN(yi) || float.IsNaN(yo)) continue;
                    // ② 外が別の段 = 段と段の取り合い(`adjacency_check` の担当)。ここで二重に鳴らさない
                    bool onOther = false;
                    foreach (var t2 in Terraces) if (t2 != t && t2.In(uo, vo, 0f)) { onOther = true; break; }
                    if (onOther) { skipOther++; continue; }
                    // ⚠ **落差は両向きに見る。**内が高い = 盛(擁壁が要る)/ 外が高い = 切(法面が立つ)。
                    //   ⛔ 片側だけ見ると、段の背後の 1:1 の切土法面(43°の草の崖)を丸ごと見落とす。
                    float drop = yi - yo;
                    // ④ 壁は幾何で引く(角では隣の段の壁が受ける)。⛔ `Walled(we, ...)` は自分の段しか見ない
                    float pu = vertEdge ? fix : q, pv = vertEdge ? q : fix;
                    bool covered = WalledAt(pu, pv, yi) || WalledAt(pu, pv, yo);
                    // ⭕ **開口の中は斜路・石段が落差を受ける**ので欠陥ではない(⛔ 一律に鳴らさない)
                    if (!float.IsNaN(RampY(uo, vo)) || !float.IsNaN(StairY(uo, vo))
                     || !float.IsNaN(RampY(ui, vi)) || !float.IsNaN(StairY(ui, vi))) covered = true;
                    if (Mathf.Abs(drop) > lim + 1e-4f && covered) held++;
                    bool hurt = Mathf.Abs(drop) > lim + 1e-4f && !covered;
                    if (hurt && (float.IsNaN(runLo) || Mathf.Abs(drop) > Mathf.Abs(worst)))
                        kind = drop > 0f ? "盛" : "切";
                    if (hurt)
                    {
                        if (float.IsNaN(runLo)) { runLo = q; worst = drop; }
                        runHi = q;
                        if (Mathf.Abs(drop) > Mathf.Abs(worst)) worst = drop;
                    }
                    else if (!float.IsNaN(runLo))
                    {
                        if (Emit(sb, t, en[e], vertEdge, fix, runLo, runHi, worst, kind, lim)) bad++; else nub++;
                        runLo = float.NaN;
                    }
                    spans++;
                }
                if (!float.IsNaN(runLo))
                { if (Emit(sb, t, en[e], vertEdge, fix, runLo, runHi, worst, kind, lim)) bad++; else nub++; }
            }
        }
        return "検査① 段の縁 " + spans + " 点 / 土留めの無い落差 " + bad + " 区間"
             + "(ほかに 1間 未満の点だけの当たり " + nub + " 件は隅の刻みの粗さなので落とした)"
             + "\n   仕分け: 区画の外で見ない " + skipOut + " 点 / 外が別の段(`adjacency_check` の担当) "
             + skipOther + " 点 / **土留めが現に受けた " + held + " 点**"
             + (held == 0 ? " ⛔ **0 = 検査に歯が無い**(除外が効きすぎている)" : "")
             + (bad == 0 ? "" : "\n" + sb.ToString()
                + "   ⛔ **これは指図の欠落**(`terraceWalls` に壁が無い)— 実装で壁を発明しない。指図方へ回すこと");
    }

    /// <summary>検査①の1区間を刷る。⚠ **1間 に満たない当たりは落とす** — 0.5間 刻みで段の隅を
    /// 回ると、隣の段の角で1点だけ当たることがあり、実体のある区間と混ざると読めなくなる。</summary>
    static bool Emit(System.Text.StringBuilder sb, Terrace t, string edge, bool vertEdge,
                     float fix, float lo, float hi, float worst, string kind, float lim)
    {
        if (hi - lo < 1.0f) return false;
        sb.AppendLine("  ⚠ " + t.name + " の辺 " + edge + "(" + (vertEdge ? "u" : "v") + "="
            + fix.ToString("F2") + ") " + (vertEdge ? "v" : "u") + "[" + lo.ToString("F1")
            + ".." + hi.ToString("F1") + "] " + (hi - lo).ToString("F1") + "間 / "
            + kind + "の落差 最大 " + Mathf.Abs(worst).ToString("F2")
            + "m > " + lim.ToString("F2") + "m なのに土留めが無い");
        return true;
    }

    /// <summary>**検査② 門・小門の門口を石垣が塞いでいないか。**
    /// `gate` と `komon` の s ± w/2 の帯に、天端が敷居(`sill`)より高い `Ishigaki` の駒の
    /// 実メッシュが入っていないかを見る。⚠ **呼び寸法でなく駒の実メッシュ**で測る(規則5)。</summary>
    [MenuItem(MENU + "検査② 門口を石垣が塞いでいないか KomonIshigakiQA")]
    public static void KomonIshigakiQAMenu() { Debug.Log("[Doi] " + KomonIshigakiQA()); }
    public static string KomonIshigakiQA()
    {
        var grp = GameObject.Find(Grp);
        if (grp == null) return "検査②: 屋敷のルートが無い";
        var ig = grp.transform.Find("Ishigaki");
        if (ig == null) return "検査②: Ishigaki の群が無い(Stage3 が未実行)";
        // 門口の一覧(表門 + 小門)
        var mouths = new List<Vector4>();                  // x=edge, y=s, z=w, w=sill
        var gt = O(D["gate"]);
        mouths.Add(new Vector4(F(gt["edge"]), F(gt["s"]), F(O(gt["plan"])["monW"]), F(gt["sill"])));
        var names = new List<string>(); names.Add("表門");
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            mouths.Add(new Vector4(F(k["edge"]), F(k["s"]), F(k["w"]), F(k["sill"])));
            names.Add(S(k["name"]));
        }
        var sb = new System.Text.StringBuilder(); int bad = 0;
        var all = ig.GetComponentsInChildren<Transform>();
        for (int m = 0; m < mouths.Count; m++)
        {
            int edge = (int)mouths[m].x; float s = mouths[m].y, w = mouths[m].z, sill = mouths[m].w;
            Vector2 pA = EdgePt(edge, s - w / 2f), pB = EdgePt(edge, s + w / 2f);
            Vector2 dir = (pB - pA).normalized;
            for (int i = 0; i < all.Length; i++)
            {
                var tr = all[i];
                if (tr == ig) continue;
                var rs = tr.GetComponents<Renderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds; for (int k2 = 0; k2 < rs.Length; k2++) b.Encapsulate(rs[k2].bounds);
                if (b.max.y <= sill + 0.02f) continue;                 // 敷居より低い駒は塞がない
                // 駒の実メッシュの頂点を辺の s へ射影して重なりを見る
                float lo = float.MaxValue, hi = float.MinValue, dmax = 0f;
                foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
                {
                    var msh = mf.sharedMesh; if (msh == null) continue;
                    var vt = msh.vertices;
                    for (int k2 = 0; k2 < vt.Length; k2 += 7)          // 粗く間引く(頂点は多い)
                    {
                        Vector3 wv = mf.transform.TransformPoint(vt[k2]);
                        Vector2 d2 = new Vector2(wv.x, wv.z) - pA;
                        float ss = Vector2.Dot(d2, dir);
                        float dd = Mathf.Abs(d2.x * dir.y - d2.y * dir.x);
                        if (dd > 3.0f) continue;                       // 辺から離れた駒は関係ない
                        lo = Mathf.Min(lo, ss); hi = Mathf.Max(hi, ss); dmax = Mathf.Max(dmax, dd);
                    }
                }
                if (lo > hi) continue;
                float ov = Mathf.Min(hi, w) - Mathf.Max(lo, 0f);
                if (ov > 0.05f)
                {
                    // ⚠ **2通りある。**① run を割り損ねて基壇が門口へ食い込んだ(実装の欠陥)
                    //   ② run の**中の潜り**で基壇は続いてよいが、`komon[].sill` が基壇の天端より
                    //      低い(**指図の不整合** — 潜りの敷居は基壇の上に載るはず)。
                    bool inRun = false;
                    foreach (var r in Runs)
                        if (r.edge == edge && r.s0 - 1e-6f <= s - w / 2f && s + w / 2f <= r.s1 + 1e-6f) inRun = true;
                    sb.AppendLine("  ⚠ " + names[m] + "(辺" + edge + " s" + s.ToString("F2") + "・門口 "
                        + w.ToString("F2") + "m・敷居 " + sill.ToString("F2") + ")に "
                        + tr.name + " が " + ov.ToString("F2") + "m 入る(天端 " + b.max.y.ToString("F2") + ")"
                        + (inRun
                           ? " ⇒ **run の中の潜り**なので基壇は続いてよい。敷居が基壇の天端より "
                             + (b.max.y - sill).ToString("F2") + "m 低いのが問題 = **指図の不整合**"
                             + "(⛔ 実装で敷居も基壇も動かさない・指図方へ)"
                           : " ⇒ run を割り損ねている = **実装の欠陥**"));
                    bad++;
                }
            }
        }
        return "検査② 門口 " + mouths.Count + " 口 / 石垣が塞ぐ " + bad + " 件"
             + (bad == 0 ? "" : "\n" + sb.ToString());
    }

    /// <summary>**検査③ 石垣の駒が区画の外へ出ていないか。**
    /// 全 `Ishigaki` の駒の**実メッシュの頂点**を `EdoParcels.Get("doi")` の多角形で判定する。
    /// ⚠ OBB でも呼び寸法でもなく頂点で見る(駒は 2.400 × 2.000 で、ピボットが隅にある)。</summary>
    [MenuItem(MENU + "検査③ 石垣が区画外へ出ていないか ParcelOutQA")]
    public static void ParcelOutQAMenu() { Debug.Log("[Doi] " + ParcelOutQA()); }
    public static string ParcelOutQA()
    {
        var grp = GameObject.Find(Grp);
        if (grp == null) return "検査③: 屋敷のルートが無い";
        var ig = grp.transform.Find("Ishigaki");
        if (ig == null) return "検査③: Ishigaki の群が無い(Stage3 が未実行)";
        var P = Poly;
        var sb = new System.Text.StringBuilder(); int bad = 0, tot = 0; float worst = 0f; string wn = "";
        foreach (var tr in ig.GetComponentsInChildren<Transform>())
        {
            if (tr == ig) continue;
            if (tr.GetComponents<Renderer>().Length == 0) continue;
            // ⭕ **門外の踏石は意図した例外** — `komon[].fumiishi` は街路側(区画線の外)に据える物で、
            //   敷居と街路の差を受けるのが役目。⛔ これを「区画外へ出た」として差し戻さない。
            if (tr.name.StartsWith("Fumiishi_")) continue;
            tot++;
            float outMax = 0f;
            foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
            {
                var msh = mf.sharedMesh; if (msh == null) continue;
                var vt = msh.vertices;
                for (int k = 0; k < vt.Length; k += 7)
                {
                    Vector3 wv = mf.transform.TransformPoint(vt[k]);
                    var q = new Vector2(wv.x, wv.z);
                    if (EdoGeom.PIP(P, q)) continue;
                    // 区画の外 — 最寄りの辺までの距離を出す
                    float d = float.MaxValue;
                    for (int e = 0, j = P.Length - 1; e < P.Length; j = e++)
                    {
                        Vector2 a = P[j], b = P[e], ab = b - a;
                        float L2 = Mathf.Max(1e-9f, ab.sqrMagnitude);
                        float t2 = Mathf.Clamp01(Vector2.Dot(q - a, ab) / L2);
                        d = Mathf.Min(d, Vector2.Distance(q, a + ab * t2));
                    }
                    outMax = Mathf.Max(outMax, d);
                }
            }
            if (outMax > 0.40f)
            {
                bad++;
                if (outMax > worst) { worst = outMax; wn = tr.name; }
                if (bad <= 20) sb.AppendLine("  ⚠ " + tr.name + " が区画外へ " + outMax.ToString("F2") + "m");
            }
        }
        return "検査③ 石垣 " + tot + " 駒 / 区画外へ 0.40m 超 = " + bad + " 駒"
             + (bad == 0 ? "" : "(最悪 " + wn + " " + worst.ToString("F2") + "m)\n" + sb.ToString());
    }

    [MenuItem(MENU + "検査①②③ をまとめて走らせる")]
    public static void AllQAMenu()
    { Debug.Log("[Doi]\n" + EdgeStepQA() + "\n" + KomonIshigakiQA() + "\n" + ParcelOutQA()); }

    // ---------------------------------------------------------------- Stage2 外周
    /// <summary>犬走り ≒ 1尺。石垣の法肩と囲いの外面の距離(`const.inubashiri`)。</summary>
    static float Inubashiri { get { return C("inubashiri"); } }

    /// <summary>長屋の駒の**壁の実体**。lo/hi = 走り(local X)、zLo/zHi = 梁間(local Z)。
    /// ⚠ **ピボットは壁の中心ではない** — `es_knagaya` の壁は local Z が −5.37〜−1.07 で、
    /// 全体が −Z 側に寄っている。ピボットを設計の中心へ置くと棟が 3.2m ずれ、
    /// 区画線から 0.30m 控えたつもりが 1.37m 引っ込む(2026-09-06 に踏んだ)。
    /// ⇒ **据えるときは必ず zLo/zHi で寄せ直す**(規則5「部材どうしを中心で合わせない」)。</summary>
    struct NagMod
    {
        public string path; public float lo, hi, zLo, zHi;
        public float W { get { return hi - lo; } }
        public float ZC { get { return (zLo + zHi) * 0.5f; } }
    }
    /// <summary>表長屋の駒の**壁の実体**の走り方向の範囲(ピボット基準)。⛔ 決め打ちしない —
    /// 屋根の反り・鬼・破風は端で出るので壁(wall/namako/dodai)だけで測る(松平 Measure と同じ)。</summary>
    static NagMod Measure(string path)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf == null) return new NagMod { path = path, lo = 0f, hi = 0f };
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero; go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one * ES;
        float mn = float.MaxValue, mx = float.MinValue, zn = float.MaxValue, zx = float.MinValue;
        foreach (var r in go.GetComponentsInChildren<Renderer>())
        {
            string n = r.gameObject.name.ToLower();
            if (!(n.Contains("wall") || n.Contains("namako") || n.Contains("dodai"))) continue;
            mn = Mathf.Min(mn, r.bounds.min.x); mx = Mathf.Max(mx, r.bounds.max.x);
            zn = Mathf.Min(zn, r.bounds.min.z); zx = Mathf.Max(zx, r.bounds.max.z);
        }
        UnityEngine.Object.DestroyImmediate(go);
        return new NagMod { path = path, lo = mn, hi = mx, zLo = zn, zHi = zx };
    }
    /// <summary>edogoyomi の共通倍率(江戸間へ落とす)。</summary>
    public const float ES = 1.818f;

    /// <summary>小門が名指しする部材のパス。⚠ `inRun` を持つ小門(通用門)は
    /// **表長屋の run ごと焼いた一体の部材の中**にあるので、独立した部材は無い(null)。</summary>
    static string KomonAsset(Dictionary<string, object> k)
    {
        if (Has(k, "inRun")) return null;               // run の躯体に彫ってある
        if (!Has(k, "asset")) return null;
        string api = S(k["asset"]);
        if (api != null && api.Contains("Own.Kido(")) return EdoAssets.Own.Kido(F(k["w"]));
        return null;                                     // 解けない名は呼び側が Wait へ積む
    }

    /// <summary>開口が run を切る**実際の幅**。⛔ 呼び寸法(`komon[].w`)で継がない —
    /// 木戸の走り方向の実寸は開口より方立柱2本ぶん広い(規則5・指図 `komon._asset`)。</summary>
    static float KomonSpan(Dictionary<string, object> k)
    {
        string p = KomonAsset(k);
        if (p != null) { var b = Box(p); if (b.ok) return b.max.x - b.min.x; }
        return F(k["w"]);
    }
    /// <summary>表門が run を切る実際の幅(部材の実メッシュ)。</summary>
    static float GateSpan()
    {
        var b = Box(EdoAssets.Own.DoiNagayamon);
        return b.ok ? (b.max.x - b.min.x) : F(O(O(D["gate"])["plan"])["monW"]);
    }

    /// <summary>開口(表門・小門)で run の区間を割る。</summary>
    static List<Vector2> SplitByOpenings(int edge, float s0, float s1)
    {
        var cuts = new List<Vector2>();
        var g = O(D["gate"]);
        if ((int)F(g["edge"]) == edge)
        {
            float gs = F(g["s"]), gw = GateSpan();
            cuts.Add(new Vector2(gs - gw / 2f, gs + gw / 2f));
        }
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            if ((int)F(k["edge"]) != edge) continue;
            float s = F(k["s"]), w = KomonSpan(k);
            // ⚠ **run の中に収まる小門は開口で割らない** — 指図 `leaf.by` が
            //   「表長屋の潜りに含める」= 躯体に彫る潜り戸で、run を切る開口ではない。
            bool inside = false;
            foreach (var r in Runs)
                if (r.edge == edge && r.s0 - 1e-6f <= s - w / 2f && s + w / 2f <= r.s1 + 1e-6f) inside = true;
            if (inside) continue;
            cuts.Add(new Vector2(s - w / 2f, s + w / 2f));
        }
        cuts.Sort((x, y) => x.x.CompareTo(y.x));
        var outp = new List<Vector2>();
        float cur = s0;
        foreach (var c in cuts)
        {
            if (c.y <= s0 || c.x >= s1) continue;
            if (c.x > cur) outp.Add(new Vector2(cur, Mathf.Min(c.x, s1)));
            cur = Mathf.Max(cur, c.y);
        }
        if (cur < s1) outp.Add(new Vector2(cur, s1));
        return outp;
    }

    [MenuItem(MENU + "2 外周(表長屋・練塀・門)")]
    public static void Stage2Menu() { Debug.Log("[Doi] " + Stage2_Perimeter()); }
    public static string Stage2_Perimeter()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder();
        var kak = Group("Kakoi"); Clear(kak);
        var mon = Group("Mon"); Clear(mon);
        // 2026-08-12 の仮置き(EdoSannoKitaBuilder.Stage2_Doi)の残骸。**手組みではなく生成物**なので撤去する。
        {
            var old = Group("").Find("Omotemon");
            if (old != null) { UnityEngine.Object.DestroyImmediate(old.gameObject); sb.AppendLine("旧 Omotemon 群(2026-08-12 仮置き)を撤去"); }
        }

        EdoNishiTameikeBuilder.NaturalMode = false;      // 天端は run の seat で通す

        // ── 練塀(表裏2枚組・段が違うので run ごと)
        int hei = 0;
        foreach (var r in Runs)
        {
            if (r.nagaya) continue;
            Vector2 outw = OutNormal(r.edge);
            int seg = 0;
            foreach (var s in SplitByOpenings(r.edge, r.s0, r.s1))
            {
                Vector2 a = EdgePt(r.edge, s.x), b = EdgePt(r.edge, s.y);
                if ((b - a).magnitude < 1.2f) continue;
                // 犬走り: 石垣の法肩(=区画線)から内へ 0.30m 控える
                a -= outw * Inubashiri; b -= outw * Inubashiri;
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, r.name + (seg > 0 ? "_s" + seg : ""),
                                                false, r.seat, Vector2.zero, -1);
                hei++; seg++;
            }
        }

        // ── 表長屋。⭐ **run 長ちょうどに焼いた一体の部材**(2026-09-04 裁定=案A / 2026-09-06 焼成)。
        //   ⛔ 定尺の駒(`es_knagaya`)を並べない — 端数が必ず残り、継ぎ目が重なるか門へ食い込む。
        //   ピボット = 走りの中心 / 土台の底 / **壁の外面**、見え面 = +Z(街路側)。
        int nag = 0;
        foreach (var r in Runs)
        {
            if (!r.nagaya) continue;
            float L = r.s1 - r.s0;
            // 通用門は独立した部材ではなく、この run の躯体に門口を抜いて焼いてある(指図 `komon._asset`)
            Dictionary<string, object> km = null;
            foreach (var o in A(D["komon"]))
            { var k = O(o); if (Has(k, "inRun") && S(k["inRun"]) == r.name) { km = k; break; } }
            string path = km != null
                ? EdoAssets.Own.NagayaOmoteMon(L, F(km["s"]) - r.s0, false)
                : EdoAssets.Own.NagayaOmote(L);
            if (!Exists(path))
            {
                Wait("表長屋 " + r.name + "(run 長 " + L.ToString("F2") + "m"
                   + (km != null ? " / 門口の芯 run s0 から " + (F(km["s"]) - r.s0).ToString("F2") + "m" : "")
                   + ")の部材が無い: " + path
                   + " → blender --background --python Tools/Blender/build_nagaya_omote.py -- "
                   + L.ToString("0.##"));
                continue;
            }
            Vector2 outw = OutNormal(r.edge);
            // 犬走り: 石垣の法肩(=区画線)から内へ控える。⭕ ピボットが**壁の外面**なので
            //   そのぶんを足し引きしない(⛔ `es_knagaya` のように芯を戻す必要は無い)
            Vector2 mid = EdgePt(r.edge, (r.s0 + r.s1) * 0.5f) - outw * Inubashiri;
            // ⭐ **2026-09-06 に `komon[Tsuyo_Mon].sill` を 21.52 → 21.90 =(run の `seat`)へ改めた。**
            //   ⇒ 通用門込みの本も**ピボットより下へ出る頂点は 0**(`--gate-drop` なしで焼き直し)。
            //   ⛔ **従前の「0.38 の沈み代」の補正は入れない** — 敷居と座が同じ値なので `seat` をそのまま渡す。
            //   ⚠ 街路(区画線の外 21.29)との 0.61m の段差は**門外の踏石**が吸収する(部材は未造)。
            var go = EdoBuild.Place(path, new Vector3(mid.x, r.seat, mid.y), YawFace(outw),
                                    Vector3.one, kak, r.name);
            if (go == null) continue;
            nag++;
            ReportFit(sb, go, r.edge, r.s0, r.s1, "長屋 " + r.name);
        }
        sb.AppendLine("練塀 " + hei + " 区間 / 表長屋 " + nag + " run(run 長ちょうどの一体部材)");

        // ── 表門(長屋門・片番所 格子付・片潜門)。⭐ 2026-09-06 に焼けた `Doi_Nagayamon`
        {
            var g = O(D["gate"]);
            int ge = (int)F(g["edge"]); float gs = F(g["s"]), sill = F(g["sill"]);
            var plan = O(g["plan"]);
            string path = EdoAssets.Own.DoiNagayamon;
            if (!Exists(path))
                Wait("表門の部材が無い: " + path);
            else
            {
                Vector2 outw = OutNormal(ge);
                // ⛔ 在庫の `es_nagayamon` は流用不可(番所と格子が門の中央を跨ぐ左右対称の1メッシュ)。
                // ⭕ 扉(両開きの板戸)は躯体に作り付け — ⛔ 別部材の扉を上から重ねない(指図 `leaf._`)。
                // 門口は部材の走りの中心(`--gate 5.91` = len/2)なので、ピボットを開口の芯 s へ置く。
                Vector2 p = EdgePt(ge, gs) - outw * Inubashiri;
                var go = EdoBuild.Place(path, new Vector3(p.x, sill, p.y), YawFace(outw),
                                        Vector3.one, mon, "Omotemon");
                if (go != null)
                {
                    var bx = Box(path);
                    ReportFit(sb, go, ge, gs - (bx.max.x - bx.min.x) / 2f, gs + (bx.max.x - bx.min.x) / 2f, "表門");
                    float ridge = bx.max.y;
                    if (Mathf.Abs(ridge - F(plan["monH"])) > 0.02f)
                        sb.AppendLine("   ⚠ 表門の棟高: 部材 " + ridge.ToString("F3")
                                    + " / 指図 `gate.plan.monH` " + F(plan["monH"]).ToString("F3")
                                    + " — `gate.plan.assembly` の宣言(棟高は隣接の表長屋の実測に合わせる)"
                                    + "に従えば部材が正。⛔ 実装では決めない(`_pending.monh` → 普請奉行の裁定)");
                }
            }
        }

        // ── 小門。裏木戸だけが独立した部材(通用門は表長屋の run に含まれる)
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            string name = S(k["name"]);
            if (Has(k, "inRun")) { sb.AppendLine("   小門 " + name + " は run " + S(k["inRun"]) + " の躯体に作り付け"); continue; }
            string path = KomonAsset(k);
            if (path == null || !Exists(path))
            {
                Wait("小門 " + name + "(辺" + F(k["edge"]).ToString("0") + " s=" + F(k["s"]).ToString("F1")
                   + " 開口 " + F(k["w"]).ToString("F2") + "m・敷居 " + F(k["sill"]).ToString("F2")
                   + ")の部材が引けない: " + (Has(k, "asset") ? S(k["asset"]) : "(asset 無し)")
                   + " → 指図方・部材方へ差し戻し");
                continue;
            }
            int ke = (int)F(k["edge"]); float ks = F(k["s"]), ksill = F(k["sill"]);
            Vector2 outw = OutNormal(ke);
            Vector2 p = EdgePt(ke, ks) - outw * Inubashiri;
            // ⚠⚠ **厚み方向は芯対称ではない。**部材は練塀の組(`DobeiRun` の表裏2枚)と
            //   同じ厚み(内へ 0.776 / 外へ 0.576)で焼いてあり、**外側の1枚の bbox 中心が
            //   run の線**に乗る(`build_kido.DOBEI_GAP` の註)。実測すると local +Z 側が
            //   0.776 = **内**なので、**+Z を屋敷の内へ向ける**(= −Z が街路)。
            //   ⛔ 壁の芯で合わせない・+Z を外へ向けると練塀と両面 0.20 ずつ食い違う(規則5)。
            var go2 = EdoBuild.Place(path, new Vector3(p.x, ksill, p.y), YawFace(-outw),
                                     Vector3.one, mon, name);
            if (go2 == null) continue;
            float lo2, hi2;
            Vector3 nAx = new Vector3(outw.x, 0f, outw.y);
            if (ProjMesh(go2, nAx, out lo2, out hi2))
            {
                float line = Vector3.Dot(new Vector3(p.x, 0f, p.y), nAx);
                sb.AppendLine("   小門 " + name + " 厚み: run の線から 外 " + (hi2 - line).ToString("F3")
                            + " / 内 " + (line - lo2).ToString("F3")
                            + "(練塀の組は 外 0.576 / 内 0.776)");
            }
            // ⚠⚠ **置いた駒の材質スロットは、部材の submesh が増えても追随しない。**
            //   2026-09-06 普請検査: `Ura_Kido` の slot[2](小壁+瓦)が **NULL でマゼンタ**だった。
            //   FBX の側は正しく `s_heimap` に結ばれていて、**シーンの駒だけが古い override** を
            //   抱えていた(submesh 2 が増える前に置かれた駒)。⇒ 置いた直後に素の部材から結び直す。
            RebindMaterials(go2, path);
            ReportFit(sb, go2, ke, ks - KomonSpan(k) / 2f, ks + KomonSpan(k) / 2f, "小門 " + name);
        }

        // ── 門外の踏石(`komon[].fumiishi`)。⭐ 2026-09-06 に指図が持った(検図方 中-1)。
        //   ⛔ **蹴上・踏面をここで決めない** — 蹴上は `(sill − 街路の地盤) ÷ n` の**従属値**、
        //     踏面は `const.fumi`、幅は門口 `w`。指図 `fumiishi._` の宣言どおり。
        sb.Append(PlaceFumiishi(mon));

        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>置いた駒の材質を、素の部材のスロットから結び直す。
    /// ⚠ **FBX を焼き直して submesh が増えても、既にシーンに在る駒の `m_Materials` は伸びない**
    /// (古い長さのまま残るか、増えた分が null になる)。remap は**アセットにしか効かない**ので
    /// 目視するまで気づけない(2026-09-06 普請検査で `Ura_Kido` の slot[2] が NULL=マゼンタ)。</summary>
    static void RebindMaterials(GameObject go, string modelPath)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
        if (src == null || go == null) return;
        var sr = src.GetComponentsInChildren<MeshRenderer>(true);
        var dr = go.GetComponentsInChildren<MeshRenderer>(true);
        if (sr.Length != dr.Length) return;                    // 構成が違う = 触らない
        for (int i = 0; i < dr.Length; i++)
        {
            var want = sr[i].sharedMaterials;
            var got = dr[i].sharedMaterials;
            bool same = got.Length == want.Length;
            if (same) for (int j = 0; j < got.Length; j++) if (got[j] != want[j]) { same = false; break; }
            if (!same) dr[i].sharedMaterials = want;
        }
    }

    /// <summary>**門外の踏石。**指図 `komon[].fumiishi`(`n` 段・`side`)。
    /// ⭐ 蹴上 = **(敷居 − 街路の地盤) ÷ n** の従属値、踏面 = `const.fumi`、幅 = 門口 `w`。
    /// ⛔ **どれも実装で決め打ちしない**(指図 `fumiishi._` が「ここに書かない」と宣言している)。
    /// ⚠ 石段 `kaidans` と同じ作り(`Own.DanishiStep` を段ごとに天端で据える)。
    /// ⚠ **区画線の外へ出る**が、門外の踏石なので**意図した例外**(`ParcelOutQA` が名で除外)。</summary>
    static string PlaceFumiishi(Transform mon)
    {
        int made = 0, nk = 0; var sb = new System.Text.StringBuilder();
        float tread = C("fumi"), keri = C("keri");
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            if (!Has(k, "fumiishi")) continue;
            var fi = O(k["fumiishi"]);
            int n = (int)F(fi["n"]);
            string nm = S(k["name"]);
            if (n < 1) { Wait("踏石 " + nm + " の `fumiishi.n` が " + n); continue; }
            if (!Exists(EdoAssets.Own.DanishiStep))
            { Wait("段石の部材が無い: " + EdoAssets.Own.DanishiStep); break; }
            int ke = (int)F(k["edge"]); float ks = F(k["s"]), sill = F(k["sill"]), wid = F(k["w"]);
            Vector2 outw = OutNormal(ke);
            Vector2 p = EdgePt(ke, ks);
            // 街路の地盤は**造成前の正本**から採る(生成器 `komon_step_check` と同じ点・同じ源)
            float g9 = NaturalY(p.x, p.y);
            if (float.IsNaN(g9)) { Wait("踏石 " + nm + ": 街路の地盤が引けない"); continue; }
            float dz = sill - g9, rise = dz / n;
            if (rise > keri + 1e-4f)
                Wait("踏石 " + nm + " の蹴上が " + rise.ToString("F3") + "m(上限 `const.keri` "
                   + keri.ToString("F2") + ")— 段数を増やすのは**指図の判断**。指図方へ");
            Vector2 up = -outw;                                  // 登る向き(街路 → 門)
            float yaw = Mathf.Atan2(up.x, up.y) * Mathf.Rad2Deg; // 段石は local +Z = 登る向き
            Vector2 side = new Vector2(up.y, -up.x);
            int across = Mathf.Max(1, Mathf.RoundToInt(wid / C("stepW")));
            float laid = 0f;
            for (int i = 0; i < n; i++)
            {
                // 天端 = 街路 + 蹴上×(i+1)。最上段の天端は敷居に一致する
                float top = g9 + rise * (i + 1);
                // 芯 = 区画線から外へ (n − i − 0.5) × 踏面(最上段が門口に接する)
                Vector2 c0 = p + outw * (tread * (n - i - 0.5f));
                for (int j = 0; j < across; j++)
                {
                    float t = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 c = c0 + side * t;
                    var go = EdoBuild.Place(EdoAssets.Own.DanishiStep, new Vector3(c.x, top, c.y),
                                            yaw, Vector3.one, mon, "Fumiishi_" + nm + "_" + i + "_" + j);
                    if (go == null) continue;
                    var bb = EdoBuild.RB(go);
                    go.transform.position += new Vector3(c.x - bb.center.x, top - bb.max.y, c.y - bb.center.z);
                    var bb2 = EdoBuild.RB(go);
                    laid = Mathf.Max(laid, bb2.size.x > bb2.size.z ? bb2.size.x : bb2.size.z);
                    made++;
                }
            }
            nk++;
            sb.AppendLine("   踏石 " + nm + ": " + n + "段 × " + across + "枚 / 街路 "
                + g9.ToString("F3") + " → 敷居 " + sill.ToString("F3")
                + "(差 " + dz.ToString("F3") + "m)/ 蹴上 " + rise.ToString("F3")
                + " ・踏面 " + tread.ToString("F2") + " ・門口 " + wid.ToString("F2") + "m");
            if (across * C("stepW") < wid - 0.05f)
                Wait("踏石 " + nm + " の実幅 " + (across * C("stepW")).ToString("F2")
                   + "m が門口 " + wid.ToString("F2") + "m に足りない(段石の定尺 "
                   + C("stepW").ToString("F2") + "m の割り)— 部材方・指図方へ");
        }
        return "踏石: " + made + " 枚 / " + nk + " 口\n" + sb.ToString();
    }

    // ---------------------------------------------------------------- Stage3 石垣
    // ⚠⚠ **Castle Wall の実メッシュ**(2026-09-06 実測):
    //     local X ∈ [−2.400, 0.000] / Y ∈ [0, 4.000] / Z ∈ [−2.000, 0.000]。
    //   据えるとき **local +X = 外向き・local +Z = 走り**にしているので、
    //   ⛔ **ピボットは走りの「頭」ではなく「尻」** — 駒は pivot から **−Z へ 2.0m 後ろへ**延びる
    //   (胴も +X でなく −X へ 2.4m = 内側へ入る。こちらは区画の内側なので都合がよい)。
    //   ⇒ 走りの始点にピボットを置くと、駒が **2.0m 手前へはみ出す**。
    //   これが 2026-09-06 の普請検査で「門口を石垣が塞ぐ」「区画外へ 2.19m 出る」として
    //   別々に上がった 2 件の**同一の原因**だった(⛔ 呼び寸法で置いた・規則5)。
    const float IG_RUN = 2.00f;        // Castle Wall の走り方向の実体[m](= 実測の Z 幅)
    const float IG_H = 4.00f;          // 同・高さ[m](ピボットは底)
    const float IG_PITCH_MAX = 1.80f;  // ピッチ上限(重なり 0.20m 以上 = 隙間は原理的に出ない)

    [MenuItem(MENU + "3 石垣(外周の基壇・境界の基壇・郭内の土留め・石段の側)")]
    public static void Stage3Menu() { Debug.Log("[Doi] " + Stage3_Ishigaki()); }
    public static string Stage3_Ishigaki()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        var grp = Group("Ishigaki"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        int made = 0, segs = 0;

        Action<Vector2, Vector2, float, string> lay = (a, b, top, name) =>
        {
            float L = Vector2.Distance(a, b);
            if (L < 0.4f) return;
            Vector2 dir = (b - a) / L;
            Vector2 nn = new Vector2(dir.y, -dir.x);                 // 走り方向から右手 = 外向き候補
            // 外向きは呼び出し側が a→b の向きで与える約束(ローカル +X を外へ・+Z を走りへ)
            float psi = Mathf.Atan2(-nn.y, nn.x) * Mathf.Rad2Deg;
            int N = (L <= IG_RUN) ? 1 : Mathf.CeilToInt((L - IG_RUN) / IG_PITCH_MAX) + 1;
            float pitch = (N > 1) ? (L - IG_RUN) / (N - 1) : 0f;
            // ⚠ 丁場が駒1枚より短いと、どちらの端に合わせても反対側へ食み出す。
            //   ⇒ **中央へ寄せて食み出しを半分ずつに分け**、⛔ 黙って通さず控えへ積む。
            float head = (L <= IG_RUN) ? (L + IG_RUN) / 2f : IG_RUN;
            if (L <= IG_RUN)
                Wait("石垣 " + name + ": 丁場 " + L.ToString("F2") + "m が駒1枚(" + IG_RUN.ToString("F2")
                   + "m)より短い — 中央へ寄せたので両端へ " + ((IG_RUN - L) / 2f).ToString("F2") + "m ずつ食み出す");
            for (int i = 0; i < N; i++)
            {
                // ⭕ **駒はピボットから −Z(走りの手前)へ 2.0m 延びる**ので、頭の駒のピボットは
                //   走りの始点 a ではなく **a + IG_RUN** に置く。⇒ 頭の駒が [a, a+2.0]、
                //   尻の駒が [b−2.0, b] に載り、**両端が run の端にぴたりと合う**。
                //   ⛔ a に置くと run 全体が 2.0m 手前へずれる(門口を塞ぐ・区画外へ出る)。
                Vector2 p = a + dir * (head + pitch * i);
                var go = EdoBuild.Place(EdoAssets.JC.CastleWall, new Vector3(p.x, top - IG_H, p.y),
                                        psi, Vector3.one, grp, name + "_" + made);
                if (go != null) made++;
            }
            segs++;
        };

        // ① 外周 run の基壇(表長屋・練塀の足元)。天端 = run の seat
        foreach (var r in Runs)
        {
            if (!r.ishigaki) continue;
            foreach (var s in SplitByOpenings(r.edge, r.s0, r.s1))
            {
                Vector2 outw = OutNormal(r.edge);
                Vector2 a = EdgePt(r.edge, s.x), b = EdgePt(r.edge, s.y);
                Vector2 dir = (b - a).normalized;
                // ローカル +X を外へ: 走りの向きを外向き法線から決める
                if (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) < 0f) { var t2 = a; a = b; b = t2; }
                lay(a, b, r.seat, "IG_" + r.name);
            }
        }
        // ② 境界の基壇(隣家が持つ辺。塀は隣家の物なので石垣だけ回す)
        foreach (var o in A(D["boundaryPlinth"]))
        {
            var bp = O(o);
            int e = (int)F(bp["edge"]);
            Vector2 outw = OutNormal(e);
            Vector2 a = EdgePt(e, F(bp["s0"])), b = EdgePt(e, F(bp["s1"]));
            Vector2 dir = (b - a).normalized;
            if (Vector2.Dot(new Vector2(dir.y, -dir.x), outw) < 0f) { var t2 = a; a = b; b = t2; }
            lay(a, b, F(bp["coping"]), "BP_e" + e + "_" + F(bp["s0"]).ToString("F0"));
        }
        // ③ 郭内の土留め(14本)。開口の区間には置かない。天端は coping で一直線。
        //    高い側は「壁の外(=低い側)」なので、法線は**高い側から低い側**へ向ける。
        foreach (var w in Walls)
        {
            var f = Grid;
            bool vert = Mathf.Abs(w.a.x - w.b.x) < 1e-9f;
            // 走りに沿って開口で割る(グリッド座標)
            var pieces = new List<Vector2>();
            float t0 = vert ? Mathf.Min(w.a.y, w.b.y) : Mathf.Min(w.a.x, w.b.x);
            float t1 = vert ? Mathf.Max(w.a.y, w.b.y) : Mathf.Max(w.a.x, w.b.x);
            bool hg = vert ? w.hasGapV : w.hasGapU;
            float gc = vert ? w.gapV : w.gapU;
            if (hg && w.gapHalf > 0f)
            {
                if (gc - w.gapHalf > t0) pieces.Add(new Vector2(t0, gc - w.gapHalf));
                if (gc + w.gapHalf < t1) pieces.Add(new Vector2(gc + w.gapHalf, t1));
            }
            else pieces.Add(new Vector2(t0, t1));
            // 低い側の向き(法線)。壁の外側 = 段の外 = 設計面が壁の天端より低い側
            Vector2 mid = vert ? new Vector2(w.a.x, (t0 + t1) * 0.5f) : new Vector2((t0 + t1) * 0.5f, w.a.y);
            Vector2 probe = vert ? new Vector2(1f, 0f) : new Vector2(0f, 1f);
            float yPlus = DesignY(mid.x + probe.x * 0.5f, mid.y + probe.y * 0.5f);
            float yMinus = DesignY(mid.x - probe.x * 0.5f, mid.y - probe.y * 0.5f);
            float lowSign = ((float.IsNaN(yPlus) ? -1e9f : yPlus) < (float.IsNaN(yMinus) ? -1e9f : yMinus)) ? 1f : -1f;
            foreach (var pc in pieces)
            {
                Vector2 ga = vert ? new Vector2(w.a.x, pc.x) : new Vector2(pc.x, w.a.y);
                Vector2 gb = vert ? new Vector2(w.a.x, pc.y) : new Vector2(pc.y, w.a.y);
                Vector2 wa = f.W(ga.x, ga.y), wbp = f.W(gb.x, gb.y);
                Vector2 outg = f.W(mid.x + probe.x * lowSign, mid.y + probe.y * lowSign) - f.W(mid.x, mid.y);
                outg = outg.normalized;
                Vector2 dir = (wbp - wa).normalized;
                if (Vector2.Dot(new Vector2(dir.y, -dir.x), outg) < 0f) { var t2 = wa; wa = wbp; wbp = t2; }
                lay(wa, wbp, w.coping, "TW_" + w.name);
            }
            // 袖石垣(開口の両端で直角に振れて高い側の土を受ける)
            if (w.hasSode && hg && w.gapHalf > 0f)
            {
                Vector2 inDir = vert ? new Vector2(-lowSign, 0f) : new Vector2(0f, -lowSign);  // 高い側へ
                for (int k = 0; k < 2; k++)
                {
                    float q = gc + (k == 0 ? -w.gapHalf : w.gapHalf);
                    Vector2 ga = vert ? new Vector2(w.a.x, q) : new Vector2(q, w.a.y);
                    Vector2 gb = ga + inDir * w.sodeLen;
                    Vector2 wa = f.W(ga.x, ga.y), wbp = f.W(gb.x, gb.y);
                    // 袖は開口の内側を向く
                    Vector2 og = f.W(gc, gc) - f.W(gc, gc);            // 使わない(向きは下で決める)
                    Vector2 dir = (wbp - wa).normalized;
                    Vector2 toGap = (vert ? f.W(w.a.x, gc) : f.W(gc, w.a.y)) - f.W(ga.x, ga.y);
                    if (Vector2.Dot(new Vector2(dir.y, -dir.x), toGap) < 0f) { var t2 = wa; wa = wbp; wbp = t2; }
                    lay(wa, wbp, w.coping, "SODE_" + w.name + "_" + k);
                }
            }
        }
        // ④ 石段の側石垣(flank)。石段の帯の両側に走り run の長さで立てる
        foreach (var o in A(D["kaidans"]))
        {
            var k = O(o);
            if (!Has(k, "flank")) continue;
            var fl = O(k["flank"]);
            TWall w = null;
            foreach (var x in Walls) if (x.name == S(k["atWall"])) { w = x; break; }
            if (w == null) { Wait("石段 " + S(k["name"]) + " の atWall が引けない"); continue; }
            var f = Grid;
            bool vert = Mathf.Abs(w.a.x - w.b.x) < 1e-9f;
            float run = F(fl["run"]) / f.ken, hw = F(k["w"]) / 2f / f.ken;
            float lo = StairDownSign(k, w);
            for (int side = 0; side < 2; side++)
            {
                float off = (side == 0 ? -hw : hw);
                Vector2 ga, gb;
                if (vert)
                {
                    float cv = F(k["gapV"]) + off;
                    ga = new Vector2(w.a.x, cv); gb = new Vector2(w.a.x + lo * run, cv);
                }
                else
                {
                    float cu = F(k["gapU"]) + off;
                    ga = new Vector2(cu, w.a.y); gb = new Vector2(cu, w.a.y + lo * run);
                }
                Vector2 wa = f.W(ga.x, ga.y), wbp = f.W(gb.x, gb.y);
                Vector2 dir = (wbp - wa).normalized;
                Vector2 toStair = (vert ? f.W(w.a.x, F(k["gapV"])) : f.W(F(k["gapU"]), w.a.y)) - wa;
                if (Vector2.Dot(new Vector2(dir.y, -dir.x), toStair) < 0f) { var t2 = wa; wa = wbp; wbp = t2; }
                lay(wa, wbp, w.coping, "FLANK_" + S(k["name"]) + "_" + side);
            }
        }
        sb.AppendLine("石垣: " + made + " 駒 / " + segs + " 区間");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>石段が壁からどちらへ下るか(`sashizu_lib.stair_y` と同じ判定)。</summary>
    static float StairDownSign(Dictionary<string, object> k, TWall w)
    {
        bool vert = Mathf.Abs(w.a.x - w.b.x) < 1e-9f;
        if (vert)
        {
            float v = Has(k, "gapV") ? F(k["gapV"]) : (w.a.y + w.b.y) * 0.5f;
            float probe = DesignY(w.a.x - 0.5f, v);
            return (float.IsNaN(probe) || probe < w.coping) ? -1f : 1f;
        }
        else
        {
            float u = Has(k, "gapU") ? F(k["gapU"]) : (w.a.x + w.b.x) * 0.5f;
            float probe = DesignY(u, w.a.y - 0.5f);
            return (float.IsNaN(probe) || probe < w.coping) ? -1f : 1f;
        }
    }

    // ---------------------------------------------------------------- Stage4 御殿複合
    /// <summary>棟・廊下をこの回転グリッドへ据えるときの yaw。
    /// ⚠ (u,v) と Unity local(+X,+Z) の手系が違うので、local +X=+u / local +Z=−v に置く
    ///   (松平ビルダーの註と同じ。逆にすると棟が鏡像になる)。</summary>
    /// <summary>桁行が u に沿う棟・廊下の yaw。**local +X=+u / local +Z=−v**。原点 local(0,0)=(u0, v1)。
    ///
    /// ⚠⚠ **松平の式 `Atan2(-vx,-vz)` をそのまま持ってきてはいけない。**
    /// 松平の (u,v) は世界に対して**左手系**(det = ux·vz − uz·vx = −1)だが、
    /// **当邸の (u,v) は右手系**(det = +1。指図 `grid._`「(u,v) は世界と同じ向き」)。
    /// Unity の local(+X,+Z) は yaw をどう振っても**左手系**なので、右手系の当邸では
    /// (u, −v) の対に合わせる必要がある。松平の式を当てると **local +X が −v を向き**、
    /// 棟が据え付け点から 90°違う方へ伸びる(2026-09-06 に実際に踏んだ — 表役所が
    /// 設計位置から 18.2m ずれ、7棟すべてが同じだけ回っていた)。
    /// ⛔ 手系を確かめずに他邸の式を移さない。
    ///
    /// 【回転の式(実測で確かめた)】Unity の Y 回転は
    /// <c>local +X → (cosθ, −sinθ) / local +Z → (sinθ, cosθ)</c>(x,z 平面)。
    /// ⇒ **+X を向き d に合わせる yaw は `Atan2(−d.z, d.x)`**、
    ///    **+Z を向き d に合わせる yaw は `Atan2(d.x, d.z)`**。
    /// ⛔ この2つを取り違えると物が 90° 回る(2026-09-06 に棟・長屋・垣で踏んだ)。</summary>
    public static float YawFor(Vector2 xDir) { return Mathf.Atan2(-xDir.y, xDir.x) * Mathf.Rad2Deg; }
    /// <summary>+Z(見え面)を dir へ向ける yaw。</summary>
    public static float YawFace(Vector2 zDir) { return Mathf.Atan2(zDir.x, zDir.y) * Mathf.Rad2Deg; }

    static float YawAlongU() { var f = Grid; return YawFor(new Vector2(f.ux, f.uz)); }
    /// <summary>桁行が v に沿う棟・廊下の yaw。**local +X=+v / local +Z=−u**。原点 local(0,0)=(u1, v0)。</summary>
    static float YawAlongV() { var f = Grid; return YawFor(new Vector2(f.vx, f.vz)); }

    /// <summary>棟・廊下の**据え付け点**。⛔ 検査だけが式を持つとズレるので、
    /// `EdoSashizuExport.CheckScene` はここを呼ぶ(既定の松平式は桁行が u の棟しか合わない —
    /// 当邸は書院・奥・台所の3棟が桁行 v で、既定式だと 3棟が「ずれている」と出る)。</summary>
    public static Vector2 Pivot(Dictionary<string, object> o, string kind)
    {
        var f = Grid;
        float u0 = F(o["u0"]), v0 = F(o["v0"]), u1 = F(o["u1"]), v1 = F(o["v1"]);
        bool alongU = (u1 - u0) >= (v1 - v0);
        // alongU: +X=+u / +Z=+v ⇒ 原点は (u0, v0)
        // alongV: +X=+v / +Z=−u ⇒ 原点は (u1, v0)
        return alongU ? f.W(u0, v0) : f.W(u1, v0);
    }

    [MenuItem(MENU + "4 御殿複合(棟・廊下)")]
    public static void Stage4Menu() { Debug.Log("[Doi] " + Stage4_Goten()); }
    public static string Stage4_Goten()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var grp = Group("Buildings"); Clear(grp);
        var f = Grid;
        float yawU = YawAlongU(), yawV = YawAlongV();
        var sb = new System.Text.StringBuilder();
        int nm = 0, nl = 0;
        float floor = C("gotenFloor");

        foreach (var o in A(D["munes"]))
        {
            var m = O(o);
            string name = S(m["name"]);
            float fu0 = F(m["u0"]), fv0 = F(m["v0"]), fu1 = F(m["u1"]), fv1 = F(m["v1"]);
            // ⚠ **原点は半間でよい。整数を要求するのは外形の間数だけ。**
            //   勝手 Daidokoro は u −15.5..−5.5(10間ちょうどだが原点が半間)で、原点で撥ねると
            //   建たない(2026-09-06 に踏んだ)。部材キットは間数しか見ないので原点は float でよい。
            int ku = Mathf.RoundToInt(fu1 - fu0), kv = Mathf.RoundToInt(fv1 - fv0);
            float y = F(m["y"]);
            bool goten = Has(m, "goten") && Convert.ToBoolean(m["goten"]);

            // 厩は御殿の部材ではない(専用に焼いた `Own.DoiUmaya`)
            if (name == "Umaya") { nm += PlaceUmaya(grp, m, sb) ? 1 : 0; continue; }

            if (Mathf.Abs((fu1 - fu0) - ku) > 0.01f || Mathf.Abs((fv1 - fv0) - kv) > 0.01f)
            { Wait("棟 " + name + ": 外形の間数が整数でない(" + fu0 + "," + fv0 + ")-(" + fu1 + "," + fv1 + ")"); continue; }
            if (ku < 3 || kv < 3) { Wait("棟 " + name + ": 入側一間を四方に回すと身舎が残らない"); continue; }

            // 大棟は桁行に架かる。桁行が v の棟は yawV で据え、原点は (u0, v0)
            bool alongU = ku >= kv;
            int kw = alongU ? ku : kv, kd = alongU ? kv : ku;
            float muneYaw = alongU ? yawU : yawV;
            // ⭐⭐ **屋根は帯割り**(2026-09-06 ユーザー裁定=案C)。身舎を平行な帯に割り、帯ごとに
            //   入母屋を架けて境を谷で受ける。⛔ **梁間10間超を一枚の小屋組で飛ばす入母屋・寄棟は
            //   引かない** — 現存最大の [山脇武家屋敷門]A ですら梁間 4.7m で、**存在しない型**だった。
            //   ⭕ 帯の割り付け(`ws`・`along`・`moyaAcross`・`moyaAlong`)は **指図
            //   `munes[].roof.bands` が正典**(生成器が `const.moyaBand` と足形から書き戻す)。
            //   ⛔ 実装で帯を数え直さない・端数を丸めない。帯に割らない棟は
            //   `const.moyaBand.exempt` に名指しがあるものだけ(厩は上で分岐済み)。
            var rspec = Has(m, "roof") ? O(m["roof"]) : null;
            var bspec = (rspec != null && Has(rspec, "bands")) ? O(rspec["bands"]) : null;
            string roof = null; float roofYaw = 0f; float ridgeYSpec = float.NaN;
            if (bspec == null)
            {
                Wait("棟 " + name + ": 指図 `roof.bands` が無い。⛔ 帯に割らない棟は "
                   + "`const.moyaBand.exempt` に名指しが要る(⛔ 入母屋・寄棟の一枚屋根へ倒さない)— 指図方へ");
            }
            else
            {
                AuditKeys(bspec, "棟 " + name + " の `roof.bands`",
                          "n", "along", "across", "ws", "moyaAcross", "moyaAlong",
                          "eaveH", "ridgeH", "ridgeG", "ridgeY", "at");
                var wsA = A(bspec["ws"]);
                int[] ws = new int[wsA.Count];
                float wsum = 0f;
                for (int i = 0; i < wsA.Count; i++) { ws[i] = Mathf.RoundToInt(F(wsA[i])); wsum += ws[i]; }
                bool alongVRoof = S(bspec["along"]) == "v";
                float spanF = F(bspec["moyaAlong"]), across = F(bspec["moyaAcross"]);
                int spanKen = Mathf.RoundToInt(spanF);
                var mb = O(O(D["const"])["moyaBand"]);
                float iriB = Has(mb, "irikawa") ? F(mb["irikawa"]) : float.NaN;
                float acrossKen = alongVRoof ? (fu1 - fu0) : (fv1 - fv0);
                float alongKen = alongVRoof ? (fv1 - fv0) : (fu1 - fu0);
                if (Has(bspec, "ridgeY"))
                    foreach (var ry in A(bspec["ridgeY"]))
                        if (float.IsNaN(ridgeYSpec) || F(ry) > ridgeYSpec) ridgeYSpec = F(ry);
                if (float.IsNaN(iriB))
                    Wait("指図 `const.moyaBand.irikawa` が無い(⛔ 1間で埋めない)— 指図方へ");
                else if (Mathf.Abs(wsum - across) > 0.01f
                      || Mathf.Abs(across + 2f * iriB - acrossKen) > 0.01f
                      || Mathf.Abs(spanF + 2f * iriB - alongKen) > 0.01f
                      || Mathf.Abs(spanF - spanKen) > 0.01f
                      || (Has(bspec, "n") && Mathf.RoundToInt(F(bspec["n"])) != ws.Length))
                    Wait("棟 " + name + ": 指図の帯の割り付けが足形と合わない(帯の和 " + wsum
                       + " / moyaAcross " + across + " / moyaAlong " + spanF + " / 足形 "
                       + acrossKen + "×" + alongKen + "間・入側 " + iriB + ")— 指図方へ");
                else
                {
                    string wsTag = "";
                    for (int i = 0; i < ws.Length; i++) wsTag += (i > 0 ? "," : "") + ws[i];
                    roof = EdoAssets.Goten.RoofBanded(ws, spanKen, alongVRoof);
                    if (!Exists(roof))
                    {
                        Wait("棟 " + name + " の帯割り屋根が無い: " + roof + " → blender --background "
                           + "--python Tools/Blender/build_goten_roof.py -- banded " + wsTag + " "
                           + spanKen + " --along " + (alongVRoof ? "v" : "u"));
                        roof = null;
                    }
                    // ⚠ 帯割りの部材は**モデル局所 +X = 格子の +u**(部材方の註)。桁行が v の棟は
                    //   棟の local が 90° 回っているので、**世界の yaw が格子の yaw ちょうど**に
                    //   なる差ぶんだけ屋根を戻す。⛔ 「_v だから 90° 足す」ではない。
                    roofYaw = Mathf.DeltaAngle(muneYaw, yawU);
                }
            }
            var w = alongU ? f.W(fu0, fv0) : f.W(fu1, fv0);
            var g = EdoGotenKit.Mune(name, grp, new Vector3(w.x, y, w.y), muneYaw,
                                     kw - 2, kd - 2, 1, floor, roof, iriX: 1,
                                     roofAtFloor: true, roofYaw: roofYaw);
            Undo.RegisterCreatedObjectUndo(g, "mune");
            // 実測で検算 — ⛔ 帯割りは FBX の z=0 が床なので、据え損なうと 3.4m 浮く。
            //   ⚠ 天端は**棟瓦の座とも**の実測で、指図 `ridgeY`(座を除く棟高の絶対値)より座のぶん高い。
            {
                float mlo, mhi;
                if (roof != null && ProjMesh(g, Vector3.up, out mlo, out mhi))
                    sb.AppendLine("  " + name + ": 床Y " + (y + floor).ToString("F3")
                                + "(面 " + y.ToString("F2") + " + gotenFloor " + floor.ToString("F2")
                                + ")/ 実測の天端Y " + mhi.ToString("F3")
                                + (float.IsNaN(ridgeYSpec) ? ""
                                   : "(指図の棟高Y " + ridgeYSpec.ToString("F3") + " + 棟瓦の座 "
                                     + (mhi - ridgeYSpec).ToString("F3") + ")"));
                // ⭐⭐ **帯が指図の位置に載っているかを実測で検める**(規則19)。
                //   ⛔ 帯の並びは立面からは見えない(上から見ないと分からない)ので、目視では捕まらない。
                //   ⚠ 2026-09-07 にこの検査で `Banded_4-5x10ken_v` の**帯が名前と逆に焼かれている**
                //     のを捕まえた(5間帯が across の小さい側に来ていた)。
                if (roof != null && bspec != null && Has(bspec, "at") && Has(bspec, "ridgeH"))
                {
                    var atA = A(bspec["at"]); var rhA = A(bspec["ridgeH"]);
                    float hMax = -9999f;
                    for (int i = 0; i < rhA.Count; i++) if (F(rhA[i]) > hMax) hMax = F(rhA[i]);
                    float eLo = 9999f, eHi = -9999f;
                    for (int i = 0; i < rhA.Count && i < atA.Count; i++)
                        if (Mathf.Abs(F(rhA[i]) - hMax) < 0.01f)
                        { if (F(atA[i]) < eLo) eLo = F(atA[i]); if (F(atA[i]) > eHi) eHi = F(atA[i]); }
                    bool acrossIsU = S(bspec["along"]) == "v";
                    float rlo, rhi, rtop;
                    if (eHi > -9998f && TopRidgeGrid(g, acrossIsU, out rlo, out rhi, out rtop)
                        && (Mathf.Abs(rlo - eLo) > 0.06f || Mathf.Abs(rhi - eHi) > 0.06f))
                        Wait("棟 " + name + ": **いちばん高い帯の大棟が指図の位置に無い** — 実測 "
                           + (acrossIsU ? "u " : "v ") + rlo.ToString("F2") + "‥" + rhi.ToString("F2")
                           + " / 指図 `bands.at` " + eLo.ToString("F2") + "‥" + eHi.ToString("F2")
                           + "(棟高 " + hMax.ToString("F3") + " の帯)。⚠ 部材 " + roof.Substring(roof.LastIndexOf('/') + 1)
                           + " の**帯の並びが名前と逆**でないか(据え付けは格子の yaw ちょうど)— 部材方へ");
                }
            }
            nm++;
            if (!goten) sb.AppendLine("  (" + name + " は goten=false — 独立棟)");
        }

        // 渡廊下・階段廊下・御錠口。両端は棟の壁面へ突き付けるので端の柱通りは落とす
        foreach (var o in A(D["links"]))
        {
            var l = O(o);
            string name = S(l["name"]);
            // ⚠ 原点は半間でよい(L_ImaDaidokoro は u −5.5..−4)。⛔ 原点を丸めると 0.5間 ずれる
            float lu0 = F(l["u0"]), lv0 = F(l["v0"]), lu1 = F(l["u1"]), lv1 = F(l["v1"]);
            float fku = lu1 - lu0, fkv = lv1 - lv0;
            bool alongU = fku >= fkv;
            float span = alongU ? fku : fkv, wide = alongU ? fkv : fku;
            if (Mathf.Abs(wide - 1f) > 0.01f)
                Wait("廊下 " + name + ": 幅が一間でない(" + fku + "×" + fkv + "間)— "
                   + "部材キットの廊下は幅一間しか作れないので一間で据えた。指図方へ差し戻し");
            // ⭐ **端数の間数をそのまま据える**(⛔ 整数へ丸めない — `L_ImaDaidokoro` は 1.5間 で、
            //   2間で据えると居間棟へ 0.909m 食い込む)。屋根は端数の定尺を引く。
            string rk = EdoAssets.Goten.RoofKirizuma(span);
            if (!Exists(rk))
                Wait("廊下 " + name + " の切妻屋根が無い: " + span.ToString("0.##") + "間 → "
                   + "blender --background --python Tools/Blender/build_goten_roof.py -- kirizuma "
                   + span.ToString("0.##"));
            float y = F(l["y"]);
            var w = alongU ? f.W(lu0, lv0) : f.W(lu1, lv0);
            var g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, span,
                                     floor, colStart: false, colEnd: false);
            Undo.RegisterCreatedObjectUndo(g, "roka");
            nl++;
        }
        sb.AppendLine("棟 " + nm + "/" + A(D["munes"]).Count + " 棟、廊下 " + nl + "/" + A(D["links"]).Count + " 本");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>厩(5.5×7間)。⭐ 2026-09-06 に専用部材 `Own.DoiUmaya` が焼けた
    /// (⛔ 従前の `Eg.KnagayaL/R` の2駒は撤去 — 足形も棟高も合っていない)。
    ///
    /// ⚠⚠ **部材の local +X は桁行 7間 = 当図の v 方向**(`bom` の断り・部材方の docstring)。
    /// u と取り違えると 90° 転ぶので、**足形の長辺から向きを引く**(⛔ 定数で決め打ちしない)。</summary>
    static bool PlaceUmaya(Transform grp, Dictionary<string, object> m, System.Text.StringBuilder sb)
    {
        var f = Grid;
        float u0 = F(m["u0"]), v0 = F(m["v0"]), u1 = F(m["u1"]), v1 = F(m["v1"]), y = F(m["y"]);
        string path = EdoAssets.Own.DoiUmaya;
        if (!Exists(path))
        { Wait("厩の部材が無い: " + path + " → blender --background --python Tools/Blender/build_doi_buzai.py -- umaya"); return false; }
        var holder = new GameObject("Umaya"); holder.transform.SetParent(grp, false);
        Undo.RegisterCreatedObjectUndo(holder, "umaya");
        // 群のピボットは棟と同じ据え付け点に置く(⛔ 原点に置くと突き合わせが「ずれている」と出る)
        var pv = Pivot(m, "mune"); holder.transform.position = new Vector3(pv.x, y, pv.y);

        Vector2 uDir = (f.W(1f, 0f) - f.W(0f, 0f)).normalized;
        Vector2 vDir = (f.W(0f, 1f) - f.W(0f, 0f)).normalized;
        bool xAlongV = (v1 - v0) >= (u1 - u0);                 // 長手(桁行)= 部材の +X
        float yaw = YawFor(xAlongV ? vDir : uDir);             // ⛔ `YawFace`(+Z を向ける式)と取り違えない
        Vector2 c0 = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);  // ピボット = footprint の中心・地盤
        var go = EdoBuild.Place(path, new Vector3(c0.x, y, c0.y), yaw, Vector3.one,
                                holder.transform, "Umaya_0");
        if (go == null) return false;
        // 実測で検算 — 桁行が v へ、梁間が u へ伸びているか(⛔ world の AABB で測らない)
        float lo, hi;
        Vector3 vAx = new Vector3(vDir.x, 0f, vDir.y), uAx = new Vector3(uDir.x, 0f, uDir.y);
        var cw = new Vector3(c0.x, 0f, c0.y);
        if (ProjMesh(go, vAx, out lo, out hi))
            sb.AppendLine("  厩: v 方向の実寸 " + (hi - lo).ToString("F3") + "m(桁行 "
                        + ((v1 - v0) * f.ken).ToString("F3") + "m + 軒の出)");
        if (ProjMesh(go, uAx, out lo, out hi))
            sb.AppendLine("      u 方向の実寸 " + (hi - lo).ToString("F3") + "m(梁間 "
                        + ((u1 - u0) * f.ken).ToString("F3") + "m + 軒の出)");
        return true;
    }

    // ---------------------------------------------------------------- Stage5 郭内の造作
    [MenuItem(MENU + "5 郭内(附属屋・井戸・石段・斜路・竹垣)")]
    public static void Stage5Menu() { Debug.Log("[Doi] " + Stage5_Zosaku()); }
    public static string Stage5_Zosaku()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(PlaceService());
        sb.AppendLine(PlaceWells());
        sb.AppendLine(PlaceKaidans());
        sb.AppendLine(PlaceTakegaki());
        sb.Append(WaitReport());
        return sb.ToString();
    }

    static string PlaceService()
    {
        var grp = Group("Fuzoku/Service"); Clear(grp);
        var f = Grid; int made = 0;
        var mc = Measure(EdoAssets.Eg.KnagayaC);
        var ml = Measure(EdoAssets.Eg.KnagayaL);
        var mr = Measure(EdoAssets.Eg.KnagayaR);
        foreach (var o in A(D["service"]))
        {
            var s = O(o);
            string name = S(s["name"]);
            float u0 = F(s["u0"]), v0 = F(s["v0"]), u1 = F(s["u1"]), v1 = F(s["v1"]), y = F(s["y"]);
            Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);

            if (name == "Inari")
            {
                // 稲荷の小祠(1.5間角)。指図 `gardens.G_Okuniwa.yashiro.hokora.asset` が部材を名指し
                string path = EdoAssets.Own.Inari15;
                if (!Exists(path)) { Wait("稲荷の祠の部材が無い: " + path); continue; }
                var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), YawAlongU(), Vector3.one, grp, name);
                if (go != null) { EdoBuild.SeatBottom(go, GroundY(c.x, c.y)); made++; }
                continue;
            }
            if (name.StartsWith("Kura") || name == "Komegura")
            {
                // ⭐ 2026-09-06 に足形どおりに焼けた(`Own.DoiKura`)。⛔ 在庫の `Eg.Kura`
                //   (梁間 3.65間)は当図のどの足形とも一致しないので使わない。
                // ⚠⚠ **割り当ては `service` の矩形で決める**(⛔ 部材方の対応表の文言で据えない)。
                int du = Mathf.RoundToInt(u1 - u0), dv = Mathf.RoundToInt(v1 - v0);
                int hari = Mathf.Min(du, dv), keta = Mathf.Max(du, dv);
                if (Mathf.Abs((u1 - u0) - du) > 0.01f || Mathf.Abs((v1 - v0) - dv) > 0.01f)
                { Wait("蔵 " + name + ": 足形が整数間でない(" + (u1 - u0) + "×" + (v1 - v0) + "間)"); continue; }
                string kpath = EdoAssets.Own.DoiKura(hari, keta);
                if (!Exists(kpath))
                {
                    Wait("蔵 " + name + "(" + S(s["label"]) + " " + hari + "×" + keta + "間)の部材が無い: "
                       + kpath + " → blender --background --python Tools/Blender/build_doi_buzai.py -- kura");
                    continue;
                }
                Vector2 uD = (f.W(1f, 0f) - f.W(0f, 0f)).normalized;
                Vector2 vD = (f.W(0f, 1f) - f.W(0f, 0f)).normalized;
                bool xAlongV = (v1 - v0) >= (u1 - u0);          // 部材の +X = 長手(桁行)
                var kgo = EdoBuild.Place(kpath, new Vector3(c.x, y, c.y), YawFor(xAlongV ? vD : uD),
                                         Vector3.one, grp, name);
                if (kgo != null) made++;
                continue;
            }
            // 家中長屋(回転物。`uc,vc,L,D,yaw` が正典)
            if (!Has(s, "yaw")) { Wait("附属屋 " + name + ": 部材が決まっていない"); continue; }
            float uc = F(s["uc"]), vc = F(s["vc"]), L = F(s["L"]), Dp = F(s["D"]), yaw = F(s["yaw"]);
            // 長軸(桁行)の向き = yaw[度] を v 軸から回した向き
            float r = yaw * Mathf.Deg2Rad;
            Vector2 gDir = new Vector2(Mathf.Sin(r), Mathf.Cos(r));       // (u,v) での長手方向
            Vector2 cW = f.W(uc, vc);
            Vector2 dW = (f.W(uc + gDir.x, vc + gDir.y) - cW).normalized;
            float psi = YawFor(dW);          // 走り = local +X(⛔ +Z を向ける式と取り違えない)
            float Lm = L * f.ken;
            if (mc.W < 0.5f) { Wait("家中長屋の部材が測れない"); continue; }
            int n = Mathf.Max(1, Mathf.CeilToInt(Lm / mc.W - 0.03f));
            var holder = new GameObject(name); holder.transform.SetParent(grp, false);
            Undo.RegisterCreatedObjectUndo(holder, "kachu");
            holder.transform.position = new Vector3(cW.x, y, cW.y);
            Vector2 zW = new Vector2(-dW.y, dW.x);       // local +Z の世界向き
            for (int i = 0; i < n; i++)
            {
                NagMod m = (n == 1) ? mc : (i == 0 ? ml : (i == n - 1 ? mr : mc));
                if (!Exists(m.path)) { Wait("長屋の部材が無い: " + m.path); continue; }
                float sPiece = (n == 1) ? (-m.W * 0.5f) : (-Lm * 0.5f + (Lm - m.W) * i / (float)(n - 1));
                // ⚠ 壁は local Z が −5.37..−1.07 に寄っている。芯を戻さないと棟が 3.2m ずれる
                Vector2 p = cW + dW * (sPiece - m.lo) - zW * m.ZC;
                var go = EdoBuild.Place(m.path, new Vector3(p.x, y, p.y), psi, Vector3.one * ES,
                                        holder.transform, name + "_" + i);
                if (go != null) EdoBuild.SeatBottom(go, y);
            }
            made++;
        }
        return "附属屋: " + made + "/" + A(D["service"]).Count;
    }

    /// <summary>井戸5口。⭐ 2026-09-06 に `Own.DoiIdo` が焼けた。**5口とも同じ部材**で、
    /// ピボット = **井戸の芯・地盤レベル** ⇒ `wells[].u,v` をそのまま使える。
    /// ⛔ `SeatBottom` で据えない — 底 −0.06 は根石が地中へ入る意図。</summary>
    static string PlaceWells()
    {
        var grp = Group("Fuzoku/Ido"); Clear(grp);
        var f = Grid;
        string path = EdoAssets.Own.DoiIdo;
        int n = A(D["wells"]).Count, made = 0;
        if (!Exists(path))
        {
            Wait("井戸の部材が無い: " + path
               + " → blender --background --python Tools/Blender/build_doi_buzai.py -- ido");
            return "井戸: 0/" + n + "(部材待ち)";
        }
        foreach (var o in A(D["wells"]))
        {
            var w = O(o);
            Vector2 p = f.W(F(w["u"]), F(w["v"]));
            var go = EdoBuild.Place(path, new Vector3(p.x, GroundY(p.x, p.y), p.y), YawAlongU(),
                                    Vector3.one, grp, S(w["name"]));
            if (go != null) made++;
        }
        return "井戸: " + made + "/" + n;
    }

    static string PlaceKaidans()
    {
        var grp = Group("Fuzoku/Kaidan"); Clear(grp);
        var f = Grid;
        if (!Exists(EdoAssets.Own.DanishiStep))
        { Wait("段石の部材が無い: " + EdoAssets.Own.DanishiStep); return "石段: 0"; }
        int made = 0, nk = 0;
        foreach (var o in A(D["kaidans"]))
        {
            var k = O(o);
            string nm = S(k["name"]);
            TWall w = null;
            foreach (var x in Walls) if (x.name == S(k["atWall"])) { w = x; break; }
            if (w == null) { Wait("石段 " + nm + ": atWall " + S(k["atWall"]) + " が引けない"); continue; }
            float drop = F(k["drop"]), run = F(k["run"]), wid = F(k["w"]);
            int steps = Mathf.Max(1, (int)F(k["steps"]));
            float y1 = w.coping, y0 = y1 - drop;                       // 天端は土留めの天端(指図が持つ)
            bool vert = Mathf.Abs(w.a.x - w.b.x) < 1e-9f;
            float lo = StairDownSign(k, w);
            // 下る向き(グリッド)。up = 下から上(壁の側)へ
            Vector2 gTop = vert ? new Vector2(w.a.x, F(k["gapV"])) : new Vector2(F(k["gapU"]), w.a.y);
            Vector2 gBot = gTop + (vert ? new Vector2(lo * run / f.ken, 0f) : new Vector2(0f, lo * run / f.ken));
            Vector2 wTop = f.W(gTop.x, gTop.y), wBot = f.W(gBot.x, gBot.y);
            Vector2 up = (wTop - wBot).normalized;
            Vector2 side = new Vector2(up.y, -up.x);
            float yaw = Mathf.Atan2(up.x, up.y) * Mathf.Rad2Deg;
            float rise = drop / steps, tread = run / steps;
            int across = Mathf.Max(1, Mathf.RoundToInt(wid / 1.98f));
            for (int i = 0; i < steps; i++)
            {
                Vector2 c0 = wBot + up * (tread * (i + 0.5f));
                float top = y0 + rise * (i + 1);
                for (int j = 0; j < across; j++)
                {
                    float t = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 c = c0 + side * t;
                    var go = EdoBuild.Place(EdoAssets.Own.DanishiStep, new Vector3(c.x, top, c.y),
                                            yaw, Vector3.one, grp, nm + "_" + i + "_" + j);
                    if (go == null) continue;
                    var bb = EdoBuild.RB(go);
                    go.transform.position += new Vector3(c.x - bb.center.x, top - bb.max.y, c.y - bb.center.z);
                    made++;
                }
            }
            nk++;
        }
        return "石段: " + made + " 枚 / " + nk + " 本";
    }

    /// <summary>垣の run を1本敷く。⭕ **1スパン = 1間ちょうど**なので **1.818 のピッチで突き付ける**。
    /// 端数は **端の駒を run の端に合わせ、内側の継ぎ目で重ねて吸う**
    /// (⛔ 等ピッチで中央寄せにすると端の駒が run の外へ出る — `qa-and-pitfalls`
    /// 「run の端は端の駒を端に合わせる」)。⛔ `SeatBottom` で据えない(根入れ 0.150)。
    /// ⛔ run の +X 端の端柱を省かない(省くと胴縁が宙で終わる)。</summary>
    static int LayGaki(Transform grp, string label, string spanPath, string postPath,
                       Vector2 A0, Vector2 B0, int idx0)
    {
        const float SPAN = 1.818f;
        float len = Vector2.Distance(A0, B0);
        if (len < 0.05f) return 0;
        Vector2 dir = (B0 - A0) / len;
        float yaw = YawFor(dir);                     // 垣の幅は local +X(走り)
        int k = Mathf.Max(1, Mathf.RoundToInt(len / SPAN));
        if (k * SPAN < len - 0.02f) k++;             // 足りないなら1枚足す(⛔ 隙間を作らない)
        int made = 0;
        for (int q = 0; q < k; q++)
        {
            float a = (k == 1) ? (len - SPAN) * 0.5f : (len - SPAN) * q / (float)(k - 1);
            Vector2 c = A0 + dir * (a + SPAN * 0.5f);
            var go = EdoBuild.Place(spanPath, new Vector3(c.x, GroundY(c.x, c.y), c.y), yaw,
                                    Vector3.one, grp, label + "_" + (idx0 + made));
            if (go != null) made++;
        }
        if (Exists(postPath))
        {
            var go = EdoBuild.Place(postPath, new Vector3(B0.x, GroundY(B0.x, B0.y), B0.y), yaw,
                                    Vector3.one, grp, label + "_Post" + (idx0 + made));
            if (go != null) made++;
        }
        return made;
    }

    /// <summary>郭のあいだの見切りの竹垣(`rails`)。⭐ 2026-09-06 の指図の改訂で
    /// **丈 `h` が入った**(0.9)ので据えられる。⛔ 焼いていない丈へ寄せない。</summary>
    static string PlaceTakegaki()
    {
        var grp = Group("Fuzoku/Takegaki"); Clear(grp);
        var rails = A(D["rails"]);
        if (rails == null || rails.Count == 0) return "竹垣: 指図に rails が無い";
        var f = Grid;
        int made = 0, done = 0;
        foreach (var o in rails)
        {
            var r = O(o);
            string nm = S(r["name"]);
            if (!Has(r, "h"))
            {
                Wait("竹垣 " + nm + ": 指図に丈 `h` が無い(四つ目垣は丈ごとに胴縁の段数が違う)"
                   + " → 指図方へ差し戻し");
                continue;
            }
            float h = F(r["h"]);
            string span = EdoAssets.Own.YotsumeGaki(h), post = EdoAssets.Own.YotsumeGakiPost(h);
            if (!Exists(span))
            {
                Wait("竹垣 " + nm + "(四つ目垣 h" + h.ToString("F1") + ")の部材が無い: " + span
                   + "(⛔ 焼いていない丈へ寄せない)");
                continue;
            }
            var pts = A(r["pts"]);
            if (pts == null || pts.Count < 2) { Wait("竹垣 " + nm + ": `pts` が読めない"); continue; }
            int idx = 0;
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                var a = A(pts[i]); var b = A(pts[i + 1]);
                Vector2 A0 = f.W(F(a[0]), F(a[1])), B0 = f.W(F(b[0]), F(b[1]));
                int n = LayGaki(grp, nm, span, post, A0, B0, idx);
                idx += n; made += n;
            }
            done++;
        }
        return "竹垣: " + made + " 枚 / " + done + "/" + rails.Count + " 本";
    }

    // ---------------------------------------------------------------- 通し
    [MenuItem(MENU + "S1→S6 を通す")]
    public static void RunAllMenu() { Debug.Log("[Doi] " + RunAll()); }
    public static string RunAll()
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("[0] " + Stage0_Backup());
        sb.AppendLine("[1] " + Stage1_Grade());
        sb.AppendLine("[2] " + Stage2_Perimeter());
        sb.AppendLine("[3] " + Stage3_Ishigaki());
        sb.AppendLine("[4] " + Stage4_Goten());
        sb.AppendLine("[5] " + Stage5_Zosaku());
        sb.AppendLine("[6] " + Stage6_Niwa());
        return sb.ToString();
    }
}
