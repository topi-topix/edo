// 山王社北・3上屋敷ビルダー (2026-08-12)
//   赤=岡部筑前守(和泉岸和田藩5万3千石) 黄=土井大隅守(三河刈谷藩2万3千石) 水=松平出羽守(出雲松江藩18万6千石)
// 【考証 2026-08-12 Web調査+NDL1286657(外桜田永田町絵図)IIIF実見】
//   ・3屋敷とも切絵図原画像で家紋を実見=いずれも上屋敷。
//     岡部=左三つ巴 / 土井=六つ水車 / 松平出羽守=雲州松平の家紋(葵紋系)。
//   ・岡部筑前守=岡部長寛(安政2年家督。「筑前守」表記はユーザー典拠の安政2年以降版。
//     NDL嘉永版の表記は「岡部内膳正」=先代長和)。譜代・雁間。跡地=都立日比谷高校。
//     東の通りは岡部/安部/渡辺3邸に由来する「三べ坂」(現存坂名)。表門=北東辺(文字の頭=NE)。
//   ・土井大隅守=土井利善(弘化4年大隅守叙任, 〜慶応2)。譜代。跡地=駐日メキシコ大使館。
//     安政江戸地震で「外構練壁が潰れる」記録(内閣府災害教訓報告書)→塀は練塀(dobei)。表門=東辺北寄り。
//   ・松平出羽守=斉貴(〜嘉永6強制隠居)/定安(嘉永6〜)。親藩・出雲国主・大広間。上屋敷11,942坪
//     (下書き区画=13,237坪と整合)。跡地=衆参両院議長公邸。表門=北辺(赤坂御門からの大通り, 文字の頭=NNW)。
//   ・街路: 西=溜池北腕東岸の堀端通り / 北=赤坂御門→永田馬場の大通り / 東=三べ坂前身の南北道。
//     土井と岡部の北端の間に道のジョグ(下書きの9m楔=袋小路スタブ)。松平と土井は背中合わせ。
// 【地形】赤区画東半の「h16.1完全平坦テラス+鋭い段差」=日比谷高校校庭の近代造成 →ラプラシアン緩和で
//   斜面復元(backup=scratchpad/sannokita_backup.bin)。黄区画内の浅い掘り込み(メキシコ大使館)も軽く緩和。
//   岡部の表門前T1=15.0/表御殿T2=19.0の小段丘は近代改変域内のみ(13bの段状テラス作法)。他は造成ゼロ。
// 【敷地内構成】各屋敷の指図は未発見のため一般類型(典拠: 格式論+上屋敷類型。§15)。池は典拠なし=作らない。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSannoKitaBuilder
{
    const string PKmon = EdoAssets.Eg.Kmon;
    const string PNmon = EdoAssets.Eg.Nagayamon;
    const string PBansho = EdoAssets.Eg.Bansho;
    const string PKura = EdoAssets.Eg.Kura;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBigHouse = EdoAssets.VK.BigHouse;
    const string PManor = EdoAssets.VK.Manor;
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JG.Boxwood01 };
    // ⚠ **斜面の植栽に竹を使わない**(2026-08-22 是正)。BambooBig は孟宗竹型の太稈で、
    //   嘉永期の江戸の孟宗竹は吹上御苑と近郊農村の筍畑にしか無い。斜面は Pines + Shrubs の
    //   3帯(指図 matsudaira_sashizu.json の slopeBands)。竹垣は垣の材なので別物。
    //   復活させる前に docs/Sashizu/matsudaira_kosho.md「斜面の植生」を読むこと。
    const string PTobi = EdoAssets.JG.TobiIshi01;
    public const float ES = 1.818f;

    // ---------- 区画(下書きスナップ済 2026-08-12) ----------
    // 共有点: T=三分岐点(岡部NW/土井SW/松平E線上), R4=岸の岡部/松平境
    // ⚠ 岡部の南辺 0-1 / 2-3 は 2026-08-19 まで「隣が持つ(skip)」と書いていたが**誤り**。
    //   実装(EdoOkabeYashikiBuilder.Runs)は南辺を全長 築地塀で囲っており、樹下(140.6m)・
    //   常明院(61.0m)も同じ境界に建てていて 204.8m = 南辺の 74% が二重だった。
    //   ユーザー裁定 2026-08-19(確度U): **南辺 275.9m は全長 岡部が持つ** — 北辺(指図 其十一)と
    //   同じ規則。よって skip するのは**隣の側**(樹下 JUGE 辺4 / 常明院 poly 辺2)。
    //   決め手は樹下辺: 岡部の主郭が 1.4〜7.2m 高く IG_S_Sk(壁高 8.0m)が岡部所有で立つ。
    //   塀は擁壁の天端に載るので、法尻側の樹下が持つ形は成立しない。
    // 岡部: 0-1=S(樹下共有=岡部所有) 1-2=S(社叢斜面=境内) 2-3=S(常明院共有=岡部所有) 3-4=W(堀端通り)
    //       4-5,5-6=NW(松平共有=松平所有skip) 6-7,7-8=N(土井共有=**岡部所有** — 実体は
    //       EdoOkabeYashikiBuilder の Hei_N1〜N4b が建てるのでここでは skip)
    //       8-9=楔スタブ 9-10=NE(表門) 10-0=E(三べ坂沿い盲長屋)
    public static readonly Vector2[] OKABE = {
        new Vector2(-373.0f, 947.0f), new Vector2(-514.5f, 947.0f), new Vector2(-585.5f, 943.3f),
        new Vector2(-648.5f, 936.8f), new Vector2(-694.7f, 1029.5f), new Vector2(-660.8f, 1049.2f),
        new Vector2(-640.0f, 1073.8f), new Vector2(-612.6f, 1062.5f), new Vector2(-459.4f, 1086.6f),
        new Vector2(-425.4f, 1096.3f), new Vector2(-384.4f, 1054.3f) };
    // 土井: 0-1,1-2=S(岡部共有=**岡部所有 skip** — 岡部側 Hei_N1〜N4b が建てる。
    //       旧注記「土井所有」は撤回済みの裁定(2026-08-16)の取り残しで、辺0-1を建てると
    //       185m が二重になる。検図 2026-08-22 で是正)
    //       2-3=ジョグ 3-4=楔N 4-5=E(表門) 5-6,6-7,7-8,8-0=N/W(松平共有=松平所有skip)
    //       正典は docs/Sashizu/doi_sashizu.json の _edges。
    public static readonly Vector2[] DOI = {
        new Vector2(-640.0f, 1073.8f), new Vector2(-612.6f, 1062.5f), new Vector2(-459.4f, 1086.6f),
        new Vector2(-460.9f, 1094.9f), new Vector2(-431.8f, 1105.9f), new Vector2(-458.5f, 1177.8f),
        new Vector2(-530.9f, 1155.8f), new Vector2(-606.9f, 1156.9f), new Vector2(-609.0f, 1107.5f) };
    // 松平(13頂点): 0-1,1-2,2-3,3-4=S(土井共有・松平所有。3-4は土井辺8-0と共有)
    //   4-5,5-6=SE(岡部共有=岡部辺5-6/4-5・松平所有) 6-7,7-8,8-9=W(堀端=溜池東岸)
    //   9-10=NW 10-11=N(表門・大通り) 11-12=NE 12-0=E(三べ坂前身道)
    //   ⚠ 旧注記は11頂点時代のもので辺番号が1〜2ズレていた(検図 2026-08-22 で是正)。
    //   正典は docs/Sashizu/matsudaira_sashizu.json の _edges。
    public static readonly Vector2[] MATSU = {
        new Vector2(-458.5f, 1177.8f), new Vector2(-530.9f, 1155.8f), new Vector2(-606.9f, 1156.9f),
        new Vector2(-609.0f, 1107.5f), new Vector2(-640.0f, 1073.8f), new Vector2(-660.8f, 1049.2f),
        new Vector2(-694.7f, 1029.5f), new Vector2(-723.4f, 1070.8f), new Vector2(-746.9f, 1123.8f),
        new Vector2(-755.2f, 1180.6f), new Vector2(-737.0f, 1224.5f), new Vector2(-569.3f, 1300.9f),
        new Vector2(-500.6f, 1307.0f) };

    // 表門
    static readonly Vector2 GATE_OKABE = new Vector2(-410.0f, 1081.5f);   // NE辺(9-10)
    static readonly Vector2 GATE_DOI = new Vector2(-448.2f, 1150.0f);     // E辺(4-5)
    static readonly Vector2 GATE_MATSU = new Vector2(-680.0f, 1250.4f);   // N辺(10-11)

    // ---------- helpers (EdoSannoBukeBuilder と同型) ----------
    static float Ground(float x, float z) { return EdoNishiTameikeBuilder.Ground(x, z); }
    static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    { return EdoNishiTameikeBuilder.Place(path, pos, ry, scale, parent, name); }
    static Bounds RB(GameObject go) { return EdoNishiTameikeBuilder.RB(go); }
    static void SeatBottom(GameObject go, float y) { EdoNishiTameikeBuilder.SeatBottom(go, y); }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null) { var g = new GameObject(seg); Undo.RegisterCreatedObjectUndo(g, "grp"); g.transform.SetParent(cur, false); nx = g.transform; }
            cur = nx;
        }
        return cur;
    }
    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
        return inside;
    }
    static float SignedArea(Vector2[] poly)
    {
        float a = 0;
        for (int i = 0; i < poly.Length; i++) { var p = poly[i]; var q = poly[(i + 1) % poly.Length]; a += p.x * q.y - q.x * p.y; }
        return 0.5f * a;
    }
    static Vector2 InwardNormal(Vector2[] poly, int i)
    {
        var a = poly[i]; var b = poly[(i + 1) % poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        if (SignedArea(poly) < 0) n = -n;
        return n;
    }
    static float DistToEdge(Vector2 p, Vector2 a, Vector2 b)
    {
        var d = b - a; float len = d.magnitude; d /= len;
        float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
        return (p - (a + d * t)).magnitude;
    }
    static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++) m = Mathf.Min(m, DistToEdge(p, poly[i], poly[(i + 1) % poly.Length]));
        return m;
    }
    static Material Mat(Color c) { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; }
    static void CenterSeat(GameObject go, float x, float z, float sink = 0.12f)
    {
        var b = RB(go);
        go.transform.position += new Vector3(x - b.center.x, 0, z - b.center.z);
        b = RB(go);
        float gmn = float.MaxValue;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
            gmn = Mathf.Min(gmn, Ground(b.center.x + i * b.extents.x, b.center.z + j * b.extents.z));
        go.transform.position += new Vector3(0, (gmn - sink) - b.min.y, 0);
    }
    static float PlaceGate(string path, Transform monGrp, Vector2 gate, Vector2 fout, int bansho, string name, System.Text.StringBuilder sb)
    {
        float basePad = Ground(gate.x, gate.y);
        Vector2 inw = -fout;
        float psiIn = Mathf.Atan2(inw.x, inw.y) * Mathf.Rad2Deg;
        var mon = Place(path, Vector3.zero, psiIn, Vector3.one * ES, monGrp, name);
        CenterSeat(mon, gate.x, gate.y, 0.05f);
        float kmn = float.MaxValue, kmx = float.MinValue;
        foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
            foreach (var vtx in mf.sharedMesh.vertices)
            { var wp = mf.transform.TransformPoint(vtx); float pr = wp.x * inw.x + wp.z * inw.y; kmn = Mathf.Min(kmn, pr); kmx = Mathf.Max(kmx, pr); }
        }
        if (kmn != float.MaxValue)
        {
            var mc = RB(mon).center;
            if ((kmn + kmx) * 0.5f < mc.x * inw.x + mc.z * inw.y)
            { mon.transform.rotation *= Quaternion.Euler(0, 180, 0); CenterSeat(mon, gate.x, gate.y, 0.05f); sb.AppendLine(name + " flipped"); }
        }
        float wmn = float.MaxValue, wmx = float.MinValue;
        Vector2 uh = new Vector2(fout.y, -fout.x);
        foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
            foreach (var vtx in mf.sharedMesh.vertices)
            {
                var wp = mf.transform.TransformPoint(vtx);
                if (wp.y < basePad + 0.5f || wp.y > basePad + 4.5f) continue;
                float pr = (wp.x - gate.x) * uh.x + (wp.z - gate.y) * uh.y;
                wmn = Mathf.Min(wmn, pr); wmx = Mathf.Max(wmx, pr);
            }
        float gateHalf = Mathf.Max(Mathf.Abs(wmn), Mathf.Abs(wmx));
        for (int i = 0; i < bansho; i++)
        {
            float side = (bansho == 1) ? 1f : (i == 0 ? 1f : -1f);
            float extrude = path == PNmon ? 1.7f : 0.5f;
            Vector2 bp = gate + uh * (side * (gateHalf + 3.4f)) + fout * extrude;
            float bg2 = Ground(bp.x, bp.y);
            var ban = Place(PBansho, new Vector3(bp.x, bg2, bp.y), psiIn + 180f, Vector3.one * ES, monGrp, name + "_Bansho" + i);
            SeatBottom(ban, bg2 - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * fout.x + f3.z * fout.y < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg, 0);
        }
        sb.AppendLine(name + " halfW=" + gateHalf.ToString("F2"));
        return gateHalf;
    }
    static void FrontWall(Transform kak, Vector2 a, Vector2 b, Vector2 outw, Vector2 gate, float gateHalf, string prefix)
    {
        Vector2 dir = (b - a).normalized;
        Vector2 gL = gate - dir * (gateHalf - 0.15f), gR = gate + dir * (gateHalf - 0.15f);
        if (Vector2.Distance(a, gL) > 1.6f && Vector2.Dot(gL - a, dir) > 0)
            EdoNishiTameikeBuilder.DobeiRun(kak, a, gL, outw, prefix + "_L", true, 0, Vector2.zero, -1);
        if (Vector2.Distance(gR, b) > 1.6f && Vector2.Dot(b - gR, dir) > 0)
            EdoNishiTameikeBuilder.DobeiRun(kak, gR, b, outw, prefix + "_R", true, 0, Vector2.zero, -1);
    }
    static void Well(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "well");
        var stone = Mat(new Color(0.55f, 0.55f, 0.52f));
        var wood = Mat(new Color(0.38f, 0.28f, 0.18f));
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.3f, 0.35f, 1.3f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.12f, 1.1f, 0.12f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.85f : 0.85f, 1.1f, 0);
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    // ---------- Stage 0: 地形 (backup→緩和→段丘→門前apron) ----------
    public static string Stage0_Terrain()
    {
        var sb = new System.Text.StringBuilder();
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        // 正規化ハイトマップ ↔ 世界標高 (terrain原点Y=tp.yのオフセットを忘れない!)
        Func<float, float> HtoW = hn => hn * ts.y + tp.y;
        Func<float, float> WtoH = wy => (wy - tp.y) / ts.y;

        // backup (x[-710,-360] z[930,1290])
        int bx0 = IX(-710f), bx1 = IX(-360f), bz0 = IZ(930f), bz1 = IZ(1290f);
        int bw = bx1 - bx0 + 1, bh = bz1 - bz0 + 1;
        var bak = td.GetHeights(bx0, bz0, bw, bh);
        string bakPath = "/private/tmp/claude-501/-Users-toshio-project-edo-unity/28bb58d6-5752-4df2-bbb2-c112823166e4/scratchpad/sannokita_backup_" + bx0 + "_" + bz0 + "_" + bw + "x" + bh + ".bin";
        using (var bwr = new System.IO.BinaryWriter(System.IO.File.Open(bakPath, System.IO.FileMode.Create)))
        { bwr.Write(bx0); bwr.Write(bz0); bwr.Write(bw); bwr.Write(bh);
          for (int z = 0; z < bh; z++) for (int x = 0; x < bw; x++) bwr.Write(bak[z, x]); }
        sb.AppendLine("backup " + bw + "x" + bh + " -> " + bakPath);

        // --- 1) 日比谷高校校庭ベンチのラプラシアン緩和 ---
        //     可動セル: x[-462,-366] z[942,1094] かつ 現況h<23 (尾根h>=23は固定)
        {
            int x0 = IX(-462f), x1 = IX(-366f), z0 = IZ(942f), z1 = IZ(1094f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            var mov = new bool[h, w]; int nm = 0;
            for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
                if (HtoW(H[z, x]) < 23f) { mov[z, x] = true; nm++; }
            for (int it = 0; it < 900; it++)
            {
                var H2 = (float[,])H.Clone();
                for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
                    if (mov[z, x]) H2[z, x] = (H[z - 1, x] + H[z + 1, x] + H[z, x - 1] + H[z, x + 1]) * 0.25f;
                H = H2;
            }
            td.SetHeightsDelayLOD(x0, z0, H);
            sb.AppendLine("bench relax cells=" + nm);
        }
        // --- 2) 土井区画内の浅い掘り込み(メキシコ大使館)を軽く緩和 ---
        {
            int x0 = IX(-537f), x1 = IX(-462f), z0 = IZ(1106f), z1 = IZ(1172f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            var mov = new bool[h, w]; int nm = 0;
            for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
                if (HtoW(H[z, x]) < 25.9f) { mov[z, x] = true; nm++; }
            for (int it = 0; it < 400; it++)
            {
                var H2 = (float[,])H.Clone();
                for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
                    if (mov[z, x]) H2[z, x] = (H[z - 1, x] + H[z + 1, x] + H[z, x - 1] + H[z, x + 1]) * 0.25f;
                H = H2;
            }
            td.SetHeightsDelayLOD(x0, z0, H);
            sb.AppendLine("doi relax cells=" + nm);
        }
        // --- 3) 岡部の段丘 T1=15.0(門前〜表庭) / T2=19.0(表御殿) — 近代改変域(x>=-472)内のみ ---
        {
            Vector2 g = GATE_OKABE;
            Vector2 inw = new Vector2(-0.715f, -0.699f);           // 表門辺の内向き
            Vector2 uh = new Vector2(-inw.y, inw.x);               // 辺沿い
            int x0 = IX(-478f), x1 = IX(-366f), z0 = IZ(1000f), z1 = IZ(1100f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            int nm = 0;
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
            {
                float wx = WX(x0 + x), wz = WZ(z0 + z);
                if (wx < -472f) continue;
                var p = new Vector2(wx, wz);
                if (!PIP(OKABE, p) || DistToPolyEdge(OKABE, p) < 1.2f) continue;
                float u = Vector2.Dot(p - g, uh), v = Vector2.Dot(p - g, inw);
                float target;
                if (v < -2f || v > 68f || Mathf.Abs(u) > 30f) continue;
                if (v <= 14f) target = 15.0f;
                else if (v <= 24f) target = Mathf.Lerp(15.0f, 19.0f, Mathf.SmoothStep(0f, 1f, (v - 14f) / 10f));
                else target = 19.0f;
                // 縁のフェザー(縁6mで自然地形へ)
                float eu = Mathf.Clamp01((30f - Mathf.Abs(u)) / 6f);
                float ev = Mathf.Clamp01((68f - v) / 6f) * Mathf.Clamp01((v + 2f) / 4f);
                float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(eu, ev));
                float cur = HtoW(H[z, x]);
                H[z, x] = WtoH(Mathf.Lerp(cur, target, k));
                nm++;
            }
            td.SetHeightsDelayLOD(x0, z0, H);
            sb.AppendLine("okabe terrace cells=" + nm);
        }
        // --- 4) 門前apron ×3 (r13平場 → r13-21 smoothstep, §19の作法) ---
        var aprons = new[] {
            new { g = GATE_OKABE, H0 = 15.0f },
            new { g = GATE_DOI, H0 = 22.0f },
            new { g = GATE_MATSU, H0 = 26.0f } };
        foreach (var ap in aprons)
        {
            int x0 = IX(ap.g.x - 22f), x1 = IX(ap.g.x + 22f), z0 = IZ(ap.g.y - 22f), z1 = IZ(ap.g.y + 22f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
            {
                float wx = WX(x0 + x), wz = WZ(z0 + z);
                float d = Vector2.Distance(new Vector2(wx, wz), ap.g);
                if (d > 21f) continue;
                float k = d <= 13f ? 1f : 1f - Mathf.SmoothStep(0f, 1f, (d - 13f) / 8f);
                float cur = HtoW(H[z, x]);
                H[z, x] = WtoH(Mathf.Lerp(cur, ap.H0, k));
            }
            td.SetHeightsDelayLOD(x0, z0, H);
        }
        td.SyncHeightmap();
        sb.AppendLine("aprons done");
        return sb.ToString();
    }

    // ---------- Stage 1: 岡部筑前守上屋敷 ----------
    public static string Stage1_Okabe()
    {
        const string G = "Edo_Yashiki_OkabeChikuzen";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Okabe";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(OKABE, 9);   // 辺9(NE)
        float gateHalf = PlaceGate(PKmon, monGrp, GATE_OKABE, fout, 2, "Kmon", sb);
        int N = OKABE.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = OKABE[i], b = OKABE[(i + 1) % N];
            Vector2 outw = -InwardNormal(OKABE, i);
            if (i == 0 || i == 2) continue;                 // 樹下・常明院と背中合わせ
            else if (i == 4 || i == 5) continue;            // 松平所有
            else if (i == 6 || i == 7) continue;            // 岡部所有(EdoOkabeYashikiBuilder の Hei_N1〜N4b が実体。二重に建てない)
            else if (i == 9)
                FrontWall(kak, a, b, outw, GATE_OKABE, gateHalf + 0.5f, "Hei_F");
            else if (i == 10)
                EdoNishiTameikeBuilder.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_E");  // 三べ坂沿い=盲長屋
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        // 御殿群: 表御殿(T2)=門正対 / 役所(T1) / 奥御殿・台所・蔵=自然の尾根上
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var og = Place(PBigHouse, Vector3.zero, yawGate, Vector3.one, bg, "OmoteGoten");
        CenterSeat(og, -437f, 1053f);
        var yk = Place(PHouseB, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Yakusho");
        CenterSeat(yk, -400f, 1060f);
        var ok = Place(PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OkuGoten");
        CenterSeat(ok, -505f, 1030f);
        var dd = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one * 0.9f, bg, "Daidokoro");
        CenterSeat(dd, -487f, 1000f);
        for (int i = 0; i < 2; i++)
        {
            var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -545f - i * 9f, 1005f);
        }
        Well(bg, -495f, 1012f);
        // 庭: 尾根上=松+刈込 / 西低地(旧溜池端)=松疎林
        var gg = Group(G, "Garden");
        var rnd = new System.Random(53000);
        for (int i = 0, gd = 0; i < 30 && gd < 1400; gd++)
        {
            float px = Mathf.Lerp(-690f, -380f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(940f, 1090f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(OKABE, p2) || DistToPolyEdge(OKABE, p2) < 4f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            // 表門・段丘の白洲は空けておく
            Vector2 inw = -(-InwardNormal(OKABE, 9));
            float v = Vector2.Dot(p2 - GATE_OKABE, InwardNormal(OKABE, 9));
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_OKABE, new Vector2(-InwardNormal(OKABE, 9).y, InwardNormal(OKABE, 9).x)));
            if (v > -3f && v < 34f && u < 24f) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.72)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        // 門→表御殿の飛石
        for (float tt = 0; tt <= 1.001f; tt += 0.09f)
        {
            Vector2 p = Vector2.Lerp(GATE_OKABE + InwardNormal(OKABE, 9) * 4f, new Vector2(-431f, 1057f), tt);
            float y = Ground(p.x, p.y);
            var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, gg, "Tobi_" + tt);
            SeatBottom(go, y + 0.02f);
        }
        return sb.ToString() + "okabe done";
    }

    // ---------- Stage 2: 土井大隅守上屋敷 ----------
    public static string Stage2_Doi()
    {
        const string G = "Edo_Yashiki_DoiOsumi";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Doi";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(DOI, 4);   // 辺4(E)
        float gateHalf = PlaceGate(PNmon, monGrp, GATE_DOI, fout, 2, "Nagayamon", sb);
        int N = DOI.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = DOI[i], b = DOI[(i + 1) % N];
            Vector2 outw = -InwardNormal(DOI, i);
            if (i >= 5 || i <= 1) continue;                  // 北・西=松平所有 / 南(0-1,1-2)=岡部所有
            else if (i == 4)
                FrontWall(kak, a, b, outw, GATE_DOI, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);   // 練塀(記録: 安政地震で大破)
        }
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var shu = Place(PHouse, Vector3.zero, yawGate, Vector3.one, bg, "Goten");
        CenterSeat(shu, -478f, 1140f);
        var dd = Place(PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 0.85f, bg, "Daidokoro");
        CenterSeat(dd, -502f, 1152f);
        for (int i = 0; i < 2; i++)
        {
            var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -530f - i * 9f, 1128f);
        }
        Well(bg, -492f, 1142f);
        var gg = Group(G, "Garden");
        var rnd = new System.Random(23000);
        for (int i = 0, gd = 0; i < 12 && gd < 700; gd++)
        {
            float px = Mathf.Lerp(-635f, -440f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(1070f, 1174f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(DOI, p2) || DistToPolyEdge(DOI, p2) < 3.5f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.7)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.6f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "doi done";
    }

    // ---------- Stage 3: 松平出羽守上屋敷 ----------
    public static string Stage3_Matsudaira()
    {
        const string G = "Edo_Yashiki_MatsudairaDewa";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Matsudaira";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(MATSU, 10);   // 辺10(N西)
        float gateHalf = PlaceGate(PKmon, monGrp, GATE_MATSU, fout, 2, "Kmon", sb);
        int N = MATSU.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = MATSU[i], b = MATSU[(i + 1) % N];
            Vector2 outw = -InwardNormal(MATSU, i);
            if (i == 10)
                FrontWall(kak, a, b, outw, GATE_MATSU, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        // 表御殿=Manor(facade+35.2偏心 → OBB中心=facadeの31.2m奥)
        var manor = Place(PManor, Vector3.zero, yawGate, Vector3.one, bg, "OmoteGoten");
        CenterSeat(manor, -658f, 1202f);
        var okg = Place(PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OkuGoten");
        CenterSeat(okg, -595f, 1175f);
        var yks = Place(PHouseB, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Yakusho");
        CenterSeat(yks, -625f, 1237f);
        var dd = Place(PSmallHouse, Vector3.zero, yawGate, Vector3.one, bg, "Daidokoro");
        CenterSeat(dd, -692f, 1180f);
        for (int i = 0; i < 4; i++)
        {
            var kr = Place(PKura, Vector3.zero, 90f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -560f - i * 9f, 1195f);
        }
        // 家臣長屋 2組(定府家臣)
        var n1 = Place(EdoAssets.Eg.KnagayaL, Vector3.zero, 0f, Vector3.one * ES, bg, "KashinNagaya_A_L");
        CenterSeat(n1, -545f, 1272f);
        var n2 = Place(EdoAssets.Eg.KnagayaR, Vector3.zero, 0f, Vector3.one * ES, bg, "KashinNagaya_A_R");
        CenterSeat(n2, -537.2f, 1272f);
        var n3 = Place(EdoAssets.Eg.KnagayaL, Vector3.zero, 90f, Vector3.one * ES, bg, "KashinNagaya_B_L");
        CenterSeat(n3, -510f, 1240f);
        var n4 = Place(EdoAssets.Eg.KnagayaR, Vector3.zero, 90f, Vector3.one * ES, bg, "KashinNagaya_B_R");
        CenterSeat(n4, -510f, 1232.2f);
        Well(bg, -672f, 1185f);
        // 庭: 台地=松・刈込 / 西斜面(溜池を望む)=**指図 slopeBands の3帯**(2026-08-22 是正)
        //   下部〜裾(<10.5)=草地・高木なし / 中部(10.5〜14)=低木・下草 / 上部(≥14)=黒松(疎)+雑木。
        //   竹林ではない — [橋本・堀1998](査読) 溜池の水辺の樹木は2例とも松/竹薮は江戸の水辺79事例中1例。
        //   『江戸名所図会』溜池・広重「赤坂桐畑」もこの崖線を松+広葉樹で描き竹は無い。
        //   ⚠ 竹垣(rails R_West/R_South)は垣の材で別物。
        var gg = Group(G, "Garden");
        var rnd = new System.Random(186000);
        for (int i = 0, gd = 0; i < 46 && gd < 2000; gd++)
        {
            float px = Mathf.Lerp(-750f, -470f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(1035f, 1300f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(MATSU, p2) || DistToPolyEdge(MATSU, p2) < 4f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float v = Vector2.Dot(p2 - GATE_MATSU, InwardNormal(MATSU, 10));
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_MATSU, new Vector2(-InwardNormal(MATSU, 10).y, InwardNormal(MATSU, 10).x)));
            if (v > -3f && v < 26f && u < 18f) continue;    // 門前白洲
            float y = Ground(px, pz);
            if (y < 10.5f) continue;                       // 下部〜裾=草地。高木を置かない
            if (y < 14f)
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            else if (rnd.NextDouble() < 0.7)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "matsudaira done";
    }

    // ---------- Stage 4: スプラット(道・敷地) ----------
    public static string Stage4_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -775, x1 = -360, z0 = 932, z1 = 1325;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        // 東の南北道(三べ坂前身: 門前町→楔→永田馬場) / 北の大通り(赤坂御門→永田馬場) / 堀端通り
        Vector2[] eastRoad = { new Vector2(-367f, 948f), new Vector2(-372f, 1000f), new Vector2(-380.4f, 1057f),
            new Vector2(-421.8f, 1099.8f), new Vector2(-427.2f, 1108f), new Vector2(-453.9f, 1179.6f),
            new Vector2(-468f, 1240f), new Vector2(-482f, 1298f) };
        Vector2[] northRoad = { new Vector2(-772f, 1212f), new Vector2(-741f, 1230f), new Vector2(-660f, 1268f),
            new Vector2(-573f, 1307f), new Vector2(-501f, 1313f), new Vector2(-462f, 1315f) };
        Vector2[] shoreRoad = { new Vector2(-651f, 940f), new Vector2(-672f, 985f), new Vector2(-699f, 1031f),
            new Vector2(-727.5f, 1071f), new Vector2(-751f, 1124f), new Vector2(-759.5f, 1180f), new Vector2(-741f, 1226f) };
        Vector2[] wedge = { new Vector2(-431f, 1101f), new Vector2(-458f, 1091.3f) };
        Func<Vector2, Vector2[], float> dPoly = (p, pts) =>
        {
            float m = float.MaxValue;
            for (int i = 0; i < pts.Length - 1; i++) m = Mathf.Min(m, DistToEdge(p, pts[i], pts[i + 1]));
            return m;
        };
        Vector2[][] parcels = { OKABE, DOI, MATSU };
        Vector2 inw9 = InwardNormal(OKABE, 9);
        Vector2 uh9 = new Vector2(-inw9.y, inw9.x);
        Vector2 inwM = InwardNormal(MATSU, 10);
        Vector2 uhM = new Vector2(-inwM.y, inwM.x);
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float gnd = Ground(wx, wz);
                if (gnd < 7.0f) continue;                    // 水面・水際は触らない
                if (wz < 948f && wx > -585f) continue;       // 樹下・常明院・境内側は触らない
                float bare = -1, grass = 0, dirt = 0;
                Vector2[] inP = null;
                foreach (var pp in parcels) if (PIP(pp, p)) { inP = pp; break; }
                float de = dPoly(p, eastRoad), dn = dPoly(p, northRoad), ds = dPoly(p, shoreRoad), dw = dPoly(p, wedge);
                if (inP != null)
                {
                    // 門前白洲
                    bool shirasu = false;
                    if (inP == OKABE)
                    {
                        float v = Vector2.Dot(p - GATE_OKABE, inw9), u = Mathf.Abs(Vector2.Dot(p - GATE_OKABE, uh9));
                        if (v > -1f && v < 32f && u < 23f) shirasu = true;
                    }
                    else if (inP == MATSU)
                    {
                        float v = Vector2.Dot(p - GATE_MATSU, inwM), u = Mathf.Abs(Vector2.Dot(p - GATE_MATSU, uhM));
                        if (v > -1f && v < 24f && u < 17f) shirasu = true;
                    }
                    if (shirasu) { bare = 0.62f; grass = 0.08f; dirt = 0.30f; }
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.38f, 0.65f, noise); bare = 0.14f; dirt = 1f - grass - bare;
                    }
                }
                else if (dn < 5.0f || de < 3.2f || ds < 3.2f || dw < 3.0f) { bare = 0.55f; grass = 0.05f; dirt = 0.40f; }
                else if (dn < 6.6f || de < 4.8f || ds < 4.8f) { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }
                if (bare < 0) continue;
                float sum = bare + grass + dirt;
                for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                changed++;
            }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- 一括 ----------
    public static string BuildAll()
    {
        EdoNishiTameikeBuilder.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Terrain());
        sb.AppendLine(Stage1_Okabe());
        sb.AppendLine(Stage2_Doi());
        sb.AppendLine(Stage3_Matsudaira());
        sb.AppendLine(Stage4_Splat());
        return sb.ToString();
    }
}
