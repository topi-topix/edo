# アセット目録 — 用途別インデックス

**「〜を再現して」と言われたら、フォルダを掘る前にここを見る。**
無い物を無いと即答するためのリストでもある(→ §9)。

- 全 2,700 点の生データ: [`asset-index.tsv`](asset-index.tsv)(1行1アセット・タブ区切り)
- フォルダ別の件数: [`asset-index-summary.md`](asset-index-summary.md)
- 再生成: Unity で **Edo ▸ アセット目録 ▸ 目録を再生成**
  (`Assets/Edo/Scripts/Editor/EdoAssetCatalog.cs`)

## 0. 読み方(先に3つだけ)

1. **寸法は scale=1 で置いたときの実寸[m]**(X×Y×Z、ルート自身の補正スケール込み)。
   `pivot_bottom` は「ピボットから最下端までの y」。**0 なら足元がピボット**、
   −1.0 なら **1m 埋まった状態が原点**(edogoyomi の門・長屋がこれ)。
2. **edogoyomi は共通スケール ES = 1.818 を掛けて使う。** 下表の寸法は生寸法なので、
   実寸は ×1.818。例: `kura.obj` 3.43 → 6.2m の土蔵。
3. **`Meshes/` でなく `Prefabs/` を置く。** Japanese Castle / Village Kit は同じ物が
   `Meshes/*.fbx` と `Prefabs/*.prefab` に二重にある(目録の件数が倍なのはこのため)。
   マテリアルが付いているのはプレハブ側。

### パックごとに階層が違う件

Asset Store 製(Japanese Castle / Village Kit / Waldemarst / NatureManufacture)は
**用途別フォルダ**(`Prefabs/Exterior/...`)、江戸暦は **商品1点=1フォルダ**の平置きで、
中には Poser 由来の `Runtime/Geometries/Honey/` が挟まる。ベンダーの梱包の違いなので**揃えない**
(揃えても gitignore されていて version 管理されず、再 import で元に戻り、パスを直書きしている
ビルダー19本が `LoadAssetAtPath → null` で静かに壊れる)。代わりに**接頭辞で読む**:

| 接頭辞 | 中身 | 例 |
|---|---|---|
| `es_` | 江戸 street シリーズ = **建物**。ほぼ全部使える | `es_kura`(蔵)`es_nmon`(長屋門)`es_shop01` |
| `obj_` | 屋外の**構造物・道具**。使える | `obj_itabei`(板塀)`obj_tsujiandon`(辻行灯) |
| `t_` | **石灯籠** | `t_kasuga` `t_yukimi` `t_oribe` |
| `s_` | **石造物**(石仏・塔)。⚠ スケール壊れが多い | `s_jizo` `s_gorin` `s_hokyoin` |
| `pp_` `pp2_` | Poser **props**。屋内小物・座敷・屋台。obj が深い階層にある | `pp_sobaya_yatai` `pp2_kakechaya` |
| `cr2_` | Poser **キャラクター**の衣装・馬具。素体が無いので**使えない** | `cr2_m3shokunin` `cr2_baguset` |
| 接頭辞なし | 髷・簪などキャラ部品。使えない | `marumage` `icho-gaeshi` |

なお **4パックのデモシーンは削除済み**(2026-08-14)。プレハブ本体は残っているので配置には影響しない。
再 import すると戻るが、また消してよい。

**コードから使うときはパスを直書きしない。** `Assets/Edo/Scripts/Editor/EdoAssets.cs` の定数
(`EdoAssets.Eg.Kura` / `EdoAssets.VK.BigHouse` / `EdoAssets.JG.PineBig01` …)を経由する。
`LoadAssetAtPath` は存在しないパスでも例外を投げず `null` を返すので、直書きは静かに壊れる。

grep の例:

```bash
grep -iE "gate|mon" docs/asset-index.tsv | awk -F'\t' '$5>5'   # 幅5m超の門らしき物
```

---

## 1. 門

