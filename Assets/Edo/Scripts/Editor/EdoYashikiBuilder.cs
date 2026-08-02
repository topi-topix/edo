using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 溜池の南（葵坂沿い）に、幕末の切絵図にある三つの武家屋敷を建てる。
///
///   1. 太田善太夫  1225坪  旗本屋敷  … 導水路(Road B)に面する。広重「葵坂」の赤枠の建物がこれ。
///   2. 加納備中守  1599坪  大名(上総一宮藩1万3千石)中屋敷 … 葵坂の追分角地。
///   3. 松平備前守  6975坪  大名上屋敷 … 葵坂沿いの街区をまるごと占める。
///
/// 造成の考え方（ブックマーク#3/#4 の指示「石垣を積んで、その上に屋敷を配置」）:
///   ・敷地ポリゴン内を水平な壇(padY)に均し、周囲を Castle Wall の石垣で土留めする。
///   ・石垣は敷地ごとに position.y / scale.y が単一 → 天端は一直線（unity-modular-stonewall R1）。
///   ・天端の上に築地塀(Wall Exterior Defence)を廻し、表門の位置だけ塀を切って門を据える。
///   ・門の外は坂(スロープ)を地形に刻むので、街路から壇へ上がって入れる。
///   ・大名屋敷は表通り側の塀の内側に長屋(長屋塀)を通す。これが広重の絵の白壁＋瓦屋根の列。
///
/// メニュー:
///   Edo ▸ 建造 ▸ 武家屋敷 ▸ 三屋敷をすべて建てる
///   Edo ▸ 建造 ▸ 武家屋敷 ▸ 太田善太夫 / 加納備中守 / 松平備前守（個別）
///   Edo ▸ 建造 ▸ 武家屋敷 ▸ 造成前の地形に戻す
///
/// 再実行すると各グループを作り直す。地形は最初の造成時に Library/ へ退避する（Undo 不可のため）。
/// </summary>
public static class EdoYashikiBuilder
{
    // ---- 石垣（Castle Wall キット） ----
    // 石垣の作法は太田屋敷（手で組んだ基準）から採寸した値。
    // Castle Wall はローカル X∈[-2.4,0] が厚み、Z∈[-2.0,0] が走り。scale 1 で 2.4m 厚 × 2.0m モジュール。
    // 敷地ポリゴン＝石垣の「外面」。頂点を時計回りに辿ると胴が敷地内側に入る。
    const float ISHI_DROP = 8.0f;   // 既定の天端→基部の高さ(m)。scale.y = ISHI_DROP/4（Site 側で上書き可）
    const float ISHI_STEP = 1.80f;  // 直線部のピッチ(m)。モジュール2.0mを0.2m重ねる
    const float ISHI_SX = 1.0f;     // = 厚み2.4m
    const float ISHI_SZ = 1.0f;     // = 走り方向2.0m
    const float ISHI_CORNER_SZ = 1.0f; // 出隅は XZ 正方（R4）
    const float ISHI_MOD = 2.4f;    // scale 1 でのローカル寸法(m)
    // 石垣の天端は庭の地面より PARAPET だけ高い＝土留めの立ち上がり。築地塀はその天端に乗る。
    // 庭はほぼ自然地盤なりに置くので、門は街路とほぼ同じ高さで開く（壇の上に載せない）。
    const float PARAPET = 1.5f;

    // ---- 土塀（edogoyomi es_dobei）----
    // ピボットは足元。走りはローカル +X、厚みは z 対称。実測で継ぎ目は 0.01m 以下に収まる。
    const string P_HEI = "Assets/edogoyomi/es_dobei/s_hei_center.obj";
    const string P_HEI_COR = "Assets/edogoyomi/es_dobei/s_hei_corner.obj";
    const float HEI_PITCH = 1.64f * EDO_SCALE;   // 2.982m
    const float HEI_BACK = 1.30f * EDO_SCALE;    // 原点から左端までの距離 2.364m
    const float HEI_FWD = 0.34f * EDO_SCALE;     // 原点から右端までの距離 0.618m
    // 見えている厚み(±0.575m)は瓦の笠木で、壁の本体は ±0.172m（足元の幅木は ±0.219m）。
    // 面一にすべきは【壁の下方の面】なので、ピボットからその面までの 0.172m だけ内へ寄せる。
    const float HEI_BODY = 0.172f;

    // ---- 長屋（edogoyomi es_knagaya）----
    // 胴はすべて原点の -Z 側。街路に面するのは -Z の面。足元はピボットより 1.836m 下。
    const string P_NAGAYA_C = "Assets/edogoyomi/es_knagaya/knagaya01c.obj";
    const string P_NAGAYA_L = "Assets/edogoyomi/es_knagaya/knagaya01l.obj";
    const string P_NAGAYA_R = "Assets/edogoyomi/es_knagaya/knagaya01r.obj";
    const float NG_PITCH = 4.45f * EDO_SCALE;    // 8.090m
    const float NG_LIFT = 1.01f * EDO_SCALE;     // 1.836m
    const float NG_FRONT = 4.773f;   // 原点から街路側の【壁面】まで。軒は 5.363m まで出るので軒で合わせない
    const float NG_BACK = 2.42f * EDO_SCALE;     // 原点から左端まで 4.400m
    const float NG_HALF = 2.03f * EDO_SCALE;     // 原点から右端まで 3.691m

    // ---- 表門 ----
    // 表門は edogoyomi（HONEY「江戸街並みシリーズ」）の実物モデル。1間=1.818m でモデリングされている。
    const float EDO_SCALE = 1.818f;
    const string G_HMON = "Assets/edogoyomi/es_hmon/h_mon.obj";        // 旗本屋敷の長屋門 15.4m
    const string G_NMON = "Assets/edogoyomi/es_nmon/nagayamon.obj";    // 大名屋敷の長屋門 22.5m
    const string G_KMON = "Assets/edogoyomi/es_kmon/k_mon.obj";        // 大名屋敷の表門 14.4m
    const string G_BANSHO = "Assets/edogoyomi/es_dbansho/dbansho.obj"; // 出番所（k_mon と同じ原点で作られている）

    static float _gateOpen = 6f;    // 石垣・塀を切る幅(m)。門モデルの実幅から決まる
    const float RAMP_LEN = 22.0f;   // 門の外へ刻む坂の長さ(m)

    // ---- 長屋 ----
    const float NAGAYA_OUT = 3.6f;  // 表側の壁の内寄せ(m)
    const float NAGAYA_DEPTH = 4.0f;
    const float NAGAYA_WALL_H = 3.0f;

    // ---- 造成 ----
    const float GRADE_FEATHER = 14.0f; // 切土側の摺り付け(m)
    // 水平な壇は境界より GRADE_INSET だけ内側で終える。石垣は厚み4.8mで境界から内へ張るので、
    // 高低差のすり替わりが石垣の“中”で起きる＝外から見ると石垣の面が根元まで出る。
    // 水平な壇はこの分だけ外面より内側で終える。高低の摺り付けが石垣の胴(2.4m)の中に隠れ、
    // 外面では自然地盤のままになるので石垣の面が根元まで出る。
    const float GRADE_INSET = 2.2f;
    const string SNAPSHOT = "EdoYashiki_terrain_before.bin";

