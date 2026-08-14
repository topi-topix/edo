// アセットパスの一元管理。
//
// ビルダーがパスを直書きしていたため、同じパスが最大16箇所に散っていた
// (k_mon のパス定数だけで8ファイルにコピーがあった)。パックの構成が変わったとき、
// LoadAssetAtPath は例外を投げず null を返すだけなので**静かに壊れる**。
// パスの literal はこのファイルだけに置き、各ビルダーはここを参照すること。
//
// 各ファイルの `const string PKmon = EdoAssets.Eg.Kmon;` のようなローカル別名は、
// 呼び出し側を変えずに参照元を1本化するための alias。新規に literal を書かないこと。
//
// 在庫と実寸は docs/asset-catalog.md / docs/asset-index.tsv を見る。
// 目録の更新は Edo ▸ アセット目録 ▸ 目録を再生成。

public static class EdoAssets
{
    /// <summary>江戸暦(共通スケール ES = 1.818 を掛けて使う)</summary>
    public static class Eg
    {
        public const string ES_NOTE = "scale 1.818";

        // 門
        public const string Kmon        = "Assets/edogoyomi/es_kmon/k_mon.obj";
        public const string Hmon        = "Assets/edogoyomi/es_hmon/h_mon.obj";
        public const string Nagayamon   = "Assets/edogoyomi/es_nmon/nagayamon.obj";
        public const string Kabukimon   = "Assets/edogoyomi/es_kabukimon/kabukimon.obj";
        public const string KidoOpen    = "Assets/edogoyomi/es_kido/kido_open.obj";

        // 建物
        public const string Kura        = "Assets/edogoyomi/es_kura/kura.obj";
        public const string KnagayaC    = "Assets/edogoyomi/es_knagaya/knagaya01c.obj";
        public const string KnagayaL    = "Assets/edogoyomi/es_knagaya/knagaya01l.obj";
        public const string KnagayaR    = "Assets/edogoyomi/es_knagaya/knagaya01r.obj";
        public const string Bansho      = "Assets/edogoyomi/es_dbansho/dbansho.obj";
        public const string Kidobanya   = "Assets/edogoyomi/es_kidobanya/kidobanya.obj";
        public const string Jishinban   = "Assets/edogoyomi/es_jishinban/jishinban.obj";
        public const string Hinomiyagura= "Assets/edogoyomi/es_hinomi/hinomiyagura.obj";
        public const string Shop01      = "Assets/edogoyomi/es_shop01/shop01.obj";
        public const string Shop02      = "Assets/edogoyomi/es_shop02/shop02.obj";

        // 塀
        public const string DobeiCenter = "Assets/edogoyomi/es_dobei/s_hei_center.obj";
        public const string DobeiCorner = "Assets/edogoyomi/es_dobei/s_hei_corner.obj";
        public const string Itabei5     = "Assets/edogoyomi/obj_itabei/itabei5.obj";
        public const string Hogaki5     = "Assets/edogoyomi/obj_hogaki/hogaki5.obj";

        // 店先の小物
        public const string Shop01Taru  = "Assets/edogoyomi/es_shop01/s01_taru.obj";
        public const string Shop01Oke   = "Assets/edogoyomi/es_shop01/oke.obj";

        // テクスチャ(マテリアル生成用)
        public const string TexShop01     = "Assets/edogoyomi/es_shop01/shop01.jpg";
        public const string TexShop02     = "Assets/edogoyomi/es_shop02/shop02.jpg";
        public const string TexOke        = "Assets/edogoyomi/es_shop01/oke.jpg";
        public const string TexKomodaru   = "Assets/edogoyomi/es_shop01/komodaru.jpg";
        public const string TexKidobanya  = "Assets/edogoyomi/es_kidobanya/kidobanya.jpg";
    }

    /// <summary>Japanese Village Kit</summary>
    public static class VK
    {
        public const string House      = "Assets/Japanese Village Kit/Prefabs/House.prefab";
        public const string HouseA     = "Assets/Japanese Village Kit/Prefabs/House A.prefab";
        public const string HouseB     = "Assets/Japanese Village Kit/Prefabs/House B.prefab";
        public const string SmallHouse = "Assets/Japanese Village Kit/Prefabs/Small House.prefab";
        public const string BigHouse   = "Assets/Japanese Village Kit/Prefabs/Big House.prefab";
        public const string Manor      = "Assets/Japanese Village Kit/Prefabs/Manor.prefab";

