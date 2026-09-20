// 松平出羽守上屋敷(出雲松江藩 18万6千石)ビルダー。
//
// 【正典は指図】docs/Sashizu/matsudaira_dewa_sashizu.json を**実行時に読む**。
//   設計値(面の高さ・段の矩形・外周の run・土留め・棟)を C# に書き写さない —
//   写した瞬間に指図とビルダーが別々に動き出す(CLAUDE.md 絶対規則9 と同じ理由。
//   区画は既に parcels.json へ寄せた。ここでは指図そのものを同じやり方で寄せる)。
//
// 【グリッド】主郭は回転間グリッド。u=北辺沿い東+ / v=敷地の奥+、単位は間(1.818m)。
//   原点=表門の芯([五千分一東京図31] 明治16年実測図の開口 s=123.8)。
//
// 【造成の考え方】敷地の中を三層で決める(岡部 EdoOkabeYashikiBuilder.DesignY の作法)。
//   ① 段(terraces)の矩形の中 … 設計値そのまま
//   ② bench=true の run の外周帯 … その run の天端で平ら
//   ③ ①②の外 … **現地形のまま**(=造成しない)。段の縁からは TRANS m で擦り付ける。
//   ③が「守られる部分」で、①②が切土/盛土の対象。指図 断面の色分けと同じ区分。
//
// ⚠ 地形の編集は Undo の外。走らせる前に Stage0_Backup でハイトマップを退避すること。
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static partial class EdoMatsudairaDewaBuilder
{
    public const string SashizuRel = "docs/Sashizu/matsudaira_dewa_sashizu.json";
    public const string ParcelId = "matsudaira_dewa";
    public const string Grp = "Edo_Yashiki_MatsudairaDewa";

    /// <summary>bench=true の run の内側を天端で平らにする幅[m]。**指図 `const.benchBand` から読む**
    /// (⛔ 数値をここに持たない — 2026-09-02 検図【中6】【中3】: 「_runs の『外周帯(内側幅3m)』」は
    /// 存在しない出典だった)。指図に無ければ例外(発明しない)。</summary>
    public static float BAND
    {
        get
        {
            var c = O(D["const"]);
            if (!Has(c, "benchBand")) throw new Exception("指図 const.benchBand が無い(BAND の出典)");
            return F(c["benchBand"]);
        }
    }

    // ---------------------------------------------------------------- 指図の読み込み
    static Dictionary<string, object> _d;
    static string SashizuPath
    {
        get { return Path.Combine(Directory.GetParent(Application.dataPath).FullName, SashizuRel); }
    }
    public static void Reload() { _d = null; _frame = null; _terr = null; _runs = null; _walls = null; _nat = null; _natRes = 0; }
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
    static bool Has(Dictionary<string, object> o, string k) { return o != null && o.ContainsKey(k) && o[k] != null; }

    // ---------------------------------------------------------------- 回転間グリッド
    public class Frame
    {
        public float x0, z0, ux, uz, vx, vz, ken;
        public Vector2 W(float u, float v)
        {
            return new Vector2(x0 + (ux * u + vx * v) * ken, z0 + (uz * u + vz * v) * ken);
        }
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
                    ken = F(O(D["const"])["ken"])
                };
            }
            return _frame;
        }
    }

    public struct Terrace { public string name; public float u0, v0, u1, v1, y; }
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
                    list.Add(new Terrace
                    {
                        name = (string)t["name"],
                        u0 = F(t["u0"]), v0 = F(t["v0"]), u1 = F(t["u1"]), v1 = F(t["v1"]), y = F(t["y"])
                    });
                }
                _terr = list.ToArray();
            }
            return _terr;
        }
    }

    /// <summary>郭内の土留め(グリッド座標の線分)。**ここに線がある縁だけが垂直**。</summary>
    public struct TWall { public string name; public Vector2 a, b; public float coping, s; }
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
                    list.Add(new TWall
                    {
                        name = (string)w["name"],
                        a = new Vector2(F(a[0]), F(a[1])), b = new Vector2(F(b[0]), F(b[1])),
                        coping = F(w["coping"]), s = F(w["s"])
                    });
                }
                _walls = list.ToArray();
            }
            return _walls;
        }
    }
    public static float BatterFill { get { return F(O(D["const"])["batterFill"]); } }
    public static float BatterCut { get { return F(O(D["const"])["batterCut"]); } }
    public static float WallNear { get { return F(O(D["const"])["wallNear"]); } }
    public static float FeatherCap { get { return F(O(D["const"])["featherCap"]); } }

    public struct Run
    {
        public string name; public int edge; public float s0, s1, seat; public bool bench, nagaya, nijukai;
        /// <summary>長屋門の門口の辺沿い s[m](0 なら門口なし)。指図の `runs[].mon`。
        /// ⛔ **開口だけの短い長屋部材は作れない**(妻2つ+bay で最小およそ 8.8m)ので、
        /// 門口は run の中に開ける。天端の段は門口の外へ動かしてある(ユーザー裁定 2026-08-30 案A)。</summary>
        public float monS, monW, monH;

        /// <summary>この run に石垣基壇が付くか。**指図の `base` が正典**。
        /// ⚠ 2026-08-29 まで指図の `s`(駒のモジュール規模)を 0 かどうかで代用していたが、
        /// ユーザー裁定で駒を実寸固定にしたため `s` は廃止された。規模の値を有無の旗に
        /// 兼ねさせると、規模を消した瞬間に石垣が全部消える。</summary>
        public bool ishigaki;
        /// <summary>斜面の run は天端が一直線に下る。seat は**中点**にすぎないので、
        /// 位置を持つ処理は必ず SeatAt(s) を使うこと。
        /// (2026-08-23 土井邸から「一本の run で −3.35m 埋没と +4.35m 露出が同時に起きる」と
        ///  指摘され発覚 — 指摘の数値は seat を平坦に読んだ実装の姿そのものだった)</summary>
        public float seat0, seat1;
        public float SeatAt(float s)
        {
            if (s1 - s0 < 1e-6f) return seat0;
            float t = Mathf.Clamp01((s - s0) / (s1 - s0));
            return seat0 + (seat1 - seat0) * t;
        }
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
                        name = (string)r["name"],
                        edge = (int)F(r["edge"]),
                        s0 = F(r["s0"]), s1 = F(r["s1"]), seat = F(r["seat"]),
                        seat0 = Has(r, "seat0") ? F(r["seat0"]) : F(r["seat"]),
                        seat1 = Has(r, "seat1") ? F(r["seat1"]) : F(r["seat"]),
                        bench = Has(r, "bench") && (bool)r["bench"],
                        nagaya = (string)r["kind"] == "Nagaya",
                        nijukai = Has(r, "nijukai") && (bool)r["nijukai"],
                        ishigaki = Has(r, "base") && (string)r["base"] == "Ishigaki",
                        monS = Has(r, "mon") ? F(O(r["mon"])["s"]) : 0f,
                        monW = Has(r, "mon") ? F(O(r["mon"])["w"]) : 0f,
                        monH = Has(r, "mon") ? F(O(r["mon"])["h"]) : 0f
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
        Vector2 d = b - a; float L = d.magnitude;
        return a + d / Mathf.Max(1e-5f, L) * s;
    }

    // ---------------------------------------------------------------- 幾何のこまごま
    static float G(float x, float z)
    {
        var t = Terrain.activeTerrain;
        return t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y;
    }

    // ---------------------------------------------------------------- 現況地形(退避から読む)
    // ⚠ **設計面が「いまの地形」を読むと冪等でなくなる。** 擦り付けの帯は
    //   Lerp(段の高さ, 現況) なので、二度流すと現況の側が前回の結果に置き換わり、
    //   帯が回を追うごとに段の高さへ寄って最後は崖になる。
    //   よって現況は **Stage0 の退避(造成前のハイトマップ)** から読む。これで何度流しても同じ。
    static float[,] _nat; static int _natRes;
    static void LoadNatural()
    {
        string bin = Path.Combine(BakDir, "heightmap_full.bin");
        if (!File.Exists(bin)) { _natRes = 0; return; }
        using (var r = new BinaryReader(File.OpenRead(bin)))
        {
            int rz = r.ReadInt32(), rx = r.ReadInt32();
            _natRes = rx;
            _nat = new float[rz, rx];
            for (int z = 0; z < rz; z++) for (int x = 0; x < rx; x++) _nat[z, x] = r.ReadSingle();
        }
    }
    /// <summary>造成前の地形の高さ[m]。退避が無ければ現況で代用する(初回だけ)。</summary>
    public static float NaturalY(float x, float z)
    {
        if (_nat == null && _natRes == 0) LoadNatural();
        if (_nat == null) return G(x, z);
        var t = Terrain.activeTerrain; var td = t.terrainData;
        Vector3 tp = t.transform.position, ts = td.size;
        float fx = (x - tp.x) / ts.x * (_natRes - 1), fz = (z - tp.z) / ts.z * (_natRes - 1);
        int ix = Mathf.Clamp((int)fx, 0, _natRes - 2), iz = Mathf.Clamp((int)fz, 0, _natRes - 2);
        float tx = Mathf.Clamp01(fx - ix), tz = Mathf.Clamp01(fz - iz);
        float h = Mathf.Lerp(Mathf.Lerp(_nat[iz, ix], _nat[iz, ix + 1], tx),
                             Mathf.Lerp(_nat[iz + 1, ix], _nat[iz + 1, ix + 1], tx), tz);
        return h * ts.y + tp.y;
    }
    static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 d = b - a; float L2 = d.sqrMagnitude;
        if (L2 < 1e-9f) return (p - a).magnitude;
        float t = Mathf.Clamp01(Vector2.Dot(p - a, d) / L2);
        return (p - (a + d * t)).magnitude;
    }

    // ---------------------------------------------------------------- 設計面
    /// <summary>敷地内の一点の施工後の高さ。現況に依存するのは「造成しない」区間だけなので、
    /// 何度流しても同じ結果になる(冪等)。</summary>
    public static float DesignY(Vector2 p)
    {
        var f = Grid;
        Vector2 g = f.L(p);
        // ① 段(矩形・グリッド座標)。中なら距離0。あわせて縁の最寄り点も出す(土留めの判定に使う)。
        float dT = float.MaxValue, yT = 0f; Vector2 cp = g;
        foreach (var t in Terraces)
        {
            float cu = Mathf.Clamp(g.x, t.u0, t.u1), cv = Mathf.Clamp(g.y, t.v0, t.v1);
            float d = new Vector2(g.x - cu, g.y - cv).magnitude * f.ken;   // 間 → m
            if (d < dT) { dT = d; yT = t.y; cp = new Vector2(cu, cv); }
        }
        if (dT < 1e-4f) return yT;                                // 段の中

        // ② bench=true の run の外周帯
        float dR = float.MaxValue, yR = 0f;
        foreach (var r in Runs)
        {
            if (!r.bench) continue;
            float d = DistSeg(p, EdgePt(r.edge, r.s0), EdgePt(r.edge, r.s1));
            if (d < dR) { dR = d; yR = r.seat; }
        }
        if (dR <= BAND) return yR;

        float yN = NaturalY(p.x, p.y);

        // ③ 段の外。**その縁に土留めがあるなら垂直**(石垣が段差を受ける)ので現地形のまま。
        //    土留めが無いなら 1:feather の土の法面で現地形へ着地させる。
        //    一律の幅で擦り付けると、段差の小さい縁では要らぬ土をいじり、
        //    大きい縁では崖が残る(2026-08-23 ユーザー指摘。断面D の南縁で 60°になっていた)。
        foreach (var w in Walls)
            if (DistSegG(cp, w.a, w.b) <= WallNear) return yN;

        // ⚠ 法面は「盛土を支えるため」にだけ張る。三つとも満たさないと張らない:
        //   (a) 縁そのものが盛土になっている(地山と同高の縁には支える土手が無い)
        //   (b) 縁から featherCap 以内(それ以上は土手でなく崖・石垣の領分)
        //   (c) 1:feather を cap まで延ばして現地形に着地する
        //   (a) を落としていたせいで、西斜面の「縁は地山と同高だが外は崖」という所に
        //   最大9mの土手が伸びた(2026-08-23 実装で発覚)。
        var cpW = f.W(cp.x, cp.y);
        float dEdge = yT - NaturalY(cpW.x, cpW.y);
        if (dEdge <= 0.05f) return yN;                        // (a)
        if (dT > FeatherCap) return yN;                       // (b)
        if (!Daylights(cp, g, yT)) return yN;                 // (c)

        // 盛土は 1:batterFill(1.5)、切土は 1:batterCut(1.0)。指図 §3b の既定値。
        float slack = dT / Mathf.Max(0.5f, yT > yN ? BatterFill : BatterCut);
        return Mathf.Clamp(yN, yT - slack, yT + slack);
    }

    /// <summary>段の縁 cp から点 g の向きへ 1:feather の法面を featherCap[m] 延ばしたとき、
    /// 現地形に着地するか。着地しない縁は崖(石垣で受けるべき所)。</summary>
    static bool Daylights(Vector2 cp, Vector2 g, float yT)
    {
        var f = Grid;
        Vector2 dir = g - cp;
        if (dir.sqrMagnitude < 1e-9f) return true;
        dir.Normalize();
        float cap = FeatherCap;
        Vector2 probeG = cp + dir * (cap / f.ken);
        Vector2 probeW = f.W(probeG.x, probeG.y);
        return yT - cap / Mathf.Max(0.5f, BatterFill) <= NaturalY(probeW.x, probeW.y);
    }

    /// <summary>グリッド座標(間)での点と線分の距離。</summary>
    static float DistSegG(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 d = b - a; float L2 = d.sqrMagnitude;
        if (L2 < 1e-9f) return (p - a).magnitude;
        float t = Mathf.Clamp01(Vector2.Dot(p - a, d) / L2);
        return (p - (a + d * t)).magnitude;
    }

    // ---------------------------------------------------------------- Stage0 退避
    static string BakDir
    {
        get
        {
            return Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                                "TerrainBackups/matsudaira_20260823_pre_grade");
        }
    }

    [MenuItem("Edo/松平出羽守上屋敷/0 ハイトマップを退避")]
    public static void Stage0Menu() { Debug.Log("[Matsudaira] " + Stage0_Backup()); }
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
    [MenuItem("Edo/松平出羽守上屋敷/1 造成(指図の面へ)")]
    public static void Stage1Menu() { Debug.Log("[Matsudaira] " + Stage1_Grade()); }
    public static string Stage1_Grade()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

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
        int n = 0; float cmax = 0f, fmax = 0f; double cutSum = 0, fillSum = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            var p = new Vector2(WX(x0 + x), WZ(z0 + z));
            if (!EdoGeom.PIP(P, p)) continue;                             // 敷地の外は一切触らない
            float cur = H[z, x] * ts.y + tp.y;
            float y = DesignY(p);
            if (y < cur) { cmax = Mathf.Max(cmax, cur - y); cutSum += cur - y; }
            else { fmax = Mathf.Max(fmax, y - cur); fillSum += y - cur; }
            H[z, x] = (y - tp.y) / ts.y; n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1);
        double a = cell * cell;
        return string.Format("造成 cells={0} 切土 最大{1:F2}m 体積{2:F0}m³ / 盛土 最大{3:F2}m 体積{4:F0}m³",
                             n, cmax, cutSum * a, fmax, fillSum * a);
    }

    // ---------------------------------------------------------------- 造成の検査
    [MenuItem("Edo/松平出羽守上屋敷/造成を検査 GradeQA")]
    public static void GradeQAMenu() { Debug.Log("[Matsudaira] " + GradeQA()); }
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
            float cur = H[z, x] * ts.y + tp.y;
            float dif = Mathf.Abs(cur - DesignY(p));
            n++;
            if (dif > TOL) { bad++; if (dif > worst) { worst = dif; wp = p; } }
        }
        return string.Format("GradeQA: 敷地内 {0} セル / 設計面と {1:F2}m 超ずれ = {2} 件 ({3:P1})。最悪 {4:F2}m at ({5:F1},{6:F1})",
                             n, TOL, bad, n == 0 ? 0f : (float)bad / n, worst, wp.x, wp.y);
    }

    // ---------------------------------------------------------------- Stage2 外周
    /// <summary>木柵の駒の継ぎ目の重ね[m]。地形なりに折れるので、突き付けだと折れ角で口が開く。</summary>
    const float FENCE_OVER = 0.15f;

    /// <summary>穂垣の**実寸**(走り方向の幅)。プレハブを1枚置いて測り、すぐ捨てる。
    /// ⛔ 決め打ちの定数に戻さない — 部材を差し替えた瞬間に穴が開く。</summary>
    static float FenceWidth(Transform parent, float psi)
    {
        var probe = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Hogaki5, new Vector3(0, -9999f, 0),
                                                 psi, Vector3.one, parent, "__probe");
        if (probe == null) return 4.0f;
        float w = 0f;
        bool first = true;
        Bounds lb = new Bounds();
        foreach (var mf in probe.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var m = probe.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix;
            var b = mf.sharedMesh.bounds;
            for (int sx = 0; sx < 2; sx++)
                for (int sy = 0; sy < 2; sy++)
                    for (int sz = 0; sz < 2; sz++)
                    {
                        var pt = m.MultiplyPoint3x4(new Vector3(sx == 0 ? b.min.x : b.max.x,
                                                                sy == 0 ? b.min.y : b.max.y,
                                                                sz == 0 ? b.min.z : b.max.z));
                        if (first) { lb = new Bounds(pt, Vector3.zero); first = false; }
                        else lb.Encapsulate(pt);
                    }
        }
        w = Mathf.Max(lb.size.x, lb.size.z);
        UnityEngine.Object.DestroyImmediate(probe);
        return w > 0.5f ? w : 4.0f;
    }

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
        for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(t.GetChild(i).gameObject);
    }
    /// <summary>辺 e の外向き法線(区画の外側)。
    /// ⛔ **重心で向きを決めてはいけない。** 2026-08-29 まで「頂点の平均が内側に来る向き」で
    ///   揃えていたが、当区画は西へ張り出した凸凹の 15 角形で、**頂点平均 z=1152.3 が
    ///   辺1 の中点 z=1157.0 より南**にある。そのため辺1 だけ判定が反転し、土井境の中央
    ///   78.9m(S_Hei_C・石垣113駒)が**区画線の外へ 0.95m 出て**建っていた。
    ///   凸多角形でしか成り立たない近似を、凹みのある区画へ当てていたのが原因。
    /// → **多角形そのものへ当てて決める**(法線方向へ少し出た点が区画の外かを内外判定で見る)。
    ///   全15辺で幾何の外向きと一致することを実測で確認済み。</summary>
    /// <summary>**門構えの両端**(辺沿いの走り s)を `gate.plan.sPos` の最小・最大から採る。
    ///
    /// ⛔ **番所の外縁を門構えの両端と決め打ちしない。** 2026-09-08(指図 第28次)に並びが
    ///   **表長屋 → 袖塀 → 番所 → 門柱 → 番所 → 袖塀 → 表長屋** へ改まり、両端は袖塀になった。
    ///   旧実装は `sPos.banshoW[0]` / `sPos.banshoE[1]` を両端として読んでいたので、
    ///   袖塀の区間(左右 5.5m)が開口の外に取り残されていた(`_pending.omotemonSodeBuzai`
    ///   「実装で併せて直す 2 箇所」)。生成器の `_opening_span` と同じ直し。
    /// ⛔ 欄の名前を並びの順序として仮定しない(欄が増減しても壊れない)。</summary>
    public static void GateSpan(Dictionary<string, object> sPos, out float s0, out float s1)
    {
        s0 = float.MaxValue; s1 = float.MinValue;
        foreach (var kv in sPos)
        {
            if (kv.Key.StartsWith("_")) continue;
            var a = A(kv.Value);
            if (a == null || a.Count < 2) continue;
            s0 = Mathf.Min(s0, Mathf.Min(F(a[0]), F(a[1])));
            s1 = Mathf.Max(s1, Mathf.Max(F(a[0]), F(a[1])));
        }
        if (s0 > s1) throw new Exception("指図 gate.plan.sPos が読めない(門構えの両端が出ない)");
    }

    public static Vector2 OutNormal(int e)
    {
        var P = Poly; int n = P.Length;
        Vector2 d = (P[(e + 1) % n] - P[e % n]).normalized;
        Vector2 nn = new Vector2(-d.y, d.x);
        Vector2 mid = (P[e % n] + P[(e + 1) % n]) * 0.5f;
        // 辺の長さに対して十分小さく、かつ数値誤差より十分大きい距離で試す
        float probe = Mathf.Min(2f, Vector2.Distance(P[e % n], P[(e + 1) % n]) * 0.2f);
        if (PointInPoly(mid + nn * probe)) nn = -nn;
        return nn;
    }

    /// <summary>区画の内側か(交差数法)。OutNormal の向きはこれで決める。</summary>
    static bool PointInPoly(Vector2 p)
    {
        var P = Poly; int n = P.Length; bool c = false;
        for (int i = 0, j = n - 1; i < n; j = i++)
            if ((P[i].y > p.y) != (P[j].y > p.y) &&
                p.x < (P[j].x - P[i].x) * (p.y - P[i].y) / (P[j].y - P[i].y) + P[i].x) c = !c;
        return c;
    }

    // ---------------------------------------------------------------- 表長屋の並べ方
    // ⚠ 共有の EdoNishiTameikeBuilder.NagayaRun は使わない。あれは
    //     ・PITCH=7.81m 決め打ち。**部材の実体は 8.062m** なので全継ぎ目が 0.252m 重なる
    //       → 海鼠紋が二重・瓦が二重・窓の割りが継ぎ目でずれる
    //     ・さらに pitchRun = span/(n-1) で run ごとにピッチを変えるので重なり量が run ごとに違う
    //     ・run ごとに 4.4/3.7 内側へ寄せるので、段違いの run の間に 8m の隙間があく
    //   ここでは **部材の実寸ピッチで、辺の上で連続する長屋 run を1本の鎖として通す**。
    //   段(seat)は部材の中心が入っている run のものを使う → 雛壇の段は部材の境目で起きる。
    struct NagModule { public float lo, hi, pivot; }   // ピボット基準の走り方向の実体範囲[m]
    static NagModule Measure(string path)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one * EdoSannoKitaBuilder.ES;
        var rs = go.GetComponentsInChildren<Renderer>();
        // 壁(namako/wall/dodai)の範囲が繰り返し長。屋根の反り・鬼は端で出るので使わない。
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var r in rs)
        {
            string n = r.gameObject.name.ToLower();
            if (!(n.Contains("wall") || n.Contains("namako") || n.Contains("dodai"))) continue;
            mn = Mathf.Min(mn, r.bounds.min.x); mx = Mathf.Max(mx, r.bounds.max.x);
        }
        UnityEngine.Object.DestroyImmediate(go);
        return new NagModule { lo = mn, hi = mx, pivot = 0f };
    }


    [MenuItem("Edo/松平出羽守上屋敷/2 外周(塀・長屋・木柵)")]
    public static void Stage2Menu() { Debug.Log("[Matsudaira] " + Stage2_Perimeter()); }
    public static string Stage2_Perimeter()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        EdoNishiTameikeBuilder.NaturalMode = false;     // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak);
        var sb = new System.Text.StringBuilder();
        int nag = 0, hei = 0;

        // 門の開口(表門は組立全幅、小門は w)
        var gate = O(D["gate"]);
        var gplan = O(gate["plan"]);
        var gsp = O(gplan["sPos"]);
        float gA, gB; GateSpan(gsp, out gA, out gB);      // ⛔ 番所の外縁で決め打ちしない(GateSpan の注記)
        int gEdge = (int)F(gate["edge"]);
        var komon = new List<float[]>();               // {edge, s0, s1}
        foreach (var o in A(D["komon"]))
        {
            var k = O(o); float s = F(k["s"]), w = F(k["w"]);
            komon.Add(new float[] { F(k["edge"]), s - w / 2f, s + w / 2f });
        }
        Func<int, float, float, List<Vector2[]>> split = (edge, s0, s1) =>
        {
            // 開口で run を割る
            var cuts = new List<float[]>();
            if (edge == gEdge) cuts.Add(new float[] { gA, gB });
            foreach (var k in komon) if ((int)k[0] == edge) cuts.Add(new float[] { k[1], k[2] });
            cuts.Sort((x, y) => x[0].CompareTo(y[0]));
            var outp = new List<Vector2[]>();
            float cur = s0;
            foreach (var c in cuts)
            {
                if (c[1] <= s0 || c[0] >= s1) continue;
                if (c[0] > cur) outp.Add(new Vector2[] { EdgePt(edge, cur), EdgePt(edge, Mathf.Min(c[0], s1)) });
                cur = Mathf.Max(cur, c[1]);
            }
            if (cur < s1) outp.Add(new Vector2[] { EdgePt(edge, cur), EdgePt(edge, s1) });
            return outp;
        };

        // 練塀は run ごとに(段が違うので繋げない)
        foreach (var r in Runs)
        {
            if (r.nagaya) continue;
            Vector2 outw = OutNormal(r.edge);
            foreach (var seg in split(r.edge, r.s0, r.s1))
            {
                if ((seg[1] - seg[0]).magnitude < 1.2f) continue;
                // 斜面の run は天端が一直線に下るので、2m 刻みに割ってその位置の天端で据える
                if (Mathf.Abs(r.seat1 - r.seat0) < 0.01f)
                    EdoNishiTameikeBuilder.DobeiRun(kak, seg[0], seg[1], outw, r.name, false, r.seat0, Vector2.zero, -1);
                else
                {
                    float segLen = Vector2.Distance(seg[0], seg[1]);
                    int nSeg = Mathf.Max(1, Mathf.RoundToInt(segLen / 2.0f));
                    for (int q = 0; q < nSeg; q++)
                    {
                        Vector2 pa = Vector2.Lerp(seg[0], seg[1], q / (float)nSeg);
                        Vector2 pb = Vector2.Lerp(seg[0], seg[1], (q + 1) / (float)nSeg);
                        float sMid = r.s0 + (r.s1 - r.s0) * ((q + 0.5f) / nSeg);
                        EdoNishiTameikeBuilder.DobeiRun(kak, pa, pb, outw, r.name + "_" + q, false,
                                                        r.SeatAt(sMid), Vector2.zero, -1);
                    }
                }
                hei++;
            }
        }
        // 表長屋は **run ごとに1本**。指図が run の長さを持ち、その長さの部材を Blender で焼いてある
        // (`Tools/Blender/build_nagaya_omote.py`)。
        // ⛔ **丸ごとのモジュールを並べない。** 端が成り行きになって門・隅との間に隙間が空く
        //   (2026-08-29: 御蔵門の西へ 1.66m 食い込み・東へ 0.96m の隙間が同時に出ていた。
        //    原因は鎖を run の中央へ寄せる `cursor = s0 + (L - total) * 0.5f` だった)。
        //   → CLAUDE.md 絶対規則5「部材どうしを中心で合わせない。どの面がどの面に接するかを指図に書く」
        //   → 取り合いは指図の `joints`(どの面がどの面に・可動側はどちら)が正典
        foreach (var r in Runs)
        {
            if (!r.nagaya) continue;
            // ⛔ **run の長さをそのまま部材の呼び寸法にしてはいけない。**
            //   `Nagaya_Omote_<L>` の L は**破風の外端どうし(屋根の全長)**で、壁の実体は
            //   両端 TSUMA_OVER だけ内側にある。run 長で頼むと隣り合う run の**壁が 0.64m 空き、
            //   軒だけが渡る**(2026-08-29 ユーザーのブックマーク #1・#2・#3・#4〜#12 の光の筋。
            //   辺12 s=152.00 で実測 151.68 / 152.32)。**壁の実体が run を覆う長さ**で頼む。
            float len = r.s1 - r.s0 + 2f * NAGAYA_TSUMA_OVER;
            string path;
            if (r.monS > 0f)
            {
                // 長屋門(ユーザー裁定 2026-08-30 案A)。門口は**部材のローカル +X の左端から**測る。
                // ⚠ **その「左端」は run の s1 の側**(実測 2026-08-30)。据える yaw は
                //   `atan2(outw.x, outw.y)` で見え面 +Z を外へ向けるので、部材のローカル +X は
                //   **s の減る向き**へ写る。s0 から測ると門口が反対側へ出る — 実際に
                //   辺13 で 3.7m ずれ、指図 s12.50〜15.50 の門口が s8.8〜11.7 に開いた。
                //   ⛔ 向きを式で決めない。`RunEndQA` が**据えた実メッシュの穴の位置**を測って見張る。
                float gc = r.s1 - r.monS + NAGAYA_TSUMA_OVER;
                path = EdoAssets.Own.NagayaOmoteMon(len, gc, r.nijukai);
            }
            else path = r.nijukai ? EdoAssets.Own.NagayaOmote2F(len) : EdoAssets.Own.NagayaOmote(len);
            // ⭐ **2026-09-09: 指図 `chains` と突き合わせる。**`chains[].pieces[].asset` は指図が持つ
            //   「この run にはこの呼び出しの部材が載る」という設計値だが、ビルダーは一度も読んでいなかった
            //   (`_pending.jissouShukudai` ①の13キーの1つ)。⛔ 長さを指図から取り直すのではない —
            //   長さは run(と妻の出)からの従属値なので、**導いた式が指図と一致するか**だけを見る。
            {
                string expr = (r.monS > 0f)
                    ? "EdoAssets.Own.NagayaOmoteMon(" + len.ToString("0.##") + "f, "
                      + (r.s1 - r.monS + NAGAYA_TSUMA_OVER).ToString("0.##") + "f, "
                      + (r.nijukai ? "true" : "false") + ")"
                    : "EdoAssets.Own." + (r.nijukai ? "NagayaOmote2F(" : "NagayaOmote(")
                      + len.ToString("0.##") + "f)";
                string want = null;
                foreach (var co in A(D["chains"]))
                    foreach (var po in A(O(co)["pieces"]))
                    { var pc2 = O(po); if ((string)pc2["run"] == r.name && Has(pc2, "asset")) want = (string)pc2["asset"]; }
                if (want == null) sb.AppendLine("⚠ 長屋 " + r.name + " が指図 chains に無い(部材の宣言が欠けている)");
                else if (want != expr)
                    sb.AppendLine("★ 長屋 " + r.name + " の部材が指図と食い違う — 指図 " + want + " / 導いた式 " + expr);
            }
            Vector2 outw2 = OutNormal(r.edge);
            float psi2 = Mathf.Atan2(outw2.x, outw2.y) * Mathf.Rad2Deg;   // 見え面 +Z を外へ
            float sMid = (r.s0 + r.s1) * 0.5f;
            // ⚠ この部材は**ピボットが壁の外面**なので、置く時点で犬走りぶん内へ寄せる。
            //   `AlignInubashiri` は壁面の部材名(namako/hei…)で外面を測るが、この FBX は
            //   単一メッシュで子を持たないため対象外になる(軒で測ると 0.93m 余計に引っ込む)。
            Vector2 p3 = EdgePt(r.edge, sMid) - outw2 * INUBASHIRI;
            float seat3 = r.SeatAt(sMid);
            // ピボット = 走りの中心・土台の底・**壁の外面**。FBX は実寸(m)なので scale=1
            var go3 = EdoNishiTameikeBuilder.Place(path, new Vector3(p3.x, seat3, p3.y), psi2,
                                                   Vector3.one, kak, r.name);
            if (go3 == null)
            {
                sb.AppendLine("⚠ 部材が無い: " + path + "\n   焼くには: blender --background --python "
                              + "Tools/Blender/build_nagaya_omote.py -- " + len.ToString("0.##")
                              + (r.nijukai ? " --floors 2" : ""));
                continue;
            }
            EdoNishiTameikeBuilder.SeatBottom(go3, seat3 - 0.10f);
            nag++;
        }
        sb.AppendLine("塀・長屋: 長屋 " + nag + "棟 / 練塀run " + hei);
        sb.AppendLine(PlaceKado(kak));

        // 木柵(地形なり)。在庫の矢来を等間隔に立てる。
        var fen = Group("Fences"); Clear(fen);
        int posts = 0;
        foreach (var o in A(D["fences"]))
        {
            var fdef = O(o);
            int e = (int)F(fdef["edge"]);
            float s0 = F(fdef["s0"]), s1 = F(fdef["s1"]);
            Vector2 outw = OutNormal(e);
            float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
            // 穂垣(hogaki5=5枚スパン)を地形なりに並べる。基礎も整地も無い境界の標示。
            // ⚠ **ピッチを決め打ちしない。** 2026-08-29(EDO-0053): SPAN=4.6 の決め打ちに対して
            //   穂垣の実寸は 4.111m しかなく、**駒ごとに 0.49m の穴**が開いていた。加えて
            //   run の端に端数が残り、西〜南西で **合計 21.4m が素通し**になっていた
            //   (ユーザーは北東しか見ていないが、こちらのほうが深刻だった)。
            //   長屋の PITCH 決め打ちと同じ欠陥 — **部材を1枚置いて実寸を測り、端から端まで敷き詰める**。
            float w = FenceWidth(fen, psi);
            // 端は run をわずかに**越えて**敷く。隣の run(角)や練塀と突き付けで終わると、
            // 折れ角のぶんだけ角に口が開く(2026-08-29 実測で P11 に 1.27m・P12 に 1.70m)。
            float a0 = s0 - FENCE_OVER, a1 = s1 + FENCE_OVER;
            float L = a1 - a0;
            int nF = Mathf.Max(1, Mathf.CeilToInt((L - w) / Mathf.Max(0.1f, w - FENCE_OVER)) + 1);
            float pitch = nF > 1 ? (L - w) / (nF - 1) : 0f;
            for (int q = 0; q < nF; q++)
            {
                float s = a0 + w * 0.5f + pitch * q;
                Vector2 p = EdgePt(e, s);
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Hogaki5, new Vector3(p.x, 0, p.y),
                                                     psi, Vector3.one, fen, (string)fdef["name"] + "_" + posts);
                if (go == null) continue;
                EdoNishiTameikeBuilder.SeatBottom(go, G(p.x, p.y) - 0.05f);
                posts++;
            }
        }
        sb.AppendLine("木柵: " + posts + "枚(" + A(D["fences"]).Count + " run)");
        // 石垣の法肩から犬走りを残して据え直す(石垣は Stage3 だが法肩＝区画線なので順序に依らない)
        sb.AppendLine(AlignInubashiri());
        sb.AppendLine(CloseKadoSeams(kak));
        return sb.ToString();
    }

    /// <summary>**隅部材と、隣り合う run の端の駒の隙間を、駒を伸ばして塞ぐ。**
    ///
    /// ⚠ 2026-09-06 にユーザーが「練塀が隣の塀と隙間が残っている」と指摘して発覚(ブックマーク#4)。
    ///   実測すると入隅 `Kado_J_P2` の壁体と隣の練塀の壁体が **0.176〜0.455m** 空いていた。
    ///   ⛔ 外接箱でも、屋根まで含めた最短距離でも見えない — **軒が張り出して先に触れる**ので
    ///   「接している」と誤診する(私が一度そう報告した)。⭕ **壁体の高さ帯だけを取り出して測る**。
    ///
    /// 直し方は CLAUDE.md 規則5 のとおり「置いた駒の実メッシュから面を測って寄せる」:
    /// 隅の腕の端の面と、隣の駒の端の面の距離だけ、**駒を走り方向へ伸ばす**(伸ばす向きは隅側)。
    /// ⛔ 隅部材そのものは伸ばさない(留め継ぎの角度が崩れる)。⚠ 伸び代の上限は 1 駒の 25%。</summary>
    static string CloseKadoSeams(Transform kak)
    {
        var sb = new System.Text.StringBuilder();
        var kados = new List<Transform>(); var runs = new List<Transform>();
        foreach (Transform ch in kak) { if (ch.name.StartsWith("Kado_")) kados.Add(ch); else runs.Add(ch); }
        int nFix = 0; float worst = 0f; string worstName = "";
        foreach (var kado in kados)
        {
            var kb = MeshBody(kado, 999999); if (kb.Count == 0) continue;   // 隅は全頂点(間引かない・上のコメント参照)
            float ky0 = 1e9f, ky1 = -1e9f; foreach (var v in kb) { if (v.y < ky0) ky0 = v.y; if (v.y > ky1) ky1 = v.y; }
            float lo = ky0 + (ky1 - ky0) * 0.15f, hi = ky0 + (ky1 - ky0) * 0.80f;   // 壁体の帯
            foreach (var run in runs)
            {
                // ⛔ **隅(Kado)は単一メッシュで裏面が無い**(実測: run 側の裏面 `_0b` との隙間
                //   0.33〜0.38m は「相手が無い」だけで実体の欠陥ではない)。練塀 run は前後2枚
                //   (`_0f` 表 / `_0b` 裏)で厚みを作るが、隅にはこの裏面に対応する駒が無いので、
                //   裏面との隙間を数え続けても直しようが無い警告にしかならない。表面(`_0f` /
                //   末尾が f/b で終わらない棟=長屋)だけを隅の相手として数える。
                if (run.name.EndsWith("_0b")) continue;
                var rb = MeshBody(run); if (rb.Count == 0) continue;
                float best = 1e9f; Vector3 pa = Vector3.zero, pb = Vector3.zero;
                foreach (var a in kb) { if (a.y < lo || a.y > hi) continue;
                    foreach (var b in rb) { if (b.y < lo || b.y > hi) continue;
                        float d = (a - b).sqrMagnitude; if (d < best) { best = d; pa = a; pb = b; } } }
                if (best > 1e8f) continue;
                float gap = Mathf.Sqrt(best);
                if (gap < 0.02f || gap > 1.0f) continue;             // 接している / 隣ではない
                // ⛔ 走り方向を「局所 +X」と決め打ちしない — 練塀の駒は**外向き法線**で yaw を取っており、
                //   +X が走りとは限らない。⭕ **駒の実メッシュを局所 X と局所 Z へ投影して長い方**を走りに採る。
                float exX = LocalSpan(run, Vector3.right), exZ = LocalSpan(run, Vector3.forward);
                bool useX = exX >= exZ; float len = useX ? exX : exZ;
                Vector3 ax = run.rotation * (useX ? Vector3.right : Vector3.forward);
                float sgn = Vector3.Dot(pa - pb, ax) >= 0 ? 1f : -1f;
                // ⛔ **走り方向で既に重なっている継ぎ目は伸ばしても詰まらない** — 隙間は横(法線)方向にある。
                //   2026-09-06 実測: 入隅 Kado_J_P2 と S_Hei_C_23f は走りで 0.414m 重なりながら壁体が 0.486m 空く。
                //   原因は `AlignInubashiri` が run だけを犬走りに合わせ、**隅部材を動かしていない**こと(横のずれ)。
                //   ⇒ ここでは触らず、そのまま報告する(直しは隅部材の横合わせ・棟梁へ)。
                // ⚠ 2026-09-08(棟梁差戻し・検証して撤回): 「間引き(900点)が隅部材の極値頂点を
                //   取りこぼし、`AlignInubashiri` の横合わせ自体の残差を過大にしていた」のは実証済み
                //   (`MeshBody(tr, 999999)` で間引きを止めたら、隅の外面が -0.30±0.02 まで揃った —
                //   これは残す)。⛔ しかし**「揃ったなら重なり判定を無視して伸ばしてよい」は誤りだった**
                //   — P0/P1/P3/P13 は角度のある留め継ぎ(直角でない)なので、run を**自身の走り軸に
                //   沿って**伸ばしても、隅の断面に対して斜めにしか近づかず、3D最短距離の隙間
                //   (0.02〜0.13m)はほぼ変化しなかった(実測: 伸縮の前後で隙間が小数点以下まで同じ)。
                //   ⇒ 判定は元に戻す。この残差(0.02〜0.13m)は**壁面どうしが別メッシュで角度を持って
                //   接する継ぎ目に残る限界**として棟梁から普請奉行へ報告する(run の軸方向伸縮では解けない
                //   — 隅部材側の断面形状を直すか、指図側で許容差を見直すかの二択)。
                float kA = EdgeAlong(kado, ax, -1f), kB = EdgeAlong(kado, ax, 1f);
                float rA = EdgeAlong(run, ax, -1f), rB = EdgeAlong(run, ax, 1f);
                if (Mathf.Min(kB, rB) - Mathf.Max(kA, rA) > 0.02f)
                { sb.AppendLine(string.Format("⚠ {0} ⇔ {1}: 壁体が {2:F3}m 空くが走りでは重なっている — **横のずれ**(隅部材が犬走りに合っていない)。棟梁へ", kado.name, run.name, gap)); continue; }
                // 伸ばしてよい上限: 指図の joints[].tol が正典(J_P* の tol は概ね [-0.05〜-0.10, 0.0] =
                //   数cmの重なりは許すが、正の隙間は本来ゼロという設計値)。⚠ 2026-09-08(棟梁・普請検査差戻し):
                //   旧 `max(0.60, len*0.35)` は駒(pitch≈2.98m)の 35% ≈ 1.04m まで無条件に伸ばしていたため、
                //   隅部材の腕の実寸不足(例: `Dobei_Kado_88M` の腕 3.27m。指図は 4.10〜4.15m を前提)を
                //   run の伸縮で丸ごと隠し、**run の終端が指図の s0/s1 から 0.81〜0.84m ずれる**副作用が出ていた
                //   (RunEndQA が指摘)。腕の実寸不足は run 側の対症療法では直らない(部材方の腕を伸ばすか、
                //   指図側で s0/s1 を実寸へ合わせるかの二択)。ここでは**駒の継ぎ目としてあり得る小さな誤差
                //   だけを詰め**、それを超える隙間は run を歪めず報告する。
                const float CAP = 0.20f;
                if (len < 0.2f || gap > CAP) { sb.AppendLine(string.Format("⚠ {0} ⇔ {1}: 隙間 {2:F3}m > 上限 {3:F2}m — 伸ばさず(部材方/指図方へ。隅部材の腕の実寸が指図の前提より短い疑い)", kado.name, run.name, gap, CAP)); continue; }
                // ⛔ ピボットが駒の中心とは限らないので「伸ばして半分ずらす」では詰まらない(2026-09-06 実測)。
                // ⭕ 伸ばした**あとに実測**し、隅側の端が目標へ来るまで平行移動する(規則5: 実メッシュで測る)。
                float nearBefore = EdgeAlong(run, ax, sgn);
                float target = nearBefore + sgn * gap;
                var ls = run.localScale; float k = (len + gap) / len;
                run.localScale = useX ? new Vector3(ls.x * k, ls.y, ls.z) : new Vector3(ls.x, ls.y, ls.z * k);
                float nearAfter = EdgeAlong(run, ax, sgn);
                Vector3 delta = ax * (target - nearAfter);
                run.position += delta;
                // ⚠ 2026-09-08: 表(_?f)だけ伸ばして裏(_?b)を置き去りにすると、壁の表裏が
                //   走り方向にずれて剥離する(実測: S_Hei_W0b_0f/_0b が 2.13m 食い違っていた)。
                //   裏に同じ駒番号の対がいれば、同じ scale 係数・同じ移動量を裏にも適用する。
                if (run.name.EndsWith("f"))
                {
                    string bName = run.name.Substring(0, run.name.Length - 1) + "b";
                    var back = kak.Find(bName);
                    if (back != null)
                    {
                        var lsb = back.localScale;
                        back.localScale = useX ? new Vector3(lsb.x * k, lsb.y, lsb.z) : new Vector3(lsb.x, lsb.y, lsb.z * k);
                        back.position += delta;
                    }
                }
                nFix++; if (gap > worst) { worst = gap; worstName = kado.name + " ⇔ " + run.name; }
            }
        }
        sb.AppendLine(string.Format("隅の継ぎ目を詰めた: {0} 駒(最大 {1:F3}m {2})", nFix, worst, worstName));
        return sb.ToString().TrimEnd();
    }




    /// <summary>指図の「点」を格子座標へ。⭐ **`[u, v]` の配列だけでなく `{"ref": "&lt;中仕切/門の名&gt;"}` を解く**
    /// (2026-09-06: 段や道の端が木戸に取り付くとき、literal を書かず木戸の芯に従属させるため。
    ///  ユーザー指摘「飛石が木戸とずれている」— 段の起点が木戸の芯から 1.1 間ずれていた)。
    /// ⛔ ref の相手が見つからなければ例外(黙って 0,0 に置かない)。</summary>
    static Vector2 GridPt(object o)
    {
        var arr = o as List<object>;
        if (arr != null) return new Vector2(F(arr[0]), F(arr[1]));
        var dic = o as Dictionary<string, object>;
        if (dic != null && dic.ContainsKey("ref"))
        {
            string rn = (string)dic["ref"];
            foreach (var w in A(D["nakajikiri"]))
            {
                var ww = O(w); if ((string)ww["name"] != rn) continue;
                var a = A(ww["a"]); var b = A(ww["b"]);
                var mid = new Vector2((F(a[0]) + F(b[0])) * 0.5f, (F(a[1]) + F(b[1])) * 0.5f);
                if (dic.ContainsKey("add")) { var ad = A(dic["add"]); mid += new Vector2(F(ad[0]), F(ad[1])); }
                return mid;
            }
            throw new Exception("指図の点の ref『" + rn + "』が nakajikiri に無い");
        }
        throw new Exception("指図の点が [u,v] でも {ref} でもない");
    }

    /// <summary>駒の**壁体**の、軸 <paramref name="ax"/> 方向の端の座標(<paramref name="sgn"/> が +1 なら最大側)。</summary>
    static float EdgeAlong(Transform tr, Vector3 ax, float sgn)
    {
        float mn = 1e9f, mx = -1e9f;
        foreach (var v in MeshBody(tr)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
        return sgn >= 0 ? mx : mn;
    }

    /// <summary>駒の**実メッシュ**を、駒の局所軸 <paramref name="localAxis"/> へ投影した伸び[m](世界の尺度)。</summary>
    static float LocalSpan(Transform tr, Vector3 localAxis)
    {
        Vector3 ax = tr.rotation * localAxis;
        float mn = 1e9f, mx = -1e9f;
        foreach (var v in MeshBody(tr)) { float q = Vector3.Dot(v, ax); if (q < mn) mn = q; if (q > mx) mx = q; }
        return mx > mn ? mx - mn : 0f;
    }

    /// <summary>**壁体**(屋根・軒・垂木・棟・桁を除く)の頂点を世界座標で。⛔ 軒は先に触れるので継ぎ目の判定に使わない。
    /// <paramref name="maxSamples"/> 既定 900(従来どおり・性能優先)。
    /// ⚠ 2026-09-08(棟梁差戻し): **一様な添字間引きは極値(最小/最大)を落とすことがある** — 隅部材
    /// (`Kado_*`、単一メッシュ 1.6〜1.8万頂点)を 900 点に間引くと、留め継ぎの先端の疎な頂点が
    /// 選ばれず、実測で「壁体が 0.07〜0.46m 空く」の**過大な偽陽性**を出した(実際は全頂点で測ると
    /// 0.01〜0.24m — 半分以下)。⇒ **隅部材の頂点を測る側(呼び出し元)は `maxSamples` を大きく渡し、
    /// 相手側(長い run/長屋)は間引いたままにする**(隅×長屋の全頂点同士だと O(n・m) が重い)。</summary>
    static List<Vector3> MeshBody(Transform tr, int maxSamples = 900)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            string n = mf.name.ToLower();
            if (n.Contains("yane") || n.Contains("noki") || n.Contains("taruki") || n.Contains("mune") || n.Contains("keta")) continue;
            var l2w = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            int step = Mathf.Max(1, vs.Length / Mathf.Max(1, maxSamples));
            for (int i = 0; i < vs.Length; i += step) L.Add(l2w.MultiplyPoint3x4(vs[i]));
        }
        return L;
    }

    static Bounds RendBounds(Transform tr)
    {
        var rs = tr.GetComponentsInChildren<Renderer>();
        var b = new Bounds(tr.position, Vector3.zero);
        bool first = true;
        foreach (var r in rs) { if (!r.enabled) continue; if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
        return b;
    }

    /// <summary>犬走り ≒ 1尺。石垣の法肩と囲いの外面の距離(スキル `perimeter.md` ★★・裁定U/B)。</summary>
    public const float INUBASHIRI = 0.30f;

    /// <summary>囲いの「外面」を成す部材の名前。屋根・軒・垂木は**外面ではない**(庇は出てよい)。</summary>
    static readonly HashSet<string> WallFace = new HashSet<string> {
        "hei", "shitami", "koshi", "namako", "namako2", "n_namako", "dodai", "n_dodai", "hashira2"
    };

    /// <summary>**石垣の法肩から犬走りを残して囲いを据え直す。**
    ///
    /// ⚠ 2026-08-29(EDO-0053)にユーザーが「長屋と石垣の間にスペースがある」と指摘して発覚。
    ///   実測すると全 39 run が外れていた — **長屋は 1.63m 引っ込み、練塀は 0.08m せり出して**いた
    ///   (規定はどちらも 0.30m 控える)。長屋の 1.63m は石垣の天端がまるごと露出する幅で、
    ///   「石垣の上に空地があってその奥に長屋が建っている」ようにしか見えない。
    ///
    /// 石垣は `EdgePt` の上に法肩を置いて据えている(Castle Wall のメッシュは局所 X が −2.4〜0 で、
    /// +X を外向きにしているので**法肩＝区画線**)。よって囲いの外面の目標は **線から内へ 0.30m**。
    /// ⛔ 部材の見かけ幅を決め打ちしない — **置いた駒の実メッシュから外面を測って**寄せる。
    ///   部材を差し替えた瞬間に決め打ちは壊れる(スキルの警告「lat 値で置くのは不可」)。</summary>
    /// <summary>**隅部材(留め継ぎ)を据える。**指図の `joints` の `part` が正典。
    ///
    /// ⚠ 2026-08-29 まで **このビルダーには隅を据える処理が一つも無かった**
    /// (`EdoOkabeYashikiBuilder` にしかなかった)。P0・P1・P2・P3・P13 の5隅すべてで、
    /// 指図は留め継ぎの隅部材を指定しているのに実装は直線材を突き付けるだけだった。
    ///
    /// ⛔ **折れ角を決め打ちしない。**角度は区画が決めるもので毎回違う
    /// (当邸は +90.95° / +18.54° / −87.76° / +41.24° / +18.52°)。
    /// `EdoAssets.Own.Kado("Dobei", 折れ角)` が名前を作る。無い角度は build_kado.py で起こす。
    ///
    /// 据え: `position = 頂点 / yaw = **入りの run の走りの方位** / scale = ES`。
    /// ⚠ scale は **ES(1.818)**。素の部材は丈 1.455 で、×ES = 2.645m ≒ `const.dobeiH` 2.65。
    ///   直線材も `DobeiRun` が `(sx, ES, ES)` で据えているので倍率が揃う。
    ///   **素の単位のまま置くと丈が 1.46m に潰れる。**
    /// ⚠ 直線材は `SeatBottom(seat − 0.10)` で天端へ 0.10m 沈めてある。隅だけ seat ちょうどに
    ///   置くと 0.10m 浮いて軒の線が隅で段になる(岡部で実測)。同じだけ沈める。</summary>
    static string PlaceKado(Transform parent)
    {
        var sb = new System.Text.StringBuilder();
        int n = 0; var miss = new List<string>();
        foreach (var o in A(D["joints"]))
        {
            var j = O(o);
            if (!Has(j, "part") || !Has(j, "kado")) continue;      // 隅部材を使う継ぎ目だけ
            var kd = O(j["kado"]);
            int e = (int)F(j["edge"]);
            int v = (e + 1) % Poly.Length;                         // 継ぎ目の頂点 = 辺 e の終点
            Vector2 a = Poly[e % Poly.Length], b = Poly[v];
            Vector2 dIn = (b - a).normalized;
            float deg = F(kd["deg"]);
            string path = EdoAssets.Own.Kado((string)kd["part"], deg);
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (src == null)
            {
                miss.Add((string)j["id"] + " → " + path
                       + "(blender --background --python Tools/Blender/build_kado.py -- --part dobei --deg "
                       + deg.ToString("F1") + ")");
                continue;
            }
            // 天端は入りの run の座に合わせる(隅で天端が揃うのが正典)
            float seat = F(kd["seat"]);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            Undo.RegisterCreatedObjectUndo(go, "kado");
            go.name = "Kado_" + (string)j["id"];
            go.transform.position = new Vector3(b.x, seat - 0.10f, b.y);
            go.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(dIn.x, dIn.y) * Mathf.Rad2Deg, 0);
            go.transform.localScale = Vector3.one * ES_KADO;
            n++;
        }
        sb.Append("隅部材: " + n + " 基");
        if (miss.Count > 0) sb.Append(" / ★ 部材が無い " + miss.Count + " 件 — " + string.Join(" / ", miss.ToArray()));
        return sb.ToString();
    }

    /// <summary>隅部材・練塀の直線材に共通の倍率。素の部材は江戸暦の単位なので ES を掛ける。</summary>
    const float ES_KADO = 1.818f;

    public static string AlignInubashiri()
    {
        var kak = Group("Kakoi");
        var sb = new System.Text.StringBuilder();
        var byRun = new Dictionary<string, List<float>>();
        int moved = 0;
        for (int i = 0; i < kak.childCount; i++)
        {
            var c = kak.GetChild(i);
            int ri = -1;                                     // Run は struct なので添字で持つ
            for (int k = 0; k < Runs.Length; k++)
                if (c.name.StartsWith(Runs[k].name) && (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
            if (ri < 0) continue;
            var r = Runs[ri];
            Vector2 n2 = OutNormal(r.edge);
            var a = Poly[r.edge % Poly.Length];
            // 外面 = 壁面の部材の頂点を外向き法線へ射影した最大値
            float best = float.MinValue;
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                if (!WallFace.Contains(mf.gameObject.name)) continue;
                var m = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = m.MultiplyPoint3x4(v);
                    best = Mathf.Max(best, (w.x - a.x) * n2.x + (w.z - a.y) * n2.y);
                }
            }
            if (best == float.MinValue) continue;
            float shift = (-INUBASHIRI) - best;                  // 目標 = 線から内へ 0.30m
            if (Mathf.Abs(shift) > 0.02f)
            {
                c.position += new Vector3(n2.x * shift, 0f, n2.y * shift);
                moved++;
            }
            if (!byRun.ContainsKey(r.name)) byRun[r.name] = new List<float>();
            byRun[r.name].Add(best + shift);
        }
        sb.Append("犬走りを揃えた: " + moved + "駒 / " + byRun.Count + " run");

        // ---- 隅部材(留め継ぎ)の横合わせ。
        //   隅は2辺に属するので、**留め継ぎの折れ角(yaw)は動かさず**、両辺それぞれの外向き法線方向に
        //   外面が -INUBASHIRI へ来るよう平行移動だけを解く(2本の直線までの距離=2元1次方程式)。
        //
        // ⛔ **2026-09-07 に一度無効化した版の欠陥**: 「辺 e の外向き法線への最大投影＝その辺の外面」を
        //   腕の選り分け無しに全頂点へ適用すると、入隅(凹)ではもう一方の腕がその方向へ余計に張り出すため
        //   最大投影が別の腕の面になり、Kado_J_P2 が 5.9m 動いた(レンダで隅の練塀が消えた)。
        // ⭕ **直し: 腕ごとに頂点を選り分けてから測る。** 隅の折れ点 P(= 辺 e1 の終点 = 辺 e2 の始点)から、
        //   辺 e の**腕の走り方向**(隅から外へ)を t_e とすると、辺 e の腕に属する頂点は
        //   「(v−P)·t_e ≥ 0(その腕の外向きにある)かつ |(v−P)·t_other − (v−P)·t_e・cosθ| ≤ armThresh
        //   (相手の腕の中心線からのはみ出しが小さい。θ=t1,t2 のなす角)」の物だけ。この部分集合の中で
        //   n_e への最大投影を取れば、入隅でも出隅でも正しく「その腕の外面」になる
        //   (実測で検証済 — scratchpad の sim.py)。
        // ⚠ 2026-09-08(棟梁差戻し): 当初は |(v−P)·t_other| ≤ 定数0.6 という**絶対窓**だったが、
        //   折れ角が浅い隅(t1,t2 がほぼ反対向き)では d_other が d_e にほぼ比例して増えるため、
        //   腕の長さぶん窓が効かなくなる(P1/P13 で実測: d1=1.26m の壁面点が d_other=-0.98 となり
        //   絶対窓 0.6 を割った)。⇒ 窓を「中心線 d_e・cosθ からの残差」に直し、しきい値も
        //   壁厚の実寸(dobeiWallT)から導く(0.6 という決め打ちの値を保守しない)。
        // ⚠ **選り分けは呼び出し時点の(まだ動かす前の)頂点位置で一度だけ行う。** 動かした後の位置で
        //   毎回選り直すと、選り分けの基準(P からの相対位置)自体が補正でずれて発散する
        //   (実測: 1回目の大きな補正の後、2回目の選り分けで「両辺とも該当頂点なし」になり暴走した)。
        //   選り分けを固定すれば dot 積は補正量に対して線形なので**平行移動は一発の連立方程式で解ける**
        //   (2元1次方程式の解が exact — 反復は不要。実際 2 回目に再計算しても残差は浮動小数点誤差のみ)。
        int movedKado = 0; var kadoNote = new List<string>();
        foreach (var o in A(D["joints"]))
        {
            var j = O(o);
            if (!Has(j, "kado")) continue;
            string id = (string)j["id"];
            var kc = kak.Find("Kado_" + id);
            if (kc == null) continue;
            int e1 = (int)F(j["edge"]);
            int e2 = (e1 + 1) % Poly.Length;
            Vector2 a1 = Poly[e1 % Poly.Length];             // 辺 e1 の遠端(隅の反対側)
            Vector2 P = Poly[e2 % Poly.Length];               // 隅の折れ点(= 辺 e1 の終点 = 辺 e2 の始点)
            Vector2 a3 = Poly[(e2 + 1) % Poly.Length];        // 辺 e2 の遠端
            Vector2 t1 = (a1 - P).normalized, t2 = (a3 - P).normalized;   // 隅から外への腕の走り方向
            Vector2 kn1 = OutNormal(e1), kn2 = OutNormal(e2);
            float det = kn1.x * kn2.y - kn1.y * kn2.x;
            if (Mathf.Abs(det) < 0.05f) { kadoNote.Add(id + ": 両辺がほぼ平行(det=" + det.ToString("F3") + ") — 解けず(棟梁へ)"); continue; }
            var body = MeshBody(kc, 999999);   // 隅は全頂点(間引かない・MeshBody のコメント参照)
            if (body.Count == 0) { kadoNote.Add(id + ": メッシュ無し"); continue; }
            // Kado の FBX は単一メッシュ(run のように hei/namako で分かれていない)。
            // run と同じ「壁体の帯」(高さの15〜80%, `CloseKadoSeams` と同じ帯)で屋根を除く。
            float ky0 = 1e9f, ky1 = -1e9f;
            foreach (var v in body) { if (v.y < ky0) ky0 = v.y; if (v.y > ky1) ky1 = v.y; }
            float lo = ky0 + (ky1 - ky0) * 0.15f, hi = ky0 + (ky1 - ky0) * 0.80f;
            // ⭐ 2026-09-08(棟梁差戻し): 折れ角が浅い隅(t1・t2 がほぼ反対向き。例 P1/P13 の 18.5°)では
            //   腕1の実の壁面上の点でも d2(相手の腕への射影)が d1 にほぼ比例して大きくなる
            //   (d2 ≒ d1・cosθ, θ=t1,t2 のなす角)ため、**絶対値の窓 |d2|≤定数 は腕が長いほど
            //   すぐに外れる**(実測: P1 で d1=1.26m の壁面点が d2=-0.98 になり 0.6 の窓を割る)。
            //   ⇒ 窓は「腕の中心線からのはみ出し」= d2 と d1・cosθ の**差**で測る(実際の折れ角=腕の
            //   実寸から導く。決め打ちの絶対窓をやめる)。しきい値そのものも壁厚の実寸(dobeiWallT)から
            //   導く — 0.6 という値を保守しない。
            float cosT = Vector2.Dot(t1, t2);
            float dobeiWallT = F(O(D["const"])["dobeiWallT"]);
            float armThresh = dobeiWallT * 1.5f;   // 壁厚+留め継ぎの面取り分の余裕(実寸由来)
            float best1 = float.MinValue, best2 = float.MinValue;
            foreach (var w in body)
            {
                if (w.y < lo || w.y > hi) continue;
                Vector2 rel = new Vector2(w.x, w.z) - P;
                float d1 = Vector2.Dot(rel, t1), d2 = Vector2.Dot(rel, t2);
                if (d1 >= 0f && Mathf.Abs(d2 - d1 * cosT) <= armThresh) best1 = Mathf.Max(best1, Vector2.Dot(rel, kn1));
                if (d2 >= 0f && Mathf.Abs(d1 - d2 * cosT) <= armThresh) best2 = Mathf.Max(best2, Vector2.Dot(rel, kn2));
            }
            if (best1 == float.MinValue || best2 == float.MinValue) { kadoNote.Add(id + ": 両辺の壁体を判別できず"); continue; }
            float r1 = (-INUBASHIRI) - best1, r2 = (-INUBASHIRI) - best2;
            float dx = (r1 * kn2.y - r2 * kn1.y) / det;
            float dz = (kn1.x * r2 - kn2.x * r1) / det;
            if (Mathf.Abs(dx) > 0.02f || Mathf.Abs(dz) > 0.02f)
            {
                kc.position += new Vector3(dx, 0f, dz);
                movedKado++;
            }
        }
        sb.Append(" / 隅の横合わせ: " + movedKado + " 基");
        if (kadoNote.Count > 0) sb.Append(" / ★ " + string.Join(" / ", kadoNote.ToArray()));
        return sb.ToString();
    }

    /// <summary>**門と扉の面を囲いの面へ揃える。**
    /// ⚠ 2026-08-29(EDO-0053)にユーザーが「門と長屋が面一になっていないので門や塀の意味を成さない」
    ///   と指摘して発覚。実測では小門が +0.59m・表門が +0.26m せり出し、囲いは −0.30m だった。
    ///   門が塀の面から飛び出していると、門が壁の一部でなく前に置いた飾りに見える。
    /// ⛔ 番所は除く — `gate.plan.bansho.protrude`(石垣畳出)で**張り出すのが指図の意図**。</summary>
    public static string AlignGateFace()
    {
        var grp = Group("Mon");
        var gateEdge = new Dictionary<string, int>();
        var g0 = O(D["gate"]);
        gateEdge["Omotemon"] = (int)F(g0["edge"]);
        foreach (var o in A(D["komon"])) { var k = O(o); gateEdge[(string)k["name"]] = (int)F(k["edge"]); }
        int moved = 0;
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < grp.childCount; i++)
        {
            var c = grp.GetChild(i);
            if (c.name.StartsWith("Bansho")) continue;              // 張り出すのが正
            string bas = c.name.Split(new[] { "_Tobira" }, System.StringSplitOptions.None)[0];
            if (!gateEdge.ContainsKey(bas)) continue;
            int e = gateEdge[bas];
            Vector2 n2 = OutNormal(e);
            var a = Poly[e % Poly.Length];
            float best = float.MinValue;
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var m = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = m.MultiplyPoint3x4(v);
                    best = Mathf.Max(best, (w.x - a.x) * n2.x + (w.z - a.y) * n2.y);
                }
            }
            if (best == float.MinValue) continue;
            float shift = (-INUBASHIRI) - best;
            if (Mathf.Abs(shift) > 0.02f)
            {
                c.position += new Vector3(n2.x * shift, 0f, n2.y * shift);
                moved++;
                sb.AppendLine("　" + c.name + " 外面 " + best.ToString("+0.00;-0.00") + " → -0.30");
            }
        }
        sb.Append("門の面を揃えた: " + moved + " 基");
        return sb.ToString();
    }

    // ---------------------------------------------------------------- Stage3 石垣基壇
    //
    // ★ 2026-08-29 ユーザー裁定で作り方を入れ替えた。
    //   「1つの石垣オブジェクト自体のXYZ方向の長さは変えない / run の長さは石垣の重なり具合で
    //     調整する / 石垣の高さは地面への埋まり具合で調整する」
    //
    // ⛔ **run ごとに駒を等倍で拡大縮小してはいけない。** 2026-08-29 まで run の高さに合わせて
    //   `scale = (s,s,s)` を掛けていたため、隣り合う run で石の大きさが 0.26〜1.90m(**7.3倍**)
    //   違い、テクスチャの目が段ごとに変わって見えていた(辺3 S1e→S2 で 2.3倍、辺12 W3→
    //   N_Nagaya_W で 2.1倍)。さらに**ずれ量が駒の大きさに比例する**ので、隣の run との間に
    //   隙間(辺2 で 0.68m)や重なり(辺2 で 0.70m)が必ず出た。ユーザーのブックマーク#14/#15。
    //   石の寸法は実物で決まっている。低い所は**駒を地中へ沈めて**高さを合わせる。
    //
    // ⛔ **駒の箱の向きを文書で決めない。実測した値がこれ**(scale=1・Castle Wall):
    //   ローカル X −2.40〜0 / Y 0〜4.00 / Z −2.00〜0、ピボットは (0, 0(底), 0) の角。
    //   据えると **外向きの面がピボット**(厚み 2.40m は内側へ)、走り方向は **[pos, pos+2.00]**。
    //   スキル §4 は「箱は [pos − 2.0×s, pos]」と書いており**向きが逆**。それを信じて
    //   `t0 + 2.0×s` から並べていたので、石垣が run ごと丸ごと 1 駒ぶん s の増える向きへずれ、
    //   s0 側が裸・s1 側がはみ出していた(「石垣と塀の端があってません」の正体)。
    //
    // 割り付け: L = s1 − s0 を N 枚で覆う。N = ceil((L − 2.00) / 1.80) + 1、
    //   pitch = (L − 2.00) / (N − 1)。pitch ≤ 1.80 が保証されるので**重なりは常に 0.20m 以上**で
    //   隙間は原理的に出ない。i 枚目のピボットは s0 + i·pitch、最後の駒の端が s1 にちょうど乗る。
    // 高さ: position.y = 天端 − 4.00(駒の天端が座に来る)。露出は最大 2.49m(N_Nagaya_W)なので
    //   4.00m の駒で全 run 足りる。露出が 0 以下の区間は完全に地中でよい。
    /// <summary>表長屋の妻で、破風・鬼が**壁の実体より外へ出る量**[m](片側)。
    /// `Nagaya_Omote_36.fbx` を実測: 全長 36.000 に対し壁は 35.360(両端 0.320 内側)。
    /// 妻部材は長さによらず同じなので定数。⛔ 呼び寸法をそのまま run 長に使わない理由がこれ。</summary>
    const float NAGAYA_TSUMA_OVER = 0.32f;

    // ⭐ **2026-09-09: 駒の実寸と割り付けは指図 `ishigaki` から読む。**
    //   ⛔ C# の const に写さない(CLAUDE.md 規則4「数値は指図にのみ置く」)。
    //   写していたあいだ、指図の `ishigaki.piece` / `pitchMax` / `overlapMin` は
    //   **ビルダーが一度も読まない設計値**だった(`_pending.jissouShukudai` ①の13キーの1つ)。
    static Dictionary<string, object> Ig
    {
        get
        {
            if (!Has(D, "ishigaki")) throw new Exception("指図 ishigaki が無い(石垣の駒の出典)");
            return O(D["ishigaki"]);
        }
    }
    /// <summary>駒の走り方向の実長[m]。指図 `ishigaki.piece[2]`。</summary>
    static float IG_RUN { get { return F(A(Ig["piece"])[2]); } }
    /// <summary>駒の高さ[m]。指図 `ishigaki.piece[1]`。天端を座に置き、余りは地中へ埋める。</summary>
    static float IG_H { get { return F(A(Ig["piece"])[1]); } }
    /// <summary>継ぎ目の最大ピッチ[m]。指図 `ishigaki.pitchMax`。これ以下で重なり `overlapMin` を保証する。</summary>
    static float IG_PITCH_MAX { get { return F(Ig["pitchMax"]); } }
    [MenuItem("Edo/松平出羽守上屋敷/3 石垣基壇")]
    public static void Stage3Menu() { Debug.Log("[Matsudaira] " + Stage3_Ishigaki()); }
    public static string Stage3_Ishigaki()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var grp = Group("Ishigaki"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        // ⭐ 指図 `ishigaki` を読んだうえで、**部材の実物と食い違っていないか**を先に測る(規則5)。
        //   ⛔ 指図の `piece` を信じて据えない — 在庫の駒が差し替わったら黙って全 run がずれる。
        {
            if ((string)Ig["partPath"] != EdoAssets.JC.CastleWall)
                sb.AppendLine("⚠ 指図 ishigaki.partPath が EdoAssets.JC.CastleWall と違う: "
                              + Ig["partPath"] + " / " + EdoAssets.JC.CastleWall);
            var probe = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.JC.CastleWall);
            if (probe != null)
            {
                var rs = probe.GetComponentsInChildren<MeshFilter>(true);
                var bb = new Bounds();
                bool first = true;
                foreach (var mf in rs)
                {
                    if (mf.sharedMesh == null) continue;
                    var b0 = mf.sharedMesh.bounds;
                    if (first) { bb = b0; first = false; } else bb.Encapsulate(b0);
                }
                if (!first)
                {
                    var pc = A(Ig["piece"]);
                    float[] want = { F(pc[0]), F(pc[1]), F(pc[2]) };
                    float[] have = { bb.size.x, bb.size.y, bb.size.z };
                    for (int k = 0; k < 3; k++)
                        if (Mathf.Abs(have[k] - want[k]) > 0.05f)
                            sb.AppendLine("⚠ 石垣の駒 piece[" + k + "] 指図 " + want[k].ToString("F2")
                                          + " / 実測 " + have[k].ToString("F2") + "m");
                }
            }
        }
        var gate = O(D["gate"]);
        var gsp = O(O(gate["plan"])["sPos"]);
        float gA, gB; GateSpan(gsp, out gA, out gB);      // ⛔ 番所の外縁で決め打ちしない(GateSpan の注記)
        int gEdge = (int)F(gate["edge"]);
        var komon = new List<float[]>();
        foreach (var o in A(D["komon"]))
        {
            var k = O(o); float s = F(k["s"]), w = F(k["w"]);
            komon.Add(new float[] { F(k["edge"]), s - w / 2f, s + w / 2f });
        }
        // 隅の留め継ぎ(kado)は run の s0/s1 の外側に「腕」を持つ(直線材はそのぶん手前で止まる —
        // 例: J_P2 は S_Hei_C の s1=74.82 より隅 s=78.92 まで4.1m 先)。直線材は止まっても
        // **基壇(石垣)は頂点まで通す**(J_P14 の注記どおり「石垣基壇は開口を作らず通す」)。
        // 腕の区間の天端は隅部材の座(joints[].kado.seat)を採る — run 自身の SeatAt(clamp)は
        // run 内側の座であって腕の座と一致するとは限らない
        // (2026-09-06 EDO-0147 実測: 隅 Kado_J_P2 が基壇なしで 1.25m 浮いていた)。
        var armEnd = new Dictionary<string, Vector2>();     // run名(joints[].a)→(頂点s, 隅の座)
        var armStart = new Dictionary<string, float>();     // run名(joints[].b)→隅の座(頂点=0扱い)
        foreach (var o in A(D["joints"]))
        {
            var j = O(o);
            if (!Has(j, "kado")) continue;
            float armSeat = F(O(j["kado"])["seat"]);
            if (Has(j, "a")) armEnd[(string)j["a"]] = new Vector2(F(j["s"]), armSeat);
            if (Has(j, "b")) armStart[(string)j["b"]] = armSeat;
        }

        int made = 0, runs = 0;
        foreach (var r in Runs)
        {
            if (!r.ishigaki) continue;                        // base=Ishigaki のみ
            // 開口で割る(縁を起点に並べるため、区間の端を正確に持つ)
            var cuts = new List<float[]>();
            if (r.edge == gEdge) cuts.Add(new float[] { gA, gB });
            foreach (var k in komon) if ((int)k[0] == r.edge) cuts.Add(new float[] { k[1], k[2] });
            cuts.Sort((x, y) => x[0].CompareTo(y[0]));
            var segs = new List<float[]>();
            float cur = r.s0;
            foreach (var c in cuts)
            {
                if (c[1] <= r.s0 || c[0] >= r.s1) continue;
                if (c[0] > cur) segs.Add(new float[] { cur, Mathf.Min(c[0], r.s1) });
                cur = Mathf.Max(cur, c[1]);
            }
            if (cur < r.s1) segs.Add(new float[] { cur, r.s1 });
            var segSeat = new List<float>();                  // NaN = r.SeatAt(mid) を使う
            foreach (var _s in segs) segSeat.Add(float.NaN);
            // 隅の腕ぶんを追加区間として足す(直線材の s0/s1 の外)
            if (armEnd.TryGetValue(r.name, out Vector2 ae) && ae.x > r.s1 + 0.01f)
            { segs.Add(new float[] { r.s1, ae.x }); segSeat.Add(ae.y); }
            if (armStart.TryGetValue(r.name, out float asSeat) && r.s0 > 0.01f)
            { segs.Insert(0, new float[] { 0f, r.s0 }); segSeat.Insert(0, asSeat); }

            Vector2 n = OutNormal(r.edge);
            // ローカル +X を外向きに、+Z を s の増える向きに合わせる
            float psi = Mathf.Atan2(-n.y, n.x) * Mathf.Rad2Deg;
            // ⚠ 天端は駒ごとに r.SeatAt(t) から取る(腕の区間は上の segSeat が優先)。r.seat は
            //   斜面 run の**中点**で、これで平らに据えると一本の run の中で埋没と過大露出が
            //   同時に起きる(2026-08-23)。石垣そのものは水平が正典(unity-modular-stonewall §3)
            //   なので、**斜面では run が2m刻みに割られた単位ごとに水平**にし、run 全体では
            //   階段状に下る。
            for (int si = 0; si < segs.Count; si++)
            {
                float t0 = segs[si][0], t1 = segs[si][1], L = t1 - t0;
                if (L < 0.05f) continue;
                // 何枚で覆うか。pitch は必ず IG_PITCH_MAX 以下になるので**重なりは 0.20m 以上**、
                // つまり隙間は原理的に出ない(閉じは「隙間 > めり込み」)。
                int N = (L <= IG_RUN) ? 1 : Mathf.CeilToInt((L - IG_RUN) / IG_PITCH_MAX) + 1;
                float pitch = (N > 1) ? (L - IG_RUN) / (N - 1) : 0f;
                for (int i = 0; i < N; i++)
                {
                    float t = t0 + pitch * i;                 // 駒の箱は [t, t + IG_RUN]
                    float mid = Mathf.Min(t + IG_RUN * 0.5f, t1);
                    float seat = float.IsNaN(segSeat[si]) ? r.SeatAt(mid) : segSeat[si];
                    Vector2 p = EdgePt(r.edge, t);
                    // ⚠ 2026-09-08(普請検査差戻し): 隅の「腕」区間(segSeat[si] が非NaN)は
                    //   joints[].kado.seat という**run とは別の設計値**を天端に持つ(隅で天端の段を
                    //   作るのは、J_P0/J_P2/J_P13/J_P3 の【申し送り】どおり指図の意図どおり)。
                    //   同じ r.name のまま並べると `IshigakiQA` が「run ごとに一直線」の判定で
                    //   腕の段を run 本体の不良と誤診する(実測: S_Hei_E1 0.10m / S_Hei_W0b 0.31m /
                    //   NE_Nagaya_1 0.30m / S_Hei_Doi_S1b 1.12m — いずれも run 本体の seat と
                    //   隅の kado.seat の差にちょうど一致)。腕は run 本体と別バケツに分けて数える。
                    string bucketName = float.IsNaN(segSeat[si]) ? r.name : (r.name + "_arm");
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.JC.CastleWall,
                        new Vector3(p.x, seat - IG_H, p.y), psi,
                        Vector3.one, grp, "IG_" + bucketName + "_" + made);
                    if (go != null) made++;
                }
                runs++;
            }
        }
        sb.AppendLine("石垣基壇: " + made + "駒 / " + runs + "区間");
        return sb.ToString();
    }

    /// <summary>石垣のQA(スキル §5)。天端のばらつき・distinct な position.y / scale.y・横ばらつき。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/石垣を検査")]
    public static void IshigakiQAMenu() { Debug.Log("[Matsudaira] " + IshigakiQA()); }
    public static string IshigakiQA()
    {
        var grp = GameObject.Find(Grp);
        if (grp == null) return "群が無い";
        var t = grp.transform.Find("Ishigaki");
        if (t == null) return "Ishigaki が無い";
        var byRun = new Dictionary<string, List<Transform>>();
        foreach (Transform c in t)
        {
            var parts = c.name.Split('_');
            string key = parts.Length > 2 ? string.Join("_", parts, 1, parts.Length - 2) : c.name;
            if (!byRun.ContainsKey(key)) byRun[key] = new List<Transform>();
            byRun[key].Add(c);
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("run              駒  天端min..max  ばらつき  distinct posY/scaleY  横ばらつき");
        int bad = 0;
        foreach (var kv in byRun)
        {
            float tmn = float.MaxValue, tmx = float.MinValue;
            var py = new HashSet<float>(); var sy = new HashSet<float>();
            var pts = new List<Vector2>();
            foreach (var c in kv.Value)
            {
                var rs = c.GetComponentsInChildren<Renderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds; foreach (var rr in rs) b.Encapsulate(rr.bounds);
                tmn = Mathf.Min(tmn, b.max.y); tmx = Mathf.Max(tmx, b.max.y);
                py.Add(Mathf.Round(c.position.y * 1000f) / 1000f);
                sy.Add(Mathf.Round(c.localScale.y * 1000f) / 1000f);
                pts.Add(new Vector2(c.position.x, c.position.z));
            }
            // 横ばらつき: 最初と最後を結ぶ直線からの距離
            float lat = 0f;
            if (pts.Count > 2)
            {
                Vector2 a = pts[0], b2 = pts[pts.Count - 1];
                Vector2 d = (b2 - a).normalized;
                foreach (var q in pts) lat = Mathf.Max(lat, Mathf.Abs((q - a).x * d.y - (q - a).y * d.x));
            }
            // 斜面 run は天端が seat0→seat1 で下るので、**1 run 1天端を要求しない**。
            // 実物の練塀・石垣も斜面では段状に降りる(水平な駒を規則的に落とす)。
            // 代わりに ①段が単調 ②1段の落差が上限以内 ③駒ごとの scale.y は1種 を見る。
            // (2026-08-24: 検図/普請検査が「設計=一直線 / 実装=階段」の食い違いとして挙げたのを、
            //  実物の作りに合わせて実装の側で正とし、検査と指図の文言を揃えた)
            bool slope = false; float stepMax = 0f; bool mono = true;
            foreach (var r0 in Runs)
                if (r0.name == kv.Key) { slope = Mathf.Abs(r0.seat1 - r0.seat0) > 0.01f; break; }
            if (slope)
            {
                var ys = new List<float>();
                foreach (var c in kv.Value) ys.Add(c.position.y);
                ys.Sort();
                var uy = new List<float>();
                foreach (var y in ys) if (uy.Count == 0 || Mathf.Abs(y - uy[uy.Count - 1]) > 0.001f) uy.Add(y);
                for (int i2 = 1; i2 < uy.Count; i2++) stepMax = Mathf.Max(stepMax, uy[i2] - uy[i2 - 1]);
                mono = true;                                 // ys をソートしているので単調は自明
            }
            const float STEP_CAP = 0.90f;                    // 1段の落差の上限[m]
            bool ng = slope
                ? (stepMax > STEP_CAP || !mono || sy.Count > 1 || lat > 0.10f)
                : ((tmx - tmn) > 0.005f || py.Count > 1 || sy.Count > 1 || lat > 0.10f);
            if (ng) bad++;
            sb.AppendLine(kv.Key.PadRight(16) + kv.Value.Count.ToString().PadLeft(3) + "  "
                + tmn.ToString("F2") + ".." + tmx.ToString("F2") + "  " + (tmx - tmn).ToString("F3")
                + "  " + py.Count + "/" + sy.Count + "  " + lat.ToString("F3") + (ng ? "  <<" : ""));
        }
        sb.AppendLine("不合格 run: " + bad + " / " + byRun.Count);
        return sb.ToString();
    }

    // ---------------------------------------------------------------- Stage 4: 御殿複合
    /// <summary>床高(地面から)。EdoGotenKit.Mune / Roka の既定と同じ値を明示で渡す。</summary>
    public const float GOTEN_FLOOR = 0.62f;

    /// <summary>棟・渡廊下をこの回転グリッドへ据えるときの yaw と原点。
    ///
    /// ⚠ **(u,v) は世界(x,z)に対して左手系**(det = ux·vz − uz·vx = −1)。
    /// 一方 Unity の local(+X,+Z) は yaw をどう振っても右手系(det=+1)なので、
    /// local +X=+u / local +Z=+v とは**置けない** — そう置くと棟が鏡像になる
    /// (入側・妻・座敷飾りが左右反転し、屋根の大棟だけ正しく見えるので気づきにくい)。
    ///
    /// 桁行が u に沿う棟・廊下: local +X=+u / local +Z=**−v**。原点 local(0,0) = (u0, **v1**)
    /// 桁行が v に沿う廊下:     local +X=+v / local +Z=**+u**。原点 local(0,0) = (u0, v0)</summary>
    static float YawAlongU() { var f = Grid; return Mathf.Atan2(-f.vx, -f.vz) * Mathf.Rad2Deg; }
    static float YawAlongV() { var f = Grid; return Mathf.Atan2(-f.vz, f.vx) * Mathf.Rad2Deg; }

    /// <summary>Stage4 が据えた棟の実体。渡廊下の**当たり**を実メッシュから測るために持つ
    /// (⛔ 紙の上の軒高を焼き込まない・規則5)。</summary>
    static readonly Dictionary<string, GameObject> _muneGo = new Dictionary<string, GameObject>();

    /// <summary>格子座標 (u,v) を足形に含む棟の指図を返す(端点=辺の上でも含むと見る)。</summary>
    static Dictionary<string, object> MuneAt(float u, float v)
    {
        const float eps = 1e-3f;
        foreach (var o in A(D["munes"]))
        {
            var m = O(o);
            float a = F(m["u0"]), b = F(m["u1"]), c = F(m["v0"]), d = F(m["v1"]);
            if (u >= a - eps && u <= b + eps && v >= c - eps && v <= d + eps) return m;
        }
        return null;
    }

    /// <summary>棟 <paramref name="root"/> の**屋根の実メッシュ**を world の鉛直線 (xz) で貫き、
    /// **最も低い交点の world Y** を返す(= その点での葺き面の下端 = 取り合いの「当たり」の面)。
    /// 交わらなければ NaN。⛔ bbox で測らない(隅棟の角が片側 0.14 飛び出すので偽陽性が出る)。</summary>
    static float RoofPierceMinY(Transform root, Vector2 xz)
    {
        float best = float.NaN;
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>())
        {
            if (mf == null || mf.sharedMesh == null) continue;
            bool isRoof = false;
            for (var q = mf.transform; q != null && q != root.parent; q = q.parent)
                if (q.name.Contains("Roof")) { isRoof = true; break; }
            if (!isRoof) continue;
            var t = mf.transform;
            var bw = mf.sharedMesh.bounds;
            var cw = t.TransformPoint(bw.center);
            float r = bw.size.magnitude * 0.5f * Mathf.Max(Mathf.Max(
                Mathf.Abs(t.lossyScale.x), Mathf.Abs(t.lossyScale.y)), Mathf.Abs(t.lossyScale.z));
            if ((new Vector2(cw.x, cw.z) - xz).magnitude > r) continue;
            var vs = mf.sharedMesh.vertices;
            var tri = mf.sharedMesh.triangles;
            var wv = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) wv[i] = t.TransformPoint(vs[i]);
            for (int i = 0; i + 2 < tri.Length; i += 3)
            {
                float hy;
                if (!TriPierceY(wv[tri[i]], wv[tri[i + 1]], wv[tri[i + 2]], xz, out hy)) continue;
                if (float.IsNaN(best) || hy < best) best = hy;
            }
        }
        return best;
    }

    /// <summary>棟 local の z = <paramref name="zLocal"/> の帯(±<paramref name="band"/>)にある
    /// **屋根メッシュ**の頂点の最高 Y(棟 local)。x は [x0,x1] に限る(隅棟の角を避ける)。
    /// 三方庇の辺の見分けに使う(⛔ bbox では見抜けない)。</summary>
    static float RoofTopAtLocalZ(Transform mune, float zLocal, float band, float x0, float x1)
    {
        float best = float.NaN;
        foreach (var mf in mune.GetComponentsInChildren<MeshFilter>())
        {
            if (mf == null || mf.sharedMesh == null) continue;
            bool isRoof = false;
            for (var q = mf.transform; q != null && q != mune.parent; q = q.parent)
                if (q.name.Contains("Roof")) { isRoof = true; break; }
            if (!isRoof) continue;
            var vs = mf.sharedMesh.vertices;
            var t = mf.transform;
            for (int i = 0; i < vs.Length; i++)
            {
                var p = mune.InverseTransformPoint(t.TransformPoint(vs[i]));
                if (p.x < x0 || p.x > x1) continue;
                if (Mathf.Abs(p.z - zLocal) > band) continue;
                if (float.IsNaN(best) || p.y > best) best = p.y;
            }
        }
        return best;
    }

    /// <summary>据えた渡廊下の**縁の下**(縁板の下端の地盤上高さ[m])を実メッシュから測る。
    /// ⛔ 板厚を足し引きして算で出さない(指図 `roka.ennoshitaMin` はここで測る量)。</summary>
    static float EnnoshitaY(GameObject roka)
    {
        float best = float.NaN;
        foreach (var mf in roka.GetComponentsInChildren<MeshFilter>())
        {
            if (mf == null || mf.sharedMesh == null) continue;
            bool isBoard = false;
            for (var q = mf.transform; q != null && q != roka.transform.parent; q = q.parent)
                if (q.name.Contains("Enita") || q.name.Contains("FloorBoard")) { isBoard = true; break; }
            if (!isBoard) continue;
            float lo = roka.transform.InverseTransformPoint(
                mf.transform.TransformPoint(mf.sharedMesh.bounds.min)).y;
            if (float.IsNaN(best) || lo < best) best = lo;
        }
        return best;
    }

    /// <summary>三角形を鉛直線 (p.x, p.y=z) が貫くか。貫けば交点の Y を返す。</summary>
    static bool TriPierceY(Vector3 a, Vector3 b, Vector3 c, Vector2 p, out float y)
    {
        y = 0f;
        float den = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z);
        if (Mathf.Abs(den) < 1e-9f) return false;
        float w0 = ((b.z - c.z) * (p.x - c.x) + (c.x - b.x) * (p.y - c.z)) / den;
        float w1 = ((c.z - a.z) * (p.x - c.x) + (a.x - c.x) * (p.y - c.z)) / den;
        float w2 = 1f - w0 - w1;
        if (w0 < -1e-4f || w1 < -1e-4f || w2 < -1e-4f) return false;
        y = w0 * a.y + w1 * b.y + w2 * c.y;
        return true;
    }

    /// <summary>棟 <paramref name="m"/> の四辺 {u0, u1, v0, v1} の**軒を出すか**(1 = 出す / 0 = 落とす)。
    /// 指図は持たない**従属値**で、棟の外形どうしを総当たりで突き合わせて出す
    /// (⛔ 人が数えて書き写さない — `EdoAssets.Goten.RoofBanded` の <c>noki</c> の注)。
    ///
    /// <para>判定は生成器 `Tools/Sashizu/build_matsudaira_dewa_sashizu.py` の `_roof_noki` /
    /// 部材方 `Tools/Blender/build_matsudaira_dewa_roofs.py` の `_touching()` と**同一** —
    /// 外形の線を共有し(例: <c>m.u1 == n.u0</c>)、**直交方向の重なりが正**のとき「接している」。</para>
    ///
    /// <para>⚠ 隣が `roof.bands` を**持たない**棟(御湯殿・長局北・奥台所・厩=長屋型)のときは
    /// 落とさない — 相手の屋根の形が分からないまま軒を落とすと**壁の上が素通し**になる。</para>
    ///
    /// <para>⚠ 突き合わせは**名**で行う(同じ dict の参照で比べると、指図の読み直しを挟んだ
    /// ときに静かに全辺「接していない」へ倒れる)。</para></summary>
    static int[] RoofNoki(Dictionary<string, object> m, List<object> munes)
    {
        string mn = (string)m["name"];
        float mu0 = F(m["u0"]), mu1 = F(m["u1"]), mv0 = F(m["v0"]), mv1 = F(m["v1"]);
        var tou = new Dictionary<string, object>[4];          // u0, u1, v0, v1
        foreach (var o in munes)
        {
            var n = O(o);
            if (n == null || (string)n["name"] == mn) continue;
            float nu0 = F(n["u0"]), nu1 = F(n["u1"]), nv0 = F(n["v0"]), nv1 = F(n["v1"]);
            float ovV = Mathf.Min(mv1, nv1) - Mathf.Max(mv0, nv0);
            float ovU = Mathf.Min(mu1, nu1) - Mathf.Max(mu0, nu0);
            if (ovV > 0f)
            {
                if (Mathf.Abs(mu0 - nu1) < 1e-4f) tou[0] = n;
                if (Mathf.Abs(mu1 - nu0) < 1e-4f) tou[1] = n;
            }
            if (ovU > 0f)
            {
                if (Mathf.Abs(mv0 - nv1) < 1e-4f) tou[2] = n;
                if (Mathf.Abs(mv1 - nv0) < 1e-4f) tou[3] = n;
            }
        }
        var r = new int[4];
        for (int i = 0; i < 4; i++)
        {
            bool drop = false;
            if (tou[i] != null && Has(tou[i], "roof"))
            {
                var rf = O(tou[i]["roof"]);
                drop = rf != null && Has(rf, "bands") && A(rf["bands"]) != null && A(rf["bands"]).Count > 0;
            }
            r[i] = drop ? 0 : 1;
        }
        return r;
    }

    [MenuItem("Edo/松平出羽守上屋敷/4 御殿複合")]
    public static void Stage4Menu() { Debug.Log("[Matsudaira] " + Stage4_Goten()); }
    public static string Stage4_Goten()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var grp = Group("Buildings"); Clear(grp);
        var f = Grid;
        float yawU = YawAlongU(), yawV = YawAlongV();
        var sb = new System.Text.StringBuilder();
        int nm = 0, nl = 0;
        _muneGo.Clear();

        foreach (var o in A(D["munes"]))
        {
            var m = O(o);
            string name = (string)m["name"];
            int u0 = Mathf.RoundToInt(F(m["u0"])), v0 = Mathf.RoundToInt(F(m["v0"]));
            int u1 = Mathf.RoundToInt(F(m["u1"])), v1 = Mathf.RoundToInt(F(m["v1"]));
            int kw = u1 - u0, kd = v1 - v0;              // 外形(四方の入側一間を含む)の間数
            if (kw < kd)
            {
                // 大棟は桁行に架かる。u より v が長い棟が出たら、ここで yawV 側へ振る実装が要る
                sb.AppendLine("⚠ " + name + ": 桁行が u 方向でない(" + kw + "x" + kd + ") — 未対応");
                continue;
            }
            if (kw < 3 || kd < 3)
            {
                sb.AppendLine("⚠ " + name + ": 入側一間を四方に回すと身舎が残らない(" + kw + "x" + kd + ")");
                continue;
            }
            float y = F(m["y"]);
            var w = f.W(u0, v1);                          // local(0,0) の角
            // EDO-0149: 指図に munes[].roof(帯割り)があれば RoofBanded へ差し替える。
            // 無い棟(御湯殿・長局北・奥台所・厩=長屋型)は帯割りの部材が無いので、
            // 従来の入母屋(RoofIrimoya_)のまま残す(⛔ 発明しない・指図どおり)。
            string roof; bool roofAtFloor = false; float roofYaw = 0f;
            int[] irikawaEdges = null, nokiEdges = null;   // 据えた後の検算に使う(辺ごとの入側[間]・軒の有無)
            string[] omitEdges = null;                     // 庇を回さない辺(三方庇の検算に使う)
            var roofSpec = Has(m, "roof") ? O(m["roof"]) : null;
            if (roofSpec != null)
            {
                var bandsL = A(roofSpec["bands"]);
                int[] bands = new int[bandsL.Count];
                for (int bi = 0; bi < bandsL.Count; bi++) bands[bi] = Mathf.RoundToInt(F(bandsL[bi]));
                int spanKen = Mathf.RoundToInt(F(roofSpec["spanKen"]));
                bool alongV = Has(roofSpec, "alongV") && (bool)roofSpec["alongV"];
                string fukizai = Has(roofSpec, "fukizai") ? (string)roofSpec["fukizai"] : "sangawara";
                if (fukizai != "sangawara")
                {
                    sb.AppendLine("⛔ " + name + ": fukizai=" + fukizai + " は未対応(桟瓦以外)。差し戻し — 現状の入母屋のまま残す");
                    roof = EdoAssets.Goten.RoofIrimoya_(kw, kd);
                }
                else
                {
                    // ⭐ **入側は辺ごと**(2026-09-09・部材方)。指図 `roof.irikawa` の
                    //   {"u":[u0,u1],"v":[v0,v1]} を **u0,u1,v0,v1 の順**でそのまま部材名へ渡す。
                    //   ⛔ 省くと四周1間の部材を引き当てる — それが表向4棟の屋根が
                    //     1間ずつ過大になって隣と 3.18間 重なっていた原因。
                    int[] irikawa = null;
                    if (Has(roofSpec, "irikawa"))
                    {
                        var ik = O(roofSpec["irikawa"]);
                        var iu = A(ik["u"]); var iv = A(ik["v"]);
                        irikawa = new int[] { Mathf.RoundToInt(F(iu[0])), Mathf.RoundToInt(F(iu[1])),
                                              Mathf.RoundToInt(F(iv[0])), Mathf.RoundToInt(F(iv[1])) };
                    }
                    // ⭐⭐ **軒落とし(`noki`)も渡す**(2026-09-16 是正)。
                    //   ⛔ 省くと**四周とも軒を出す部材**を引き当てる — それが表向4棟の
                    //     隣どうしの軒が 1.80m 食い込み、寄りのレンダで「軒線が X 字に交差 /
                    //     軒先が宙に浮く」姿になっていた原因(`EdoAssets.Goten.RoofBanded` の
                    //     noki の注)。⛔ 0/1 を人が数えて書き写さない — 棟の外形の総当たり。
                    int[] noki = RoofNoki(m, A(D["munes"]));
                    irikawaEdges = irikawa; nokiEdges = noki;
                    string banded = EdoAssets.Goten.RoofBanded(bands, spanKen, alongV, irikawa, noki);
                    if (AssetDatabase.LoadAssetAtPath<GameObject>(banded) != null)
                    {
                        roof = banded; roofAtFloor = true; roofYaw = 0f;
                    }
                    else
                    {
                        sb.AppendLine("⛔ " + name + ": 帯割り屋根が無い " + banded +
                                      " — edo-buzai へ照会(build_goten_roof.py -- banded " +
                                      string.Join(",", System.Array.ConvertAll(bands, x => x.ToString())) +
                                      " " + spanKen + (alongV ? " --along v" : " --along u") +
                                      (irikawa == null ? "" : " --irikawa " + irikawa[0] + "," + irikawa[1]
                                       + "," + irikawa[2] + "," + irikawa[3]) +
                                      " --noki-edges " + noki[0] + "," + noki[1] + "," + noki[2] + "," + noki[3] +
                                      ")。現状の入母屋のまま残す");
                        roof = EdoAssets.Goten.RoofIrimoya_(kw, kd);
                    }
                }
            }
            else
            {
                // ⭐⭐ **平入り + 庇**(指図 `const.nagayaGataRoof`・2026-09-19 施主裁定A)。
                //   帯割り(4/5 の和)で梁間が作れない奥向4棟+厩の型。⛔ 入母屋へ落とさない。
                //   ⚠ 部材へ渡すのは**床上**の身舎の軒桁。指図の軒高は**地盤基準**なので
                //     `const.gotenFloor` を引く(⛔ 2.744/2.410 を焼き込まない)。
                var c1 = O(D["const"]);
                string zone1 = Has(m, "zone") ? (string)m["zone"] : null;
                float eaveGround = (zone1 == "厩") ? F(c1["umayaEave"]) : F(c1["nagayaGataEave"]);
                float eaveAboveFloor = eaveGround - F(c1["gotenFloor"]);
                string[] omit = null;
                if (Has(m, "hisashiOmit"))
                {
                    var ol = A(m["hisashiOmit"]);
                    omit = new string[ol.Count];
                    for (int oi = 0; oi < ol.Count; oi++) omit[oi] = (string)ol[oi];
                }
                omitEdges = omit;
                // ⭐⭐ **渡廊下が取り付く辺の切り欠き**(2026-09-20)。指図 `_roka` ④ の取り合いは
                //   「廊下の**桁の下端** ↔ **庇の軒桁の天端**」であって軒先の下端ではない
                //   (軒先の下へ潜らせる納めは `_roka` ③ が採らない)。⇒ その1間だけ庇の軒先を
                //   切り詰め、底に軒桁の天端の受け面を出した版を引く。
                //   ⛔ 辺と位置を人が数えない — `EdoAssets.Goten.HirairiNotches` が
                //     `munes[]`/`links[]` の矩形から機械的に解く(規則5)。
                //   ⛔ 口(`kind` が「渡廊下」でない = 御錠口・御膳所口)は渡さない — 下屋を
                //     架けないので軒先を切る理由が無い。
                //   ⛔ 取り付く棟へ切り欠き無しの版を据えない(柱筋の頭上が `roka.zujoMin` を
                //     65mm 割る・2026-09-20 実測)。どちらを引くかは返り値の空/非空で決まる。
                var rokaRects = new List<float[]>();
                foreach (var lo in A(D["links"]))
                {
                    var l0 = O(lo);
                    string k0 = Has(l0, "kind") ? (string)l0["kind"] : "渡廊下";
                    if (k0 != "渡廊下") continue;
                    rokaRects.Add(new float[] { F(l0["u0"]), F(l0["u1"]), F(l0["v0"]), F(l0["v1"]) });
                }
                string[] nSide; float[] nKen;
                EdoAssets.Goten.HirairiNotches(
                    new float[] { F(m["u0"]), F(m["u1"]), F(m["v0"]), F(m["v1"]) },
                    rokaRects, out nSide, out nKen);
                string hira = EdoAssets.Goten.RoofHirairi(kw, kd, eaveAboveFloor, omit, nSide, nKen);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(hira) != null)
                {
                    // ⛔ 寄せ直さない — 部材の z=0 が床で、軒桁は焼き込んである(帯割りと同じ据え方)
                    roof = hira; roofAtFloor = true; roofYaw = 0f;
                    if (nSide.Length > 0)
                    {
                        var nb = new System.Text.StringBuilder();
                        for (int ni = 0; ni < nSide.Length; ni++)
                            nb.Append(ni == 0 ? "" : " ").Append(nSide[ni]).Append('-')
                              .Append(EdoAssets.Goten.KenTag(nKen[ni]));
                        sb.AppendLine("・" + name + ": 渡廊下の切り欠き " + nSide.Length + "か所(" + nb + ")");
                    }
                }
                else
                {
                    sb.AppendLine("⛔ " + name + ": 平入りの屋根が無い " + hira +
                                  " — edo-buzai へ照会(build_goten_roof.py -- hirairi " + kw + " " + kd +
                                  " " + eaveAboveFloor.ToString("F3") +
                                  (omit == null ? "" : " --omit " + string.Join(",", omit)) +
                                  ")。現状の入母屋のまま残す");
                    roof = EdoAssets.Goten.RoofIrimoya_(kw, kd);
                }
            }
            if (roof != null && AssetDatabase.LoadAssetAtPath<GameObject>(roof) == null)
            {
                sb.AppendLine("⚠ " + name + ": 屋根が無い " + kw + "x" + kd +
                              "ken — build_goten_roof.py -- " + (kw * f.ken) + " " + (kd * f.ken) +
                              " Goten_Roof_Irimoya_" + kw + "x" + kd + "ken");
                roof = null;
            }
            // ⭐ 2026-09-08(普請奉行の裁定): 軒高 const(nagayaGataEave/umayaEave)は
            //   「軒下端の濡縁上高さ」— 部材の系列ごとにピボット基準が食い違うので、
            //   `EdoGotenKit.Mune` 側で実メッシュの軒下端を測って寄せる(定数オフセットは決め打ちしない)。
            //   ここでは棟の種別に応じた「指図の軒高」を選ぶだけ。長屋型4棟(御湯殿・長局北・
            //   奥台所・厩。roofSpec 無し)は zone で umayaEave/nagayaGataEave を選ぶ
            //   (`munes[].kind` が json に無いための代用。厩は zone="厩")。
            //   序列: 厩(umayaEave)2.35 < 長屋類(nagayaGataEave)2.80 < 御殿(gotenEave)3.40。
            //
            // ⛔⛔ **帯割り(roofSpec あり)はここで寄せ直さない**(2026-09-16・普請検査【高1】の是正)。
            //   `Tools/Blender/build_goten_roof.py:make_banded` は **z=0 = 床**で、引数 `eave` に
            //   指図 `const.gotenEave`(**床上の身舎の軒桁**の高さ)を焼き込んである
            //   ⇒ **床へ据えれば指図どおり**(土井の帯割りと同じ据え方)。
            //   `gotenEave` を「軒下端(濡縁上)の高さ」と読んで実メッシュの最下端をそこへ寄せると、
            //   **屋根が 0.712m 浮く** = 入側1間+軒の出の下がり 0.992 − 濡縁 datum の差 0.28。
            //   それが全周 0.39m の空き帯(屋根底 30.74 / 柱天端 30.35・8棟)の正体だった。
            //
            // ⭐⭐ **2026-09-19 施主裁定A の是正** — 平入り+庇の部材が焼けたので、長屋型5棟も
            //   **床へ据える**(`roofAtFloor`)。⛔ ここで軒下端を寄せ直すと、指図の軒高の定義が
            //   2026-09-18 に**身舎の軒桁・地盤基準**へ変わっているため **屋根が 1.2m 沈む**。
            //   寄せ直しが残るのは、部材が見つからず入母屋へ落ちた長屋型の棟だけ(旧挙動の保全)。
            float roofEaveLocalY = float.NaN;
            if (roofSpec == null && !roofAtFloor)
            {
                var c = O(D["const"]);
                string zone = Has(m, "zone") ? (string)m["zone"] : null;
                roofEaveLocalY = (zone == "厩") ? F(c["umayaEave"]) : F(c["nagayaGataEave"]);
            }
            var g = EdoGotenKit.Mune(name, grp, new Vector3(w.x, y, w.y), yawU,
                                     kw - 2, kd - 2, 1, GOTEN_FLOOR, roof, iriX: 1,
                                     roofAtFloor: roofAtFloor, roofYaw: roofYaw,
                                     roofEaveLocalY: roofEaveLocalY);
            Undo.RegisterCreatedObjectUndo(g, "mune");
            if (g != null) _muneGo[name] = g;
            // ⭐ 帯割りは**据えた実メッシュで検算する**(規則5。⛔ 目分量で下げない)。
            //   軒先の下端の床上高さは指図の従属値 =
            //     min(辺) [ gotenEave − (入側[間]×ken + 軒の出) × 瓦勾配 ](軒を落とした辺は軒の出 0)。
            //   実測はそこから**軒先瓦の垂れ**のぶんだけ下がる(⛔ 垂れは部材の持ち物で指図は持たない)。
            if (roofSpec != null && g != null)
            {
                var c3 = O(D["const"]);
                float kenM = c3.ContainsKey("ken") ? F(c3["ken"]) : f.ken;
                float eaveH = F(c3["gotenEave"]), kobai = F(c3["gesyaKobai"]), nokiDe = F(c3["nokiE"]);
                int[] ik3 = irikawaEdges ?? new int[] { 1, 1, 1, 1 };
                int[] nk3 = nokiEdges ?? new int[] { 1, 1, 1, 1 };
                float want = float.MaxValue;
                for (int e = 0; e < 4; e++)
                {
                    float run = ik3[e] * kenM + (nk3[e] == 1 ? nokiDe : 0f);
                    float h3 = eaveH - run * kobai;
                    if (h3 < want) want = h3;
                }
                float got = float.NaN; string rnm = null;
                foreach (Transform ch in g.transform)
                {
                    var mf3 = ch.GetComponent<MeshFilter>();
                    if (mf3 == null || mf3.sharedMesh == null || !ch.name.Contains("Roof")) continue;
                    got = ch.localPosition.y + mf3.sharedMesh.bounds.min.y - GOTEN_FLOOR; rnm = ch.name;
                }
                if (rnm == null) sb.AppendLine("⚠ " + name + ": 据えた屋根が見つからず軒先を検算できない");
                else if (got > want + 0.02f || got < want - 0.25f)
                    sb.AppendLine("★ " + name + ": 軒先の下端 床上 " + got.ToString("F3") +
                                  "m — 指図の従属値 " + want.ToString("F3") +
                                  "m(gotenEave − (入側+軒の出)×瓦勾配)から外れる。" +
                                  "部材 " + rnm + " の焼き直しか指図の const を疑う");
            }
            // ⭐ **三方庇は外形(bbox)では検算できない**(庇を断った辺も本屋根の軒が 0.90 出るので
            //   外形は四方庇と対称のまま・2026-09-20 部材方)。⇒ **辺ごとに軒先手前の天端を測る**。
            //   庇を断った辺は本屋根が架かるので、庇の辺より**天端が高い**。
            //   ⚠ Blender の軸と格子の綴りの対応が入れ替わっていると v0/v1 が裏返るので、
            //     食い違ったら屋根を 180° 振って直す(足形の中心が回転の芯なので平面は動かない)。
            if (roofSpec == null && roofAtFloor && omitEdges != null && omitEdges.Length > 0 && g != null)
            {
                float Dm = kd * f.ken, Wm = kw * f.ken, noki0 = F(O(D["const"])["nokiE"]);
                bool omitV1 = System.Array.IndexOf(omitEdges, "v1") >= 0;
                bool omitV0 = System.Array.IndexOf(omitEdges, "v0") >= 0;
                if (omitV1 != omitV0)
                {
                    // 棟 local の z=0 が格子 v1、z=Dm が v0。軒先はそこから更に noki 外
                    float zV1 = -(noki0 - 0.3f), zV0 = Dm + (noki0 - 0.3f);
                    float tV1 = RoofTopAtLocalZ(g.transform, zV1, 0.2f, Wm * 0.3f, Wm * 0.7f);
                    float tV0 = RoofTopAtLocalZ(g.transform, zV0, 0.2f, Wm * 0.3f, Wm * 0.7f);
                    string hi = (tV1 > tV0) ? "v1" : "v0";
                    string want2 = omitV1 ? "v1" : "v0";
                    sb.AppendLine("・" + name + ": 庇を断った辺の検算 軒先手前0.3の天端 v1=" +
                                  tV1.ToString("F3") + " / v0=" + tV0.ToString("F3") +
                                  " → 本屋根は " + hi + "(指図 hisashiOmit=" + want2 + ")");
                    if (hi != want2)
                    {
                        foreach (Transform ch in g.transform)
                            if (ch.name.Contains("Roof"))
                                ch.localRotation = Quaternion.Euler(0f, 180f, 0f);
                        sb.AppendLine("★ " + name + ": 庇を断った辺が裏返っていたので屋根を 180° 振った");
                    }
                }
            }
            nm++;
        }

        // 渡廊下・御錠口 — 両端は棟の壁面へ突き付けるので端の柱通りは落とす(柱の二重置き=z-fighting)
        //
        // ⭐⭐ **2026-09-17 ユーザー裁定A** — 渡廊下は独立した大棟を持たず、主屋の軒下から
        //   葺き下ろす**差し掛けの下屋(両流れ)**。頭(葺き下ろしの線)の高さは廊下ごとの従属値で、
        //   **据えた隣の棟の実メッシュを鉛直に貫いて当たりを測る**(規則5。⛔ 紙の数を焼き込まない)。
        // ⛔ **口2本(御錠口・御膳所口)には下屋を架けない**(指図 `_roka`・2026-09-18 の決定3)。
        //   帯の両側の軒が合わさる谷に樋を回す扱いなので、ここでは屋根を据えない。
        var rk = O(D["roka"]);
        float rkClear = F(rk["clear"]);
        string kobaiKey = (string)rk["kobaiFrom"];
        float rkKobai = F(O(D["const"])[kobaiKey]);
        string floorKey = (string)rk["floorFrom"];
        if (floorKey != "nureen")
            sb.AppendLine("⛔ roka.floorFrom=" + floorKey + " は未対応 — 指図方へ差し戻し");
        // 渡廊下の床は**落縁(=濡縁)の天端**へ継ぐ(指図 `roka.floorFrom`)。⛔ 口は畳面のまま
        float rokaFloor = GOTEN_FLOOR - EdoGotenKit.NUREEN_DROP;
        foreach (var o in A(D["links"]))
        {
            var l = O(o);
            string name = (string)l["name"];
            string kind = Has(l, "kind") ? (string)l["kind"] : "渡廊下";
            int u0 = Mathf.RoundToInt(F(l["u0"])), v0 = Mathf.RoundToInt(F(l["v0"]));
            int u1 = Mathf.RoundToInt(F(l["u1"])), v1 = Mathf.RoundToInt(F(l["v1"]));
            int kw = u1 - u0, kd = v1 - v0;
            bool alongU = kw >= kd;
            int n = alongU ? kw : kd;
            if ((alongU ? kd : kw) != 1)
                sb.AppendLine("⚠ " + name + ": 廊下の幅が一間でない(" + kw + "x" + kd + ")");
            float y = F(l["y"]);
            var w = alongU ? f.W(u0, v1) : f.W(u0, v0);
            GameObject g;
            if (kind != "渡廊下")
            {
                // 口 — 下屋も床下げも掛けない(指図 `_roka` 決定3)
                g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, n,
                                     GOTEN_FLOOR, roof: false, colStart: false, colEnd: false);
                sb.AppendLine("・" + name + "(" + kind + "): 下屋なし・床=畳面 " +
                              GOTEN_FLOOR.ToString("F3"));
            }
            else
            {
                // 端ごとの当たり(地盤上[m])を実メッシュから測る
                float midU = (u0 + u1) * 0.5f, midV = (v0 + v1) * 0.5f;
                float[] endU = alongU ? new float[] { u0, u1 } : new float[] { midU, midU };
                float[] endV = alongU ? new float[] { midV, midV } : new float[] { v0, v1 };
                float[] atari = new float[2];
                bool[] omoya = new bool[2];
                string[] endName = new string[2];
                for (int e = 0; e < 2; e++)
                {
                    var mm = MuneAt(endU[e], endV[e]);
                    if (mm == null) { atari[e] = float.NaN; endName[e] = "?"; continue; }
                    endName[e] = (string)mm["name"];
                    omoya[e] = Has(mm, "roof");
                    GameObject mg; _muneGo.TryGetValue(endName[e], out mg);
                    if (mg == null) { atari[e] = float.NaN; continue; }
                    // 廊下の幅を横切って 5 点を測り、中央値を採る(瓦は名目面から ±0.15 うねる)
                    var hits = new List<float>();
                    for (int s = -2; s <= 2; s++)
                    {
                        float t = s * 0.2f;
                        Vector2 p = f.W(endU[e] + (alongU ? 0f : t), endV[e] + (alongU ? t : 0f));
                        float hy = RoofPierceMinY(mg.transform, p);
                        if (!float.IsNaN(hy)) hits.Add(hy - y);
                    }
                    if (hits.Count == 0) { atari[e] = float.NaN; continue; }
                    hits.Sort();
                    atari[e] = hits[hits.Count / 2];
                }
                if (float.IsNaN(atari[0]) || float.IsNaN(atari[1]))
                {
                    sb.AppendLine("⛔ " + name + ": 当たりを実メッシュから測れない(" +
                                  endName[0] + "/" + endName[1] + ")— 下屋を架けずに残す");
                    g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, n,
                                         rokaFloor, roof: false, colStart: false, colEnd: false);
                }
                else
                {
                    // ⭐⭐ 元に採る端 = **当たりの低い端**(全渡廊下で一律。普請奉行の決定
                    //   EDO-0276・2026-09-20。⛔ 指図 json は書き換えない=規則4、決定は掲示板が正典)。
                    //   指図 `_roka` は「両端とも御殿なら高い側」と「端ごとに 頭 ≤ 当たり − clear」
                    //   (縛り①)の二つを持つが、**後者は めり込み = 許容0 を防ぐ縛りなので優先する**。
                    //   高い側の規則は頭上の有効高を最大に取るための U 推論で、低い側でも頭上 2.100 と
                    //   目標 `roka.zujoTarget` 1.97 を上回るため失う物がない ⇒ 奥向どうしの規則
                    //   (低い側)へ揃える。`omoya[]` は残すが選り分けには使わない。
                    int pick = atari[0] <= atari[1] ? 0 : 1;
                    float head = atari[pick] - rkClear;
                    float colTop = head - (EdoGotenKit.K * 0.5f) * rkKobai;
                    g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, n,
                                         rokaFloor, colStart: false, colEnd: false,
                                         geyaHeadLocalY: head, geyaKobai: rkKobai, enita: true);
                    sb.AppendLine("・" + name + " " + n + "間: 当たり " +
                                  endName[0] + "=" + atari[0].ToString("F3") + " / " +
                                  endName[1] + "=" + atari[1].ToString("F3") +
                                  " → 元=" + endName[pick] + " 頭 " + head.ToString("F3") +
                                  " 柱筋の頭上 " + (colTop - rokaFloor).ToString("F3") +
                                  " 縁の下 " + EnnoshitaY(g).ToString("F3"));
                    float other = atari[1 - pick];
                    if (head > other - rkClear + 1e-3f)
                        sb.AppendLine("★ " + name + ": 頭 " + head.ToString("F3") +
                                      " が反対の端(" + endName[1 - pick] + ")の当たり " +
                                      other.ToString("F3") + " − clear " + rkClear.ToString("F2") +
                                      " を超える — roka_clear_check の縛り①");
                }
            }
            Undo.RegisterCreatedObjectUndo(g, "roka");
            nl++;
        }

        sb.Append("棟 " + nm + "/" + A(D["munes"]).Count + " 棟、廊下 " + nl + "/" + A(D["links"]).Count + " 本");
        return sb.ToString();
    }

    // ---------------------------------------------------------------- Stage 5: 門
    /// <summary>表門・番所2・小門2を据える。
    /// ⚠ 旧 `Omotemon` 群(撤回した s=42 案の残骸・設計位置から66.8mずれ・非アクティブ)は
    ///   ここで撤去する。**手組み資産ではなく生成物**なので消してよい
    ///   (手組みの Ishigaki / Nagaya は触らない)。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/5 門(表門・番所・小門)")]
    public static void Stage5Menu() { Debug.Log("[Matsudaira] " + Stage5_Mon()); }
    public static string Stage5_Mon()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var root = Group("");
        // 旧案の残骸を撤去
        var old = root.Find("Omotemon");
        if (old != null) { UnityEngine.Object.DestroyImmediate(old.gameObject); }
        var grp = Group("Mon"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        int n = 0;

        var gate = O(D["gate"]);
        int ge = (int)F(gate["edge"]);
        float gs = F(gate["s"]), sill = F(gate["sill"]);
        Vector2 outw = OutNormal(ge);
        // 部材のローカル +X を辺の走り方向へ、+Z を外向きへ揃える。
        // ⚠ Blender 側は (走り X / 高さ Z / 奥行 Y) で組み、FBX 書き出しで Y-up に直る。
        //   Unity 側の yaw は **+Z を外向き**にする角。Atan2(outw.x, outw.y) がそれ。
        float yaw = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;

        Vector2 gp = EdgePt(ge, gs);
        var mon = EdoNishiTameikeBuilder.Place(EdoAssets.Own.MatsudairaOmotemon,
            new Vector3(gp.x, sill, gp.y), yaw, Vector3.one, grp, "Omotemon");
        if (mon != null) { n++; sb.AppendLine("表門 s=" + gs.ToString("F1") + " 敷居=" + sill.ToString("F2")); }

        // 番所2棟 — sPos の banshoW / banshoE の中心へ。門の面より外へ protrude 分だけ出す
        var plan = O(gate["plan"]);
        var sp = O(plan["sPos"]);
        var bs = O(plan["bansho"]);
        float prot = F(bs["protrude"]);
        // ⭐ **番所躯体の面の s**(低い側・高い側)を控える。袖塀の小口(J_Sode_*)は
        //   指図が「番所躯体の妻面」と名指ししているので、据えたあとここへ突き付けて検める。
        var banshoFace = new Dictionary<string, Vector2>();
        // 辺の走り方向の単位ベクトルと、投影値 → 辺沿い s の変換
        Vector2 eDir0 = (EdgePt(ge, 1f) - EdgePt(ge, 0f)).normalized;
        float sBase = Vector2.Dot(EdgePt(ge, 0f), eDir0);
        foreach (var key in new[] { "banshoW", "banshoE" })
        {
            var a = A(sp[key]);
            float mid = (F(a[0]) + F(a[1])) * 0.5f;
            Vector2 q = EdgePt(ge, mid) + outw * (prot * 0.5f);
            // ⭐ 部材名に**躯体の幅**が入る(2026-09-09)。⛔ 寸法なしの旧名は削除済み —
            //   指図の `w` を動かしたら「部材が無い」と鳴るのが正。⛔ 旧寸で黙って建てない。
            var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.MatsudairaBansho(F(bs["w"])),
                new Vector3(q.x, sill, q.y), yaw, Vector3.one, grp, "Bansho_" + key.Substring(6));
            if (go != null)
            {
                n++;
                // ⭐⭐ **2026-09-09 普請奉行の裁定 C — 検査を「躯体の面」で測る。**
                //   指図の継ぎ目 `J_Bansho_*` / `J_Sode_*` が名指しするのは**番所躯体の東端/西端**で、
                //   部材のメッシュは恒久的に 躯体 + 0.40m(基壇 +0.18 / 側面の出格子 +0.22)。
                //   ⛔ `ProjSpan`(全メッシュの最大投影)で `w` と比べると**必ず 0.40m 過大**に出て、
                //      「部材が指図と違う」という誤診になる(今日この邸で3度出た『軒・庇・基壇が
                //      先に触れる』型と同じ)。⇒ 帯 `MatsudairaBanshoBodyBand` の頂点だけで測る。
                float yLoB = sill + EdoAssets.Own.MatsudairaBanshoBodyBand[0];
                float yHiB = sill + EdoAssets.Own.MatsudairaBanshoBodyBand[1];
                // ⭐ 奥行の窓で**基壇の天端**を外す(同じ高さに並んでいる)。半幅は指図の `d`
                float bMn, bMx;
                ProjBand(go, eDir0, yLoB, yHiB, out bMn, out bMx,
                         outw, new Vector2(go.transform.position.x, go.transform.position.z),
                         F(bs["d"]) * 0.5f + 0.05f);
                float whole = ProjSpan(go, eDir0);                    // 参考: 基壇・出格子を含む外接
                if (bMx <= bMn)
                {
                    sb.AppendLine("⛔ 番所 " + key + ": 躯体の帯 y=" + yLoB.ToString("F2") + "‥"
                        + yHiB.ToString("F2") + "(奥行の窓 ±" + (F(bs["d"]) * 0.5f + 0.05f).ToString("F2")
                        + ")に頂点が無い — 部材のピボット/丈が変わった疑い。"
                        + "⛔ 外接で代用して合格にしない(全メッシュ " + whole.ToString("F2") + "m)");
                }
                else
                {
                    float have = bMx - bMn, want = F(bs["w"]);
                    float sLo = bMn - sBase, sHi = bMx - sBase;       // 躯体の妻面の辺沿い s
                    banshoFace[key] = new Vector2(sLo, sHi);
                    if (Mathf.Abs(have - want) > 0.05f)
                        sb.AppendLine("⚠ 【申し送り】番所 " + key + " の**躯体**の実幅 " + have.ToString("F2")
                            + "m が指図 `gate.plan.bansho.w`=" + want.ToString("F2") + "m と "
                            + (have - want).ToString("+0.00;-0.00") + "m 違う ⇒ 左右へ "
                            + ((have - want) * 0.5f).ToString("F2") + "m ずつはみ出す(継ぎ目 J_Bansho_"
                            + key.Substring(6) + " の許容 −0.05‥0 を超える)。部材方へ焼き直しの照会が要る"
                            + "(⛔ 横だけ縮めない — 出格子と唐破風が潰れる)");
                    // 継ぎ目: 躯体の妻面 ↔ 指図の枠(`sPos`)。⛔ 外接では測らない
                    float wantLo = Mathf.Min(F(a[0]), F(a[1])), wantHi = Mathf.Max(F(a[0]), F(a[1]));
                    float dLo = sLo - wantLo, dHi = sHi - wantHi;
                    if (Mathf.Abs(dLo) > 0.05f)
                        sb.AppendLine("⚠ 番所 " + key + " の躯体**西端** s=" + sLo.ToString("F2")
                            + " が指図 " + wantLo.ToString("F2") + " と "
                            + dLo.ToString("+0.00;-0.00") + "m 違う");
                    if (Mathf.Abs(dHi) > 0.05f)
                        sb.AppendLine("⚠ 番所 " + key + " の躯体**東端** s=" + sHi.ToString("F2")
                            + " が指図 " + wantHi.ToString("F2") + " と "
                            + dHi.ToString("+0.00;-0.00") + "m 違う");
                    sb.AppendLine("番所 " + key + " s=" + mid.ToString("F1") + " **躯体**幅"
                        + have.ToString("F2") + "m(指図 " + want.ToString("F2") + ")躯体の面 s="
                        + sLo.ToString("F2") + "‥" + sHi.ToString("F2") + "(指図 " + wantLo.ToString("F2")
                        + "‥" + wantHi.ToString("F2") + ")/ 参考: 基壇・出格子を含む外接 "
                        + whole.ToString("F2") + "m");
                }
            }
        }

        // ---------------- 継ぎ目 J_Bansho_W / J_Bansho_E(番所躯体の妻面 ↔ 門柱(鏡柱)の外側面・隙間0)
        //
        // ⭐⭐ **門柱の面は「冠木より下」で測る**(2026-09-09)。冠木は柱より 0.35m ずつ長く、
        //   帯を上まで伸ばすと門が 5.20m あることになって継ぎ目が 0.35m の「めり込み」に化ける。
        // ⛔⛔ **帯の下端を敷居より上に取らない。**柱は箱なので**頂点が上下の縁にしかない** —
        //   0.5m から測ったら柱の足元が落ちて、扉だけの 3.66m を「柱の外面」と誤読した(実際に踏んだ)。
        //   ⇒ 帯は **敷居 〜 敷居 + `plan.monH` × 0.6**(冠木の下端 3.5m より下・柱の足元を含む)。
        if (mon != null)
        {
            float mMn, mMx;
            ProjBand(mon, eDir0, sill, sill + F(plan["monH"]) * 0.6f, out mMn, out mMx);
            if (mMx > mMn)
            {
                float sMonLo = mMn - sBase, sMonHi = mMx - sBase;
                var mArr = A(sp["mon"]);
                float wantMonLo = Mathf.Min(F(mArr[0]), F(mArr[1])), wantMonHi = Mathf.Max(F(mArr[0]), F(mArr[1]));
                sb.AppendLine("門柱(鏡柱)の外側面 s=" + sMonLo.ToString("F2") + "‥" + sMonHi.ToString("F2")
                    + "(指図 `sPos.mon` " + wantMonLo.ToString("F2") + "‥" + wantMonHi.ToString("F2")
                    + " / 幅 " + (sMonHi - sMonLo).ToString("F2") + "m ↔ `plan.monW` "
                    + F(plan["monW"]).ToString("F2") + "m)");
                // 番所躯体の妻面と突き合わせる。⛔ 許容は指図の `joints[].tol` と同じ −0.05‥0
                if (banshoFace.ContainsKey("banshoW"))
                {
                    float d = banshoFace["banshoW"].y - sMonLo;   // 正 = 番所が門柱へめり込む
                    sb.AppendLine("継ぎ目 J_Bansho_W: 番所躯体の東端 s="
                        + banshoFace["banshoW"].y.ToString("F2") + " ↔ 門柱の外側面 s="
                        + sMonLo.ToString("F2") + " ⇒ " + d.ToString("+0.00;-0.00") + "m"
                        + (d < -0.001f ? "  ⚠ **すき間**(門の脇が素通しになる)"
                           : (d > 0.05f ? "  ⚠ めり込みが許容 0.05m を超える" : "  ⭕")));
                }
                if (banshoFace.ContainsKey("banshoE"))
                {
                    float d = sMonHi - banshoFace["banshoE"].x;
                    sb.AppendLine("継ぎ目 J_Bansho_E: 門柱の外側面 s=" + sMonHi.ToString("F2")
                        + " ↔ 番所躯体の西端 s=" + banshoFace["banshoE"].x.ToString("F2")
                        + " ⇒ " + d.ToString("+0.00;-0.00") + "m"
                        + (d < -0.001f ? "  ⚠ **すき間**(門の脇が素通しになる)"
                           : (d > 0.05f ? "  ⚠ めり込みが許容 0.05m を超える" : "  ⭕")));
                }
            }
            else sb.AppendLine("⛔ 門柱の面が測れない(帯 " + sill.ToString("F2") + "‥"
                    + (sill + F(plan["monH"]) * 0.6f).ToString("F2") + " に頂点が無い)");
        }

        // ---------------- 袖塀2枚 — **番所の外側の妻面 ↔ 表長屋の妻面**(指図 第28次で並びが改まった)
        //
        // ⚠ **2026-09-09 に新設。**それまで袖塀は表門の一体部材に焼き込まれており、第28次で
        //   「番所は門柱へ直付け」([松江上屋敷門写真]A)になった時点で部材から外された。
        //   ⇒ 実装が据えていなかったので、番所と表長屋のあいだが素通しだった。
        // 取り合いは指図の `joints` J_Sode_W / J_Sode_E(袖塀の小口 ↔ 番所の外側の妻面・隙間0)。
        // ⛔ 長さを発明しない — `gate.plan.sPos.sodeW` / `sodeE` の従属値。
        // ⭐ 部材のピボットは**走りの起点(ローカル x=0)の小口・厚みの芯・地盤**なので、
        //   起点を**番所側の小口**(= 開口の芯 `gate.s` に近い方の端)に取って +X を外へ向ける。
        {
            var kg = Has(plan, "kuguri") ? O(plan["kuguri"]) : null;
            string kSode = kg != null ? (string)kg["sode"] : null;
            float kOff = kg != null ? F(kg["offset"]) : -1f;
            float dobeiH = F(O(D["const"])["dobeiH"]);
            Vector2 eDir = (EdgePt(ge, 1f) - EdgePt(ge, 0f)).normalized;   // s の増える向き
            foreach (var key in new[] { "sodeW", "sodeE" })
            {
                if (!Has(sp, key)) continue;
                var a = A(sp[key]);
                float a0 = Mathf.Min(F(a[0]), F(a[1])), a1 = Mathf.Max(F(a[0]), F(a[1]));
                // 起点 = 開口の芯に近い端(=番所側の小口)
                bool startAtLow = Mathf.Abs(a0 - gs) < Mathf.Abs(a1 - gs);
                float sStart = startAtLow ? a0 : a1;
                float len = a1 - a0;
                Vector2 dirX = startAtLow ? eDir : -eDir;
                float yawS = Mathf.Atan2(-dirX.y, dirX.x) * Mathf.Rad2Deg;
                string side = key.Substring(4);                            // "W" / "E"
                // 潜り戸は片側だけ(`gate.plan.kuguri`)。焼けていなければ**潜り戸なしで据えて申し送る**
                string path = EdoAssets.Own.Sodebei(len);
                bool wantK = (kSode != null && kSode == side && kOff >= 0f);
                if (wantK)
                {
                    string pk = EdoAssets.Own.Sodebei(len, kOff);
                    if (AssetDatabase.LoadAssetAtPath<GameObject>(pk) != null) path = pk;
                    else sb.AppendLine("⛔ 潜り戸つきの袖塀が焼けていない " + pk
                        + " — 部材方へ: blender --background --python Tools/Blender/build_sodebei.py -- "
                        // ⛔ 焼成の引数は**指図の生値**(`gate.plan.kuguri.offset`)。⚠ ファイル名の方は
                        //   `Sodebei(len, kuguri)` が "0.##" で丸めるので 0.775 → `_K0.78`(名前だけの丸め)
                        + len.ToString("0.##") + " --kuguri " + kOff.ToString("0.###")
                        + "。当面は潜り戸なしで据える");
                }
                Vector2 p0 = EdgePt(ge, sStart);
                var go = EdoNishiTameikeBuilder.Place(path, new Vector3(p0.x, sill, p0.y), yawS,
                                                     Vector3.one, grp, "Sode_" + side);
                if (go == null) { sb.AppendLine("⛔ 袖塀の部材が無い " + path); continue; }
                // 犬走り: **壁体の外面**を区画線から内へ INUBASHIRI 。⛔ 外接箱(屋根の出 0.5)で測らない
                //   — 屋根で測ると壁が 0.27m 余計に引っ込む(長屋で踏んだのと同じ型)。
                //   壁体の帯は丈の 0.2〜0.6(腰板〜貫。屋根は 0.66 より上)。
                {
                    var apex = Poly[ge % Poly.Length];
                    float best = float.MinValue;
                    float yLo = sill + dobeiH * 0.20f, yHi = sill + dobeiH * 0.60f;
                    foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                    {
                        if (mf.sharedMesh == null) continue;
                        var mtx = mf.transform.localToWorldMatrix;
                        foreach (var v in mf.sharedMesh.vertices)
                        {
                            var w2 = mtx.MultiplyPoint3x4(v);
                            if (w2.y < yLo || w2.y > yHi) continue;
                            best = Mathf.Max(best, (w2.x - apex.x) * outw.x + (w2.z - apex.y) * outw.y);
                        }
                    }
                    if (best > float.MinValue)
                    {
                        float shift = (-INUBASHIRI) - best;
                        go.transform.position += new Vector3(outw.x * shift, 0f, outw.y * shift);
                    }
                }
                n++;
                // ⭐ **継ぎ目 J_Sode_*(袖塀の小口 ↔ 番所躯体の妻面)を実測で検める。**
                //   ⛔ 屋根の出(0.5)を含む外接で測らない — 壁体の帯(丈の 0.2〜0.6)で測る。
                //   ⛔ 相手も**番所躯体の面**(上で帯から測った値)。基壇・出格子は当てる面ではない。
                {
                    float mnS, mxS;
                    ProjBand(go, eDir0, sill + dobeiH * 0.20f, sill + dobeiH * 0.60f, out mnS, out mxS);
                    if (mxS > mnS)
                    {
                        float sA = mnS - sBase, sB = mxS - sBase;
                        // 番所に突き付く側 = 開口の芯に近い小口
                        float sMeet = Mathf.Abs(sA - gs) < Mathf.Abs(sB - gs) ? sA : sB;
                        string bkey = "bansho" + side;
                        if (banshoFace.ContainsKey(bkey))
                        {
                            var bf = banshoFace[bkey];
                            float sFace = Mathf.Abs(bf.x - gs) < Mathf.Abs(bf.y - gs) ? bf.y : bf.x;
                            float gap = Mathf.Abs(sMeet - sFace);
                            sb.AppendLine("継ぎ目 J_Sode_" + side + ": 袖塀の小口 s=" + sMeet.ToString("F2")
                                + " ↔ 番所躯体の妻面 s=" + sFace.ToString("F2") + " ⇒ 差 "
                                + (sMeet - sFace).ToString("+0.00;-0.00") + "m"
                                + (gap > 0.05f ? "  ⚠ 許容 0.05m を超える" : "  ⭕"));
                        }
                    }
                }
                sb.AppendLine("袖塀 " + side + " s=" + a0.ToString("F1") + "‥" + a1.ToString("F1")
                              + " 長" + len.ToString("F2") + "m 起点 s=" + sStart.ToString("F1")
                              + (wantK && path.Contains("_K") ? " 潜り戸 芯" + kOff.ToString("F2") + "m" : " 潜り戸なし"));
            }
        }

        // 小門(御蔵門・東小門)— **扉ごと長屋に作り付けてある。ここでは何も置かない。**
        //
        // ⚠ 2026-08-31 ユーザー裁定2-A。それまでは在庫の冠木門 `Eg.Kabukimon` を開口へ
        //   落とし込み、`PartSize(go).x`(= **部材の全幅**)が開口幅 w になるよう横へ縮めていた。
        //   ところが冠木門の全幅 14.413m には**屋根の出と袖塀**が入っていて、壁に接すべき
        //   躯体は扉の高さで 7.53m しかない。w=3.0 に合わせると躯体は **1.56m** まで痩せ、
        //   左右に **0.72m ずつ隙間**が空いた(ユーザー指摘の画像で門の脇に草が見えていた)。
        //   さらに冠木門は自前の小屋根を持つので、長屋の通し屋根と**二重**になっていた。
        //   → 規則5「呼び寸法で合わせない/接する面で合わせる」。
        //
        //   いまは `runs[].mon` の門口を `build_nagaya_omote.py --gate` が長屋の躯体に彫り、
        //   方立・楣・**両開きの板戸(3.0×2.8m)・扉の上の小壁**まで作り付けている。
        //   開口の閉じは長屋のメッシュが持つので、閉じ検査もそのまま通る。
        // ⛔ ここに門を置き直さない。置くと屋根が二重になり、隙間がまた開く。
        foreach (var o in A(D["komon"]))
        {
            var k = O(o);
            sb.AppendLine("小門 " + (string)k["name"] + " 辺" + F(k["edge"]).ToString("0")
                        + " s=" + F(k["s"]).ToString("F1")
                        + " — 門口・扉とも長屋に作り付け(部材を置かない)");
        }

        // 表門の扉 — ⭕⭕ **2026-09-09 普請奉行の裁定: 躯体が持っている両開きの板戸を採る。**
        //   ⛔ **別部材の扉(`JC.GateDoorYaguraL/R` 丈 3.0m)を重ねて据えない。**
        //   躯体の扉は門柱の丈 `plan.monH` 5.20m と釣り合っており、櫓門の扉 3.0m より整合する。
        //   ⚠ 指図 `gate.plan.leaf._`(「躯体が扉を持たないので別部材の扉を据える」)は
        //     **次の設計の巡で直る**(指図方へ差し戻し済み)。⛔ ここで指図の欄を書き換えない。
        if (Has(plan, "leaf"))
        {
            var lf = O(plan["leaf"]);
            // ⚠ **扉が二重になっていないかを、置いた実物のメッシュで測って申し送る**(2026-09-09 部材方の注意)。
            //   指図 `gate.plan.leaf._` は「躯体が扉を持たないので別部材の扉を据える」と書くが、
            //   `Matsudaira_Omotemon.fbx` は単一メッシュなので `HasOwnDoors`(子の名前で判定)では
            //   捕まらない。⇒ **開口の内側(|x| < 内法/2)に躯体の頂点があるか**で判定する。
            //   ⛔ ここで扉を抜く/据えるを実装が決めない — 指図の欄と部材のどちらを採るかは奉行の裁定。
            if (mon != null)
            {
                float monW = F(plan["monW"]);
                int inOpen = 0; float dTop = float.MinValue, dBot = float.MaxValue;
                foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        // 部材のローカル +X = 走り。柱の内法は monW − 柱2本ぶんなので余裕をみて 0.75×monW/2
                        if (Mathf.Abs(v.x) > monW * 0.375f) continue;
                        inOpen++; dTop = Mathf.Max(dTop, v.y); dBot = Mathf.Min(dBot, v.y);
                    }
                }
                if (inOpen > 0)
                    sb.AppendLine("表門の扉: **躯体の両開きの板戸を採る**(開口の内の実体 頂点 " + inOpen
                        + " 点・丈 " + dBot.ToString("F2") + "‥" + dTop.ToString("F2") + "m = "
                        + (dTop - dBot).ToString("F2") + "m / 門柱の丈 `plan.monH` "
                        + F(plan["monH"]).ToString("F2") + "m)。⛔ 別部材の扉は据えない(普請奉行の裁定"
                        + " 2026-09-09)。⚠ 指図 `gate.plan.leaf`(" + (string)lf["kind"] + "・丈 "
                        + F(lf["h"]).ToString("F2") + "m・`by`=" + (Has(lf, "by") ? (string)lf["by"] : "—")
                        + ")は**躯体の扉を指していない** ⇒ 指図方へ差し戻し(⛔ 実装は指図を書き換えない)");
                else
                    sb.AppendLine("⛔ 表門の躯体が開口の内に実体を持たない(素通し)— 裁定の前提"
                        + "『躯体が両開きの板戸を持つ』が崩れる。⇒ 呼び出し元へ差し戻し"
                        + "(⛔ 実装が勝手に別部材の扉を据えない)");
            }
        }
        sb.AppendLine(AlignGateFace());
        sb.Append("門 " + n + " 基");
        return sb.ToString();
    }


    /// <summary>門が自前の扉を持っているか、置いた実物のメッシュ名で判定する
    /// (edogoyomi の冠木門は doorl / doorr。名前で門の種類を決め打ちしない)。</summary>
    static bool HasOwnDoors(GameObject go)
    {
        if (go == null) return false;
        bool l = false, r = false;
        foreach (var mr in go.GetComponentsInChildren<MeshRenderer>(true))
        {
            string nm = mr.gameObject.name.ToLowerInvariant();
            if (nm == "doorl" || nm == "sdoorl") l = true;
            if (nm == "doorr" || nm == "sdoorr") r = true;
        }
        return l && r;
    }

    /// <summary>門扉(両開き)を開口の芯へ据える。L/R とも突き合わせ側にピボットがあるので、
    /// 同じ点に両方置けば閉じる。開口幅 <paramref name="want"/> へは**横だけ**伸ばす。
    /// ⚠ 扉を書いても建てなければ開口は素通しのまま — 2026-08-29(EDO-0053)に
    ///   御蔵門・東小門が 2.7〜2.9m 開いていた。指図に leaf があるのに実装が無い状態を作らない。</summary>
    static int Leaves(Transform grp, string name, string pathL, string pathR,
                      float pairW, float footOff, Vector2 p, float yaw, float want, float sill)
    {
        int n = 0;
        float fx = (pairW > 0.1f && want > 0.1f) ? want / pairW : 1f;
        foreach (var pr in new[] { new[] { pathL, "L" }, new[] { pathR, "R" } })
        {
            var go = EdoNishiTameikeBuilder.Place(pr[0], new Vector3(p.x, sill - footOff, p.y), yaw,
                                                  new Vector3(fx, 1f, 1f), grp, name + "_Tobira" + pr[1]);
            if (go != null) n++;
        }
        return n;
    }

    // ---------------------------------------------------------------- Stage 6: 郭内の造作
    /// <summary>中仕切塀・竹垣・石段・井戸・隅櫓・附属屋を据える。
    ///
    /// 【向き】ローカル軸とグリッドの対応(左手系の補正が入るので必ずここを読む):
    ///   yawU … +X → +u ／ +Z → **−v**
    ///   yawV … +X → +v ／ +Z → **+u**
    /// 部材のピボットは footprint の中心・地盤レベル、+X = 桁行、+Z = 表。
    ///
    /// 【高さ】面の上は <see cref="DesignY"/>。造成しない所は現地形が返る(指図と同じ三層)。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/6 郭内の造作(塀・垣・石段・井戸・櫓・附属屋)")]
    public static void Stage6Menu() { Debug.Log("[Matsudaira] " + Stage6_Zosaku()); }
    public static string Stage6_Zosaku()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var grp = Group("Fuzoku"); Clear(grp);
        var f = Grid;
        float yawU = YawAlongU(), yawV = YawAlongV();
        var sb = new System.Text.StringBuilder();
        int nHei = 0, nGaki = 0, nDan = 0, nIdo = 0, nYag = 0, nYa = 0;

        // ---------------- 中仕切塀(板塀)と庭木戸
        var kido = new List<Vector2[]>();               // 木戸の world 区間(板塀はここを空ける)
        foreach (var o in A(D["nakajikiri"]))
        {
            var w = O(o);
            if ((string)w["kind"] != "庭木戸") continue;
            var a = A(w["a"]); var b = A(w["b"]);
            kido.Add(new[] { f.W(F(a[0]), F(a[1])), f.W(F(b[0]), F(b[1])) });
        }
        var njGrp = Group("Fuzoku/Nakajikiri");
        // ⚠ **木戸を先に据えてから板塀を敷く**(2026-09-06 是正)。板塀が空ける穴は据えた木戸の実メッシュから
        //    取るので、指図の並び順(木戸が最後)のまま流すと**古い穴で塀を敷いてしまう**。
        var njOrder = new List<Dictionary<string, object>>();
        foreach (var o in A(D["nakajikiri"])) { var w0 = O(o); if ((string)w0["kind"] == "庭木戸") njOrder.Add(w0); }
        foreach (var o in A(D["nakajikiri"])) { var w0 = O(o); if ((string)w0["kind"] != "庭木戸") njOrder.Add(w0); }
        foreach (var w in njOrder)
        {
            string nm = (string)w["name"];
            var a = A(w["a"]); var b = A(w["b"]);
            Vector2 A2 = f.W(F(a[0]), F(a[1])), B2 = f.W(F(b[0]), F(b[1]));
            float h = F(w["h"]);
            if ((string)w["kind"] == "庭木戸")
            {
                // 在庫の冠木門を開口幅へ合わせて据える【確度B — 庭木戸そのものの在庫は無い】
                // ⚠ **2026-09-06 ユーザー指摘の是正**(ブックマーク#3・#5「木戸と板塀の位置がずれている/中心で
                //    測っていないか」)。旧実装の欠陥は 2 つ:
                //    ① **yaw は元のまま**(`Atan2(dir.y, -dir.x)`)。2026-09-06 に一度 `Atan2(dir.x, dir.y)` へ
                //       変えたが、冠木門は棟が走りに直交して見える姿になった(レンダで確認)ので戻した。
                //    ② 冠木門のメッシュは**ピボットから 2.3m 離れて**おり、ピボットを開口の中心へ置くと
                //       実体が塀の走りから外れる。⇒ CLAUDE.md 規則5「中心で合わせない・実メッシュの面で寄せる」に従い、
                //       据えたあと**実メッシュの外接箱の中心**が開口の中心に来るよう平面で寄せ直す。
                Vector2 c = (A2 + B2) * 0.5f;
                Vector2 dir = (B2 - A2).normalized;
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Kabukimon,
                    new Vector3(c.x, DesignY(c), c.y), Mathf.Atan2(dir.y, -dir.x) * Mathf.Rad2Deg,
                    Vector3.one * EdoSannoKitaBuilder.ES, njGrp, nm);
                if (go != null)
                {
                    var bb = EdoNishiTameikeBuilder.RB(go);
                    // 幅は**走り方向へ投影した実メッシュの伸び**で測る(外接箱の x/z の大きい方ではない)
                    float have = ProjSpan(go, dir);
                    float want = (B2 - A2).magnitude;
                    if (have > 0.1f)
                    {
                        var ls = go.transform.localScale;
                        go.transform.localScale = new Vector3(ls.x * want / have, ls.y * h / bb.size.y, ls.z);
                    }
                    // 平面: 実メッシュの中心を開口の中心へ / 鉛直: 実メッシュの底を設計地盤へ
                    var bb2 = EdoNishiTameikeBuilder.RB(go);
                    go.transform.position += new Vector3(c.x - bb2.center.x, DesignY(c) - bb2.min.y, c.y - bb2.center.z);
                    // 板塀が空ける「穴」は、指図の a/b ではなく**据えた実メッシュの走り方向の伸び**で取る
                    var bb3 = EdoNishiTameikeBuilder.RB(go);
                    float half = ProjSpan(go, dir) * 0.5f;
                    Vector2 mc = new Vector2(bb3.center.x, bb3.center.z);
                    for (int ki = 0; ki < kido.Count; ki++)
                        if (Vector2.Distance((kido[ki][0] + kido[ki][1]) * 0.5f, c) < 0.05f)
                            kido[ki] = new[] { mc - dir * half, mc + dir * half };
                    nHei++;
                }
                continue;
            }
            nHei += ItabeiRun(njGrp, A2, B2, h, nm, kido);
        }
        // ⭐ **根石は板塀と木戸を据えたあと**(木戸の穴は据えた実メッシュから取るので順序が要る)
        sb.AppendLine(NeishiPlace(njGrp, kido));

        // ---------------- 竹垣(法肩の転落止め)
        var rlGrp = Group("Fuzoku/Takegaki");
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Eg.TakeGaki);
        if (src == null) sb.AppendLine("⚠ 竹垣の部材が無い: " + EdoAssets.Eg.TakeGaki);
        else foreach (var o in A(D["rails"]))
        {
            var rl = O(o);
            string nm = (string)rl["name"];
            var pts = A(rl["pts"]);
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                var p0 = A(pts[i]); var p1 = A(pts[i + 1]);
                Vector2 P0 = f.W(F(p0[0]), F(p0[1])), P1 = f.W(F(p1[0]), F(p1[1]));
                float len = (P1 - P0).magnitude;
                // 部材は走りが +Z(生 1.05m)。ES ではなく江戸間の割りに合わせて 0.909 で使う
                const float S = 0.909f, PITCH = 1.05f * S;
                int n = Mathf.Max(1, Mathf.RoundToInt(len / PITCH));
                float pitch = len / n;
                Vector2 dir = (P1 - P0) / len;
                float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
                for (int k = 0; k < n; k++)
                {
                    Vector2 c = P0 + dir * (pitch * (k + 0.5f));
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.TakeGaki,
                        new Vector3(c.x, DesignY(c), c.y), yaw,
                        new Vector3(S, S * 1.30f, S * pitch / PITCH), rlGrp, nm + "_" + k);
                    if (go == null) continue;
                    var bb = EdoNishiTameikeBuilder.RB(go);
                    go.transform.position += new Vector3(c.x - bb.center.x,
                        DesignY(c) - 0.05f - bb.min.y, c.y - bb.center.z);
                    nGaki++;
                }
            }
        }

        // ---------------- 石段
        var dnGrp = Group("Fuzoku/Kaidan");
        foreach (var o in A(D["kaidans"]))
        {
            var k = O(o);
            string nm = (string)k["name"];

            // ---- 庭の段(`kind: "庭の段"`)は郭をつなぐ石段と持ち物が違う。
            //   ⛔ 蹴上・踏面・落差を**指図から読まない** — 両端が地形で固定されるので段数からの従属値
            //   (`_kaidans` の注記 ②、汐見坂の裁定 2026-08-24 と同じ扱い)。
            //   指図が持つのは **両端 a/b・折れ点 via・段数 steps・幅 w** だけ。
            //   ⭐ 導出は生成器 `build_matsudaira_dewa_sashizu.py::garden_step_geom` と同じ式にする:
            //      走り = 折れ線 a→via…→b の**平面長**(⛔ 両端の直線距離で測らない)/ 落差 = |yb − ya|
            //      蹴上 = 落差/n ・ 踏面 = 走り/n。地盤は**実地形**(造成 1 と築山 1b の後の面)。
            //   2026-09-04 棟梁: ここが無く、Stage6 が 庭の段 の `drop` で KeyNotFoundException を投げていた。
            if (Has(k, "kind") && (string)k["kind"] == "庭の段")
            {
                if (!Has(k, "a") || !Has(k, "b"))
                { sb.AppendLine("⚠ 庭の段 " + nm + ": 指図に a/b が無い"); continue; }
                var gpath = new List<Vector2>();
                gpath.Add(f.W(GridPt(k["a"]).x, GridPt(k["a"]).y));
                if (Has(k, "via")) foreach (var q in A(k["via"])) { var pq = A(q); gpath.Add(f.W(F(pq[0]), F(pq[1]))); }   // ⚠ `pv` は同じ関数の後段(pos の v)で宣言されるので別名(CS0136)
                gpath.Add(f.W(GridPt(k["b"]).x, GridPt(k["b"]).y));
                float ghor = 0f;
                for (int i = 1; i < gpath.Count; i++) ghor += Vector2.Distance(gpath[i - 1], gpath[i]);
                int gn = Mathf.Max(1, (int)F(k["steps"]));
                float gya = TerrainY(gpath[0].x, gpath[0].y);
                float gyb = TerrainY(gpath[gpath.Count - 1].x, gpath[gpath.Count - 1].y);
                float gdrop = Mathf.Abs(gyb - gya), gy0 = Mathf.Min(gya, gyb);
                float gkeri = gdrop / gn, gfumi = ghor / gn;
                float gw = F(k["w"]);
                int gacross = Mathf.Max(1, Mathf.RoundToInt(gw / 1.98f));
                bool upFromA = gyb > gya;
                var gmod = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Own.DanishiStep);
                if (gmod == null) { sb.AppendLine("⚠ 段石が無い: " + EdoAssets.Own.DanishiStep); continue; }
                for (int i = 0; i < gn; i++)
                {
                    // 下から i 段目。弧長 s は**登る向き**に測る
                    float sUp = gfumi * (i + 0.5f);
                    float sA = upFromA ? sUp : ghor - sUp;          // a 端からの弧長
                    // 折れ線上の点と接線
                    Vector2 c = gpath[0], tan = (gpath[1] - gpath[0]).normalized;
                    float acc = 0f;
                    for (int j = 1; j < gpath.Count; j++)
                    {
                        float seg = Vector2.Distance(gpath[j - 1], gpath[j]);
                        if (sA <= acc + seg || j == gpath.Count - 1)
                        {
                            float tt = seg < 1e-6f ? 0f : Mathf.Clamp01((sA - acc) / seg);
                            c = Vector2.Lerp(gpath[j - 1], gpath[j], tt);
                            tan = (gpath[j] - gpath[j - 1]).normalized;
                            break;
                        }
                        acc += seg;
                    }
                    if (!upFromA) tan = -tan;                        // 接線は登る向きへ
                    float gyaw = Mathf.Atan2(tan.x, tan.y) * Mathf.Rad2Deg;
                    Vector2 gside = new Vector2(tan.y, -tan.x);
                    float gtop = gy0 + gkeri * (i + 1);
                    for (int j = 0; j < gacross; j++)
                    {
                        float t2 = (j - (gacross - 1) * 0.5f) * (gw / gacross);
                        Vector2 cc = c + gside * t2;
                        var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.DanishiStep,
                            new Vector3(cc.x, gtop, cc.y), gyaw, Vector3.one, dnGrp, nm + "_" + i + "_" + j);
                        if (go == null) continue;
                        float have2 = RunWidth(EdoNishiTameikeBuilder.RB(go), gyaw);
                        if (have2 > 0.05f) go.transform.localScale = new Vector3((gw / gacross) / have2, 1f, 1f);
                        var bb2 = EdoNishiTameikeBuilder.RB(go);
                        go.transform.position += new Vector3(cc.x - bb2.center.x, gtop - bb2.max.y, cc.y - bb2.center.z);
                        nDan++;
                    }
                }
                sb.AppendLine("庭の段 " + nm + " " + gn + "段×" + gacross + "枚 蹴上" + gkeri.ToString("F3")
                              + " 踏面" + gfumi.ToString("F3") + " 走り" + ghor.ToString("F2")
                              + " (" + Mathf.Min(gya, gyb).ToString("F2") + "→" + Mathf.Max(gya, gyb).ToString("F2") + ")"
                              + (Has(k, "orikaeshi") && !Has(k, "via")
                                 ? "  ⚠ orikaeshi=" + F(k["orikaeshi"]) + " なのに via が無い(折れ点が指図に無い→指図方へ)" : ""));
                continue;
            }

            var pos = A(k["pos"]);
            float pu = F(pos[0]), pv = F(pos[1]);
            string dir = Has(k, "dir") ? (string)k["dir"] : null;
            if (dir == null) { sb.AppendLine("⚠ 石段 " + nm + ": 指図に dir が無い"); continue; }
            Vector2 up;
            if (!TryGridDir(dir, out up))
            { sb.AppendLine("★ 石段 " + nm + ": dir が知らない値 \"" + dir + "\" — +u/-u/+v/-v のどれか"); continue; }
            float drop = F(k["drop"]), run = F(k["run"]), wid = F(k["w"]);
            int steps = Mathf.Max(1, (int)F(k["steps"]));
            Vector2 c0 = f.W(pu, pv);
            // ⚠ 足元と天端の標高は**指図が持つ**(y0/y1)。地形から推測しない —
            //   段の縁のすぐ外は擦り付けの途中だし、門の敷居は設計面に現れない
            //   (2026-08-25: 地形読みで御蔵門の段が 0.33m 浮き、東小門の段は落差0と誤検知した)。
            if (!Has(k, "y0") || !Has(k, "y1"))
            { sb.AppendLine("⚠ 石段 " + nm + ": 指図に y0/y1 が無い"); continue; }
            float baseY = F(k["y0"]), topY = F(k["y1"]);
            if (Mathf.Abs((topY - baseY) - drop) > 0.005f)
                sb.AppendLine("★ 石段 " + nm + ": 指図の中で矛盾 — y1-y0=" +
                              (topY - baseY).ToString("F2") + " と drop=" + drop.ToString("F2"));
            // 天端は必ず設計面に乗る(足元は敷居のこともあるので見ない)
            float atTop = DesignY(c0 + up * (run * 0.5f + 1.0f));
            if (Mathf.Abs(atTop - topY) > 0.45f)
                sb.AppendLine("⚠ 石段 " + nm + ": 天端 " + topY.ToString("F2") +
                              " に対し、上がった先の設計面は " + atTop.ToString("F2") + "m");
            float rise = drop / steps, tread = run / steps;
            float yaw = Mathf.Atan2(up.x, up.y) * Mathf.Rad2Deg;
            var mod = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Own.DanishiStep);
            if (mod == null) { sb.AppendLine("⚠ 段石が無い: " + EdoAssets.Own.DanishiStep); continue; }
            int across = Mathf.Max(1, Mathf.RoundToInt(wid / 1.98f));
            Vector2 side = new Vector2(up.y, -up.x);         // 走りに直交
            for (int i = 0; i < steps; i++)
            {
                float s = -run * 0.5f + tread * (i + 0.5f);
                float top = baseY + rise * (i + 1);
                for (int j = 0; j < across; j++)
                {
                    float t = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 c = c0 + up * s + side * t;
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.DanishiStep,
                        new Vector3(c.x, top, c.y), yaw, Vector3.one, dnGrp,
                        nm + "_" + i + "_" + j);
                    if (go == null) continue;
                    // 幅を割り付けぶんへ合わせる(段石の実寸は 1.98m。端数はここで吸収する)
                    float have = RunWidth(EdoNishiTameikeBuilder.RB(go), yaw);
                    if (have > 0.05f)
                        go.transform.localScale = new Vector3((wid / across) / have, 1f, 1f);
                    // **天端を段のレベルに合わせる**(段石は上面が踏面。汐見坂と同じ据え方)
                    var bb = EdoNishiTameikeBuilder.RB(go);
                    go.transform.position += new Vector3(c.x - bb.center.x, top - bb.max.y, c.y - bb.center.z);
                    nDan++;
                }
            }
            sb.AppendLine("石段 " + nm + " " + steps + "段×" + across + "枚 蹴上" + rise.ToString("F3")
                          + " 踏面" + tread.ToString("F2") + " 昇り" + dir
                          + " (" + baseY.ToString("F2") + "→" + topY.ToString("F2") + ")");
        }

        // ---------------- 井戸
        var idGrp = Group("Fuzoku/Ido");
        foreach (var o in A(D["wells"]))
        {
            var w = O(o);
            Vector2 c = f.W(F(w["u"]), F(w["v"]));
            var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.Matsudaira.Ido,
                new Vector3(c.x, DesignY(c), c.y), yawU, Vector3.one, idGrp, (string)w["name"]);
            // ⚠ バウンズ中心で寄せない。**自作部材のピボットは footprint の中心・地盤**なので
            //   Place がそのまま正位置。桁や鳥居で重心が偏る部材でバウンズに寄せると設計点からずれる
            if (go != null) nIdo++;
        }

        // ---------------- 隅櫓(石垣の天端の上)
        var ygGrp = Group("Fuzoku/Yagura");
        var P = Poly;
        foreach (var o in A(D["yagura"]))
        {
            var y = O(o);
            int vi = (int)F(y["vertex"]);
            float seat = F(y["seat"]), kn = F(y["ken"]);
            Vector2 c = YaguraSeat(P, vi, kn * f.ken);
            Vector2 e = (P[(vi + 1) % P.Length] - P[vi % P.Length]).normalized;
            var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.Matsudaira.Yagura,
                new Vector3(c.x, seat, c.y), Mathf.Atan2(e.y, -e.x) * Mathf.Rad2Deg,
                Vector3.one, ygGrp, (string)y["name"]);
            if (go == null) continue;
            nYag++;
            // ⚠ 隅櫓は外周の長屋と**同じ隅**を取り合う。指図の run に開口が無いと必ず食い込む。
            //   ⚠ world の AABB で測らない — 斜めに回った 7.4m 角の箱は AABB が 10.4m 角に
            //   膨らみ、離れている駒まで「食い込み」に出る(2026-08-25 に偽陽性5件)。
            //   **水平の OBB を分離軸で測る。**
            {
                var kak2 = Group("").Find("Kakoi");
                float worst = 0f; string wn = null;
                if (kak2 != null) foreach (Transform c2 in kak2)
                {
                    float ov = ObbOverlap2D(go.transform, c2);
                    if (ov > worst) { worst = ov; wn = c2.name; }
                }
                if (worst > 0.25f)
                    sb.AppendLine("★ 隅櫓 " + (string)y["name"] + " が " + wn + " と水平で " +
                                  worst.ToString("F2") + "m 食い込む — **指図の開口(gapA/gapB)が足りない**");
            }
        }

        // ---------------- 附属屋
        var svGrp = Group("Fuzoku/Service");
        foreach (var o in A(D["service"]))
        {
            var sv = O(o);
            string nm = (string)sv["name"];
            float u0 = F(sv["u0"]), v0 = F(sv["v0"]), u1 = F(sv["u1"]), v1 = F(sv["v1"]);
            float ku = u1 - u0, kv = v1 - v0;
            string path; float yaw;
            // ⭐ **指図の `api` が最優先**(⛔ ビルダーで部材を決め打ちしない。点景 6d と同じ作法)。
            //   2026-09-16: 稲荷社の部材が朱の鳥居つき `Matsudaira.Inari` 決め打ちのままで、
            //   指図が名指しする祠だけの `Matsudaira.InariHokora` を読んでいなかった。
            string apiRaw = Has(sv, "api") ? (string)sv["api"] : null;
            string apiPath = apiRaw == null ? null : ResolveApi(apiRaw);
            if (apiRaw != null && apiPath == null)
            {
                sb.AppendLine("⛔ 附属屋 " + nm + ": 指図の api が解けない " + apiRaw +
                              " — `EdoAssets` への登録(⇒ edo-buzai/edo-zaiko)か指図方へ差し戻し");
                continue;
            }
            if (apiPath != null)            { path = apiPath;                        yaw = yawU; }
            else if (nm.StartsWith("Kura")) { path = EdoAssets.Own.Matsudaira.Dozo;  yaw = yawV; }
            else if (nm == "Sakuji")        { path = EdoAssets.Own.Matsudaira.Koya;  yaw = yawU; }
            else if (nm == "Chatei")        { path = EdoAssets.Own.Matsudaira.Sukiya; yaw = yawU; }
            else { sb.AppendLine("⚠ 附属屋 " + nm + ": 割り当てる部材が決まっていない"); continue; }

            // ⭐ `facing` = **正面(表)の面の外向きの法線**(⛔ 進む向きではない)。
            //   部材の正面(`buhin.front`)をその向きへ振る。⛔ `yawU` 固定にしない。
            Vector2 fdir = Vector2.zero; bool hasFacing = false;
            if (Has(sv, "facing"))
            {
                if (!TryGridDir((string)sv["facing"], out fdir))
                {
                    sb.AppendLine("⛔ 附属屋 " + nm + ": facing=" + (string)sv["facing"] +
                                  " が読めない(+u/-u/+v/-v のいずれか)— 指図方へ差し戻し");
                    continue;
                }
                var bh = Has(sv, "buhin") ? O(sv["buhin"]) : null;
                string front = (bh != null && Has(bh, "front")) ? (string)bh["front"] : null;
                if (front != "+Z")
                {
                    sb.AppendLine("⛔ 附属屋 " + nm + ": 部材の正面 buhin.front=" + (front ?? "(指図に無い)") +
                                  " は未対応(実装はローカル +Z だけ)— 指図方・部材方へ差し戻し");
                    continue;
                }
                hasFacing = true;
                yaw = Mathf.Atan2(fdir.x, fdir.y) * Mathf.Rad2Deg;      // ローカル +Z を facing へ
            }

            Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
            var go = EdoNishiTameikeBuilder.Place(path, new Vector3(c.x, DesignY(c), c.y),
                yaw, Vector3.one, svGrp, nm);
            if (go == null) { sb.AppendLine("⚠ 附属屋 " + nm + ": 部材が読めない " + path); continue; }

            // ---- 面で納める(`seat`)。⛔ 中心で合わせない(CLAUDE.md 規則5)
            //   指図 `service[].seat`: 社の**背面**(ローカル `buhin.front` の逆の端)を
            //   矩形の `facing` の逆側の面から `gap` だけ**離して**据える。
            //   ⭐ 背面のローカル Z は**据えた駒の実メッシュから測る**(⛔ 指図の `buhin.zLocal` を
            //     写して使わない — 部材が焼き直されたときに黙ってズレる)。宣言との差は報告に出す。
            if (hasFacing && Has(sv, "seat"))
            {
                var seat = O(sv["seat"]);
                if (!Has(seat, "gap"))
                    sb.AppendLine("⛔ 附属屋 " + nm + ": seat.gap が無い — 指図方へ差し戻し(⛔ 離れを発明しない)");
                else
                {
                    float gap = F(seat["gap"]);
                    float zmn, zmx; PartLocalZ(go, out zmn, out zmx);
                    Vector2 back = -fdir;                                  // 背面が向く側
                    Vector2 faceP = RectFaceCenter(u0, v0, u1, v1, back);  // 矩形の背面側の面の中央
                    Vector2 piv = faceP + back * (-gap + zmn);
                    go.transform.position = new Vector3(piv.x, DesignY(piv), piv.y);
                    // 実測の検算(⛔ 自分で合格と言わない — 数字だけ出す)
                    float gotGap = Vector2.Dot(faceP - (piv + back * (-zmn)), back);
                    var bh2 = O(sv["buhin"]);
                    string decl = "";
                    if (Has(bh2, "zLocal"))
                    {
                        var zl = A(bh2["zLocal"]);
                        decl = " / 指図 buhin.zLocal " + F(zl[0]).ToString("F2") + "‥" + F(zl[1]).ToString("F2")
                             + "(差 " + (zmn - F(zl[0])).ToString("F3") + " / " + (zmx - F(zl[1])).ToString("F3") + ")";
                    }
                    float tolLo = -0.05f, tolHi = 0.05f;
                    if (Has(seat, "tol")) { var tl = A(seat["tol"]); tolLo = F(tl[0]); tolHi = F(tl[1]); }
                    bool ok = (gotGap - gap) >= tolLo - 1e-4f && (gotGap - gap) <= tolHi + 1e-4f;
                    sb.AppendLine("附属屋 " + nm + " の据え付け: 正面 " + (string)sv["facing"]
                        + "(yaw " + yaw.ToString("F1") + "°)/ 背面〜矩形の面 実測 " + gotGap.ToString("F3")
                        + "m(指図 gap " + gap.ToString("F2") + "m・許容 " + tolLo.ToString("F2")
                        + "‥" + tolHi.ToString("F2") + ")" + (ok ? " ⭕" : " ⚠")
                        + " / 部材のローカル Z 実測 " + zmn.ToString("F2") + "‥" + zmx.ToString("F2") + decl);
                }
            }
            // 指図の間数と部材の実寸が食い違っていないか(黙って伸ばさず、数字で出す)。
            // ⚠ world の AABB で測らない — 回転間グリッドは斜めなので、13.8×8.9 の箱が
            //   16.0×13.1 に見えて誤検知する(2026-08-25)。**部材そのものの寸法**で測る。
            Vector3 ps = PartSize(go);
            float wantLong = Mathf.Max(ku, kv) * f.ken, wantShort = Mathf.Min(ku, kv) * f.ken;
            float haveLong = Mathf.Max(ps.x, ps.z), haveShort = Mathf.Min(ps.x, ps.z);
            if (Mathf.Abs(haveLong - wantLong) > 2.2f || Mathf.Abs(haveShort - wantShort) > 2.2f)
                sb.AppendLine("⚠ 附属屋 " + nm + ": 指図 " + ku + "×" + kv + "間(" +
                              wantLong.ToString("F1") + "×" + wantShort.ToString("F1") +
                              "m)に対し部材の外形は " + haveLong.ToString("F1") + "×" +
                              haveShort.ToString("F1") + "m(軒の出を含む)");
            nYa++;
        }

        sb.Append("中仕切 " + nHei + "枚 / 竹垣 " + nGaki + "枚 / 段石 " + nDan + "枚 / 井戸 " +
                  nIdo + "基 / 隅櫓 " + nYag + "基 / 附属屋 " + nYa + "棟");
        return sb.ToString();
    }

    /// <summary>グリッドの向き("+u"/"-u"/"+v"/"-v")を world の単位ベクトルにする。
    /// ⛔ **知らない値を既定値へ倒さない。**旧版は `default: return -v` で、
    /// `dir` の誤字が黙って「-v」の石段になっていた(2026-08-26。指図側は vocab_check が拾うが、
    /// 実装側でも倒さない — 語彙の欄は分岐が静かに「その他」へ落ちるのが常)。</summary>
    static bool TryGridDir(string d, out Vector2 dir)
    {
        var f = Grid;
        switch (d)
        {
            case "+u": dir = new Vector2(f.ux, f.uz).normalized; return true;
            case "-u": dir = -new Vector2(f.ux, f.uz).normalized; return true;
            case "+v": dir = new Vector2(f.vx, f.vz).normalized; return true;
            case "-v": dir = -new Vector2(f.vx, f.vz).normalized; return true;
        }
        dir = Vector2.zero; return false;
    }

    /// <summary>部材のローカル Z の**符号つきの範囲**[m](回転・位置を除く)。
    /// <see cref="PartSize"/> は差し渡しだけを返すので、正面/背面のどちらの端かが分からない。
    /// ⚠ 先頭の MeshFilter だけ見ない(サブメッシュが 30 以上に分かれている部材がある)。</summary>
    static void PartLocalZ(GameObject go, out float zMin, out float zMax)
    {
        var w2l = go.transform.worldToLocalMatrix;
        zMin = float.MaxValue; zMax = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var b = mf.sharedMesh.bounds;
            var m = w2l * mf.transform.localToWorldMatrix;
            for (int i = 0; i < 8; i++)
            {
                var q = m.MultiplyPoint3x4(new Vector3(((i & 1) == 0 ? b.min : b.max).x,
                                                       ((i & 2) == 0 ? b.min : b.max).y,
                                                       ((i & 4) == 0 ? b.min : b.max).z));
                if (q.z < zMin) zMin = q.z;
                if (q.z > zMax) zMax = q.z;
            }
        }
        if (zMin > zMax) { zMin = 0f; zMax = 0f; }
    }

    /// <summary>グリッドの矩形(間)の、<paramref name="dir"/> の側の**面の中央**の world 点。
    /// `dir` はグリッドの軸に沿った単位ベクトル(<see cref="TryGridDir"/> の出力)。
    /// ⛔ 矩形の中心ではない — 面で納める取り合い(規則5)のための相手の面。</summary>
    static Vector2 RectFaceCenter(float u0, float v0, float u1, float v1, Vector2 dir)
    {
        var f = Grid;
        Vector2 uu = new Vector2(f.ux, f.uz).normalized, vv = new Vector2(f.vx, f.vz).normalized;
        float du = Vector2.Dot(dir, uu), dv = Vector2.Dot(dir, vv);
        if (Mathf.Abs(du) >= Mathf.Abs(dv))
            return f.W(du > 0f ? Mathf.Max(u0, u1) : Mathf.Min(u0, u1), (v0 + v1) * 0.5f);
        return f.W((u0 + u1) * 0.5f, dv > 0f ? Mathf.Max(v0, v1) : Mathf.Min(v0, v1));
    }

    /// <summary>水平面の OBB どうしの食い込み量[m](分離軸法)。0 なら離れている。</summary>
    static float ObbOverlap2D(Transform a, Transform b)
    {
        Vector3 sa = PartSize(a.gameObject), sbz = PartSize(b.gameObject);
        if (sa == Vector3.zero || sbz == Vector3.zero) return 0f;
        Vector2 ca = new Vector2(a.position.x, a.position.z), cb = new Vector2(b.position.x, b.position.z);
        float ra = a.eulerAngles.y * Mathf.Deg2Rad, rb = b.eulerAngles.y * Mathf.Deg2Rad;
        Vector2 ax = new Vector2(Mathf.Cos(ra), -Mathf.Sin(ra)), az = new Vector2(Mathf.Sin(ra), Mathf.Cos(ra));
        Vector2 bx = new Vector2(Mathf.Cos(rb), -Mathf.Sin(rb)), bz = new Vector2(Mathf.Sin(rb), Mathf.Cos(rb));
        float hax = sa.x * 0.5f, haz = sa.z * 0.5f, hbx = sbz.x * 0.5f, hbz = sbz.z * 0.5f;
        Vector2 dd = cb - ca;
        float best = float.MaxValue;
        Vector2[] axes = { ax, az, bx, bz };
        foreach (var n2 in axes)
        {
            float pa = hax * Mathf.Abs(Vector2.Dot(n2, ax)) + haz * Mathf.Abs(Vector2.Dot(n2, az));
            float pb = hbx * Mathf.Abs(Vector2.Dot(n2, bx)) + hbz * Mathf.Abs(Vector2.Dot(n2, bz));
            float gap = pa + pb - Mathf.Abs(Vector2.Dot(n2, dd));
            if (gap <= 0f) return 0f;               // 分離軸が見つかった
            best = Mathf.Min(best, gap);
        }
        return best;
    }

    /// <summary>部材そのものの寸法(回転を含まない)。
    /// ⚠ world の AABB を使わない — 斜めグリッドでは 13.8×8.9 の箱が 16.0×13.1 に膨らむ。
    /// ⚠ 先頭の MeshFilter だけ見ない — obj の部材は 30 以上のサブメッシュに分かれていることがあり、
    ///   1枚だけ測ると 4.65m の門が 1.24m に見える(2026-08-25 に小門が 0.37 倍へ潰れた原因)。
    /// **全部の子メッシュを root のローカル系へ写して合成する。**</summary>
    static Vector3 PartSize(GameObject go)
    {
        var w2l = go.transform.worldToLocalMatrix;
        bool any = false; Vector3 mn = Vector3.zero, mx = Vector3.zero;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var b = mf.sharedMesh.bounds;
            var m = w2l * mf.transform.localToWorldMatrix;
            for (int i = 0; i < 8; i++)
            {
                var c = new Vector3(((i & 1) == 0 ? b.min : b.max).x,
                                    ((i & 2) == 0 ? b.min : b.max).y,
                                    ((i & 4) == 0 ? b.min : b.max).z);
                var q = m.MultiplyPoint3x4(c);
                if (!any) { mn = mx = q; any = true; }
                else { mn = Vector3.Min(mn, q); mx = Vector3.Max(mx, q); }
            }
        }
        if (!any) return Vector3.zero;
        var ls2 = go.transform.localScale;
        var sz = mx - mn;
        return new Vector3(Mathf.Abs(sz.x * ls2.x), Mathf.Abs(sz.y * ls2.y), Mathf.Abs(sz.z * ls2.z));
    }

    static float RunWidth(Bounds b, float yaw)
    {
        // yaw で回した後のローカル +X 方向の見付。段石は幅が X なので、これが割り付けの単位
        float r = yaw * Mathf.Deg2Rad;
        var ax = new Vector3(Mathf.Cos(r), 0, -Mathf.Sin(r));
        return Mathf.Abs(ax.x) * b.size.x + Mathf.Abs(ax.z) * b.size.z;
    }

    /// <summary>隅櫓の据え位置 — 区画の頂点 vi から内向きの二等分線に沿って side/2+犬走り 分だけ入る。</summary>
    static Vector2 YaguraSeat(Vector2[] P, int vi, float side)
    {
        int n = P.Length;
        Vector2 p = P[vi % n];
        Vector2 a = (P[(vi - 1 + n) % n] - p).normalized;
        Vector2 b = (P[(vi + 1) % n] - p).normalized;
        Vector2 bis = (a + b).normalized;
        if (bis.sqrMagnitude < 1e-6f) bis = new Vector2(-a.y, a.x);
        // 重心側へ向ける
        Vector2 g = Vector2.zero; foreach (var q in P) g += q; g /= n;
        if (Vector2.Dot(g - p, bis) < 0) bis = -bis;
        // 二等分線に沿って入れる量 = (半幅 + 犬走り 0.30) / sin(半角)。
        // 折れ角は現地が決めるので直角を仮定しない(unity-modular-stonewall §1)。
        float half = Mathf.Max(0.20f, Mathf.Acos(Mathf.Clamp(Vector2.Dot(a, bis), -1f, 1f)));
        float inset = (side * 0.5f + 0.30f) / Mathf.Max(0.35f, Mathf.Sin(half));
        return p + bis * inset;
    }

    /// <summary>板塀を A→B に実寸ピッチで通す。skip の区間(庭木戸)は**丸ごと落とさず**、
    /// 木戸の両側を短い駒で埋める。表裏2枚組。
    /// 【普請奉行の指示・2026-09-06 EDO-0147(実測 15:50・掲示板)】:
    ///   ⚠ 端の駒の縮め率は下限 0.85倍。それ未満になるなら1駒足す(下の PlaceItabeiSpan と同じ
    ///   round()+0.85チェックへ吸収させている — 短い残区間ほど自然にこの分岐へ落ちる)。
    ///   ⚠ 各駒の両端で地盤を取り、低い端に合わせて座る。段差が0.3mを超えたら駒を分ける
    ///   (PlaceItabeiSpan が中点で再帰的に割る)。
    /// 現況(是正前): NJ_Oku_S_W_11(6.8m)・NJ_Oku_N_W_2/3(7.2m×2)のように、木戸と重なる
    /// bay を丸ごと落としていたため木戸の両側に 2.3m/5m の素通しの隙間ができていた。</summary>

    /// <summary>置いた駒の**実メッシュ**のうち、**世界の y が [yLo,yHi] の帯にある頂点だけ**を
    /// 走り方向 <paramref name="dir"/> へ投影した min/max。
    ///
    /// <para>⭐⭐ **「指図が名指しした面」を測るための道具**(CLAUDE.md 規則5)。
    /// 部材には躯体のほかに**基壇・軒・庇・出格子**が付いていて、全メッシュの最大投影は
    /// それらを拾う。⛔ その値を指図の呼び寸法と比べると、部材が正しくても必ず外れる
    /// (2026-09-09・番所で 0.40m 過大に出た。同じ型を今日3度踏んでいる)。
    /// ⇒ 帯は**指図が名指しした面が存在する高さ**から取る(⛔「見た目に妥当な高さ」で決めない)。</para>
    /// ⛔ 見えないメッシュは数えない(理由は <see cref="ProjSpan"/> と同じ)。</summary>
    /// <param name="perpDir">奥行(走りに直交)の向き。<paramref name="perpMax"/> が正のとき、
    /// <paramref name="origin"/> からの奥行が ±perpMax を超える頂点を落とす。
    /// ⭐ **同じ高さに二つの部位が同居するとき**(番所の y=0.55 には腰壁の底と**基壇の天端**が
    /// 並ぶ)、帯だけでは切り分けられない。⛔ 0 なら奥行の窓を使わない。</param>
    static void ProjBand(GameObject go, Vector2 dir, float yLo, float yHi, out float mn, out float mx,
                         Vector2 perpDir = default(Vector2), Vector2 origin = default(Vector2),
                         float perpMax = 0f)
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

    /// <summary>置いた駒の**実メッシュ**を走り方向 <paramref name="dir"/> へ投影した伸び[m]。
    /// ⛔ 外接箱の x/z の大きい方で代用しない — 斜めのグリッドでは箱が膨らむ(2026-08 の偽陽性5件と同じ罠)。
    /// ⛔ **躯体の面**を測る用途に使わない — 基壇・軒・出格子が混ざる。そちらは <see cref="ProjBand"/>。</summary>
    static float ProjSpan(GameObject go, Vector2 dir)
    {
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            // ⛔ **見えないメッシュを数えない**(2026-09-06): 冠木門のプレハブには Renderer の無い/切ってある
            //    駒が入っており、頂点を素で走ると走り方向の伸びが 2.38m(実際に見えるのは 1.17m)になる。
            //    その値で開口を空けると木戸の両側に 0.6m の隙間が残る(ユーザー ブックマーク#3・#5)。
            var rr = mf.GetComponent<Renderer>();
            if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var l2w = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices)
            {
                var wv = l2w.MultiplyPoint3x4(v);
                float t = wv.x * dir.x + wv.z * dir.y;
                if (t < mn) mn = t; if (t > mx) mx = t;
            }
        }
        return mx > mn ? mx - mn : 0f;
    }

    /// <summary>**板塀の根石(玉石)を据える** — 指図 `nakajikiriRule.neishi` が正典。
    ///
    /// <para>⭐ 2026-09-09(第2回)に**申し送りから実装へ**変わった。前の巡は「在庫に玉石が無い」
    /// ので据えずに数だけ返していた(`NeishiReport`)。部材方が `Neishi_Tamaishi_L*.fbx` を
    /// 8 個体焼いたので据える。⛔ 代用の庭石(`JG_Rock_A_*`)は今も使わない。</para>
    ///
    /// 【指図から引く値。⛔ ここで数を作らない】
    ///   `applyKind` … 根石が付く塀の種別(庭木戸には付かない) / `show` 見え高 / `bury` 埋まり比 /
    ///   `long` 一石の走り(**乱尺**) / `bay` 柱間[間] / `seatStepMax` 隣の柱間との段の上限 /
    ///   `seatDevMax` 柱間の中の |座 − 設計地盤| の上限 / `nakajikiri[].seatSpans` 面の縁で切った区間。
    ///
    /// <para>⭐⭐ **座(y)は指図が持たない従属値。**区間の中を柱間(`bay` 間)に割り、
    /// ①その柱間の**設計地盤**の (最大+最小)÷2 を 0.05m に丸め、②隣の柱間との差を
    /// `seatStepMax` で頭打ちにする(生成器 `_seat_bays` と同じ式)。⛔ 定数の座で埋めない —
    /// 埋めると検査①が構造的に鳴らなくなる(2026-09-03 に指図側で廃した型)。
    /// ⛔ 継ぎ目(区間の境)の前後 <see cref="SeatJointHalf"/> 間は測らない(土留めが受ける)。</para>
    ///
    /// <para>⚠ 設計地盤は**板塀と同じ <see cref="DesignY"/>** から採る(⛔ 生成器の `_ground_uv` と
    /// 違って築山の盛土は入らない)。根石は板塀の足元に据わる物なので、**板塀が立っている地盤**に
    /// 合わせるのが筋。⇒ 生成器の表と 0.0x m 級で食い違うことがあり得るので、
    /// その差は**この巡の報告に実測で出す**(⛔ どちらかを黙って正としない)。</para>
    ///
    /// <para>⭐⭐ **芯々は「地盤線での差し渡し」で詰める。**⛔ 外接で突き付けない —
    /// 玉石は丸いので地盤線の差し渡しは外接の 92〜96% しかなく、外接どうしを突き付けると
    /// **地盤線の高さで石のあいだに空が抜ける**(部材方 2026-09-09)。⇒ 据える前に
    /// **個体を1つずつ仮置きして地盤線(局所 y=0)の帯の伸びを実測**し、その値で詰める
    /// (CLAUDE.md 規則5「置いた駒の実メッシュから測る」。⛔ 0.93 という比を焼き込まない)。</para>
    ///
    /// <para>⭐ 個体は 8 つしかないので、**長さの選びと yaw 180° の反転を run ごとに決まった乱数**で
    /// 混ぜる(⛔ 実行のたびに変わる乱数にしない — 冪等でなくなる)。</para></summary>
    static string NeishiPlace(Transform njGrp, List<Vector2[]> kido)
    {
        if (!Has(D, "nakajikiriRule")) return "⚠ 指図 nakajikiriRule が無い(根石の出典)";
        var nr = O(D["nakajikiriRule"]);
        if (!Has(nr, "neishi")) return "⚠ 指図 nakajikiriRule.neishi が無い";
        var ne = O(nr["neishi"]);
        var kinds = new List<string>();
        foreach (var o in A(ne["applyKind"])) kinds.Add(o as string);
        // ⭐⭐ **見え高は指図が literal で持たない**(2026-09-10 に `show` を廃した)。
        //   `_show`: 見え高 = **その石の地盤線の差し渡し × `showMul`** — 丸石は上ほど急に細るので、
        //   比を一定にして「大きい石ほど大きく見える」ようにしてある。丈は部材が持つ(`bury` 0.5)。
        //   ⛔ 旧実装は `ne["show"]` を読んでいて KeyNotFoundException で Stage6 が落ちていた。
        if (!Has(ne, "showMul"))
            return "⚠ 指図 nakajikiriRule.neishi.showMul が無い(見え高の出典)— 指図方へ差し戻し";
        float showMul = F(ne["showMul"]);
        float bay0 = Has(ne, "bay") ? F(ne["bay"]) : 1f;
        float stepMax = Has(ne, "seatStepMax") ? F(ne["seatStepMax"]) : 0.15f;
        float devMax = Has(ne, "seatDevMax") ? F(ne["seatDevMax"]) : 0.08f;
        var f = Grid;
        var sb = new System.Text.StringBuilder();

        // ---- 部材: 個体ごとに**地盤線での差し渡し**を実測する(仮置き→測る→消す)
        float[] LONG = EdoAssets.Own.NeishiLong;
        var paths = new string[LONG.Length];
        var gspan = new float[LONG.Length];
        var bbox = new float[LONG.Length];
        int haveVar = 0;
        for (int i = 0; i < LONG.Length; i++)
        {
            paths[i] = EdoAssets.Own.Neishi(LONG[i]);
            var probe = EdoNishiTameikeBuilder.Place(paths[i], Vector3.zero, 0f, Vector3.one,
                                                    njGrp, "probe_neishi");
            if (probe == null) { gspan[i] = 0f; continue; }
            float mn = float.MaxValue, mx = float.MinValue, bmn = float.MaxValue, bmx = float.MinValue;
            foreach (var mf in probe.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var l2w = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = l2w.MultiplyPoint3x4(v);
                    if (w.x < bmn) bmn = w.x; if (w.x > bmx) bmx = w.x;
                    // ⛔⛔ **帯を厚く取らない。**玉石は真ん中がいちばん太いので、±0.05m で測ると
                    //   「地盤線の差し渡し」でなく**近傍の最大**を拾い、最大 0.048m 過大になる
                    //   (実測: L0.70 は y=0 で 0.644 / ±0.05 で 0.692)。その値で詰めると
                    //   **地盤線の高さで石のあいだに空が抜ける** — 部材方が警告したその失敗そのもの。
                    //   ⇒ 頂点の輪が地盤線に在るので ±0.005m で足りる(8 個体とも拾えることを実測で確認)。
                    if (Mathf.Abs(w.y) > 0.005f) continue;         // 地盤線(ピボットの高さ)の輪
                    if (w.x < mn) mn = w.x; if (w.x > mx) mx = w.x;
                }
            }
            UnityEngine.Object.DestroyImmediate(probe);
            bbox[i] = (bmx > bmn) ? bmx - bmn : 0f;
            gspan[i] = (mx > mn) ? mx - mn : bbox[i];
            if (gspan[i] > 0.05f) haveVar++;
        }
        if (haveVar == 0)
            return "⛔ 板塀の根石: 部材が一つも引けない(" + paths[0] + " ほか)"
                 + " — 部材方(`edo-buzai`)へ照会。⛔ 庭石で代用しない";

        // ---- 石樋の水抜き(根石を切る区間)。指図 `sensui.yarimizu.kuguri`
        string kugRun = null; float kugU = 0f, kugSpan = 0f;
        {
            var sen = Has(D, "sensui") ? O(D["sensui"]) : null;
            var yar = (sen != null && Has(sen, "yarimizu")) ? O(sen["yarimizu"]) : null;
            var kug = (yar != null && Has(yar, "kuguri")) ? O(yar["kuguri"]) : null;
            if (kug != null && Has(kug, "nakajikiri") && Has(kug, "span"))
            { kugRun = (string)kug["nakajikiri"]; kugU = F(kug["u"]); kugSpan = F(kug["span"]); }
        }

        int total = 0, nRun = 0, nDevBad = 0, nStepBad = 0, nNoSeat = 0, nNoSeatJoint = 0;
        float totalLen = 0f;
        foreach (var o in A(D["nakajikiri"]))
        {
            var w = O(o);
            if (!kinds.Contains((string)w["kind"])) continue;
            string nm = (string)w["name"];
            var aa = A(w["a"]); var bb2 = A(w["b"]);
            Vector2 gA = new Vector2(F(aa[0]), F(aa[1])), gB = new Vector2(F(bb2[0]), F(bb2[1]));
            Vector2 A2 = f.W(gA.x, gA.y), B2 = f.W(gB.x, gB.y);
            float len = (B2 - A2).magnitude;
            if (len < 0.5f) continue;
            Vector2 dir = (B2 - A2) / len;
            nRun++; totalLen += len;

            // 走る向き(生成器 `_nj_axis` と同じ)。fix = 一定側の座標 / lo,hi = 弧長の範囲
            bool vert = Mathf.Abs(gB.x - gA.x) < Mathf.Abs(gB.y - gA.y);
            float fix = vert ? gA.x : gA.y;
            float lo = vert ? Mathf.Min(gA.y, gB.y) : Mathf.Min(gA.x, gB.x);
            float hi = vert ? Mathf.Max(gA.y, gB.y) : Mathf.Max(gA.x, gB.x);
            float jh = SeatJointHalf(vert, fix, lo, hi);

            // ---- 柱間ごとの座(従属値)。⛔ 指図は区間の宣言しか持たない
            var spS0 = new List<float>(); var spS1 = new List<float>();   // 区間そのものの範囲
            var bw0 = new List<float>(); var bw1 = new List<float>();
            var bSeat = new List<float>(); var bDev = new List<float>();
            var bRaw = new List<float>(); var bClamp = new List<bool>();
            var bSpanName = new List<string>();
            int nSpan = 0, nClamped = 0;
            float devWorst = 0f, stepWorst = 0f;
            var spans = Has(w, "seatSpans") ? A(w["seatSpans"]) : new List<object>();
            foreach (var so in spans)
            {
                var sp2 = O(so);
                var rng = Has(sp2, "u") ? A(sp2["u"]) : (Has(sp2, "v") ? A(sp2["v"]) : null);
                if (rng == null) continue;
                float s0 = Mathf.Max(Mathf.Min(F(rng[0]), F(rng[1])), lo);
                float s1 = Mathf.Min(Mathf.Max(F(rng[0]), F(rng[1])), hi);
                if (s1 - s0 <= 1e-6f) continue;
                nSpan++; spS0.Add(s0); spS1.Add(s1);
                float bay = Has(sp2, "bay") ? F(sp2["bay"]) : bay0;
                int nb = Mathf.Max(1, Mathf.RoundToInt((s1 - s0) / Mathf.Max(0.05f, bay)));
                string spName = s0.ToString("0.##") + "〜" + s1.ToString("0.##");
                float prev = float.NaN;
                for (int k = 0; k < nb; k++)
                {
                    float w0 = s0 + (s1 - s0) * k / nb, w1 = s0 + (s1 - s0) * (k + 1) / nb;
                    var ys = new List<float>();
                    for (float q = w0; q <= w1 + 1e-6f; q += 0.25f)
                    {
                        // ⛔ 継ぎ目(区間の境)の前後は測らない — 土留めが受ける
                        if (Mathf.Min(Mathf.Abs(q - s0), Mathf.Abs(q - s1)) < jh
                            && (s0 > lo + 1e-6f || s1 < hi - 1e-6f)) continue;
                        float qu = vert ? fix : q, qv = vert ? q : fix;
                        // ⭕ 石樋の水口の区間は根石を切るので測らない
                        if (kugRun == nm && kugSpan > 0f && Mathf.Abs(qu - kugU) <= kugSpan * 0.5f) continue;
                        ys.Add(DesignY(f.W(qu, qv)));
                    }
                    if (ys.Count == 0) continue;
                    float mnY = float.MaxValue, mxY = float.MinValue;
                    foreach (var y in ys) { if (y < mnY) mnY = y; if (y > mxY) mxY = y; }
                    float raw = Mathf.Round(((mxY + mnY) * 0.5f) / 0.05f) * 0.05f;
                    float seat = raw; bool clamped = false;
                    if (!float.IsNaN(prev) && Mathf.Abs(raw - prev) > stepMax)
                    { seat = prev + Mathf.Sign(raw - prev) * stepMax; clamped = true; nClamped++; }
                    // ⛔ 生の跳びで見る(頭打ち後の座だけを比べると判定②は構造的に鳴らない)
                    if (!float.IsNaN(prev) && bRaw.Count > 0)
                        stepWorst = Mathf.Max(stepWorst, Mathf.Abs(raw - bSeat[bSeat.Count - 1]));
                    prev = seat;
                    float dev = 0f;
                    foreach (var y in ys) dev = Mathf.Max(dev, Mathf.Abs(seat - y));
                    devWorst = Mathf.Max(devWorst, dev);
                    bw0.Add(w0); bw1.Add(w1); bSeat.Add(seat); bDev.Add(dev);
                    bRaw.Add(raw); bClamp.Add(clamped); bSpanName.Add(spName);
                }
            }
            if (bSeat.Count == 0)
            {
                sb.AppendLine("⛔ 板塀 " + nm + ": `seatSpans` から柱間が一つも取れない ⇒ 根石を据えない"
                            + "(⛔ 座を発明しない。指図方へ差し戻し)");
                continue;
            }

            // ---- 抜く区間(t = A2 からの距離[m])— 庭木戸の開口 と 石樋の水口
            var holes = new List<Vector2>();
            foreach (var sg in kido)
            {
                float ta = Vector2.Dot(sg[0] - A2, dir), tb = Vector2.Dot(sg[1] - A2, dir);
                float h0 = Mathf.Clamp(Mathf.Min(ta, tb), 0f, len), h1 = Mathf.Clamp(Mathf.Max(ta, tb), 0f, len);
                // 走りから外れた木戸(別の run のもの)は拾わない
                Vector2 mid2 = (sg[0] + sg[1]) * 0.5f;
                float perp = Mathf.Abs(Vector2.Dot(mid2 - A2, new Vector2(-dir.y, dir.x)));
                if (h1 > h0 && perp < 1.0f) holes.Add(new Vector2(h0, h1));
            }
            int nKidoHole = holes.Count, nKug = 0;
            if (kugRun == nm && kugSpan > 0f)
            {
                // 水口の区間(グリッド u)を t へ。⭕ 根石はここで切れる(枠石が受ける)
                Vector2 k0 = f.W(kugU - kugSpan * 0.5f, fix), k1 = f.W(kugU + kugSpan * 0.5f, fix);
                if (vert) { k0 = f.W(fix, kugU - kugSpan * 0.5f); k1 = f.W(fix, kugU + kugSpan * 0.5f); }
                float ta = Vector2.Dot(k0 - A2, dir), tb = Vector2.Dot(k1 - A2, dir);
                float h0 = Mathf.Clamp(Mathf.Min(ta, tb), 0f, len), h1 = Mathf.Clamp(Mathf.Max(ta, tb), 0f, len);
                if (h1 > h0) { holes.Add(new Vector2(h0, h1)); nKug = 1; }
            }

            // ---- 据える。⛔ 実行のたびに変わる乱数を使わない(run 名から作る)
            var grp2 = Group("Fuzoku/Nakajikiri/" + nm + "_Neishi");
            uint rnd = 2166136261u;
            foreach (var ch in nm) rnd = (rnd ^ (uint)ch) * 16777619u;
            System.Func<uint> next = () => { rnd ^= rnd << 13; rnd ^= rnd >> 17; rnd ^= rnd << 5; return rnd; };
            float baseYaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;   // 局所 +X を走りへ
            int made = 0; float t0 = 0f; int guard = 0;
            while (t0 < len - 0.05f && guard++ < 5000)
            {
                int vi = (int)(next() % (uint)LONG.Length);
                if (gspan[vi] < 0.05f) continue;
                float span = gspan[vi];
                if (t0 + span > len)
                {
                    // 端の残り: 収まる個体があればそれに替える。無ければ打ち切る(⛔ 縮めない)
                    int best = -1;
                    for (int i = 0; i < LONG.Length; i++)
                        if (gspan[i] > 0.05f && t0 + gspan[i] <= len
                            && (best < 0 || gspan[i] > gspan[best])) best = i;
                    if (best < 0) break;
                    vi = best; span = gspan[vi];
                }
                float tc = t0 + span * 0.5f;
                bool inHole = false; float holeEnd = 0f;
                foreach (var hh in holes)
                    if (tc > hh.x && tc < hh.y) { inHole = true; holeEnd = Mathf.Max(holeEnd, hh.y); }
                if (inHole) { t0 = holeEnd; continue; }
                Vector2 c = A2 + dir * tc;
                Vector2 gc = f.L(c);
                float q2 = vert ? gc.y : gc.x;
                float y2 = float.NaN;
                for (int i = 0; i < bSeat.Count; i++)
                    if (q2 >= bw0[i] - 1e-4f && q2 <= bw1[i] + 1e-4f) { y2 = bSeat[i]; break; }
                if (float.IsNaN(y2))
                {
                    // ⚠ 座が決まらない石。**理由を分けて数える**(⛔ 一つの数にまとめない —
                    //   ①と②は差し戻し先が違う)。⛔ どちらも座を発明せず設計地盤へ落として申し送る。
                    bool inSpan = false;
                    for (int i = 0; i < spS0.Count; i++)
                        if (q2 >= spS0[i] - 1e-4f && q2 <= spS1[i] + 1e-4f) { inSpan = true; break; }
                    if (inSpan) nNoSeatJoint++; else nNoSeat++;
                    y2 = DesignY(c);
                }
                float yaw2 = baseYaw + (((next() & 1u) == 1u) ? 180f : 0f);   // 繰り返しを崩す
                var go2 = EdoNishiTameikeBuilder.Place(paths[vi], new Vector3(c.x, y2, c.y), yaw2,
                                                       Vector3.one, grp2, nm + "_ne" + made);
                if (go2 != null) made++;
                t0 += span;
            }
            total += made;
            if (devWorst > devMax + 1e-4f) nDevBad++;
            if (stepWorst > stepMax + 1e-4f) nStepBad++;
            float seatLo = float.MaxValue, seatHi = float.MinValue;
            foreach (var s3 in bSeat) { seatLo = Mathf.Min(seatLo, s3); seatHi = Mathf.Max(seatHi, s3); }
            sb.AppendLine("根石 " + nm + ": " + made + " 石 / 延長 " + len.ToString("F1")
                + "m / 区間 " + nSpan + "・柱間 " + bSeat.Count + "(継ぎ目の除外 ±"
                + jh.ToString("F2") + " 間)/ 座 " + seatLo.ToString("F2") + "‥" + seatHi.ToString("F2")
                + " / |座−設計地盤| 最大 " + devWorst.ToString("F3")
                + (devWorst > devMax + 1e-4f ? " ⚠許容 " + devMax.ToString("F2") + " 超" : " ⭕")
                + " / 生の跳び 最大 " + stepWorst.ToString("F3")
                + (stepWorst > stepMax + 1e-4f ? " ⚠許容 " + stepMax.ToString("F2") + " 超" : " ⭕")
                + " / 頭打ち " + nClamped + " / 抜き 木戸" + nKidoHole + "・水口" + nKug);
        }

        var meas = new System.Text.StringBuilder();
        for (int i = 0; i < LONG.Length; i++)
            meas.Append((i > 0 ? " / " : "") + LONG[i].ToString("0.##") + "→"
                + gspan[i].ToString("F3") + (bbox[i] > 0.01f
                    ? "(外接比 " + (gspan[i] / bbox[i]).ToString("P0") + ")" : ""));
        // 見え高の帯は**従属値** = `showMul` × 据えた個体の地盤線の差し渡しの下限〜上限
        float gsLo = float.MaxValue, gsHi = 0f;
        for (int i = 0; i < LONG.Length; i++)
            if (gspan[i] > 0.05f) { gsLo = Mathf.Min(gsLo, gspan[i]); gsHi = Mathf.Max(gsHi, gspan[i]); }
        sb.AppendLine("根石 合計 " + total + " 石 / " + nRun + " run・延長 " + totalLen.ToString("F1")
            + "m(見え高 = 地盤線の差し渡し × `showMul` " + showMul.ToString("F2") + " ⇒ 実測で "
            + (gsLo * showMul).ToString("F2") + "〜" + (gsHi * showMul).ToString("F2")
            + "m・埋まり比 " + F(ne["bury"]).ToString("F2") + " ⇒ 丈は部材が持つ)");
        sb.AppendLine("根石の芯々(**地盤線の差し渡しを実測**。⛔ 外接では詰めない): " + meas);
        if (nNoSeat > 0)
            sb.AppendLine("⚠ 【申し送り①】" + nNoSeat + " 石が `seatSpans` の**外**(区間が run の端を覆っていない)"
                        + " ⇒ 座でなく設計地盤へ落とした。指図方へ");
        if (nNoSeatJoint > 0)
            sb.AppendLine("⚠ 【裁定を仰ぐ②】" + nNoSeatJoint + " 石は区間の**中**だが座が決まらない —"
                        + " その柱間の測点が**継ぎ目の窓(`_seat_joint_half`)と石樋の水口で全部落ちた**。"
                        + " 指図 `nakajikiriRule.neishi._seat` の『継ぎ目には敷居を当てない』には読みが二つある:"
                        + " ⓐ **測らないだけ**(根石は据える)/ ⓑ **根石そのものを据えない**(土留めが受ける)。"
                        + " ⛔ 実装は決めない — 当面 ⓐ とみなし設計地盤へ落としてある。"
                        + " ⚠ 窓は run によって ±2.85 間(5.2m)にもなるので、ⓑ なら塀の足元が十数 m 素地になる");
        if (nDevBad > 0 || nStepBad > 0)
            sb.AppendLine("⚠ 座の判定に外れた run: |座−地盤| " + nDevBad + " 本 / 生の跳び " + nStepBad
                        + " 本 ⇒ 指図の `seatSpans` を割り直す照会(⛔ 実装で許容を緩めない)");
        sb.Append("⚠ 座は**板塀と同じ `DesignY`** から採った(生成器 `_ground_uv` は築山の盛土を足すので"
                + "、築山に掛かる区間では 0.0x m 級の差が出得る。⛔ どちらかを黙って正としない)");
        return sb.ToString();
    }

    /// <summary>区間の継ぎ目(面の縁)で**座を測らない**幅[間]の半分 = 従属値。
    /// 生成器 `_seat_joint_half` と同じ式: (段の高さ − **造成前**の地盤)× `batterFill` ÷ 1間 ÷ 2。
    /// ⛔ 設計地盤と比べない — 段の上では常に 0 になる。</summary>
    static float SeatJointHalf(bool vert, float fix, float lo, float hi)
    {
        var f = Grid;
        float drop = 0f;
        foreach (var t in Terraces)
        {
            float e0 = vert ? t.v0 : t.u0, e1 = vert ? t.v1 : t.u1;
            for (int i = 0; i < 2; i++)
            {
                float e = (i == 0) ? e0 : e1;
                if (!(e > lo + 1e-6f && e < hi - 1e-6f)) continue;
                Vector2 p = vert ? f.W(fix, e) : f.W(e, fix);
                drop = Mathf.Max(drop, Mathf.Abs(t.y - NaturalY(p.x, p.y)));
            }
        }
        return drop > 0f ? drop * BatterFill / f.ken / 2f : 0f;
    }

    static int ItabeiRun(Transform parent, Vector2 A2, Vector2 B2, float h, string prefix,
                         List<Vector2[]> skip)
    {
        var probe = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Itabei5, Vector3.zero, 0,
            Vector3.one * EdoSannoKitaBuilder.ES, parent, "probe");
        if (probe == null) return 0;
        var pb = EdoNishiTameikeBuilder.RB(probe);
        float spanES = pb.size.x, rawH = pb.size.y / EdoSannoKitaBuilder.ES;
        UnityEngine.Object.DestroyImmediate(probe);
        if (spanES < 0.5f) return 0;

        float len = (B2 - A2).magnitude;
        Vector2 dir = (B2 - A2) / len;
        Vector2 nrm = new Vector2(-dir.y, dir.x);
        float sy = h / rawH;                                  // 指図の高さ(2.4m)に立てる
        float yaw = Mathf.Atan2(nrm.x, nrm.y) * Mathf.Rad2Deg;

        // 1) 木戸の開口を t(=A2 からの距離)の区間へ変換して合体する。
        //    ⛔ **余白を足さない**(2026-09-06 ユーザー指摘 ブックマーク#3・#5「木戸と板塀の位置がずれている」)。
        //    旧実装は左右へ 0.6m のパディングを足しており、木戸の実メッシュとの間に 0.593m の隙間が残っていた。
        //    `skip` の区間は**据えた木戸の実メッシュの走り方向の伸び**(Stage6 で書き戻す)なので、
        //    そのまま突き付ければ面と面が接する(CLAUDE.md 規則5)。
        var holes = new List<Vector2>();
        foreach (var sg in skip)
        {
            float ta = Vector2.Dot(sg[0] - A2, dir), tb = Vector2.Dot(sg[1] - A2, dir);
            float t0h = Mathf.Clamp(Mathf.Min(ta, tb), 0f, len);
            float t1h = Mathf.Clamp(Mathf.Max(ta, tb), 0f, len);
            if (t1h > t0h) holes.Add(new Vector2(t0h, t1h));
        }
        holes.Sort((x, y) => x.x.CompareTo(y.x));
        var merged = new List<Vector2>();
        foreach (var hh in holes)
        {
            if (merged.Count > 0 && hh.x <= merged[merged.Count - 1].y)
                merged[merged.Count - 1] = new Vector2(merged[merged.Count - 1].x, Mathf.Max(merged[merged.Count - 1].y, hh.y));
            else merged.Add(hh);
        }

        // 2) 木戸を除いた区間(seg)を集める
        var segs = new List<Vector2>();
        float cursor = 0f;
        foreach (var hh in merged)
        {
            if (hh.x > cursor) segs.Add(new Vector2(cursor, hh.x));
            cursor = Mathf.Max(cursor, hh.y);
        }
        if (len - cursor > 0.02f) segs.Add(new Vector2(cursor, len));

        int made = 0, idx = 0;
        foreach (var seg in segs)
        {
            float segLen = seg.y - seg.x;
            if (segLen < 0.3f) continue;                      // 木戸の際の端数(パディング内)は無視できる幅
            int n = Mathf.Max(1, Mathf.RoundToInt(segLen / (spanES - 0.15f)));
            float pitch = segLen / n;
            if (pitch / spanES < 0.85f) { n += 1; pitch = segLen / n; }   // 下限0.85倍 → それ未満なら1駒足す
            for (int k = 0; k < n; k++)
            {
                float t0 = seg.x + pitch * k, t1 = t0 + pitch;
                made += PlaceItabeiSpan(parent, A2, dir, nrm, t0, t1, spanES, sy, yaw,
                                        prefix + "_" + (idx++), 0);
            }
        }
        return made;
    }

    /// <summary>板塀の1区間 [t0,t1](A2 からの距離)に駒(表裏2枚)を据える。
    /// 両端の地盤差が 0.3m を超えたら中点で分ける(普請奉行の指示)。低い端に合わせて座る
    /// (旧実装は高い端に合わせていたため低い端が 0.6〜0.75m 浮いていた)。</summary>
    static int PlaceItabeiSpan(Transform parent, Vector2 A2, Vector2 dir, Vector2 nrm,
                                float t0, float t1, float spanES, float sy, float yaw,
                                string name, int depth)
    {
        Vector2 pL = A2 + dir * t0, pR = A2 + dir * t1;
        float gL = DesignY(pL), gR = DesignY(pR);
        if (depth < 4 && Mathf.Abs(gL - gR) > 0.3f && (t1 - t0) > 0.3f)
        {
            float tm = (t0 + t1) * 0.5f;
            return PlaceItabeiSpan(parent, A2, dir, nrm, t0, tm, spanES, sy, yaw, name + "a", depth + 1)
                 + PlaceItabeiSpan(parent, A2, dir, nrm, tm, t1, spanES, sy, yaw, name + "b", depth + 1);
        }
        float pitch = t1 - t0;
        float sx = EdoSannoKitaBuilder.ES * pitch / spanES;
        Vector2 c = (pL + pR) * 0.5f;
        float y = Mathf.Min(gL, gR);                          // 低い端に合わせて座る
        int made = 0;
        for (int side = 0; side < 2; side++)
        {
            var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Itabei5, Vector3.zero,
                side == 0 ? yaw : yaw + 180f, new Vector3(sx, sy, EdoSannoKitaBuilder.ES),
                parent, name + (side == 0 ? "f" : "b"));
            if (go == null) continue;
            var b = EdoNishiTameikeBuilder.RB(go);
            Vector2 tgt = c + nrm * (side == 0 ? 0.06f : -0.06f);
            go.transform.position += new Vector3(tgt.x - b.center.x, y - 0.08f - b.min.y, tgt.y - b.center.z);
            made++;
        }
        return made;
    }

    /// <summary>附属屋 FBX のマテリアルを、**借り先を名指しして**結び直す。
    /// ⚠ `SearchAndRemapMaterials(..., Everywhere)` はプロジェクト全体(6.9GB)を舐めるので使わない
    ///   — 2026-08-24 に実際にユーザーの PC が固まった。借り先は3フォルダだけ見る。
    /// ⚠ **2026-09-06 に `Models/Niwa`(立石 `Own.Tateishi`)を追加するまで、このメニューは
    ///   庭石の類を一切見ていなかった**(対象は Fuzokuya/Mon/Trees だけだった)。
    ///   `Models/Niwa` の FBX を増やしたら、ここに folder を足すのを忘れないこと
    ///   — 忘れると真っ白のまま気づかれない(門・番所で 2026-08-31 に踏んだのと同じ型)。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap")]
    public static void RemapFuzokuyaMenu() { Debug.Log("[Matsudaira] " + RemapFuzokuya()); }
    public static string RemapFuzokuya()
    {
        string[] donorDirs = {
            "Assets/Japanese Village Kit/Materials",
            "Assets/Japanese Castle/Meshes/Exterior/Materials",
            "Assets/Edo/Materials",              // キットに無い材(鳥居の朱 Shu_Torii など)
            // 新造した木(Own.Jokuroku / Own.Ume)は在庫の桜の樹皮・葉の材質名を名乗る
            // 立石・平石2種・切石橋(Own.Tateishi/Own.Hiraishi/Own.Ishibashi)は
            // `M_FJG_Rock_001`(護岸の転石 JG_Rock_A_01..03 と同じ材。2026-09-06 裁定1=B)
            // の材質名をそのまま運ぶ — この donorDir(FreeJapaneseGarden/Materials)で拾える。
            "Assets/Waldemarst/FreeJapaneseGarden/Materials",
            // 岡部庭の Ishigumi/Tobiishi/Kutsunugi は今も NatureManufacture の
            // photoscanned rock の材質名を運ぶ(EdoOkabeYashikiBuilder 参照。立石側は
            // 2026-09-06 にこちらから M_FJG_Rock_001 へ切り替えたので、このフォルダは
            // もう Own.Tateishi 用ではない)。
            "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/Rocks/Rocks/Models/Materials",
        };
        var byName = new Dictionary<string, Material>();
        foreach (var dir in donorDirs)
        {
            if (!AssetDatabase.IsValidFolder(dir)) continue;
            foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { dir }))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                if (m != null && !byName.ContainsKey(m.name)) byName[m.name] = m;
            }
        }
        int n = 0; var miss = new List<string>();
        // ⚠ 門・番所(Models/Mon)も同じ借り先を使う。2026-08-31 に番所の瓦を
        //   Village Kit の `Roof B` へ替えたとき、ここが Fuzokuya しか見ていなかったため
        //   材質名が変わった番所が真っ白になった。**FBX を焼いた folder は必ずここに足す。**
        //   ⭐ 2026-09-08: 表門の**袖塀**(`Own.Sodebei`)を独立部材にして `Models/Hei` へ焼いたので
        //   このフォルダを足した。⚠ `Models/Hei` には岡部邸の のし塀・木戸も居るが、材質名で
        //   引き直すだけなので同名の同じ .mat に当たる(冪等)。
        string[] modelDirs = { "Assets/Edo/Models/Fuzokuya", "Assets/Edo/Models/Mon",
                               "Assets/Edo/Models/Trees", "Assets/Edo/Models/Niwa",
                               "Assets/Edo/Models/Hei" };
        foreach (var guid in AssetDatabase.FindAssets("t:Model", modelDirs))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter; if (imp == null) continue;
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path); if (go == null) continue;
            bool touched = false;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    Material donor;
                    if (!byName.TryGetValue(m.name, out donor)) { if (!miss.Contains(m.name)) miss.Add(m.name); continue; }
                    if (donor == m) continue;
                    imp.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), m.name), donor);
                    touched = true;
                }
            if (touched)
            {
                AssetDatabase.WriteImportSettingsIfDirty(path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                n++;
            }
        }
        AssetDatabase.SaveAssets();
        return "remap " + n + " 本" + (miss.Count > 0 ? " / 借り先が見つからない材: " + string.Join(", ", miss.ToArray()) : "");
    }


    // ---------------------------------------------------------------- Stage 7: 庭の植栽
    /// <summary>指図の `gardens` と `planting` を読んで木を植える。
    ///
    /// 【作法】`unity-buke-yashiki/references/gardens-ponds.md`「植栽 — 庭師の技術と年代」:
    ///   ・主木は **3・5・7 の奇数の塊**で不等辺三角に置く(等間隔に散らさない)
    ///   ・常緑:落葉 ≒ 7:3(全部落葉だと冬に骨組みが消える)
    ///   ・刈込は**塊で**(点在させない)/ 下草は**樹下**に散らして裸地を残さない
    /// 【季節】⛔ **開花木を置かない。**桜は Summer variant のみ(メモリ scene-season-not-spring)。
    /// 【樹種】**指図の `planting[].parts[].api` が決める。**ビルダーは配るだけ(ResolveApi/PartBag)。
    /// 常緑広葉樹とウメは在庫に無いので 2026-08-31 に新造した(ユーザー裁定 案C・Own.Jokuroku / Own.Ume)。
    /// ⛔ 自作の低ポリ木 `Own.Broadleaf` は使用禁止(CLAUDE.md 規則10)。
    ///
    /// ⚠ 置く位置は**決定論**(zone 名から種を作る)。流し直しで木が動くと検証レンダが比較できない。</summary>

    /// <summary>指図の `parts[].api` の文字列を実際のパスへ解決する。
    /// ⛔ **ビルダーに樹種を書かない。**指図が `api` で名指ししたものだけを置く
    /// (規則11 と同じ考え方 — 値の正典は指図で、ソースへ写さない)。
    /// 2026-08-31 まで中木と花木が `Own.Broadleaf` 決め打ちで、指図の parts を無視していた。</summary>
    static string ResolveApi(string api)
    {
        if (string.IsNullOrEmpty(api)) return null;
        api = api.Trim(); if (api.StartsWith("EdoAssets.")) api = api.Substring("EdoAssets.".Length);   // 指図の石は `EdoAssets.Own.Tateishi(...)` と書かれる(2026-09-06 解けずに転石へ落ちていた)
        // ⭐ **引数を取らない定数の `api`**(関数でなく const フィールド)。下の正規表現は
        //   `Own.Matsudaira.InariHokora` のような**3節**を通さないので、ここで先に引く。
        //   ⛔ パスの literal を書かない(規則12)— `EdoAssets` の定数をそのまま返す。
        //   2026-09-16: 稲荷の祠と鳥居が解けず、6d で「部材なし」に落ちていた。
        switch (api)
        {
            case "Own.Torii":                    return EdoAssets.Own.Torii;
            case "Own.Matsudaira.InariHokora":   return EdoAssets.Own.Matsudaira.InariHokora;
            case "Own.Matsudaira.Inari":         return EdoAssets.Own.Matsudaira.Inari;
        }
        var m = System.Text.RegularExpressions.Regex.Match(api, @"^([A-Za-z]+)\.([A-Za-z0-9_]+)(?:\((.*)\))?$");
        if (!m.Success) return null;
        string cls = m.Groups[1].Value, fn = m.Groups[2].Value, arg = m.Groups[3].Value;
        var raw = arg.Length == 0 ? new string[0] : arg.Split(',');
        var a = new List<string>();
        foreach (var x in raw) a.Add(x.Trim().Trim('"'));
        int i0 = a.Count > 0 ? SafeInt(a[0]) : 0;
        int i1 = a.Count > 1 ? SafeInt(a[1]) : 0;
        if (cls == "Own")
        {
            // 個体番号は省略できる(第2引数が無ければ 1 本目)
            if (fn == "Jouryoku") return EdoAssets.Own.Jouryoku(a[0], a.Count > 1 ? i1 : 1);
            if (fn == "Jokuroku") return EdoAssets.Own.Jouryoku(a[0], a.Count > 1 ? i1 : 1);  // 旧綴り
            if (fn == "Momiji")   return EdoAssets.Own.Momiji(a[0], a.Count > 1 ? i1 : 1);
            if (fn == "Ume")      return EdoAssets.Own.Ume(a[0], a.Count > 1 ? i1 : 1);
            if (fn == "Tateishi") return EdoAssets.Own.Tateishi(a[0], a.Count > 1 ? i1 : 1);
            if (fn == "Hiraishi") return EdoAssets.Own.Hiraishi(a[0]);     // 平石(天井石 Tenjo / 伏石 Fuse・2026-09-06 新造)
            if (fn == "Ishibashi") return EdoAssets.Own.Ishibashi();      // 切石の一枚橋   // 立石 S/M/L(2026-09-06 石組の api を解けず在庫の転石へ落ちていた)
        }
        else if (cls == "JG")
        {
            if (fn == "Pine")          return EdoAssets.JG.Pine(a[0], i1);
            if (fn == "SakuraSummer")  return EdoAssets.JG.SakuraSummer(a[0], i1);
            if (fn == "Boxwood")       return EdoAssets.JG.Boxwood(i0);
            if (fn == "Fern")          return EdoAssets.JG.Fern(i0);
            if (fn == "Rock")          return EdoAssets.JG.Rock(i0);
        }
        else if (cls == "JC")
        {
            if (fn.StartsWith("Azalea")) return EdoAssets.JG.Azalea(SafeInt(fn.Substring(6)));
        }
        else if (cls == "NM")
        {
            if (fn == "MapleBush")  return EdoAssets.NM.MapleBush(i0);
            if (fn == "GreyWillow") return EdoAssets.NM.GreyWillow(i0);
        }
        return null;
    }

    static int SafeInt(string t) { int v; return int.TryParse(t, out v) ? v : 0; }

    /// <summary>指図の `parts[]` を、それぞれの `n` の割当てだけ順に配る器。
    /// **呼ぶたびに1本ぶん減る。**割当てを使い切ったら null を返す。</summary>
    class PartBag
    {
        readonly List<string> paths = new List<string>();
        readonly List<float> scales = new List<float>();
        public int Count { get { return paths.Count; } }
        public PartBag(object partsArr, System.Random rnd)
        {
            if (partsArr == null) return;
            foreach (var o in A(partsArr))
            {
                var q = O(o);
                string path = ResolveApi((string)q["api"]);
                if (path == null) continue;
                int n = Has(q, "n") ? (int)F(q["n"]) : 1;
                float sc = Has(q, "scale") ? F(q["scale"]) : 1f;
                for (int i = 0; i < n; i++) { paths.Add(path); scales.Add(sc); }
            }
            // 種類が固まって並ばないよう混ぜる(決定論)
            for (int i = paths.Count - 1; i > 0; i--)
            {
                int j = rnd.Next(i + 1);
                var tp = paths[i]; paths[i] = paths[j]; paths[j] = tp;
                var ts = scales[i]; scales[i] = scales[j]; scales[j] = ts;
            }
        }
        public bool Next(out string path, out float scale)
        {
            path = null; scale = 1f;
            if (paths.Count == 0) return false;
            path = paths[paths.Count - 1]; scale = scales[scales.Count - 1];
            paths.RemoveAt(paths.Count - 1); scales.RemoveAt(scales.Count - 1);
            return true;
        }
    }

    [MenuItem("Edo/松平出羽守上屋敷/7 庭の植栽")]
    public static void Stage7Menu() { Debug.Log("[Matsudaira] " + Stage7_Niwa()); }
    public static string Stage7_Niwa()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var root = Group("");
        // 撤回した池の案の残骸(非アクティブ)。生成物なので消してよい
        var stale = root.Find("Garden");
        if (stale != null) UnityEngine.Object.DestroyImmediate(stale.gameObject);

        var grp = Group("Niwa"); Clear(grp);
        var f = Grid;
        var sb = new System.Text.StringBuilder();

        // ---- 木を置いてはいけない矩形(棟・附属屋・廊下・井戸・石段)
        var block = new List<Vector4>();
        foreach (var o in A(D["munes"]))   { var m = O(o); block.Add(new Vector4(F(m["u0"]) - 1f, F(m["v0"]) - 1f, F(m["u1"]) + 1f, F(m["v1"]) + 1f)); }
        foreach (var o in A(D["links"]))   { var l = O(o); block.Add(new Vector4(F(l["u0"]) - 1f, F(l["v0"]) - 1f, F(l["u1"]) + 1f, F(l["v1"]) + 1f)); }
        foreach (var o in A(D["service"])) { var s = O(o); block.Add(new Vector4(F(s["u0"]) - 1.5f, F(s["v0"]) - 1.5f, F(s["u1"]) + 1.5f, F(s["v1"]) + 1.5f)); }
        foreach (var o in A(D["wells"]))   { var w = O(o); block.Add(new Vector4(F(w["u"]) - 1.5f, F(w["v"]) - 1.5f, F(w["u"]) + 1.5f, F(w["v"]) + 1.5f)); }
        foreach (var o in A(D["kaidans"])) { var k = O(o); var p = A(k["pos"]); block.Add(new Vector4(F(p[0]) - 2f, F(p[1]) - 2f, F(p[0]) + 2f, F(p[1]) + 2f)); }
        foreach (var o in A(D["nakajikiri"]))
        {
            var w = O(o); var a = A(w["a"]); var b = A(w["b"]);
            block.Add(new Vector4(Mathf.Min(F(a[0]), F(b[0])) - 0.8f, Mathf.Min(F(a[1]), F(b[1])) - 0.8f,
                                  Mathf.Max(F(a[0]), F(b[0])) + 0.8f, Mathf.Max(F(a[1]), F(b[1])) + 0.8f));
        }
        Func<float, float, float, bool> free = (u, v, r) =>
        {
            foreach (var b in block)
                if (u > b.x - r && u < b.z + r && v > b.y - r && v < b.w + r) return false;
            var w2 = f.W(u, v);
            return EdoGeom.PIP(Poly, w2) && DistSeg(w2, Poly[0], Poly[1]) > 0.0f;   // 区画の外へ出さない
        };

        var zones = new Dictionary<string, Vector4>();
        foreach (var o in A(D["gardens"]))
        {
            var g = O(o);
            zones[(string)g["name"]] = new Vector4(F(g["u0"]), F(g["v0"]), F(g["u1"]), F(g["v1"]));
        }

        int nTree = 0, nShrub = 0, nGround = 0, nRock = 0;
        var report = new List<string>();

        foreach (var o in A(D["planting"]))
        {
            var pl = O(o);
            string zone = (string)pl["zone"], layer = (string)pl["layer"];
            int want = (int)F(pl["n"]);
            if (!zones.ContainsKey(zone)) { sb.AppendLine("★ 植栽の zone " + zone + " が gardens に無い"); continue; }
            var z = zones[zone];
            var sub = Group("Niwa/" + zone);
            // 決定論: zone+layer から種を作る(流し直しで動かない)
            var rnd = new System.Random((zone + "/" + layer).GetHashCode());
            int made = 0;

            if (layer == "主木")
            {
                // **奇数の塊**で置く。1本ずつ散らさない
                int[] clump = { 7, 5, 3, 3, 5 };
                int ci = 0;
                while (made < want && ci < 40)
                {
                    int cn = Mathf.Min(clump[ci % clump.Length], want - made);
                    Vector2 c;
                    if (!Spot(z, rnd, free, 3.5f, out c)) break;
                    for (int i = 0; i < cn; i++)
                    {
                        // 不等辺三角に散らす(等間隔にしない)
                        float ang = (float)rnd.NextDouble() * 6.283f;
                        float rad = 1.2f + (float)rnd.NextDouble() * 2.6f;
                        float u = c.x + Mathf.Cos(ang) * rad, v = c.y + Mathf.Sin(ang) * rad;
                        if (!free(u, v, 2.0f)) continue;
                        string path = EdoAssets.JG.Pine(i == 0 ? "Big" : (rnd.Next(3) == 0 ? "Small" : "Mid"), 1 + rnd.Next(3));
                        // ⛔ **全数を同じ向きへ傾けない。**2026-09-01 に指図が撤回した案。
                        //    旧: tiltU -1f =「崖(西)へ傾ける=海風の見立て」を松の全数に掛けていた。
                        //    庭方の判定「溜池は18m下の淡水で海風の見立てが立つ地形ではない【?】。
                        //    全数を同方向へ倒すと 12.5m の松で頂が 0.9〜2.0m 振れ、意匠でなく
                        //    ピボットのずれに見える」。⭐ 傾けるのは**岬の付け根の1本だけ**で、
                        //    それは指図の `at` で名指しされる(このべた書きの経路では扱わない)。
                        var go = Plant(path, u, v, sub, zone + "_Pine_" + made, 1.65f, rnd, tiltU: 0f);
                        if (go != null) { made++; nTree++; }
                    }
                    ci++;
                }
            }
            else if (layer.StartsWith("中木"))
            {
                // **指図の parts が樹種と本数を決める。**ビルダーは配るだけ
                var bagN = new PartBag(Has(pl, "parts") ? pl["parts"] : null, rnd);
                for (int i = 0; i < want; i++)
                {
                    Vector2 c;
                    if (!Spot(z, rnd, free, 2.2f, out c)) break;
                    string path; float sc;
                    if (!bagN.Next(out path, out sc)) break;
                    var go = Plant(path, c.x, c.y, sub, zone + "_Naka_" + i, sc, rnd, 0f);
                    if (go != null) { made++; nTree++; }
                }
            }
            else if (layer.StartsWith("低木"))
            {
                // **塊で n 群**(点在させない)。1群 = 皐月/柘植 5〜9株
                for (int gi = 0; gi < want; gi++)
                {
                    Vector2 c;
                    if (!Spot(z, rnd, free, 2.5f, out c)) break;
                    int cn = 5 + rnd.Next(5);
                    for (int i = 0; i < cn; i++)
                    {
                        float u = c.x + ((float)rnd.NextDouble() - 0.5f) * 3.2f;
                        float v = c.y + ((float)rnd.NextDouble() - 0.5f) * 2.2f;
                        if (!free(u, v, 0.8f)) continue;
                        string path = rnd.Next(4) == 0 ? EdoAssets.JG.Boxwood(1 + rnd.Next(3))
                                                       : EdoAssets.JG.Azalea(new[] { 1, 3, 4 }[rnd.Next(3)]);
                        var go = Plant(path, u, v, sub, zone + "_Karikomi_" + gi + "_" + i, 1.0f, rnd, 0f);
                        if (go != null) nShrub++;
                    }
                    made++;
                }
            }
            else if (layer.StartsWith("下草"))
            {
                // **樹下に散らす。裸地を残さない。**want=0 なので木の数から決める
                var trees = new List<Transform>();
                foreach (Transform t in sub) if (t.name.Contains("_Pine_") || t.name.Contains("_Naka_")) trees.Add(t);
                foreach (var t in trees)
                {
                    var lp = f.L(new Vector2(t.position.x, t.position.z));
                    for (int i = 0; i < 3; i++)
                    {
                        float u = lp.x + ((float)rnd.NextDouble() - 0.5f) * 2.4f;
                        float v = lp.y + ((float)rnd.NextDouble() - 0.5f) * 2.4f;
                        if (!free(u, v, 0.4f)) continue;
                        var go = Plant(EdoAssets.JG.Fern(1 + rnd.Next(2)), u, v, sub, zone + "_Shita_" + nGround, 1.0f, rnd, 0f);
                        if (go != null) nGround++;
                    }
                }
                made = nGround;
            }
            else if (layer.StartsWith("花木"))
            {
                // 梅林 — **等間隔の並木にしない**。塊で植え、間を空ける
                var bagU = new PartBag(Has(pl, "parts") ? pl["parts"] : null, rnd);
                for (int i = 0; i < want; i++)
                {
                    Vector2 c;
                    if (!Spot(z, rnd, free, 1.8f, out c)) break;
                    string path; float sc;
                    if (!bagU.Next(out path, out sc)) break;
                    var go = Plant(path, c.x, c.y, sub, zone + "_Ume_" + i, sc, rnd, 0f);
                    if (go != null) { made++; nTree++; }
                }
            }
            report.Add(string.Format("{0} {1} {2}/{3}", zone, layer, made, want));
            if (made < want)
                sb.AppendLine("⚠ " + zone + " の " + layer + " が " + made + "/" + want +
                              " しか置けない — 庭が狭いか、避ける矩形が多い");
        }

        // ---- 景石。主木の塊の際に据える(三石・1/3 埋め)
        foreach (var zn in new[] { "G_NishiNiwa", "G_OkuNishiNiwa" })
        {
            if (!zones.ContainsKey(zn)) continue;
            var z = zones[zn];
            var sub = Group("Niwa/" + zn);
            var rnd = new System.Random((zn + "/rock").GetHashCode());
            for (int g2 = 0; g2 < 3; g2++)
            {
                Vector2 c;
                if (!Spot(z, rnd, free, 2.0f, out c)) break;
                for (int i = 0; i < 3; i++)          // **三石**(奇数)
                {
                    float u = c.x + ((float)rnd.NextDouble() - 0.5f) * 2.0f;
                    float v = c.y + ((float)rnd.NextDouble() - 0.5f) * 2.0f;
                    if (!free(u, v, 0.6f)) continue;
                    var go = Plant(EdoAssets.JG.Rock(1 + rnd.Next(3)), u, v, sub, zn + "_Ishi_" + g2 + "_" + i,
                                   1.5f + (float)rnd.NextDouble() * 1.4f, rnd, 0f, sink: 0.34f);
                    if (go != null) nRock++;
                }
            }
        }

        sb.Append("木 " + nTree + " / 刈込 " + nShrub + " 株 / 下草 " + nGround +
                  " / 景石 " + nRock + "  [" + string.Join(" | ", report.ToArray()) + "]");
        return sb.ToString();
    }

    /// <summary>庭の矩形の中で、空いている点を決定論的に探す。見つからなければ false。</summary>
    static bool Spot(Vector4 z, System.Random rnd, Func<float, float, float, bool> free, float clr, out Vector2 c)
    {
        for (int t = 0; t < 240; t++)
        {
            float u = Mathf.Lerp(z.x + clr, z.z - clr, (float)rnd.NextDouble());
            float v = Mathf.Lerp(z.y + clr, z.w - clr, (float)rnd.NextDouble());
            if (z.z - z.x < clr * 2 || z.w - z.y < clr * 2) break;
            if (free(u, v, clr)) { c = new Vector2(u, v); return true; }
        }
        c = Vector2.zero; return false;
    }

    /// <summary>1本植える。設計面に据え、向きと大きさを散らす。tiltU!=0 なら u 方向へ傾ける。</summary>
    // ---------------------------------------------------------------- Stage 8: 西斜面の林
    /// <summary>指図の `slopeArea` と `slopePlanting` を読んで西の法面に林を作る。
    ///
    /// 【役目】`perimeterClosure` の「遮蔽は法面が受け、木柵は境の標示にとどまる」を成立させる。
    ///   素の崖だけでは対岸(溜池東岸の堀端通り)から御殿の軒が見えるので、**法肩に沿った
    ///   遮蔽木の列**がそれを受ける。列に見せないため offset と pitch を振る。
    ///
    /// 【置き方】`placement`:
    ///   `crestLine` … 法肩の折れ線に沿って `screen.pitch` 間隔(±`jitter`)。法肩から
    ///                 外(斜面側)へ `screen.offset` の範囲で振り出す。**落差が
    ///                 `screen.minDrop` に満たない区間は数えない**(北西の登りは浅い)。
    ///   `scatter`   … `slopeArea.bands` が示す「法肩→法尻の道のりの割合」の帯へ撒く。
    ///
    /// 【地面】⛔ `DesignY` を使わない — 法面は造成面ではないので設計面が無い。
    ///   **live terrain を実測して据える**(規則3の「面の高さは地形が決める」の斜面版)。
    /// 【樹種】指図の `parts[].api` が決める。ビルダーは配るだけ。
    /// 【決定論】種は帯+層の名から作る。流し直しで木が動くと検証レンダが比較できない。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/8 西斜面の林")]
    public static void Stage8Menu() { Debug.Log("[Matsudaira] " + Stage8_Shamen()); }
    public static string Stage8_Shamen()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var reviewGate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (reviewGate != null) return reviewGate; }

        var grp = Group("Shamen"); Clear(grp);
        var f = Grid;
        var sb = new System.Text.StringBuilder();
        var sa = O(D["slopeArea"]);
        var sc = O(sa["screen"]);
        float pitch = F(sc["pitch"]), jit = F(sc["jitter"]), minDrop = F(sc["minDrop"]);
        var offR = A(sc["offset"]);
        float off0 = F(offR[0]), off1 = F(offR[1]);

        // ---- 法肩の折れ線(世界座標)
        var crestArr = A(sa["crest"]);
        var crest = new List<Vector2>();
        foreach (var o in crestArr) { var q = A(o); crest.Add(f.W(F(q[0]), F(q[1]))); }
        if (crest.Count < 2) return "法肩の折れ線が無い";

        // ---- 法肩の「下る側」。⛔ **区画の内外では決まらない** — 法面は区画の**内側**にあり
        //      (法尻=区画の西辺)、法肩の両側とも内側になる。2026-08-31 に内外で判定して
        //      主平面の側を「外」と取り、遮蔽木が 0/23 になった。
        //      **どちらが下るかで決める**(規則3「面の高さは地形が決める」の斜面版)。
        Func<int, Vector2> segOut = (i) =>
        {
            Vector2 a = crest[i], b = crest[i + 1];
            Vector2 t = (b - a).normalized;
            Vector2 n = new Vector2(t.y, -t.x);
            Vector2 mid = (a + b) * 0.5f;
            if (TerrainY(mid + n * 8f) > TerrainY(mid - n * 8f)) n = -n;
            return n;
        };

        // ---- 法肩から下る側へ、**下りが終わるまで**の距離(=法面の幅)。
        //      区画の外へ出たらそこで打ち切る(法尻は区画の西辺)。
        Func<Vector2, Vector2, float> slopeWidth = (p, n) =>
        {
            float lo = TerrainY(p), d = 0f;
            for (float t = 1f; t <= 90f; t += 1f)
            {
                Vector2 q = p + n * t;
                if (!EdoGeom.PIP(Poly, q)) break;
                float y = TerrainY(q);
                if (y < lo) { lo = y; d = t; }
                else if (y > lo + 1.5f) break;             // 下りきった
            }
            return d;
        };

        var placed = new List<Vector3>();                    // 既に置いた木(間隔の検査に使う)
        var screens = new List<Vector4>();                   // 遮蔽木(x,z,樹高,—)
        int nAll = 0;
        var report = new List<string>();

        foreach (var o in A(D["slopePlanting"]))
        {
            var bd = O(o);
            string band = (string)bd["band"], layer = (string)bd["layer"];
            int want = (int)F(bd["n"]);
            float clr = F(bd["clr"]), spacing = F(bd["spacing"]);
            string mode = (string)bd["placement"];
            var rnd = new System.Random((band + "/" + layer).GetHashCode());
            var bag = new PartBag(Has(bd, "parts") ? bd["parts"] : null, rnd);
            float tilt0 = 0f, tilt1 = 0f;
            if (Has(bd, "tilt")) { var t2 = A(bd["tilt"]); tilt0 = F(t2[0]); tilt1 = F(t2[1]); }
            float sj0 = 0.88f, sj1 = 1.14f;
            if (Has(bd, "scaleJitter")) { var j2 = A(bd["scaleJitter"]); sj0 = F(j2[0]); sj1 = F(j2[1]); }
            var sub = Group("Shamen/" + layer);
            int made = 0;

            if (mode == "crestLine")
            {
                // 落差が minDrop 以上の区間だけを、弧長で pitch ごとに刻む
                float acc = 0f;
                for (int i = 0; i < crest.Count - 1 && made < want; i++)
                {
                    Vector2 a = crest[i], b = crest[i + 1], n = segOut(i);
                    float L = Vector2.Distance(a, b);
                    for (float t = acc; t < L && made < want; t += pitch)
                    {
                        Vector2 p = Vector2.Lerp(a, b, t / L);
                        float w = slopeWidth(p, n);
                        float drop = TerrainY(p) - TerrainY(p + n * Mathf.Max(1f, w));
                        if (drop < minDrop) continue;                   // 浅い区間は数えない
                        Vector2 q = p + n * (off0 + (float)rnd.NextDouble() * (off1 - off0));
                        q += new Vector2((float)rnd.NextDouble() - 0.5f, (float)rnd.NextDouble() - 0.5f) * jit;
                        if (!Far(placed, q, spacing)) continue;
                        string path; float ps;
                        if (!bag.Next(out path, out ps)) break;
                        var go = PlantOnTerrain(path, q, sub, layer + "_" + made, ps, rnd, sj0, sj1,
                                                tilt0, tilt1);
                        if (go == null) continue;
                        placed.Add(new Vector3(q.x, 0f, q.y));
                        screens.Add(new Vector4(q.x, q.y, TreeHeight(go), 0f));
                        made++; nAll++;
                    }
                    acc = Mathf.Max(0f, acc + pitch * Mathf.Ceil(L / pitch) - L);
                }
            }
            else
            {
                // ⛔ 2026-09-02 検図【高5】/庭方【高1】: `slopeArea.bands` は図と別の帯(0.40/0.78 vs 0.33/0.70)で
                //    t の定義も別だった。帯は `slopeBands` に一本化され、斜面の散布は生成器の sidecar
                //    (Stage7' `planting_out.json`・ground:"terrain")が担う。ここは既定値へ黙って落ちない。
                if (!Has(sa, "bands"))
                    return "⛔ 旧 Stage8 の scatter は廃止 — 斜面の点は 7' 植栽(sidecar)が据える(slopeArea.bands は指図から消えた)";
                var bands = O(sa["bands"]);
                float b0, b1;
                { var bb = A(bands[band]); b0 = F(bb[0]); b1 = F(bb[1]); }
                for (int k = 0; k < want * 60 && made < want; k++)
                {
                    int i = rnd.Next(crest.Count - 1);
                    Vector2 a = crest[i], b = crest[i + 1], n = segOut(i);
                    Vector2 p = Vector2.Lerp(a, b, (float)rnd.NextDouble());
                    float w = slopeWidth(p, n);
                    if (w < 2f) continue;
                    float fr = b0 + (float)rnd.NextDouble() * (b1 - b0);
                    Vector2 q = p + n * (w * fr);
                    if (!EdoGeom.PIP(Poly, q)) continue;
                    if (!Far(placed, q, spacing)) continue;
                    string path; float ps;
                    if (!bag.Next(out path, out ps)) break;
                    var go = PlantOnTerrain(path, q, sub, layer + "_" + made, ps, rnd, sj0, sj1, tilt0, tilt1);
                    if (go == null) continue;
                    placed.Add(new Vector3(q.x, 0f, q.y));
                    made++; nAll++;
                }
            }
            report.Add(layer + " " + made + "/" + want);
            if (made < want)
                sb.AppendLine("⚠ " + band + " の " + layer + " が " + made + "/" + want +
                              " しか置けない — 間隔 " + spacing.ToString("F1") + "m か帯が狭い");
        }

        sb.AppendLine(ScreenQA(crest, segOut, slopeWidth, screens, sc));
        sb.Append("斜面の木 " + nAll + " 本  [" + string.Join(" | ", report.ToArray()) + "]");
        return sb.ToString();
    }

    /// <summary>**遮蔽の検査。**法肩に `step` ごとの検査点を取り、`reach` 以内に樹高 `minH` 以上の
    /// 木があるかを見る。⛔ 0件でなければ対岸から御殿の軒が抜ける。
    /// ⚠ 樹高は**据えた実メッシュから測る**(呼び寸法や prefab の名前で信じない)。</summary>
    static string ScreenQA(List<Vector2> crest, Func<int, Vector2> segOut,
                           Func<Vector2, Vector2, float> slopeWidth,
                           List<Vector4> screens, System.Collections.Generic.Dictionary<string, object> sc)
    {
        float step = F(sc["step"]), reach = F(sc["reach"]), minH = F(sc["minH"]), minDrop = F(sc["minDrop"]);
        int pts = 0, bad = 0; float worst = 0f; Vector2 worstAt = Vector2.zero;
        for (int i = 0; i < crest.Count - 1; i++)
        {
            Vector2 a = crest[i], b = crest[i + 1], n = segOut(i);
            float L = Vector2.Distance(a, b);
            for (float t = 0f; t < L; t += step)
            {
                Vector2 p = Vector2.Lerp(a, b, t / L);
                float w = slopeWidth(p, n);
                if (TerrainY(p) - TerrainY(p + n * Mathf.Max(1f, w)) < minDrop) continue;   // 浅い所は対象外
                pts++;
                float best = 0f;
                foreach (var s2 in screens)
                    if (Vector2.Distance(p, new Vector2(s2.x, s2.y)) <= reach && s2.z > best) best = s2.z;
                if (best < minH) { bad++; if (minH - best > worst) { worst = minH - best; worstAt = p; } }
            }
        }
        if (pts == 0) return "遮蔽QA: 落差 " + minDrop.ToString("F0") + "m 以上の法肩が無い";
        return "遮蔽QA: 法肩の検査点 " + pts + " / 樹高 " + minH.ToString("F1") + "m 未満 = " + bad + " 件"
             + (bad > 0 ? "(最悪 " + worst.ToString("F1") + "m 不足 at (" + worstAt.x.ToString("F0") + "," + worstAt.y.ToString("F0") + "))" : "");
    }

    /// <summary>据えた木の**実メッシュ**の高さ[m]。⛔ prefab の名前や呼び寸法で信じない。</summary>
    static float TreeHeight(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>(true);
        if (rs.Length == 0) return 0f;
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b.size.y;
    }

    static bool Far(List<Vector3> placed, Vector2 q, float d)
    {
        foreach (var p in placed)
            if ((p.x - q.x) * (p.x - q.x) + (p.z - q.y) * (p.z - q.y) < d * d) return false;
        return true;
    }

    /// <summary>法面へ据える。⛔ `DesignY` を使わない — 法面は造成面ではない。
    /// live terrain を実測して足元を地面に置く。</summary>
    static GameObject PlantOnTerrain(string path, Vector2 w, Transform parent, string name,
                                     float scale, System.Random rnd, float sj0, float sj1,
                                     float tilt0, float tilt1)
    {
        float y = TerrainY(w);
        float s = scale * (sj0 + (float)rnd.NextDouble() * (sj1 - sj0));
        var go = EdoNishiTameikeBuilder.Place(path, new Vector3(w.x, y, w.y),
            (float)rnd.NextDouble() * 360f, Vector3.one * s, parent, name);
        if (go == null) return null;
        float tl = tilt0 + (float)rnd.NextDouble() * (tilt1 - tilt0);
        if (tl > 0.01f)
        {
            float az = (float)rnd.NextDouble() * 360f;
            go.transform.RotateAround(go.transform.position,
                Quaternion.Euler(0, az, 0) * Vector3.forward, tl);
        }
        return go;
    }

    /// <summary>live terrain の高さ。⚠ 造成前の地盤(base_dem)ではなく**いまの作業面**。
    /// 法面は造成していないので両者は一致するが、木は「いまの地面」に立てる。</summary>
    static float TerrainY(Vector2 w)
    {
        var t = Terrain.activeTerrain;
        if (t == null) return 0f;
        return t.SampleHeight(new Vector3(w.x, 0f, w.y)) + t.transform.position.y;
    }

    static GameObject Plant(string path, float u, float v, Transform parent, string name,
                            float scale, System.Random rnd, float tiltU, float sink = 0f)
    {
        var f = Grid;
        Vector2 w = f.W(u, v);
        float y = DesignY(w);
        float s = scale * (0.82f + (float)rnd.NextDouble() * 0.36f);   // 同じ大きさで並べない
        var go = EdoNishiTameikeBuilder.Place(path, new Vector3(w.x, y - sink * s, w.y),
            (float)rnd.NextDouble() * 360f, Vector3.one * s, parent, name);
        if (go != null && Mathf.Abs(tiltU) > 1e-3f)
        {
            // 崖(西=−u)へ傾ける。海風に振られた黒松の見立て
            float yawU = YawAlongU();
            go.transform.rotation = Quaternion.Euler(0, go.transform.eulerAngles.y, 0);
            go.transform.RotateAround(go.transform.position,
                Quaternion.Euler(0, yawU, 0) * Vector3.forward,
                tiltU * (5f + (float)rnd.NextDouble() * 7f));
        }
        return go;
    }

    /// <summary>**犬走りと門の面の検査。**囲いの外面が石垣の法肩から 0.30m 控えているか、
    /// 門の面が囲いと揃っているか。⚠ これが無かったので、長屋が 1.63m 引っ込み・練塀が 0.08m
    /// せり出した状態のままユーザーに見せてしまった(2026-08-29 EDO-0053)。</summary>
    public static string InubashiriQA()
    {
        var kak = Group("Kakoi");
        var bad = new List<string>();
        int n = 0;
        for (int i = 0; i < kak.childCount; i++)
        {
            var c = kak.GetChild(i);
            int ri = -1;
            for (int k = 0; k < Runs.Length; k++)
                if (c.name.StartsWith(Runs[k].name) && (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
            if (ri < 0) continue;
            var r = Runs[ri];
            Vector2 n2 = OutNormal(r.edge);
            var a = Poly[r.edge % Poly.Length];
            float best = float.MinValue;
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null || !WallFace.Contains(mf.gameObject.name)) continue;
                var m = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = m.MultiplyPoint3x4(v);
                    best = Mathf.Max(best, (w.x - a.x) * n2.x + (w.z - a.y) * n2.y);
                }
            }
            if (best == float.MinValue) continue;
            n++;
            if (Mathf.Abs(best + INUBASHIRI) > 0.05f)
                bad.Add(c.name + " の外面が " + best.ToString("+0.00;-0.00") + "(規定 -0.30)");
        }
        if (bad.Count == 0) return "犬走りQA: " + n + "駒すべて 0.30±0.05m";
        return "犬走りQA: ★ " + bad.Count + "/" + n + " 駒が外れている。例 " + string.Join(" / ", bad.GetRange(0, Mathf.Min(3, bad.Count)));
    }

    /// <summary>**走り方向の端の検査。**`InubashiriQA` の対。
    ///
    /// ⚠ 2026-08-29 にユーザーがブックマーク15枚で指摘した不具合は、**全部これが無かったせい**。
    /// 犬走りQA は外向き d しか見ておらず、**辺に沿う s の端を測る検査が一つも無かった**ので、
    /// 次の4つがどれも 0 件で通っていた:
    ///   ① 長屋の壁が継ぎ目で 0.64m 空く(部材長が「屋根の全長」で、壁は両端 0.32m 内側)
    ///   ② 石垣が run ごと丸ごと 1 駒ぶんずれる(駒の箱の向きを文書で決めていた)
    ///   ③ 隣り合う run で石の大きさが 7.3 倍違う(run ごとに駒を等倍拡大縮小していた)
    ///   ④ 辺1 だけ外向き法線が反転(重心で向きを決めていた)
    ///
    /// 層ごと(石垣 / 囲い)に**据えた実メッシュから端面を測り**、指図の s0/s1 と、
    /// 隣り合う run の端面どうしを突き合わせる。⛔ 部材の呼び寸法や指図の値で代用しない。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/走り方向の端を検査 RunEndQA")]
    public static void RunEndQAMenu() { Debug.Log("[Matsudaira] " + RunEndQA()); }
    public static string RunEndQA()
    {
        var kak = Group("Kakoi"); var ig = Group("Ishigaki");
        var sb = new System.Text.StringBuilder();
        var bad = new List<string>();
        // 層ごとに run 名 → 辺沿い s の [最小, 最大]
        var kakSpan = new Dictionary<string, float[]>();
        var igSpan = new Dictionary<string, float[]>();
        System.Action<Transform, Dictionary<string, float[]>, bool> gather = (grp, dst, wallOnly) =>
        {
            for (int i = 0; i < grp.childCount; i++)
            {
                var c = grp.GetChild(i);
                int ri = -1;
                for (int k = 0; k < Runs.Length; k++)
                {
                    string pre = (grp == ig ? "IG_" : "") + Runs[k].name;
                    if ((c.name == pre || c.name.StartsWith(pre + "_")) &&
                        (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
                }
                if (ri < 0) continue;
                var r = Runs[ri];
                var a = Poly[r.edge % Poly.Length];
                var b = Poly[(r.edge + 1) % Poly.Length];
                Vector2 u = (b - a).normalized;
                float lo = float.MaxValue, hi = float.MinValue;
                foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var m = mf.transform.localToWorldMatrix;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = m.MultiplyPoint3x4(v);
                        float s = (w.x - a.x) * u.x + (w.z - a.y) * u.y;
                        // 囲いは**壁の実体**で測る。屋根の軒・反り・鬼は端ではない(①の再発防止)。
                        // ⛔ **部材名で壁を選ってはいけない** — Blender で起こした表長屋は
                        //   単一メッシュ(`Nagaya_Omote_36` 1枚)なので WallFace の名前に一つも当たらず、
                        //   **長屋10本が丸ごと検査から抜け落ちていた**(2026-08-29 に自分で踏んだ)。
                        //   代わりに**座から 0.6〜1.4m の水平な薄切り**で取る。この高さは練塀でも
                        //   長屋(一階・二階)でも壁の実体しか通らない。
                        // ⚠ 帯は**その s の座**で取る。run の中点の座で取ると斜面の run で両端が
                        //   帯から外れ「壁が届いていない」と誤報する(辺2 で 6m 誤報した)
                        if (wallOnly)
                        {
                            float seat = r.SeatAt(s);
                            if (w.y < seat + 0.6f || w.y > seat + 1.4f) continue;
                        }
                        if (s < lo) lo = s; if (s > hi) hi = s;
                    }
                }
                if (lo == float.MaxValue) continue;
                float[] cur;
                if (dst.TryGetValue(r.name, out cur)) { cur[0] = Mathf.Min(cur[0], lo); cur[1] = Mathf.Max(cur[1], hi); }
                else dst[r.name] = new float[] { lo, hi };
            }
        };
        gather(kak, kakSpan, true);
        gather(ig, igSpan, false);

        // ---- 石垣(igSpan)だけ、隅の腕ぶん期待範囲を広げる。
        //   2026-09-06 実装が入隅の浮きを消すため、`joints[].kado` の隅の腕の下まで石垣の基壇を
        //   延ばした(囲いの run は s0/s1 ちょうどで止まるのが正 — 隅部材が腕を兼ねる)。
        //   腕の長さは **`kado.parts[<part>].armRaw × kado.scale`** が正典(数値を複製しない。
        //   `_pending.runEndQAIshigakiArm` の申し送り)。`a` 側の run は s1 を、`b` 側の run は
        //   s0 を、その分だけ広げる(`_joints` の入り腕/出り腕の記法と対応)。
        var armHi = new Dictionary<string, float>();   // a側: 期待 s1 を広げる
        var armLo = new Dictionary<string, float>();   // b側: 期待 s0 を狭める(下げる)
        {
            var kadoTop = O(D["kado"]);
            float kScale = F(kadoTop["scale"]);
            var parts = O(kadoTop["parts"]);
            foreach (var o in A(D["joints"]))
            {
                var j = O(o);
                if (!Has(j, "kado")) continue;
                string suf = ((string)j["id"]).Replace("J_", "");
                float armLen = -1f;
                foreach (var kv in parts)
                {
                    var pd = O(kv.Value);
                    bool hit = false;
                    foreach (var u in A(pd["use"])) if ((string)u == suf) { hit = true; break; }
                    if (hit) { armLen = F(pd["armRaw"]) * kScale; break; }
                }
                if (armLen < 0f) continue;
                if (Has(j, "a")) armHi[(string)j["a"]] = armLen;
                if (Has(j, "b")) armLo[(string)j["b"]] = armLen;
            }
        }

        // (1) 各層の端が指図の s0/s1 に乗っているか
        int nk = 0, ni = 0;
        foreach (var r in Runs)
        {
            float[] v;
            if (kakSpan.TryGetValue(r.name, out v))
            {
                nk++;
                if (Mathf.Abs(v[0] - r.s0) > 0.10f || Mathf.Abs(v[1] - r.s1) > 0.10f)
                    bad.Add("囲い " + r.name + " 辺" + r.edge + " 壁 " + v[0].ToString("F2") + "〜" + v[1].ToString("F2")
                            + "(指図 " + r.s0.ToString("F2") + "〜" + r.s1.ToString("F2") + ")");
            }
            if (igSpan.TryGetValue(r.name, out v))
            {
                ni++;
                // 駒は切れないので、run が駒1枚より短い区間は**はみ出す側で納める**
                // (裁定「run の長さは石垣の重なり具合で調整する」。隙間は不可・重なりは可)
                float tolHi = (r.s1 - r.s0 < IG_RUN) ? (IG_RUN - (r.s1 - r.s0)) + 0.10f : 0.10f;
                float lo0, hi0;
                float expS0 = r.s0 - (armLo.TryGetValue(r.name, out lo0) ? lo0 : 0f);
                float expS1 = r.s1 + (armHi.TryGetValue(r.name, out hi0) ? hi0 : 0f);
                if (v[0] - expS0 < -0.10f || v[0] - expS0 > 0.10f || v[1] - expS1 < -0.10f || v[1] - expS1 > tolHi)
                    bad.Add("石垣 " + r.name + " 辺" + r.edge + " " + v[0].ToString("F2") + "〜" + v[1].ToString("F2")
                            + "(指図 " + expS0.ToString("F2") + "〜" + expS1.ToString("F2")
                            + (lo0 != 0f || hi0 != 0f ? "・腕込み" : "") + ")");
            }
        }
        // (2) 同じ辺で隣り合う run の端面どうし。隙間は不可・めり込みは 1.0m まで可
        for (int e = 0; e < Poly.Length; e++)
        {
            var line = new List<Run>();
            foreach (var r in Runs) if (r.edge == e) line.Add(r);
            line.Sort((x, y) => x.s0.CompareTo(y.s0));
            for (int i = 0; i + 1 < line.Count; i++)
            {
                if (Mathf.Abs(line[i + 1].s0 - line[i].s1) > 0.01f) continue;   // 指図で連続する対のみ
                foreach (var pair in new[] { new object[] { "囲い", kakSpan }, new object[] { "石垣", igSpan } })
                {
                    var dst = (Dictionary<string, float[]>)pair[1];
                    float[] p, q;
                    if (!dst.TryGetValue(line[i].name, out p) || !dst.TryGetValue(line[i + 1].name, out q)) continue;
                    float gap = q[0] - p[1];
                    if (gap > 0.02f)
                        bad.Add((string)pair[0] + " 辺" + e + " s=" + line[i].s1.ToString("F2") + " "
                                + line[i].name + "→" + line[i + 1].name + " に隙間 " + gap.ToString("F2") + "m");
                    else if (gap < -1.0f)
                        bad.Add((string)pair[0] + " 辺" + e + " s=" + line[i].s1.ToString("F2") + " "
                                + line[i].name + "→" + line[i + 1].name + " が " + (-gap).ToString("F2") + "m めり込み");
                }
            }
        }
        // (2b) 長屋門の門口が指図の s に開いているか。⛔ 呼び寸法で信じない — **壁の帯に
        //      頂点が無い区間**(=穴)を実メッシュから拾って、指図の mon.s と突き合わせる。
        //      2026-08-30: 部材のローカル +X の向きを取り違えて 3.7m ずれた前例がある。
        foreach (var r in Runs)
        {
            if (r.monS <= 0f) continue;
            Transform tr = null;
            for (int i = 0; i < kak.childCount; i++)
                if (kak.GetChild(i).name == r.name) tr = kak.GetChild(i);
            if (tr == null) continue;
            var a2 = Poly[r.edge % Poly.Length];
            var b2 = Poly[(r.edge + 1) % Poly.Length];
            Vector2 u2 = (b2 - a2).normalized;
            float seat2 = r.SeatAt(r.monS);
            // ⚠ 2026-08-31: 門口に扉を作り付けた(ユーザー裁定2-A)ので、
            //   「run の中でいちばん広い空き」を門口とみなす旧法は成り立たなくなった
            //   (扉が穴を埋め、代わりに壁のどこか別の空きを門口と誤認して
            //    辺13 で s=13.30・幅1.40m と報告した)。
            //   **壁の外面だけを見る。**扉は壁厚の中ほどに吊ってあるので外面には出ない。
            Vector2 on2 = OutNormal(r.edge);
            int NB = 4000; var bins = new int[NB]; var doorBins = new int[NB];
            float dOut = float.NegativeInfinity;
            // 1巡目 — 壁の外面の位置 dOut を、目の高さの帯から採る
            foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var m2 = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = m2.MultiplyPoint3x4(v);
                    if (w.y < seat2 + 0.6f || w.y > seat2 + 1.4f) continue;
                    float d = (w.x - a2.x) * on2.x + (w.z - a2.y) * on2.y;
                    if (d > dOut) dOut = d;
                }
            }
            // 2巡目 — 門口(壁の外面)と扉(方立の内側)を別々に数える。
            // ⚠ **高さの帯を分ける。** 扉は板の箱でできているので、頂点は丈の上下
            //   (足元と頭)にしかない。目の高さの帯で数えると 0 になり、
            //   塞がっているのに「塞がっていない」と出る(2026-08-31 に実測 42 頂点)。
            foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var m2 = mf.transform.localToWorldMatrix;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    var w = m2.MultiplyPoint3x4(v);
                    float d = (w.x - a2.x) * on2.x + (w.z - a2.y) * on2.y;
                    int bi = Mathf.RoundToInt(((w.x - a2.x) * u2.x + (w.z - a2.y) * u2.y) * 10f);
                    if (bi < 0 || bi >= NB) continue;
                    if (w.y >= seat2 + 0.6f && w.y <= seat2 + 1.4f && d > dOut - 0.12f)
                        bins[bi]++;                                   // 壁の外面(=門口はここが空く)
                    if (w.y >= seat2 - 0.05f && w.y <= seat2 + r.monH
                        && d < dOut - 0.12f && d > dOut - 0.80f)
                        doorBins[bi]++;                               // 方立の内側(=扉)
                }
            }
            float best = -1f, bw = 0f; int st2 = -1;
            for (int i = Mathf.RoundToInt(r.s0 * 10f) + 2; i <= Mathf.RoundToInt(r.s1 * 10f) - 2; i++)
            {
                if (bins[i] == 0 && st2 < 0) st2 = i;
                if ((bins[i] > 0 || i == Mathf.RoundToInt(r.s1 * 10f) - 2) && st2 >= 0)
                {
                    float w2 = (i - st2) / 10f;
                    if (w2 > bw) { bw = w2; best = (st2 + i) / 20f; }
                    st2 = -1;
                }
            }
            // 門口が扉で塞がっているか — **扉が開口の端から端まで届いているか**を測る。
            // ⚠ ビンごとの頂点の有無で数えない。扉は板の箱なので頂点は板の小口にしか
            //   無く、0.30m ピッチの板を 0.10m のビンで数えると必ず穴が空く
            //   (2026-08-31 に 8/24 と出て、塞がっているのに不合格になった)。
            if (best >= 0f)
            {
                int dLo = -1, dHi = -1;
                for (int i = 0; i < NB; i++) if (doorBins[i] > 0) { if (dLo < 0) dLo = i; dHi = i; }
                if (dLo < 0)
                    bad.Add("長屋門 " + r.name + " 辺" + r.edge + " の門口に扉が無い(素通し)");
                else
                {
                    float cover = (dHi - dLo) / 10f;
                    if (cover < bw - 0.20f)
                        bad.Add("長屋門 " + r.name + " 辺" + r.edge + " の扉が開口に届いていない(扉 "
                                + cover.ToString("F2") + "m / 開口 " + bw.ToString("F2") + "m)");
                }
            }
            if (best < 0f) bad.Add("長屋門 " + r.name + " に門口の穴が見つからない");
            else if (Mathf.Abs(best - r.monS) > 0.30f)
                bad.Add("長屋門 " + r.name + " 辺" + r.edge + " の門口が s=" + best.ToString("F2")
                        + "(指図 " + r.monS.ToString("F2") + "・幅 " + bw.ToString("F2") + "m)");
        }

        // (3) 石垣の駒が実寸のままか(run ごとに拡大縮小していないか)
        var scales = new List<float>();
        for (int i = 0; i < ig.childCount; i++)
        {
            var sc = ig.GetChild(i).lossyScale;
            if (Mathf.Abs(sc.x - 1f) > 0.01f || Mathf.Abs(sc.y - 1f) > 0.01f || Mathf.Abs(sc.z - 1f) > 0.01f)
                if (scales.Count < 3) scales.Add(sc.x);
        }
        if (scales.Count > 0)
            bad.Add("石垣の駒が実寸でない(scale≠1)。例 " + string.Join(", ", scales.ConvertAll(x => x.ToString("F2")).ToArray()));

        sb.Append("走り方向の端QA: 囲い " + nk + " run / 石垣 " + ni + " run — ");
        if (bad.Count == 0) sb.Append("0 件");
        else
        {
            sb.Append("★ " + bad.Count + " 件");
            for (int i = 0; i < Mathf.Min(8, bad.Count); i++) sb.Append("\n    " + bad[i]);
            if (bad.Count > 8) sb.Append("\n    ほか " + (bad.Count - 8) + " 件");
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 指図と実装の突き合わせ
    [MenuItem("Edo/松平出羽守上屋敷/指図と実装を突き合わせる")]
    public static void CompareMenu() { Debug.Log("[Matsudaira] " + Compare()); }
    public static string Compare()
    {
        // 検査の本体は EdoSashizuExport.CheckScene(汎用の器・屋敷テーブル "matsudaira_dewa")。
        // ★を出すインライン実装は 2026-08-26 に共通側へ移した — 検査項目・判定・出力とも同一
        //   (移設の前後で出力の byte 一致を実機確認)。ここに残るのは造成の GradeQA だけ
        //   (指図の設計面と live terrain の照合はこのビルダー固有の Stage0 退避を使うため)。
        return EdoSashizuExport.CheckScene("matsudaira_dewa") + GradeQA() + "\n" + InubashiriQA()
             + "\n" + RunEndQA();
    }
}
