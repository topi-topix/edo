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
    static Transform Group(string child)
    {
        var r = GameObject.Find(Grp);
        if (r == null) { r = new GameObject(Grp); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);      // プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var go = new GameObject(seg);
                Undo.RegisterCreatedObjectUndo(go, "grp");
                go.transform.SetParent(cur, false);
                nx = go.transform;
            }
            cur = nx;
        }
        return cur;
    }
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
    static string WaitReport()
    {
        if (_wait.Count == 0) return "未据え付け: 0 件";
        var sb = new System.Text.StringBuilder("未据え付け " + _wait.Count + " 件:");
        foreach (var s in _wait) sb.Append("\n   ⚠ " + s);
        return sb.ToString();
    }
    [MenuItem(MENU + "未据え付けの一覧")]
    public static void WaitMenu() { Debug.Log("[Doi] " + WaitReport()); }

    static bool Exists(string path)
    { return !string.IsNullOrEmpty(path) && AssetDatabase.LoadAssetAtPath<GameObject>(path) != null; }

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

    /// <summary>開口(表門・小門)で run の区間を割る。</summary>
    static List<Vector2> SplitByOpenings(int edge, float s0, float s1)
    {
        var cuts = new List<Vector2>();
        var g = O(D["gate"]);
        if ((int)F(g["edge"]) == edge)
        {
            float gs = F(g["s"]), gw = F(O(g["plan"])["monW"]);
            cuts.Add(new Vector2(gs - gw / 2f, gs + gw / 2f));
        }
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            if ((int)F(k["edge"]) != edge) continue;
            float s = F(k["s"]), w = F(k["w"]);
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

        // ── 表長屋(edogoyomi es_knagaya。⛔ ピッチを決め打ちせず壁の実体を測る)
        var mc = Measure(EdoAssets.Eg.KnagayaC);
        var ml = Measure(EdoAssets.Eg.KnagayaL);
        var mr = Measure(EdoAssets.Eg.KnagayaR);
        int nag = 0; float worstOver = 0f; string worstRun = "";
        if (mc.W < 0.5f) Wait("表長屋の部材が測れない: " + EdoAssets.Eg.KnagayaC);
        else
        {
            foreach (var r in Runs)
            {
                if (!r.nagaya) continue;
                Vector2 outw = OutNormal(r.edge);
                float psi = YawFace(outw);                       // 見え面 +Z を外へ
                // ⚠ **見え面を外へ向けた時点で、部材の走り(local +X)の向きは選べない。**
                //   +X = (outw.y, −outw.x) なので、辺の +s と同じ向きか逆かは辺ごとに違う。
                //   ⛔ 「+X は +s」と決め打ちすると駒が run の外へ並ぶ(2026-09-06 に踏んだ)。
                Vector2 dEdge = (EdgePt(r.edge, 1f) - EdgePt(r.edge, 0f)).normalized;
                Vector2 xDir = new Vector2(outw.y, -outw.x);
                float sgn = Vector2.Dot(xDir, dEdge) >= 0f ? 1f : -1f;
                float L = r.s1 - r.s0;
                // ⚠ 端数は**重ねて**吸う(⛔ 穴を作らない — メモリ「門と塀の閉じは隙間>めり込み」)。
                //   3% までの不足は継ぎ目の微小な空きとして許す(軒の出が覆う)。
                int n = Mathf.Max(1, Mathf.CeilToInt(L / mc.W - 0.03f));
                // 継ぎ目の重なり(報告用)。⛔ 据え位置は下の a で決める
                float over = n > 1 ? mc.W - (L - mc.W) / (n - 1) : 0f;
                if (n > 1 && over > worstOver) { worstOver = over; worstRun = r.name; }
                for (int i = 0; i < n; i++)
                {
                    // ⚠ 妻(破風・鬼)は `l` が local −X 側・`r` が +X 側にある(実測)。
                    //   走りが −s を向く辺では **l と r が入れ替わる** — でないと妻が run の中で向き合う。
                    bool lowEnd = (i == 0), hiEnd = (i == n - 1);
                    NagMod m = mc;
                    if (n > 1)
                    {
                        if (sgn > 0f) { if (lowEnd) m = ml; else if (hiEnd) m = mr; }
                        else { if (lowEnd) m = mr; else if (hiEnd) m = ml; }
                    }
                    if (!Exists(m.path)) { Wait("表長屋の部材が無い: " + m.path); continue; }
                    // 駒の**壁の実体**が s ∈ [a, a+駒幅] を覆うようにピボットを置く。
                    // ⚠ **端の駒は run の端にぴたりと合わせる**(⛔ 等ピッチで中央寄せにすると
                    //   端の駒が (駒幅−ピッチ)/2 だけ run の外へ出て、門の開口へ 0.71m 食い込んだ
                    //   — 2026-09-06 実測)。余りは内側の継ぎ目で重ねて吸う。
                    float a = (n == 1) ? (r.s0 + (L - m.W) * 0.5f)
                                       : (r.s0 + (L - m.W) * i / (float)(n - 1));
                    float sPivot = (sgn > 0f) ? (a - m.lo) : (a + m.hi);
                    // ⚠ **壁の外面**を区画線から犬走り 0.30m 控えた所へ寄せる。
                    //   ピボットは壁の面ではない(local Z −5.37..−1.07)ので、その分を戻す。
                    Vector2 p = EdgePt(r.edge, Mathf.Clamp(sPivot, -20f, EdgeLen(r.edge) + 20f))
                              - outw * (Inubashiri + m.zHi);
                    var go = EdoBuild.Place(m.path, new Vector3(p.x, r.seat, p.y), psi,
                                            Vector3.one * ES, kak, r.name + "_" + i);
                    if (go == null) continue;
                    EdoBuild.SeatBottom(go, r.seat - 0.10f);
                    nag++;
                }
            }
        }
        sb.AppendLine("練塀 " + hei + " 区間 / 表長屋 " + nag + " 駒(駒幅 " + mc.W.ToString("F3") + "m)");
        if (worstOver > 0.05f)
            sb.AppendLine("⚠ 表長屋の継ぎ目の重なり 最大 " + worstOver.ToString("F2") + "m(" + worstRun
                        + ")— run 長が駒幅 " + mc.W.ToString("F3") + "m の整数倍でない。⛔ 発明しない(裁定へ)");

        // ── 表門(長屋門・片番所)。**部材は新造待ち**(`_pending.monsun` / bom「(新造)Doi_Nagayamon」)
        {
            var g = O(D["gate"]);
            string asset = S(g["asset"]);
            int ge = (int)F(g["edge"]); float gs = F(g["s"]), sill = F(g["sill"]);
            var plan = O(g["plan"]);
            // ⛔ 在庫の `es_nagayamon` は使えない(番所と格子が門の中央を跨ぐ左右対称の1メッシュ。
            //    2026-08-23 在庫方)。⛔ 代用品を置かない。
            Wait("表門(長屋門・片番所・格子付・片潜門)桁行 " + F(plan["monW"]).ToString("F2")
               + "m・棟高 " + F(plan["monH"]).ToString("F2") + "m・敷居 " + sill.ToString("F2")
               + " 辺" + ge + " s=" + gs.ToString("F1")
               + " — 部材が無い(指図 `bom`「(新造)Doi_Nagayamon」/ `_pending.monsun` は桁行の確定待ち)。"
               + "在庫の " + asset + " は流用不可");
        }

        // ── 小門(裏木戸・通用門)。⚠ 指図に `asset`/`api` が無いので部材を選べない(⛔ 発明しない)
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            if (Has(k, "asset")) continue;
            Wait("小門 " + S(k["name"]) + "(辺" + F(k["edge"]).ToString("0") + " s=" + F(k["s"]).ToString("F1")
               + " 幅 " + F(k["w"]).ToString("F2") + "m・敷居 " + F(k["sill"]).ToString("F2")
               + ")— 指図に部材(`komon[].asset`)が無い。⛔ 在庫から勝手に選ばない → 指図方へ差し戻し");
        }

        sb.Append(WaitReport());
        return sb.ToString();
    }

    // ---------------------------------------------------------------- Stage3 石垣
    const float IG_RUN = 2.00f;        // Castle Wall の走り方向の実体[m]
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
            for (int i = 0; i < N; i++)
            {
                Vector2 p = a + dir * (pitch * i);
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

            // 厩は御殿の部材ではない(指図 bom「厩: Eg.KnagayaL/R・6間なので l+r ペア」)
            if (name == "Umaya") { nm += PlaceUmaya(grp, m, sb) ? 1 : 0; continue; }

            if (Mathf.Abs((fu1 - fu0) - ku) > 0.01f || Mathf.Abs((fv1 - fv0) - kv) > 0.01f)
            { Wait("棟 " + name + ": 外形の間数が整数でない(" + fu0 + "," + fv0 + ")-(" + fu1 + "," + fv1 + ")"); continue; }
            if (ku < 3 || kv < 3) { Wait("棟 " + name + ": 入側一間を四方に回すと身舎が残らない"); continue; }

            // 大棟は桁行に架かる。桁行が v の棟は yawV で据え、原点は (u0, v0)
            bool alongU = ku >= kv;
            int kw = alongU ? ku : kv, kd = alongU ? kv : ku;
            string roof = EdoAssets.Goten.RoofIrimoya_(kw, kd);
            if (!Exists(roof))
            {
                Wait("棟 " + name + " の入母屋屋根が無い: " + kw + "x" + kd + "間 → "
                   + "blender --background --python Tools/Blender/build_goten_roof.py -- "
                   + (kw * f.ken).ToString("0.###") + " " + (kd * f.ken).ToString("0.###")
                   + " Goten_Roof_Irimoya_" + kw + "x" + kd + "ken");
                roof = null;
            }
            var w = alongU ? f.W(fu0, fv0) : f.W(fu1, fv0);
            var g = EdoGotenKit.Mune(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV,
                                     kw - 2, kd - 2, 1, floor, roof, iriX: 1);
            Undo.RegisterCreatedObjectUndo(g, "mune");
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
            int n = Mathf.Max(1, Mathf.RoundToInt(span));
            if (Mathf.Abs(wide - 1f) > 0.01f)
                Wait("廊下 " + name + ": 幅が一間でない(" + fku + "×" + fkv + "間)— "
                   + "部材キットの廊下は幅一間しか作れないので一間で据えた。指図方へ差し戻し");
            if (Mathf.Abs(span - n) > 0.01f)
                Wait("廊下 " + name + ": 長さが整数間でない(" + span.ToString("0.##") + "間)— "
                   + n + "間で据えた(差 " + (n - span).ToString("0.##") + "間)。指図方へ差し戻し");
            float y = F(l["y"]);
            var w = alongU ? f.W(lu0, lv0) : f.W(lu1, lv0);
            var g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, n,
                                     floor, colStart: false, colEnd: false);
            Undo.RegisterCreatedObjectUndo(g, "roka");
            nl++;
        }
        sb.AppendLine("棟 " + nm + "/" + A(D["munes"]).Count + " 棟、廊下 " + nl + "/" + A(D["links"]).Count + " 本");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>厩(5.5×7間)。指図 bom が `Eg.KnagayaL/R` を名指ししている。</summary>
    static bool PlaceUmaya(Transform grp, Dictionary<string, object> m, System.Text.StringBuilder sb)
    {
        var f = Grid;
        float u0 = F(m["u0"]), v0 = F(m["v0"]), u1 = F(m["u1"]), v1 = F(m["v1"]), y = F(m["y"]);
        var ml = Measure(EdoAssets.Eg.KnagayaL);
        var mr = Measure(EdoAssets.Eg.KnagayaR);
        if (!Exists(EdoAssets.Eg.KnagayaL) || !Exists(EdoAssets.Eg.KnagayaR) || ml.W < 0.5f)
        { Wait("厩の部材が無い: " + EdoAssets.Eg.KnagayaL); return false; }
        // 桁行は長手(v: 7間 = 12.73m)。l+r の2駒で覆う
        bool alongU = (u1 - u0) >= (v1 - v0);
        float L = (alongU ? (u1 - u0) : (v1 - v0)) * f.ken;
        Vector2 c0 = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
        Vector2 dir = alongU ? (f.W(u1, (v0 + v1) * 0.5f) - f.W(u0, (v0 + v1) * 0.5f)).normalized
                             : (f.W((u0 + u1) * 0.5f, v1) - f.W((u0 + u1) * 0.5f, v0)).normalized;
        // 長屋の駒は**走りが local +X**。⛔ `YawFace`(+Z を向ける式)と取り違えると 90° 回る
        float yaw = YawFor(dir);
        var mods = new NagMod[] { ml, mr };
        int n = mods.Length;
        var holder = new GameObject("Umaya"); holder.transform.SetParent(grp, false);
        Undo.RegisterCreatedObjectUndo(holder, "umaya");
        // 群のピボットは棟と同じ据え付け点に置く(⛔ 原点に置くと突き合わせが「ずれている」と出る)
        var pv = Pivot(m, "mune"); holder.transform.position = new Vector3(pv.x, y, pv.y);
        // 梁間の向き(local +Z の世界向き)。⚠ 壁は −Z 側に寄っているので芯を戻す
        Vector2 zDir = new Vector2(-dir.y, dir.x);
        for (int i = 0; i < n; i++)
        {
            var mm = mods[i];
            float sPiece = (n == 1) ? (-mm.W * 0.5f) : (-L * 0.5f + (L - mm.W) * i / (float)(n - 1));
            Vector2 p = c0 + dir * (sPiece - mm.lo) - zDir * mm.ZC;
            var go = EdoBuild.Place(mm.path, new Vector3(p.x, y, p.y), yaw, Vector3.one * ES,
                                    holder.transform, "Umaya_" + i);
            if (go != null) EdoBuild.SeatBottom(go, y);
        }
        sb.AppendLine("  厩: 2駒(" + EdoAssets.Eg.KnagayaL + " / R)");
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
            if (name.StartsWith("Kura"))
            {
                // ⛔ 御土蔵は据えない — 部材の足形が合っていない(`_pending.kurabuzai`:
                //    等倍 3.43×3.65間 に対して指図は 3×8間 / 3×3間。並べるのか伸ばすのかが未決)
                Wait("御土蔵 " + name + "(" + S(s["label"]) + " " + (u1 - u0).ToString("0.#") + "×"
                   + (v1 - v0).ToString("0.#") + "間)— 部材の足形が合わない(`_pending.kurabuzai`)。"
                   + "等倍 `EdoAssets.Eg.Kura` は 3.43×3.65間 — 並べ方が未決なので据えない");
                continue;
            }
            if (name == "Komegura")
            {
                Wait("御米蔵 Komegura(3×8間)— 同上(`_pending.kurabuzai`)。土蔵の部材の足形が未決");
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

    static string PlaceWells()
    {
        var grp = Group("Fuzoku/Ido"); Clear(grp);
        // ⛔ 井戸の部材は在庫に無い(`_pending.ido`: 石枠 1.3×0.35×1.3 + 木柱2 + 梁 + 釣瓶 の合成)。
        //    ⛔ 代用品を置かない。
        int n = 0;
        foreach (var o in A(D["wells"])) { n++; }
        Wait("井戸 " + n + " 口(勝手・門前・表役所・奥向・奥庭)— 部材が在庫に無い(`_pending.ido`)。"
           + "石枠 1.3×0.35×1.3 + 木柱2 + 梁 + 釣瓶 の合成部材を部材方が起こす必要がある");
        return "井戸: 0/" + n + "(部材待ち)";
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

    /// <summary>郭のあいだの見切りの竹垣(`rails`)。⚠ 指図は**丈を持たない** — 焼いてある四つ目垣は
    /// 丈で部材が変わる(胴縁の段数が違う)ので、勝手に寄せずに一覧へ出す。</summary>
    static string PlaceTakegaki()
    {
        var grp = Group("Fuzoku/Takegaki"); Clear(grp);
        var rails = A(D["rails"]);
        if (rails == null || rails.Count == 0) return "竹垣: 指図に rails が無い";
        Wait("竹垣(見切り)" + rails.Count + " 本 — 指図 `rails[]` に**丈 `h` が無い**。"
           + "四つ目垣の部材は丈ごとに胴縁の段数が違う(`EdoAssets.Own.YotsumeGaki(h)` は 0.6/0.9/1.2)ので"
           + "近い丈へ寄せられない → 指図方へ差し戻し(書き起こし漏れ)");
        return "竹垣: 0/" + rails.Count + "(丈の指定待ち)";
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
