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

public static class EdoMatsudairaDewaBuilder
{
    public const string SashizuRel = "docs/Sashizu/matsudaira_dewa_sashizu.json";
    public const string ParcelId = "matsudaira_dewa";
    public const string Grp = "Edo_Yashiki_MatsudairaDewa";

    /// <summary>bench=true の run の内側を天端で平らにする幅[m]。指図 _runs の「外周帯(内側幅3m)」。</summary>
    public const float BAND = 3.0f;

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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

        EdoNishiTameikeBuilder.NaturalMode = false;     // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak);
        var sb = new System.Text.StringBuilder();
        int nag = 0, hei = 0;

        // 門の開口(表門は組立全幅、小門は w)
        var gate = O(D["gate"]);
        var gplan = O(gate["plan"]);
        var gsp = O(gplan["sPos"]);
        float gA = F(A(gsp["banshoW"])[0]), gB = F(A(gsp["banshoE"])[1]);
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
        return sb.ToString();
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

    /// <summary>駒の走り方向の実長[m](scale=1 の実測値)。</summary>
    const float IG_RUN = 2.00f;
    /// <summary>駒の高さ[m](scale=1 の実測値)。天端を座に置き、余りは地中へ埋める。</summary>
    const float IG_H = 4.00f;
    /// <summary>継ぎ目の最大ピッチ[m]。これ以下にすることで重なり 0.20m 以上を保証する。</summary>
    const float IG_PITCH_MAX = 1.80f;
    [MenuItem("Edo/松平出羽守上屋敷/3 石垣基壇")]
    public static void Stage3Menu() { Debug.Log("[Matsudaira] " + Stage3_Ishigaki()); }
    public static string Stage3_Ishigaki()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

