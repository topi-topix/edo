// 松平出羽守上屋敷(出雲松江藩 18万6千石)ビルダー。
//
// 【正典は指図】docs/Sashizu/matsudaira_sashizu.json を**実行時に読む**。
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

public static class EdoMatsudairaBuilder
{
    public const string SashizuRel = "docs/Sashizu/matsudaira_sashizu.json";
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
        public string name; public int edge; public float s0, s1, seat; public bool bench, nagaya; public float ishi;
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
                        bench = Has(r, "bench") && (bool)r["bench"],
                        nagaya = (string)r["kind"] == "Nagaya",
                        ishi = Has(r, "s") ? F(r["s"]) : 0f
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
    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x))
                inside = !inside;
        return inside;
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
            if (!PIP(P, p)) continue;                             // 敷地の外は一切触らない
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
            if (!PIP(P, p)) continue;
            float cur = H[z, x] * ts.y + tp.y;
            float dif = Mathf.Abs(cur - DesignY(p));
            n++;
            if (dif > TOL) { bad++; if (dif > worst) { worst = dif; wp = p; } }
        }
        return string.Format("GradeQA: 敷地内 {0} セル / 設計面と {1:F2}m 超ずれ = {2} 件 ({3:P1})。最悪 {4:F2}m at ({5:F1},{6:F1})",
                             n, TOL, bad, n == 0 ? 0f : (float)bad / n, worst, wp.x, wp.y);
    }

    // ---------------------------------------------------------------- Stage2 外周
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
    /// <summary>辺 e の外向き法線(区画の外側)。</summary>
    public static Vector2 OutNormal(int e)
    {
        var P = Poly; int n = P.Length;
        Vector2 d = (P[(e + 1) % n] - P[e % n]).normalized;
        Vector2 nn = new Vector2(-d.y, d.x);
        float area = 0f;
        for (int i = 0; i < n; i++) { var a = P[i]; var b = P[(i + 1) % n]; area += a.x * b.y - b.x * a.y; }
        if (area > 0) nn = -nn;                  // 内向きになったら反転
        // 重心が内側に来る向きに揃える
        Vector2 c = Vector2.zero; foreach (var q in P) c += q; c /= n;
        Vector2 mid = (P[e % n] + P[(e + 1) % n]) * 0.5f;
        if (Vector2.Dot(c - mid, nn) > 0) nn = -nn;
        return nn;
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

    /// <summary>辺 e の [s0,s1] に表長屋を実寸ピッチで通す。seatAt(s) がその位置の天端を返す。</summary>
    static int NagayaChain(Transform parent, int e, float s0, float s1, Func<float, float> seatAt, string prefix)
    {
        var mc = Measure(EdoAssets.Eg.KnagayaC);
        var ml = Measure(EdoAssets.Eg.KnagayaL);
        var mr = Measure(EdoAssets.Eg.KnagayaR);
        float Wc = mc.hi - mc.lo;                      // 実測 8.065m
        float L = s1 - s0;
        int n = Mathf.Max(1, Mathf.RoundToInt(L / Wc));
        Vector2 outw = OutNormal(e);
        float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
        // 走り方向はローカル -X。辺の向きが逆なら flip。
        Vector2 a = EdgePt(e, 0f), b = EdgePt(e, 1f);
        Vector2 rdir = (b - a).normalized;
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        bool flip = Vector2.Dot(rdir, negRight) < 0;
        // 端の妻部材は壁幅が 0.155m 狭い(l/r = 7.910 / c = 8.065)。**一律ピッチだと妻の隣に
        // 隙間があく**ので、部材ごとの実寸を積み上げるカーソルで置く。
        Func<int, string> pathAt = k =>
        {
            if (n > 1 && k == 0) return flip ? EdoAssets.Eg.KnagayaR : EdoAssets.Eg.KnagayaL;
            if (n > 1 && k == n - 1) return flip ? EdoAssets.Eg.KnagayaL : EdoAssets.Eg.KnagayaR;
            return EdoAssets.Eg.KnagayaC;
        };
        Func<string, NagModule> modOf = p2 =>
            p2 == EdoAssets.Eg.KnagayaL ? ml : (p2 == EdoAssets.Eg.KnagayaR ? mr : mc);
        float total = 0f;
        for (int k = 0; k < n; k++) { var m2 = modOf(pathAt(k)); total += m2.hi - m2.lo; }
        float cursor = s0 + (L - total) * 0.5f;        // 鎖を run の中央に置く(端数は隅・開口が受ける)
        int made = 0;
        for (int k = 0; k < n; k++)
        {
            string path = pathAt(k);
            var m = modOf(path);
            float w = m.hi - m.lo;
            // 壁の低い側の端がちょうど cursor に来るピボット位置
            //   flip=false … ローカル+X が s の増える向き → s = pivot + x
            //   flip=true  … ローカル+X が s の減る向き → s = pivot - x
            float sPiv = flip ? (cursor + m.hi) : (cursor - m.lo);
            Vector2 p = EdgePt(e, sPiv);
            float seat = seatAt(cursor + w * 0.5f);
            var go = EdoNishiTameikeBuilder.Place(path, new Vector3(p.x, seat, p.y), psi,
                                                  Vector3.one * EdoSannoKitaBuilder.ES, parent, prefix + "_" + k);
            if (go != null) { EdoNishiTameikeBuilder.SeatBottom(go, seat - 0.10f); made++; }
            cursor += w;                               // 継ぎ目は必ず面一
        }
        return made;
    }

    [MenuItem("Edo/松平出羽守上屋敷/2 外周(塀・長屋・木柵)")]
    public static void Stage2Menu() { Debug.Log("[Matsudaira] " + Stage2_Perimeter()); }
    public static string Stage2_Perimeter()
    {
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
                EdoNishiTameikeBuilder.DobeiRun(kak, seg[0], seg[1], outw, r.name, false, r.seat, Vector2.zero, -1);
                hei++;
            }
        }
        // 表長屋は**辺の上で連続する run を1本の鎖**にして実寸ピッチで通す。
        // こうしないと段違いの run の継ぎ目に 8m の隙間があく(E1/E2/E3 の雛壇)。
        foreach (int e in new SortedSet<int>(new List<int>(Array.ConvertAll(
                     Array.FindAll(Runs, r => r.nagaya), r => r.edge))))
        {
            var onEdge = new List<Run>(Array.FindAll(Runs, r => r.nagaya && r.edge == e));
            onEdge.Sort((x, y) => x.s0.CompareTo(y.s0));
            // 連続する run をまとめる
            int i = 0;
            while (i < onEdge.Count)
            {
                float cs0 = onEdge[i].s0, cs1 = onEdge[i].s1;
                int j = i;
                while (j + 1 < onEdge.Count && Mathf.Abs(onEdge[j + 1].s0 - cs1) < 0.05f)
                { j++; cs1 = onEdge[j].s1; }
                var chain = onEdge.GetRange(i, j - i + 1);
                Func<float, float> seatAt = s =>
                {
                    foreach (var r in chain) if (s >= r.s0 - 0.01f && s <= r.s1 + 0.01f) return r.seat;
                    return chain[0].seat;
                };
                foreach (var seg in split(e, cs0, cs1))
                {
                    float a0 = Vector2.Dot(seg[0] - EdgePt(e, 0f), (EdgePt(e, 1f) - EdgePt(e, 0f)).normalized);
                    float a1 = Vector2.Dot(seg[1] - EdgePt(e, 0f), (EdgePt(e, 1f) - EdgePt(e, 0f)).normalized);
                    if (a1 - a0 < 4f) continue;
                    nag += NagayaChain(kak, e, a0, a1, seatAt, "NG_e" + e + "_" + Mathf.RoundToInt(a0));
                }
                i = j + 1;
            }
        }
        sb.AppendLine("塀・長屋: 長屋 " + nag + "棟 / 練塀run " + hei);

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
            const float SPAN = 4.6f;              // 実寸に合わせた並べピッチ[m]
            for (float s = s0 + SPAN * 0.5f; s < s1; s += SPAN)
            {
                Vector2 p = EdgePt(e, s);
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.Hogaki5, new Vector3(p.x, 0, p.y),
                                                     psi, Vector3.one, fen, (string)fdef["name"] + "_" + posts);
                if (go == null) continue;
                EdoNishiTameikeBuilder.SeatBottom(go, G(p.x, p.y) - 0.05f);
                posts++;
            }
        }
        sb.AppendLine("木柵: " + posts + "枚(" + A(D["fences"]).Count + " run)");
        return sb.ToString();
    }

    // ---------------------------------------------------------------- Stage3 石垣基壇
    // 作法は unity-modular-stonewall。要点:
    //   ・ピッチ 1.800×s(2.0×s モジュール)→ 継ぎ目ごとに 0.20×s 重なる
    //   ・**駒のピボットは走り方向の端**。ローカル箱は [pos − 2.0×s, pos]。
    //     だから開口は「縁を起点に外へ並べる」— skip では縁を狙えない(スキル §4)
    //   ・天端は run ごとに**一つの丸い数字**。position.y = seat − 4.0×s / scale.y = s
    //   ・地形を壁に合わせる。壁を地形に合わせない(ピースごとの scale.y は生成壁の兆候)
    [MenuItem("Edo/松平出羽守上屋敷/3 石垣基壇")]
    public static void Stage3Menu() { Debug.Log("[Matsudaira] " + Stage3_Ishigaki()); }
    public static string Stage3_Ishigaki()
    {
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
            if (r.ishi <= 0f) continue;                       // base=Ishigaki のみ
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
            float baseY = r.seat - 4.0f * r.ishi;             // 天端 = seat
            foreach (var sg in segs)
            {
                float t0 = sg[0], t1 = sg[1];
                float len0 = 2.0f * r.ishi, pit = 1.8f * r.ishi;
                if (t1 - t0 < len0 - 0.01f) continue;
                var ts = new List<float>();
                for (float t = t0 + len0; t <= t1 - 0.25f * pit; t += pit) ts.Add(t);
                ts.Add(t1);                                   // 端面を t1 に合わせる仕舞い
                foreach (float t in ts)
                {
                    Vector2 p = EdgePt(r.edge, t);
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.JC.CastleWall,
                        new Vector3(p.x, baseY, p.y), psi,
                        new Vector3(r.ishi, r.ishi, r.ishi), grp,
                        "IG_" + r.name + "_" + made);
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
            bool ng = (tmx - tmn) > 0.005f || py.Count > 1 || sy.Count > 1 || lat > 0.10f;
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

    // ---------------------------------------------------------------- 指図と実装の突き合わせ
    [MenuItem("Edo/松平出羽守上屋敷/指図と実装を突き合わせる")]
    public static void CompareMenu() { Debug.Log("[Matsudaira] " + Compare()); }
    public static string Compare()
    {
        var sb = new System.Text.StringBuilder();
        var f = Grid;
        var gate = O(D["gate"]);
        var gp = A(gate["pos"]);
        Vector2 jsonPos = new Vector2(F(gp[0]), F(gp[1]));
        Vector2 fromEdge = EdgePt((int)F(gate["edge"]), F(gate["s"]));
        sb.AppendLine("表門: json pos=" + jsonPos + " / 辺+s から=" + fromEdge +
                      " 差=" + (jsonPos - fromEdge).magnitude.ToString("F3") + "m");
        sb.AppendLine("グリッド原点=(" + f.x0 + "," + f.z0 + ") 表門芯との差=" +
                      (new Vector2(f.x0, f.z0) - jsonPos).magnitude.ToString("F3") + "m");
        sb.AppendLine("段 " + Terraces.Length + "枚 / run " + Runs.Length + "本 / 区画 " + Poly.Length + "頂点");

        // ---- 据わっている現物を指図と照合する ★これが無いと 106m ずれた棟が「0件」で通る
        // (2026-08-23 検図: 本数と GradeQA しか見ておらず、突き合わせが空手形になっていた)
        int ng = 0;
        var root = GameObject.Find(Grp);
        if (root == null) { sb.AppendLine("★ ルートが無い"); ng++; }
        else
        {
            float yawU = YawAlongU(), yawV = YawAlongV();
            var seen = new HashSet<string>();
            Action<Transform, string, Vector2, string> chk = (grp, name, want, kind) =>
            {
                seen.Add(name);
                var t = grp == null ? null : grp.Find(name);
                if (t == null) { sb.AppendLine("★ " + kind + " " + name + " が実装に無い"); ng++; return; }
                float dd = Vector2.Distance(new Vector2(t.position.x, t.position.z), want);
                if (dd > 0.02f)
                { sb.AppendLine("★ " + kind + " " + name + " が " + dd.ToString("F2") + "m ずれている"); ng++; }
            };
            var bld = root.transform.Find("Buildings");
            foreach (var o in A(D["munes"]))
            {
                var m = O(o);
                var w = Grid.W(F(m["u0"]), F(m["v1"]));
                chk(bld, (string)m["name"], w, "棟");
            }
            foreach (var o in A(D["links"]))
            {
                var l = O(o);
                float u0 = F(l["u0"]), v0 = F(l["v0"]), u1 = F(l["u1"]), v1 = F(l["v1"]);
                bool alongU = (u1 - u0) >= (v1 - v0);
                var w = alongU ? Grid.W(u0, v1) : Grid.W(u0, v0);
                chk(bld, (string)l["name"], w, "廊下");
            }
            if (bld != null)
                for (int i = 0; i < bld.childCount; i++)
                {
                    string n = bld.GetChild(i).name;
                    if (!seen.Contains(n)) { sb.AppendLine("★ 孤児(指図に無い): " + n); ng++; }
                }
            // 囲い — 指図の run/fence の名前が実装のグループ名に現れるか
            var kak = root.transform.Find("Kakoi");
            if (kak != null)
            {
                var have = new HashSet<string>();
                for (int i = 0; i < kak.childCount; i++) have.Add(kak.GetChild(i).name);
                foreach (var r in Runs) if (!have.Contains(r.name)) { sb.AppendLine("★ 囲い " + r.name + " が実装に無い"); ng++; }
                foreach (var nm in have)
                {
                    bool known = false;
                    foreach (var r in Runs) if (r.name == nm) { known = true; break; }
                    if (!known)
                        foreach (var o in A(D["fences"])) if ((string)O(o)["name"] == nm) { known = true; break; }
                    if (!known) { sb.AppendLine("★ 孤児の囲い: " + nm); ng++; }
                }
            }
        }
        sb.AppendLine(ng == 0 ? "指図と実装の突き合わせ: 0 件" : "★ 指図と実装の不一致 " + ng + " 件");
        sb.Append(GradeQA());
        return sb.ToString();
    }
}
