// 岡部筑前守(和泉岸和田藩5万3千石・譜代雁間)上屋敷 — 全面再構成 v3 (2026-08-14)
//
// 【v3 でやり直した理由】ユーザー差し戻し。v2 は
//   (1) 建屋を「台地の平場に載る分」だけ置いて敷地の大半を空地にした
//   (2) 御殿複合を表門の45°軸に合わせたため敷地形・外周長屋と向きが揃わなかった
//   越前福井藩上屋敷の再現3D(ユーザー提示)では敷地ほぼ全体に建屋が載り、外周塀と建物の向きが揃う。
//   v1/v2 の成果は削除せず SetActive(false) で保存する(§A-1)。
//
// 【区割りの典拠 = ユーザー下書き(2026-08-14, EdoSketch)】確度U。色は EdoSketch.Palette:
//   赤(0)=長屋  黄(1)=屋敷エリア(連続御殿複合)  桃(4)=庭園  緑(3)=塀  白(5)=表門前スペース
//   ・表門 = 東辺(三べ坂沿い) z≒1001。下書きの三角マークが表門の位置指定。
//     ⚠ 2026-08-12 の考証では「表門=北東辺(切絵図の文字の頭)」としていたが、
//        ユーザーの区割り指定を優先する。北東の隅切り辺は長屋になる。
//   ・長屋 = 南辺全部 + 東辺全部(表門の開口を除く) + 北東の隅切り辺 + 内部の南北二列(x=-558/-572)
//   ・塀   = 西辺・北辺(溜池の汀と土井/松平との隣地境)
//   ・屋敷エリアは台地と東西の低地にまたがる。ユーザー指示:
//     「高地と低地でつながっていますが、この部分は廊下と階段とかで繋げてください」
//     → 段の間は渡り廊下(Roka)と石段(Kaidan)で一続きにする。
//   ・「連続御殿複合の屋敷内にも廊下を設置して建物内を移動できるように」(2026-08-14 追加指示)
//     → 棟と棟の間にも渡り廊下を通す。
//
// 【格式の判断】御成門・能舞台・御成風呂は作らない。御成対応は原則として家門・大藩の装置で、
//   [福井図]で御成門を持つ越前松平は家門。譜代雁間5.3万石の当家に御成セットの典拠はない。
//   【典拠: estate-types.md 上屋敷の項/当屋敷の一次史料は未確認】
//
// 【地形】§B-1。段は「建物が載る大きな平場」で、雛壇リボンではない。
//   主郭25.5 / 東三段22.0・18.0・14.5 / 表門前13.5 / 西低地9.5。
//   西斜面(x -602..-576)は勾配41〜65%で平場にできない → 階段廊下と法面・庭のみ。
//   切盛 clamp = 切4.0 / 盛5.0(菊地2003「1〜4mが多い」/紀伊家紀尾井町の盛土5.0mが上限実例)。
//   backup = scratchpad/okabe_v3_backup.bin
//
// ⚠ MCP タイムアウト後の再送で多重実行が起きる。地形ステージはマーカーで、
//   構造ステージは「作る前に消す」で冪等にしてある。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using B = EdoSanbezakaBuilder;
using NT = EdoNishiTameikeBuilder;
using SK = EdoSannoKitaBuilder;

public static class EdoOkabeYashikiBuilder
{
    public const string GN = "Edo_Yashiki_OkabeChikuzen";
    const float ES = 1.818f;
    const float CUT_MAX = 5.5f, FILL_MAX = 5.0f;
    // 表門 = 冠木門形式の k_mon(EdoSanbezakaBuilder には無い)
    const string PKmon = "Assets/edogoyomi/es_kmon/k_mon.obj";

