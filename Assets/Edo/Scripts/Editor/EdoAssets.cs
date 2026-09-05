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
        /// <summary>竹垣(0.9高 x 1.05長)。水際・庭園帯の囲いに。
        /// 典拠は広重「赤坂桐畑」の対岸の柵 — ただし寺群の囲いの可能性が高く類推。
        /// ⛔ **これは四つ目垣ではない。**2026-09-04 に Blender で実見したところ
        /// **竹の菱格子(網代風)**で、四つ目(縦横の格子で向こうが四角く抜ける)ではなかった。
        /// 四つ目垣・建仁寺垣が要るなら <see cref="Own.YotsumeGaki"/> / <see cref="Own.KenninjiGaki"/>。
        /// ⭕ 本物の四つ目垣は同じキットの **`Fences/Bamboo garden fence`(B の付かない方)**で、
        /// そちらは親柱2+立子4+胴縁4+棕櫚縄16 の正しい四つ目(丈0.900・スパン1.000)。</summary>
        public const string TakeGaki    = "Assets/Japanese Village Kit/Prefabs/Fences/bamboo garden fence B.prefab";

        /// <summary>**雪見灯籠**(六角の広い笠 + 宝珠 + 火袋 + **竿を持たない三脚**)。
        /// ⭕ **在庫にあるので新造しない**(2026-09-04 に部材方が実見して確認)。
        /// 生 0.431 × 0.504 × 0.498 → **ES(1.818)を掛けて 0.784 × 0.916 × 0.906**、1,158三角。
        /// テクスチャは同じフォルダの `t_yukimi.jpg`(御影石)。ピボットは足元(接地)。
        /// ⚠ **他の edogoyomi と同じく素で置かず `ES = 1.818` を掛ける。**
        /// ⚠ 指図が h1.2 を求めるなら `scale = 1.818 × 1.31`(笠径 1.19 になるので大振り)。
        /// ⛔ **自作の <see cref="Own.YukimiLantern"/> は当邸では使わない** — 材質
        ///   `M_LanternStone` が**テクスチャを1枚も持たない**(べた塗り)。他邸で使用中なので消さない。
        /// ⛔ 春日型(<see cref="Own.KasugaLantern"/> / edogoyomi の `t_kasuga`)を庭に置かない
        ///   (指図 `gardens[].toro` 「⛔ 春日型を置かない」)。</summary>
        public const string ToroYukimi  = "Assets/edogoyomi/t_yukimi/t_yukimi.obj";
        public const string TexToroYukimi = "Assets/edogoyomi/t_yukimi/t_yukimi.jpg";

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
        public const string Nureen      = P + "Goten_Nureen_1ken.fbx";   // 濡縁+高欄(ピボットは建物側・高欄は外縁)
        public const string NureenCorner= P + "Goten_NureenCorner.fbx";  // 濡縁の入隅(0.891角・高欄が+X面と-Z面)
        public const string Koran       = P + "Goten_Koran_1ken.fbx";    // 高欄 単体(高1.158)渡廊下の縁

        /// <summary>階段廊下 — 木の段になった渡廊下。幅は他の廊下と同じ一間。
        /// 原点 = 坂上・**上段の廊下の床**の高さ。走りはローカル -Z(坂下)、段は下るので Y が負。
        /// 郭をまたぐ登廊の床に使う(屋外の石段を廊下に流用すると幅も踏み心地も合わない)。
        /// 生成: build_goten_kaidan.py -- &lt;走り&gt; &lt;落差&gt;</summary>
        public static string KaidanRoka(float run, float drop)
        {
            return P + "Goten_KaidanRoka_" + run.ToString("0.##") + "x" + drop.ToString("0.##") + ".fbx";
        }

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

        /// <summary>棟の外形(身舎+入側)の間数で引く入母屋。<paramref name="wKen"/>=桁行(大棟の走る側)。
        /// 大棟は桁行に架かるので **wKen >= dKen** で呼ぶこと(足りない向きで呼ぶと棟が短辺に架かる)。
        /// 無い寸法は build_goten_roof.py -- &lt;W&gt; &lt;D&gt; Goten_Roof_Irimoya_&lt;w&gt;x&lt;d&gt;ken で足す。</summary>
        public static string RoofIrimoya_(int wKen, int dKen)
        {
            return RoofDir + "Goten_Roof_Irimoya_" + wKen + "x" + dKen + "ken.fbx";
        }

        /// <summary>渡廊下の切妻屋根。幅1間・長さ<see cref="RoofKirizumaKen"/>間の定尺で作ってある
        /// (瓦の繰り返し 1.785/2.004m は江戸間と割り切れないので1間モジュールにはできない)。
        /// 無い長さが要るときは build_goten_roof.py -- kirizuma &lt;間数&gt; で足す。
        /// ピボット = 廊下の中心・軒先レベル。大棟の天端は軒先から 0.953。</summary>
        public static readonly int[] RoofKirizumaKen = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12 };
        public static string RoofKirizuma(int nKen)
        {
            return RoofDir + "Goten_Roof_Kirizuma_" + nKen + "ken.fbx";
        }

        /// <summary>登廊(階段廊下)の屋根。切妻を斜長ぶん通し、幅は石段の平場ぶん取ったもの。
        /// **据えるときに勾配ぶん傾ける**ので、屋根そのものは平らに作ってある。
        /// 生成: build_goten_roof.py -- noboriro &lt;斜長&gt; &lt;幅&gt; &lt;名前&gt;</summary>
        public static string RoofNoboriro(string tag)
        {
            return RoofDir + "Goten_Roof_Noboriro_" + tag + ".fbx";
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

        // 門扉。**開口に扉を建てないと外周が素通しになる**(2026-08-29 EDO-0053 で
        // 御蔵門・東小門が 2.7〜2.9m 開いたままだった)。
        // L/R とも**突き合わせる側**にピボットがあるので、開口の芯へ両方置けば閉じる。
        /// <summary>小門用(1.5×2.8)。対で開口 3.0m ちょうど。足元は local y=0.10。</summary>
        public const string GateDoorCastleL = "Assets/Japanese Castle/Meshes/Exterior/Gate Castle Door L.fbx";
        public const string GateDoorCastleR = "Assets/Japanese Castle/Meshes/Exterior/Gate Castle Door R.fbx";
        public const float  GateDoorCastleFoot = 0.10f;
        /// <summary>表門用(2.143×3.0)。対で 4.0m、足元は local y=0。開口へは横だけ伸ばす。</summary>
        public const string GateDoorYaguraL = "Assets/Japanese Castle/Prefabs/Exterior/Gate Yagura/Gate Yagura Door A Left Hinge.prefab";
        public const string GateDoorYaguraR = "Assets/Japanese Castle/Prefabs/Exterior/Gate Yagura/Gate Yagura Door A Right Hinge.prefab";

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
        public const string TobiIshi02= "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_TobiIshi_A_02.prefab";

        // ---- 植栽の系列(Stage7 が使う)。生の高さと江戸の木に合わせる倍率は目録 §9。
        const string JGP = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/";
        /// <summary>黒松。生 5.6m ×1.65。Big/Mid/Small × 01..03</summary>
        public static string Pine(string size, int i)
        { return JGP + "Trees/BlackPine/Tree_BlackPine_" + size + "_Green_0" + i + ".prefab"; }
        /// <summary>竹。**Big/Mid/Small × 01・02**(`Green` のみ引く — `Dry` は枯れ姿で当プロジェクトでは使わない)。
        /// 実寸[m]は目録 `docs/asset-index.tsv` の実測値(scale=1・幅 × **丈** × 奥行):
        ///   Small_01 4.33 × <b>4.33</b> × 1.93 ／ Small_02 4.03 × <b>4.03</b> × 2.25
        ///   Mid_01   6.29 × <b>6.32</b> × 3.26 ／ Mid_02   6.70 × <b>6.70</b> × 3.91
        ///   Big_01   9.56 × <b>9.61</b> × 5.90 ／ Big_02   9.03 × <b>9.06</b> × 6.70
        /// ピボットは足元(`pivot_bottom` = 0)なので地盤の y をそのまま渡せる。
        /// ⚠ **ヤダケ(矢竹)の代用に使うときは丈で縮める** — 指図 `nishi.hayashi.yadake` は 4〜6m で、
        ///   Small でも素のままだと下限に張り付く。⛔ 孟宗竹の姿のまま大きく置かない。</summary>
        public static string Bamboo(string size, int i)
        { return JGP + "Trees/Bamboo/Tree_Bamboo_" + size + "_Green_0" + i + ".prefab"; }
        /// <summary>桜。⚠ **Summer のみ使う**(季節は春ではない)。01 と 05 の2種。生 ×1.4</summary>
        public static string SakuraSummer(string size, int i)
        { return JGP + "Trees/Sakura/Tree_Sakura_" + size + "_Summer_0" + i + ".prefab"; }
        /// <summary>柘植の刈込。Spring/Fall × 01..03、Single/ もある</summary>
        public static string Boxwood(int i) { return JGP + "Plants/Boxwood/Plant_Boxwood_Spring_0" + i + ".prefab"; }
        /// <summary>羊歯の下草。Spring/Fall × 01..02</summary>
        public static string Fern(int i) { return JGP + "Plants/PaintedFern/Plant_PaintedFern_Spring_0" + i + ".prefab"; }
        /// <summary>庭石。01..03</summary>
        public static string Rock(int i) { return JGP + "Misc/Rocks/JG_Rock_A_0" + i + ".prefab"; }
        /// <summary>躑躅・皐月。⚠ **A 02 は存在しない** — 01 / 03 / 04 の3種</summary>
        public static string Azalea(int i)
        { return "Assets/Japanese Castle/Prefabs/Foliage/Azalea A 0" + i + ".prefab"; }
    }

    /// <summary>NatureManufacture Meadow Environment。**灌木の在庫**(高木のポプラは江戸に使えない)。
    /// ⚠ パックは再配布不可・gitignore。手元に無ければ README.md の手順で import する。</summary>
    public static class NM
    {
        const string Bush = "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/Bushes/Prefabs/";

        /// <summary>カエデの灌木(下草・林床の中層)。i = 1..4。</summary>
        public static string MapleBush(int i) { return Bush + "prefab_maple_bush_0" + i + ".prefab"; }

        /// <summary>ヤナギの灌木(水際・法面の下層)。i = 1..4。</summary>
        public static string GreyWillow(int i) { return Bush + "prefab_grey_willow_0" + i + ".prefab"; }

        const string GrassDir = "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/"
                              + "Grass/Prefabs Unity Terrain Grass/";

        /// <summary>**草地(メドウ)の草叢**。岡部邸のススキ(見透しの窓・法尻)に使う。
        /// ⚠ ファイル名は `prefab_**Terrain_**grass_meadow_…` で、**`Terrain_` が入る**
        /// (2026-09-04 の在庫の報告は落ちていた。⛔ 名を推測で組まない)。
        ///
        /// <para><paramref name="family"/> = "01"/"02"/"03"、<paramref name="variant"/> =
        /// ""(無印)/"cross"/"detailed"、<paramref name="i"/> = 個体。
        /// ⚠ **通し番号は系統ごとに歯抜け**なので、必ず <see cref="GrassMeadowIndices"/> で
        /// 実在する番号を引くこと(例: 02 の無印は **1 が無く 2〜6**)。</para>
        ///
        /// ⚠ これは **Unity Terrain の detail 用**のプレハブ。GameObject として据えても動くが、
        /// 数が増えるなら Terrain の detail 層へ載せるほうが軽い。</summary>
        public static string GrassMeadow(string family, string variant, int i)
        {
            return GrassDir + "prefab_Terrain_grass_meadow_" + family
                 + (string.IsNullOrEmpty(variant) ? "" : "_" + variant) + "_" + i + ".prefab";
        }

        /// <summary>系統・変種ごとに**実在する**個体の番号(2026-09-04 に `ls` で確認)。
        /// ⛔ 連番と決めつけない — 02 の無印は 1 が無い。03 に cross/detailed は無い。</summary>
        public static int[] GrassMeadowIndices(string family, string variant)
        {
            if (family == "01")
            {
                if (variant == "cross")    return new[] { 1, 2, 3 };
                if (variant == "detailed") return new[] { 1, 2 };
                return new[] { 1, 2, 3, 4, 5, 6 };
            }
            if (family == "02")
            {
                if (variant == "cross")    return new[] { 1, 2, 3 };
                if (variant == "detailed") return new[] { 1, 2 };
                return new[] { 2, 3, 4, 5, 6 };          // ⚠ 1 は無い
            }
            if (family == "03")
            {
                if (variant == "cross" || variant == "detailed") return new int[0];  // ⚠ 無い
                return new[] { 1, 2, 3, 4 };
            }
            return new int[0];
        }
    }


    /// <summary>自作(Assets/Edo 配下)</summary>
    public static class Own
    {
        public const string KasugaLantern = "Assets/Edo/Prefabs/KasugaLantern.prefab";
        public const string YukimiLantern = "Assets/Edo/Prefabs/YukimiLantern.prefab";
        public const string DanishiStep   = "Assets/Edo/Models/Shiomizaka/P_DanishiStep2m.prefab";
        public const string MichibataIshi = "Assets/Edo/Models/Shiomizaka/P_MichibataIshi2m.prefab";

        /// <summary>常緑の広葉樹(モッコク・モチノキ・カシ・シイの見立て)。実寸 5.6×5.9×4.7m。
        /// ⚠ **キットに常緑広葉樹が無いのでこれで代用する。**JapaneseGarden パックにあるのは
        /// 黒松・桜・竹だけで、NatureManufacture の広葉樹はポプラで江戸には使えない
        /// (`docs/asset-catalog.md` §9)。**梅もこれで代用する** — 夏の梅は葉だけの姿なので
        /// 樹種の違いは遠景で出ない。⛔ 種名を名乗らせないこと(確度が化ける)。</summary>
        [System.Obsolete("⛔ 使用禁止(2026-08-30 ユーザー指示「2度と使わないでください。見た目が" +
            "しょぼすぎます」)。自作の低ポリゴン(2,384三角)で、在庫の木と並べると明らかに見劣りする。" +
            "植栽は在庫のパックから採る(JG / JC.Foliage / NatureManufacture)。在庫に無い樹種が" +
            "要るなら、在庫の木の作り(枝の分岐・葉のカード・LOD・材質)を参考にリアルに再現して起こす。")]
        public const string Broadleaf = "Assets/Edo/Terrain/details/BroadleafTree.prefab";

        /// <summary>**常緑広葉樹**(モッコク・モチノキ・シラカシ・スダジイの見立て)。
        /// 江戸の庭木の主役だが在庫の高木は黒松(針葉)・桜(落葉)・竹の三種しか無いので、
        /// **在庫の木の作りを参考に新造した**(ユーザー裁定 2026-08-30 案C)。
        /// 骨格は空間占有法で伸ばすので樹冠が箱にならず、内部にも枝が通る。
        /// 材質は借り物の名前だけを運ぶ(`M_FJG_Tree_Sakura_Bark_A` / `..._Sprout_Summer`)ので
        /// **Unity で remap する**。LOD_0/1/2 の3本入り。
        /// 樹高: Small 3.6m / Mid 5.8m / Big 8.2m(在庫の同格に合わせた実測値)。
        ///
        /// <para><paramref name="i"/> は**個体**(1〜3)。⚠ 2026-09-01 の庭方の指摘
        /// 「2プレハブでモッコク・モチノキ・カシ・シイの4樹種43本を代表しており、
        /// 近景で同じ木の繰り返しになる」。骨格の乱数を個体ごとに変えて姿を散らしてある。
        /// ⛔ 1本の層を1個体で埋めない — 指図の parts で個体を混ぜること。</para>
        ///
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- jouryoku Small Mid Big</summary>
        public static string Jouryoku(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Jouryoku_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        /// <summary>⛔ 綴りの誤り(常緑の訓みは Jouryoku)。<see cref="Jouryoku"/> へ移した。
        /// 指図が古い綴りのまま残っている間だけの転送。</summary>
        [System.Obsolete("Own.Jouryoku(size, i) を使う(常緑=Jouryoku)")]
        public static string Jokuroku(string size) { return Jouryoku(size); }

        /// <summary>**イロハモミジ**。⭐ **株立ち3〜5幹・枝が水平に張る**(幅が高さを上回る)。
        /// ⚠ 在庫の `NM.MapleBush` は**灌木**(丈1.5m)で中木に使えず、桜の夏姿での代用も
        /// 不可(夏でも幹肌が桜と読め、季節の確度が化ける)。庭方の要求で 2026-09-01 に新造。
        /// ⛔ **紅葉色にしない** — 季節は春ではないが**秋でもない**。葉は夏の緑。
        /// <paramref name="i"/> は個体(1〜3)。樹高: Small 3.6m / Mid 5.8m。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- momiji Small Mid</summary>
        public static string Momiji(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Momiji_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        public static string Ume(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Ume_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        // ---------------------------------------------------------------- 落葉高木3種(岡部邸)
        // ⚠ **在庫の Small/Mid/Big(3.6/5.8/8.2m)では収まらない。**指図が要求するのは
        //   エノキ 11〜16 / ムクノキ 10〜14 / ケヤキ 13〜16 で、桜 Big の 2 倍近い。
        //   ⇒ 生成器は樹種ごとの寸法表を持つ。**同じ "Mid" でも樹種で樹高が違う**(下の doc)。
        // ⚠ 樹皮・葉の材質は在庫の桜のものを名乗る(キットに落葉高木の樹皮が無い)=確度U。
        //   姿(幹の分かれ方・枝の角度・樹冠の輪郭)で樹種を描き分けてある。
        // ⛔ **紅葉色にしない** — 季節は春でも秋でもない。葉は夏の緑。

        /// <summary>**エノキ**(一里塚の木)。⭐ **低い位置で数本の大枝に分かれ、枝が斜め上へ
        /// 開いて扇形〜半球形の広い樹冠**。幅 ≒ 高さ。法尻の3本と林の11本に使う。
        /// 樹高: **Small 11.0m / Mid 13.5m / Big 16.0m**(実測 W×D: 11〜12 / 14〜15 / 17〜19m)。
        /// <paramref name="i"/> は個体(1〜3)。⛔ 1本の層を1個体で埋めない — 混ぜること。
        /// LOD_0/1/2 の3本入り(LOD0 6.4〜8.1k tri)。⚠ 材質は名前だけなので **Unity で remap**。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- enoki Small Mid Big</summary>
        public static string Enoki(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Enoki_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        /// <summary>**ムクノキ**。エノキに似るが ⭐ **幹がより通直で高く、樹冠は縦長**
        /// (幅 &lt; 高さ)。枝は細くしなやかで垂れ気味。
        /// 樹高: **Small 10.0m / Mid 12.0m / Big 14.0m**(実測 W×D: 9 / 11 / 13m 前後)。
        /// <paramref name="i"/> は個体(1〜3)。LOD0 4.5〜6.0k tri。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- mukunoki Small Mid Big</summary>
        public static string Mukunoki(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Mukunoki_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        /// <summary>**ケヤキ**。⭐ **箒形** — 短い直幹から大枝が扇状に立ち上がり、上へ広がる
        /// 逆三角の樹冠。⛔ 他の2種と同じ丸い樹冠にしない(**箒形が樹種の見分け**)。
        /// 単木で抜く木なので、近景に耐えるよう個体を混ぜること。
        /// 樹高: **Small 13.0m / Mid 14.5m / Big 16.0m**(実測 W×D: 12〜13 / 14 / 15〜16m)。
        /// <paramref name="i"/> は個体(1〜3)。LOD0 6.8〜7.9k tri
        /// (⚠ 在庫の同格 5,960〜6,575 をやや超える。樹冠が大きいぶん枝が多い)。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- keyaki Small Mid Big</summary>
        public static string Keyaki(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Keyaki_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        // ---------------------------------------------------------------- つる3種(岡部邸 西の斜面)
        // 指図 `nishi.hayashi.tsuru`(フジ5・テイカカズラ・キヅタ「高木の幹に絡む」)。
        // ⚠ 在庫の `Japanese Village Kit/Prefabs/Foliage/Wisteria_A_01` は**藤棚専用**で
        //   幹に絡む姿が作れない(在庫方の判定 = 在庫に無い)。⇒ 2026-09-04 に新造。
        // ⭐ **どれも「幹径 0.60m(半径 0.30)の高木」を前提に作ってある。**
        //   実装は高木の幹の位置に据え、`scale = (d/0.60, 1, d/0.60)` で幹径 d に合わせる。
        //   ⚠ **XZ だけ伸縮するので葉も横に伸びる。**d は **0.40〜0.85m の範囲に収める**こと
        //   (倍率 0.67〜1.42。それを超えると葉が潰れて樹種が読めなくなる)。
        // ⚠ 丈は指図の値へ合わせて **Y を別途伸縮**してよい(±25% までは姿が保つ)。
        // ⛔ **開花させない**(規則10)。フジの花房は一切入っていない(旧暦6月で花期は過ぎている)。
        // ⚠ 材質は名前だけを運ぶ ⇒ **Unity で `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`**。

        /// <summary>**フジ(ノダフジ)が高木の幹に絡む姿**。2〜3本の蔓が幹を巻いて登り、
        /// 羽状複葉の葉が外へ張り出す。⛔ **花は無い**(旧暦6月・花期後)。
        /// <para>葉は在庫の `Wisteria_A_Leaves_01/02` の実物(材 `Wisteria_A_01`)。
        /// 蔓の本体だけは多角柱で起こしてある — ⚠ キットの `Wisteria_A_Branches_01` は
        /// **枝の絵を描いた平らなカード**で、幹に巻くと色の抜けた帯にしか見えなかった。</para>
        /// <para><paramref name="i"/> は個体(1〜3)。**丈が違う**:
        /// 1 = 3.49m / 2 = 4.66m / 3 = 5.86m(いずれも実測。幅・厚みは 1.5〜2.1m)。
        /// ⛔ 5本すべてを1個体で埋めない — 指図の tsuru.fuji=5 は個体を混ぜて割り付ける。</para>
        /// 巻きは**上から見て時計回り**(ノダフジ=右巻きの見立て。⚠ 和名の右/左は文献で割れる = 確度U)。
        /// 生成: blender --background --python Tools/Blender/build_tsuru.py -- fuji --render</summary>
        public static string TsuruFuji(int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tsuru_Fuji_" + i.ToString("00") + ".fbx";
        }

        /// <summary>**テイカカズラ**(常緑のつる)。幹に貼り付いて登る**細い帯**。
        /// 匍匐する茎3本 + 小さな葉のカード。⭐ フジと違い空中へ出ず、幹の面を這う。
        /// <para>⭐ **覆うのはローカル +X の側だけ**(帯幅 約150°)。⛔ 全周は覆わない
        /// — **向きは実装が yaw で振る**こと(振らないと全個体が同じ側を向く)。</para>
        /// <para><paramref name="i"/> は個体(1〜2)。丈 1 = 2.68m / 2 = 3.73m(実測)。</para>
        /// ⚠ 葉は在庫の桜の夏葉のアトラスを借りている(キットに常緑のつるの葉が無い)= **確度U**。
        /// 生成: blender --background --python Tools/Blender/build_tsuru.py -- teika --render</summary>
        public static string TsuruTeika(int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tsuru_Teika_" + i.ToString("00") + ".fbx";
        }

        /// <summary>**キヅタ**(常緑のつる)。テイカカズラより ⭐ **葉が大きく・帯が広く(約240°)・
        /// 密**で、幹を覆う「蔓のマント」になる。匍匐する茎4本。
        /// <para>⭐ 覆うのはローカル +X の側。⛔ 全周は覆わない — **向きは実装が yaw で振る**。</para>
        /// <para><paramref name="i"/> は個体(1〜2)。丈 1 = 2.50m / 2 = 3.47m(実測)。</para>
        /// ⚠ 葉は在庫の桜の夏葉のアトラスを借りている = **確度U**(キヅタ本来の濃い照葉ではない)。
        /// 生成: blender --background --python Tools/Blender/build_tsuru.py -- kizuta --render</summary>
        public static string TsuruKizuta(int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tsuru_Kizuta_" + i.ToString("00") + ".fbx";
        }

        /// <summary>石段の法面を留める「坂の土留め」。天端が勾配どおりに**一直線で斜め**に下がる
        /// 一枚物(段々に下がるモジュールでは実物の石段の袖にならない)。生成は
        /// Tools/Blender/build_ishigaki_saka.py。無い寸法は -- &lt;走り&gt; &lt;落差&gt; で足す。
        /// ローカル: +Z が坂下・Y=0 が下段の地面・X は芯線を挟んで±0.36(左右対称)。</summary>
        public static string IshigakiSaka(float run, float drop)
        {
            return "Assets/Edo/Models/Ishigaki/Ishigaki_Saka_"
                 + run.ToString("0.##") + "x" + drop.ToString("0.##") + ".fbx";
        }

        /// <summary>**長さ可変の表長屋**。在庫の `knagaya01c/l/r` を窓割り(bay=2.6874m)で切って
        /// 並べ、両端に妻(破風・鬼・妻壁)を継いだ一体物。門と隅のあいだを**1本で**埋めるための部材。
        /// 在庫の中部材 8.065m / 妻部材 7.910m の固定寸法では端数が必ず残る
        /// (御蔵門の西に 1.66m の食い込み・東に 0.96m の隙間。2026-08-29 実測)。
        ///
        /// ⚠ **FBX は実寸(m)で出ている。`scale = Vector3.one` で置く**(edogoyomi の .obj と違い ES 不要)。
        /// ローカル: 幅=X(=len) / 高さ=Y / 厚み=Z、**見え面(街路側)= +Z**。
        /// ピボット = **走りの中心・土台の底・壁の外面**。外周線の上に
        /// `position = 区間の中点 / yaw = 外向き法線の方位 / scale = Vector3.one` で置ける。
        /// 軒は +Z へ 0.63m 出て、躯体は −Z へ 3.73m 入る。高さ 5.51m(妻の鬼まで)。
        /// 直線材と同じく **`SeatBottom(seat − 0.10)`** で沈めること(隅部材と段差が出る)。
        ///
        /// len は m。**任意の長さを 1cm 単位でそのまま作れる**(窓割りの本数 k と無地の壁の
        /// 詰め ε で吸うので、瓦・海鼠・格子の形は一切伸びない)。L≥12m で ε は ±0.21m 以内。
        /// 無い長さは:
        ///   blender --background --python Tools/Blender/build_nagaya_omote.py -- &lt;長さm&gt; [--render]
        /// 隣へ突き付ける(妻を出さない)版が要るときは `-- &lt;長さm&gt; --ends none`
        /// → `Nagaya_Omote_&lt;len&gt;_none.fbx`。</summary>
        public static string NagayaOmote(float len) { return NagayaOmote(len, true); }
        /// <summary>Blender の生成器がファイル名に使う数字の書き方
        /// (<c>("%.2f" % L).rstrip("0").rstrip(".")</c>)を C# 側で**同じ結果**に再現する。
        ///
        /// ⛔ <c>float.ToString("0.##")</c> は使えない。.NET は書式化の前に**最短往復表現**へ
        /// 丸めるので、<c>73.475f</c>(実体は 73.4749984…)が "73.48" になり得る。生成器は
        /// 格納された値そのものを丸めて <c>..._73.47_2f.fbx</c> を出すので、名前が食い違う。
        /// ⚠ パスの取り違えは <c>LoadAssetAtPath</c> が **null を返すだけ**で例外にならない
        /// (CLAUDE.md 規則12)ので、目で気づけない。
        /// ⭕ 格納された値を 1/100 単位へ落としてから文字列にする。
        /// ⚠ 二進で厳密に x.xx5 になる値(0.125 など)だけは Python の偶数丸めと割れるが、
        ///   run 長のような十進リテラル由来の値では起きない。</summary>
        static string Len2(float m)
        {
            long h = (long)System.Math.Floor((double)m * 100.0 + 0.5);
            string t = (h / 100L).ToString(System.Globalization.CultureInfo.InvariantCulture);
            long f = h % 100L;
            if (f != 0L) t += "." + (f % 10L == 0L ? (f / 10L).ToString() : f.ToString("00"));
            return t;
        }

        /// <summary>二階建ての表長屋(案A・**ユーザー裁定 2026-08-29**)。
        /// 海鼠壁は腰壁のまま動かさず、白壁の帯を 1.673m 積んで階を作る(H 5.509 → 7.183m)。
        /// ⛔ 海鼠を二階の腰まで立ち上げない — 平屋の区間との継ぎ目で帯が 2.1m 段になる。
        /// ⚠ 上階の窓の位置は**典拠が無い【確度P】**(温古写真は画角外)。一次史料が出たら覆せる。
        ///   blender --background --python Tools/Blender/build_nagaya_omote.py -- &lt;長さm&gt; --floors 2 --render
        ///
        /// ⭐ **岡部の表門の両袖**(辺12・ユーザー裁定12-A 2026-09-04)。`len` は **run 長そのもの**を渡す
        /// (`E_Nagaya_S` 6.189 / `E_Nagaya_N` 73.475)。⛔ **妻の出を足さない** — 生成器の `len` は
        /// 破風まで含む全幅で、6.189 + 16.362(表門) + 73.475 = 96.026 が辺12にちょうど収まり、
        /// 隣り合う破風どうしが突き付く。実寸は W=len(X) × H 7.183(Y) × D 4.352(Z)。</summary>
        public static string NagayaOmote2F(float len)
        {
            return "Assets/Edo/Models/Nagaya/Nagaya_Omote_" + Len2(len) + "_2f.fbx";
        }
        /// <summary>**長屋門**(ユーザー裁定 2026-08-30)— 表長屋の躯体を門の上まで通し、
        /// その足元に門口を抜いた版。**扉(両開きの板戸)は部材に作り付け**(裁定2-A 2026-08-31)。
        ///
        /// ⛔ **開口だけの短い部材は作れない**(妻2つ+bay で最小およそ 5.2m)。門口は
        /// 必ず長い run の中に開ける。⚠ `gateFromLeft` は**部材のローカル +X の左端からの
        /// 中心距離**[m]。生成器は書き出す前に Z まわりに 180° 回すので、obj 空間では
        /// 右端から測って抜いている(取り違えると門口が反対の端に出る)。
        /// 有効高は**土台の底から**測る。1階の軒までおよそ 3.9m あるので 3.3m の門口が収まる。
        ///
        /// ⚠ **`len` は破風(妻)まで含む全幅。** 破風は土台の小口より片側 0.352m 外へ出るので、
        /// 柱通りで寸法を組むときは `len = 桁行 + 0.704` にする(隣の棟と突き付けるときは
        /// 全幅どうしを足せば継ぎ目が合う)。
        ///
        /// ⭐ **岡部の表門**(ユーザー裁定12-A 2026-09-04: 表長屋の棟 7.183 に対し**門は 8.5**)。
        /// 桁行9間16.362 / 梁間 4.35 / 門口 2間3.636 を中央(=len/2)に / 両端の番所 各1.5間は
        /// **躯体内の出格子**。棟は `--ridge` で上げる — **瓦の勾配は不変で軒高だけで稼ぎ**、
        /// 上げ代は各階へ等分される。⛔ 全部を軒下へ積むと二階の窓の上に 2.3m の
        /// のっぺりした白壁が残り、門でなく土蔵に見える。
        ///   blender --background --python Tools/Blender/build_nagaya_omote.py -- 16.362 --gate 8.181 3.636 3.30 --doorh 3.30 --floors 2 --ridge 8.5 --bansho 2 --kabuki 0.42 --render
        ///
        /// 実寸(Unity): W 16.362(X) × H 8.500(Y) × D 4.352(Z)。ピボット = **走りの中心 /
        /// 敷居(=土台の底) / 壁の外面**。見え面 = +Z で軒が +Z へ 0.626 出て躯体は −Z へ 3.726 入る。
        /// 敷居レベルに置くので、街路 12.25 の表門なら `position.y = 12.25`。</summary>
        public static string NagayaOmoteMon(float len, float gateFromLeft, bool nikai)
        {
            return "Assets/Edo/Models/Nagaya/Nagaya_Omote_" + Len2(len)
                 + "_mon" + Len2(gateFromLeft) + (nikai ? "_2f" : "") + ".fbx";
        }

        /// <summary>tsuma=false は両端を突き付けにした版(`--ends none`)。鎖の途中の一本に使う。</summary>
        public static string NagayaOmote(float len, bool tsuma)
        {
            return "Assets/Edo/Models/Nagaya/Nagaya_Omote_" + Len2(len)
                 + (tsuma ? "" : "_none") + ".fbx";
        }

        // ---------------------------------------------------------------- 崖下(法尻の帯)の部材
        /// <summary>**崖下の詰人長屋**(岡部邸 `service` の N1/N2、`roofs.ObiNagaya`)。
        /// 平屋・**桟瓦(いぶし黒)**・**下見板の腰**(なまこ無し)・**水側は盲面で開口は東**。
        /// 表長屋(本瓦・二階・なまこ)と**格を分ける**のが指図の宣言なので、
        /// <see cref="NagayaOmote(float)"/> で代用しないこと。
        ///
        /// ローカル: 幅=X(桁行)/ 高さ=Y / 厚み=Z。**+Z = 開口面(指図で言う東・山側)/
        /// −Z = 盲面(水側)**。⚠ 据えるとき +Z を山側へ向ける(逆にすると盲面の意味が反転する)。
        /// ピボット = **footprint の中心・地盤レベル**なので `service` の (u0..u1, v0..v1) の
        /// 中心をそのまま使える。⚠ **軒はピボットの矩形の外へ出る** — 長手 ±Z に 0.900m
        /// (指図 `nishi.obi.nokiOut` と実測一致)、妻 ±X に 0.37m。
        /// 7.5×2.5間の実寸 14.375(X) × 4.300(Y) × 6.537(Z)、**棟天端 4.300**
        /// (指図 `roofs.ObiNagaya.ridgeH` と一致)、軒桁 2.700。
        /// 生成: blender --background --python Tools/Blender/build_obi_nagaya.py -- nagaya --ken 7.5 2.5</summary>
        public static string ObiNagaya(float wKen, float dKen)
        {
            return NagayaDir + "Obi_Nagaya_" + wKen.ToString("0.##") + "x"
                 + dKen.ToString("0.##") + "ken.fbx";
        }
        /// <summary>梁間は家臣長屋の規約どおり 2.5間(`const.nagayaD` = 4.545m)固定。</summary>
        public static string ObiNagaya(float wKen) { return ObiNagaya(wKen, 2.5f); }

        /// <summary>**崖下の物置**(岡部邸 `service.M1`)。3×1.5間・長屋と同じ作りで開口1
        /// (中央に2間の両開き板戸)。実寸 6.194 × 3.804 × 4.419、棟天端 3.804・軒桁 2.700。
        /// ⚠ 軒の出は **0.75m【U】**(指図の 0.9 は長屋について測る値。1.5間の小屋に 0.9 を
        /// 出すと屋根が躯体の2倍近くになるので下げた)。ピボット・向きは <see cref="ObiNagaya(float,float)"/> と同じ。
        /// 生成: blender --background --python Tools/Blender/build_obi_nagaya.py -- monooki</summary>
        public const string ObiMonooki = NagayaDir + "Obi_Monooki_3x1.5ken.fbx";

        /// <summary>**崖下のかわや**(岡部邸 `service.K_Obi`)。1間角・戸1。
        /// 実寸 2.558 × 2.941 × 3.210、棟天端 2.941。⚠ 軒高 **2.20【U】**・軒の出 **0.60【U】**
        /// — 指図の 2.70/0.9 のままだと1間角の塔になる。西面の目隠し(建仁寺垣・指図
        /// `nishi.obi.fences`)は**この部材に作り付けていない** — Unity 側で立てること。
        /// 生成: blender --background --python Tools/Blender/build_obi_nagaya.py -- kawaya</summary>
        public const string ObiKawaya = NagayaDir + "Obi_Kawaya_1ken.fbx";

        const string NagayaDir = "Assets/Edo/Models/Nagaya/";

        /// <summary>**通用口の棟門**(岡部邸 `komon.Tsuyodo` — 袋小路に開く勝手口)。
        /// 二本の本柱の上に直に切妻を載せる最も簡素な門。⚠ 在庫の門は薬医門(`Eg.Kmon`)・
        /// 冠木門・城門しかなく、**棟門は無い**。通用口に薬医門を据えると格が上がる。
        ///
        /// ローカル: 幅=X(門口の方向)/ 高さ=Y / 厚み=Z、**+Z = 外(袋小路の側)**。
        /// ピボット = **門の芯・敷居レベル**なので `komon[].sill`(16.06)をそのまま y に使える。
        /// 有効高 2.40・**棟天端 3.60**・**底は −0.260**(沓石が敷居より下へ出る)。
        /// 焼いてある門口(`komon[].w`): **2.7** と **2.727**(=1.5間)。
        /// ⚠ ファイル名は**小数2桁**(`ToString("0.##")`)なので 2.727 は `Munamon_2.73.fbx`。
        ///   実寸(門口 2.727): 4.627(X) × 3.860(Y) × 2.592(Z)。
        ///   実寸(門口 2.7  ): 4.600(X) × 3.860(Y) × 2.592(Z)。
        /// ⭕ **袖塀と突き付けるなら 2.727 を使う** — 2.7 だと両脇に 0.03m の隙が出る(規則5)。
        ///
        /// <paramref name="opened"/> = true で**内開きに 78° 開いた**版。扉が −Z へ 1.3m ほど
        /// 張り出すので、据える所の内側にその余地が要る(bbox の D が 2.641 へ増える)。
        /// ⚠ **仮置き【U】**: 棟高3.60 / 本柱 0.24角(「φ0.24」を角柱の見付として採った)/
        /// 冠木下端2.40 / 桁3.00 / 梁間1.30 / 軒の出0.55 / 扉の丈・振れ角。指図に無い。
        /// 生成: blender --background --python Tools/Blender/build_munamon.py -- --w 2.727 [--render]</summary>
        public static string Munamon(float w, bool opened)
        {
            return MonDir + "Munamon_" + w.ToString("0.##") + (opened ? "_Open" : "") + ".fbx";
        }
        public static string Munamon(float w) { return Munamon(w, false); }

        const string MonDir = "Assets/Edo/Models/Mon/";

        // ---------------------------------------------------------------- 丸太物(手すり・汀の杭)
        /// <summary>**丸太の手すり 1スパン**(岡部邸 `routes.R_Katte.outsideRail.tesuri`)。
        /// 柱 φ0.12・高さ0.90・芯々1間、**横木は丸太1段**。⛔ 竹垣にしない — 法肩の竹垣と
        /// 読み違える。道の外肩が 1.2m 落ちる所の落下止め。
        /// ⭕ **在庫の丸太**(NatureManufacture `wood_log_0X`)を切って使っているので樹皮が本物。
        ///
        /// ローカル: 幅=X(走り)/ 高さ=Y / 厚み=Z。ピボット = **スパンの中心・地盤レベル**。
        /// 柱はスパンの **−X 端**に立ち、横木は −X 端から +X 端まで通る。
        /// ⇒ 折れ線の各スパンの中点に yaw を与えて並べれば柱が 1.818 ピッチで立ち横木が続く。
        /// ⛔ **run の +X 端には <see cref="MarutaTesuriPost"/> を1本足すこと** —
        ///    足さないと最後の横木が宙で終わる。
        /// 実寸 1.865 × 0.920 × 0.119。
        /// 生成: blender --background --python Tools/Blender/build_maruta.py -- tesuri</summary>
        public const string MarutaTesuri = MarutaDir + "Maruta_Tesuri_1ken.fbx";

        /// <summary>手すりの run の端に足す柱1本。ピボット = 柱の芯・地盤レベル。
        /// 実寸 0.107 × 0.920 × 0.119。</summary>
        public const string MarutaTesuriPost = MarutaDir + "Maruta_Tesuri_Post.fbx";

        /// <summary>**汀の杭 1本**(岡部邸 `nishi.kuiretsu`)。全長 1.55(根入れ1.2)・傾 5°。
        /// <paramref name="dia"/> は 0.12 / 0.15 / 0.18 の3種(指図 `dMin`..`dMax`)。
        /// ⛔ **1種で並べない・芯々を等間隔にしない**(`pitchMin` 0.30〜`pitchMax` 0.40)。
        ///
        /// ピボット = **頭の芯**で、杭は −Y へ 1.55 垂れる。⇒ `y = 水面 + rand(0.25, 0.45)`
        /// (`topMin`/`topMax`)を直に入れればよい。傾き 5° は **+X 方向へ焼き込んである**ので、
        /// **yaw を乱数で振れば傾きの方位が散る**。実寸(0.12)0.247 × 1.548 × 0.106。
        /// 生成: blender --background --python Tools/Blender/build_maruta.py -- kui</summary>
        public static string Kui(float dia)
        {
            return MarutaDir + "Kui_" + dia.ToString("0.00") + ".fbx";
        }

        /// <summary>杭列の**貫**(`nishi.kuiretsu.nuki`)。⚠ 指図の「1段」は杭の芯々(0.3〜0.4m)
        /// ごとだが、**それでは部材が数千本になる**ので **1間(1.818m)の丸太1本**として出した。
        /// 据えるときは `y = 杭の頭 − 0.35`(`nuki.below`)、杭列の水側へ寄せて走りに沿って回す。
        /// ピボット = 中心・水平。実寸 1.818 × 0.080 × 0.082。
        /// 生成: blender --background --python Tools/Blender/build_maruta.py -- nuki</summary>
        public const string KuiNuki = MarutaDir + "Kui_Nuki_1ken.fbx";

        const string MarutaDir = "Assets/Edo/Models/Maruta/";

        /// <summary>御殿の**入母屋屋根**を間数で引く。⚠ 実体は <see cref="Goten.RoofIrimoya_"/> で、
        /// これはそこへの転送(⛔ パスの literal を二重に書かないため)。棟梁が `Own.` の下で
        /// 探すので入口だけ用意してある。<paramref name="wKen"/> は桁行(大棟の走る側)で
        /// **wKen ≥ dKen** で呼ぶこと(足りない向きで呼ぶと棟が短辺に架かる)。
        ///
        /// 岡部邸で焼いてあるもの(実寸 X × Y(高) × Z / 三角形数):
        /// 11×11 玄関棟 22.14×6.76×22.14 (32,572) / 13×6 書院棟 25.78×4.28×13.05 (23,973) /
        /// 12×10 台所棟 23.96×6.26×20.32 (31,839) / 11×9 中奥棟 22.14×5.76×18.50 (28,838) /
        /// 12×9 奥向棟 23.96×5.76×18.50 (30,879) / 20×7 長局 38.50×4.77×14.87 (39,558)。
        /// ⚠ **外形は間数より 2.14m 大きい**(軒の出 0.90 が四周に付く)。棟の壁面で合わせない。
        /// 無い寸法は:
        ///   blender --background --python Tools/Blender/build_goten_roof.py -- &lt;桁行m&gt; &lt;梁間m&gt; Goten_Roof_Irimoya_&lt;w&gt;x&lt;d&gt;ken</summary>
        public static string GotenRoofIrimoya(int wKen, int dKen)
        {
            return Goten.RoofIrimoya_(wKen, dKen);
        }

        /// <summary>折れ角のある隅の部材(留め継ぎ)。生成は Tools/Blender/build_kado.py。
        /// 在庫の出隅ブロックは折れ角 Δ≳60° でしか成立しないので、浅い折れはこれで納める。
        /// ローカル: 走り(進行方向) = +Z ／ 躯体 = −X ／ 原点 = 折れ点・足元・内面。
        /// 据えは `position = 折れ点 / yaw = 入りの走りの方位 / scale = (s,s,s)`。
        /// deg が負(名前の末尾 M)は鏡像 = yaw が**減る**向きの折れ。
        /// 腕は片側 1 モジュールなので、入りの run は 1 モジュール短く、出の run は
        /// 1 モジュール遅く始める。
        ///
        /// ⚠ **名前は `RoundToInt(|deg|)` の 2 桁**なので、|deg| &lt; 0.5° は `00` に丸まる。
        /// 生成器(build_kado.py)も同じ丸めで名前を作るので一致する。
        /// ⭕ **浅い折れも留めで通る** — Δ=0.24° は「ほぼ直材」の一枚物として焼ける
        /// (2026-09-04 実測。突き付けに逃げる必要は無い)。
        ///
        /// 焼いてあるもの(Dobei = 練塀。腕は折れ点から ±2.26m・高さ 1.455m・s を掛けて据える):
        /// 00M 01M 06 07 11 14M 18 19 31 38M 41 62M 88M 91 95M ／ Ishigaki 31・31M ／
        /// Tsuijibei 31 ／ Nagaya 38M。無い角度は:
        ///   blender --background --python Tools/Blender/build_kado.py -- --part dobei --deg &lt;符号つき角度&gt; --render</summary>
        public static string Kado(string part, float deg)
        {
            return "Assets/Edo/Models/Kado/" + part + "_Kado_"
                 + UnityEngine.Mathf.RoundToInt(UnityEngine.Mathf.Abs(deg)).ToString("00") + (deg < 0f ? "M" : "") + ".fbx";
        }

        public const string MShop01     = "Assets/Edo/Materials/M_Shop01.mat";
        public const string MShop02     = "Assets/Edo/Materials/M_Shop02.mat";
        public const string MKido       = "Assets/Edo/Materials/M_Kido.mat";
        public const string MKidobanya  = "Assets/Edo/Materials/M_Kidobanya.mat";
        public const string MJishinban  = "Assets/Edo/Materials/M_Jishinban.mat";
        public const string MGateStone  = "Assets/Edo/Materials/GateStone.mat";
        // 自作マテリアルの名前引き(規則11: パスの literal はここ以外に書かない)
        public static string Mat(string name) { return "Assets/Edo/Materials/" + name + ".mat"; }

        /// <summary>松江松平邸の表門 — **屋根なしの冠木門**(角柱・冠木・内開き扉・潜り戸・袖塀の一体物)。
        /// 姿は温古写真集11(88005761・明治初撮影)の実見【A】+『日本案内記 関東篇』昭和5年【A】。
        /// ⚠ 切妻小屋根を載せる前案は 2026-08-23 に撤回済み。**屋根なしが正**。
        /// 在庫の es_kmon は薬医門(小屋根あり)、es_kabukimon は柱高3.74mで指図の5.2mに足りない。
        /// 実寸 W13.12 × D0.52 × H5.30(開口13.0m=五千分一図の実測)。
        /// **ピボット = 門の芯・敷居レベル**なので gate.pos と gate.sill をそのまま使える。
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_omotemon.py -- [--render]</summary>
        public const string MatsudairaOmotemon = "Assets/Edo/Models/Mon/Matsudaira_Omotemon.fbx";

        /// <summary>松江松平邸の表門の番所 — **向唐破風・出格子・切石畳出の基壇**。左右に2棟。
        /// 姿は温古写真集11【A】+『日本案内記 関東篇』昭和5年「両側に唐破風造の番所」【A】。
        /// 在庫の es_dbansho(3.6×2.1m)は規模も意匠も不足。指図 gate.plan.bansho は 5.5×3.6m・張出2.0m。
        /// ⚠ 唐破風は**中央が起り・両端が照りで反り上がる S 字**。単純な sin にすると樽屋根になる。
        /// ⚠ 出格子は**細い竪子を密に**。太い方立を疎に並べると牢格子に見える。
        /// **ピボット = 走り方向の芯・基壇の下端**。
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_bansho.py -- [--render]</summary>
        public const string MatsudairaBansho = "Assets/Edo/Models/Mon/Matsudaira_Bansho.fbx";

        /// <summary>松江松平邸の附属屋・工作物。すべて `Tools/Blender/build_matsudaira_dewa_fuzokuya.py`
        /// で起こす(在庫照会 `docs/asset-catalog.md` §10「無い物」の結果 — 井戸・鳥居・祠・二層櫓は
        /// 目録に無く、土蔵・数寄屋・作事小屋は在庫の寸法が指図に合わない)。
        /// **ピボットは footprint の中心・地盤レベル**。ローカル +X = 桁行、+Z = 表。
        /// 作り直し: `blender --background --python Tools/Blender/build_matsudaira_dewa_fuzokuya.py -- &lt;名&gt; [--render]`
        /// (名 = dozo / koya / sukiya / inari / ido / yagura。省くと全部)</summary>
        public static class Matsudaira
        {
            /// <summary>土蔵 4×7間。実寸 13.76(X) × 7.12(Y) × 8.89(Z)</summary>
            public const string Dozo   = FuzokuyaDir + "Matsudaira_Dozo.fbx";
            /// <summary>御作事小屋 10×4間(片側の長手が開いた小屋)。実寸 19.32 × 5.50 × 8.99</summary>
            public const string Koya   = FuzokuyaDir + "Matsudaira_Koya.fbx";
            /// <summary>御茶屋(数寄屋)2.5間角・宝形の柿葺。実寸 6.55 × 4.44 × 6.55</summary>
            public const string Sukiya = FuzokuyaDir + "Matsudaira_Sukiya.fbx";
            /// <summary>稲荷社(明神鳥居+一間社流造の小祠)。実寸 2.50 × 2.76 × 3.34。
            /// 鳥居は +Z 側 = 祠の正面。据えるときは参道を +Z へ向ける</summary>
            public const string Inari  = FuzokuyaDir + "Matsudaira_Inari.fbx";
            /// <summary>石井戸枠+釣瓶の桁。実寸 1.90 × 2.21 × 1.90。**枠の天端は地盤+0.72**</summary>
            public const string Ido    = FuzokuyaDir + "Matsudaira_Ido.fbx";
            /// <summary>二重の隅櫓 3間角。実寸 7.39 × 8.64 × 7.39。据えは石垣の天端</summary>
            public const string Yagura = FuzokuyaDir + "Matsudaira_SumiYagura.fbx";
        }
        const string FuzokuyaDir = "Assets/Edo/Models/Fuzokuya/";

        // ---------------------------------------------------------------- 岡部邸の附属屋・結界
        /// <summary>**厩** 4×9間(岡部邸 `service.Umaya`)。長手 = v。**前面(+Z)は吹き放ち**で
        /// 足元に半高の板壁、馬房を4つに仕切る。背面と両妻は下見板。
        /// ローカル: 幅=X(**長手 = v**)/ 高さ=Y / 厚み=Z、**+Z = 開いている側**。
        /// ⇒ 据えるときは **ローカル +X を +v へ**向ける yaw を与える。
        /// ピボット = footprint の中心・地盤レベル。実寸 17.142 × 5.174 × 9.164。
        /// ⚠ **仮置き【U】**: 軒高 2.85 / 馬房4 / 軒の出 0.85 / 切妻。指図は位置と間数だけを持つ。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- umaya</summary>
        public const string Umaya = FuzokuyaDir + "Okabe_Umaya.fbx";

        /// <summary>**供待** 3×5間(岡部邸 `service.Tomomachi`)。長手 = v。
        /// **前面(+Z)は腰高まで塞いで上は吹き放ち**、床は板張りの縁。背面と妻は下見板+漆喰。
        /// 実寸 9.870 × 4.508 × 7.346。向き・ピボットは <see cref="Umaya"/> と同じ。
        /// ⚠ **仮置き【U】**: 軒高 2.70 / 軒の出 0.85 / 切妻。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- tomomachi</summary>
        public const string Tomomachi = FuzokuyaDir + "Okabe_Tomomachi.fbx";

        /// <summary>**納戸小屋** 1.5×1間・**板葺**(岡部邸 `service.Nando_Nagatsubone`)。
        /// 長局の物干の道具を仕舞う小屋。⛔ **瓦を葺いていない** — `roof 2x2` の勾配は
        /// 0.5456 固定で 1間の小屋には棟が高すぎるため、指図どおり板葺(勾配 0.40【U】)にした。
        /// 長手 = u(1.5間)。実寸 3.247 × 2.722 × 2.658。**+Z に片開きの板戸**。
        /// ⚠ **仮置き【U】**: 軒高 2.05 / 板葺の勾配 0.40 / 軒の出 0.42。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- nandokoya</summary>
        public const string NandoKoya = FuzokuyaDir + "Okabe_NandoKoya.fbx";

        /// <summary>**車寄** 3間(間口)× 2間(奥行)(岡部邸 `munes[0]` / `roofs.Goten_Kurumayose`)。
        /// 指図の「⛔ **入母屋を架けない・入側を回さない別種**」に従い、**四方を開けた寄せ**
        /// (柱8本+頭貫+桁+天井板)に**妻入の切妻**を架けた — 参道から見て破風が正面に来る。
        /// 前庭は真砂土の叩きなので**床を張っていない**。
        ///
        /// ローカル: **+X = +u(間口)/ +Z = 参道の側(= −v)**。ピボット = footprint の中心・**地盤**レベル。
        /// ⚠ 玄関棟は +v 側に建つので、据えるときは **ローカル −Z を玄関の面へ**向ける。
        /// 実寸 7.146 × 4.342 × 4.376(軒桁 2.30 / 軒先 1.89 / **棟天端 4.34**)。
        ///
        /// ⚠⚠ **裁定事項** — 棟天端 4.34 は玄関棟の軒先(床0.62+2.577 = **地盤+3.20**)より
        /// **1.14m 高い**。⇒ 車寄の背面の屋根は玄関棟の屋根面へ食い込む(実物の車寄の納まりだが、
        /// 見え方を決めるのは普請奉行)。⛔ 軒桁を下げて逃げると人がくぐれない。
        /// 原因は瓦の勾配が `roof 2x2` の実測 0.5456 に固定で、3間の span では避けられないこと。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- kurumayose</summary>
        public const string Kurumayose = FuzokuyaDir + "Okabe_Kurumayose.fbx";

        /// <summary>**車寄(切り欠き済み)** — 玄関棟の屋根へ差し込むための納めを**部材の側で解いた**版
        /// 【2026-09-04 ユーザー裁定10=A】。⭕ 棟梁は実行時にメッシュを割らないので、こちらを据える。
        /// ⛔ 素の <see cref="Kurumayose"/> を置いて交差させたままにしない — 瓦が二重に見える。
        ///
        /// 切るのは **玄関棟の屋根面そのもの**(2026-09-04 焼き直し):
        /// <code>v ≧ atV の側で、面からの高さ z &gt; aboveY + (v − atV) × 1.818 × slope を落とす</code>
        /// atV = 51.505 間 / aboveY = 3.197 m / **slope = 0.5456**(= 瓦モジュールの 5.5寸勾配)。
        /// ⛔ 玄関棟の屋根は切らない(親側は無傷)。
        ///
        /// ⚠⚠ **`aboveY` の水平面では切れない。**玄関棟の屋根は軒先から 5.5寸で上がる斜面なので、
        /// 水平面で切ると(a)軒下に隠れて見えない所まで落とし、(b)切り口の壁が軒先の線に立って
        /// 玄関棟の軒先と同じ面で喧嘩する。⇒ 棟梁の実機が「屋根面に 177 頂点食い込む」と出したのは
        /// これ。⭕ 斜面で切ると車寄の屋根が**玄関棟の軒の下へ滑り込む**(検証レンダで確認済)。
        ///
        /// ⚠⚠ **<see cref="EdoOkabeYashikiBuilder"/> の <c>KirikakiCheck</c> は水平面のままなので、
        /// この版を据えると 278 頂点(最大 +0.643m)を誤検出する。**⭕ 判定式を上の斜面へ
        /// 揃えること(揃えれば残り 0 頂点 — 焼いた FBX を実測して確認済)。
        /// ⭐ **指図 `kirikaki` にも `slope` を持たせるのが筋**(いまは生成器が瓦モジュールの
        /// `R.RATIO` で補っている)。⛔ 部材方は指図を書き換えない — 指図方へ回すこと。
        ///
        /// ローカル・ピボット・材質は素の版と同一(**+X = +u / +Z = 参道の側**、footprint の中心・地盤)。
        /// 外形の実寸も同じ **7.146 × 4.342 × 4.376** — 落ちるのは奥(+v)の上部だけで、
        /// 参道から見える破風・棟・軒はすべて素のまま残る。面 1381 → **1633**。
        /// ⚠ 切り口は**開けたまま**(玄関棟の屋根の下に隠れる位置)。⛔ 塞ぐと瓦の開いたシェルまで
        ///   一緒に張られて屋根の上に膜が出る(2026-09-04 に踏んだ)。
        ///
        /// ⭕ **決着済**【2026-09-04 ユーザー裁定 = B】。`atV` は 51.505 間
        ///   (= 外壁 52.0 間 − 軒の出 0.90m / 1.818)。⛔ **単位を混ぜない** — 従前の 51.1 は
        ///   間と m を混ぜて引いた値で、玄関棟の軒先より 0.736m 手前を切るため平らな切り口が
        ///   露天に出ていた。生成器が焼くたびに指図の導き方で検算して食い違いを叫ぶ。
        /// ⚠ 屋根 FBX の bbox(22.140)から軒の出を出すと 1.071m になるが、**それは隅棟の角の
        ///   飛び出し**で、車寄の載る帯(|u|≦3.60)では 0.900 ちょうど(実測)。
        /// 重ねて見る: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- sashikomi
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- kurumayose_cut --render</summary>
        public const string KurumayoseCut = FuzokuyaDir + "Okabe_Kurumayose_Cut.fbx";

        /// <summary>**御錠口** 3間角(岡部邸 `links[2]` L_Jouguchi)。表向と奥向を分ける
        /// **一口だけ**の口([西川1959]/[高知2000] A)。**幅一間の渡廊下**が ±X の面に取り付く。
        /// ⭕ **+X の開口に御錠口の唐戸(両開きの板戸)を建て込んである。** −X 側は開けたまま。
        /// ±Z は白漆喰の大壁に連子窓(裏に明かり障子)。
        ///
        /// ローカル: **+X = 廊下の通る向き**。ピボット = footprint の中心・**床レベル**
        /// (⚠ 地盤ではない — `EdoGotenKit` の棟と同じ規約。据えるときは 面 + `const.gotenFloor` 0.62)。
        /// 実寸 7.596 × 5.858 × 7.596、**底 −0.620**(基壇が床より下へ出る)。軒先は棟と揃えて床+2.577。
        ///
        /// ⚠⚠ **裁定事項** — 入母屋なので棟天端が **床+5.24** になり、渡廊下(大棟天端 床+2.503)
        /// より 2.7m 高い。実物でも御錠口は一段高い屋根で標すが、⭕ 姿を決めるのは普請奉行。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- jouguchi</summary>
        public const string Jouguchi = FuzokuyaDir + "Okabe_Jouguchi.fbx";

        /// <summary>**稲荷社の小祠** 1.5間角(岡部邸 `service.Inari`)。台石+一間社流造の小祠。
        /// **+Z = 正面(南)**。ピボット = footprint の中心・地盤レベル。実寸 2.727 × 2.540 × 2.727。
        /// ⛔ **鳥居はこの部材に入っていない** — 指図 `gardens[3].yashiro` が「躯体の矩形は
        /// service/Inari が持つ」と書いており、鳥居・参道・四つ目垣は庭方が別に範囲を決めている。
        /// 鳥居は <see cref="Torii"/> を参道へ据えること。
        /// ⛔ **在庫の <see cref="Matsudaira.Inari"/> は流用できない** — あれは**朱の明神鳥居**込みで、
        /// 指図 `certs.garden.inari` の「玉垣・朱鳥居は使わない」に反する。
        /// ⚠ **当屋敷に稲荷があった記録は無い=U**(一般類型)。姿も一般形。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- inari15</summary>
        public const string Inari15 = FuzokuyaDir + "Okabe_Inari15.fbx";

        /// <summary>**素木の明神鳥居**(稲荷の参道の点景)。⛔ **朱に塗らない**(指図の明文)。
        /// ローカル: 幅=X(柱の並び)/ 高さ=Y / 厚み=Z。ピボット = **柱の芯の中央・地盤レベル**。
        /// 実寸 2.000 × 2.320 × 0.300、**底 −0.100**(根巻石が地盤より下へ出る)。内法幅 1.30・柱高 1.85。
        /// 生成: blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- torii</summary>
        public const string Torii = FuzokuyaDir + "Okabe_Torii.fbx";

        /// <summary>**のし塀**(熨斗瓦を載せた白壁の袖塀)。岡部邸の**結界** `kekkai` の7本。
        /// ⛔ 外構の練塀・築地塀で代用しないこと — 指図が「**屋内の仕切りなので外構より軽く**」と
        /// 明記している(`assetCert`)。⭕ 笠木は Village Kit の `roof top x1`(冠瓦+熨斗2段の
        /// 実ジオメトリ)を継いである。
        ///
        /// ローカル: 幅=X(走り)/ 高さ=Y / 厚み=Z。ピボット = **走りの中心・地盤レベル・壁の芯**
        /// (⚠ 面ではなく芯 — 塀は表裏が同じ作り)。⇒ `position = 区間の中点 / yaw = 走りの方位 /
        /// scale = Vector3.one`。高さは **1.800 ちょうど**(`kekkai[].h` と一致)、厚み 0.47
        /// (壁 0.30 + 腰石の出 + 控柱 0.10。控柱は **−Z 側**に片側だけ)。
        ///
        /// 焼いてある長さ(**現行** = 指図の7本を、据えた開口部材の**実メッシュ**で割った実長):
        /// **1.82**(W4・W7)/ **2.69**(W1 東)/ **3.64**(W2)/ **5.45**(W3)/
        /// **20.67**(W5)/ **44.24**(W1 西)/ **53.67**(W6)。
        /// ⚠⚠ **run の長さは開口の呼び寸法では出ない。**<see cref="EdoOkabeYashikiBuilder"/> の
        /// `PlaceKekkai` は据えた門・木戸の **OBB の走り方向の実寸**で塀を切る(CLAUDE.md 規則5)。
        /// 実測: 中門 `Munamon_2.73` = **4.627**(⚠ **軒の出込み**で開口より 1.90 広い)/
        /// 木戸 `Kido_2.73` = **3.197** / `Kido_2.91` = **3.379**。
        /// ⚠ 旧値 3.64(W1 東)/ 20.91 / 45.19 / 53.45 の FBX は**残してある**(参照が残りうるため)が、
        /// いまの指図では**どれも据わらない**。
        /// ⚠ **開口(中門・木戸)はこの部材に含まれない。**中門は <see cref="Munamon(float,bool)"/>
        /// (門口 **2.727m = 1.5間**。2.7 だと両脇に 0.03m の隙が出る)、木戸は <see cref="Kido(float)"/>。
        /// 焼き直し: blender --background --python Tools/Blender/build_noshibei.py -- kekkai
        /// 無い長さは: blender --background --python Tools/Blender/build_noshibei.py -- &lt;長さm&gt;</summary>
        public static string Noshibei(float len)
        {
            return "Assets/Edo/Models/Hei/Noshibei_" + len.ToString("0.##") + ".fbx";
        }

        /// <summary>**結界の木戸**(のし塀 `kekkai[].gap` の開口を塞ぐ)。方立柱2本+冠木+敷居+板戸。
        /// ⚠ <see cref="Noshibei(float)"/> は**開口を含まない**ので、W5・W6 の口はこれで塞ぐ。
        ///
        /// ローカル: 幅=X(開口の走り)/ 高さ=Y / 厚み=Z。ピボット = **開口の芯・地盤レベル**
        /// (塀の芯と揃う)。**+Z = 見え面**。⇒ のし塀の run と同じ yaw を与えれば面が揃う。
        /// ⚠ **X の実寸は開口より柱2本ぶん広い** — 開口 2.727 → 実寸 3.197 / 2.909 → 3.379。
        /// **塀の run はこの実寸の外側に取り付く**(開口の値で継ぐと 0.47m 食い込む)。
        /// 高さ 1.940(柱 1.80 + 沓石が −0.140 まで下がる)・内法 1.50【U】。
        ///
        /// 焼いてあるのは 2.73(W5「庭掃除と落葉出し用」1.5間)と 2.91(W6「勝手の木戸」1.6間)。
        /// ⚠⚠ **W6 は指図の中で数が3つ食い違う** — `gap.from/to` の差 3.00間 /
        /// `gap._` の文言 1.6間 / 塀の実際の口(`b` が v111.25 なので)1.85間。
        /// ⭕ ここでは**文言の 1.6間**を採った(最新の裁定8=A の帰結として書かれているため)。
        /// ⛔ **指図側で1つに揃うまで据えないこと。**
        /// ⚠ **依頼は「片開き」だが 2.7〜2.9m の一枚戸は建具として成立しない**(板 4m² 超)。
        /// ⭕ 開口 1.4m 以下は片開き / 超えたら両開き、として焼いてある。片開きで通すなら
        /// 開口を狭めるか袖に羽目板の固定部が要り、どちらも塀の run が動く=**裁定事項**。
        /// 生成: blender --background --python Tools/Blender/build_kido.py -- kekkai</summary>
        public static string Kido(float w)
        {
            return "Assets/Edo/Models/Hei/Kido_" + w.ToString("0.##") + ".fbx";
        }

        /// <summary>**汀の柵の潜り**(`nishi.saku.kuguri`・辺5 の **s=55.7**)。幅1間・**片開き h1.2**。
        /// ⛔ **「堤へ出る門」ではない** — 区画界より外は当家の地ではない。⭕ 柵の一枚を低い潜りにして
        /// **足元の水を見せる口**で、**敷居が見所⑫を兼ねる**(`nishi.mikoro[0]`「木戸の敷居(堀端)」・立って見る)。
        /// ⛔ **桟橋・船着・水汲みの段を付けない。**
        /// ⚠ 柵は h1.4 のまま下げない(`nishi.saku._`)ので、潜り(1.2)の上の 0.2 は横木で埋めてある。
        /// ⭕ 戸は**縦の簀子** — 閉めても足元の水が透けて見所として働く。
        /// ローカル: 幅=X / 高さ=Y / 厚み=Z。ピボット = **開口の芯・地盤レベル**、**+Z = 見え面**。
        /// 実寸 2.268 × 1.540 × 0.340(**底 −0.140** — 沓石が地盤より下へ出る)。開口は 1.818。
        /// 生成: blender --background --python Tools/Blender/build_kido.py -- horikido</summary>
        public const string HoriKido = "Assets/Edo/Models/Hei/HoriKido.fbx";

        /// <summary>**汀の木柵 1スパン**(`fences[0]` F_Hori・辺5 の全長 s0〜80.589)。
        /// 杭 0.11角 + 貫2段 + 上の横木 + **南京下見に重ねた横板5枚**。
        /// ⛔ **在庫の `Eg.Hogaki5` は実丈 0.79m** で、指図 `const.fenceH` 1.40 に 0.6m 足りない
        /// (視線の遮蔽の計算が天端=地盤+1.40 を前提にしている)。Village Kit の `fence A/B`・
        /// `Fence_B_01` はいずれも**屋根つきの板塀**で「基礎を持たない木柵」ではない。
        /// ⭕ 杭・材・上の横木の高さは <see cref="HoriKido"/>(潜り)と揃えてある。
        /// ローカル: 幅=X(走り)/ 高さ=Y / 厚み=Z。**+Z = 見え面 = 外(水側)**。
        /// ピボット = **スパンの中心・地盤レベル**。実寸 1.818 × 1.520 × 0.148(**底 −0.120** = 根入れ)。
        /// ⛔ **`SeatBottom` で据えない**(根入れぶん 0.12 浮く)— `position.y = 地盤` を直に入れる。
        /// ⚠ 杭は **−X 端**(外面が x=−0.909)。**bbox がちょうど1間**なので、
        ///   **重なりを取らず 1.818 ちょうどのピッチ**で突き付けること(重ねると板が z-fighting する)。
        /// 生成: blender --background --python Tools/Blender/build_hori_saku.py -- [--render]</summary>
        public const string HoriSaku = "Assets/Edo/Models/Hei/HoriSaku.fbx";

        /// <summary>**汀の木柵の端の杭**。⛔ 足さないと run の最後の板が宙で終わる。
        /// ピボット = **run の +X 端(杭の +X 面)・地盤レベル** ⇒ `s = s1` をそのまま渡せる。
        /// 実寸 0.110 × 1.520 × 0.110(**底 −0.120** = 根入れ)。
        /// 生成: blender --background --python Tools/Blender/build_hori_saku.py -- post</summary>
        public const string HoriSakuPost = "Assets/Edo/Models/Hei/HoriSakuPost.fbx";

        // ---------------------------------------------------------------- 庭の点景(岡部邸)
        // 指図 `gardens[]` / 算出物 `okabe_impl.json` の `gardens[].asset` が指す部材。
        // ⛔ **雪見灯籠だけは在庫にある** → <see cref="Eg.ToroYukimi"/>(下の Toro は転送)。
        // 材質は 石 = `M_photoscanned_rocks_01` / 竹垣 = `Bamboo garden fence` /
        // 乱杭 = `M_Wood_fence`。⛔ 新規マテリアルは1つも作っていない。
        // remap は **`Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`**(`Models/Niwa` を見る)。
        const string NiwaDir = "Assets/Edo/Models/Niwa/";

        /// <summary>**庭石1個**(景石・石組護岸の石・岩島・中島の汀石・荒磯の立石を全部これで置く)。
        /// ⭕ NatureManufacture の **photoscanned rock** を切って使っているので写真計測の実肌。
        /// ⛔ 円柱や多面体を自作していない。⛔ `JG.Rock01..03` は使わない
        ///   (FBX 内の材質名が `Test` で remap が当たらない)。
        ///
        /// <para><b>丈をちょうど 1.000 に正規化してある。ピボット = 石の芯・底。</b>
        /// ⇒ 総丈 H で置くなら `localScale = Vector3.one * H`、`position.y = 据える底の高さ`。
        /// 指図の `h` は**露出高**で `buryRatio` 0.333 なので **H = h × 1.5**、
        /// `position.y = 地盤 − 0.5h`(= 地盤 − H/3)。
        /// 護岸石のように**長軸**で指定される場合は `localScale = Vector3.one * (長軸 / W_i)`。</para>
        ///
        /// <para><paramref name="i"/> = 個体 0..4。⛔ **1種で並べない**(指図は「不同」を要求)。
        /// 丈 1.000 のときの平面の実測 W(X) × D(Z) と姿:
        /// <list type="bullet">
        /// <item>0 … 0.263 × 0.839 <b>立石(板状に立つ)</b> — 三石の主石向き</item>
        /// <item>1 … 0.889 × 0.603 <b>立石(やや太い)</b> — 副石向き</item>
        /// <item>2 … 2.161 × 1.435 <b>臥石(低く広い)</b> — 添石・州浜の平石向き</item>
        /// <item>3 … 1.536 × 1.167 <b>塊石</b> — 護岸の役石・荒磯の立石向き</item>
        /// <item>4 … 1.174 × 1.363 <b>小塊</b> — 中島の汀石・岩島の肩石向き</item>
        /// </list>
        /// ⭕ **yaw を乱数で振る** — 5個体しかないので、向きを散らさないと同じ石が並ぶ。</para>
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- ishigumi</summary>
        public static string Ishigumi(int i) { return NiwaDir + "Ishigumi_" + i + ".fbx"; }

        /// <summary>**飛石・沢飛石1枚**(天端が平ら)。⭕ 同じ photoscanned rock の**頭を水平に
        /// 落として**天端を作り、縁は自然石のまま残してある(⛔ 切石に見せない)。
        ///
        /// <para><b>長軸をちょうど 1.000 に正規化してある。ピボット = 天端の芯</b>で、石は
        /// −Y へ垂れる。⇒ `localScale = Vector3.one * 長軸`、<b>`position.y = 天端の高さ`</b>を直に。
        /// 沢飛石は `sawatobi.topY`(水面 +0.12)、飛石は 地盤 +0.03〜0.05。</para>
        ///
        /// <para><paramref name="i"/> = 個体 0..2。長軸 1.000 のときの実測:
        /// <list type="bullet">
        /// <item>0 … 1.000 × 0.841、<b>厚 0.300</b>(Y −0.300..0) 飛石(薄手)</item>
        /// <item>1 … 0.862 × 1.000、<b>厚 0.360</b>(Y −0.360..0) 飛石(厚手)</item>
        /// <item>2 … 0.889 × 1.000、<b>厚 0.950</b>(Y −0.950..0) <b>沢飛石</b></item>
        /// </list>
        /// ⚠ **沢飛石(くびれ)には 2 を使う。**0/1 は厚 0.30〜0.36 しかないので、
        /// 水深 0.45(`migiwa.shallow`)の池床に届かず**水中に浮く**。2 は長軸 0.62 のとき
        /// 厚 0.59 になり、天端 24.12 − 0.59 = 23.53 ≒ 池床 23.55 に据わる。
        /// ⛔ 陸の飛石に 2 を使うと厚みぶんの土工が要る(埋めれば見えないので実害は無い)。</para>
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- tobiishi</summary>
        public static string Tobiishi(int i) { return NiwaDir + "Tobiishi_" + i + ".fbx"; }

        /// <summary>**沓脱石**(根府川石)。天端を平らに落とした自然石。
        /// <b>実寸 1.200(X) × 0.500(Y) × 0.750(Z)、ピボット = 天端の芯</b>で石は Y −0.500..0
        /// (露出 0.35 + 根 0.15)。⇒ <b>`position.y = 天端の高さ`</b>を直に入れる。
        /// ⚠ 指図は長局 0.9×0.6 / 見晴らし 1.0×0.7 も要求する。⭕ **一様スケール `L/1.2`** で当てる
        /// (0.9 → 0.675 幅 / 1.0 → 0.625 幅。指図の 0.6 / 0.7 と 0.05〜0.08 差)。
        /// ⛔ X と Z を別々に伸ばすと石肌が方向でつぶれる。
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- kutsunugi</summary>
        public const string Kutsunugi = NiwaDir + "Kutsunugi.fbx";

        /// <summary>**立石(縦長の庭石)3種**。松江松平上屋敷の庭(`tenkei[].stones[]` の
        /// 主石・副石・鏡石、`sensui.iwaya` の鏡石ほか)向け。ユーザー裁定3=A(2026-09-06)。
        /// ⛔ **在庫の岩は使わない** — `JG.Rock01..03`(FreeJapaneseGarden)は実見すると
        /// 全部が丈&lt;幅の扁平な転石で、立石(丈&gt;幅)に使える個体が無い。⭕ Blender の bmesh で
        /// 手続き生成した(円柱・直方体の押し出しではなく、前面だけ真っ平らな「見付」を持ち
        /// 残りは不等な円弧で割れ肌を持つ多角柱)。
        ///
        /// <para>実寸(Unity座標・スケール1で): W(X)×H(Y)×D(Z)。ピボット = **底面中央**。
        /// <list type="bullet">
        /// <item><b>S</b> … 0.600 × 1.000 × 0.450</item>
        /// <item><b>M</b> … 0.700 × 1.400 × 0.500</item>
        /// <item><b>L</b> … 0.800 × 2.100 × 0.600(岩屋の鏡石・主石組の主石向け)</item>
        /// </list>
        /// 各サイズ3個体(<paramref name="variant"/> = 1..3)。⛔ **1個体で並べない**
        /// (庭方の設計は「不等辺」を要求する — 同じ石を並べると三石・五石の意匠が壊れる)。
        /// 石は据える側で 1/3 埋める前提の**全丈**なので、地盤より下へ沈める場合は
        /// <c>position.y = 地盤 − H/3</c> のように呼び出し側で埋め代を引くこと(石自体は削らない)。</para>
        ///
        /// <para>材質: ⛔⛔ **依頼(JG_Rock_A_01 の材質名を保つ)はそのまま実装していない。**
        /// `JG_Rock_A_01_LOD0.fbx` の材質名は Blender から見て `Test` で、この名前の .mat は
        /// プロジェクトに存在せず remap が当たらない(2026-09-04 に岡部庭の景石で踏まれた地雷と
        /// 同じ — `Ishigumi`/`Tobiishi`/`Kutsunugi` のコメント参照)。⭕ 代わりに**同じ岩石景の
        /// 部材が既に使っている** `M_photoscanned_rocks_01`(NatureManufacture・写真計測の実肌)を
        /// そのまま運んだ。新規マテリアルは作っていない。UV は同じアトラスの1枚岩ぶんの矩形を
        /// 密度そのまま(0.30 uv/m)で使うので、丈2.1mでも引き伸ばされない。</para>
        ///
        /// <para>LOD1 を同梱(Decimate 40%・約500三角)。Unity 側は `Tateishi_&lt;size&gt;_&lt;variant&gt;_LOD0`/`_LOD1`
        /// の命名から自動で LODGroup を作る(README の命名規則どおり。ただしこのビルドで
        /// 初めて使うので、Unity 取り込み後に LODGroup が実際に立つか確認すること)。</para>
        /// 生成: blender --background --python Tools/Blender/build_tateishi.py -- all --render</summary>
        public static string Tateishi(string size, int variant)
        { return NiwaDir + "Tateishi_" + size + "_" + variant + ".fbx"; }

        /// <summary>**四つ目垣 1スパン(1間)**。親柱1 + 立子5 + 胴縁(h1.2 で4段 / h0.9 で3段)+
        /// 棕櫚縄の結び。⭕ 竹の断面・アトラスの帯・**結びの実体**は在庫の
        /// `Japanese Village Kit/Meshes/Fences/Bamboo garden fence`(本物の四つ目垣)から借りた。
        /// ⛔ <see cref="Eg.TakeGaki"/> は**菱格子**で四つ目ではない(2026-09-04 に実見)。
        ///
        /// <para>ローカル: 幅=X(走り)/ 高さ=Y / 厚み=Z。**+Z = 見え面**(胴縁と結びがこちら)。
        /// ピボット = **スパンの中心・地盤レベル**。親柱は **−X 端**(外面が x = −0.909)で
        /// **bbox がちょうど1間**。⇒ **1.818 ちょうどのピッチで突き付ける**(⛔ 重ねない)。
        /// ⛔ run の +X 端には <see cref="YotsumeGakiPost"/> を1本足す(足さないと胴縁が宙で終わる)。
        /// ⛔ **`SeatBottom` で据えない** — 根入れ 0.150 が Y&lt;0 に出ているので 0.15 浮く。
        /// `position.y = 地盤` を直に入れる。</para>
        ///
        /// <para><paramref name="h"/> = 1.2(井戸囲い `mizu.gensen.idoKaki` / 帯の井戸)/
        /// 0.9(稲荷の垣 `yashiro.kaki`)/ <b>0.6</b>(**視軸の区間** `nishi.mado.railH`・
        /// 法肩の u−0.92〜2.92。竹垣 h0.9 は床几の視線を切る(余裕 −0.08m)ので、
        /// その区間だけ落とす — 2026-09-03 庭方 K210)。実寸:
        /// h1.2 → 1.818 × <b>1.350</b> × 0.087(Y −0.150..1.200・胴縁4段)/
        /// h0.9 → 1.818 × <b>1.050</b> × 0.087(Y −0.150..0.900・胴縁3段)/
        /// h0.6 → 1.818 × <b>0.750</b> × 0.087(Y −0.150..0.600・<b>胴縁2段</b>)。
        /// ⚠ **段数は丈で変える** — h0.6 で3段にすると芯々 0.18 で詰まり、
        /// 建仁寺垣のように塞がって見えて**窓の足元が抜けない**。</para>
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- yotsume</summary>
        public static string YotsumeGaki(float h)
        { return NiwaDir + "YotsumeGaki_" + h.ToString("0.0") + ".fbx"; }

        /// <summary>四つ目垣の run の **+X 端に足す親柱1本**。⛔ 足さないと最後の胴縁が宙で終わる。
        /// ピボット = **run の終端(柱の +X 面)・地盤レベル** ⇒ `s = s1` をそのまま渡せる。
        /// 実寸 0.064 × (h + 0.150) × 0.064。⛔ `SeatBottom` で据えない(根入れ 0.150)。</summary>
        public static string YotsumeGakiPost(float h)
        { return NiwaDir + "YotsumeGakiPost_" + h.ToString("0.0") + ".fbx"; }

        /// <summary>**建仁寺垣 1スパン(1間)**。親柱1 + 胴縁3(裏)+ **割竹の立子35枚を隙間なく** +
        /// 押縁3段 + 玉縁 + 結び12。⛔ **立子に目地を空けていない**(芯々 = 見付 0.052)—
        /// 7mm でも空けると向こうが透けて、目隠しの垣という前提が崩れる(汀の木柵で実見した型)。
        /// ⭕ 割竹の丸みは**見え面(+Z)側**へ向けてある(背の弦を表に出すと横縞の平板に見える)。
        /// ⭕ 節の高さは立子ごとに位相をずらしてある(揃えると垣の中ほどに横一文字の帯が出る)。
        ///
        /// <para>ローカル: 幅=X / 高さ=Y / 厚み=Z。**+Z = 見え面**(押縁と結びがこちら)。
        /// ピボット = **スパンの中心・地盤レベル**。親柱は **−X 端**で **bbox がちょうど1間**。
        /// ⇒ 1.818 ちょうどのピッチで突き付ける。⛔ +X 端に <see cref="KenninjiGakiPost"/> を足す。
        /// ⛔ `SeatBottom` で据えない(根入れ 0.150)。</para>
        ///
        /// <para><paramref name="h"/> = 1.5(かわや `K_Obi` の西面の目隠し。`obi` の 2間)。
        /// 実寸 1.818 × <b>1.686</b> × 0.106(Y −0.150..1.536)。
        /// ⚠ **高さ 1.686 は玉縁(天端の笠竹)の分**で、垣そのものの丈は 1.500。
        /// 遮蔽の計算は 1.5 でなく **1.536(玉縁の天端)**で立つ。</para>
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- kenninji</summary>
        public static string KenninjiGaki(float h)
        { return NiwaDir + "KenninjiGaki_" + h.ToString("0.0") + ".fbx"; }

        /// <summary>建仁寺垣の run の **+X 端に足す親柱1本**。ピボット = run の終端・地盤レベル。
        /// 実寸 0.064 × (h + 0.150) × 0.064。</summary>
        public static string KenninjiGakiPost(float h)
        { return NiwaDir + "KenninjiGakiPost_" + h.ToString("0.0") + ".fbx"; }

        /// <summary>**乱杭1本**(汀を留める細い杭。`gardens[].rangui`)。
        /// ⭕ 在庫の**細丸太**(NatureManufacture `wood_log_06/08/09`・径 0.062〜0.069)を
        /// **半径方向だけ**縮めて切り出した。⛔ 太丸太(`wood_log_01/02/04`・径 0.12)から
        /// 絞ると樹皮の刻みが実寸で 1/3 になり「つるつるの棒」になる。
        ///
        /// <para><paramref name="dia"/> = 0.034 / 0.043 / 0.052 の3種(指図 `rMin`..`rMax`)。
        /// ⛔ **1種で並べない・芯々を等間隔にしない**(指図は芯々 0.125 の**密度**であって
        /// 等間隔の指定ではない)。
        /// ピボット = **頭の芯**で杭は −Y へ **0.660** 垂れる。⇒ `position.y = topY`
        /// (`rangui.topY` 23.67 = 水面 −0.33)を直に入れる。
        /// 傾 4°(`rangui.tilt`)は **+X 方向へ焼き込んである**ので、**yaw を乱数で振れば
        /// 傾きの方位が散る**。実寸(0.043)0.089 × 0.660 × 0.042。</para>
        /// ⚠ 全長 0.660 は**指図に無い値**(確度 U)。細丸太の実長が 0.718m しか無いのが上限。
        /// 生成: blender --background --python Tools/Blender/build_okabe_niwa.py -- rangui</summary>
        public static string Rangui(float dia)
        { return NiwaDir + "Rangui_" + dia.ToString("0.000") + ".fbx"; }

        /// <summary>**雪見灯籠**。⚠ 実体は在庫の <see cref="Eg.ToroYukimi"/>(edogoyomi)で、
        /// これはそこへの転送(⛔ パスの literal を二重に書かないため)。棟梁が `Own.` の下で
        /// 探すので入口だけ用意してある。⛔ **`ES = 1.818` を掛けて置く**(素だと 0.5m の模型)。
        /// ⛔ 春日型を置かない。⛔ 自作の <see cref="YukimiLantern"/> は使わない(材質がべた塗り)。</summary>
        public const string Toro = Eg.ToroYukimi;

        /// <summary>地表層(TerrainLayer)。**「実寸」= 繰り返しの一枚の大きさ `m_TileSize`**[m]。
        /// ⚠ タイリングが小さいほど近景は細かく、遠景は模様が目立つ。塗り分けるときは
        ///   隣り合う層のタイルの大きさを見て、境目で柄が急に変わらないようにする。
        /// ⛔ ここに無い層を勝手に足さない — 地表の設計は指図(どの層で塗るか)が持つ。</summary>
        public const string LayerGrass  = "Assets/Edo/Terrain/layers/L_grass.terrainlayer";  // 芝・草地。タイル 4×4m
        /// <summary>土(踏み固めた道・白洲・前庭)。タイル 8×8m</summary>
        public const string LayerDirt   = "Assets/Edo/Terrain/layers/L_dirt.terrainlayer";
        /// <summary>裸地(切土の肌・法面)。タイル 11×11m</summary>
        public const string LayerBare   = "Assets/Edo/Terrain/layers/L_bare.terrainlayer";
        /// <summary>岩(崖・露岩)。タイル 7×7m。⚠ 4層のうちこれだけ `Smoothness` 0.15(濡れて見える)</summary>
        public const string LayerRock   = "Assets/Edo/Terrain/layers/L_rock.terrainlayer";

        /// <summary>詳細植生(Detail)の下草。**丈は 0.11m** — 地表の毛羽で、草叢ではない。
        /// 実寸[m]は目録の実測値(幅 × **丈** × 奥行):A 0.45 × <b>0.11</b> × 0.40 / B 0.33 × <b>0.11</b> × 0.20。
        /// ⚠ `pivot_bottom` = −0.02 なので、地盤の y をそのまま渡すと 2cm 沈む(下草なので実害は無い)。
        /// ⚠ Terrain の Detail として使う版は同じフォルダの `GrassLowA_up.asset` / `GrassLowB_up.asset`。
        /// ⛔ **同じフォルダの `BroadleafTree` は使用禁止のまま**(CLAUDE.md 規則10 —
        ///   「これは2度と使わないでください。見た目がしょぼすぎます」2026-08-30 ユーザー指示)。</summary>
        public const string GrassLowA   = "Assets/Edo/Terrain/details/GrassLowA.prefab";
        public const string GrassLowB   = "Assets/Edo/Terrain/details/GrassLowB.prefab";
    }
}