| 欲しい物 | アセット | 生寸法(W×H×D) | 備考 |
|---|---|---|---|
| 長屋門 | `edogoyomi/es_nmon/nagayamon.obj` | 12.37×2.81×3.31 | ES後 **22.5m**。扉側=ローカル −Z |
| 長屋門(農家) | `edogoyomi/obj_nagayamon_nouka/nagayamon_nouka.obj` | 7.64×2.85×2.74 | ES後14m。在方の格 |
| 表門(薬医門系) | `edogoyomi/es_kmon/k_mon.obj` | 7.93×3.68×4.77 | ES後 **14.4m**。本体はピボットの −Z 側 8.66m |
| 表門(小) | `edogoyomi/es_hmon/h_mon.obj` | 8.47×2.81×3.31 | ES後15.4m |
| 冠木門 | `edogoyomi/es_kabukimon/kabukimon.obj` | 4.43×2.06×0.65 | ES後8.1m(実体半幅3.87) |
| 木戸(町の) | `edogoyomi/es_kido/kido_open.obj` | 2.56×0.98×0.71 | 開いた状態。番屋は `es_kidobanya` |
| **櫓門** | `Japanese Castle/Prefabs/Yaguramon A.prefab` | 21.15×11.3×11.15 | 城郭規模。虎御門で使用中 |
| 城門(枡形の扉) | `Japanese Castle/.../Walls/Gate Castle Exterior.prefab` | 4×4×1.97 | +End L/R。壁に嵌める |
| 門(民家・農家) | `Japanese Village Kit/Prefabs/Fences/gate.prefab` | 1.7×5.14×7.43 | 高5.1m。竹垣とセット |
| 番所(門脇) | `edogoyomi/es_dbansho/dbansho.obj` | 1.99×1.93×1.17 | ES後3.6×2.1m。前面 +Z |

⚠ `pp_yakuimon` / `pp_koraimon` は Poser 形式(.pp2)で **Unity にインポートされない**。

## 2. 塀・垣・柵

| 欲しい物 | アセット | 生寸法 | 備考 |
|---|---|---|---|
| 土塀(築地塀) | `edogoyomi/es_dobei/s_hei_center.obj` | 1.64×1.46×0.63 | **片面ポリ**。表裏0.2mペアで置く。`_l` `_r` `_corner` あり |
| 板塀 | `edogoyomi/obj_itabei/itabei5.obj` | 4.12×0.8×0.08 | ES後7.49m・h1.45。単体 `itabei.obj`・柱 `_pole` |
| 矢来・水際の柵 | `edogoyomi/obj_hogaki/hogaki5.obj` | 4.11×0.78×0.04 | 帆掛(ほがき)。単体・柱あり |
| **犬矢来** | `Village Kit/Prefabs/Props/Inuyarai_A_01_x1..x8` | 1〜8×1.5×0.68 | 町屋の足元。**未使用** |
| 板塀(高い・洋風寄り) | `Village Kit/Prefabs/Fences/fence A|B` | 0.46×3.3×2 | h3.3m。corner/end/x8 |
| 板塀(低い) | `Village Kit/Prefabs/Fences/Fence_B_01_x1|x2|x8` | 1〜8×1.98×0.53 | Cor/End/Gate 完備 |
| 竹垣 | `Village Kit/Prefabs/Fences/Bamboo garden fence (B)` | 0.05×0.9×1.05 | 低い。庭の仕切り |
| 店先の柵 | `Village Kit/.../Shopping Streets/Fence Shop *` | 1×0.63×0.1 | 高0.63m |
| 城の塀(狭間付) | `Japanese Castle/.../Defence Walls/Wall Exterior Defence *` | 2×2.57×2.1 | Tall(4.27)/45°/Corner/End/Window A-C |

## 3. 石垣・基礎・土台

石垣の**据え方**は `unity-modular-stonewall` スキルが正典。ここは在庫のみ。

| 欲しい物 | アセット | 生寸法 |
|---|---|---|
| 石垣(標準・高4m) | `Japanese Castle/.../Defence Walls/Castle Wall.prefab` | 2.4×4×2 |
| 同 8m長 / 12m高 | `Castle Wall x 8` / `Castle Wall 4x12` `8x12` | 2.4×4×8 / 4.4×12×4 |
| 出隅 | `Castle Wall Corner` / `Corner x 12` / `Corner 2` `2_2x2` | 2.4×4×2.4 ほか |
| 別テクスチャ系統 | `Castle Wall B *` / `Castle Wall C *` | B=3.4幅 / C=2〜8×4〜12 |
| 布基礎・石場建て | `Village Kit/Prefabs/Foundations/Foundation_A_01|02|03` | 2〜8×0.5〜2.4 |
| 地面パッチ | `Japanese Castle/.../Ground/Ground 4x4|8x8` | 4×0×4 |

## 4. 建物 — 住居・長屋・蔵・町屋