    // ---------- 段(平場)の定義: x範囲 / z範囲 / 高さ ----------
    public struct Terr { public float x0, x1, z0, z1, y; public string name; }
    public static Terr[] Terraces()
    {
        return new[] {
            new Terr{ name="Shukaku", x0=-566f, x1=-455f, z0=946f, z1=1058f, y=25.5f },
            new Terr{ name="TE3",     x0=-455f, x1=-435f, z0=946f, z1=1058f, y=21.5f },
            new Terr{ name="TE2",     x0=-435f, x1=-415f, z0=946f, z1=1058f, y=17.5f },
            new Terr{ name="TE1",     x0=-415f, x1=-374f, z0=946f, z1=1058f, y=13.5f },
            new Terr{ name="Chudan",  x0=-592f, x1=-566f, z0=950f, z1=1052f, y=19.5f },
            new Terr{ name="TW1",     x0=-647f, x1=-592f, z0=950f, z1=1052f, y=11.5f },
        };
    }
    // 石垣(土留め)の芯線 = 外面。天端は上段のレベル、scale.y は 4.0m/1.0 の丸数字。
    // 走り方向の左(local -X)に躯体2.4mが出るので、高い側が左になるよう a→b を取る。
    public struct Wall { public Vector2 a, b; public float coping, sy; public string name; public float gapZ; }
    public static Wall[] Walls()
    {
        return new[] {
            // 東: 主郭→TE3→TE2→門前。南→北へ走る(左=西=高い側)
            new Wall{ name="IG_E1", a=new Vector2(-455f, 947f), b=new Vector2(-455f, 1056f), coping=25.5f, sy=1.0f, gapZ=1001f },
            new Wall{ name="IG_E2", a=new Vector2(-435f, 947f), b=new Vector2(-435f, 1056f), coping=21.5f, sy=1.0f, gapZ=1001f },
            new Wall{ name="IG_E3", a=new Vector2(-415f, 947f), b=new Vector2(-415f, 1056f), coping=17.5f, sy=1.0f, gapZ=1001f },
            // 西: 主郭→中段→西低地。北→南へ走る(左=東=高い側)
            new Wall{ name="IG_W1", a=new Vector2(-566f, 1052f), b=new Vector2(-566f, 949f), coping=25.5f, sy=1.5f, gapZ=1006f },
            new Wall{ name="IG_W2", a=new Vector2(-592f, 1052f), b=new Vector2(-592f, 949f), coping=19.5f, sy=2.0f, gapZ=1006f },
        };
    }
    // 建屋を置ける矩形(段の内側、外周長屋・庭園帯・法面を除いた実効ゾーン)
    public struct Zone { public float x0, x1, z0, z1, y; public string name; }
    public static Zone[] Zones()
    {
        return new[] {
            new Zone{ name="Shukaku", x0=-556f, x1=-456f, z0=957f, z1=1054f, y=25.5f },
            new Zone{ name="TE3",     x0=-454f, x1=-438f, z0=957f, z1=1054f, y=21.5f },
            new Zone{ name="TE2",     x0=-434f, x1=-418f, z0=957f, z1=1054f, y=17.5f },
            new Zone{ name="TE1",     x0=-414f, x1=-402f, z0=957f, z1=1048f, y=13.5f },
            new Zone{ name="Chudan",  x0=-589f, x1=-568f, z0=956f, z1=1048f, y=19.5f },
            new Zone{ name="TW1",     x0=-645f, x1=-594f, z0=956f, z1=1048f, y=11.5f },
        };
    }
    // 中庭(建屋を置かない矩形)
    public static Rect[] Courts()
    {
        return new[] {
            new Rect(-537f, 1000f, 20f, 22f),   // 表の中庭
            new Rect(-497f, 1030f, 22f, 20f),   // 奥の中庭
            new Rect(-505f,  965f, 18f, 18f),   // 台所前の坪庭
            new Rect(-634f, 1000f, 16f, 16f),   // 西低地の内庭
        };
    }
    // 表門(下書きの三角マーク) と その外向き
    public static readonly Vector2 GATE = new Vector2(-381.0f, 1001.0f);
    public static Vector2 GateOut() { return (-B.InwardNormal(SK.OKABE, 10)).normalized; }
    public static float YawGate() { var o = GateOut(); return Mathf.Atan2(o.x, o.y) * Mathf.Rad2Deg; }

    // 外周長屋・塀・内部長屋の芯線(下書きを垂直水平に正規化)
    public struct Run { public Vector2 a, b, outw; public string name; public bool nagaya; }
    public static Run[] Runs()
    {
        var P = SK.OKABE;
        Func<int, Vector2> eo = i => -B.InwardNormal(P, i);
        var d10 = (P[0] - P[10]).normalized;              // 東辺の走り(北→南)
        return new[] {
            new Run{ name="NG_S0", a=P[3], b=P[2], outw=eo(2), nagaya=true },   // 南辺(西)
            new Run{ name="NG_S1", a=P[2], b=P[1], outw=eo(1), nagaya=true },   // 南辺(中)
            new Run{ name="NG_S2", a=P[1], b=P[0], outw=eo(0), nagaya=true },   // 南辺(東)
            new Run{ name="NG_E_S", a=P[0], b=GATE + d10 * 6.5f, outw=eo(10), nagaya=true },  // 東辺 南半
            new Run{ name="NG_E_N", a=GATE - d10 * 6.5f, b=P[10], outw=eo(10), nagaya=true }, // 東辺 北半
            new Run{ name="NG_NE",  a=P[10], b=P[9], outw=eo(9), nagaya=true },  // 北東の隅切り辺
            new Run{ name="Hei_N1", a=P[9], b=P[8], outw=eo(8), nagaya=false },
            new Run{ name="Hei_N2", a=P[8], b=P[7], outw=eo(7), nagaya=false },
            new Run{ name="Hei_N3", a=P[7], b=P[6], outw=eo(6), nagaya=false },
            new Run{ name="Hei_W1", a=P[6], b=P[5], outw=eo(5), nagaya=false },
            new Run{ name="Hei_W2", a=P[5], b=P[4], outw=eo(4), nagaya=false },
            new Run{ name="Hei_W3", a=P[4], b=P[3], outw=eo(3), nagaya=false },
        };
    }

