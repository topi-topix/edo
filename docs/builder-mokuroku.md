# 邸ビルダーの目録(生成物・手で直さない)

<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py -->

**メニューの名・Stage の関数・ビルダーの中の関数を探すときは、C# を grep で読み歩かずまずここを引く。**
Stage の本体(何をどの順に据えるか)は目録に無い — 名を決めてから、その関数の行だけ読む。

- `Assets/Edo/Scripts/Editor/Edo*Builder*.cs`・`Edo*Rebuild*.cs` 16 本・メニュー 79・関数 606(非公開も)。
- メニューは Unity の `execute_menu_item` にそのまま渡せる全名。呼ぶ関数 = メニューの関数の頭で呼んでいる同じファイルの関数。
- 関数へ跳ぶ: `grep -n "static .* <名>(" Assets/Edo/Scripts/Editor/<ファイル>`。
- 据え方の関数は `docs/edobuild-mokuroku.md`、部材の名は `docs/edoassets-mokuroku.md`。⛔ 手で直さない(`python3 Tools/Unity/edobuild_mokuroku.py`)。

## ファイルの索引

| ファイル | 何の道具か(ファイル冒頭の注釈) | メニュー | 関数 |
|---|---|---|---|
| [EdoDoiBuilder.Niwa.cs](#edodoibuilderniwacs) | 土井大隅守上屋敷 — 奥庭(Stage6)。 | 3 | 40 |
| [EdoDoiBuilder.cs](#edodoibuildercs) | 土井大隅守上屋敷(三河刈谷藩2万3千石・譜代・雁間)ビルダー。 | 15 | 84 |
| [EdoMatsudairaDewaBuilder.Niwa.cs](#edomatsudairadewabuilderniwacs) | 松平出羽守上屋敷 — 庭の工程(池・築山・水の系・石組・点景・滝見口)。 | 9 | 30 |
| [EdoMatsudairaDewaBuilder.cs](#edomatsudairadewabuildercs) | 松平出羽守上屋敷(出雲松江藩 18万6千石)ビルダー。 | 15 | 97 |
| [EdoOkabeYashikiBuilder.cs](#edookabeyashikibuildercs) | 岡部筑前守長寛(和泉岸和田藩5万3千石・譜代・帝鑑間)上屋敷 ビルダー — 全面起こし直し(2026-09-03) | 17 | 101 |
| [EdoSannoShaBuilder.cs](#edosannoshabuildercs) | 山王権現社(日枝神社)本体+観理院+樹下家邸+山王門前町ビルダー (2026-08-11) | 1 | 34 |
| [EdoSannoShaRebuild.cs](#edosannosharebuildcs) | 山王権現社 — 指図どおりに建て直すビルダー (2026-09-10 棟梁) | 13 | 99 |
| [EdoSanyashikiRebuild.cs](#edosanyashikirebuildcs) | 三屋敷(太田・加納・鍋島=松平肥前守)の区画を下書きv3へ更新 (2026-08-08) | 0 | 6 |
| [EdoSekiBuilder.cs](#edosekibuildercs) | — | 1 | 8 |
| [EdoShiomizakaRebuild.cs](#edoshiomizakarebuildcs) | 汐見坂(段坂)を新区割りの回廊へ敷き直す (2026-08-09) | 0 | 12 |
| [EdoTypologyBuilder.Inari.cs](#edotypologybuilderinarics) | 類型ビルダー — 稲荷(町屋の裏手の小祠と鳥居)。EDO-0326。 | 0 | 1 |
| [EdoTypologyBuilder.Jisha.cs](#edotypologybuilderjishacs) | 類型ビルダー — 寺社の境内(Stage 3〜4 の jisha 分)。本堂・庫裏・蔵・鐘楼・墓地・塔頭を置く。 | 0 | 9 |
| [EdoTypologyBuilder.Machiya.cs](#edotypologybuildermachiyacs) | 類型ビルダー — 町屋(machiya)の段。24 区画。EDO-0325。 | 0 | 5 |
| [EdoTypologyBuilder.Niwa.cs](#edotypologybuilderniwacs) | 類型の庭(Stage 5)— どの類型が何をどこへだけ。EDO-0323。 | 0 | 26 |
| [EdoTypologyBuilder.cs](#edotypologybuildercs) | 類型ビルダー — 区画の形(parcels.json)と類型表(typology.json)から、一本で建てる。 | 5 | 41 |
| [EdoYamatoRebuild.cs](#edoyamatorebuildcs) | 松平大和守(川越藩17万石)上屋敷の再建 v2 (2026-08-08) | 0 | 13 |

## EdoDoiBuilder.Niwa.cs

土井大隅守上屋敷 — 奥庭(Stage6)。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `検査④ 池が水面の下に納まっているか PondQA` | `PondQAMenu` | `PondQA` |
| `6 奥庭(掘削・護岸・点景・園路・稲荷・植栽)` | `Stage6Menu` | `Stage6_Niwa`, `Niwa_A_Dokou`, `Niwa_B_Gogan`, `Niwa_C_Mizushiri` |
| `6a 池を掘り築山を盛る(⛔ WaterBaker.Recarve は呼ばない)` | `Niwa_A_Menu` | `Niwa_A_Dokou` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Wu(u, v)` | `Vector2` |  | — |
| `Sh(oneBased)` | `Vector2` |  | 汀線の点(指図の `roles` は 1 始まり)。 |
| `SnapToWaterEdge(g)` | `Vector2` |  | 設計の汀の点を水面メッシュの縁(Chaikin×2)へ寄せる(最寄り点)。 |
| `ShoreWalk(frm, to)` | `List<Vector2>` |  | 汀線を frm→to へ辿った折れ線(1 始まり・巡回)。 |
| `LerpLine(L, t, dir)` | `Vector2` |  | — |
| `LineLen(L)` | `float` |  | — |
| `PondWorld()` | `Vector2[]` |  | 設計の汀(`migiwa.pts`)を世界座標で。 |
| `Cross2(p, q, r)` | `float` |  | — |
| `SegHit(a, b, c, d)` | `bool` |  | — |
| `PondOverlapsCell(wx, wz, half)` | `bool` |  | セル(世界の軸平行な正方形)が汀多角形と少しでも重なるか(coverage &gt; 0)。 |
| `EditNiwaHeights(fn, label)` | `string` |  | ハイトマップの窓を開いて fn(u, v, 現況) で書き、閉じる。 |
| `PondEdge()` | `Vector2[]` |  | 水面メッシュの縁(グリッド座標)。 ⚠⚠ `WaterBaker.RebuildSurface` は輪郭に Chaikin ×2(`WaterGeom.SmoothTagged(…, 2)`)を 掛けてから三角形にするの… |
| `InWater(u, v)` | `bool` |  | 水面メッシュの縁の内側か(⛔ `NiwaM.InPond` は設計の汀で、こちらは見える汀)。 |
| `PondQA()` | `string` | 公 | — |
| `Stage6_Niwa()` | `string` | 公 | — |
| `Niwa_A_Dokou()` | `string` | 公 | — |
| `Niwa_B_Gogan()` | `string` | 公 | — |
| `Niwa_C_Mizushiri()` | `string` | 公 | 水尻。⭐ 2026-09-06 に部材が焼けた。 |
| `Niwa_D_Tenkei()` | `string` | 公 | — |
| `Niwa_E_Enro()` | `string` |  | — |
| `Niwa_F_Yashiro()` | `string` |  | — |
| `Niwa_G_Kaki()` | `string` |  | — |
| `TerrY(x, z)` | `float` |  | 実地形の高さ(heightmap から。 |
| `Niwa_H_Shokusai()` | `string` | 公 | — |
| `ShitakusaRegions()` | `List<SkRegion>` |  | — |
| `CrownR(sk)` | `float` |  | 樹冠の半径[間]。⛔ 呼び寸法を使わない — 据える部材の実メッシュの 平面の大きい方 ÷2 × `scale`(生成器が `docs/asset-index.tsv` から引くのと同じ値)。 |
| `SkIn(r, u, v)` | `bool` |  | — |
| `SkCells(r)` | `IEnumerable<Vector2>` |  | 面積を測る格子(0.1間)。⚠ 生成器 `_shitakusa_pts` と同じ数え方にする — 樹冠の円は円ごとに走査するので重なりを二重に数える(=面積は上限値)。 |
| `ShoreOut(i)` | `Vector2` |  | 汀線の辺 i(0起算)の外向き法線(単位・(u,v))。 |
| `SuhamaBands()` | `List<Vector2[]>` |  | 州浜の砂利帯の平面形(汀の陸側 `toLand` のオフセット帯)。 |
| `SkInBand(bands, q)` | `bool` |  | — |
| `MeasureWH(path, w, h)` | `void` |  | 部材を1枚置いて実寸(平面の幅・丈)を測り、すぐ捨てる。 |
| `ResolveNiwaApi(api, variant)` | `string` |  | 指図が書く `EdoAssets.…` の呼び名を実パスへ解く。 |
| `JGPine(size, i)` | `string` |  | — |
| `ParseIshiPick(s)` | `int[]` |  | 護岸の地の石の駒の選び方(指図 `gogan[].ishiPick`。 |
| `ArgNum(api, dflt)` | `float` |  | `Own.Kido(1.8)` の 1.8 を取り出す。 |
| `ArgSize(api)` | `string` |  | `Own.Jouryoku("Big", i)` の "Big" を取り出す。 |

## EdoDoiBuilder.cs

土井大隅守上屋敷(三河刈谷藩2万3千石・譜代・雁間)ビルダー。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/土井大隅守上屋敷/指図を読み直す` | `Reload` | — |
| `Edo/土井大隅守上屋敷/未据え付けの一覧` | `WaitMenu` | `PendingReport`, `Reload`, `O`, `Has` |
| `Edo/土井大隅守上屋敷/0 ハイトマップを退避` | `Stage0Menu` | `Stage0_Backup`, `Exists` |
| `Edo/土井大隅守上屋敷/1 造成(指図の面へ)` | `Stage1Menu` | `Stage1_Grade`, `Stage0_Backup` |
| `Edo/土井大隅守上屋敷/造成を検査 GradeQA` | `GradeQAMenu` | `GradeQA` |
| `Edo/土井大隅守上屋敷/裏木戸の材質を練塀へ明示的に結ぶ` | `RemapKidoMenu` | `RemapKido` |
| `Edo/土井大隅守上屋敷/検査① 段の縁の落差と土留め EdgeStepQA` | `EdgeStepQAMenu` | `EdgeStepQA`, `C` |
| `Edo/土井大隅守上屋敷/検査② 門口を石垣が塞いでいないか KomonIshigakiQA` | `KomonIshigakiQAMenu` | `KomonIshigakiQA`, `O`, `F` |
| `Edo/土井大隅守上屋敷/検査③ 石垣が区画外へ出ていないか ParcelOutQA` | `ParcelOutQAMenu` | `ParcelOutQA` |
| `Edo/土井大隅守上屋敷/検査①②③ をまとめて走らせる` | `AllQAMenu` | `EdgeStepQA`, `KomonIshigakiQA`, `ParcelOutQA`, `C` |
| `Edo/土井大隅守上屋敷/2 外周(表長屋・練塀・門)` | `Stage2Menu` | `Stage2_Perimeter`, `Clear`, `Group` |
| `Edo/土井大隅守上屋敷/3 石垣(外周の基壇・境界の基壇・郭内の土留め・石段の側)` | `Stage3Menu` | `Stage3_Ishigaki`, `Group`, `Clear` |
| `Edo/土井大隅守上屋敷/4 御殿複合(棟・廊下)` | `Stage4Menu` | `Stage4_Goten`, `Clear`, `Group`, `YawAlongU` |
| `Edo/土井大隅守上屋敷/5 郭内(附属屋・井戸・石段・斜路・竹垣)` | `Stage5Menu` | `Stage5_Zosaku`, `Clear`, `PlaceService`, `PlaceWells` |
| `Edo/土井大隅守上屋敷/S1→S6 を通す` | `RunAllMenu` | `RunAll`, `Stage0_Backup`, `Stage1_Grade`, `Stage2_Perimeter` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `O(o)` | `Dictionary<string, object>` |  | — |
| `A(o)` | `List<object>` |  | — |
| `F(o)` | `float` |  | — |
| `S(o)` | `string` |  | — |
| `Has(o, k)` | `bool` |  | — |
| `C(k)` | `float` |  | — |
| `EdgePt(edge, s)` | `Vector2` | 公 | 辺 edge の走り s[m] の世界座標。 |
| `EdgeLen(edge)` | `float` | 公 | — |
| `PointInPoly(p)` | `bool` |  | — |
| `OutNormal(e)` | `Vector2` | 公 | 辺 e の外向き法線。⛔ 重心では決めない(凹みのある区画で反転する) — 法線方向へ出た点が区画の外かを内外判定で見る(松平 OutNormal と同じ作法)。 |
| `LoadNat()` | `void` |  | — |
| `NaturalY(x, z)` | `float` | 公 | 造成前の地盤[m]。無い所は NaN(⛔ live terrain で埋めない — 埋めると 「造成しない」区間が他家の造成へ寄る)。 |
| `InParcelUV(u, v)` | `bool` |  | — |
| `DesignY(u, v)` | `float` | 公 | その (u,v) を覆う段の高さ。無ければ NaN(=造成しない斜面)。 |
| `RunEdges()` | `List<Vector2>` |  | — |
| `WalledEdges(t)` | `List<WSeg>` |  | 段 t の四辺のうち土留めが載っている区間。 |
| `Walled(we, edge, w)` | `bool` |  | — |
| `RampY(u, v)` | `float` |  | 土の斜路の踏面。無ければ NaN。(`sashizu_lib.ramp_y`) |
| `StairY(u, v)` | `float` |  | 石段の掘割(切通し)の踏面。外なら NaN。 |
| `GradedY(u, v, nat)` | `float` | 公 | 造成後の地盤(`sashizu_lib.graded_y` の移植)。 |
| `GroundY(x, z)` | `float` | 公 | 世界座標での施工後の地盤。⭕ 奥庭の矩形の中は庭の土工(池床・築山・土手)を重ねる (生成器 `ground_y`)。 |
| `Group(child)` | `Transform` |  | 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 EdoYashikiPrefab.Group。 |
| `Clear(t)` | `void` |  | — |
| `Marked(stage)` | `bool` |  | 非冪等の工程の実行済みマーカー(⛔ active にする — `GameObject.Find` は非アクティブを見つけない)。 |
| `Mark(stage, note)` | `void` |  | — |
| `Wait(s)` | `void` |  | — |
| `AuditKeys(o, what, known)` | `void` |  | 指図の欄のうち実装が知らない物を「未据え付け」へ積む守り。 |
| `WaitReport()` | `string` |  | — |
| `SimpleApi(api)` | `bool` |  | 未据え付けの一覧。⚠ `_wait` は「この巡で走らせた Stage が積んだ物」しか持たない — ドメインリロード後や Stage を走らせていない状態では空で、それを「0 件 = 全部据わった」と 読むと嘘になる(… |
| `PendingReport()` | `string` | 公 | — |
| `Exists(path)` | `bool` |  | — |
| `Box(path)` | `PartBox` |  | — |
| `ProjMesh(go, axis, lo, hi)` | `bool` |  | 据えた現物のメッシュの頂点を軸へ落として範囲を取る。 |
| `TopRidgeGrid(go, acrossIsU, lo, hi, topY)` | `bool` |  | 棟のいちばん高い大棟が、江戸間格子のどこに載っているかを実測する。 |
| `ReportFit(sb, go, edge, s0, s1, label)` | `void` |  | 据えた囲いの駒が run の丁場に収まっているかを実測して報告する。 |
| `Stage0_Backup()` | `string` | 公 | — |
| `Stage1_Grade()` | `string` | 公 | — |
| `GradeQA()` | `string` | 公 | — |
| `RemapKido()` | `string` | 公 | — |
| `WalledAt(u, v, top)` | `bool` |  | グリッド点 (u,v) を土留めが受けているか。 |
| `EdgeStepQA()` | `string` | 公 | — |
| `Emit(sb, t, edge, vertEdge, fix, lo, hi, worst, kind, lim)` | `bool` |  | 検査①の1区間を刷る。⚠ 1間 に満たない当たりは落とす — 0.5間 刻みで段の隅を 回ると、隣の段の角で1点だけ当たることがあり、実体のある区間と混ざると読めなくなる。 |
| `KomonIshigakiQA()` | `string` | 公 | — |
| `ParcelOutQA()` | `string` | 公 | — |
| `Measure(path)` | `NagMod` |  | 表長屋の駒の壁の実体の走り方向の範囲(ピボット基準)。 |
| `KomonAsset(k)` | `string` |  | 小門が名指しする部材のパス。⚠ `inRun` を持つ小門(通用門)は 表長屋の run ごと焼いた一体の部材の中にあるので、独立した部材は無い(null)。 |
| `KomonSpan(k)` | `float` |  | 開口が run を切る実際の幅。⛔ 呼び寸法(`komon[].w`)で継がない — 木戸の走り方向の実寸は開口より方立柱2本ぶん広い(規則5・指図 `komon._asset`)。 |
| `GateSpan()` | `float` |  | 表門が run を切る実際の幅(部材の実メッシュ)。 |
| `SplitByOpenings(edge, s0, s1)` | `List<Vector2>` |  | 開口(表門・小門)で run の区間を割る。 |
| `Stage2_Perimeter()` | `string` | 公 | — |
| `RebindMaterials(go, modelPath)` | `void` |  | 置いた駒の材質を、素の部材のスロットから結び直す。 |
| `PlaceFumiishi(mon)` | `string` |  | 門外の踏石。指図 `komon[].fumiishi`(`n` 段・`side`)。 |
| `Stage3_Ishigaki()` | `string` | 公 | — |
| `StairDownSign(k, w)` | `float` |  | 石段が壁からどちらへ下るか(`sashizu_lib.stair_y` と同じ判定)。 |
| `YawFor(xDir)` | `float` | 公 | 棟・廊下をこの回転グリッドへ据えるときの yaw。 |
| `YawFace(zDir)` | `float` | 公 | +Z(見え面)を dir へ向ける yaw。 |
| `YawAlongU()` | `float` |  | — |
| `YawAlongV()` | `float` |  | 桁行が v に沿う棟・廊下の yaw。local +X=+v / local +Z=−u。 |
| `Pivot(o, kind)` | `Vector2` | 公 | 棟・廊下の据え付け点。⛔ 検査だけが式を持つとズレるので、 `EdoSashizuExport.CheckScene` はここを呼ぶ(既定の松平式は桁行が u の棟しか合わない — 当邸は書院・奥・台所の3棟が桁行 v… |
| `FaceY(u0, v0, u1, v1, designY, label)` | `float` |  | — |
| `Stage4_Goten()` | `string` | 公 | — |
| `PlaceUmaya(grp, m, sb)` | `bool` |  | 厩(5.5×7間)。⭐ 2026-09-06 に専用部材 `Own.DoiUmaya` が焼けた (⛔ 従前の `Eg.KnagayaL/R` の2駒は撤去 — 足形も棟高も合っていない)。 |
| `Stage5_Zosaku()` | `string` | 公 | — |
| `PlaceService()` | `string` |  | — |
| `PlaceWells()` | `string` |  | 井戸5口。⭐ 2026-09-06 に `Own.DoiIdo` が焼けた。 |
| `PlaceKaidans()` | `string` |  | — |
| `LayGaki(grp, label, spanPath, postPath, A0, B0, idx0)` | `int` |  | 垣の run を1本敷く。⭕ 1スパン = 1間ちょうどなので 1.818 のピッチで突き付ける。 |
| `PlaceTakegaki()` | `string` |  | 郭のあいだの見切りの竹垣(`rails`)。 |
| `RunAll()` | `string` | 公 | — |

## EdoMatsudairaDewaBuilder.Niwa.cs

松平出羽守上屋敷 — 庭の工程(池・築山・水の系・石組・点景・滝見口)。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/松平出羽守上屋敷/1b 築山の盛土` | `Stage1bMenu` | `Stage1b_Tsukiyama`, `Marked`, `HasKey` |
| `Edo/松平出羽守上屋敷/6a 御泉水を掘る(⛔ 掲示板起票のあと)` | `Stage6aMenu` | `Stage6a_Sensui`, `Marked` |
| `Edo/松平出羽守上屋敷/6a' 岬・中島の隆起と澪筋` | `Stage6a2Menu` | `Stage6a2_Mounds`, `Marked`, `UVLine`, `HasKey` |
| `Edo/松平出羽守上屋敷/6b 水の系(枡・遣水の野筋・滝)` | `Stage6bMenu` | `Stage6b_Mizu`, `HasKey` |
| `Edo/松平出羽守上屋敷/6c 岩屋・石組・護岸` | `Stage6cMenu` | `Stage6c_Ishigumi`, `Marked`, `UVLine`, `HasKey` |
| `Edo/松平出羽守上屋敷/6d 点景と垣` | `Stage6dMenu` | `Stage6d_Tenkei`, `StrOf` |
| `Edo/松平出羽守上屋敷/6e 滝見口を開ける` | `Stage6eMenu` | `Stage6e_TakiKido`, `StrOf` |
| `Edo/松平出羽守上屋敷/6f 参道の玉砂利(稲荷)` | `Stage6fMenu` | `Stage6f_Tamajari`, `StrOf`, `HasKey` |
| `Edo/松平出羽守上屋敷/7' 植栽(指図の散布点を据える)` | `Stage7bMenu` | `Stage7b_NiwaFromScatter` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `HasKey(d, k)` | `bool` |  | — |
| `StrOf(d, k)` | `string` |  | — |
| `Marked(stage)` | `bool` |  | 非冪等の工程の実行済みマーカー(⛔ active にする — `GameObject.Find` は非アクティブを見つけない)。 |
| `Mark(stage, note)` | `void` |  | — |
| `EditHeights(mn, mx, fn, label)` | `string` |  | ハイトマップの窓を開いて fn で書き、閉じる。 |
| `TerrainY(wx, wz)` | `float` |  | — |
| `UVLine(pts)` | `List<Vector2>` |  | 指図の (u,v)[間] 折れ線 → 世界座標。 |
| `InPoly(P, q)` | `bool` |  | — |
| `DistLine(L, q, closed, sAlong)` | `float` |  | — |
| `Stage1b_Tsukiyama()` | `string` | 公 | — |
| `Stage6a_Sensui()` | `string` | 公 | — |
| `Stage6a2_Mounds()` | `string` | 公 | — |
| `Stage6b_Mizu()` | `string` | 公 | — |
| `Stage6c_Ishigumi()` | `string` | 公 | — |
| `StoneBedY(tk, st, depth=…)` | `float` |  | 石の `bedY` を解く。生成器 `_stone_bedY()` と同じ式 — dict なら {ref: 同じ点景内の石の名, add} として 参照先の天端(bedY + show)+ add(架け石は支え石の天端… |
| `ScaleToHeight(go, h)` | `void` |  | 置いた駒の実メッシュの高さを測って、丈 h[m] に合わせる(CLAUDE.md 規則5: 呼び寸法で置かない)。 |
| `Stage6d_Tenkei()` | `string` | 公 | — |
| `Stage6e_TakiKido()` | `string` | 公 | — |
| `Stage6f_Tamajari()` | `string` | 公 | — |
| `Stage7b_NiwaFromScatter()` | `string` | 公 | — |
| `NiwaQA()` | `string` | 公 | 庭を「指図と実装の突き合わせ」へ載せる(`_pending.jissouShukudai` ②)。 |

## EdoMatsudairaDewaBuilder.cs

松平出羽守上屋敷(出雲松江藩 18万6千石)ビルダー。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/松平出羽守上屋敷/0 ハイトマップを退避` | `Stage0Menu` | `Stage0_Backup` |
| `Edo/松平出羽守上屋敷/1 造成(指図の面へ)` | `Stage1Menu` | `Stage1_Grade` |
| `Edo/松平出羽守上屋敷/造成を検査 GradeQA` | `GradeQAMenu` | `GradeQA` |
| `Edo/松平出羽守上屋敷/2 外周(塀・長屋・木柵)` | `Stage2Menu` | `Stage2_Perimeter`, `Group`, `Clear` |
| `Edo/松平出羽守上屋敷/3 石垣基壇` | `Stage3Menu` | `Stage3_Ishigaki`, `Group`, `Clear` |
| `Edo/松平出羽守上屋敷/石垣を検査` | `IshigakiQAMenu` | `IshigakiQA` |
| `Edo/松平出羽守上屋敷/4 御殿複合` | `Stage4Menu` | `Stage4_Goten`, `Group`, `Clear` |
| `Edo/松平出羽守上屋敷/5 門(表門・番所・小門)` | `Stage5Menu` | `Stage5_Mon`, `Group` |
| `Edo/松平出羽守上屋敷/6 郭内の造作(塀・垣・石段・井戸・櫓・附属屋)` | `Stage6Menu` | `Stage6_Zosaku`, `Group`, `Clear`, `YawAlongU` |
| `Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap` | `RemapFuzokuyaMenu` | `RemapFuzokuya`, `RemapFuzokuyaMenuCommon` |
| `Edo/共通/附属屋・門・木のマテリアルをremap` | `RemapFuzokuyaMenuCommon` | `RemapFuzokuya` |
| `Edo/松平出羽守上屋敷/7 庭の植栽` | `Stage7Menu` | `Stage7_Niwa`, `Clear`, `Group` |
| `Edo/松平出羽守上屋敷/8 西斜面の林` | `Stage8Menu` | `Stage8_Shamen` |
| `Edo/松平出羽守上屋敷/走り方向の端を検査 RunEndQA` | `RunEndQAMenu` | `RunEndQA`, `Group` |
| `Edo/松平出羽守上屋敷/指図と実装を突き合わせる` | `CompareMenu` | `Compare`, `GradeQA`, `InubashiriQA`, `RunEndQA` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Reload()` | `void` | 公 | — |
| `O(o)` | `Dictionary<string, object>` |  | — |
| `A(o)` | `List<object>` |  | — |
| `F(o)` | `float` |  | — |
| `Has(o, k)` | `bool` |  | — |
| `EdgePt(edge, s)` | `Vector2` | 公 | 辺 edge の走り s[m] の世界座標。 |
| `G(x, z)` | `float` |  | — |
| `LoadNatural()` | `void` |  | — |
| `NaturalY(x, z)` | `float` | 公 | 造成前の地形の高さ[m]。退避が無ければ現況で代用する(初回だけ)。 |
| `DistSeg(p, a, b)` | `float` |  | — |
| `DesignY(p)` | `float` | 公 | 敷地内の一点の施工後の高さ。現況に依存するのは「造成しない」区間だけなので、 何度流しても同じ結果になる(冪等)。 |
| `Daylights(cp, g, yT)` | `bool` |  | 段の縁 cp から点 g の向きへ 1:feather の法面を featherCap[m] 延ばしたとき、 現地形に着地するか。 |
| `DistSegG(p, a, b)` | `float` |  | グリッド座標(間)での点と線分の距離。 |
| `Stage0_Backup()` | `string` | 公 | — |
| `Stage1_Grade()` | `string` | 公 | — |
| `Stage1_Grade(clipUV)` | `string` | 公 | 造成を流す範囲を格子(u,v)の矩形 clipUV = {u0,v0,u1,v1} に限る版。 |
| `GradeQA()` | `string` | 公 | — |
| `FenceWidth(parent, psi)` | `float` |  | 穂垣の実寸(走り方向の幅)。プレハブを1枚置いて測り、すぐ捨てる。 |
| `Group(child)` | `Transform` |  | 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 EdoYashikiPrefab.Group。 |
| `Clear(t)` | `void` |  | — |
| `GateSpan(sPos, s0, s1)` | `void` | 公 | 辺 e の外向き法線(区画の外側)。 ⛔ 重心で向きを決めてはいけない。 |
| `OutNormal(e)` | `Vector2` | 公 | — |
| `PointInPoly(p)` | `bool` |  | 区画の内側か(交差数法)。OutNormal の向きはこれで決める。 |
| `Measure(path)` | `NagModule` |  | — |
| `Stage2_Perimeter()` | `string` | 公 | — |
| `GridPt(o)` | `Vector2` |  | 指図の「点」を格子座標へ。⭐ `[u, v]` の配列だけでなく `{"ref": "&lt;中仕切/門の名&gt;"}` を解く (2026-09-06: 段や道の端が木戸に取り付くとき、literal を書かず木戸の… |
| `MeshBody(tr, maxSamples=…)` | `List<Vector3>` |  | 壁体(屋根・軒・垂木・棟・桁を除く)の頂点を世界座標で。 |
| `RendBounds(tr)` | `Bounds` |  | — |
| `PlaceKado(parent)` | `string` |  | 石垣の法肩から犬走りを残して囲いを据え直す。 |
| `ResetTerraceY()` | `void` | 公 | — |
| `TerraceY(t, spread, nPt)` | `float` |  | — |
| `TerraceOf(u, v)` | `Terrace` |  | 格子点 (u,v) を含む段。無ければ最寄り(距離 0 の段が無い所に棟は建たない想定)。 |
| `JointGap(id)` | `float` |  | 指図 `joints[id].gap`(+ = 隙間 / − = 差し込み)。 |
| `KadoArmSpan(kak, lo, hi)` | `string` |  | 据えた隅部材の「腕」が、接する二辺の s をどこまで覆っているかを実メッシュで測る。 |
| `AlignInubashiri()` | `string` | 公 | — |
| `Stage3_Ishigaki()` | `string` | 公 | — |
| `IshigakiQA()` | `string` | 公 | — |
| `YawAlongU()` | `float` |  | 棟・渡廊下をこの回転グリッドへ据えるときの yaw と原点。 |
| `YawAlongV()` | `float` |  | — |
| `MuneAt(u, v)` | `Dictionary<string, object>` |  | 格子座標 (u,v) を足形に含む棟の指図を返す(端点=辺の上でも含むと見る)。 |
| `RoofPierceMinY(root, xz)` | `float` |  | 棟 root の屋根の実メッシュを world の鉛直線 (xz) で貫き、 最も低い交点の world Y を返す(= その点での葺き面の下端 = 取り合いの「当たり」の面)。 |
| `RoofPierceMinY(root, xz, outward)` | `float` |  | — |
| `RoofTopAtLocalZ(mune, zLocal, band, x0, x1)` | `float` |  | 棟 local の z = zLocal の帯(±band)にある 屋根メッシュの頂点の最高 Y(棟 local)。 |
| `EnnoshitaY(roka)` | `float` |  | 据えた渡廊下の縁の下(縁板の下端の地盤上高さ[m])を実メッシュから測る。 |
| `SegGeya(seg)` | `Transform` |  | 渡廊下の区間に実際に据わっている下屋の駒。 |
| `TriPierceY(a, b, c, p, y)` | `bool` |  | 三角形を鉛直線 (p.x, p.y=z) が貫くか。 |
| `RoofNoki(m, munes)` | `int[]` |  | 棟 m の四辺 {u0, u1, v0, v1} の軒を出すか(1 = 出す / 0 = 落とす)。 |
| `Stage4_Goten()` | `string` | 公 | — |
| `Stage5_Mon()` | `string` | 公 | — |
| `HasOwnDoors(go)` | `bool` |  | 門が自前の扉を持っているか、置いた実物のメッシュ名で判定する (edogoyomi の冠木門は doorl / doorr。 |
| `Leaves(grp, name, pathL, pathR, pairW, footOff, p, yaw, want, sill)` | `int` |  | 門扉(両開き)を開口の芯へ据える。L/R とも突き合わせ側にピボットがあるので、 同じ点に両方置けば閉じる。 |
| `Stage6_Zosaku()` | `string` | 公 | — |
| `TryGridDir(d, dir)` | `bool` |  | グリッドの向き("+u"/"-u"/"+v"/"-v")を world の単位ベクトルにする。 |
| `PartLocalZ(go, zMin, zMax)` | `void` |  | 部材のローカル Z の符号つきの範囲[m](回転・位置を除く)。 |
| `RectFaceCenter(u0, v0, u1, v1, dir)` | `Vector2` |  | グリッドの矩形(間)の、dir の側の面の中央の world 点。 |
| `ObbOverlapInBand(a, b)` | `float` |  | 水平面の OBB どうしの食い込み量[m](分離軸法)。 |
| `ObbOverlap2D(a, b)` | `float` |  | — |
| `PartSize(go)` | `Vector3` |  | 部材そのものの寸法(回転を含まない)。 ⚠ world の AABB を使わない — 斜めグリッドでは 13.8×8.9 の箱が 16.0×13.1 に膨らむ。 |
| `RunWidth(b, yaw)` | `float` |  | — |
| `YaguraKeepout(lo, hi)` | `string` |  | 隅櫓の逃げ — 指図 `yagura[].gapA` / `gapB`(従属値)を実メッシュから解く。 |
| `YaguraSeat(P, vi, side, seat, log=…)` | `Vector2` |  | 隅櫓の据え位置 — 区画の頂点 vi から内向きの二等分線に沿って入れる。 |
| `ProjBand(go, dir, yLo, yHi, mn, mx, perpDir=…, origin=…, perpMax=…)` | `void` |  | 板塀を A→B に実寸ピッチで通す。skip の区間(庭木戸)は丸ごと落とさず、 木戸の両側を短い駒で埋める。 |
| `ProjSpan(go, dir)` | `float` |  | 置いた駒の実メッシュを走り方向 dir へ投影した伸び[m]。 |
| `NeishiPlace(njGrp, kido)` | `string` |  | 板塀の根石(玉石)を据える — 指図 `nakajikiriRule.neishi` が正典。 |
| `SeatJointHalf(vert, fix, lo, hi)` | `float` |  | 区間の継ぎ目(面の縁)で座を測らない幅[間]の半分 = 従属値。 |
| `ItabeiRun(parent, A2, B2, h, prefix, skip)` | `int` |  | — |
| `PlaceItabeiSpan(parent, A2, dir, nrm, t0, t1, spanES, sy, yaw, name, depth)` | `int` |  | 板塀の1区間 [t0,t1](A2 からの距離)に駒(表裏2枚)を据える。 |
| `RemapFuzokuya()` | `string` | 公 | — |
| `ResolveApi(api)` | `string` |  | 指図の `gardens` と `planting` を読んで木を植える。 |
| `SafeInt(t)` | `int` |  | — |
| `Stage7_Niwa()` | `string` | 公 | — |
| `Spot(z, rnd, free, clr, c)` | `bool` |  | 庭の矩形の中で、空いている点を決定論的に探す。 |
| `Stage8_Shamen()` | `string` | 公 | — |
| `ScreenQA(crest, segOut, slopeWidth, screens, sc)` | `string` |  | 遮蔽の検査。法肩に `step` ごとの検査点を取り、`reach` 以内に樹高 `minH` 以上の 木があるかを見る。 |
| `TreeHeight(go)` | `float` |  | 据えた木の実メッシュの高さ[m]。⛔ prefab の名前や呼び寸法で信じない。 |
| `Far(placed, q, d)` | `bool` |  | — |
| `PlantOnTerrain(path, w, parent, name, scale, rnd, sj0, sj1, tilt0, tilt1)` | `GameObject` |  | 法面へ据える。⛔ `DesignY` を使わない — 法面は造成面ではない。 |
| `TerrainY(w)` | `float` |  | live terrain の高さ。⚠ 造成前の地盤(base_dem)ではなくいまの作業面。 |
| `Plant(path, u, v, parent, name, scale, rnd, tiltU, sink=…)` | `GameObject` |  | — |
| `InubashiriQA()` | `string` | 公 | 犬走りと門の面の検査。囲いの外面が石垣の法肩から 0.30m 控えているか、 門の面が囲いと揃っているか。 |
| `RunEndQA()` | `string` | 公 | — |
| `Compare()` | `string` | 公 | — |

## EdoOkabeYashikiBuilder.cs

岡部筑前守長寛(和泉岸和田藩5万3千石・譜代・帝鑑間)上屋敷 ビルダー — 全面起こし直し(2026-09-03)

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/岡部筑前守上屋敷/指図を読み直す` | `Reload` | — |
| `Edo/岡部筑前守上屋敷/0 ハイトマップを退避` | `Stage0Menu` | `Stage0_Backup`, `Window` |
| `Edo/岡部筑前守上屋敷/1 造成(指図の面へ)` | `Stage1Menu` | `Stage1_Grade`, `ReviewGate`, `Stage0_Backup`, `Window` |
| `Edo/岡部筑前守上屋敷/造成を検査 GradeQA` | `GradeQAMenu` | `GradeQA`, `ImplTol`, `Window` |
| `Edo/岡部筑前守上屋敷/2 外周(練塀・基壇・木柵・隅)` | `Stage2Menu` | `Stage2_Perimeter`, `ReviewGate`, `Group`, `Clear` |
| `Edo/岡部筑前守上屋敷/3 主郭(棟・廊下・附属屋・井戸・結界・石段)` | `Stage3Menu` | `Stage3_Shukaku`, `ReviewGate`, `PlaceMunes`, `PlaceLinks` |
| `Edo/岡部筑前守上屋敷/4 庭(部材を据える・地形には触らない)` | `Stage4Menu` | `Stage4_Niwa`, `ReviewGate`, `A`, `Get` |
| `Edo/岡部筑前守上屋敷/5 西の斜面(林・松・帯・汀)` | `Stage5Menu` | `Stage5_Nishi`, `ReviewGate`, `PlantFromImpl`, `PlaceTesuri` |
| `Edo/岡部筑前守上屋敷/外周の閉じを検査 ClosureQA` | `ClosureQAMenu` | `ClosureQA`, `Openings` |
| `Edo/岡部筑前守上屋敷/開口と run の食い違いを検査 OpeningQA` | `OpeningQAMenu` | `OpeningQA`, `Openings` |
| `Edo/岡部筑前守上屋敷/区画と指図の座標を突き合わせる` | `ParcelQAMenu` | `ParcelQA`, `A`, `Get` |
| `Edo/岡部筑前守上屋敷/算出物を検める` | `ImplQAMenu` | `ImplQA`, `Reload` |
| `Edo/岡部筑前守上屋敷/S1→S5 を通す` | `RunAllMenu` | `RunAll`, `Reload`, `ParcelQA`, `Stage1_Grade` |
| `Edo/岡部筑前守上屋敷/隅部材のマテリアルをremap` | `RemapKadoMaterials` | `RemapDir`, `BindDonorMaterials`, `RemapKadoMaterialsCommon` |
| `Edo/共通/隅部材のマテリアルをremap` | `RemapKadoMaterialsCommon` | `RemapKadoMaterials`, `BindDonorMaterials` |
| `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap` | `RemapOkabeShinzoMenu` | `RemapOkabeShinzo` |
| `Edo/岡部筑前守上屋敷/坂の土留めのマテリアルをremap` | `RemapSakaMaterials` | `RemapDir` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `ReviewGate()` | `string` |  | — |
| `VerifyImplFingerprint()` | `void` |  | 算出物がいまの指図から焼かれた物か。⚠ 古い焼きで建てると、指図では直った はずの物が黙って復活する(2026-09-01 に松江松平の Stage7 で起きた型)。 |
| `O(o)` | `Dictionary<string, object>` |  | — |
| `A(o)` | `List<object>` |  | — |
| `F(o)` | `float` |  | — |
| `S(o)` | `string` |  | — |
| `Has(d, k)` | `bool` |  | — |
| `Get(d, k)` | `object` |  | — |
| `C(key)` | `float` | 公 | 指図の `const` の値。⛔ 無ければ例外(発明しない・既定値で埋めない)。 |
| `EdgeLen(e)` | `float` | 公 | — |
| `EdgePt(e, s)` | `Vector2` | 公 | 辺 e の始点から走り s[m] の世界座標。 |
| `OutNormal(e)` | `Vector2` | 公 | 辺 e の外向き単位法線。符号付き面積から決めるので凹みのある区画でも全辺で一貫する。 |
| `DesignY(p)` | `float` | 公 | 敷地内の一点の造成後の高さ[m]。区画の外は NaN。 |
| `ImplTol(key, ifMissing)` | `float` |  | — |
| `Group(child)` | `Transform` |  | 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 EdoYashikiPrefab.Group。 |
| `Clear(t)` | `void` |  | — |
| `Stage0_Backup()` | `string` | 公 | 着工前の地形を .bin へ。無いときだけ書く。 |
| `Window(x0, z0, w, h)` | `void` |  | 造成とその検査が使う窓。区画の外接矩形 + 余白。 |
| `Stage1_Grade()` | `string` | 公 | — |
| `GradeQA()` | `string` | 公 | 敷地内の全セルで ／地形 − 設計面／ を測る。 |
| `Stage2_Perimeter()` | `string` | 公 | — |
| `PlaceOmoteNagaya(kak, wait)` | `string` |  | 外周の表長屋と表門。⭕ 2026-09-04 裁定12=A(二階・棟 7.183 / 表門の棟 8.5)。 |
| `PlaceNagayaPiece(kak, name, path, edge, sMid, seat, call, wait, lastH)` | `bool` |  | — |
| `PlaceIshigaki()` | `string` |  | 基壇石垣。run ごとの倍率 `s` で据える(壁高 4.0s / 天端幅 1.4s / 底厚 2.4s)。 |
| `PlaceKomon()` | `string` |  | 袋小路へ開く通用口。指図 `komon[]` の 辺・走り s・門口の幅 w・敷居 sill が正典。 |
| `FaceOut(go, e)` | `float` |  | 据えた現物の外面(辺 e の区画線から外向きへの最大の張り出し[m])。 |
| `PlaceFences()` | `string` |  | 木柵(辺5=溜池の堤)。基礎も整地も石垣も持たない地形なりなので天端を持たない。 |
| `MeasureRunWidth(path, parent, psi)` | `float` |  | 部材を1枚置いて走り方向の実寸を測り、すぐ捨てる。 |
| `MeasureHeight(path, parent)` | `float` |  | — |
| `FitKado(kak, lo, hi)` | `string` |  | 据えた隅の両腕の外面を犬走りへ寄せ、腕の実端面を測る。 |
| `PlaceKado(parent)` | `string` |  | 隅部材を据える。折れ角は区画が決めるもので毎回違うので決め打ちしない。 |
| `AlignInubashiri()` | `string` | 公 | 石垣の法肩から犬走りを残して囲いを据え直す。 |
| `YawU()` | `float` | 公 | ローカル +X を +u へ向ける yaw。 |
| `YawV()` | `float` | 公 | ローカル +X を +v へ向ける yaw。 |
| `AlongU(du, dv)` | `bool` | 公 | 棟・廊下の据え付けピボット(グリッド座標)。 |
| `PivotUV(u0, v0, u1, v1)` | `Vector2` | 公 | — |
| `Pivot(o, kind)` | `Vector2` | 公 | 突き合わせが読む据え付け点(世界座標)。 |
| `Stage3_Shukaku()` | `string` | 公 | — |
| `PlaceMunes(wait)` | `string` |  | 御殿の棟。部材キットで一間の柱割りから組む(Village Kit の一軒家プレハブでは 入側から壁が見えて御殿にならない — 2026-08-14 ユーザー裁定)。 |
| `KirikakiCheck(go, m, rf, wait)` | `string` |  | 車寄の切り欠き(2026-09-04 裁定10=A)。 |
| `PlaceLinks(wait)` | `string` |  | 渡廊下は幅一間(指図 `_links`)で部材キットが組む。 |
| `AssetByKey(key)` | `string` |  | 指図が名指しした部材のキーを `EdoAssets` の実体へ解く。 |
| `AssetByKey(key, wKen, dKen)` | `string` |  | 指図の `asset` を `EdoAssets` の実体へ解く。 |
| `YawTo(du, dv)` | `float` | 公 | ローカル +X をグリッドの向き (du, dv) へ向ける yaw[°]。 |
| `PlaceBox(grp, nm, path, c, y, wKen, dKen, yaw, wait)` | `bool` |  | 箱状の附属屋を一つ据える(足跡の中心・地盤レベル)。 |
| `OrientOf(key, du, dv, xu, xv, note)` | `void` |  | 部材ごとの向きの規約。⛔ 「長いほうへ +X」で一律に決めない — 部材の doc が正典。 |
| `PlaceService(wait)` | `string` |  | — |
| `PlaceWells(wait)` | `string` |  | — |
| `PlaceKekkai(wait)` | `string` |  | 表向と奥向を屋外でも分ける結界の塀。練塀ではなく「のし塀+瓦」 (屋敷の内部の仕切りなので外構より軽くする — 指図 `_kekkai`)。 |
| `PlaceTakegaki(wait)` | `string` |  | 法肩の竹垣(四つ目垣)。⚠ 2026-09-04 まで据える処理が無かった上、 最初に通したときは在庫の `Eg.TakeGaki`(竹の菱格子=網代風で四つ目垣ではない)を 非一様スケールで伸ばしていた。 |
| `PlaceKaidans(wait)` | `string` |  | 石段。⚠ 足元と天端の標高は指図が持つ(`y0`/`y1`)。 |
| `PlaceSando(wait)` | `string` |  | 参道(表門の軸を通る白洲)。⭕ 屋根を架けない(2026-08-19 ユーザー裁定 — 前庭は開けた白洲で、屋根は式台・車寄せまで)。 |
| `Stage4_Niwa()` | `string` | 公 | — |
| `PlaceWaterSurface(items, wait)` | `string` |  | 池の水面だけを張る(2026-09-04 普請奉行の裁定)。 |
| `PaintSplat(items, wait)` | `string` |  | 地表を塗る(2026-09-04 指図方が `layer` を宣言した分)。 |
| `PlaceNiwaItem(sub, g, kind, key, pts, missing, wait)` | `int` |  | 庭の一節を据える。部材ごとに据え方が違うので種別で分ける。 |
| `IshigumiW(i)` | `float` |  | 庭石の個体 i の、丈 1.000 のときの平面の幅 W(X)[m](部材の doc の実測値)。 |
| `PolyAt(pts, t)` | `Vector2` |  | 折れ線 `pts`(世界座標)の走り比 t(0〜1)の点。 |
| `SeatByBury(go, g, groundY)` | `void` |  | 石を「丈の `buryRatio` だけ埋めて」据える。 |
| `PlantByKey(key)` | `string` |  | 植栽の部材のキーを解く。キーは指図(算出物)が持ち、ここは辞書を引くだけ。 |
| `PlantByKey(key, seedName)` | `string` |  | — |
| `ObbWD(go, wLocal, dLocal)` | `void` |  | 据えた現物のローカル軸での幅(+X)と奥行(+Z)[m]。 |
| `TrunkDiameter(host, y0, y1)` | `float` |  | 据えた木の幹径[m]。根元の少し上(`y0`〜`y1` m)の帯で、幹の芯からの 半径の 90 分位を取って 2 倍する。 |
| `StableHash(s2)` | `int` |  | 名前から決まる安定した非負の整数。⛔ 乱数ではない — 何度流しても同じ物が出る。 |
| `NaturalHeight(path, parent)` | `float` |  | — |
| `Stage5_Nishi()` | `string` | 公 | — |
| `PlantFromImpl(wait)` | `string` |  | 生成器が撒いた散布点を据えるだけ。 期待する欄は impl.planting[](素の配列。 |
| `PlaceTesuri(wait)` | `string` |  | 勝手の道が法肩の竹垣の外(池側)を通る区間の落下止め (2026-09-03 ユーザー裁定1=A)。 |
| `PlaceKuiretsu(wait)` | `string` |  | 汀線に沿う松の丸太杭。⭐ 本数は汀線の実長から算出する(⛔ 辺5の長さを流用しない — 2026-09-03 庭方4巡目)。 |
| `ReportNishiRest(wait)` | `string` |  | 西の斜面のうち、据える物が無いか部材待ちのものを一覧に出す。 |
| `UnionLen(ivs, lo, hi)` | `float` |  | — |
| `Openings()` | `List<float[]>` |  | 指図の開口(表門・通用口)。辺と s の区間で返す。 |
| `ClosureQA()` | `string` | 公 | 外周が全周で閉じているかを辺ごとに数字で出す。 |
| `OpeningQA()` | `string` | 公 | 開口の上に囲いが載っていないか。指図は run の `s` で既に開口を避けてあるので、 ここが 0 でなければ指図か区画のどちらかが動いた合図(実装は開口を切り直さない)。 |
| `ParcelQA()` | `string` | 公 | 区画の正典(parcels.json)と指図の同期コピーが一致しているか。 |
| `ImplQA()` | `string` | 公 | 算出物 `okabe_impl.json` の自己検査。 ⟶ 返す: 人が読む報告 |
| `TerraceRingDist(uv)` | `float` |  | 点(グリッド座標)から段の輪郭(外輪・抜き・keeps)までの最短距離[間]。 |
| `RingDist(ring, p)` | `float` |  | — |
| `DistSeg(p, a, b)` | `float` |  | — |
| `HeightRange(zone, role, species, name, lo, hi)` | `bool` |  | 指図が宣言している丈の範囲を引く。⛔ 宣言の無い層に既定の範囲を当てない — 当てると「検査を通った」ことになるが、実際には何も検めていない。 |
| `RunAll()` | `string` | 公 | — |
| `BindDonorMaterials()` | `string` |  | 素材の提供元からマテリアルを直接結ぶ。 ⚠ `SearchAndRemapMaterials` は独立した .mat しか探さない。 |
| `RemapOkabeShinzo()` | `string` | 公 | — |
| `RemapDir(dir)` | `int` |  | — |

## EdoSannoShaBuilder.cs

山王権現社(日枝神社)本体+観理院+樹下家邸+山王門前町ビルダー (2026-08-11)

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/山王社/新造部材のマテリアルをremap` | `RemapSannoShinzoMenu` | `RemapSannoShinzo` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `ReloadSashizu()` | `void` | 公 | — |
| `Obj(o)` | `Dictionary<string, object>` |  | — |
| `Arr(o)` | `List<object>` |  | — |
| `Num(o)` | `float` |  | — |
| `Has(o, k)` | `bool` |  | — |
| `UV(u, v)` | `Vector2` |  | 指図の境内グリッド (u,v)[間] → 世界座標。 |
| `Ground(x, z)` | `float` |  | — |
| `Place(path, pos, ry, scale, parent, name)` | `GameObject` |  | — |
| `RB(go)` | `Bounds` |  | — |
| `SeatBottom(go, y)` | `void` |  | — |
| `Group(root, child)` | `Transform` |  | — |
| `Mat(c)` | `Material` |  | — |
| `Box(parent, name, pos, scale, m, ry=…)` | `GameObject` |  | — |
| `Cyl(parent, name, pos, scale, m, euler)` | `GameObject` |  | — |
| `PlaceNative(path, pos, ry, parent, name)` | `GameObject` |  | プレハブ固有スケールを保持して配置(Shiomizakaモデル等はルートに補正スケールを持つ) |
| `CenterSeat(go, x, z, sink=…)` | `void` |  | バウンズ中心を(x,z)へ、足元を接地 |
| `Stage1_Keidai()` | `string` | 公 | — |
| `Chozuya(parent, x, z)` | `void` |  | 手水舎: 4柱+屋根+水盤(Stone Basket) |
| `Shoro(parent, x, z, bell)` | `void` |  | 鐘楼/鼓楼(合成) |
| `Stage2_Sando()` | `string` | 公 | 石段=P_DanishiStep2m(汐見坂の段坂と同じ段石)+P_MichibataIshi2m(両脇の道端石)。 |
| `Torii(parent, x, z, ry)` | `void` |  | 石鳥居(明神鳥居, 合成) |
| `Tsutsui(parent, x, z)` | `void` |  | つつ井(屋形付き井戸) |
| `Endai(parent, x, z)` | `void` |  | 茶店の縁台(合成) |
| `Stage3_Kanriin()` | `string` | 公 | — |
| `Ido(parent, x, z)` | `void` |  | 井戸(簡素) |
| `Stage4_Juge()` | `string` | 公 | 2026-08-26 引退: 樹下邸は旧 EdoSannoBukeBuilder.Stage1_Juge が受け持ち、2026-09-21(EDO-0094)から 類型ビルダー(Edo_Typo_sannobuke_ju… |
| `Stage5_Monzencho()` | `string` | 公 | — |
| `MonzenMat(name, texPath)` | `Material` |  | — |
| `Stage6_Splat()` | `string` | 公 | 2026-09-23 引退(EDO-0422): 社地を旧い敷地割の形で土色に吹き、参道・女坂の帯を直書きの点列で塗っていた。 |
| `Stage6_Splat_Retired()` | `string` |  | — |
| `Stage7_Keidairin()` | `string` | 公 | — |
| `BuildAll()` | `string` | 公 | — |
| `RemapSannoShinzo()` | `string` | 公 | — |

## EdoSannoShaRebuild.cs

山王権現社 — 指図どおりに建て直すビルダー (2026-09-10 棟梁)

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/山王社/建て直し/指図を読み直す(キャッシュを捨てる)` | `Reload` | `Cv`, `G`, `F`, `HasNum` |
| `Edo/山王社/建て直し/0 旧実装を退避する(z=857 の物)` | `Stage0Menu` | `Stage0_Retire` |
| `Edo/山王社/建て直し/1 整地(算出物の設計面へ)` | `Stage1Menu` | `Stage1_Grade`, `Gate`, `UnSkin` |
| `Edo/山王社/建て直し/2 石段(男坂・女坂・参道の階)` | `Stage2Menu` | `Stage2_Kaidan`, `Gate`, `UnSkin` |
| `Edo/山王社/建て直し/3 土留め(13本。⛔ 埋まっている区間は建てない)` | `Stage3Menu` | `Stage3_Dodome`, `Gate`, `UnSkin`, `Group` |
| `Edo/山王社/建て直し/4 囲い(腰高の柵・板塀)` | `Stage4Menu` | `Stage4_Kakoi`, `Gate` |
| `Edo/山王社/建て直し/5 門・鳥居` | `Stage5Menu` | `Stage5_MonTorii`, `Gate`, `Group`, `Clear` |
| `Edo/山王社/建て直し/6 社殿5棟+木階` | `Stage6Menu` | `Stage6_Shaden` |
| `Edo/山王社/建て直し/7 社叢(算出物の点をそのまま置く)` | `Stage7Menu` | `Stage7_Shaso` |
| `Edo/山王社/建て直し/8 前庭の井戸(板石敷・井筒+井桁・井戸屋形)` | `Stage8Menu` | `Stage8_Ido`, `WKeidai`, `D`, `F` |
| `Edo/山王社/建て直し/9 縁の皮(段石・袖・土留め・面の縁の升に穴を開けて皮で描く)` | `Stage9Menu` | `Stage9_Hifu`, `Gate`, `Group` |
| `Edo/山王社/建て直し/5b 踏石・踏み止め(門・石段の頭の敷石)` | `Stage5bMenu` | `Stage5b_Fumiishi`, `Gate`, `Group`, `Clear` |
| `Edo/山王社/建て直し/一括(0→6・8・9。⛔ 社叢は撒かない)` | `BuildAllMenu` | `BuildAll`, `Gate` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Gate()` | `string` |  | — |
| `VerifyImplFingerprint()` | `void` |  | 算出物がいまの指図から焼かれた物か。⚠ 古い焼きで建てると、指図では直った はずの物が黙って復活する(2026-09-01 に松江松平の Stage7 で起きた型・EdoOkabeYashikiBuilder と同じ照合… |
| `Cv(o)` | `float` |  | — |
| `G(d, k)` | `object` |  | — |
| `F(d, k)` | `float` |  | — |
| `HasNum(d, k)` | `bool` |  | — |
| `D(d, k)` | `Dictionary<string, object>` |  | — |
| `L(d, k)` | `List<object>` |  | — |
| `S(d, k)` | `string` |  | — |
| `P2(o)` | `Vector2` |  | — |
| `Pts(l)` | `List<Vector2>` |  | — |
| `W(u, v)` | `Vector2` |  | 境内グリッド (u,v)[間] → 世界。 |
| `Group(child)` | `Transform` |  | — |
| `Clear(t)` | `void` |  | — |
| `PolyLen(p)` | `float` |  | 折れ線の道具 --------------------------------------------------------- |
| `PolyAt(p, s, pos, dir)` | `void` |  | 折れ線上の弧長 s の点と、その場の進行方向。 |
| `YawZ(d)` | `float` |  | ローカル +Z を d へ向ける yaw[deg]。 |
| `YawX(d)` | `float` |  | ローカル +X を d へ向ける yaw[deg]。 |
| `Stage0_Retire()` | `string` | 公 | いま建っている `Edo_Sanno_Sha`(z=857 の旧実装)を `Edo_Sanno_Sha_Kyu` へ改名して 非活性のままプレハブへ切り出す。 |
| `Stage1_Grade()` | `string` | 公 | 算出物 `graded` の設計面へ地形を寄せる。 |
| `InUngradedParcel(p)` | `bool` |  | 点 p が造成の持ち主が居ない区画(類型表 typology.json に載り built:hand でない区画 ── 類型ビルダーは造成しない)の中か。 |
| `NearSeg(segs, p, r)` | `bool` |  | — |
| `DemAt()` | `Func<float, float, float>` |  | 造成前の地盤(`sanno_dem.json`・2m 格子の双一次)。 |
| `Stage1_Grade(prevImplPath)` | `string` | 公 | 設計面から外れた節点を造成前の地盤へ戻して整地する。 |
| `Stage2_Kaidan()` | `string` | 公 | 算出物 `stairs` の `spans`(= 生成器の `stair_spans`)から段石を据える。 |
| `SodeWallsOf(kaidan)` | `Dictionary<string, List<Vector2>>` |  | 石段 kaidan に沿う袖の土留め(`terraceWalls` の coping:"stair" で `vFrom.kaidan` か `copingFrom.kaidan` がこの石段)→ 算出物の折れ線。 |
| `TopFaceOf(stair, face, poly, y, kind)` | `bool` |  | 取り合いの欄(`joints`)で石段 stair の最上段の相手になっている面(`平場 <名>`)。 |
| `SodeFootAt(x, z)` | `float` |  | 袖の見え面の足元の設計面(算出物 graded の双一次。 |
| `IsSodeWall(tw)` | `bool` |  | 石段に沿う土留め = 袖(石段の組で据える)か。 |
| `DistToPoly(p, c)` | `float` |  | — |
| `GroupNameOf(designName)` | `string` | 公 | 指図の名 → シーンの群の名。⛔ 綴りの読み替えだけ(⭐ 対応表が消えるのが正しい終点)。 |
| `Stage3_Dodome()` | `string` | 公 | 算出物 `runs` の `of=="wall"` を石垣で積む。 |
| `Nozura(runs, grp, placed, faceOf, dg, probe, sb)` | `int` |  | 野面の乱積みの土留め(`terraceWalls[].masonry`)を据える。 |
| `SegIsBase(prof, step, sBase, len)` | `bool` |  | 区間が基壇か ── 建つ所(見付 &gt; 0)の受け高が全て負(天端が両側の地盤より上)。 |
| `IsNozuraSode(g)` | `bool` |  | 袖の駒が野面の乱積みの袖(`IshidanSodeNozura*`)か(メッシュの資産名で)。 |
| `FamilyOf(n)` | `string` |  | — |
| `ArcOf(poly, p)` | `float` |  | 折れ線 poly 上での点 p の弧長。 |
| `ProfileAt(prof, step, s, top, faceH, backH)` | `bool` |  | `profile` = [走り s, 天端 y, 低い側の地盤, 高い側の地盤, 見付高, 受け高] を s で線形補間。 |
| `AbutStairsToWalls()` | `string` | 公 | Stage3 の後段: 全ての石段について、段石の両の小口と袖の背の小口を脇の土留めの面へ突き付ける(EDO-0430)。 |
| `Stage4_Kakoi()` | `string` | 公 | 算出物 `runs` の `of=="run"` を建てる。 |
| `SakuRun(r, name, grp, hasSeat, seat, sb)` | `int` |  | 腰高の柵の run。部材の原点 = スパンの中心・地盤レベル・柱はローカル −X 端。 |
| `SakuProfile(halfT, hgt, postL)` | `void` |  | 腰高の柵の部材の半厚・丈・柱の長さ[m]を資産から測る。 |
| `PanelProfile(path, halfT, hgt)` | `void` |  | 板塀(edogoyomi の片面 obj)の半厚・丈[m]を資産から測る。 |
| `ClipRunEndsToGates(a, b, hgt, halfT, hasSeat, seat, name, sb)` | `void` |  | 口(seg と seg の間)に門が建つなら、両脇の seg の端を門の脇柱の角へ取り付ける。 |
| `RetractRunEndsFromWalls(sa, sbb, halfT, hgt, hasSeat, seat, name, sb)` | `void` |  | 柵・板塀の run の端(始まり・終わり・口の両脇)が土留め・基壇の駒の中に在るなら、その実面まで詰める (EdoBuild.RetractEndFromBodies・2026-09-26 EDO-0430)── `It… |
| `ShiftRunToCutShoulder(sa, sbb, halfT, hgt, hasSeat, name, sb)` | `void` |  | 切土の法に沿う板塀の走りを法肩の上へ移す(2026-09-26・EDO-0437 施主裁定イ)。 |
| `BuiltSegs(r, a, b)` | `void` | 公 | run の `segs` を、Stage4 が実際に建てる区間へ直して返す(口に門が建つなら、その縁を 門の脇柱の角へ取り付けた後の端)。 |
| `GatePlacement(gt, path, pos, yaw)` | `bool` |  | 算出物の `gates[]` の行から、据える部材のパス・座・向きを引く(Stage5 と同じ物差し)。 |
| `Kairo(r, name, grp, sb)` | `int` |  | 回廊の翼を1本据える(2026-09-20 に建てはじめた)。 |
| `FindBom(label)` | `Dictionary<string, object>` |  | 部材表の行を名で引く。⛔ 寸法をここに写さない。 |
| `BomPartPath(label)` | `string` |  | `bom[<label>].手当` が名指す部材のパスを引く(「… → `Assets/….fbx`」の最初の一つ)。 |
| `GateNameOf(designName)` | `string` | 公 | 門の名 → シーンの名(⛔ 部材のパスではない)。 |
| `Sukibei(r, name, grp, sb)` | `int` |  | — |
| `SukibeiPart(spanM, ends, name, sb)` | `string` |  | スパンの呼び寸[m]と端の種類から部材を引く。 |
| `SukibeiKado(sb)` | `int` |  | 透塀の隅部材を据える。隅は `joints` が名指す run の対(8箇所)で、 出隅・入隅の別は折れ線の凹凸から測る(⛔ 決め打ちしない)。 |
| `Sodebei(r, name, grp, sb)` | `int` |  | 袖塀(楼門と回廊の翼の間)を据える。部材の註: 走り = X・門側 = −X・ ピボット = 走りの中心・門側の足元(= 楼門の敷居)。 |
| `GateBed()` | `EdoBuild.Bed` | 公 | 設計面(算出物)を優先し、無ければ live terrain。 |
| `SurfaceY(p)` | `float` |  | — |
| `Stage5_MonTorii()` | `string` | 公 | 算出物 `gates` の芯・yaw・敷居の高さへ据える。 |
| `ToriiPart()` | `string` |  | 石造明神鳥居の部材。⭐ まず `bom[鳥居].手当` を見る(正典は指図)。 |
| `Michi()` | `List<List<Vector2>>` |  | 道の芯線(算出物 `routes[].world` と指図 `fumotomichi[].pts`)を集める。 |
| `ToriiFacing(p, face)` | `bool` |  | 鳥居の正面(部材の +Z)の向き。⭐ 指図は鳥居の yaw を書かない(座だけ)ので、 鳥居が載っている道の芯線の接線から引く ── 正面は境内から遠い側(参詣者が来る方)。 |
| `ToriiNameOf(designName)` | `string` | 公 | 鳥居の名 → シーンの名(⛔ 部材のパスではない)。 |
| `Stage6_Shaden()` | `string` | 公 | 社殿。⭐ 部材のピボット = その棟の区画 (u0,v0,du,dv) の中心・地盤レベル。 |
| `PartFromPath(partFrom)` | `string` |  | 棟・鳥居の `partFrom` を部材のパスへ解く。 |
| `FrontAxisOf(row, label, name=…, path=…)` | `string` |  | 部材の「正面はローカルのどの軸か」の宣言を引く。 |
| `Muki(row, label, name, yaw, why)` | `bool` |  | 棟・鳥居の yaw を、図の `front`(方位)と部材の `axis.front`(ローカル軸)から出す。 |
| `Muki(row, label, name, path, yaw, why)` | `bool` |  | — |
| `ToriiFromMune(grp, sb, pend)` | `int` |  | 棟に寄る鳥居(`torii[].posFrom`)を据える。 |
| `BomLabelFor(mune)` | `string` |  | 棟の名 → `bom` の行の名。⭐ 行は「棟の名」そのものか「棟の名(役)」で立っている (例 `御供所` → `御供所(供の棟)`)。 |
| `ShadenNameOf(designName)` | `string` | 公 | 棟の名 → シーンの名。⭐ 突き合わせ(`EdoSannoShaCheck`)も同じ物差しを使う ⇒ public(⛔ 検査が別の名簿を持たない・規則19)。 |
| `RetireKeidairin()` | `string` |  | — |
| `Stage7_Shaso()` | `string` | 公 | 社叢。⛔ 撒き直さない・乱数を振らない ── 算出物 `planting.points` の 1点 1本を そのまま置くだけ。 |
| `TreePath(q)` | `string` |  | 点の `part`(例 `Own.Matsu("Mid", 3)`)を部材のパスへ解く。 |
| `FindByName(src, key, name)` | `Dictionary<string, object>` |  | — |
| `WKeidai(u, v)` | `Vector2` |  | 境内グリッド (u,v)[間] → 世界。 |
| `Stage8_Ido()` | `string` | 公 | 前庭の井戸 — 指図 `ido` の3点を据える(2026-09-23・EDO-0274)。 |
| `Stage9_Hifu()` | `string` | 公 | — |
| `SkinFaces(sb)` | `List<EdoBuild.SkinFace>` |  | 皮が高さを揃える面 = 算出物 `terraces` + 取り合いの欄の「被せ」(面の輪郭が石段の最上段の外形を包む ── `EdoBuild.WrapTopStep` で最上段の実メッシュから輪郭を測って足す・join… |
| `HifuGapTable()` | `string` | 公 | 皮と部材の隙の内訳(A 面の高さで塞がる / B 駒が浮く / C 面の外の取り合い)を皮を起こし直さずに刷る。 |
| `HifuMeasure()` | `string` | 公 | 描かれた地表(皮)で測る: 男坂・女坂の踏面の埋没・袖と土留めの天端の埋没。 |
| `Stage5b_Fumiishi()` | `string` | 公 | — |
| `UnSkin()` | `string` |  | 据え直す Stage の冒頭で縁の皮を外す(穴を塞ぐ)。 |
| `RunFrom(changed)` | `string` | 公 | 変えた Stage から後だけ流す(key: Retire・Grade・Kaidan・Dodome・Kakoi・Mon・Fumiishi・Shaden・Ido・Hifu)。 |
| `PlanFrom(changed)` | `string` | 公 | 流さずに、流れる Stage だけを見積もる。 |
| `BuildAll()` | `string` | 公 | — |

## EdoSanyashikiRebuild.cs

三屋敷(太田・加納・鍋島=松平肥前守)の区画を下書きv3へ更新 (2026-08-08)

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `PIP(poly, p)` | `bool` |  | EdoGeom.PIP と実装差あり — 統一は裁定待ち |
| `InwardN(e, i)` | `Vector2` |  | — |
| `S1_Deactivate()` | `string` | 公 | — |
| `S2_GradeEdges()` | `string` | 公 | 池保護矩形: (2,190)-(48,230) ±6m は不変 |
| `S3_Enclosure(groupName)` | `string` | 公 | — |
| `S4_QA()` | `string` | 公 | — |

## EdoSekiBuilder.cs

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/建造/石垣の堰を作る` | `Build` | — |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `OneSidedFootprint(line, waterCenter, thick)` | `List<Vector2>` |  | 片面壁の底面ポリゴン: 線を陸側(水と反対)へ厚みぶんオフセットして閉じる。 |
| `MakeFrustum(name, topPoly, parent, mat)` | `void` |  | 天端ポリゴン(CCW/CW自動)を、外側に勾配をつけて基部へ押し出した石垣メッシュ。 |
| `IntegrateTerrain(polys)` | `void` |  | 石垣の各辺を「水側」か「陸側(端)」に分類し、水側の地形を水面下まで掘って石を出し、 陸側の地形を天端まで上げて端を埋める。 |
| `PunchHoles(polys, inset)` | `void` |  | 複数フットプリントの内側の地形セルに穴を開ける(石垣が地形に埋もれない)。 |
| `PointInPolyInset(p, poly, inset)` | `bool` |  | — |
| `PointInPoly(p, poly)` | `bool` |  | — |
| `DistToSeg(p, a, b)` | `float` |  | — |

## EdoShiomizakaRebuild.cs

汐見坂(段坂)を新区割りの回廊へ敷き直す (2026-08-09)

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `W(t, n)` | `Vector2` | 公 | — |
| `Profile(t)` | `float` | 公 | — |
| `BuildProfile()` | `void` |  | — |
| `Steps()` | `List<Vector2>` | 公 | — |
| `RoadH(t)` | `float` | 公 | — |
| `Z0_Restore(baselinePath)` | `string` | 公 | ⚠ 造成後の地形からプロファイルを取り直すと「前回の段」を地形と誤認して段が減り続ける。 |
| `Z1_Grade()` | `string` | 公 | — |
| `Z2_Mesh()` | `string` | 公 | — |
| `Z3_Danishi()` | `string` | 公 | — |
| `Z4_ReseatGate()` | `string` | 公 | — |
| `Z5_QA()` | `string` | 公 | — |
| `RunAll()` | `string` | 公 | — |

## EdoTypologyBuilder.Inari.cs

類型ビルダー — 稲荷(町屋の裏手の小祠と鳥居)。EDO-0326。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Inari(s, root, poly, fronts, shopD, gateC, built)` | `string` |  | 町内の稲荷。表店の列の背後(裏手)へ小祠を据え、その正面へ鳥居を立てる。 |

## EdoTypologyBuilder.Jisha.cs

類型ビルダー — 寺社の境内(Stage 3〜4 の jisha 分)。本堂・庫裏・蔵・鐘楼・墓地・塔頭を置く。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `JCorners(e, p, yawDeg)` | `Vector2[]` |  | ───────────────────────── 矩形の下働き ───────────────────────── |
| `JCenter(c)` | `Vector2` |  | — |
| `JSep(a, b)` | `float` |  | 凸四角形どうしの離れの下限[m](負ならめり込み)。 |
| `JInside(poly, c, margin)` | `bool` |  | 矩形の四隅と各辺の 5 分点が、区画の内側で縁から margin 以上あるか。 |
| `JMinEdge(poly, c)` | `float` |  | — |
| `JExt(go, withRoof, e)` | `bool` |  | 駒の局所矩形(ピボットからの x0,x1,z0,z1)を実メッシュから測る。 |
| `JYaw(dirZ)` | `float` |  | — |
| `JishaOmoya(s, root, poly, front, pad, gateC)` | `string` |  | 寺社の境内を建てる。⭐ Omoya() の jisha 枝 — 返る文字列は「主屋と付属: …」の 2 行。 |
| `JAdd(items, dropped, g, name, path, mode, yaw, rank)` | `void` |  | プレハブの駒を 1 つ起こして一覧へ足す。 |

## EdoTypologyBuilder.Machiya.cs

類型ビルダー — 町屋(machiya)の段。24 区画。EDO-0325。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `OmotedanaFor(maguchiKen)` | `string[]` |  | その間口の表店を当方で起こしてあるかを資産の有無で見て、あれば深い順に返す (深い版 → 詰めた版)。 |
| `MachiyaFrontEdges(s, edges, front)` | `List<Edge>` | 公 | 表店を載せる接道辺。`two_sided=false` は 1 本、`true` は長い順に 2 本。 |
| `Machiya(s, root, poly, front, edges, pad, gateC, gateHalf)` | `string` |  | Stage 3m — 町屋。表店の列(接道辺 1〜2 本)・自身番屋・裏長屋。 |
| `UraNagaya(s, root, poly, fronts, depthM, roomM, shopD, pad, avoid)` | `string` |  | 裏長屋(裏店)。表の `ura_nagaya` がそのまま数ならその棟数まで、 数でなければ奥行と間口から割った列を全部建てる(表の `defaults.machiya.ura_nagaya` が 「間口と奥行から割る」… |
| `UnusedFields(s)` | `string` |  | ⛔ ビルダーが読みもしていない欄を黙って捨てない(規則19)。 |

## EdoTypologyBuilder.Niwa.cs

類型の庭(Stage 5)— どの類型が何をどこへだけ。EDO-0323。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `LinMix(rnd, deShare)` | `Func<string, string>` |  | 屋敷林の個体の採り方。⭐ 庭全体で常緑:落葉 = 7:3(覆さない線③)に着地させる。 |
| `DeShare(band)` | `float` |  | 帯の落葉の割り。⭐ 0.30 固定(庭方 2026-09-22 の直し③)。 |
| `MomijiPalFor(garden)` | `string[]` |  | モミジの個体プール。⭐ 型で決める(庭方 2026-09-22 の裁定7)— 坪庭は常に Small だけ(MaxCrown 2.45m)、chisen/small は Mid も混ぜる(3.49m)。 |
| `Rng(r, lo, hi)` | `int` |  | — |
| `Odd(r, lo, hi)` | `int` |  | 奇数で引く(⛔ 偶数の塊を作らない)。 |
| `Rf(r, lo, hi)` | `float` |  | — |
| `OddSplit(total, rnd)` | `List<int>` |  | 層の本数を奇数の塊へ割る(7/5/3/1)。 |
| `MaxCrown(pal)` | `float` |  | — |
| `TakeSite(pool, rnd, f, r, o)` | `Vector2?` |  | 候補の池から、その半径が本当に空いている点を1つ取り出す。 |
| `Layer(grp, name, f, pool, pal, want, rnd, o, want_, got_, poolAlt=…)` | `void` |  | 層をひと組据える。⭐ 意図した数と据わった数の差を必ず控える(§5-2 ①・規則19)。 |
| `MainBand(f, apex, n, faceLen, depth)` | `List<Vector2>` |  | 主景の帯 — 座敷面の中点 + 法線 3.0m を起点に、幅 = 面長 + 左右各 4.0m・奥行 25m の 帯と庭域 G の交わり(検分⑨)。 |
| `GateThrough(gate)` | `float` |  | 門の通り抜け(柱間)[m] — 参道の帯(白洲)の幅を引くための代用値(検分③)。 |
| `Perimeter(poly)` | `float` |  | — |
| `AddGroundZone(grp, kind, pts, radius=…)` | `void` |  | 点の集合を NiwaGroundZone として grp の下へ置く。 |
| `AddSandoZone(grp, f)` | `float` |  | 参道の帯(白洲)を帯の四角形そのものとして印に置く(EDO-0372)。 ⟶ 返す: 帯の区画内の面積[m²] |
| `SandoAxis(s, root, front, gateC, openHow)` | `float` |  | 参道の帯の芯と片側の幅。gateC を門の通り抜けの実開口の芯へ寄せ、 片側 = 開口/2 + 1.5(上限 6.0m)を返す。 |
| `Niwa(s, root, poly, front, pad, gateC, gateHalf)` | `string` |  | 庭を建てる。gateC / gateHalf は Stage 1 で 実測した門構えの開口(⛔ 当て推量の GateWidth ではない)。 |
| `NiwaChisen(s, grp, f, poly, front, rnd, main, katte, per, faceLen, zashikiMid, zashikiN, gateC, bandHalf, want, got, log, k)` | `void` |  | 池泉(大名上屋敷)と中規模(中屋敷)。k = 1.0 なら chisen、 0.55 なら small(⛔ small は池代地を持たない)。 |
| `NiwaTsubo(s, grp, f, poly, front, rnd, main, per, zashikiMid, zashikiN, want, got, log)` | `void` |  | 坪庭(大身旗本)。⭐ 本義は棟と棟の間のポケット(軒から1.0〜6.0 の最大連結成分)。 |
| `NiwaUra(s, grp, f, mune, rnd, katte, kdir, cO, want, got, log)` | `void` |  | 裏庭(中級旗本)。⭐ 実用の庭。作庭しない庭として作る。 |
| `NiwaIshigumi(grp, f, pool, rnd, kumi, want, got, poolAlt=…)` | `void` |  | 景石(1組 = 三石)。⭐ 丈 1.000 に正規化した部材なので localScale = 総丈、 沈めは 総丈÷3(1/3埋め・庭方 §5-0「据え」)。 |
| `NiwaTobiishi(grp, f, rnd, start, aim, n, want, got, log, label=…)` | `void` |  | 飛石1条 — 座敷面の中点の外 2.0m から庭へ下りる筋(検分①)。 |
| `NiwaToro(grp, f, pool, rnd, n, want, got, poolAlt=…)` | `void` |  | 灯籠(雪見)。⚠ edogoyomi の駒なので ES を掛ける。 |
| `NiwaIdo(grp, f, katte, rnd, n, want, got, log)` | `void` |  | 井戸。⚠ 類型の井戸の部材は未造で、山王社の井桁の井戸を当てている(部材方へ・EDO-0318)。 |
| `NiwaMaeniwa(grp, f, rnd, gateC, bandHalf, front, want, got)` | `void` |  | 前庭。⛔ 帯の中には置かない(白洲)。門の内側の左右に松を必ず非対称に。 |
| `NiwaInspect(f, g, want, got)` | `string` |  | 庭方 §5-2 の5項目。⛔ 「置けた本数」だけを刷らない — 意図との差・帯の侵入・ 実測の離れ・偶数の塊・樹冠の被覆率まで出して、はじめて検査になる。 |

## EdoTypologyBuilder.cs

類型ビルダー — 区画の形(parcels.json)と類型表(typology.json)から、一本で建てる。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/類型/選択中の区画を建てる` | `BuildSelectedMenu` | `BuildParcel`, `BuildTargetMenu` |
| `Edo/類型/狙った区画を建てる %#t` | `BuildTargetMenu` | `BuildParcel`, `PickTargetMenu` |
| `Edo/類型/区画を選ぶ(区画割の選択から)` | `PickTargetMenu` | — |
| `Edo/類型/全区画を建てる` | `BuildAllMenu` | `BuildAll`, `BuildParcel` |
| `Edo/類型/辺の素性を検める(選択中)` | `EdgesMenu` | `Edges`, `FrontEdge` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `S(d, k)` | `string` |  | — |
| `I(d, k, dflt)` | `int` |  | — |
| `IA(d, k)` | `int[]` |  | 整数の配列(`main_hall_ken` = [桁行, 梁間] など)。 |
| `Bo(d, k, dflt)` | `bool` |  | — |
| `DefaultsFor(d)` | `Dictionary<string, object>` |  | この区画の類型に当たる defaults の塊。 |
| `Fill(d, def)` | `void` |  | 区画に書いていない欄だけ既定で埋める(表の `_` の約束「区画の欄が null のとき ビルダーがここから採る」の実装)。 |
| `LoadTable()` | `void` | 公 | — |
| `Centroid(poly)` | `Vector2` |  | — |
| `Outward(poly, i)` | `Vector2` |  | — |
| `Edges(id)` | `List<Edge>` | 公 | 辺ごとに「道に面するか、隣の区画と共有か」を実際の区画の形から決める。 |
| `DirVec(d)` | `Vector2` |  | — |
| `FrontEdge(s, edges)` | `Edge` | 公 | 表門を載せる辺。 ⭐ 史料で読めた方位は、長さの都合より強い。 |
| `FrontEdge(s, edges, warn)` | `Edge` | 公 | — |
| `TuckInside(go, poly, outward, log)` | `float` |  | 辺に載らない門構えを敷地の内へ折り込む。 ⟶ 返す: 下げた量[m](0 なら折り込み不要) |
| `Seat(go, log)` | `bool` |  | 接地箇所を測って据える(EdoBuild.SeatOnGround)。 |
| `Pad(id, spread)` | `float` | 公 | 造成はしない(規則3・9)。区画内のハイトマップ格子点の高さの中央値を、据える面に採る。 |
| `GatePath(g)` | `string` |  | ───────────────────────── 部材の解決 ───────────────────────── |
| `GateScale(g)` | `float` |  | 門の部材の倍率。⛔ 一律 ES を掛けない。 |
| `GateWidth(s)` | `float` |  | 門の実幅の概算(m)。⛔ 部材の実メッシュではなく「表門の辺を選ぶための目安」で、 据えた後の納めは実メッシュで解く(規則5)。 |
| `BanshoCount(b)` | `int` |  | — |
| `Group(name, parent)` | `Transform` |  | ───────────────────────── Stage 1〜2: 囲いと門 ───────────────────────── |
| `FindRoot(name)` | `GameObject` |  | シーンのルートを名前で引く。⭐ 寝ているルートも拾う — 撤去は SetActive(false) の決まり(規則1)なので、GameObject.Find だけでは見落とす。 |
| `Externalize(root)` | `string` |  | 建て終えた類型ルートを 1軒1プレハブ へ切り出す(EDO-0296)。 |
| `BuildParcel(id, force)` | `string` | 公 | — |
| `FenceFace(encl, front)` | `float` |  | 前辺に建った塀の通りの側の面が、区画の境界線からどれだけ外/内にあるか。 |
| `EnclosureFor(s, e, isFront)` | `string` |  | この辺を何で囲うか。⛔ 2026-09-21 まで公有地は `fence` の欄を読まずに `yarai` を直書きしていて、 表に書いた yarai 1 / boji 3 / kui 1 / ita 1 / none… |
| `Omoya(s, root, poly, front, pad, gateC)` | `string` |  | 主屋・付属・庭木。区画の内側へ SETBACK 引いた所に、型ごとの棟を置く。 |
| `PairDir(a, b)` | `Vector3` |  | 二つの駒を互いへ押し付ける向き(a から b・水平)。 |
| `OmoyaOf(s)` | `string` |  | この区画の主屋の型。⭐ 表の `omoya` が勝ち、書いていないときだけ格帯から採る (割り当ては docs/typology-builder.md §4 の表と同じ)。 |
| `Plan(s)` | `List<KeyValuePair<string, float>>` |  | 型ごとに「何を何棟」。⛔ 在庫の代用が多い — 専用部材は部材方の宿題。 |
| `Inner(poly, d)` | `List<Vector2>` |  | 区画を d だけ内側へ寄せた所の「置ける点」を粗い格子で拾う。 |
| `Candidates(poly, cand, placed, r, tried)` | `IEnumerable<Vector2>` |  | Spot を次々に引く候補の列(引いた点は tried へ入れる)。 |
| `Spot(poly, cand, placed, r, tried)` | `Vector2?` |  | まだ空いていて、半径 r が区画からはみ出さず、既に置いた棟から MIN_BLDG_GAP 離れる点。 |
| `OutsideBy(poly, t, withRoof)` | `float` |  | 駒が区画の外へ出た量[m]。⭐ 壁体と軒を分けて測る。 |
| `Inspect(id, root, poly)` | `string` | 公 | 境界侵犯・埋没・浮きを、建てたその場で測って刷る(0件でも刷る・規則19)。 |
| `BuildAll(force)` | `string` | 公 | — |

## EdoYamatoRebuild.cs

松平大和守(川越藩17万石)上屋敷の再建 v2 (2026-08-08)

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `VG(p)` | `float` |  | — |
| `PIP(poly, p)` | `bool` |  | EdoGeom.PIP と実装差あり — 統一は裁定待ち |
| `DEdge(p)` | `float` |  | — |
| `PadAt(p)` | `float` | 公 | 基壇を考慮した設計地盤(建物・庭の接地用) |
| `Y1_Grade()` | `string` | 公 | — |
| `PlanSegments(log)` | `List<Seg>` |  | — |
| `Y2_Enclosure()` | `string` | 公 | — |
| `PlaceUV(path, u, v, yawOff, scale, parent, name)` | `GameObject` | 公 | — |
| `Y3_Buildings()` | `string` | 公 | — |
| `NohButai(parent, u, v)` | `void` |  | — |
| `UmayaPair(parent, u, v, name)` | `void` |  | — |
| `Well(parent, u, v)` | `void` |  | — |
| `Inari(parent, u, v)` | `void` |  | — |