        public const string Roof2x8    = "Assets/Japanese Village Kit/Prefabs/Roofs/roof 2x8.prefab";
        public const string RoofEnd2x1 = "Assets/Japanese Village Kit/Prefabs/Roofs/roof end 2x1.prefab";
        public const string RoofTopX8  = "Assets/Japanese Village Kit/Prefabs/Roofs/roof top x8.prefab";

        public const string FloorInterior2x2 = "Assets/Japanese Village Kit/Prefabs/Walls and floors/floor interior 2x2.prefab";
        public const string ColumnA          = "Assets/Japanese Village Kit/Prefabs/Walls and floors/column A .prefab"; // 末尾の空白はベンダー由来
        public const string WallShopWoodX8    = "Assets/Japanese Village Kit/Prefabs/Shopping Streets/Wall Shop Wood x 8.prefab";
        public const string WallShopPlasterX8 = "Assets/Japanese Village Kit/Prefabs/Shopping Streets/Wall Shop Plaster x 8.prefab";
    }

    /// <summary>御殿の部材(Blender で Village Kit から江戸間に起こしたもの)
    /// 生成は Tools/Blender/。規約: 幅X・高さY・厚みZ、表=+Z、ピボット=一間の中心・床レベル。
    /// 1間=1.818m / 建具高=2.727m / 柱=0.182角。</summary>
    public static class Goten
    {
        const string P = "Assets/Edo/Models/Goten/Parts/";

        public const string Shoji1ken   = P + "Goten_Shoji_1ken.fbx";    // 障子 一間2枚建て
        public const string ShojiHalf   = P + "Goten_ShojiHalf.fbx";     // 障子 半間1枚
        public const string WallPlaster = P + "Goten_WallPlaster_1ken.fbx"; // 白壁(外周)
        public const string WallRenji   = P + "Goten_WallRenji_1ken.fbx";   // 連子窓
        public const string Column      = P + "Goten_Column.fbx";
        public const string Beam        = P + "Goten_Beam_1ken.fbx";
        public const string Tatami      = P + "Goten_Tatami_1ken.fbx";   // 一間角=江戸間2畳
        public const string FloorBoard  = P + "Goten_FloorBoard_1ken.fbx"; // 入側の板敷き
        public const string Ceiling     = P + "Goten_Ceiling_1ken.fbx";
        public const string Nureen      = P + "Goten_Nureen_1ken.fbx";   // 濡縁+高欄(ピボットは建物側)
        public const string Koran       = P + "Goten_Koran_1ken.fbx";    // 高欄 単体(高1.158)渡廊下の縁

        // 建具・座敷飾り(キットに無いので Blender で新造 — build_goten_fittings.py)
        public const string Fusuma      = P + "Goten_Fusuma_1ken.fbx";       // 襖 内法まで(高1.818)
        public const string Ranma       = P + "Goten_Ranma_1ken.fbx";        // 筬欄間(高0.909)襖の上
        public const string Amado       = P + "Goten_Amado_1ken.fbx";        // 雨戸(板戸・全高)
        public const string JodanKamachi= P + "Goten_JodanKamachi_1ken.fbx"; // 上段框(段0.15)
        public const string Tokonoma    = P + "Goten_Tokonoma_1ken.fbx";     // 床の間(奥行0.98)
        public const string Chigaidana  = P + "Goten_Chigaidana_1ken.fbx";   // 違い棚
        public const string Chodaigamae = P + "Goten_Chodaigamae_1ken.fbx";  // 帳台構(枠が左右へ0.17出る)

        /// <summary>入母屋屋根。棟の寸法ごとに Blender で生成する:
        /// blender --background --python Tools/Blender/build_goten_roof.py -- W D 名前</summary>
        public const string RoofDir     = "Assets/Edo/Models/Goten/Roofs/";
        public const string RoofIrimoya    = RoofDir + "Goten_Roof_Irimoya.fbx";     // 8間x5間
        public const string RoofIrimoya5x5 = RoofDir + "Goten_Roof_Irimoya_5x5.fbx"; // 5間x5間

