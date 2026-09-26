# EdoBuild の据え方の関数の目録(生成物・手で直さない)

<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py · 指紋 19caa1e970d6 -->

**据え方の関数を探すときは C# を grep で読み歩かず、まずここを引く。**置き方の手順と相手ごとの道具の選び方は
`docs/oki-kata.md`(正典)。ここは「どの関数が在り、何を返し、どこで使われているか」の索引だけ。

- 公開関数 226 本(注釈なし 17)。`Assets/Edo/Scripts/Editor/EdoBuild*.cs`・`EdoGeom.cs`・`EdoParcels.cs`(区画)の `///` 注釈から刷る。
- 同じ道具が刷る目録: 邸ビルダーのメニュー → Stage と中の関数 `docs/builder-mokuroku.md` / 部材の名 `docs/edoassets-mokuroku.md`。
- 札: **硬** = 注釈に「硬い/許容0」・**柔** = 「柔らかい/狙い」がある(判定ではなく注釈の語)。相手の札(地面・駒どうし・天端・床・断面・面・隅・区域)も注釈の語を拾っただけ。
- 呼んでいる所 = 定義のファイルの外で `EdoBuild.<名>(` と書いている C# ファイル(`Edo` と `Builder/Rebuild` を落とした名)と、その中の呼んでいる関数(Stage)。同じ名の多重定義はまとめて数える。`EdoBuild` の中どうしの呼び出しは載せない。
- 関数へ跳ぶ: `grep -n "static .* <名>(" Assets/Edo/Scripts/Editor/<ファイル>` → その行から読む。
- ⛔ 手で直さない。関数を足した・注釈を直したら `python3 Tools/Unity/edobuild_mokuroku.py` で刷り直し、C# と同じコミットに入れる。

## ファイルの索引

