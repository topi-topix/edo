# 部材の名の目録 — EdoAssets(生成物・手で直さない)

<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py -->

**部材のパスの名を探すときは `EdoAssets.cs` を grep で読み歩かずまずここを引く。**在庫に何が在るか(実寸・ピボット)は `docs/asset-catalog.md` → `docs/asset-index.tsv`。ここは C# から呼べる名の索引だけ。

- `Assets/Edo/Scripts/Editor/EdoAssets.cs` の公開の名 376(入れ子の分類ごと)。中身 = 定数ならパスの末尾、関数なら注釈の一文目。
- 使っている所 = `EdoAssets.<分類>.<名>` と書いている C# ファイルとその中の関数。
- ⛔ 手で直さない(`python3 Tools/Unity/edobuild_mokuroku.py`)。

## Eg

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Eg.ES_NOTE` | string | `scale 1.818` | — |
| `Eg.Kmon` | string | `k_mon.obj` — 門 | PartSpec(Bake), Sanyashiki, Typology(GatePath), Yamato |
| `Eg.Hmon` | string | `h_mon.obj` | PartSpec(Bake), Sanyashiki, Typology(GatePath) |
| `Eg.Nagayamon` | string | `nagayamon.obj` | PartSpec(Bake), Typology(GatePath) |
| `Eg.Kabukimon` | string | `kabukimon.obj` | Typology(GateChoices・GatePath), MatsudairaDewa(Stage6_Zosaku), OkabeYashiki(AssetByKey), PartSpec(Bake) ほか1 |
| `Eg.KidoOpen` | string | `kido_open.obj` | PartSpec(Bake), SannoSha, Typology(GatePath) |
| `Eg.Kura` | string | `kura.obj` — 建物 | OkabeYashiki(AssetByKey), SannoSha, Typology(Plan), TypologyBuilder.Jisha(JishaOmoya) ほか1 |
| `Eg.KnagayaC` | string | `knagaya01c.obj` | BuildRun, Doi(PlaceService), NagayaOmote(Remap), OkabeYashiki(BindDonorMaterials) ほか1 |
| `Eg.KnagayaL` | string | `knagaya01l.obj` | BuildRun, Doi(PlaceService), NagayaOmote(Remap), OkabeYashiki(BindDonorMaterials) ほか1 |
| `Eg.KnagayaR` | string | `knagaya01r.obj` | BuildRun, Doi(PlaceService), NagayaOmote(Remap), Yamato(UmayaPair) |
| `Eg.Bansho` | string | `dbansho.obj` | Typology(BuildParcel・GateWidth), PartSpec(Bake), Sanyashiki, Yamato |
| `Eg.Kidobanya` | string | `kidobanya.obj` | — |
| `Eg.Jishinban` | string | `jishinban.obj` | TypologyBuilder.Inari(Inari), TypologyBuilder.Machiya(Machiya) |
| `Eg.Hinomiyagura` | string | `hinomiyagura.obj` | Typology(Plan) |
| `Eg.Shop01` | string | `shop01.obj` | BuildMachiya(HangNoren・MachiyaRun), SannoSha, TypologyBuilder.Machiya(Machiya) |
| `Eg.Shop02` | string | `shop02.obj` | BuildMachiya(HangNoren・MachiyaRun), SannoSha, TypologyBuilder.Machiya(Machiya) |
| `Eg.DobeiCenter` | string | `s_hei_center.obj` — 塀 | BuildRun, Doi(RemapKido), OkabeYashiki(BindDonorMaterials), PartSpec(Bake) |
| `Eg.DobeiCorner` | string | `s_hei_corner.obj` | — |
| `Eg.Itabei5` | string | `itabei5.obj` | SannoSha(BuiltSegs・RemapSannoShinzo・Stage4_Kakoi), MatsudairaDewa(ItabeiRun・PlaceItabeiSpan), OkabeYashiki(AssetByKey) |
| `Eg.Hogaki5` | string | `hogaki5.obj` | MatsudairaDewa(FenceWidth・Stage2_Perimeter), OkabeYashiki(AssetByKey) |
| `Eg.TakeGaki` | string | `bamboo garden fence B.prefab` — 竹垣(0.9高 x 1.05長)。水際・庭園帯の囲いに。 | MatsudairaDewa(Stage6_Zosaku), MatsudairaDewaBuilder.Niwa(Stage6d_Tenkei), OkabeYashiki(AssetByKey) |
| `Eg.ToroYukimi` | string | `t_yukimi.obj` — 雪見灯籠(六角の広い笠 + 宝珠 + 火袋 + 竿を持たない三脚)。 | DoiBuilder.Niwa(ResolveNiwaApi), OkabeYashiki(PlaceNiwaItem) |
| `Eg.TexToroYukimi` | string | `t_yukimi.jpg` | — |
| `Eg.ToroKasuga` | string | `t_kasuga.obj` — 春日灯籠(edogoyomi `t_kasuga`)── 寺社の境内の献灯(本堂の前・参道の左右に一対)にだけ当てる (庭方の境内の設計 2026-09-27・EDO-0477 P5)。 | TypologyBuilder.Keidai(NiwaKeidai) |
| `Eg.TexToroKasuga` | string | `t_kasuga.jpg` | — |
| `Eg.BareTex` | System.Collections.Generic.Dictionary<string, string> | 材の無い edogoyomi の駒 → 同じフォルダの画像(2026-09-28 EDO-0477 施主指摘「灯籠が真っ白」)。 | Build(Place) |
| `Eg.NorenSpec` | string | `noren.json` — 表店の暖簾・看板の店ごとの染め分け(EDO-0503 施主「全部同じ暖簾」)。 | BuildMachiya(MachiKidoAcross・NorenVariants) |
| `Eg.KindaiSpec` | string | `kindai.json` — 近代の造作を除く帳(EDO-0514)。 | BuildZosei(BaseDem・KindaiList) |
| `Eg.NorenTex(shop, key)` | 関数 | — | BuildMachiya(NorenMaterial) |
| `Eg.NorenMat(shop, key)` | 関数 | — | BuildMachiya(NorenKitMaterial・NorenMaterial・NorenVariants) |
| `Eg.Shop01Taru` | string | `s01_taru.obj` — 店先の小物 | — |
| `Eg.Shop01Oke` | string | `oke.obj` | — |
| `Eg.TexShop01` | string | `shop01.jpg` — テクスチャ(マテリアル生成用) | — |
| `Eg.TexShop02` | string | `shop02.jpg` | — |
| `Eg.TexOke` | string | `oke.jpg` | — |
| `Eg.TexKomodaru` | string | `komodaru.jpg` | — |
| `Eg.TexKidobanya` | string | `kidobanya.jpg` | — |

## VK

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `VK.House` | string | `House.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath), SannoSha, Typology(Plan) |
| `VK.HouseA` | string | `House A.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath), Yamato |
| `VK.HouseB` | string | `House B.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath) |
| `VK.SmallHouse` | string | `Small House.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath), SannoSha, Typology(Plan), TypologyBuilder.Jisha(JishaOmoya) ほか1 |
| `VK.BigHouse` | string | `Big House.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath), Typology(Plan), Yamato |
| `VK.Manor` | string | `Manor.prefab` | TypologyBuilder.Yuragi(YuKomaName・YuKomaPath), Yamato |
| `VK.Roof2x8` | string | `roof 2x8.prefab` | — |
| `VK.RoofEnd2x1` | string | `roof end 2x1.prefab` | — |
| `VK.RoofTopX8` | string | `roof top x8.prefab` | — |
| `VK.FloorInterior2x2` | string | `floor interior 2x2.prefab` | — |
| `VK.ColumnA` | string | `column A .prefab` | — |
| `VK.WallShopWoodX8` | string | `Wall Shop Wood x 8.prefab` | — |
| `VK.WallShopPlasterX8` | string | `Wall Shop Plaster x 8.prefab` | — |