    const string P_WALL = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Castle Wall.prefab";
    const string P_WALL_CORNER = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Castle Wall Corner.prefab";
    const string P_HEI8 = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence x 8.prefab";
    const string P_HEI1 = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence.prefab";
    const string P_HEI_CORNER = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence Corner.prefab";
    const string P_GATE = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior.prefab";
    const string P_GATE_L = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior End L.prefab";
    const string P_GATE_R = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior End R.prefab";
    const string P_NAGAYA_OUT = "Assets/Japanese Village Kit/Prefabs/Shopping Streets/Wall Shop Plaster x 8.prefab";
    const string P_NAGAYA_IN = "Assets/Japanese Village Kit/Prefabs/Shopping Streets/Wall Shop Wood x 8.prefab";
    const string P_ROOF_SLOPE = "Assets/Japanese Village Kit/Prefabs/Roofs/roof 2x8.prefab";
    const string P_ROOF_TOP = "Assets/Japanese Village Kit/Prefabs/Roofs/roof top x8.prefab";
    const string P_TREE = "Assets/Edo/Terrain/details/BroadleafTree.prefab";

    // ===================== 敷地定義 =====================

    /// <summary>建物は「表門の位置を原点、u=表通りに沿う向き、v=敷地の奥行き」のローカル座標で置く。</summary>
    class Building
    {
        public string prefab;
        public float u, v, relYaw;
        public Building(string p, float u_, float v_, float y) { prefab = p; u = u_; v = v_; relYaw = y; }
    }

    class Site
    {
        public string group;
        public string label;
        public Vector2[] poly;    // 石垣の外面（時計回り／反時計回りどちらでも可・内部で時計回りに揃える）
        public float padY;        // 庭の地面の高さ(world Y)。石垣の天端は padY + PARAPET
        public float ishiDrop;    // 石垣の高さ(天端→基部)。敷地の高低差に合わせる
        // 石垣を残すかどうかは Site ごとの設定ではなく、常に「残す」が既定。
        // 作り直すのは「石垣も作り直す」メニューを明示的に選んだときだけ。
        public int gateEdge;      // 表門を置く辺（表通りに面する辺）
        public float gateT;       // その辺のどこか(0..1)
        public string gatePrefab; // 表門のモデル（家格に合わせる）
        public string gateSub;    // 門に添える出番所など（無ければ null）
        public int[] nagayaEdges;    // 石垣がまだ無いときの長屋の辺
        public int[] nagayaFromGate; // 石垣から実測したときの長屋の辺（門のある辺を0とした相対）
        public Building[] buildings;
        public Vector2[] trees;   // (u,v)
    }

    // Village Kit の建物
    const string B_MANOR = "Assets/Japanese Village Kit/Prefabs/Manor.prefab";
    const string B_BIG = "Assets/Japanese Village Kit/Prefabs/Big House.prefab";
    const string B_HOUSE = "Assets/Japanese Village Kit/Prefabs/House.prefab";
    const string B_HOUSE_A = "Assets/Japanese Village Kit/Prefabs/House A.prefab";
    const string B_HOUSE_B = "Assets/Japanese Village Kit/Prefabs/House B.prefab";
    const string B_SMALL = "Assets/Japanese Village Kit/Prefabs/Small House.prefab";

    // 区画はユーザーが手で組み直した太田の石垣から実測した外面ポリゴンが基準。
    // 太田の4隅を実測 → 加納・松平はその辺を共有するように取り直した（3区画が隙間なく街区を分ける）。
    //   D=(53.10,243.01) A=(116.77,298.36) B=(160.40,275.16) C=(88.88,212.98)  ← 太田（実測）
    //   P5,Q,P6,P7,P8 はブックマーク#5 のマーク
    static readonly Vector2 V_D = new Vector2( 53.10f, 243.01f);
    static readonly Vector2 V_A = new Vector2(116.77f, 298.36f);
    static readonly Vector2 V_B = new Vector2(160.40f, 275.16f);
    static readonly Vector2 V_C = new Vector2( 88.88f, 212.98f);
    static readonly Vector2 V_P5 = new Vector2( 50.70f, 328.40f);
    static readonly Vector2 V_Q = new Vector2( -8.21f, 290.91f);
    static readonly Vector2 V_P6 = new Vector2(-39.50f, 271.00f);
    static readonly Vector2 V_P7 = new Vector2(-126.90f, 209.40f);
    static readonly Vector2 V_P8 = new Vector2(-12.90f, 113.60f);

    static Site[] Sites()
    {
        var ota = new Site
        {
            group = "Edo_Yashiki_Ota",
            label = "太田善太夫 1250坪 (旗本屋敷)",
            poly = new[] { V_D, V_A, V_B, V_C },
            padY = 8.5f, ishiDrop = 6.0f,        // 天端 10.0（手組みの石垣に一致）。自然地盤 平均8.9
            gateEdge = 2, gateT = 0.571f,        // 辺 B→C ＝ 南東の表通り側。既存石垣の開口位置に合わせた
            gatePrefab = G_HMON,                 // 旗本屋敷の長屋門（readme に "gate of hatamoto's mansion"）
            nagayaEdges = new[] { 2 }, nagayaFromGate = new[] { 0 },
            // 間口91m×奥行44mの短冊形なので、主屋・台所・土蔵を表通りと平行に一列に並べる
            buildings = new[] {
                new Building(B_HOUSE,  -26f, 20f, 180f),
                new Building(B_SMALL,   10f, 26f, 180f),
                new Building(B_HOUSE_B, 30f, 20f,  90f),
            },
            trees = new[] { new Vector2(-8f, 32f), new Vector2(-42f, 14f), new Vector2(20f, 33f), new Vector2(-14f, 10f) },
        };

        var kano = new Site
        {
            group = "Edo_Yashiki_Kano",
            label = "加納備中守 1617坪 (上総一宮藩 中屋敷)",
            poly = new[] { V_D, V_Q, V_P5, V_A },
            padY = 12.5f, ishiDrop = 8.0f,       // 天端 14.0。自然地盤 平均12.4。太田より高い
            gateEdge = 1, gateT = 0.45f,         // 辺 Q→P5 ＝ 葵坂側
            gatePrefab = G_NMON,                 // 大名屋敷の長屋門
            nagayaEdges = new[] { 1, 2 }, nagayaFromGate = new[] { 0, 1 },   // 葵坂側と堰へ向かう道の側
            buildings = new[] {
                new Building(B_BIG,     20f, 36f, 180f),
                new Building(B_HOUSE_A, -6f, 26f, 180f),
                new Building(B_SMALL,    6f, 60f,   0f),
                new Building(B_SMALL,   46f, 42f,  90f),
            },
            trees = new[] { new Vector2(-10f, 44f), new Vector2(32f, 18f), new Vector2(30f, 58f), new Vector2(-12f, 14f) },
        };

        var matsu = new Site
        {
            group = "Edo_Yashiki_Matsudaira",
            label = "松平備前守直正 5800坪 (上屋敷)",
            poly = new[] { V_D, V_C, V_P8, V_P7, V_P6, V_Q },
            padY = 12.0f, ishiDrop = 8.0f,       // 天端 13.5。自然地盤 平均10.8
            gateEdge = 3, gateT = 0.42f,         // 辺 P7→P6 ＝ 葵坂側
            gatePrefab = G_KMON, gateSub = G_BANSHO,  // 上屋敷なので格式の高い表門＋出番所
            nagayaEdges = new[] { 3, 5 }, nagayaFromGate = new[] { 0, 1 },   // 葵坂側と、太田・加納に面する北東側
            buildings = new[] {
                new Building(B_MANOR,   38f,  72f,  90f),   // 御殿。長手を表通りと平行に
                new Building(B_BIG,     -8f,  34f, 180f),
                new Building(B_HOUSE_A, 66f,  28f, 180f),
                new Building(B_HOUSE,   62f, 115f,  90f),
                new Building(B_SMALL,    8f, 112f,   0f),
                new Building(B_SMALL,   16f, 128f,   0f),
                new Building(B_HOUSE_B, -8f,  94f,  90f),
            },
            trees = new[] {
                new Vector2(16f, 16f),  new Vector2(46f, 20f),  new Vector2(-16f, 54f), new Vector2(70f, 60f),
                new Vector2(24f, 34f),  new Vector2(-14f, 94f), new Vector2(70f, 88f),  new Vector2(-2f, 92f),
                new Vector2(38f, 124f), new Vector2(50f, 46f),
            },
        };

        return new[] { ota, kano, matsu };
    }

