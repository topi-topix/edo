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
        public const string FloorBoard  = P + "Goten_FloorBoard_1ken.fbx"; // 入側の板敷き(厚0.0636・ピボット z=0 は**底**)

        /// <summary>**渡廊下の縁板** 一間角(厚 **1寸 0.0303**)。⛔ <see cref="FloorBoard"/> の置き換えではない
        /// (あちらは入側の板敷きで、他邸が使っている)。
        ///
        /// <para>【なぜ別に要るか】廊下の床は落縁(=濡縁)の天端に継ぐので、**縁の下**(縁板の下端〜地盤)は
        /// 指図 `roka.ennoshitaMin` **0.303** を満たさねばならない。床の面は
        /// `const.gotenFloor` 0.62 − <c>EdoGotenKit.NUREEN_DROP</c> 0.28 = **0.34** なので
        /// **板厚は 0.037 以下**。キットの板(0.0636)では縁の下 0.276 で **27mm 割る**
        /// (2026-09-20 部材方の実測 → 普請奉行の発注)。1寸なら縁の下 **0.3097**。</para>
        ///
        /// <para>⚠⚠ **ピボットの z=0 は「板の天端」**(⛔ <see cref="FloorBoard"/> は z=0 が**底**)。
        /// 廊下の床は面で落縁へ継ぐので、<c>new Vector3(x, floor, z)</c> へ置けば天端が床に揃い、
        /// 厚は下へ逃げる。⛔ 板厚を足さない・引かない。平面のピボットは一間角の中心。</para>
        ///
        /// <para>⭕ 形は**キットの床板を薄くしただけ**(材質名 `floor` と板目を保つ)。走り方向の
        /// 倍率(<c>EdoGotenKit.Roka</c> の端数の駒)もそのまま効く。
        /// 松江松平の渡廊下6本で **20枚**(4+6+4+2+2+2)。</para>
        /// 生成: GOTEN_ONLY=RokaEnita blender --background --python Tools/Blender/build_goten_parts.py</summary>
        public const string RokaEnita   = P + "Goten_RokaEnita_1ken.fbx";
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

        /// <summary>棟の外形(身舎+入側)の間数で引く**寄棟**。<paramref name="wKen"/>=桁行。
        /// ⛔ **御殿の棟には使わない** — 入母屋より一段格が下で、**役所・附属の棟**に充てる
        /// (土井の表役所 = 2026-09-06 ユーザー裁定)。
        ///
        /// <para>⚠⚠ **正方形の平面では必ず方形造(宝形)になる。** 四面の勾配が等しい限り
        /// **大棟の長さ = 桁行 − 梁間** なので、正方形では 0 になり隅棟4本が一点で交わる
        /// 四角錐にしかならない(生成器は大棟 0.35m 以下で**露盤**を載せて頂点を塞ぐ)。
        /// 「大棟のある寄棟」が要るなら**平面を長方形にする**しかない = **設計側の裁定事項**
        /// (土井の表役所 10×10間は 2026-09-06 ユーザー裁定=方形造のままでよい)。</para>
        ///
        /// <para>⛔ **入母屋の妻を潰した物で代用しない** — 妻壁・破風・木連格子・懸魚・袖瓦は
        /// そもそも作らないのが寄棟で、潰すと使われない頂点と z-fighting する板が残る。
        /// ⚠ 入母屋と同じく**外形は間数より 2.14m 大きい**(軒の出 0.90 が四周に付く)。
        /// 焼いてあるもの: **10x10ken(実寸 20.32 × 5.89 × 20.32)**。</para>
        /// 無い寸法は:
        ///   blender --background --python Tools/Blender/build_goten_roof.py -- yosemune &lt;桁行m&gt; &lt;梁間m&gt; Goten_Roof_Yosemune_&lt;w&gt;x&lt;d&gt;ken</summary>
        public static string RoofYosemune_(int wKen, int dKen)
        {
            return RoofDir + "Goten_Roof_Yosemune_" + wKen + "x" + dKen + "ken.fbx";
        }

        /// <summary>**帯割りの入母屋**。身舎を帯(2〜5間)に割り、帯ごとに入母屋を架けて
        /// 境を**水平の谷**にした屋根。梁間が10間を超えて**一枚の小屋組で飛ばせない**棟に使う
        /// (2026-09-06 ユーザー裁定=案C)。外周1間の入側は**身舎の屋根がそのまま延びた一枚の流れ**で
        /// 覆う — ⛔ 段のある「下屋」ではない(同日、語ごと撤回)。立面で入側と身舎の境は見えない。
        ///
        /// <para>⛔⛔ **z=0 は「床」。<see cref="RoofIrimoya_"/> / <see cref="RoofYosemune_"/> と違う。**
        /// あちらは z=0 が**軒先**で <c>EdoGotenKit</c> が <c>floor + H − 0.15f</c> へ据えるが、
        /// これは <c>new Vector3(cx, floor, cz)</c> に**そのまま置く**。
        /// ⛔ <c>gotenFloor</c> を足さない・軒先高を足さない — **足すと 3.4m 浮く**。
        /// <c>floor</c>(= FBX の z=0 を置く Unity Y)= **郭の面 + <c>gotenFloor</c>(0.62)**。</para>
        ///
        /// <para>⚠ **向きは「モデル局所 +X = 江戸間格子の +u」。**大棟が u に架かる棟は
        /// <paramref name="alongV"/>=false、v に架かる棟は **true(`_v` の別体を焼いてある)**。
        /// ⇒ 棟梁が振るのは**江戸間格子の yaw だけ**。⛔ **90° を足さない**(2026-09-06 部材方の判断)。</para>
        ///
        /// <para>⭐⭐ **<paramref name="bands"/> の先頭 = across 軸(帯の並ぶ向き)の小さい側。**
        /// <paramref name="alongV"/> が true でも false でも変わらない。across は along の直交軸なので、
        /// **`alongV`=false(大棟が u)なら across は v / `alongV`=true(大棟が v)なら across は u**。
        /// ⇒ **指図の `ws` をそのまま渡してよい。**
        /// ⭕ 奥棟の実測(FBX から): 4間帯の大棟が **u=4.00**、5間帯が **u=8.51**、谷が **u=5.98**。
        /// 指図(`ws=[4,5]` / `at=[4, 8.5]` / 谷 u=6・身舎 u 2〜11)と一致。
        /// ⚠ **これは棟梁が yaw −20.604° を振ったあとでは読み取れない情報**なので、
        /// 「どちらの端が先頭か」は必ずここを見ること。
        /// ⚠ 生成器の中身は逆(帯を +Y に並べ v なら +90° 回すので並びが裏返る)だが、
        /// **2026-09-06 に `make_banded` が受け取った時点で反転して打ち消す**ようにした。
        /// ⛔ それ以前に焼いた `5-4x10ken_v` は**同じ幾何の別名**。消してあるので使わない。</para>
        ///
        /// <para>高さは**すべて床上**(⛔ 地盤上と取り違えない): 軒高 3.400 /
        /// 入側外の柱通り 2.408 / **軒先の先端 1.917** / 大棟の天端(座とも) 4間帯 6.066・5間帯 6.562。
        /// 棟高(座を除く)は 4間帯 **5.384**・5間帯 **5.880**。足形は身舎の各辺に **+2.718**
        /// (入側1間 1.818 + 軒の出 0.90)が四周に付く。
        /// ⚠ 棟ごとの**世界座標(郭の面・床Y・足形の中心・棟高の絶対値)は
        /// `docs/Sashizu/doi_sashizu.json` が正典**。CLAUDE.md 規則4によりここへは写さない。</para>
        ///
        /// <para>⚠⚠ **H はピボット(=床・z=0)から天端まで**であって、**メッシュの丈ではない**。
        /// 一番低い点(軒先の先端)が床から **1.790** 上にあるので、**bbox の丈は 4.275(4間帯)/
        /// 4.771(5間帯)**しかない。⛔ bbox の丈から棟高を出さない・接地の判定に使わない。</para>
        ///
        /// <para>焼いてあるもの(W(X) × H(Y) × D(Z)・Unity 座標・素通し検査すべて 0px。
        /// 谷の位置はモデル局所・ピボット基準):
        /// <list type="bullet">
        /// <item>{4,4} x8  u  … 表役所・玄関 — 20.323 × 6.066 × 20.323(谷1本 y=0)</item>
        /// <item>{4}   x12 v  … 書院       — 13.051 × 6.066 × 27.595(谷なし)</item>
        /// <item>{5,5} x14 u  … 居間       — 31.231 × 6.562 × 23.959(谷1本 y=0)</item>
        /// <item>{4,5} x10 v  … 奥         — 22.141 × 6.562 × 23.959(谷1本 x=−0.909)</item>
        /// <item>{4,4} x10 v  … 台所       — 20.323 × 6.066 × 23.959(谷1本 x=0)</item>
        /// </list></para>
        ///
        /// <para>**松江松平(2026-09-08・第28次の帯割りの引き直しで新造)**。
        /// ⭐ **帯数の上限を 3 → 4 へ広げた**(生成器の歯止めだけの変更。幾何は N 一般だった)。
        /// ⛔ 5帯へは広げない — 谷4本の小屋組は説明が付かない。
        /// <list type="bullet">
        /// <item>{3,3,4,4} x12 v … 表役所 — 31.231 × 6.066 × 27.595(谷3本 x=−7.272/−1.818/+5.454)</item>
        /// <item>{4,4,4}   x10 v … 黒書院・玄関 — 27.595 × 6.066 × 23.959(谷2本 x=∓3.636)</item>
        /// <item>{4,5,5}   x12 v … 大広間 — 31.231 × **6.562** × 27.595(谷2本 x=−5.454/+3.636)</item>
        /// <item>{3,3,4,4} x16 u … 大台所 — 34.867 × 6.066 × 31.231(谷3本 z=+7.272/+1.818/−5.454)</item>
        /// </list>
        /// ⚠⚠ **帯の並ぶ向き(across)は `along` で符号が違う。** `bands[0]` が来るのは
        /// **v のとき局所 +X の小さい側 / u のとき局所 +Z の<b>大きい</b>側**
        /// (格子 v = −(局所 Z) の帰結)。⛔ 「どちらも +X/+Z の小さい側」と読まない —
        /// 2026-09-08 に部材方が検算をこの符号で書き誤り、正しい部材を不良と判定しかけた。
        /// ⭕ 実測で確かめる術: 帯の芯(across)で切って**頂の高さ**を測る。
        /// 幅の広い帯ほど棟が高いので、並びが入れ替われば必ず高さが食い違う
        /// (⛔ 高さで頂点を拾って across を見る作りにしない — 広い帯の斜面が狭い帯の棟高を通る)。</para>
        ///
        /// <para>⛔ <c>fukizai</c> は桟瓦のみ(本瓦は生成器が例外で止まる)。
        /// 入側1 / 軒の出0.90 / 勾配0.5456 / 妻の出0.30 / gable_frac 0.45 は**部材の既定値**で摘みにしない。
        /// 無い寸法は:
        ///   blender --background --python Tools/Blender/build_goten_roof.py -- banded &lt;帯 4,5&gt; &lt;桁行間数&gt; [--along u|v]</para></summary>
        /// <param name="irikawa">⭐⭐ **入側の間数を郭グリッドの軸ごとに** <c>{u0, u1, v0, v1}</c>
        /// (指図 <c>munes[].roof.irikawa</c> の <c>u:[u0,u1] / v:[v0,v1]</c> をこの順に並べたもの)。
        /// <c>null</c> = 四周1間(旧来の既定。土井の帯割り屋根はすべてこれ)。
        ///
        /// <para>⛔⛔ **2026-09-09 の差し戻し1。**それまで生成器は入側スカラ1つを四周へ当てていたので、
        /// <c>irikawa</c> が [1,1] でない軸の屋根が **1間ずつ過大**に焼けていた。松江松平の表向4棟は
        /// 隣どうし 3.18間(5.78m)重なり、真上から見ると4棟が1枚の巨大な屋根に融けていた。
        /// ⇒ **総寸 = 身舎 + 入側(辺ごと) + 軒**。⛔ 横に縮める対処は採らない(瓦の目と破風が潰れる)。</para>
        ///
        /// <para>⭐ **入側が四周1間でないときだけ名前に <c>_i&lt;u0&gt;&lt;u1&gt;&lt;v0&gt;&lt;v1&gt;</c> が付く**
        /// (例 `Goten_Roof_Banded_3-3-4-4x12ken_v_i0011`)。⛔ 入側を名前に入れずに焼くと、
        /// **同じ名前で幾何の違う屋根**が静かに上書きし合う(松江松平の表向 u=[0,0] と
        /// 土井の四周1間はどちらも `4-4-4x10ken_v` になる)。</para></param>
        /// <param name="noki">⭐⭐ **辺ごとに軒を出すか**を郭グリッドの軸ごとに <c>{u0, u1, v0, v1}</c>
        /// (**1 = 出す / 0 = 落とす**)。<c>null</c> = 四周出す(既定)。
        ///
        /// <para>⛔⛔ **2026-09-10 の差し戻し1。**棟の外形が**隣の棟と接している**辺
        /// (<c>munes[].u1</c> = 次の棟の <c>u0</c>)へ軒 0.90m を出すと、隣どうしの軒が
        /// **1.80m 食い込む**。普請検査の寄りのレンダでは「二つの軒先の間から空が透ける /
        /// 桟瓦の列が空中で途切れる / 軒先が何にも載らず宙に浮く / 目の高さで軒線が X 字に交差」
        /// という姿になっていた。⭕ **接する辺の軒を落とす**と屋根の面が棟の外形の線で終わり、
        /// 隣の棟が出す**半分の谷樋**と合わさって**一本の谷**になる。
        /// ⛔ 身舎・入側は 1mm も動かない ⇒ **ピボットも棟の外形も不動**。</para>
        ///
        /// <para>⛔ **妻側(大棟の両端 = <c>alongV</c> の軸の辺)は落とせない** — 破風・懸魚・
        /// 妻壁が付く辺で、軒だけ落とすと板が宙に浮く。生成器が例外で止まる。</para>
        ///
        /// <para>⭐ 落とした辺があるときだけ名前に <c>_n&lt;u0&gt;&lt;u1&gt;&lt;v0&gt;&lt;v1&gt;</c> が付く。
        /// ⛔ 入れずに焼くと <c>_i</c> と同じ事故が起きる — 松江松平の黒書院(両隣が接する)と
        /// 玄関(片側だけ接する)はどちらも `4-4-4x10ken_v_i0011` になり静かに上書きし合う。</para></param>
        public static string RoofBanded(int[] bands, int spanKen, bool alongV = false,
                                        int[] irikawa = null, int[] noki = null)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            string b = "";
            for (int i = 0; i < bands.Length; i++)
                b += (i > 0 ? "-" : "") + bands[i].ToString(inv);
            string suf = "";
            if (irikawa != null && irikawa.Length == 4
                && !(irikawa[0] == 1 && irikawa[1] == 1 && irikawa[2] == 1 && irikawa[3] == 1))
                suf = "_i" + irikawa[0].ToString(inv) + irikawa[1].ToString(inv)
                            + irikawa[2].ToString(inv) + irikawa[3].ToString(inv);
            if (noki != null && noki.Length == 4
                && !(noki[0] == 1 && noki[1] == 1 && noki[2] == 1 && noki[3] == 1))
                suf += "_n" + noki[0].ToString(inv) + noki[1].ToString(inv)
                            + noki[2].ToString(inv) + noki[3].ToString(inv);
            return RoofDir + "Goten_Roof_Banded_" + b + "x" + spanKen.ToString(inv)
                 + "ken" + (alongV ? "_v" : "") + suf + ".fbx";
        }

        // ⭐ **`noki` の 0/1 は人が数えて書き写さない。**指図の棟の外形どうしを総当たりで
        //   突き合わせて出すこと(判定 = 外形の線を共有し、直交方向の重なりが正)。
        //   ⚠ 隣が**この生成器の屋根を持たない棟**(`roof` が空)のときは落とさない —
        //     相手の屋根の形が分からないまま落とすと壁の上が素通しになる。
        //   松江松平の実装は `Tools/Blender/build_matsudaira_dewa_roofs.py` の `_touching()`。
        //   焼き直し: blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- --render

        /// <summary>渡廊下の切妻屋根。幅1間・長さ<see cref="RoofKirizumaKen"/>間の定尺で作ってある
        /// (瓦の繰り返し 1.785/2.004m は江戸間と割り切れないので1間モジュールにはできない)。
        /// 無い長さが要るときは build_goten_roof.py -- kirizuma &lt;間数&gt; で足す。
        /// ピボット = 廊下の中心・軒先レベル。大棟の天端は軒先から 0.953。
        ///
        /// <para>⚠⚠ **間数は整数とはかぎらない。** 土井の `L_ImaDaidokoro` は **1.5間**で、
        /// 整数へ丸めて 2間で据えると居間棟へ **0.909m 食い込む**(2026-09-06)。
        /// ⇒ 引数は `float` で、名前は Python の `("%g")` と同じく**末尾の 0 を落とす**
        /// (1.5 → `1.5ken` / 2 → `2ken`)。⛔ `ToString("0.#")` はロケールで小数点が
        /// 変わるので使わない(InvariantCulture で書く)。</para></summary>
        public static readonly float[] RoofKirizumaKen = { 1f, 1.5f, 2f, 3f, 4f, 5f, 6f, 7f, 8f, 9f, 10f, 12f };
        public static string RoofKirizuma(float nKen)
        {
            return RoofDir + "Goten_Roof_Kirizuma_" + KenTag(nKen) + "ken.fbx";
        }
        /// <summary>間数をファイル名の綴りへ。整数はそのまま、端数は小数第2位まで(末尾の0を落とす)。</summary>
        public static string KenTag(float nKen)
        {
            long h = (long)System.Math.Floor((double)nKen * 100.0 + 0.5);
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            string t = (h / 100L).ToString(inv);
            long f = h % 100L;
            if (f != 0L) t += "." + (f % 10L == 0L ? (f / 10L).ToString(inv) : f.ToString("00", inv));
            return t;
        }

        /// <summary>**平入り + 庇**の屋根(身舎に切妻を架け、その外を庇一間が回る)。
        /// 松江松平邸の**奥向の棟4棟と厩**(指図 `const.nagayaGataRoof`)のための型で、
        /// 梁間の外形が帯割り(4/5 の和)で作れない棟に使う。
        ///
        /// <para>⭐⭐ **z=0 は「床」**(<see cref="RoofBanded"/> と同じ。⛔ <see cref="RoofIrimoya_"/> の
        /// 軒先ではない)。棟梁は <c>new Vector3(cx, floor, cz)</c> へ**そのまま置く**
        /// (<c>EdoGotenKit.Mune</c> なら <c>roofAtFloor: true</c> / <c>roofEaveLocalY: NaN</c>)。
        /// 平面のピボットは**足形(庇を含む外形)の中心**、向きは**モデル局所 +X = 江戸間格子の +u**。</para>
        ///
        /// <para>⚠ <paramref name="eaveAboveFloor"/> は**床上の身舎の軒桁**[m]。指図
        /// (`const.nagayaGataEave` / `const.umayaEave`)は**地盤基準**なので
        /// <c>− const.gotenFloor</c> してから渡す(焼いてあるのは 2.744 と 2.410)。</para>
        ///
        /// <para>⚠ **bbox は呼び寸より大きい。** 外形 = 間数×1.818 + 軒の出 0.90×2 だが、
        /// **隅棟の角が更に片側 0.14 飛び出す**(入母屋の 0.171 と同じ性質)。
        /// ⛔ 離れを bbox で測ると偽陽性が出る。高さも同じで、**bbox の丈 4.120 は
        /// ピボットからの高さではない**(部材は z 1.399..5.519 = 軒先より下に破風が垂れる)。</para>
        ///
        /// <para><paramref name="omit"/> = 庇を回さない辺(格子の綴り "u0","u1","v0","v1" を
        /// 並べた物。指図 `munes[].hisashiOmit` をそのまま。⛔ 人が辺を数えない)。</para>
        ///
        /// <para>⭐⭐ <paramref name="notches"/> = **渡廊下が取り付く辺の切り欠き**(辺, 中心の間数)。
        /// 指図の取り合い(`_roka` ④「廊下の**桁の下端** ↔ **庇の軒桁の天端**」)を成り立たせるため、
        /// その1間だけ庇の軒先を切り詰め、底に**軒桁の天端の水平な受け面**を出してある。
        /// ⛔ 軒先の下へ潜らせる納めは指図が採らない(`_roka` ③)。⛔ 切り欠き無しの版を
        /// 渡廊下の取り付く棟へ据えない — 柱筋の頭上が `roka.zujoMin` を 65mm 割る(2026-09-20 実測)。
        /// ⇒ <see cref="HirairiNotches"/> が `munes[]`/`links[]` から機械的に解く。
        /// 中心は **u の辺は棟の v0 から / v の辺は棟の u0 から**の間数。</para>
        ///
        /// <para>⭕ **受け面(庇の軒桁の天端)の実測 = ピボットから z +1.9259**(軒桁 2.744 の4棟)
        /// / **+1.5919**(厩 2.410)。棟梁はここへ廊下の桁を掛ける。切り欠きは**幅1間・奥行 0.90**
        /// (軒の出ぶん)で、両脇と奥は板で塞いである。
        /// ⛔⛔ **当たりは「最も低い交点」** — 受け面の下に**受け板の下端**がもう一枚あり、
        /// 実機はそちらを拾う。⇒ 板は **3分(0.0091)** まで薄くしてある
        /// (書き出した FBX の実測 = 受け面 **1.9259** / 板の下端 **1.9168**)。
        /// これで柱筋の頭上 **1.7332 ≥ `roka.zujoMin` 1.727**(余裕 6mm)。
        /// ⛔ この板を厚くしない — 厚みがそのまま頭上の余裕を食う(0.08 で 65mm 割った)。</para>
        ///
        /// <para>焼いてあるもの — 切り欠き**あり**(この邸の取り付き6か所):
        /// 6x6 ku1-2.5 / 18x6 ku0-2.5 ku1-2.5 kv1-4.5 / 10x6 ku0-2.5 / 22x5 ov1 kv0-10.5(e2744)。
        /// 切り欠き**なし**(取り付かない辺・他邸用): 6x6 / 18x6 / 10x6 / 22x5 ov1(e2744)、
        /// 14x5 ov1(e2410・厩は渡廊下が無い)。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- --hirairi --render
        /// (切り欠き無しは同 `-- --hirairi --plain` / 単発は
        ///  build_goten_roof.py -- hirairi &lt;桁行間&gt; &lt;梁間間&gt; &lt;軒桁m&gt; [--omit v1] [--notch u1-2.5] [--render])</summary>
        public static string RoofHirairi(int wKen, int dKen, float eaveAboveFloor,
                                         string[] omit = null, string[] notchSide = null,
                                         float[] notchKen = null)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            string s = RoofDir + "Goten_Roof_Hirairi_" + wKen + "x" + dKen + "ken";
            var order = new[] { "u0", "u1", "v0", "v1" };
            string q = "";
            foreach (var side in order)
                if (omit != null && System.Array.IndexOf(omit, side) >= 0) q += side;
            if (q.Length > 0) s += "_o" + q;
            if (notchSide != null && notchSide.Length > 0)
            {
                var idx = new System.Collections.Generic.List<int>();
                for (int i = 0; i < notchSide.Length; i++) idx.Add(i);
                idx.Sort((a, b) =>
                {
                    int c = System.Array.IndexOf(order, notchSide[a])
                            .CompareTo(System.Array.IndexOf(order, notchSide[b]));
                    return c != 0 ? c : notchKen[a].CompareTo(notchKen[b]);
                });
                foreach (var i in idx) s += "_k" + notchSide[i] + "-" + KenTag(notchKen[i]);
            }
            // ⚠ mm は **四捨五入**(floor は浮動小数で 1mm 落ちる)。Python 側と同じ綴りにすること
            long mm = (long)System.Math.Floor((double)eaveAboveFloor * 1000.0 + 0.5);
            return s + "_e" + mm.ToString(inv) + ".fbx";
        }

        /// <summary>棟に取り付く渡廊下から、<see cref="RoofHirairi"/> へ渡す**切り欠き**
        /// (辺 <paramref name="side"/> と中心の間数 <paramref name="ken"/>)を解く。
        /// ⛔ 人が数えた数を書かない — 部材方 `build_matsudaira_dewa_roofs.notches_for` と同じ規則:
        /// **外形の線を共有し、直交方向の重なりが正**なら取り付き。
        /// ⭕ 中心は **u の辺は棟の v0 から / v の辺は棟の u0 から**の間数(棟の格子基準)。
        /// ⛔ 口(`kind` が「渡廊下」でないもの = 御錠口・御膳所口)は渡さない — 下屋を架けないので
        /// 軒先を切る理由が無い。
        ///
        /// <para>矩形はどれも <c>{u0, u1, v0, v1}</c> の 4 要素。⇒ 指図の `munes[]` / `links[]` を
        /// そのまま渡せる。</para></summary>
        public static void HirairiNotches(float[] mune,
                                          System.Collections.Generic.IEnumerable<float[]> rokaRects,
                                          out string[] side, out float[] ken)
        {
            var ss = new System.Collections.Generic.List<string>();
            var kk = new System.Collections.Generic.List<float>();
            foreach (var l in rokaRects)
            {
                double ovV = System.Math.Min(mune[3], l[3]) - System.Math.Max(mune[2], l[2]);
                double ovU = System.Math.Min(mune[1], l[1]) - System.Math.Max(mune[0], l[0]);
                if (ovV > 0.0)
                {
                    float cv = (l[2] + l[3]) / 2f - mune[2];
                    if (System.Math.Abs(mune[0] - l[1]) < 1e-4) { ss.Add("u0"); kk.Add(cv); }
                    if (System.Math.Abs(mune[1] - l[0]) < 1e-4) { ss.Add("u1"); kk.Add(cv); }
                }
                if (ovU > 0.0)
                {
                    float cu = (l[0] + l[1]) / 2f - mune[0];
                    if (System.Math.Abs(mune[2] - l[3]) < 1e-4) { ss.Add("v0"); kk.Add(cu); }
                    if (System.Math.Abs(mune[3] - l[2]) < 1e-4) { ss.Add("v1"); kk.Add(cu); }
                }
            }
            side = ss.ToArray(); ken = kk.ToArray();
        }

        /// <summary>**渡廊下の差し掛けの下屋(両流れ)**。主屋の軒下から葺き下ろす下屋で、
        /// 独立した大棟を持つ <see cref="RoofKirizuma"/> とは別物(松江松平 2026-09-17 ユーザー裁定A)。
        /// 幅 1間・勾配 `const.sashikakeKobai`(4寸)・軒の出 `const.nokiE`(0.90)。
        ///
        /// <para>⭐⭐ **z=0 は「頭」**(= 葺き下ろしの線 = 廊下の芯の屋根面の頂)。⛔ 床でも軒先でもない。
        /// 頭の高さは廊下ごとの従属値 = **その端の当たり − `roka.clear`** なので、棟梁が
        /// その値を Y に入れて据える(⛔ 部材は高さを持てない)。大棟の冠瓦はそこから 0.13 上へ出る。</para>
        ///
        /// <para>⚠ 両端は主屋の面へ **0.10 差し込んで**焼いてある ⇒ **bbox の桁行は呼び寸 + 0.20**
        /// (更に大棟の駒が両端で 0.07 ずつ出るので実測は +0.34)。⛔ bbox から桁行を読まない。
        /// 焼いてあるもの: **2 / 4 / 6間**(指図 `links` の渡廊下6本を覆う)。
        /// ⛔ 口(御錠口・御膳所口)には架けない。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- --geya --render
        /// (単発は build_goten_roof.py -- geya &lt;桁行間&gt; [--width &lt;間&gt;] [--kobai 0.4] [--render])</summary>
        public static string RoofRokaGeya(float nKen)
        {
            return RoofDir + "Goten_Roof_RokaGeya_" + KenTag(nKen) + "ken.fbx";
        }

        /// <summary>**段違いの下屋の折れ目を塞ぐ雨押え**(小壁 + 面戸の一体物)。
        /// 渡廊下が <c>links[].dan</c> で段を折ると、<see cref="RoofRokaGeya"/> はピボットが「頭」なので
        /// 上下の葺き面のあいだに口が開く(松江松平 2026-09-20 棟梁の実測 **0.19m**。許容0の隙)。
        ///
        /// <para>⛔⛔ **「口の丈ぶんの板を1枚立てる」では塞がらない。**口は板ではなく**管**で、
        /// ①走り方向(低い側の空 ↔ 高い屋根の裏)と ②**幅方向(廊下の一方の軒先 ↔ 反対の軒先)**の
        /// 両方に抜ける。⚠ ②が本体で、**廊下の横から覗くと 3.7m の隙間が素通し**になる。
        /// ⇒ この部材は口の断面を**埋める**。下端は瓦の谷より 0.01 下・上端は上の屋根の裏板より
        /// 0.01 上まで差し込んであり、瓦の山は部材の中に隠れる(実物の面戸と同じ納まり)。
        /// 生成器が下屋2本を実際に重ねて profile を光線で読み、**素通し 0/2502 を確かめてから**焼く。</para>
        ///
        /// <para>⭐ 幅 = X(**廊下の幅方向**)/ 高さ = Y / 厚み = Z、**+Z = 見え面 = 段の低い側**。
        /// ピボット = **廊下の芯・折れ目の線・低い区間の下屋の頭**
        /// (= 低い側の <see cref="RoofRokaGeya"/> を据えた Y と**同じ値**をそのまま入れる)。
        /// ⭕ 松江松平の3本は廊下が v 走り・段が u 線なので **<c>YawAlongU</c> でそのまま据わる**
        /// (局所 +X = 格子 +u = 廊下の幅 / 局所 +Z = 格子 −v = 低い側)。
        /// ⛔ **下屋の yaw をそのまま使わない** — 下屋は局所 +X が**走り**でこの部材とは 90° 違う。</para>
        ///
        /// <para>外形 W(X) **3.618** × H(Y) **1.042** × D(Z) **0.350**(幅 1間 + 軒の出 0.90×2)。
        /// <paramref name="danMm"/> = 上下の下屋の**頭の高さの差**[mm](⛔ 指図に無い従属値。棟梁が実測して渡す)。
        /// 焼いてあるもの: **260**。無い段は下のコマンドで足す。材 `wood` ⇒ `Edo/御殿/新しい御殿FBXのマテリアルをremap`。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- amaosae --dan 0.26 --render</summary>
        public static string Amaosae(int danMm)
        {
            return RoofDir + "Goten_Amaosae_1ken_d" + danMm + ".fbx";
        }

        /// <summary>**渡廊下の段を受ける框**(框 + 蹴込板 + 地覆)。
        /// ⛔ <see cref="JodanKamachi"/> は**段 0.15 固定**で、しかも上の床板(見込み 0.55)を
        /// 抱き込む形なので渡廊下には使えない(2026-09-20 棟梁が桁材を縮めて仮に充てていたのの置き換え)。
        ///
        /// <para>⭐ 幅 = X(1間)/ 高さ = Y / 見込み = Z、**+Z = 見え面 = 低い側**。
        /// ピボット = **幅の中心・低い側の床板の天端・框の見付面**(Z=0)。
        /// ⇒ 低い区間の <see cref="RokaEnita"/> と**同じ Y** へ置けば天端が段の高さに揃う
        /// (あちらもピボット z=0 が板の天端)。</para>
        ///
        /// <para>⭕ **躯体は Z ∈ [−0.12, 0] = 高い側にしか出ない** — 段の柱は低い側に立つので干渉しない
        /// (高い側に立てると下屋のけらばを突き抜ける。2026-09-20 棟梁が実測で是正)。
        /// ⚠ 蹴込板だけ Y −0.020 へ出る(低い側の床板 厚 0.0303 に噛ませて継ぎ目の光を消す)。
        /// ⛔ <c>SeatBottom</c> で据えない。</para>
        ///
        /// <para>外形 W(X) **1.818** × H(Y) **0.321** × D(Z) **0.120**。
        /// <paramref name="danMm"/> = 両側の落縁の天端の差[mm](⛔ 指図に無い従属値)。焼いてあるもの: **301**。
        /// 材 `wood` ⇒ `Edo/御殿/新しい御殿FBXのマテリアルをremap`。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- kamachi --dan 0.301 --render</summary>
        public static string RokaKamachi(int danMm)
        {
            return P + "Goten_RokaKamachi_1ken_d" + danMm + ".fbx";
        }

        /// <summary>登廊(階段廊下)の屋根。切妻を斜長ぶん通し、幅は石段の平場ぶん取ったもの。
        /// **据えるときに勾配ぶん傾ける**ので、屋根そのものは平らに作ってある。
        /// <para>⚠ **幅は 1間(1.818)**。aa7edbae のコミット文の「幅4.4m」は誤り(柱の芯々のこと)で、
        /// 焼いてある FBX の梁間は <see cref="RoofKirizuma"/> と同一(2026-09-22 EDO-0394 で実測して復元)。
        /// 斜長は W1 = 10.82 / W2 = 14.42。</para>
        /// 生成: blender --background --python Tools/Blender/build_goten_roof.py -- noboriro 10.82 1.818 Goten_Roof_Noboriro_W1</summary>
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

        /// <summary>**玉砂利**(参道・敷き)の材。URP/Lit(パックの URP パッチ済み)。
        /// ⚠ パックは再配布不可・gitignore。⚠ terrain 用に焼かれた材なので **_BaseMap のタイリングは 1×1** —
        /// 敷く側が UV を m 単位で張る(1m で1周)。⚠ 在庫にこれ以外の玉砂利は無い(2026-09-16 照会)。</summary>
        public const string GravelMat = "Assets/Waldemarst/FreeJapaneseGarden/Materials/Terrain/M_FJG_Terrain_Ground_Gravel_01.mat";

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

        const string CliffDir = "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/"
                              + "Rocks/Cliffs/Models/";

        /// <summary>**実肌の岩棚(野面石 1 段の土留め)**。松江松平邸 `slopeDoryu`(法尻の土留め)に使う。
        /// i = 8〜10。実寸(目録 `docs/asset-index.tsv`・Unity W×H×D):
        /// <c>cliff_piece_08</c> 3.63×0.44×1.74m / <c>cliff_piece_09</c> **2.19×0.30×1.12m**(指図の既定)/
        /// <c>cliff_piece_10</c> 1.76×0.42×0.92m。ピボットは底からの差 −0.01〜−0.05m(ほぼ底)。
        /// ⚠ **FBX(拡張子は大文字 `.FBX`)を返す。** プレハブは `prefab_cliff_piece_10` しか無い
        /// (08/09 は Prefabs に無い — 2026-09-13 に `ls` で確認)ので揃えて Models を指す。
        /// ⚠ パックは再配布不可・gitignore。材は FBX が持つ NatureManufacture の .mat で remap 不要。</summary>
        public static string CliffPiece(int i)
        {
            if (i < 8 || i > 10)
                throw new System.ArgumentOutOfRangeException("i", i, "NM.CliffPiece は 8〜10(登録済みのみ)");
            return CliffDir + "cliff_piece_" + i.ToString("00") + ".FBX";
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

        /// <summary>**常緑の照葉低木**(サカキ・アオキ・ヤブツバキの見立て)。山王社の
        /// **社叢の下層・林縁・前庭の帯・平場の縁**に撒く。在庫方 2026-09-06 の判定=**在庫0件**で、
        /// <see cref="Jouryoku"/> と同じ作り(空間占有法の骨格+葉のカード・LOD_0/1/2 の3本入り)で新造した。
        /// ⭐ **株立ち(地際から4〜7幹)・立ち枝・下がすぼまり上が丸い**卵形の樹冠。
        /// ⛔ **刈込(玉物)にしない** — 指図 `gardens[前庭の帯].forbidden` に「刈込」が立っている。
        /// ⛔ 花を付けない・紅葉色にしない(季節は春でも秋でもない)。
        /// <paramref name="size"/> は**丈をそのまま名乗る 4 段**: **H12 1.2m / H16 1.6m / H20 2.0m / H24 2.4m**
        /// (`scaleY` 0.75〜1.10 で 0.90〜2.64m を継ぎ目なく覆う)。⛔ 旧綴り Small/Mid は現物に無い。
        /// ⛔ 桜の同格 3.6/5.8/8.2 は当てない。
        /// **樹冠 ÷ 丈 = 0.79〜0.94**(実測 W: H12 0.96〜1.06 / H16 1.37〜1.41 / H20 1.80〜1.89 / H24 1.90〜2.22m)。
        /// ⚠ 指図 `gardens[前庭の帯].shrubs.crownRKen` 0.33間(半径0.60m)に収まるのは **H12 だけ** — 丈で選ぶ前に樹冠を測ること。
        /// 実寸の正典は `Tools/Blender/build_tree.py` 末尾の実測表。
        /// <para><paramref name="i"/> は**個体**(1〜3)。⛔ 1本の層を1個体で埋めない。</para>
        /// ⚠ 材質は在庫の桜のもの(`M_FJG_Tree_Sakura_Bark_A` / `..._Sprout_Summer`)の**名前だけ**を
        /// 運ぶ=確度U。**Unity で remap する**(`Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap`
        /// は邸名が付いているが `Models/Trees` 全体を舐める共通のもの)。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- teiboku H12 H16 H20 H24 --render</summary>
        public static string Teiboku(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Teiboku_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        /// <summary>**クロマツ(社叢)**。山王社の社叢の高木。⭐ **林の松** — 在庫の
        /// `JG.Pine` は独立して枝を張った**庭の松**で樹形が別。
        /// ⚠ **なぜ新造したか**: 在庫の素の丈は 6.43〜6.64m が上限で、指図の社叢は
        /// `slopeBands[*].matsuH` = 9.5〜13.0m。実装は `scaleY` 1.43〜1.99 で縦に伸ばしており、
        /// `scaleXZ ≤ 1.15` の規約と合わせて**異方比 最悪 1.99**(針葉の房が縦に2倍)になっていた。
        /// 庭方 2026-09-07 九巡目 中4 の判定で部材の側を直したもの。
        /// ⭐ 樹形は**ゆるく曲がる幹・水平に張り出す枝の段・段の上に乗る板状の針葉の房・
        /// 枝下の枯れ枝の名残**。⛔ **仕立て(門被り・段作り)にしない** — 社叢の松であって庭木ではない。
        /// 樹高: **Mid 10.5m / Big 12.5m**。⭐ **丈 ≤ 11.5m は Mid・超は Big** を選べば
        /// `scaleY` は 0.905〜1.095 に収まる。⛔ 桜の同格(3.6/5.8/8.2)も落葉高木の刻みも当てない。
        /// 樹冠 ÷ 丈 = 0.55〜0.77(在庫の黒松の LOD0 実測 0.681 と同じ帯)。
        /// <para><paramref name="i"/> は**個体**(1〜3)。⛔ 1本の層を1個体で埋めない。</para>
        /// ⭕ 材質は**在庫のクロマツの物**の名前だけを運ぶ(`M_FJG_Tree_BlackPine_Bark` /
        /// `..._Sprout_A_Green`)。**Unity で remap 済**(2026-09-07)。
        /// 生成: blender --background --python Tools/Blender/build_tree.py -- matsu Mid Big</summary>
        public static string Matsu(string size, int i = 1)
        {
            return "Assets/Edo/Models/Trees/Tree_Matsu_" + size
                 + (i <= 1 ? "" : "_" + i.ToString("00")) + ".fbx";
        }

        /// <summary>**山王社の楼門(隨身門)・坂下の門(仁王門)兼用**。三間一戸・単層・入母屋・出組・本瓦葺。
        /// 在庫方 2026-09-13 の判定=在庫に三間一戸の寺社の門が無い(城郭の櫓門・長屋門のみ)ので新造。
        /// 柱芯は X ±1.818(梁間2間=通り抜けの奥行)/ Z ±2.727(桁行3間=門の幅)。外形 6.76×7.00×8.58m。
        /// ⭐ **通り抜け=ローカル X・正面=+X・ピボット=門の芯・敷居の高さ**(基壇は −0.60 まで根入れ)。
        /// yaw 0° で据えると正面=東・通り抜け=東西。scale は Vector3.one。
        /// ⚠ 材は名前だけ ⇒ `Edo/山王社/新造部材のマテリアルをremap`。柱高・組物・妻飾り・軒反りは【U 類型】。
        /// ⭐ 基壇の出だけ門ごとに作り分ける(柱芯から +X/−X/+Z/−Z・mm)。出は指図の取り合いの面から生成器が決める
        ///   — 楼門 452,452,178,178/坂下の門 297,297,178,178。±Z は側柱の外面(面の2mm手前)まで。
        /// 生成: blender --background --python Tools/Blender/build_sanno_romon.py -- --render</summary>
        public static string SannoRomon(int duKen, int dvKen, int pX, int mX, int pZ, int mZ)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Romon_" + duKen + "x" + dvKen + "ken_k"
                 + pX + "-" + mX + "-" + pZ + "-" + mZ + ".fbx";
        }

        /// <summary>**山王社の楼門(隨身門)— 明治16年実測図の寸法**(ユーザー裁定C 2026-09-14)。三間一戸・単層・入母屋・出組・本瓦葺。
        /// 柱芯の外形は <paramref name="passMm"/>(通り抜け=X)× <paramref name="widthMm"/>(幅=Z)[mm]、柱間は外形 ÷ 間数
        /// (5750×7620 ⇒ 2.875 × 2.54)。⭐ 通り抜け=ローカル X・正面=+X・ピボット=門の芯・敷居の高さ・yaw 0 で正面=東・scale one。
        /// 基壇の出 k は柱芯から +X/−X/+Z/−Z[mm]。⚠ 現行は基壇の全外形 7.9×11.1【A】で四周一様(1075,1075,1740,1740)—
        /// 基壇は詰めずに下を腰石垣(天端 = 基壇の下端)で受ける。前面(+X)と両脇(±Z)の根入れ帯 0.60 は**見え掛りの切石+葛石の縁**
        /// (葛石 0.20・羽目石 0.40 を 0.015 引く【U 部材方 2026-09-14】)、背面 −X は据え置き。前後の石段は持たない(天端=Y0)。
        /// 外形 W(X)9.70 × H(Y)8.47(−0.60〜7.87)× D(Z)11.57・24.7k tris。柱高 3.8【U】・丸桁の上端 4.75(軒高 4.8【U】)・
        /// 軒の出 側柱芯から 中央 1.81 / 隅(軒反り込み)1.97。大棟の上端 7.61 = 勾配規則の従属値・入母屋【S】(棟高 9.0 の目安は出典なし・考証が撤回)。
        /// 材は名前だけ ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: SANNO_SASHIZU=&lt;指図&gt; blender --background --python Tools/Blender/build_sanno_romon.py -- --only 楼門 --kidan 7.9x11.1 --pitch 2.875x2.54 --render</summary>
        public static string SannoRomon(int duKen, int dvKen, int passMm, int widthMm, int pX, int mX, int pZ, int mZ)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Romon_" + duKen + "x" + dvKen + "ken_" + passMm + "x" + widthMm
                 + "_k" + pX + "-" + mX + "-" + pZ + "-" + mZ + ".fbx";
        }

        /// <summary>**山王社の坂下の門(仁王門)— 明治16年実測図 第2稿の読み**(2026-09-14)。三間一戸・単層・**切妻・組物なし**・本瓦葺。
        /// 明治図には写っていない(撤去済み)ので外形 <paramref name="passMm"/>(通り抜け=X)× <paramref name="widthMm"/>(幅=Z)は【U】
        /// (御宮絵図の楼門比)、姿は【S 名所図会】。現行 (2,3,3000,6000,298,298,178,178) = 柱間 1.5 × 2.0・戸口 2.0。
        /// ⭐ 楼門と同じ規約: 通り抜け=ローカル X・正面=+X(扉は −X へ開く)・大棟=Z・ピボット=門の芯・敷居の高さ・yaw 0 で正面=東・scale one。
        /// 基壇の出 k は柱芯から +X/−X/+Z/−Z[mm]。取り合いの面の 2 mm 手前: +Z = 袖塀 `Ita_Niou_N` の木口(北の側柱の外面 0.18)、
        /// −X = 前庭の西縁の腰石垣の面(犬走り 0.30)。面の無い +X・−Z は向かいの側に揃える(旧 300 四周は Ita_Niou_N を 0.120 越えた)。
        /// 外形 W(X)5.62 × H(Y)5.86(−0.60〜5.26)× D(Z)8.31・12.3k tris。柱高 3.10・軒の出 1.20・妻の出 0.90・軒桁の上端 3.40・
        /// 軒先の名目 2.89(従属値)・大棟の瓦場 4.69【すべて U 類型】。材は名前だけ ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: SANNO_SASHIZU=&lt;指図&gt; blender --background --python Tools/Blender/build_sanno_romon.py -- --only 坂下 --kidan 3.6x6.6 --plan 3.0x6.0 --bays 2x3 --kirizuma --faces -,0.30,0.18,- --render --full</summary>
        public static string SannoSakashitamon(int duKen, int dvKen, int passMm, int widthMm, int pX, int mX, int pZ, int mZ)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Sakashitamon_" + duKen + "x" + dvKen + "ken_" + passMm + "x" + widthMm
                 + "_k" + pX + "-" + mX + "-" + pZ + "-" + mZ + ".fbx";
        }

        /// <summary>**山王社の袖塀(回廊の翼の妻 ↔ 楼門の側面)** — 瓦葺の築地塀・長さ <paramref name="lenMm"/>[mm]・両端を袖瓦と漆喰で塞ぐ。
        /// 形は【S 名所図会「低い屋根付きの袖塀」/ S 御宮絵図「細い一本の部材」】から瓦葺の築地塀と読んだ【U】、丈・断面は練塀 `Dobei2m` のまま【U 類型】。
        /// 現行 4200(離れ 4.2 ± 0.5【A 明治16年図】)。外形 W(X)4.20 × H(Y)2.51 × D(Z)1.00・928 tris。
        /// ⭐ 走り=ローカル X・高さ=Y・厚み=Z(表裏なし)・ピボット=走りの中心・足元(楼門の敷居の高さ)。南北に走らせるなら yaw 90・scale one。
        /// ⚠ 楼門の芯の通り(X=0)で側柱の外面から走らせると、足元が礎盤に 0.09 食い込む(礎盤の丈 0.15)。
        /// ⚠ 材 `Wall Exterior Defence`(Japanese Castle)を持つので `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap` で結ぶ
        ///   (山王社の remap は Japanese Castle の材を見ない)。
        /// 生成: blender --background --python Tools/Blender/build_sanno_sodebei.py -- --len 4.2 --render</summary>
        public static string SannoSodebei(int lenMm)
        {
            return "Assets/Edo/Models/Hei/Sanno_Sodebei_" + lenMm + ".fbx";
        }

        /// <summary>**山王社の袖塀 — 足元二段**(普請奉行の裁定 案A 2026-09-14)。断面・屋根は <see cref="SannoSodebei(int)"/> と同じ(屋根は一直線)。
        /// ⭐ **門側 = ローカル −X**。門側の端から <paramref name="stepAtMm"/> までは足元 Y0(楼門の基壇の天端 28.3)、その先は Y +<paramref name="stepRiseMm"/>
        /// (回廊の基壇の妻の石垣の天端 29.0)に載る。腰板と貫の帯は足元に沿って上がり、段の小口は板で塞ぐ。
        /// 門側の木口の足元は楼門の礎盤の形に 0.095 × 0.155 欠く(礎盤への食い込み 0)。現行 (4200, 1560, 700)。
        /// 外形 W(X)4.20 × H(Y)2.51 × D(Z)1.00・1.1k tris。ピボット=走りの中心・Y0(楼門の敷居の高さ)。
        /// ⚠ 材 `Wall Exterior Defence` ⇒ `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_sodebei.py -- --len 4.2 --step 1.56x0.70 --render</summary>
        public static string SannoSodebei(int lenMm, int stepAtMm, int stepRiseMm)
        {
            return "Assets/Edo/Models/Hei/Sanno_Sodebei_" + lenMm + "_d" + stepAtMm + "-" + stepRiseMm + ".fbx";
        }

        /// <summary>**山王社の透塀(瑞垣)— 1スパン**。屋根銅瓦葺【S 目録1941】・腰板+連子格子+小壁。丈は【U 考証】
        /// 腰の天端 0.75 / 透かし 0.75〜1.65 / 小壁 1.65〜1.95 / 軒先 1.95 / 棟の天端 2.25(実測 2.250)。
        /// <paramref name="spanMm"/> = 柱芯間(中門側は本柱の外面から)[mm]。<paramref name="ends"/> = 端の種類 2 文字(−X, +X):
        /// n = 次のスパンへ続く(⭐ 柱は +X の端にだけ持つ)/ t = 中門の本柱の外面へ突き付け(柱なし・破風板で閉じる)/ c = 隅部材へ続く(柱なし・屋根を 0.40 手前で止める)/
        /// h = 口の縁の柱で止める(柱芯 = スパンの端。柱を棟の天端まで立てて頭に銅の笠。⭐ 渡廊下の北の木口はこの柱の南の面へ突き付く)。
        /// ⭐ 走り=ローカル X・高さ=Y・厚み=Z(見え面 +Z・断面は表裏対称)・ピボット=スパンの中心・床(基壇の天端)。scale one。
        /// 外形【実測 2026-09-18・s = spanMm/1000】基壇 X ±s/2(厚み ±0.30)/ 腰 −s/2〜+s/2+0.09(±0.293)/ 透かし・小壁 ±s/2(±0.40)/ 軒・屋根 −s/2〜+s/2+0.09(±0.40)。
        /// 丈 H(Y)2.55(−0.30〜2.250)。基壇の根入れ 0.30・幅 0.60。端の引き: n = 0(節点ちょうど。柱は節点をまたいで ±0.09)/ t = 0(節点ちょうど・柱なし)/
        /// c = 基壇 0.300・躯体 0.090・銅瓦 0.400 を内へ引く(残りは隅部材が受ける)/ h = 柱が節点をまたいで ±0.09(銅の笠 ±0.12)。⚠ t・h の端は袖の稜で厚みが ±0.457 に広がる。
        /// 例 1852_nn: W(X)1.942(−0.926〜+1.016)× H 2.55 × D 0.80・1.1k tris。
        /// ⚠ 辺は run 側で**等分**して焼く(n = round(辺長 / 1.818)、スパン = 辺長 / n。柱間 6 尺【施主裁定 2026-09-18】)。瓦はスパンに瓦モジュールが整数枚になる縮尺。
        /// 材 `wood` / `wall C` / `Doukawara` / `Kirishi` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_sukibei.py -- --span 1.852 --ends cn,nc,nn --no-kado --render</summary>
        public static string SannoSukibei(int spanMm, string ends)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Sukibei_" + spanMm + "_" + ends + ".fbx";
        }

        /// <summary>**山王社の透塀の隅**。<paramref name="part"/> = "Dezumi"(出隅: 脚が −X と −Z、見え面 +Z の側が隅棟)/
        /// "Irizumi"(入隅: 脚が −X と +Z、見え面の側が谷)。ピボット=隅の柱の芯・床。隅の柱・隅の瓦場(隅棟と谷の銅板)・野地・基壇の升を持つ。
        /// 隣のスパンは端 `c` を使う。<paramref name="refSpanMm"/> = 瓦の縮尺を合わせた基準スパン(= 柱間 6 尺 1818【施主裁定 2026-09-18】)。
        /// 外形【実測 2026-09-18】出隅 X[−0.477,+0.493]・Z[−0.477,+0.493] / 入隅 X[−0.477,+0.493]・Z[−0.493,+0.477]、H(Y)2.55(−0.30〜2.250)・489 tris。
        /// 脚の到達(隅柱の芯から)基壇 0.300 / 躯体 0.400 / 銅瓦 0.4766(外の角の隅棟は 0.4928 出る)⇒ 端 `c` のスパンと基壇が面一・躯体が 0.310・銅瓦が 0.077 重なる。
        /// ⛔ 隣のスパンの割り付けからこの長さを引かない(スパン部材が端の型ごとに自分の中で引いてある ── 二重の引き算になる)。
        /// 材 ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_sukibei.py -- --span 1.818 --ends cn --render</summary>
        public static string SannoSukibeiKado(string part, int refSpanMm = 1818)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Sukibei_Kado_" + part + "_" + refSpanMm + ".fbx";
        }

        /// <summary>**山王社の社殿(権現造)— 明治16年実測図の寸法**(ユーザー裁定C 2026-09-14)。1棟1FBX・銅瓦葺。
        /// <paramref name="kind"/> = "Honden" / "Heiden" / "Tsukuriai" / "Haiden" / "Kohai"。
        /// 間数 <paramref name="nuKen"/>(東西=X)×<paramref name="nvKen"/>(南北=Z)、柱芯の外形 <paramref name="ewMm"/>×<paramref name="nsMm"/>[mm]、
        /// 柱間は外形 ÷ 間数。⭐ ピボット = `munes` の区画の中心・地盤レベル、ローカル +X = 東 = 正面 ⇒ yaw 0・scale one。
        /// ・本殿 (3,3,7620,7620) 外形 W12.75×H11.82×D12.75・33.6k tris・大棟の上端 11.56【S 目録 三間×三間 / A 帯の南北 / U 柱間 2.54】
        ///   ⛔ (3,3,9200,7620) は東西を拝殿の梁間で読んだ誤り(2026-09-14 考証 第2稿で撤回)。旧 FBX はシーンが参照中なので残す — 据えない
        /// ・幣殿 (3,1,7620,7620) 外形 W8.94×H6.10×D8.82・11.6k tris。桁行三間=軸(東西)・梁間一間=本殿の中央三間幅・兩下造【S 目録 / A 加藤2018 §5-2】。舞良戸は柱間ごと
        /// ・作り合い (1,1,2000,7620) 外形 W3.32×H6.10×D8.82・5.7k tris。軸方向 2.0【P 残差】・幅は幣殿に揃えた。本殿への木階を内に持つ
        ///   幣殿・作り合いの棟は隣の軒の 0.25 下(5.90)に頭打ち — 屋根は本殿・拝殿の軒下へ 0.75 潜る
        /// ・拝殿 (3,7,9200,17800) 外形 W15.32×H11.83×D23.92・57.1k tris・大棟の上端 11.57・千鳥破風は柱間に寄せた
        /// ・向拝 (1,3,1900,7620) 外形 W3.50×H7.61×D8.90・4.8k tris
        /// 床高・本殿の段・反り・軒反り・亀腹・腰組は旧部材と同じ規則。軒の出 = 半スパン×0.63 で 2.90m になるので、
        /// 本殿・拝殿は壁通りに軒小壁を立てて組物の帯を塞いだ。柱高・組物・内法は【U】。材は名前だけ ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: SANNO_SASHIZU=&lt;指図&gt; blender --background --python Tools/Blender/build_sanno_shaden.py -- honden tsukuriai heiden haiden kohai kizahashi --render</summary>
        public static string SannoShaden(string kind, int nuKen, int nvKen, int ewMm, int nsMm)
        {
            return "Assets/Edo/Models/Sanno/Sanno_" + kind + "_" + nuKen + "x" + nvKen + "ken_" + ewMm + "x" + nsMm + ".fbx";
        }

        /// <summary>**山王社の向拝の木階(三級・登高欄なし)— 明治16年寸法**。幅 <paramref name="wMm"/>(南北=Z)× 出 <paramref name="runMm"/>(東へ=X)
        /// × 丈 <paramref name="riseMm"/>[mm](`kaidans[向拝の階]` の wKen・a〜b・yTop−yBot)。現行 (7620,1140,950)・252 tris。
        /// ⭐ ピボット = a〜b の中点・地盤レベル、東(+X)へ降りる ⇒ yaw 0・scale one。⛔ 石段(`Dan_*`)にしない。
        /// ⚠ 本殿の木階は作り合いの部材に入る(今回は未造)。
        /// 生成: SANNO_SASHIZU=&lt;指図&gt; blender --background --python Tools/Blender/build_sanno_shaden.py -- kizahashi</summary>
        public static string SannoKizahashi(int wMm, int runMm, int riseMm)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Kizahashi_" + wMm + "x" + runMm + "x" + riseMm + ".fbx";
        }

        /// <summary>**山王社の御供所(供の棟)— 御宮絵図の形の独立の一棟**(施主の再裁定 2026-09-15)。切妻・棟は南北・本瓦葺【U】。
        /// 柱芯 <paramref name="nuKen"/>(東西=X)× <paramref name="nvKen"/>(南北=Z)[間]、外形 <paramref name="ewMm"/>×<paramref name="nsMm"/>[mm]。
        /// 現行 (3, 4.5, 5454, 8181)。柱間は東西 1間×3 / 南北 4.5間を5等分【U 部材方】。
        /// ⭐ ピボット = 柱芯の矩形の中心・地盤(+X = 東 / +Z = 北)⇒ yaw 0・scale one。
        /// 外形 W(X)7.204 × H(Y)5.360 × D(Z)9.311。基壇 0.45(出 0.30 四周)・軒先 3.00・軒の出 0.75・ケラバ 0.45・大棟の上端 5.147。
        /// 口: 北面の東の柱間(X 0.909〜2.727)= 渡廊下の口(戸を立てない)/ 南面の東の柱間 = 勝手口(板戸を半ば引いた姿)。
        /// ⭕ **勝手口は東の柱間に焼けている**(2026-09-20 に FBX を読み直して実測: 南面の板戸 X 0.999〜1.858)⇒ 焼き直しは済み。
        /// ⛔ 明治16年の L 字3本(`Sanno_Gokusho_{Omoya,Tsugi,Higashi}_*`)は据えない。
        /// 材 `wood` / `wall C` / `door wall` / `roof` / `roof ornaments` / `Kirishi` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_gokusho_ikko.py -- --render</summary>
        /// <remarks>⚠ 引数は **double**(⛔ float にしない)── 指図 `bom` が予定した綴り
        /// `SannoGokusho(3, 4.5, 5454, 8181)` の `4.5` は double 定数なので、float では通らない。</remarks>
        public static string SannoGokusho(double nuKen, double nvKen, int ewMm, int nsMm)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            return "Assets/Edo/Models/Sanno/Sanno_Gokusho_" + nuKen.ToString("0.##", inv) + "x"
                 + nvKen.ToString("0.##", inv) + "ken_" + ewMm + "x" + nsMm + ".fbx";
        }

        /// <summary>**山王社の回廊(屋根付きの廊)— 翼1本**。楼門の両脇から社殿へ回る翼で、北・南で長さと間数が違う。
        /// <paramref name="bays"/> = 走りの間数【U】/ <paramref name="bariBays"/> = 梁間の間数【U】/
        /// <paramref name="runMm"/> = 走り(北 20650 / 南 17550【A 明治16年実測図】)/ <paramref name="bariMm"/> = 梁間(4200【A】)。
        /// 現行 北 (8, 2, 20650, 4200) / 南 (7, 2, 17550, 4200)。切妻・**銅瓦葺**【U `runs[Kairo_*].roof`】。
        /// ⭐ 走り = ローカル X・高さ = Y・梁間 = Z。**見え面(腰板+連子窓の閉じた壁)= +Z = 外(東)**、−Z(中庭の側)は柱だけで開ける。
        /// ⭐ ピボット = 柱芯の矩形の中心・**床(= 石垣の基壇の天端 `runs[Kairo_*].seat` 29.0)**。⛔ 部材は基壇を持たない(石垣が受ける)。
        /// ⭕ 走り X について**軸部は鏡像対称**(瓦の位相だけ非対称・袖瓦が隠す)⇒ 門側がどちらの X 端でも据わる。北翼・南翼とも同じ yaw
        /// (`grid.frames[東面]` 4.6° 込みで +Z が東を向く向き)。scale one。
        /// 丈【U 部材方 2026-09-20 ── `_pending`「回廊の軒高・棟高…」の①】: 軒先 2.100 / 桁の天端 2.405 / 大棟の上端 3.942 / 鬼の頂 4.116。
        /// 軒の出 0.909(半間)・ケラバ 0.455・勾配は瓦モジュールの素の 5.5寸 ⇒ 棟高は従属値。
        /// 上下を挟む実測: 袖塀の屋根の天端(座から 1.805)&lt; 軒先 2.100(余裕 0.295)/ 大棟(絶対 32.942)&lt; 楼門の軒高 33.100(余裕 0.158)。
        /// 外形 北 W(X)21.789 × H(Y)4.316 × D(Z)6.262・24.9k tris / 南 W(X)18.689・同 H・D・21.7k tris(どちらも Y −0.200〜4.116 = 根入れ 0.20)。
        /// 腰板 0.75 / 連子窓 0.75〜1.80 / 小壁 1.88〜2.205。門側の妻は**閉じた壁**で袖塀の木口を受ける(`joints` 突き付け・隙間は不可)。
        /// 材 `wood` / `wall C` / `Doukawara` / `Kirishi` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_kairo.py -- --render</summary>
        public static string SannoKairo(int bays, int bariBays, int runMm, int bariMm)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Kairo_" + bays + "x" + bariBays + "ken_"
                 + runMm + "x" + bariMm + ".fbx";
        }

        /// <summary>**山王社の鳥居 — 石造の明神鳥居**。⭐ **一ノ鳥居・二ノ鳥居に同じ1点を使う**(同形式【A】・
        /// 駒絵の大小は遠近の誇張なので ⛔ 寸法比を採らない)。座は `torii[].pos`。
        /// 形式【A 考証 2026-09-20 ── 『江戸名所百人美女』「山王御宮」安政4年の原寸実見】: 笠木に反り・島木あり・
        /// 貫は柱を貫いて木鼻を出す・額束に扁額(朱地)・足元は八角の段付き台石。⛔ 三角の破風を付けない(山王鳥居にしない)。
        /// ⛔ 崩れ・欠けを表現しない(安政2年10月に倒れたが石は砕けず、同じ石で起こし直した直後の姿【A】)。
        /// <paramref name="spanMm"/> = 柱間(柱芯々)/ <paramref name="tallMm"/> = 総高(笠木の上端・中央)[mm]。現行 (5454, 7272) = 3間 × 4間【U 部材方】。
        /// ⭐ 幅 = ローカル X・高さ = Y・厚み = Z。**正面(扁額のある面)= +Z**。ピボット = 柱芯の中央・地盤(台石は Y −0.35 まで根入れ)。
        /// ⛔ `SeatBottom` で据えない。⭕ X について左右対称。
        /// 外形 W(X)7.654 × H(Y)7.922(−0.350〜7.572・反りの頂)× D(Z)1.450・1.1k tris。
        /// 内法 4.854(柱径 0.60)・笠木の長さ 7.654・木鼻の先 ±3.271・柱頭は ころび 1/40 で 0.154 内へ。
        /// 道との関係: 二ノ鳥居の辻の路面 5.50 に対し柱が路面の内へ片側 0.323 ／ 笠木 7.654 &lt; 道敷(領域 12〜15m)。
        /// 材 `Kirishi` / **`Shu_Torii`**(扁額の朱地)⇒ `Edo/山王社/新造部材のマテリアルをremap`
        /// (⚠ `Shu_Torii.mat` は `Assets/Edo/Materials` に在るので、その借り先を remap に足してある)。
        /// 生成: blender --background --python Tools/Blender/build_sanno_torii.py -- --render</summary>
        public static string SannoTorii(int spanMm, int tallMm)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Torii_" + spanMm + "x" + tallMm + ".fbx";
        }

        /// <summary>**山王社の段石(石段の一段)**。蹴上 <paramref name="keri"/> / 踏面 <paramref name="fumi"/> / 幅 <paramref name="w"/>[m]、
        /// 個体 <paramref name="i"/> の偶奇で a / b を振る(⛔ 片方だけを53段並べない — 目地が一直線に立つ)。
        /// 寸法は指図 `kaidans` が正典で、**蹴上・踏面は段数と平面長・比高からの従属値**(⛔ CLAUDE.md の 0.30/0.45 は参道の坂に当てない)。
        /// 焼けている組: 男坂 (0.260, 0.650, 6.999) / 女坂 (0.300, 1.199, 6.363) / 参道の階 (0.250, 0.542, 5.509)。
        /// ⚠ 旧 (0.260, **0.693**, 6.999) は男坂の平面長を詰める前の組で、**どの階も参照していない**(消していない)。
        /// ⭐ 幅 = X / 高さ = Y / 走り = Z、**+Z = 見え面 = 坂下(蹴上の面)**。ピボット = 踏面の中心・**踏面の天端**。
        /// ⇒ 段 i(下から0起点)は position = 下端 + 進行方向 × 踏面×(i+0.5)、position.y = 下端の天端 + 蹴上×(i+1)。
        /// ⛔ `SeatBottom` で据えない(躯体が Y −0.18 へ垂れている)。走りは Z −(踏面/2+0.10)〜+踏面/2(0.10 は上の段の下へ潜る差し込み)。
        /// 外形(男坂)W(X)6.999 × H(Y)0.440 × D(Z)0.750。材 `M_FJG_Rock_001` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: blender --background --python Tools/Blender/build_sanno_buzai.py -- dan --only=男坂 --render</summary>
        public static string SannoDan(float keri, float fumi, float w, int i)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            return "Assets/Edo/Models/Kaidan/Dan_" + keri.ToString("F3", inv) + "_"
                 + fumi.ToString("F3", inv) + "_" + w.ToString("F3", inv) + "_"
                 + (i % 2 == 0 ? "a" : "b") + ".fbx";
        }

        /// <summary>**山王社の小庭の井戸 — 井筒(玉石の輪積み)と井桁を一体で**。⛔ 井戸屋形・釣瓶・縁石・板石敷は持たない
        /// (在庫にも無いので部材方へ。井戸屋形の棟の向きは指図 `_pending` が未決)。
        /// 在庫の `Doi_Ido` / `Matsudaira_Ido` はどちらも**切石の角井戸枠 + 桁 + 釣瓶**で玉石の輪も井桁も持たない ⇒ 新造【U 庭方 2026-09-15】。
        /// <paramref name="naikeiMm"/> = 井筒の内径(3尺 = 909)/ <paramref name="igetaTallMm"/> = 井桁の丈(見付 0.15 × 3 段 = 450)[mm]。
        /// 現行 (909, 450)。指図 `ido`(前庭の井戸と同じ作り)が正典 — 内径 3尺・壁厚 0.24・井桁は内法 3尺 / 見付 0.15 / 3 段。
        /// ⭐ 高さ = Y / 平面 = X・Z(井筒は円・井桁は X と Z に対称 ⇒ **向きは任意**)。ピボット = 井戸の芯・**地盤レベル**。
        /// ⛔ `SeatBottom` で据えない(井筒が Y −1.50 まで根入れしている)。
        /// 井筒 天端 +0.05(地盤から石の輪を覗かせる)〜 −1.50・底は石の円板。井桁 0.05〜0.50、段ごとに向きを互い違いにし木口を 0.06 出す【U 部材方】。
        /// 材 `Foundation_A_01`(Village Kit のアトラス)/ `wood` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。⛔ 新規マテリアルなし。
        /// 生成: blender --background --python Tools/Blender/build_sanno_ido.py -- --render</summary>
        public static string SannoIdoIgeta(int naikeiMm, int igetaTallMm)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Ido_Igeta_" + naikeiMm + "x" + igetaTallMm + ".fbx";
        }

        /// <summary>**山王社の中門(瑞垣門)**。一間平唐門・四脚(本柱2+控柱4)・銅瓦葺【S [国宝建造物目録1941]】。
        /// 在庫『無い』(指図 `bom[中門(一間平唐門)]`)ので新造。
        /// ⭐ **通り抜け=ローカル X・正面=+X(扉は −X へ開く)・大棟=Z(唐破風は ±Z の妻)・ピボット=門の芯・敷居の高さ**。
        /// yaw 0° で据えると正面=東・通り抜け=東西。scale は Vector3.one。
        /// 柱芯: 本柱 Z ±0.909(戸口1間)/ 控柱 X ±0.909・Z ±0.909。外形 W(X)3.90 × H(Y)4.45(−0.30〜4.15)× D(Z)3.36・15.9k tris。
        /// 基壇は敷居と面一の切石(根入れ 0.30)。出は柱芯から +X/−X/+Z/−Z(mm)で、±Z は透塀の門口の縁(=本柱の芯)
        /// ⇒ 0。礎盤だけ柱の半径 0.15 まで出る。材 `wood` / `door wall` / `Kirishi` / `Doukawara` ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 柱の太さ・高さ・冠木・軒と妻の出・唐破風の断面・基壇は【U 類型】。
        /// 生成: blender --background --python Tools/Blender/build_sanno_chumon.py -- --render</summary>
        public static string SannoChumon(int duKen, int dvKen, int pX, int mX, int pZ, int mZ)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Chumon_" + duKen + "x" + dvKen + "ken_k"
                 + pX + "-" + mX + "-" + pZ + "-" + mZ + ".fbx";
        }

        /// <summary>**山王社の中門(瑞垣門)— 明治16年寸法**(ユーザー裁定C 2026-09-14)。一間平唐門・四脚・銅瓦葺【S 目録1941】。
        /// 柱芯の外形は <paramref name="passMm"/>(通り抜け=X)× <paramref name="widthMm"/>(幅=Z)[mm]。柱間は社殿群で揃う 2.54【U 考証方の当て】
        /// ⇒ 本柱の芯 Z ±1.27(`axis.colWidthM`)・控柱の芯 X ±1.27(通り抜けも同じ一間【U 部材方】)。
        /// ⭐ 通り抜け=ローカル X・正面=+X(扉は −X へ開く)・大棟=Z(唐破風は ±Z の妻)・ピボット=門の芯・敷居の高さ・yaw 0 で正面=東・scale one。
        /// 口: 本柱の外面の間 2.84(礎盤の帯。丈 1.0 で 2.828 — 柱の転び)/ 本柱の内面の間 2.25。
        /// 基壇の出 k(柱芯から +X/−X/+Z/−Z・mm): ±X = 面なしの設計値 0.40・±Z = 透塀の口の縁(本柱の外面)の 2 mm 手前。
        /// 外形 W(X)4.62 × H(Y)4.74(−0.30〜4.44)× D(Z)4.08・21.1k tris。高さ・柱の太さ・唐破風・軒の出 0.90・妻の出 0.60 は旧と同じ【U 類型】。
        /// 材は名前だけ ⇒ `Edo/山王社/新造部材のマテリアルをremap`。
        /// 生成: SANNO_SASHIZU=&lt;指図&gt; blender --background --python Tools/Blender/build_sanno_chumon.py -- --pitch 2.54x2.54 --render</summary>
        public static string SannoChumon(int duKen, int dvKen, int passMm, int widthMm, int pX, int mX, int pZ, int mZ)
        {
            return "Assets/Edo/Models/Sanno/Sanno_Chumon_" + duKen + "x" + dvKen + "ken_" + passMm + "x" + widthMm
                 + "_k" + pX + "-" + mX + "-" + pZ + "-" + mZ + ".fbx";
        }

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

        /// <summary>**切石の縁石**(白洲・平場の縁。指図 `fuchi[]`)。在庫に切石の縁石は無い
        /// (<see cref="SannoDan"/> は石段の一段・<see cref="Ishibashi"/> は橋)ので新造【U 部材方 2026-09-20】。
        ///
        /// <para>⭐⭐ **一つの型で落差 0 と落差 0.30 の両方を賄う** — 天端を揃え、**下に隠れる丈を変える**。
        /// 天端は常に Y=0、躯体は常に **Y −0.480**(= 最大落差 0.30 + 根入れ 0.18)まで垂れる。
        /// 落差 0 の縁(`F_Omote_N`。両側とも 26.70)は**全丈が地中**で天端だけが砂利留めの見切りとして出、
        /// 落差 0.30 の縁は低い側に 0.30 が出て残り 0.18 が地中に入る。
        /// ⛔ **落差が 0 でも縁石を省かない** — 役目は『白洲の砂利を留める』ことで落差の有無とは別。</para>
        ///
        /// <para>⭐ 走り = X / 高さ = Y / 見込み = Z、**+Z = 見え面 = 落差の低い側**。
        /// ピボット = **走りの中心・天端・縁の線(見付面)**。躯体は Z ∈ [−w, 0] = **高い側**に置いてある
        /// ⇒ <c>position = 縁の線の中点 / position.y = 高い側の面の高さ / yaw = 低い側を向く法線の方位</c>。
        /// ⛔ <c>SeatBottom</c> で据えない(躯体が Y −0.48 へ垂れている)。
        /// ⛔ 走りを分割して並べない — **1本で1本の縁**(石の目地は部材の中で約 1.2m ごとに入っている)。</para>
        ///
        /// <para><paramref name="runKen"/> = 縁の長さ[間](指図 `fuchi[].b − fuchi[].a`)、
        /// <paramref name="w"/> = 見込み[m](指図 `fuchi[].w`。既定 0.36)。
        /// 焼いてあるもの: **5 / 12.52 / 14 / 17 / 52 間**(すべて w 0.36)。外形 H(Y) 0.480 × D(Z) = w。
        /// 材 `Kirishi` ⇒ `Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap`。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- fuchi --render</summary>
        public static string Fuchiishi(float runKen, float w = 0.36f)
        {
            return "Assets/Edo/Models/Fuchi/Fuchiishi_" + Goten.KenTag(runKen)
                 + "ken_w" + (int)System.Math.Floor(w * 1000.0 + 0.5) + ".fbx";
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
        /// 奥行(Z)は語を分けて読む: **軒の出 +Z 0.58m** / **躯体 3.11〜3.12m**(壁の外面 → 内壁面。
        /// 生成器 3.12・普請検査の実測 3.11。指図 `const.nagayaD` はこれ)/ **内側の軒 0.6m 級**を含む
        /// **外接の内端 −Z 3.73m** / 外接の奥行 4.35m。⛔ 3.73 を「躯体」と呼ばない(2026-09-13 に直した)。
        /// 高さ 5.51m(妻の鬼まで)。
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

        /// <summary>**裏長屋(裏店)— 割長屋**。町屋24町の路地に並ぶ九尺二間の棟(類型共用)。
        /// 桁行 <paramref name="wKen"/> 間 × **奥行 2間**・平屋・桟瓦・下見板腰。
        /// **+Z の一面だけに戸**が並び、−Z は盲面(背中合わせの隣棟・隣地の塀に接する面)。
        ///
        /// <para>⭐ 1戸 = **間口 九尺(1.5間 = 2.727m)× 奥行 二間**【一般類型 A】。
        /// 桁行は 1.5間で機械的に割る ⇒ **3間=2戸 / 4.5間=3戸 / 6間=4戸 / 9間=6戸 / 12間=8戸**
        /// (4.5間・3間は EDO-0362 で追加)。
        /// ⛔ **戸数を史実として名乗らせない**【U】— その筆に何戸あったかの史料は当プロジェクトに無い。</para>
        ///
        /// <para>実寸(焼いてある5本)— **W 5.994 / 8.721 / 11.448 / 16.902 / 22.356(X)× H 3.592(Y)× D 4.928(Z)**・
        /// 面 2,984 / 4,058 / 5,021 / 7,151 / 9,231。軒桁 **2.30**・棟天端 **3.592**・底 0.000。
        /// ⭕ 在庫の表店 <see cref="Eg.Shop01"/>(ES後 W4.93 × H4.25 × D4.03)より **0.66m 低い**。
        /// ⚠ 丈だけでは見分けが付かない — **1.5間ピッチの戸が延々続く割り**と**見世棚が無いこと**で見る。</para>
        ///
        /// <para>⭐ **列に詰めるとき効く一行**(EDO-0362・部材方 2026-09-22): 1棟が食う走りは
        /// **呼び寸法(ken×1.818)+0.540**(けらば 0.20×2 + 袖瓦の見付 0.07×2)— 5寸法とも一定。
        /// 呼び寸法のまま詰めると1棟ごとに 0.54m ずれるので、<see cref="EdoBuild.UraNagayaRun"/> は
        /// 必ず <see cref="EdoBuild.OwnMeasure"/> の実測 W を引いて使う(呼び寸法を直接使わない)。</para>
        ///
        /// <para>⚠ 軒は footprint の外へ ±Z に 0.55・±X に 0.20 出る。**ピボットには含まれない**
        /// (ピボット = footprint の中心・地盤レベル)。据えるときは **+Z を路地へ**向けること —
        /// 逆に向けると盲面が路地に向いて戸が消える。</para>
        ///
        /// 材 = `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`(すべてキット由来)。
        /// 無い寸法は
        /// blender --background --python Tools/Blender/build_typ_nagaya.py -- ura --ken &lt;桁行間&gt;
        /// で足す。</summary>
        public static string UraNagaya(float wKen)
        {
            return NagayaDir + "Typ_UraNagaya_" + Len2(wKen) + "ken.fbx";
        }

        /// <summary>**裏長屋 — 棟割長屋**(背中合わせ)。<see cref="UraNagaya(float)"/> と同じ割りだが
        /// **奥行 4間**(2間+2間)で、大棟を挟んで **±Z の両面に戸**が並ぶ。1棟で路地を2本分まかなう。
        ///
        /// <para>実寸 — **W 5.994 / 8.721 / 11.448 / 16.902 / 22.356(X)× H 4.584(Y)× D 8.564(Z)**・
        /// 面 4,298 / 5,824 / 7,195 / 10,127 / 13,067。軒桁 **2.30**(割長屋と同じ)・棟天端 **4.584**。
        /// ⚠ **棟高は梁間からの従属値** — 瓦の勾配 0.5456 は動かせないので、梁間が 2間→4間 になった分
        /// 棟が 0.99m 上がる。⇒ 表店 <see cref="Eg.Shop01"/>(4.25)より **0.33m 高い**。
        /// 見分けは丈ではなく**割りと見世棚の有無**で付く。</para>
        ///
        /// <para>⛔ <see cref="UraNagaya(float)"/> を2棟背中合わせに置いて代用しない —
        /// 間に隙間が出て棟が2本立って見える。</para>
        ///
        /// ピボット・材・軒の出は <see cref="UraNagaya(float)"/> と同じ(±Z とも開口面なので向きは自由)。
        /// 生成: blender --background --python Tools/Blender/build_typ_nagaya.py -- munewari --ken &lt;桁行間&gt;</summary>
        public static string UraNagayaMunewari(float wKen)
        {
            return NagayaDir + "Typ_UraNagaya_" + Len2(wKen) + "ken_munewari.fbx";
        }

        const string NagayaDir = "Assets/Edo/Models/Nagaya/";

        /// <summary>**山門 — 四脚門**(類型共用・寺4区画)。門口 **2間(3.636m)**・本柱2 + 控柱4・
        /// 切妻本瓦。実寸 **W 5.896 × H 5.382 × D 5.292**・面 1,765・**底 −0.260**(沓石が敷居より下)。
        /// 有効高 3.10 / 桁 3.95 / **棟天端 5.12**。
        ///
        /// <para>⛔ 2026-09-21 まで `gate:sanmon` は <see cref="Eg.Kabukimon"/>(冠木門)へ落ちていて
        /// **格が3段違っていた**(EDO-0318 ①)。格の梯子は
        /// <see cref="Own.Munemon"/> 3.60 &lt; <see cref="Yakuimon"/> 4.41 &lt; **山門 5.12**。</para>
        ///
        /// ローカル **+X = 門口の方向 / +Z = 外(参道)**。ピボット = **門の芯・敷居レベル**。
        /// 寸法は【U】— 指図に欄が無く、部材方が「格の順が立面で読める」ことだけを条件に決めた。
        /// 生成: blender --background --python Tools/Blender/build_typ_jisha.py -- sanmon</summary>
        public const string Sanmon = MonDir + "Typ_Sanmon.fbx";

        /// <summary>**薬医門**(類型共用・社家=神主の屋敷)。門口 **3.00m**・本柱2 + **控柱2(後ろだけ)**・
        /// 切妻本瓦。実寸 **W 5.060 × H 4.673 × D 4.692**・面 1,564・**底 −0.260**。
        /// 有効高 2.70 / 桁 3.35 / **棟天端 4.41**。
        ///
        /// <para>⛔ 在庫の <see cref="Eg.Kmon"/> で代用しない — あれも薬医門だが **ES 後 W14.4m** の
        /// 袖付きの大門で、屋敷門に据えると長屋門級になる(在庫方 2026-09-21)。</para>
        ///
        /// <para>⚠ **控柱は −Z(内)側**。据えるとき +Z を表へ向けないと控柱が通りに出る。</para>
        /// ピボット = 門の芯・敷居レベル。寸法は【U】。
        /// 生成: blender --background --python Tools/Blender/build_typ_jisha.py -- yakuimon</summary>
        public const string Yakuimon = MonDir + "Typ_Yakuimon.fbx";

        const string JishaDir = "Assets/Edo/Models/Jisha/";

        /// <summary>**鐘楼 — 袴腰**(類型共用・寺4区画)。基壇 <paramref name="ken"/> 間角・
        /// 袴腰・上層は吹き放ち(柱間2間)・高欄・**梵鐘**・入母屋本瓦。
        /// 実寸(3間)**W 5.877 × H 6.942 × D 5.877**・面 3,028・底 0.000。
        /// 基壇 0.55 / 縁 2.60 / 桁 4.75 / 棟天端 6.94。
        ///
        /// <para>⛔ 在庫の `obj_shoro1` で代用しない — **ES 後 実丈 1.45m** の石造小物で、
        /// 101箇所に灯籠として据わっている駒(在庫方 2026-09-21)。拡大しても彫りが灯籠のまま。</para>
        ///
        /// <para>⚠ **材が2つ増える** — 梵鐘は Japanese Castle の `Ornament`(金具)、
        /// 基壇と縁石は `Kirishi`(山王の段石の切石)。remap のとき見落とさないこと。
        /// ⛔ `Foundation_A_01`(玉石積み)を基壇に当て直さない — 「小石を盛った台」に見える。</para>
        ///
        /// ピボット = **基壇の中心・地盤レベル**。⭕ 正面が無いので向きは自由。寸法は【U】。
        /// 生成: blender --background --python Tools/Blender/build_typ_jisha.py -- shoro</summary>
        public static string Shoro(float ken) { return JishaDir + "Typ_Shoro_" + Len2(ken) + "ken.fbx"; }

        /// <summary>**墓地の一画**(類型共用・寺3区画)。切石の低い囲い + **半間ピッチの墓石 59基**
        /// (角柱・櫛形・板碑の3型)+ 卒塔婆。実寸(6×4間)**W 10.908 × H 1.224 × D 7.272**・面 1,566。
        ///
        /// <para>⭐ **一画を一体で焼いてある** — 1基ずつ Unity 側で撒かない。撒き方は区画ごとに
        /// 変わらず、類型ビルダーは棟を置く器しか持たない。⇒ 寺ごとに向きだけ変えて据える。
        /// ⚠ 乱数の種を 1856 で固定してあるので、同じ寸法なら何度焼いても同じ並びになる。</para>
        ///
        /// <para>⚠ 材は **`Kirishi`**(切石)。⛔ `Foundation_A_01` に戻さない — 玉石積みの材なので
        /// 墓石が「小石を積んだ山」に見える(2026-09-21 に焼いて実見)。</para>
        ///
        /// ピボット = **一画の中心・地盤レベル**。⭕ 正面が無い。墓石の姿は【U】。
        /// 生成: blender --background --python Tools/Blender/build_typ_jisha.py -- bochi</summary>
        public static string Bochi(float wKen, float dKen)
        {
            return JishaDir + "Typ_Bochi_" + Len2(wKen) + "x" + Len2(dKen) + "ken.fbx";
        }

        /// <summary>**庫裏**(類型共用・寺と塔頭の台所兼住居)。平屋・**切妻の平入**・桟瓦・
        /// 下見板腰・妻に煙出し。桁行 <paramref name="wKen"/> 間 × 梁間 <paramref name="dKen"/> 間。
        /// 焼いてあるのは **6×4間** と **5×3.5間** の2寸法。
        ///
        /// <para>⛔ **<see cref="VK.SmallHouse"/> を庫裏に当て直さない** — 実測 14.49 × 10.49m で
        /// 本堂(7×6間)とほぼ同大になり、成満寺ほか狭い境内 3〜4 区画で収まらず未建に落ちた
        /// (在庫方 2026-09-22: これより小さい住居の完成駒は在庫に無い)。</para>
        ///
        /// <para>⭐ **躯体と屋根が別オブジェクト**(`<name>_body` / `<name>_yane`)。`_yane` は
        /// <c>EdoBuild.IsRoofName</c> の篩に掛かるので **<c>EdoBuild.Body(go, n, withRoof:false)</c> が
        /// 屋根を落とす** = 「軒は区画の線を越えてよい・壁体は内側」で測れる。
        /// けらば裏板と破風板も屋根の側に入れてある。</para>
        ///
        /// 実寸(6×4間): 屋根込 **W 11.768 × H 5.194 × D 9.264** / 壁体 **W 11.168 × H 4.834 × D 7.532**。
        /// 実寸(5×3.5間): 屋根込 **W 9.830 × H 4.736 × D 8.155** / 壁体 **W 9.350 × H 4.436 × D 6.623**。
        /// 軒桁 2.85 / 2.70、軒の出 0.90 / 0.80、けらば 0.36 / 0.30。
        ///
        /// <para>ローカル: 幅=X(桁行)/ 高さ=Y / 厚み=Z(梁間)、**+Z = 平入の正面**。
        /// ピボット = **足形の中心・床(地盤)レベル**・底 0.000。
        /// ⚠ **土間口(大戸)が Unity +X 寄りで左右非対称** — yaw で土間口の向きが変わる。</para>
        ///
        /// <para>⚠ 材は `wood` / `wall C` / `wall A` / `Foundation_A_01` / `roof` / `roof ornaments`。
        /// remap は **Edo ▸ 類型 ▸ 新造部材のマテリアルをremap**(`Models/Jisha` を見ている)。</para>
        ///
        /// 生成: blender --background --python Tools/Blender/build_typ_kuri.py -- [kuri6|kuri5] --render</summary>
        public static string Kuri(float wKen, float dKen)
        {
            return JishaDir + "Typ_Kuri_" + Len2(wKen) + "x" + Len2(dKen) + "ken.fbx";
        }

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
        /// 焼いてあるもの(Dobei = 練塀。腕は折れ点から ±2.26m・高さ 1.455m・s を掛けて据える。
        /// s=1.818 で据えれば片腕は世界で 4.10m):
        /// 00 00M 01 01M 06 07 08 08M 11 11M 14 14M 18 18M 19 31 38M 41 62 62M 88M 91 95 95M ／
        /// Ishigaki 31・31M ／ Tsuijibei 31 ／ Nagaya 38M。無い角度は:
        ///   blender --background --python Tools/Blender/build_kado.py -- --part dobei --deg &lt;符号つき角度&gt; --render
        ///
        /// ⚠ **+deg と −deg は互いの厳密な鏡像ではない。**素の練塀が厚み方向に非対称
        /// (表裏2枚組が 0.2m ずれる)なので、留め面を反転すると残る材が少し変わる
        /// (Δ=95 で 面 5278 対 4478・張り出し 0.56m 対 0.34m)。⭕ 折れの向きは正しく逆で、
        /// 躯体面はどちらも同じ側に残る — **据える側は符号だけ見ればよい**(2026-09-21 実測)。</summary>
        public static string Kado(string part, float deg)
        {
            return "Assets/Edo/Models/Kado/" + part + "_Kado_"
                 + UnityEngine.Mathf.RoundToInt(UnityEngine.Mathf.Abs(deg)).ToString("00") + (deg < 0f ? "M" : "") + ".fbx";
        }

        public const string MShop01     = "Assets/Edo/Materials/M_Shop01.mat";
        public const string MShop02     = "Assets/Edo/Materials/M_Shop02.mat";
        public const string MKido       = "Assets/Edo/Materials/M_Kido.mat";
        public const string MKidobanya  = "Assets/Edo/Materials/M_Kidobanya.mat";

        /// <summary>**山王社の段石の材**(`Danishi`)。切石の基壇 `Kirishi.mat` と**同じテクスチャ**
        /// (`T_Kirishi_Albedo` / `T_Kirishi_Normal`)で、`_BaseColor` の灰だけを 0.936 に落とした物。
        /// 受入値(庭方): H 25〜50° / S ≤ 12 / V 44〜54・平均 V 49±3。
        /// 実測(物差し = albedo × _BaseColor の sRGB 平均色の HSV。Kirishi の H36/S11.2/V52.4 と同じ測り方):
        /// **H 36.0 / S 11.2 / V 49.0**(V p10〜p90 45.5〜52.5)。線形合成で測っても H36.0/S11.3/V48.8。
        /// 【U 設計値】— 史料は石の色を言わない。2026-09-14 部材方。</summary>
        public const string MSannoDanishi = "Assets/Edo/Materials/Sanno/Danishi.mat";
        public const string MJishinban  = "Assets/Edo/Materials/M_Jishinban.mat";
        public const string MGateStone  = "Assets/Edo/Materials/GateStone.mat";
        // 自作マテリアルの名前引き(規則11: パスの literal はここ以外に書かない)
        public static string Mat(string name) { return "Assets/Edo/Materials/" + name + ".mat"; }

        /// <summary>**色だけの無地の材質**(URP/Lit)を置く場所。`EdoSolidMat.Get(Color)` が色ごとに 1 枚だけ起こす
        /// (EDO-0301)。⛔ コードで `new Material(...)` して資産にしないと、プレハブの m_Materials が null になり、
        /// そのプレハブを別の場所へ置くとマゼンタになる。</summary>
        public const string SolidMatDir = "Assets/Edo/Materials/Solid";
        public static string SolidMat(string hex) { return SolidMatDir + "/Solid_" + hex + ".mat"; }

        /// <summary>**コードで起こしたメッシュ**の置き場。`EdoSolidMesh.Save(mesh, 名)` が
        /// `&lt;名&gt;_&lt;中身の指紋&gt;.asset` で 1 枚だけ起こす(EDO-0332)。⛔ `new Mesh()` を
        /// そのまま `sharedMesh` へ入れると、プレハブの m_Mesh が null になり、そのプレハブを
        /// 別の場所へ置いた途端にその部材だけ消える。⛔ 手で作る資産はここへ置かない — 生成物だけ。</summary>
        public const string GenMeshDir = "Assets/Edo/Meshes/Gen";
        public static string GenMesh(string name) { return GenMeshDir + "/" + name + ".asset"; }

        /// <summary>松江松平邸の表門 — **屋根なしの冠木門**(角柱・冠木・内開きの板戸)。
        /// 姿は温古写真集11(88005761・明治初撮影)の実見【A】+『日本案内記 関東篇』昭和5年【A】。
        /// ⚠ 切妻小屋根を載せる前案は 2026-08-23 に撤回済み。**屋根なしが正**。
        /// 在庫の es_kmon は薬医門(小屋根あり)、es_kabukimon は柱高3.74mで指図の5.2mに足りない。
        /// ⭐⭐ **2026-09-08(指図 第28次)で袖塀をこの部材から外した。** 並びが
        /// 表長屋 → 袖塀 → 番所 → 門柱 → 門柱 → 番所 → 袖塀 → 表長屋 に改まり、
        /// **番所が門柱へ直付け**([松江上屋敷門写真]A)になったため。袖塀は <see cref="Sodebei(float,float)"/>。
        /// ⇒ **実寸が W13.12 → W5.20 に変わった**(D0.52 → D0.50 / H5.30 は不変)。
        /// 門そのものの寸法は動いていない: 門柱の外面どうし **4.50**(= 指図 gate.plan.monW)/
        /// 内法 **3.66**(柱 0.42 角 ×2)/ 柱高 **5.20**(+銅冠 0.10)/ 冠木の出 0.35×2。
        /// ⚠ **躯体が両開きの板戸(内法 3.66・丈 4.45)を持っている。**指図 `gate.plan.leaf._` は
        /// 「躯体が扉を持たないので別部材の扉を据える」と書いていて食い違う — Stage5_Mon の
        /// `Leaves(...)` と二重になっていないか据えたときに確かめること(2026-09-08 部材方)。
        /// **ピボット = 門の芯・敷居レベル**なので gate.pos と gate.sill をそのまま使える。
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_omotemon.py -- [--render]</summary>
        public const string MatsudairaOmotemon = "Assets/Edo/Models/Mon/Matsudaira_Omotemon.fbx";

        /// <summary>**袖塀**(長さ可変・潜り戸つき)— 表門の脇で外周を塞ぐ練塀。
        /// 断面は外周の練塀(`Tools/Blender/build_dobei.py` = `Assets/Edo/Models/Dobei/Dobei2m.fbx`)と
        /// 同じ生成器から起こす:下見板の腰 → 貫 → 白漆喰 → **本瓦の両流れ**
        /// (キットの実ジオメトリ)→ 熨斗の大棟。両端は**袖瓦**で塞ぐ(⛔ 木の破風は付かない)。
        /// 全高 **2.65**(= 指図 const.dobeiH)/ 屋根の総幅(厚み)**1.00** / 壁の厚み 0.36。
        ///
        /// ⭐ **ピボット = 走りの起点(ローカル x=0)の小口面・厚みの芯・地盤レベル。**
        /// ⛔ 中心ピボットではない(CLAUDE.md 規則5 — 据える側は**面**で寄せる)。
        /// ⇒ x=0 の小口を番所の外側の妻面へ突き付ければ、反対の小口が x=len に来る。
        /// ローカル +X = 走り / +Y = 高さ / +Z・−Z = 厚み(表裏は同じ作り)。scale = Vector3.one。
        ///
        /// 引数: <paramref name="len"/> = 走りの実長[m](指図 gate.plan.sPos.sodeW / sodeE の**従属値**)。
        /// <paramref name="kuguri"/> = **潜り戸の中心**を走りの起点から測った距離[m]。負なら潜り戸なし。
        /// 潜り戸は幅 **0.95** × 有効高 **1.85**(従前の一体部材の実測をそのまま運んだ値)の**一枚戸**。
        /// ⭕ **焼いてあるのは `Sodebei_5.5.fbx`(潜り戸なし)** — 長さは指図 第29次の
        /// `gate.plan.sPos.sodeW`/`sodeE`(111.8‥117.3 / 130.3‥135.8)の従属値 5.5m。
        /// ⚠ 4.25 の 2 本(`Sodebei_4.25` / `Sodebei_4.25_K2.13`)は第28次の仮値で**もう使わない**。
        /// ⛔ **潜り戸つきは焼いていない** — 走りのどこに開くかも、西・東どちらの袖に付くかも
        /// 指図が持っていない【U】(`_pending.omotemonSodeKuguri`)。⛔ 部材方は発明しない。
        /// ⇒ 指図が中心を持ったら `--kuguri &lt;中心m&gt;` で焼き足す。
        /// 生成: blender --background --python Tools/Blender/build_sodebei.py -- &lt;長さm&gt; [--kuguri &lt;中心m&gt;] [--render]</summary>
        public static string Sodebei(float len, float kuguri = -1f)
        {
            string s = "Assets/Edo/Models/Hei/Sodebei_" + len.ToString("0.##");
            if (kuguri >= 0f) s += "_K" + kuguri.ToString("0.##");
            return s + ".fbx";
        }

        /// <summary>**練塀(築地塀)の一体物** — 腰の下見板・貫・白漆喰・本瓦の両流れが1駒に焼いてある
        /// (`Tools/Blender/build_dobei.py`)。EDO-0351: 在庫方の照会は「練塀は在庫に無く板塀
        /// `EdoAssets.Eg.DobeiCenter` が兼ねている」としたが誤りで、**この部材が在る** — `FenceRun` の
        /// dobei 枝が結線し忘れて板塀へ落ちていただけ(EDO-0318 ⑤ の訂正)。
        /// ローカル: 走り +X ∈ [0, 2.004]・高さ +Y・厚み Z(芯 0 を挟んで左右対称・**表裏の別なし**)。
        /// ⭐ **真の m で作ってあり scale=1 で置く**(edogoyomi の ES も Village Kit の vklib.S も掛けない)。
        /// ⚠ 単体は両小口とも開放(隣の駒を継ぐ前提の断面)。**妻を塞いだ自由端**は <see cref="Dobei2mEnd"/>。
        /// ⛔ 隅の留め継ぎは未対応(塀の Kado 統合はまだ無い — `kado-mitre-parts.md`「塀と長屋は未解決」)。
        /// 生成: blender --background --python Tools/Blender/build_dobei.py -- [--render]</summary>
        public const string Dobei2m = "Assets/Edo/Models/Dobei/Dobei2m.fbx";

        /// <summary><see cref="Dobei2m"/> の**妻を塞いだ端部**(x=0 側の小口に袖瓦を葺いて閉じた駒。
        /// build_dobei.py の gable='L')。塀が行き止まる自由端(門の脇など)に使う — 開放小口のまま
        /// 置くと軒裏の三角の空隙が見える。走りの**高位側**を閉じたいときは 180°回して継ぐ
        /// (`ButtOnRun` は実メッシュを測って突き付けるので、鏡像でなく回転で足りる)。
        /// 生成: build_dobei.py の main() が Dobei2m と同時に書き出す(引数なし)。</summary>
        public const string Dobei2mEnd = "Assets/Edo/Models/Dobei/Dobei2m_End.fbx";

        /// <summary>松江松平邸の表門の番所 — **向唐破風・出格子・切石畳出の基壇**。左右に2棟。
        /// 姿は温古写真集11【A】+『日本案内記 関東篇』昭和5年「両側に唐破風造の番所」【A】。
        /// 在庫の es_dbansho(3.6×2.1m)は規模も意匠も不足。指図 gate.plan.bansho は 5.5×3.6m・張出2.0m。
        /// ⚠ 唐破風は**中央が起り・両端が照りで反り上がる S 字**。単純な sin にすると樽屋根になる。
        /// ⚠ 出格子は**細い竪子を密に**。太い方立を疎に並べると牢格子に見える。
        /// **ピボット = 走り方向の芯・基壇の下端**。
        ///
        /// <para>⚠⚠ **<paramref name="w"/> は「躯体」の幅であって外形ではない**(2026-09-09 実測)。
        /// 指図の継ぎ目 <c>J_Bansho_W/E</c> / <c>J_Sode_W/E</c> は当てる面を
        /// **「番所躯体の東端/西端」**と名指ししているので、<c>gate.plan.bansho.w</c> は躯体。
        /// **メッシュの走り方向の実寸は 躯体 + 0.40m**(切石基壇が +X 側へ 0.18 /
        /// 側面の出格子が −X 側へ 0.22 出る)= w 4.25 のとき **4.65m**。
        /// ⛔ **`Renderer.bounds` の投影幅を <c>w</c> と直に比べない** — 必ず 0.40m 過大に出る。
        /// 実装側の検査は躯体の面で測ること(2026-09-09 に部材方から実装へ申し送り)。</para>
        ///
        /// <para>⚠ **w は 2026-09-08(第29次)に 5.5 → 4.25 へ詰まった**
        /// ((`plan.opening.w` 13.0 − `plan.monW` 4.5) ÷ 2 の従属値)。旧寸の
        /// `Matsudaira_Bansho.fbx`(躯体 5.5・メッシュ 5.90)は 2026-09-09 に**削除した** —
        /// ⛔ 寸法の入らない名で焼くと旧寸が居座って実装が気づけない。
        /// 実寸(Unity・w=4.25)**4.650(X) × 4.660(Y) × 4.700(Z)**。
        /// 向唐破風の起り = 弦(桁行)の 1/7 = 0.607m(**幅からの従属値**)、
        /// 出格子の竪子は芯々 0.209m 固定で本数が従属(⛔ 本数を固定して幅だけ縮めない)。</para>
        /// 生成: blender --background --python Tools/Blender/build_matsudaira_bansho.py -- --w 4.25 --render</summary>
        public static string MatsudairaBansho(float w)
        {
            return MonDir + "Matsudaira_Bansho_W"
                 + w.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ".fbx";
        }

        /// <summary>⭐⭐ **番所の「躯体」を測るための帯** — ピボット(= 走りの芯・**基壇の下端**)からの
        /// 局所 y[m]。⇒ 世界では <c>[敷居 + 0.60, 敷居 + 1.30]</c>。
        ///
        /// <para>⛔⛔ **番所の走り方向の実寸を、外接や全メッシュの最大投影で測らない**(2026-09-09 の裁定)。
        /// 部材は恒久的に **躯体 + 0.40m**(切石基壇が +X へ 0.18 / 側面の出格子が −X へ 0.22)で焼けるので、
        /// 全頂点を走ると必ず 0.40m 過大に出る。指図の継ぎ目 <c>J_Bansho_*</c> / <c>J_Sode_*</c> が
        /// 名指ししている面は**躯体の東端/西端**なので、検査もこの帯の頂点だけで測る
        /// (CLAUDE.md 規則5「指図が名指しした面を測って寄せる」)。</para>
        ///
        /// <para>⛔⛔ **帯は「面の途中」でなく『頂点のある高さ』に取る**(2026-09-09 に実際に踏んだ)。
        /// 部材は箱の集まりなので、**壁面の頂点は箱の上下の縁にしか無い**。
        /// 腰壁(0.55‥1.40)の *途中* に 0.60‥1.30 の帯を取ったら**頂点が 1 つも入らず**、
        /// 検査が「躯体が測れない」と鳴った。⇒ 採るのは **基壇の天端 = 腰壁の底 0.55**。</para>
        ///
        /// <para>⭐ **帯だけでは足りない — 奥行の窓と併せて使う。**y=0.55 には
        /// 腰壁の底(走り ±w/2・奥行 ±d/2)と**基壇の天端**(走り ±(w/2+0.18)・奥行 ±(d/2+0.18))が
        /// 同居する。⇒ **奥行 |perp| ≤ d/2 + 0.05** で基壇を外す(出格子と桁はこの高さに無い)。
        /// 実測(w=4.25): この窓で頂点 12 点・走り **4.250m**(= 指図の `w` ちょうど)。</para>
        ///
        /// <para>帯の根拠(<c>Tools/Blender/build_matsudaira_bansho.py</c> の実寸):
        /// 基壇 <c>BASE_H</c> 0.55 / 腰壁 <c>KOSHI_H</c> 0.85(0.55‥1.40)/ 出格子の受け 1.38 から上 /
        /// 桁 3.00 から上。</para></summary>
        public static readonly float[] MatsudairaBanshoBodyBand = { 0.50f, 0.60f };

        /// <summary>**板塀の根石(玉石)** — 松江松平邸の中仕切の板塀 8 run(延長 444.2m・約 800 石)。
        /// 指図 <c>nakajikiriRule.neishi</c> が正典: 見え <c>show</c> 0.15〜0.20m /
        /// 埋まり比 <c>bury</c> 0.5 ⇒ **丈 = 2×見え**(0.30〜0.40m)/ 全厚 <c>t</c> 0.35m /
        /// 一石の走り <c>long</c> 0.40〜0.70m の**乱尺**。
        ///
        /// <para>⭐⭐ **ピボット = 走りの芯・厚みの芯・座(地盤線)**。ローカル **+X = 塀の走り** /
        /// **+Y = 上**(Y=0 が地盤線。メッシュは −見え 〜 +見えの対称)/ **+Z = 厚み**。
        /// ⇒ <c>neishi_seat_check</c> が柱間ごとに決めた**座**をそのまま <c>position.y</c> へ。
        /// ⛔ 底でも天端でもない。</para>
        ///
        /// <para>⚠⚠ **芯々を外接寸法で詰めない** — 玉石は丸いので **地盤線での差し渡しは外接の 85〜100%**
        /// (2026-09-13 焼き直し後の実測: L0.41→0.397 / L0.45→0.424 / L0.5→0.467 / L0.54→0.539 /
        /// L0.58→0.528 / L0.62→0.528 / L0.66→0.622 / L0.7→0.637)。外接どうしを突き付けると**地盤線の高さで
        /// 石のあいだに空が抜ける**。⇒ 芯々は「地盤線の差し渡し」で詰めること。</para>
        ///
        /// <para>⭐ **8個体を乱尺で焼いてある**(下の <see cref="NeishiLong"/>)。土台は在庫の実肌の小石
        /// <c>s_rock_01..06_LOD0</c>(NatureManufacture)を 6 種回してあるので、
        /// **柄(アトラスの領域)もシルエットも個体差がある**。
        /// 繰り返しがまだ目につくなら据える側で **yaw 180° の反転**を混ぜること(⛔ 部材を増やす前に)。</para>
        ///
        /// <para>⛔⛔ **2026-09-10 の差し戻し3**(普請検査「厚み数 cm の黒い三日月にしか見えない /
        /// 黒く角張っていて河原石に見えない」)で **土台と材を入れ替えた**。
        /// ⛔ 従前は Waldemarst の**庭石** <c>FJG_Rock_A_0{1,2,3}</c>(1.25〜1.99m)を 0.5m 級へ
        /// 大きく縮め、材は <c>M_FJG_Rock_001</c>(= <c>T_FJG_Rock_Dark_001_Albedo</c>。
        /// 名のとおり **Dark**。テクスチャ実測 **V14.9% / 粒 14.2**)だった。
        /// ⭕ いまは <c>M_photoscanned_rocks_01</c>(**V40.8% / 粒 9.1** = 明るく肌理が細かい。
        /// ⛔ 新規マテリアルではなく在庫の .mat)で、土台も**元から根石の寸法**の小石なので
        /// 縮尺による丸みの痩せを原理的に踏まない。
        /// 丸みは実測 — 凸の稜の局所半径の下位5%が **0.040〜0.060m**
        /// (従前 0.020〜0.045。ユーザー指摘「角が鋭すぎませんか?」2026-09-06 の帯 2〜6cm の上半分)。
        /// 面数は 407〜855(従前 284)。</para>
        ///
        /// <para>⭐ **見え高 = 地盤線の差し渡し × 指図 <c>showMul</c>(0.45)/ 丈 = 2 × 見え**(<c>bury</c> 0.5)。
        /// 2026-09-13 に焼き直し、生成器が丈を収束させる(全個体 1 巡・|Δ丈| ≤ 0.001)。
        /// 見え高 / 丈 [m]: L0.41 0.179/0.357 ・ L0.45 0.191/0.382 ・ L0.5 0.210/0.420 ・ L0.54 0.243/0.485 ・
        /// L0.58 0.238/0.475 ・ L0.62 0.238/0.476 ・ L0.66 0.280/0.561 ・ L0.7 0.286/0.572。
        /// ⚠ 指図に <c>show</c> キーはもう無い(従属値)。</para>
        /// 生成: blender --background --python Tools/Blender/build_neishi.py -- all --render</summary>
        public static readonly float[] NeishiLong =
            { 0.41f, 0.45f, 0.50f, 0.54f, 0.58f, 0.62f, 0.66f, 0.70f };
        public static string Neishi(float lng)
        {
            return NiwaDir + "Neishi_Tamaishi_L"
                 + lng.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ".fbx";
        }

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
            public const string InariHokora = FuzokuyaDir + "Matsudaira_Inari_Hokora.fbx";
            /// <summary>**生成メッシュの保存先**(参道の玉砂利の帯など、指図の折れ線から起こす面)。
            /// ⚠ ランタイム生成の Mesh は**アセットに保存しないとシーン保存で消える**ので、
            /// ビルダーは `AssetDatabase.CreateAsset` でここへ焼く(再実行は CopySerialized で上書き)。</summary>
            public const string GenMeshDir = "Assets/Edo/Models/Niwa/Generated/";
            /// <summary>石井戸枠+釣瓶の桁。実寸 1.90 × 2.21 × 1.90。**枠の天端は地盤+0.72**</summary>
            public const string Ido    = FuzokuyaDir + "Matsudaira_Ido.fbx";
            /// <summary>二重の隅櫓 3間角。実寸 7.39 × 8.64 × 7.39。据えは石垣の天端</summary>
            public const string Yagura = FuzokuyaDir + "Matsudaira_SumiYagura.fbx";
        }
        const string FuzokuyaDir = "Assets/Edo/Models/Fuzokuya/";

        /// <summary>**類型共用の附属屋**(邸を問わず `EdoTypologyBuilder` が 88 区画で使う3点)。
        /// EDO-0304 案A ①(2026-09-21 施主裁定)— 三べ坂で類型版が薄く見えたのは棟数ではなく
        /// **附属の種別が消えた**ためで、汎用在庫は土蔵 <see cref="Eg.Kura"/> 1点しか無かった。
        ///
        /// <para>⛔ **邸ごとの手組み(`Doi_*` / `Okabe_*` / `Matsudaira_*`)をここへ転用しない。**
        /// あちらは指図の間数どおりの一品物で、類型の中〜小の筆には入らない(在庫方の判定)。
        /// ⭕ 逆に、類型の邸で指図が起きたら専用部材へ置き換える — ここは**当てが無いときの既定**。</para>
        ///
        /// <para>【寸法は部材方が決めた・確度 U】柱間は整数間。足形は3点とも
        /// <see cref="Eg.Kura"/>(ES 後 6.23 × 6.51 × 6.64)と同じ桁に収めてあり、
        /// **半対角は順に 5.46 / 5.35 / 3.84m** — `EdoTypologyBuilder.Plan()` が蔵に与える
        /// 離隔半径 6m のまま置ける。⛔ これより大きくしない。</para>
        ///
        /// <para>【向きとピボット】幅=X(**長手 = 棟の走る向き**)/ 高さ=Y / 厚み=Z。
        /// ピボット = **footprint の中心・地盤レベル**(3点とも)。
        /// ⚠ 厩と作事小屋は **+Z が開口面**なので、据えるとき +Z を郭の内へ向けること。</para>
        ///
        /// 作り直し: `blender --background --python Tools/Blender/build_typ_fuzokuya.py -- [名] [--render]`
        /// (名 = komegura / umaya / sakuji。省くと全部。`-- narabe` は `Eg.Kura` との並べ比べ)</summary>
        public static class Typ
        {
            /// <summary>**米蔵** 3間(梁間)× 4間(桁行)。石腰+白漆喰の大壁・妻に観音扉・**切妻の本瓦**。
            /// 実寸 **8.310(X) × 7.227(Y) × 7.071(Z)**・面 2,286。軒の下端 5.20 / 棟 7.23。
            ///
            /// <para>⭕ **<see cref="Eg.Kura"/>(汎用の土蔵)と並べて見分けが付く**ことが在庫方の出した
            /// 合否条件で、四つで分けてある: ① 丈が **+0.72m 高い** ② 妻の小窓を **0.51m 角**へ縮めた
            /// (土蔵は 0.92m 角)③ 足形が 1.18:1 の長手のある矩形(`Eg.Kura` は 1.07:1 のほぼ正方)
            /// ④ 長手の大壁に **風抜きの高窓を3口ずつ**。
            /// ⚠ ④は 2026-09-21 に実際に並べて焼いて足した — ①〜③だけでは長手が 7.3 × 3.1m の
            /// 一面の白になり「意匠の無い箱」に見えた(`Eg.Kura` は妻に窓・扉・庇・棟飾りが付く)。</para>
            ///
            /// <para>⚠ **棟高は指定できない従属値。**瓦の勾配 0.5456 は動かせないので
            /// 棟 = 軒 + (梁間/2 + 0.75) × 0.5456。丈を変えたければ軒を動かすこと。
            /// ⚠ **観音扉は −X の妻**、小窓は +X の妻。据えるときの yaw が扉の向きを決める。</para>
            ///
            /// 材 = `Fence_B_01` / `Foundation_A_01` / `Wall Exterior Defence` / `roof` /
            /// `roof ornaments` / `wall C` / `wood`(すべてキット由来)。
            /// 生成: blender --background --python Tools/Blender/build_typ_fuzokuya.py -- komegura --render</summary>
            public const string Komegura = FuzokuyaDir + "Typ_Komegura.fbx";

            /// <summary>**厩** 3間(梁間)× 4間(桁行)。板壁・桟瓦・**前面(+Z)は吹き放ち**で
            /// 足元に半高の板壁、馬房を4つ(桁行4間なので1房ちょうど1間)。
            /// 実寸 **8.052(X) × 4.378(Y) × 7.046(Z)**・面 5,037。軒 2.55 / 棟 4.04。
            ///
            /// <para>⛔⛔ **軒高だけを下げない。**吹き放ちの帯 = 軒 − 軒の出×0.5456 − (半高壁+0.09) で、
            /// 軒を下げると帯が鼻隠しに隠れて **「大屋根の物置」**になる(2026-09-06 に岡部で実見)。
            /// いまの 2.55 / 半高壁 1.15 / 軒の出 0.70 で **帯 0.928m**(岡部の 0.95 と同等)。
            /// ⚠ 軒 2.55 は「棟 4.04 を主屋より低く納める」ための逆算値で、独立した根拠ではない。</para>
            ///
            /// <para>⚠ **+Z が開口面**。据えるときは郭の内側(区画の境界と反対)へ +Z を向ける —
            /// 境界側へ開けると隣家へ向いて馬房が開くことになる。</para>
            ///
            /// 材 = `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`。
            /// 生成: blender --background --python Tools/Blender/build_typ_fuzokuya.py -- umaya --render</summary>
            public const string Umaya = FuzokuyaDir + "Typ_Umaya.fbx";

            /// <summary>**作事小屋** 2間(梁間)× 3間(桁行)。四周板壁・**板葺(4寸)**・
            /// 前面(+Z)に両開きの板戸 1.30m。実寸 **6.054(X) × 3.537(Y) × 4.736(Z)**・面 2,664。
            /// 軒 2.45 / 棟 3.40(棟押えの天端 3.54)。
            ///
            /// <para>⛔ **瓦を葺いていない** — `roof 2x2` の勾配は 0.5456 固定で、2間の梁間でも
            /// 作事の小屋には棟が立ち過ぎる(岡部の納戸小屋と同じ判断)。板葺なので勾配は選べる。
            /// ⭕ その結果 **附属3点の丈が 7.23 / 4.38 / 3.54 と段になり**、遠目にも作り分けが読める。</para>
            ///
            /// <para>⚠ 納戸小屋(1.5×1間・片開き 0.82m)との違いは**大きさと戸**だけで、型は同じ。
            /// ⚠ **+Z が板戸のある面**。姿は【確度 U】。</para>
            ///
            /// 材 = `wood` / `wall C` / `Foundation_A_01` / `wall A`(瓦が無いので4種)。
            /// 生成: blender --background --python Tools/Blender/build_typ_fuzokuya.py -- sakuji --render</summary>
            public const string SakujiKoya = FuzokuyaDir + "Typ_SakujiKoya.fbx";

        const string KakoiDir = "Assets/Edo/Models/Kakoi/";

            /// <summary>**竹矢来(たけやらい)**— 2間モジュールの**透ける囲い**(類型共用・EDO-0363)。
            /// 実寸 **3.636(X) × 2.000(Y) × 0.212(Z)**・面 660・頂点 2,640・材は `Bamboo garden fence` 1種。
            ///
            /// <para>⭐ **意匠の要は「透け」。**見付の充実率 **30.4%**(= 69.6% が抜け・光線で実測)で、
            /// 板塀・穂垣(どちらも 100%)と **20m 離れても取り違えようがない**。
            /// ⛔ 2026-09-22 まで囲い種別 `yarai` は <see cref="Eg.Hogaki5"/>(穂垣)で代用しており、
            /// 「濃い板の連続にしか見えない」と在庫方が差し戻した — 丈ではなく**姿**が問題だった。</para>
            ///
            /// <para>⛔⛔ **<see cref="EdoBuild.PanelRun"/> の既定(表裏の対)で置かない。**
            /// 穂垣・板塀は**片面ポリゴン**なので表裏2枚で1枚の塀になるが、これは**実ジオメトリの
            /// 両面もの**。2枚置くと格子が 0.12m ずれて二重になり、**透けが潰れて藪に見える**。
            /// ⛔ **ES 倍しない** — `Eg.*` の obj と違い、これは自前で焼いた**実寸**の FBX。
            /// ⭕ 1スパン1枚・伸縮は走りだけ(`Vector3(sx, 1f, 1f)`)。</para>
            ///
            /// <para>【組み方】竹の丸材を 45° の筋違に **0.606m(1間の1/3)ピッチ**で表裏へ渡し、
            /// 胴縁2段(高さ 0.34 / 1.84)で挟んで縄で結ぶ。**親柱は x = ±0.909(各1間の中心)**なので、
            /// モジュールを突き付けると柱が **1.818m 等間隔**で通り、継ぎ目に柱が重ならない。
            /// 幅 3.636 = 0.606 × 6 ちょうどなので**格子も継ぎ目を跨いで通る**。
            /// ⚠ **端に柱が無い** — run の両端と隅には 0.909m ぶん柱無しの格子が残る。</para>
            ///
            /// <para>【ピボット】走りの中心・足元・柱の芯(FBX ノードの平行移動は 0)。丈 2.000 のうち
            /// **0.10 を土へ入れる**前提(`PanelRun` の `SeatBottom(baseY - 0.10f)`)なので **実丈 1.90m**。</para>
            ///
            /// 生成: blender --background --python Tools/Blender/build_typ_yarai.py -- --render
            /// (`-- narabe` は穂垣との 20m 並べ比べ。書き出さない)</summary>
            public const string Takeyarai = KakoiDir + "Typ_Takeyarai_2ken.fbx";

        const string MachiyaDir = "Assets/Edo/Models/Machiya/";

        /// <summary>**表店(おもてだな)**— 町屋24町の通りに面して並ぶ2階建ての商家(類型共用)。
        /// 桁行 <paramref name="wKen"/> 間・奥行 4間相当(7.272m)・**厨子二階**・見世棚つき。
        ///
        /// <para>⭐ 在庫の <see cref="Eg.Shop01"/>(軒幅 4.93m)/ <see cref="Eg.Shop02"/>(7.13m)では
        /// 表の `maguchi_ken` 5間(9.09m)を **1枚で埋められなかった**(Shop01×2 = 9.86m で +0.77m)。
        /// これは **軒の端から端が 9.090m ちょうど** — `EdoBuild.ShopMeasure` が測る幅
        /// (<see cref="EdoBuild.ShopModule.W"/> = 軒込み)がそのまま表の 5間に一致する。</para>
        ///
        /// <para>実寸 **W 9.090(X) × H 4.284(Y) × D 7.272(Z)**・面 7,858・底 0.000。
        /// 立面は Shop01 に合わせてある: 1階庇の先端 **1.73** / 頂 **2.361** / 2階の窓 **2.40〜2.87** /
        /// 2階の軒先 **3.35** / 瓦面の大棟 **4.050** / **棟天端 4.240**(Shop01 は 4.236)/
        /// けらば **0.11**。⇒ 同じ列へ軒を接して継いでも屋根がめり込まず、棟の段も出ない。
        /// ⚠ bbox の丈 4.284 は袖瓦の上端で、棟天端そのものの差は +0.004。</para>
        ///
        /// <para>⚠ **柱間は 1.750m(0.96間)**。桁行 5間 = 9.09 は**軒の端から端**で取ってあり、
        /// 柱通りはそこから軒の出(0.17×2)を引いた内側。⛔ 柱間を 1.818 固定にすると
        /// 軒幅が 9.45 になって表の 5間 と 0.36m ずれる。</para>
        ///
        /// <para>⚠ **段違いの2棟**(表屋 = 厨子二階 / 奥 = 平屋)。4間の奥行を1枚の切妻で架けると
        /// 瓦の勾配 0.5456 では棟天端が 5.4m まで上がり Shop01 より 1.2m 高くなるため。
        /// 奥棟の棟天端 3.279 / 谷 2.235。奥行は <see cref="Omotedana(float,float)"/> で詰められる
        /// (**奥棟だけが縮み、表の立面は一切動かない**。実用の下限は 6.30m = 奥が約1間)。</para>
        ///
        /// <para>ローカル **+X = 桁行(通りに沿う)/ +Z = 通り(店先)**。ピボット = **足形の中心・地盤レベル**。
        /// ⚠ **大戸口(出入口)は −X 寄りの1間**、残り4間が見世(格子+見世棚)。左右非対称なので
        /// yaw で大戸口の位置が変わる。⚠ 軒は足形の外へ ±X に 0.17 出る(ピボットには含まれない)。</para>
        ///
        /// 材 = `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments` /
        /// **`Noren 2`**(キットの藍の暖簾。⚠ 色は .mat が乗せるので remap 必須)。
        /// 生成: blender --background --python Tools/Blender/build_typ_machiya.py -- --render</summary>
        public static string Omotedana(float wKen)
        {
            return MachiyaDir + "Typ_Omotedana_" + Len2(wKen) + "ken.fbx";
        }

        /// <summary>**奥行を詰めた表店。**背後の余地が 4間(7.272m)に足りない筆で使う。
        /// ⭐ 縮むのは**奥棟だけ**で、店先の立面・軒先 3.35・棟天端 4.240・けらば 0.11 は動かない。
        /// 焼いてあるのは **5×3.85間(D 7.000m・面 7,776)**。実用の下限は **D 6.30**(奥が約1間)。
        /// ⛔ 4間より深くしない — 奥棟の棟天端が表屋の軒桁 3.465 へ迫る(生成器が ⚠ を刷る)。
        /// 無い寸法は
        /// blender --background --python Tools/Blender/build_typ_machiya.py -- --ken &lt;桁行間&gt; --okuyuki &lt;奥行m&gt;
        /// で足す。</summary>
        public static string Omotedana(float wKen, float dKen)
        {
            return MachiyaDir + "Typ_Omotedana_" + Len2(wKen) + "x" + Len2(dKen) + "ken.fbx";
        }
        }

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
        /// 同じ — `Ishigumi`/`Tobiishi`/`Kutsunugi` のコメント参照)。
        /// 【2026-09-06 ユーザー裁定1=案②(護岸と同じ材)】護岸の転石(<see cref="JG.Rock01"/> 系列の実体
        /// `JG_Rock_A_01..03.prefab`)と材を揃えるため、`M_photoscanned_rocks_01`(旧)から
        /// <b>`M_FJG_Rock_001`</b>(`Assets/Waldemarst/FreeJapaneseGarden/Materials/Misc/
        /// M_FJG_Rock_001.mat`。護岸の転石が実際に使う .mat)へ材質名を切り替えた。
        /// ⭕ 問題は元から「FBX 内の材質名が `Test`」だったことで、.mat 自体は実在する —
        /// FBX 側の材質名を最初から `M_FJG_Rock_001` にして書き出せば Search&amp;Remap は
        /// 当たる(`build_tateishi._borrow_rock_material` は `vklib.named_material` で
        /// 名前だけの入れ物を作る。FBX 由来では**借りない**)。UV は実測すると
        /// `M_FJG_Rock_001` のテクスチャも「個体ごとの矩形アイランド」アトラスだったので
        /// (`FJG_Rock_A_01..03` がそれぞれ別の象限を専有)、矩形選定+密度実測(0.32 uv/m)を
        /// やり直した(旧 0.30 uv/m から微修正)。新規マテリアルは作っていない。</para>
        ///
        /// <para>LOD1 を同梱(Decimate 40%・約500三角)。Unity 側は `Tateishi_&lt;size&gt;_&lt;variant&gt;_LOD0`/`_LOD1`
        /// の命名から自動で LODGroup を作る(README の命名規則どおり。ただしこのビルドで
        /// 初めて使うので、Unity 取り込み後に LODGroup が実際に立つか確認すること)。</para>
        /// 生成: blender --background --python Tools/Blender/build_tateishi.py -- all --render</summary>
        public static string Tateishi(string size, int variant)
        { return NiwaDir + "Tateishi_" + size + "_" + variant + ".fbx"; }

        /// <summary>**大型の平石2種**(天井石・伏石)。松江松平上屋敷の庭向け。
        /// ユーザー裁定2=案①(新造)(2026-09-06)。在庫の丸い転石(`JG.Rock01..03`)には
        /// 「架ける/伏せる」扁平な大型石が無いため新造。材質は立石と同じ
        /// `M_FJG_Rock_001`(裁定1=案②(護岸と同じ材) と揃えた石材)。
        ///
        /// <para>⚠⚠ **2026-09-06 三度目の差し戻しで作り方を全面変更した。**
        /// 当初は bmesh の輪切りロフト(手続き生成)で作っていたが、5回のUV差し戻しの後も
        /// 天端が cos(2θ)の鞍型に凹む・胴に継ぎ目線が一周見える、という「パラメトリックな
        /// 輪切り」特有の人工物が抜けなかった。⭕ **在庫の転石メッシュ
        /// `JG_Rock_A_03_LOD0.fbx`(実肌・`M_FJG_Rock_001` のアトラスUVを個体ごとの
        /// 矩形アイランドとして既に持つ)を土台に、変形だけで目標寸法へ持っていく**方式に
        /// 切り替えた。UV・トポロジーは無傷(スケール・非一様な低周波伸長は頂点位置しか
        /// 動かさないので、在庫メッシュのアトラスUVはそのまま正しく貼られる)。
        /// ⚠ 素の FBX 取り込みは「置いた姿」ではない — `JG_Rock_A_03.prefab` の Transform
        /// は回転・一様スケール0.5込みで扁平に見えるよう置いている。Blenderの取り込み軸は
        /// Unityと同一ではないので、**姿を実見して**Blender側でX軸+90°回すのが正しいと
        /// 確認した(build_hiraishi.py._load_donor 参照)。</para>
        ///
        /// <para>実寸(Unity座標) W(X)×H(Y)×D(Z)、ピボット = <b>底面中央</b>:
        /// <list type="bullet">
        /// <item><paramref name="kind"/> = <b>"Tenjo"</b>(天井石)… 1.050 × 0.450 × 0.550。
        /// 岩屋の脇石2本の上に<b>架ける</b>水平な梁石。</item>
        /// <item><paramref name="kind"/> = <b>"Fuse"</b>(伏石)… 1.200 × <b>0.280</b> × 0.850。
        /// 築山の裾に<b>伏せる</b>扁平な転石。⚠ H は当初 0.42 だったが、庭方裁定
        /// 「伏せる石は埋め0」で見え丈がそのまま全丈になり 0.28 へ変更(2026-09-06)。</item>
        /// </list>
        /// 各 variant 1 個体のみ(裁定どおり)。軸ごとの直接スケールは 1.25倍まで、
        /// 超える軸(Fuse の W・D)だけ低周波の非一様な追加伸長(閉じた式
        /// `T(t)=t+1.5(k-1)(t-t³/3)`。Lattice/Proportional Edit 相当)で補う。</para>
        /// 生成: blender --background --python Tools/Blender/build_hiraishi.py -- Tenjo Fuse --render</summary>
        public static string Hiraishi(string kind)
        { return NiwaDir + "Hiraishi_" + kind + "_1.fbx"; }

        /// <summary>**切石橋**(切石の一枚物の橋)。松江松平上屋敷の庭向け。
        /// ユーザー裁定2=案①(新造)(2026-09-06)。<see cref="Hiraishi"/> と違い**加工石**なので
        /// bmesh のロフトではなく箱(bmesh box)+全辺 1〜2cm の面取りで作る — 自然石の
        /// 割れ肌ノイズは掛けず、上面・下面・小口は完全な平面のまま、側面・小口の
        /// 法線がほぼ水平な頂点だけに矢穴跡程度の弱いノイズ(振幅4mm)を乗せた。
        /// 材質は <see cref="Hiraishi"/> / <see cref="Tateishi"/> と同じ `M_FJG_Rock_001`。
        ///
        /// <para>実寸(Unity座標) W(X)×H(Y)×D(Z) = <b>2.200 × 0.250 × 0.900</b>、
        /// ピボット = 底面中央。variant 1 個体のみ。</para>
        /// 生成: blender --background --python Tools/Blender/build_hiraishi.py -- Ishibashi --render</summary>
        public static string Ishibashi() { return NiwaDir + "Ishibashi_Kiri_1.fbx"; }

        /// <summary>刈込の生垣モジュール(ツゲ・マサキの見立て・1 間 × 1.90m × 0.80m、葉カード・材 M_FJG_Plant_Boxwood_01_Spring・LOD1)。
        /// <c>end</c> は小口が葉で閉じた端部(+X が突き付け面)。ピボットは 1 間の中心・床レベル、前後対称。
        /// 実寸(葉の持ち出し込み)1.908×2.02×1.09。Blender: <c>blender --background --python Tools/Blender/build_ikegaki.py</c>(2026-09-06 部材方)。</summary>
        public static string Ikegaki(bool end)
        { return NiwaDir + (end ? "Ikegaki_End_1.818.fbx" : "Ikegaki_1.818.fbx"); }

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


        // ---------------------------------------------------------------- 土井大隅守上屋敷の新造部材
        // 2026-09-06 に部材方が焼いた。⛔ **新規マテリアルは1つも作っていない** — 材質名は
        // すべて在庫キット(Village Kit / edogoyomi)のままなので、Unity 側の Search&Remap が当たる。
        // remap のメニュー: 表長屋・長屋門は **`Edo/長屋/表長屋のマテリアルをremap`**、
        //   それ以外(附属屋・木戸・垣・屋根)は **`Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`**
        //   (⚠ メニュー名に岡部と入っているが、**名前一致で当てるので邸に依らない**)。

        /// <summary>**土井邸の表門 = 長屋門**(片番所 格子付・片潜門)。表長屋の躯体を門の上まで
        /// 通し、その足元に門口を抜いた版。**扉(両開きの板戸)は部材に作り付け**。
        ///
        /// <para>実寸 **11.820(X) × 5.509(Y) × 4.381(Z)**。桁行は指図 `gate.plan.monW` と一致。
        /// 内訳: 門口 3.636 × 有効高 3.300 / 板戸 3.000 + 小壁 0.300 / 冠木 0.300 /
        /// 片潜門 0.900 × 1.900 の一枚戸 / 出格子 1.251 × 1.637(出 0.500)。
        /// **番所と潜門はともに向かって左**。
        /// ピボット = **走りの中心 / 土台の底 / 壁の外面**、**見え面 = +Z(街路側)**。</para>
        ///
        /// <para>⚠⚠ **棟高 5.509 は `gate.plan.monH`(5.40)と 0.109 食い違う。**
        /// `gate.plan.assembly` が「棟高・梁間は隣接の表長屋の実測に合わせる」と宣言していて、
        /// その表長屋が 5.509 で焼けた ⇒ **宣言に従うなら 5.509 が正**(`_pending.monh`)。
        /// ⚠ **潜門と主扉の間の壁は 0.46m しかない** — 据えてから目で見て確かめること(図では読めない)。
        /// ⚠ **門戸部の間数そのものは確度 U**(`_pending.monsun` の史料待ち)。部材が焼けたことは
        /// 寸法の典拠にならない。</para>
        /// 生成: blender --background --python Tools/Blender/build_nagaya_omote.py -- 11.82 --name Doi_Nagayamon --gate 5.91 3.636 3.30 --doorh 3.0 --kuguri 8.637 0.90 1.90 --bansho 1 --bansho-out 0.5 --kabuki 0.30 --render</summary>
        public const string DoiNagayamon = NagayaDir + "Doi_Nagayamon.fbx";

        /// <summary>**厩** 5.5×7間(土井邸 `munes.Umaya`)。実寸 **13.506(X) × 5.418(Y) × 11.291(Z)**。
        /// ⭕ 棟高 5.418 は `munes.Umaya.roof.ridgeH`(5.42)と一致し、**表長屋(5.509)より低い**
        /// — 格を分ける狙いどおり。
        ///
        /// <para>⚠⚠ **部材の X(13.506)は桁行 7間、Z(11.291)は梁間 5.5間。**
        /// `munes.Umaya` は **u が 5.5間・v が 7間** なので、**据えるとき ローカル +X を +v へ**向ける。
        /// 取り違えると 90° 転ぶ(2026-09-06 普請奉行の裁定でこの断りのまま棟梁へ申し送る)。
        /// ピボット = footprint の中心・地盤レベル。⚠ 屋根の**型**は未定のまま(`_pending.yanekata`)。</para>
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- umaya --render</summary>
        public const string DoiUmaya = FuzokuyaDir + "Doi_Umaya_5.5x7ken.fbx";

        /// <summary>**家中長屋**(邸内の長屋・土井邸 `service.Kachu_N1/N2/N3/S1/Y` の5棟)。
        /// **平家・桟瓦・下見板の腰・真壁漆喰・片面だけ開口**。桁行 <paramref name="ketaKen"/>間 × 梁間 2.5間。
        ///
        /// <para>⛔⛔ **表長屋で代用しない。** [西川1959]A の原文は「外周部は、**二階瓦葺窓付の長屋**が
        /// めぐらされ、**邸内には平家建の長屋が密接して建並んでいた**」— **外周=二階建 / 邸内=平家建**で
        /// 別の建物である。⛔ <see cref="Eg.KnagayaC"/> も <see cref="NagayaOmote(float)"/> も当てないこと
        /// (2026-09-06 考証方 高2 で `const.nagayaRidge` 5.509 の流用は明示的に禁じられた)。</para>
        ///
        /// <para>**焼いてあるのは 8 / 9 / 10間 の3種**(`service` の桁行は 10/8/9/8/8間)。
        /// 実寸(Unity) — 8間 **15.284(X) × 4.400(Y) × 6.537(Z)** / 9間 **17.102 × 4.400 × 6.537** /
        /// 10間 **18.920 × 4.400 × 6.537**。⭕ **モジュールを並べず桁行ごとに一体で焼いてある**
        /// (表長屋の 2026-09-04 裁定=案A と同じ判断。継ぎ目と端部材の小口を持ち込まないため)。</para>
        ///
        /// <para>⭐ **ピボット = 足形(桁行×梁間)の中心・地盤レベル**(底 Y=0.000)。
        /// ⇒ `service[].uc, vc` をそのまま XZ に、段の面の高さ `service[].y` をそのまま `position.y` に入れる。
        /// ⛔ **軒先高でも棟高でもない**(`Goten.RoofBanded` の z と取り違えない)。
        /// ⚠ **屋根は足形の外へ出る** — 平(±Z)へ **0.900m**・けらば(±X)へ **0.370m**。
        /// **ピボットの矩形には含まれない**ので、隣との空きは足形でなく軒先線で見ること。</para>
        ///
        /// <para>⭐ **向き**: ローカル **+X = 桁行**(`service[].L` の側)/ **+Z = 開口面**(戸と格子窓)/
        /// **−Z = 背面**(開口なしの壁)。`service[].yaw` は **v 軸から測った桁行の角**なので、
        /// 郭グリッドの向きに `yaw` を足した角で振ること(⛔ 部材の側は 90° を持たない)。
        /// ⚠⚠ **開口をどちらへ向けるかは指図に欄が無い**【U】⇒ **+Z を郭の内側(境界と反対)へ**向けること。
        /// 境界側は犬走りしか無く、そちらへ開けると隣家へ向かって開くことになる。</para>
        ///
        /// <para>**実測(部材実測 P・`_pending.kachu_noki` の宿題への回答)**: 軒桁 **2.800**
        /// (= `const.kachuEave`)/ 瓦面の大棟 **4.040**(= 指図が刷る棟高と一致)/
        /// ⚠ **棟天端は 4.400** — 瓦面の上に大棟(熨斗+冠瓦)が 0.360 見え掛かるため。
        /// ⇒ 指図の 4.04 は**瓦面の頂**であって天端ではない。⛔ 天端を 4.04 に合わせるために
        /// 軒桁を下げないこと(格は軒高で読む: 厩 2.35 &lt; 家中 2.80 &lt; 御殿 3.40)。</para>
        ///
        /// 材 = `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`(すべてキット由来)。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- kachu --render</summary>
        public static string DoiKachu(int ketaKen)
        {
            return NagayaDir + "Doi_Kachu_" + ketaKen + "x2.5ken.fbx";
        }

        /// <summary>**土蔵**(土井邸 `service` の `Komegura` / `Kura1` / `Kura2`)。置屋根・海鼠腰。
        /// ⛔ 在庫の <see cref="Eg.Kura"/> は梁間 3.65間で、当図の足形のどれとも一致しないので使わない。
        ///
        /// <para>焼いてあるもの — **3×8間 = 15.582(X) × 6.867(Y) × 7.071(Z)** /
        /// **3×3間 = 6.492(X) × 6.867(Y) × 7.071(Z)**。ピボット = footprint の中心・地盤レベル。</para>
        ///
        /// <para>⚠⚠ **引数の順は <see cref="Goten.RoofIrimoya_"/> と逆。**
        /// <paramref name="hariKen"/> = 梁間(短辺 = ローカル Z)、<paramref name="ketaKen"/> = 桁行
        /// (長辺 = ローカル X)で、ファイル名の "3x8" がそのまま (3, 8)。
        /// ⚠⚠ **割り当ては足形で決めること** — `service` の矩形が正典で、
        /// **3×8 → `Kura1` と `Komegura` の2棟 / 3×3 → `Kura2` の1棟**(2026-09-06 普請奉行の裁定)。
        /// ⛔ 部材方の対応表の文言(3×8 を「Kura1/Kura2」)で据えない。
        /// ⚠ `const.kuraWallTop`(妻壁の頂 6.02)は旧部材由来のまま【確度 ?】(`_pending.kurabuzai`)。
        /// 見切りの合否は地盤〜棟で立つのでそこは動かない。</para>
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- kura --render</summary>
        public static string DoiKura(int hariKen, int ketaKen)
        {
            return FuzokuyaDir + "Doi_Kura_" + hariKen + "x" + ketaKen + "ken.fbx";
        }

        /// <summary>**井戸**(土井邸 `wells` の5口とも同じ部材)。石の角井戸枠 + 木の桁2本 + 梁 + 釣瓶。
        /// 実寸 **1.900(X) × 2.210(Y) × 1.900(Z)**。石枠の丈は `_pending.ido` の 0.35m
        /// (⚠ 松江松平の <see cref="Matsudaira.Ido"/> の 0.62 より低い — 別部材である)。
        /// ⛔ **井戸屋形(屋根)は付けていない** — 当図に無い【確度 U】。
        /// ピボット = **井戸の芯・地盤レベル**なので `wells[].u,v` をそのまま使える。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- ido --render</summary>
        public const string DoiIdo = FuzokuyaDir + "Doi_Ido.fbx";

        /// <summary>**手水石(水盤)** — 稲荷の社前・参道の西(`yashiro.chozu`)。
        /// 実寸 **0.700(X) × 0.480(Y) × 0.500(Z)**。
        /// ⚠⚠ **指図の呼び寸法(`yashiro.chozu` 0.6 × 0.4)は水盤の内法**で、部材の外形は
        /// 縁の出のぶん 0.70 × 0.50 になる。⛔ **呼び寸法を部材へ渡さない**(規則5)。
        /// ⛔ 蹲踞・手水鉢(茶庭の露地の要素)にしていない — 当屋敷に茶室・露地は無い。
        /// ピボット = **水盤の芯・地盤レベル**(⚠ 底は −0.06 = 根石が地中へ入る)。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- chozu --render</summary>
        public const string DoiChozu = FuzokuyaDir + "Doi_Chozu.fbx";

        /// <summary>**沓脱石** — 奥棟の南入側の前の一枚石(`gardens.G_Okuniwa.kutsunugi.Kutsunugi_Oku`)。
        /// 実寸 **1.400(X) × 0.488(Y) × 0.950(Z)**。在庫の実岩 `Rock_05_cut` を切り、
        /// **上面だけを均した自然石**(⛔ 面(chamfer)は立てていない — 稜を取ると据石の格が変わる)。
        ///
        /// <para>ピボット = **足形の芯・天端(水切りの中立点)**。石は Y **−0.483 … +0.005**。
        /// ⇒ <c>position.y = kutsunugi[].topY</c>(26.92)を**直に**入れる
        /// (⛔ bbox から座り直さない)。</para>
        ///
        /// <para>天端は水平だが **ローカル +Z へ 1/100 の水切り**(見込み 0.95m で落差 9.5mm)。
        /// ⛔ **+Z を入側へ向けない** — 指図 `mizukiri.to` は「−u(入側と反対=庭側)」で、
        /// 裏を返せば **−Z が入側**(奥棟の南面 = +u 側)を向く。雨を縁の下へ入れないための向き。</para>
        ///
        /// ⛔ **非一様スケールを掛けない**(写真計測の石肌の斑が流れる)。
        /// ⛔ **根固めの栗石は部材に含まない** — 地表側(棟梁)の表現。
        /// 材 = `M_photoscanned_rocks_01`(⛔ 新規マテリアルを作らない。remap が要る)。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- kutsunugi --render</summary>
        public const string DoiKutsunugi = FuzokuyaDir + "Doi_Kutsunugi.fbx";

        /// <summary>**水尻の石の閾(余水吐)**。汀 #14(西端)、天端は `mizu.mizushiri.shiki.sill`
        /// (水面 +0.05)。実寸 **1.200(X) × 0.490(Y) × 0.890(Z)**。数量1。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- shiki --render</summary>
        public const string DoiMizushiriShiki = FuzokuyaDir + "Doi_Mizushiri_Shiki.fbx";

        /// <summary>**水尻の石組の吐き口**(埋樋の終点)。実寸 **0.950(X) × 0.740(Y) × 0.820(Z)**。
        /// ⭕ **埋樋(石樋 φ0.24)の本体は焼いていない** — 土被り 0.30m 以上で埋まり地上から見えない。
        /// 指図の延長は `mizu.mizushiri.umeToi.pts` から測った設計値の記録で、部材の数量ではない。
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- hakiguchi --render</summary>
        public const string DoiMizushiriHakiguchi = FuzokuyaDir + "Doi_Mizushiri_Hakiguchi.fbx";

        /// <summary>**水尻の石敷きの落とし溝** — **1m モジュール**。実寸 **1.000(X) × 0.240(Y) × 0.700(Z)**。
        /// 吐き口から `mizu.mizushiri.otoshimizo.to` まで法面を下る。
        /// ⭕ **走りを 1m 刻みで並べ、端数は端の1本を切って吸う**。
        /// ⛔ **全体を伸縮させて溝の石を引き伸ばさない。**
        /// 生成: blender --background --python Tools/Blender/build_doi_buzai.py -- otoshimizo --render</summary>
        public const string DoiOtoshimizo = FuzokuyaDir + "Doi_Otoshimizo_1m.fbx";

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

    /// <summary>シーン。</summary>
    public static class Scenes
    {
        /// <summary>本番の一枚。</summary>
        public const string Akasaka = "Assets/Edo/Scenes/Akasaka.unity";

        /// <summary>作業場 — 建て直しの輪を回す軽いシーン(地形+光+対象邸+20m 以内の隣)。
        /// `Edo/普請/作業場を仕立てる` が赤坂から起こす。中身は使い捨てなので gitignore。
        /// → <see cref="EdoKoba"/></summary>
        public const string Koba    = "Assets/Edo/Scenes/Koba.unity";
    }
}
