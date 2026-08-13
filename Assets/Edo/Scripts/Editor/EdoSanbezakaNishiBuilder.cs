// 三べ坂西街区ビルダー (2026-08-13)
//   赤=渡辺備中守(和泉伯太藩13,520石・譜代)上屋敷 / 黄=鳥居丹波守(下野壬生藩3万石・譜代) / 水色=松平主水正(2,000石旗本)
// 【典拠と確度】
//   ・区画=ユーザー下書き(EdoSketch, 切絵図トレース)が正。色0=赤/1=黄/2=水色/3=緑(=三べ坂)。
//   ・渡辺=上屋敷: 先行考証(EdoSanbezakaBuilder header)+ベイク切絵図(oldmap_center)で当該区画に家紋ブロブ実見。
//   ・表門向き: 3邸とも文字の頭は0.68px/mで判読不能。渡辺=北の道向き【推定: 接道(西=三べ坂/北=北の道)と
//     台地地形(門と御殿を同レベルに)から】。鳥居=北の道(南辺)向き【推定同上】。松平=南【接道が南1面のみ=確度高】。
//   ・鳥居の屋敷格=未確定(家紋判読不能)。1〜3万石譜代共通の門格式(長屋門+格子出両番所)で建て、御成セットは付けない。
//   ・敷地内構成=一般類型(スキル§15/§25/§31)。3邸とも指図・絵画は未発見。
// 【地形】区画内は自然地形(8mグリッド実測で近代造成痕なし)=造成ゼロ・地形追従(§20)。
//   渡辺は安部と同じ崖線をまたぐ(東台地h28.5/西低地h15)。三べ坂=緑線に沿う実在の坂(南h15→北h29)。
// 【境界所有】渡辺E=W2板塀(既存)・渡辺SE=安部NG_NW(既存)→skip。鳥居E(松平境)=鳥居所有。松平W=skip。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using B = EdoSanbezakaBuilder;
using NT = EdoNishiTameikeBuilder;

public static class EdoSanbezakaNishiBuilder
{
    public static readonly Vector2[] WATANABE = {
        new Vector2(-377.5f, 1060.4f), new Vector2(-416.3f, 1103.1f), new Vector2(-442.7f, 1178.1f),
        new Vector2(-293.2f, 1178.4f), new Vector2(-293.9f, 1123.7f) };
    public static readonly Vector2[] TORII = {
        new Vector2(-475.6f, 1272.5f), new Vector2(-445.7f, 1185.9f), new Vector2(-333.3f, 1186.5f),
        new Vector2(-301.0f, 1255.8f), new Vector2(-382.3f, 1245.7f), new Vector2(-410.4f, 1292.9f) };
    public static readonly Vector2[] MATSU = {
        new Vector2(-332.1f, 1186.5f), new Vector2(-213.8f, 1185.9f), new Vector2(-212.6f, 1270.2f),
        new Vector2(-298.6f, 1257.0f) };

    static readonly Vector2 GATE_WATANABE = new Vector2(-320f, 1178.25f); // 北の道向き(推定)
    static readonly Vector2 GATE_TORII = new Vector2(-360f, 1186.15f);    // 北の道(南辺)向き(推定)
    static readonly Vector2 GATE_MATSU = new Vector2(-260f, 1186.1f);     // 南(接道1面)

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
    const float ES = 1.818f;

    static float G(float x, float z) { return B.Ground(x, z); }

    static void SeatB(GameObject go, float y)
    {
        var b = B.RB(go);
        go.transform.position += new Vector3(0, y - b.min.y, 0);
    }

    static List<Bounds> Obst(params Transform[] groups)
    {
        var list = new List<Bounds>();
        foreach (var g in groups)
        {
            if (g == null) continue;
            foreach (Transform c in g)
            {
                if (!c.gameObject.activeSelf) continue;
                var b = B.RB(c.gameObject); b.Expand(new Vector3(2.2f, 200f, 2.2f)); list.Add(b);
            }
        }
        return list;
    }