        /// <summary>渡廊下の切妻屋根。幅1間・長さ<see cref="RoofKirizumaKen"/>間の定尺で作ってある
        /// (瓦の繰り返し 1.785/2.004m は江戸間と割り切れないので1間モジュールにはできない)。
        /// 無い長さが要るときは build_goten_roof.py -- kirizuma &lt;間数&gt; で足す。
        /// ピボット = 廊下の中心・軒先レベル。大棟の天端は軒先から 0.953。</summary>
        public static readonly int[] RoofKirizumaKen = { 2, 3, 4, 5, 6, 8 };
        public static string RoofKirizuma(int nKen)
        {
            return RoofDir + "Goten_Roof_Kirizuma_" + nKen + "ken.fbx";
        }

        public const float Ken       = 1.818f;   // 江戸間
        public const float DoorH     = 2.727f;   // 建具・柱の高さ = 内法+欄間
        public const float Uchinori  = 1.818f;   // 内法高(6尺) — 襖・帳台構・床の間の落掛
        public const float RanmaH    = 0.909f;   // 欄間(半間)
        public const float ColumnW   = 0.182f;
        public const float KoranH    = 1.158f;   // 高欄の高さ
        public const float BeamH     = 0.182f;   // 梁・桁の成
    }

    /// <summary>Japanese Castle</summary>
    public static class JC
    {
        public const string CastleWall       = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Castle Wall.prefab";
        public const string CastleWallCorner = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Castle Wall Corner.prefab";
        public const string CastleWall4x12Mesh = "Assets/Japanese Castle/Meshes/Exterior/Castle Wall 4x12.fbx";

        public const string WallDefence       = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence.prefab";
        public const string WallDefenceX8     = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence x 8.prefab";
        public const string WallDefenceCorner = "Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/Wall Exterior Defence Corner.prefab";

        public const string GateExterior     = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior.prefab";
        public const string GateExteriorEndL = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior End L.prefab";
        public const string GateExteriorEndR = "Assets/Japanese Castle/Prefabs/Exterior/Walls/Gate Castle Exterior End R.prefab";
        public const string YaguramonA       = "Assets/Japanese Castle/Prefabs/Yaguramon A.prefab";

        public const string StoneBasket = "Assets/Japanese Castle/Prefabs/Props/Stone Basket.prefab";
        public const string Azalea01    = "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 01.prefab";
        public const string Azalea03    = "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 03.prefab"; // A 02 は存在しない
        public const string Azalea04    = "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 04.prefab";
    }

    /// <summary>Waldemarst Free Japanese Garden(季節は Summer を使う)</summary>
    public static class JG
    {
        public const string PineBig01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_01.prefab";
        public const string PineBig02 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_02.prefab";
        public const string PineBig03 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_03.prefab";
        public const string PineMid01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Mid_Green_01.prefab";

        public const string SakuraBig01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Big_Summer_01.prefab";
        public const string SakuraBig05 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Big_Summer_05.prefab";
        public const string SakuraMid01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Mid_Summer_01.prefab";
        public const string SakuraMid05 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Sakura/Tree_Sakura_Mid_Summer_05.prefab";

        public const string BambooBig01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_01.prefab";
        public const string BambooBig02 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_02.prefab";

        public const string Boxwood01 = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_01.prefab";
        public const string Fern01    = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/PaintedFern/Plant_PaintedFern_Spring_01.prefab";

        public const string Rock01    = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_01.prefab";
        public const string Rock02    = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_02.prefab";
        public const string Rock03    = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_03.prefab";
        public const string TobiIshi01= "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_TobiIshi_A_01.prefab";
    }

    /// <summary>自作(Assets/Edo 配下)</summary>
    public static class Own
    {
        public const string KasugaLantern = "Assets/Edo/Prefabs/KasugaLantern.prefab";
        public const string YukimiLantern = "Assets/Edo/Prefabs/YukimiLantern.prefab";
        public const string DanishiStep   = "Assets/Edo/Models/Shiomizaka/P_DanishiStep2m.prefab";
        public const string MichibataIshi = "Assets/Edo/Models/Shiomizaka/P_MichibataIshi2m.prefab";

        public const string MShop01     = "Assets/Edo/Materials/M_Shop01.mat";
        public const string MShop02     = "Assets/Edo/Materials/M_Shop02.mat";
        public const string MKido       = "Assets/Edo/Materials/M_Kido.mat";
        public const string MKidobanya  = "Assets/Edo/Materials/M_Kidobanya.mat";
        public const string MJishinban  = "Assets/Edo/Materials/M_Jishinban.mat";

        public const string LayerGrass  = "Assets/Edo/Terrain/layers/L_grass.terrainlayer";
    }
}
