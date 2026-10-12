# 邸ビルダーの目録(生成物・手で直さない)

<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py -->

**メニューの名・Stage の関数・ビルダーの中の関数を探すときは、C# を grep で読み歩かずまずここを引く。**
Stage の本体(何をどの順に据えるか)は目録に無い — 名を決めてから、その関数の行だけ読む。

- `Assets/Edo/Scripts/Editor/Edo*Builder*.cs`・`Edo*Rebuild*.cs` 27 本・メニュー 94・関数 957(非公開も)。
- メニューは Unity の `execute_menu_item` にそのまま渡せる全名。呼ぶ関数 = メニューの関数の頭で呼んでいる同じファイルの関数。
- 関数へ跳ぶ: `grep -n "static .* <名>(" Assets/Edo/Scripts/Editor/<ファイル>`。
- 据え方の関数は `docs/edobuild-mokuroku.md`、部材の名は `docs/edoassets-mokuroku.md`。⛔ 手で直さない(`python3 Tools/Unity/edobuild_mokuroku.py`)。

## ファイルの索引

| ファイル | 何の道具か(ファイル冒頭の注釈) | メニュー | 関数 |
|---|---|---|---|
| [EdoDoiBuilder.Dan.cs](#edodoibuilderdancs) | ══════════════════════════════════════════════════════════════════════ | 1 | 6 |
| [EdoDoiBuilder.Hifu.cs](#edodoibuilderhifucs) | 土井 S4b 縁の皮(案A・EDO-0533)── 2m 格子の地形では描けない土留めの天端の奥・石段の踏面・面の縁の升に穴を開け、 | 1 | 2 |
| [EdoDoiBuilder.Mizo.cs](#edodoibuildermizocs) | 土井 S9 排水(案A・EDO-0533)── 指図 drains[D1〜D13] の segs/masu/cross/toriai/outletBuild と drainKata(型 A〜P)を読み、 | 1 | 10 |
| [EdoDoiBuilder.Mon.cs](#edodoibuildermoncs) | ══════════════════════════════════════════════════════════════════════ | 1 | 17 |
| [EdoDoiBuilder.Mune.cs](#edodoibuildermunecs) | ══════════════════════════════════════════════════════════════════════ | 2 | 11 |
| [EdoDoiBuilder.Niwa.cs](#edodoibuilderniwacs) | 土井大隅守上屋敷 — 奥庭(Stage6)。 | 4 | 82 |
| [EdoDoiBuilder.Saku.cs](#edodoibuildersakucs) | 土井 S6 柵・垣(案A・EDO-0533)── 指図 fences[] を読み、EdoBuild.GakiRun で敷く。 | 1 | 3 |
| [EdoDoiBuilder.Shokusai.cs](#edodoibuildershokusaics) | 土井 S8 植栽(案A・EDO-0533)── 林方の設計(指図 planting)を生成器が撒いた点 `doi_impl.json` の planting.points を据える。 | 2 | 4 |
| [EdoDoiBuilder.cs](#edodoibuildercs) | 土井大隅守上屋敷(三河刈谷藩2万3千石・譜代・雁間)ビルダー。 | 15 | 89 |
| [EdoMatsudairaDewaBuilder.Niwa.cs](#edomatsudairadewabuilderniwacs) | 松平出羽守上屋敷 — 庭の工程(池・築山・水の系・石組・点景・滝見口)。 | 9 | 30 |
| [EdoMatsudairaDewaBuilder.cs](#edomatsudairadewabuildercs) | 松平出羽守上屋敷(出雲松江藩 18万6千石)ビルダー。 | 16 | 120 |
| [EdoOkabeYashikiBuilder.cs](#edookabeyashikibuildercs) | 岡部筑前守長寛(和泉岸和田藩5万3千石・譜代・帝鑑間)上屋敷 ビルダー — 全面起こし直し(2026-09-03) | 21 | 274 |
| [EdoSannoShaBuilder.cs](#edosannoshabuildercs) | 山王権現社(日枝神社)本体+樹下家邸+山王門前町ビルダー (2026-08-11。観理院は 2026-09-26 に類型へ移し削除) | 1 | 31 |
| [EdoSannoShaRebuild.cs](#edosannosharebuildcs) | 山王権現社 — 指図どおりに建て直すビルダー (2026-09-10 棟梁) | 13 | 102 |
| [EdoSanyashikiRebuild.cs](#edosanyashikirebuildcs) | 三屋敷(太田・加納・鍋島=松平肥前守)の区画を下書きv3へ更新 (2026-08-08) | 0 | 6 |
| [EdoSekiBuilder.cs](#edosekibuildercs) | — | 1 | 8 |
| [EdoShiomizakaRebuild.cs](#edoshiomizakarebuildcs) | 汐見坂(段坂)を新区割りの回廊へ敷き直す (2026-08-09) | 0 | 12 |
| [EdoTypologyBuilder.Inari.cs](#edotypologybuilderinarics) | 類型ビルダー — 稲荷(町屋の裏手の小祠と鳥居)。EDO-0326。 | 0 | 1 |
| [EdoTypologyBuilder.Jisha.cs](#edotypologybuilderjishacs) | 類型ビルダー — 寺社の境内(Stage 3〜4 の jisha 分)。本堂・庫裏・蔵・鐘楼・墓地・塔頭を置く。 | 0 | 18 |
| [EdoTypologyBuilder.Katte.cs](#edotypologybuilderkattecs) | 類型ビルダー — 勝手まわり(低い平場の菜園と、主の平場から降りる段石)。EDO-0532 施主裁定A(2026-10-03)。 | 0 | 1 |
| [EdoTypologyBuilder.Keidai.cs](#edotypologybuilderkeidaics) | 類型の庭 — 寺社の境内(garden=keidai)。2026-09-27・EDO-0477 P5。 | 0 | 3 |
| [EdoTypologyBuilder.Machiya.cs](#edotypologybuildermachiyacs) | 類型ビルダー — 町屋(machiya)の段。24 区画。EDO-0325。 | 0 | 9 |
| [EdoTypologyBuilder.Niwa.cs](#edotypologybuilderniwacs) | 類型の庭(Stage 5)— どの類型が何をどこへだけ。EDO-0323。 | 0 | 27 |
| [EdoTypologyBuilder.Rim.cs](#edotypologybuilderrimcs) | 類型の崖の縁の石垣(Stage 4y・2026-09-28・EDO-0477 施主裁定A「石垣を積み、その上に塀」)。 | 0 | 2 |
| [EdoTypologyBuilder.Yuragi.cs](#edotypologybuilderyuragics) | 類型ビルダー — 揺らぎ(EDO-0476・施主裁定 2026-09-27)。 | 0 | 21 |
| [EdoTypologyBuilder.cs](#edotypologybuildercs) | 類型ビルダー — 区画の形(parcels.json)と類型表(typology.json)から、一本で建てる。 | 5 | 55 |
| [EdoYamatoRebuild.cs](#edoyamatorebuildcs) | 松平大和守(川越藩17万石)上屋敷の再建 v2 (2026-08-08) | 0 | 13 |

## EdoDoiBuilder.Dan.cs

══════════════════════════════════════════════════════════════════════

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `4a 邸内の土留め・石段(案A)` | `Stage4aMenu` | `Stage4a_Dodome` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `DanStepQOf(runName)` | `float` |  | runs[name].seatFrom が「段は X の倍数」と名乗るなら X、無ければ 0(段塀の刻み ── EdoBuild.DanPlan)。 |
| `TerracePolyW(name, y)` | `Vector2[]` |  | terraces[name] の多角形(主郭の格子 u,v)を世界へ。 |
| `Stage4a_Dodome()` | `string` | 公 | S4 邸内の土留め・石段(案A・EDO-0533)。 |
| `MeasureNozura(nm, got, a, b, cop, hardMax, footPoly, footY, abutA, backP, backN, tally)` | `string` |  | 据わった野面の駒を測る(据えは動かさない)。 |
| `PlaceKaidansA(tally)` | `string` |  | kaidans(案A の書式 `pos` `dir` `steps` `keri` `fumi` `w` `y0` `y1`)を EdoBuild.SlopeSteps で据える。 |

## EdoDoiBuilder.Hifu.cs

土井 S4b 縁の皮(案A・EDO-0533)── 2m 格子の地形では描けない土留めの天端の奥・石段の踏面・面の縁の升に穴を開け、

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `4b 縁の皮(土留め・石段の足元の升を皮で描く)` | `Stage4bHifuMenu` | `Stage4b_Hifu` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Stage4b_Hifu()` | `string` | 公 | — |

## EdoDoiBuilder.Mizo.cs

土井 S9 排水(案A・EDO-0533)── 指図 drains[D1〜D13] の segs/masu/cross/toriai/outletBuild と drainKata(型 A〜P)を読み、

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `9 排水(雨落ち・溝・桝・落とし)` | `Stage9MizoMenu` | `Stage9_Mizo` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Gk(d, k)` | `object` |  | 欄が無ければ null(指図の drains は系統ごとに持つ欄が違う ── 索引子で引くと KeyNotFound で S9 ごと落ちる)。 |
| `Stage9_Mizo()` | `string` | 公 | — |
| `MasuPlannedChecks9(mz, go, pl, blds, eave, segs, masuOf, masuFace, line)` | `bool` |  | 群の下で名が prefix(または prefix_…)の段を持つ駒(Stage9 の piecesByPrefix と同じ引き方)。 |
| `PiecesByPrefix9(prefix, root)` | `List<GameObject>` |  | — |
| `BuildDanOchi9(g, grp, solvedEnds, receivers, masuOf, kf, line)` | `void` |  | 型 H(段落ち)の区間: 頭の底(始点の区間の尻・入る区間の尻 ── 線の頭から 3m 内)と尻の狙い(欄の 段 × 1段/吐口が塀の水抜きなら塀の外の道 + bottomAboveRoad)を 欄から読み、EdoBui… |
| `BuildHariOtoshi9(g, grp, byId, edgeChk, kf, line)` | `void` |  | 区間の欄 drop(型 I 張り石の落とし): 始点 = 座の「辺N 側の縁」のうち受ける区間に最も近い所・終点 = 受ける区間の線(垂線の足)を引き、 頭 = 座の縁の地盤(この区間の尻の底が低ければそれ)・法尻 =… |
| `BuildUke9(g, grp, masuAt, masuFloor, edgeChk, line)` | `void` |  | 型 J(玉石の受け)の区間: 線「受け: <条件> のうち <起点> に最も近い所に a×b 間」を読み、起点の桝(据えた位置)・指名の辺・勾配の上限を EdoBuild.PlaceUke(置き場は PlaceBest… |
| `BuildAfterUke9(g, grp, masuAt, segById, kf, line)` | `bool` |  | ⑥ 線「<Dn> masu[k] の芯から <区間> の受けの縁の最寄りの中央へ直線 ── 頭は地盤が埋樋の管底 + c まで下がった所・尻は受けの底」の型 H(段落ち)を、 桝と受け(型 J)を据えた後に引いて据える。 |
| `ToArr(mc)` | `string[]` |  | — |

## EdoDoiBuilder.Mon.cs

══════════════════════════════════════════════════════════════════════

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `3門 表門・通用門・広敷門` | `Stage3MonMenu` | `Stage3_Mon` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `EdgeDir(e)` | `Vector2` |  | — |
| `SLimit(e, c, eo)` | `float[]` |  | 辺 e の線(区画の線から内へ c)の上で、走り s を動かしたとき隣の辺 eo の内に居る s の限り [下限, 上限]。 |
| `SpanOn(go, e)` | `Vector2` |  | 駒の走りの区間 [s の最小, 最大](辺 e の始点から・躯体の帯 0.3〜2.0m の実メッシュ)。 |
| `SpecOrMeasure(path, kind, how)` | `EdoPartSpec.Spec` |  | 札(無ければ実メッシュの断面から測った案 ── 焼かない)。 |
| `PassageOn(sp, t, e)` | `Vector2` |  | 口の走りの区間(辺 e の始点からの s)── 札の passage の両端を世界へ。 |
| `PassageOn(pa, t, e)` | `Vector2` |  | — |
| `HasKuguri(sp)` | `bool` |  | 札の潜戸の口(passageKuguri)が在るか(JsonUtility は欄が無くても空の Span を作る ── 幅で見る)。 |
| `PlinthOpeningEdges(pcs, a0, d, open)` | `Vector2` |  | 基壇の口の縁 = 口(走りの区間)の芯の左で最も奥の駒の端・右で最も手前の駒の端(実メッシュ)。 |
| `DoorBottom(go, a0, d, open)` | `float` |  | 口(走りの区間)の中の実メッシュの最下点 = 扉の下端(敷居)。 |
| `FootFront(sp)` | `float` |  | 足元の外面(札の foot の +Z の最大・局所)── 基壇の天端の前の縁 + 犬走りの線に当てる面。 |
| `Stage3_Mon()` | `string` | 公 | S3 門(案A・EDO-0533)。① 表門(gate)の下の基壇(城の石垣・天端 = 欄の coping・扉口だけ空ける)→ 表門を外面の線・口の芯 s へ・ 土台の底を天端へ → 角の練塀 E13_Hei_Kado… |
| `BuildBackPlinth(ig, kak, mon, tally, sb, log)` | `void` |  | 背の基壇(boundaryPlinth.back・EDO-0533)。 |
| `BuildOkuHei(oku, sb, log, gapOverride)` | `int` |  | 奥の塀(区画の内の段塀・runs[].pts)を建てる。 ⟶ 返す: ⚠ の数 |
| `EndsToFaces(r, pts)` | `string` |  | runs[].ends の「廊下 L_xxx の…側面」を、建っている廊下の実メッシュへ突き付ける(EdoBuild.EndToFace)。 |
| `SpecOf(go)` | `EdoPartSpec.Spec` |  | — |
| `SlitNote(slit, y, band)` | `string` |  | 継ぎ目の素通し(EdoBuild.SeamSlit)の刷り。 |

## EdoDoiBuilder.Mune.cs

══════════════════════════════════════════════════════════════════════

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `5棟 御殿・廊下・附属屋・井戸(案A)` | `Stage5MuneMenu` | `Stage5_Mune` |
| `5棟b 廊下の柱の足を据え直す(4b・9 の後)` | `Stage5bRokaAshiMenu` | `Stage5b_RokaAshi` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `FindDeep(t, name)` | `Transform` |  | — |
| `ServiceFace(s, dirUV, minusX, why)` | `bool` |  | 附属屋の開口の向き(格子の向き)と、開口が部材のどの局所の面か。 |
| `ServicePart(s)` | `string` |  | 附属屋の部材(EdoAssets の名指し)。 |
| `Stage5_Mune()` | `string` | 公 | S5 棟(案A・EDO-0533)。① 御殿7棟を EdoGotenKit.Mune(入側四周1間 = const.moyaBand.irikawa・入母屋 = munes[].roof・床下の足元)で、 面 = 造成後… |
| `PlaceGotenA(line)` | `void` |  | — |
| `PlaceLinksA(line)` | `void` |  | — |
| `Stage5b_RokaAshi()` | `string` | 公 | 廊下の柱の足と御殿の棟の床下の足元を、今の描かれた地表で据え直す(EDO-0533 第9巡・棟の足元は第11巡)。 |
| `PlaceServiceA(line)` | `void` |  | — |
| `PlaceWellsA(line)` | `void` |  | — |

## EdoDoiBuilder.Niwa.cs

土井大隅守上屋敷 — 奥庭(Stage6)。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `検査④ 池が水面の下に納まっているか PondQA` | `PondQAMenu` | `PondQA` |
| `6 奥庭(掘削・護岸・点景・園路・稲荷・植栽)` | `Stage6Menu` | `Stage6_Niwa`, `Niwa_A_Dokou`, `Niwa_B_Gogan`, `Niwa_C_Mizushiri` |
| `6i 池の水面の上に反射プローブを置いて焼く(6h の後)` | `Niwa_I_Menu` | `Niwa_I_Kagami` |
| `6a 池を掘り築山を盛る(⛔ WaterBaker.Recarve は呼ばない)` | `Niwa_A_Menu` | `Niwa_A_Dokou` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Sk(d, k)` | `string` |  | 欄の文字列。無い欄は null(⛔ KeyNotFound で庭の段を丸ごと止めない ── 無い欄は呼び手が Wait へ申し送る)。 |
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
| `ShoreRule()` | `ShoreRuleV` |  | — |
| `TamotoW(widen)` | `List<EdoBuild.NiwaTamoto>` |  | 石橋の袂(世界)── 指図 `hashi[]` の a・b(汀の点)・L・W と exceptAbut の幅の余りから EdoBuild.NiwaTamotoOfBridge で引く。 |
| `TamotoSeatCheck(sr, tamoto)` | `string` |  | 6a の後の袂の座の検め(abutPad ── 硬い)。 |
| `SuhamaWaterLine(run, fromWater)` | `List<Vector2>` |  | 州浜(`suhama[name=run]`)の見えている汀の折れ線(グリッド)と、水の側の帯の幅 fromWater[m]。 |
| `SuhamaZone(line, q, dVisM, fromWater)` | `bool` |  | 点 q(汀の内)が州浜の帯の内か: 最寄りの見えている汀が州浜の区間で、そこから fromWater m 以内。 |
| `BridgeAxesW()` | `List<Vector2[]>` |  | 橋(`hashi[]`)の軸 a→b(世界)。 |
| `RolePointsW(word)` | `List<Vector2>` |  | `migiwa.roles` が語 word を書いた汀の点(世界)。 |
| `NearAny(segs, w, r)` | `bool` |  | — |
| `NearPts(pts, w, r)` | `bool` |  | — |
| `PondEdge()` | `Vector2[]` |  | 水面メッシュの縁(グリッド座標)。 ⚠⚠ `WaterBaker.RebuildSurface` は輪郭に Chaikin ×2(`WaterGeom.SmoothTagged(…, 2)`)を 掛けてから三角形にするの… |
| `InWater(u, v)` | `bool` |  | 水面メッシュの縁の内側か(⛔ `NiwaM.InPond` は設計の汀で、こちらは見える汀)。 |
| `PondQA()` | `string` | 公 | — |
| `Stage6_Niwa()` | `string` | 公 | — |
| `Niwa_I_Kagami()` | `string` | 公 | — |
| `Niwa_A_Dokou()` | `string` | 公 | — |
| `Garden(name)` | `Dictionary<string, object>` |  | 指図の庭を名で引く(`gardens[].name`)。 |
| `UV(o)` | `Vector2` |  | — |
| `WuV(uv)` | `Vector2` |  | — |
| `WDir(uvFrom, uvTo)` | `Vector2` |  | (u,v) の向き d を世界の向きへ(格子は回っている)。 |
| `Rnd(r, a, b)` | `float` |  | — |
| `Pair(o, k, a, b)` | `bool` |  | — |
| `EdgeWalk(frm, to)` | `List<Vector2>` |  | 見えている汀(水面メッシュの縁 = PondEdge)を汀の番号 frm→to へ辿る折れ線(グリッド座標)。 |
| `NakaWalk(frm, to, note)` | `List<Vector2>` |  | 中島の汀(`nakajima.pts`・1 始まり・巡回)を frm→to へ辿り、見えている島の汀(描かれた地表が水面を切る線)へ寄せた折れ線(グリッド)。 |
| `NakaCenter()` | `Vector2` |  | 中島の輪郭の頂点の重心(グリッド)── 島の外向きを決めるのに使う。 |
| `WaterSide(p, dir, naka)` | `Vector2` |  | 折れ線の点 p・接線 dir での水の側の単位法線(グリッド)。 |
| `SkipPts(o)` | `List<Vector3>` |  | `skip` / `skipUV` の抜き所(グリッドの点・半幅 m)。 |
| `InSkip(sk, p)` | `bool` |  | — |
| `Niwa_B_Gogan()` | `string` | 公 | — |
| `NomikuchiSueTsuchi(grp, nomi, st, nm, pUV, tgUV, rnd, tl, wy, bs)` | `string` |  | 呑口の据え土(指図 `nomikuchi.sueTsuchi`)。 |
| `_niwaCellForSue()` | `float` |  | heightmap のセルの一辺[m](地形が無ければ 2.0)。 |
| `Niwa_C_Mizushiri()` | `string` | 公 | — |
| `Niwa_D_Tenkei()` | `string` | 公 | — |
| `EngawaAim(txt, at, what, drop, groundMin, mune, hit)` | `bool` |  | 欄の文「<棟>の縁板の天端 −0.40(測る)・地盤 +0.25 以上」を読み、点 at に最も近い縁板の天端を EdoBuild.EngawaTopNear で測る。 |
| `Kutsunugi(grp, kg, nm, notes)` | `bool` |  | 沓脱石一つ(数の topY・水切りの向き mizukiri.to)。 |
| `ReadAbutSeat(o, nm, why)` | `EdoBuild.NiwaAbutSeatSpec` |  | 指図 `hashi[].abutSeat` を据えの作法へ読む(言い方の照合はここ・据えは EdoBuild.NiwaAbutStone)。 |
| `AbutSeatLine(ar, sp)` | `string` |  | 据えの作法で据えた橋台石の刷り(硬い = 埋め ≤ umeMax・柔らかい = 当たりの面・刷るだけ = 隙と起伏)。 |
| `AboveGroundNote(bestTopAbove)` | `string` |  | 汀の石を建てなかった名指しに添える「天端と地表」の一句(天端が地表の下に沈む候補しか無かったとき)。 |
| `ReadRootStone(r, tag, sukiMax)` | `EdoBuild.NiwaRootSpec` |  | 指図 `abutStone[].rootStone` を根石の作法へ読む(言い方の照合はここ・据えは EdoBuild.NiwaAbutRootStones)。 |
| `AbutAlts(api)` | `List<string>` |  | 橋台石の「石の版を替える」先(指図 abutSeat.tenba)── 名指しの部材が個体の族(Own.Ishigumi(i))なら同じ族の他の個体。 |
| `Niwa_E_Enro()` | `string` |  | — |
| `Niwa_F_Yashiro()` | `string` |  | — |
| `Niwa_G_Kaki()` | `string` |  | — |
| `TerrY(x, z)` | `float` |  | 実地形の高さ(heightmap から。 |
| `PlantSize(sk, api, i)` | `string` |  | 株の大きさ(Big/Mid/Small)── 欄 sizeEach[i] → size → 部材の呼び名の引数("Small" 等)の順に読む。 |
| `Niwa_H_Shokusai()` | `string` | 公 | — |
| `BodyGroups()` | `List<Transform>` |  | 壁体の足元の外形を取る群(建物・廊下・囲い・門・奥の塀・附属屋と基壇・井戸・石段・柵)── 在る物だけ(⛔ Group で作らない)。 |
| `InGardenPoly(uv)` | `bool` |  | 庭の区画(泉水・奥庭の poly)のどれかの内か。 |
| `PlantPath(sk, api, i)` | `string` |  | 植栽の行の i 本目の部材。`sizeEach` があれば丈の呼び名をそれで、`(1/2/3)` の個体は順に回す。 |
| `ShitakusaRegions()` | `List<SkRegion>` |  | — |
| `ClipHalf(P, axisU, sign, at)` | `List<Vector2>` |  | 多角形を半平面(axisU ? u : v)·sign ≥ at·sign で切る(Sutherland–Hodgman)。 |
| `CrownR(sk)` | `float` |  | — |
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
| `ParenFloats(s)` | `List<float>` |  | 括弧の中の数の並び(引用符の中は数えない)。 |
| `ParenInts(s)` | `List<int>` |  | — |
| `ResolveTobi(api)` | `string` |  | 飛石・踏分石の駒(`Own.Tobiishi(n)`)。 |
| `OptAsset(cls, member, args)` | `string` |  | まだ EdoAssets に無いかもしれない部材を名で引く(別の役が新造中の物 ── 石橋・土橋・丸太段・延段・縁先手水鉢・腰掛)。 |

## EdoDoiBuilder.Saku.cs

土井 S6 柵・垣(案A・EDO-0533)── 指図 fences[] を読み、EdoBuild.GakiRun で敷く。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `6柵 柵・垣(案A)` | `Stage6SakuMenu` | `Stage6_Saku` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Stage6_Saku()` | `string` | 公 | — |
| `SakuPart(fc, h, span, post)` | `string` |  | 柵の欄 part/kind → 部材(EdoAssets の名指し)。 |

## EdoDoiBuilder.Shokusai.cs

土井 S8 植栽(案A・EDO-0533)── 林方の設計(指図 planting)を生成器が撒いた点 `doi_impl.json` の planting.points を据える。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `8 植栽(算出物の点を据える)` | `Stage8ShokusaiMenu` | `Stage8_Shokusai` |
| `8b 植栽・庭の木の根元を据え直す(9・4b の後)` | `Stage8bSuenaoshiMenu` | `Stage8b_RootReseat` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Stage8_Shokusai()` | `string` | 公 | — |
| `Stage8b_RootReseat()` | `string` | 公 | 植栽・庭の木・刈込・下草の根元を、今の描かれた地表で据え直す(EDO-0533 第11巡 ── 根元の浮き 19・最大 0.209)。 |

## EdoDoiBuilder.cs

土井大隅守上屋敷(三河刈谷藩2万3千石・譜代・雁間)ビルダー。

| メニュー | 関数 | 呼ぶ関数(Stage) |
|---|---|---|
| `Edo/土井大隅守上屋敷/指図を読み直す` | `Reload` | — |
| `Edo/土井大隅守上屋敷/未据え付けの一覧` | `WaitMenu` | `PendingReport`, `Reload`, `O`, `Has` |
| `Edo/土井大隅守上屋敷/0 ハイトマップを退避` | `Stage0Menu` | `Stage0_Backup`, `Exists` |
| `Edo/土井大隅守上屋敷/1 造成(指図の面へ)` | `Stage1Menu` | `Stage1_Grade`, `Stage0_Backup`, `Window` |
| `Edo/土井大隅守上屋敷/造成を検査 GradeQA` | `GradeQAMenu` | `GradeQA`, `Window`, `LoadBackup` |
| `Edo/土井大隅守上屋敷/裏木戸の材質を練塀へ明示的に結ぶ` | `RemapKidoMenu` | `RemapKido`, `AnANotYet` |
| `Edo/土井大隅守上屋敷/検査① 段の縁の落差と土留め EdgeStepQA` | `EdgeStepQAMenu` | `EdgeStepQA`, `AnANotYet`, `C` |
| `Edo/土井大隅守上屋敷/検査② 門口を石垣が塞いでいないか KomonIshigakiQA` | `KomonIshigakiQAMenu` | `KomonIshigakiQA`, `AnANotYet`, `O`, `F` |
| `Edo/土井大隅守上屋敷/検査③ 石垣が区画外へ出ていないか ParcelOutQA` | `ParcelOutQAMenu` | `ParcelOutQA` |
| `Edo/土井大隅守上屋敷/検査①②③ をまとめて走らせる` | `AllQAMenu` | `EdgeStepQA`, `KomonIshigakiQA`, `ParcelOutQA`, `C` |
| `Edo/土井大隅守上屋敷/2 外周(表長屋・練塀・門)` | `Stage2Menu` | `Stage2_Perimeter` |
| `Edo/土井大隅守上屋敷/3 石垣(外周の基壇・境界の基壇・郭内の土留め・石段の側)` | `Stage3Menu` | `Stage3_Ishigaki`, `AnANotYet`, `Group`, `Clear` |
| `Edo/土井大隅守上屋敷/4 御殿複合(棟・廊下)` | `Stage4Menu` | `Stage4_Goten`, `AnANotYet`, `Clear`, `Group` |
| `Edo/土井大隅守上屋敷/5 郭内(附属屋・井戸・石段・斜路・竹垣)` | `Stage5Menu` | `Stage5_Zosaku`, `AnANotYet`, `Clear`, `PlaceService` |
| `Edo/土井大隅守上屋敷/S1→S6 を通す` | `RunAllMenu` | `RunAll`, `Stage0_Backup`, `Stage1_Grade`, `GradeQA` |

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `O(o)` | `Dictionary<string, object>` |  | — |
| `A(o)` | `List<object>` |  | — |
| `F(o)` | `float` |  | — |
| `S(o)` | `string` |  | — |
| `Has(o, k)` | `bool` |  | — |
| `C(k)` | `float` |  | — |
| `JoinsSay(r, other, word)` | `bool` |  | runs[r].joins のどれかの値が相手の名 other と語 word を共に含むか(欄の取り合いの言い方を読むだけ)。 |
| `EdgePt(edge, s)` | `Vector2` | 公 | 辺 edge の走り s[m] の世界座標。 |
| `EdgeLen(edge)` | `float` | 公 | — |
| `PointInPoly(p)` | `bool` |  | — |
| `OutNormal(e)` | `Vector2` | 公 | 辺 e の外向き法線。⛔ 重心では決めない(凹みのある区画で反転する) — 法線方向へ出た点が区画の外かを内外判定で見る(松平 OutNormal と同じ作法)。 |
| `LoadNat()` | `void` |  | — |
| `NaturalY(x, z)` | `float` | 公 | 造成前の地盤[m]。無い所は NaN(⛔ live terrain で埋めない — 埋めると 「造成しない」区間が他家の造成へ寄る)。 |
| `ImplY(x, z)` | `float` | 公 | 世界座標の造成後の地盤[m](算出物 `graded` の双一次)。 |
| `AnANotYet(what)` | `string` |  | — |
| `InParcelUV(u, v)` | `bool` |  | — |
| `DesignY(u, v)` | `float` | 公 | その (u,v) を覆う段の高さ。無ければ NaN(=造成しない斜面)。 |
| `RunEdges()` | `List<Vector2>` |  | — |
| `WalledEdges(t)` | `List<WSeg>` |  | 段 t の四辺のうち土留めが載っている区間。 |
| `Walled(we, edge, w)` | `bool` |  | — |
| `RampY(u, v)` | `float` |  | 土の斜路の踏面。無ければ NaN。(`sashizu_lib.ramp_y`) |
| `StairY(u, v)` | `float` |  | 石段の掘割(切通し)の踏面。外なら NaN。 |
| `GradedY(u, v, nat)` | `float` | 公 | 造成後の地盤。⭐ 案A(EDO-0533)から算出物 `graded` を引くだけ(旧案の RampY / StairY / 段 / 法面の式は使わない)。 |
| `GroundY(x, z)` | `float` | 公 | 世界座標での施工後の地盤 = 算出物 `graded`(案A・EDO-0533)。 |
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
| `Stage0_Backup()` | `string` | 公 | 全面のハイトマップを .bin へ。無いときだけ書く(走るたび上書きすると造成後が退避に化ける)。 |
| `LoadBackup()` | `float[,]` |  | — |
| `Window(pad, x0, z0, w, h)` | `void` |  | 造成と検査の窓(区画の外接矩形 + pad)。 |
| `Stage1_Grade()` | `string` | 公 | — |
| `GradeQA()` | `string` | 公 | 区画の内の節点で 地形 − 算出物 graded(最大・中央値)/ 区画の外 2m 帯の節点で 退避からの変化の最大。 |
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
| `Edo/松平出羽守上屋敷/7' 植栽(指図の散布点を据える)` | `Stage7bMenu` | `Stage7b_NiwaFromScatter`, `HasKey` |

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
| `Edo/松平出羽守上屋敷/1c 線際の帯を地山へ戻す` | `Stage1cMenu` | `Stage1c_BoundaryNatural`, `Has`, `O`, `F` |
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
| `PlaceAgari(bld)` | `string` |  | 口の外の上がり口(中の口 = munes.Omotegoten.order.中の口.at・広敷の口 = links[].sotoAgari)の沓脱と踏段。 |
| `Pivot(o, kind)` | `Vector2` | 公 | 突き合わせ(EdoSashizuExport.CheckScene)が棟・廊下の据えた点を期待する式 ── ビルダーの据え方と同じ式(検査だけが式を持たない・規則19)。 |
| `NormalizeShapes(d)` | `void` |  | 図から起こし直した指図(2026-10-04・EDO-0554)の新しい欄の形を、矩形で読む古い Stage が落ちないように読み替える。 |
| `MunesExpanded()` | `List<object>` |  | 棟の一覧を、poly の棟は屋根の部分(roof.parts)ごとの矩形の棟へ割って返す(EDO-0554・L 字の表御殿)。 |
| `O(o)` | `Dictionary<string, object>` |  | — |
| `A(o)` | `List<object>` |  | — |
| `F(o)` | `float` |  | — |
| `Has(o, k)` | `bool` |  | — |
| `PolyOrRect(t)` | `Vector2[]` |  | 欄の形(格子座標)を多角形で返す: `poly` があればそれ、無ければ矩形 u0..v1 の4隅。 ⟶ 返す: `poly` があればそれ、無ければ矩形 u0..v1 の4隅 |
| `PolyDistG(pg, g, cp)` | `float` |  | 格子座標の点 g から多角形 pg の縁への最短距離[間]と、その縁の最寄り点。 |
| `EdgePt(edge, s)` | `Vector2` | 公 | 辺 edge の走り s[m] の世界座標。 |
| `G(x, z)` | `float` |  | — |
| `LoadNatural()` | `void` |  | — |
| `LoadEdoWorld()` | `void` |  | — |
| `EdoWorldY(x, z)` | `float` |  | — |
| `NaturalY(x, z)` | `float` | 公 | 造成前の地盤の高さ[m] = 江戸期の復元面。 |
| `DistSeg(p, a, b)` | `float` |  | — |
| `DesignY(p)` | `float` | 公 | 敷地内の一点の施工後の高さ。現況に依存するのは「造成しない」区間だけなので、 何度流しても同じ結果になる(冪等)。 |
| `DesignYRaw(p)` | `float` |  | — |
| `RampYAt(p)` | `float` | 公 | 世界の点 p が坂の路盤(芯から半幅の中・芯の両端の外は含めない)なら芯の高さ(道のりで一次)、外なら NaN。 |
| `GradeRamps()` | `string` |  | 坂の路盤を均した後の法(路肩の外)を今の地形へ擦り付ける(置き方は EdoBuild.GradeSaka)。 |
| `Daylights(cp, g, yT)` | `bool` |  | 段の縁 cp から点 g の向きへ 1:feather の法面を featherCap[m] 延ばしたとき、 現地形に着地するか。 |
| `DistSegG(p, a, b)` | `float` |  | グリッド座標(間)での点と線分の距離。 |
| `Stage0_Backup()` | `string` | 公 | — |
| `Stage1c_BoundaryNatural()` | `string` | 公 | — |
| `Stage1_Grade()` | `string` | 公 | — |
| `Stage1_Grade(clipUV)` | `string` | 公 | 造成を流す範囲を格子(u,v)の矩形 clipUV = {u0,v0,u1,v1} に限る版。 |
| `GradeQA()` | `string` | 公 | — |
| `FenceWidth(parent, psi)` | `float` |  | 穂垣の実寸(走り方向の幅)。プレハブを1枚置いて測り、すぐ捨てる。 |
| `Group(child)` | `Transform` |  | 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 EdoYashikiPrefab.Group。 |
| `Clear(t)` | `void` |  | — |
| `GateSpan(sPos, s0, s1)` | `void` | 公 | 辺 e の外向き法線(区画の外側)。 ⛔ 重心で向きを決めてはいけない。 |
| `OutNormal(e)` | `Vector2` | 公 | — |
| `OutNormalNear(q)` | `Vector2` |  | 点 q に最も近い区画の辺の外向き法線。 |
| `PointInPoly(p)` | `bool` |  | 区画の内側か(交差数法)。OutNormal の向きはこれで決める。 |
| `Measure(path)` | `NagModule` |  | — |
| `Stage2_Perimeter()` | `string` | 公 | — |
| `BuildNagayaOne(r, kak, sb, nag)` | `void` |  | 表長屋 run を1本建てる(Stage2 の本体から切り出し・中身は従来のまま)。 |
| `Stage2Fences()` | `string` |  | Stage2 の木柵(fences)。 |
| `BuildPtsHei(kak, hei)` | `string` |  | 辺に載らない練塀(runs[].pts ── 崖の上の練塀 W_Hei_Gake)を段塀で建てる。 |
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
| `SeatKakoiOnBase(ig)` | `string` |  | 基壇に載る外周の駒(練塀・長屋・隅)を、据えた石垣の天端へ据え直す(EdoBuild.SeatOnBeds・根入れ 0.10)。 |
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
| `PlaceMizo()` | `string` |  | 溝(mizu.nodes の MZ16・MZ17・MZ18 と drains の D_Zentei.amaochi ── 指図の pts と点ごとの inv)。 |
| `PlaceUchiNagaya(sv, grp)` | `string` |  | 内長屋(service[].zone=長屋)を据える。 |
| `TerraceWallsNozura()` | `string` |  | 郭内の土留め(terraceWalls)を野面の乱積みで積む。 |
| `NozuraLines(segs, face, grp, pool, log)` | `List<KeyValuePair<GameObject, Vector2>>` |  | 野面の乱積みを指図の線(世界 xz)へ網で据える(置き方は EdoBuild.PlaceNozuraNet)。 |
| `DaidokoromonGamae()` | `string` |  | 御臺所門の構え(komon[].kaeshi ・kaidans の門の内の石段)。 |
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
| `Edo/岡部筑前守上屋敷/指図を読み直す` | `Reload` | `Clear` |
| `Edo/岡部筑前守上屋敷/0 ハイトマップを退避` | `Stage0Menu` | `Stage0_Backup`, `OnKita`, `Stage0_Backup_`, `Window` |
| `Edo/岡部筑前守上屋敷/1 造成(指図の面へ)` | `Stage1Menu` | `Stage1_Grade`, `OnKita`, `Stage1_Grade_`, `ReviewGate` |
| `Edo/岡部筑前守上屋敷/造成を検査 GradeQA` | `GradeQAMenu` | `GradeQA` |
| `Edo/岡部筑前守上屋敷/2 外周(練塀・基壇・木柵・隅)` | `Stage2Menu` | `Stage2_Perimeter`, `OnKita`, `Stage2_Perimeter_`, `ReviewGate` |
| `Edo/岡部筑前守上屋敷/2b 段の土留め(terraceWalls・天端の垣)` | `Stage2bMenu` | `Stage2b_Dan`, `OnKita`, `Stage2b_Dan_`, `ReviewGate` |
| `Edo/岡部筑前守上屋敷/検: 背の路地を解く(据えない)` | `SeRojiReportMenu` | `SeRojiPlanOf`, `SeRojiReport`, `BackTrenchesFull`, `BackTrenches` |
| `Edo/岡部筑前守上屋敷/3 主郭(棟・廊下・附属屋・井戸・結界・石段)` | `Stage3Menu` | `Stage3_Shukaku`, `Stage3c_SodeSlopeCheck`, `OnKita`, `Stage3c_SodeSlopeCheck_` |
| `Edo/岡部筑前守上屋敷/3b 溝を据え、溝の下の地面を下げる(皮は退役 2026-10-11)` | `Stage3bMenu` | `Stage3d_Mizo`, `PondBankDesign`, `A`, `Get` |
| `Edo/岡部筑前守上屋敷/検: 地面と駒の取り合い(皮なし)` | `GroundQAMenu` | `GroundQA`, `OnKita`, `GroundQA_`, `ImplTol` |
| `Edo/岡部筑前守上屋敷/4 庭(部材を据える・地形には触らない)` | `Stage4Menu` | `Stage4_Niwa`, `OnKita`, `Stage4_Niwa_`, `ReviewGate` |
| `Edo/岡部筑前守上屋敷/5 西の斜面(林・松・帯・汀)` | `Stage5Menu` | `Stage5_Nishi`, `OnKita`, `Stage5_Nishi_`, `ReviewGate` |
| `Edo/岡部筑前守上屋敷/外周の閉じを検査 ClosureQA` | `ClosureQAMenu` | `ClosureQA`, `OnKita`, `ClosureQA_` |
| `Edo/岡部筑前守上屋敷/開口と run の食い違いを検査 OpeningQA` | `OpeningQAMenu` | `OpeningQA`, `OnKita`, `OpeningQA_`, `Openings` |
| `Edo/岡部筑前守上屋敷/区画と指図の座標を突き合わせる` | `ParcelQAMenu` | `ParcelQA`, `A`, `Get` |
| `Edo/岡部筑前守上屋敷/算出物を検める` | `ImplQAMenu` | `ImplQA`, `Reload` |
| `Edo/岡部筑前守上屋敷/S1→S5 を通す` | `RunAllMenu` | `RunAll`, `OnKita`, `RunAll_`, `Reload` |
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
| `OnKita()` | `IDisposable` |  | Stage の間だけ地形を岡部の芯の地形(北の3邸の細かい地形・2026-10-11)へ名指す(EdoBuild.TerrainFocus)。 |
| `EdgeLen(e)` | `float` | 公 | — |
| `EdgePt(e, s)` | `Vector2` | 公 | 辺 e の始点から走り s[m] の世界座標。 |
| `OutNormal(e)` | `Vector2` | 公 | 辺 e の外向き単位法線。符号付き面積から決めるので凹みのある区画でも全辺で一貫する。 |
| `SolveSeatRules(inOff)` | `string` |  | 天端の切れ目を実地形で解く(指図 runs[].seatRule「天端 a の一直線を…通し、内の地盤が天端 +d を超える所…の run の切れ目で b へ上げる。 |
| `SeatBreaks(r, a, b)` | `List<float>` |  | run の区間 [a, b] を天端の段ごとに割る点(両端を含む)── 切れ目(hasStep)の前の一直線は一つ・それ以外の傾いた所は約 2m ごと。 |
| `MichiNarashiAt(m, x, z)` | `float` |  | 帯の均した面の高さ。最も近い格子点が帯の外なら NaN(帯の縁で外へにじませない ── 帯の外の道は触らない【硬】)。 |
| `OutsideBase()` | `Func<float, float, float>` |  | — |
| `GradedBin()` | `WGrid` |  | 0.25m の造成の面(施主裁定 2026-10-11・EDO-0502)── `python3 Tools/Sashizu/impl_okabe.py --graded-bin` が焼く 2 進 (EdoAssets.… |
| `DesignY(p)` | `float` | 公 | 敷地内の一点の造成後の高さ[m]。区画の外は NaN。 |
| `Stale(col)` | `bool` |  | 算出物の欄がいまの指図から焼かれていない(`baked.carried` に名がある = 前の指図のまま据え置き)か。 |
| `RetireStaleGroup(child, col)` | `string` |  | 据え置きの欄から前に建てた群を退ける(SetActive(false)・消さない)。 |
| `ImplTol(key, ifMissing)` | `float` |  | — |
| `Group(child)` | `Transform` |  | 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 EdoYashikiPrefab.Group。 |
| `Clear(t)` | `void` |  | — |
| `Stage0_Backup()` | `string` | 公 | 着工前の地形を .bin へ。無いときだけ書く。 |
| `Stage0_Backup_()` | `string` |  | — |
| `Window(x0, z0, w, h)` | `void` |  | 造成とその検査が使う窓。区画の外接矩形 + 余白。 |
| `Stage1_Grade()` | `string` | 公 | — |
| `Stage1_Grade_()` | `string` |  | — |
| `ProfSNodes(r, f, note)` | `KeyValuePair<Vector2[], float[]>` |  | 坂の縦断 `profS`([s, y] の並び・同じ s に二つの高さ = 石段)と芯 `pts` から、均す芯の節点(世界 xz)と高さを起こす(EDO-0502 第8巡)。 |
| `RampAxis(r, pts, ys, width, note)` | `bool` |  | 指図の坂 r の芯(世界 xz)・芯の高さ・路盤の幅を読む(GradeRamps と造成QA が同じ読みを使う)。 |
| `GradeRamps()` | `string` |  | 折れ線の坂の路盤(案1・EDO-0502)。 |
| `PlaceCurb(nm, line, pts, ys, curbH)` | `string` |  | 坂の路肩の野面石の縁(toeFix)を、路肩の線へ野面の乱積みで据える。 |
| `GradeQA()` | `string` | 公 | 敷地内の全セルで ／地形 − 設計面／ を測る。 |
| `ServicePads()` | `List<PadAx>` |  | 勾配の面(指図 service[].yFrom)の上に据わった附属屋の棟の下の均しの範囲(足あと = EdoBuild.BodyFootWorld・高さ = 据わった躯体の底・ 面 = TerracePolyAt)。 |
| `GradeQA(badAt)` | `string` | 公 | badAt が null でなければ超過の節点(x, z, 地形−設計面)を入れて返す(測りの内訳)。 |
| `GradeQA_(badAt)` | `string` |  | — |
| `Stage2_Perimeter()` | `string` | 公 | — |
| `Stage2_Perimeter_()` | `string` |  | — |
| `HeiRun(kak, a, b, outw, name, seat, endA, endB, wait)` | `void` |  | 岡部の練塀の駒(施主裁定 2026-10-12「案1」・EDO-0502 第118巡)── 一枚物の閉じた断面 EdoBuild.NeribeiPanelRun (旧 EdoBuild.DobeiRun の表裏 2 枚は… |
| `HeiRun(kak, a, b, outw, name, seat, endA, endB, faceIn, wait)` | `void` |  | faceIn: 天端の線・芯線の run(const.heiLine)── 外面を線から faceIn 内へ据える時に実メッシュの壁面で合わせる(⛔ 後で AlignInubashiri で寄せない)。 |
| `JoinEndToGable(kak, r, atStart, sEnd, wait)` | `bool` |  | 辺の端の練塀が隣の辺の長屋の妻へ斜めに当たる端(旧い KiriEnd が長屋の妻で切った端)を、直角の端のまま妻の面へ厚みの全幅で突き込む (JoinEndToNagaya と同じ光線 3×7 ── 最も奥の当たり +… |
| `MiterOf(kutaiPath, r, sSign, warn)` | `string` |  | 区画の角で留めた表長屋の版(EDO-0502 2026-10-03)を引く。 |
| `JoinEndToNagaya(kak, r, atStart, sEnd, wait)` | `bool` |  | 練塀の端を隣の辺の線で斜めに切った駒の据え場所(EDO-0502 2026-10-03・部材の約束は EdoAssets.Own.DobeiKiri)。 |
| `JoinEndToBody(r, atStart, ng, sEnd, wait)` | `bool` |  | — |
| `PrePlaceTomeForKado(kak)` | `string` |  | 留め柱を隅の駒より先に据え、柱で止まる辺の腕の先の範囲を取る(第116巡 ── 第115巡 P2 の腕が辺1 を 0.75 越えて長屋 N41_5 の妻と柱を貫いた)。 |
| `PlaceTomeBashira(kak, r, rs0, rs1, wait)` | `int` |  | — |
| `ButtMissingKado(kak, kadoLo, kadoHi)` | `string` |  | 練塀の隅の駒が焼けていない出隅(算出物 corners の part = Dobei・Kado_&lt;id&gt; が据わらない)を突き付けで仮に納める: 入りの run は出の run の外面の線まで(s = L −… |
| `KiriEnd(r, atStart, sEnd)` | `KeyValuePair<string, Vector3>` |  | — |
| `PlaceOmoteNagaya(kak, wait)` | `string` |  | 外周の表長屋と表門。⭕ 2026-09-04 裁定12=A(二階・棟 7.183 / 表門の棟 8.5)。 |
| `GateInNagaya(kak, r, call, nikai, gS, gW, label, wait)` | `string` |  | 門長屋の口の向きを検めて、要れば引き直す(案1・EDO-0502)。 |
| `RunText(run, key)` | `string` |  | 指図 runs[] の欄 key(無ければ null)。 |
| `NamedCornerPart(v, prefix)` | `string` |  | 頂点 v の隅の駒を指図が名指していれば、その部材の名(拡張子なし・prefix で始まる物)。 |
| `FrontGutterWidth()` | `float` |  | 前の下水溝の駒(石組の溝 型A ── 背の雨落ち・表門脇の下水と同じ型)の実測の全幅[m](外の壁を含む)。 |
| `FrontForGutter(go, r)` | `string` |  | 長屋の前の面を、前の下水溝の分だけ区画の線の内へ(指図 runs[].front「前の面を、区画の線から『前の下水溝+外の壁』だけ内へ寄せる」【硬】・座は変えない【硬】・ 普請方 2026-10-10m・EDO-0502… |
| `PlaceNagayaPiece(kak, name, path, edge, sMid, seat, call, wait, lastH)` | `bool` |  | — |
| `StackCurbOnSkin()` | `string` |  | 坂の路肩の野面石の縁(Stage1 の PlaceCurb・Saka/Curb_*)の段の境の継ぎ目の下を、皮を起こした後の描かれた地表まで 同じ駒で積み下ろす(置き方は EdoBuild.StackDownAtNozu… |
| `SeatMonOnSkin()` | `string` |  | 通用口(Mon の駒)を皮の後の描かれた地表へ据え直す(置き方は EdoBuild.SeatGamaeOn)。 |
| `SeatKakiOnBed()` | `string` |  | 天端の垣 DanKaki を皮の後の据わる床(描かれた地表と土留め Ishigaki・Dan の上向きの面の高い方)で据え直す (置き方は EdoBuild.ReseatCrestFence)。 |
| `SeatHeiOnBed(kak)` | `string` |  | 練塀(表裏の f/b を一組)・隅 Kado_*・端を切った Kiri_* を、床 = 描かれた地表と基壇 IG_* の天端の高い方 (EdoBuild.Bed)へ組ごと据える(EdoBuild.SinkGroupToB… |
| `SeatHeiOnBed(kak, withMizo)` | `string` |  | withMizo: 床に溝・桝の駒の上面も数える(第119巡 ── 地面を焼き切った後に据える 3d では、腰の内の縁が溝の縁石の上に掛かる)。 |
| `HeiLinePieceKey(r, c)` | `string` |  | 天端の線(const.heiLine)の区間ごとに床へ組ごと据える鍵 ── 同じ区間の駒は一つの組で動く(⛔ 駒ごとに床へ据えると区間の中に天端の段が出る【硬 ≤0.01】)。 |
| `HeiLineKadoKey(nm)` | `string` |  | 隅の駒 Kado_P{v} の天端の線の鍵 ── 頂点が区間の中(頂点で段を切らない)ならその区間、頂点が段の点なら低い側の区間(隅の底は腕に続く直線の低い方 ── SeatKadoToRuns と同じ決め・座で止める)… |
| `KidanC(e, s)` | `float` |  | 辺 e・走り s の run の法肩の控え c(基壇の無い run は辺の最大・基壇の無い辺は 0 ── 法肩が無く外面は線から犬走り)。 |
| `FaceIn(e, s)` | `float` |  | 囲い(練塀・長屋・門)の外面の、区画の線から内への離れ = 法肩の控え c + 犬走り(const.kidan.faces「+c+inubashiri」)。 |
| `ClearHeiLine()` | `void` |  | — |
| `HeiLineRangesFromSashizu()` | `List<Vector2Int>` |  | const.heiLine.trial の辺の範囲を読む(「辺1〜11・19〜24・28〜38」)。 |
| `HeiLineEdgeSet()` | `HashSet<int>` |  | 天端の線を当てる辺(指図から毎回読む ── domain reload で Runs の線が消えた後の 3d でも、天端の線の駒を床へ動かさない・後合わせの規則を通さない)。 |
| `HeiLineFace()` | `string` |  | 外周の練塀の芯線を一続きに決める(指図 const.heiLine・施主裁定 2026-10-12 案A/案1)── 欄を EdoBuild へ渡すだけ(規則21): 範囲 = heiLine.trial の「辺 a〜b… |
| `ReadTenba(knots, steps, maxGrade, notes)` | `bool` |  | 天端の線の決めた座と段を指図から読む(const.heiLine.tenba の SW・SE・N の文 ── 普請方の設計を普請奉行が採った値・施主裁定 2026-10-12 案1)。 |
| `HeiLineTenba()` | `string` |  | 天端の線を指図の値で一本に決める(const.heiLine.tenba・施主裁定 2026-10-12 案1)── 範囲ごとに EdoBuild.HeiTenbaProfile へ芯線の控え d・決めた座・段を渡し、… |
| `HeiLineBand()` | `string` |  | 塀の内の帯を坂なりの線に揃える(const.heiLine.tenba.band「塀の内の帯を均して地盤を坂なりの線に揃える・区画の外は触らない【硬】」・設計の全文 method 「帯=塀の内面から b を座−δ、先は盛… |
| `HeiLineBaseFromTenba()` | `string` |  | 天端の線の run の台の石垣の区間と倍率を、天端の線の座から解く(runs[].sFrom「天端 − 法尻の地形(棟梁が実地形から導く)」・const.baseMin / baseUnit・第121巡)。 |
| `ProfileOfEdge(e)` | `EdoBuild.HeiProfile` |  | 辺 e を含む天端の線(無ければ null)。 |
| `OnHeiLine(r)` | `bool` |  | run が天端の線・芯線の上か(新しい決め方の経路 ── 後合わせの規則 AlignInubashiri・KeepInsidePoly・SeatKadoToRuns・2m 割り・床へ据える を通らない)。 |
| `SeatHeiLineKado(kak)` | `string` |  | 芯線の頂点の隅を天端の線へ据える(const.heiLine.tenba・第121巡)── 隅の実メッシュの足(腰の底)を両腕の先で測り(腕の先 = 練塀の駒が突き付く所)、 その所の線の座(EdoBuild.HeiPr… |
| `OnHeiLineVertex(v)` | `bool` |  | 頂点 v の両脇の辺が芯線(const.heiLine)の上か(隅の駒を据える時に一続きの控え d で面を合わせる ── FitKado・SeatKadoToRuns を通らない)。 |
| `RunInu(e, s)` | `float` |  | 辺 e・走り s の run の犬走り ── 既定は const.inubashiri。 |
| `PlaceIshigaki()` | `string` |  | 外周の基壇(城の石垣・const.kidan 甲の型 ── 普請方の設計 2026-10-11 を普請奉行が採った)。 |
| `PlaceKomon()` | `string` |  | — |
| `FaceOut(go, e)` | `float` |  | 据えた現物の外面(辺 e の区画線から外向きへの最大の張り出し[m])。 |
| `PlaceFences()` | `string` |  | 木柵(辺5=溜池の堤)。基礎も整地も石垣も持たない地形なりなので天端を持たない。 |
| `MeasureRunWidth(path, parent, psi)` | `float` |  | 部材を1枚置いて走り方向の実寸を測り、すぐ捨てる。 |
| `MeasureHeight(path, parent)` | `float` |  | — |
| `FitKado(kak, lo, hi)` | `string` |  | 据えた隅の両腕の外面を犬走りへ寄せ、腕の実端面を測る。 |
| `SeatKadoToRuns(kak)` | `string` |  | 練塀の隅の駒の高さを、両腕に突き付けた直線の駒の底の低い方へ(第119巡)。 |
| `SeatKadoToRuns(kak, lowerOnly)` | `string` |  | lowerOnly: 下げるだけ(床へ据えた後 ── 上げると浮く・3d の地面の後・第119巡)。 |
| `PlaceKado(parent)` | `string` |  | 隅部材を据える。折れ角は区画が決めるもので毎回違うので決め打ちしない。 |
| `AlignInubashiri()` | `string` | 公 | 石垣の法肩から犬走りを残して囲いを据え直す。 |
| `YawU()` | `float` | 公 | ローカル +X を +u へ向ける yaw。 |
| `YawV()` | `float` | 公 | ローカル +X を +v へ向ける yaw。 |
| `AlongU(du, dv)` | `bool` | 公 | 棟・廊下の据え付けピボット(グリッド座標)。 |
| `PivotUV(u0, v0, u1, v1)` | `Vector2` | 公 | — |
| `Pivot(o, kind)` | `Vector2` | 公 | 突き合わせが読む据え付け点(世界座標)。 |
| `Stage2b_Dan()` | `string` | 公 | — |
| `Stage2b_Dan_()` | `string` |  | — |
| `KeepToe(keepB, wallB, q, nw)` | `bool` |  | 法尻の土留めの背の小段(指図 terraceWalls[].toeBench を持つ欄 ── TW_Nishi_Kado・TW_Higashi_Minami・EDO-0502 第33巡)を、 据えた駒(Dan の「名_p… |
| `ToeBenches(note)` | `List<EdoBuild.ToeBench>` |  | — |
| `BackTrenches(sb)` | `List<BackTrench>` |  | 返しの石垣と溝を解く(Stage2b の据えと Stage3b の皮の設計の地盤が同じ答えを読む)。 |
| `SeRoji()` | `SeRojiPlan` |  | この巡の解き(Stage2b が解いた物・domain reload の後は解き直す)。 |
| `SeRojiWallName()` | `string` |  | 背の路地の奥の石垣の名(指図 seRoji.w「その先が TW_* の見え面の足元」)。 |
| `SeRojiPlanOf()` | `SeRojiPlan` | 公 | 背の路地と TW_Higashi_Se を解く(指図 grading.seRoji・terraceWalls[TW_Higashi_Se]【硬】)。 |
| `MinamiWallOf(w, why)` | `Dictionary<string, object>` |  | 南の練塀の内の高い石垣 TW_Higashi_Minami の線を解き、検算する(施主裁定 2026-10-12 案A・指図 terraceWalls[TW_Higashi_Minami].line / lineChec… |
| `SeRojiSouthExtend(P)` | `string` |  | 背の路地の南の延長(指図 grading.seRoji.south「南の端は塞がず、路地の床のまま南の練塀(S_Hei_01 系)の内の足元まで通す【硬】・床 12.15〜12.25・北へ 1/100【柔】」 ・施主裁定… |
| `SeRojiHeiFoot(write=…)` | `string` |  | 練塀の内の足元の帯(指図 grading.seRoji.heiFootSpec【硬】・第115巡 ── 第114巡の文の読み(heiFoot の正規表現)から構造の欄へ替えた)。 |
| `DrainByName(nm)` | `Dictionary<string, object>` |  | drains[D_MinamiHei] を引く(無ければ null)。 |
| `SeRojiNiwaFill(spl)` | `string` |  | 角の庭の窪みを盛る(指図 drains[D_MinamiHei].niwa「角の庭は全面 a 以上【硬】・どの点からも庭の溝へ下り窪み無し【硬】・高い順に 足元の帯 ≥ 庭 ≥ 溝の天端」・第115巡)。 |
| `NiwaFilledKeys(yMin)` | `HashSet<long>` |  | 角の庭として盛った節点(Stage2b の SeRojiNiwaFill)── Stage3d の駒の下の下げの下限。 |
| `NodeKey(x, z)` | `long` |  | — |
| `SeRojiSouthKadoReport(spl)` | `string` |  | TW_Higashi_Se の南の端の隅の駒(terraceWalls[].southKado・seRoji.southKado)の据わりを刷る: 天端・根入れ(床 − 底)・丈・見え面から 1.0 以内の床 −0.02… |
| `ClipIn()` | `float` |  | 床・帯の多角形を区画の線から内へ切る幅(指図 grading.seRoji.clipOrder「区画の線から半升(0.125)内で切る」)。 |
| `SeRojiPlan_Prof(f, s)` | `float` |  | — |
| `SeRojiProfTxt(f)` | `string` |  | — |
| `SeRojiReport()` | `string` | 公 | — |
| `BackTrenchesFull()` | `List<BackTrench>` |  | 背の台の石垣を棟の背の全長に通す欄(backOf&lt;棟&gt; 追記 2026-10-10o)の溝。 |
| `BackOfFullLine(list, nozSegs)` | `string` |  | 背の台の石垣を棟の背の全長に通す(指図 terraceWalls[].backOf&lt;棟&gt; 追記 2026-10-10o【硬】・EDO-0502 第98巡)。 |
| `TrenchAt(ts, q)` | `float` |  | 点 q が溝(背の面から off の帯・止めの妻から返しの端 + off まで)の中なら溝の高さ、外なら NaN。 |
| `RoadGround(q)` | `float` |  | 野面の段の土留めの石段の口(EDO-0502 第57巡・施主裁定 2026-10-08「野面に揃える」)。 ⟶ 返す: 口の道のり [s0, s1] の並び |
| `StairGaps(key, w, nodes, top, kaiRoot, nozSegs, sb)` | `List<Vector2>` |  | — |
| `EndExtensions(nm, w, nodes, top, key, sb, partners)` | `List<EndExt>` |  | 段の土留めの両端の延長の線(指図 terraceWalls[].ends・EDO-0502 第20巡・第57巡に城の石垣の枝から切り出し ── 野面の枝も同じ線を読む)。 |
| `EndDecisions(nm, w, nodes, tops, sb, rets)` | `void` |  | 段の土留めの両端の決め(指図 terraceWalls[].ends・EDO-0502 第20巡 TW_Minami_Koshi)。 |
| `PlaceDanKaki(fgrp, walls, wallOf, lineOf, topOf, gapOf)` | `string` |  | 天端の垣を、指図 terraceWalls[].fenceOnTop の型で据える(置き方は EdoBuild.PlaceCrestFence)。 |
| `Stage3c_SodeSlopeCheck()` | `string` | 公 | 袖の坂の硬い検めを皮の後に測り直す(指図 sodeSlope「天端と背の地盤の差 ≤ x」【硬】・EDO-0502 第45巡)。 |
| `Stage3c_SodeSlopeCheck_()` | `string` |  | — |
| `Stage3_Shukaku()` | `string` | 公 | — |
| `Stage3_Shukaku_()` | `string` |  | — |
| `PondBankDesign(gh, ok, dx0, dz0, dstep, dnx, dnz, sb)` | `List<Vector2[]>` |  | 池の岸の断面(指図 hosoku.zosei「gardens[NiwaShoin].hori」.danmen・EDO-0502 第61巡)を格子 gh(dx0/dz0/dstep・dnx×dnz)へ書く。 |
| `PondBankToTerrain()` | `string` |  | 池の岸の断面を細かい地形へ(2026-10-11・皮の代わり)。 |
| `PlaceKomonFront()` | `string` |  | 小門の前の地面と踏み石(指図 komon[].front ── 施主 2026-10-12「門の前の地面は道の面のまま・土を盛って段を作らない【硬】。 |
| `Stage3d_Mizo()` | `string` | 公 | 3d 溝(施主裁定 2026-10-11・EDO-0502: 皮をやめ 0.25m の細かい地形へ移った)── Stage3b の皮を外し、皮の前に据えていた溝・桝を据え、 溝・桝の駒の下の地面を駒の底より下げる(Edo… |
| `Stage3d_Mizo_()` | `string` |  | — |
| `GroundQA()` | `string` | 公 | — |
| `GroundQA_()` | `string` |  | — |
| `Stage3b_Hifu()` | `string` | 公 | — |
| `Stage3b_Hifu_()` | `string` |  | — |
| `NozuraCrestCoverOf(sb, buried=…)` | `EdoBuild.NozuraCrestCover` |  | 野面の石垣の天端の裏石の帯を土で覆う型(EdoBuild.NozuraCrestCover)を、段の土留め(Dan)の野面の駒から起こす (指図 const.nozuraCrestCover・普請方の設計 2026-10… |
| `SteepEdgeReport(root)` | `string` |  | 算出物 graded の写しに、坂の路盤(ramps[] の芯・幅・縦断)の帯の中だけ今の地形(GradeRamps の均し)を写す(EDO-0502 第8巡)。 |
| `FlatReport(root, buried)` | `string` |  | 面の平らの検め(指図 terraces[].flat「面は y、外れ ±e【硬】」・普請方 2026-10-09f・第73巡)。 |
| `FlatFacesOf(buried, sb)` | `List<EdoBuild.FlatFace>` |  | 指図 terraces[].flat を皮の平らな面(EdoBuild.FlatFace)へ ── 面は y・外れ ±e【硬】・例外は欄の文(小口を被せる土 = 埋める駒から 0.8 以内・ Higashi_Fall へ… |
| `FaceFootHulls(poly)` | `List<Vector2[]>` |  | 面の縁の帯を受ける部材 = 野面の石垣の駒(Dan)と石段の段石(名 K_)の外形 ── 面の輪郭から 8m 以内の物(第75巡・指図 flat 追記 2026-10-09g「石垣・石段の見え面の足元」)。 |
| `S2F(faceName)` | `float` |  | 面の名 → 高さ(terraces[].y)。 |
| `RoadAtS(r, sAl)` | `float` |  | 道の高さ(線の外 0.5)── 皮が区画の外を描くのと同じ測り(EdoBuild.OutsideOwnGround: 区画の内の地形の節点は造成前の地盤へ)。 |
| `RoadEdgeHost(tx)` | `string` |  | 腰石垣の棟 = roadEdge の文が「&lt;棟&gt; の前」と最初に名指す run(指図の名・⛔ C# に名を書かない)。 |
| `RoadEdgePlanOf()` | `RoadEdgePlan` |  | — |
| `TrimRoadSpans(r)` | `string` |  | 腰石垣の区間の端を、駒の底の全幅の下に地盤が在る所まで縮める(roadEdge 追記 2026-10-10g【硬】・第90巡)── 計画(RoadEdgePlanOf)の中で一度だけ。 |
| `RoadEdgeSegs(nozSegs)` | `string` |  | 腰石垣の区間を野面の区間へ(Stage2b の据えの前に)。 |
| `TsumaWall(r, nozSegs, seg, e2, sb)` | `string` |  | 台の妻の面の石垣(指図 terraces[].roadEdge 追記 2026-10-10k・EDO-0502 第94巡)── 道の側の腰石垣の妻の線の端を隅の駒で出隅にし、妻の線に沿って背へ折る。 |
| `RoadEdgeEndReport(root)` | `string` |  | 腰石垣の妻の線の端の前の落差(指図 roadEdge 追記 2026-10-10j「出会わなければ見切り石で止め、端の前の落差は x 以下【硬】」)── 皮の後に、 端の駒(見切り石)の実メッシュの最も先の s から 0… |
| `PlaceGateSteps(wait)` | `string` |  | 門の口の踏み段(roadEdge【硬】一段目の段鼻は区画の線を越えない・蹴上 = 落差 ÷ 段数・段数 = 落差 ÷ 屋敷の中の石段の既定の蹴上 0.30 の切り上げ・踏面は欄を狙う【柔】)。 |
| `OmoteGesuiPlan()` | `GesuiPlan` |  | — |
| `SumpGesuiPlan(g, og, hT, sSump)` | `GesuiPlan` |  | 集水枡の下水の線(指図 terraces[].omoteGesui「&lt;棟&gt; の背の s=n の集水枡」・普請方 2026-10-10p・EDO-0502 第102巡)。 |
| `PlaceOmoteGesui()` | `string` |  | 表門脇の下水を据える(指図 omoteGesui【硬】出口は入口より低く区画の外へ落とす・塀をくぐる所だけ暗渠)。 |
| `PlaceOmoteGesuiLay(headBottom)` | `string` |  | — |
| `MizoAByDepth(need, topAbove)` | `string` |  | DoiMizo 型 A のうち実測の深さ ≤ need + topAbove の最も深い駒(第80巡: 名の深さで選ぶと縁 0.02 の分だけ天端が浮いて落ちた)。 |
| `FaceYAt(faces, q, skipPrefix)` | `float` |  | 点 q を含む面のうち面積の最も小さい物の高さ(皮と同じ選び方)。 |
| `PlaceFrontGutters()` | `string` |  | 長屋の前の下水溝(指図 terraces[].roadEdge 追記 2026-10-10m・runs[].front・drains D_&lt;棟&gt;_Mae・普請方・EDO-0502 第95巡)。 |
| `PlaceMizoSections()` | `string` |  | 台の前の溝の区間(指図 grading.omoteNagayaDai.mizo ── sections Mizo_Kita / Mizo_Minami / Mizo_Hashi・outlets・outerTop/topL… |
| `LidEdge(q)` | `int` |  | 点に最も近い区画の辺(蓋石を線の内へ寄せる向き)。 |
| `FootLinesOn(edges)` | `Dictionary<int, EdoBuild.FootLine>` |  | 辺ごとの練塀の内面の線(実メッシュ ── 練塀・隅の駒・留め柱の頂点を一番近い辺へ)。 |
| `RXm(t, pat)` | `System.Text.RegularExpressions.Match` |  | 二本の線(点 + 向き)の交点。平行なら NaN。 |
| `LineX(a0, d0, a1, d1)` | `Vector2` |  | — |
| `PlaceMinamiHei()` | `string` |  | 南の練塀の内の溝 D_MinamiHei(指図 drains[D_MinamiHei] の segs・第115巡 ── 普請方の設計 2026-10-12)。 |
| `PlaceSeRojiAnkyo()` | `string` |  | 背の路地の暗渠(指図 drains[D_SeRoji].make ── flow・masu・kuchi・toi・at・table・order・EDO-0502 第109巡)。 |
| `PlaceDrainFrontGutters()` | `string` |  | 長屋の前の下水溝(drains の route で名指す型)(指図 drains[].route「&lt;棟&gt;/&lt;棟&gt; の前の全長(s a→b)に区画の内の石組の下水溝(型A)」・普請方 2026-10… |
| `PlaceFrontAnkyo(run, T, tailBottom, sTail, tailPiece)` | `string` |  | 前の下水溝の尻の暗渠(指図 drains D_&lt;棟&gt;_Mae の route ── 普請方 2026-10-10n・EDO-0502 第96巡)。 |
| `PlaceBackGutters()` | `string` |  | — |
| `RestorePerimeterSpill(band)` | `string` | 公 | 袖の坂(指図 terraceWalls[].sodeSlope・普請方の設計 2026-10-07・EDO-0502 第41〜42巡)── 袖の天端を段にせず、背の法 + off の坂の一続きの線にする (上端 cap… |
| `RestorePerimeterSpill_(band)` | `string` |  | — |
| `RestorePerimeterSpill_(band, lowerOnly)` | `string` |  | <param name="lowerOnly">盛りの波及だけを戻す(基準 = base_dem と道の線際の均し michiNarashi の低い方より 0.3 を超えて高い節点を基準へ)── 造成の後に呼ぶとき(se… |
| `TrimRunsToPartners(segs)` | `string` |  | 指図 ends 追記 2026-10-10f【硬】(第89巡): 「突き付け」を名指す run の端が、別の run の区間の線を越えていれば交点まで縮める(EdoBuild.TrimSegToPartnerLine)─… |
| `CutEndsMikiri(segs)` | `string` |  | 指図 cuts 追記 2026-10-10f【硬】(第89巡): 「〜が切る口の両端は見切り石で納め、隅の駒を口に置かない」── その欄の run の区間の端のうち、名指しの石段の駒から 1.5m 以内の端に見切り石を名… |
| `TrimRunsBelowFront(segs)` | `string` |  | 指図 sideEnd・sodeSlope 追記 2026-10-10d【硬】の打ち切り(第87巡)── 欄が「flat の帯の中に駒を置かない」を持つ run(sodeSlope = 欄の名・sideEnd = 欄の名… |
| `MikiriSoil(which)` | `float` |  | 指図 roadEdge・cuts 追記 2026-10-10h の見切り石の背の土 ── 0: 頭より下げる量・1: 平らの幅(一間 = ken)・2: 先の法 1:n。 |
| `ToeBand(sb, which)` | `float` |  | 指図 const.fillEdgeSlope「盛りの縁は 1:n より急にしない【硬】」の n(読めなければ NaN と ★)。 |
| `ToeBandBack(sb, which)` | `float` |  | 指図 const.toeBand 追記 2026-10-10p(普請方・第98巡の差し戻し)の背の押さえ ── 0: 法尻の線から背への近い帯(法尻 + 上限)・1: 遠い帯の端・2: 天端からの下げ。 |
| `FillEdgeSlope(sb)` | `float` |  | — |
| `SideEndSlopeHits(ks)` | `string` |  | 延長の背の法の行き先の検め(指図 TW_Kado_Shumen.sideEnd 追記 2026-10-10b【硬】・第81巡)。 |
| `SodeSlopeSegs(key, nodes, txt, nozSegs, chk, landOut=…, coverOut=…, skipOwnLanding=…, sinkEndOverride=…, endGrades=…, endReach=…)` | `string` |  | — |
| `StairSideAndEndBacks(res, note, depth, rx)` | `void` |  | 石段の脇の返しの背(指図 kaidans[].sideBack)と、段の土留めの両端の延長の背(指図 terraceWalls[].endsBack)の小段 (EDO-0502 第60巡・普請方の設計 5d33ffe5… |
| `SodeBenches(note)` | `Dictionary<string, List<KeyValuePair<int, EdoBuild.BackBench>>>` |  | — |
| `RampPatchedDesign(G, sb)` | `float[]` |  | — |
| `AllFacesAt(faces, q, y, tol, skipPrefix)` | `bool` |  | 皮が高さを揃える平らな面(指図 terraces の poly を世界へ)。 |
| `FlatFaces(sb)` | `List<EdoBuild.SkinFace>` |  | — |
| `PadRimAt(q)` | `EdoBuild.PadRim` |  | 点 q を含む面(指図 terraces の poly を世界へ・勾配の面も含む)のうち最も小さい物。 |
| `TerracePolyAt(q)` | `Vector2[]` |  | — |
| `SkinGround(x, z)` | `float` |  | 皮が描く地表(Stage3b の縁の皮が描く高さ)を、皮を起こす前に引く: 平らな面の中は面の高さ、外は設計の地盤 graded と 地形の低い方(区画の外・graded の無い所は地形)。 |
| `RampDrawnByProfile(r)` | `bool` |  | 石段を名指す坂(kaidans[].atRoute)の路盤の帯(芯から幅/2)の中の、縦断の高さ(RampAxis の節点を道のりで一次 ── GradeRamps と皮の設計と同じ)。 |
| `RampProfileAt(q)` | `float` |  | — |
| `PlaceMunes(wait)` | `string` |  | 御殿の棟。部材キットで一間の柱割りから組む(Village Kit の一軒家プレハブでは 入側から壁が見えて御殿にならない — 2026-08-14 ユーザー裁定)。 |
| `KirikakiCheck(go, m, rf, wait)` | `string` |  | 車寄の切り欠き(2026-09-04 裁定10=A)。 |
| `PlaceLinks(wait)` | `string` |  | 渡廊下は幅一間(指図 `_links`)で部材キットが組む。 |
| `AssetByKey(key)` | `string` |  | 指図が名指しした部材のキーを `EdoAssets` の実体へ解く。 |
| `AssetByKey(key, wKen, dKen)` | `string` |  | 指図の `asset` を `EdoAssets` の実体へ解く。 |
| `YawTo(du, dv)` | `float` | 公 | ローカル +X をグリッドの向き (du, dv) へ向ける yaw[°]。 |
| `PlaceBox(grp, nm, path, c, y, wKen, dKen, yaw, wait)` | `bool` |  | 箱状の附属屋を一つ据える(足跡の中心・地盤レベル)。 |
| `OrientOf(key, du, dv, xu, xv, note)` | `void` |  | 部材ごとの向きの規約。⛔ 「長いほうへ +X」で一律に決めない — 部材の doc が正典。 |
| `FrontLocalYaw(key)` | `float` |  | 部材の開口の面がローカルのどの軸か(+Z を 0° として時計回りの yaw[°])。 |
| `PlaceService(wait)` | `string` |  | — |
| `PlaceWells(wait)` | `string` |  | — |
| `PlaceKekkai(wait)` | `string` |  | 表向と奥向を屋外でも分ける結界の塀。練塀ではなく「のし塀+瓦」 (屋敷の内部の仕切りなので外構より軽くする — 指図 `_kekkai`)。 |
| `PlaceTakegaki(wait)` | `string` |  | 法肩の竹垣(四つ目垣)。⚠ 2026-09-04 まで据える処理が無かった上、 最初に通したときは在庫の `Eg.TakeGaki`(竹の菱格子=網代風で四つ目垣ではない)を 非一様スケールで伸ばしていた。 |
| `PlaceKaidans(wait)` | `string` |  | 石段。⚠ 足元と天端の標高は指図が持つ(`y0`/`y1`)。 |
| `SodeFirstWall(nm)` | `string` |  | 石段の袖(指図 kaidans[].sode・普請方の設計 2026-10-07・EDO-0502)── 土留めを切って張り出す石段の両脇を袖石垣で受ける。 |
| `SodesBeforeNet(danGrp, segs, pool)` | `string` |  | 石段の袖を本線より先に据え、口の両端の本線をその外の面へ突き付けて止める(指図 TW_Kado_Hokuto.cuts 追記 2026-10-10o【硬】・EDO-0502 第99巡)。 |
| `PlaceKaidanSodes(danGrp, planSegs=…, placed=…)` | `string` |  | — |
| `RouteExists(nm)` | `bool` |  | — |
| `KaidanAB(k, a, b)` | `bool` |  | 石段の平面の両端(世界 xz)。坂の上の石段(`atRoute`・`atS`[m]・`planeLen`[m])は坂の芯の道のり atS ± planeLen/2 から解く (EDO-0502 第31巡 ── 欄の a・… |
| `ExtendKaidanEndsToWalls(walls)` | `string` |  | 案1の石段の書式 `{a, b, yBot, yTop, steps, flights?, landingKen?, fumi, wKen, planeLen}`(EDO-0502)。 |
| `MeasureSideFaces(walls)` | `string` |  | sideFace の実測(指図 kaidans[].sideFace・EDO-0502 第57巡)── 各段の列の芯から踏面の天端 +0.05 の高さで左右へ光線を打ち、 脇の土留めの見え面までの距離 − 段の半幅(=… |
| `TopLandingFaces(sb)` | `List<EdoBuild.SkinFace>` |  | 上がり口の段石の背の平らな面(指図 kaidans[].topStep「背の地盤は天端 − x」・topStepBackFlat の奥行【硬】・EDO-0502 第58巡)。 |
| `PlaceKaidanAB(grp, k, wait)` | `int` |  | — |
| `PlaceSando(wait)` | `string` |  | 参道(表門の軸を通る白洲)。⭕ 屋根を架けない(2026-08-19 ユーザー裁定 — 前庭は開けた白洲で、屋根は式台・車寄せまで)。 |
| `Stage4_Niwa()` | `string` | 公 | — |
| `Stage4_Niwa_()` | `string` |  | — |
| `AnkyoReport()` | `string` |  | 水抜きの溝が道を通る区間(暗渠)を測る(案1・EDO-0502・指図 gardens[].mizu.outflow.crossings)。 |
| `PlaceWaterSurface(items, wait)` | `string` |  | 池の水面だけを張る(2026-09-04 普請奉行の裁定)。 |
| `PaintSplat(items, wait)` | `string` |  | 地表を塗る(2026-09-04 指図方が `layer` を宣言した分)。 |
| `PlaceNiwaItem(sub, g, kind, key, pts, missing, wait)` | `int` |  | 庭の一節を据える。部材ごとに据え方が違うので種別で分ける。 |
| `SeatNiwaStone(sub, nm, idv, c, h, bury, sink, waterY, yaw, drawn, wait)` | `int` |  | 庭石を一つ据える(景石・岩島・肩石)。⭐ 高さは地面と触れる箇所で決める(EdoBuild.SeatOnGround)── ⛔ ピボットを地盤の値へ置かない。 |
| `IshigumiW(i)` | `float` |  | 庭石の個体 i の、丈 1.000 のときの平面の幅 W(X)[m](部材の doc の実測値)。 |
| `PolyAt(pts, t)` | `Vector2` |  | 折れ線 `pts`(世界座標)の走り比 t(0〜1)の点。 |
| `SeatByBury(go, g, groundY)` | `void` |  | 石を「丈の `buryRatio` だけ埋めて」据える。 |
| `PlantByKey(key)` | `string` |  | 植栽の部材のキーを解く。キーは指図(算出物)が持ち、ここは辞書を引くだけ。 |
| `PlantByKey(key, seedName)` | `string` |  | ⭐ 中身は共通の一本 EdoBuild.PlantPathByKey(EDO-0533 で移した・土井 Stage8 と共有)。 |
| `ObbWD(go, wLocal, dLocal)` | `void` |  | 据えた現物のローカル軸での幅(+X)と奥行(+Z)[m]。 |
| `TrunkDiameter(host, y0, y1)` | `float` |  | 据えた木の幹径[m]。根元の少し上(`y0`〜`y1` m)の帯で、幹の芯からの 半径の 90 分位を取って 2 倍する。 |
| `StableHash(s2)` | `int` |  | 名前から決まる安定した非負の整数。⛔ 乱数ではない — 何度流しても同じ物が出る。 |
| `NaturalHeight(path, parent)` | `float` |  | 部材の素の丈[m]。⭐ 中身は共通の一本 EdoBuild.PlantNaturalHeight(EDO-0533 で移した)。 |
| `Stage5_Nishi()` | `string` | 公 | — |
| `Stage5_Nishi_()` | `string` |  | — |
| `PlantFromImpl(wait)` | `string` |  | 生成器が撒いた散布点を据えるだけ。 期待する欄は impl.planting[](素の配列。 |
| `PlaceTesuri(wait)` | `string` |  | 勝手の道が法肩の竹垣の外(池側)を通る区間の落下止め (2026-09-03 ユーザー裁定1=A)。 |
| `PlaceKuiretsu(wait)` | `string` |  | 汀線に沿う松の丸太杭。⭐ 本数は汀線の実長から算出する(⛔ 辺5の長さを流用しない — 2026-09-03 庭方4巡目)。 |
| `ReportNishiRest(wait)` | `string` |  | 西の斜面のうち、据える物が無いか部材待ちのものを一覧に出す。 |
| `UnionLen(ivs, lo, hi)` | `float` |  | — |
| `HostsOpening(run, edge, a, b)` | `bool` |  | run が開口の門長屋か(案1・EDO-0502)。 |
| `HostedGate(run, s, w, label)` | `bool` |  | 門長屋の口(辺 e の走り s・幅 w)。 |
| `Openings()` | `List<float[]>` |  | 指図の開口(表門・通用口)。辺と s の区間で返す。 |
| `ClosureQA()` | `string` | 公 | 外周が全周で閉じているかを辺ごとに数字で出す。 |
| `ClosureQA_()` | `string` |  | — |
| `OpeningQA()` | `string` | 公 | 開口の上に囲いが載っていないか。指図は run の `s` で既に開口を避けてあるので、 ここが 0 でなければ指図か区画のどちらかが動いた合図(実装は開口を切り直さない)。 |
| `OpeningQA_()` | `string` |  | — |
| `ParcelQA()` | `string` | 公 | 区画の正典(parcels.json)と指図の同期コピーが一致しているか。 |
| `ImplQA()` | `string` | 公 | 算出物 `okabe_impl.json` の自己検査。 ⟶ 返す: 人が読む報告 |
| `TerraceRingDist(uv)` | `float` |  | 点(グリッド座標)から段の輪郭(外輪・抜き・keeps)までの最短距離[間]。 |
| `RingDist(ring, p)` | `float` |  | — |
| `DistSeg(p, a, b)` | `float` |  | — |
| `HeightRange(zone, role, species, name, lo, hi)` | `bool` |  | 指図が宣言している丈の範囲を引く。⛔ 宣言の無い層に既定の範囲を当てない — 当てると「検査を通った」ことになるが、実際には何も検めていない。 |
| `RunAll()` | `string` | 公 | — |
| `RunAll_()` | `string` |  | — |
| `BindDonorMaterials()` | `string` |  | 素材の提供元からマテリアルを直接結ぶ。 ⚠ `SearchAndRemapMaterials` は独立した .mat しか探さない。 |
| `RemapOkabeShinzo()` | `string` | 公 | — |
| `RemapDir(dir)` | `int` |  | — |

## EdoSannoShaBuilder.cs

山王権現社(日枝神社)本体+樹下家邸+山王門前町ビルダー (2026-08-11。観理院は 2026-09-26 に類型へ移し削除)

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
| `Stage4_Juge()` | `string` | 公 | 2026-08-26 引退: 樹下邸は旧 EdoSannoBukeBuilder.Stage1_Juge が受け持ち、2026-09-21(EDO-0094)から 類型ビルダー(Edo_Typo_sannobuke_ju… |
| `Stage5_Monzencho()` | `string` | 公 | 2026-10-03 引退(EDO-0527 施主指示「古いものであれば削除」): 門前町は類型ビルダー(Edo_Typo_sanno_monzen_1〜4)が 受け持つ。 |
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
| `FaceFlushSegs(runs, sandoPieces, sb)` | `List<FaceFlushSeg>` |  | 見え面を石段の袖の背の面に揃える土留め(指図 joints: a = その run・kind「面一」・bFace「袖の背の面」── 前庭の切り込みの返し 施主裁定 2026-09-27 EDO-0437)の区間ごとに、紙… |
| `KeepClearOfFlushWalls(sa, sbb, name, sb)` | `void` |  | 板塀・柵の端が、見え面を袖の背へ移した土留めから紙の離れを保つ(2026-09-27・EDO-0437 普請検査 r15 ── 返しが外へ 0.60 移ったのに 板塀 Ita_ZN・Ita_ZNE の端が紙のまま残り、最… |
| `Nozura(runs, grp, placed, faceOf, dg, probe, sb)` | `int` |  | 野面の乱積みの土留め(`terraceWalls[].masonry`)を据える。 |
| `SegIsBase(prof, step, sBase, len)` | `bool` |  | 区間が基壇か ── 建つ所(見付 &gt; 0)の受け高が全て負(天端が両側の地盤より上)。 |
| `IsNozuraSode(g)` | `bool` |  | 袖の駒が野面の乱積みの袖(`IshidanSodeNozura*`)か(メッシュの資産名で)。 |
| `FamilyOf(n)` | `string` |  | — |
| `ArcOf(poly, p)` | `float` |  | 折れ線 poly 上での点 p の弧長。 |
| `ProfileAt(prof, step, s, top, faceH, backH)` | `bool` |  | `profile` = [走り s, 天端 y, 低い側の地盤, 高い側の地盤, 見付高, 受け高] を s で線形補間。 |
| `AbutStairsToWalls()` | `string` | 公 | — |
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
| `OnFumotomichi(p, keep)` | `bool` |  | 点が社の小道(指図 `fumotomichi[]`)の上か、その辺から keep の内か。 |
| `Michi()` | `List<List<Vector2>>` |  | 道の芯線(指図 `sando.pts`・算出物 `routes[].world`・指図 `fumotomichi[].pts`)を集める。 |
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
| `JDemMedian(dem, c, frac=…)` | `float` |  | 矩形の下の造成前の地盤(BaseDem)の分位 frac(0.5 = 中央値・1 = 最も高い所)── 1m 格子で引く。 |
| `JMinEdge(poly, c)` | `float` |  | — |
| `JExt(go, withRoof, e)` | `bool` |  | 駒の局所矩形(ピボットからの x0,x1,z0,z1)を実メッシュから測る。 |
| `JYaw(dirZ)` | `float` |  | — |
| `JishaOmoya(s, root, poly, front, pad, gateC)` | `string` |  | 寺社の境内を建てる。⭐ Omoya() の jisha 枝 — 返る文字列は「主屋と付属: …」の 2 行。 |
| `JSeed(id)` | `int` |  | 区画 id からの決まった種(FNV-1a)。 |
| `JCert(s, key)` | `string` |  | 表の欄の確度(`cert` の中の欄名)。 |
| `JHallBaked()` | `List<int[]>` |  | 焼いてある入母屋の間数(梁間 3 間以上・桁行/梁間 ≤ 1.8)。 |
| `JPickSize(area, rng, minD, lo=…, hi=…)` | `int[]` |  | 坪 area に近い焼いた入母屋を一つ(目安の 0.85〜1.25 倍の帯から種で選ぶ・帯が空なら最寄り)。 |
| `JHallSizes(s, tsubo, firm, rng, note)` | `List<int[]>` |  | 本堂の間数の候補(先頭が第一候補、以下は境内に収まらないときの一回りずつ小さい物)。 |
| `JRoofOf(it, go)` | `Vector2[]` |  | 置いた棟の屋根込みの矩形(置いた位置と向きから ── 測った局所矩形を載せる)。 |
| `JEnclosureRoofs(root, taken)` | `int` |  | 囲いの長屋の駒ごとに、屋根込みの矩形(駒の向きの軸で実メッシュを測った外形)を taken へ足す。 ⟶ 返す: 足した数 |
| `JGapTo(rc, taken)` | `float` |  | 矩形から置いた棟の屋根の矩形までの最小の離れ(無ければ 99)。 |
| `JAdd(items, dropped, g, name, path, mode, yaw, rank, hyo=…)` | `void` |  | プレハブの駒を 1 つ起こして一覧へ足す。 |

## EdoTypologyBuilder.Katte.cs

類型ビルダー — 勝手まわり(低い平場の菜園と、主の平場から降りる段石)。EDO-0532 施主裁定A(2026-10-03)。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `Katte(s, root, poly)` | `string` |  | — |

## EdoTypologyBuilder.Keidai.cs

類型の庭 — 寺社の境内(garden=keidai)。2026-09-27・EDO-0477 P5。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `KeidaiFor(kind, area)` | `KeidaiK` |  | kind ごとの係数(庭方の設計 k)。 |
| `KeidaiSlope(p)` | `float` |  | 庭域の点の勾配(±1m の差の大きい方 ÷ 2m)。 |
| `NiwaKeidai(s, grp, f, poly, front, rnd, mune, gateC, half, sandoB, want, got, log)` | `void` |  | 寺社の境内の庭。mune は据わった棟、half は参道の帯の片幅。 |

## EdoTypologyBuilder.Machiya.cs

類型ビルダー — 町屋(machiya)の段。24 区画。EDO-0325。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `NorenKeysFor(s)` | `string[]` |  | その間口の表店を当方で起こしてあるかを資産の有無で見て、あれば深い順に返す (深い版 → 詰めた版)。 |
| `MaguchiMix(s)` | `int[]` |  | 表の `maguchi_mix`(軒ごとに引く間口[間]の候補)。 |
| `OmotedanaFor(kens)` | `string[]` |  | 間口の候補すべてについて、当方で起こした駒を集める(幅ごとに深い順)。 |
| `OmotedanaFor(maguchiKen)` | `string[]` |  | — |
| `MachiyaFrontEdges(s, edges, front)` | `List<Edge>` | 公 | 表店を載せる接道辺。`two_sided=false` は 1 本、`true` は長い順に 2 本。 |
| `MachiKido(s, root, poly)` | `string` |  | 町木戸(EDO-0503 ②)。表の欄 machi_kido: {"with": "&lt;隣の区画&gt;", "end": "N／S／E／W"} を読み、 この区画と隣の区画の角どうしの組(間が道幅 4〜20m)のう… |
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
| `TakeSite(pool, rnd, f, r, o)` | `Vector2?` |  | — |
| `Layer(grp, name, f, pool, pal, want, rnd, o, want_, got_, poolAlt=…)` | `void` |  | 層をひと組据える。⭐ 意図した数と据わった数の差を必ず控える(§5-2 ①・規則19)。 |
| `MainBand(f, apex, n, faceLen, depth)` | `List<Vector2>` |  | 主景の帯 — 座敷面の中点 + 法線 3.0m を起点に、幅 = 面長 + 左右各 4.0m・奥行 25m の 帯と庭域 G の交わり(検分⑨)。 |
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
| `NiwaIdo(grp, f, katte, rnd, n, yaw0, want, got, log)` | `void` |  | 井戸。⭐ 据え方は PutIdo(山王社の前庭の井戸と同じ・EDO-0490)。 |
| `FillIdoHoles(root)` | `int` | 公 | 区画のルート(かその資産)の中の井戸が抜いた地形の穴を塞ぐ。 ⟶ 返す: 塞いだセルの数 |
| `PutIdo(grp, f, site, yaw0, spin, name, log)` | `GameObject` |  | 井戸一式を 1 口据える。返り値 = 板石敷の駒(井筒+井桁はその子)。 ⟶ 返す: 板石敷の駒(井筒+井桁はその子) |
| `NiwaMaeniwa(grp, f, rnd, gateC, bandHalf, front, want, got)` | `void` |  | 前庭。⛔ 帯の中には置かない(白洲)。門の内側の左右に松を必ず非対称に。 |
| `NiwaInspect(f, g, want, got)` | `string` |  | 庭方 §5-2 の5項目。⛔ 「置けた本数」だけを刷らない — 意図との差・帯の侵入・ 実測の離れ・偶数の塊・樹冠の被覆率まで出して、はじめて検査になる。 |

## EdoTypologyBuilder.Rim.cs

類型の崖の縁の石垣(Stage 4y・2026-09-28・EDO-0477 施主裁定A「石垣を積み、その上に塀」)。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `CornerReaches(edges, e, kind, atA, atB)` | `void` |  | 辺 e の囲いを区画の角で頂点の先へ延ばす長さ(始点 atA・終点 atB)。 |
| `Rim(s, root, poly, edges, front, machiyaFronts, pads, padY, rims, bed)` | `string` |  | — |

## EdoTypologyBuilder.Yuragi.cs

類型ビルダー — 揺らぎ(EDO-0476・施主裁定 2026-09-27)。

| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |
|---|---|---|---|
| `YuOrig(s, k)` | `string` |  | Plan の k 棟目を揺らぎで差し替えたなら、元の駒のパス。 |
| `YuRng(id, what)` | `System.Random` |  | 区画 id と用途から決まる乱数。⛔ 用途ごとに種を分ける ── 一つの乱数を使い回すと、 前段で引く回数が変わっただけで後段の姿が全部入れ替わる。 |
| `YuUnit(id, key)` | `float` |  | [0,1) の決まった値(区画 id と鍵から)。 |
| `YuLeaf(type, kind)` | `Dictionary<string, object>` |  | 表の `defaults.yuragi` の、この型に当たる塊。 |
| `YuLeaf(s)` | `Dictionary<string, object>` |  | — |
| `YuFirm(row, field)` | `bool` |  | その欄が史料値か(確度 S/A/B/P)。 |
| `YuF(d, k, dflt)` | `float` |  | — |
| `YuL(d, k)` | `List<object>` |  | — |
| `YuSay(id, what)` | `void` |  | — |
| `YuNote(s)` | `string` |  | 建てた log に刷る一行(揺らいだ欄の一覧)。 |
| `YuragiFields(id, row)` | `void` |  | 表の欄を揺らす。LoadTable が既定を差した後に呼ぶ。 |
| `YuKomaName(path)` | `string` |  | — |
| `YuKomaPath(name)` | `string` |  | — |
| `YuKoma(s, path, k)` | `string` |  | 主屋級の駒を同じ格の駒へ差し替える(表の `yuragi.buke.koma`)。 |
| `YuYaw(s, path, label)` | `float` |  | 付属の向きの足し[度](表の `yuragi.buke.fuzoku_yaw`)。 |
| `YuOkiba(s, p)` | `float` |  | 置き場の候補の点数に足す揺らぎ[m](表の `yuragi.buke.okiba_m`)── 点の座標から決まる(並べ替えの比較で毎回同じ値)。 |
| `YuTanaSeed(s, prefix)` | `int` |  | 表店の組を引く種(表の `yuragi.machiya.tana_mix`)。 |
| `YuJishaOkiba(s, dflt)` | `float` |  | 附属の置き場の点数の揺らぎ[m](表の `yuragi.jisha.<kind>.okiba_m`・無ければ dflt)。 |
| `YuHallBand(s)` | `Vector2` |  | 本堂の帯の倍率 [下, 上](表の `hall_band`)。 |
| `YuHallRange(s)` | `int[]` |  | 坊の主屋の間数の幅(表の `main_hall_w` / `main_hall_d`)。 |
| `YuKuri(s)` | `float[]` |  | 庫裏の間数(表の `kuri` の候補から種で)。 |

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
| `MachiyaYashikiRank(me, nb)` | `int` |  | 町屋と屋敷(武家・寺社)が接する辺だけ: 自分が屋敷なら +1・町屋なら -1。 |
| `DirVec(d)` | `Vector2` |  | — |
| `FrontEdge(s, edges)` | `Edge` | 公 | 表門を載せる辺。 ⭐ 史料で読めた方位は、長さの都合より強い。 |
| `FrontEdge(s, edges, warn)` | `Edge` | 公 | — |
| `ShopFront(poly, t, hull)` | `EdoBuild.MonPad` |  | 接地箇所を測って据える(EdoBuild.SeatOnGround)。 |
| `Seat(go, log)` | `bool` |  | — |
| `SeatGamae(go, log)` | `bool` |  | 門構えの駒を据える(EdoBuild.SeatGamae ── 札の contact の部材で当てる)。 |
| `Pad(id, spread)` | `float` | 公 | 造成はしない(規則3・9)。区画内のハイトマップ格子点の高さの中央値を、据える面に採る。 |
| `GatePathOf(g)` | `string` | 公 | 門の語 → 部材の道(札の試験 EdoPartSpecTests が読む)。 |
| `GatePath(g)` | `string` |  | — |
| `GateWidth(s, path)` | `float` |  | 門構えの幅の目安[m](表門の辺を選ぶため)= 門の札の脇の面の間 × 倍率(EDO-0491)。 |
| `GateChoices(g)` | `string[]` |  | 門の語の駒の候補(大きい順)。⭐ 冠木門は在庫の袖付き(幅 8.0m)と袖無し(2間・部材方 2026-09-30)の二つ ── 型は類型表の語のまま、接道辺に載る方を採る(施主裁定A 2026-09-30「袖の無い冠木… |
| `PickGatePath(s, edges)` | `string` |  | 接道辺のどれかに門構え(×1.25)が載る最も大きい候補。 |
| `BanshoCount(b)` | `int` |  | — |
| `Group(name, parent)` | `Transform` |  | ───────────────────────── Stage 1〜2: 囲いと門 ───────────────────────── |
| `FindRoot(name)` | `GameObject` |  | シーンのルートを名前で引く。⭐ 寝ているルートも拾う — 撤去は SetActive(false) の決まり(規則1)なので、GameObject.Find だけでは見落とす。 |
| `Externalize(root)` | `string` |  | 建て終えた類型ルートを 1軒1プレハブ へ切り出す(EDO-0296)。 |
| `BuildParcel(id, force)` | `string` | 公 | — |
| `EnclosureFor(s, e, isFront)` | `string` |  | この辺を何で囲うか。⛔ 2026-09-21 まで公有地は `fence` の欄を読まずに `yarai` を直書きしていて、 表に書いた yarai 1 / boji 3 / kui 1 / ita 1 / none… |
| `Omoya(s, root, poly, front, pad, gateC)` | `string` |  | 主屋・付属・庭木。区画の内側へ SETBACK 引いた所に、型ごとの棟を置く。 |
| `PairDir(a, b)` | `Vector3` |  | 二つの駒を互いへ押し付ける向き(a から b・水平)。 |
| `OmoyaOf(s)` | `string` |  | この区画の主屋の型。⭐ 表の `omoya` が勝ち、書いていないときだけ格帯から採る (割り当ては docs/typology-builder.md §4 の表と同じ)。 |
| `Plan(s)` | `List<KeyValuePair<string, float>>` |  | 型ごとに「何を何棟」。⛔ 在庫の代用が多い — 専用部材は部材方の宿題。 |
| `Inner(poly, d)` | `List<Vector2>` |  | 区画を d だけ内側へ寄せた所の「置ける点」を粗い格子で拾う。 |
| `Candidates(poly, cand, placed, r, tried)` | `IEnumerable<Vector2>` |  | Spot を次々に引く候補の列(引いた点は tried へ入れる)。 |
| `Spot(poly, cand, placed, r, tried)` | `Vector2?` |  | まだ空いていて、半径 r が区画からはみ出さず、既に置いた棟から MIN_BLDG_GAP 離れる点。 |
| `OutsideBy(poly, t, withRoof)` | `float` |  | 駒が区画の外へ出た量[m]。⭐ 壁体と軒を分けて測る。 |
| `SpecOutsideBy(poly, t)` | `float` |  | 門構え(門・番所)の区域侵犯 = 札の足元(EdoPartSpec.Spec.foot)が区画の外へ出た量[m](硬い・許容0)。 |
| `MichiInsideBy(poly, t)` | `float` |  | 道の上の物(群 "Michi" — 町木戸)が区画の内へ入り込んだ量[m](硬い・許容0)。 |
| `OutsideBy(poly, pts)` | `float` |  | — |
| `GamaeJointReport(encl, gm, front, frontKind)` | `string` |  | — |
| `IsSueMono(name)` | `bool` |  | — |
| `MonBedFor(piece)` | `System.Func<float, float, float>` |  | 門構えの駒の床 = 地面 + その駒の基壇の布石(縁と目地は 5cm 跨ぐ)。 |
| `GroundBed(x, z)` | `float` |  | 当たりの相手 = 見えている地表(live terrain)。 |
| `TuckBase(p0, p1, inw, stone=…)` | `float` |  | GroundBed と同じ床だが、石垣の天端の継ぎ目の穴(その点に天端の面が無く、0.35m 以内に有る所)は NaN を返す ── 塀は穴を跨いで石に載るので、穴の下の地面を床に数えない(EdoBuild.RootTo… |
| `RimStoneBack(bed, p, inw, maxIn)` | `float` |  | 点 p から内へ、石垣の天端の面(bed)が始まる離れ[m](最大 maxIn)。 |
| `GroundBedSpan(x, z)` | `float` |  | — |
| `KakoiBedFor(t)` | `System.Func<float, float, float>` |  | 囲いの駒の当たりの相手。布石("_ishi")は自分が床なので地面だけで測る ── 床の索引で測ると自分の天端を床に採り、 地中へ埋めた底を「浮き」と数えた(観理院の段塀の布石 86/86 駒・最悪 0.96m・2026… |
| `Inspect(id, root, poly)` | `string` | 公 | — |
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

