// 溜池北西の新街区3屋敷ビルダー (2026-08-09)
//   黄=松平美濃守(筑前福岡藩黒田家52万石・■=中屋敷) 約22,300坪
//   水色=水野日向守(1.8万石) 約3,900坪
//   赤=相良越前守(肥後人吉藩2.21万石) 約4,700坪
// 区画=ユーザー下書き線(EdoSketch)。内部境界(黄-水色/黄-赤/水色-赤)は道なしの共有境界。
// 地形=現地形に従い造成ゼロ(terrain-follows-present-day)。
// 門の向き=切絵図の文字の頭(考証は同日のWeb調査+尾張屋版赤坂絵図)。
// 各段階は既存グループがあればスキップ(手直し保護)。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoTameikeKitaBuilder
{
    // ---------- assets ----------
    const string PKnagayaC = EdoAssets.Eg.KnagayaC;
    const string PKnagayaL = EdoAssets.Eg.KnagayaL;
    const string PKnagayaR = EdoAssets.Eg.KnagayaR;
    const string PHei = EdoAssets.Eg.DobeiCenter;
    const string PHmon = EdoAssets.Eg.Hmon;
    const string PNmon = EdoAssets.Eg.Nagayamon;
    const string PBansho = EdoAssets.Eg.Bansho;
    const string PKura = EdoAssets.Eg.Kura;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseA = EdoAssets.VK.HouseA;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBigHouse = EdoAssets.VK.BigHouse;
    const string PManor = EdoAssets.VK.Manor;
    const float ES = 1.818f;
    const float PITCH = 7.81f;

    public class Estate
    {
        public string group, label;
        public Vector2[] poly;
        public int front;
        public float gateT = 0.5f;
        public string gateType;     // h_mon | nagayamon
        public int bansho;
        public int[] nagayaEdges;
        public int[] dobeiEdges;    // 盲長屋/築地塀。共有境界で相手が受け持つ辺はどちらにも入れない
    }

    // 表門の向き=CODH翻刻の文字の頭(考証2026-08-09):
    //   黒田=北東38.7°≈辺4(Y4Y5, 溜池・桐畑通り) / 水野・相良=南西≈西側の通り(氷川・南部坂側)
    // 門格式=『青標紙』: 上屋敷5万石以下=長屋門+出片番所。中屋敷の明文規定は未確認→長屋門類型。
    //   黒田(国持格)のみ両番所、水野(上屋敷1.8万)・相良(中屋敷2.2万)=片番所。
    // ⚠ poly の正典 = docs/Sashizu/parcels.json(CLAUDE.md 規則10 / 2026-08-26 ユーザー裁定で json採用)
    public static Estate[] Estates = new Estate[]
    {
        // 黄: 12角形。辺: 0:Y0Y1(SE) 1:Y1Y2 2:Y2Y3(E) 3:Y3Y4(E=溜池道) 4:Y4Y5(NE=表) 5:Y5Y6 6:Y6Y7(N)
        //     7:Y7Y8+8:Y8Y9(内部境界:赤・水色の東) 9:Y9Y10(内部境界:水色の南) 10:Y10Y11(SW) 11:Y11Y0(S)
        // 2026-08-26 json採用で頂点+1(index8 に (-584.90,410.08) 挿入 — 旧辺7 (-619.4,536.3)→(-555.8,303.6)
        //   上の点=同一直線)、辺indexを再採番: 旧辺7→辺7+辺8 / 旧辺8→9 / 旧辺9→10 / 旧辺10→11
        new Estate{ group="Edo_Yashiki_MatsudairaMino", label="松平美濃守=黒田斉溥(福岡藩47.3万石)中屋敷",
            poly=EdoParcels.Get("tameikekita_estates_0"),
            front=4, gateT=0.45f, gateType="nagayamon", bansho=2,
            nagayaEdges=new[]{3,5}, dobeiEdges=new[]{0,1,2,6,7,8,9,10,11} },
        // 水色: 4角形。辺: 0:C0C1(W=表・街路) 1:C1C2(N 内部境界:相良側→水野が受け持つ) 2:C2C3(E:黄が受け持つ) 3:C3C0(S:黄が受け持つ)
        new Estate{ group="Edo_Yashiki_MizunoHyuga", label="水野日向守=水野勝進(結城藩1.8万石)上屋敷",
            poly=EdoParcels.Get("tameikekita_estates_1"),
            front=0, gateT=0.5f, gateType="nagayamon", bansho=1,
            nagayaEdges=new int[0], dobeiEdges=new[]{1} },
        // 赤: 5角形。辺: 0:R0R1(W=表) 1:R1R2(NW) 2:R2R3(N) 3:R3R4(E:黄が受け持つ) 4:R4R0(S:水野が受け持つ)
        new Estate{ group="Edo_Yashiki_SagaraEchizen", label="相良越前守=相良頼基(人吉藩2.21万石)中屋敷",
            poly=EdoParcels.Get("tameikekita_estates_2"),
            front=0, gateT=0.5f, gateType="nagayamon", bansho=1,
            nagayaEdges=new[]{1,2}, dobeiEdges=new int[0] },
    };

    // ---------- helpers ----------
    public static Terrain T()
    {
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy) return t;
        throw new Exception("no active terrain");
    }
    public static float Ground(float x, float z) => EdoBuild.Ground(x, z);
    public static float PadAt(Estate e, Vector2 p) { return Ground(p.x, p.y); } // 造成ゼロ=地形追従

    static GameObject Load(string path)
    {
        var a = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (a == null) throw new Exception("asset not found: " + path);
        return a;
    }
    public static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = scale;
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
    public static Bounds RB(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }
    public static void SeatBottom(GameObject go, float y)
    {
        var b = RB(go);
        go.transform.position += new Vector3(0, y - b.min.y, 0);
    }
    static void ProjExtent(GameObject go, Vector2 axis, float yMin, float yMax, Func<string, bool> nameOk, out float mn, out float mx)
    {
        mn = float.MaxValue; mx = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (nameOk != null && !nameOk(mf.gameObject.name)) continue;
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                var w = mf.transform.TransformPoint(verts[i]);
                if (w.y < yMin || w.y > yMax) continue;
                float p = w.x * axis.x + w.z * axis.y;
                if (p < mn) mn = p; if (p > mx) mx = p;
            }
        }
    }
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
    public static Vector2 InwardNormal(Estate e, int i)
    {
        var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        if (EdoGeom.SignedArea(e.poly) < 0) n = -n;
        return n;
    }
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p) => EdoGeom.DistToPolyEdge(poly, p);

    // ---------- Stage 0: backup ----------
    public static string Stage0_Backup()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        var all = td.GetHeights(0, 0, res, res);
        var bytes = new byte[res * res * 4];
        Buffer.BlockCopy(all, 0, bytes, 0, bytes.Length);
        string p = "Library/EdoBackup_20260809_tameikekita_height.bin";
        File.WriteAllBytes(p, bytes);
        // alphamap も (splat 巻き戻し用)
        int ares = td.alphamapResolution; int L = td.alphamapLayers;
        var A = td.GetAlphamaps(0, 0, ares, ares);
        var ab = new byte[ares * ares * L * 4];
        Buffer.BlockCopy(A, 0, ab, 0, ab.Length);
        string pa = "Library/EdoBackup_20260809_tameikekita_alpha.bin";
        File.WriteAllBytes(pa, ab);
        return "saved " + p + " res=" + res + " / " + pa + " ares=" + ares + " L=" + L;
    }

    // ---------- nagaya run (地形追従) ----------
    public static List<GameObject> NagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, Vector2 gapC, float gapHalf, string prefix)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        Vector2 sA = A, sB = B; Vector2 rdir = dir;
        if (Vector2.Dot(dir, negRight) < 0) { sA = B; sB = A; rdir = -dir; }
        float span = len - 4.4f - 3.7f;
        int n = Mathf.Max(2, Mathf.CeilToInt(span / PITCH) + 1);
        float pitchRun = span / (n - 1);
        float t0 = 4.4f;
        var kept = new List<float>();
        for (int k = 0; k < n; k++)
        {
            float tk = t0 + pitchRun * k;
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - sA, rdir);
                float skipLo = gT - gapHalf - 3.9f, skipHi = gT + gapHalf + 3.9f;
                if (tk + 3.6f > skipLo && tk - 4.3f < skipHi) continue;
            }
            kept.Add(tk);
        }
        for (int k = 0; k < kept.Count; k++)
        {
            float tk = kept[k];
            bool lowEnd = (k == 0) || (kept[k] - kept[k - 1] > pitchRun * 1.5f);
            bool highEnd = (k == kept.Count - 1) || (kept[k + 1] - kept[k] > pitchRun * 1.5f);
            string path = lowEnd ? PKnagayaL : (highEnd ? PKnagayaR : PKnagayaC);
            if (lowEnd && highEnd) path = PKnagayaC;
            var c2 = sA + rdir * tk;
            float g0 = Ground(c2.x - rdir.x * 4f, c2.y - rdir.y * 4f);
            float g1 = Ground(c2.x + rdir.x * 4f, c2.y + rdir.y * 4f);
            float gc = Ground(c2.x, c2.y);
            float pieceBase = Mathf.Min(g0, Mathf.Min(g1, gc));
            var go = Place(path, new Vector3(c2.x, pieceBase, c2.y), psi, new Vector3(ES, ES, ES), parent, prefix + "_" + k);
            SeatBottom(go, pieceBase - 0.10f);
            made.Add(go);
        }
        if (made.Count > 0) VerifyFlipOutward(made, outward, prefix);
        return made;
    }
    static void VerifyFlipOutward(List<GameObject> mods, Vector2 outward, string prefix)
    {
        var probe = mods[Mathf.Min(1, mods.Count - 1)];
        float mn, mx;
        ProjExtent(probe, outward, -100, 1000, nm => nm.ToLower().Contains("namako"), out mn, out mx);
        if (mn == float.MaxValue) return;
        var c = RB(probe).center; float cp = c.x * outward.x + c.z * outward.y;
        if (mx < cp)
        {
            foreach (var go in mods)
            {
                var b0 = RB(go);
                go.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b1 = RB(go);
                go.transform.position += b0.center - b1.center;
            }
            Debug.LogWarning(prefix + ": namako was inward -> flipped 180");
        }
    }

    // ---------- dobei run (表裏ペア・地形追従) ----------
    public static List<GameObject> DobeiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / 2.982f));
        float pitch = len / n;
        float sx = pitch / 1.6447f;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        for (int k = 0; k < n; k++)
        {
            var c2 = A + dir * (pitch * (k + 0.5f));
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - A, dir);
                if (Mathf.Abs(pitch * (k + 0.5f) - gT) < gapHalf + pitch * 0.5f - 0.01f) continue;
            }
            float g1 = Ground(c2.x - dir.x * pitch * 0.5f, c2.y - dir.y * pitch * 0.5f);
            float g2 = Ground(c2.x + dir.x * pitch * 0.5f, c2.y + dir.y * pitch * 0.5f);
            float baseY = Mathf.Max(g1, g2);
            for (int side = 0; side < 2; side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var off2 = outward * (side == 0 ? 0.0f : -0.2f);
                var go = Place(PHei, Vector3.zero, ry, new Vector3(sx, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                go.transform.localScale = new Vector3(sx, ES, ES);
                var b = RB(go);
                var target = new Vector3(c2.x + off2.x, 0, c2.y + off2.y);
                go.transform.position += new Vector3(target.x - b.center.x, 0, target.z - b.center.z);
                SeatBottom(go, baseY - 0.10f);
                made.Add(go);
            }
        }
        return made;
    }

    // ---------- Stage 2: enclosure ----------
    public static string Stage2_Enclosure(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Kakoi") != null) return "SKIP: " + e.group + "/Kakoi exists";
        var kak = Group(e.group, "Kakoi");
        var monGrp = Group(e.group, "Omotemon");
        int N = e.poly.Length;
        var sb = new System.Text.StringBuilder();

        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 fin = InwardNormal(e, e.front);
        Vector2 fout = -fin;
        float basePad = PadAt(e, gate2);

        float gateHalf; GameObject mon;
        float psiIn = Mathf.Atan2(fin.x, fin.y) * Mathf.Rad2Deg;
        if (e.gateType == "nagayamon")
            mon = Place(PNmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Nagayamon");
        else
            mon = Place(PHmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one, monGrp, "Hmon");
        SeatBottom(mon, basePad - 0.05f);
        var mb = RB(mon);
        mon.transform.position += new Vector3(gate2.x - mb.center.x, 0, gate2.y - mb.center.z);
        Vector2 runAxis = (fB - fA).normalized;
        float wmn, wmx;
        ProjExtent(mon, runAxis, basePad + 0.5f, basePad + 4.5f, null, out wmn, out wmx);
        float monHalf = (wmx - wmn) * 0.5f;
        gateHalf = monHalf;
        sb.AppendLine("gate " + e.gateType + " width=" + (wmx - wmn).ToString("F2"));
        float kmn, kmx;
        ProjExtent(mon, fout, -100, 1000, nm => nm.ToLower().Contains("kagami"), out kmn, out kmx);
        if (kmn != float.MaxValue)
        {
            var mc = RB(mon).center; float cp = mc.x * fout.x + mc.z * fout.y;
            if ((kmn + kmx) * 0.5f > cp)
            {
                mon.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b2 = RB(mon);
                mon.transform.position += new Vector3(gate2.x - b2.center.x, 0, gate2.y - b2.center.z);
                sb.AppendLine("gate flipped (kagami was outward)");
            }
        }
        for (int i = 0; i < e.bansho; i++)
        {
            float side = (e.bansho == 1) ? 1f : (i == 0 ? 1f : -1f);
            float du = monHalf + 3.2f;
            Vector2 bp = gate2 + runAxis * (side * du) + fout * 0.5f;
            var ban = Place(PBansho, new Vector3(bp.x, basePad, bp.y), psiIn + 180f, Vector3.one * ES, monGrp, "Bansho_" + i);
            SeatBottom(ban, basePad - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * fout.x + f3.z * fout.y < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg, 0);
        }

        for (int i = 0; i < N; i++)
        {
            Vector2 a = e.poly[i], b = e.poly[(i + 1) % N];
            Vector2 outw = -InwardNormal(e, i);
            if (i == e.front)
                NagayaRun(kak, a, b, outw, gate2, gateHalf, "NG_F" + i);
            else if (e.nagayaEdges.Contains(i))
                NagayaRun(kak, a, b, outw, Vector2.zero, -1, "NG_" + i);
            else if (e.dobeiEdges.Contains(i))
                DobeiRun(kak, a, b, outw, "Hei_" + i, Vector2.zero, -1);
        }
        SceneView.RepaintAll();
        return sb.ToString() + "enclosure done: " + e.group;
    }

    // ---------- Stage 3: buildings ----------
    public static GameObject PlaceUV(Estate e, string path, float u, float v, float faceYawOffset, Vector3 scale, Transform parent, string name)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized;
        Vector2 vhat = InwardNormal(e, e.front);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float streetYaw = Mathf.Atan2(-vhat.x, -vhat.y) * Mathf.Rad2Deg;
        float y = PadAt(e, p);
        var go = Place(path, new Vector3(p.x, y, p.y), streetYaw + faceYawOffset, scale, parent, name);
        SeatBottom(go, y - 0.12f);
        return go;
    }

    public static string Stage3_Buildings(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Buildings") != null) return "SKIP: Buildings exists";
        var bg = Group(e.group, "Buildings");
        if (e.group.Contains("Mino"))
        {
            // 国持大藩の中屋敷: 表御殿(Manor)→奥御殿を門から奥の台地へ連続、台所、蔵3(搬入=溜池道側)、厩+中間長屋
            // 門=NE辺(溜池・桐畑通り)。奥(v+)=南西の台地へ登る。台地の平坦パッチ(u0,v103,Δ0.6m)に御殿。
            // 確定値(2026-08-09 実配置。斜面の浮き/埋まりを実測で収束させた後の座標)
            PlaceUV(e, PManor, 0, 103, 0, Vector3.one, bg, "OmoteGoten");
            PlaceUV(e, PHouseA, -32, 142, 0, Vector3.one, bg, "OkuGoten");
            PlaceUV(e, PHouse, -33, 100, 0, Vector3.one, bg, "OkuGoten2");
            PlaceUV(e, PSmallHouse, 41, 104, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, -72, 38, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, -78, 48, 90, Vector3.one * ES, bg, "Kura_2");
            PlaceUV(e, PKura, -84, 58, 90, Vector3.one * ES, bg, "Kura_3");
            Well(e, bg, 48, 112);
            Well(e, bg, -47, 131);
            Umaya(e, bg, -65, 25);
            Umaya(e, bg, -88, 26);
        }
        else if (e.group.Contains("Mizuno"))
        {
            PlaceUV(e, PBigHouse, -8, 46, 0, Vector3.one, bg, "OmoteGoten");
            PlaceUV(e, PHouse, 12, 68, 0, Vector3.one, bg, "OkuGoten");
            PlaceUV(e, PSmallHouse, -28, 60, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, 26, 82, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, 34, 74, 90, Vector3.one * ES, bg, "Kura_2");
            Well(e, bg, 2, 62);
            Umaya(e, bg, -30, 18);
        }
        else
        {
            PlaceUV(e, PBigHouse, -11, 46, 0, Vector3.one, bg, "OmoteGoten");
            PlaceUV(e, PHouse, -18, 72, 0, Vector3.one, bg, "OkuGoten");
            PlaceUV(e, PSmallHouse, 3, 78, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, 24, 78, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, 32, 70, 90, Vector3.one * ES, bg, "Kura_2");
            Well(e, bg, -2, 60);
            Umaya(e, bg, -34, 24);
        }
        return "buildings done: " + e.group;
    }

    static void Well(Estate e, Transform parent, float u, float v)
    {
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized; Vector2 vhat = InwardNormal(e, e.front);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float y = PadAt(e, p);
        g.transform.position = new Vector3(p.x, y, p.y);
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.3f, 0.35f, 1.3f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.38f, 0.28f, 0.18f);
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
        Undo.RegisterCreatedObjectUndo(g, "well");
    }

    static void Umaya(Estate e, Transform parent, float u, float v)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized; Vector2 vhat = InwardNormal(e, e.front);
        Vector2 c = gate2 + uhat * u + vhat * v;
        float y = PadAt(e, c);
        float psi = Mathf.Atan2(vhat.x, vhat.y) * Mathf.Rad2Deg;
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var g = new GameObject("Umaya");
        g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        var m1 = Place(PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = Place(PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        Vector2 p1 = c - negRight * (PITCH * 0.5f);
        Vector2 p2 = c + negRight * (PITCH * 0.5f);
        m1.transform.position = new Vector3(p1.x, y, p1.y);
        m2.transform.position = new Vector3(p2.x, y, p2.y);
        SeatBottom(m1, y - 0.10f); SeatBottom(m2, y - 0.10f);
    }

    // ---------- Stage 4: garden ----------
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    // 季節=非春のため夏緑の桜を使う(ユーザー指示 2026-08-09: 開花木は不可)
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
    const string PBamboo = EdoAssets.JG.BambooBig01;

    public static string Stage4_Garden(string groupName, int seed)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        var dead = new List<GameObject>();
        foreach (Transform ch in root.transform) if (ch.name == "Garden" || ch.name.StartsWith("Garden/")) dead.Add(ch.gameObject);
        foreach (var d in dead) UnityEngine.Object.DestroyImmediate(d);
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
        Func<Vector2, float> edgeMargin = p =>
        {
            float best = float.MaxValue; float bm = 7.5f;
            for (int i = 0; i < e.poly.Length; i++)
            {
                var a = e.poly[i]; var b2 = e.poly[(i + 1) % e.poly.Length];
                var d = b2 - a; float len = d.magnitude; d /= len;
                float tcl = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
                float dd = (p - (a + d * tcl)).magnitude;
                if (dd < best) { best = dd; bm = (i == e.front || e.nagayaEdges.Contains(i)) ? 8.5f : 3.0f; }
            }
            return bm;
        };
        Func<Vector2, float, bool> clear = (p, m) =>
        {
            if (!EdoGeom.PIP(e.poly, p)) return false;
            if (DistToPolyEdge(e.poly, p) < edgeMargin(p)) return false;
            if (InPond(e, p, 4f)) return false;
            foreach (var b in obs)
                if (p.x > b.min.x - m && p.x < b.max.x + m && p.y > b.min.z - m && p.y < b.max.z + m) return false;
            return true;
        };
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 vhat = InwardNormal(e, e.front);
        Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
        float vCen = Vector2.Dot(cen - gate2, vhat);
        var bb = new Bounds(new Vector3(cen.x, 0, cen.y), Vector3.zero);
        foreach (var p in e.poly) bb.Encapsulate(new Vector3(p.x, 0, p.y));
        bool big = e.group.Contains("Mino");
        int nPine = big ? 42 : 16;
        int placed = 0, guard = 0;
        while (placed < nPine && guard++ < 2500)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            float v = Vector2.Dot(p - gate2, vhat);
            if (v < vCen * 0.7f && rnd.NextDouble() < 0.75) continue;
            if (!clear(p, 2.5f)) continue;
            float y = PadAt(e, p);
            float sc = 1.65f * (0.9f + 0.5f * (float)rnd.NextDouble());
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Pine_" + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        // 桜の群れ
        int nSakuraGrove = big ? 2 : 1;
        for (int gv = 0; gv < nSakuraGrove; gv++)
        {
            Vector2 skC = Vector2.zero; bool found = false;
            for (int i = 0; i < 300 && !found; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) > vCen * 1.15f && clear(p, 3f)) { skC = p; found = true; }
            }
            if (found)
                for (int i = 0; i < 3 + (big ? 2 : 0); i++)
                {
                    var p = skC + new Vector2((float)rnd.NextDouble() * 10 - 5, (float)rnd.NextDouble() * 10 - 5);
                    if (!clear(p, 2f)) continue;
                    float y = PadAt(e, p);
                    float sc = 1.4f * (0.9f + 0.4f * (float)rnd.NextDouble());
                    var go = Place(Sakuras[rnd.Next(Sakuras.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Sakura_" + gv + "_" + i);
                    SeatBottom(go, y - 0.05f);
                }
        }
        // 竹叢 (奥の隅)
        if (AssetDatabase.LoadAssetAtPath<GameObject>(PBamboo) != null)
        {
            Vector2 bkC = Vector2.zero; bool bkF = false;
            for (int i = 0; i < 300 && !bkF; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) > vCen * 1.3f && clear(p, 3f)) { bkC = p; bkF = true; }
            }
            if (bkF)
                for (int i = 0; i < (big ? 8 : 5); i++)
                {
                    var p = bkC + new Vector2((float)rnd.NextDouble() * 7 - 3.5f, (float)rnd.NextDouble() * 7 - 3.5f);
                    if (!clear(p, 1f)) continue;
                    float y = PadAt(e, p);
                    var go = Place(PBamboo, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.85f + 0.4f * (float)rnd.NextDouble())), trees, "Bamboo_" + i);
                    SeatBottom(go, y - 0.05f);
                }
        }
        // 岩組
        int nClu = big ? 3 : 2;
        for (int cIdx = 0; cIdx < nClu; cIdx++)
        {
            for (int i = 0; i < 250; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) < vCen) continue;
                if (!clear(p, 2f)) continue;
                float y = PadAt(e, p);
                int cnt = 3 + rnd.Next(2);
                for (int r = 0; r < cnt; r++)
                {
                    var rp = p + new Vector2((float)rnd.NextDouble() * 3.4f - 1.7f, (float)rnd.NextDouble() * 3.4f - 1.7f);
                    float rs = (r == 0 ? 3.2f : 1.6f) * (0.8f + 0.5f * (float)rnd.NextDouble());
                    var rg = Place(Rocks[rnd.Next(Rocks.Length)], new Vector3(rp.x, y, rp.y), (float)rnd.NextDouble() * 360f, Vector3.one * rs, rocks, "Iwa_" + cIdx + "_" + r);
                    SeatBottom(rg, PadAt(e, rp) - 0.25f);
                }
                break;
            }
        }
        // ツツジ・下草
        int nShrub = big ? 40 : 16;
        for (int i = 0, g2 = 0; i < nShrub && g2 < 1500; g2++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (!clear(p, 1.2f)) continue;
            float y = PadAt(e, p);
            float sc = 0.9f + 0.7f * (float)rnd.NextDouble();
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, shrubs, "Shrub_" + i);
            SeatBottom(go, y - 0.04f);
            i++;
        }
        // 飛石: 門→玄関
        var bld = root.transform.Find("Buildings");
        Transform main = bld != null ? (bld.Find("Shuoku") ?? bld.Find("OmoteGoten")) : null;
        if (main != null)
        {
            var m2 = new Vector2(main.position.x, main.position.z);
            Vector2 g0 = gate2 + vhat * 3.5f;
            Vector2 g1 = m2 - vhat * 9f;
            Vector2 ctrl = (g0 + g1) * 0.5f + new Vector2(-vhat.y, vhat.x) * 3.2f;
            int steps = Mathf.Max(4, Mathf.RoundToInt((g1 - g0).magnitude / 2.4f));
            for (int i = 0; i <= steps; i++)
            {
                float tt = (float)i / steps;
                Vector2 p = (1 - tt) * (1 - tt) * g0 + 2 * (1 - tt) * tt * ctrl + tt * tt * g1;
                p += new Vector2((float)rnd.NextDouble() * 0.5f - 0.25f, (float)rnd.NextDouble() * 0.5f - 0.25f);
                float y = PadAt(e, p);
                var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, path, "Tobi_" + i);
                SeatBottom(go, y + 0.02f);
            }
        }
        // 灯籠
        int nLan = big ? 5 : 3;
        for (int i = 0, g3 = 0; i < nLan && g3 < 600; g3++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 0.8f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = PadAt(e, p);
            string lp = (i % 2 == 0) ? PKasuga : PYukimi;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(lp) == null) lp = EdoAssets.JC.StoneBasket;
            var go = Place(lp, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, props, "Lantern_" + i);
            SeatBottom(go, y - 0.03f);
            i++;
        }
        Inari(e, props, rnd);
        return "garden done: " + e.group;
    }

    // 鴨場の大池。【典拠: 黒田赤坂中屋敷に鴨猟用の大池が明治初期まで残存した記録(福岡市博物館アーカイブズ
    // No.274ほか)。存在は記録ベース、位置・形状は北西の谷地形からの推定】
    public static Vector2[] MinoPondOutline = null;
    static bool InPond(Estate e, Vector2 p, float margin)
    {
        if (!e.group.Contains("Mino")) return false;
        if (MinoPondOutline == null)
        {
            var go = GameObject.Find("Water_KurodaKamoba");
            if (go != null)
            {
                var wb = go.GetComponent<WaterBody>();
                if (wb != null && wb.outline != null && wb.outline.Count >= 3)
                    MinoPondOutline = wb.outline.Select(v => new Vector2(v.x, v.z)).ToArray();
            }
        }
        if (MinoPondOutline == null) return false;
        if (EdoGeom.PIP(MinoPondOutline, p)) return true;
        return DistToPolyEdge(MinoPondOutline, p) < margin;
    }

    // 鴨場の大池を WaterBaker で掘る(建物の後・庭の前に呼ぶ)
    // ※ユーザー指示(2026-08-09)で一旦保留。掘った池は RestoreAndDelete で埋め戻し済み。
    //   再開時はこの関数を呼ぶだけでよい(記録: 黒田赤坂中屋敷に鴨場の大池が明治初期まで残存)。
    public static string BuildMinoPond()
    {
        if (GameObject.Find("Water_KurodaKamoba") != null) return "SKIP: Water_KurodaKamoba exists";
        var e = Estates[0];
        // 北西の低地(谷)に長軸を NE辺と平行にした楕円+ジッタ。中心はローカル探索で最低地点へ寄せる
        Vector2 c0 = new Vector2(-537f, 474f);
        Vector2 best = c0; float bestG = float.MaxValue;
        for (float du = -14; du <= 14; du += 4)
            for (float dv = -14; dv <= 14; dv += 4)
            {
                var p = c0 + new Vector2(du, dv);
                if (!EdoGeom.PIP(e.poly, p) || DistToPolyEdge(e.poly, p) < 38f) continue;
                float g = Ground(p.x, p.y);
                if (g < bestG) { bestG = g; best = p; }
            }
        Vector2 axA = new Vector2(-0.7772f, 0.6289f);   // NE辺と平行
        Vector2 axB = new Vector2(-0.6289f, -0.7772f);  // 敷地奥向き
        float A = 32f, B = 16f;
        var rndp = new System.Random(20260809);
        var outline = new List<Vector3>();
        int NP = 15;
        for (int i = 0; i < NP; i++)
        {
            float th = i * Mathf.PI * 2f / NP;
            float jr = 0.85f + 0.3f * (float)rndp.NextDouble();
            Vector2 p = best + axA * (Mathf.Cos(th) * A * jr) + axB * (Mathf.Sin(th) * B * jr);
            outline.Add(new Vector3(p.x, Ground(p.x, p.y), p.y));
        }
        var wb = WaterBaker.Create(outline, 2.0f);
        wb.gameObject.name = "Water_KurodaKamoba";
        MinoPondOutline = outline.Select(v => new Vector2(v.x, v.z)).ToArray();
        return "pond carved at (" + best.x.ToString("F0") + "," + best.y.ToString("F0") + ") waterY=" + wb.waterY.ToString("F2");
    }

    static void Inari(Estate e, Transform parent, System.Random rnd)
    {
        Vector2 best = Vector2.zero; float bestScore = float.MinValue;
        var bbMin = new Vector2(e.poly.Min(p => p.x), e.poly.Min(p => p.y));
        var bbMax = new Vector2(e.poly.Max(p => p.x), e.poly.Max(p => p.y));
        for (int i = 0; i < 400; i++)
        {
            var p2 = new Vector2(Mathf.Lerp(bbMin.x, bbMax.x, (float)rnd.NextDouble()), Mathf.Lerp(bbMin.y, bbMax.y, (float)rnd.NextDouble()));
            if (!EdoGeom.PIP(e.poly, p2) || DistToPolyEdge(e.poly, p2) < 5f) continue;
            if (InPond(e, p2, 5f)) continue;
            float score = p2.x + p2.y;
            if (score > bestScore) { bestScore = score; best = p2; }
        }
        if (bestScore == float.MinValue) return;
        float y = PadAt(e, best);
        var g = new GameObject("Inari");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(best.x, y, best.y);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        var shu = new Material(Shader.Find("Universal Render Pipeline/Lit")); shu.color = new Color(0.78f, 0.15f, 0.08f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
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
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.30f, 0.18f);
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

    // ---------- Stage 5: splat ----------
    public static string Stage5_Splat()
    {
        var t = T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -770, x1 = -385, z0 = 85, z1 = 555;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        foreach (var e in Estates)
        {
            int N = e.poly.Length;
            Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
            Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
            Vector2 vhat = InwardNormal(e, e.front);
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
                    float uAbs = Mathf.Abs(Vector2.Dot(p - gate2, (fB - fA).normalized));
                    float bare, grass, dirt;
                    float vBare = e.group.Contains("Mino") ? 42f : vCen * 0.55f;
                    float uBare = e.group.Contains("Mino") ? 48f : 30f;
                    if (InPond(e, p, 10f)) { grass = 0.75f; bare = 0.05f; dirt = 0.20f; } // 鴨場の岸は草地
                    else if (v < vBare && uAbs < uBare) { bare = 0.8f; grass = 0.06f; dirt = 0.14f; }
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
        var e = Estates.First(x => x.group == groupName);
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
            float coarse = float.MaxValue;
            for (int cx = 0; cx < 2; cx++) for (int cz = 0; cz < 2; cz++)
            {
                var p2 = new Vector2(cx == 0 ? b.min.x : b.max.x, cz == 0 ? b.min.z : b.max.z);
                float d = DistToPolyEdge(e.poly, p2);
                if (!EdoGeom.PIP(e.poly, p2)) d = -d;
                if (d < coarse) coarse = d;
            }
            if (coarse > 1.0f) continue;
            float worst = float.MaxValue;
            foreach (var p in SamplePts(it))
            {
                var p2 = new Vector2(p.x, p.z);
                float d = DistToPolyEdge(e.poly, p2);
                if (!EdoGeom.PIP(e.poly, p2)) d = -d;
                if (d < worst) worst = d;
            }
            if (worst < 1.0f) sb.AppendLine("⚠ " + it.name + " boundary dist=" + worst.ToString("F2"));
        }
        for (int i = 0; i < items.Count; i++)
            for (int j = i + 1; j < items.Count; j++)
            {
                var bi = RB(items[i].gameObject); var bj = RB(items[j].gameObject);
                bi.Expand(1.0f);
                if (!bi.Intersects(bj)) continue;
                float md = MeshMinDist(items[i], items[j]);
                if (md < 0.5f) sb.AppendLine("⚠ " + items[i].name + " x " + items[j].name + " meshDist=" + md.ToString("F2"));
            }
        return sb.Length == 0 ? "QA clean: " + groupName : sb.ToString();
    }
    static float MeshMinDist(Transform a, Transform b)
    {
        var pa = SamplePts(a); var pb = SamplePts(b);
        float m = float.MaxValue;
        foreach (var p in pa) foreach (var q in pb) { float d = Vector3.Distance(p, q); if (d < m) m = d; }
        return m;
    }
    static List<Vector3> SamplePts(Transform t)
    {
        var pts = new List<Vector3>();
        var mfs = t.GetComponentsInChildren<MeshFilter>();
        int perFilter = Mathf.Max(4, 240 / Mathf.Max(1, mfs.Length));
        foreach (var mf in mfs)
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var vts = mesh.vertices;
            for (int i = 0; i < vts.Length; i += Mathf.Max(1, vts.Length / perFilter)) pts.Add(mf.transform.TransformPoint(vts[i]));
        }
        if (pts.Count > 300)
        {
            var thin = new List<Vector3>();
            for (int i = 0; i < pts.Count; i += pts.Count / 300 + 1) thin.Add(pts[i]);
            return thin;
        }
        return pts;
    }

    // ---------- gate junction fix ----------
    public static string FixGateJunctions(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var sb = new System.Text.StringBuilder();
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 runAxis = (fB - fA).normalized;
        Vector2 fout = -InwardNormal(e, e.front);
        var monGrp = root.transform.Find("Omotemon");
        var kak = root.transform.Find("Kakoi");
        if (monGrp == null || kak == null) return "missing groups";
        Transform mon = null; var banshos = new List<Transform>();
        foreach (Transform c in monGrp)
        {
            if (c.name.StartsWith("Bansho")) banshos.Add(c);
            else mon = c;
        }
        if (mon == null) return "no mon";
        float basePad = PadAt(e, Vector2.Lerp(fA, fB, e.gateT));
        float gMn, gMx; ProjExtent(mon.gameObject, runAxis, basePad + 0.5f, basePad + 4.5f, null, out gMn, out gMx);
        float gFmn, gFmx; ProjExtent(mon.gameObject, fout, basePad + 0.2f, basePad + 4.5f, null, out gFmn, out gFmx);
        float banEdgeLo = gMn, banEdgeHi = gMx;
        for (int i = 0; i < banshos.Count; i++)
        {
            var ban = banshos[i];
            float side = (banshos.Count == 1) ? 1f : (i == 0 ? 1f : -1f);
            float bMn, bMx; ProjExtent(ban.gameObject, runAxis, basePad + 0.2f, basePad + 4f, null, out bMn, out bMx);
            float bFmn, bFmx; ProjExtent(ban.gameObject, fout, basePad + 0.2f, basePad + 4f, null, out bFmn, out bFmx);
            float shiftU = side > 0 ? (gMx - 0.15f) - bMn : (gMn + 0.15f) - bMx;
            float proud = e.gateType == "nagayamon" ? 1.7f : 0f;
            float shiftV = (gFmx + proud) - bFmx;
            ban.position += new Vector3(runAxis.x * shiftU + fout.x * shiftV, 0, runAxis.y * shiftU + fout.y * shiftV);
            SeatBottom(ban.gameObject, basePad - 0.05f);
            float nMn, nMx; ProjExtent(ban.gameObject, runAxis, basePad + 0.2f, basePad + 4f, null, out nMn, out nMx);
            if (side > 0) banEdgeHi = Mathf.Max(banEdgeHi, nMx); else banEdgeLo = Mathf.Min(banEdgeLo, nMn);
            sb.AppendLine("bansho" + i + " side=" + side + " shiftU=" + shiftU.ToString("F2") + " shiftV=" + shiftV.ToString("F2"));
        }
        var lows = new List<Transform>(); var highs = new List<Transform>();
        float gateC = (gMn + gMx) * 0.5f;
        foreach (Transform c in kak)
        {
            if (!c.name.StartsWith("NG_F" + e.front)) continue;
            float mMn, mMx; ProjExtent(c.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx);
            if ((mMn + mMx) * 0.5f < gateC) lows.Add(c); else highs.Add(c);
        }
        if (lows.Count > 0)
        {
            float best = float.MinValue;
            foreach (var m in lows) { float mMn, mMx; ProjExtent(m.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx); if (mMx > best) best = mMx; }
            float shift = (banEdgeLo + 0.2f) - best;
            foreach (var m in lows) m.position += new Vector3(runAxis.x * shift, 0, runAxis.y * shift);
            sb.AppendLine("low subrun n=" + lows.Count + " shift=" + shift.ToString("F2"));
        }
        if (highs.Count > 0)
        {
            float best = float.MaxValue;
            foreach (var m in highs) { float mMn, mMx; ProjExtent(m.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx); if (mMn < best) best = mMn; }
            float shift = (banEdgeHi - 0.2f) - best;
            foreach (var m in highs) m.position += new Vector3(runAxis.x * shift, 0, runAxis.y * shift);
            sb.AppendLine("high subrun n=" + highs.Count + " shift=" + shift.ToString("F2"));
        }
        return sb.ToString();
    }

    public static string CloseFrontLine(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 runAxis = (fB - fA).normalized;
        float len = (fB - fA).magnitude;
        Vector2 fout = -InwardNormal(e, e.front);
        var kak = root.transform.Find("Kakoi");
        var monGrp = root.transform.Find("Omotemon");
        float basePad = PadAt(e, Vector2.Lerp(fA, fB, e.gateT));
        var cover = new List<(float lo, float hi)>();
        var sb = new System.Text.StringBuilder();
        foreach (Transform c in monGrp)
        {
            float mn, mx; ProjExtent(c.gameObject, runAxis, basePad + 0.4f, basePad + 4.2f, null, out mn, out mx);
            if (mn == float.MaxValue) continue;
            float off = Vector2.Dot(fA, runAxis);
            cover.Add((mn - off, mx - off));
        }
        var toKill = new List<GameObject>();
        foreach (Transform c in kak)
        {
            if (!c.name.StartsWith("NG_F" + e.front)) continue;
            float mn, mx; ProjExtent(c.gameObject, runAxis, basePad + 0.4f, basePad + 4.2f, null, out mn, out mx);
            if (mn == float.MaxValue) continue;
            float off = Vector2.Dot(fA, runAxis);
            float lo = mn - off, hi = mx - off;
            int prevE = (e.front + N - 1) % N, nextE = (e.front + 1) % N;
            bool prevNag = e.nagayaEdges.Contains(prevE), nextNag = e.nagayaEdges.Contains(nextE);
            if ((lo < -1.2f && !prevNag) || (hi > len + 1.2f && !nextNag)) { toKill.Add(c.gameObject); sb.AppendLine("kill overshoot " + c.name); continue; }
            cover.Add((lo, hi));
        }
        foreach (var g in toKill) UnityEngine.Object.DestroyImmediate(g);
        {
            int prevE = (e.front + N - 1) % N, nextE = (e.front + 1) % N;
            if (e.nagayaEdges.Contains(prevE)) cover.Add((-0.5f, 4.2f));
            if (e.nagayaEdges.Contains(nextE)) cover.Add((len - 4.2f, len + 0.5f));
        }
        cover.Sort((x, y) => x.lo.CompareTo(y.lo));
        float cur = 0.05f; int fills = 0;
        var gaps = new List<(float, float)>();
        foreach (var iv in cover)
        {
            if (iv.lo > cur + 0.3f) gaps.Add((cur, iv.lo));
            cur = Mathf.Max(cur, iv.hi);
        }
        if (cur < len - 0.3f) gaps.Add((cur, len - 0.05f));
        foreach (var g in gaps)
        {
            Vector2 a = fA + runAxis * (g.Item1 - 0.15f);
            Vector2 b = fA + runAxis * (g.Item2 + 0.15f);
            DobeiRun(kak, a, b, fout, "HeiFill_" + e.front + "_" + fills, Vector2.zero, -1);
            fills++;
            sb.AppendLine("fill gap [" + g.Item1.ToString("F1") + "," + g.Item2.ToString("F1") + "]");
        }
        return sb.Length == 0 ? "front line closed (no gaps)" : sb.ToString();
    }

    public static string RebuildEnclosure(string groupName)
    {
        var root = GameObject.Find(groupName);
        if (root != null)
        {
            var k = root.transform.Find("Kakoi"); if (k != null) UnityEngine.Object.DestroyImmediate(k.gameObject);
            var m = root.transform.Find("Omotemon"); if (m != null) UnityEngine.Object.DestroyImmediate(m.gameObject);
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage2_Enclosure(groupName));
        sb.AppendLine(FixGateJunctions(groupName));
        sb.AppendLine(CloseFrontLine(groupName));
        return sb.ToString();
    }

    public static string Shot(string file, Vector3 pos, Vector3 lookAt, bool ortho, float orthoSize, int wpx, int hpx)
    {
        return EdoNishiTameikeBuilder.Shot(file, pos, lookAt, ortho, orthoSize, wpx, hpx);
    }
}
