// 松平大和守(川越藩17万石)上屋敷の再建 v2 (2026-08-08)
// ユーザー方針: 旧9/15/23m段丘は「変形させすぎ」→ 赤下書き線で再作成。
// 地形: 造成前(git 9137fd1)ベースラインへ復元済み。実在の北東平地(~9m)と南西台地(~28m)は温存し、
//       近代の擁壁崖・掘削穴の帯(前辺から奥行き60-150m)だけを調和補間でなだらかな坂に置換。
// 建物は基壇(小パッド)、外周は街路に段追従する石垣+塀、平地は盲長屋。門=k_mon+両番所(家門17万石)。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoYamatoRebuild
{
    const string GROUP = "Edo_Yashiki_MatsudairaYamato";
    const string P_CW = EdoAssets.JC.CastleWall;
    const string P_CWC = EdoAssets.JC.CastleWallCorner;
    const string P_KMON = EdoAssets.Eg.Kmon;
    const string P_BANSHO = EdoAssets.Eg.Bansho;
    const string P_MANOR = EdoAssets.VK.Manor;
    const string P_BIG = EdoAssets.VK.BigHouse;
    const string P_HOUSEA = EdoAssets.VK.HouseA;
    const string P_SMALL = EdoAssets.VK.SmallHouse;
    const string P_KURA = EdoAssets.Eg.Kura;
    const float ES = 1.818f;

    // 赤下書き線 (P14/P15の重複は除去済み)。順序=ユーザー描画順(反時計回り)。
    // 正典 = docs/Sashizu/parcels.json(CLAUDE.md 規則10)
    public static Vector2[] Poly { get { return EdoParcels.Get("matsudaira_yamato"); } }
    const int FRONT = 13; // 辺 P13->P0 = 汐見坂
    const float GATE_T = 0.40f;

    static Vector2 FA => Poly[FRONT];
    static Vector2 FB => Poly[0];
    static Vector2 Uhat => (FB - FA).normalized;
    static Vector2 Vin { get { var d = Uhat; return new Vector2(-d.y, d.x); } } // 内向き(南西)
    public static Vector2 Gate2 => Vector2.Lerp(FA, FB, GATE_T);
    static float VG(Vector2 p) => Vector2.Dot(p - FA, Vin);

    // 基壇(建物パッド): (u,v)中心, 半幅hu/hv, レベル
    struct Pad { public float u, v, hu, hv, level; public Pad(float u_, float v_, float hu_, float hv_, float l_) { u = u_; v = v_; hu = hu_; hv = hv_; level = l_; } }
    static readonly Pad[] Pads = {
        new Pad(0, 52, 32, 27, 9.5f),     // 表向き(表御殿・能舞台・台所)
        new Pad(6, 100, 20, 15, 15.0f),   // 奥御殿
        new Pad(4, 136, 22, 10, 20.0f),   // 蔵前サービス帯
    };

    // EdoGeom.PIP と実装差あり — 統一は裁定待ち
    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool ins = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) ins = !ins;
        return ins;
    }
    static float DEdge(Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < Poly.Length; i++)
        {
            var a = Poly[i]; var b = Poly[(i + 1) % Poly.Length];
            var d = b - a; float len = d.magnitude; d /= len;
            float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
            m = Mathf.Min(m, (p - (a + d * t)).magnitude);
        }
        return m;
    }
    // 基壇を考慮した設計地盤(建物・庭の接地用)
    public static float PadAt(Vector2 p)
    {
        var g2 = Gate2;
        float u = Vector2.Dot(p - g2, Uhat), v = Vector2.Dot(p - g2, Vin);
        foreach (var pd in Pads)
            if (Mathf.Abs(u - pd.u) < pd.hu && Mathf.Abs(v - pd.v) < pd.hv) return pd.level;
        return EdoNishiTameikeBuilder.Ground(p.x, p.y);
    }

    // ---------- Y1: 造成(壊れ帯の調和補間 + 基壇 + 門前平場) ----------
    public static string Y1_Grade()
    {
        var t = EdoNishiTameikeBuilder.T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = t.transform.position; var ts = td.size;
        float cell = ts.x / (res - 1);
        float x0 = -250, x1 = 26, z0 = -83, z1 = 181;
        int ix0 = Mathf.FloorToInt((x0 - tp.x) / cell), ix1 = Mathf.CeilToInt((x1 - tp.x) / cell);
        int iz0 = Mathf.FloorToInt((z0 - tp.z) / cell), iz1 = Mathf.CeilToInt((z1 - tp.z) / cell);
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h);
        float sy = ts.y;
        Func<int, int, Vector2> W2 = (zz, xx) => new Vector2(tp.x + (ix0 + xx) * cell, tp.z + (iz0 + zz) * cell);
        // 壊れ帯マスク: 区画内 かつ vG∈[55,155] (実測: 崖はv90-110、穴はv60-90)
        var mask = new bool[h, w]; int nm = 0;
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = W2(zz, xx);
            if (!PIP(Poly, p)) continue;
            float v = VG(p);
            if (v > 55 && v < 155) { mask[zz, xx] = true; nm++; }
        }
        // 調和補間: マスクセルを反復平均(境界=マスク外)。初期値は線形ランプで収束を早める
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
            if (mask[zz, xx])
            {
                float v = VG(W2(zz, xx));
                H[zz, xx] = Mathf.Lerp((9.3f - tp.y) / sy, (28.5f - tp.y) / sy, Mathf.Clamp01((v - 55) / 100f));
            }
        for (int it = 0; it < 1200; it++)
            for (int zz = 1; zz < h - 1; zz++) for (int xx = 1; xx < w - 1; xx++)
                if (mask[zz, xx]) H[zz, xx] = (H[zz - 1, xx] + H[zz + 1, xx] + H[zz, xx - 1] + H[zz, xx + 1]) * 0.25f;
        // 基壇: パッド矩形をレベルへ、周囲4mフェザー
        var g2 = Gate2;
        int npad = 0;
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = W2(zz, xx);
            if (!PIP(Poly, p)) continue;
            float u = Vector2.Dot(p - g2, Uhat), v = Vector2.Dot(p - g2, Vin);
            foreach (var pd in Pads)
            {
                float du = Mathf.Abs(u - pd.u) - pd.hu, dv = Mathf.Abs(v - pd.v) - pd.hv;
                float dOut = Mathf.Max(du, dv);
                if (dOut < 0) { H[zz, xx] = (pd.level - tp.y) / sy; npad++; }
                else if (dOut < 4f)
                {
                    float s = dOut / 4f; s = s * s * (3 - 2 * s);
                    H[zz, xx] = Mathf.Lerp((pd.level - tp.y) / sy, H[zz, xx], s);
                }
            }
        }
        // 門前平場: 門中心から半径12m=門地盤、12-20mフェザー(区画外のみ)
        float gatePad = EdoNishiTameikeBuilder.Ground(g2.x, g2.y);
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = W2(zz, xx);
            if (PIP(Poly, p)) continue;
            float dg = (p - g2).magnitude;
            if (dg < 20f)
            {
                float s = Mathf.Clamp01((dg - 12f) / 8f); s = s * s * (3 - 2 * s);
                H[zz, xx] = Mathf.Lerp((gatePad - tp.y) / sy, H[zz, xx], s);
            }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        return "Y1 done: maskCells=" + nm + " padCells=" + npad + " gatePad=" + gatePad.ToString("F2");
    }

    // ---------- Y2: 外周(石垣 段追従 + 塀 / 平地は長屋) ----------
    // 辺ごとに 4mサンプル: inner(内側4m) と street(外側5m) を実測。
    //   |inner-street| <= 1.2 → 長屋ゾーン / それ以外 → 石垣(coping=max(inner,street付近)+1.0を0.5刻み)+塀
    class Seg { public Vector2 a, b; public bool nagaya; public float coping; }
    static List<Seg> PlanSegments(out string log)
    {
        var sb = new System.Text.StringBuilder();
        var segs = new List<Seg>();
        int N = Poly.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 A = Poly[i], B = Poly[(i + 1) % N];
            float len = (B - A).magnitude;
            var d = (B - A).normalized;
            var inw = new Vector2(-d.y, d.x); // 反時計回りポリゴンの左法線=内向き
            int ns = Mathf.Max(1, Mathf.RoundToInt(len / 8f));
            Seg cur = null;
            for (int k = 0; k < ns; k++)
            {
                float t0 = (float)k / ns, t1 = (float)(k + 1) / ns;
                var m = Vector2.Lerp(A, B, (t0 + t1) * 0.5f);
                float inner = EdoNishiTameikeBuilder.Ground((m + inw * 4).x, (m + inw * 4).y);
                float street = EdoNishiTameikeBuilder.Ground((m - inw * 5).x, (m - inw * 5).y);
                bool nag = Mathf.Abs(inner - street) <= 1.2f;
                float cop = Mathf.Round((Mathf.Max(inner, street) + 1.0f) * 2f) / 2f;
                if (cur != null && cur.nagaya == nag && (nag || Mathf.Abs(cur.coping - cop) < 0.26f))
                { cur.b = Vector2.Lerp(A, B, t1); }
                else
                {
                    cur = new Seg { a = Vector2.Lerp(A, B, t0), b = Vector2.Lerp(A, B, t1), nagaya = nag, coping = cop };
                    segs.Add(cur);
                }
            }
            sb.AppendLine("edge" + i + " len=" + len.ToString("F0") + " segs=" + segs.Count);
        }
        log = sb.ToString();
        return segs;
    }

    public static string Y2_Enclosure()
    {
        var root = GameObject.Find(GROUP);
        // v2グループ(新規)。旧サブグループは SetActive(false) のまま温存
        Transform kak = root.transform.Find("Kakoi_v2");
        if (kak != null) UnityEngine.Object.DestroyImmediate(kak.gameObject);
        var kg = new GameObject("Kakoi_v2"); kg.transform.SetParent(root.transform, false); kak = kg.transform;
        Transform mon = root.transform.Find("Omotemon_v2");
        if (mon != null) UnityEngine.Object.DestroyImmediate(mon.gameObject);
        var mg = new GameObject("Omotemon_v2"); mg.transform.SetParent(root.transform, false); mon = mg.transform;
        Undo.RegisterCreatedObjectUndo(kg, "kakoi"); Undo.RegisterCreatedObjectUndo(mg, "mon");

        string plog; var segs = PlanSegments(out plog);
        var sb = new System.Text.StringBuilder(plog);
        var g2 = Gate2;
        int nIshi = 0, nHei = 0, nNag = 0;
        foreach (var s in segs)
        {
            float len = (s.b - s.a).magnitude;
            if (len < 2.5f) continue;
            var d = (s.b - s.a).normalized;
            var inw = new Vector2(-d.y, d.x);
            var outw = -inw;
            // 門スパンはスキップ(前辺のみ該当)
            bool onFront = Mathf.Abs(Vector2.Dot(s.a - FA, new Vector2(-Uhat.y, Uhat.x))) < 3f && Mathf.Abs(Vector2.Dot(s.b - FA, new Vector2(-Uhat.y, Uhat.x))) < 3f;
            float gT0 = Vector2.Dot(g2 - s.a, d);
            bool gateHere = onFront && gT0 > -12 && gT0 < len + 12;
            if (s.nagaya)
            {
                float baseY = EdoNishiTameikeBuilder.Ground(((s.a + s.b) * 0.5f + inw * 2).x, ((s.a + s.b) * 0.5f + inw * 2).y);
                var mods = EdoNishiTameikeBuilder.NagayaRun(kak, s.a, s.b, outw, baseY,
                    gateHere ? g2 : Vector2.zero, gateHere ? 9.5f : -1f, "NGv2_" + nNag);
                nNag++;
            }
            else
            {
                // 石垣: pitch1.8、ローカル+Z=進行、体は左=外 → 進行方向は「外が左」になる向き
                //   ポリゴンは反時計回り(内面)なので、辺を逆走(b→a)すると左=外になる
                var A2 = s.b; var B2 = s.a; var dd = (B2 - A2).normalized;
                float yaw = Mathf.Atan2(dd.x, dd.y) * Mathf.Rad2Deg;
                float ground = Mathf.Min(EdoNishiTameikeBuilder.Ground((A2 - inw * 5).x, (A2 - inw * 5).y),
                                          EdoNishiTameikeBuilder.Ground((B2 - inw * 5).x, (B2 - inw * 5).y));
                float baseY2 = Mathf.Min(ground - 0.6f, s.coping - 2.0f);
                float syw = Mathf.Max(0.5f, (s.coping - baseY2) / 4.0f);
                int n = Mathf.Max(1, Mathf.CeilToInt(len / 1.8f));
                for (int k = 0; k <= n; k++)
                {
                    float tk = Mathf.Min(k * 1.8f, len - 0.01f);
                    var p = A2 + dd * tk;
                    if (gateHere) { float gtk = Vector2.Dot(g2 - A2, dd); if (Mathf.Abs(tk - gtk) < 9.5f) continue; }
                    var go = EdoNishiTameikeBuilder.Place(P_CW, new Vector3(p.x, baseY2, p.y), yaw, new Vector3(1, syw, 1), kak, "CWv2_" + nIshi);
                    nIshi++;
                }
                // 塀(表裏ペア)を天端に
                var hei = EdoNishiTameikeBuilder.DobeiRun(kak, s.a, s.b, outw, "HeiV2_" + nHei, false, s.coping - 0.05f,
                    gateHere ? g2 : Vector2.zero, gateHere ? 9.5f : -1f);
                nHei++;
            }
        }
        // 門: k_mon + 両番所
        float gatePad = EdoNishiTameikeBuilder.Ground(g2.x, g2.y);
        float psiIn = Mathf.Atan2(Vin.x, Vin.y) * Mathf.Rad2Deg;
        var monGo = EdoNishiTameikeBuilder.Place(P_KMON, new Vector3(g2.x, gatePad, g2.y), psiIn, Vector3.one * ES, mon, "Kmon");
        EdoNishiTameikeBuilder.SeatBottom(monGo, gatePad - 0.05f);
        var mb = EdoNishiTameikeBuilder.RB(monGo);
        monGo.transform.position += new Vector3(g2.x - mb.center.x, 0, g2.y - mb.center.z);
        // kagami が内側かの検証(外なら180回転)
        float kmn = float.MaxValue, kmx = float.MinValue;
        foreach (var mf in monGo.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
            foreach (var vtx in mf.sharedMesh.vertices)
            {
                var wp = mf.transform.TransformPoint(vtx);
                float pr = wp.x * (-Vin.x) + wp.z * (-Vin.y);
                kmn = Mathf.Min(kmn, pr); kmx = Mathf.Max(kmx, pr);
            }
        }
        if (kmn != float.MaxValue)
        {
            var mc = EdoNishiTameikeBuilder.RB(monGo).center;
            float cp = mc.x * (-Vin.x) + mc.z * (-Vin.y);
            if ((kmn + kmx) * 0.5f > cp)
            {
                monGo.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b2 = EdoNishiTameikeBuilder.RB(monGo);
                monGo.transform.position += new Vector3(g2.x - b2.center.x, 0, g2.y - b2.center.z);
                sb.AppendLine("kmon flipped");
            }
        }
        for (int i = 0; i < 2; i++)
        {
            float side = i == 0 ? 1f : -1f;
            var bp = g2 + Uhat * (side * 11f) + (-Vin) * 0.5f;
            var ban = EdoNishiTameikeBuilder.Place(P_BANSHO, new Vector3(bp.x, gatePad, bp.y), psiIn + 180f, Vector3.one * ES, mon, "Bansho_" + i);
            EdoNishiTameikeBuilder.SeatBottom(ban, gatePad - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * (-Vin.x) + f3.z * (-Vin.y) < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(-Vin.x, -Vin.y) * Mathf.Rad2Deg, 0);
            // 前面を門前面と面一
            var bb = EdoNishiTameikeBuilder.RB(ban); var gb = EdoNishiTameikeBuilder.RB(monGo);
            float bf = bb.center.x * (-Vin.x) + bb.center.z * (-Vin.y) + bb.extents.magnitude * 0f;
            // 簡易: 門の外面へ z 揃え(実測: 門前面=バウンズの外向き最大)
            float gFront = gb.center.x * (-Vin.x) + gb.center.z * (-Vin.y) + 3.2f;
            float bFront = bb.center.x * (-Vin.x) + bb.center.z * (-Vin.y) + 1.05f * ES;
            float shift = gFront - bFront - 0.6f;
            ban.transform.position += new Vector3(-Vin.x * shift, 0, -Vin.y * shift);
        }
        sb.AppendLine("ishi=" + nIshi + " heiRuns=" + nHei + " nagRuns=" + nNag);
        SceneView.RepaintAll();
        return sb.ToString();
    }

    // ---------- Y3: 建物 ----------
    public static GameObject PlaceUV(string path, float u, float v, float yawOff, Vector3 scale, Transform parent, string name)
    {
        var g2 = Gate2;
        var p = g2 + Uhat * u + Vin * v;
        float y = PadAt(p);
        float streetYaw = Mathf.Atan2(-Vin.x, -Vin.y) * Mathf.Rad2Deg;
        var go = EdoNishiTameikeBuilder.Place(path, new Vector3(p.x, y, p.y), streetYaw + yawOff, scale, parent, name);
        EdoNishiTameikeBuilder.SeatBottom(go, y - 0.12f);
        return go;
    }

    public static string Y3_Buildings()
    {
        var root = GameObject.Find(GROUP);
        Transform bg = root.transform.Find("Buildings_v2");
        if (bg != null) UnityEngine.Object.DestroyImmediate(bg.gameObject);
        var b = new GameObject("Buildings_v2"); b.transform.SetParent(root.transform, false); bg = b.transform;
        Undo.RegisterCreatedObjectUndo(b, "bld");
        // Manor はピボットが facade+35.2 と大きく偏心 → pivot v=61 で facade≈v26 (門から26m)
        PlaceUV(P_MANOR, 0, 61, 0, Vector3.one, bg, "OmoteGoten");
        PlaceUV(P_HOUSEA, 24, 62, 0, Vector3.one, bg, "Daidokoro");
        PlaceUV(P_BIG, 6, 100, 0, Vector3.one, bg, "OkuGoten");
        PlaceUV(P_SMALL, 22, 96, 0, Vector3.one, bg, "OkuDaidokoro");
        PlaceUV(P_KURA, -10, 134, 90, Vector3.one * ES, bg, "Kura_1");
        PlaceUV(P_KURA, 2, 138, 90, Vector3.one * ES, bg, "Kura_2");
        PlaceUV(P_KURA, 14, 140, 90, Vector3.one * ES, bg, "Kura_3");
        PlaceUV(P_SMALL, -22, 162, 0, new Vector3(0.72f, 0.72f, 0.72f), bg, "Chaya");
        // 能舞台(§12a合成): 台+柱+鏡板+SmallHouseの屋根
        NohButai(bg, -22, 46);
        // 厩・中間長屋(knagaya l+r ペア×2) 門脇
        UmayaPair(bg, 32, 16, "Umaya");
        UmayaPair(bg, 48, 18, "Chugen");
        // 井戸2
        Well(bg, 16, 44); Well(bg, 18, 94);
        // 邸内稲荷(台地の一隅)
        Inari(bg, 34, 158);
        return "Y3 done: " + bg.childCount + " buildings";
    }

    static void NohButai(Transform parent, float u, float v)
    {
        var g2 = Gate2; var p = g2 + Uhat * u + Vin * v;
        float y = PadAt(p);
        var g = new GameObject("NohButai"); g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, y, p.y);
        float faceYaw = Mathf.Atan2(Uhat.x, Uhat.y) * Mathf.Rad2Deg; // 正面を御殿(東)へ
        g.transform.rotation = Quaternion.Euler(0, faceYaw, 0);
        Undo.RegisterCreatedObjectUndo(g, "noh");
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.45f, 0.34f, 0.22f);
        var dai = GameObject.CreatePrimitive(PrimitiveType.Cube);
        dai.name = "dai"; dai.transform.SetParent(g.transform, false);
        dai.transform.localScale = new Vector3(6.4f, 0.85f, 6.4f);
        dai.transform.localPosition = new Vector3(0, 0.425f, 0);
        dai.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 4; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.22f, 1.6f, 0.22f);
            post.transform.localPosition = new Vector3(i % 2 == 0 ? -2.8f : 2.8f, 2.4f, i < 2 ? -2.8f : 2.8f);
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
        var kagami = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kagami.name = "kagamiita"; kagami.transform.SetParent(g.transform, false);
        kagami.transform.localScale = new Vector3(5.6f, 2.4f, 0.12f);
        kagami.transform.localPosition = new Vector3(0, 2.05f, 3.1f);
        kagami.GetComponent<Renderer>().sharedMaterial = wood;
        var shAsset = AssetDatabase.LoadAssetAtPath<GameObject>(P_SMALL);
        var sh = (GameObject)PrefabUtility.InstantiatePrefab(shAsset);
        sh.name = "roofDonor"; sh.transform.SetParent(g.transform, false);
        var keep = new List<GameObject>();
        foreach (Transform c in sh.transform) if (!c.name.ToLower().Contains("roof")) keep.Add(c.gameObject);
        foreach (var k in keep) UnityEngine.Object.DestroyImmediate(k);
        sh.transform.localScale = new Vector3(0.57f, 0.8f, 0.63f);
        sh.transform.localPosition = new Vector3(0, 1.1f, 0);
    }

    static void UmayaPair(Transform parent, float u, float v, string name)
    {
        var g2 = Gate2; var c = g2 + Uhat * u + Vin * v;
        float y = PadAt(c);
        float psi = Mathf.Atan2(Vin.x, Vin.y) * Mathf.Rad2Deg;
        float rad = psi * Mathf.Deg2Rad;
        var negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var g = new GameObject(name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        var m1 = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.KnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = EdoNishiTameikeBuilder.Place(EdoAssets.Eg.KnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        var p1 = c - negRight * 3.9f; var p2 = c + negRight * 3.9f;
        m1.transform.position = new Vector3(p1.x, y, p1.y);
        m2.transform.position = new Vector3(p2.x, y, p2.y);
        EdoNishiTameikeBuilder.SeatBottom(m1, y - 0.10f);
        EdoNishiTameikeBuilder.SeatBottom(m2, y - 0.10f);
    }

    static void Well(Transform parent, float u, float v)
    {
        var g2 = Gate2; var p = g2 + Uhat * u + Vin * v;
        float y = PadAt(p);
        var g = new GameObject("Ido_" + u + "_" + v); g.transform.SetParent(parent, false);
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

    static void Inari(Transform parent, float u, float v)
    {
        var g2 = Gate2; var p = g2 + Uhat * u + Vin * v;
        float y = PadAt(p);
        var g = new GameObject("Inari"); g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, y, p.y);
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
}
