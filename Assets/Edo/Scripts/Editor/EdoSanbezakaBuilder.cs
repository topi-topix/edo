// 三べ坂東街区ビルダー (2026-08-12)
//   赤=山王門前町(辻の角=嘉永版実見+参道両側の帯=ユーザー版(安政2以降)) 黄=五島兵部(富江領3000石交代寄合)
//   水=安部摂津守(武蔵岡部藩20,250石) 緑=勝田左京(3000石寄合) 紫=大岡八十一郎(嘉永版=大岡土佐守, 2000石)
//   白=小旗本6筆: 稲垣安太郎(馬場角)/奥村/佐藤/石井/浅井/満田(北の道+袋小路)
// 【考証 2026-08-12: Web調査+NDL1286657(外桜田永田町絵図・嘉永版)IIIF実見。絵図の上=シーンの東で照合確定】
//   ・東の南北道=「永田馬場」(絵図に道名実見)。北から稲垣→大岡→袋小路→勝田→五島が並び全て文字の頭=馬場向き
//     → 表門は東(馬場)。下書きの区割りと完全一致。
//   ・安部摂津守=安部信宝(天保13年4歳で家督/安政期当主。譜代・菊間広縁・無城2万250石。嘉永版表記=安部虎之助)。
//     絵図で家紋実見(丸に梶の葉=Web調査の家紋と一致)=上屋敷。表門=東の袋小路(勝田/大岡間の路地)の突き当り
//     (文字の頭=袋小路向き)。跡地=旧永田町小学校。三べ坂の名は岡部/安部/渡辺の3邸に由来。
//     寛政6年麹町から延焼で焼失。8代信亨の代「静遠館」新築詩会=文雅の家風。安政5年当主は大坂加番で在番。
//     門=2万石級無城譜代 → 長屋門(nagayamon)+格子出両番所(同格の土井大隅守と同格式)。
//   ・五島兵部=富江領五島家(福江藩分家3000石・交代寄合表御礼衆)。安政期当主=7代盛貫(家茂側役)。
//     「兵部」は世襲通称(国立公文書館「五島兵部江城築立被仰渡」)。門=長屋門h_mon+片番所(交代寄合の体面)。
//   ・勝田左京=月光院(家継生母)実家の旗本勝田家(正徳2年3000石・寄合)。「左京」=月光院「左京の局」由来の世襲通称。
//     門=h_mon+片番所。
//   ・大岡八十一郎=旗本大岡氏(大岡忠吉家2,300石が候補・推定)。嘉永版は「大岡土佐守」(版年で当主表記が違う)。
//     門=h_mon(番所なし)。
//   ・小旗本6筆=数百石級。囲い=板塀、門=腕木門(kabukimon)。嘉永版実見の並び: 馬場角=細田文哉?+稲垣安太郎/
//     北の道沿い西から石井?・佐藤?・[袋小路]・奥村?/内側に浅井?・満田?。W1-W5への個別割当は推定。
//   ・山王門前町: 嘉永版では辻の角の2筆(「山王門前」「町」実見)のみ。参道沿いの帯はユーザー版に従い再現。
//   ・安部北西の楔(スケッチ範囲外)=渡辺備中守(伯太藩)上屋敷 → 未再現。北の道→安部NW斜め道=三べ坂。
// 【地形】街区西半の「h12完全平坦+鋭い崖」=旧永田町小学校の校庭・校舎基礎(近代造成)。z955-975のトレンチ群も
//   基礎跡 → ラプラシアン緩和で台地縁の斜面へ復元([[terrain-follows-present-day]])。東半の台地(h26-29)は自然=不触。
// 【敷地内構成】各屋敷の指図は未発見のため一般類型(典拠: 格式論+屋敷類型§15)。池は典拠なし=作らない。
// 【2026-08-12 安部邸改修(シーン内直接編集。Stage3の座標は旧配置のまま=再実行しないこと)】
//   スキル§25(上屋敷類型)/§15適用: 奥御殿を表御殿の背後4.5mへ(近接分棟)・台所を表奥中間3.3mへ・
//   厩(knagaya l+r)と勝手井戸(Ido_Katte)を蔵の帯へ・邸内稲荷を庭の一隅(前庭北東)へ・
//   三べ坂盲長屋のNG_NW_2を撤去(SetActive false)し隣接2枚を妻キャップ(NG_NW_3r/NG_NW_1l)化して
//   藩士用小門(Uramon/Koguchimon=腕木門)を挿入。Kura_3は平坦帯(-284,992)へ。
// 【2026-08-12 密度是正(ユーザー指摘「建物が小さすぎ/少なすぎ」)】旧OmoteGoten/OkuGoten=SetActive(false)、
//   表御殿をManor複合体(x[-302,-240] z[1047,1085])へ格上げ。北帯z[1085,1099]を24へ延長造成(旧校庭envelope内)し
//   台所(×1.05)+長局(Nagatsubone)+井戸、南に中奥翼(NakaokuWing)+役所移設(z1035.5)、蔵4棟目、中間長屋第2対。
//   Seienkan(静遠館・詩会堂)は北西台地に納まらず SetActive(false) で保留。建蔽率9%→18%(外周長屋除く)。
// 【2026-08-12 家臣長屋4列を増築(KachuNagayaグループ)】典拠=一般類型(西川1959「御殿の外側に定府家臣の長屋」)。
//   西縁(h13.5-16, 勾配3%)にKN_W1/W2=向かい合わせ2列(各10棟・路地5.6m)、勝田境裏KN_E=6棟、
//   五島境裏KN_S=5棟(東端1棟は窪みspread1.31で退避)。造成ゼロ・段状接地。建蔽率23.5%(囲い込み26.8%)。
//   ⚠️【2026-08-13 訂正】KN_W1/W2 が面する西縁は「三べ坂」ではない。EdoSketch下書き(UserData/Sketches/
//   Assets_Edo_Scenes_Akasaka.unity.json)を色番号で読み直した結果(0=赤=渡辺備中守/1=黄=鳥居丹波守/
//   2=水色=松平主水正/3=緑=三べ坂)、赤(渡辺備中守=和泉伯太藩13,520石、未再現)の起点が安部ABE[1]
//   (-377.5,1060.5)と完全一致 → この西縁は**渡辺備中守邸との隣地境界**。本物の三べ坂(緑線、
//   (-495.9,1306.0)-(-422.4,1099.2))はそこからさらに59m北西の別区画で、現況の再現範囲外。
//   なお KN_W1/W2 のなまこ面(表)は敷地重心基準で確認済み=安部内側向き・裏が境界側(KN_E/KN_S と同一
//   規則で整合)なので、この訂正による建物の建て直しは不要(呼称のみの誤り)。渡辺邸を将来再現する際は
//   KN_W1(境界から6.5m)との間隔をOBBクリアランスで確認すること。
// 【2026-08-13 下段一郭を造成+建設(ユーザー指示: 下段にも御殿格の棟を)】
//   西半は旧永田町小学校の近代改変域なので段状造成が正当(§13b 段状テラス類型)。渡辺境フレーム
//   (eA=(-365.5,962.3)→eB=(-377.5,1060.5), inw0=内向き)で d19-46/t17-98 を TG=14.9+0.02(t-20) の
//   微傾斜パッドに切り、d46-62=法面、t74-93×d44-72=昇りランプ(下段16.4→御殿パッド24, 勾配30%)。
//   下段一郭: ShitadanGoten(House, 部屋住・隠居向)+SakujiYakusho(HouseB, 作事方)+Kura_5/6+Ido_Shitadan。
//   典拠=一般類型(下段=作事・役所・居住の一郭。高知藩麻布邸の作事系/§22内藤邸の低平帯役所と同型)。
//   建蔽率26.4%(外周込み30.0%)。地形バックアップ=scratchpad/abe_shitadan_backup_806_981_41x71.bin。
//   ⚠地形の注意: この斜面の実形状は不確定(ラプラシアン補間)。両端(東台地h26-29/西低地h13-14)は
//   GSI実測で確実だが中間の勾配分布は推定。明治期実測図(参謀本部五千分一等)で将来検証可。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSanbezakaBuilder
{
    public const string PNmon = EdoAssets.Eg.Nagayamon;
    public const string PHmon = EdoAssets.Eg.Hmon;
    public const string PKabuki = EdoAssets.Eg.Kabukimon;
    public const string PBansho = EdoAssets.Eg.Bansho;
    public const string PKura = EdoAssets.Eg.Kura;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    const string PItabei5 = EdoAssets.Eg.Itabei5;
    public const string PKnagayaL = EdoAssets.Eg.KnagayaL;
    public const string PKnagayaR = EdoAssets.Eg.KnagayaR;
    public const string PHouse = EdoAssets.VK.House;
    public const string PHouseB = EdoAssets.VK.HouseB;
    public const string PSmallHouse = EdoAssets.VK.SmallHouse;
    public const string PBigHouse = EdoAssets.VK.BigHouse;
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
    public const string PTobi = EdoAssets.JG.TobiIshi01;
    public const float ES = 1.818f;

    // ---------- 参道(山王坂)軸: EdoSannoBukeBuilder.SANDO_AXIS と同一 ----------
    public static float AxisZ(float x) { return 894f + (x + 371f) * (5f / 240f); }

    // ---------- 区画(下書きスナップ済) ----------
    public static readonly Vector2[] GOTO = {
        new Vector2(-135.5f, 911.4f), new Vector2(-238.5f, 909.3f), new Vector2(-238.5f, 901.8f),
        new Vector2(-331.5f, 899.9f), new Vector2(-342.4f, 950.6f), new Vector2(-332.1f, 951.0f),
        new Vector2(-332.1f, 962.0f), new Vector2(-338.6f, 962.0f), new Vector2(-328.6f, 982.5f),
        new Vector2(-139.3f, 982.5f) };
    public static readonly Vector2[] ABE = {
        new Vector2(-365.5f, 962.3f), new Vector2(-377.5f, 1060.5f), new Vector2(-295.0f, 1126.5f),
        new Vector2(-258.6f, 1104.6f), new Vector2(-222.0f, 1102.8f), new Vector2(-213.7f, 1070.5f),
        new Vector2(-222.8f, 1070.5f), new Vector2(-222.8f, 1062.5f), new Vector2(-216.0f, 1062.5f),
        new Vector2(-216.0f, 982.5f), new Vector2(-328.6f, 982.5f), new Vector2(-338.6f, 962.0f) };
    public static readonly Vector2[] KATSUTA = {
        new Vector2(-139.3f, 982.5f), new Vector2(-216.0f, 982.5f), new Vector2(-216.0f, 1062.5f),
        new Vector2(-141.8f, 1062.5f) };
    public static readonly Vector2[] OOKA = {
        new Vector2(-141.8f, 1070.5f), new Vector2(-213.7f, 1070.5f), new Vector2(-224.0f, 1122.7f),
        new Vector2(-144.3f, 1121.3f) };
    // 小旗本6筆: W1=満田? W2=浅井? W3=石井? W4=佐藤? W5=奥村? W6=稲垣安太郎(馬場角)
    public static readonly Vector2[] W1 = {
        new Vector2(-222.0f, 1102.8f), new Vector2(-224.6f, 1121.5f), new Vector2(-246.9f, 1130.9f),
        new Vector2(-258.6f, 1104.6f) };
    public static readonly Vector2[] W2 = {
        new Vector2(-259.9f, 1106.7f), new Vector2(-294.0f, 1126.5f), new Vector2(-291.2f, 1179.2f),
        new Vector2(-277.6f, 1178.5f), new Vector2(-281.0f, 1137.2f), new Vector2(-256.7f, 1136.3f),
        new Vector2(-248.2f, 1132.4f) };
    public static readonly Vector2[] W3 = {
        new Vector2(-257.4f, 1138.6f), new Vector2(-279.0f, 1139.1f), new Vector2(-276.3f, 1177.9f),
        new Vector2(-257.1f, 1176.5f) };
    public static readonly Vector2[] W4 = {
        new Vector2(-229.4f, 1127.0f), new Vector2(-257.0f, 1139.2f), new Vector2(-254.6f, 1174.4f),
        new Vector2(-229.4f, 1173.7f) };
    public static readonly Vector2[] W5 = {
        new Vector2(-224.0f, 1124.4f), new Vector2(-224.0f, 1173.1f), new Vector2(-183.8f, 1172.3f),
        new Vector2(-184.4f, 1123.0f) };
    public static readonly Vector2[] W6 = {
        new Vector2(-182.0f, 1123.6f), new Vector2(-181.5f, 1170.4f), new Vector2(-146.2f, 1170.3f),
        new Vector2(-145.7f, 1121.8f) };

    // 表門 (全て切絵図の文字の頭に基づく)
    static readonly Vector2 GATE_GOTO = new Vector2(-137.6f, 950.0f);     // 馬場向き(E)
    static readonly Vector2 GATE_KATSUTA = new Vector2(-140.6f, 1025.0f); // 馬場向き(E)
    static readonly Vector2 GATE_OOKA = new Vector2(-143.1f, 1096.0f);    // 馬場向き(E)
    static readonly Vector2 GATE_ABE = new Vector2(-222.8f, 1066.5f);     // 袋小路突き当り(E)
    static readonly Vector2 GATE_W1 = new Vector2(-235.7f, 1126.2f);      // 袋小路西枝(NNW)
    static readonly Vector2 GATE_W2 = new Vector2(-284.4f, 1178.9f);      // 北の道
    static readonly Vector2 GATE_W3 = new Vector2(-266.7f, 1177.2f);
    static readonly Vector2 GATE_W4 = new Vector2(-242.0f, 1174.1f);
    static readonly Vector2 GATE_W5 = new Vector2(-204.0f, 1172.7f);
    static readonly Vector2 GATE_W6 = new Vector2(-146.0f, 1146.0f);      // 馬場向き(E)

    // ---------- helpers ----------
    public static float Ground(float x, float z) { return EdoNishiTameikeBuilder.Ground(x, z); }
    public static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    { return EdoNishiTameikeBuilder.Place(path, pos, ry, scale, parent, name); }
    public static Bounds RB(GameObject go) { return EdoNishiTameikeBuilder.RB(go); }
    static void SeatBottom(GameObject go, float y) { EdoNishiTameikeBuilder.SeatBottom(go, y); }
    public static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
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
    public static bool PIP(Vector2[] poly, Vector2 p)
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
    public static Vector2 InwardNormal(Vector2[] poly, int i)
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
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++) m = Mathf.Min(m, DistToEdge(p, poly[i], poly[(i + 1) % poly.Length]));
        return m;
    }
    static Material Mat(Color c) { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; }
    public static void CenterSeat(GameObject go, float x, float z, float sink = 0.12f)
    {
        var b = RB(go);
        go.transform.position += new Vector3(x - b.center.x, 0, z - b.center.z);
        b = RB(go);
        float gmn = float.MaxValue;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
            gmn = Mathf.Min(gmn, Ground(b.center.x + i * b.extents.x, b.center.z + j * b.extents.z));
        go.transform.position += new Vector3(0, (gmn - sink) - b.min.y, 0);
    }
    public static float PlaceGate(string path, Transform monGrp, Vector2 gate, Vector2 fout, int bansho, string name, System.Text.StringBuilder sb)
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
    public static void FrontWall(Transform kak, Vector2 a, Vector2 b, Vector2 outw, Vector2 gate, float gateHalf, string prefix, bool itabei = false)
    {
        Vector2 dir = (b - a).normalized;
        Vector2 gL = gate - dir * (gateHalf - 0.15f), gR = gate + dir * (gateHalf - 0.15f);
        if (Vector2.Distance(a, gL) > 1.6f && Vector2.Dot(gL - a, dir) > 0)
        {
            if (itabei) EdoSannoJuboBuilder.PanelRun(kak, a, gL, outw, prefix + "_L", PItabei5, Vector2.zero, -1);
            else EdoNishiTameikeBuilder.DobeiRun(kak, a, gL, outw, prefix + "_L", true, 0, Vector2.zero, -1);
        }
        if (Vector2.Distance(gR, b) > 1.6f && Vector2.Dot(b - gR, dir) > 0)
        {
            if (itabei) EdoSannoJuboBuilder.PanelRun(kak, gR, b, outw, prefix + "_R", PItabei5, Vector2.zero, -1);
            else EdoNishiTameikeBuilder.DobeiRun(kak, gR, b, outw, prefix + "_R", true, 0, Vector2.zero, -1);
        }
    }
    public static void Well(Transform parent, float x, float z)
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
    static Material MonzenMat(string name, string texPath)
    {
        string mp = "Assets/Edo/Materials/" + name + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(mp);
        if (m != null) return m;
        m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        var tx = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        if (tx != null) m.mainTexture = tx;
        AssetDatabase.CreateAsset(m, mp);
        return m;
    }
    static void ApplyShopMat(GameObject go, Material m)
    {
        foreach (var r in go.GetComponentsInChildren<Renderer>())
        { var arr = r.sharedMaterials; for (int i = 0; i < arr.Length; i++) arr[i] = m; r.sharedMaterials = arr; }
    }
    // 主屋+台所+蔵+井戸 の小旗本セット
    static void HatamotoSet(string grpName, Vector2[] poly, Vector2 gate, Vector2 fout, float houseScale, System.Text.StringBuilder sb, int kura = 0, float houseV = 16f)
    {
        var bg = Group(grpName, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        Vector2 inw = -fout;
        Vector2 c = gate + inw * houseV;
        var shu = Place(PSmallHouse, Vector3.zero, yawGate, Vector3.one * houseScale, bg, "Shuoku");
        CenterSeat(shu, c.x, c.y);
        Well(bg, (gate + inw * 9f + new Vector2(fout.y, -fout.x) * 5f).x, (gate + inw * 9f + new Vector2(fout.y, -fout.x) * 5f).y);
        for (int i = 0; i < kura; i++)
        {
            Vector2 kc = gate + inw * 25f + new Vector2(fout.y, -fout.x) * (-6f - i * 8f);
            if (!PIP(poly, kc)) kc = gate + inw * 22f;
            var kr = Place(PKura, Vector3.zero, yawGate + 90f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, kc.x, kc.y);
        }
        // 坪庭: 奥の隅に松2+刈込2
        var gg = Group(grpName, "Garden");
        var rnd = new System.Random(grpName.GetHashCode() & 0x7fff);
        for (int i = 0, gd = 0; i < 4 && gd < 250; gd++)
        {
            float mnx = poly.Min(p => p.x), mxx = poly.Max(p => p.x);
            float mnz = poly.Min(p => p.y), mxz = poly.Max(p => p.y);
            float px = Mathf.Lerp(mnx, mxx, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(mnz, mxz, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(poly, p2) || DistToPolyEdge(poly, p2) < 2.5f) continue;
            if (Vector2.Dot(p2 - gate, inw) < 22f) continue;   // 前庭は空ける
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.6)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.55f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.5f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
    }

    // ---------- Stage 0: 地形 (backup→旧永田町小学校の基礎跡を緩和) ----------
    public static string Stage0_Terrain()
    {
        var sb = new System.Text.StringBuilder();
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<float, float> HtoW = hn => hn * ts.y + tp.y;

        // backup (x[-385,-130] z[895,1195])
        int bx0 = IX(-385f), bx1 = IX(-130f), bz0 = IZ(895f), bz1 = IZ(1195f);
        int bw = bx1 - bx0 + 1, bh = bz1 - bz0 + 1;
        var bak = td.GetHeights(bx0, bz0, bw, bh);
        string bakPath = "/private/tmp/claude-501/-Users-toshio-project-edo-unity/6b8eed4b-5ca1-445b-86a2-734f1c70def7/scratchpad/sanbezaka_backup_" + bx0 + "_" + bz0 + "_" + bw + "x" + bh + ".bin";
        if (!System.IO.File.Exists(bakPath))
        {
            using (var bwr = new System.IO.BinaryWriter(System.IO.File.Open(bakPath, System.IO.FileMode.Create)))
            { bwr.Write(bx0); bwr.Write(bz0); bwr.Write(bw); bwr.Write(bh);
              for (int z = 0; z < bh; z++) for (int x = 0; x < bw; x++) bwr.Write(bak[z, x]); }
            sb.AppendLine("backup " + bw + "x" + bh + " -> " + bakPath);
        }
        else sb.AppendLine("backup exists (kept): " + bakPath);

        // --- 旧永田町小学校(校庭h12盆地+校舎基礎トレンチ)のラプラシアン緩和 ---
        {
            int x0 = IX(-382f), x1 = IX(-186f), z0 = IZ(908f), z1 = IZ(1160f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            var mov = new bool[h, w]; int nm = 0;
            for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
            {
                float wx = tp.x + (x0 + x) * ts.x / (hres - 1);
                float wz = tp.z + (z0 + z) * ts.z / (hres - 1);
                if (wx < -333f && wz < 963f) continue;          // 門前町一帯の自然低地は固定
                if (HtoW(H[z, x]) < 24.5f) { mov[z, x] = true; nm++; }
            }
            for (int it = 0; it < 1100; it++)
            {
                var H2 = (float[,])H.Clone();
                for (int z = 1; z < h - 1; z++) for (int x = 1; x < w - 1; x++)
                    if (mov[z, x]) H2[z, x] = (H[z - 1, x] + H[z + 1, x] + H[z, x - 1] + H[z, x + 1]) * 0.25f;
                H = H2;
            }
            td.SetHeightsDelayLOD(x0, z0, H);
            sb.AppendLine("school relax cells=" + nm);
        }
        td.SyncHeightmap();
        return sb.ToString();
    }

    // ---------- Stage 1: 門前町 (既存 Monzen_0-6/Kido は不触。並木の支障分を SetActive(false)) ----------
    public static string Stage1_Monzencho()
    {
        const string G = "Edo_Sanno_Monzencho";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var root = Group(G, "");
        if (root.Find("MonzenS_0") != null) return "SKIP Monzencho";
        var mS1 = MonzenMat("M_Shop01", EdoAssets.Eg.TexShop01);
        var mS2 = MonzenMat("M_Shop02", EdoAssets.Eg.TexShop02);
        // 支障並木を無効化: 北列は全部(五島塀/町屋帯の内側に立つ)、南列は町屋帯区間のみ
        var sha = GameObject.Find("Edo_Sanno_Sha");
        int off = 0;
        if (sha != null)
            foreach (var tr in sha.GetComponentsInChildren<Transform>(true))
            {
                if (!tr.name.StartsWith("Namiki_") || tr.name == "Namiki") continue;
                var parts = tr.name.Split('_');
                if (parts.Length < 3) continue;
                float d; float s;
                if (!float.TryParse(parts[1], out d) || !float.TryParse(parts[2], out s)) continue;
                bool kill = (s > 0f) || (s < 0f && d >= 133f);
                if (kill && tr.gameObject.activeSelf) { tr.gameObject.SetActive(false); off++; }
            }
        sb.AppendLine("namiki off=" + off);
        // 参道両側の表店 (ユーザー版の帯: 南 x[-237,-137] / 北 x[-237.5,-137])
        var rnd = new System.Random(4649);
        int n = 0;
        for (float x = -236.5f; x < -138f; x += 8.1f)
        {
            bool big = (n % 3 == 1);
            float axis = AxisZ(x + 3f);
            // 南側: 前面=axis-4.5、奥へ
            float zc = axis - 4.5f - 3.2f;
            var go = Place(big ? PShop02 : PShop01, Vector3.zero, 181.2f, Vector3.one * ES, root, "MonzenS_" + n);
            ApplyShopMat(go, big ? mS2 : mS1);
            CenterSeat(go, x, zc, 0.10f);
            // 北側: 前面=axis+4.5
            float zc2 = axis + 4.5f + 3.2f;
            var go2 = Place(big ? PShop01 : PShop02, Vector3.zero, 1.2f, Vector3.one * ES, root, "MonzenN_" + n);
            ApplyShopMat(go2, big ? mS1 : mS2);
            CenterSeat(go2, x + 4.0f, zc2, 0.10f);
            n++;
        }
        // 西の門前町拡張: (a)小路沿い x-371.8面(既存の南北列の南延長+北延長)
        float[] zS = { 905.5f, 911.2f, 943.0f };
        for (int i = 0; i < zS.Length; i++)
        {
            bool big = (i == 1);
            var go = Place(big ? PShop02 : PShop01, Vector3.zero, 270f, Vector3.one * ES, root, "MonzenW_" + i);
            ApplyShopMat(go, big ? mS2 : mS1);
            CenterSeat(go, -368.4f, zS[i], 0.10f);
        }
        // (b)参道向き x-334..-343 (idx4南)
        for (int i = 0; i < 2; i++)
        {
            float x = -336.5f - i * 5.6f;
            float axis = AxisZ(x);
            var go = Place(i == 0 ? PShop01 : PShop02, Vector3.zero, 181.2f, Vector3.one * ES, root, "MonzenT_" + i);
            ApplyShopMat(go, i == 0 ? mS1 : mS2);
            CenterSeat(go, x, axis + 4.5f + 3.2f, 0.10f);
        }
        // (c)三べ坂向き (idx4北帯 x-365線, z950-961)
        for (int i = 0; i < 2; i++)
        {
            float z = 953.2f + i * 5.6f;
            var go = Place(i == 0 ? PShop01 : PShop02, Vector3.zero, 270f, Vector3.one * ES, root, "MonzenSB_" + i);
            ApplyShopMat(go, i == 0 ? mS1 : mS2);
            CenterSeat(go, -361.5f, z, 0.10f);
        }
        // 裏の井戸2
        Well(root, -190f, AxisZ(-190f) + 10.5f);
        Well(root, -350f, 930f);
        return sb.ToString() + "monzen shops=" + (n * 2 + 7);
    }

    // ---------- Stage 2: 五島兵部 (富江領3000石交代寄合) ----------
    public static string Stage2_Goto()
    {
        const string G = "Edo_Yashiki_GotoHyobu";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Goto";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(GOTO, 9);   // 辺9(E=馬場)
        float gateHalf = PlaceGate(PHmon, monGrp, GATE_GOTO, fout, 1, "Hmon", sb);
        int N = GOTO.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = GOTO[i], b = GOTO[(i + 1) % N];
            Vector2 outw = -InwardNormal(GOTO, i);
            if (i == 7) continue;                                        // 安部所有(共有diag)
            else if (i == 8)
                EdoNishiTameikeBuilder.DobeiRun(kak, new Vector2(-216.0f, 982.5f), b, outw, "Hei_8", true, 0, Vector2.zero, -1); // 勝田境のみ(西半は安部所有)
            else if (i == 9)
                FrontWall(kak, a, b, outw, GATE_GOTO, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var shu = Place(PHouseB, Vector3.zero, yawGate, Vector3.one, bg, "Shuoku");
        CenterSeat(shu, -166f, 950f);
        var dd = Place(PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 0.85f, bg, "Daidokoro");
        CenterSeat(dd, -186f, 962f);
        for (int i = 0; i < 2; i++)
        {
            var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -198f - i * 9f, 928f);
        }
        Well(bg, -178f, 960f);
        var gg = Group(G, "Garden");
        var rnd = new System.Random(3000);
        for (int i = 0, gd = 0; i < 26 && gd < 1500; gd++)
        {
            float px = Mathf.Lerp(-330f, -145f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(905f, 980f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(GOTO, p2) || DistToPolyEdge(GOTO, p2) < 3.5f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float v = Vector2.Dot(p2 - GATE_GOTO, -fout);
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_GOTO, new Vector2(fout.y, -fout.x)));
            if (v > -2f && v < 26f && u < 15f) continue;                 // 門前白洲
            float y = Ground(px, pz);
            if (y < 17f && px < -280f)
            {
                var go = Place(Bamboo[rnd.Next(2)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Take_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else if (rnd.NextDouble() < 0.68)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.62f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "goto done";
    }

    // ---------- Stage 3: 安部摂津守上屋敷 (地形パッド込み) ----------
    public static string Stage3_Abe()
    {
        const string G = "Edo_Yashiki_AbeSettsu";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Abe";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;

        // --- 御殿パッド(近代改変域=旧小学校内のみ): 目標=緩和後地盤の丸め ---
        {
            var t = Terrain.activeTerrain; var td = t.terrainData;
            int hres = td.heightmapResolution;
            Vector3 tp = t.transform.position, ts = td.size;
            Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
            Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
            float avg = 0;
            avg += Ground(-240f, 1050f); avg += Ground(-240f, 1085f);
            avg += Ground(-295f, 1050f); avg += Ground(-295f, 1085f);
            avg *= 0.25f;
            float TG = Mathf.Clamp(Mathf.Round(avg), 22f, 27f);
            int x0 = IX(-312f), x1 = IX(-228f), z0 = IZ(1030f), z1 = IZ(1104f);
            int w = x1 - x0 + 1, h = z1 - z0 + 1;
            var H = td.GetHeights(x0, z0, w, h);
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
            {
                float wx = tp.x + (x0 + x) * ts.x / (hres - 1);
                float wz = tp.z + (z0 + z) * ts.z / (hres - 1);
                var p = new Vector2(wx, wz);
                if (!PIP(ABE, p) || DistToPolyEdge(ABE, p) < 1.5f) continue;
                if (wx < -306f || wx > -232f || wz < 1036f || wz > 1098f) continue;
                float ex = Mathf.Min(Mathf.Clamp01((wx + 306f) / 6f), Mathf.Clamp01((-232f - wx) / 6f));
                float ez = Mathf.Min(Mathf.Clamp01((wz - 1036f) / 6f), Mathf.Clamp01((1098f - wz) / 6f));
                float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(ex, ez));
                float cur = (H[z, x] * ts.y + tp.y);
                H[z, x] = ((Mathf.Lerp(cur, TG, k)) - tp.y) / ts.y;
            }
            td.SetHeightsDelayLOD(x0, z0, H);
            td.SyncHeightmap();
            sb.AppendLine("goten pad TG=" + TG);
        }

        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        // 表門=東の袋小路突き当り。長屋門(22.5m)は湾口(8m)より広く、両翼は敷地内で塀の背後に隠れる。
        // 袋小路の湾内に番所を置く物理的余地が無いため bansho=0(長屋門自体が番所部屋を内蔵する形式)。
        Vector2 fout = new Vector2(1f, 0f);
        float gateHalf = PlaceGate(PNmon, monGrp, GATE_ABE, fout, 0, "Nagayamon", sb);
        int N = ABE.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = ABE[i], b = ABE[(i + 1) % N];
            Vector2 outw = -InwardNormal(ABE, i);
            if (i == 1)
                EdoNishiTameikeBuilder.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_NW");   // 三べ坂沿い=盲長屋
            else if (i == 6)
                FrontWall(kak, a, b, outw, GATE_ABE, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var og = Place(PBigHouse, Vector3.zero, yawGate, Vector3.one, bg, "OmoteGoten");
        CenterSeat(og, -252f, 1066f);
        var yk = Place(PHouseB, Vector3.zero, yawGate + 90f, Vector3.one, bg, "Yakusho");
        CenterSeat(yk, -243f, 1091f);
        var okg = Place(PHouse, Vector3.zero, yawGate, Vector3.one, bg, "OkuGoten");
        CenterSeat(okg, -288f, 1057f);
        var dd = Place(PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 0.9f, bg, "Daidokoro");
        CenterSeat(dd, -282f, 1085f);
        for (int i = 0; i < 3; i++)
        {
            var kr = Place(PKura, Vector3.zero, 90f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -262f - i * 9f, 1005f);
        }
        // 中間長屋(表の脇・南東)
        var n1 = Place(PKnagayaL, Vector3.zero, 180f, Vector3.one * ES, bg, "ChugenNagaya_L");
        CenterSeat(n1, -236f, 995f);
        var n2 = Place(PKnagayaR, Vector3.zero, 180f, Vector3.one * ES, bg, "ChugenNagaya_R");
        CenterSeat(n2, -228.2f, 995f);
        Well(bg, -274f, 1080f);
        // 庭: 西斜面=松+刈込、低地(h<18)=竹林 (溜池への借景)
        var gg = Group(G, "Garden");
        var rnd = new System.Random(20250);
        for (int i = 0, gd = 0; i < 40 && gd < 2200; gd++)
        {
            float px = Mathf.Lerp(-372f, -230f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(968f, 1120f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(ABE, p2) || DistToPolyEdge(ABE, p2) < 4f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float v = Vector2.Dot(p2 - GATE_ABE, -fout);
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_ABE, new Vector2(fout.y, -fout.x)));
            if (v > -2f && v < 30f && u < 18f) continue;                 // 門前白洲
            float y = Ground(px, pz);
            if (y < 18f)
            {
                var go = Place(Bamboo[rnd.Next(2)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Take_" + i);
                SeatBottom(go, y - 0.05f);
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
        // 門→表御殿の飛石
        for (float tt = 0; tt <= 1.001f; tt += 0.1f)
        {
            Vector2 p = Vector2.Lerp(GATE_ABE + new Vector2(-4f, 0f), new Vector2(-238f, 1066f), tt);
            float y = Ground(p.x, p.y);
            var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, gg, "Tobi_" + tt);
            SeatBottom(go, y + 0.02f);
        }
        return sb.ToString() + "abe done";
    }

    // ---------- Stage 4: 勝田左京 ----------
    public static string Stage4_Katsuta()
    {
        const string G = "Edo_Yashiki_KatsutaSakyo";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Katsuta";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(KATSUTA, 3);   // 辺3(E=馬場)
        float gateHalf = PlaceGate(PHmon, monGrp, GATE_KATSUTA, fout, 1, "Hmon", sb);
        // 辺0(S)=五島所有skip 辺1(W)=安部所有skip 辺2(N=小路)=own 辺3(E)=FrontWall
        EdoNishiTameikeBuilder.DobeiRun(kak, KATSUTA[2], KATSUTA[3], -InwardNormal(KATSUTA, 2), "Hei_2", true, 0, Vector2.zero, -1);
        FrontWall(kak, KATSUTA[3], KATSUTA[0], -InwardNormal(KATSUTA, 3), GATE_KATSUTA, gateHalf + 0.5f, "Hei_F");
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var shu = Place(PHouse, Vector3.zero, yawGate, Vector3.one * 0.95f, bg, "Shuoku");
        CenterSeat(shu, -168f, 1024f);
        var dd = Place(PSmallHouse, Vector3.zero, yawGate + 90f, Vector3.one * 0.8f, bg, "Daidokoro");
        CenterSeat(dd, -186f, 1037f);
        for (int i = 0; i < 2; i++)
        {
            var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -198f - i * 9f, 1000f);
        }
        Well(bg, -180f, 1034f);
        var gg = Group(G, "Garden");
        var rnd = new System.Random(3001);
        for (int i = 0, gd = 0; i < 12 && gd < 800; gd++)
        {
            float px = Mathf.Lerp(-213f, -145f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(986f, 1060f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(KATSUTA, p2) || DistToPolyEdge(KATSUTA, p2) < 3f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float v = Vector2.Dot(p2 - GATE_KATSUTA, -fout);
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_KATSUTA, new Vector2(fout.y, -fout.x)));
            if (v > -2f && v < 22f && u < 13f) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.65)
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
        return sb.ToString() + "katsuta done";
    }

    // ---------- Stage 5: 大岡八十一郎 ----------
    public static string Stage5_Ooka()
    {
        const string G = "Edo_Yashiki_OokaYasoichiro";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Ooka";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 fout = -InwardNormal(OOKA, 3);   // 辺3(E=馬場)
        float gateHalf = PlaceGate(PHmon, monGrp, GATE_OOKA, fout, 0, "Hmon", sb);
        // 辺0(S=小路)=own 辺1(W)=安部所有skip 辺2(N=W5/W6境)=own 辺3(E)=FrontWall
        EdoNishiTameikeBuilder.DobeiRun(kak, OOKA[0], OOKA[1], -InwardNormal(OOKA, 0), "Hei_0", true, 0, Vector2.zero, -1);
        EdoNishiTameikeBuilder.DobeiRun(kak, OOKA[2], OOKA[3], -InwardNormal(OOKA, 2), "Hei_2", true, 0, Vector2.zero, -1);
        FrontWall(kak, OOKA[3], OOKA[0], -InwardNormal(OOKA, 3), GATE_OOKA, gateHalf + 0.5f, "Hei_F");
        var bg = Group(G, "Buildings");
        float yawGate = Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg;
        var shu = Place(PHouse, Vector3.zero, yawGate, Vector3.one * 0.85f, bg, "Shuoku");
        CenterSeat(shu, -170f, 1096f);
        var kr1 = Place(PKura, Vector3.zero, 90f, Vector3.one * ES, bg, "Kura_1");
        CenterSeat(kr1, -198f, 1082f);
        Well(bg, -184f, 1104f);
        var gg = Group(G, "Garden");
        var rnd = new System.Random(2000);
        for (int i = 0, gd = 0; i < 9 && gd < 600; gd++)
        {
            float px = Mathf.Lerp(-220f, -148f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(1073f, 1119f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!PIP(OOKA, p2) || DistToPolyEdge(OOKA, p2) < 3f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float v = Vector2.Dot(p2 - GATE_OOKA, -fout);
            float u = Mathf.Abs(Vector2.Dot(p2 - GATE_OOKA, new Vector2(fout.y, -fout.x)));
            if (v > -2f && v < 20f && u < 12f) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.6)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.58f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "ooka done";
    }

    // ---------- Stage 6: 小旗本6筆 (板塀+腕木門) ----------
    public static string Stage6_Kohatamoto()
    {
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var defs = new[] {
            new { G = "Edo_Yashiki_MitsudaW1", poly = W1, gate = GATE_W1, gateEdge = 1, scale = 0.82f, kura = 0, houseV = 13f },
            new { G = "Edo_Yashiki_AsaiW2",    poly = W2, gate = GATE_W2, gateEdge = 2, scale = 0.9f,  kura = 1, houseV = 16f },
            new { G = "Edo_Yashiki_IshiiW3",   poly = W3, gate = GATE_W3, gateEdge = 2, scale = 0.85f, kura = 0, houseV = 16f },
            new { G = "Edo_Yashiki_SatoW4",    poly = W4, gate = GATE_W4, gateEdge = 2, scale = 0.85f, kura = 0, houseV = 16f },
            new { G = "Edo_Yashiki_OkumuraW5", poly = W5, gate = GATE_W5, gateEdge = 1, scale = 0.9f,  kura = 1, houseV = 16f },
            new { G = "Edo_Yashiki_InagakiW6", poly = W6, gate = GATE_W6, gateEdge = 2, scale = 0.95f, kura = 1, houseV = 15f } };
        // 塀の所有(重複防止): 安部境/大岡境は上位側所有=skip。W2-W3/W3-W4/W5-W6 の間は一方のみ建てる
        var own = new Dictionary<string, int[]> {
            { "Edo_Yashiki_MitsudaW1", new[] { 0, 1 } },
            { "Edo_Yashiki_AsaiW2",    new[] { 1, 2, 3, 4, 5, 6 } },
            { "Edo_Yashiki_IshiiW3",   new[] { 2, 3 } },
            { "Edo_Yashiki_SatoW4",    new[] { 0, 2, 3 } },
            { "Edo_Yashiki_OkumuraW5", new[] { 0, 1, 2 } },
            { "Edo_Yashiki_InagakiW6", new[] { 1, 2 } } };
        foreach (var d in defs)
        {
            var exist = GameObject.Find(d.G);
            if (exist != null && exist.transform.childCount > 0) { sb.AppendLine("SKIP " + d.G); continue; }
            var kak = Group(d.G, "Kakoi");
            var monGrp = Group(d.G, "Omotemon");
            Vector2 fout = -InwardNormal(d.poly, d.gateEdge);
            float gateHalf = PlaceGate(PKabuki, monGrp, d.gate, fout, 0, "Kabukimon", sb);
            int N = d.poly.Length;
            foreach (int i in own[d.G])
            {
                Vector2 a = d.poly[i], b = d.poly[(i + 1) % N];
                Vector2 outw = -InwardNormal(d.poly, i);
                if (i == d.gateEdge)
                    FrontWall(kak, a, b, outw, d.gate, gateHalf + 0.4f, "Itabei_F", true);
                else
                    EdoSannoJuboBuilder.PanelRun(kak, a, b, outw, "Itabei_" + i, PItabei5, Vector2.zero, -1);
            }
            HatamotoSet(d.G, d.poly, d.gate, fout, d.scale, sb, d.kura, d.houseV);
        }
        return sb.ToString() + "kohatamoto done";
    }

    // ---------- Stage 7: スプラット(道・敷地・畑) ----------
    public static string Stage7_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -388, x1 = -124, z0 = 880, z1 = 1195;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        Vector2[] babaRoad = { new Vector2(-129.5f, 892f), new Vector2(-131.5f, 911f), new Vector2(-136.2f, 982f),
            new Vector2(-138.9f, 1062f), new Vector2(-141.3f, 1121f), new Vector2(-143.4f, 1170f), new Vector2(-145.5f, 1195f) };
        Vector2[] northRoad = { new Vector2(-293.5f, 1182.5f), new Vector2(-224f, 1177.5f), new Vector2(-146f, 1173.5f) };
        Vector2[] sanbeRoad = { new Vector2(-381.5f, 1053f), new Vector2(-298.5f, 1129.5f), new Vector2(-294.5f, 1182.5f) };
        Vector2[] lane1 = { new Vector2(-222.6f, 1066.5f), new Vector2(-141f, 1066.5f) };
        Vector2[] lane2 = { new Vector2(-226.7f, 1173.5f), new Vector2(-226.7f, 1128f), new Vector2(-250f, 1133.5f) };
        Func<Vector2, Vector2[], float> dPoly = (p, pts) =>
        {
            float m = float.MaxValue;
            for (int i = 0; i < pts.Length - 1; i++) m = Mathf.Min(m, DistToEdge(p, pts[i], pts[i + 1]));
            return m;
        };
        Vector2[][] parcels = { GOTO, ABE, KATSUTA, OOKA, W1, W2, W3, W4, W5, W6 };
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                if (wx < -374f) continue;                        // 樹下・観理院・岡部側は不触
                float axis = AxisZ(wx);
                float bare = -1, grass = 0, dirt = 0;
                bool inSandoCore = (wz > axis - 4.5f && wz < axis + 4.5f && wx > -372f && wx < -128f);
                if (inSandoCore) continue;                       // 既存の参道舗装は不触
                Vector2[] inP = null;
                foreach (var pp in parcels) if (PIP(pp, p)) { inP = pp; break; }
                float db = dPoly(p, babaRoad), dn = dPoly(p, northRoad), ds = dPoly(p, sanbeRoad);
                float d1 = dPoly(p, lane1), d2 = dPoly(p, lane2);
                bool machiyaBand = (wx > -239f && wx < -134f && ((wz >= 884.2f && wz < axis - 4.5f) || (wz > axis + 4.5f && wz <= axis + 12.5f)));
                bool monzenW = (wx > -373f && wx < -332f && wz > 901f && wz < 962f);
                if (inP != null)
                {
                    bool shirasu = false;
                    float v = Vector2.Dot(p - GATE_ABE, new Vector2(-1f, 0f)), u = Mathf.Abs(wz - GATE_ABE.y);
                    if (inP == ABE && v > -1f && v < 28f && u < 17f) shirasu = true;
                    if (shirasu) { bare = 0.62f; grass = 0.08f; dirt = 0.30f; }
                    else if (inP == GOTO && wx < -250f && wz < 960f)
                    { bare = 0.20f; grass = 0.22f; dirt = 0.58f; }       // 五島西南=畑・作業地
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.38f, 0.65f, noise); bare = 0.14f; dirt = 1f - grass - bare;
                    }
                }
                else if (machiyaBand || monzenW) { bare = 0.42f; grass = 0.12f; dirt = 0.46f; }
                else if (db < 4.5f || dn < 3.5f || ds < 3.5f || d1 < 3.0f || d2 < 2.2f) { bare = 0.55f; grass = 0.05f; dirt = 0.40f; }
                else if (db < 6.0f || dn < 5.0f || ds < 5.0f || d1 < 4.2f || d2 < 3.4f) { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }
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
        sb.AppendLine(Stage1_Monzencho());
        sb.AppendLine(Stage2_Goto());
        sb.AppendLine(Stage3_Abe());
        sb.AppendLine(Stage4_Katsuta());
        sb.AppendLine(Stage5_Ooka());
        sb.AppendLine(Stage6_Kohatamoto());
        sb.AppendLine(Stage7_Splat());
        return sb.ToString();
    }
}