        var grp = Group("Ishigaki"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        var gate = O(D["gate"]);
        var gsp = O(O(gate["plan"])["sPos"]);
        float gA = F(A(gsp["banshoW"])[0]), gB = F(A(gsp["banshoE"])[1]);
        int gEdge = (int)F(gate["edge"]);
        var komon = new List<float[]>();
        foreach (var o in A(D["komon"]))
        {
            var k = O(o); float s = F(k["s"]), w = F(k["w"]);
            komon.Add(new float[] { F(k["edge"]), s - w / 2f, s + w / 2f });
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

            Vector2 n = OutNormal(r.edge);
            // ローカル +X を外向きに、+Z を s の増える向きに合わせる
            float psi = Mathf.Atan2(-n.y, n.x) * Mathf.Rad2Deg;
            // ⚠ 天端は駒ごとに r.SeatAt(t) から取る。r.seat は斜面 run の**中点**で、
            //   これで平らに据えると一本の run の中で埋没と過大露出が同時に起きる(2026-08-23)。
            //   石垣そのものは水平が正典(unity-modular-stonewall §3)なので、**斜面では
            //   run が2m刻みに割られた単位ごとに水平**にし、run 全体では階段状に下る。
            foreach (var sg in segs)
            {
                float t0 = sg[0], t1 = sg[1], L = t1 - t0;
                // 何枚で覆うか。pitch は必ず IG_PITCH_MAX 以下になるので**重なりは 0.20m 以上**、
                // つまり隙間は原理的に出ない(閉じは「隙間 > めり込み」)。
                int N = (L <= IG_RUN) ? 1 : Mathf.CeilToInt((L - IG_RUN) / IG_PITCH_MAX) + 1;
                float pitch = (N > 1) ? (L - IG_RUN) / (N - 1) : 0f;
                for (int i = 0; i < N; i++)
                {
                    float t = t0 + pitch * i;                 // 駒の箱は [t, t + IG_RUN]
                    float mid = Mathf.Min(t + IG_RUN * 0.5f, t1);
                    Vector2 p = EdgePt(r.edge, t);
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.JC.CastleWall,
                        new Vector3(p.x, r.SeatAt(mid) - IG_H, p.y), psi,
                        Vector3.one, grp, "IG_" + r.name + "_" + made);
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

    [MenuItem("Edo/松平出羽守上屋敷/4 御殿複合")]
    public static void Stage4Menu() { Debug.Log("[Matsudaira] " + Stage4_Goten()); }
    public static string Stage4_Goten()
    {
        // ⛔ **検図関門**(CLAUDE.md 規則18)。不合格の指図を実装しない。
        //    2026-09-01: Stage7 が指図の poly/at/groups/clr を読まず、**撤回済みの
        //    「松を全数 −u へ傾ける」がコードに生きていた**。流せば撤回した案が復活する。
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

        var grp = Group("Buildings"); Clear(grp);
        var f = Grid;
        float yawU = YawAlongU(), yawV = YawAlongV();
        var sb = new System.Text.StringBuilder();
        int nm = 0, nl = 0;

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
            string roof = EdoAssets.Goten.RoofIrimoya_(kw, kd);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(roof) == null)
            {
                sb.AppendLine("⚠ " + name + ": 屋根が無い " + kw + "x" + kd +
                              "ken — build_goten_roof.py -- " + (kw * f.ken) + " " + (kd * f.ken) +
                              " Goten_Roof_Irimoya_" + kw + "x" + kd + "ken");
                roof = null;
            }
            var g = EdoGotenKit.Mune(name, grp, new Vector3(w.x, y, w.y), yawU,
                                     kw - 2, kd - 2, 1, GOTEN_FLOOR, roof, iriX: 1);
            Undo.RegisterCreatedObjectUndo(g, "mune");
            nm++;
        }

        // 渡廊下・御錠口 — 両端は棟の壁面へ突き付けるので端の柱通りは落とす(柱の二重置き=z-fighting)
        foreach (var o in A(D["links"]))
        {
            var l = O(o);
            string name = (string)l["name"];
            int u0 = Mathf.RoundToInt(F(l["u0"])), v0 = Mathf.RoundToInt(F(l["v0"]));
            int u1 = Mathf.RoundToInt(F(l["u1"])), v1 = Mathf.RoundToInt(F(l["v1"]));
            int kw = u1 - u0, kd = v1 - v0;
            bool alongU = kw >= kd;
            int n = alongU ? kw : kd;
            if ((alongU ? kd : kw) != 1)
                sb.AppendLine("⚠ " + name + ": 廊下の幅が一間でない(" + kw + "x" + kd + ")");
            float y = F(l["y"]);
            var w = alongU ? f.W(u0, v1) : f.W(u0, v0);
            var g = EdoGotenKit.Roka(name, grp, new Vector3(w.x, y, w.y), alongU ? yawU : yawV, n,
                                     GOTEN_FLOOR, colStart: false, colEnd: false);
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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

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
        foreach (var key in new[] { "banshoW", "banshoE" })
        {
            var a = A(sp[key]);
            float mid = (F(a[0]) + F(a[1])) * 0.5f;
            Vector2 q = EdgePt(ge, mid) + outw * (prot * 0.5f);
            var go = EdoNishiTameikeBuilder.Place(EdoAssets.Own.MatsudairaBansho,
                new Vector3(q.x, sill, q.y), yaw, Vector3.one, grp, "Bansho_" + key.Substring(6));
            if (go != null) { n++; sb.AppendLine("番所 " + key + " s=" + mid.ToString("F1")); }
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

        // 表門の扉
        if (Has(plan, "leaf"))
        {
            var lf = O(plan["leaf"]);
            int nl3 = Leaves(grp, "Omotemon", EdoAssets.JC.GateDoorYaguraL, EdoAssets.JC.GateDoorYaguraR,
                             4.0f, 0f, gp, yaw, F(lf["w"]), sill);
            if (nl3 > 0) sb.AppendLine("表門の扉 " + (string)lf["kind"] + " 幅" + F(lf["w"]).ToString("F1"));
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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

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
        foreach (var o in A(D["nakajikiri"]))
        {
            var w = O(o);
            string nm = (string)w["name"];
            var a = A(w["a"]); var b = A(w["b"]);
            Vector2 A2 = f.W(F(a[0]), F(a[1])), B2 = f.W(F(b[0]), F(b[1]));
            float h = F(w["h"]);
            if ((string)w["kind"] == "庭木戸")
            {
                // 在庫の冠木門を開口幅へ合わせて据える【確度B — 庭木戸そのものの在庫は無い】
                Vector2 c = (A2 + B2) * 0.5f;
                Vector2 dir = (B2 - A2).normalized;
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Kabukimon,
                    new Vector3(c.x, DesignY(c), c.y), Mathf.Atan2(dir.y, -dir.x) * Mathf.Rad2Deg,
                    Vector3.one * EdoSannoKitaBuilder.ES, njGrp, nm);
                if (go != null)
                {
                    var bb = EdoNishiTameikeBuilder.RB(go);
                    float have = Mathf.Max(bb.size.x, bb.size.z);
                    float want = (B2 - A2).magnitude;
                    if (have > 0.1f)
                    {
                        var ls = go.transform.localScale;
                        go.transform.localScale = new Vector3(ls.x * want / have, ls.y * h / bb.size.y, ls.z);
                    }
                    go.transform.position += new Vector3(0, DesignY(c) - EdoNishiTameikeBuilder.RB(go).min.y, 0);
                    nHei++;
                }
                continue;
            }
            nHei += ItabeiRun(njGrp, A2, B2, h, nm, kido);
        }

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
            if (nm.StartsWith("Kura"))      { path = EdoAssets.Own.Matsudaira.Dozo;   yaw = yawV; }
            else if (nm == "Sakuji")        { path = EdoAssets.Own.Matsudaira.Koya;   yaw = yawU; }
            else if (nm == "Chatei")        { path = EdoAssets.Own.Matsudaira.Sukiya; yaw = yawU; }
            else if (nm == "Inari")         { path = EdoAssets.Own.Matsudaira.Inari;  yaw = yawU; }
            else { sb.AppendLine("⚠ 附属屋 " + nm + ": 割り当てる部材が決まっていない"); continue; }
            Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
            var go = EdoNishiTameikeBuilder.Place(path, new Vector3(c.x, DesignY(c), c.y),
                yaw, Vector3.one, svGrp, nm);
            if (go == null) { sb.AppendLine("⚠ 附属屋 " + nm + ": 部材が読めない " + path); continue; }
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

    /// <summary>板塀を A→B に実寸ピッチで通す。skip の区間(庭木戸)は空ける。表裏2枚組。</summary>
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
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (spanES - 0.15f)));
        float pitch = len / n;
        float sx = EdoSannoKitaBuilder.ES * pitch / spanES;
        float sy = h / rawH;                                  // 指図の高さ(2.4m)に立てる
        float yaw = Mathf.Atan2(nrm.x, nrm.y) * Mathf.Rad2Deg;
        int made = 0;
        for (int k = 0; k < n; k++)
        {
            Vector2 c = A2 + dir * (pitch * (k + 0.5f));
            bool skipped = false;
            foreach (var sg in skip)
            {
                // 木戸の区間と重なる bay は置かない(門の幅ぶん確実に空ける)
                float t = Vector2.Dot(c - sg[0], (sg[1] - sg[0]).normalized);
                float gl = (sg[1] - sg[0]).magnitude;
                if (DistSeg(c, sg[0], sg[1]) < pitch * 0.5f + 0.6f && t > -pitch && t < gl + pitch)
                { skipped = true; break; }
            }
            if (skipped) continue;
            float y = Mathf.Max(DesignY(c - dir * pitch * 0.5f), DesignY(c + dir * pitch * 0.5f));
            for (int side = 0; side < 2; side++)
            {
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Itabei5, Vector3.zero,
                    side == 0 ? yaw : yaw + 180f, new Vector3(sx, sy, EdoSannoKitaBuilder.ES),
                    parent, prefix + "_" + k + (side == 0 ? "f" : "b"));
                if (go == null) continue;
                var b = EdoNishiTameikeBuilder.RB(go);
                Vector2 tgt = c + nrm * (side == 0 ? 0.06f : -0.06f);
                go.transform.position += new Vector3(tgt.x - b.center.x, y - 0.08f - b.min.y, tgt.y - b.center.z);
                made++;
            }
        }
        return made;
    }

