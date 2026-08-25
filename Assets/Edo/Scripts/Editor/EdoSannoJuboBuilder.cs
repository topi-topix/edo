// 山王社麓・社僧十坊ビルダー (2026-08-10/11)
//   東(北東)から: 円乗院(ユーザー表記:円成院)/成就院/宝蔵院/長明院/福寿院/智光院/宝仙院/無量院/智乗院/常明院
// 【考証 2026-08-10 Web調査(NDL/CODH/神殿大観=日枝神社史/江戸名所図会 実見)】
//   ・十坊=山王権現(現日枝神社)別当・観理院配下の「社僧の坊」(天台宗)。独立寺院ではない住坊。
//     明治の神仏分離で全坊廃絶。跡地=永田町(星岡茶寮→現キャピトル東急ほか)。
//   ・尾張屋版「外桜田永田町絵図」(嘉永3, NDL1286657 / CODH 7-069〜7-078)で並び順を実見確認。
//     ユーザー指定の東→西順と一致。『日枝神社史』系は円城院・長命院・福聚院・宝泉院の表記。
//   ・表門は山側の小道向き(道は区画列の内側=山王山裾にのみ有り、観理院の角から分かれ常明院付近で行き止まり)。
//     裏は溜池水際に直接落ちる(物干・畑・土手)。
//   ・住坊の類型: 本堂・山門・鐘楼・墓地は持たない。書院造の主屋(庫裏一体, 桁行5〜7間)+
//     下屋・小土蔵/物置・井戸。門=棟門/腕木門級。塀=板塀+生垣(水際は柵)。【典拠: 類型(確度中)。
//     各坊個別の指図は未発見 — 御府内寺社備考・日枝神社史 原本未参照】
// 【区画】ユーザー下書き(EdoSketch 10筆)を隣接間で共有境界へスナップ(中点合成)。
//   P9智乗院/P10常明院の間の約9m離隔のみ道の終端部として温存。円乗院の東の南北小路は敷地外(東縁)。
// 【地形】造成ゼロ・現地形追従(terrain-follows-present-day)。P9/P10の北東部は山腹斜面のまま。
// 各段階は既存グループがあればスキップ(手直し保護)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSannoJuboBuilder
{
    // ---------- assets ----------
    const string PKabuki = EdoAssets.Eg.Kabukimon;   // 腕木門
    const string PItabei5 = EdoAssets.Eg.Itabei5;      // 板塀5枚スパン(7.49m@ES)
    const string PHogaki5 = EdoAssets.Eg.Hogaki5;      // 穂垣5枚スパン(水際の柵)
    const string PKura = EdoAssets.Eg.Kura;
    const string PSmallHouse = EdoAssets.VK.SmallHouse; // 14.5x10.5 ≒ 8x6間
    public const float ES = 1.818f;

    public class Parcel
    {
        public string group, label;
        public Vector2[] poly;
        public int front;                       // 表門のある辺 (Pi->Pi+1)
        public float gateT = 0.5f;
        public int backEdge = 1;                // 溜池水際の辺(穂垣)
        public int[] noWallEdges = new int[0];  // 隣が受け持つ境界
        public int rank;                        // 0=両端の大坊 1=中坊 2=小坊
    }

    // 頂点順: [FE(前東), BE(裏東), BW(裏西), FW(前西)] / 辺: 0=E側 1=裏(溜池) 2=W側 3=前(山麓道)
    // 境界共有: 各坊は自分のE辺(0)+裏辺(1)+前辺(3)を建て、W辺(2)は西隣が建てる(P9は小路側W辺も自前)
    public static Parcel[] Parcels = new Parcel[]
    {
        // 2026-08-11 ユーザー下書き改訂版: 円成/成就/宝蔵は西へ詰め、東端は南北小路(x≈-386.5)の西縁。
        // 小路の東(旧P1東帯)は敷地外。宝蔵院の西辺=既存の長明院東辺(長明院所有の塀)にスナップ。
        new Parcel{ group="Edo_SannoBo_Enjoin", label="円乗院(円成院/山王社社僧)", rank=0,
            poly=EdoParcels.Get("sannojubo_parcels_0"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Jojuin", label="成就院(山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_1"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Hozoin", label="宝蔵院(山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_2"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Chomyoin", label="長明院(長命院/山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_3"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Fukujuin", label="福寿院(福聚院/山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_4"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Chikoin", label="智光院(山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_5"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Hosenin", label="宝仙院(宝泉院/山王社社僧)", rank=2,
            poly=EdoParcels.Get("sannojubo_parcels_6"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Muryoin", label="無量院(山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_7"),
            front=3, gateT=0.5f, noWallEdges=new[]{2} },
        new Parcel{ group="Edo_SannoBo_Chijoin", label="智乗院(山王社社僧)", rank=1,
            poly=EdoParcels.Get("sannojubo_parcels_8"),
            front=3, gateT=0.8f, noWallEdges=new int[0] },   // 門は低平帯(FE寄り)
        new Parcel{ group="Edo_SannoBo_Jomyoin", label="常明院(山王社社僧)", rank=0,
            poly=EdoParcels.Get("sannojubo_parcels_9"),
            // 2026-08-26 json採用で 5→10点、辺indexを再採番(旧→新の頂点対応 0→0/1→1/2→3/3→6/4→9):
            //   旧辺0(SE小路=表)→辺0 / 旧辺1(W水際=backEdge)→辺1+辺2 / 旧辺2(岡部共有)→辺3,4,5 /
            //   旧辺3(NE山腹)→辺6,7,8 / 旧辺4(E山裾)→辺9。
            // 辺3〜5 = poly[3]→[6] は**岡部筑前守邸との共有境界**。
            // ⚠ **岡部が持つ**(ユーザー裁定 2026-08-19、確度U)。岡部 Hei_S_W / Hei_S_Cd と
            //   二重になっていた(間隔 0.56〜3.06m)。囲いは1条([丸の内三丁目] 確度A)。
            // ⚠ backEdge は単一辺のため旧辺1 の下半(辺1)のみ穂垣。上半(辺2)は板塀になる —
            //   水際の続きなら次の再建時に検図で裁定する(壊すより残す)。
            front=0, gateT=0.4f, backEdge=1, noWallEdges=new[]{3,4,5} },
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

    // ---------- 板塀/穂垣 run (片面ポリゴンの表裏ペア) ----------
    // asset: 5枚スパンOBJ。バウンズ中心合わせで格子に載せ、パネル毎に接地。
    public static List<GameObject> PanelRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        string assetPath, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        // スパン実測(ES基準)
        var probe = Place(assetPath, Vector3.zero, 0, Vector3.one * ES, parent, "probe");
        float spanES = RB(probe).size.x;
        UnityEngine.Object.DestroyImmediate(probe);
        if (spanES < 0.5f) spanES = 7.49f;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (spanES - 0.15f)));
        float pitch = len / n;
        float sx = ES * pitch / spanES;
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
                var off2 = outward * (side == 0 ? 0.0f : -0.12f);
                var go = Place(assetPath, Vector3.zero, ry, new Vector3(sx, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                var b = RB(go);
                var target = new Vector3(c2.x + off2.x, 0, c2.y + off2.y);
                go.transform.position += new Vector3(target.x - b.center.x, 0, target.z - b.center.z);
                SeatBottom(go, baseY - 0.10f);
                made.Add(go);
            }
        }
        return made;
    }

    // ---------- Stage 1: 囲い(板塀+腕木門, 水際=穂垣) ----------
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

        // 腕木門(社僧坊の門格: 棟門/腕木門級)
        var mon = Place(PKabuki, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Mon");
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
                sb.AppendLine("mon flipped");
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
        float gateHalf = (wmx - wmn) * 0.5f;
        sb.AppendLine(e.group + " gate width=" + (wmx - wmn).ToString("F2"));

        for (int i = 0; i < N; i++)
        {
            if (e.noWallEdges.Contains(i)) continue;
            Vector2 a = e.poly[i], b = e.poly[(i + 1) % N];
            Vector2 outw = -InwardNormal(e, i);
            if (i == e.front)
            {
                // 前辺は「門の左右2セグメント」(ギャップ方式は短辺で全滅するため)
                float target = gateHalf - 0.15f;
                Vector2 gL = gate2 - uhat * target, gR = gate2 + uhat * target;
                if (Vector2.Distance(a, gL) > 1.2f && Vector2.Dot(gL - a, (b - a).normalized) > 0)
                    PanelRun(kak, a, gL, outw, "Itabei_FL", PItabei5, Vector2.zero, -1);
                if (Vector2.Distance(gR, b) > 1.2f && Vector2.Dot(b - gR, (b - a).normalized) > 0)
                    PanelRun(kak, gR, b, outw, "Itabei_FR", PItabei5, Vector2.zero, -1);
            }
            else if (i == e.backEdge)
                PanelRun(kak, a, b, outw, "Hogaki_" + i, PHogaki5, Vector2.zero, -1);
            else
                PanelRun(kak, a, b, outw, "Itabei_" + i, PItabei5, Vector2.zero, -1);
        }
        SceneView.RepaintAll();
        return sb.ToString() + "enclosure done";
    }

    // ---------- Stage 2: 住坊(本堂は作らない — 書院造主屋+下屋+物置/小土蔵+井戸) ----------
    public static string Stage2_Buildings(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Buildings") != null) return "SKIP: Buildings exists";
        var bg = Group(e.group, "Buildings");

        if (e.rank == 0)
        {
            // 両端の大坊: 主屋(やや大)+下屋(勝手)+持仏堂+小土蔵+井戸
            PlaceUVFlat(e, PSmallHouse, 0, 22, 0, Vector3.one * 1.15f, bg, "Shuoku", 17, 13, 10, 4.5f);
            PlaceUVFlat(e, PSmallHouse, 14, 30, 90, Vector3.one * 0.62f, bg, "Katte", 8, 7, 8, 3.5f);
            PlaceUVFlat(e, PSmallHouse, -14, 34, 0, Vector3.one * 0.6f, bg, "Jibutsudo", 8, 7, 8, 3.5f);
            PlaceUVFlat(e, PKura, 10, 44, 90, Vector3.one * ES, bg, "Kura", 7, 5, 8, 3.5f);
            Well(e, bg, -8, 26);
        }
        else if (e.rank == 1)
        {
            // 中坊: 主屋+物置(小土蔵)+井戸
            PlaceUVFlat(e, PSmallHouse, 0, 18, 0, Vector3.one, bg, "Shuoku", 15, 11, 9, 4f);
            PlaceUVFlat(e, PKura, 10, 28, 90, Vector3.one * ES * 0.8f, bg, "Monooki", 6, 4, 8, 3f);
            Well(e, bg, -7, 24);
        }
        else
        {
            // 小坊: 主屋+井戸
            PlaceUVFlat(e, PSmallHouse, 0, 15, 0, Vector3.one * 0.9f, bg, "Shuoku", 13, 10, 8, 3.5f);
            Well(e, bg, 6, 22);
        }
        return "buildings done: " + e.group;
    }

    // 井戸(合成)
    static void Well(Parcel e, Transform parent, float u, float v)
    {
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 p = gate2 + uhat * u + vhat * v;
        if (!EdoGeom.PIP(e.poly, p) || DistToPolyEdge(e.poly, p) < 2.0f) p = FlatNear(e, u, v, 3, 3, 8, 2.0f);
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

    // ---------- Stage 3: 境内植栽(松基調+竹叢+生垣・刈込, 桜なし=図会は松杉基調) ----------
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JC.Azalea04,
        EdoAssets.JG.Boxwood01 };
    static string[] Bamboo = {
        EdoAssets.JG.BambooBig01,
        EdoAssets.JG.BambooBig02 };
    const string PTobi = EdoAssets.JG.TobiIshi01;
    const string PKasuga = EdoAssets.Own.KasugaLantern;
    const string PYukimi = EdoAssets.Own.YukimiLantern;

    public static string Stage3_Garden(string groupName, int seed)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var dead = new List<GameObject>();
        foreach (Transform ch in root.transform) if (ch.name == "Garden") dead.Add(ch.gameObject);
        foreach (var dg in dead) UnityEngine.Object.DestroyImmediate(dg);
        var trees = Group(e.group, "Garden/Trees");
        var shrubs = Group(e.group, "Garden/Shrubs");
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
            if (DistToPolyEdge(e.poly, p) < 2.2f) return false;
            foreach (var b in obs)
                if (p.x > b.min.x - m && p.x < b.max.x + m && p.y > b.min.z - m && p.y < b.max.z + m) return false;
            return true;
        };
        Vector2 gate2, uhat, vhat; Frame(e, out gate2, out uhat, out vhat);
        Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
        float vCen = Vector2.Dot(cen - gate2, vhat);
        var bb = new Bounds(new Vector3(cen.x, 0, cen.y), Vector3.zero);
        foreach (var p in e.poly) bb.Encapsulate(new Vector3(p.x, 0, p.y));

        int nPine = e.rank == 0 ? 7 : (e.rank == 1 ? 5 : 3);
        int placed = 0, guard = 0;
        while (placed < nPine && guard++ < 900)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            float v = Vector2.Dot(p - gate2, vhat);
            if (v < vCen * 0.55f && rnd.NextDouble() < 0.7) continue;
            if (!clear(p, 2.5f)) continue;
            float y = Ground(p.x, p.y);
            float sc = 1.65f * (0.9f + 0.5f * (float)rnd.NextDouble());
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Pine_" + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        // 竹叢(裏手の一隅)
        for (int i = 0, g2 = 0; i < (e.rank == 2 ? 2 : 4) && g2 < 300; g2++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 1.15f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = Ground(p.x, p.y);
            float sc = 1.5f * (0.85f + 0.4f * (float)rnd.NextDouble());
            var go = Place(Bamboo[rnd.Next(Bamboo.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Bamboo_" + i);
            SeatBottom(go, y - 0.05f);
            i++;
        }
        // 低木(生垣・刈込)
        int nShrub = e.rank == 0 ? 10 : (e.rank == 1 ? 7 : 5);
        for (int i = 0, g2 = 0; i < nShrub && g2 < 500; g2++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (!clear(p, 1.2f)) continue;
            float y = Ground(p.x, p.y);
            float sc = 0.9f + 0.7f * (float)rnd.NextDouble();
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, shrubs, "Shrub_" + i);
            SeatBottom(go, y - 0.04f);
            i++;
        }
        // 参道飛石: 門 → 主屋玄関
        var bld = root.transform.Find("Buildings");
        Transform main = bld != null ? bld.Find("Shuoku") : null;
        if (main != null)
        {
            var mbb = RB(main.gameObject);
            var m2 = new Vector2(mbb.center.x, mbb.center.z);
            Vector2 g0 = gate2 + vhat * 2.5f;
            Vector2 g1 = m2 - vhat * 7f;
            int steps = Mathf.Max(3, Mathf.RoundToInt((g1 - g0).magnitude / 2.4f));
            for (int i = 0; i <= steps; i++)
            {
                float tt = (float)i / steps;
                Vector2 p = Vector2.Lerp(g0, g1, tt);
                p += new Vector2((float)rnd.NextDouble() * 0.4f - 0.2f, (float)rnd.NextDouble() * 0.4f - 0.2f);
                float y = Ground(p.x, p.y);
                var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, path, "Tobi_" + i);
                SeatBottom(go, y + 0.02f);
            }
        }
        // 灯籠 1-2基
        int nLan = e.rank == 0 ? 2 : 1;
        for (int i = 0, g3 = 0; i < nLan && g3 < 200; g3++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 0.4f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = Ground(p.x, p.y);
            string lp = (i % 2 == 0) ? PKasuga : PYukimi;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(lp) == null) lp = EdoAssets.JC.StoneBasket;
            var go = Place(lp, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, props, "Lantern_" + i);
            SeatBottom(go, y - 0.03f);
            i++;
        }
        return "garden done: " + e.group;
    }

    // ---------- Stage 4: スプラット(境内+裏の畑・物干帯+前面道路+道の終端) ----------
    public static string Stage4_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -660, x1 = -350, z0 = 620, z1 = 960;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        // 前面道路: 各坊の前辺角の連なり(P1FE→…→P9FW)を外側3.2mへオフセット
        var roadPts = new List<Vector2>();
        for (int pi = 0; pi < 9; pi++)
        {
            var e = Parcels[pi];
            Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % e.poly.Length];
            Vector2 outw = -InwardNormal(e, e.front);
            if (pi == 0) roadPts.Add(fB + outw * 3.2f);
            roadPts.Add(fA + outw * 3.2f);
        }
        // 東の南北小路(円乗院東縁, x≈-386.5): 南は溜池岸へ行き止まり
        var eastA = new Vector2(-386.6f, 726f);
        var eastB = new Vector2(-386.0f, 641f);
        // 道の終端部(P9/P10間の離隔)
        var laneA = new Vector2(-589.8f, 841.1f);
        var laneB = new Vector2(-612.1f, 834.7f);
        Func<Vector2, float> distRoad = p =>
        {
            float m = float.MaxValue;
            for (int i = 0; i < roadPts.Count - 1; i++) m = Mathf.Min(m, EdoGeom.DistToEdge(p, roadPts[i], roadPts[i + 1]));
            m = Mathf.Min(m, EdoGeom.DistToEdge(p, laneA, laneB));
            m = Mathf.Min(m, EdoGeom.DistToEdge(p, eastA, eastB));
            return m;
        };
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float bare = -1, grass = 0, dirt = 0;
                float dR = distRoad(p);
                bool inParcel = false; Parcel pe = null;
                foreach (var e in Parcels) if (EdoGeom.PIP(e.poly, p)) { inParcel = true; pe = e; break; }
                if (inParcel)
                {
                    Vector2 gate2, uhat, vhat; Frame(pe, out gate2, out uhat, out vhat);
                    float v = Vector2.Dot(p - gate2, vhat);
                    float uAbs = Mathf.Abs(Vector2.Dot(p - gate2, uhat));
                    var bA = pe.poly[pe.backEdge]; var bB = pe.poly[(pe.backEdge + 1) % pe.poly.Length];
                    float dBack = EdoGeom.DistToEdge(p, bA, bB);
                    if (v < 11 && uAbs < 8) { bare = 0.78f; grass = 0.08f; dirt = 0.14f; }     // 門内前庭
                    else if (dBack < 10) { bare = 0.22f; grass = 0.18f; dirt = 0.60f; }         // 裏の畑・物干場
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.42f, 0.70f, noise); bare = 0.08f; dirt = 1f - grass - bare;
                    }
                }
                else if (dR < 3.0f) { bare = 0.55f; grass = 0.05f; dirt = 0.40f; }              // 道
                else if (dR < 4.5f) { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }              // 路肩
                if (bare < 0) continue;
                float sum = bare + grass + dirt;
                for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                changed++;
            }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- OBB QA ----------
    public static void ObbFootprint(Transform it, out float mnx, out float mxx, out float mnz, out float mxz, out float mny)
        => EdoBuild.ObbFootprint(it, out mnx, out mxx, out mnz, out mxz, out mny);
    public static string QA_Obb(string groupName)
    {
        var e = Parcels.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        var bld = root != null ? root.transform.Find("Buildings") : null;
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
        return childPath + " 埋=" + buried.ToString("F2") + " 浮=" + floating.ToString("F2");
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
            sb.AppendLine(Stage3_Garden(e.group, seed++));
        sb.AppendLine(Stage4_Splat());
        return sb.ToString();
    }
}
