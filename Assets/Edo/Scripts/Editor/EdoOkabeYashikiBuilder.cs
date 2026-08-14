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
    const string PKmon = EdoAssets.Eg.Kmon;

    // ---------- 段(平場)の定義: x範囲 / z範囲 / 高さ ----------
    public struct Terr { public float x0, x1, z0, z1, y; public string name; }
    public static Terr[] Terraces()
    {
        return new[] {
            new Terr{ name="Shukaku", x0=-566f, x1=-455f, z0=946f, z1=1058f, y=25.5f },
            new Terr{ name="TE",      x0=-455f, x1=-425f, z0=946f, z1=1058f, y=19.5f },
            new Terr{ name="Monzen",  x0=-425f, x1=-374f, z0=946f, z1=1058f, y=13.5f },
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
            // 東: 主郭25.5 → 東中段19.5 → 表門前13.5。南→北へ走る(左=西=高い側)。開口は参道 z=1001
            new Wall{ name="IG_E1", a=new Vector2(-455f, 947f), b=new Vector2(-455f, 1056f), coping=25.5f, sy=1.5f, gapZ=1001f },
            new Wall{ name="IG_E2", a=new Vector2(-425f, 947f), b=new Vector2(-425f, 1056f), coping=19.5f, sy=1.5f, gapZ=1001f },
            // 西: 主郭25.5 → 中段19.5 → 西低地11.5。北→南へ走る(左=東=高い側)。開口は北縁 z=1036
            new Wall{ name="IG_W1", a=new Vector2(-566f, 1052f), b=new Vector2(-566f, 949f), coping=25.5f, sy=1.5f, gapZ=1036f },
            new Wall{ name="IG_W2", a=new Vector2(-592f, 1052f), b=new Vector2(-592f, 949f), coping=19.5f, sy=2.0f, gapZ=1036f },
        };
    }

    // =========================================================================
    // 指図(docs/Sashizu/okabe_sashizu.html)の座標をそのまま持つ。図面と実装をズラさない。
    //   主郭プレート : u=0 が x=-457 で西へ増加 / v=0 が z=955 で北へ増加
    //   西の下郭     : u=0 が x=-648 で東へ増加 / v=0 が z=948 で北へ増加
    // =========================================================================
    public struct Blk { public float x0, z0, x1, z1, y; public string name; }
    static Blk S_(float u0, float v0, float u1, float v1, float y, string n)
    { return new Blk { x0 = -457f - u1, z0 = 955f + v0, x1 = -457f - u0, z1 = 955f + v1, y = y, name = n }; }
    static Blk W_(float u0, float v0, float u1, float v1, float y, string n)
    { return new Blk { x0 = -648f + u0, z0 = 948f + v0, x1 = -648f + u1, z1 = 948f + v1, y = y, name = n }; }

    // 身舎(棟の中身)。廊下はこの外周2mに自動で回る
    public static Blk[] Muneya()
    {
        return new[] {
            S_(4,38,18,62,    25.5f, "Genkan"),      S_(24,14,46,50, 25.5f, "Ohiroma"),
            S_(24,66,46,96,   25.5f, "Shoin"),       S_(56,14,78,50, 25.5f, "Nakaoku"),
            S_(56,66,78,96,   25.5f, "Daidokoro"),   S_(88,42,104,68,25.5f, "Okumuki"),
            S_(88,8,104,28,   25.5f, "Nagatsubone"),
            W_(9,8,25,22,     11.5f, "Katte"),       W_(9,30,25,74,  11.5f, "ShimoGoten"),
            W_(9,80,21,88,    11.5f, "Yudono"),      W_(35,30,51,58, 11.5f, "Jochu"),
            W_(35,66,46,88,   11.5f, "Goyobeya"),    W_(64,24,74,88, 19.5f, "NagatsuboneW"),   // 家臣長屋との隙間を取る(bm1 23-24)
        };
    }
    // 渡廊下・外廊下(入側は身舎から自動生成)
    public static Blk[] RokaLinks()
    {
        return new[] {
            S_(20,46,22,48,25.5f,"L_GenkanOhiroma"), S_(48,50,54,52,25.5f,"L_OhiromaNakaoku"),
            S_(48,64,54,66,25.5f,"L_ShoinDaidokoro"),S_(34,52,36,64,25.5f,"L_OhiromaShoin"),
            S_(66,52,68,64,25.5f,"L_NakaokuDaidokoro"), S_(80,46,86,48,25.5f,"L_Jouguchi"),
            S_(96,30,98,40,25.5f,"L_OkuNagatsubone"), S_(104,70,106,86,25.5f,"L_ShimoKuruwa"),
            // 主郭の東縁 → 石段Bへ
            new Blk{ x0=-459f, z0=999f, x1=-455f, z1=1003f, y=25.5f, name="L_HigashiEn" },
            // 東中段の参道
            new Blk{ x0=-450f, z0=1000f, x1=-425f, z1=1002f, y=19.5f, name="L_Sando19" },
            // 表門前段の参道
            new Blk{ x0=-420f, z0=1000f, x1=-398f, z1=1002f, y=13.5f, name="L_Sando13" },
            // 西の下郭 (levelは段ごと)
            W_(7,24,9,28,11.5f,"LW_KatteShimo"),  W_(7,76,9,78,11.5f,"LW_ShimoYudono"),
            W_(27,42,33,44,11.5f,"LW_ShimoJochu"),W_(41,60,43,64,11.5f,"LW_JochuGoyo"),
            W_(23,88,33,90,11.5f,"LW_Kita1"),     W_(48,88,49.5f,90,11.5f,"LW_Kita2"),
            W_(56,88,58.4f,90,19.5f,"LW_Kita3"),   W_(58.4f,88,60,90,19.5f,"LW_Kita4"),
            W_(76,88,77,90,19.5f,"LW_Kita5"),     W_(82,88,84.4f,90,25.5f,"LW_Kita6"),
            W_(84.4f,88,92,90,25.5f,"LW_Kita7"),
        };
    }
    // 庭(指図と同じ矩形)。白洲を塗るときにここは芝のまま残す
    public static Blk[] Gardens()
    {
        return new[] {
            S_(0,0,20,36,25.5f,"NiwaOmoteE"),  S_(20,0,80,12,25.5f,"NiwaOmoteS"),
            S_(0,68,20,101,25.5f,"NiwaShoin"), S_(36,52,66,64,25.5f,"Tsubo"),
            S_(88,70,104,96,25.5f,"NiwaOkuUchi"),
        };
    }
    // 折返し石段 (rect / 上端レベル / 下端レベル / 降りる向き)
    public struct Kai { public float x0, z0, x1, z1, yTop, yBot; public bool east; public string name; }
    public static Kai[] Kaidans()
    {
        return new[] {
            new Kai{ x0=-455f, z0=999f, x1=-450f, z1=1003f, yTop=25.5f, yBot=19.5f, east=true,  name="Kaidan_E1" },
            new Kai{ x0=-425f, z0=999f, x1=-420f, z1=1003f, yTop=19.5f, yBot=13.5f, east=true,  name="Kaidan_E2" },
            new Kai{ x0=-571f, z0=1034f, x1=-566f, z1=1038f, yTop=25.5f, yBot=19.5f, east=false, name="Kaidan_W1" },
            new Kai{ x0=-598.5f, z0=1034f, x1=-592f, z1=1038f, yTop=19.5f, yBot=11.5f, east=false, name="Kaidan_W2" },
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
    const string PFloor = EdoAssets.VK.FloorInterior2x2;
    const string PCol = EdoAssets.VK.ColumnA;
    const string PRoof = EdoAssets.VK.Roof2x8;
    const string PRoofEnd = EdoAssets.VK.RoofEnd2x1;
    const string PStep = EdoAssets.Own.DanishiStep;
    const string PKnagayaC = EdoAssets.Eg.KnagayaC;
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JG.Boxwood01 };
    static string[] Bamboo = {
        EdoAssets.JG.BambooBig01,
        EdoAssets.JG.BambooBig02 };

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
        var mk = GameObject.Find("OKABE_GRADED_v4");
        if (mk != null) return "grade: SKIP (already graded v4)";
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
        mk = new GameObject("OKABE_GRADED_v4");
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
    const string P_CW = EdoAssets.JC.CastleWall;
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
    // Stage 5: 連続御殿複合 — 指図の身舎矩形を Village Kit の棟で埋める(躯体間0.6m)
    //   案a: 棟を密着させて屋根を一枚の塊に見せる。等間隔の格子には置かない。
    // =========================================================================
    struct Slot { public string path; public float w, d, ry; }
    static Slot SL(string p, float w, float d, float ry) { return new Slot { path = p, w = w, d = d, ry = ry }; }
    // 躯体寸法(ry適用後)。BigHouse 26.2x24.2 / House 18.2x14.3 / HouseB 8.2x17.1 / SmallHouse 12.2x8.2
    static Slot[] Pal = {
        SL(B.PBigHouse, 26.2f, 24.2f, 0f),
        SL(B.PHouse,    18.2f, 14.3f, 0f),  SL(B.PHouse,    14.3f, 18.2f, 90f),
        SL(B.PHouseB,    8.2f, 17.1f, 0f),  SL(B.PHouseB,   17.1f,  8.2f, 90f),
        SL(B.PSmallHouse,12.2f, 8.2f, 0f),  SL(B.PSmallHouse,8.2f, 12.2f, 90f),
    };

    public static string Stage5_Goten()
    {
        var sb = new System.Text.StringBuilder();
        var bg = Grp("Buildings"); Clear(bg);
        int total = 0; float area = 0;
        foreach (var m in Muneya())
        {
            int n; float a;
            FillMuneya(bg, m, out n, out a);
            total += n; area += a;
            sb.AppendLine("  " + m.name + " " + (m.x1 - m.x0).ToString("F0") + "x" + (m.z1 - m.z0).ToString("F0") + "m  棟=" + n);
        }
        sb.AppendLine("goten units=" + total + " bodyArea=" + area.ToString("F0"));
        return sb.ToString();
    }

    // 矩形を充填。躯体を重ねてよい(内部を作らないので重なりは外から見えない)。
    //   0.6m の隙間を空けると幅が埋まらず身舎の26〜45%が空く。重ねて埋め切る方が
    //   福井図・二条城の「大小の屋根が重なり合って相ならぶ」姿に近い(2026-08-14 是正)。
    static void FillMuneya(Transform parent, Blk m, out int n, out float area)
    {
        n = 0; area = 0;
        float W = m.x1 - m.x0;
        float z = m.z0; int idx = 0;
        while (m.z1 - z >= 7.5f)
        {
            float rest = m.z1 - z;
            var row = new List<Slot>(); float cov = 0;
            RowFill(W, rest, row, ref cov);
            if (row.Count == 0) break;
            // 行の左端から、重なりを均等に配って幅いっぱいに散らす
            float sum = 0; foreach (var s2 in row) sum += s2.w;
            float overlap = (row.Count > 1) ? (sum - W) / (row.Count - 1) : 0f;
            float x = m.x0; float used = 0;
            foreach (var pick in row)
            {
                float cx = x + pick.w * 0.5f, cz = z + pick.d * 0.5f;
                var go = B.Place(pick.path, Vector3.zero, pick.ry, Vector3.one, parent, m.name + "_" + (idx++));
                var rb = B.RB(go);
                go.transform.position += new Vector3(cx - rb.center.x, 0, cz - rb.center.z);
                rb = B.RB(go);
                go.transform.position += new Vector3(0, (m.y - 0.12f) - rb.min.y, 0);
                n++; area += pick.w * pick.d;
                used = Mathf.Max(used, pick.d);
                x += pick.w - overlap;
            }
            z += used - Mathf.Min(1.5f, used * 0.15f);   // 行方向も少し重ねて軒を繋ぐ
        }
    }
    // 幅Wを覆う組み合わせ(合計幅 >= W を最小の余りで満たす)。奥行は rest 以下
    static void RowFill(float W, float rest, List<Slot> outRow, ref float cov)
    {
        List<Slot> best = null; float bestScore = float.MaxValue;
        var cur = new List<Slot>();
        System.Action<float, int> rec = null;
        rec = (w, depth) =>
        {
            if (w >= W - 0.01f)
            {
                // 余り(重なり)が小さく、奥行が深いものを優先
                float dsum = 0; foreach (var s in cur) dsum += s.d;
                float score = (w - W) * 3f - dsum / Mathf.Max(1, cur.Count);
                if (score < bestScore) { bestScore = score; best = new List<Slot>(cur); }
                return;
            }
            if (depth >= 4) return;
            foreach (var s in Pal)
            {
                if (s.d > rest + 0.01f) continue;
                if (s.w > W * 1.35f) continue;
                cur.Add(s); rec(w + s.w, depth + 1); cur.RemoveAt(cur.Count - 1);
            }
        };
        rec(0f, 0);
        if (best == null)
        {   // 幅を覆えない場合は入る中で最大の1棟
            Slot pick = default; bool ok = false; float bw = -1;
            foreach (var s in Pal) if (s.d <= rest + 0.01f && s.w <= W + 0.01f && s.w * s.d > bw) { bw = s.w * s.d; pick = s; ok = true; }
            if (ok) outRow.Add(pick);
            return;
        }
        outRow.AddRange(best);
        foreach (var s in best) cov += s.w;
    }

    // =========================================================================
    // Stage 6: 廊下 — 入側(身舎の外周2m)・渡廊下・外廊下・折返し石段
    //   入側は一間幅(約2m)。棟の外形を膨らませて廊下にしない(幅が倍になる)。
    // =========================================================================
    const float RW = 2.0f;   // 廊下幅 ≒ 一間
    public static string Stage6_Roka()
    {
        var rk = Grp("Roka"); Clear(rk);
        int nr = 0;
        foreach (var m in Muneya())
        {
            // 入側 = 身舎の外周に幅RWの帯を4本
            RokaRect(rk, m.x0 - RW, m.z0 - RW, m.x1 + RW, m.z0, m.y, m.name + "_IrikawaS"); nr++;
            RokaRect(rk, m.x0 - RW, m.z1, m.x1 + RW, m.z1 + RW, m.y, m.name + "_IrikawaN"); nr++;
            RokaRect(rk, m.x0 - RW, m.z0, m.x0, m.z1, m.y, m.name + "_IrikawaW"); nr++;
            RokaRect(rk, m.x1, m.z0, m.x1 + RW, m.z1, m.y, m.name + "_IrikawaE"); nr++;
        }
        foreach (var l in RokaLinks()) { RokaRect(rk, l.x0, l.z0, l.x1, l.z1, l.y, l.name); nr++; }
        int nk = 0;
        foreach (var k in Kaidans()) { Kaidan(rk, k); nk++; }
        return "roka rects=" + nr + " kaidan=" + nk;
    }

    // 矩形の廊下: 床(2x2) + 柱 + 屋根(2x8)。長辺方向に棟を通す
    static void RokaRect(Transform parent, float x0, float z0, float x1, float z1, float lv, string nm)
    {
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "roka");
        float W = x1 - x0, D = z1 - z0;
        bool alongX = W >= D;
        var floorPre = AssetDatabase.LoadAssetAtPath<GameObject>(PFloor);
        var colPre = AssetDatabase.LoadAssetAtPath<GameObject>(PCol);
        var roofPre = AssetDatabase.LoadAssetAtPath<GameObject>(PRoof);
        float y = lv + 0.45f;
        int nx = Mathf.Max(1, Mathf.RoundToInt(W / 2f)), nz = Mathf.Max(1, Mathf.RoundToInt(D / 2f));
        for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++)
        {
            float cx = x0 + (i + 0.5f) * W / nx, cz = z0 + (j + 0.5f) * D / nz;
            var f = (GameObject)PrefabUtility.InstantiatePrefab(floorPre, g.transform);
            Undo.RegisterCreatedObjectUndo(f, "rf"); f.name = "F_" + i + "_" + j;
            f.transform.position = new Vector3(cx, y, cz);
            f.transform.localScale = new Vector3((W / nx) / 2f, 1f, (D / nz) / 2f);
        }
        // 柱: 長辺の両側に2m間隔
        int npc = Mathf.Max(2, (alongX ? nx : nz) + 1);
        for (int i = 0; i < npc; i++)
            for (int s = 0; s < 2; s++)
            {
                float t = (float)i / (npc - 1);
                float cx = alongX ? Mathf.Lerp(x0 + 0.15f, x1 - 0.15f, t) : (s == 0 ? x0 + 0.15f : x1 - 0.15f);
                float cz = alongX ? (s == 0 ? z0 + 0.15f : z1 - 0.15f) : Mathf.Lerp(z0 + 0.15f, z1 - 0.15f, t);
                var c = (GameObject)PrefabUtility.InstantiatePrefab(colPre, g.transform);
                Undo.RegisterCreatedObjectUndo(c, "rc"); c.name = "C_" + i + "_" + s;
                c.transform.position = new Vector3(cx, y, cz);
            }
        // 屋根: 長辺方向に 2x8 を並べる
        float L = alongX ? W : D;
        int nrf = Mathf.Max(1, Mathf.RoundToInt(L / 8f));
        for (int i = 0; i < nrf; i++)
        {
            var r = (GameObject)PrefabUtility.InstantiatePrefab(roofPre, g.transform);
            Undo.RegisterCreatedObjectUndo(r, "rr"); r.name = "R_" + i;
            float seg = L / nrf;
            r.transform.rotation = Quaternion.Euler(0, alongX ? 90f : 0f, 0);
            r.transform.localScale = new Vector3(1f, 1f, seg / 8f);
            float cxr = alongX ? (x0 + (i + 0.5f) * seg) : (x0 + (x1 - x0) * 0.5f);
            float czr = alongX ? (z0 + (z1 - z0) * 0.5f) : (z0 + (i + 0.5f) * seg);
            // roof 2x8 は pivot が幅方向の端(local x=0)にあり、local +X は
            //   ry=0 で world +X、ry=90 で world -Z を向く。向きに合わせて端へ寄せる。
            //   ⚠ ここを両方 -half にしていたため、東西方向の廊下だけ屋根が2mずれて床が露出した
            float half = (alongX ? D : W) * 0.5f;
            if (alongX) czr += half; else cxr -= half;
            r.transform.position = new Vector3(cxr, y + 3.0f + 1.06f, czr);
        }
    }

    // 折返し石段: 二流れ+踊り場。蹴上0.30m
    static void Kaidan(Transform parent, Kai k)
    {
        var g = new GameObject(k.name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "kaidan");
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(PStep);
        int n = Mathf.Max(2, Mathf.RoundToInt((k.yTop - k.yBot) / 0.30f));
        int half = n / 2;
        float runLen = (k.x1 - k.x0);
        float wHalf = (k.z1 - k.z0) * 0.5f;
        float dir = k.east ? 1f : -1f;
        float xStart = k.east ? k.x0 : k.x1;
        for (int i = 0; i <= n; i++)
        {
            bool first = i <= half;
            int ii = first ? i : (n - i);
            float t = (float)ii / Mathf.Max(1, half);
            float px = xStart + dir * (runLen * t);
            float pz = first ? (k.z0 + wHalf * 0.5f) : (k.z1 - wHalf * 0.5f);
            float lvl = Mathf.Lerp(k.yTop, k.yBot, (float)i / n);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, g.transform);
            Undo.RegisterCreatedObjectUndo(go, "st"); go.name = "S_" + i;
            go.transform.rotation = Quaternion.Euler(0, 90f, 0);
            var rb = B.RB(go);
            go.transform.position += new Vector3(px - rb.center.x, lvl - rb.max.y, pz - rb.center.z);
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
            float cx = -614f + (i % 2) * 9f, cz = 960f + (i / 2) * 9f;   // 下御殿棟に刺さらない位置(bm1 19-22)
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
        var mus = Muneya();
        int n = 0;
        for (int i = 0, guard = 0; i < 150 && guard < 12000; guard++)
        {
            float px = Mathf.Lerp(-694f, -374f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(938f, 1094f, (float)rnd.NextDouble());
            var p = new Vector2(px, pz);
            if (!B.PIP(SK.OKABE, p) || B.DistToPolyEdge(SK.OKABE, p) < 5f) continue;
            bool inMune = false;
            foreach (var mu in mus) if (px > mu.x0 - 4f && px < mu.x1 + 4f && pz > mu.z0 - 4f && pz < mu.z1 + 4f) inMune = true;
            if (inMune) continue;
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
    // Stage 9: 郭の内側を白洲(砂利)に塗る。芝のままだと村に見える
    // =========================================================================
    public static string Stage9_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((-660f - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((-370f - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((940f - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((1060f - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        var terr = Terraces(); var gard = Gardens();
        int changed = 0;
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            float wx = tp.x + (ix0 + xx + 0.5f) * cell, wz = tp.z + (iz0 + zz + 0.5f) * cell;
            var p = new Vector2(wx, wz);
            if (!B.PIP(SK.OKABE, p)) continue;
            bool inTerr = false;
            foreach (var tr in terr) if (wx > tr.x0 && wx < tr.x1 && wz > tr.z0 && wz < tr.z1) inTerr = true;
            if (!inTerr) continue;
            bool inG = false;
            foreach (var g in gard) if (wx > g.x0 - 1f && wx < g.x1 + 1f && wz > g.z0 - 1f && wz < g.z1 + 1f) inG = true;
            float bare, grass, dirt;
            if (inG) { grass = 0.72f; dirt = 0.20f; bare = 0.08f; }
            else { bare = 0.70f; dirt = 0.24f; grass = 0.06f; }
            float sum = bare + grass + dirt;
            for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
            A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
            changed++;
        }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
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
        sb.AppendLine(Stage9_Splat());
        sb.AppendLine(Stage2_Reseat());
        UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
        return sb.ToString();
    }
}