| 欲しい物 | アセット | 実寸(W×H×D) | 備考 |
|---|---|---|---|
| 御殿の躯体に使う大屋根 | `Village Kit/Prefabs/Big House.prefab` | 28.5×11.3×26.5 | 屋根込み。躯体のみなら 26.2×24.2 |
| 中規模 | `Village Kit/Prefabs/House.prefab` | 20.5×7.3×16.5 | |
| 細長 | `Village Kit/Prefabs/House B.prefab` | 8.8×9.3×18.3 | 妻入り |
| 小 | `Village Kit/Prefabs/Small House.prefab` | 14.5×7.3×10.5 | |
| 角屋根 | `Village Kit/Prefabs/House A.prefab` | 14.5×11.3×14.5 | |
| 巨大(御殿代用) | `Village Kit/Prefabs/Manor.prefab` | 38.5×15.3×62.5 | 62m。単体では大きすぎる |
| 集落まるごと | `Village Kit/Prefabs/Village.prefab` | 126×12.6×114 | 参考用。実配置には不向き |
| **家中長屋** | `edogoyomi/es_knagaya/knagaya01c|l|r.obj` | 生4.45〜4.67 | ES後 **ピッチ7.81m**。表=+Z。c=妻開き / l,r=けらば付 |
| 土蔵 | `edogoyomi/es_kura/kura.obj` | 生3.43 | ES後6.2m。バウンズ底 −0.15 で据える |
| 町屋(店舗) | `edogoyomi/es_shop01/shop01.obj` | 生2.71×2.34×2.22 | ES後4.9×4.3m。樽・桶・札・囲い付属 |
| 町屋(大) | `edogoyomi/es_shop02/shop02.obj` | 生3.92×2.58×3.8 | ES後7.1×4.7×6.9m |
| 自身番屋 | `edogoyomi/es_jishinban/jishinban.obj` | 生2.12×3.64×2.72 | ES後3.9×6.6×4.9。大提灯付属 |
| 木戸番屋 | `edogoyomi/es_kidobanya/kidobanya.obj` | 生1.83×1.61×2.78 | 箱・笠・草鞋・縄の小物付属 |
| 火の見櫓 | `edogoyomi/es_hinomi/hinomiyagura.obj` | 生1.65×5.15 | ES後 h9.4m |
| 農家 | `edogoyomi/obj_nouka1/nouka1.obj` | 生2.38×1.42×1.67 | ES後4.3m |
| 居酒屋 / 船宿 | `edogoyomi/es_izakaya/` `es_funayado/` の `Runtime/Geometries/Honey/` | 生2.3前後 | 建屋+障子・戸が別 obj |
| 掛茶屋 | `edogoyomi/pp2_kakechaya/Geometries/Honey/kakechaya.obj` | 生0.2級の小物21点と同居 | 葭簀・竈・茶器一式付き |
| 数寄屋・書院(座敷) | `edogoyomi/pp2_shoinl` `pp2_shoins` `pp2_sukiya_hana` `pp2_sukiya_umi` | 部屋単位 | 襖・障子・掛軸が別 obj。**内装用** |

## 5. 建物モジュール(壁・屋根・床)

小屋を自作するときはこれを積む。すべて 2m/4m/8m グリッド。

- **町屋の壁**: `Village Kit/.../Shopping Streets/Wall Shop (B|C|D|E|F|Plaster|Wood)` 2×3×0.18
- **民家の壁**: `Village Kit/.../Walls and floors/Wall B *` `Wall D *`(Exterior/Window/Top/Balcony 各種)
- **柱・梁・床・天井**: 同フォルダの `column A|B (small|tall)` `beam` `floor` `ceiling`
- **屋根(瓦)**: `Village Kit/Prefabs/Roofs/roof *` — 2x2〜4x16、corner A/B、end、ornaments、top
- **屋根(別系統)**: `Roofs B/*`
- **城の屋根**: `Japanese Castle/.../Roof/Roof Castle *`(明石破風 Akashi B/M/S、鯱 `Shachihoko`)
- **縁側・廻縁**: `Village Kit/Prefabs/Balcony/balcony A〜D`(corner L/R あり)
- **店の庇**: `Shopping Streets/Roof shop` 2.08×0.95×2.13、`Roof shop x 8`

## 6. 内装(御殿の中を作るとき)

- 畳: `Japanese Castle/Prefabs/Interior/Tatami_A_01`(2×1)、`2x2` `2x3` `4x4`
- 襖・壁: `Wall Fusuma A|B|C`、`Fusuma B Painting 1X1|2X2`、`Wall Interior Plaster|Wood`
- 床・天井・柱: `Floor` `Ceiling` `Column A|B|C`(高1/3/6m)
- 階段: `Stair` `Stair 2`(3x1 で高さ4.2m)、`Stair B`
- 調度: `Biombo`(屏風 ×4/×6 折)、`Chest Choba-dansu` `Chest Tansu`、`Kimono Stand`、
  `Stand 5|10 Sword`(刀掛)、`Candle Stand Rosokutate A`、`Kakemono_A_01..03`(掛軸)