| ファイル | 何の道具か(ファイル冒頭の注釈) | 当たる先 | 関数 |
|---|---|---|---|
| [EdoBuild.cs](#edobuildcs) | 配置・資産系の共有基盤 (Phase 2c, 2026-08-26) | — | 43 |
| [EdoBuildGoten.cs](#edobuildgotencs) | 御殿複合(表向・中奥・奥向の3核)を組む — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは | — | 3 |
| [EdoBuildHifu.cs](#edobuildhifucs) | 縁の皮 — 地形に穴を開け、穴の縁から部材の面までを皮のメッシュで描く (EdoBuild の partial・2026-09-24・EDO-0430) | 切通しの石段(山王の女坂・男坂・参道の階)・天端を地盤に揃えた土留め(山王・土井・岡部の郭)・ 造成した面の縁(全邸の段の縁)。 | 12 |
| [EdoBuildInari.cs](#edobuildinarics) | 稲荷 — 小祠と鳥居を据える (EdoBuild の partial・2026-09-21・EDO-0326) | — | 3 |
| [EdoBuildIshidan.cs](#edobuildishidancs) | 石段の組 — 段石と袖(袖石垣)を一組の材で据える(EDO-0415・2026-09-23 施主指摘)。 | — | 32 |
| [EdoBuildJisha.cs](#edobuildjishacs) | 寺社の本堂(と坊・社家の主屋)を、間数ごとに焼いた入母屋で組む — EdoBuild の一部(規則21)。 | — | 1 |
| [EdoBuildJun.cs](#edobuildjuncs) | 部材を依存の順に解き、変えた所から後だけ流し直す (EdoBuild の partial・2026-09-26・EDO-0455) | 山王社の建て直し(EdoSannoShaRebuild の Stage0〜9)。 | 0 |
| [EdoBuildKado.cs](#edobuildkadocs) | 隅部材(留め継ぎ)の据え — EdoBuild の partial (2026-09-21・EDO-0289 ②) | — | 25 |
| [EdoBuildMachiya.cs](#edobuildmachiyacs) | 町屋の表店の run — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは EdoBuild の関数だけ」)。 | — | 7 |
| [EdoBuildMuki.cs](#edobuildmukics) | 向き(正面)の解き — EdoBuild の partial (2026-09-22・EDO-0261 ③) | — | 7 |
| [EdoBuildNiwa.cs](#edobuildniwacs) | 庭の置き方 — 類型の庭(Stage 5・EDO-0323)が使う「置く・測る・据える」だけ。 | — | 16 |
| [EdoBuildNozura.cs](#edobuildnozuracs) | 野面の乱積みの土留めを一本の折れ線へ据える — EdoBuild の partial(2026-09-25・EDO-0430) | — | 9 |
| [EdoBuildOsameru.cs](#edobuildosamerucs) | 寄せて測るを収まるまで回す (EdoBuild の partial・2026-09-26・EDO-0454) | 類型ビルダーの番所→門(EdoTypologyBuilder Stage 1・2b)。 | 2 |
| [EdoBuildRun.cs](#edobuildruncs) | 囲いの run — 長屋・土塀・板塀を辺に沿って並べる (EdoBuild の partial・2026-09-21) | — | 19 |
| [EdoBuildSeiyaku.cs](#edobuildseiyakucs) | 制約の二種 — 硬い制約(関門)と柔らかい制約(狙い)を、置く側の共通の層で使い分ける(EDO-0372・施主 2026-09-23)。 | — | 1 |
| [EdoBuildSueru.cs](#edobuildsuerucs) | 埋め込む駒・差し込む駒・載せる駒を据える (EdoBuild の partial・2026-09-23・EDO-0274) | 山王の前庭の井戸(板石敷・井筒+井桁・井戸屋形)。 | 15 |
| [EdoBuildUeru.cs](#edobuilduerucs) | 植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401) | SeatPlant を呼ぶ所すべて(今は山王の社叢の下層と名指しの木 = Stage7_Shaso だけ)。 | 10 |
| [EdoGeom.cs](#edogeomcs) | 純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26) | — | 6 |
| [EdoParcels.cs](#edoparcelscs) | 町割(敷地割)の正典 — docs/Sashizu/parcels.json | — | 15 |

## EdoBuild.cs

配置・資産系の共有基盤 (Phase 2c, 2026-08-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.ES` | `float` |  | edogoyomi の倍率 = 江戸間 1 間 = 6 尺 (CLAUDE.md 座標系の表)。 | — |
| `EdoBuild.InvalidateTerrain()` | `void` |  | 掴んでいる Terrain を捨てる。⚠ Terrain を差し替えたのに古い物が active のまま残る 差し替え方をしたときだけ要る(active が落ちる差し替えなら T が自分で拾い直す)。 | — |
| `EdoBuild.T()` | `Terrain` |  | アクティブな Terrain (最初の1枚)。 | SannoSha(Stage2_Kaidan・Stage3_Dodome・Stage7_Shaso…), Shiomizaka(Z0_Restore・Z1_Grade・Z4_ReseatGate), SannoSashizuCheck(Check), Sanyashiki(S2_GradeEdges), Yamato(Y1_Grade) |
| `GroundProbe`(struct) | — | | 地表を何度も引くための掴み。Terrain と原点の y を一度だけ掴み、以後は `SampleHeight` だけを叩く。 | |
| `EdoBuild.Probe()` | `GroundProbe` | 地面 | 地表の引き手を一つ作る。GroundProbe を見よ。 | — |
| `EdoBuild.Ground(x, z)` | `float` |  | live terrain の標高 (m)。 | SannoSha(Ground・SodeFootAt・Stage5_MonTorii…), OkabeYashiki(PlaceFences・PlaceKekkai・PlaceNiwaItem…), Yamato(PadAt・PlanSegments・Y1_Grade…), Sanyashiki(S2_GradeEdges・S3_Enclosure), Shiomizaka(BuildProfile・Z5_QA) |
| `EdoBuild.Place(path, pos, ry, scale, parent, name)` | `GameObject` |  | プレハブを実体化して置く。パスは EdoAssets 経由で渡すこと (規則11)。 | OkabeYashiki(MeasureHeight・MeasureRunWidth・NaturalHeight…), SannoSha(Kairo・Place・SakuRun…), MatsudairaDewa(FenceWidth・ItabeiRun・Leaves…), Doi(LayGaki・PlaceFumiishi・PlaceKaidans…), DoiBuilder.Niwa(Niwa_B_Gogan・Niwa_C_Mizushiri・Niwa_D_Tenkei…) ほか5 |
| `EdoBuild.RB(go)` | `Bounds` |  | 子孫 Renderer 全体のワールド Bounds。 | SannoSha(AbutStairsToWalls・Kairo・RB…), OkabeYashiki(MeasureHeight・NaturalHeight・PlaceBox…), MatsudairaDewa(ItabeiRun・ObbOverlapInBand・PlaceItabeiSpan…), Typology(BuildParcel・FenceFace・Omoya…), Doi(Box・PlaceFumiishi・PlaceKaidans) ほか7 |
| `EdoBuild.SeatBottom(go, y)` | `void` |  | Bounds の底面を y に据える。 | OkabeYashiki(PlaceKekkai・PlaceNagayaPiece・PlaceNiwaItem…), Yamato(PlaceUV・UmayaPair・Y2_Enclosure), DoiBuilder.Niwa(Niwa_D_Tenkei・Niwa_F_Yashiro), Doi(PlaceService), MatsudairaDewa(Stage2_Perimeter) ほか2 |
| `EdoBuild.ObbFootprint(it, mnx, mxx, mnz, mxz, mny)` | `void` |  | it のローカル座標系での mesh 頂点 footprint (OBB)。 | OkabeYashiki(ObbWD・PlaceNagayaPiece) |

### 据え付けの技法(2026-09-20)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.IsRoofName(name)` | `bool` |  | 屋根系のメッシュ名か(yane / noki / taruki / mune / keta)。 | Assets(Bochi) |
| `EdoBuild.Body(tr, maxSamples=…, withRoof=…)` | `List<Vector3>` | 地面・面・隅・区域 | 壁体(屋根・軒・垂木・棟・桁を除く、見えているメッシュ)の頂点を世界座標で。 | SannoSha(AbutStairsToWalls・Nozura・Stage2_Kaidan), TypologyBuilder.Jisha(JExt・JishaOmoya), Assets(Bochi), MatsudairaDewa(MeshBody), Typology(OutsideBy) ほか1 |
| `EdoBuild.EdgeAlong(tr, ax, sgn)` | `float` |  | 駒の壁体の、世界軸 ax 方向の端の座標(sgn ≥ 0 なら最大側)。 | SannoSha(Stage8_Ido) |
| `EdoBuild.FaceSpan(go, dir, yLo, yHi, mn, mx, perpDir=…, origin=…, perpMax=…)` | `void` | 天端 | 高さの帯 [yLo, yHi] にある見えている頂点を、 走り方向 dir(xz)へ投影した min/max。 | MatsudairaDewa(ProjBand), Typology(BuildParcel) |
| `EdoBuild.ProjSpan(go, dir)` | `float` | 面 | 駒の実メッシュ(見えている物だけ)を走り方向 dir(xz)へ投影した伸び[m]。 | TypologyBuilder.Niwa(Niwa・NiwaUra), MatsudairaDewa(ProjSpan) |
| `EdoBuild.LocalSpan(tr, localAxis)` | `float` |  | 駒の壁体を、駒の局所軸 localAxis へ投影した伸び[m](世界の尺度)。 | — |
| `EdoBuild.Face(go, dir, yLo, yHi, maxSide, perpDir=…, origin=…, perpMax=…)` | `float` |  | FaceSpan の片側。maxSide なら dir の正の側の面。 | MatsudairaDewa(Stage5_Mon) |
| `EdoBuild.FaceOut(go, a, n, yLo, yHi, pick=…)` | `float` |  | 線(点 a・外向き法線 n)からの、帯内の頂点の最大の張り出し[m] (= その駒の外面の位置。 | OkabeYashiki(AlignInubashiri・FaceOut), Typology(FenceFace) |
| `EdoBuild.AlignFace(go, a, n, target, yLo, yHi, pick=…)` | `float` |  | 外面(FaceOut)が target へ来るよう、法線 n 方向に 平行移動する。 ⟶ 返す: 移動量[m](測れなければ NaN) | MatsudairaDewa(Stage5_Mon), Typology(BuildParcel) |
| `EdoBuild.Abut(mover, dir, yLo, yHi, moverMaxSide, targetProj, gap=…, perpDir=…, origin=…, perpMax=…)` | `float` | 駒どうし・面 | 突き付け。可動側 mover の面(帯で測る)を、走り方向 dir 上の 相手の面の投影値 targetProj へ寄せる。 ⟶ 返す: 移動量[m](測れなければ NaN) | MatsudairaDewa(Stage5_Mon), SannoSha(ToriiFromMune) |
| `EdoBuild.StretchEnd(piece, pair, ax, sgn, target)` | `float` |  | 駒の端を目標へ伸縮させる(敷設の最後の一手。 ⟶ 返す: 伸ばした量[m](負 = 縮めた | — |
| `EdoBuild.GroundGrid(x, z)` | `float` |  | ハイトマップの格子点の世界座標と高さ。⛔ `Ground`(双一次)は格子の間で縁の擦り付けを拾い 0.1m が 2m に化ける(岡部 GradeQA)— 面の高さは格子点で測る。 | Typology(Inspect) |
| `EdoBuild.PadY(polyWorld, edgeMargin, spread, n)` | `float` | 地面 | 多角形(世界 xz)の内側、縁から edgeMargin 以上離れたハイトマップ格子点の高さの中央値。 | Doi(FaceY), GotenTypoTest(Build), MatsudairaDewa(TerraceY), Typology(Pad) |
| `EdoBuild.CrestY(stones, at, radius)` | `float` | 天端 | 点 at(世界 xz)を xz で含む(radius だけ広げた)石垣の駒の 天端の最大[m]。 | — |
| `EdoBuild.Contact(a, b, dir, at, count, tol=…, cell=…, maxSamples=…, withRoof=…)` | `float` | 地面・駒どうし・面・隅 | 二つの駒が実際に触れている箇所を測る。dir は 「a を押し付ける向き」(a から b へ向かう向き)。 ⟶ 返す: その取り合いの 最小の隙[m](正 = 隙間 / 負 = めり込み / 0 = 接触) | Typology(Inspect・Omoya), SannoSashizuCheck(Check), TypologyBuilder.Jisha(JishaOmoya) |
| `EdoBuild.Abut(mover, other, dir, gap, at, count, cell=…, maxSamples=…, withRoof=…)` | `float` | 駒どうし・面 | 触れている箇所で突き付ける。mover を dir へ動かし、 other との実際の接触(Contact)が gap(+ = 残す隙 / − = 差し込む量)になる所で止める。 ⟶ 返す: 動かした量[m] (向き合っていなければ NaN) | MatsudairaDewa(Stage5_Mon), SannoSha(ToriiFromMune) |
| `EdoBuild.Contact(go, at, count, tol=…, maxSamples=…)` | `float` | 地面・駒どうし・隅・区域 | 地面と触れている箇所を測る。(相手が地形のときの Contact。 ⟶ 返す: その隙[m](正=浮き・負=埋没・0=接触) | Typology(Inspect・Omoya), SannoSashizuCheck(Check), TypologyBuilder.Jisha(JishaOmoya) |
| `EdoBuild.UNDERFLOOR_MAX` | `float` | 床 | 床下の開きの合否閾値[m](縁の下 0.45m + 規則3 の系統差 ±0.25m = 0.70m。 | — |
| `EdoBuild.UnderfloorGap(go, at, maxSamples=…)` | `float` | 地面・床 | 床下の開き[m]。駒の接地候補点のうち、地面から最も離れた点(浮きの最悪。 | — |
| `EdoBuild.UnderfloorGap(pieces, worstName, maxSamples=…)` | `float` | 床 | 複数駒の床下の開きの最悪[m]と、その駒名。 | — |
| `EdoBuild.SeatOnGround(go, sink=…, maxSamples=…)` | `float` | 地面・天端・床 | 地面に据える。Contact で測った 地面と触れる箇所が地形(格子点)に着く高さへ動かし、 sink だけ沈める。 ⟶ 返す: 動かした量[m] | Typology(Omoya・Seat), TypologyBuilder.Jisha(JishaOmoya) |
| `EdoBuild.SeatBuried(go, fraction, maxSamples=…)` | `float` |  | 丈の fraction だけ埋めて据える。 ⟶ 返す: 埋めた量[m] | MatsudairaDewaBuilder.Niwa(Stage6c_Ishigumi) |
| `EdoBuild.SeatOnCrest(go, stones, sink, crest)` | `bool` | 天端 | 駒の底を、その真下の石垣の天端(CrestY)から sink だけ沈めた高さに据える。 | MatsudairaDewa(PlaceKado) |
| `EdoBuild.FitRunAlongAxis(foot, up, treadS, treadTop, searchHalf, step, accept, devBefore, devAfter)` | `float` | 地面・天端 | 段(石段)の一連を、地表の落ち際へ合わせて走り方向に滑らせる。 | MatsudairaDewa(Stage6_Zosaku) |
| `EdoBuild.KeepInsidePoly(go, poly, runDir, maxPull, before, step=…)` | `float` | 駒どうし・隅・区域 | 壁体を区画の多角形の内へ収める。置いた駒の実メッシュ(屋根を除く)が poly の外へ出ていたら、走り runDir に沿って 最小量だけ引いて収める。 ⟶ 返す: 動かした量[m](+ は runDir 向き・0 = 元から内側) | MatsudairaDewa(Stage3_Ishigaki) |
| `EdoBuild.GroundUnder(c, axisA, halfA, axisB, halfB, n, mn, mx)` | `void` | 地面 | 足あとの下の地形(格子点)の最小と最大。 | MatsudairaDewa(Stage6_Zosaku) |

### 隅の駒と塀の取り合い(2026-09-21)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.BodyAt(prefabPath, pos, yaw, withRoof=…)` | `List<Vector3>` |  | プレハブ資産を pos / yaw に据えたと仮定したときの 世界頂点。 | SannoSha(PanelProfile・SakuProfile・Stage3_Dodome), MatsudairaDewa(YaguraKeepout) |
| `EdoBuild.SectionAt(prefabPath, pos, yaw, y, withRoof=…)` | `List<Vector3>` | 天端・床・断面 | 部材を据えたときの、高さ y の水平断面(世界座標・実体化しない)。 | — |
| `EdoBuild.IsRoofLabel(name)` | `bool` |  | 材やサブメッシュの名で屋根を見分ける。IsRoofName(和名)に 英名の roof / 屋根 を足したもの。 | — |
| `EdoBuild.BodyBelowRoofAt(prefabPath, pos, yaw)` | `List<Vector3>` |  | 一体メッシュの駒の「一層目の躯体」の世界頂点(実体化しない)。 | — |
| `EdoBuild.BodyExRoofAt(prefabPath, pos, yaw, bodyParts=…, roofParts=…)` | `List<Vector3>` | 区域 | 一体メッシュの駒の「躯体」全部(屋根の材を除いたすべての材)の世界頂点(実体化しない)。 | MatsudairaDewa(YaguraSeat) |
| `EdoBuild.BodyExRoof(tr, maxSamples=…)` | `List<Vector3>` |  | Body 相当だが、単一メッシュに焼かれた駒(庫裏・墓地・鐘楼・山門など、 Blender 側で屋根まで join した部材)も材(サブメッシュ)の名で屋根を見分けて落とす (BodyExRoofAt の、実体化済み T… | Typology(OutsideBy), TypologyBuilder.Jisha(JExt) |
| `EdoBuild.CorridorSpan(pts, A, B, perpDir, perpLo, perpHi, yLo, yHi, s0, s1)` | `bool` | 地面・断面・隅 | 塀の通り道(回廊)を、その駒がどこからどこまで塞いでいるか。 | MatsudairaDewa(YaguraKeepout) |
| `EdoBuild.CorridorJambs(pts, A, B, perpDir, perpLo, perpHi, yLo, yHi, p0, p1, s0, s1)` | `bool` | 床 | 回廊を塞ぐ駒の「塞ぎ始め・塞ぎ終わりの点」(CorridorSpan の点版)。 | — |
| `EdoBuild.OpeningJambs(prefabPath, pos, yaw, A, B, perpHalf, yLo, yHi, bite, j0, j1, s0, s1, how)` | `bool` | 天端・床・断面 | 口に建つ駒(門)の脇柱へ、囲いの run の終端を取り付ける点を測る。 | SannoSha(ClipRunEndsToGates) |
| `EdoBuild.DobeiProfile(A, B, outward, seat, perpDir, perpLo, perpHi, yLo, yHi, outerAt=…, pad=…)` | `bool` | 断面 | その辺に建てる練塀の断面を、駒を1枚仮に据えて実測する。 | MatsudairaDewa(YaguraKeepout) |

## EdoBuildGoten.cs

御殿複合(表向・中奥・奥向の3核)を組む — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.GotenTargetArea(poly, root)` | `float` | 区域 | 御殿の建坪の目安[m²]。 = 建蔽率 GOTEN_KENPEI × 敷地 − 実測した外周(囲い・門)の建坪。 | Typology(Omoya) |
| `EdoBuild.FootprintXZ(group, maxSamples=…)` | `float` | 駒どうし | 群の直下の駒の壁体の footprint[m²]の合計(駒ごとの局所軸での外形。 | — |
| `EdoBuild.GotenComplex(parent, name, poly, gateC, inward, pad, targetArea, setback, verts, note)` | `GameObject` |  | 御殿複合を建てる。中軸(門から敷地の奥へ)に 玄関 → 表向 → 中奥 → 奥向 を並べ、 渡廊下でつなぐ。 | GotenTypoTest(Build), Typology(Omoya) |

## EdoBuildHifu.cs

縁の皮 — 地形に穴を開け、穴の縁から部材の面までを皮のメッシュで描く (EdoBuild の partial・2026-09-24・EDO-0430)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.SKIN_PREFIX` | `string` |  | 皮の GameObject の名の頭。Drawn はこの名の MeshFilter を皮と読む。 | — |
| `SkinFace`(struct) | — | | 皮の中で高さを揃える造成の面(世界 XZ の多角形と面の高さ)。 | |
| `SkinDesign`(class) | — | | 皮が面の外で写す設計の地盤(算出物 `graded` の節点格子。 | |
| `SkinReport`(struct) | — | | CutEdgeSkin の報告。 | |
| `EdoBuild.BAND` | `float` | 地面 | 面の縁の線の帯の幅(縁からこの距離の中で地形が描く高さを検める)[m]。 | — |
| `EdoBuild.FLAT` | `float` | 天端 | 裏込めの天端の平ら(部材の外形の縁から)[m]。 | — |
| `EdoBuild.BACK_FILL` | `float` |  | 土留めの背の外形の縁で、外の地盤(0.6m 先)が駒の底より低いときに底まで盛ってよい高さ[m](2026-09-26・EDO-0437 第3巡)。 | — |
| `EdoBuild.CREST_BAND` | `float` | 天端 | 天端の帯の深さ・周りを見る半径[m](TopIndex.banded)。 | — |
| `EdoBuild.FloorTris(g, faces, floorTop, hull)` | `List<Vector3[]>` | 地面・天端・床 | 門の床(基壇)の三角形(EDO-0428)。 | — |
| `EdoBuild.OpenUpTris(g, upOnly=…)` | `List<Vector3[]>` |  | 駒の屋根・軒でない三角形(upOnly なら上向きの面だけ)。 | — |
| `EdoBuild.GATE_UNDER` | `float` | 硬 | 皮を門の上向きの面の下へ納める量[m](硬い: 面 − 皮 ≥ 0.02 ── 普請検査 EDO-0428 二巡目)。 | — |
| `EdoBuild.GATE_BURY` | `float` | 天端 | 皮に埋まる門の上向きの面を拾う深さ[m](= 皮の天端の下へ納める量 under と同じ)。 | — |
| `EdoBuild.FLOOR_REACH` | `float` | 天端・床 | FloorTris が床の天端を探す、面の高さからの幅[m]。 | — |
| `EdoBuild.CutEdgeSkin(name, parent, parts, faces, faceTol, step=…, margin=…, eps=…, under=…, design=…, drawTol=…, backfill=…, sealFace=…, digParts=…, digUnder=…, digBatter=…, crestBandParts=…, plantPoints=…, floorParts=…)` | `SkinReport` | 硬 地面・天端・床 | 縁の皮を起こす。parts(石段・袖・土留め)の外形に掛かる地形の升と、 faces の縁で地形が面の高さから faceTol を超えて外れる升に穴を開け、 その升を step 格子の皮で描く(皮は parent の下に… | SannoSha(Stage9_Hifu) |
| `EdoBuild.MeasureSkinContact(parts, samples=…, crestBandParts=…)` | `SkinReport` |  | 皮と部材の取り合いを測り直す(皮を起こし直さずに)。 | — |
| `EdoBuild.SkinGapTable(parts, faces, faceTol)` | `string` | 地面・駒どうし | 皮と部材の隙を三つに分けて刷る(2026-09-25 普請奉行の決め・EDO-0430): A 面の高さで塞がる(外が面の中・部材の底 ≤ 面 + 許容)/ B 駒が浮く(外が面の中・底 &gt; 面 + 許容 ── 駒… | SannoSha(HifuGapTable・Stage9_Hifu) |
| `EdoBuild.ClearEdgeSkins(parent)` | `int` |  | ⚠ 注釈なし | SannoSha(Stage9_Hifu・UnSkin) |
| `DrawnGround`(class) | — | | 描かれた地表を引く掴み。穴の升では皮の高さ(皮が無ければ NaN = 何も描かれていない)、 それ以外は地形(SampleHeight)。 | |
| `EdoBuild.Drawn()` | `DrawnGround` | 地面 | 描かれた地表の掴みを作る(DrawnGround)。 | SannoSha(AbutStairsToWalls・HifuMeasure・RetractRunEndsFromWalls…), SannoSashizuCheck(Check) |
| `EdoBuild.DrawnExpected()` | `DrawnGround` | 地面 | 皮を外している間も、外す前の皮を描かれた地表として読む掴み(2026-09-26・EDO-0437 第11巡)。 | SannoSha(AbutStairsToWalls) |
| `PartTops`(class) | — | | 部材の上を向いた面の最も高い所を引く掴み(駒が他の駒の下に入っているかを見る)。 | |
| `Bed`(class) | — | | 据わる床 = 描かれた地表(Drawn ── 縁の皮の升では皮)と、据えた部材(土留め・石段・袖)の 上向きの面の、高い方。 | |
| `EdoBuild.ContactOn(go, bedAt, at, count, tol=…, maxSamples=…)` | `float` | 床 | Contact と同じ測り(格子ごとの最下点)を、 任意の床 bedAt に対して取る。 ⟶ 返す: 触れている所の隙(正=浮き・負=埋没) | — |
| `EdoBuild.SettleOnBed(go, bedAt, before, maxSamples=…)` | `float` | 硬 床 | 浮いていれば床へ下ろす。座(指図の面の高さ・`sill`/`seat`)は上限として置いた駒を、 床(Bed)から浮いていれば触れる所まで下ろす。 ⟶ 返す: 下ろした量[m](0 以上) | SannoSha(Stage5_MonTorii) |
| `EdoBuild.SeatOrBed(x, z, seat, root, bedAt)` | `float` | 床 | 走りの継ぎ目(駒の原点 = 地盤の高さ・根入れ root を持つ柵の柱)の高さ: 座 seat で駒の足元(座 − 根入れ)が床より上に出る(= 浮く)なら床へ、そうでなければ座。 | SannoSha(SakuRun) |
| `EdoBuild.TopBurial(piece, dg, over, samples, hidden, worst, worstAt, step=…)` | `int` | 地面・天端 | 駒の天端の埋没を描かれた地表で数える(石段の段石など、天端が一枚の面の駒)。 ⟶ 返す: 埋没の点の数 | SannoSha(HifuMeasure) |

## EdoBuildInari.cs

稲荷 — 小祠と鳥居を据える (EdoBuild の partial・2026-09-21・EDO-0326)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `InariTally`(struct) | — | | 稲荷を据えた結果。⛔ 呼び手は必ず全部刷る(規則19)— とくに cands が 0 のときは「置かなかった」であって「合格」ではない。 | |
| `EdoBuild.PivotSink(path, scale)` | `float` |  | 地盤レベルのピボット規約で焼かれた駒が、ピボットより下へ出している量[m]。 | — |
| `EdoBuild.BodyOut(go, a, n)` | `float` | 面 | 駒の壁体(屋根を外した実メッシュ)の、点 a から向き n への最大の張り出し[m]。 | — |
| `EdoBuild.InariSet(parent, prefix, poly, hokoraPath, toriiPath, face, anchor, sandoM, avoid, clear, t)` | `List<GameObject>` | 面・区域 | <summary>稲荷を一社据える。小祠を anchor に一番近い空き地へ据え、 その正面の実面から sandoM 離して鳥居を立てる。 ⟶ 返す: 据わった駒(祠・鳥居)。据えられなければ空で、理由は t.why。 | TypologyBuilder.Inari(Inari) |

## EdoBuildIshidan.cs

石段の組 — 段石と袖(袖石垣)を一組の材で据える(EDO-0415・2026-09-23 施主指摘)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.ISHIDAN_SODE_KASA` | `float` | 天端 | 袖の天端の線が段鼻の線から上がる高さ[m]。 | — |
| `EdoBuild.PlaceIshidanSode(dan, sodePath, side, parent, name, warn)` | `GameObject` | 硬 駒どうし・天端 | 段石1段の脇に袖の駒を1つ据える(石段の組・EDO-0415)。 ⟶ 返す: 据えた駒 | — |
| `SodeRise`(struct) | — | | PlaceIshidanSode の 天端の上げの勘定。 | |
| `EdoBuild.PlaceIshidanSodeByDepth(dan, pathOf, depths, side, parent, name, groundHi, warn, rise, lineTop=…, footAt=…, neiri=…)` | `GameObject` | 硬 天端・床 | 丈を選んで袖を据える(EDO-0430 2026-09-24)。 | SannoSha(Stage2_Kaidan) |
| `EdoBuild.PlaceIshidanSode(dan, sodePath, side, parent, name, groundHi, warn, rise, lineTop=…)` | `GameObject` | 硬・柔 地面・天端 | 段石1段の脇に袖の駒を1つ据える。groundHi = true なら指図の `copingRise:"groundHi"`(天端 = max(段鼻の線 + 笠, 高い側の地盤) ── 裁定 EDO-0182 (a))を… | — |
| `EdoBuild.SodeFootShort(sode, dan, side, footAt, neiri)` | `float` | 面 | 袖の根入れの不足[m](joints[69]・2026-09-25)。 | — |
| `EdoBuild.MiterIshidanSode(dans, sodes, side, keri, fumi, w, warn)` | `int` | 硬 | 曲がる石段の袖を留めに切る(EDO-0415 ②)。 ⟶ 返す: 切った継ぎ目の数 | SannoSha(Stage2_Kaidan) |
| `EdoBuild.MiterIshidanSode(dans, sodes, side, keri, fumi, w, warn, depthOf)` | `int` |  | 丈を段ごとに持つ版。depthOf[i] = 段 i の袖の丈(SodeRise.depth・ null または 0 は既定 2.20)⇒ 留めの駒も同じ丈の物を引く(丈違いの駒へ差し替えると下端が段石の底より上に出る)… | SannoSha(Stage2_Kaidan) |
| `EdoBuild.IshidanSodeSide(dan, wallNodes)` | `int` |  | 袖を据える側 = 段石の ±X のどちらに、その袖の土留めの線があるか。 | SannoSha(Stage2_Kaidan) |
| `EdoBuild.AbutCrestToStep(pieces, outw, step, band=…)` | `float` | 駒どうし・天端・床・面 | 石垣の区間の天端の前の縁を、石段の最上段の段石の背の端へ突き付ける(指図 joints[72]「奥の辺の外面 × 最上段」・2026-09-25・EDO-0430)。 ⟶ 返す: 動かした量[m](+ = 坂下へ・測れなければ NaN) | SannoSha(Stage3_Dodome) |
| `EdoBuild.WrapTopStep(dan, m)` | `Vector2[]` |  | 最上段の段石の外形を包む面の輪郭(取り合いの「被せ」── 面の輪郭が最上段の小口まで届き外形を包む・EDO-0430)。 | SannoSha(Stage9_Hifu) |

### 端を相手の面へ突き付ける(法の付いた壁と鉛直な端)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.ExtentAlong(g, outDir)` | `Vector2` |  | 駒 g の実メッシュの、水平の向き outDir への射影の [最小, 最大](駒の位置からの距離)。 | SannoSha(AbutStairsToWalls) |
| `EdoBuild.EndOffsets(g, outDir, perp, along, y, walls, maxIn, maxOut)` | `float[]` | 駒どうし | 駒の端の面から相手の面までの離れを、高さ y の水平な光線で測る(2026-09-25・EDO-0430)。 | — |
| `EdoBuild.ResizeEnd(g, outDir, delta)` | `float` |  | 駒の片方の端だけを delta[m] 動かす(+ = outDir へ伸ばす・− = 詰める)。 ⟶ 返す: 軸の縮尺の比(駒が回っていて平行な軸が無ければ NaN・動かさない) | — |
| `EndAbut`(struct) | — | | 端の突き付けの報告(AbutEndToFace)。 | |
| `EdoBuild.AbutEndToFace(g, outDir, perp, along, yLo, yHi, walls, maxIn, maxOut, spreadTol)` | `EndAbut` | 硬 駒どうし | 鉛直な端を、法の付いた相手の面へ、高さの中ほどで突き付ける(2026-09-25・EDO-0430 施主指示)。 | SannoSha(AbutStairsToWalls) |
| `EdoBuild.AXIS_MARK` | `string` | 駒どうし | 石段の段石の両の小口を、脇の土留め(法の付いた面)へ段ごとに突き付ける(2026-09-25・EDO-0430 施主指示)。 | — |
| `EdoBuild.StepAxis(dan)` | `Vector3` |  | 段石の芯(石段の軸の上の点)。印 AXIS_MARK があればその位置、無ければ駒の位置。 | SannoSashizuCheck(Check) |
| `EdoBuild.AbutStepEndsToWalls(dans, keri, fumi, walls, maxIn=…, maxOut=…, spreadTol=…)` | `List<KeyValuePair<string, EndAbut>>` |  | ⚠ 注釈なし | SannoSha(AbutStairsToWalls) |

### 端を法の面で切った駒へ差し替える(EDO-0430 2026-09-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.RayFarthest(bodies, o, d, maxDist)` | `float` |  | 光線が bodies の三角形を通る距離のうち最も遠い物(駒の中から打てば、外の面を出る所)。 | — |
| `BatterEnd`(struct) | — | | 段石の端が法の面の相手(返し・隅の駒)に当たる形の実測(MeasureStepEndOnBatter)。 | |
| `EdoBuild.MeasureStepEndOnBatter(flatDan, side, keri, walls, maxIn=…, maxOut=…, spreadTol=…)` | `BatterEnd` | 駒どうし・隅 | 段石の片方の端と法の面の相手の取り合いを測る(2026-09-26・EDO-0430)。 | — |
| `EdoBuild.MeasureSodeBackOnBatter(sode, keri, walls, spread, maxOut=…)` | `float` | 駒どうし・隅 | 袖の背(坂上の端)と法の面の相手の離れ e を測る(2026-09-26・EDO-0430)。 | — |
| `EdoBuild.MeasureSodeBackEnvelope(sode, keri, walls, nori, spread, maxOut=…, visAt=…)` | `float` | 天端・隅 | 袖の背と野面の相手の離れを石の出の包絡で測る(2026-09-26・EDO-0437 第3巡)。 | — |
| `EdoBuild.EnvelopeCut(flatDan, side, keri, walls, nori, visAt, straddle)` | `float` | 地面・駒どうし・隅 | 段石の端と野面の相手の包絡の切り d(2026-09-26・EDO-0437 第3巡)。 | Assets(DanKiriEnd) |
| `EdoBuild.EnvelopeStraddle(flatDan, side, keri, walls, dEnv, visAt, uphill, za)` | `bool` | 隅 | 跨ぐ端の隅の駒のもう一面を野面の包絡で測る(2026-09-26・EDO-0437 第4巡)。 | — |
| `EdoBuild.SwapToFitted(pieces, fitPathOf, sb)` | `Dictionary<GameObject, GameObject>` | 駒どうし | 相手の石の形に沿わせて焼いた駒へ、据えを変えずに差し替える(2026-09-26・EDO-0437 第11巡)。 ⟶ 返す: 旧 → 新 | SannoSha(AbutStairsToWalls) |
| `EdoBuild.SwapWallsBesideStep(step, walls, fitPathOf, sb, reach=…)` | `Dictionary<GameObject, GameObject>` | 天端 | 段石の端に脇から接する土留めの駒を、その段に合わせて焼いた駒へ、据えを変えずに差し替える(2026-09-27・EDO-0437 r14)。 ⟶ 返す: 旧 → 新(呼び手は群の一覧を差し替える) | SannoSha(AbutStairsToWalls) |
| `EdoBuild.CutStairEndsToBatter(label, dans, sodes, keri, fumi, walls, flatDanPath, kiriPath, flatSodePath, noriPath, sb, tol=…, envNori=…, sodeEnvNori=…, envVisAt=…, envWall=…)` | `HashSet<GameObject>` | 硬 駒どうし・隅 | 石段の段石の端・袖の背を、法の面の相手に合わせて切った駒へ差し替える(2026-09-26・EDO-0430 施主裁定B・EDO-0442)。 ⟶ 返す: 差し替えた駒(呼び手は突き付けを掛けない) | SannoSha(AbutStairsToWalls) |

### 袖の脇の面 × 隅の駒・土留めの法(EDO-0437 第8巡 2026-09-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `StepYield`(struct) | — | | YieldWallsToSteps の一件(土留めの駒ひとつ)。 | |
| `EdoBuild.YieldWallsToSteps(steps, walls, visAt, keri, maxMove=…, fixedNear=…)` | `List<StepYield>` | 硬 地面・隅 | 段石の端に被さる土留め・隅の駒を、段の外へ退ける(2026-09-26・EDO-0437 第9巡・普請奉行の決め「段は動かさない ── 隅石の据えの側で避ける」)。 | SannoSha(AbutStairsToWalls) |
| `SodeSideBite`(struct) | — | | MeasureSodeSideBites の一件(袖の駒 × 相手の駒 × 脇の向き)。 | |
| `EdoBuild.MeasureSodeSideBites(sodes, walls, visAt)` | `List<SodeSideBite>` | 硬 地面・駒どうし・隅 | 石段の袖の脇の面へ入る相手(隅の駒・土留めの法の足)を測る(2026-09-26・EDO-0437 第8巡・普請奉行の決め「袖が譲る」)。 | SannoSha(AbutStairsToWalls) |

### 敷石(踏石・石段の頭の踏み止め)・袖の端を相手の面まで延ばす(EDO-0428 2026-09-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Shiki`(struct) | — | | LayShikiishi の報告。口・食い込みは据えた後に天端の帯で光線を打って測った最大(相手の在る端だけ・無ければ NaN)。 | |
| `EdoBuild.RayAtTopBand(mates, o, d, maxDist, yTop, band=…)` | `float` | 駒どうし・天端 | 天端の帯へ光線を打つ。高さ yTop − 0.005 から band 下まで 0.01 刻みで o(高さは無視)から d へ打ち、最初に当たった高さでの距離(当たらなければ NaN)。 | — |
| `EdoBuild.ExtendEndToFace(piece, dir, mates, yTop, maxReach, spread, hits)` | `float` | 駒どうし・天端 | 駒の端を相手の面まで伸ばす(StretchEnd)。 ⟶ 返す: 伸ばした量[m](当たらなければ NaN・駒は触らない) | — |
| `EdoBuild.MeasureEndGap(piece, dir, mates, yTop)` | `float` | 駒どうし・天端 | 駒の dir の端と相手の面の見える口[m](+ 口 / − 食い込み)の最大 ── 駒の厚みの 3 点 × 天端の帯 (yTop − 0.005 から下へ、最初に当たる高さ)。 | — |
| `FlatSode`(struct) | — | | LayFlatSode の検め(全て実メッシュで測った値)。 | |
| `EdoBuild.LayFlatSode(old, below, pathOf, depths, up, mates, yBand, maxReach, rep, warn)` | `GameObject` | 硬 駒どうし・天端 | 石段の袖の最上段の駒を、天端が水平な袖へ差し替えて相手の面まで伸ばす(EDO-0459 施主裁定A 2026-09-26)。 | SannoSha(Stage5b_Fumiishi) |
| `EdoBuild.LayShikiishi(pathOf, quad, front, top, parent, name, backMates, frontMates, sideMates, rep)` | `List<GameObject>` | 硬・柔 地面・天端・面 | 敷石を据える(踏石・石段の頭の踏み止め・EDO-0428)。 | SannoSha(Stage5b_Fumiishi) |
| `EdoBuild.SinkCoplanarUnder(pieces, others, report, tol=…, drop=…, measureOnly=…, maxDrop=…)` | `int` | 天端 | 相手の上向きの面と同じ高さで重なる駒を下げる(普請奉行の決め 2026-09-26・EDO-0428 二巡目)。 ⟶ 返す: 下げた駒の数 | SannoSha(Stage5b_Fumiishi) |

## EdoBuildJisha.cs

寺社の本堂(と坊・社家の主屋)を、間数ごとに焼いた入母屋で組む — EdoBuild の一部(規則21)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.Honden(parent, name, wKen, dKen, note)` | `GameObject` |  | 間数(外形)で本堂を建てる。桁行 wKen ≥ 梁間 dKen になるよう入れ替える(大棟は桁行に架かる)。 | TypologyBuilder.Jisha(JishaOmoya) |

## EdoBuildJun.cs

部材を依存の順に解き、変えた所から後だけ流し直す (EdoBuild の partial・2026-09-26・EDO-0455)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Jun`(class) | — | | 解く順。 Stage を依存つきで宣言し、変えた Stage から下流だけを流す。 | |

## EdoBuildKado.cs

隅部材(留め継ぎ)の据え — EdoBuild の partial (2026-09-21・EDO-0289 ②)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.KadoDeg(poly, vertex)` | `float` | 区域 | 隅の折れ角[°]を区画から測る。入りの走り(頂点の手前の辺)から出の走り(次の辺)への旋回で、 左へ曲がれば負・右へ曲がれば正。 | MatsudairaDewa(PlaceKado), OkabeYashiki(PlaceKado) |
| `EdoBuild.KadoFace(kc, poly, e1, outNormal, target, wallT, moved, note)` | `bool` | 隅・区域 | 隅部材の両腕の外面を、平行移動だけで target(区画線から外向きへ。 ⟶ 返す: 動かした量(xz) | MatsudairaDewa(AlignInubashiri), OkabeYashiki(FitKado) |
| `EdoBuild.KadoArm(kc, poly, e1, outNormal, target, wallT, seatDrop, h, l)` | `bool` |  | 据えた隅部材の「腕」が、接する二辺の s をどこまで覆っているかを実メッシュで測る。 | MatsudairaDewa(KadoArmSpan), OkabeYashiki(FitKado) |
| `EdoBuild.PlaceRunKado(runA, nA, runB, nB, pathOf, groundAt, parent, name, tol, note, convex=…, abut=…, armPathOf=…, farA=…, farB=…)` | `GameObject` | 硬 地面・天端・面・隅 | 石垣の run の出隅へ隅の駒を据える(2026-09-25・EDO-0430)。 | — |
| `EdoBuild.ARM_OVER` | `float` | 硬 面・隅 | 隅の腕の長さを、相手の実測から焼いてある駒の中で選ぶ(2026-09-26・EDO-0437)。 | — |
| `EdoBuild.KadoArmNeeds(kc, P, yLo, yHi, armX, armZ, abut, full, needX, byX, needZ, byZ)` | `void` | 隅 | 隅の駒の各腕へ入る相手の走りの最小を測る(2026-09-26・EDO-0437 第7巡)。 | — |
| `MeshInside`(class) | — | | 点が駒の実メッシュの中に在るかを 8 方向の光線で読む器(2026-09-26・EDO-0437 第7巡)。 | |
| `EdoBuild.DebugCorners` | `bool` | 面 | 石垣の run の区間の端ひとつ。key = 区間の駒の並びの名(run#区間)、node = run の折れ線の節点の番号、 outw = 見え面の外向き、away = 端から区間の奥へ向かう走り。 | — |
| `RunEnd`(struct) | — | | (注釈なし) | |
| `EdoBuild.PlaceRunCorners(ends, pieces, pathOf, groundAt, parent, tol, log, made, abut=…, armPathOf=…)` | `int` | 硬 天端・面・隅 | 石垣の run の折れ目すべてに出隅の隅の駒を据える(PlaceRunKado を区間の端の組ごとに呼ぶ)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.FaceSide(run, axis)` | `Vector2` | 面 | 石垣の駒の並び run の見え面の外向きを、軸 axis の ± のうち 下の帯(下 25%)が上の帯(上 15%)より前へ出る側として測る(法の付いた面が見え面・鉛直な背は出ない)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.WallFaceRise(piece, groundAt)` | `float` | 地面・面 | 石垣の駒の見え面(法の付いた面)が低い側を向いているかを測る(2026-09-25・EDO-0430)。 ⟶ 返す: 前 − 後ろ[m](+ なら見え面が高い側を向く = 裏返り) | SannoSha(HifuMeasure) |
| `EdoBuild.WallFace(piece)` | `Vector2` | 天端・面 | 石垣の駒の見え面の向き(世界 XZ の単位)。 | SannoSha(HifuMeasure) |
| `EdoBuild.CrestAboveGround(piece, outw, groundAt, probe=…)` | `float` | 地面・天端・面・隅 | 駒の天端が見え面の前の地表より上に出るか(全体が地表の下に来る駒を見分ける・2026-09-25 EDO-0430 joints[68])。 ⟶ 返す: 天端 − 地表 の最大[m](≤ 0 なら全ての帯で天端が地表の下 = 全体が埋まる駒) | SannoSha(Stage3_Dodome) |
| `EdoBuild.EndAboveGround(piece, away, groundAt, probe=…)` | `float` | 地面・天端 | 駒の端の小口が地表より上に出るか(run の端で埋まる駒を退けた後の検め・2026-09-25 EDO-0430 joints[67])。 ⟶ 返す: 天端 − 地表[m](> 0 なら小口の上が地表より上に出ている) | SannoSha(Stage3_Dodome) |
| `EdoBuild.KadoFaces(piece, f1, f2)` | `void` | 面・隅 | 出隅の駒の二つの見え面(局所の二軸の FaceSide)。 | SannoSha(HifuMeasure) |
| `EdoBuild.WallFaceRiseKado(piece, groundAt)` | `float` | 面・隅 | 出隅の駒の見え面が低い側を向いているかを測る(2026-09-25・EDO-0430)。 ⟶ 返す: 前の高い方 − 後ろ[m](+ なら裏返り) | SannoSha(HifuMeasure) |
| `EdoBuild.LowSide(a, b, groundAt, probe, eps, use, votes, against)` | `Vector2` | 地面・面 | 線 a→b のどちら側が低いかを描かれた地表で測る(2026-09-25・EDO-0430)。 ⟶ 返す: 低い側の単位法線 (票が無ければ Vector2.zero ── 呼ぶ側が別の手掛かりで決める) | SannoSha(Stage3_Dodome) |
| `EdoBuild.LowSideAwayFromWalls(a, b, probe, walls, self, band)` | `Func<float, bool>` | 硬 地面・天端・面・隅 | LowSide の測り点が他の壁の体の上に落ちる走りを外す(use に渡す述語・2026-09-26・EDO-0437)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.RunLowHand(segs, groundAt, probe, eps, use)` | `int` | 面 | 一本の折れ線の土留めの「低い側の手」を区間の票の差で決める(2026-09-25・EDO-0430)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.OverlapAlong(p0, p1, run)` | `float` |  | 折れ線 run を線分 p0→p1 へ射影したとき、線分の上で重なる長さ[m](2026-09-25・EDO-0430)。 | SannoSha(Stage2_Kaidan・Stage3_Dodome) |
| `EdoBuild.ShortSegConvexEnd(a, b, outw, segs, tol=…)` | `int` | 駒どうし・天端・面・隅 | 駒より短い区間の、どちらの端が出隅か(2026-09-25・EDO-0430)。 ⟶ 返す: +1(a だけが出隅)/ −1(b だけが出隅)/ 0(どちらでもない・両方) | SannoSha(Stage3_Dodome) |
| `EdoBuild.FlushRunEnd(piece, end, toward, band=…)` | `float` | 駒どうし・天端 | 駒の端を区間の端へ突き付ける(ShortSegConvexEnd の相方・2026-09-25・EDO-0430)。 ⟶ 返す: 動かした量[m](+ = 端の側へ) | SannoSha(Stage3_Dodome) |
| `RunEndStop`(struct) | — | | RunEndAtFace の答え。 | |
| `EdoBuild.RunEndAtFace(end, toward, faceBodies, angTolDeg=…)` | `RunEndStop` | 硬 駒どうし | run の端を、相手の駒(石段の袖など)の外面で止める(2026-09-26・EDO-0430 指図 joints「土留めは袖の外面で止め、端に隅の塊を置かない」)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.BlockOutward(a, b, others, tol=…)` | `Vector2` | 地面・天端・面 | 基壇(天端が両側の地盤より上の石垣)の見え面の向きを、端で継ぐ壁の走りから決める(2026-09-25・EDO-0430)。 | SannoSha(Stage3_Dodome) |
| `EdoBuild.FaceWallToLine(piece, lowN, lineA, band=…)` | `float` | 天端・面 | 石垣の駒の見え面(法の面)を lowN へ向け、天端の前の縁を線へ寄せる(2026-09-25・EDO-0430)。 ⟶ 返す: 寄せた量[m](+ = 低い側へ) | SannoSha(Stage3_Dodome) |

### 一直線の継ぎ目・二段築の下段(2026-09-25・EDO-0430)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.ContinuesStraight(end, away, others, tolM=…, tolDeg=…)` | `bool` | 床 | run の端 end の先へ、別の区間(others の [a, b])が一直線に続くかを測る。 | SannoSashizuCheck(Check), SannoSha(Sukibei) |
| `TierUpper`(struct) | — | | 二段築の上段の区間ひとつ ── 据わった上段の駒(pieces)と区間の線 [a, b](天端の前の縁の線)・見え面の外向き。 | |
| `EdoBuild.CrestToBack(piece, outw, band=…)` | `float` | 天端 | 石垣の駒の控え = 天端の前の縁(天端の帯 band の外向きへの射影の最大)− 背(全頂点の射影の最小)[m]。 | — |
| `EdoBuild.PlaceTierBelow(ups, piecePath, runLen, pitchMax, pieceH, groundAt, probe, parent, eps, endsOut, segOut, faceOut, made, log)` | `int` | 硬 駒どうし・天端・面・隅 | 二段築の下段を、据わった上段の駒の実メッシュから測って据える(指図 `terraceWalls[].tierPlan`・2026-09-25・EDO-0430)。 | SannoSha(Stage3_Dodome) |

## EdoBuildMachiya.cs

町屋の表店の run — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは EdoBuild の関数だけ」)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `ShopModule`(struct) | — | | 表店の駒の寸法(ES 倍・ピボットからの片寄せ込み)。 | |
| `ShopPiece`(struct) | — | | 表店の駒 1 種 = パス+倍率。⭐ 測る倍率と置く倍率を分けて持てない形にした — edogoyomi は ES 倍、 当方で起こした駒は実寸(1 倍)で、片方だけ取り違えると 1.8 倍(または 0.55 倍)の町屋… | |
| `EdoBuild.EdgeDepth(poly, A, B, outward)` | `float` | 硬 区域 | 辺の背後に実際に何 m あるか。辺の上の 9 点から敷地の内へ歩いて、区画の外へ出るまでの 距離の中央値。 | — |
| `EdoBuild.ShopMeasure(path)` | `ShopModule` |  | 在庫の edogoyomi の駒(ES 倍で使う物)を測る。 | TypologyBuilder.Machiya(Machiya) |
| `EdoBuild.OwnMeasure(path)` | `ShopModule` |  | 当方で起こした駒(実寸で使う物 = 倍率 1)を測る。 | TypologyBuilder.Machiya(UraNagaya) |
| `EdoBuild.ModuleMeasure(path, scale)` | `ShopModule` |  | 駒を scale 倍・無回転で仮置きして軒と躯体の走り・奥行を測る。 | — |
| `MachiyaTally`(struct) | — | | 表店の run が何を建てたか。⛔ 呼び手は必ず全部刷る(規則19)— とくに wantHouses と houses の差は「5間の駒が無い」ことの実測の現れで、 黙って飲むと在庫の宿題(EDO-0318 ④)が見えな… | |
| `EdoBuild.TileWidths(target, widths, joint, res=…)` | `int[]` |  | 列の残り長さを、繰り返し使える棟の実寸の組合せで埋める計画(掲示板 EDO-0362 §1d の型)。 | — |
| `EdoBuild.MachiyaRun(parent, A, B, outward, baseY, maguchiM, maxDepthM, gapC, gapHalf, prefix, leadPath, ours, keepInside, avoid, tally)` | `List<GameObject>` | 硬 面・区域 | <summary>表店の列。辺 A→B に、通りへ店先を向けた町屋を軒を接して並べる。 | TypologyBuilder.Machiya(Machiya) |
| `EdoBuild.UraNagayaRun(parent, A, B, outward, baseY, insetM, cap, prefix, keepInside, avoid, dropped, wallGap, gapM, munewari=…)` | `List<GameObject>` | 床 | <summary>裏長屋(裏店)の列。表店の列の背後に、路地を挟んで棟を並べる。 | TypologyBuilder.Machiya(UraNagaya) |

## EdoBuildMuki.cs

向き(正面)の解き — EdoBuild の partial (2026-09-22・EDO-0261 ③)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.DirDeg(compass, deg)` | `bool` |  | 方位の語 → 真北からの角[°・上から見て時計回り]。 | — |
| `EdoBuild.LocalAxisDeg(axis, deg)` | `bool` |  | 部材のローカル軸の綴り → 真北からの角[°](Unity の Y 回転 0 のとき。 | — |
| `EdoBuild.FaceYaw(front, localFront, yaw)` | `bool` |  | 正面を向ける yaw[°]。front = 図が宣言する正面の方位(東/西/南/北…)、 localFront = 部材が宣言する「正面はローカルのどの軸か」(+X / +Z …)。 | SannoSha(Muki・Stage5_MonTorii・ToriiFromMune…) |
| `EdoBuild.FaceYaw(front, localFront, frameDeg, yaw)` | `bool` |  | 回した枠の上の正面を向ける yaw[°]。 | SannoSha(Muki・Stage5_MonTorii・ToriiFromMune…) |
| `EdoBuild.DirVec(compass, frameDeg, v)` | `bool` |  | 回した枠の上の方位の語 → 世界の単位ベクトル(FaceYaw と同じ枠の回り[°・時計回り]を足す)。 | SannoSashizuCheck(Check), SannoSha(ToriiFromMune) |
| `EdoBuild.BomFrontAxis(bom, row, label, name, partPath)` | `string` |  | 部材の「正面はローカルのどの軸か」を指図から引く(2026-09-24・EDO-0430)。 | SannoSha(FrontAxisOf) |
| `EdoBuild.DirVec(compass, v)` | `bool` |  | 方位の語 → 世界の単位ベクトル(XZ 平面。 | SannoSashizuCheck(Check), SannoSha(ToriiFromMune) |

## EdoBuildNiwa.cs

庭の置き方 — 類型の庭(Stage 5・EDO-0323)が使う「置く・測る・据える」だけ。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.Seed(s)` | `int` | 区域 | 文字列から版を跨いで同じ乱数の種を作る。 | TypologyBuilder.Niwa(Niwa) |
| `EdoBuild.PartSize(path)` | `Vector3` |  | 部材の実メッシュの外形(scale=1・yaw=0 の Renderer bounds の大きさ)。 | — |
| `EdoBuild.CrownR(path)` | `float` |  | 樹冠(や駒)の平面の半径[m] — 実メッシュの XZ の大きい方の半分(scale=1 のとき)。 | TypologyBuilder.Niwa(MaxCrown・NiwaIdo・NiwaToro…) |
| `NiwaOcc`(class) | — | | 実メッシュの標本を 1m の升へ撒いて、「この点から一番近い実メッシュまで何 m か」を 打ち切り付きで返す。 | |
| `EdoBuild.NiwaGateOpening(mon, along, centerProj)` | `float` | 区域 | 門の通り抜けの実開口を実メッシュから測る[m]。 | TypologyBuilder.Niwa(SandoAxis) |
| `EdoBuild.GateClearance(go, gateC, withRoof=…)` | `float` | 地面 | 門の芯 gateC から駒の実外形までの水平の離れ[m](外形の中なら 0)。 | Typology(Omoya) |
| `NiwaSet`(struct) | — | | 据えるときの作法ひと組。 ⭐ 囲いからの離れは「幹の芯」で、軒からの離れは「樹冠の外接円」で測る(庭方 2026-09-22 の検分⑧)。 | |
| `NiwaKoma`(struct) | — | | 据えた駒ひとつ。⭐ 実メッシュで測り直した樹冠の半径 r(外接円の中心 c)と 地際から測った幹の芯 trunk を両方持つ — 囲いは幹で、軒は樹冠で検めるため(検分⑧)。 | |
| `EdoBuild.NiwaTrunk(go, c, maxSamples=…)` | `bool` |  | 駒の地際(実メッシュの底から「丈の12%か0.30mの厚い方」の帯)に入る頂点の重心 = 幹の芯。 | — |
| `NiwaField`(class) | — | | 庭の地 — 「どこに置けるか」を実メッシュから解いて持つ。 | |
| `EdoBuild.NiwaClump(parent, prefix, f, center, palette, n, rnd, o, layer, pick=…)` | `List<GameObject>` |  | 塊をひと組据える。⭐ 本数は必ず奇数・外形は不等辺・乱れは4つ全部(§5-0)。 ⟶ 返す: 据わった駒 | TypologyBuilder.Niwa(Layer・NiwaChisen・NiwaIshigumi…) |
| `EdoBuild.NiwaWallBandSites(f, lo, hi, k, rnd, skip, fromWall, blind)` | `List<Vector2>` | 区域 | 散らしではなく帯。周長を k 等分した箇所から内へ歩き、 囲い・長屋の実メッシュからの距離が lo〜hi に入る点を返す。 | TypologyBuilder.Niwa(NiwaChisen・NiwaTsubo) |
| `EdoBuild.NiwaStepPitch(stoneLong, rnd)` | `float` |  | 飛石の芯々[m] = 石の長軸 × 1.05〜1.25(検分①)。 | TypologyBuilder.Niwa(NiwaTobiishi・NiwaUra) |
| `EdoBuild.NiwaStepWay(start, dir0, total, rnd)` | `List<Vector2>` |  | 飛石の経路。起点から dir0 の向きへ、折れ2箇所・各15〜40°で 総長 total の折れ線を引く(検分①)。 | TypologyBuilder.Niwa(NiwaTobiishi) |
| `EdoBuild.NiwaStepAim(f, start, n0, halfDeg, total, pitch, r, o)` | `Vector2` |  | 飛石の出だしの向きを測って決める。n0 から ±halfDeg を 10°刻みで当たり、その向きへ芯々ごとに置いたときいちばん多く据わる向きを採る。 | TypologyBuilder.Niwa(NiwaTobiishi) |
| `EdoBuild.NiwaWalk(way, s, p, dir)` | `bool` |  | 折れ線に沿った位置 s[m] の点と向き。 | — |
| `EdoBuild.NiwaStepPath(parent, prefix, f, way, palette, n, rnd, stoneLong, o, layer, pitch)` | `List<GameObject>` | 天端 | 飛石1条。way の折れ線に沿って、芯々を石の実寸から出して並べる (⛔ 2〜3m 間隔で置かない — 歩幅の石である)。 | TypologyBuilder.Niwa(NiwaTobiishi・NiwaUra) |
| `EdoBuild.NiwaPocket(f, lo, hi, minCells)` | `List<Vector2>` |  | 庭域の格子点のうち、軒からの距離が lo〜hi の 最大連結成分(坪庭のポケット)。 | TypologyBuilder.Niwa(NiwaTsubo) |
| `EdoBuild.NiwaBlob(f, subset, minCells)` | `List<Vector2>` |  | 格子点の部分集合の最大連結成分(8近傍)。 | TypologyBuilder.Niwa(NiwaChisen) |
| `EdoBuild.NiwaVoidPoly(c, longR, rnd)` | `Vector2[]` |  | 不定形の空地の輪郭(池代地)。⛔ 円・楕円にしない(§5-1 chisen ③)。 | TypologyBuilder.Niwa(NiwaChisen) |

## EdoBuildNozura.cs

野面の乱積みの土留めを一本の折れ線へ据える — EdoBuild の partial(2026-09-25・EDO-0430)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `NozuraWall`(class) | — | | 野面の土留めの一本(隅と段の境で折れ・継ぐ)。 | |
| `EdoBuild.PlaceNozuraRun(w, groundAt, probe, parent, name, log)` | `List<KeyValuePair<GameObject, Vector2>>` | 地面・駒どうし・天端・床・面・隅 | 野面の乱積みの土留めを据える(2026-09-25・EDO-0430)。 ⟶ 返す: 据えた駒と見え面の向き | — |
| `EdoBuild.RayToBodies(bodies, o, d, maxDist)` | `float` | 駒どうし・面 | 走りの端を相手の駒の実面まで延ばす(2026-09-25・EDO-0430)。 | — |
| `EdoBuild.ReachToBodies(from, toward, bodies, halfT, yLo, yHi, maxReach)` | `float` |  | ⚠ 注釈なし | SannoSha(SakuRun・ShiftRunToCutShoulder) |
| `EdoBuild.RetractEndFromBodies(end, inward, bodies, halfT, yLo, yHi, maxBack)` | `float` | 硬 駒どうし・面・隅 | 走りの端が相手の駒の中に在るなら、相手の実面まで詰める(ReachToBodies の逆向き・2026-09-26・EDO-0430)。 | SannoSha(RetractRunEndsFromWalls) |
| `EdoBuild.RetractEndToBedEdge(end, inward, beds, halfT, yTop, maxBack, groundAt)` | `float` | 硬 地面・駒どうし・天端・床 | 受けの駒の天端の上に立つ走りの端を、受けの駒が足の下に在る所まで詰める(2026-09-26・EDO-0437 第6巡)。 | SannoSha(RetractRunEndsFromWalls) |
| `EdoBuild.BedTopAt(p, beds, yTop)` | `float` |  | 点 p の真上から下ろした光線が beds の上向きの面に最初に当たる高さ(当たらなければ NaN)。 | SannoSha(AbutStairsToWalls・RetractRunEndsFromWalls・Stage4_Kakoi) |
| `EdoBuild.SoilSideCrestShort(g, faces, soilAt, at)` | `float` | 地面・天端・面 | 土の側(背)の天端の足りなさ(2026-09-25・EDO-0430)。 | — |
| `EdoBuild.SOIL_SIDE` | `float` | 天端 | 背の帯の奥行[m]。皮は周り 0.5m(CAPR 2 × 0.25)の天端で下げるので、同じだけ見る。 | — |

### 野面の土留めの網(2026-09-26・EDO-0437)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `NozuraSeg`(class) | — | | 野面の土留めの一区間(直線)。指図の run を口(石段の口)で割った一本ずつ。 | |
| `EdoBuild.PlaceNozuraNet(segs, groundAt, faceGroundAt, probe, parent, straight, kado, dan, kiri, mikiriPath, heights, pool, log, kiriEnd=…, noriEnd=…, kadoAbut=…)` | `List<KeyValuePair<GameObject, Vector2>>` | 地面・駒どうし・面・隅 | 野面の土留めの網を据える(2026-09-26・EDO-0437)。 ⟶ 返す: 据えた駒と見え面の向き(駒の名は据わった区間の名) | SannoSha(Nozura) |
| `EdoBuild.PlaceNozuraMikiri(pathOfH, edge, toward, face, footY, crestY, partners, parent, name, log, soilAt=…)` | `GameObject` | 天端・床・面 | 口の縁の見切り石を据える(2026-09-26・EDO-0437)。 | — |

## EdoBuildOsameru.cs

寄せて測るを収まるまで回す (EdoBuild の partial・2026-09-26・EDO-0454)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Tori`(class) | — | | 取り合い一つ。「残り」(0 が狙い・単位 m)を測る手と、一手寄せる手の組。 | |
| `Osamari`(class) | — | | Converge の結果。Ok と Reason だけ読めば次の手が決まる。 | |
| `EdoBuild.Converge(toris, maxRounds=…, stall=…)` | `Osamari` | 硬 | 寄せて測るを収まるまで回す。toris を渡した順に寄せ(帯の中の物は動かさない)、 巡ごとに全部を測り直す。 ⟶ 返す: 合否・理由・取り合いごとの前後の残り・最悪値 | — |
| `EdoBuild.AbutAndSeat(mover, other, dir, gap=…, sink=…, maxSamples=…, maxRounds=…)` | `Osamari` | 地面・駒どうし | 一つの駒を「相手へ突き付け → 地面に据える」で納める近道(番所→門・袖塀→番所 の型)。 | Typology(BuildParcel) |

## EdoBuildRun.cs

囲いの run — 長屋・土塀・板塀を辺に沿って並べる (EdoBuild の partial・2026-09-21)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.CutShoulder(toe, outward, floorY, batter, natural, maxDist=…, step=…)` | `float` | 地面 | 切土の法の法肩までの水平距離(2026-09-26・EDO-0437)。 | SannoSha(ShiftRunToCutShoulder) |
| `EdoBuild.ShoulderLevelEnd(toe0, along, outward, floorY, batter, natural, maxD, eps, profile=…, drawn=…)` | `float` | 駒どうし | 法肩の線が下り始める所(2026-09-26・EDO-0437 第6巡)。 | SannoSha(ShiftRunToCutShoulder) |
| `EdoBuild.NaturalMode` | `bool` | 地面 | 自然地形モード: true なら造成せず、駒は一枚ずつ地面へ据える。 | — |
| `NagModule`(struct) | — | | 部材の壁実寸(走り方向)。edogoyomi knagaya の壁 = n_wall/namako/n_dodai。 | |
| `EdoBuild.NagayaMeasure(path)` | `NagModule` |  | 部材をES倍で仮置きして壁(wall/namako/dodai)のローカルX実寸を測る。 | — |
| `EdoBuild.NagayaRun(parent, A, B, outward, baseY, gapC, gapHalf, prefix, keepInside=…)` | `List<GameObject>` | 駒どうし・床・区域 | 実寸カーソル方式(2026-08-26 Phase 4a 統一・ユーザー承認済み)。 | Sanyashiki(S3_Enclosure), Typology(BuildParcel), Yamato(Y2_Enclosure) |
| `RunModule`(struct) | — | | 部材の走り方向(ローカルX)の実寸。倍率1・回転なしで仮置きして頂点から測る(NagayaMeasure の塀版)。 | |
| `EdoBuild.RunMeasure(path)` | `RunModule` |  | ⚠ 注釈なし | — |
| `RunHeightM`(struct) | — | | 部材のローカル Y の実寸。根入れ(原点より下にある分)と丈の中ほどを取るために測る。 | |
| `EdoBuild.RunMeasureY(path)` | `RunHeightM` |  | 部材のローカル Y の実寸を測る(結果は綴りごとに憶える)。 | SannoSha(SakuRun) |
| `EdoBuild.MidSection(go)` | `List<Vector3>` | 断面 | 据わった駒を、その駒自身の丈の中ほど(継ぎ目の高さ)で切った断面(世界座標)。 | SannoSashizuCheck(Check) |
| `EdoBuild.PolylineParam(poly, p, s, lat, ext=…)` | `void` |  | 折れ線 poly(xz)の上で点 p に最も近い所の 道のり s と符号付きの横のずれ lat(走りの左が +)。 | SannoSashizuCheck(Check) |
| `EdoBuild.GroundPolyline(a, b, span, floatMax, buryMax, smooth=…)` | `List<Vector3>` | 地面 | 地表なりの折れ線へ割る。辺 a→b を、描かれている地表に沿った実長(道のり)で span ごとに割り、継ぎ目の点(世界座標・高さは地表)を返す。 | SannoSha(SakuRun) |
| `EdoBuild.SplitAtBedSteps(a, b, heightAt, jump, res=…, minLen=…)` | `List<Vector2[]>` | 天端・床 | 走りを床の段(鉛直の落ち)で割る(2026-09-26・EDO-0430 山王 `Ita_Keidai` の柵 × 御供所の郭の土留め)。 | SannoSha(SakuRun) |
| `EdoBuild.PlaceOnChord(path, j0, j1, parent, name)` | `GameObject` |  | 弦に沿って駒を据える。継ぎ目 j0→j1 に張るよう、 yaw = 走り・roll = 弦の勾配・走り方向の伸縮 = 弦の実長(斜距離)で置く。 | SannoSha(SakuRun) |
| `EdoBuild.DobeiRun(parent, A, B, outward, prefix, followGround, flatBase, gapC, gapHalf)` | `List<GameObject>` | 駒どうし | 走り方向: 区間を pitch に等分し、駒の実寸(RunMeasure)を pitch へ伸縮して、前の駒の実測の端へ突き付ける。 | SannoSha(Stage1_Keidai・Stage2_Sando), Doi(Stage2_Perimeter), MatsudairaDewa(Stage2_Perimeter), OkabeYashiki(Stage2_Perimeter), Sanyashiki(S3_Enclosure) ほか1 |
| `EdoBuild.NeribeiRun(parent, A, B, outward, prefix, followGround, flatBase, gapC, gapHalf)` | `List<GameObject>` | 隅・区域 | DobeiRun(表裏2枚の板塀)と違い Dobei2m は1駒で厚みを持つ一体物なので、side ループは無い。 | — |
| `EdoBuild.PanelRun(parent, A, B, outward, prefix, assetPath, gapC, gapHalf, pair=…, unitScale=…, beds=…, bedAt=…, splitPost=…, splitBoard=…)` | `List<GameObject>` |  | <remarks>据えは DobeiRun と同じ — 触れている箇所を測る(規則21)。 | SannoSha(Stage4_Kakoi) |
| `EdoBuild.PostBoardRun(parent, A, B, outward, prefix, postPath, boardPath, bedAt, root, pair=…)` | `List<GameObject>` | 駒どうし・床・断面 | 柱と板を分けた組で板塀の run を張る(2026-09-26・EDO-0437 第7巡)。 | — |
| `EdoBuild.SeatPanelOnBed(go, A, dir, mn, mx, bedAt, root)` | `void` | 地面・床 | 板塀の駒を描かれた地表の弦に張って据える(2026-09-26・EDO-0437 第5巡)。 | — |
| `EdoBuild.RestOnBeds(go, beds)` | `float` | 地面・天端・床 | 駒の足の下に在る受けの駒(土留め・石垣)の天端に載せる(2026-09-26・EDO-0437 第3巡)。 ⟶ 返す: 上げた量(0 = 動かさない) | — |
| `EdoBuild.FenceRun(parent, A, B, outward, kind, baseY, gapC, gapHalf, prefix, note)` | `List<GameObject>` |  | 辺 A→B に種別どおりの囲いを建てる。 | Typology(BuildParcel) |
| `EdoBuild.KuiRun(parent, A, B, outward, prefix, gapC, gapHalf, pitchKen, dias, label, note)` | `List<GameObject>` | 地面 | 杭列(傍示杭・杭)。⛔ 連続の塀にしない — 間を空けて立てる。 | — |

## EdoBuildSeiyaku.cs

制約の二種 — 硬い制約(関門)と柔らかい制約(狙い)を、置く側の共通の層で使い分ける(EDO-0372・施主 2026-09-23)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Hard`(class) | — | | 硬い制約。ok(駒) が false の置き場は退ける。 | |
| `Soft`(class) | — | | 柔らかい制約。measure(駒) が Target 以上なら満たす(大きいほど良い物だけを書く)。 | |
| `SeiyakuTally`(class) | — | | 制約ごとの勘定。邸ビルダーの log へそのまま刷る(規則19)。 | |
| `EdoBuild.PlaceBest(spots, maxTries, place, hards, softs, tally)` | `GameObject` | 硬・柔 | 置き場の候補を順に試し、硬い制約で退け・柔らかい制約で選ぶ。 | Typology(Omoya) |

## EdoBuildSueru.cs

埋め込む駒・差し込む駒・載せる駒を据える (EdoBuild の partial・2026-09-23・EDO-0274)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.BodyOfMat(tr, mat)` | `List<Vector3>` |  | 材(サブメッシュの材質名)で絞った、駒の世界頂点。 | — |
| `EdoBuild.Section(tr, y, mat=…)` | `List<Vector3>` | 断面 | 実体化した駒の水平断面(高さ y で三角形を切った交点・世界座標)。 | SannoSashizuCheck(Check) |
| `EdoBuild.ContactPts(pa, pb, dir, at, count, tol=…, cell=…)` | `float` | 面 | 二つの頂点の集まりが触れている箇所(Contact の中身)。 ⟶ 返す: 最小の隙(負 = めり込み)・NaN = 向き合っていない | — |
| `EdoBuild.RestGap(mover, moverMat, bed, bedMat, at, count, tol=…)` | `float` | 天端・床 | 載る駒と受ける駒が鉛直に触れている箇所(材で絞る・null で全材)。 ⟶ 返す: 最小の隙[m](負 = めり込み・NaN = 上下に重ならない)、 at = その所、count = 最小から tol 以内の点の数 | — |
| `EdoBuild.RestOn(mover, moverMat, bed, bedMat, gap, at, count)` | `float` | 床 | 受けの上に載せる。RestGap が gap(0 = 接触)になる高さへ 鉛直に動かす。 ⟶ 返す: 動かした量[m](上下に重ならなければ NaN で動かさない) | SannoSha(Stage8_Ido) |
| `EdoBuild.FlushGap(go, mat, rise, at, count, cell=…, tol=…)` | `float` | 地面・天端 | 天端を地表に揃えて埋める駒の、天端と地表の差。 ⟶ 返す: 最小(負 = 天端が土に埋まっている)、 rise = 最大(天端が地表から出ている量) | SannoSha(Stage8_Ido) |
| `EdoBuild.SeatFlush(go, mat, proud, rise, cell=…)` | `float` | 地面・天端 | 天端を地表に揃えて埋める。FlushGap の最小が proud (+ = 地表から出す量・0 = 面一)になる高さへ動かす。 ⟶ 返す: 動かした量[m] | SannoSha(Stage8_Ido) |
| `EdoBuild.CenterInOpening(plug, plugMat, socket, socketMat, y, margin, clearMin, clearMax)` | `Vector2` | 床・断面 | 差す駒を相手の穴へ芯出しする。高さ y で、差す駒(材 plugMat)の 断面の外周と、受ける駒(材 socketMat)の断面のうち差す駒の外周から margin 以内にある物(= 穴の壁)を取り、両方の外形の中点を… ⟶ 返す: 動かした量(XZ・測れなければ NaN で動かさない) | SannoSha(Stage8_Ido) |
| `EdoBuild.CenterOnBed(mover, moverMat, yMover, bed, bedMat, yBed, reach, worstFoot)` | `Vector2` | 床・断面 | 足(柱)を受け(礎石)へ芯出しする。載る駒(材 moverMat)の高さ yMover の 断面(= 足の実形)と、受ける駒(材 bedMat)の高さ yBed の断面のうち 足の外形から reach 以内の物(= 受け… ⟶ 返す: 動かした量(XZ・測れなければ NaN で動かさない) | SannoSha(Stage8_Ido) |

### 駒の下の地形(2026-09-23・EDO-0274)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.HullOfMat(tr, mat=…)` | `Vector2[]` |  | 駒(材 mat・null で全材)の実メッシュの平面の外形(XZ の凸包・世界座標)。 | SannoSashizuCheck(Check), SannoSha(Stage8_Ido) |
| `EdoBuild.OpeningOf(tr, mat, y, n=…)` | `Vector2[]` | 断面 | 筒の口(輪になった駒の内周)を高さ y の断面から採る。 | SannoSha(Stage8_Ido) |
| `TerrainCells`(struct) | — | | 地形のセル範囲の報告。 | |
| `EdoBuild.ClearDetailIn(poly, cellOk=…)` | `TerrainCells` |  | 多角形に少しでも掛かる detail のセルを空にする(全層)。 ⟶ 返す: 掛かったセルと値の変わったセル | SannoSha(Stage8_Ido) |
| `EdoBuild.CutHole(opening, covers, why, joint=…)` | `TerrainCells` | 地面・駒どうし | 口の下の地形に穴を開ける(TerrainData の holes)。 | SannoSha(Stage8_Ido) |
| `EdoBuild.FillHoles(cells)` | `int` |  | CutHole で抜いた範囲を塞ぐ(据え直しの前に)。 ⟶ 返す: 塞いだセルの数 | — |

### 天端の下の地形(2026-09-23・EDO-0414)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `CrestTuck`(struct) | — | | TuckUnderCrest の報告。 | |
| `EdoBuild.TuckUnderCrest(pieces, mat, depth=…, minGap=…, inset=…, coTol=…, faces=…, measureOnly=…, crestBand=…)` | `CrestTuck` | 硬・柔 地面・天端・面 | 天端を地表と同じ高さに据えた駒の下の地形を納める。 | SannoSha(HifuMeasure・Stage2_Kaidan・Stage3_Dodome) |

## EdoBuildUeru.cs

植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.SeatPlant(go, sink, bury, flt, buryMax=…, floatMax=…, footBand=…, maxSamples=…)` | `bool` | 地面 | 植木を足元の当たりで据える。戻り値 = 埋没 ≤ buryMax かつ 根元の浮き ≤ floatMax で据わったか。 ⟶ 返す: 埋没 ≤ buryMax かつ 根元の浮き ≤ floatMax で据わったか | — |
| `EdoBuild.TrunkFootBand` | `float` | 地面・断面 | ── 幹の足(2026-09-25・EDO-0409)────────────────────────────────────────────── ⭐ 何が足りなかったか: 社叢の木は点へピボットを置いていた(⛔ 規則2… | — |
| `EdoBuild.Lod0Filters(root)` | `List<MeshFilter>` |  | LOD0 の MeshFilter(LODGroup が無ければ見えている全部)。 | — |
| `EdoBuild.Lod0PointsRootFrame(root)` | `List<Vector3>` |  | LOD0 の全頂点を「ルートの回転と位置を外した枠」(= 世界の m・ルートの向き)で。 | AssetCatalog(MeasureTree) |
| `EdoBuild.TrunkFootSlab` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.TrunkFootOf(root, foot, yFoot)` | `bool` |  | 幹の足の中心(ルートの枠の xz)と足元の高さ(y = LOD0 全頂点の最下)。 | AssetCatalog(MeasureTree) |
| `EdoBuild.CutGroupNearest(cut, seed, link)` | `Rect` | 断面 | 断面の切り口の点を link で繋いだ群のうち、seed に最も近い点を含む群の外接矩形。 | — |
| `EdoBuild.TrunkFootLocal(prefabPath)` | `Vector2` |  | 部材の幹の足の中心(部材の局所 xz・scale 1・m)。 | SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TrunkFootLocal(prefab)` | `Vector2` |  | ⚠ 注釈なし | SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TreePivotForTrunk(point, footLocal, widthScale, rotationRad)` | `Vector2` | 地面 | 地形の木(TreeInstance)のピボットの世界 xz = 点 − R(rotation)·(幹の足 × widthScale)。 | SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TrunkFootWorld(go, foot)` | `bool` |  | 据えた木の幹の足の中心(世界)。傾き・scale は据えたとおり(帯は上向きに 0.3m)。 | — |
| `EdoBuild.SeatPlantAt(go, trunkXZ, sink, bury, flt, buryMax=…, floatMax=…)` | `bool` |  | 幹の足の中心を trunkXZ へ寄せてから SeatPlant で据える。 | SannoSha(Stage7_Shaso) |

## EdoGeom.cs

純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoGeom.PIP(poly, p)` | `bool` |  | point-in-polygon (偶奇則)。 | DoiBuilder.Niwa(EditNiwaHeights・InWater・PondOverlapsCell…), SannoSha(InUngradedParcel・Nozura・ShiftRunToCutShoulder…), Doi(GradeQA・ParcelOutQA・PointInPoly…), MatsudairaDewa(GradeQA・Stage1_Grade・Stage7_Niwa…), OkabeYashiki(GradeQA・ImplQA・PaintSplat…) ほか8 |
| `EdoGeom.SignedArea(poly)` | `float` |  | 符号付き面積。CCW で正。 | — |
| `EdoGeom.InwardNormal(poly, i)` | `Vector2` |  | 辺 i (poly[i]→poly[i+1]) の、多角形の内側を向く単位法線。 | GotenTypoTest(Build), OkabeYashiki(OutNormal), Typology(Outward), TypologyBuilder.Jisha(JishaOmoya) |
| `EdoGeom.DistToEdge(p, a, b)` | `float` | 区域 | 点 p から線分 ab への最短距離。 ⚠ 長さ0の線分では NaN を返してはいけない。 | TypologyBuilder.Niwa(NiwaChisen・NiwaTsubo), SannoSha(Stage4_Kakoi), Typology(FenceFace) |
| `EdoGeom.DistToPolyEdge(poly, p)` | `float` |  | 点 p から多角形の外周(全辺)への最短距離。 | Typology(Candidates・Inner・Omoya…), TypologyBuilder.Jisha(JInside・JMinEdge・JishaOmoya), TypologyBuilder.Niwa(NiwaChisen・NiwaUra), SannoSashizuCheck(Check) |
| `EdoGeom.HullXZ(pts)` | `int[]` | 区域 | 点集合の凸包の頂点インデックス(反時計回り・共線点は落とす)。 | — |

## EdoParcels.cs

町割(敷地割)の正典 — docs/Sashizu/parcels.json

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoParcels.RelPath` | `string` |  | ⚠ 注釈なし | — |
| `EdoParcels.TSUBO` | `float` |  | ⚠ 注釈なし | — |
| `EdoParcels.KEN` | `float` |  | ⚠ 注釈なし | — |
| `EdoParcels.Palette` | `Color[]` | 区域 | 区画の色。EdoSketch のパレットと揃える(下書きの色が意味を持つため)。 | — |
| `EdoParcels.Categories` | `string[]` | 区域 | 区画の種別。色ではなくこれで分類する(色は見やすさのための物)。 | — |
| `EdoParcels.CategoryLabel(c)` | `string` |  | ⚠ 注釈なし | ParcelWindow(Refresh) |
| `Parcel`(class) | — | | (注釈なし) | |
| `EdoParcels.Version` | `int` | 地面 | データが差し替わる/書き換わるたびに増える。 | — |
| `EdoParcels.Load()` | `void` |  | ⚠ 注釈なし | ParcelWindow(Refresh) |
| `EdoParcels.MarkDirty()` | `void` |  | ⚠ 注釈なし | ParcelTool(DeleteVertex・HandleInput・PopUndo…), ParcelWindow(FrameOn) |
| `EdoParcels.IsDirty` | `bool` |  | ⚠ 注釈なし | — |
| `EdoParcels.Save()` | `void` |  | ⚠ 注釈なし | ParcelTool(AutoSave・DrawHud・FinishDrawing…), ParcelWindow(FrameOn・Refresh) |
| `EdoParcels.Find(id)` | `Parcel` |  | ⚠ 注釈なし | ParcelTool(PopUndo), Typology(Edges) |
| `EdoParcels.Get(id)` | `Vector2[]` | 区域 | 区画のポリゴンを引く。無ければ 例外を投げずに null を返し、警告を出す (LoadAssetAtPath と同じ作法。 | SannoSha(InUngradedParcel・Stage1_Grade・Stage7_Shaso…), Doi(In・KomonIshigakiQA), Typology(BuildParcel・Edges・Pad), OkabeYashiki(C), SurfacePaint(Paint・Verify) ほか5 |
| `EdoParcels.GetByPrefix(prefix)` | `List<Vector2[]>` | 区域 | json に無ければ fallback を返す。 | SannoSha(Stage6_Splat_Retired・Stage7_Keidairin) |
| `EdoParcels.GetOr(id, fallback)` | `Vector2[]` |  | ⚠ 注釈なし | — |
| `EdoParcels.Add(id, label, category, color, pts)` | `Parcel` |  | ⚠ 注釈なし | ParcelTool(FinishDrawing), ParcelWindow(FrameOn) |
| `EdoParcels.Remove(p)` | `void` |  | ⚠ 注釈なし | ParcelWindow(FrameOn) |
| `Harvested`(class) | — | | (注釈なし) | |
| `EdoParcels.HarvestFromBuilders()` | `List<Harvested>` |  | ⚠ 注釈なし | ParcelWindow(FrameOn) |
| `EdoParcels.DiffAgainstBuilders(tol=…)` | `string` | 区域 | 取り込み済みの区画と、いまのビルダーの配列を突き合わせる。 | ParcelWindow(Refresh) |
| `EdoParcels.MenuDiff()` | `void` |  | ⚠ 注釈なし | — |
| `EdoParcels.MenuReload()` | `void` |  | ⚠ 注釈なし | — |
| `EdoParcels.MenuSave()` | `void` |  | ⚠ 注釈なし | — |