    // ===================== メニュー =====================

    // 既にシーンにある石垣は、手で直されている可能性があるので既定では絶対に壊さない。
    // 作り直したいときだけ「石垣も作り直す」メニューから明示的に行う。
    static bool _rebuildIshigaki = false;

    [MenuItem("Edo/建造/武家屋敷/三屋敷をすべて建てる")]
    static void BuildAll()
    {
        SnapshotTerrain();
        foreach (var s in Sites()) Build(s);
        Flush();
    }

    [MenuItem("Edo/建造/武家屋敷/太田善太夫（旗本屋敷）")]
    static void BuildOta() { SnapshotTerrain(); Build(Sites()[0]); Flush(); }

    [MenuItem("Edo/建造/武家屋敷/加納備中守（中屋敷）")]
    static void BuildKano() { SnapshotTerrain(); Build(Sites()[1]); Flush(); }

    [MenuItem("Edo/建造/武家屋敷/松平備前守（上屋敷）")]
    static void BuildMatsu() { SnapshotTerrain(); Build(Sites()[2]); Flush(); }

    [MenuItem("Edo/建造/武家屋敷/石垣も作り直す（手直しは失われます）")]
    static void RebuildWithIshigaki()
    {
        int n = 0;
        foreach (var s in Sites())
        {
            var g = GameObject.Find(s.group);
            var i = g == null ? null : g.transform.Find("Ishigaki");
            if (i != null) n += i.childCount;
        }
        if (!EditorUtility.DisplayDialog("石垣を作り直しますか？",
                "シーンにある石垣 " + n + " 枚をすべて破棄して、スクリプトから生成し直します。\n" +
                "手で動かした位置・追加した石垣は元に戻せません。\n\n" +
                "続ける前に、シーンを保存してコミットしておくことを強くすすめます。",
                "作り直す", "やめる")) return;
        _rebuildIshigaki = true;
        try { SnapshotTerrain(); foreach (var s in Sites()) Build(s); Flush(); }
        finally { _rebuildIshigaki = false; }
    }

    [MenuItem("Edo/建造/武家屋敷/造成前の地形に戻す")]
    static void RestoreTerrain()
    {
        var t = Terrain.activeTerrain;
        var td = t.terrainData;
        int R = td.heightmapResolution;
        string path = Path.Combine(Application.dataPath, "../Library/" + SNAPSHOT);
        if (!File.Exists(path)) { Debug.LogError("[Yashiki] snapshot not found: " + path); return; }
        var bytes = File.ReadAllBytes(path);
        if (bytes.Length != R * R * 4) { Debug.LogError("[Yashiki] snapshot size mismatch"); return; }
        var arr = new float[R, R];
        int bi = 0;
        for (int z = 0; z < R; z++)
            for (int x = 0; x < R; x++) { arr[z, x] = System.BitConverter.ToSingle(bytes, bi); bi += 4; }
        td.SetHeights(0, 0, arr);
        Debug.Log("[Yashiki] terrain restored from " + SNAPSHOT);
    }