## Goten

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Goten.Shoji1ken` | string | — | GotenKit(Mune) |
| `Goten.ShojiHalf` | string | — | — |
| `Goten.WallPlaster` | string | — | GotenKit(Mune) |
| `Goten.WallRenji` | string | — | — |
| `Goten.Column` | string | — | GotenKit(Mune・Roka) |
| `Goten.Beam` | string | — | GotenKit(Roka) |
| `Goten.Tatami` | string | — | GotenKit(Mune) |
| `Goten.FloorBoard` | string | — | GotenKit(Mune・Roka) |
| `Goten.RokaEnita` | string | 渡廊下の縁板 一間角(厚 1寸 0.0303)。 | GotenKit(Mune・Roka) |
| `Goten.Ceiling` | string | — | GotenKit(Mune) |
| `Goten.Nureen` | string | — | GotenKit(Mune) |
| `Goten.NureenCorner` | string | — | GotenKit(Mune) |
| `Goten.Koran` | string | — | GotenKit(Roka) |
| `Goten.EnKeta(floor)` | 関数 | 御殿の床下の足元(EDO-0502 2026-10-03)。 | GotenKit(Mune), OkabeYashiki(PlaceMunes) |
| `Goten.EnTsuka(floor)` | 関数 | — | GotenKit(Mune) |
| `Goten.Soseki(floor)` | 関数 | — | GotenKit(Mune) |
| `Goten.KaidanRoka(run, drop)` | 関数 | 階段廊下 — 木の段になった渡廊下。幅は他の廊下と同じ一間。 | — |
| `Goten.Fusuma` | string | 建具・座敷飾り(キットに無いので Blender で新造 — build_goten_fittings.py) | GotenKit(Mune・Partition), OkabeYashiki(PlaceLinks) |
| `Goten.Ranma` | string | — | GotenKit(Mune・Partition) |
| `Goten.Amado` | string | — | — |
| `Goten.JodanKamachi` | string | — | GotenKit(Jodan・Mune・Roka) |
| `Goten.Tokonoma` | string | — | GotenKit(Zashikikazari) |
| `Goten.Chigaidana` | string | — | GotenKit(Zashikikazari) |
| `Goten.Chodaigamae` | string | — | GotenKit(Zashikikazari) |
| `Goten.RoofDir` | string | `` — 入母屋屋根。棟の寸法ごとに Blender で生成する: blender --background --python Tools/Blender/build_goten_roof.py -- W D 名前 | — |
| `Goten.RoofIrimoya` | string | — | GotenKit(BuildTestGankou・BuildTestMune) |
| `Goten.RoofIrimoya5x5` | string | — | GotenKit(BuildTestGankou) |
| `Goten.RoofIrimoya_(wKen, dKen)` | 関数 | 棟の外形(身舎+入側)の間数で引く入母屋。 | BuildJisha(Honden), BuildGoten(GotenComplex), MatsudairaDewa(Stage4_Goten), TypologyBuilder.Jisha(JHallBaked) |
| `Goten.RoofYosemune_(wKen, dKen)` | 関数 | 棟の外形(身舎+入側)の間数で引く寄棟。 | — |
| `Goten.RoofBanded(bands, spanKen, alongV=…, irikawa=…, noki=…)` | 関数 | 帯割りの入母屋。身舎を帯(2〜5間)に割り、帯ごとに入母屋を架けて 境を水平の谷にした屋根。 | MatsudairaDewa(Stage4_Goten・TriPierceY), Doi(Stage4_Goten), GotenKit(Put) |
| `Goten.RoofKirizumaKen` | float[] | 渡廊下の切妻屋根。幅1間・長さRoofKirizumaKen間の定尺で作ってある (瓦の繰り返し 1.785/2.004m は江戸間と割り切れないので1間モジュールにはできない)。 | — |
| `Goten.RoofKirizuma(nKen)` | 関数 | — | GotenKit(Mune・Roka), Doi(Stage4_Goten) |
| `Goten.KenTag(nKen)` | 関数 | 間数をファイル名の綴りへ。整数はそのまま、端数は小数第2位まで(末尾の0を落とす)。 | GotenKit(Roka), MatsudairaDewa(Stage4_Goten) |
| `Goten.RoofHirairi(wKen, dKen, eaveAboveFloor, omit=…, notchSide=…, notchKen=…)` | 関数 | 平入り + 庇の屋根(身舎に切妻を架け、その外を庇一間が回る)。 | MatsudairaDewa(Stage4_Goten) |
| `Goten.HirairiNotches(mune, rokaRects, side, ken)` | 関数 | 棟に取り付く渡廊下から、RoofHirairi へ渡す切り欠き (辺 side と中心の間数 ken)を解く。 | MatsudairaDewa(Stage4_Goten) |
| `Goten.RoofRokaGeya(nKen)` | 関数 | 渡廊下の差し掛けの下屋(両流れ)。主屋の軒下から葺き下ろす下屋で、 独立した大棟を持つ RoofKirizuma とは別物(松江松平 2026-09-17 ユーザー裁定A)。 | GotenKit(Mune・Roka) |
| `Goten.Amaosae(danMm)` | 関数 | 段違いの下屋の折れ目を塞ぐ雨押え(小壁 + 面戸の一体物)。 | MatsudairaDewa(Stage4_Goten) |
| `Goten.RokaKamachi(danMm)` | 関数 | 渡廊下の段を受ける框(框 + 蹴込板 + 地覆)。 | GotenKit(Roka・RokaKamachi) |
| `Goten.RoofNoboriro(tag)` | 関数 | 登廊(階段廊下)の屋根。切妻を斜長ぶん通し、幅は石段の平場ぶん取ったもの。 | — |
| `Goten.Ken` | float | — | GotenKit, OkabeYashiki(PlaceLinks) |
| `Goten.DoorH` | float | — | GotenKit |
| `Goten.Uchinori` | float | — | GotenKit(Mune・Partition) |
| `Goten.RanmaH` | float | — | — |
| `Goten.ColumnW` | float | — | — |
| `Goten.KoranH` | float | — | — |
| `Goten.BeamH` | float | — | GotenKit(Roka) |

## JC

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `JC.CastleWall` | string | `Castle Wall.prefab` | OkabeYashiki(Pivot・PlaceIshigaki・Stage2b_Dan), BuildDanIshigaki(CastleWallOfExpose), BuildIshidan, Doi(Stage3_Ishigaki) ほか4 |
| `JC.CastleWallCorner` | string | `Castle Wall Corner.prefab` | Yamato |
| `JC.CastleWall4x12Mesh` | string | `Castle Wall 4x12.fbx` | IshigakiFit |
| `JC.GateDoorCastleL` | string | `Gate Castle Door L.fbx` — 小門用(1.5×2.8)。対で開口 3.0m ちょうど。 | — |
| `JC.GateDoorCastleR` | string | `Gate Castle Door R.fbx` | — |
| `JC.GateDoorCastleFoot` | float | — | — |
| `JC.GateDoorYaguraL` | string | `Gate Yagura Door A Left Hinge.prefab` — 表門用(2.143×3.0)。対で 4.0m、足元は local y=0。 | — |
| `JC.GateDoorYaguraR` | string | `Gate Yagura Door A Right Hinge.prefab` | — |
| `JC.WallDefence` | string | `Wall Exterior Defence.prefab` | — |
| `JC.WallDefenceX8` | string | `Wall Exterior Defence x 8.prefab` | — |
| `JC.WallDefenceCorner` | string | `Wall Exterior Defence Corner.prefab` | — |
| `JC.GateExterior` | string | `Gate Castle Exterior.prefab` | — |
| `JC.GateExteriorEndL` | string | `Gate Castle Exterior End L.prefab` | — |
| `JC.GateExteriorEndR` | string | `Gate Castle Exterior End R.prefab` | — |
| `JC.YaguramonA` | string | `Yaguramon A.prefab` | SannoSha |
| `JC.StoneBasket` | string | `Stone Basket.prefab` | SannoSha |
| `JC.Azalea01` | string | `Azalea A 01.prefab` | — |
| `JC.Azalea03` | string | `Azalea A 03.prefab` | — |
| `JC.Azalea04` | string | `Azalea A 04.prefab` | — |

## JG

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `JG.PineBig01` | string | `Tree_BlackPine_Big_Green_01.prefab` | DoiBuilder.Niwa(JGPine), SannoSha |
| `JG.PineBig02` | string | `Tree_BlackPine_Big_Green_02.prefab` | DoiBuilder.Niwa(JGPine), SannoSha |
| `JG.PineBig03` | string | `Tree_BlackPine_Big_Green_03.prefab` | DoiBuilder.Niwa(JGPine), SannoSha |
| `JG.PineMid01` | string | `Tree_BlackPine_Mid_Green_01.prefab` | — |
| `JG.SakuraBig01` | string | `Tree_Sakura_Big_Summer_01.prefab` | — |
| `JG.SakuraBig05` | string | `Tree_Sakura_Big_Summer_05.prefab` | — |
| `JG.SakuraMid01` | string | `Tree_Sakura_Mid_Summer_01.prefab` | — |
| `JG.SakuraMid05` | string | `Tree_Sakura_Mid_Summer_05.prefab` | — |
| `JG.BambooBig01` | string | `Tree_Bamboo_Big_Green_01.prefab` | SannoSha(Stage7_Keidairin) |
| `JG.BambooBig02` | string | `Tree_Bamboo_Big_Green_02.prefab` | SannoSha(Stage7_Keidairin) |
| `JG.Boxwood01` | string | `Plant_Boxwood_Spring_01.prefab` | — |
| `JG.Fern01` | string | `Plant_PaintedFern_Spring_01.prefab` | — |
| `JG.GravelMat` | string | `M_FJG_Terrain_Ground_Gravel_01.mat` — 玉砂利(参道・敷き)の材。URP/Lit(パックの URP パッチ済み)。 | MatsudairaDewaBuilder.Niwa(Stage6f_Tamajari) |
| `JG.Rock01` | string | `JG_Rock_A_01.prefab` | — |
| `JG.Rock02` | string | `JG_Rock_A_02.prefab` | — |
| `JG.Rock03` | string | `JG_Rock_A_03.prefab` | — |
| `JG.TobiIshi01` | string | `JG_TobiIshi_A_01.prefab` | SannoSha |
| `JG.TobiIshi02` | string | `JG_TobiIshi_A_02.prefab` | — |
| `JG.Pine(size, i)` | 関数 | 黒松。生 5.6m ×1.65。Big/Mid/Small × 01..03 | MatsudairaDewa(ResolveApi・Stage7_Niwa), OkabeYashiki(PlantByKey), TypologyBuilder.Niwa(DeShare) |
| `JG.Bamboo(size, i)` | 関数 | 竹。Big/Mid/Small × 01・02(`Green` のみ引く — `Dry` は枯れ姿で当プロジェクトでは使わない)。 | OkabeYashiki(PlantByKey) |
| `JG.SakuraSummer(size, i)` | 関数 | 桜。⚠ Summer のみ使う(季節は春ではない)。 | MatsudairaDewa(ResolveApi) |
| `JG.Boxwood(i)` | 関数 | 柘植の刈込。Spring/Fall × 01..03、Single/ もある | DoiBuilder.Niwa(Niwa_H_Shokusai・ResolveNiwaApi), MatsudairaDewa(ResolveApi・Stage7_Niwa), OkabeYashiki(PlantByKey), TypologyBuilder.Niwa(MomijiPalFor) |
| `JG.BoxwoodSingle(i)` | 関数 | 柘植の一株(Single)。01..03・実寸 約1.0×0.8〜1.1×0.9m・120〜140ポリ。 | BuildRun(IkegakiRow) |
| `JG.Fern(i)` | 関数 | 羊歯の下草。Spring/Fall × 01..02 | DoiBuilder.Niwa(Niwa_H_Shokusai・ResolveNiwaApi), MatsudairaDewa(ResolveApi・Stage7_Niwa), OkabeYashiki(PlantByKey), TypologyBuilder.Niwa(MomijiPalFor) |
| `JG.Rock(i)` | 関数 | 庭石。01..03 | MatsudairaDewa(ResolveApi・Stage7_Niwa), MatsudairaDewaBuilder.Niwa(Stage6c_Ishigumi・Stage6d_Tenkei) |
| `JG.Azalea(i)` | 関数 | 躑躅・皐月。⚠ A 02 は存在しない — 01 / 03 / 04 の3種 | MatsudairaDewa(ResolveApi・Stage7_Niwa), BuildRun(OutsidePlot) |

## NM

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `NM.MapleBush(i)` | 関数 | カエデの灌木(下草・林床の中層)。i = 1..4。 | MatsudairaDewa(ResolveApi), OkabeYashiki(PlantByKey) |
| `NM.GreyWillow(i)` | 関数 | ヤナギの灌木(水際・法面の下層)。i = 1..4。 | MatsudairaDewa(ResolveApi), OkabeYashiki(PlantByKey) |
| `NM.GrassMeadow(family, variant, i)` | 関数 | 草地(メドウ)の草叢。岡部邸のススキ(見透しの窓・法尻)に使う。 | OkabeYashiki(PlantByKey) |
| `NM.GrassMeadowIndices(family, variant)` | 関数 | 系統・変種ごとに実在する個体の番号(2026-09-04 に `ls` で確認)。 | OkabeYashiki(PlantByKey) |
| `NM.CliffPiece(i)` | 関数 | 実肌の岩棚(野面石 1 段の土留め)。松江松平邸 `slopeDoryu`(法尻の土留め)に使う。 | — |

## Own

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Own.KasugaLantern` | string | `KasugaLantern.prefab` | DoiBuilder.Niwa(ResolveNiwaApi), SannoSha |
| `Own.YukimiLantern` | string | `YukimiLantern.prefab` | DoiBuilder.Niwa(ResolveNiwaApi) |
| `Own.DanishiStep` | string | `P_DanishiStep2m.prefab` | OkabeYashiki(AssetByKey・PlaceKaidanAB・PlaceKaidans), Doi(PlaceFumiishi・PlaceKaidans), MatsudairaDewa(Stage6_Zosaku), SannoSha ほか1 |
| `Own.MichibataIshi` | string | `P_MichibataIshi2m.prefab` | SannoSha |
| `Own.Broadleaf` | string | ⛔ 使用禁止(Obsolete)。`BroadleafTree.prefab` — 常緑の広葉樹(モッコク・モチノキ・カシ・シイの見立て)。 | — |
| `Own.Jouryoku(size, i=…)` | 関数 | 常緑広葉樹(モッコク・モチノキ・シラカシ・スダジイの見立て)。 | TypologyBuilder.Niwa(DeShare), DoiBuilder.Niwa(ResolveNiwaApi), MatsudairaDewa(ResolveApi), OkabeYashiki(PlantByKey) ほか1 |
| `Own.Jokuroku(size)` | 関数 | ⛔ 使用禁止(Obsolete)。⛔ 綴りの誤り(常緑の訓みは Jouryoku)。 | — |
| `Own.Teiboku(size, i=…)` | 関数 | 常緑の照葉低木(サカキ・アオキ・ヤブツバキの見立て)。 | BuildRun(EdgeFacesSlope), OkabeYashiki(PlantByKey), SannoSha(TreePath), TypologyBuilder.Niwa(MomijiPalFor) |
| `Own.Matsu(size, i=…)` | 関数 | クロマツ(社叢)。山王社の社叢の高木。⭐ 林の松 — 在庫の `JG.Pine` は独立して枝を張った庭の松で樹形が別。 | OkabeYashiki(PlantByKey), SannoSha(TreePath), TypologyBuilder.Niwa |
| `Own.SannoRomon(duKen, dvKen, pX, mX, pZ, mZ)` | 関数 | 山王社の楼門(隨身門)・坂下の門(仁王門)兼用。 | — |
| `Own.SannoRomon(duKen, dvKen, passMm, widthMm, pX, mX, pZ, mZ)` | 関数 | 山王社の楼門(隨身門)— 明治16年実測図の寸法(ユーザー裁定C 2026-09-14)。 | — |
| `Own.SannoSakashitamon(duKen, dvKen, passMm, widthMm, pX, mX, pZ, mZ)` | 関数 | 山王社の坂下の門(仁王門)— 明治16年実測図 第2稿の読み(2026-09-14)。 | — |
| `Own.SannoSodebei(lenMm)` | 関数 | 山王社の袖塀(回廊の翼の妻 ↔ 楼門の側面) — 瓦葺の築地塀・長さ lenMm[mm]・両端を袖瓦と漆喰で塞ぐ。 | SannoSha(Sodebei) |
| `Own.SannoSodebei(lenMm, stepAtMm, stepRiseMm)` | 関数 | 山王社の袖塀 — 足元二段(普請奉行の裁定 案A 2026-09-14)。 | SannoSha(Sodebei) |
| `Own.SannoSukibei(spanMm, ends)` | 関数 | 山王社の透塀(瑞垣)— 1スパン。屋根銅瓦葺【S 目録1941】・腰板+連子格子+小壁。 | SannoSha(GateNameOf・SukibeiPart) |
| `Own.SannoSukibeiKado(part, refSpanMm=…)` | 関数 | 山王社の透塀の隅。part = "Dezumi"(出隅: 脚が −X と −Z、見え面 +Z の側が隅棟)/ "Irizumi"(入隅: 脚が −X と +Z、見え面の側が谷)。 | SannoSha(SukibeiKado) |
| `Own.SannoShaden(kind, nuKen, nvKen, ewMm, nsMm)` | 関数 | 山王社の社殿(権現造)— 明治16年実測図の寸法(ユーザー裁定C 2026-09-14)。 | — |
| `Own.SannoKizahashi(wMm, runMm, riseMm)` | 関数 | 山王社の向拝の木階(三級・登高欄なし)— 明治16年寸法。 | SannoSha(Stage6_Shaden) |
| `Own.SannoGokusho(nuKen, nvKen, ewMm, nsMm)` | 関数 | 山王社の御供所(供の棟)— 御宮絵図の形の独立の一棟(施主の再裁定 2026-09-15)。 | — |
| `Own.SannoKairo(bays, bariBays, runMm, bariMm)` | 関数 | 山王社の回廊(屋根付きの廊)— 翼1本。 | SannoSha(GatePlacement・Kairo) |
| `Own.SannoTorii(spanMm, tallMm)` | 関数 | 山王社の鳥居 — 石造の明神鳥居。⭐ 一ノ鳥居・二ノ鳥居に同じ1点を使う(同形式【A】・ 駒絵の大小は遠近の誇張なので ⛔ 寸法比を採らない)。 | — |
| `Own.SannoToriiMassha(spanMm, tallMm)` | 関数 | 山王社の末社(稲荷社)の小鳥居 — 木造朱塗りの明神鳥居。 | — |
| `Own.SannoDo(kata, nuKen, nvKen, xMm, zMm)` | 関数 | 山王社の堂宇(高床の小堂)。指図 `bom` 行9「高床構造としてまとめて起こす」の本体。 | — |
| `Own.SannoInari` | string | `Sanno_Inari_Kasuga_1ken.fbx` — 山王社の稲荷社 — 一間社春日造(縋破風形式)・銅板葺【A 千代田区の実測 = `bom` 行32】。 | — |
| `Own.SannoUmaya(nuKen, nvKen, ewMm, nsMm)` | 関数 | 山王社の御厩(供の棟)。nuKen(東西=X・桁行)×nvKen(南北=Z・梁間)[間]、 ewMm×nsMm = 柱芯[mm]。 | — |
| `Own.SannoKura(nuKen, nvKen, ewMm, nsMm)` | 関数 | 山王社の御蔵 — 土蔵造・置屋根【`bom` 行33】。 | — |
| `Own.SannoDan(keri, fumi, w, i)` | 関数 | 山王社の段石(石段の一段)。蹴上 keri / 踏面 fumi / 幅 w[m]、 個体 i の偶奇で a / b を振る(⛔ 片方だけを53段並べない — 目地が一直線に立つ)。 | DoiBuilder.Dan(MeasureNozura・PlaceKaidansA), SannoSha(Dan), TypologyBuilder.Katte(Katte) |
| `Own.SannoDanNearest(width, i)` | 関数 | 幅が最も近い焼けた段石(SannoDan の綴りの物の中から・個体 i の偶奇で a / b)。 | SannoSha(Stage5b_Fumiishi) |
| `Own.IshidanSode(keri, fumi, i)` | 関数 | 石段の袖(袖石垣)の1段ぶんの駒 — どの石段にも使える汎用の型(寸法は蹴上 keri・踏面 fumi[m] から従属)。 | BuildIshidan(FitObliqueEnd・PlaceIshidanSode), SannoSha(AbutStairsToWalls・Stage2_Kaidan) |
| `Own.ISHIDAN_SODE_DEPTH_STD` | float | 袖の丈(天端の線から下端まで)の既定 2.20 = 最大見付 1.74 + 根入れ 0.46。 | BuildIshidan(MiterIshidanSode), SannoSha(Stage2_Kaidan) |
| `Own.IshidanSodeDepths` | float[] | 焼いてある袖の丈(浅い順)。切通しで袖を背の地盤まで上げる(`copingRise:"groundHi"`)とき、 上げの上限 = 丈 − 笠の上がり 0.30 − 段石の根入れ(実メッシュで測る。 | SannoSha(Stage2_Kaidan・Stage5b_Fumiishi), BuildIshidan(PlaceIshidanSode) |
| `Own.IshidanSode(keri, fumi, i, depth)` | 関数 | 丈の深い石段の袖(EDO-0430 2026-09-24)。 | BuildIshidan(FitObliqueEnd・PlaceIshidanSode), SannoSha(AbutStairsToWalls・Stage2_Kaidan) |
| `Own.IshidanSodeFlat(depth)` | 関数 | 天端が水平な石段の袖(EDO-0459 施主裁定A 2026-09-26・男坂の最上段の袖石)。 | BuildIshidan(EndGapProfile), SannoSha(Stage2_Kaidan) |
| `Own.IshidanSodeFlat(depth, len)` | 関数 | 走りを指定した天端が水平な石段の袖(EDO-0437 施主裁定 2026-09-27・参道の階の段4 の袖 ── 走り = その段の踏面 0.542)。 | BuildIshidan(EndGapProfile), SannoSha(Stage2_Kaidan) |
| `Own.IshidanSodeFlatNori(depth)` | 関数 | 坂上の小口を法 1:0.25 に切った水平の袖(EDO-0459 2026-09-27・男坂の最上段 → 楼門の腰の隅 kado1 の法の面へ突き付ける)。 | SannoSha(Stage5b_Fumiishi) |
| `Own.ISHIDAN_SODE_FLAT_NORI_KINK` | float | 男坂の小口の折れ点 = 袖の天端 28.58 − kado1 の天端 28.27(EDO-0459 2026-09-27)。 | — |
| `Own.IshidanSodeFlatNori(depth, kink)` | 関数 | IshidanSodeFlatNori の小口を折れにした版(EDO-0459 2026-09-27・kado1 の天端から楼門の基壇までの鉛直な帯で 0.009 の口が残った)。 | SannoSha(Stage5b_Fumiishi) |
| `Own.ISHIDAN_SODE_FLAT_NORI_LEN` | float | 男坂の据えの天端の稜の長さ(折れを kado1 の天端に合わせた実測 北 1.2468・南 1.2460 の平均・2026-09-27)。 | — |
| `Own.IshidanSodeFlatNori(depth, kink, len)` | 関数 | IshidanSodeFlatNori の天端の稜の長さ len を明示する版。 | SannoSha(Stage5b_Fumiishi) |
| `Own.IshidanSodeMiter(keri, fumi, w, hF, hB, i)` | 関数 | 曲がる石段の袖 — 端を留めに切った駒(EDO-0415 ②③)。 | BuildIshidan(MiterPath・PlaceIshidanSodeFlat) |
| `Own.IshidanSodeMiter(keri, fumi, w, hF, hB, i, depth)` | 関数 | 丈の深い袖の留めの駒(EDO-0430 2026-09-24)。 | BuildIshidan(MiterPath・PlaceIshidanSodeFlat) |
| `Own.IshidanSodeNori(keri, fumi, e, i, depth=…)` | 関数 | 背を法 1:0.25 に切った石段の袖(EDO-0442 施主裁定B・2026-09-26)。 | BuildIshidan(FitObliqueEnd), SannoSha(AbutStairsToWalls) |
| `Own.SodeNoriYc(keri)` | 関数 | IshidanSodeNori の背の出 e を測る高さ(袖の局所 Y)。 | BuildIshidan(CutStairEndsToBatter・FitObliqueEnd・MeasureSodeBackEnvelope…) |
| `Own.SodeNoriSnap(e)` | 関数 | IshidanSodeNori の焼いてある刻み(0.05)へ丸める。 | BuildIshidan(CutStairEndsToBatter・SwapWallsBesideStep) |
| `Own.SannoDanKiri(keri, fumi, w, i, endL, endR)` | 関数 | 両の小口を脇の相手に合わせて切った段石(EDO-0442 施主裁定B・2026-09-26)。 | BuildIshidan(AbutStepEndsToWalls・RayFarthest), SannoSha(AbutStairsToWalls) |
| `Own.DanKiriNone` | string | `0` — SannoDanKiri の切らない端。 | BuildIshidan(CutStairEndsToBatter) |
| `Own.DanKiriEnd(d)` | 関数 | SannoDanKiri の端: 全長を返しの法で切る(d = 蹴上の中ほどでの返しの面の食い込み)。 | BuildIshidan(CutStairEndsToBatter・MeasureStepEndOnBatter) |
| `Own.DanKiriEnd(d, za, cornerUphill)` | 関数 | SannoDanKiri の端: 返しと袖に跨る。 | BuildIshidan(CutStairEndsToBatter・MeasureStepEndOnBatter) |
| `Own.DanKiriEnd(d, za, cornerUphill, nori)` | 関数 | SannoDanKiri の端: 返しと袖に跨り、返しの面・欠いた奥の面とも法 nori(野面の乱積み 1:0.3 ── EDO-0437 2026-09-26)。 | BuildIshidan(CutStairEndsToBatter・MeasureStepEndOnBatter) |
| `Own.DanKiriEnd(d, deg, nori)` | 関数 | SannoDanKiri の端: 平面で斜めに切る。 | BuildIshidan(CutStairEndsToBatter・MeasureStepEndOnBatter) |
| `Own.NearestBaked(path, tol)` | 関数 | 綴りの数だけが違う焼いてある兄弟を引く(EDO-0430 2026-09-26)。 | BuildIshidan(CutStairEndsToBatter) |
| `Own.IsSannoNozura(meshAssetPath)` | 関数 | メッシュの資産パスが山王の野面の乱積みの駒(1間・隅・切り・法切り・見切り ── `Sanno_Nozura_*`)か。 | SannoSha(AbutStairsToWalls) |
| `Own.SannoNozura(h, grade, i)` | 関数 | 野面の乱積みの土留め — 1間の駒(山王社の前庭の縁。 | BuildNozura(PlaceNozuraRun), BuildRim(BridgeCorner), OkabeYashiki(PlaceCurb・Stage2b_Dan), DoiBuilder.Dan(Stage4a_Dodome) ほか2 |
| `Own.SannoNozuraKiri(risesToPlusX, i)` | 関数 | 野面の乱積みの打ち切り — 根石一段が地中へ沈む駒(見付 0.2 未満で壁を終える所)。 | OkabeYashiki(PlaceCurb・Stage2b_Dan), DoiBuilder.Dan(Stage4a_Dodome), SannoSha(Nozura), TypologyBuilder.Rim(Rim) |
| `Own.SannoNozuraKado(h, i)` | 関数 | 野面の乱積みの出隅 90° の隅の駒(2026-09-25・山王 本殿の西の土留め `TW_Nozura_ShadenW` の帯の北西・南西の隅。 | OkabeYashiki(PlaceCurb・Stage2b_Dan), DoiBuilder.Dan(Stage4a_Dodome), SannoSha(Nozura), TypologyBuilder.Rim(Rim) |
| `Own.SannoNozuraKadoCut(h, i, axis, at)` | 関数 | SannoNozuraKado の片腕を袖の背の面で一度だけ切った版(EDO-0437 2026-09-27・参道の階の前庭の北の縁の口の出隅。 | SannoSha(Nozura) |
| `Own.SannoNozuraKadoCut(h, i, axis, at, arm)` | 関数 | SannoNozuraKadoCut の切った側の腕を arm に詰めた版(EDO-0437 2026-09-27 r16)。 | SannoSha(Nozura) |
| `Own.SannoNozuraDan(risesToPlusX, i)` | 関数 | 野面の乱積みの段の境の駒(2026-09-25・帯 `SukibeiSoto` 29.65 → `SukibeiSoto_Chu` 29.25 の差 0.40 を 1間で流す) = SannoNozura(1.50, ±… | OkabeYashiki(PlaceCurb・Stage2b_Dan), DoiBuilder.Dan(Stage4a_Dodome), SannoSha(Nozura), TypologyBuilder.Rim(Rim) |
| `Own.SannoNozuraMikiri` | string | `Sanno_Nozura_Mikiri.fbx` — 見切りの大きな野面石(男坂の下で城の石垣と野面の乱積みを継ぐ1点)。 | — |
| `Own.SannoNozuraMikiriH(h)` | 関数 | 丈を合わせた見切り石(2026-09-26 EDO-0437・男坂の口の両脇 TW_Zentei_W の端 2 か所)。 | SannoSha(Nozura) |
| `Own.SannoNozuraKiriEnd(deg, atPlusX, faceLonger, h, i)` | 関数 | 片端を斜めの鉛直面で切った野面の乱積みの駒(2026-09-26 EDO-0437・前庭の南の土留め TW_Zentei_SW の東端 / SE の西端を女坂の袖の外面へ当てる)。 | BuildNozura, SannoSha(Nozura) |
| `Own.SannoNozuraNori` | float | 小口を相手の法で切った野面の短い駒(2026-09-26 EDO-0437 第3巡・前庭の W の南の区間 ── 入隅の可動側の端が 通す側 TW_Zentei_SW の見え面の法の楔に入る所)。 | SannoSha(AbutStairsToWalls) |
| `Own.SannoNozuraNoriEnd(len, atPlusX, h)` | 関数 | — | BuildNozura, SannoSha(Nozura) |
| `Own.IshidanSodeNozuraNori(keri, fumi, e, i)` | 関数 | 背を相手の法で切った野面の袖(2026-09-26 EDO-0437 第3巡・参道の階の袖の背が切り込みの出隅の駒の法に当たる所)。 | SannoSha(AbutStairsToWalls) |
| `Own.SannoNozuraFillSandoKai4(side)` | 関数 | 段 4 に面する所だけ天端を埋めた前庭の野面の駒(EDO-0437 r13 2026-09-27)。 | — |
| `Own.SannoNozuraFillBeside(basePath, stair, i, side)` | 関数 | 石段 stair の段 i の脇 side('W'/'E')に合わせて焼いた野面の駒の名 (元の部材 basePath の名 + "_" + 石段 + 段 + 脇)。 | — |
| `Own.SannoDanFit(keri, fumi, w, i, stair)` | 関数 | 両端を相手の野面の石の見える外形に沿わせた段石(EDO-0437 第10巡 2026-09-26 → r11 2026-09-27)。 | SannoSashizuCheck(Check) |
| `Own.IshidanSodeNozuraFit(keri, fumi, stair, side, k, i)` | 関数 | 背を相手の野面の石の見える外形に沿わせた野面の袖(EDO-0437 第10巡 2026-09-26 → r11 2026-09-27)。 | — |
| `Own.IshidanSodeNozura(keri, fumi, i)` | 関数 | 石段の袖 — 野面の乱積み版(2026-09-24)。 | SannoSha(AbutStairsToWalls・Stage2_Kaidan) |
| `Own.SannoIdoIgeta(naikeiMm, igetaTallMm)` | 関数 | 山王社の小庭の井戸 — 井筒(玉石の輪積み)と井桁を一体で。 | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(NiwaIdo) |
| `Own.SannoIdoYakata(pitchMm, nokiMm, muneMm)` | 関数 | 山王社の前庭の井戸屋形(木部) — 四本柱・妻梁・軒桁・棟束・棟木・垂木・切妻こけら葺・破風板・棟押え + 釣瓶の横木と滑車(指図 bom 行22・行25)。 | SannoSha(Stage8_Ido) |
| `Own.SannoIdoIshiki(sideMm, slopeDen)` | 関数 | 山王社の前庭の井戸の板石敷一式 — 板石(東へ水勾配)・敷砂・割栗・井戸の縁石 4 石・礎石 4 石・ 浸透枡(伏せ枡・板蓋)(指図 bom 行26・行27)。 | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(NiwaIdo) |
| `Own.SannoChumon(duKen, dvKen, pX, mX, pZ, mZ)` | 関数 | 山王社の中門(瑞垣門)。一間平唐門・四脚(本柱2+控柱4)・銅瓦葺【S [国宝建造物目録1941]】。 | — |
| `Own.SannoChumon(duKen, dvKen, passMm, widthMm, pX, mX, pZ, mZ)` | 関数 | 山王社の中門(瑞垣門)— 明治16年寸法(ユーザー裁定C 2026-09-14)。 | — |
| `Own.Momiji(size, i=…)` | 関数 | イロハモミジ。⭐ 株立ち3〜5幹・枝が水平に張る(幅が高さを上回る)。 | DoiBuilder.Niwa(ResolveNiwaApi), MatsudairaDewa(ResolveApi), OkabeYashiki(PlantByKey), TypologyBuilder.Niwa(MomijiPalFor) |
| `Own.Ume(size, i=…)` | 関数 | — | DoiBuilder.Niwa(ResolveNiwaApi), MatsudairaDewa(ResolveApi), OkabeYashiki(PlantByKey), TypologyBuilder.Niwa(NiwaUra) |
| `Own.Enoki(size, i=…)` | 関数 | エノキ(一里塚の木)。⭐ 低い位置で数本の大枝に分かれ、枝が斜め上へ 開いて扇形〜半球形の広い樹冠。 | OkabeYashiki(PlantByKey), SannoSha(TreePath), TypologyBuilder.Niwa |
| `Own.Mukunoki(size, i=…)` | 関数 | ムクノキ。エノキに似るが ⭐ 幹がより通直で高く、樹冠は縦長 (幅 &lt; 高さ)。 | OkabeYashiki(PlantByKey), SannoSha(TreePath), TypologyBuilder.Niwa |
| `Own.Keyaki(size, i=…)` | 関数 | ケヤキ。⭐ 箒形 — 短い直幹から大枝が扇状に立ち上がり、上へ広がる 逆三角の樹冠。 | OkabeYashiki(PlantByKey), SannoSha(TreePath), TypologyBuilder.Niwa |
| `Own.TsuruFuji(i=…)` | 関数 | フジ(ノダフジ)が高木の幹に絡む姿。2〜3本の蔓が幹を巻いて登り、 羽状複葉の葉が外へ張り出す。 | OkabeYashiki(PlantByKey) |
| `Own.TsuruTeika(i=…)` | 関数 | テイカカズラ(常緑のつる)。幹に貼り付いて登る細い帯。 | OkabeYashiki(PlantByKey) |
| `Own.TsuruKizuta(i=…)` | 関数 | キヅタ(常緑のつる)。テイカカズラより ⭐ 葉が大きく・帯が広く(約240°)・ 密で、幹を覆う「蔓のマント」になる。 | OkabeYashiki(PlantByKey) |
| `Own.IshigakiSaka(run, drop)` | 関数 | 石段の法面を留める「坂の土留め」。天端が勾配どおりに一直線で斜めに下がる 一枚物(段々に下がるモジュールでは実物の石段の袖にならない)。 | — |
| `Own.Fuchiishi(runKen, w=…)` | 関数 | 切石の縁石(白洲・平場の縁。指図 `fuchi[]`)。 | MatsudairaDewa(Stage6_Zosaku) |
| `Own.NagayaOmote(len)` | 関数 | 長さ可変の表長屋。在庫の `knagaya01c/l/r` を窓割り(bay=2.6874m)で切って 並べ、両端に妻(破風・鬼・妻壁)を継いだ一体物。 | OkabeYashiki(AssetByKey・PlaceOmoteNagaya), Doi(Stage2_Perimeter), MatsudairaDewa(Stage2_Perimeter), NagayaOmote |
| `Own.NagayaOmote2F(len)` | 関数 | 二階建ての表長屋(案A・ユーザー裁定 2026-08-29)。 | OkabeYashiki(AssetByKey・PlaceOmoteNagaya), Doi(Stage2_Perimeter), MatsudairaDewa(Stage2_Perimeter) |
| `Own.NagayaOmoteMon(len, gateFromLeft, nikai)` | 関数 | 長屋門(ユーザー裁定 2026-08-30)— 表長屋の躯体を門の上まで通し、 その足元に門口を抜いた版。 | OkabeYashiki(AssetByKey・GateInNagaya・PlaceOmoteNagaya), DoiBuilder.Mon(Stage3_Mon), MatsudairaDewa(Stage2_Perimeter) |
| `Own.NagayaOmote2FKutai(len)` | 関数 | 躯体の長さ = 呼び寸法の表長屋(二階)(EDO-0502 2026-10-03)。 | BuildTsugime(BodySpanAlong) |
| `Own.KutaiOf(path)` | 関数 | 表長屋・門長屋のパスを、躯体 = 呼び寸法の版(`_kutai`)へ読み替える(在れば)。 | OkabeYashiki(GateInNagaya・PlaceOmoteNagaya), Doi(Stage2_Perimeter), DoiBuilder.Mon(Stage3_Mon) |
| `Own.NagayaOmoteMonKutai(len, gateFromLeft, nikai)` | 関数 | 躯体の長さ = 呼び寸法の門長屋(NagayaOmote2FKutai の口抜き版)。 | — |
| `Own.NagayaOmote2FKutaiMiter(len, thL, thR)` | 関数 | 外へ折れる区画の角で留めた表長屋(躯体 = 呼び寸法・二階)。 | OkabeYashiki(Stage2_Perimeter) |
| `Own.NagayaOmoteMonKutaiMiter(len, gateFromLeft, nikai, thL, thR)` | 関数 | NagayaOmoteMonKutai の端の妻壁を区画の線の折れ(全角 thL = −X 端・thR = +X 端・度)の二等分の面へ寝かせた版 (NagayaOmote2FKutaiMiter の門長屋版)。 | — |
| `Own.NagayaOmote(len, tsuma)` | 関数 | tsuma=false は両端を突き付けにした版(`--ends none`)。 | OkabeYashiki(AssetByKey・PlaceOmoteNagaya), Doi(Stage2_Perimeter), MatsudairaDewa(Stage2_Perimeter), NagayaOmote |
| `Own.ObiNagaya(wKen, dKen)` | 関数 | 崖下の詰人長屋(岡部邸 `service` の N1/N2、`roofs.ObiNagaya`)。 | OkabeYashiki(AssetByKey・ReportNishiRest), TypologyBuilder.Jisha(JishaOmoya) |
| `Own.ObiNagaya(wKen)` | 関数 | 梁間は家臣長屋の規約どおり 2.5間(`const.nagayaD` = 4.545m)固定。 | OkabeYashiki(AssetByKey・ReportNishiRest), TypologyBuilder.Jisha(JishaOmoya) |
| `Own.ObiMonooki` | string | 崖下の物置(岡部邸 `service.M1`)。 | OkabeYashiki(AssetByKey), TypologyBuilder.Jisha(JishaOmoya) |
| `Own.ObiKawaya` | string | 崖下のかわや(岡部邸 `service.K_Obi`)。 | OkabeYashiki(AssetByKey) |
| `Own.UraNagaya(wKen)` | 関数 | 裏長屋(裏店)— 割長屋。町屋24町の路地に並ぶ九尺二間の棟(類型共用)。 | BuildMachiya(MachiyaRun・UraNagayaRun), TypologyBuilder.Machiya(Machiya・UraNagaya) |
| `Own.UraNagayaMunewari(wKen)` | 関数 | 裏長屋 — 棟割長屋(背中合わせ)。UraNagaya と同じ割りだが 奥行 4間(2間+2間)で、大棟を挟んで ±Z の両面に戸が並ぶ。 | BuildMachiya(MachiyaRun・UraNagayaRun), TypologyBuilder.Machiya(Machiya・UraNagaya) |
| `Own.Sanmon` | string | 山門 — 四脚門(類型共用・寺4区画)。 | Typology(GatePath) |
| `Own.Yakuimon` | string | 薬医門(類型共用・社家=神主の屋敷)。門口 3.00m・本柱2 + 控柱2(後ろだけ)・ 切妻本瓦。 | Typology(GatePath) |
| `Own.Shoro(ken)` | 関数 | 鐘楼 — 袴腰(類型共用・寺4区画)。基壇 ken 間角・ 袴腰・上層は吹き放ち(柱間2間)・高欄・梵鐘・入母屋本瓦。 | TypologyBuilder.Jisha(JishaOmoya) |
| `Own.Shoro(kenX, kenZ)` | 関数 | 鐘楼 — 非正方(2026-09-23 EDO-0395 施主裁定B)。 | TypologyBuilder.Jisha(JishaOmoya) |
| `Own.Koro(ken)` | 関数 | 鼓楼 — 袴腰(Shoro と同じ躯体に太鼓を吊った対の棟)。 | — |
| `Own.Koro(kenX, kenZ)` | 関数 | 鼓楼 — 非正方(Shoro と同じ躯体に太鼓)。 | — |
| `Own.Bochi(wKen, dKen)` | 関数 | 墓地の一画(類型共用・寺3区画)。切石の低い囲い + 半間ピッチの墓石 59基 (角柱・櫛形・板碑の3型)+ 卒塔婆。 | TypologyBuilder.Jisha(JishaOmoya) |
| `Own.Kuri(wKen, dKen)` | 関数 | 庫裏(類型共用・寺と塔頭の台所兼住居)。 | TypologyBuilder.Jisha(JishaOmoya) |
| `Own.Munamon(w, opened)` | 関数 | 通用口の棟門(岡部邸 `komon.Tsuyodo` — 袋小路に開く勝手口)。 | DoiBuilder.Mon(Stage3_Mon), OkabeYashiki(AssetByKey), Typology(GatePath) |
| `Own.Munamon(w)` | 関数 | — | DoiBuilder.Mon(Stage3_Mon), OkabeYashiki(AssetByKey), Typology(GatePath) |
| `Own.KabukimonNoSode` | string | 袖の無い冠木門(旗本屋敷の表門・類型 gate=kabukimon。 | Typology(GateChoices) |
| `Own.MachiKido(haba)` | 関数 | 町木戸(町境・参道の口を夜に閉じる木戸。 | TypologyBuilder.Machiya(MachiKido・MachiyaFrontEdges), BuildMachiya(UraNagayaRun) |
| `Own.MachiKido(haba, keisha)` | 関数 | 道の横断勾配に追従する町木戸。keisha = −X 端から +X 端への地面の下がり[m] (正 = +X が低い)。 | TypologyBuilder.Machiya(MachiKido・MachiyaFrontEdges), BuildMachiya(UraNagayaRun) |
| `Own.MarutaTesuri` | string | 丸太の手すり 1スパン(岡部邸 `routes.R_Katte.outsideRail.tesuri`)。 | OkabeYashiki(AssetByKey) |
| `Own.MarutaTesuriPost` | string | 手すりの run の端に足す柱1本。ピボット = 柱の芯・地盤レベル。 | OkabeYashiki(AssetByKey・PlaceTesuri) |
| `Own.Kui(dia)` | 関数 | 汀の杭 1本(岡部邸 `nishi.kuiretsu`)。 | OkabeYashiki(AssetByKey・PlaceKuiretsu・ReportNishiRest), BuildRun(FenceRun・KuiRun) |
| `Own.KuiNuki` | string | 杭列の貫(`nishi.kuiretsu.nuki`)。 | OkabeYashiki(AssetByKey・PlaceKuiretsu) |
| `Own.GotenRoofIrimoya(wKen, dKen)` | 関数 | 御殿の入母屋屋根を間数で引く。⚠ 実体は Goten.RoofIrimoya_ で、 これはそこへの転送(⛔ パスの literal を二重に書かないため)。 | OkabeYashiki(AssetByKey・PlaceMunes) |
| `Own.Kado(part, deg)` | 関数 | 折れ角のある隅の部材(留め継ぎ)。生成は Tools/Blender/build_kado.py。 | BuildKado(KadoGauge), MatsudairaDewa(PlaceKado・RendBounds), OkabeYashiki(PlaceKado) |
| `Own.Kado(part, deg, armIn, armOut, armFull)` | 関数 | 腕の短い隅(Kado と同じ留め継ぎ・同じ据え・同じ s)。 | BuildKado(KadoGauge), MatsudairaDewa(PlaceKado・RendBounds), OkabeYashiki(PlaceKado) |
| `Own.IshigakiKado(deg, h)` | 関数 | 丈違いの石垣の隅(`Castle Wall` の留め継ぎ・丈 h m)。 | BuildKado(KadoArm), Doi(Stage2_Perimeter), OkabeYashiki(Stage2b_Dan), SannoSha(Stage3_Dodome) |
| `Own.IshigakiKado(deg, h, armNegZ, armPosX)` | 関数 | 腕の短い石垣の隅(IshigakiKado と同じ留め継ぎ・同じ据え: position = 両腕の控えの線の交点 P・y = 天端 − h / yaw = 入りの run の駒の yaw / scale = 1)。 | BuildKado(KadoArm), Doi(Stage2_Perimeter), OkabeYashiki(Stage2b_Dan), SannoSha(Stage3_Dodome) |
| `Own.IshigakiKado2(deg1, deg2, mid, h, armNegZ, armPosX)` | 関数 | 二重折れの石垣の隅(`Castle Wall` の留め継ぎを二つ一体に)。 | BuildKado(PlaceRunKado), OkabeYashiki(Stage2b_Dan) |
| `Own.IshigakiChoku(h)` | 関数 | 丈違いの城の石垣の直線の駒(`JC.CastleWall` 1 枚・走り 2.00 を丈 h m へ下へ継いだ物)。 | BuildDanIshigaki(CastleWallOfExpose) |
| `Own.DobeiKiri(deg, faceLonger, cutAtMinusX=…)` | 関数 | 端を隣の辺の線で斜めに切った練塀の駒(`DobeiRun` の組 = `s_hei_center` 表裏2枚を実寸で 1 枚分・走り 2.990)。 | OkabeYashiki(KiriEnd・MiterOf) |
| `Own.NagayaKado(deg, armNegZ, armPosX, tsuma)` | 関数 | 出隅の隅長屋(L 字の長屋の角・EDO-0500 2026-10-01 観理院 北東の施主指摘 ── 妻を突っ込む納めは屋根が重なり窓が途中で切れた)。 | BuildRun(NagayaKadoPlace) |
| `Own.NagayaTsuma2(len)` | 関数 | 両端とも妻で閉じた一棟の長屋(真っ直ぐ・折らない)。 | BuildRun(OutsideParcel・SwapTsuma2) |
| `Own.NagayaKado90(armNegZ, armPosX)` | 関数 | NagayaKado の 90°・妻なし(`Nagaya_Kado_90_A&lt;negZ&gt;x&lt;posX&gt;`)。 | BuildRun(KadoAt) |
| `Own.IshigakiKiri(deg, atPlusZ, faceLonger)` | 関数 | 片端を斜めの鉛直面で切った城の石垣の駒(`JC.CastleWall` を走りに 2 枚つないだ 4.00m・丈 4.00・EDO-0430)。 | — |
| `Own.MShop01` | string | `M_Shop01.mat` | — |
| `Own.MShop02` | string | `M_Shop02.mat` | — |
| `Own.MKido` | string | `M_Kido.mat` | — |
| `Own.MKidobanya` | string | `M_Kidobanya.mat` | — |
| `Own.MSannoDanishi` | string | `Danishi.mat` — 山王社の段石の材(`Danishi`)。 | — |
| `Own.MJishinban` | string | `M_Jishinban.mat` | — |
| `Own.MGateStone` | string | `GateStone.mat` | — |
| `Own.Mat(name)` | 関数 | 自作マテリアルの名前引き(規則11: パスの literal はここ以外に書かない) | Build(DressBare), BuildRun(TintFoliage), SolidMat(Named) |
| `Own.SolidMatDir` | string | `Solid` — 色だけの無地の材質(URP/Lit)を置く場所。 | SolidMat(Get・Migrate) |
| `Own.SolidMat(hex)` | 関数 | — | SolidMat(Get) |
| `Own.GenMeshDir` | string | `Gen` — コードで起こしたメッシュの置き場。`EdoSolidMesh.Save(mesh, 名)` が `&lt;名&gt;_&lt;中身の指紋&gt;.asset` で 1 枚だけ起こす(EDO-0332)。 | SolidMesh(Get・Save), BuildHifu(ClearEdgeSkins) |
| `Own.GenMesh(name)` | 関数 | — | SolidMesh(Get・Save) |
| `Own.SkinMatDir` | string | `Hifu` — 縁の皮(地形の穴の縁から部材の面までを描くメッシュ・`EdoBuild.CutEdgeSkin`)の材質の置き場。 | BuildHifu(SkinMaterials) |
| `Own.SkinMat(terrain, pass)` | 関数 | — | BuildHifu(SkinMaterials) |
| `Own.MatsudairaOmotemon` | string | `Matsudaira_Omotemon.fbx` — 松江松平邸の表門 — 屋根なしの冠木門(角柱・冠木・内開きの板戸)。 | MatsudairaDewa(Stage5_Mon) |
| `Own.Sodebei(len, kuguri=…)` | 関数 | 袖塀(長さ可変・潜り戸つき)— 表門の脇で外周を塞ぐ練塀。 | MatsudairaDewa(Stage5_Mon) |
| `Own.Dobei2m` | string | `Dobei2m.fbx` — 練塀(築地塀)の一体物 — 腰の下見板・貫・白漆喰・本瓦の両流れが1駒に焼いてある (`Tools/Blender/build_dobei.py`)。 | BuildRun(NeribeiRun・NeribeiStepRun), BuildRim(FenceFaceOffsets), Doi(Stage2_Perimeter), DoiBuilder.Mon(Stage3_Mon) ほか1 |
| `Own.Dobei2mNunoishi` | string | `Dobei2m_Nunoishi.fbx` — Dobei2m の下に据える布石(腰の石) — 切石の布積み 4段の1駒(EDO-0477)。 | BuildGamae(DodomeAlongEdge・EnsureKidanProbe・HirabaStation…), BuildRun(DanPlanCore・NeribeiStepRun) |
| `Own.Dobei2mEnd` | string | `Dobei2m_End.fbx` — Dobei2m の妻を塞いだ端部(x=0 側の小口に袖瓦を葺いて閉じた駒。 | BuildRun(NeribeiRun・NeribeiStepRun), BuildGamae(FenceEndPiece), PartSpec(Bake) |
| `Own.MatsudairaBansho(w)` | 関数 | 松江松平邸の表門の番所 — 向唐破風・出格子・切石畳出の基壇。 | MatsudairaDewa(Stage5_Mon) |
| `Own.MatsudairaBanshoBodyBand` | float[] | ⭐⭐ 番所の「躯体」を測るための帯 — ピボット(= 走りの芯・基壇の下端)からの 局所 y[m]。 | MatsudairaDewa(Stage5_Mon) |
| `Own.NeishiLong` | float[] | 板塀の根石(玉石) — 松江松平邸の中仕切の板塀 8 run(延長 444.2m・約 800 石)。 | MatsudairaDewa(NeishiPlace) |
| `Own.Neishi(lng)` | 関数 | — | MatsudairaDewa(NeishiPlace) |

## Own.Matsudaira

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Own.Matsudaira.Dozo` | string | 土蔵 4×7間。実寸 13.76(X) × 7.12(Y) × 8.89(Z) | MatsudairaDewa(Stage6_Zosaku), OkabeYashiki(AssetByKey) |
| `Own.Matsudaira.Koya` | string | 御作事小屋 10×4間(片側の長手が開いた小屋)。 | MatsudairaDewa(Stage6_Zosaku), OkabeYashiki(AssetByKey) |
| `Own.Matsudaira.Sukiya` | string | 御茶屋(数寄屋)2.5間角・宝形の柿葺。 | MatsudairaDewa(Stage6_Zosaku) |
| `Own.Matsudaira.Inari` | string | 稲荷社(明神鳥居+一間社流造の小祠)。実寸 2.50 × 2.76 × 3.34。 | MatsudairaDewa(ResolveApi) |
| `Own.Matsudaira.InariHokora` | string | — | MatsudairaDewa(ResolveApi) |
| `Own.Matsudaira.GenMeshDir` | string | `` — 生成メッシュの保存先(参道の玉砂利の帯など、指図の折れ線から起こす面)。 | — |
| `Own.Matsudaira.Ido` | string | 石井戸枠+釣瓶の桁。実寸 1.90 × 2.21 × 1.90。 | MatsudairaDewa(Stage6_Zosaku), OkabeYashiki(AssetByKey) |
| `Own.Matsudaira.Yagura` | string | 二重の隅櫓 3間角。実寸 7.39 × 8.64 × 7.39。 | MatsudairaDewa(Stage6_Zosaku・YaguraKeepout・YaguraSeat) |

## Own.Typ

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Own.Typ.Komegura` | string | 米蔵 3間(梁間)× 4間(桁行)。石腰+白漆喰の大壁・妻に観音扉・切妻の本瓦。 | OkabeYashiki(AssetByKey), Typology(Plan) |
| `Own.Typ.Umaya` | string | 厩 3間(梁間)× 4間(桁行)。板壁・桟瓦・前面(+Z)は吹き放ちで 足元に半高の板壁、馬房を4つ(桁行4間なので1房ちょうど1間)。 | Typology(Plan) |
| `Own.Typ.SakujiKoya` | string | 作事小屋 2間(梁間)× 3間(桁行)。 | Typology(Plan), TypologyBuilder.Jisha(JishaOmoya) |
| `Own.Typ.Takeyarai` | string | 竹矢来(たけやらい)— 2間モジュールの透ける囲い(類型共用・EDO-0363)。 | BuildRun(FenceRun・NeribeiStepRun), BuildGamae(FenceEndPiece), PartSpec(Bake) |
| `Own.Typ.Omotedana(wKen)` | 関数 | 表店(おもてだな)— 町屋24町の通りに面して並ぶ2階建ての商家(類型共用)。 | TypologyBuilder.Machiya(OmotedanaFor), BuildMachiya |
| `Own.Typ.Omotedana(wKen, dKen)` | 関数 | 奥行を詰めた表店。背後の余地が 4間(7.272m)に足りない筆で使う。 | TypologyBuilder.Machiya(OmotedanaFor), BuildMachiya |
| `Own.Typ.OmotedanaHira(wKen, dKen)` | 関数 | 平屋の小店(厨子二階の無い表店・裏通りや門前の端の店)。 | TypologyBuilder.Machiya(OmotedanaFor) |

## Own(続き)

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Own.Umaya` | string | 厩 4×9間(岡部邸 `service.Umaya`)。 | OkabeYashiki(AssetByKey) |
| `Own.Tomomachi` | string | 供待 3×5間(岡部邸 `service.Tomomachi`)。 | OkabeYashiki(AssetByKey) |
| `Own.Kura4x5` | string | 土蔵 4×5間(岡部邸 `service.Kura1` / `Kura2`・EDO-0502)。 | OkabeYashiki(AssetByKey) |
| `Own.Makigura` | string | 薪蔵(板倉) 4×3間(岡部邸 `service.Makigura`・EDO-0502)。 | OkabeYashiki(AssetByKey) |
| `Own.Tomomachi35` | string | 供待 3.5×5間(岡部邸 `service.Tomomachi`・EDO-0502 で 3×5 から改めた)。 | OkabeYashiki(AssetByKey) |
| `Own.NandoKoya` | string | 納戸小屋 1.5×1間・板葺(岡部邸 `service.Nando_Nagatsubone`)。 | OkabeYashiki(AssetByKey) |
| `Own.Kurumayose` | string | 車寄 3間(間口)× 2間(奥行)(岡部邸 `munes[0]` / `roofs.Goten_Kurumayose`)。 | OkabeYashiki(AssetByKey) |
| `Own.KurumayoseCut` | string | 車寄(切り欠き済み) — 玄関棟の屋根へ差し込むための納めを部材の側で解いた版 【2026-09-04 ユーザー裁定10=A】。 | OkabeYashiki(AssetByKey) |
| `Own.Jouguchi` | string | 御錠口 3間角(岡部邸 `links[2]` L_Jouguchi)。 | OkabeYashiki(AssetByKey) |
| `Own.Inari15` | string | 稲荷社の小祠 1.5間角(岡部邸 `service.Inari`)。 | Doi(PlaceService), DoiBuilder.Niwa(ResolveNiwaApi), OkabeYashiki(AssetByKey), TypologyBuilder.Inari(Inari) |
| `Own.Torii` | string | 素木の明神鳥居(稲荷の参道の点景)。⛔ 朱に塗らない(指図の明文)。 | DoiBuilder.Niwa(ResolveNiwaApi), MatsudairaDewa(ResolveApi), OkabeYashiki(AssetByKey), TypologyBuilder.Inari(Inari) |
| `Own.Noshibei(len)` | 関数 | のし塀(熨斗瓦を載せた白壁の袖塀)。岡部邸の結界 `kekkai` の7本。 | OkabeYashiki(AssetByKey) |
| `Own.Kido(w)` | 関数 | 結界の木戸(のし塀 `kekkai[].gap` の開口を塞ぐ)。 | Doi(KomonAsset), DoiBuilder.Niwa(ResolveNiwaApi), OkabeYashiki(AssetByKey) |
| `Own.HoriKido` | string | `HoriKido.fbx` — 汀の柵の潜り(`nishi.saku.kuguri`・辺5 の s=55.7)。 | OkabeYashiki(AssetByKey) |
| `Own.HoriSaku` | string | `HoriSaku.fbx` — 汀の木柵 1スパン(`fences[0]` F_Hori・辺5 の全長 s0〜80.589)。 | BuildRun(FenceRun), OkabeYashiki(PlaceFences) |
| `Own.HoriSakuPost` | string | `HoriSakuPost.fbx` — 汀の木柵の端の杭。⛔ 足さないと run の最後の板が宙で終わる。 | OkabeYashiki(PlaceFences) |
| `Own.TategoshiSaku(h=…)` | 関数 | 竪格子の柵 1間(EDO-0503・町屋の表店の列の端に残った空き 1〜3m を閉じる仕切り)。 | BuildRun(FenceRun) |
| `Own.TategoshiSakuPost(h=…)` | 関数 | 竪格子の柵の端柱(TategoshiSaku の run の +X 端を受ける柱1本・笠木つき)。 | — |
| `Own.ItabeiIta` | string | `Itabei_Ita_1.410.fbx` — 板塀の板(柱なし)1間。在庫の板塀 Eg.Itabei5(柱と板が一体の 5間の駒)を 柱と板に分けた組の板の方(2026-09-26・EDO-0437 山王 前庭の南の板塀 `Ita_ZSE`)。 | SannoSha(Stage4_Kakoi) |
| `Own.ItabeiHashira` | string | `Itabei_Hashira_N0.30.fbx` — 板塀の柱1本(ItabeiIta と組・2026-09-26・EDO-0437)。 | — |
| `Own.ItabeiJifuku` | string | `Itabei_Jifuku_1.410_Hk0.60.fbx` — 板塀の地覆(板の下の横木)1間・光付けの代つき(2026-09-27・EDO-0437 施主裁定 案A「板を石の天端・地面まで下ろす」)。 | BuildRun(PostBoardRun), SannoSha(Stage4_Kakoi) |
| `Own.ItabeiHashiraHk` | string | `Itabei_Hashira_Hk0.60.fbx` — 板塀の柱1本・光付けの代つき(ItabeiJifuku と組・2026-09-27・EDO-0437 案A)。 | BuildRun(PostBoardRun), SannoSha(Stage4_Kakoi) |
| `Own.Ishigumi(i)` | 関数 | 庭石1個(景石・石組護岸の石・岩島・中島の汀石・荒磯の立石を全部これで置く)。 | DoiBuilder.Niwa(Niwa_B_Gogan・Niwa_D_Tenkei・ResolveNiwaApi), OkabeYashiki(PlaceNiwaItem), TypologyBuilder.Niwa(MomijiPalFor) |
| `Own.Tobiishi(i)` | 関数 | 飛石・沢飛石1枚(天端が平ら)。⭕ 同じ photoscanned rock の頭を水平に 落として天端を作り、縁は自然石のまま残してある(⛔ 切石に見せない)。 | DoiBuilder.Niwa(Niwa_D_Tenkei・ResolveNiwaApi), OkabeYashiki(PlaceNiwaItem), TypologyBuilder.Niwa(MomijiPalFor) |
| `Own.Kutsunugi` | string | 沓脱石(根府川石)。天端を平らに落とした自然石。 | OkabeYashiki(PlaceNiwaItem) |
| `Own.Tateishi(size, variant)` | 関数 | 立石(縦長の庭石)3種。松江松平上屋敷の庭(`tenkei[].stones[]` の 主石・副石・鏡石、`sensui.iwaya` の鏡石ほか)向け。 | DoiBuilder.Niwa(ResolveNiwaApi), MatsudairaDewa(ResolveApi) |
| `Own.Hiraishi(kind)` | 関数 | 大型の平石2種(天井石・伏石)。松江松平上屋敷の庭向け。 | MatsudairaDewa(ResolveApi) |
| `Own.Ishibashi()` | 関数 | 切石橋(切石の一枚物の橋)。松江松平上屋敷の庭向け。 | MatsudairaDewa(ResolveApi) |
| `Own.HatakeUne` | string | 菜園の畝(うね)1本・1間(樹下邸の菜園・EDO-0532)。 | TypologyBuilder.Katte(Katte) |
| `Own.Ikegaki(end)` | 関数 | 刈込の生垣モジュール(ツゲ・マサキの見立て・1 間 × 1.90m × 0.80m、葉カード・材 M_FJG_Plant_Boxwood_01_Spring・LOD1)。 | MatsudairaDewaBuilder.Niwa(Stage6d_Tenkei) |
| `Own.YotsumeGaki(h)` | 関数 | 四つ目垣 1スパン(1間)。親柱1 + 立子5 + 胴縁(h1.2 で4段 / h0.9 で3段)+ 棕櫚縄の結び。 | OkabeYashiki(PlaceDanKaki・PlaceNiwaItem・PlaceTakegaki), DoiBuilder.Niwa(Niwa_G_Kaki・ResolveNiwaApi), Doi(PlaceTakegaki) |
| `Own.YotsumeGakiPost(h)` | 関数 | 四つ目垣の run の +X 端に足す親柱1本。 | OkabeYashiki(PlaceDanKaki・PlaceNiwaItem・PlaceTakegaki), DoiBuilder.Niwa(Niwa_G_Kaki・ResolveNiwaApi), Doi(PlaceTakegaki) |
| `Own.KenninjiGaki(h)` | 関数 | 建仁寺垣 1スパン(1間)。親柱1 + 胴縁3(裏)+ 割竹の立子35枚を隙間なく + 押縁3段 + 玉縁 + 結び12。 | DoiBuilder.Niwa(Niwa_G_Kaki・ResolveNiwaApi), OkabeYashiki(PlaceDanKaki・PlaceNiwaItem), BuildRun(FenceRun) |
| `Own.KenninjiGakiPost(h)` | 関数 | 建仁寺垣の run の +X 端に足す親柱1本。 | DoiBuilder.Niwa(Niwa_G_Kaki・ResolveNiwaApi), OkabeYashiki(PlaceDanKaki・PlaceNiwaItem) |
| `Own.DoiNagayamon` | string | 土井邸の表門 = 長屋門(片番所 格子付・片潜門)。 | Doi(GateSpan), DoiBuilder.Mon(Stage3_Mon) |
| `Own.DoiUmaya` | string | 厩 5.5×7間(土井邸 `munes.Umaya`)。 | Doi(PlaceUmaya) |
| `Own.DoiKachu(ketaKen)` | 関数 | 家中長屋(邸内の長屋・土井邸 `service.Kachu_N1/N2/N3/S1/Y` の5棟)。 | — |
| `Own.DoiKura(hariKen, ketaKen)` | 関数 | 土蔵(土井邸 `service` の `Komegura` / `Kura1` / `Kura2`)。 | Doi(PlaceService) |
| `Own.DoiIdo` | string | 井戸(土井邸 `wells` の5口とも同じ部材)。 | Doi(PlaceWells) |
| `Own.DoiChozu` | string | 手水石(水盤) — 稲荷の社前・参道の西(`yashiro.chozu`)。 | DoiBuilder.Niwa(Niwa_F_Yashiro), TypologyBuilder.Keidai(NiwaKeidai) |
| `Own.DoiKutsunugi` | string | 沓脱石 — 奥棟の南入側の前の一枚石(`gardens.G_Okuniwa.kutsunugi.Kutsunugi_Oku`)。 | DoiBuilder.Niwa(ResolveNiwaApi) |
| `Own.DoiMizushiriShiki` | string | 水尻の石の閾(余水吐)。汀 #14(西端)、天端は `mizu.mizushiri.shiki.sill` (水面 +0.05)。 | DoiBuilder.Niwa(Niwa_C_Mizushiri) |
| `Own.DoiMizushiriHakiguchi` | string | 水尻の石組の吐き口(埋樋の終点)。実寸 0.950(X) × 0.740(Y) × 0.820(Z)。 | DoiBuilder.Niwa(Niwa_C_Mizushiri) |
| `Own.DoiOtoshimizo` | string | 水尻の石敷きの落とし溝 — 1m モジュール。 | DoiBuilder.Niwa(Niwa_C_Mizushiri) |
| `Own.Rangui(dia)` | 関数 | 乱杭1本(汀を留める細い杭。`gardens[].rangui`)。 | DoiBuilder.Niwa(Niwa_B_Gogan), OkabeYashiki(PlaceNiwaItem) |
| `Own.Toro` | string | 雪見灯籠。⚠ 実体は在庫の Eg.ToroYukimi(edogoyomi)で、 これはそこへの転送(⛔ パスの literal を二重に書かないため)。 | DoiBuilder.Niwa(ResolveNiwaApi), TypologyBuilder.Niwa(NiwaToro) |
| `Own.LayerGrass` | string | `L_grass.terrainlayer` — 地表層(TerrainLayer)。「実寸」= 繰り返しの一枚の大きさ `m_TileSize`[m]。 | IshigakiFit |
| `Own.LayerDirt` | string | `L_dirt.terrainlayer` — 土(踏み固めた道・白洲・前庭)。タイル 8×8m | — |
| `Own.LayerBare` | string | `L_bare.terrainlayer` — 裸地(切土の肌・法面)。タイル 11×11m | — |
| `Own.LayerRock` | string | `L_rock.terrainlayer` — 岩(崖・露岩)。タイル 7×7m。⚠ 4層のうちこれだけ `Smoothness` 0.15(濡れて見える) | — |
| `Own.LayerShirasu` | string | `L_shirasu.terrainlayer` — 白砂利(参道・前庭の白洲)。タイル 3×3m。 | GardenSurfacePaint(EnsureLayers) |
| `Own.LayerMoss` | string | `L_moss.terrainlayer` — 苔(坪庭)。タイル 3×3m。典拠テクスチャは Waldemarst FreeJapaneseGarden の `Ground_Moss_01`。 | GardenSurfacePaint(EnsureLayers) |
| `Own.GrassLowA` | string | `GrassLowA.prefab` — 詳細植生(Detail)の下草。丈は 0.11m — 地表の毛羽で、草叢ではない。 | — |
| `Own.GrassLowB` | string | `GrassLowB.prefab` | — |

## (直下)

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `OwnPath(api)` | 関数 | 指図が書いた呼び名を部材のパスへ解く。(2026-09-22・EDO-0261 ②) 指図の `munes[].partFrom` / `torii[].partFrom` / `planting[].part` は `… | SannoSha(PartFromPath・Stage6_Shaden) |

## PartSpecs

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `PartSpecs.Dir` | string | `` — 札の置き場。ファイル名 = 部材の資産名(拡張子なし)+ `.json`。 | PartSpec(FileFor・Reload・Save…), PartSpecTests(門の語はすべて札を持つ) |
| `PartSpecs.GateKinds` | string | 類型表の門の語 → 札のファイル名(C# の試験と Python の関門が同じ表を読む)。 | PartSpec(GateKinds・Reload) |

## Scenes

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `Scenes.Akasaka` | string | `Akasaka.unity` — 本番の一枚。 | Koba(BackToAkasaka・Harvest・OnCompile…), AppBuild(Build・OnProcessScene・OnlyAkasaka) |
| `Scenes.Koba` | string | `Koba.unity` — 作業場 — 建て直しの輪を回す軽いシーン(地形+光+対象邸+20m 以内の隣)。 | Koba(Open・Shitateru) |

## App

| 名 | 種 | 中身・注釈の一文目 | 使っている所 |
|---|---|---|---|
| `App.BuildDir` | string | `Builds` — 書き出し先(gitignore の Builds/)。 | AppBuild(Build) |
| `App.PcRPAsset` | string | `PC_RPAsset.asset` — エディタの URP 資産(App の複写元)。 | AppBuild(EnsureAppPipeline) |
| `App.RPAsset` | string | `App_RPAsset.asset` — アプリだけが使う URP 資産(品質 App)。 | AppBuild(EnsureAppPipeline) |
| `App.EditorOnlyRoots` | string[] | 図の上の置き場 — 書き出しから外すルート。 | AppBuild(OnProcessScene) |
| `App.MeshLodModels` | string[] | 遠くで面を自動で間引く(Mesh LOD)模型。 | AppBuild(DropInactive・Reimport) |