- 江戸暦側の座敷小物: `pp2_shoinl/shs_*`(文机・硯・和本 `pp2_wahon`・琴 `pp2_koto`・鼓)

## 7. 道・水路・橋・石段

| 欲しい物 | アセット | 寸法 |
|---|---|---|
| 石段(2m幅・蹴上0.3) | `Assets/Edo/Models/Shiomizaka/P_DanishiStep2m.prefab` | 1.98×0.49×0.62 |
| 道端石 | `Assets/Edo/Models/Shiomizaka/P_MichibataIshi2m.prefab` | 2m |
| 城の石段(45°・急) | `Japanese Castle/.../Ground/Steps A|B|C` | 4×2.1×5.2 |
| 側溝つき街路 | `Village Kit/.../Shopping Streets/Paving ground dirt street (narrow|wide) waterway x4|x12|x24` | 12〜24m長 |
| 側溝単体 | `Paving waterway` `X1` `2X4` `2X14` `corner` | 2×1×1.2 |
| 小橋(溝を渡す) | `Paving waterway bridge` | 1.98×0.25×1 |
| 土の舗装 | `Paving ground dirt 1X1|4X4|8x8|16x16` | 平板 |
| 反り橋 | `Japanese Castle/Prefabs/Castle Bridge.prefab` | 35.5×6.1×9.45(堀スケール) |
| 橋の部材 | `.../Exterior/Bridge/Bridge floor x 8` `Bridge side x 8` `Bridge post` | 8×0.07×2 ほか |

## 8. 点景

**灯り**: 春日灯籠 `Assets/Edo/Prefabs/KasugaLantern.prefab` / 雪見 `YukimiLantern.prefab`(自作)。
江戸暦の石灯籠 `t_kasuga` `t_yukimi` `t_oribe` `t_yama` `t_joyato`(常夜灯)、
釣灯籠 `obj_tsuritourou`、辻行灯 `obj_tsujiandon`(生 h4.45 = ES後8m。**大きすぎるので個別縮小**)、
大提灯 `es_jishinban/daichochin.obj`、町の街灯 `Village Kit/.../Lamp Street Village (B)`、
松明 `Torch`、石籠 `Japanese Castle/Prefabs/Props/Stone Basket`(灯籠の代用)。

**石造物**: 地蔵 `s_jizo/jizo2.obj`(0.55×0.79 — 唯一まともなスケール)、五輪塔 `s_gorin`、
宗塔 `s_sohtoh`、多宝塔 `obj_tahouto`、鐘楼 `obj_shoro1`。
⚠ `s_hokyoin`(宝篋印塔 生200×478m)・`s_dosojin`(道祖神 41×49m)・`s_koshin`(庚申塔 13×31m)は
**インポートスケールが壊れている**。ES ではなく目標高さから逆算して個別に縮小すること。

**生業・小物**: 荷車 `Village Kit/Props/Cart_A_01|02`、米俵 `RiceBarrel_01`、桶 `bucket A|B`、
陶器 `Shopping Streets/pottery A〜D`(割れ版あり)、酒屋看板 `sign Sake Store (Small|B)`、
暖簾 `Noren A|B|C`、縄暖簾 `es_izakaya/nawanoren.obj`、床几 `bench`、
江戸暦: 屋台 `pp_sobaya_yatai`(蕎麦屋)、鉄鍋 `pp_tetsunabe`、山駕籠 `pp_yamakago`、
竹籠 `obj_takekago`、唐箕 `obj_toumi`、稲架 `pp2_hasa`、箒 `pp2_houki`、熊手 `pp2_kumade`、
竹梯子 `pp2_takebashigo`、脚立 `pp2_takekyatatsu`、四手網 `pp2_yotsude`、火鉢 `obj_maruhibachi`、
神棚 `obj_kamidana`、衝立 `pp_tsuitate01|02`、行灯 `pp_a_01〜05` `pp_a_enshu`、
文箱 `pp_fubako` `pp2_fubako2`、切子灯籠 `pp_kiriko`、折鶴 `obj_orizuru`、南瓜 `obj_kabocha`。

**舟**: 荷足船 `obj_nitaribune/nitaribune.obj`(生0.57×1.91 = ES後 3.5m。櫓 `ro.obj` 付)、
屋根舟 `obj_yanebune/yanebune.obj`(生0.68 — **要スケール確認**。簾の開閉2種)。

## 9. 植栽・自然

