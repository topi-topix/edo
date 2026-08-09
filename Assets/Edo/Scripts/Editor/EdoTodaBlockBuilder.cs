// 溜池西ブロック5敷地ビルダー (2026-08-09)
//   紫=戸田采女正(氏正/大垣藩10万石)【上屋敷】 赤=定火消御役屋敷 小出伊織(有義/5000石)
//   緑=寄合 井上寿一郎(4000石/麻布谷丁)  黄=澄泉寺(真宗高田派触頭・塔頭3)  水=陽泉寺(曹洞宗・門前ねぶと町)
// 【典拠】区画=ユーザー下書き(EdoSketch 5色)を隣接壁・道路へスナップ。
//   考証=尾張屋版「今井谷六本木赤坂絵図」嘉永3(NDL 1286666, IIIF実見)+CODH 9-106〜9-110 ほか
//   (2026-08-09 Web調査: 戸田=上屋敷(九曜紋/跡地アークヒルズ・ANAインターコンチ)、
//    小出=定火消御役屋鋪(赤坂溜池組, 嘉永2-安政3 小出有義)、澄泉寺=高田派江戸三箇寺・塔頭3寺、
//    陽泉寺=門前俗称ねぶと町(東縁の町屋短冊)、井上=安政武鑑寄合「あさふ谷丁 井上寿一郎」)。
// 【門の向き】切絵図文字の頭: 戸田=西北西(北西の通り)/小出=南西(谷町へ抜ける小路)/
//    井上=東南東(御先手組・明福寺との間の道)/澄泉寺=北東(溜池端方面)/陽泉寺=東(門前町の通り)。
// 【地形】造成ゼロ・現地形追従(terrain-follows-present-day)。屋敷内部絵図は未発見のため
//    敷地内構成は同格の一般類型(典拠: 一般類型/当地の一次史料は未確認)。池は典拠なしのため作らない。
// 各段階は既存グループがあればスキップ(手直し保護)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoTodaBlockBuilder
{
    // ---------- assets ----------
    const string PHei = "Assets/edogoyomi/es_dobei/s_hei_center.obj";
    const string PHmon = "Assets/edogoyomi/es_hmon/h_mon.obj";
    const string PKmon = "Assets/edogoyomi/es_kmon/k_mon.obj";
    const string PNmon = "Assets/edogoyomi/es_nmon/nagayamon.obj";
    const string PKabuki = "Assets/edogoyomi/es_kabukimon/kabukimon.obj";
    const string PBansho = "Assets/edogoyomi/es_dbansho/dbansho.obj";
    const string PKura = "Assets/edogoyomi/es_kura/kura.obj";
    const string PHinomi = "Assets/edogoyomi/es_hinomi/hinomiyagura.obj";
    const string PKnagayaC = "Assets/edogoyomi/es_knagaya/knagaya01c.obj";
    const string PKnagayaL = "Assets/edogoyomi/es_knagaya/knagaya01l.obj";
    const string PKnagayaR = "Assets/edogoyomi/es_knagaya/knagaya01r.obj";
    const string PHouse = "Assets/Japanese Village Kit/Prefabs/House.prefab";
    const string PHouseB = "Assets/Japanese Village Kit/Prefabs/House B.prefab";
    const string PSmallHouse = "Assets/Japanese Village Kit/Prefabs/Small House.prefab";
    const string PBigHouse = "Assets/Japanese Village Kit/Prefabs/Big House.prefab";
    const string PManor = "Assets/Japanese Village Kit/Prefabs/Manor.prefab";
    const string PShop01 = "Assets/edogoyomi/es_shop01/shop01.obj";
    const string PShop02 = "Assets/edogoyomi/es_shop02/shop02.obj";
    public const float ES = 1.818f;

    // ---------- parcel data ----------
    public class Parcel
    {
        public string group, label;
        public Vector2[] poly;
        public int front;            // 表門のある辺 (Pi->Pi+1)
        public float gateT = 0.5f;
        public string gateType;      // k_mon | h_mon | nagayamon | sanmon | none
        public int bansho;
        public int[] nagayaEdges = new int[0];
        public int[] dobeiEdges = new int[0];
        public int[] noWallEdges = new int[0]; // 隣が受け持つ境界
    }

    // 境界線の定義:
    //  L1: 松平日向守 南壁ライン(-425.3,222.7)->(-292.3,144.2) の 2.2m 内側
    //  L2: 山口(牛久)南西壁ライン(-289.7,142.1)->(-200.3,88.2) の 8.2m 内側(壁2.2+街路6)
    //  小出西辺=寺地との小路(幅6m)の東縁。陽泉寺東辺=小路から10m(ねぶと町奥行)。
    public static Parcel[] Parcels = new Parcel[]
    {
        new Parcel{ group="Edo_Yashiki_TodaUneme", label="戸田采女正(大垣藩10万石)上屋敷",
            poly=new[]{
                new Vector2(-324.2f,158.7f),   // 0 澄泉寺NW角と共有
                new Vector2(-425.5f,219.5f),   // 1 NE角(日向守SW角の2.2m内側)
                new Vector2(-530.6f,68.0f),    // 2 北西の通り沿い南端
                new Vector2(-589.3f,105.5f),   // 3 腕部NW角
                new Vector2(-619.4f,60.5f),    // 4 腕部W角
                new Vector2(-511.5f,-9.0f),    // 5 腕部S角
                new Vector2(-469.6f,28.0f),    // 6 井上SW角
                new Vector2(-472.9f,55.75f),   // 7 井上NW角
                new Vector2(-453.7f,83.7f),    // 8 井上N角
                new Vector2(-373.4f,31.7f),    // 9 井上E角
                new Vector2(-354.5f,50.6f),    // 10 陽泉寺SW角
                new Vector2(-329.8f,91.8f),    // 11 陽泉寺NW角
                new Vector2(-357.9f,108.75f),  // 12 澄泉寺SW角
            },
            front=1, gateT=0.13f, gateType="k_mon", bansho=2,          // 表門=北西の通り北寄り(文字の頭=西北西/谷筋平坦帯に玄関正対)
            nagayaEdges=new[]{2,4},                                    // 街路沿いの家臣長屋
            dobeiEdges=new[]{0,3,5,6,7,8,9,10,11,12} },
        new Parcel{ group="Edo_Hikeshi_Koide", label="定火消御役屋敷 小出伊織(5000石)",
            poly=new[]{
                new Vector2(-203.1f,80.4f),    // 0 NE角(L2街路南縁∩大通り)
                new Vector2(-245.4f,-6.7f),    // 1 S角(大通り∩南の小路)
                new Vector2(-290.0f,15.9f),    // 2 SW角(南の小路∩寺小路)
                new Vector2(-242.1f,104.0f),   // 3 NW角(寺小路∩L2街路)
            },
            front=1, gateT=0.45f, gateType="h_mon", bansho=1,          // 表門=南西の小路(文字倒立)
            nagayaEdges=new[]{0,3},                                    // 臥煙部屋・与力同心長屋(大通り沿い+北)
            dobeiEdges=new[]{2} },
        new Parcel{ group="Edo_Yashiki_Inoue", label="寄合 井上寿一郎(4000石)",
            poly=new[]{
                new Vector2(-373.4f,31.7f),    // 0 E角
                new Vector2(-453.7f,83.7f),    // 1 N角
                new Vector2(-472.9f,55.75f),   // 2 NW角
                new Vector2(-469.6f,28.0f),    // 3 SW角
                new Vector2(-400.6f,-13.25f),  // 4 S角
            },
            front=4, gateT=0.5f, gateType="h_mon", bansho=1,           // 表門=南東の道(文字の頭=東南東)
            nagayaEdges=new[]{3},                                      // 南の道沿い
            dobeiEdges=new int[0],                                     // 0,1,2 は戸田側が受け持つ
            noWallEdges=new[]{0,1,2} },
        new Parcel{ group="Edo_Temple_Chosenji", label="澄泉寺(真宗高田派触頭)",
            poly=new[]{
                new Vector2(-324.2f,158.7f),   // 0 NW角
                new Vector2(-247.4f,106.9f),   // 1 NE角(参道側)
                new Vector2(-266.9f,71.0f),    // 2 SE角(小路沿い)
                new Vector2(-299.5f,91.4f),    // 3 陽泉寺との折れ
                new Vector2(-308.65f,80.4f),   // 4 陽泉寺との折れ
                new Vector2(-357.9f,108.75f),  // 5 SW角
            },
            front=0, gateT=0.62f, gateType="sanmon", bansho=0,         // 山門=北東辺(溜池端方面, 文字正立)
            dobeiEdges=new[]{0,1,2},
            noWallEdges=new[]{3,4,5} },                                // 西は戸田塀/南は陽泉寺塀
        new Parcel{ group="Edo_Temple_Yosenji", label="陽泉寺(曹洞宗)",
            poly=new[]{
                new Vector2(-329.8f,91.8f),    // 0 NW角
                new Vector2(-308.65f,80.4f),   // 1 澄泉寺との折れ
                new Vector2(-299.5f,91.4f),    // 2 澄泉寺との折れ
                new Vector2(-275.1f,76.9f),    // 3 NE角(ねぶと町北端)
                new Vector2(-301.5f,28.5f),    // 4 SE角(ねぶと町南端)
                new Vector2(-298.7f,19.2f),    // 5 S角(小路との辻)
                new Vector2(-354.5f,50.6f),    // 6 SW角
            },
            front=3, gateT=0.45f, gateType="sanmon", bansho=0,         // 山門=東辺(門前町の通りへ)
            dobeiEdges=new[]{1,2,3,4,5},
            noWallEdges=new[]{0,6} },                                  // 西/北西は戸田塀
    };

    // ---------- helpers (EdoNishiTameikeBuilder の公開ヘルパを利用) ----------
    static float Ground(float x, float z) { return EdoNishiTameikeBuilder.Ground(x, z); }
    static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    { return EdoNishiTameikeBuilder.Place(path, pos, ry, scale, parent, name); }
    static Bounds RB(GameObject go) { return EdoNishiTameikeBuilder.RB(go); }
    static void SeatBottom(GameObject go, float y) { EdoNishiTameikeBuilder.SeatBottom(go, y); }

    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var g = new GameObject(seg);
                Undo.RegisterCreatedObjectUndo(g, "grp");
                g.transform.SetParent(cur, false);
                nx = g.transform;
            }
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
    public static Vector2 InwardNormal(Parcel e, int i)
    {
        var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        if (SignedArea(e.poly) < 0) n = -n;
        return n;
    }
    static float DistToEdge(Vector2 p, Vector2 a, Vector2 b)
    {
        var d = b - a; float len = d.magnitude; d /= len;
        float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
        return (p - (a + d * t)).magnitude;
    }
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++) m = Mathf.Min(m, DistToEdge(p, poly[i], poly[(i + 1) % poly.Length]));
        return m;
    }
    public static Vector2 GatePos(Parcel e)
    {
        int N = e.poly.Length;
        return Vector2.Lerp(e.poly[e.front], e.poly[(e.front + 1) % N], e.gateT);
    }
    // (u,v) 敷地ローカル: 原点=門, u=表辺沿い, v=内向き
    public static void Frame(Parcel e, out Vector2 gate2, out Vector2 uhat, out Vector2 vhat)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        gate2 = Vector2.Lerp(fA, fB, e.gateT);
        uhat = (fB - fA).normalized;
        vhat = InwardNormal(e, e.front);
    }
    public static GameObject PlaceUV(Parcel e, string path, float u, float v, float faceYawOffset, Vector3 scale, Transform parent, string name)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float streetYaw = Mathf.Atan2(-vhat.x, -vhat.y) * Mathf.Rad2Deg;
        float y = Ground(p.x, p.y);
        var go = Place(path, new Vector3(p.x, y, p.y), streetYaw + faceYawOffset, scale, parent, name);
        SeatBottom(go, y - 0.12f);
        return go;
    }
    // (u,v)アンカー周辺で「W×D 矩形の高低差が最小」の点を探す(±searchR, 1m刻み)
    public static Vector2 FlatNear(Parcel e, float u, float v, float W, float D, float searchR, float edgeMargin)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 anchor = gate2 + uhat * u + vhat * v;
        float bestScore = float.MaxValue; Vector2 best = anchor;
        for (float dx = -searchR; dx <= searchR; dx += 1.5f)
            for (float dz = -searchR; dz <= searchR; dz += 1.5f)
            {
                var c = anchor + new Vector2(dx, dz);
                if (!PIP(e.poly, c) || DistToPolyEdge(e.poly, c) < edgeMargin) continue;
                float mn = float.MaxValue, mx = float.MinValue;
                for (int i = -1; i <= 1; i++)
                    for (int j = -1; j <= 1; j++)
                    {
                        var q = c + uhat * (i * W / 2) + vhat * (j * D / 2);
                        float h = Ground(q.x, q.y);
                        mn = Mathf.Min(mn, h); mx = Mathf.Max(mx, h);
                    }
                float score = (mx - mn) + (c - anchor).magnitude * 0.01f;
                if (score < bestScore) { bestScore = score; best = c; }
            }
        return best;
    }
    public static GameObject PlaceUVFlat(Parcel e, string path, float u, float v, float faceYawOffset, Vector3 scale,
        Transform parent, string name, float W, float D, float searchR, float edgeMargin)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 c = FlatNear(e, u, v, W, D, searchR, edgeMargin);
        float streetYaw = Mathf.Atan2(-vhat.x, -vhat.y) * Mathf.Rad2Deg;
        // 矩形四隅+中心の最小地盤に据える(浮き対策は SeatBottom + 最小値)
        float mn = float.MaxValue;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
        {
            var q = c + uhat * (i * W / 2) + vhat * (j * D / 2);
            mn = Mathf.Min(mn, Ground(q.x, q.y));
        }
        var go = Place(path, new Vector3(c.x, mn, c.y), streetYaw + faceYawOffset, scale, parent, name);
        SeatBottom(go, mn - 0.12f);
        return go;
    }

    // ---------- Stage 1: 囲い ----------
    public static string Stage1_Enclosure(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Kakoi") != null) return "SKIP: " + e.group + "/Kakoi exists";
        var kak = Group(e.group, "Kakoi");
        var monGrp = Group(e.group, "Omotemon");
        int N = e.poly.Length;
        var sb = new System.Text.StringBuilder();

        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 fout = -vhat;
        float basePad = Ground(gate2.x, gate2.y);
        float psiIn = Mathf.Atan2(vhat.x, vhat.y) * Mathf.Rad2Deg;

        // --- 門 ---
        GameObject mon = null; float gateHalf = 0f;
        if (e.gateType == "k_mon") mon = Place(PKmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Kmon");
        else if (e.gateType == "nagayamon") mon = Place(PNmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Nagayamon");
        else if (e.gateType == "h_mon") mon = Place(PHmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one, monGrp, "Hmon");
        else if (e.gateType == "sanmon") mon = Place(PKabuki, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Sanmon");
        if (mon != null)
        {
            SeatBottom(mon, basePad - 0.05f);
            var mb = RB(mon);
            mon.transform.position += new Vector3(gate2.x - mb.center.x, 0, gate2.y - mb.center.z);
            // kagami(控柱)が内側かの検証(外なら180回転)
            float kmn = float.MaxValue, kmx = float.MinValue;
            foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
            {
                if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
                foreach (var vtx in mf.sharedMesh.vertices)
                {
                    var wp = mf.transform.TransformPoint(vtx);
                    float pr = wp.x * fout.x + wp.z * fout.y;
                    kmn = Mathf.Min(kmn, pr); kmx = Mathf.Max(kmx, pr);
                }
            }
            if (kmn != float.MaxValue)
            {
                var mc = RB(mon).center;
                float cp = mc.x * fout.x + mc.z * fout.y;
                if ((kmn + kmx) * 0.5f > cp)
                {
                    mon.transform.rotation *= Quaternion.Euler(0, 180, 0);
                    var b2 = RB(mon);
                    mon.transform.position += new Vector3(gate2.x - b2.center.x, 0, gate2.y - b2.center.z);
                    sb.AppendLine("mon flipped (kagami was outward)");
                }
            }
            // 実体幅(壁高帯)
            float wmn = float.MaxValue, wmx = float.MinValue;
            foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
                foreach (var vtx in mf.sharedMesh.vertices)
                {
                    var wp = mf.transform.TransformPoint(vtx);
                    if (wp.y < basePad + 0.5f || wp.y > basePad + 4.5f) continue;
                    float pr = wp.x * uhat.x + wp.z * uhat.y;
                    wmn = Mathf.Min(wmn, pr); wmx = Mathf.Max(wmx, pr);
                }
            gateHalf = (wmx - wmn) * 0.5f;
            sb.AppendLine("gate " + e.gateType + " width=" + (wmx - wmn).ToString("F2"));
        }
        // 番所
        for (int i = 0; i < e.bansho; i++)
        {
            float side = (e.bansho == 1) ? 1f : (i == 0 ? 1f : -1f);
            Vector2 bp = gate2 + uhat * (side * (gateHalf + 3.2f)) + fout * 0.5f;
            float bg = Ground(bp.x, bp.y);
            var ban = Place(PBansho, new Vector3(bp.x, bg, bp.y), psiIn + 180f, Vector3.one * ES, monGrp, "Bansho_" + i);
            SeatBottom(ban, bg - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * fout.x + f3.z * fout.y < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg, 0);
        }

        // --- 辺 ---
        for (int i = 0; i < N; i++)
        {
            if (e.noWallEdges.Contains(i)) continue;
            Vector2 a = e.poly[i], b = e.poly[(i + 1) % N];
            Vector2 outw = -InwardNormal(e, i);
            if (i == e.front)
            {
                if (e.gateType == "nagayamon")
                    EdoNishiTameikeBuilder.NagayaRun(kak, a, b, outw, 0, gate2, gateHalf, "NG_F" + i);
                else
                    EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_F" + i, true, 0, gate2, gateHalf + 0.6f);
            }
            else if (e.nagayaEdges.Contains(i))
                EdoNishiTameikeBuilder.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_" + i);
            else if (e.dobeiEdges.Contains(i))
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        SceneView.RepaintAll();
        return sb.ToString() + "enclosure done: " + e.group;
    }

    // ---------- Stage 2: 建物 ----------
    public static string Stage2_Buildings(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Buildings") != null) return "SKIP: Buildings exists";
        var bg = Group(e.group, "Buildings");
        var sb = new System.Text.StringBuilder();

        if (e.group.Contains("Toda"))
        {
            // 上屋敷: 表御殿(玄関正対)→奥御殿を中庭+渡りで連続、台所は中間、米蔵は搬入門近く
            // 御殿群は門内の低平地(現地形h~11)に置く。庭園=南東の斜面(池は典拠なしのため無し)。
            PlaceUVFlat(e, PManor, 0, 55, 0, Vector3.one, bg, "OmoteGoten", 42, 30, 14, 10);   // Manorはfacade+35.2偏心→pivot v=55でfacade≈v20
            PlaceUVFlat(e, PHouse, 26, 78, 0, Vector3.one, bg, "OkuGoten", 22, 18, 10, 9);
            PlaceUVFlat(e, PSmallHouse, -22, 66, 0, Vector3.one, bg, "Daidokoro", 14, 12, 8, 8);
            PlaceUVFlat(e, PHouseB, -42, 40, 0, Vector3.one, bg, "Yakusho", 20, 16, 10, 9);    // 表役所
            // 蔵列: 裏門(南の通り)近く
            PlaceUVFlat(e, PKura, -60, 62, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 8, 6);
            PlaceUVFlat(e, PKura, -68, 70, 90, Vector3.one * ES, bg, "Kura_2", 7, 5, 8, 6);
            PlaceUVFlat(e, PKura, -76, 78, 90, Vector3.one * ES, bg, "Kura_3", 7, 5, 8, 6);
            Well(e, bg, -14, 74);
            Umaya(e, bg, 30, 24);
        }
        else if (e.group.Contains("Koide"))
        {
            // 定火消御役屋敷: 御役宅(主屋)正面、火の見櫓は大通り側の角、臥煙・与力同心は外周長屋(囲い)
            PlaceUVFlat(e, PHouseB, 0, 30, 0, Vector3.one, bg, "Oyakutaku", 20, 16, 10, 9);
            PlaceUVFlat(e, PSmallHouse, -18, 42, 0, Vector3.one, bg, "Daidokoro", 14, 12, 8, 8);
            PlaceUVFlat(e, PKura, 20, 52, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 8, 6);
            // 火の見櫓: 大通り(NE辺)側の東角近く — 遠望が利く位置
            var yg = PlaceUVFlat(e, PHinomi, 34, 16, 0, Vector3.one * ES, bg, "HinomiYagura", 6, 6, 10, 5);
            Well(e, bg, -8, 48);
            Umaya(e, bg, 24, 14);
            sb.AppendLine("hinomi at " + yg.transform.position);
        }
        else if (e.group.Contains("Inoue"))
        {
            // 旗本4000石: 主屋中央・玄関正対、台所は主屋脇、蔵は境の裏手
            PlaceUVFlat(e, PHouse, 0, 26, 0, Vector3.one, bg, "Shuoku", 20, 16, 10, 9);
            PlaceUVFlat(e, PSmallHouse, -16, 38, 0, Vector3.one, bg, "Daidokoro", 14, 12, 8, 8);
            PlaceUVFlat(e, PKura, 18, 48, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 8, 6);
            Well(e, bg, -6, 44);
        }
        else if (e.group.Contains("Chosenji"))
        {
            // 触頭寺: 本堂(山門正対)+庫裏+塔頭3(常國寺・正福寺・林誓寺)
            PlaceUVFlat(e, PBigHouse, 0, 34, 0, Vector3.one, bg, "Hondo", 24, 18, 10, 8);
            PlaceUVFlat(e, PSmallHouse, 20, 44, 90, Vector3.one, bg, "Kuri", 14, 12, 8, 7);
            PlaceUVFlat(e, PSmallHouse, -30, 22, 0, Vector3.one * 0.85f, bg, "Tacchu_Jokokuji", 12, 10, 8, 6);
            PlaceUVFlat(e, PSmallHouse, -44, 34, 0, Vector3.one * 0.85f, bg, "Tacchu_Shofukuji", 12, 10, 8, 6);
            PlaceUVFlat(e, PSmallHouse, -56, 48, 0, Vector3.one * 0.85f, bg, "Tacchu_Rinseiji", 12, 10, 8, 6);
            Well(e, bg, 12, 52);
            Shoro(e, bg, -14, 42);
        }
        else if (e.group.Contains("Yosenji"))
        {
            PlaceUVFlat(e, PBigHouse, 0, 30, 0, Vector3.one, bg, "Hondo", 22, 16, 9, 8);
            PlaceUVFlat(e, PSmallHouse, 18, 40, 90, Vector3.one, bg, "Kuri", 14, 12, 8, 7);
            Well(e, bg, 10, 48);
        }
        return sb.ToString() + "buildings done: " + e.group;
    }

    // 井戸(合成)
    static void Well(Parcel e, Transform parent, float u, float v)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float y = Ground(p.x, p.y);
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, y, p.y);
        Undo.RegisterCreatedObjectUndo(g, "well");
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.38f, 0.28f, 0.18f);
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
        var beam = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        beam.name = "beam"; beam.transform.SetParent(g.transform, false);
        beam.transform.localScale = new Vector3(0.09f, 0.95f, 0.09f);
        beam.transform.localEulerAngles = new Vector3(0, 0, 90);
        beam.transform.localPosition = new Vector3(0, 2.1f, 0);
        beam.GetComponent<Renderer>().sharedMaterial = wood;
    }

    // 厩/中間長屋: knagaya l+r ペア
    static void Umaya(Parcel e, Transform parent, float u, float v)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 c = FlatNear(e, u, v, 16, 8, 8, 6);
        float y = Ground(c.x, c.y);
        float psi = Mathf.Atan2(vhat.x, vhat.y) * Mathf.Rad2Deg;
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var g = new GameObject("Umaya");
        g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        var m1 = Place(PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = Place(PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        Vector2 p1 = c - negRight * 3.9f;
        Vector2 p2 = c + negRight * 3.9f;
        m1.transform.position = new Vector3(p1.x, y, p1.y);
        m2.transform.position = new Vector3(p2.x, y, p2.y);
        SeatBottom(m1, y - 0.10f); SeatBottom(m2, y - 0.10f);
    }

    // 鐘楼(成満寺 Shoro と同型の合成: 石基壇+4柱+貫+入母屋風屋根+梵鐘)
    static void Shoro(Parcel e, Transform parent, float u, float v)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 c = FlatNear(e, u, v, 6, 6, 8, 5);
        float y = Ground(c.x, c.y);
        var g = new GameObject("Shoro");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(c.x, y, c.y);
        Undo.RegisterCreatedObjectUndo(g, "shoro");
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.58f, 0.57f, 0.54f);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.33f, 0.24f, 0.15f);
        var dark = new Material(Shader.Find("Universal Render Pipeline/Lit")); dark.color = new Color(0.16f, 0.16f, 0.18f);
        var kidan = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kidan.name = "Kidan"; kidan.transform.SetParent(g.transform, false);
        kidan.transform.localScale = new Vector3(4.6f, 0.7f, 4.6f);
        kidan.transform.localPosition = new Vector3(0, 0.35f, 0);
        kidan.GetComponent<Renderer>().sharedMaterial = stone;
        for (int i = 0; i < 4; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "Hashira"; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.28f, 1.75f, 0.28f);
            post.transform.localPosition = new Vector3((i % 2 == 0 ? -1.5f : 1.5f), 0.7f + 1.75f, (i < 2 ? -1.5f : 1.5f));
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
        for (int i = 0; i < 2; i++)
        {
            var nuki = GameObject.CreatePrimitive(PrimitiveType.Cube);
            nuki.name = "Nuki"; nuki.transform.SetParent(g.transform, false);
            nuki.transform.localScale = i == 0 ? new Vector3(3.6f, 0.18f, 0.24f) : new Vector3(0.24f, 0.18f, 3.6f);
            nuki.transform.localPosition = new Vector3(0, 3.35f, 0);
            nuki.GetComponent<Renderer>().sharedMaterial = wood;
        }
        // 屋根: 2枚勾配板 + 棟
        for (int i = 0; i < 2; i++)
        {
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "Yane"; roof.transform.SetParent(g.transform, false);
            roof.transform.localScale = new Vector3(5.4f, 0.12f, 2.9f);
            roof.transform.localPosition = new Vector3(0, 4.75f, i == 0 ? -1.25f : 1.25f);
            roof.transform.localEulerAngles = new Vector3(i == 0 ? -22 : 22, 0, 0);
            roof.GetComponent<Renderer>().sharedMaterial = dark;
        }
        var mune = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mune.name = "Mune"; mune.transform.SetParent(g.transform, false);
        mune.transform.localScale = new Vector3(5.6f, 0.22f, 0.4f);
        mune.transform.localPosition = new Vector3(0, 5.3f, 0);
        mune.GetComponent<Renderer>().sharedMaterial = dark;
        // 梵鐘
        var bell = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        bell.name = "Bonsho"; bell.transform.SetParent(g.transform, false);
        bell.transform.localScale = new Vector3(1.1f, 0.85f, 1.1f);
        bell.transform.localPosition = new Vector3(0, 2.9f, 0);
        var bronze = new Material(Shader.Find("Universal Render Pipeline/Lit")); bronze.color = new Color(0.23f, 0.27f, 0.24f);
        bell.GetComponent<Renderer>().sharedMaterial = bronze;
    }

    // ---------- Stage 3: 門前町(ねぶと町) ----------
    public static string Stage3_Nebutocho()
    {
        const string GROUP = "Edo_Monzen_Nebutocho";
        var exist = GameObject.Find(GROUP);
        if (exist != null && exist.transform.childCount > 0) return "SKIP: " + GROUP + " exists";
        var root = Group(GROUP, null);
        // 小路の西縁ライン(陽泉寺東)に沿って町屋短冊を東向きに並べる
        // ライン: (-295.1,19.2)->(-247.4,106.9) 方向(0.478,0.879)。町屋は z 30..72 の帯。
        Vector2 A = new Vector2(-295.1f, 19.2f);
        Vector2 d = new Vector2(0.478f, 0.879f);
        Vector2 outE = new Vector2(0.879f, -0.478f); // 小路(東)向き法線
        float yawE = Mathf.Atan2(outE.x, outE.y) * Mathf.Rad2Deg;
        var mS1 = MonzenMat("M_Shop01", "Assets/edogoyomi/es_shop01/shop01.jpg");
        var mS2 = MonzenMat("M_Shop02", "Assets/edogoyomi/es_shop02/shop02.jpg");
        int n = 0;
        for (float t = 14f; t <= 74f; t += 7.6f)
        {
            // 山門参道(t≈44±5)は開ける
            if (Mathf.Abs(t - 44f) < 5.5f) continue;
            Vector2 c = A + d * t + (-outE) * 4.6f;
            float y = Ground(c.x, c.y);
            bool big = (n % 3 == 1);
            var go = Place(big ? PShop02 : PShop01, new Vector3(c.x, y, c.y), yawE, Vector3.one * ES, root, "Nebuto_" + n);
            SeatBottom(go, y - 0.10f);
            foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = big ? mS2 : mS1;
            n++;
        }
        return "nebutocho houses=" + n;
    }
    static Material MonzenMat(string name, string texPath)
    {
        string matPath = "Assets/Edo/Materials/" + name + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (m != null) return m;
        m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        if (tex != null) m.mainTexture = tex;
        System.IO.Directory.CreateDirectory("Assets/Edo/Materials");
        AssetDatabase.CreateAsset(m, matPath);
        return m;
    }

    // ---------- Stage 4: 庭・境内の植栽 ----------
    static string[] Pines = {
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_01.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_02.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_03.prefab" };
    static string[] Sakuras = {
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Big_Summer_01.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Big_Summer_05.prefab" };
    static string[] Shrubs = {
        "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 01.prefab",
        "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 03.prefab",
        "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 04.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_01.prefab" };
    static string[] Rocks = {
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_01.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_02.prefab",
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_03.prefab" };
    const string PTobi = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_TobiIshi_A_01.prefab";
    const string PKasuga = "Assets/Edo/Prefabs/KasugaLantern.prefab";
    const string PYukimi = "Assets/Edo/Prefabs/YukimiLantern.prefab";

    public static string Stage4_Garden(string groupName, int seed)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var dead = new List<GameObject>();
        foreach (Transform ch in root.transform) if (ch.name == "Garden" || ch.name.StartsWith("Garden/")) dead.Add(ch.gameObject);
        foreach (var dg in dead) UnityEngine.Object.DestroyImmediate(dg);
        var trees = Group(e.group, "Garden/Trees");
        var shrubs = Group(e.group, "Garden/Shrubs");
        var rocks = Group(e.group, "Garden/Rocks");
        var path = Group(e.group, "Garden/Path");
        var props = Group(e.group, "Garden/Props");
        var rnd = new System.Random(seed);
        var obs = new List<Bounds>();
        foreach (Transform sub in root.transform)
            if (sub.name == "Buildings" || sub.name == "Omotemon")
                foreach (Transform ch in sub) { var rb = RB(ch.gameObject); if (rb.size.sqrMagnitude > 0.01f) obs.Add(rb); }
        Func<Vector2, float, bool> clear = (p, m) =>
        {
            if (!PIP(e.poly, p)) return false;
            // 最寄り辺の種別でマージン: 長屋/表辺=8.5, その他=3.0
            float best = float.MaxValue; float bm = 7.5f;
            for (int i = 0; i < e.poly.Length; i++)
            {
                var a = e.poly[i]; var b2 = e.poly[(i + 1) % e.poly.Length];
                float dd2 = DistToEdge(p, a, b2);
                if (dd2 < best) { best = dd2; bm = (i == e.front || e.nagayaEdges.Contains(i)) ? 8.5f : 3.0f; }
            }
            if (best < bm) return false;
            foreach (var b in obs)
                if (p.x > b.min.x - m && p.x < b.max.x + m && p.y > b.min.z - m && p.y < b.max.z + m) return false;
            return true;
        };
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
        float vCen = Vector2.Dot(cen - gate2, vhat);
        var bb = new Bounds(new Vector3(cen.x, 0, cen.y), Vector3.zero);
        foreach (var p in e.poly) bb.Encapsulate(new Vector3(p.x, 0, p.y));
        bool isTemple = e.gateType == "sanmon";
        bool isToda = e.group.Contains("Toda");
        bool isKoide = e.group.Contains("Koide");
        int nPine = isToda ? 26 : (isTemple ? 8 : (isKoide ? 5 : 8));
        int placed = 0, guard = 0;
        while (placed < nPine && guard++ < 1200)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            float v = Vector2.Dot(p - gate2, vhat);
            if (v < vCen * 0.7f && rnd.NextDouble() < 0.75) continue;
            if (!clear(p, 2.5f)) continue;
            float y = Ground(p.x, p.y);
            float sc = 1.65f * (0.9f + 0.5f * (float)rnd.NextDouble());
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Pine_" + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        // 桜の一群(奥の一隅) — 季節=夏variant
        if (!isKoide)
        {
            Vector2 skC = Vector2.zero; bool found = false;
            for (int i = 0; i < 200 && !found; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) > vCen * 1.1f && clear(p, 3f)) { skC = p; found = true; }
            }
            if (found)
                for (int i = 0; i < 3; i++)
                {
                    var p = skC + new Vector2((float)rnd.NextDouble() * 8 - 4, (float)rnd.NextDouble() * 8 - 4);
                    if (!clear(p, 2f)) continue;
                    float y = Ground(p.x, p.y);
                    float sc = 1.4f * (0.9f + 0.4f * (float)rnd.NextDouble());
                    var go = Place(Sakuras[rnd.Next(Sakuras.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Sakura_" + i);
                    SeatBottom(go, y - 0.05f);
                }
        }
        // 岩組
        int nClu = isToda ? 3 : 1;
        for (int cIdx = 0; cIdx < nClu; cIdx++)
        {
            for (int i = 0; i < 200; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) < vCen) continue;
                if (!clear(p, 2f)) continue;
                float y = Ground(p.x, p.y);
                int cnt = 3 + rnd.Next(2);
                for (int r = 0; r < cnt; r++)
                {
                    var rp = p + new Vector2((float)rnd.NextDouble() * 3.4f - 1.7f, (float)rnd.NextDouble() * 3.4f - 1.7f);
                    float rs = (r == 0 ? 3.2f : 1.6f) * (0.8f + 0.5f * (float)rnd.NextDouble());
                    var rg = Place(Rocks[rnd.Next(Rocks.Length)], new Vector3(rp.x, y, rp.y), (float)rnd.NextDouble() * 360f, Vector3.one * rs, rocks, "Iwa_" + cIdx + "_" + r);
                    SeatBottom(rg, Ground(rp.x, rp.y) - 0.25f);
                }
                break;
            }
        }
        // 低木
        int nShrub = isToda ? 26 : (isKoide ? 8 : 14);
        for (int i = 0, g2 = 0; i < nShrub && g2 < 700; g2++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (!clear(p, 1.2f)) continue;
            float y = Ground(p.x, p.y);
            float sc = 0.9f + 0.7f * (float)rnd.NextDouble();
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, shrubs, "Shrub_" + i);
            SeatBottom(go, y - 0.04f);
            i++;
        }
        // 参道/飛石: 門 → 主建物
        var bld = root.transform.Find("Buildings");
        Transform main = null;
        if (bld != null) main = bld.Find("Hondo") ?? bld.Find("OmoteGoten") ?? bld.Find("Shuoku") ?? bld.Find("Oyakutaku");
        if (main != null)
        {
            var mb = RB(main.gameObject);
            var m2 = new Vector2(mb.center.x, mb.center.z);
            Vector2 g0 = gate2 + vhat * 3.5f;
            Vector2 g1 = m2 - vhat * 10f;
            Vector2 ctrl = (g0 + g1) * 0.5f + new Vector2(-vhat.y, vhat.x) * (isTemple ? 0f : 3.2f);
            int steps = Mathf.Max(4, Mathf.RoundToInt((g1 - g0).magnitude / 2.4f));
            for (int i = 0; i <= steps; i++)
            {
                float tt = (float)i / steps;
                Vector2 p = (1 - tt) * (1 - tt) * g0 + 2 * (1 - tt) * tt * ctrl + tt * tt * g1;
                p += new Vector2((float)rnd.NextDouble() * 0.4f - 0.2f, (float)rnd.NextDouble() * 0.4f - 0.2f);
                float y = Ground(p.x, p.y);
                var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, path, "Tobi_" + i);
                SeatBottom(go, y + 0.02f);
            }
        }
        // 灯籠
        int nLan = isTemple ? 4 : (isToda ? 3 : 2);
        for (int i = 0, g3 = 0; i < nLan && g3 < 300; g3++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 0.5f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = Ground(p.x, p.y);
            string lp = (i % 2 == 0) ? PKasuga : PYukimi;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(lp) == null) lp = "Assets/Japanese Castle/Prefabs/Props/Stone Basket.prefab";
            var go = Place(lp, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, props, "Lantern_" + i);
            SeatBottom(go, y - 0.03f);
            i++;
        }
        // 墓地(寺のみ): 本堂の裏手に墓石列
        if (isTemple) Bochi(e, props, rnd);
        // 邸内稲荷(武家のみ): 北東鬼門
        if (!isTemple) Inari(e, props, rnd);
        return "garden done: " + e.group;
    }

    // 墓地: 本堂裏(v大・u負側)に墓石(石柱+基壇)を列で
    static void Bochi(Parcel e, Transform parent, System.Random rnd)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.60f, 0.60f, 0.58f);
        var g = new GameObject("Bochi");
        g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "bochi");
        // 敷地奥の帯を走査して置けるだけ置く(最大4列x8)
        int placedTotal = 0;
        for (int row = 0; row < 4; row++)
        {
            for (int col = 0; col < 8; col++)
            {
                float u = -34f + col * 3.0f + (float)rnd.NextDouble() * 0.5f;
                float v = 52f + row * 3.0f + (float)rnd.NextDouble() * 0.5f;
                Vector2 p = gate2 + uhat * u + vhat * v;
                if (!PIP(e.poly, p) || DistToPolyEdge(e.poly, p) < 2.5f) continue;
                float y = Ground(p.x, p.y);
                var t = new GameObject("Haka_" + row + "_" + col);
                t.transform.SetParent(g.transform, false);
                t.transform.position = new Vector3(p.x, y, p.y);
                var dai = GameObject.CreatePrimitive(PrimitiveType.Cube);
                dai.name = "dai"; dai.transform.SetParent(t.transform, false);
                dai.transform.localScale = new Vector3(0.75f, 0.25f, 0.75f);
                dai.transform.localPosition = new Vector3(0, 0.12f, 0);
                dai.GetComponent<Renderer>().sharedMaterial = stone;
                var to = GameObject.CreatePrimitive(PrimitiveType.Cube);
                to.name = "to"; to.transform.SetParent(t.transform, false);
                float hh = 0.9f + (float)rnd.NextDouble() * 0.5f;
                to.transform.localScale = new Vector3(0.28f, hh, 0.28f);
                to.transform.localPosition = new Vector3(0, 0.25f + hh / 2, 0);
                to.transform.localEulerAngles = new Vector3(0, (float)rnd.NextDouble() * 8 - 4, 0);
                to.GetComponent<Renderer>().sharedMaterial = stone;
                placedTotal++;
            }
        }
    }

    // 邸内稲荷(北東鬼門)
    static void Inari(Parcel e, Transform parent, System.Random rnd)
    {
        Vector2 best = Vector2.zero; float bestScore = float.MinValue;
        var bbMin = new Vector2(e.poly.Min(p => p.x), e.poly.Min(p => p.y));
        var bbMax = new Vector2(e.poly.Max(p => p.x), e.poly.Max(p => p.y));
        for (int i = 0; i < 400; i++)
        {
            var p2 = new Vector2(Mathf.Lerp(bbMin.x, bbMax.x, (float)rnd.NextDouble()), Mathf.Lerp(bbMin.y, bbMax.y, (float)rnd.NextDouble()));
            if (!PIP(e.poly, p2) || DistToPolyEdge(e.poly, p2) < 4f) continue;
            float score = p2.x + p2.y;
            if (score > bestScore) { bestScore = score; best = p2; }
        }
        if (bestScore == float.MinValue) return;
        float y = Ground(best.x, best.y);
        var g = new GameObject("Inari");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(best.x, y, best.y);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        var shu = new Material(Shader.Find("Universal Render Pipeline/Lit")); shu.color = new Color(0.78f, 0.15f, 0.08f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.30f, 0.18f);
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "t_post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.18f, 1.25f, 0.18f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.9f : 0.9f, 1.25f, -2.2f);
            post.GetComponent<Renderer>().sharedMaterial = shu;
        }
        var kasagi = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kasagi.name = "t_kasagi"; kasagi.transform.SetParent(g.transform, false);
        kasagi.transform.localScale = new Vector3(2.6f, 0.16f, 0.2f);
        kasagi.transform.localPosition = new Vector3(0, 2.5f, -2.2f);
        kasagi.GetComponent<Renderer>().sharedMaterial = shu;
        var nuki = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nuki.name = "t_nuki"; nuki.transform.SetParent(g.transform, false);
        nuki.transform.localScale = new Vector3(2.2f, 0.12f, 0.14f);
        nuki.transform.localPosition = new Vector3(0, 2.05f, -2.2f);
        nuki.GetComponent<Renderer>().sharedMaterial = shu;
        var kidan = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kidan.name = "kidan"; kidan.transform.SetParent(g.transform, false);
        kidan.transform.localScale = new Vector3(1.5f, 0.4f, 1.2f);
        kidan.transform.localPosition = new Vector3(0, 0.2f, 0);
        kidan.GetComponent<Renderer>().sharedMaterial = stone;
        var hokora = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hokora.name = "hokora"; hokora.transform.SetParent(g.transform, false);
        hokora.transform.localScale = new Vector3(0.9f, 0.9f, 0.8f);
        hokora.transform.localPosition = new Vector3(0, 0.85f, 0);
        hokora.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "roof" + i; roof.transform.SetParent(g.transform, false);
            roof.transform.localScale = new Vector3(1.2f, 0.06f, 0.75f);
            roof.transform.localPosition = new Vector3(0, 1.5f, i == 0 ? -0.28f : 0.28f);
            roof.transform.localEulerAngles = new Vector3(i == 0 ? -35 : 35, 0, 0);
            roof.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    // ---------- OBB ユーティリティ ----------
    // ローカル footprint (メッシュ頂点) を測る
    public static void ObbFootprint(Transform it, out float mnx, out float mxx, out float mnz, out float mxz, out float mny)
    {
        mnx = float.MaxValue; mxx = float.MinValue; mnz = float.MaxValue; mxz = float.MinValue; mny = float.MaxValue;
        foreach (var mf in it.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var vts = mesh.vertices;
            for (int i = 0; i < vts.Length; i++)
            {
                var lp = it.InverseTransformPoint(mf.transform.TransformPoint(vts[i]));
                mnx = Mathf.Min(mnx, lp.x); mxx = Mathf.Max(mxx, lp.x);
                mnz = Mathf.Min(mnz, lp.z); mxz = Mathf.Max(mxz, lp.z);
                mny = Mathf.Min(mny, lp.y);
            }
        }
    }
    // OBB中心を(x,z)へ移動し、OBB輪郭点の最小地盤へ接地。埋/浮を返す。
    public static string MoveToObb(string groupName, string childPath, float x, float z)
    {
        var root = GameObject.Find(groupName);
        var it = root.transform.Find(childPath);
        if (it == null) return "missing " + childPath;
        float mnx, mxx, mnz, mxz, mny;
        ObbFootprint(it, out mnx, out mxx, out mnz, out mxz, out mny);
        if (mnx == float.MaxValue) return "no mesh " + childPath;
        // 現OBB中心(world)
        var lcC = new Vector3((mnx + mxx) / 2, mny, (mnz + mxz) / 2);
        var wC = it.TransformPoint(lcC);
        it.position += new Vector3(x - wC.x, 0, z - wC.z);
        // 接地: OBB輪郭12点の最小地盤
        float gmn = float.MaxValue;
        for (int i = 0; i <= 3; i++)
            for (int j = 0; j <= 3; j++)
            {
                if (i > 0 && i < 3 && j > 0 && j < 3) continue;
                var wp = it.TransformPoint(new Vector3(Mathf.Lerp(mnx, mxx, i / 3f), mny, Mathf.Lerp(mnz, mxz, j / 3f)));
                gmn = Mathf.Min(gmn, Ground(wp.x, wp.z));
            }
        var wBase = it.TransformPoint(new Vector3(0, mny, 0));
        it.position += new Vector3(0, (gmn - 0.12f) - wBase.y, 0);
        // 検証
        float buried = float.MinValue, floating = float.MinValue;
        for (int i = 0; i <= 3; i++)
            for (int j = 0; j <= 3; j++)
            {
                if (i > 0 && i < 3 && j > 0 && j < 3) continue;
                var wp = it.TransformPoint(new Vector3(Mathf.Lerp(mnx, mxx, i / 3f), mny, Mathf.Lerp(mnz, mxz, j / 3f)));
                float g = Ground(wp.x, wp.z);
                buried = Mathf.Max(buried, g - wp.y); floating = Mathf.Max(floating, wp.y - g);
            }
        return childPath + " @(" + x.ToString("F0") + "," + z.ToString("F0") + ") OBB" + (mxx - mnx).ToString("F0") + "x" + (mxz - mnz).ToString("F0")
            + " 埋=" + buried.ToString("F2") + " 浮=" + floating.ToString("F2");
    }
    // グループ全建物の OBB 埋/浮/境界距離レポート
    public static string QA_Obb(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        var bld = root.transform.Find("Buildings");
        if (bld == null) return "no buildings";
        var sb = new System.Text.StringBuilder();
        foreach (Transform it in bld)
        {
            float mnx, mxx, mnz, mxz, mny;
            ObbFootprint(it, out mnx, out mxx, out mnz, out mxz, out mny);
            if (mnx == float.MaxValue) { sb.AppendLine(it.name + ": no mesh"); continue; }
            float buried = float.MinValue, floating = float.MinValue, edge = float.MaxValue;
            for (int i = 0; i <= 3; i++)
                for (int j = 0; j <= 3; j++)
                {
                    if (i > 0 && i < 3 && j > 0 && j < 3) continue;
                    var wp = it.TransformPoint(new Vector3(Mathf.Lerp(mnx, mxx, i / 3f), mny, Mathf.Lerp(mnz, mxz, j / 3f)));
                    float g = Ground(wp.x, wp.z);
                    buried = Mathf.Max(buried, g - wp.y); floating = Mathf.Max(floating, wp.y - g);
                    var p2 = new Vector2(wp.x, wp.z);
                    float d = DistToPolyEdge(e.poly, p2);
                    if (!PIP(e.poly, p2)) d = -d;
                    edge = Mathf.Min(edge, d);
                }
            sb.AppendLine(it.name + " OBB" + (mxx - mnx).ToString("F0") + "x" + (mxz - mnz).ToString("F0")
                + " edge=" + edge.ToString("F1") + " 埋=" + buried.ToString("F2") + " 浮=" + floating.ToString("F2"));
        }
        return sb.ToString();
    }

    // ---------- Stage 2b: 建物の制約付き再配置 (§16 総当たり探索) ----------
    // 各建物を「敷地内・境界マージン・相互クリアランス・高低差最小」を満たす最良点へ動かす。
    // 主要建物は門正対軸上のアンカーへ引き寄せる。移動はバウンズ中心差分(合成コンテナ安全)。
    public static string Stage2b_Reposition(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var bld = root.transform.Find("Buildings");
        if (bld == null) return "no buildings";
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        var sb = new System.Text.StringBuilder();

        // 処理順: 主建物→大→小
        string[] order = { "OmoteGoten", "Oyakutaku", "Shuoku", "Hondo", "OkuGoten", "Yakusho", "Kuri",
                           "Daidokoro", "Tacchu_Jokokuji", "Tacchu_Shofukuji", "Tacchu_Rinseiji",
                           "Kura_1", "Kura_2", "Kura_3", "Umaya", "HinomiYagura", "Shoro", "Ido" };
        var items = new List<Transform>();
        foreach (var nm in order) { var c = bld.Find(nm); if (c != null) items.Add(c); }
        foreach (Transform c in bld) if (!items.Contains(c)) items.Add(c);

        // 主建物のアンカー(門正対軸上)
        var anchors = new Dictionary<string, Vector2>();
        float mainDepth = e.group.Contains("Toda") ? 42f : 28f;
        foreach (var nm in new[] { "OmoteGoten", "Oyakutaku", "Shuoku", "Hondo" })
            anchors[nm] = gate2 + vhat * mainDepth;

        var placedB = new List<Bounds>();
        // 門・番所も障害物に
        var monGrp = root.transform.Find("Omotemon");
        if (monGrp != null) foreach (Transform m in monGrp) { var rb = RB(m.gameObject); if (rb.size.sqrMagnitude > 0.01f) placedB.Add(rb); }

        foreach (var it in items)
        {
            var b0 = RB(it.gameObject);
            float hw = b0.extents.x, hd = b0.extents.z;
            string nm = it.name;
            float margin = 6f;
            if (nm.StartsWith("Kura") || nm == "Umaya" || nm == "Daidokoro" || nm.StartsWith("Tacchu") || nm == "Kuri") margin = 3.5f;
            if (nm == "HinomiYagura" || nm == "Shoro" || nm == "Ido") margin = 2.5f;
            Vector2 anchor = anchors.ContainsKey(nm) ? anchors[nm] : new Vector2(b0.center.x, b0.center.z);
            var bbMin = new Vector2(e.poly.Min(p => p.x), e.poly.Min(p => p.y));
            var bbMax = new Vector2(e.poly.Max(p => p.x), e.poly.Max(p => p.y));
            float bestScore = float.MaxValue; Vector2 best = Vector2.zero; float bestSpread = -1;
            for (float cx = bbMin.x + hw; cx <= bbMax.x - hw; cx += 2f)
                for (float cz = bbMin.y + hd; cz <= bbMax.y - hd; cz += 2f)
                {
                    var c = new Vector2(cx, cz);
                    bool ok = true;
                    // 四隅+辺中点が敷地内かつマージン確保
                    for (int i = -1; i <= 1 && ok; i++)
                        for (int j = -1; j <= 1 && ok; j++)
                        {
                            if (i == 0 && j == 0) continue;
                            var q = c + new Vector2(i * hw, j * hd);
                            if (!PIP(e.poly, q) || DistToPolyEdge(e.poly, q) < margin) ok = false;
                        }
                    if (!ok) continue;
                    // 相互クリアランス(AABB+1.5m)
                    foreach (var pb in placedB)
                    {
                        if (cx + hw > pb.min.x - 1.5f && cx - hw < pb.max.x + 1.5f &&
                            cz + hd > pb.min.z - 1.5f && cz - hd < pb.max.z + 1.5f) { ok = false; break; }
                    }
                    if (!ok) continue;
                    // 高低差
                    float mn = float.MaxValue, mx = float.MinValue;
                    for (int i = -1; i <= 1; i++)
                        for (int j = -1; j <= 1; j++)
                        {
                            float h = Ground(cx + i * hw, cz + j * hd);
                            mn = Mathf.Min(mn, h); mx = Mathf.Max(mx, h);
                        }
                    float spread = mx - mn;
                    float score = spread * 4f + (c - anchor).magnitude * 0.10f;
                    if (score < bestScore) { bestScore = score; best = c; bestSpread = spread; }
                }
            if (bestScore == float.MaxValue) { sb.AppendLine("✗ " + nm + " 解なし(縮小か削除を検討)"); continue; }
            // 移動(バウンズ中心差分) + 接地(矩形最小地盤)
            var delta = new Vector3(best.x - b0.center.x, 0, best.y - b0.center.z);
            it.position += delta;
            var b1 = RB(it.gameObject);
            float gmn = float.MaxValue;
            for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
                gmn = Mathf.Min(gmn, Ground(b1.center.x + i * b1.extents.x, b1.center.z + j * b1.extents.z));
            it.position += new Vector3(0, (gmn - 0.12f) - b1.min.y, 0);
            placedB.Add(RB(it.gameObject));
            sb.AppendLine(nm + " -> (" + best.x.ToString("F0") + "," + best.y.ToString("F0") + ") spread=" + bestSpread.ToString("F2"));
        }
        return sb.ToString();
    }

    // ---------- Stage 5: スプラット ----------
    public static string Stage5_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -640, x1 = -180, z0 = -30, z1 = 235;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        foreach (var e in Parcels)
        {
            Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
            Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
            float vCen = Vector2.Dot(cen - gate2, vhat);
            bool isKoide = e.group.Contains("Koide");
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    if (!PIP(e.poly, p)) continue;
                    float v = Vector2.Dot(p - gate2, vhat);
                    float uAbs = Mathf.Abs(Vector2.Dot(p - gate2, uhat));
                    float bare, grass, dirt;
                    if (isKoide) { bare = 0.72f; grass = 0.08f; dirt = 0.20f; }              // 火消屋敷=調練の裸地
                    else if (v < vCen * 0.6f && uAbs < 26) { bare = 0.8f; grass = 0.06f; dirt = 0.14f; } // 前庭白洲
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.42f, 0.72f, noise); bare = 0.08f; dirt = 1f - grass - bare;
                    }
                    float sum = bare + grass + dirt;
                    for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                    A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                    changed++;
                }
        }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- QA ----------
    public static string QA_Clearance(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var sb = new System.Text.StringBuilder();
        var bld = root.transform.Find("Buildings");
        if (bld == null) return "no buildings";
        var items = new List<Transform>();
        foreach (Transform c in bld) items.Add(c);
        foreach (var it in items)
        {
            var b = RB(it.gameObject);
            // 境界距離(バウンズ四隅)
            float worst = float.MaxValue;
            for (int cx = 0; cx < 2; cx++) for (int cz = 0; cz < 2; cz++)
            {
                var p2 = new Vector2(cx == 0 ? b.min.x : b.max.x, cz == 0 ? b.min.z : b.max.z);
                float d = DistToPolyEdge(e.poly, p2);
                if (!PIP(e.poly, p2)) d = -d;
                if (d < worst) worst = d;
            }
            // 埋没/浮き
            float buried = float.MinValue, floating = float.MinValue;
            for (int cx = 0; cx < 2; cx++) for (int cz = 0; cz < 2; cz++)
            {
                float g = Ground(cx == 0 ? b.min.x : b.max.x, cz == 0 ? b.min.z : b.max.z);
                buried = Mathf.Max(buried, g - b.min.y);
                floating = Mathf.Max(floating, b.min.y - g);
            }
            sb.AppendLine(it.name + ": edgeDist=" + worst.ToString("F1") + " 埋=" + buried.ToString("F2") + " 浮=" + floating.ToString("F2"));
        }
        // 建物間
        for (int i = 0; i < items.Count; i++)
            for (int j = i + 1; j < items.Count; j++)
            {
                var bi = RB(items[i].gameObject); var bj = RB(items[j].gameObject);
                bi.Expand(1.0f);
                if (!bi.Intersects(bj)) continue;
                sb.AppendLine("⚠ AABB接触 " + items[i].name + " x " + items[j].name);
            }
        return sb.ToString();
    }

    // ---------- 一括 ----------
    public static string BuildAll()
    {
        EdoNishiTameikeBuilder.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        foreach (var e in Parcels)
        {
            sb.AppendLine(Stage1_Enclosure(e.group));
            sb.AppendLine(Stage2_Buildings(e.group));
        }
        sb.AppendLine(Stage3_Nebutocho());
        int seed = 20260809;
        foreach (var e in Parcels)
            sb.AppendLine(Stage4_Garden(e.group, seed++));
        sb.AppendLine(Stage5_Splat());
        return sb.ToString();
    }
}