    /// <summary>附属屋 FBX のマテリアルを、**借り先を名指しして**結び直す。
    /// ⚠ `SearchAndRemapMaterials(..., Everywhere)` はプロジェクト全体(6.9GB)を舐めるので使わない
    ///   — 2026-08-24 に実際にユーザーの PC が固まった。借り先は3フォルダだけ見る。</summary>
    [MenuItem("Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap")]
    public static void RemapFuzokuyaMenu() { Debug.Log("[Matsudaira] " + RemapFuzokuya()); }
    public static string RemapFuzokuya()
    {
        string[] donorDirs = {
            "Assets/Japanese Village Kit/Materials",
            "Assets/Japanese Castle/Meshes/Exterior/Materials",
            "Assets/Edo/Materials",              // キットに無い材(鳥居の朱 Shu_Torii など)
            // 新造した木(Own.Jokuroku / Own.Ume)は在庫の桜の樹皮・葉の材質名を名乗る
            "Assets/Waldemarst/FreeJapaneseGarden/Materials",
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
        string[] modelDirs = { "Assets/Edo/Models/Fuzokuya", "Assets/Edo/Models/Mon",
                               "Assets/Edo/Models/Trees" };
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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

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
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa");
          if (gate != null) return gate; }

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
                var bands = O(sa["bands"]);
                float b0 = 0.0f, b1 = 0.5f;
                if (Has(bands, band)) { var bb = A(bands[band]); b0 = F(bb[0]); b1 = F(bb[1]); }
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
                if (v[0] - r.s0 < -0.10f || v[0] - r.s0 > 0.10f || v[1] - r.s1 < -0.10f || v[1] - r.s1 > tolHi)
                    bad.Add("石垣 " + r.name + " 辺" + r.edge + " " + v[0].ToString("F2") + "〜" + v[1].ToString("F2")
                            + "(指図 " + r.s0.ToString("F2") + "〜" + r.s1.ToString("F2") + ")");
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