    static string BAK = "/private/tmp/claude-501/-Users-toshio-project-edo-unity/"
        + "0481f3c6-e686-419e-90e8-8fbaf448079d/scratchpad/okabe_v3_backup.bin";
    const string PFloor = "Assets/Japanese Village Kit/Prefabs/Walls and floors/floor interior 2x2.prefab";
    const string PCol = "Assets/Japanese Village Kit/Prefabs/Walls and floors/column A .prefab";
    const string PRoof = "Assets/Japanese Village Kit/Prefabs/Roofs/roof 2x8.prefab";
    const string PRoofEnd = "Assets/Japanese Village Kit/Prefabs/Roofs/roof end 2x1.prefab";
    const string PStep = "Assets/Edo/Models/Shiomizaka/P_DanishiStep2m.prefab";
    const string PKnagayaC = "Assets/edogoyomi/es_knagaya/knagaya01c.obj";
    static string[] Pines = {
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_01.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_02.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_03.prefab" };
    static string[] Shrubs = {
        "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 01.prefab",
        "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 03.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_01.prefab" };
    static string[] Bamboo = {
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_01.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_02.prefab" };

    static float G(float x, float z) { return B.Ground(x, z); }
    static Transform Grp(string n) { return B.Group(GN, n); }
    static void Clear(Transform t) { var l = new List<Transform>(); foreach (Transform c in t) l.Add(c); foreach (var c in l) UnityEngine.Object.DestroyImmediate(c.gameObject); }
    static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
    { var d = b - a; float L = d.magnitude; if (L < 1e-4f) return (p - a).magnitude; d /= L; float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, L); return (p - (a + d * t)).magnitude; }

    // =========================================================================
    // Stage 0/1: バックアップと段の造成
    // =========================================================================
    public static string Stage0_Backup()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int bx0 = IX(-700f), bx1 = IX(-370f), bz0 = IZ(930f), bz1 = IZ(1100f);
        int bw = bx1 - bx0 + 1, bh = bz1 - bz0 + 1;
        var bak = td.GetHeights(bx0, bz0, bw, bh);
        using (var w = new System.IO.BinaryWriter(System.IO.File.Open(BAK, System.IO.FileMode.Create)))
        { w.Write(bx0); w.Write(bz0); w.Write(bw); w.Write(bh);
          for (int z = 0; z < bh; z++) for (int x = 0; x < bw; x++) w.Write(bak[z, x]); }
        return "backup " + bw + "x" + bh;
    }

    public static string Stage1_Grade()
    {
        var mk = GameObject.Find("OKABE_GRADED_v3");
        if (mk != null) return "grade: SKIP (already graded v3)";
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        Func<float, float> HtoW = hn => hn * ts.y + tp.y;
        Func<float, float> WtoH = wy => (wy - tp.y) / ts.y;
        var terr = Terraces();
        int x0 = IX(-660f), x1 = IX(-368f), z0 = IZ(938f), z1 = IZ(1070f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0; float cmax = 0, fmax = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            float wx = WX(x0 + x), wz = WZ(z0 + z);
            var p = new Vector2(wx, wz);
            if (!B.PIP(SK.OKABE, p)) continue;
            // 隣地の囲い(土井/松平所有)がある辺 4..7 は 9m、他は 1.4m あける
            float em = float.MaxValue;
            for (int i = 0; i < SK.OKABE.Length; i++)
                em = Mathf.Min(em, DistSeg(p, SK.OKABE[i], SK.OKABE[(i + 1) % SK.OKABE.Length]) - ((i >= 4 && i <= 7) ? 9f : 1.4f));
            if (em < 0f) continue;
            // どの段に属するか + 段の内側への距離
            float best = -1f, bestD = -1f;
            foreach (var tr in terr)
            {
                if (wx < tr.x0 || wx > tr.x1 || wz < tr.z0 || wz > tr.z1) continue;
                float d = Mathf.Min(Mathf.Min(wx - tr.x0, tr.x1 - wx), Mathf.Min(wz - tr.z0, tr.z1 - wz));
                if (d > bestD) { bestD = d; best = tr.y; }
            }
            if (best < 0f) continue;
            // 段の境目では隣の段と噛み合うので、フェザーは段の縁3m + 敷地際4m だけ
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(Mathf.Clamp01(bestD / 3f + 0.34f), Mathf.Clamp01(em / 4f)));
            if (k <= 0.001f) continue;
            float cur = HtoW(H[z, x]);
            // 石垣の近傍は clamp しない — 地面を壁に合わせる(unity-modular-stonewall §3)
            bool nearWall = false;
            foreach (var wl in Walls()) if (DistSeg(p, wl.a, wl.b) < 7f) { nearWall = true; break; }
            float tgt = nearWall ? best : Mathf.Clamp(best, cur - CUT_MAX, cur + FILL_MAX);
            float nw = Mathf.Lerp(cur, tgt, k);
            if (nw < cur) cmax = Mathf.Max(cmax, cur - nw); else fmax = Mathf.Max(fmax, nw - cur);
            H[z, x] = WtoH(nw); n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        // ⚠ マーカーは active のままにする。GameObject.Find は非アクティブを見つけないので
        //    SetActive(false) にするとガードが毎回すり抜けて多重造成する(2026-08-14 に実際に起きた)。
        mk = new GameObject("OKABE_GRADED_v3");
        var yg = GameObject.Find(GN); if (yg != null) mk.transform.SetParent(yg.transform, false);
        return "grade cells=" + n + " cutMax=" + cmax.ToString("F2") + " fillMax=" + fmax.ToString("F2");
    }

