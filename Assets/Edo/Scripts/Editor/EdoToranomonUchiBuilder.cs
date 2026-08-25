// 虎ノ門内(霞が関3丁目)4敷地ビルダー (2026-08-10)
//   赤=内藤能登守(政義/日向延岡藩7万石)【上屋敷】 黄=村瀬平四郎(2500石旗本)
//   水=御小姓組 小倉鈴之進  緑=林図書助(二ノ丸御留守居/500石)
// 【典拠】区画=ユーザー下書き(EdoSketch 4色)を外堀護岸・虎御門枡形・隣接区画へスナップ。
//   考証=尾張屋版「外桜田永田町絵図」嘉永3(NDL 1286657)+万延元(NDL 8369300) IIIF実見 + Web調査:
//   - 内藤=上屋敷確定(家紋あり。万延板は「内藤右近将監」)。当主=内藤政義(井伊直弼異母弟)。
//     天正19年拝領、跡地=文科省・会計検査院・霞が関ビル(千代田区町名由来板)。譜代7万石帝鑑間。
//   - 村瀬=寛政譜に村瀬氏立項(個人未特定)。2500石=大身旗本→長屋門格。
//   - 小倉=両板では「小倉太郎助」(「鈴之進」はユーザー参照の別板か)。御小姓組=両番筋→腕木門格。
//   - 林=嘉永板「林式部少輔」万延板「林圖書頭」。二ノ丸御留守居=役高700石布衣→腕木門+番所。
// 【門の向き】切絵図文字の頭: 内藤=北東(堀端通り・虎御門側)/村瀬=北西(枡形前街路)/
//   小倉・林=北(湾曲街路)。内藤と小倉・林は背中合わせ(間に街路なし)。
// 【地形】造成ゼロ・現地形追従。区画南東は堀端通り(幅10-15m)を挟んで外堀護岸(Ishigaki_Ext_3)の内側。
// 【敷地内構成】屋敷内部絵図は未入手のため一般類型(典拠: 一般類型/当屋敷の一次史料は未確認)。
//   内藤の一次史料=明治大学博物館蔵「江戸御上屋敷絵図」(安永5年)が存在する(画像未入手)。
//   池は典拠なしのため作らない。桜川(枡形前街路沿い)は未再現。
// 各段階は既存グループがあればスキップ(手直し保護)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoToranomonUchiBuilder
{
    // ---------- assets ----------
    const string PHei = EdoAssets.Eg.DobeiCenter;
    const string PHmon = EdoAssets.Eg.Hmon;
    const string PKmon = EdoAssets.Eg.Kmon;
    const string PKabuki = EdoAssets.Eg.Kabukimon;
    const string PBansho = EdoAssets.Eg.Bansho;
    const string PKura = EdoAssets.Eg.Kura;
    const string PKnagayaL = EdoAssets.Eg.KnagayaL;
    const string PKnagayaR = EdoAssets.Eg.KnagayaR;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBigHouse = EdoAssets.VK.BigHouse;
    const string PManor = EdoAssets.VK.Manor;
    public const float ES = 1.818f;

    public class Parcel
    {
        public string group, label;
        public Vector2[] poly;
        public int front;
        public float gateT = 0.5f;
        public string gateType;      // k_mon | h_mon | kabukimon
        public int bansho;
        public int[] nagayaEdges = new int[0];
        public int[] dobeiEdges = new int[0];
        public int[] noWallEdges = new int[0];
    }

    // 境界の定義:
    //   内藤SE辺=外堀NW護岸(Ishigaki_Ext_3, 天端8.48)の天端線から10-15m内側=堀端通りの内縁。
    //   内藤NE辺=枡形前街路のSW縁(村瀬N辺と同一直線)。小倉・林S辺=内藤N境界(共有・壁は内藤持ち)。
    public static Parcel[] Parcels = new Parcel[]
    {
        new Parcel{ group="Edo_Yashiki_NaitoNoto", label="内藤能登守(延岡藩7万石)上屋敷",
            poly=new[]{
                new Vector2(289f,543f),      // 0 NE角(村瀬NW角と共有・枡形前街路の南縁)
                new Vector2(281f,509f),      // 1 村瀬SW角と共有
                new Vector2(315f,490f),      // 2 村瀬S角と共有=堀端通り内縁の北端
                new Vector2(182f,359f),      // 3 堀端通り内縁の南西端
                new Vector2(69f,417f),       // 4 S角(溜池端の道との角・辻番所北)
                new Vector2(95f,556f),       // 5 西辺の折れ
                new Vector2(66f,611f),       // 6 西街路との角
                new Vector2(73.5f,630.5f),   // 7 NW角(林SW角と共有)
                new Vector2(111.5f,615f),    // 8 林/小倉境の背割り点
                new Vector2(163.5f,598f),    // 9 小倉SE角と共有
                new Vector2(167f,592f),      // 10 枡形前街路 南縁の西端
            },
            front=2, gateT=0.18f, gateType="k_mon", bansho=2,   // 表門=堀端通り北寄り(文字の頭=北東・虎御門側)
            nagayaEdges=new[]{3,4,10},                          // 南(溜池端)・西下・枡形前街路=表長屋
            dobeiEdges=new[]{0,1,5,6,7,8,9} },
        new Parcel{ group="Edo_Yashiki_Murase", label="村瀬平四郎(2500石)",
            poly=new[]{
                new Vector2(291f,542f),      // 0 NW角
                new Vector2(339f,522f),      // 1 NE角(虎御門への道沿い)
                new Vector2(330f,504f),      // 2
                new Vector2(317f,492f),      // 3 S角
                new Vector2(281f,509f),      // 4 SW角
            },
            front=0, gateT=0.5f, gateType="h_mon", bansho=0,    // 表門=北西の枡形前街路(文字の頭=北西)
            dobeiEdges=new[]{1,2},
            noWallEdges=new[]{3,4} },                           // 南西は内藤持ち
        new Parcel{ group="Edo_Yashiki_Ogura", label="御小姓組 小倉鈴之進",
            poly=new[]{
                new Vector2(163.5f,598f),    // 0 SE角
                new Vector2(176.5f,636f),    // 1 NE角
                new Vector2(126f,655f),      // 2 NW角(林NE角と共有)
                new Vector2(111.5f,615f),    // 3 SW角(林SE角と共有)
            },
            front=1, gateT=0.65f, gateType="kabukimon", bansho=0, // 表門=北の湾曲街路(文字の頭=北)
            dobeiEdges=new[]{0,2},
            noWallEdges=new[]{3} },                             // 南は内藤持ち
        new Parcel{ group="Edo_Yashiki_HayashiZusho", label="林図書助(二ノ丸御留守居500石)",
            poly=new[]{
                new Vector2(73.5f,630.5f),   // 0 SW角
                new Vector2(84.6f,667.6f),   // 1 NW角
                new Vector2(126f,655f),      // 2 NE角
                new Vector2(111.5f,615f),    // 3 SE角
            },
            front=1, gateT=0.5f, gateType="kabukimon", bansho=1, // 表門=北の湾曲街路(布衣役の体面で番所1)
            dobeiEdges=new[]{0},
            noWallEdges=new[]{2,3} },                           // 東は小倉持ち/南は内藤持ち
    };

    // ---------- helpers ----------
    static float Ground(float x, float z) { return EdoBuild.Ground(x, z); }
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
    // EdoGeom.InwardNormal と実装差あり — 統一は裁定待ち
    public static Vector2 InwardNormal(Parcel e, int i)
    {
        var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        if (EdoGeom.SignedArea(e.poly) < 0) n = -n;
        return n;
    }
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p) => EdoGeom.DistToPolyEdge(poly, p);
    public static void Frame(Parcel e, out Vector2 gate2, out Vector2 uhat, out Vector2 vhat)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        gate2 = Vector2.Lerp(fA, fB, e.gateT);
        uhat = (fB - fA).normalized;
        vhat = InwardNormal(e, e.front);
    }
    public static Vector2 FlatNear(Parcel e, float u, float v, float W, float D, float searchR, float edgeMargin)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 anchor = gate2 + uhat * u + vhat * v;
        float bestScore = float.MaxValue; Vector2 best = anchor;
        for (float dx = -searchR; dx <= searchR; dx += 1.5f)
            for (float dz = -searchR; dz <= searchR; dz += 1.5f)
            {
                var c = anchor + new Vector2(dx, dz);
                if (!EdoGeom.PIP(e.poly, c) || DistToPolyEdge(e.poly, c) < edgeMargin) continue;
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

        GameObject mon = null; float gateHalf = 0f;
        if (e.gateType == "k_mon") mon = Place(PKmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Kmon");
        else if (e.gateType == "h_mon") mon = Place(PHmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one, monGrp, "Hmon");
        else if (e.gateType == "kabukimon") mon = Place(PKabuki, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Kabukimon");
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

        for (int i = 0; i < N; i++)
        {
            if (e.noWallEdges.Contains(i)) continue;
            Vector2 a = e.poly[i], b = e.poly[(i + 1) % N];
            Vector2 outw = -InwardNormal(e, i);
            if (i == e.front)
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_F" + i, true, 0, gate2, gateHalf + 0.6f);
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

        if (e.group.Contains("Naito"))
        {
            // 上屋敷: 表門(堀端通り h≈7.5)→崖線を上がって台地上(h≈14)に表御殿。
            // 表向=台地東縁(門正対)、奥向=台地北西、蔵列=西の裏手、厩=門脇の低平帯。
            PlaceUVFlat(e, PManor, 0, 75, 0, Vector3.one, bg, "OmoteGoten", 42, 30, 18, 10);   // facade+35.2偏心→facade≈v40(崖線上端)
            PlaceUVFlat(e, PHouse, 34, 105, 0, Vector3.one, bg, "OkuGoten", 22, 18, 12, 9);
            PlaceUVFlat(e, PSmallHouse, -2, 118, 0, Vector3.one, bg, "Daidokoro", 14, 12, 10, 8);
            PlaceUVFlat(e, PHouseB, -30, 14, 0, Vector3.one, bg, "Yakusho", 20, 16, 10, 9);    // 表役所=門内の低平帯
            PlaceUVFlat(e, PKura, 70, 120, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 10, 6);
            PlaceUVFlat(e, PKura, 78, 128, 90, Vector3.one * ES, bg, "Kura_2", 7, 5, 10, 6);
            PlaceUVFlat(e, PKura, 86, 136, 90, Vector3.one * ES, bg, "Kura_3", 7, 5, 10, 6);
            Well(e, bg, 12, 112);
            Well(e, bg, -18, 30);
            Umaya(e, bg, 28, 16);
        }
        else if (e.group.Contains("Murase"))
        {
            // 大身旗本2500石: 主屋中央・玄関正対、台所脇、蔵は裏手
            PlaceUVFlat(e, PHouse, 0, 22, 0, Vector3.one, bg, "Shuoku", 20, 16, 9, 8);
            PlaceUVFlat(e, PSmallHouse, -15, 30, 0, Vector3.one, bg, "Daidokoro", 14, 12, 8, 7);
            PlaceUVFlat(e, PKura, 15, 32, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 8, 5);
            Well(e, bg, -6, 36);
        }
        else if (e.group.Contains("Ogura"))
        {
            // 御小姓組番士: 主屋+台所+井戸の簡素な構え
            PlaceUVFlat(e, PHouse, 0, 20, 0, Vector3.one, bg, "Shuoku", 20, 16, 9, 7);
            PlaceUVFlat(e, PSmallHouse, -13, 28, 0, Vector3.one, bg, "Daidokoro", 13, 11, 8, 6);
            Well(e, bg, 8, 30);
        }
        else if (e.group.Contains("Hayashi"))
        {
            // 二ノ丸御留守居500石: 主屋+台所+蔵1+井戸
            PlaceUVFlat(e, PHouse, 0, 18, 0, Vector3.one, bg, "Shuoku", 20, 16, 9, 7);
            PlaceUVFlat(e, PSmallHouse, -13, 26, 0, Vector3.one, bg, "Daidokoro", 13, 11, 8, 6);
            PlaceUVFlat(e, PKura, 13, 30, 90, Vector3.one * ES, bg, "Kura_1", 7, 5, 7, 4.5f);
            Well(e, bg, 6, 32);
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

    // ---------- Stage 4: 庭の植栽 ----------
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Sakuras = {
        EdoAssets.JG.SakuraBig01,
        EdoAssets.JG.SakuraBig05 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JC.Azalea04,
        EdoAssets.JG.Boxwood01 };
    static string[] Rocks = {
        EdoAssets.JG.Rock01,
        EdoAssets.JG.Rock02,
        EdoAssets.JG.Rock03 };
    const string PTobi = EdoAssets.JG.TobiIshi01;
    const string PKasuga = EdoAssets.Own.KasugaLantern;
    const string PYukimi = EdoAssets.Own.YukimiLantern;

    public static string Stage4_Garden(string groupName, int seed)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var dead = new List<GameObject>();
        foreach (Transform ch in root.transform) if (ch.name == "Garden" || ch.name.Contains("/")) dead.Add(ch.gameObject);
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
            if (!EdoGeom.PIP(e.poly, p)) return false;
            float best = float.MaxValue; float bm = 7.5f;
            for (int i = 0; i < e.poly.Length; i++)
            {
                var a = e.poly[i]; var b2 = e.poly[(i + 1) % e.poly.Length];
                float dd2 = EdoGeom.DistToEdge(p, a, b2);
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
        bool isNaito = e.group.Contains("Naito");
        int nPine = isNaito ? 30 : 7;
        int placed = 0, guard = 0;
        while (placed < nPine && guard++ < 1400)
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
        {
            Vector2 skC = Vector2.zero; bool found = false;
            for (int i = 0; i < 200 && !found; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) > vCen * 1.1f && clear(p, 3f)) { skC = p; found = true; }
            }
            if (found)
                for (int i = 0; i < (isNaito ? 4 : 2); i++)
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
        int nClu = isNaito ? 3 : 1;
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
        int nShrub = isNaito ? 26 : 10;
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
        // 参道/飛石: 門 → 主建物 (内藤は崖線を上がる坂参道)
        var bld = root.transform.Find("Buildings");
        Transform main = null;
        if (bld != null) main = bld.Find("OmoteGoten") ?? bld.Find("Shuoku");
        if (main != null)
        {
            var mb = RB(main.gameObject);
            var m2 = new Vector2(mb.center.x, mb.center.z);
            Vector2 g0 = gate2 + vhat * 3.5f;
            Vector2 g1 = m2 - vhat * (isNaito ? 22f : 10f);
            Vector2 ctrl = (g0 + g1) * 0.5f + new Vector2(-vhat.y, vhat.x) * 3.2f;
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
        int nLan = isNaito ? 4 : 2;
        for (int i = 0, g3 = 0; i < nLan && g3 < 300; g3++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 0.5f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = Ground(p.x, p.y);
            string lp = (i % 2 == 0) ? PKasuga : PYukimi;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(lp) == null) lp = EdoAssets.JC.StoneBasket;
            var go = Place(lp, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, props, "Lantern_" + i);
            SeatBottom(go, y - 0.03f);
            i++;
        }
        // 邸内稲荷(北東鬼門)
        Inari(e, props, rnd);
        return "garden done: " + e.group;
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
            if (!EdoGeom.PIP(e.poly, p2) || DistToPolyEdge(e.poly, p2) < 4f) continue;
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
    public static string MoveToObb(string groupName, string childPath, float x, float z)
    {
        var root = GameObject.Find(groupName);
        var it = root.transform.Find(childPath);
        if (it == null) return "missing " + childPath;
        float mnx, mxx, mnz, mxz, mny;
        ObbFootprint(it, out mnx, out mxx, out mnz, out mxz, out mny);
        if (mnx == float.MaxValue) return "no mesh " + childPath;
        var lcC = new Vector3((mnx + mxx) / 2, mny, (mnz + mxz) / 2);
        var wC = it.TransformPoint(lcC);
        it.position += new Vector3(x - wC.x, 0, z - wC.z);
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
                    if (!EdoGeom.PIP(e.poly, p2)) d = -d;
                    edge = Mathf.Min(edge, d);
                }
            sb.AppendLine(it.name + " OBB" + (mxx - mnx).ToString("F0") + "x" + (mxz - mnz).ToString("F0")
                + " edge=" + edge.ToString("F1") + " 埋=" + buried.ToString("F2") + " 浮=" + floating.ToString("F2"));
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
        float x0 = 55, x1 = 350, z0 = 345, z1 = 680;
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
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    if (!EdoGeom.PIP(e.poly, p)) continue;
                    float v = Vector2.Dot(p - gate2, vhat);
                    float uAbs = Mathf.Abs(Vector2.Dot(p - gate2, uhat));
                    float bare, grass, dirt;
                    if (v < vCen * 0.55f && uAbs < 24) { bare = 0.8f; grass = 0.06f; dirt = 0.14f; } // 前庭白洲
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
        // 堀端通り(内藤front辺の外側〜護岸天端線)と枡形前街路を土道に
        var na = Parcels[0];
        Vector2 rgate, ruhat, rvhat; Frame(na, out rgate, out ruhat, out rvhat);
        Vector2 crestA = new Vector2(320.7f, 482.0f), crestB = new Vector2(189.3f, 352.1f);
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                bool road = false;
                // 堀端通り: front辺(2->3)の外側 かつ 天端線の内側(NW)
                var fA = na.poly[2]; var fB = na.poly[3];
                float dF = EdoGeom.DistToEdge(p, fA, fB);
                float dC = EdoGeom.DistToEdge(p, crestA, crestB);
                if (!EdoGeom.PIP(na.poly, p) && dF < 16f && dC < 16f && dF + dC < 20f) road = true;
                // 枡形前街路: 辺10->0の外側8m帯
                var sA = na.poly[10]; var sB = na.poly[0];
                float dS = EdoGeom.DistToEdge(p, sA, sB);
                if (!EdoGeom.PIP(na.poly, p) && dS < 8.5f && !EdoGeom.PIP(Parcels[2].poly, p) && !EdoGeom.PIP(Parcels[1].poly, p)) road = true;
                if (!road) continue;
                for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                A[zz, xx, 0] = 0.30f; A[zz, xx, 1] = 0.05f; A[zz, xx, 2] = 0.65f;
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
        foreach (var e in Parcels)
        {
            sb.AppendLine(Stage1_Enclosure(e.group));
            sb.AppendLine(Stage2_Buildings(e.group));
        }
        int seed = 20260810;
        foreach (var e in Parcels)
            sb.AppendLine(Stage4_Garden(e.group, seed++));
        sb.AppendLine(Stage5_Splat());
        return sb.ToString();
    }
}