| 欲しい物 | アセット | 備考 |
|---|---|---|
| 松(黒松) | `Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_(Big|Mid|Small)_(Green|Dry)_01..03` | 生5.6m。**×1.65** |
| 桜 | `.../Trees/Sakura/Tree_Sakura_*_(Spring|Summer|Fall|Winter)_01|05` | **Summer を使う**(季節は春ではない)。×1.4 |
| 竹 | `.../Trees/Bamboo/Tree_Bamboo_*_(Green|Dry)_01|02` | 生6.5m。×1.5 |
| 藤棚 | `Village Kit/Prefabs/Foliage/Wisteria_A_01`(+ Branches/Flowers/Leaves) | **未使用** |
| 躑躅 | `Japanese Castle/Prefabs/Foliage/Azalea A 01|03|04` | **A 02 は存在しない** |
| 刈込 | `.../Plants/Boxwood/Plant_Boxwood_(Spring|Fall)_01..03` + `Single/` | |
| 下草 | `.../Plants/PaintedFern/*` | |
| 草・花(地形詳細) | `NatureManufacture .../Grass/Prefabs Grass`(25点・17点使用中)/ `Prefabs Flowers`(45点) | Unity Terrain 用の別セットあり |
| 低木 | `NatureManufacture .../Bushes/Prefabs`(8点) | 未使用 |
| 庭石 | `FreeJapaneseGarden/Prefabs/Misc/Rocks/JG_Rock_A_01..03` | ×1.5-3.8 |
| 飛石 | `.../JG_TobiIshi_A_01|02` | ×1.8-1.9、2-3m間隔 |
| 岩・崖 | `NatureManufacture .../Rocks/Cliffs/Prefabs`(19点・7.7m級)/ `Rocks/Rocks/Prefabs`(20点) | 草・落葉ブレンド版あり。**全て未使用** |
| 切株 | `NatureManufacture .../Tree Stump/Prefabs` | |
| 遠景の山 | `NatureManufacture .../Background Mountains/Prefabs`(6点・1km級) | **未使用** |
| ポプラ | `NatureManufacture .../Trees/*`(11点) | 江戸には使えない |

## 10. **無い物**(代用・自作の方針つき)

これらは目録に存在しない。聞かれたら「無い」と即答してよい。

| 無い物 | どうするか |
|---|---|
| **井戸** | 合成する: 石色 Cylinder 1.3×0.35×1.3 + 木柱2 + 梁 + `bucket A` |
| **鳥居・社殿・祠** | 無い。稲荷は Castle の `Gate Castle Exterior` 等では代用不能 — 自作が要る |
| **人物・馬・動物** | 無い。`edogoyomi/cr2_*` は Poser の**衣装パーツだけ**(素体なし)で使えない |
| **厩** | 無い。`Small House` の壁を抜いて作る |
| **水車・釣瓶** | 無い |
| **石橋** | 無い(`Paving waterway bridge` は木の小橋)。汐見坂の石は `Michibata` 系で代用 |
| **雪隠・湯殿** | 無い。小屋モジュールで作る |

---

## 11. 落とし穴

- **BUILTIN シェーダは現在 4 点だけ**(NatureManufacture の塵パーティクル。実害なし)。
  Waldemarst を再 import した直後はここが 80 点超に跳ねる = URP 化パッチの再適用が必要というサイン。
  `awk -F'\t' 'NR>5 && $12=="BUILTIN"' docs/asset-index.tsv | wc -l` で点検できる。
- **ルートに補正スケールを持つプレハブが 42 点**ある(`root_scale` 列が `1` でない物)。
  共通ヘルパに `Vector3.one` を渡すと化ける。`PrefabUtility.InstantiatePrefab` でネイティブスケール保持。
  例: `Edo/Models/Dobei/DobeiModule2m.fbx` はルート `(2, 0.35, 0.5)` で実寸 31×35×9.9m。
- **`.glb` は `com.unity.cloud.gltfast` 経由で普通に使える**(ScriptedImporter なので
  `t:Model` 検索には掛からない — 目録は拡張子で拾っている)。ただし現存19点は全て未使用:
  `edogoyomi/es_shop01/*.glb` 10点と `Edo/Models/shop01.glb` は `.obj` 版と重複、
  `Edo/Ishigaki/*.glb` 8点は不採用になった手続き生成石垣の試作(2m幅・高1.2/2.5/5.0)。
- **edogoyomi の Poser 残骸**(`.pp2` `.cr2` `.rsr` `.hr2` `.bum` 計 75MB)は Unity から使えない。
- edogoyomi の門・長屋は **`pivot_bottom` が −1.0 前後**。地面に置くと 1m 埋まる。