    // =========================================================================
    // Stage 2: 全再接地(石段・飛石・廊下は除外 — 設計レベルで据えてある)
    // =========================================================================
    public static string Stage2_Reseat()
    {
        int n = 0;
        var yg = GameObject.Find(GN);
        var roots = new List<Transform>();
        foreach (Transform g in yg.transform)
            if (g.name != "Roka" && g.name != "Garden" && g.name != "Ishigaki"
                && g.name != "KachuNagaya" && !g.name.EndsWith("_retired")) roots.Add(g);
        var sha = GameObject.Find("Edo_Sanno_Sha"); if (sha != null) roots.Add(sha.transform);
        foreach (var grp in roots)
            foreach (Transform c in grp)
            {
                if (!c.gameObject.activeSelf) continue;
                if (c.name.StartsWith("Ishidan") || c.name.StartsWith("Tobi") || c.name.StartsWith("Roka")) continue;
                var p = new Vector2(c.position.x, c.position.z);
                if (!B.PIP(SK.OKABE, p)) continue;
                if (ReseatOne(c, 0.10f)) n++;
            }
        return "reseat " + n;
    }
    static bool ReseatOne(Transform tr, float sink)
    {
        Vector3 mn = Vector3.one * float.MaxValue, mx = Vector3.one * float.MinValue; bool any = false;
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            foreach (var v in mf.sharedMesh.vertices)
            { var lp = tr.InverseTransformPoint(mf.transform.TransformPoint(v)); mn = Vector3.Min(mn, lp); mx = Vector3.Max(mx, lp); any = true; }
        }
        if (!any) return false;
        float gmn = float.MaxValue, bot = float.MaxValue;
        for (int i = 0; i <= 2; i++) for (int j = 0; j <= 2; j++)
        {
            var wp = tr.TransformPoint(new Vector3(Mathf.Lerp(mn.x, mx.x, i / 2f), mn.y, Mathf.Lerp(mn.z, mx.z, j / 2f)));
            gmn = Mathf.Min(gmn, G(wp.x, wp.z)); bot = Mathf.Min(bot, wp.y);
        }
        float dy = (gmn - sink) - bot;
        if (Mathf.Abs(dy) < 0.005f) return false;
        tr.position += new Vector3(0, dy, 0); return true;
    }

    // =========================================================================
    // Stage 3: v1/v2 の撤去(削除しない)
    // =========================================================================
    public static string Stage3_Retire()
    {
        int n = 0;
        var yg = GameObject.Find(GN);
        foreach (var gname in new[] { "Buildings", "Garden", "Service", "Kakoi", "Omotemon" })
        {
            var g = yg.transform.Find(gname);
            if (g == null || g.childCount == 0) continue;
            string rn = gname + "_v2_retired";
            var keep = yg.transform.Find(rn);
            if (keep == null)
            { var go = new GameObject(rn); Undo.RegisterCreatedObjectUndo(go, "retire"); go.transform.SetParent(yg.transform, false); keep = go.transform; }
            var kids = new List<Transform>(); foreach (Transform c in g) kids.Add(c);
            foreach (var c in kids) { c.SetParent(keep, true); c.gameObject.SetActive(false); n++; }
            keep.gameObject.SetActive(false);
        }
        return "retired " + n;
    }

    // =========================================================================
    // Stage 4: 外周長屋・築地塀・表門・隅櫓
    // =========================================================================
    public static string Stage4_Perimeter()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        var kak = Grp("Kakoi"); Clear(kak);
        var mon = Grp("Omotemon"); Clear(mon);
        int nm = 0;
        foreach (var r in Runs())
        {
            if ((r.b - r.a).magnitude < 6f) continue;
            if (r.nagaya) { var l = NT.NagayaRun(kak, r.a, r.b, r.outw, 0f, Vector2.zero, -1, r.name); nm += l.Count; }
            else NT.DobeiRun(kak, r.a, r.b, r.outw, r.name, true, 0, Vector2.zero, -1);
        }
        sb.AppendLine("nagaya modules=" + nm);
        // 表門(k_mon + 両番所) — 東辺、下書きの三角マーク位置
        float gh = B.PlaceGate(PKmon, mon, GATE, GateOut(), 2, "Kmon", sb);
        // 隅櫓 [福井図: 上屋敷格の外周装置] — 敷地の南東隅・南西隅
        Yagura(kak, new Vector2(-378.5f, 950.5f), new Vector2(0.83f, -0.56f), "Sumiyagura_SE");
        Yagura(kak, new Vector2(-643.5f, 940.5f), new Vector2(-0.72f, -0.69f), "Sumiyagura_SW");
        return sb.ToString();
    }
    static void Yagura(Transform parent, Vector2 p, Vector2 bis, string nm)
    {
        var ex = parent.Find(nm); if (ex != null) UnityEngine.Object.DestroyImmediate(ex.gameObject);
        float psi = Mathf.Atan2(bis.x, bis.y) * Mathf.Rad2Deg;
        float y = G(p.x, p.y);
        var go = B.Place(PKnagayaC, new Vector3(p.x, y, p.y), psi, new Vector3(ES * 0.55f, ES, ES), parent, nm);
        var rb = B.RB(go); go.transform.position += new Vector3(p.x - rb.center.x, 0, p.y - rb.center.z);
        rb = B.RB(go); go.transform.position += new Vector3(0, (y + 0.85f) - rb.min.y, 0);
    }

    // =========================================================================
    // Stage 4b: 石垣(段の土留め) + 天端に載る家臣長屋2列
    //   unity-modular-stonewall §2/§3: ピッチ1.800(0.20重ね) / 1本の壁に position.y と scale.y は1値ずつ /
    //   coping = position.y + 4.0*scale.y / 躯体2.4mは走りの左(local -X)に出る。
    // =========================================================================
    const string P_CW = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Castle Wall.prefab";
    public static string Stage4b_Ishigaki()
    {
        var ig = Grp("Ishigaki"); Clear(ig);
        var kn = Grp("KachuNagaya"); Clear(kn);
        var sb = new System.Text.StringBuilder();
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(P_CW);
        foreach (var w in Walls())
        {
            Vector2 d = (w.b - w.a); float L = d.magnitude; d /= L;
            float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
            float posY = w.coping - 4f * w.sy;
            float gapT = Vector2.Dot(new Vector2(w.a.x, w.gapZ) - w.a, d);   // 階段開口の走り座標
            int n = Mathf.Max(2, Mathf.RoundToInt((L - 2f) / 1.8f) + 1);
            int made = 0;
            for (int i = 0; i < n; i++)
            {
                float t = 2f + 1.8f * i;
                if (t > L + 0.4f) break;
                if (Mathf.Abs(t - gapT) < 4.0f) continue;          // 階段の開口(§4: 1本のrunから切り取る)
                var p = w.a + d * t;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, ig);
                Undo.RegisterCreatedObjectUndo(go, "cw"); go.name = w.name + "_" + i;
                go.transform.position = new Vector3(p.x, posY, p.y);
                go.transform.rotation = Quaternion.Euler(0, yaw, 0);
                go.transform.localScale = new Vector3(1f, w.sy, 1f);
                made++;
            }
            sb.AppendLine(w.name + " pieces=" + made + " posY=" + posY.ToString("F2") + " sy=" + w.sy.ToString("F2") + " coping=" + w.coping.ToString("F2"));
        }
        // 家臣長屋2列 — 西の石垣A/Bの天端に載せる(下書きの赤線2本)
        // perimeter.md: なまこ壁の外面を天端の外面と面一(0.00〜0.20m)、土台底 = 天端 − 1.59m
        bool nm0 = NT.NaturalMode; NT.NaturalMode = false;
        foreach (var w in Walls())
        {
            if (!w.name.StartsWith("IG_W")) continue;
            Vector2 outw = new Vector2(-1f, 0f);                    // 西向き
            var mods = NT.NagayaRun(kn, w.a + new Vector2(2.2f, 0), w.b + new Vector2(2.2f, 0), outw,
                w.coping - 1.49f, new Vector2(w.a.x, w.gapZ), 4.5f, "KN_" + w.name);
            // なまこ外面を天端外面(= 壁の芯線 x = w.a.x)へ面一に寄せる
            if (mods.Count > 0)
            {
                float sum = 0; int c = 0;
                foreach (var m in mods)
                {
                    float mx = float.MinValue;
                    foreach (var mf in m.GetComponentsInChildren<MeshFilter>())
                    {
                        if (!mf.gameObject.name.ToLower().Contains("namako")) continue;
                        foreach (var v in mf.sharedMesh.vertices)
                        { var wp = mf.transform.TransformPoint(v); mx = Mathf.Max(mx, wp.x * outw.x + wp.z * outw.y); }
                    }
                    if (mx > float.MinValue) { sum += mx; c++; }
                }
                if (c > 0)
                {
                    float crestOuter = w.a.x * outw.x;
                    float shift = 0.02f - (crestOuter - sum / c);
                    foreach (var m in mods) m.transform.position += new Vector3(-outw.x * shift, 0, -outw.y * shift);
                    sb.AppendLine("KN_" + w.name + " modules=" + mods.Count + " flushShift=" + shift.ToString("F3"));
                }
            }
        }
        NT.NaturalMode = nm0;
        return sb.ToString();
    }

    // =========================================================================
    // Stage 5: 連続御殿複合 — 各段をシェルフ充填で埋める
    // =========================================================================
    struct Slot { public string path; public float w, d; public string label; }
    static Slot S(string p, float w, float d, string l) { return new Slot { path = p, w = w, d = d, label = l }; }

    public static string Stage5_Goten()
    {
        var sb = new System.Text.StringBuilder();
        var bg = Grp("Buildings"); Clear(bg);
        var courts = Courts();
        var rnd = new System.Random(53114);
        // 躯体寸法(ry=0): BigHouse 26.2x24.2 / House 18.2x14.3 / HouseB 8.2x17.1 / SmallHouse 12.2x8.2
        var big = new[] { S(B.PBigHouse, 26.2f, 24.2f, "OmoteGoten"), S(B.PHouse, 18.2f, 14.3f, "Goten"),
                          S(B.PHouseB, 17.1f, 8.2f, "Tsubone"), S(B.PSmallHouse, 12.2f, 8.2f, "Koya") };
        var narrow = new[] { S(B.PHouseB, 17.1f, 8.2f, "Tsubone"), S(B.PSmallHouse, 12.2f, 8.2f, "Koya"),
                             S(B.PHouse, 14.3f, 18.2f, "Goten"), S(B.PHouseB, 8.2f, 17.1f, "TsuboneB") };
        int total = 0; float area = 0;
        foreach (var zn in Zones())
        {
            var pal = (zn.x1 - zn.x0) >= 30f ? big : narrow;
            float z = zn.z0; int idx = 0;
            while (z < zn.z1 - 7f)
            {
                float rowD = 0; float x = zn.x0; var row = new List<Slot>();
                // 行を組み立てる(行の奥行 = その行で一番深い棟)
                while (x < zn.x1 - 7f)
                {
                    var cand = pal[rnd.Next(pal.Length)];
                    if (x + cand.w > zn.x1) { var alt = pal.OrderBy(q => q.w).First(); if (x + alt.w > zn.x1) break; cand = alt; }
                    if (z + cand.d > zn.z1) { var alt = pal.OrderBy(q => q.d).First(); if (z + alt.d > zn.z1) break; cand = alt; }
                    row.Add(cand); x += cand.w + 0.6f; rowD = Mathf.Max(rowD, cand.d);
                }
                if (row.Count == 0) break;
                x = zn.x0;
                foreach (var c in row)
                {
                    float cx = x + c.w * 0.5f, cz = z + c.d * 0.5f;
                    bool skip = false;
                    foreach (var ct in courts)
                        if (cx + c.w * 0.5f > ct.xMin && cx - c.w * 0.5f < ct.xMax && cz + c.d * 0.5f > ct.yMin && cz - c.d * 0.5f < ct.yMax) skip = true;
                    // 参道(表門→玄関 z=1001付近)は東三段だけ空ける
                    if (zn.x0 > -460f && Mathf.Abs(cz - 1001f) < 5.5f) skip = true;
                    if (!skip)
                    {
                        float ry = (Mathf.Abs(c.w - 17.1f) < 0.05f || Mathf.Abs(c.w - 12.2f) < 0.05f || Mathf.Abs(c.w - 26.2f) < 0.05f || Mathf.Abs(c.w - 18.2f) < 0.05f) ? 0f : 90f;
                        var go = B.Place(c.path, Vector3.zero, ry, Vector3.one, bg, zn.name + "_" + c.label + "_" + (idx++));
                        var rb = B.RB(go);
                        go.transform.position += new Vector3(cx - rb.center.x, 0, cz - rb.center.z);
                        rb = B.RB(go);
                        go.transform.position += new Vector3(0, (zn.y - 0.12f) - rb.min.y, 0);
                        total++; area += c.w * c.d;
                    }
                    x += c.w + 0.6f;
                }
                z += rowD + 0.6f;
            }
        }
        sb.AppendLine("goten units=" + total + " bodyArea=" + area.ToString("F0"));
        return sb.ToString();
    }

    // =========================================================================
    // Stage 6: 廊下 — 棟間の渡り廊下と、段をつなぐ石段
    // =========================================================================
    public static string Stage6_Roka()
    {
        var rk = Grp("Roka"); Clear(rk);
        int nr = 0, nk = 0;
        // 東: 石垣の開口を石段で降りる。主郭25.5 → TE3 21.5 → TE2 17.5 → 門前13.5
        float[] xs = { -455f, -435f, -415f };
        float[] ys = { 25.5f, 21.5f, 17.5f, 13.5f };
        for (int i = 0; i < xs.Length; i++)
        { Kaidan(rk, new Vector2(xs[i] + 2.6f, 1001f), new Vector2(xs[i] - 1.6f, 1001f), ys[i], ys[i + 1], "Kaidan_E" + i); nk++; }
        // 各段の上を東西に通る渡り廊下(参道)
        Roka(rk, new Vector2(-434f, 1001f), new Vector2(-417f, 1001f), 21.5f, "Roka_TE3", false); nr++;
        Roka(rk, new Vector2(-414f, 1001f), new Vector2(-397f, 1001f), 17.5f, "Roka_TE2", false); nr++;
        Roka(rk, new Vector2(-413f, 1001f), new Vector2(-390f, 1001f), 13.5f, "Roka_Monzen", false); nr++;
        // 主郭の背骨(南北・東西)
        Roka(rk, new Vector2(-505f, 962f), new Vector2(-505f, 1052f), 25.5f, "Roka_ShukakuNS", false); nr++;
        Roka(rk, new Vector2(-553f, 1006f), new Vector2(-458f, 1006f), 25.5f, "Roka_ShukakuEW", false); nr++;
        // 主郭 → 石垣A → 中段 → 石垣B → 西低地
        Kaidan(rk, new Vector2(-563.4f, 1006f), new Vector2(-568f, 1006f), 25.5f, 19.5f, "Kaidan_W1"); nk++;
        Roka(rk, new Vector2(-569f, 1006f), new Vector2(-589f, 1006f), 19.5f, "Roka_Chudan", false); nr++;
        Kaidan(rk, new Vector2(-589.4f, 1006f), new Vector2(-594f, 1006f), 19.5f, 11.5f, "Kaidan_W2"); nk++;
        Roka(rk, new Vector2(-595f, 1006f), new Vector2(-644f, 1006f), 11.5f, "Roka_Seiteichi", false); nr++;
        Roka(rk, new Vector2(-620f, 960f), new Vector2(-620f, 1046f), 11.5f, "Roka_SeiteichiNS", false); nr++;
        Roka(rk, new Vector2(-578f, 958f), new Vector2(-578f, 1046f), 19.5f, "Roka_ChudanNS", false); nr++;
        return "roka=" + nr + " kaidan=" + nk;
    }

    // 幅2mの渡り廊下: 床 + 柱 + 屋根。followGround=true なら地面に沿わせる(参道用)
    static void Roka(Transform parent, Vector2 a, Vector2 b, float level, string nm, bool followGround)
    {
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "roka");
        Vector2 d = (b - a); float L = d.magnitude; d /= L;
        float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
        var rot = Quaternion.Euler(0, yaw, 0);
        var floorPre = AssetDatabase.LoadAssetAtPath<GameObject>(PFloor);
        var colPre = AssetDatabase.LoadAssetAtPath<GameObject>(PCol);
        var roofPre = AssetDatabase.LoadAssetAtPath<GameObject>(PRoof);
        Vector2 nrm = new Vector2(-d.y, d.x);
        int nseg = Mathf.Max(1, Mathf.RoundToInt(L / 2f));
        for (int i = 0; i < nseg; i++)
        {
            float t = (i + 0.5f) * (L / nseg);
            var p = a + d * t;
            float y = followGround ? G(p.x, p.y) + 0.45f : level + 0.45f;
            var f = (GameObject)PrefabUtility.InstantiatePrefab(floorPre, g.transform);
            Undo.RegisterCreatedObjectUndo(f, "rf"); f.name = "RokaFloor_" + i;
            f.transform.position = new Vector3(p.x, y, p.y); f.transform.rotation = rot;
            for (int s = -1; s <= 1; s += 2)
            {
                var q = p + nrm * (s * 1.0f);
                var c = (GameObject)PrefabUtility.InstantiatePrefab(colPre, g.transform);
                Undo.RegisterCreatedObjectUndo(c, "rc"); c.name = "RokaCol_" + i + "_" + s;
                c.transform.position = new Vector3(q.x, y, q.y); c.transform.rotation = rot;
            }
        }
        int nroof = Mathf.Max(1, Mathf.RoundToInt(L / 8f));
        for (int i = 0; i < nroof; i++)
        {
            float t = (i + 0.5f) * (L / nroof);
            var p = a + d * t;
            float y = followGround ? G(p.x, p.y) + 0.45f : level + 0.45f;
            var r = (GameObject)PrefabUtility.InstantiatePrefab(roofPre, g.transform);
            Undo.RegisterCreatedObjectUndo(r, "rr"); r.name = "RokaRoof_" + i;
            r.transform.rotation = rot;
            r.transform.localScale = new Vector3(1f, 1f, (L / nroof) / 8f);
            var lp = p + nrm * (-1.05f);
            r.transform.position = new Vector3(lp.x, y + 3.0f + 1.06f, lp.y);
        }
    }

    // 段差をつなぐ石段(蹴上0.30m・幅6m=3列)
    static void Kaidan(Transform parent, Vector2 top, Vector2 bot, float yTop, float yBot, string nm)
    {
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "kaidan");
        int n = Mathf.Max(1, Mathf.RoundToInt((yTop - yBot) / 0.30f));
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(PStep);
        Vector2 d = (bot - top); float L = d.magnitude; d /= L;
        Vector2 nrm = new Vector2(-d.y, d.x);
        float yaw = Mathf.Atan2(nrm.x, nrm.y) * Mathf.Rad2Deg;
        for (int i = 0; i <= n; i++)
        {
            float tt = (float)i / n;
            var p = top + d * (L * tt);
            float lvl = Mathf.Lerp(yTop, yBot, tt);
            for (int c = -1; c <= 1; c++)
            {
                var q = p + nrm * (c * 2.0f);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, g.transform);
                Undo.RegisterCreatedObjectUndo(go, "st"); go.name = "Ishidan_" + i + "_" + (c + 1);
                go.transform.rotation = Quaternion.Euler(0, yaw, 0);
                var rb = B.RB(go);
                go.transform.position += new Vector3(q.x - rb.center.x, lvl - rb.max.y, q.y - rb.center.z);
            }
        }
    }

    // =========================================================================
    // Stage 7: 服務棟(蔵・厩・稲荷・井戸)
    // =========================================================================
    public static string Stage7_Service()
    {
        var sv = Grp("Service"); Clear(sv);
        float yaw = YawGate();
        // 土蔵群 = 西低地(勝手向きの下段) [福井図: 土蔵は御殿から離した下側の空地]
        for (int i = 0; i < 4; i++)
        {
            var kr = B.Place(B.PKura, Vector3.zero, 90f, Vector3.one * ES, sv, "Kura_W" + (i + 1));
            var rb = B.RB(kr);
            float cx = -640f, cz = 1018f + i * 8.0f;
            kr.transform.position += new Vector3(cx - rb.center.x, 0, cz - rb.center.z);
            rb = B.RB(kr); kr.transform.position += new Vector3(0, (G(cx, cz) - 0.15f) - rb.min.y, 0);
        }
        B.Well(sv, -632f, 1010f);
        foreach (Transform c in sv) if (c.name == "Ido") { c.name = "Ido_Kura"; break; }
        // 表門前(13.5m段) = 厩 + 供待 [西川1959: 厩は表門まわりの帯]
        Umaya(sv, new Vector2(-393f, 1026f), 90f, "Umaya");
        var tm = B.Place(B.PSmallHouse, Vector3.zero, yaw, Vector3.one, sv, "Tomomachi");
        { var rb = B.RB(tm); tm.transform.position += new Vector3(-393f - rb.center.x, 0, 976f - rb.center.z);
          rb = B.RB(tm); tm.transform.position += new Vector3(0, (G(-393f, 976f) - 0.12f) - rb.min.y, 0); }
        // 邸内稲荷 = 鬼門(北東)。主郭の北東寄り
        Inari(sv, new Vector2(-461f, 1050f));
        B.Well(sv, -523f, 985f);
        foreach (Transform c in sv) if (c.name == "Ido") { c.name = "Ido_Katte"; break; }
        return "service ok";
    }
    static void Umaya(Transform parent, Vector2 c, float psi, string nm)
    {
        const float PITCH = 7.81f;
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var m1 = B.Place(B.PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = B.Place(B.PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        Vector2 p1 = c - negRight * (PITCH * 0.5f), p2 = c + negRight * (PITCH * 0.5f);
        float y = Mathf.Min(G(p1.x, p1.y), G(p2.x, p2.y));
        m1.transform.position = new Vector3(p1.x, y, p1.y); m2.transform.position = new Vector3(p2.x, y, p2.y);
        var b1 = B.RB(m1); m1.transform.position += new Vector3(0, (y - 0.10f) - b1.min.y, 0);
        var b2 = B.RB(m2); m2.transform.position += new Vector3(0, (y - 0.10f) - b2.min.y, 0);
    }
    static void Inari(Transform parent, Vector2 pos)
    {
        float y = G(pos.x, pos.y);
        var g = new GameObject("Inari"); g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(pos.x, y, pos.y);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        Func<Color, Material> M = c => { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; };
        var shu = M(new Color(0.78f, 0.15f, 0.08f)); var stone = M(new Color(0.55f, 0.55f, 0.52f)); var wood = M(new Color(0.42f, 0.30f, 0.18f));
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "t_post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.18f, 1.25f, 0.18f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.9f : 0.9f, 1.25f, -2.2f);
            post.GetComponent<Renderer>().sharedMaterial = shu;
        }
        var ka = GameObject.CreatePrimitive(PrimitiveType.Cube); ka.name = "t_kasagi"; ka.transform.SetParent(g.transform, false);
        ka.transform.localScale = new Vector3(2.6f, 0.16f, 0.2f); ka.transform.localPosition = new Vector3(0, 2.5f, -2.2f);
        ka.GetComponent<Renderer>().sharedMaterial = shu;
        var nu = GameObject.CreatePrimitive(PrimitiveType.Cube); nu.name = "t_nuki"; nu.transform.SetParent(g.transform, false);
        nu.transform.localScale = new Vector3(2.2f, 0.12f, 0.14f); nu.transform.localPosition = new Vector3(0, 2.05f, -2.2f);
        nu.GetComponent<Renderer>().sharedMaterial = shu;
        var kd = GameObject.CreatePrimitive(PrimitiveType.Cube); kd.name = "kidan"; kd.transform.SetParent(g.transform, false);
        kd.transform.localScale = new Vector3(1.5f, 0.4f, 1.2f); kd.transform.localPosition = new Vector3(0, 0.2f, 0);
        kd.GetComponent<Renderer>().sharedMaterial = stone;
        var ho = GameObject.CreatePrimitive(PrimitiveType.Cube); ho.name = "hokora"; ho.transform.SetParent(g.transform, false);
        ho.transform.localScale = new Vector3(0.9f, 0.9f, 0.8f); ho.transform.localPosition = new Vector3(0, 0.85f, 0);
        ho.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var rf = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rf.name = "roof" + i; rf.transform.SetParent(g.transform, false);
            rf.transform.localScale = new Vector3(1.3f, 0.06f, 0.65f);
            rf.transform.localPosition = new Vector3(0, 1.45f, i == 0 ? -0.28f : 0.28f);
            rf.transform.localEulerAngles = new Vector3(i == 0 ? -25f : 25f, 0, 0);
            rf.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    // =========================================================================
    // Stage 8: 庭園(下書きの桃色帯) + 中庭の植栽
    // =========================================================================
    public static string Stage8_Garden()
    {
        var gg = Grp("Garden"); Clear(gg);
        var rnd = new System.Random(53115);
        var obst = new List<Bounds>();
        foreach (var gn in new[] { "Buildings", "Service", "Kakoi", "Omotemon", "Roka" })
        { var g = GameObject.Find(GN).transform.Find(gn); if (g == null) continue;
          foreach (Transform c in g) { if (!c.gameObject.activeSelf) continue; var b = B.RB(c.gameObject); b.Expand(new Vector3(3f, 200f, 3f)); obst.Add(b); } }
        var zones = Zones(); var courts = Courts();
        int n = 0;
        for (int i = 0, guard = 0; i < 150 && guard < 12000; guard++)
        {
            float px = Mathf.Lerp(-694f, -374f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(938f, 1094f, (float)rnd.NextDouble());
            var p = new Vector2(px, pz);
            if (!B.PIP(SK.OKABE, p) || B.DistToPolyEdge(SK.OKABE, p) < 5f) continue;
            bool inZone = false;
            foreach (var zn in zones) if (px > zn.x0 - 2 && px < zn.x1 + 2 && pz > zn.z0 - 2 && pz < zn.z1 + 2) inZone = true;
            bool inCourt = false;
            foreach (var ct in courts) if (px > ct.xMin && px < ct.xMax && pz > ct.yMin && pz < ct.yMax) inCourt = true;
            if (inZone && !inCourt) continue;
            bool hit = false;
            foreach (var ob in obst) if (px > ob.min.x && px < ob.max.x && pz > ob.min.z && pz < ob.max.z) { hit = true; break; }
            if (hit) continue;
            float y = G(px, pz);
            GameObject go;
            if (y < 14f) go = B.Place(Bamboo[rnd.Next(2)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Take_" + i);
            else if (rnd.NextDouble() < 0.66) go = B.Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
            else go = B.Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
            var rb = B.RB(go); go.transform.position += new Vector3(0, (y - 0.05f) - rb.min.y, 0);
            i++; n++;
        }
        return "plants=" + n;
    }

    // =========================================================================
    [MenuItem("Edo/岡部筑前守上屋敷を再構成 v3")]
    public static void RunAllMenu() { Debug.Log(RunAll()); }
    public static string RunAll()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Backup());
        sb.AppendLine(Stage1_Grade());
        sb.AppendLine(BuildStructures());
        return sb.ToString();
    }
    // 地形を触らない部分。全ステージ冪等。
    public static string BuildStructures()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage3_Retire());
        sb.AppendLine(Stage4_Perimeter());
        sb.AppendLine(Stage4b_Ishigaki());
        sb.AppendLine(Stage5_Goten());
        sb.AppendLine(Stage6_Roka());
        sb.AppendLine(Stage7_Service());
        sb.AppendLine(Stage8_Garden());
        sb.AppendLine(Stage2_Reseat());
        UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
        return sb.ToString();
    }
}