    static void Flush()
    {
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene());
    }

    // ===================== 造成 =====================

    static void SnapshotTerrain()
    {
        string path = Path.Combine(Application.dataPath, "../Library/" + SNAPSHOT);
        if (File.Exists(path)) return;   // 最初の一回だけ
        var td = Terrain.activeTerrain.terrainData;
        int R = td.heightmapResolution;
        var full = td.GetHeights(0, 0, R, R);
        var bytes = new byte[R * R * 4];
        int bi = 0;
        for (int z = 0; z < R; z++)
            for (int x = 0; x < R; x++) { System.Array.Copy(System.BitConverter.GetBytes(full[z, x]), 0, bytes, bi, 4); bi += 4; }
        File.WriteAllBytes(path, bytes);
        Debug.Log("[Yashiki] terrain snapshot -> Library/" + SNAPSHOT);
    }

    static Vector2[][] _otherPolys;   // Grade 中だけ使う、隣の屋敷の敷地

    /// <summary>点 p が自分以外の屋敷の敷地内かどうか。摺り付けで隣の壇を削らないための判定。</summary>
    static bool InAnyOther(Site self, Vector2 p)
    {
        if (_otherPolys == null) return false;
        foreach (var o in _otherPolys) if (SignedDist(o, p) > 0f) return true;
        return false;
    }

    /// <summary>敷地内を padY の水平面に均し、切土側だけ外へ摺り付ける。門前には坂を刻む。</summary>
    static void Grade(Site s, Vector2[] poly, float padY, Vector2 gateMid, Vector2 gateOutDir)
    {
        var t = Terrain.activeTerrain;
        var td = t.terrainData;
        var tp = t.transform.position;
        int R = td.heightmapResolution;
        float cell = td.size.x / (R - 1);

        var others = new System.Collections.Generic.List<Vector2[]>();
        foreach (var o in Sites()) if (o.group != s.group) others.Add(o.poly);
        _otherPolys = others.ToArray();

        float margin = GRADE_FEATHER + RAMP_LEN + 12f;
        float mnx = 1e9f, mxx = -1e9f, mnz = 1e9f, mxz = -1e9f;
        foreach (var v in poly) { mnx = Mathf.Min(mnx, v.x); mxx = Mathf.Max(mxx, v.x); mnz = Mathf.Min(mnz, v.y); mxz = Mathf.Max(mxz, v.y); }
        int x0 = Mathf.Max(0, Mathf.FloorToInt((mnx - margin - tp.x) / cell));
        int x1 = Mathf.Min(R - 1, Mathf.CeilToInt((mxx + margin - tp.x) / cell));
        int z0 = Mathf.Max(0, Mathf.FloorToInt((mnz - margin - tp.z) / cell));
        int z1 = Mathf.Min(R - 1, Mathf.CeilToInt((mxz + margin - tp.z) / cell));
        int w = x1 - x0 + 1, h = z1 - z0 + 1;

        var sub = td.GetHeights(x0, z0, w, h);
        float padNorm = (padY - tp.y) / td.size.y;

        var gateRight = new Vector2(gateOutDir.y, -gateOutDir.x);

        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                float wx = tp.x + (x0 + i) * cell;
                float wz = tp.z + (z0 + j) * cell;
                var p = new Vector2(wx, wz);
                float natural = sub[j, i] * td.size.y + tp.y;

                float d = SignedDist(poly, p);   // 内側が正
                float target;

                // 門前の坂（石垣を切って街路から壇へ上がる）
                var g = p - gateMid;
                float along = Vector2.Dot(g, gateOutDir);
                float side = Mathf.Abs(Vector2.Dot(g, gateRight));
                bool onRamp = d < GRADE_INSET && along > -GRADE_INSET && along < RAMP_LEN
                              && side < _gateOpen * 0.5f + 3f;

                if (onRamp)
                {
                    float u = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(along / RAMP_LEN));
                    float sideFade = Mathf.SmoothStep(1f, 0f,
                        Mathf.InverseLerp(_gateOpen * 0.5f - 1f, _gateOpen * 0.5f + 3f, side));
                    float ramp = Mathf.Lerp(padY, natural, u);
                    target = Mathf.Lerp(natural, ramp, sideFade);
                }
                else if (d >= GRADE_INSET)
                {
                    // 石垣の内側から先は完全に水平な壇
                    target = padY;
                }
                else if (natural > padY && !InAnyOther(s, p))
                {
                    // 切土側: 境界まで壇の高さに削り、外へ GRADE_FEATHER で摺り付ける（下げるだけ）。
                    // ただし隣の屋敷の敷地内は削らない（隣の壇を掘ってしまうため）。
                    float outD = Mathf.Max(0f, -d);
                    float k = Mathf.SmoothStep(1f, 0f, Mathf.Clamp01(outD / GRADE_FEATHER));
                    target = Mathf.Min(natural, Mathf.Lerp(natural, padY, k));
                }
                else
                {
                    // 盛土側: 石垣の面が立つので自然地盤のまま残す（＝石垣が見える）
                    target = natural;
                }

                sub[j, i] = Mathf.Clamp01((target - tp.y) / td.size.y);
            }

        td.SetHeights(x0, z0, sub);
        _ = padNorm;
    }

    // ===================== 石垣の実測 =====================
    //
    // 石垣は手で直されるので「石垣が正」。土塀・長屋・門・造成・建物はすべて
    // 実物の石垣から測った外面ポリゴンに合わせる。Site の poly / padY は
    // 石垣がまだ無いときの初期値としてだけ使う。

    class Edge
    {
        public Vector2 dir;        // 走り方向
        public Vector2 outward;    // 外向き法線
        public float offset;       // dot(天端の前面上の点, outward) ← 塀・長屋を合わせる基準
        public float baseOffset;   // 基部の面（参考。石垣には勾配があるので天端とは1m前後ちがう）
        public Vector2 a, b;       // 外面ポリゴンの頂点（a→b）
        public System.Collections.Generic.List<Vector2[]> spans =
            new System.Collections.Generic.List<Vector2[]>();   // 石が実在する区間
    }

    class Enclosure
    {
        public Vector2[] poly;     // 石垣の外面（時計回り）
        public Edge[] edges;
        public float copingY;      // 天端
        public int gateEdge = -1;  // 開口のある辺
        public Vector2 gateMid;
        public float gateOpen;
    }

    /// <summary>実物の石垣から外面ポリゴン・石の実在区間・天端・門の開口を測る。</summary>
    static Enclosure Measure(Transform ish, Vector2[] designPoly)
    {
        if (ish == null || ish.childCount < 8) return null;

        // 直線材を yaw でクラスタ（±4°）。出隅材は除く。
        var keys = new System.Collections.Generic.List<int>();
        var grp = new System.Collections.Generic.Dictionary<int, System.Collections.Generic.List<Transform>>();
        float coping = float.MinValue;
        foreach (Transform c in ish)
        {
            var rs = c.GetComponentsInChildren<Renderer>();
            if (rs.Length > 0)
            {
                var bb = rs[0].bounds;
                foreach (var r in rs) bb.Encapsulate(r.bounds);
                coping = Mathf.Max(coping, bb.max.y);
            }
            var src = PrefabUtility.GetCorrespondingObjectFromSource(c.gameObject);
            if (src != null && src.name.Contains("Corner")) continue;
            int yw = Mathf.RoundToInt(c.eulerAngles.y);
            int key = yw;
            foreach (var k in keys) if (Mathf.Abs(Mathf.DeltaAngle(k, yw)) <= 4f) { key = k; break; }
            if (!grp.ContainsKey(key)) { grp[key] = new System.Collections.Generic.List<Transform>(); keys.Add(key); }
            grp[key].Add(c);
        }

        var edges = new System.Collections.Generic.List<Edge>();
        foreach (var kv in grp)
        {
            if (kv.Value.Count < 3) continue;              // 単発は出隅の代用なので直線とみなさない
            float th = kv.Key * Mathf.Deg2Rad;
            var lx = new Vector2(Mathf.Cos(th), -Mathf.Sin(th));   // ローカル +X ＝ 厚み方向
            var d = new Vector2(Mathf.Sin(th), Mathf.Cos(th));     // ローカル +Z ＝ 走り
            var outw = -lx;                                        // 外面は X=-2.4 側

            var offs = new System.Collections.Generic.List<float>();
            var iv = new System.Collections.Generic.List<Vector2>();  // (t開始, t終了)
            foreach (var c in kv.Value)
            {
                var p = new Vector2(c.position.x, c.position.z);
                var f = p + lx * (-ISHI_MOD * c.localScale.x);
                offs.Add(Vector2.Dot(f, outw));
                float t = Vector2.Dot(f, d);
                iv.Add(new Vector2(t - 2.0f * c.localScale.z, t));
            }
            offs.Sort();
            float off = offs[offs.Count / 2];               // 外れ値に強い中央値

            // 走り方向の区間をマージ（0.6m 未満の隙間は継ぎ目として詰める）
            iv.Sort((x, y) => x.x.CompareTo(y.x));
            var merged = new System.Collections.Generic.List<Vector2>();
            var cur = iv[0];
            for (int i = 1; i < iv.Count; i++)
            {
                if (iv[i].x <= cur.y + 0.6f) cur.y = Mathf.Max(cur.y, iv[i].y);
                else { merged.Add(cur); cur = iv[i]; }
            }
            merged.Add(cur);

            // 石垣には勾配(バッター)があり、面は上へ行くほど内へ退く。
            // 土塀を乗せる基準は基部の面ではなく【天端の前面】なので、天端直下の
            // メッシュ頂点から実測する（解析値 off は基部の面なので使わない）。
            float copingOff = float.MinValue;
            foreach (var c in kv.Value)
                foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var l2w = mf.transform.localToWorldMatrix;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = l2w.MultiplyPoint3x4(v);
                        if (w.y < coping - 0.7f || w.y > coping + 0.1f) continue;
                        copingOff = Mathf.Max(copingOff, Vector2.Dot(new Vector2(w.x, w.z), outw));
                    }
                }
            if (copingOff == float.MinValue) copingOff = off;

            var e = new Edge { dir = d, outward = outw, offset = copingOff, baseOffset = off };
            foreach (var m in merged)
                e.spans.Add(new[] { outw * copingOff + d * m.x, outw * copingOff + d * m.y });
            edges.Add(e);
        }
        if (edges.Count == 0) return null;

        // 石垣が3辺に満たない（隣と共有する辺の壁を落とした等）ときは、
        // 敷地の形は設計ポリゴンから取り、石のある辺だけ実測値で上書きする。
        if (edges.Count < 3)
        {
            if (designPoly == null || designPoly.Length < 3) return null;
            int dn = designPoly.Length;
            var dcen = Centroid(designPoly);
            var built = new Edge[dn];
            for (int i = 0; i < dn; i++)
            {
                var A = designPoly[i]; var B = designPoly[(i + 1) % dn];
                var dd = (B - A).normalized;
                var inw = new Vector2(dd.y, -dd.x);
                if (Vector2.Dot(inw, dcen - A) < 0f) inw = -inw;
                var outD = -inw;
                var e2 = new Edge { dir = dd, outward = outD, offset = Vector2.Dot(A, outD), baseOffset = Vector2.Dot(A, outD) };
                foreach (var r in edges)   // 同じ向きの面で、位置も近い実測の走りを採用
                {
                    if (Vector2.Dot(r.outward, outD) < 0.99f) continue;
                    if (Mathf.Abs(r.offset - Vector2.Dot(A, outD)) > 6f) continue;
                    e2.dir = r.dir; e2.outward = r.outward; e2.offset = r.offset;
                    e2.baseOffset = r.baseOffset; e2.spans = r.spans;
                    break;
                }
                built[i] = e2;
            }
            var per2 = Finish(new System.Collections.Generic.List<Edge>(built), coping, false);
            return per2;
        }

        return Finish(edges, coping, true);
    }

    /// <summary>辺の直線から頂点を出し、区間を頂点まで伸ばし、開口を拾って仕上げる。</summary>
    static Enclosure Finish(System.Collections.Generic.List<Edge> edges, float coping, bool sort)
    {
        // 外向き法線の角度で並べると凸多角形の周回順になる
        if (sort)
            edges.Sort((x, y) => Mathf.Atan2(x.outward.x, x.outward.y).CompareTo(Mathf.Atan2(y.outward.x, y.outward.y)));

        // 隣り合う辺の直線同士を交わらせて頂点を出す
        int n = edges.Count;
        var poly = new Vector2[n];
        for (int i = 0; i < n; i++)
        {
            var e1 = edges[i]; var e2 = edges[(i + 1) % n];
            var p1 = e1.outward * e1.offset; var p2 = e2.outward * e2.offset;
            float den = e1.dir.x * e2.dir.y - e1.dir.y * e2.dir.x;
            if (Mathf.Abs(den) < 1e-4f) return null;
            float t = ((p2.x - p1.x) * e2.dir.y - (p2.y - p1.y) * e2.dir.x) / den;
            poly[i] = p1 + e1.dir * t;
        }
        // poly[i] は辺 i の終点。辺 i を a→b にそろえる
        for (int i = 0; i < n; i++)
        {
            edges[i].a = poly[(i - 1 + n) % n];
            edges[i].b = poly[i];
        }
        var shifted = new Vector2[n];
        for (int i = 0; i < n; i++) shifted[i] = edges[i].a;

        // 直線材の区間は出隅ブロックの分だけ頂点の手前で終わる。塀が角で切れてしまうので、
        // 両端の区間だけを頂点まで伸ばす（門の開口は区間と区間の“内側”の隙間なので影響しない）。
        for (int i = 0; i < n; i++)
        {
            var e = edges[i];
            if (e.spans.Count == 0) continue;      // 石垣が無い辺（隣と共有して一本化した辺）
            var d = e.dir;
            var lo = Vector2.Dot(e.a, d) <= Vector2.Dot(e.b, d) ? e.a : e.b;
            var hi = Vector2.Dot(e.a, d) <= Vector2.Dot(e.b, d) ? e.b : e.a;
            var first = e.spans[0];
            if (Vector2.Dot(lo, d) < Vector2.Dot(first[0], d)) first[0] = lo;
            var last = e.spans[e.spans.Count - 1];
            if (Vector2.Dot(hi, d) > Vector2.Dot(last[1], d)) last[1] = hi;
        }

        var per = new Enclosure { poly = shifted, edges = edges.ToArray(), copingY = coping };

        // 開口（門）＝いちばん大きい区間の切れ目
        float best = 0f;
        for (int i = 0; i < n; i++)
        {
            var sp = edges[i].spans;
            for (int k = 0; k + 1 < sp.Count; k++)
            {
                float g = Vector2.Distance(sp[k][1], sp[k + 1][0]);
                if (g > best) { best = g; per.gateEdge = i; per.gateOpen = g; per.gateMid = (sp[k][1] + sp[k + 1][0]) * 0.5f; }
            }
        }
        return per;
    }

    // ===================== 屋敷の組み立て =====================

    static void Build(Site s)
    {
        var old = GameObject.Find(s.group);
        Transform keptIshigaki = null;
        if (old != null)
        {
            // 石垣は手で直されている前提で、既定では絶対に壊さない。
            // 加納の手直しをこれで一度失ったので、フラグの既定値を「残す」にしてある。
            if (!_rebuildIshigaki)
            {
                keptIshigaki = old.transform.Find("Ishigaki");
                if (keptIshigaki != null) keptIshigaki.SetParent(null, true);   // 破棄から逃がす
            }
            Object.DestroyImmediate(old);
        }
        var grp = new GameObject(s.group);
        if (keptIshigaki != null) keptIshigaki.SetParent(grp.transform, true);

        var poly = ToCW(s.poly);             // 時計回りに揃える → 石垣の胴が敷地の内側に入る
        var centroid = Centroid(poly);

        // ToCW が並びを反転した場合、辺番号も付け替える（元の辺 i は反転後の辺 n-2-i）
        int nv = s.poly.Length;
        bool reversed = SignedArea(s.poly) > 0f;
        System.Func<int, int> mapEdge = i => reversed ? (((nv - 2 - i) % nv) + nv) % nv : ((i % nv) + nv) % nv;
        var nagaya = new int[s.nagayaEdges == null ? 0 : s.nagayaEdges.Length];
        for (int i = 0; i < nagaya.Length; i++) nagaya[i] = mapEdge(s.nagayaEdges[i]);

        // ---- 石垣が既にあるなら、そこから全部を測り直して合わせる（石垣が正） ----
        var per = Measure(keptIshigaki, poly);
        Vector2 gateMid, eDir, inward;
        float padY = s.padY;

        if (per != null && per.gateEdge >= 0)
        {
            poly = per.poly;
            centroid = Centroid(poly);
            padY = per.copingY - PARAPET;      // 天端は定数でなく実物から読む
            gateMid = per.gateMid;
            _gateOpen = per.gateOpen;
            var ed = per.edges[per.gateEdge];
            eDir = ed.dir;
            inward = -ed.outward;
            // 長屋の辺は「門のある辺からの相対位置」で指定する（辺番号は実測で変わるため）
            nagaya = new int[s.nagayaFromGate.Length];
            for (int i = 0; i < nagaya.Length; i++)
                nagaya[i] = ((per.gateEdge + s.nagayaFromGate[i]) % poly.Length + poly.Length) % poly.Length;
        }
        else
        {
            int ge = mapEdge(s.gateEdge);
            var A = poly[ge]; var B = poly[(ge + 1) % poly.Length];
            eDir = (B - A).normalized;
            gateMid = Vector2.Lerp(A, B, reversed ? 1f - s.gateT : s.gateT);
            inward = new Vector2(eDir.y, -eDir.x);
            if (Vector2.Dot(inward, centroid - gateMid) < 0f) inward = -inward;
            _gateOpen = ModelWidth(s.gatePrefab, EDO_SCALE) + 0.6f;
        }
        var outward = -inward;

        Grade(s, poly, padY, gateMid, outward);

        if (keptIshigaki == null) BuildIshigaki(s, grp, poly, gateMid, eDir);
        BuildHei(grp, poly, per, nagaya, padY);
        BuildGate(s, grp, gateMid, eDir, inward, padY);
        BuildNagaya(grp, poly, per, nagaya, padY);
        BuildInterior(s, grp, poly, gateMid, eDir, inward, padY);

        grp.transform.position = Vector3.zero;
        Selection.activeGameObject = grp;
        float gw = ModelWidth(s.gatePrefab, EDO_SCALE);
        Debug.Log("[Yashiki v6] " + s.label + " built. 庭=" + padY.ToString("F2") + " 天端=" + (padY + PARAPET).ToString("F2")
                  + " 石垣=" + (keptIshigaki != null ? "手直しを維持(" + keptIshigaki.childCount + "枚)" : "新規生成")
                  + " 辺=" + poly.Length + " 開口=" + _gateOpen.ToString("F1") + "m(門" + gw.ToString("F1") + "m)"
                  + (gw > _gateOpen + 0.1f ? " ⚠門が開口より広い" : "")
                  + " 面積=" + Mathf.Abs(SignedArea(poly)).ToString("F0") + "m2 ("
                  + (Mathf.Abs(SignedArea(poly)) / 3.30579f).ToString("F0") + "坪)");
    }

    /// <summary>敷地境界に沿って石垣を廻す。天端は padY で一直線。</summary>
    static void BuildIshigaki(Site s, GameObject grp, Vector2[] poly, Vector2 gateMid, Vector2 gateDir)
    {
        var host = new GameObject("Ishigaki");
        host.transform.SetParent(grp.transform);
        var pf = Load(P_WALL);
        var pfC = Load(P_WALL_CORNER);
        float drop = s.ishiDrop > 0f ? s.ishiDrop : ISHI_DROP;
        float baseY = s.padY + PARAPET - drop;   // 天端 = padY + PARAPET
        float sy = drop / 4f;
        int n = 0;

        float tOut = ISHI_MOD * ISHI_SX;        // 外面から胴の裏までの厚み
        float tCor = ISHI_MOD * ISHI_CORNER_SZ;

        for (int i = 0; i < poly.Length; i++)
        {
            var A = poly[i];
            var B = poly[(i + 1) % poly.Length];
            var d = (B - A);
            float len = d.magnitude;
            d /= len;
            float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;

            // 出隅：この辺の外向き法線に、出隅の +Z 面を合わせる → yaw = 辺のyaw - 90°。
            // 位置は「外側の頂点＝ローカル(-t,+t)」から逆算する。
            float yawC = yaw - 90f;
            float ac = yawC * Mathf.Deg2Rad;
            var lxC = new Vector2(Mathf.Cos(ac), -Mathf.Sin(ac));   // ローカル +X の世界方向
            var lzC = new Vector2(Mathf.Sin(ac), Mathf.Cos(ac));    // ローカル +Z の世界方向
            var pc = A + lxC * tCor - lzC * tCor;
            Place(pfC, host.transform, "CWC_" + i, new Vector3(pc.x, baseY, pc.y), yawC,
                  new Vector3(ISHI_SX, sy, ISHI_CORNER_SZ));

            // 直線部は出隅の内側から始め、次の出隅に食い込ませて終える
            for (float t = tCor; t < len - tCor * 0.5f; t += ISHI_STEP)
            {
                var p = A + d * t;
                if (Vector2.Distance(p, gateMid) < _gateOpen * 0.5f) continue;   // 門の開口
                Place(pf, host.transform, "CW_" + (n++), new Vector3(p.x, baseY, p.y), yaw,
                      new Vector3(ISHI_SX, sy, ISHI_SZ));
            }
            // 端部の隙間を潰す一枚（R5：継ぎ目より重なりのほうがまし）
            var pe = A + d * (len - 0.2f);
            if (Vector2.Distance(pe, gateMid) >= _gateOpen * 0.5f)
                Place(pf, host.transform, "CW_" + (n++), new Vector3(pe.x, baseY, pe.y), yaw,
                      new Vector3(ISHI_SX, sy, ISHI_SZ));
        }
        _ = gateDir; _ = tOut;
    }

    /// <summary>辺 i の走り・内向き・石が実在する区間を返す。石垣が無い場合は設計ポリゴンで代用。</summary>
    static void EdgeGeom(Vector2[] poly, Enclosure per, int i,
                         out Vector2 d, out Vector2 inw,
                         out System.Collections.Generic.List<Vector2[]> spans)
    {
        int m = poly.Length;
        if (per != null)
        {
            var e = per.edges[i];
            d = e.dir; inw = -e.outward; spans = e.spans;
            return;
        }
        var A = poly[i]; var B = poly[(i + 1) % m];
        d = (B - A).normalized;
        inw = new Vector2(d.y, -d.x);
        if (Vector2.Dot(inw, Centroid(poly) - A) < 0f) inw = -inw;
        spans = new System.Collections.Generic.List<Vector2[]> { new[] { A, B } };
    }

    /// <summary>
    /// 石垣の天端に土塀を廻す。
    /// 土塀の【前面を石垣の外面と面一】にする＝芯線を外面から厚みの半分(0.58m)だけ内へ寄せる。
    /// 石が実在する区間にだけ置くので、門の開口や石垣の切れ目で自動的に途切れる。
    /// 出隅は「出ていく辺の方位 − 90°」で芯線の頂点に置く（unity-modular-stonewall R1/R2 の閉形式）。
    /// </summary>
    static void BuildHei(GameObject grp, Vector2[] poly, Enclosure per, int[] nagayaEdges, float padY)
    {
        var host = new GameObject("Dobei");
        host.transform.SetParent(grp.transform);
        var pf = Load(P_HEI);
        var pfC = Load(P_HEI_COR);
        float copY = padY + PARAPET;      // 土塀は石垣の天端に乗る（ピボットが足元）
        var sc = Vector3.one * EDO_SCALE;
        int m = poly.Length, n = 0;

        var dirs = new Vector2[m]; var inws = new Vector2[m];
        var spanList = new System.Collections.Generic.List<Vector2[]>[m];
        for (int i = 0; i < m; i++) EdgeGeom(poly, per, i, out dirs[i], out inws[i], out spanList[i]);

        for (int i = 0; i < m; i++)
        {
            if (System.Array.IndexOf(nagayaEdges, i) >= 0) continue;   // 長屋塀の辺には土塀を置かない
            float yaw = Mathf.Atan2(-dirs[i].y, dirs[i].x) * Mathf.Rad2Deg;   // このモデルは +X が走り
            foreach (var sp in spanList[i])
            {
                var A = sp[0] + inws[i] * HEI_BODY;
                var B = sp[1] + inws[i] * HEI_BODY;
                float len = Vector2.Distance(A, B);
                if (len < HEI_BACK + HEI_FWD) continue;
                var dd = (B - A) / len;
                for (float t = HEI_BACK; t + HEI_FWD <= len + 0.05f; t += HEI_PITCH)
                {
                    var p = A + dd * t;
                    Place(pf, host.transform, "HEI_" + (n++), new Vector3(p.x, copY, p.y), yaw, sc);
                }
            }
        }

        // 出隅：芯線どうしの交点に、出ていく辺の方位 −90° で置く
        for (int i = 0; i < m; i++)
        {
            int j = (i + 1) % m;                       // j が出ていく辺
            var p1 = poly[j] + inws[i] * HEI_BODY;     // 辺 i の芯線上の点
            var p2 = poly[j] + inws[j] * HEI_BODY;     // 辺 j の芯線上の点
            if (spanList[i].Count == 0 || spanList[j].Count == 0) continue;   // 石垣の無い辺には角を作らない
            if (System.Array.IndexOf(nagayaEdges, i) >= 0 || System.Array.IndexOf(nagayaEdges, j) >= 0) continue;
            if (!LineIntersect(p1, dirs[i], p2, dirs[j], out var v)) continue;
            if (per != null && Vector2.Distance(v, per.gateMid) < _gateOpen * 0.5f + HEI_PITCH) continue;
            float yawC = Mathf.Atan2(-dirs[j].y, dirs[j].x) * Mathf.Rad2Deg - 90f;
            Place(pfC, host.transform, "HEIC_" + i, new Vector3(v.x, copY, v.y), yawC, sc);
        }
    }

    /// <summary>
    /// 表門は edogoyomi（HONEY「江戸街並みシリーズ」）の実物モデルを使う。
    /// どのモデルも 1間=1.818m でモデリングされ、原点は足元より 1.8m 上・街路側は -Z。
    /// 位置合わせは決め打ちせず、実際のバウンズから逆算する。
    /// </summary>
    static void BuildGate(Site s, GameObject grp, Vector2 gateMid, Vector2 eDir, Vector2 inward, float padY)
    {
        var host = new GameObject("Omotemon");
        host.transform.SetParent(grp.transform);
        var pf = Load(s.gatePrefab);
        if (pf == null) return;

        float yaw = Mathf.Atan2(inward.x, inward.y) * Mathf.Rad2Deg;   // モデルの +Z が敷地の奥を向く
        var g = Place(pf, host.transform, "Mon", new Vector3(gateMid.x, padY, gateMid.y),
                      yaw, Vector3.one * EDO_SCALE);
        var sub = string.IsNullOrEmpty(s.gateSub) ? null : Load(s.gateSub);
        GameObject g2 = null;
        if (sub != null)   // 出番所は門と同じ原点・向きで作られている
            g2 = Place(sub, host.transform, "Bansho", new Vector3(gateMid.x, padY, gateMid.y),
                       yaw, Vector3.one * EDO_SCALE);

        // 足元を庭の高さへ、街路側の面を敷地境界へ、幅の中心を門の位置へ揃える
        var b = WorldBounds(g);
        float lift = padY - b.min.y;
        var c2 = new Vector2(b.center.x, b.center.z);
        float alongOff = Vector2.Dot(c2 - gateMid, eDir);                  // 幅方向のずれ
        float depthOff = Vector2.Dot(c2 - gateMid, inward) - b.size.magnitude * 0f;
        // 街路側の面（inward 方向で最も手前の隅）を境界に合わせる
        float front = float.MaxValue;
        foreach (var k in new[] { new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z),
                                  new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z) })
            front = Mathf.Min(front, Vector2.Dot(k - gateMid, inward));
        var shift = -eDir * alongOff - inward * front;
        _ = depthOff;

        g.transform.position += new Vector3(shift.x, lift, shift.y);
        if (g2 != null) g2.transform.position += new Vector3(shift.x, lift, shift.y);
    }

    /// <summary>
    /// 表通りに面する辺に大名長屋を通す（長屋塀）。これが広重の絵の白壁＋瓦屋根の列。
    /// モデルは胴が原点の -Z 側にあり、街路に面するのも -Z の面。
    /// yaw は「ローカル +Z が敷地の奥」に取り、街路側の面が境界へ来るよう原点を奥へ引く。
    /// </summary>
    static void BuildNagaya(GameObject grp, Vector2[] poly, Enclosure per, int[] nagayaEdges, float padY)
    {
        if (nagayaEdges == null || nagayaEdges.Length == 0) return;
        var host = new GameObject("Nagaya");
        host.transform.SetParent(grp.transform);
        var mc = Load(P_NAGAYA_C);
        var ml = Load(P_NAGAYA_L);
        var mr = Load(P_NAGAYA_R);
        var sc = Vector3.one * EDO_SCALE;
        float y = padY + NG_LIFT;
        int n = 0;

        foreach (int ei in nagayaEdges)
        {
            int i = ((ei % poly.Length) + poly.Length) % poly.Length;
            EdgeGeom(poly, per, i, out var d, out var inward,
                     out System.Collections.Generic.List<Vector2[]> spans);

            float yaw = Mathf.Atan2(inward.x, inward.y) * Mathf.Rad2Deg;   // ローカル +Z が敷地の奥
            var run = -d;   // この yaw ではローカル +X が -d 側を向く

            foreach (var sp in spans)
            {
                // 街路側の面(-Z)を石垣の外面と面一にする
                var A = sp[0] + inward * NG_FRONT;
                var B = sp[1] + inward * NG_FRONT;
                float len = Vector2.Distance(A, B);
                if (len < NG_PITCH) continue;
                var dd = (B - A) / len;
                // 出隅の土塀を避けて両端を1.5m空け、終端から手前へ詰める
                var seq = new System.Collections.Generic.List<Vector2>();
                for (float t = len - 1.5f - NG_HALF; t > 1.5f + NG_BACK; t -= NG_PITCH) seq.Add(A + dd * t);
                for (int k = 0; k < seq.Count; k++)
                {
                    var pf = k == 0 ? mr : (k == seq.Count - 1 ? ml : mc);
                    // 端部材は原点位置が中材とずれるので突き付くよう補正
                    float adj = k == 0 ? -0.53f : (k == seq.Count - 1 ? 0.22f : 0f);
                    var p = seq[k] + run * adj;
                    Place(pf, host.transform, "NG_" + (n++), new Vector3(p.x, y, p.y), yaw, sc);
                }
            }
        }
    }

    /// <summary>建物は表門を原点、u=表通り方向、v=敷地の奥へ、という座標で配置する。</summary>
    static void BuildInterior(Site s, GameObject grp, Vector2[] poly, Vector2 gateMid, Vector2 eDir, Vector2 inward, float padY)
    {
        float inYaw = Mathf.Atan2(inward.x, inward.y) * Mathf.Rad2Deg;
        _placed.Clear();
        // 門前は通路として空けておく
        _placed.Add(new Obb(gateMid + inward * 9f, inYaw, 7f, 9f));

        var host = new GameObject("Buildings");
        host.transform.SetParent(grp.transform);
        // 大きい建物から置く（後から来た小屋が押しのけられる側になる）
        var order = new System.Collections.Generic.List<Building>(s.buildings);
        order.Sort((x, y) => Footprint(y.prefab).CompareTo(Footprint(x.prefab)));
        foreach (var b in order)
        {
            var pf = Load(b.prefab);
            if (pf == null) continue;
            var p = gateMid + eDir * b.u + inward * b.v;
            var go = Place(pf, host.transform, Path.GetFileNameWithoutExtension(b.prefab),
                           new Vector3(p.x, padY, p.y), inYaw + b.relYaw, Vector3.one);
            FitInside(go, poly, 2.5f, 2f);  // 塀にめり込まず、建物どうしも離す
        }
        if (s.trees != null && s.trees.Length > 0)
        {
            var th = new GameObject("Garden");
            th.transform.SetParent(grp.transform);
            var tree = Load(P_TREE);
            if (tree != null)
                for (int i = 0; i < s.trees.Length; i++)
                {
                    var p = gateMid + eDir * s.trees[i].x + inward * s.trees[i].y;
                    float sc = 0.85f + ((i * 37) % 11) * 0.04f;
                    var go = Place(tree, th.transform, "Tree_" + i, new Vector3(p.x, padY, p.y),
                                   (i * 53) % 360, new Vector3(sc, sc, sc));
                    FitInside(go, poly, 4f, 0.5f);
                }
        }
    }

    // ===================== ユーティリティ =====================

    /// <summary>プレハブの平面寸法（大きい順に置くための目安）。</summary>
    static float Footprint(string path)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf == null) return 0f;
        var rs = pf.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return 0f;
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b.size.x * b.size.z;
    }

    static GameObject Load(string path)
    {
        var g = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (g == null) Debug.LogError("[Yashiki] prefab not found: " + path);
        return g;
    }

    static GameObject Place(GameObject pf, Transform parent, string name, Vector3 pos, float yaw, Vector3 scale)
    {
        if (pf == null) return null;
        var g = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        g.name = name;
        g.transform.SetParent(parent, false);
        g.transform.position = pos;
        g.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        g.transform.localScale = scale;
        return g;
    }

    /// <summary>平面上の回転した矩形。AABB だと45°回転で面積が倍近くなり、判定が過大になる。</summary>
    class Obb
    {
        public Vector2 c, ax, az;
        public float hx, hz;
        public Obb(Vector2 c_, float yaw, float hx_, float hz_)
        {
            c = c_; hx = hx_; hz = hz_;
            float a = yaw * Mathf.Deg2Rad;
            ax = new Vector2(Mathf.Cos(a), -Mathf.Sin(a));
            az = new Vector2(Mathf.Sin(a), Mathf.Cos(a));
        }
        public Vector2 Corner(int k) => c + ax * ((k & 1) == 0 ? -hx : hx) + az * ((k & 2) == 0 ? -hz : hz);
        float Extent(Vector2 axis) => Mathf.Abs(Vector2.Dot(ax, axis)) * hx + Mathf.Abs(Vector2.Dot(az, axis)) * hz;
        /// <summary>分離軸判定。clearance だけ離れていなければ true。</summary>
        public bool Overlaps(Obb o, float clearance)
        {
            foreach (var axis in new[] { ax, az, o.ax, o.az })
                if (Mathf.Abs(Vector2.Dot(o.c - c, axis)) >= Extent(axis) + o.Extent(axis) + clearance)
                    return false;
            return true;
        }
    }

    static readonly System.Collections.Generic.List<Obb> _placed =
        new System.Collections.Generic.List<Obb>();

    static Bounds WorldBounds(GameObject g)
    {
        var rs = g.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }

    /// <summary>プレハブ／モデルの幅(X)。門の開口幅を決めるのに使う。</summary>
    static float ModelWidth(string path, float scale)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf == null) return 6f;
        var rs = pf.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return 6f;
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b.size.x * scale;
    }

    /// <summary>
    /// 建物を敷地内に収め、先に置いたものと重ならない位置まで押しのける。
    /// 敷地の判定は回転を考慮した4隅（AABB ではなく OBB）で行う。
    /// </summary>
    static void FitInside(GameObject g, Vector2[] poly, float margin, float clearance)
    {
        if (g == null) return;
        var rs = g.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return;
        // オブジェクトのローカル軸での範囲（回転しても変わらない箱）。
        // Renderer.bounds はワールドの AABB なので、それをローカルへ戻すと回転ぶん膨らむ。
        // メッシュのローカル境界から積み上げること。
        var mfs = g.GetComponentsInChildren<MeshFilter>();
        var lb = new Bounds();
        bool first = true;
        foreach (var mf in mfs)
        {
            if (mf.sharedMesh == null) continue;
            var mb = mf.sharedMesh.bounds;
            var m = g.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix;
            for (int k = 0; k < 8; k++)
            {
                var p = m.MultiplyPoint3x4(new Vector3(
                    (k & 1) == 0 ? mb.min.x : mb.max.x,
                    (k & 2) == 0 ? mb.min.y : mb.max.y,
                    (k & 4) == 0 ? mb.min.z : mb.max.z));
                if (first) { lb = new Bounds(p, Vector3.zero); first = false; }
                else lb.Encapsulate(p);
            }
        }
        if (first) return;
        var centroid = Centroid(poly);
        float yaw = g.transform.eulerAngles.y;
        // ローカル箱の中心はピボットからずれていることがあるので、そのオフセットも持っておく
        var offLocal = new Vector2(lb.center.x, lb.center.z);
        System.Func<Obb> cur = () =>
        {
            var pos = new Vector2(g.transform.position.x, g.transform.position.z);
            float a = yaw * Mathf.Deg2Rad;
            var ax = new Vector2(Mathf.Cos(a), -Mathf.Sin(a));
            var az = new Vector2(Mathf.Sin(a), Mathf.Cos(a));
            return new Obb(pos + ax * offLocal.x + az * offLocal.y, yaw, lb.size.x * 0.5f, lb.size.z * 0.5f);
        };

        for (int step = 0; step < 200; step++)
        {
            var box = cur();
            bool moved = false;

            float worst = float.MaxValue;
            for (int k = 0; k < 4; k++) worst = Mathf.Min(worst, SignedDist(poly, box.Corner(k)));
            if (worst < margin)
            {
                var dir = centroid - box.c;
                if (dir.sqrMagnitude > 1e-4f)
                {
                    g.transform.position += new Vector3(dir.normalized.x, 0f, dir.normalized.y) * 1.2f;
                    moved = true;
                }
            }
            else
            {
                foreach (var o in _placed)
                {
                    if (!box.Overlaps(o, clearance)) continue;
                    var dir = box.c - o.c;
                    if (dir.sqrMagnitude < 1e-4f) dir = Vector2.right;
                    dir.Normalize();
                    g.transform.position += new Vector3(dir.x, 0f, dir.y) * 1.2f;
                    moved = true;
                    break;
                }
            }
            if (!moved) break;
        }
        _placed.Add(cur());
    }

    static Vector2 Centroid(Vector2[] p)
    {
        var c = Vector2.zero;
        foreach (var v in p) c += v;
        return c / p.Length;
    }

    static float Perimeter(Vector2[] p)
    {
        float s = 0f;
        for (int i = 0; i < p.Length; i++) s += Vector2.Distance(p[i], p[(i + 1) % p.Length]);
        return s;
    }

    static float SignedArea(Vector2[] p)
    {
        float s = 0f;
        for (int i = 0; i < p.Length; i++) { var a = p[i]; var b = p[(i + 1) % p.Length]; s += a.x * b.y - b.x * a.y; }
        return s * 0.5f;
    }

    static Vector2[] ToCCW(Vector2[] p)
    {
        if (SignedArea(p) >= 0f) return (Vector2[])p.Clone();
        var r = new Vector2[p.Length];
        for (int i = 0; i < p.Length; i++) r[i] = p[p.Length - 1 - i];
        return r;
    }

    /// <summary>時計回りに揃える。Castle Wall は CW で辿ると胴が内側に入る。</summary>
    static Vector2[] ToCW(Vector2[] p)
    {
        if (SignedArea(p) <= 0f) return (Vector2[])p.Clone();
        var r = new Vector2[p.Length];
        for (int i = 0; i < p.Length; i++) r[i] = p[p.Length - 1 - i];
        return r;
    }

    /// <summary>凸多角形を内側へ dist だけオフセット（辺を平行移動して交点を取る）。向きは自動判定。</summary>
    static Vector2[] OffsetPolygon(Vector2[] p, float dist)
    {
        int n = p.Length;
        float sgn = SignedArea(p) >= 0f ? 1f : -1f;   // CCW なら左、CW なら右が内側
        var res = new Vector2[n];
        for (int i = 0; i < n; i++)
        {
            var prev = p[(i - 1 + n) % n];
            var cur = p[i];
            var next = p[(i + 1) % n];
            var d0 = (cur - prev).normalized;
            var d1 = (next - cur).normalized;
            var n0 = new Vector2(-d0.y, d0.x) * sgn;
            var n1 = new Vector2(-d1.y, d1.x) * sgn;
            var a0 = prev + n0 * dist; var a1 = cur + n1 * dist;
            if (!LineIntersect(a0, d0, a1, d1, out res[i])) res[i] = cur + n1 * dist;
        }
        return res;
    }

    static bool LineIntersect(Vector2 p0, Vector2 d0, Vector2 p1, Vector2 d1, out Vector2 hit)
    {
        float den = d0.x * d1.y - d0.y * d1.x;
        if (Mathf.Abs(den) < 1e-5f) { hit = p1; return false; }
        var r = p1 - p0;
        float t = (r.x * d1.y - r.y * d1.x) / den;
        hit = p0 + d0 * t;
        return true;
    }

    /// <summary>凸多角形の符号付き距離（内側が正）。CCW 前提。</summary>
    static float SignedDist(Vector2[] poly, Vector2 q)
    {
        var ccw = SignedArea(poly) >= 0f ? poly : ToCCW(poly);
        float best = float.MaxValue;
        bool inside = true;
        for (int i = 0; i < ccw.Length; i++)
        {
            var a = ccw[i]; var b = ccw[(i + 1) % ccw.Length];
            var d = (b - a); float len = d.magnitude; d /= len;
            var nIn = new Vector2(-d.y, d.x);
            float side = Vector2.Dot(q - a, nIn);
            if (side < 0f) inside = false;
            float t = Mathf.Clamp(Vector2.Dot(q - a, d), 0f, len);
            best = Mathf.Min(best, Vector2.Distance(q, a + d * t));
        }
        return inside ? best : -best;
    }
}
