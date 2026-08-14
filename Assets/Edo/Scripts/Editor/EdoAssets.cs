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
