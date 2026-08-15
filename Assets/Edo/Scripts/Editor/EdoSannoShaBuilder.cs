// 山王権現社(日枝神社)本体+観理院+樹下家邸+山王門前町ビルダー (2026-08-11)
// 【典拠 2026-08-10調査】
//   ・境内構成=江戸名所図会 巻之三「日吉山王神社」挿絵(NDL 2563386/7コマ, 実見):
//     山麓の通りに二ノ鳥居+名水井戸「つつ井」/鳥居の左(西)=別当観理院・右(東)=神主樹下邸/
//     馬場状前庭に茶店縁台/男坂=直線の長い石段(現存53段)・登り口に仁王門+透塀/石段上に随身門+回廊/
//     内に神楽殿・鐘楼・鼓楼・手水舎・薬師堂・観音堂・不動堂・庚申堂・宝蔵→中門→拝殿→本社(権現造)。
//     女坂=男坂の左手(北)を屈曲しながら登る緩い坂。
//   ・位置=尾張屋版外桜田永田町絵図(NDL1286657)+CODH座標: 山王社7-079/観理院7-080/樹下近江守7-068/
//     山王門前町7-067。観理院=表参道石段下の正面(現キャピトル東急、神殿大観←水野家文書「山王絵図」)。
//   ・万治2年(1659)造営の社殿群は幕末まで存続(嘉永期=図会天保期の姿と同一でよい)。
// 【代用表現(確度は形式レベル)】社殿・堂宇=Village Kit/es_kura、随身門・仁王門=Yaguramon A縮小、
//   回廊→練塀(es_dobei)、鳥居=石鳥居の合成、石段=角柱合成。個々の建物寸法の一次史料は未参照。
// 【地形】造成ゼロ。山王山の現地形(山頂平坦面h≈28)に追従。石段は斜面上に据える。
// 各段階は既存グループがあればスキップ(手直し保護)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSannoShaBuilder
{
    const string GROUP = "Edo_Sanno_Sha";        // 境内(山上)+参道
    const string GROUP_K = "Edo_Sanno_Kanriin";  // 別当観理院
    const string GROUP_J = "Edo_Sanno_JugeYashiki"; // 神主樹下邸
    const string GROUP_M = "Edo_Sanno_Monzencho";   // 山王門前町

    const string PYaguramon = EdoAssets.JC.YaguramonA;
    const string PKmon = EdoAssets.Eg.Kmon;
    const string PKabuki = EdoAssets.Eg.Kabukimon;
    const string PKura = EdoAssets.Eg.Kura;
    const string PKido = EdoAssets.Eg.KidoOpen;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    const string PItabei5 = EdoAssets.Eg.Itabei5;
    const string PBasket = EdoAssets.JC.StoneBasket;
    const string PDanishi = EdoAssets.Own.DanishiStep;      // 段石(汐見坂で採用済)
    const string PMichibata = EdoAssets.Own.MichibataIshi;  // 道端石
    const string PKasuga = EdoAssets.Own.KasugaLantern;
    const string PTobi = EdoAssets.JG.TobiIshi01;
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JG.Boxwood01 };
    static string[] Rocks = {
        EdoAssets.JG.Rock01,
        EdoAssets.JG.Rock02,
        EdoAssets.JG.Rock03 };
    public const float ES = 1.818f;

    // ---- 幾何定数(地形実測 2026-08-11: 山頂平坦面 h≈28 = x[-565,-485] z[800,895]) ----
    // 参道軸: 東西, z=857。男坂 x[-484,-424](高低差≈16m)。
    static readonly Vector2 ZUIJIN = new Vector2(-490f, 857f);   // 随身門(石段上)
    static readonly Vector2 NIO = new Vector2(-417f, 857f);      // 仁王門(石段下)
    // 二ノ鳥居: 参道入口(観理院北角の北・南北小路との辻)。参道は北東から斜めに男坂下へ折れて入る
    // (図会「鳥居から左折して参道が進む」/ 2026-08-11 ユーザー下書き改訂: 観理院=石段下〜山麓の縦長区画)
    static readonly Vector2 TORII = new Vector2(-403f, 891.5f);
    static readonly Vector2 APPROACH_MID = new Vector2(-412.9f, 889.5f); // 観理院北角の外側で折れる
    static readonly Vector2 APPROACH_END = new Vector2(-424.5f, 857.5f); // 男坂下(観理院練塀の外に平行)
    static readonly float StairX0 = -424f, StairX1 = -482f;      // 石段の下端/上端
    static readonly Vector2[] PREC = {                            // 境内(透塀)矩形
        new Vector2(-566f, 818f), new Vector2(-490f, 818f),
        new Vector2(-490f, 896f), new Vector2(-566f, 896f) };
    // 観理院: 山麓の通り(南北小路)の西・石段下の南に接する縦長大区画(2026-08-11ユーザー下書き)
    // 辺: 0=S(前面道路) 1=W(山裾) 2=NW(参道コリドー沿い=表門) 3=N 4=E(南北小路沿い)
    static readonly Vector2[] KANRI = {
        new Vector2(-389.4f, 735.3f), new Vector2(-421.6f, 732.5f),
        new Vector2(-426.2f, 851.4f), new Vector2(-409.7f, 888.1f),
        new Vector2(-390.2f, 888.3f) };
    // 樹下邸: 北東麓
    static readonly Vector2[] JUGE = {
        new Vector2(-470f, 900f), new Vector2(-428f, 900f),
        new Vector2(-428f, 936f), new Vector2(-470f, 936f) };
    // 門前町の道: 山麓の通りの北端から北東へ
    static readonly Vector2[] MONZEN_ROAD = {
        new Vector2(-390f, 926f), new Vector2(-352f, 940f), new Vector2(-306f, 950f) };
    // 山麓の通り(南北小路, 円乗院・観理院の東縁 x≈-386.5。南は溜池岸で行き止まり)
    static readonly Vector2[] BASE_ST = {
        new Vector2(-386.0f, 641f), new Vector2(-386.6f, 726f), new Vector2(-387.2f, 780f),
        new Vector2(-387.8f, 845f), new Vector2(-387.8f, 890f), new Vector2(-389f, 908f), new Vector2(-390f, 926f) };

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
    static Material Mat(Color c) { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; }
    static GameObject Box(Transform parent, string name, Vector3 pos, Vector3 scale, Material m, float ry = 0)
    {
        var b = GameObject.CreatePrimitive(PrimitiveType.Cube);
        b.name = name; b.transform.SetParent(parent, false);
        b.transform.position = pos; b.transform.localScale = scale;
        b.transform.rotation = Quaternion.Euler(0, ry, 0);
        b.GetComponent<Renderer>().sharedMaterial = m;
        return b;
    }
    static GameObject Cyl(Transform parent, string name, Vector3 pos, Vector3 scale, Material m, Vector3 euler)
    {
        var b = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        b.name = name; b.transform.SetParent(parent, false);
        b.transform.position = pos; b.transform.localScale = scale;
        b.transform.rotation = Quaternion.Euler(euler);
        b.GetComponent<Renderer>().sharedMaterial = m;
        return b;
    }
    // プレハブ固有スケールを保持して配置(Shiomizakaモデル等はルートに補正スケールを持つ)
    static GameObject PlaceNative(string path, Vector3 pos, float ry, Transform parent, string name)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        Undo.RegisterCreatedObjectUndo(go, "place");
        return go;
    }
    // バウンズ中心を(x,z)へ、足元を接地
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

    // ---------- Stage 1: 山上境内 ----------
    public static string Stage1_Keidai()
    {
        var root = GameObject.Find(GROUP);
        if (root != null && root.transform.Find("Keidai") != null) return "SKIP: Keidai exists";
        var kg = Group(GROUP, "Keidai");
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;

        // 透塀(回廊の代用, es_dobei) — 東辺は随身門で開口
        var kak = Group(GROUP, "Keidai/Kairo");
        for (int i = 0; i < 4; i++)
        {
            Vector2 a = PREC[i], b = PREC[(i + 1) % 4];
            Vector2 mid = (a + b) * 0.5f;
            Vector2 cen = (PREC[0] + PREC[2]) * 0.5f;
            Vector2 outw = (mid - cen); outw.Normalize();
            if (i == 1) // 東辺 x=-490
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Kairo_E", true, 0, ZUIJIN, 7.2f);
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Kairo_" + i, true, 0, Vector2.zero, -1);
        }
        // 随身門(楼門: Yaguramon A ×0.6, 通路=東西)
        var zj = Place(PYaguramon, Vector3.zero, 90f, Vector3.one * 0.6f, Group(GROUP, "Keidai/Mon"), "Zuijinmon");
        CenterSeat(zj, ZUIJIN.x, ZUIJIN.y, 0.25f);
        // 社殿群(東面, 権現造の代用: 拝殿→幣殿→本殿)
        var bg = Group(GROUP, "Keidai/Shaden");
        var haiden = Place(PHouse, Vector3.zero, 90f, Vector3.one, bg, "Haiden");
        CenterSeat(haiden, -519f, 857f);
        var heiden = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one * 0.66f, bg, "Heiden");
        CenterSeat(heiden, -533.5f, 857f);
        var honden = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one * 0.85f, bg, "Honden");
        CenterSeat(honden, -545f, 857f);
        // 本殿玉垣
        var tg = Group(GROUP, "Keidai/Tamagaki");
        Vector2 t0 = new Vector2(-553f, 849f), t1 = new Vector2(-537f, 849f), t2 = new Vector2(-537f, 865f), t3 = new Vector2(-553f, 865f);
        EdoNishiTameikeBuilder.DobeiRun(tg, t0, t1, new Vector2(0, -1), "TW_S", true, 0, Vector2.zero, -1);
        EdoNishiTameikeBuilder.DobeiRun(tg, t2, t3, new Vector2(0, 1), "TW_N", true, 0, Vector2.zero, -1);
        EdoNishiTameikeBuilder.DobeiRun(tg, t3, t0, new Vector2(-1, 0), "TW_W", true, 0, Vector2.zero, -1);
        // 神楽殿(北)・宝蔵(北西)・薬師堂/観音堂(南列)・不動堂/庚申堂(北列)
        var kagura = Place(PSmallHouse, Vector3.zero, 180f, Vector3.one * 0.8f, bg, "Kaguraden");
        CenterSeat(kagura, -512f, 882f);
        var hozo = Place(PKura, Vector3.zero, 180f, Vector3.one * ES, bg, "Hozo");
        CenterSeat(hozo, -556f, 884f);
        string[] doNames = { "Yakushido", "Kannondo", "Fudodo", "Koshindo" };
        Vector2[] doPos = { new Vector2(-508f, 828f), new Vector2(-526f, 828f), new Vector2(-533f, 886f), new Vector2(-548f, 830f) };
        float[] doYaw = { 0f, 0f, 180f, 0f };
        for (int i = 0; i < 4; i++)
        {
            var d = Place(PSmallHouse, Vector3.zero, doYaw[i], Vector3.one * 0.62f, bg, doNames[i]);
            CenterSeat(d, doPos[i].x, doPos[i].y);
        }
        // 手水舎(合成) + 鐘楼・鼓楼(合成)
        Chozuya(Group(GROUP, "Keidai/Props"), -496.5f, 846f);
        Shoro(Group(GROUP, "Keidai/Props"), -500f, 832f, true);
        Shoro(Group(GROUP, "Keidai/Props"), -498f, 884f, false);
        // 灯籠一対(拝殿前)
        foreach (var szn in new float[] { 851f, 863f })
        {
            var lp = AssetDatabase.LoadAssetAtPath<GameObject>(PKasuga) != null ? PKasuga : PBasket;
            var l = Place(lp, Vector3.zero, 90f, Vector3.one * 1.5f, Group(GROUP, "Keidai/Props"), "Toro_" + szn);
            CenterSeat(l, -510f, szn, 0.05f);
        }
        // 境内の松(まばら) + 石畳(飛石で代用: 随身門→拝殿)
        var rnd = new System.Random(20260811);
        var tr = Group(GROUP, "Keidai/Trees");
        int placed = 0, guard = 0;
        while (placed < 8 && guard++ < 300)
        {
            float px = Mathf.Lerp(-563f, -493f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(821f, 893f, (float)rnd.NextDouble());
            if (Mathf.Abs(pz - 857f) < 10f && px > -540f) continue; // 参道軸は開ける
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2 && px < rb2.max.x + 2 && pz > rb2.min.z - 2 && pz < rb2.max.z + 2) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.4f * (float)rnd.NextDouble())), tr, "Pine_" + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        var pgrp = Group(GROUP, "Keidai/Path");
        for (float px = -494f; px >= -512f; px -= 2.2f)
        {
            float y = Ground(px, 857f);
            var go = Place(PTobi, new Vector3(px, y + 0.03f, 857f), (float)rnd.NextDouble() * 360f, Vector3.one * 1.9f, pgrp, "Ishi_" + px);
            SeatBottom(go, y + 0.02f);
        }
        sb.AppendLine("keidai done");
        return sb.ToString();
    }

    // 手水舎: 4柱+屋根+水盤(Stone Basket)
    static void Chozuya(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Chozuya");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "chozuya");
        var wood = Mat(new Color(0.33f, 0.24f, 0.15f));
        var dark = Mat(new Color(0.16f, 0.16f, 0.18f));
        for (int i = 0; i < 4; i++)
        {
            var p = Cyl(g.transform, "post" + i, g.transform.position + new Vector3(i % 2 == 0 ? -1.4f : 1.4f, 1.5f, i < 2 ? -1.1f : 1.1f), new Vector3(0.2f, 1.5f, 0.2f), wood, Vector3.zero);
        }
        Box(g.transform, "roof", g.transform.position + new Vector3(0, 3.25f, 0), new Vector3(4.2f, 0.14f, 3.4f), dark);
        Box(g.transform, "mune", g.transform.position + new Vector3(0, 3.45f, 0), new Vector3(4.4f, 0.16f, 0.4f), dark);
        var basket = Place(PBasket, Vector3.zero, 0, Vector3.one * 1.4f, g.transform, "suiban");
        CenterSeat(basket, x, z, 0.05f);
    }

    // 鐘楼/鼓楼(合成)
    static void Shoro(Transform parent, float x, float z, bool bell)
    {
        float y = Ground(x, z);
        var g = new GameObject(bell ? "Shoro" : "Koro");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "shoro");
        var stone = Mat(new Color(0.58f, 0.57f, 0.54f));
        var wood = Mat(new Color(0.33f, 0.24f, 0.15f));
        var dark = Mat(new Color(0.16f, 0.16f, 0.18f));
        Box(g.transform, "Kidan", g.transform.position + new Vector3(0, 0.35f, 0), new Vector3(4.6f, 0.7f, 4.6f), stone);
        for (int i = 0; i < 4; i++)
            Cyl(g.transform, "Hashira", g.transform.position + new Vector3(i % 2 == 0 ? -1.5f : 1.5f, 2.45f, i < 2 ? -1.5f : 1.5f), new Vector3(0.28f, 1.75f, 0.28f), wood, Vector3.zero);
        Box(g.transform, "Nuki1", g.transform.position + new Vector3(0, 3.35f, 0), new Vector3(3.6f, 0.18f, 0.24f), wood);
        Box(g.transform, "Nuki2", g.transform.position + new Vector3(0, 3.35f, 0), new Vector3(0.24f, 0.18f, 3.6f), wood);
        for (int i = 0; i < 2; i++)
        {
            var roof = Box(g.transform, "Yane", g.transform.position + new Vector3(0, 4.75f, i == 0 ? -1.25f : 1.25f), new Vector3(5.4f, 0.12f, 2.9f), dark);
            roof.transform.rotation = Quaternion.Euler(i == 0 ? -22 : 22, 0, 0);
        }
        Box(g.transform, "Mune", g.transform.position + new Vector3(0, 5.3f, 0), new Vector3(5.6f, 0.22f, 0.4f), dark);
        if (bell)
        {
            var bellGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            bellGo.name = "Bonsho"; bellGo.transform.SetParent(g.transform, false);
            bellGo.transform.position = g.transform.position + new Vector3(0, 2.9f, 0);
            bellGo.transform.localScale = new Vector3(1.1f, 0.85f, 1.1f);
            bellGo.GetComponent<Renderer>().sharedMaterial = Mat(new Color(0.23f, 0.27f, 0.24f));
        }
        else
        {
            var drum = Cyl(g.transform, "Taiko", g.transform.position + new Vector3(0, 2.9f, 0), new Vector3(1.3f, 0.5f, 1.3f), Mat(new Color(0.55f, 0.20f, 0.12f)), new Vector3(90, 0, 0));
        }
    }

    // ---------- Stage 2: 男坂・仁王門・鳥居・女坂・つつ井 ----------
    // 石段=P_DanishiStep2m(汐見坂の段坂と同じ段石)+P_MichibataIshi2m(両脇の道端石)。
    public static string Stage2_Sando()
    {
        var root = GameObject.Find(GROUP);
        if (root != null && root.transform.Find("Sando") != null) return "SKIP: Sando exists";
        var sg = Group(GROUP, "Sando");
        var sb = new System.Text.StringBuilder();

        // 男坂石段: x StairX0(下)→StairX1(上), z=857, 幅6m(段石2m×3列)。蹴上0.30m。
        var stGrp = Group(GROUP, "Sando/Otokozaka");
        float h0 = Ground(StairX0, 857f), h1 = Ground(StairX1, 857f);
        int nStep = Mathf.CeilToInt((h1 - h0) / 0.30f);
        float rise = (h1 - h0) / nStep;
        float runX = (StairX1 - StairX0) / nStep;
        for (int i = 0; i < nStep; i++)
        {
            float x = StairX0 + runX * (i + 0.5f);
            float top = h0 + rise * (i + 1);
            for (int c = -1; c <= 1; c++)
            {
                var st = PlaceNative(PDanishi, new Vector3(x, top, 857f + c * 1.92f), 90f, stGrp, "Dan_" + i + "_" + (c + 1));
                var bs = RB(st);   // バウンズで天端=段レベル・中心=(x,z)に合わせる
                st.transform.position += new Vector3(x - bs.center.x, top - bs.max.y, 857f + c * 1.92f - bs.center.z);
            }
        }
        sb.AppendLine("otokozaka steps=" + nStep + " rise=" + rise.ToString("F3"));
        // 両脇の道端石(縁石)
        for (int s = -1; s <= 1; s += 2)
        {
            for (float x = StairX0 - 1.0f; x >= StairX1; x -= 2.05f)
            {
                float t = Mathf.Clamp01((x - StairX0) / (StairX1 - StairX0));
                float lvl = h0 + (h1 - h0) * t;
                var mi = PlaceNative(PMichibata, new Vector3(x, lvl, 857f + s * 3.25f), 0f, stGrp, "Kerb_" + s + "_" + x.ToString("F0"));
                var bm = RB(mi);
                mi.transform.position += new Vector3(x - bm.center.x, (lvl + 0.28f) - bm.max.y, 857f + s * 3.25f - bm.center.z);
            }
        }
        // 仁王門(Yaguramon A ×0.55) + 左右透塀
        var nio = Place(PYaguramon, Vector3.zero, 90f, Vector3.one * 0.55f, sg, "Niomon");
        CenterSeat(nio, NIO.x, NIO.y, 0.25f);
        var nb = RB(nio);
        var hei = Group(GROUP, "Sando/Sukibei");
        EdoNishiTameikeBuilder.DobeiRun(hei, new Vector2(NIO.x, 857f - 22f), new Vector2(NIO.x, nb.min.z - 0.3f), new Vector2(1, 0), "SB_S", true, 0, Vector2.zero, -1);
        EdoNishiTameikeBuilder.DobeiRun(hei, new Vector2(NIO.x, nb.max.z + 0.3f), new Vector2(NIO.x, 857f + 22f), new Vector2(1, 0), "SB_N", true, 0, Vector2.zero, -1);
        // 二ノ鳥居(石鳥居): 参道入口(小路の辻)に、通行方向=参道軸(TORII→男坂下)へ向ける
        Torii(sg, TORII.x, TORII.y, 0f);
        var tor = sg.Find("NinoTorii");
        var d2 = (APPROACH_MID - TORII).normalized;
        // 柱の並び軸を実測し、参道軸と直交するよう回す
        Transform hA = null, hB = null;
        foreach (Transform c in tor) { if (c.name == "hashira0") hA = c; if (c.name == "hashira1") hB = c; }
        if (hA != null && hB != null)
        {
            var sep = hB.position - hA.position; sep.y = 0; sep.Normalize();
            var want = new Vector3(-d2.y, 0, d2.x); // 参道軸の直交
            float delta = Vector3.SignedAngle(sep, want, Vector3.up);
            tor.rotation = Quaternion.AngleAxis(delta, Vector3.up) * tor.rotation;
            sb.AppendLine("torii aligned: delta=" + delta.ToString("F1"));
        }
        // つつ井(名水井戸)+茶店縁台: 参道入口の辻まわり(観理院の外)
        Tsutsui(sg, -396f, 894f);
        Endai(sg, -400f, 894f);
        Endai(sg, -408f, 892f);
        Endai(sg, -419f, 878.5f);
        // 女坂: 北を屈曲して登る雁木(段石の飛び踏面)
        var og = Group(GROUP, "Sando/Onnazaka");
        Vector2[] wpts = { new Vector2(-426f, 872f), new Vector2(-441f, 884f), new Vector2(-458f, 890f), new Vector2(-474f, 891f), new Vector2(-487f, 888f) };
        for (int seg = 0; seg < wpts.Length - 1; seg++)
        {
            Vector2 a = wpts[seg], b = wpts[seg + 1];
            float len = Vector2.Distance(a, b);
            int nt = Mathf.Max(2, Mathf.RoundToInt(len / 2.6f));
            for (int i = 0; i < nt; i++)
            {
                Vector2 p = Vector2.Lerp(a, b, (i + 0.5f) / nt);
                float y = Ground(p.x, p.y);
                float yaw = Mathf.Atan2(b.x - a.x, b.y - a.y) * Mathf.Rad2Deg + 90f;
                var st = PlaceNative(PDanishi, new Vector3(p.x, y, p.y), yaw, og, "W_" + seg + "_" + i);
                var bw = RB(st);
                st.transform.position += new Vector3(p.x - bw.center.x, (y + 0.14f) - bw.max.y, p.y - bw.center.z);
            }
        }
        SceneView.RepaintAll();
        return sb.ToString() + "sando done";
    }

    // 石鳥居(明神鳥居, 合成)
    static void Torii(Transform parent, float x, float z, float ry)
    {
        float y = Ground(x, z);
        var g = new GameObject("NinoTorii");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "torii");
        var stone = Mat(new Color(0.62f, 0.61f, 0.58f));
        float H = 7.2f, W = 6.4f;
        for (int i = 0; i < 2; i++)
        {
            var p = Cyl(g.transform, "hashira" + i, g.transform.position + new Vector3(0, H * 0.5f - 0.2f, (i == 0 ? -W : W) * 0.5f), new Vector3(0.62f, H * 0.5f, 0.62f), stone, new Vector3(0, 0, i == 0 ? -3f : 3f));
            // 亀腹
            Cyl(g.transform, "kamehara" + i, g.transform.position + new Vector3(0, 0.25f, (i == 0 ? -W : W) * 0.5f), new Vector3(0.95f, 0.25f, 0.95f), stone, Vector3.zero);
        }
        Box(g.transform, "shimaki", g.transform.position + new Vector3(0, H - 0.55f, 0), new Vector3(0.55f, 0.5f, W + 1.7f), stone);
        var kasagi = Box(g.transform, "kasagi", g.transform.position + new Vector3(0, H, 0), new Vector3(0.62f, 0.5f, W + 2.6f), stone);
        kasagi.transform.rotation = Quaternion.Euler(0, 0, 0);
        Box(g.transform, "nuki", g.transform.position + new Vector3(0, H - 1.75f, 0), new Vector3(0.4f, 0.42f, W + 1.1f), stone);
        Box(g.transform, "gakuzuka", g.transform.position + new Vector3(0, H - 1.15f, 0), new Vector3(0.35f, 0.75f, 0.5f), stone);
        g.transform.rotation = Quaternion.Euler(0, ry, 0);
    }

    // つつ井(屋形付き井戸)
    static void Tsutsui(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Tsutsui");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "tsutsui");
        var stone = Mat(new Color(0.55f, 0.55f, 0.52f));
        var wood = Mat(new Color(0.38f, 0.28f, 0.18f));
        var dark = Mat(new Color(0.18f, 0.18f, 0.20f));
        var curb = Cyl(g.transform, "curb", g.transform.position + new Vector3(0, 0.4f, 0), new Vector3(1.5f, 0.4f, 1.5f), stone, Vector3.zero);
        for (int i = 0; i < 4; i++)
            Cyl(g.transform, "post" + i, g.transform.position + new Vector3(i % 2 == 0 ? -1.3f : 1.3f, 1.45f, i < 2 ? -1.3f : 1.3f), new Vector3(0.14f, 1.45f, 0.14f), wood, Vector3.zero);
        Box(g.transform, "roof", g.transform.position + new Vector3(0, 3.05f, 0), new Vector3(3.6f, 0.12f, 3.6f), dark);
        Box(g.transform, "mune", g.transform.position + new Vector3(0, 3.22f, 0), new Vector3(3.8f, 0.14f, 0.4f), dark);
    }

    // 茶店の縁台(合成)
    static void Endai(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Endai");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "endai");
        var wood = Mat(new Color(0.52f, 0.40f, 0.26f));
        Box(g.transform, "ita", g.transform.position + new Vector3(0, 0.42f, 0), new Vector3(1.9f, 0.07f, 0.62f), wood, 12f);
        for (int i = 0; i < 4; i++)
            Box(g.transform, "ashi" + i, g.transform.position + new Vector3(i % 2 == 0 ? -0.8f : 0.8f, 0.2f, i < 2 ? -0.22f : 0.22f), new Vector3(0.08f, 0.4f, 0.08f), wood, 12f);
    }

    // ---------- Stage 3: 観理院 (2026-08-11改訂: 山麓の縦長大区画・表門=参道コリドー側NW辺) ----------
    public static string Stage3_Kanriin()
    {
        var root = GameObject.Find(GROUP_K);
        if (root != null && root.transform.childCount > 0) return "SKIP: Kanriin exists";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(GROUP_K, "Kakoi");
        var monGrp = Group(GROUP_K, "Omotemon");
        int N = KANRI.Length;
        // 表門位置: NW辺(参道コリドー沿い, 石段下正面)の中央
        Vector2 e2a = KANRI[2], e2b = KANRI[3];
        Vector2 gate = Vector2.Lerp(e2a, e2b, 0.5f);
        Vector2 edir = (e2b - e2a).normalized;
        Vector2 inw = new Vector2(edir.y, -edir.x);                 // (0.912,-0.410) 内向き
        Vector2 cenP = Vector2.zero; foreach (var p in KANRI) cenP += p; cenP /= N;
        if (Vector2.Dot(cenP - gate, inw) < 0) inw = -inw;
        // 練塀(s_hei 表裏ペア) 全周, NW辺は門で開口
        for (int i = 0; i < N; i++)
        {
            Vector2 a = KANRI[i], b = KANRI[(i + 1) % N];
            Vector2 mid = (a + b) * 0.5f;
            Vector2 outw = (mid - cenP); outw.Normalize();
            if (i == 2)
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Nerbei_Mon", true, 0, gate, 7.6f);
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Nerbei_" + i, true, 0, Vector2.zero, -1);
        }
        // 薬医門級(k_mon): 参道コリドー向き
        float psiIn = Mathf.Atan2(inw.x, inw.y) * Mathf.Rad2Deg;
        var mon = Place(PKmon, Vector3.zero, psiIn, Vector3.one * ES, monGrp, "Mon");
        CenterSeat(mon, gate.x, gate.y, 0.05f);
        // kagami(控柱)が内側かを検証
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
            { mon.transform.rotation *= Quaternion.Euler(0, 180, 0); CenterSeat(mon, gate.x, gate.y, 0.05f); sb.AppendLine("kanriin mon flipped"); }
        }
        // 書院群(北半の平坦帯 x-390〜-416): 客殿は門に正対(斜め軸)、奥書院翼・庫裏・土蔵
        var bg = Group(GROUP_K, "Buildings");
        float faceYaw = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;   // facade(+z)を門へ
        var kyaku = Place(PHouse, Vector3.zero, faceYaw, Vector3.one, bg, "Kyakuden");
        CenterSeat(kyaku, gate.x + inw.x * 15f, gate.y + inw.y * 15f);
        var kuri = Place(PSmallHouse, Vector3.zero, faceYaw + 90f, Vector3.one * 0.9f, bg, "Kuri");
        CenterSeat(kuri, -403f, 843f);
        var oku = Place(PHouseB, Vector3.zero, 0f, Vector3.one, bg, "Okushoin");
        CenterSeat(oku, -397f, 877f);
        var kura = Place(PKura, Vector3.zero, 90f, Vector3.one * ES, bg, "Kura");
        CenterSeat(kura, -397f, 800f);
        Ido(bg, -409f, 848f);
        // 庭: 南半は奥庭(松・岩組・灯籠), 前庭は飛石と刈込
        var gg = Group(GROUP_K, "Garden");
        var rnd = new System.Random(4649);
        System.Func<Vector2, bool> inPoly = p =>
        {
            bool inside = false;
            for (int i = 0, j = N - 1; i < N; j = i++)
                if (((KANRI[i].y > p.y) != (KANRI[j].y > p.y)) &&
                    (p.x < (KANRI[j].x - KANRI[i].x) * (p.y - KANRI[i].y) / (KANRI[j].y - KANRI[i].y) + KANRI[i].x)) inside = !inside;
            return inside;
        };
        int np = 0, guard = 0;
        while (np < 12 && guard++ < 600)
        {
            float px = Mathf.Lerp(-424f, -391f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(738f, 884f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!inPoly(p2)) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.2f && px < rb2.max.x + 2.2f && pz > rb2.min.z - 2.2f && pz < rb2.max.z + 2.2f) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.6f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + np);
            SeatBottom(go, y - 0.05f);
            np++;
        }
        for (int i = 0, g2 = 0; i < 9 && g2 < 400; g2++)
        {
            float px = Mathf.Lerp(-424f, -391f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(736f, 886f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!inPoly(p2)) continue;
            float y = Ground(px, pz);
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
            SeatBottom(go, y - 0.04f);
            i++;
        }
        // 岩組(奥庭 z~790)
        for (int r = 0; r < 4; r++)
        {
            float px = -406f + r * 1.7f, pz = 786f + r * 1.2f;
            float y = Ground(px, pz);
            var go = Place(Rocks[rnd.Next(Rocks.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * ((r == 0 ? 2.8f : 1.5f) * (0.85f + 0.4f * (float)rnd.NextDouble())), gg, "Iwa_" + r);
            SeatBottom(go, y - 0.22f);
        }
        // 飛石: 門→客殿玄関
        var kb = RB(kyaku.gameObject != null ? kyaku : null);
        Vector2 g0 = gate + inw * 2.5f;
        Vector2 g1 = new Vector2(kb.center.x, kb.center.z) - inw * 9f;
        int steps = Mathf.Max(3, Mathf.RoundToInt((g1 - g0).magnitude / 2.4f));
        for (int i = 0; i <= steps; i++)
        {
            float tt = (float)i / steps;
            Vector2 p = Vector2.Lerp(g0, g1, tt);
            float y = Ground(p.x, p.y);
            var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, gg, "Tobi_" + i);
            SeatBottom(go, y + 0.02f);
        }
        var lpick = AssetDatabase.LoadAssetAtPath<GameObject>(PKasuga) != null ? PKasuga : PBasket;
        var lg = Place(lpick, Vector3.zero, 0, Vector3.one * 1.4f, gg, "Toro");
        CenterSeat(lg, -410f, 862f, 0.03f);
        var lg2 = Place(lpick, Vector3.zero, 0, Vector3.one * 1.35f, gg, "Toro2");
        CenterSeat(lg2, -404f, 792f, 0.03f);
        return sb.ToString() + "kanriin done";
    }
    // 井戸(簡素)
    static void Ido(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "ido");
        var stone = Mat(new Color(0.55f, 0.55f, 0.52f));
        var wood = Mat(new Color(0.38f, 0.28f, 0.18f));
        Cyl(g.transform, "curb", g.transform.position + new Vector3(0, 0.35f, 0), new Vector3(1.3f, 0.35f, 1.3f), stone, Vector3.zero);
        for (int i = 0; i < 2; i++)
            Cyl(g.transform, "post" + i, g.transform.position + new Vector3(i == 0 ? -0.85f : 0.85f, 1.1f, 0), new Vector3(0.12f, 1.1f, 0.12f), wood, Vector3.zero);
    }

    // ---------- Stage 4: 樹下家邸 ----------
    public static string Stage4_Juge()
    {
        var root = GameObject.Find(GROUP_J);
        if (root != null && root.transform.childCount > 0) return "SKIP: Juge exists";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(GROUP_J, "Kakoi");
        var monGrp = Group(GROUP_J, "Omotemon");
        Vector2 gate = new Vector2(-446f, 900f);   // 南辺(参道広場向き)
        for (int i = 0; i < 4; i++)
        {
            Vector2 a = JUGE[i], b = JUGE[(i + 1) % 4];
            Vector2 mid = (a + b) * 0.5f;
            Vector2 cen = (JUGE[0] + JUGE[2]) * 0.5f;
            Vector2 outw = (mid - cen); outw.Normalize();
            if (i == 0)
                EdoSannoJuboBuilder.PanelRun(kak, a, new Vector2(gate.x + 3.9f, 900f), outw, "Itabei_0a", PItabei5, Vector2.zero, -1);
            else
                EdoSannoJuboBuilder.PanelRun(kak, a, b, outw, "Itabei_" + i, PItabei5, Vector2.zero, -1);
        }
        EdoSannoJuboBuilder.PanelRun(kak, new Vector2(gate.x - 3.9f, 900f), JUGE[3], new Vector2(0, -1), "Itabei_0b", PItabei5, Vector2.zero, -1);
        // 屋根付き門(腕木門)
        var mon = Place(PKabuki, Vector3.zero, 0f, Vector3.one * ES, monGrp, "Mon");
        CenterSeat(mon, gate.x, gate.y, 0.05f);
        float kmnz = float.MaxValue, kmxz = float.MinValue;
        foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
            foreach (var vtx in mf.sharedMesh.vertices) { var wp = mf.transform.TransformPoint(vtx); kmnz = Mathf.Min(kmnz, wp.z); kmxz = Mathf.Max(kmxz, wp.z); }
        }
        if (kmnz != float.MaxValue && (kmnz + kmxz) * 0.5f < RB(mon).center.z)
        { mon.transform.rotation *= Quaternion.Euler(0, 180, 0); CenterSeat(mon, gate.x, gate.y, 0.05f); sb.AppendLine("juge mon flipped"); }
        // 主屋(玄関付き武家屋敷風)+台所+物置+井戸+刈込
        var bg = Group(GROUP_J, "Buildings");
        var shu = Place(PHouse, Vector3.zero, 180f, Vector3.one * 0.92f, bg, "Shuoku");
        CenterSeat(shu, -449f, 918f);
        var dai = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one * 0.7f, bg, "Daidokoro");
        CenterSeat(dai, -434f, 926f);
        var mono = Place(PKura, Vector3.zero, 90f, Vector3.one * ES * 0.8f, bg, "Monooki");
        CenterSeat(mono, -464f, 928f);
        // 井戸(つつ井と同型の簡素版)
        var g = new GameObject("Ido");
        g.transform.SetParent(bg, false);
        float wy = Ground(-462f, 908f);
        g.transform.position = new Vector3(-462f, wy, 908f);
        var stone = Mat(new Color(0.55f, 0.55f, 0.52f));
        Cyl(g.transform, "curb", g.transform.position + new Vector3(0, 0.35f, 0), new Vector3(1.3f, 0.35f, 1.3f), stone, Vector3.zero);
        var gg = Group(GROUP_J, "Garden");
        var rnd = new System.Random(1210);
        for (int i = 0; i < 5; i++)
        {
            float px = Mathf.Lerp(-467f, -431f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(903f, 933f, (float)rnd.NextDouble());
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2f && px < rb2.max.x + 2f && pz > rb2.min.z - 2f && pz < rb2.max.z + 2f) { nearB = true; break; } }
            if (nearB) { i--; continue; }
            float y = Ground(px, pz);
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
            SeatBottom(go, y - 0.05f);
        }
        for (int i = 0; i < 6; i++)
        {
            float px = Mathf.Lerp(-468f, -430f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(902f, 934f, (float)rnd.NextDouble());
            float y = Ground(px, pz);
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Karikomi_" + i);
            SeatBottom(go, y - 0.04f);
        }
        return sb.ToString() + "juge done";
    }

    // ---------- Stage 5: 山王門前町 ----------
    public static string Stage5_Monzencho()
    {
        var exist = GameObject.Find(GROUP_M);
        if (exist != null && exist.transform.childCount > 0) return "SKIP: Monzencho exists";
        var root = Group(GROUP_M, null);
        var mS1 = MonzenMat("M_Shop01", EdoAssets.Eg.TexShop01);
        var mS2 = MonzenMat("M_Shop02", EdoAssets.Eg.TexShop02);
        int n = 0;
        for (int seg = 0; seg < MONZEN_ROAD.Length - 1; seg++)
        {
            Vector2 a = MONZEN_ROAD[seg], b = MONZEN_ROAD[seg + 1];
            Vector2 d = (b - a).normalized;
            Vector2 nrm = new Vector2(-d.y, d.x); // 左法線(北西側)
            float len = Vector2.Distance(a, b);
            for (float t = 5f; t <= len - 5f; t += 7.7f)
            {
                for (int side = 0; side < 2; side++)
                {
                    // 南側(丘側)は西寄り半分だけ(山裾)
                    if (side == 1 && seg == 0 && t > len * 0.6f) continue;
                    Vector2 c = a + d * t + nrm * (side == 0 ? 5.4f : -5.4f);
                    float y = Ground(c.x, c.y);
                    float yaw = Mathf.Atan2(-nrm.x, -nrm.y) * Mathf.Rad2Deg + (side == 0 ? 0f : 180f);
                    bool big = (n % 3 == 1);
                    var go = Place(big ? PShop02 : PShop01, new Vector3(c.x, y, c.y), yaw, Vector3.one * ES, root, "Monzen_" + n);
                    SeatBottom(go, y - 0.10f);
                    foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = big ? mS2 : mS1;
                    n++;
                }
            }
        }
        // 木戸(両端)
        for (int i = 0; i < 2; i++)
        {
            Vector2 p = i == 0 ? MONZEN_ROAD[0] + (MONZEN_ROAD[1] - MONZEN_ROAD[0]).normalized * 2f
                              : MONZEN_ROAD[2] + (MONZEN_ROAD[1] - MONZEN_ROAD[2]).normalized * 2f;
            Vector2 d = i == 0 ? (MONZEN_ROAD[1] - MONZEN_ROAD[0]).normalized : (MONZEN_ROAD[2] - MONZEN_ROAD[1]).normalized;
            float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;   // 木戸面(ローカルz)=通行方向

            var kido = Place(PKido, Vector3.zero, yaw, Vector3.one * ES, root, "Kido_" + i);
            CenterSeat(kido, p.x, p.y, 0.05f);
        }
        return "monzencho houses=" + n;
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

    // ---------- Stage 6: スプラット(参道広場・山麓の通り・門前町・境内・山の斜面) ----------
    public static string Stage6_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -600, x1 = -290, z0 = 720, z1 = 980;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        Func<Vector2, Vector2, Vector2, float> dSeg = (p, a, b) =>
        {
            var d = b - a; float len = d.magnitude; d /= len;
            float tt = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
            return (p - (a + d * tt)).magnitude;
        };
        Func<Vector2, Vector2[], float> dPoly = (p, pts) =>
        {
            float m = float.MaxValue;
            for (int i = 0; i < pts.Length - 1; i++) m = Mathf.Min(m, dSeg(p, pts[i], pts[i + 1]));
            return m;
        };
        Func<Vector2[], Vector2, bool> pip = (poly, p) =>
        {
            bool inside = false;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
                if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                    (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
            return inside;
        };
        Vector2[] onna = { new Vector2(-426f, 872f), new Vector2(-441f, 884f), new Vector2(-458f, 890f), new Vector2(-474f, 891f), new Vector2(-487f, 888f) };
        Vector2[] sandoAxis = { new Vector2(StairX0 + 2f, 857f), new Vector2(ZUIJIN.x - 6f, 857f) };
        Vector2[] approach = { TORII, APPROACH_MID, APPROACH_END };   // 鳥居→(観理院北角)→男坂下
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float bare = -1, grass = 0, dirt = 0;
                bool inJubo = false;
                foreach (var jb in EdoSannoJuboBuilder.Parcels)
                    if (pip(jb.poly, p)) { inJubo = true; break; }
                if (inJubo) continue;    // 十坊のスプラットは触らない(JuboBuilder担当)
                if (pip(PREC, p))
                {   // 境内=白砂利
                    bare = 0.72f; grass = 0.12f; dirt = 0.16f;
                }
                else if (pip(KANRI, p) || pip(JUGE, p))
                {
                    float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                    grass = Mathf.Lerp(0.35f, 0.6f, noise); bare = 0.22f; dirt = 1f - grass - bare;
                }
                else
                {
                    float dr = Mathf.Min(dPoly(p, BASE_ST), dPoly(p, MONZEN_ROAD));
                    float ds = dPoly(p, sandoAxis);
                    float da = dPoly(p, approach);
                    float dw = dPoly(p, onna);
                    // 鳥居の辻広場(小規模)
                    bool plaza = (p - TORII).magnitude < 8.5f;
                    if (plaza) { bare = 0.7f; grass = 0.1f; dirt = 0.2f; }
                    else if (ds < 3.6f || da < 3.4f) { bare = 0.62f; grass = 0.06f; dirt = 0.32f; }
                    else if (dr < 3.0f) { bare = 0.55f; grass = 0.05f; dirt = 0.40f; }
                    else if (dr < 4.5f) { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }
                    else if (dw < 1.6f) { bare = 0.45f; grass = 0.18f; dirt = 0.37f; }
                    else
                    {
                        float hgt = Ground(wx, wz);
                        if (hgt > 13.5f && wx > -580f && wx < -400f)
                        {   // 山の斜面=境内林の下草を濃く
                            float noise = Mathf.PerlinNoise(wx * 0.07f, wz * 0.07f);
                            grass = Mathf.Lerp(0.55f, 0.85f, noise); bare = 0.03f; dirt = 1f - grass - bare;
                        }
                        else if (wx >= -430f && hgt >= 7.5f)
                        {   // 東麓の平地(旧観理院跡・旧道筋・旧広場の塗り戻しを含む)=汎用の草地
                            float noise = Mathf.PerlinNoise(wx * 0.09f, wz * 0.09f);
                            grass = Mathf.Lerp(0.30f, 0.55f, noise); bare = 0.12f; dirt = 1f - grass - bare;
                        }
                    }
                }
                if (bare < 0) continue;
                float sum = bare + grass + dirt;
                for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                changed++;
            }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- Stage 7: 境内林(山の斜面の松・竹) ----------
    public static string Stage7_Keidairin()
    {
        var root = GameObject.Find(GROUP);
        if (root != null && root.transform.Find("Keidairin") != null) return "SKIP: Keidairin exists";
        var tg = Group(GROUP, "Keidairin");
        var rnd = new System.Random(777);
        string[] bam = {
            EdoAssets.JG.BambooBig01,
            EdoAssets.JG.BambooBig02 };
        int placed = 0, guard = 0;
        while (placed < 42 && guard++ < 2500)
        {
            float px = Mathf.Lerp(-585f, -405f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(770f, 950f, (float)rnd.NextDouble());
            float hgt = Ground(px, pz);
            if (hgt < 12.5f) continue;                                   // 麓は除外
            if (px > -566f && px < -490f && pz > 818f && pz < 896f) continue; // 境内内部は除外
            bool inJubo = false;                                          // 十坊の区画内は除外
            foreach (var jb in EdoSannoJuboBuilder.Parcels)
            {
                bool ins = false; var poly = jb.poly;
                for (int i2 = 0, j2 = poly.Length - 1; i2 < poly.Length; j2 = i2++)
                    if (((poly[i2].y > pz) != (poly[j2].y > pz)) &&
                        (px < (poly[j2].x - poly[i2].x) * (pz - poly[i2].y) / (poly[j2].y - poly[i2].y) + poly[i2].x)) ins = !ins;
                if (ins) { inJubo = true; break; }
            }
            if (inJubo) continue;
            if (Mathf.Abs(pz - 857f) < 6.5f && px > -492f && px < -416f) continue; // 男坂
            bool nearOnna = false;
            Vector2[] onna = { new Vector2(-426f, 872f), new Vector2(-441f, 884f), new Vector2(-458f, 890f), new Vector2(-474f, 891f), new Vector2(-487f, 888f) };
            for (int i = 0; i < onna.Length - 1; i++)
            {
                var d = onna[i + 1] - onna[i]; float len = d.magnitude; d /= len;
                float tt = Mathf.Clamp(Vector2.Dot(new Vector2(px, pz) - onna[i], d), 0, len);
                if ((new Vector2(px, pz) - (onna[i] + d * tt)).magnitude < 2.5f) { nearOnna = true; break; }
            }
            if (nearOnna) continue;
            float y = Ground(px, pz);
            bool useBam = rnd.NextDouble() < 0.18;
            string path = useBam ? bam[rnd.Next(bam.Length)] : Pines[rnd.Next(Pines.Length)];
            float sc = (useBam ? 1.5f : 1.7f) * (0.85f + 0.5f * (float)rnd.NextDouble());
            var go = Place(path, new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * sc, tg, (useBam ? "Bam_" : "Pine_") + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        return "keidairin trees=" + placed;
    }

    // ---------- 一括 ----------
    public static string BuildAll()
    {
        EdoNishiTameikeBuilder.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage1_Keidai());
        sb.AppendLine(Stage2_Sando());
        sb.AppendLine(Stage3_Kanriin());
        sb.AppendLine(Stage4_Juge());
        sb.AppendLine(Stage5_Monzencho());
        sb.AppendLine(Stage6_Splat());
        sb.AppendLine(Stage7_Keidairin());
        return sb.ToString();
    }
}