    // 平坦点探索(§20/§31: 四隅+中点スプレッド最小)。scorer が null なら spread 最小、非nullなら制約内で score 最大。
    static bool FlatSpot(Vector2[] poly, float x0, float x1, float z0, float z1, float hx, float hz,
        List<Bounds> obst, float edgeMargin, Vector2 gate, Func<Vector2, float> scorer,
        out Vector2 best, out float bestVal)
    {
        best = Vector2.zero; bestVal = float.MinValue; bool found = false;
        float bestSpread = float.MaxValue;
        for (float x = x0; x <= x1; x += 1.5f) for (float z = z0; z <= z1; z += 1.5f)
        {
            var p = new Vector2(x, z);
            if (!B.PIP(poly, p)) continue;
            bool cornersIn = true;
            for (int a = -1; a <= 1 && cornersIn; a += 2) for (int b = -1; b <= 1 && cornersIn; b += 2)
            {
                var q = p + new Vector2(a * hx, b * hz);
                if (!B.PIP(poly, q) || B.DistToPolyEdge(poly, q) < edgeMargin) cornersIn = false;
            }
            if (!cornersIn) continue;
            // 門前白洲
            float v = Vector2.Dot(p - gate, (GetCentroid(poly) - gate).normalized);
            float u = (p - (gate + (GetCentroid(poly) - gate).normalized * v)).magnitude;
            if (v > -2f && v < 26f && u < 15f) continue;
            bool hit = false;
            foreach (var ob in obst) if (x + hx > ob.min.x && x - hx < ob.max.x && z + hz > ob.min.z && z - hz < ob.max.z) { hit = true; break; }
            if (hit) continue;
            float gmn = float.MaxValue, gmx = float.MinValue;
            for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++)
            { float gy = G(x + a * hx, z + b * hz); gmn = Mathf.Min(gmn, gy); gmx = Mathf.Max(gmx, gy); }
            float spread = gmx - gmn;
            if (spread > 1.0f) continue;
            if (scorer == null)
            { if (spread < bestSpread) { bestSpread = spread; best = p; bestVal = spread; found = true; } }
            else
            { float s = scorer(p); if (s > bestVal) { bestVal = s; best = p; found = true; } }
        }
        return found;
    }
    static Vector2 GetCentroid(Vector2[] poly)
    {
        Vector2 c = Vector2.zero; foreach (var p in poly) c += p; return c / poly.Length;
    }

    static void Inari(Transform parent, Vector2 pos)
    {
        float y = G(pos.x, pos.y);
        var g = new GameObject("Inari");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(pos.x, y, pos.y);
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
        var kasagi = GameObject.CreatePrimitive(PrimitiveType.Cube); kasagi.name = "t_kasagi"; kasagi.transform.SetParent(g.transform, false);
        kasagi.transform.localScale = new Vector3(2.6f, 0.16f, 0.2f); kasagi.transform.localPosition = new Vector3(0, 2.5f, -2.2f);
        kasagi.GetComponent<Renderer>().sharedMaterial = shu;
        var nuki = GameObject.CreatePrimitive(PrimitiveType.Cube); nuki.name = "t_nuki"; nuki.transform.SetParent(g.transform, false);
        nuki.transform.localScale = new Vector3(2.2f, 0.12f, 0.14f); nuki.transform.localPosition = new Vector3(0, 2.05f, -2.2f);
        nuki.GetComponent<Renderer>().sharedMaterial = shu;
        var kidan = GameObject.CreatePrimitive(PrimitiveType.Cube); kidan.name = "kidan"; kidan.transform.SetParent(g.transform, false);
        kidan.transform.localScale = new Vector3(1.5f, 0.4f, 1.2f); kidan.transform.localPosition = new Vector3(0, 0.2f, 0);
        kidan.GetComponent<Renderer>().sharedMaterial = stone;
        var hokora = GameObject.CreatePrimitive(PrimitiveType.Cube); hokora.name = "hokora"; hokora.transform.SetParent(g.transform, false);
        hokora.transform.localScale = new Vector3(0.9f, 0.9f, 0.8f); hokora.transform.localPosition = new Vector3(0, 0.85f, 0);
        hokora.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "roof" + i; roof.transform.SetParent(g.transform, false);
            roof.transform.localScale = new Vector3(1.3f, 0.06f, 0.65f);
            roof.transform.localPosition = new Vector3(0, 1.45f, i == 0 ? -0.28f : 0.28f);
            roof.transform.localEulerAngles = new Vector3(i == 0 ? -25f : 25f, 0, 0);
            roof.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    static void Umaya(Transform parent, Vector2 c, float psi)
    {
        const float PITCH = 7.81f;
        var g = new GameObject("Umaya");
        g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var m1 = B.Place(B.PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = B.Place(B.PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        float y = G(c.x, c.y);
        Vector2 p1 = c - negRight * (PITCH * 0.5f), p2 = c + negRight * (PITCH * 0.5f);
        m1.transform.position = new Vector3(p1.x, y, p1.y);
        m2.transform.position = new Vector3(p2.x, y, p2.y);
        SeatB(m1, y - 0.10f); SeatB(m2, y - 0.10f);
    }

    static void Garden(Transform gg, Vector2[] poly, Vector2 gate, Transform bgObst, Transform knObst,
        int count, int seed, float bambooBelow)
    {
        var rnd = new System.Random(seed);
        var obst = Obst(bgObst, knObst);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        Vector2 cen = GetCentroid(poly);
        Vector2 axis = (cen - gate).normalized;
        for (int i = 0, guard = 0; i < count && guard < 2500; guard++)
        {
            float px = Mathf.Lerp(mnx, mxx, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(mnz, mxz, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!B.PIP(poly, p2) || B.DistToPolyEdge(poly, p2) < 4f) continue;
            float v = Vector2.Dot(p2 - gate, axis);
            float u = (p2 - (gate + axis * v)).magnitude;
            if (v > -2f && v < 26f && u < 15f) continue;
            bool hit = false;
            foreach (var ob in obst) if (px > ob.min.x && px < ob.max.x && pz > ob.min.z && pz < ob.max.z) { hit = true; break; }
            if (hit) continue;
            float y = G(px, pz);
            GameObject go;
            if (y < bambooBelow)
                go = B.Place(Bamboo[rnd.Next(2)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Take_" + i);
            else if (rnd.NextDouble() < 0.72)
                go = B.Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
            else
                go = B.Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
            SeatB(go, y - 0.05f);
            i++;
        }
    }

    static void Tobiishi(Transform gg, Vector2 from, Vector2 to, int seed)
    {
        var rnd = new System.Random(seed);
        for (float tt = 0; tt <= 1.001f; tt += 0.09f)
        {
            Vector2 p = Vector2.Lerp(from, to, tt);
            float y = G(p.x, p.y);
            var go = B.Place(B.PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, gg, "Tobi_" + tt.ToString("F2"));
            SeatB(go, y + 0.02f);
        }
    }

    // ---------- Stage 1: 渡辺備中守上屋敷 ----------
    public static string Stage1_Watanabe()
    {
        const string GN = "Edo_Yashiki_WatanabeBitchu";
        var exist = GameObject.Find(GN);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Watanabe";
        var sb = new System.Text.StringBuilder();
        NT.NaturalMode = true;
        var kak = B.Group(GN, "Kakoi");
        var monGrp = B.Group(GN, "Omotemon");
        Vector2 fout = -B.InwardNormal(WATANABE, 2);   // 北の道向き
        float gateHalf = B.PlaceGate(B.PNmon, monGrp, GATE_WATANABE, fout, 2, "Nagayamon", sb);
        int N = WATANABE.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = WATANABE[i], b = WATANABE[(i + 1) % N];
            Vector2 outw = -B.InwardNormal(WATANABE, i);
            if (i == 2) B.FrontWall(kak, a, b, outw, GATE_WATANABE, gateHalf + 0.5f, "Hei_F");
            else if (i == 1) NT.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_Saka");  // 三べ坂沿い盲長屋
            else if (i == 0) NT.DobeiRun(kak, a, b, outw, "Hei_0", true, 0, Vector2.zero, -1);
            // i==3: W2板塀所有 / i==4: 安部NG_NW所有 → skip
        }
        var bg = B.Group(GN, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        // 台地は狭い(x[-325,-299])ため御殿=House級の近接分棟(§23: 区画の最適解として記録)
        var og = B.Place(B.PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OmoteGoten");
        B.CenterSeat(og, -310f, 1153f);
        var okg = B.Place(B.PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OkuGoten");
        B.CenterSeat(okg, -310f, 1132f);
        var obst = Obst(bg);
        Vector2 spot; float val;
        if (FlatSpot(WATANABE, -340f, -322f, 1128f, 1160f, 6.9f, 5.0f, obst, 4.5f, GATE_WATANABE, null, out spot, out val))
        { var dd = B.Place(B.PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Daidokoro"); B.CenterSeat(dd, spot.x, spot.y); B.Well(bg, spot.x + 7.5f, spot.y + 3f); }
        else sb.AppendLine("daidokoro: no flat spot");
        obst = Obst(bg);
        if (FlatSpot(WATANABE, -350f, -326f, 1160f, 1174f, 4.6f, 9.4f, obst, 4.0f, GATE_WATANABE, null, out spot, out val))
        { var yk = B.Place(B.PHouseB, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Yakusho"); B.CenterSeat(yk, spot.x, spot.y); }
        else sb.AppendLine("yakusho: no flat spot");
        // 蔵2+厩: 中腹〜低地でスプレッド走査
        obst = Obst(bg);
        for (int k = 1; k <= 2; k++)
        {
            if (FlatSpot(WATANABE, -410f, -350f, 1095f, 1150f, 3.4f, 3.2f, obst, 6f, GATE_WATANABE, null, out spot, out val))
            { var kr = B.Place(B.PKura, Vector3.zero, yawGate + 90f, Vector3.one * ES, bg, "Kura_" + k); B.CenterSeat(kr, spot.x, spot.y, 0.15f); obst = Obst(bg); }
            else { sb.AppendLine("kura" + k + ": no flat spot"); break; }
        }
        if (FlatSpot(WATANABE, -410f, -345f, 1085f, 1145f, 8.2f, 2.6f, obst, 6f, GATE_WATANABE, null, out spot, out val))
            Umaya(bg, spot, yawGate);
        else sb.AppendLine("umaya: no flat spot");
        // 稲荷(鬼門=北東)
        obst = Obst(bg);
        if (FlatSpot(WATANABE, -320f, -296f, 1130f, 1174f, 2.6f, 2.6f, obst, 5f, GATE_WATANABE, p => p.x + p.y, out spot, out val))
            Inari(bg, spot);
        B.Well(bg, -303f, 1142f);
        // 家臣長屋: 崖下(三べ坂裏)2列 — 街路盲長屋の内側 offset10m と、SW辺内側 offset6m
        var kn = B.Group(GN, "KachuNagaya");
        {
            Vector2 a = WATANABE[1], b = WATANABE[2];
            Vector2 inw = B.InwardNormal(WATANABE, 1);
            NT.NagayaRun(kn, a + inw * 10f + (b - a).normalized * 4f, b + inw * 10f - (b - a).normalized * 14f, -inw, 0, Vector2.zero, -1, "KN_W");
        }
        {
            Vector2 a = WATANABE[0], b = WATANABE[1];
            Vector2 inw = B.InwardNormal(WATANABE, 0);
            NT.NagayaRun(kn, a + inw * 6f + (b - a).normalized * 3f, b + inw * 6f - (b - a).normalized * 3f, inw, 0, Vector2.zero, -1, "KN_SW");
        }
        // 庭+参道
        var gg = B.Group(GN, "Garden");
        Garden(gg, WATANABE, GATE_WATANABE, bg, kn, 34, 8801, 19f);
        Tobiishi(gg, GATE_WATANABE - fout * 4f, new Vector2(-310f, 1162f), 8802);
        return sb.ToString() + "watanabe done";
    }

    // ---------- Stage 2: 鳥居丹波守邸 ----------
    public static string Stage2_Torii()
    {
        const string GN = "Edo_Yashiki_ToriiTanba";
        var exist = GameObject.Find(GN);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Torii";
        var sb = new System.Text.StringBuilder();
        NT.NaturalMode = true;
        var kak = B.Group(GN, "Kakoi");
        var monGrp = B.Group(GN, "Omotemon");
        Vector2 fout = -B.InwardNormal(TORII, 1);   // 南=北の道向き
        float gateHalf = B.PlaceGate(B.PNmon, monGrp, GATE_TORII, fout, 2, "Nagayamon", sb);
        int N = TORII.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = TORII[i], b = TORII[(i + 1) % N];
            Vector2 outw = -B.InwardNormal(TORII, i);
            if (i == 1) B.FrontWall(kak, a, b, outw, GATE_TORII, gateHalf + 0.5f, "Hei_F");
            else if (i == 0) NT.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_Saka");  // 三べ坂沿い盲長屋
            else NT.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = B.Group(GN, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var og = B.Place(B.PBigHouse, Vector3.zero, yawGate, Vector3.one, bg, "OmoteGoten");
        B.CenterSeat(og, -360f, 1213f);
        var okg = B.Place(B.PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OkuGoten");
        B.CenterSeat(okg, -395f, 1216f);
        var dd = B.Place(B.PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 1.05f, bg, "Daidokoro");
        B.CenterSeat(dd, -374f, 1237f);
        var ng = B.Place(B.PHouseB, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Nagatsubone");
        B.CenterSeat(ng, -335f, 1220f);
        B.Well(bg, -366f, 1230f);
        var obst = Obst(bg);
        Vector2 spot; float val;
        for (int k = 1; k <= 3; k++)
        {
            if (FlatSpot(TORII, -440f, -400f, 1192f, 1245f, 3.4f, 3.2f, obst, 6f, GATE_TORII, null, out spot, out val))
            { var kr = B.Place(B.PKura, Vector3.zero, yawGate + 90f, Vector3.one * ES, bg, "Kura_" + k); B.CenterSeat(kr, spot.x, spot.y, 0.15f); obst = Obst(bg); }
            else { sb.AppendLine("kura" + k + ": no flat spot"); break; }
        }
        if (FlatSpot(TORII, -415f, -370f, 1190f, 1205f, 8.2f, 2.6f, obst, 5f, GATE_TORII, null, out spot, out val))
            Umaya(bg, spot, yawGate + 180f);
        else sb.AppendLine("umaya: no flat spot");
        obst = Obst(bg);
        // 稲荷(北東=notch寄り)
        if (FlatSpot(TORII, -410f, -382f, 1250f, 1288f, 2.6f, 2.6f, obst, 5f, GATE_TORII, p => p.x + p.y, out spot, out val))
            Inari(bg, spot);
        B.Well(bg, -344f, 1200f);
        // 家臣長屋: 西(坂裏)1列 + 北辺内側1列
        var kn = B.Group(GN, "KachuNagaya");
        {
            Vector2 a = TORII[0], b = TORII[1];
            Vector2 inw = B.InwardNormal(TORII, 0);
            NT.NagayaRun(kn, a + inw * 10f + (b - a).normalized * 6f, b + inw * 10f - (b - a).normalized * 10f, -inw, 0, Vector2.zero, -1, "KN_W");
        }
        {
            Vector2 a = TORII[5], b = TORII[0];
            Vector2 inw = B.InwardNormal(TORII, 5);
            NT.NagayaRun(kn, a + inw * 6f + (b - a).normalized * 4f, b + inw * 6f - (b - a).normalized * 4f, inw, 0, Vector2.zero, -1, "KN_N");
        }
        var gg = B.Group(GN, "Garden");
        Garden(gg, TORII, GATE_TORII, bg, kn, 36, 8901, 18f);
        Tobiishi(gg, GATE_TORII - fout * 4f, new Vector2(-360f, 1200f), 8902);
        return sb.ToString() + "torii done";
    }

    // ---------- Stage 3: 松平主水正邸 ----------
    public static string Stage3_Matsudaira()
    {
        const string GN = "Edo_Yashiki_MatsudairaMondo";
        var exist = GameObject.Find(GN);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Matsudaira";
        var sb = new System.Text.StringBuilder();
        NT.NaturalMode = true;
        var kak = B.Group(GN, "Kakoi");
        var monGrp = B.Group(GN, "Omotemon");
        Vector2 fout = -B.InwardNormal(MATSU, 0);   // 南向き
        float gateHalf = B.PlaceGate(B.PHmon, monGrp, GATE_MATSU, fout, 0, "Hmon", sb);
        int N = MATSU.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = MATSU[i], b = MATSU[(i + 1) % N];
            Vector2 outw = -B.InwardNormal(MATSU, i);
            if (i == 0) B.FrontWall(kak, a, b, outw, GATE_MATSU, gateHalf + 0.5f, "Hei_F");
            else if (i == 3) continue;   // 鳥居境=鳥居所有
            else NT.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = B.Group(GN, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        // 主屋=敷地中央・式台玄関を表門に正対(§15)
        var sh = B.Place(B.PHouse, Vector3.zero, yawGate, Vector3.one, bg, "Shuoku");
        B.CenterSeat(sh, -262f, 1214f);
        var dd = B.Place(B.PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 0.95f, bg, "Daidokoro");
        B.CenterSeat(dd, -281f, 1228f);
        B.Well(bg, -272f, 1227f);
        var obst = Obst(bg);
        Vector2 spot; float val;
        for (int k = 1; k <= 2; k++)
        {
            if (FlatSpot(MATSU, -318f, -222f, 1236f, 1260f, 3.4f, 3.2f, obst, 6f, GATE_MATSU, null, out spot, out val))
            { var kr = B.Place(B.PKura, Vector3.zero, yawGate, Vector3.one * ES, bg, "Kura_" + k); B.CenterSeat(kr, spot.x, spot.y, 0.15f); obst = Obst(bg); }
            else { sb.AppendLine("kura" + k + ": no flat spot"); break; }
        }
        // 稲荷=北東角(鬼門, §15旗本)
        if (FlatSpot(MATSU, -240f, -216f, 1240f, 1266f, 2.6f, 2.6f, obst, 5f, GATE_MATSU, p => p.x + p.y, out spot, out val))
            Inari(bg, spot);
        // 表長屋(道路側, §15): 門の東脇 l+r 対
        var kn = B.Group(GN, "KachuNagaya");
        {
            var m1 = B.Place(B.PKnagayaL, Vector3.zero, yawGate + 180f, Vector3.one * ES, kn, "Omote_L");
            var m2 = B.Place(B.PKnagayaR, Vector3.zero, yawGate + 180f, Vector3.one * ES, kn, "Omote_R");
            B.CenterSeat(m1, -242f, 1192f); B.CenterSeat(m2, -234.2f, 1192f);
        }
        var gg = B.Group(GN, "Garden");
        Garden(gg, MATSU, GATE_MATSU, bg, kn, 26, 9001, 0f);
        Tobiishi(gg, GATE_MATSU - fout * 4f, new Vector2(-262f, 1205f), 9002);
        return sb.ToString() + "matsudaira done";
    }

    [MenuItem("Edo/三べ坂西街区(渡辺・鳥居・松平)を生成")]
    public static void RunAllMenu() { Debug.Log(RunAll()); }
    public static string RunAll()
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage1_Watanabe());
        sb.AppendLine(Stage2_Torii());
        sb.AppendLine(Stage3_Matsudaira());
        UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
        return sb.ToString();
    }
}
