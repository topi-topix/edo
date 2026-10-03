# EdoBuild の据え方の関数の目録(生成物・手で直さない)

<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py · 指紋 07285e99ff20 -->

**据え方の関数を探すときは C# を grep で読み歩かず、まずここを引く。**置き方の手順と相手ごとの道具の選び方は
`docs/oki-kata.md`(正典)。ここは「どの関数が在り、何を返し、どこで使われているか」の索引だけ。

- 公開関数 303 本(注釈なし 25)。`Assets/Edo/Scripts/Editor/EdoBuild*.cs`・`EdoGeom.cs`・`EdoParcels.cs`(区画)の `///` 注釈から刷る。
- 同じ道具が刷る目録: 邸ビルダーのメニュー → Stage と中の関数 `docs/builder-mokuroku.md` / 部材の名 `docs/edoassets-mokuroku.md`。
- 札: **硬** = 注釈に「硬い/許容0」・**柔** = 「柔らかい/狙い」がある(判定ではなく注釈の語)。相手の札(地面・駒どうし・天端・床・断面・面・隅・区域)も注釈の語を拾っただけ。
- 呼んでいる所 = 定義のファイルの外で `EdoBuild.<名>(` と書いている C# ファイル(`Edo` と `Builder/Rebuild` を落とした名)と、その中の呼んでいる関数(Stage)。同じ名の多重定義はまとめて数える。`EdoBuild` の中どうしの呼び出しは載せない。
- 関数へ跳ぶ: `grep -n "static .* <名>(" Assets/Edo/Scripts/Editor/<ファイル>` → その行から読む。
- ⛔ 手で直さない。関数を足した・注釈を直したら `python3 Tools/Unity/edobuild_mokuroku.py` で刷り直し、C# と同じコミットに入れる。

## ファイルの索引

| ファイル | 何の道具か(ファイル冒頭の注釈) | 当たる先 | 関数 |
|---|---|---|---|
| [EdoBuild.cs](#edobuildcs) | 配置・資産系の共有基盤 (Phase 2c, 2026-08-26) | — | 46 |
| [EdoBuildGamae.cs](#edobuildgamaecs) | ══════════════════════════════════════════════════════════════════════ | — | 17 |
| [EdoBuildGoten.cs](#edobuildgotencs) | 御殿複合(表向・中奥・奥向の3核)を組む — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは | — | 3 |
| [EdoBuildHifu.cs](#edobuildhifucs) | 縁の皮 — 地形に穴を開け、穴の縁から部材の面までを皮のメッシュで描く (EdoBuild の partial・2026-09-24・EDO-0430) | 切通しの石段(山王の女坂・男坂・参道の階)・天端を地盤に揃えた土留め(山王・土井・岡部の郭)・ 造成した面の縁(全邸の段の縁)。 | 12 |
| [EdoBuildInari.cs](#edobuildinarics) | 稲荷 — 小祠と鳥居を据える (EdoBuild の partial・2026-09-21・EDO-0326) | — | 3 |
| [EdoBuildIshidan.cs](#edobuildishidancs) | 石段の組 — 段石と袖(袖石垣)を一組の材で据える(EDO-0415・2026-09-23 施主指摘)。 | — | 33 |
| [EdoBuildJisha.cs](#edobuildjishacs) | 寺社の本堂(と坊・社家の主屋)を、間数ごとに焼いた入母屋で組む — EdoBuild の一部(規則21)。 | — | 1 |
| [EdoBuildJun.cs](#edobuildjuncs) | 部材を依存の順に解き、変えた所から後だけ流し直す (EdoBuild の partial・2026-09-26・EDO-0455) | 山王社の建て直し(EdoSannoShaRebuild の Stage0〜9)。 | 0 |
| [EdoBuildKado.cs](#edobuildkadocs) | 隅部材(留め継ぎ)の据え — EdoBuild の partial (2026-09-21・EDO-0289 ②) | — | 30 |
| [EdoBuildKatte.cs](#edobuildkattecs) | 勝手まわり(菜園の畝・自然の斜面に据える踏み段)の置き方 — EdoBuild の partial(2026-10-03・EDO-0532 施主裁定A) | — | 6 |
| [EdoBuildMachiya.cs](#edobuildmachiyacs) | 町屋の表店の run — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは EdoBuild の関数だけ」)。 | — | 12 |
| [EdoBuildMichi.cs](#edobuildmichics) | EdoBuild — 道の造成(縦断を設計して道の面を均す)。2026-09-30・EDO-0495(施主裁定②「小道を造成する」)。 | 指図の道の欄に `zosei` を持つ道(今は山王の麓の道 南西区間 = 十坊の小道だけ)。 | 4 |
| [EdoBuildMuki.cs](#edobuildmukics) | 向き(正面)の解き — EdoBuild の partial (2026-09-22・EDO-0261 ③) | — | 7 |
| [EdoBuildNiwa.cs](#edobuildniwacs) | 庭の置き方 — 類型の庭(Stage 5・EDO-0323)が使う「置く・測る・据える」だけ。 | — | 16 |
| [EdoBuildNozura.cs](#edobuildnozuracs) | 野面の乱積みの土留めを一本の折れ線へ据える — EdoBuild の partial(2026-09-25・EDO-0430) | — | 9 |
| [EdoBuildOsameru.cs](#edobuildosamerucs) | 寄せて測るを収まるまで回す (EdoBuild の partial・2026-09-26・EDO-0454) | 類型ビルダーの番所→門(EdoTypologyBuilder Stage 1・2b)。 | 2 |
| [EdoBuildQueue.cs](#edobuildqueuecs) | EdoBuildQueue.cs — 長い建て直しを MCP の 1 回の呼び出しの中で回さず、エディタの中で順に予約して即座に返す(EDO-0503)。 | — | 0 |
| [EdoBuildRim.cs](#edobuildrimcs) | 崖の縁の土留め — 区画の線の上に立つ塀の真下を削って野面の石垣を積み、塀を天端に載せる (EdoBuild の partial・2026-09-28・EDO-0477) | 類型の全区画で、区画の縁の外が平場より高い所(崖の縁の寺社・武家の山際)。 | 6 |
| [EdoBuildRun.cs](#edobuildruncs) | 囲いの run — 長屋・土塀・板塀を辺に沿って並べる (EdoBuild の partial・2026-09-21) | — | 38 |
| [EdoBuildSeiyaku.cs](#edobuildseiyakucs) | 制約の二種 — 硬い制約(関門)と柔らかい制約(狙い)を、置く側の共通の層で使い分ける(EDO-0372・施主 2026-09-23)。 | — | 1 |
| [EdoBuildSueru.cs](#edobuildsuerucs) | 埋め込む駒・差し込む駒・載せる駒を据える (EdoBuild の partial・2026-09-23・EDO-0274) | 山王の前庭の井戸(板石敷・井筒+井桁・井戸屋形)。 | 16 |
| [EdoBuildSukima.cs](#edobuildsukimacs) | EdoBuildSukima.cs — 建物と隣の構造物の間の隙のうち、通りから裏手(敷地の内側)へ抜ける物だけを柵で塞ぐ(EDO-0503)。 | 類型ビルダーの町屋の囲い(表店の列の端・角・後ろの棟との間)── 町屋の全区画。 | 1 |
| [EdoBuildUeru.cs](#edobuilduerucs) | 植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401) | SeatPlant を呼ぶ所すべて(今は山王の社叢の下層と名指しの木 = Stage7_Shaso だけ)。 | 10 |
| [EdoBuildZosei.cs](#edobuildzoseics) | EdoBuild — 造成(平場を採る)。2026-09-27・EDO-0477 P1(山王 Stage1_Grade と松江松平 DesignY の型を、図を持たない区画へ)。 | 類型ビルダーで建てる全区画(武家・寺社・町屋・公有地)。 | 8 |
| [EdoGeom.cs](#edogeomcs) | 純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26) | — | 7 |
| [EdoParcels.cs](#edoparcelscs) | 町割(敷地割)の正典 — docs/Sashizu/parcels.json | — | 15 |

## EdoBuild.cs

配置・資産系の共有基盤 (Phase 2c, 2026-08-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.ES` | `float` |  | edogoyomi の倍率 = 江戸間 1 間 = 6 尺 (CLAUDE.md 座標系の表)。 | — |
| `EdoBuild.InvalidateTerrain()` | `void` |  | 掴んでいる Terrain を捨てる。⚠ Terrain を差し替えたのに古い物が active のまま残る 差し替え方をしたときだけ要る(active が落ちる差し替えなら T が自分で拾い直す)。 | — |
| `EdoBuild.T()` | `Terrain` |  | アクティブな Terrain (最初の1枚)。 | SannoSha(Stage2_Kaidan・Stage3_Dodome・Stage7_Shaso…), Shiomizaka(Z0_Restore・Z1_Grade・Z4_ReseatGate), SannoSashizuCheck(Check), Sanyashiki(S2_GradeEdges), TypologyBuilder.Niwa(PutIdo) ほか1 |
| `GroundProbe`(struct) | — | | 地表を何度も引くための掴み。Terrain と原点の y を一度だけ掴み、以後は `SampleHeight` だけを叩く。 | |
| `EdoBuild.Probe()` | `GroundProbe` | 地面 | 地表の引き手を一つ作る。GroundProbe を見よ。 | — |
| `EdoBuild.Ground(x, z)` | `float` |  | live terrain の標高 (m)。 | SannoSha(Ground・SodeFootAt・Stage5_MonTorii…), OkabeYashiki(PlaceFences・PlaceKekkai・PlaceNiwaItem…), Yamato(PadAt・PlanSegments・Y1_Grade…), Typology(GroundBed・GroundBedSpan・TuckBase), Sanyashiki(S2_GradeEdges・S3_Enclosure) ほか3 |
| `EdoBuild.Place(path, pos, ry, scale, parent, name)` | `GameObject` |  | プレハブを実体化して置く。パスは EdoAssets 経由で渡すこと (規則11)。 | OkabeYashiki(MeasureHeight・MeasureRunWidth・NaturalHeight…), SannoSha(Kairo・Place・SakuRun…), MatsudairaDewa(FenceWidth・ItabeiRun・Leaves…), Doi(LayGaki・PlaceFumiishi・PlaceKaidans…), DoiBuilder.Niwa(Niwa_B_Gogan・Niwa_C_Mizushiri・Niwa_D_Tenkei…) ほか6 |
| `EdoBuild.DressBare(go, path)` | `void` |  | 材に画像の無い在庫の駒へ、同じフォルダの画像を貼った材を着せる(EdoAssets.Eg.BareTex)。 | — |
| `EdoBuild.RB(go)` | `Bounds` |  | 子孫 Renderer 全体のワールド Bounds。 | SannoSha(AbutStairsToWalls・FaceFlushSegs・Kairo…), OkabeYashiki(MeasureHeight・NaturalHeight・PlaceBox…), MatsudairaDewa(ItabeiRun・ObbOverlapInBand・PlaceItabeiSpan…), Typology(BuildParcel・GamaeJointReport・Omoya…), Doi(Box・PlaceFumiishi・PlaceKaidans) ほか8 |
| `EdoBuild.SeatBottom(go, y)` | `void` |  | Bounds の底面を y に据える。 | OkabeYashiki(PlaceKekkai・PlaceNagayaPiece・PlaceNiwaItem…), Yamato(PlaceUV・UmayaPair・Y2_Enclosure), DoiBuilder.Niwa(Niwa_D_Tenkei・Niwa_F_Yashiro), Doi(PlaceService), MatsudairaDewa(Stage2_Perimeter) ほか2 |
| `EdoBuild.ObbFootprint(it, mnx, mxx, mnz, mxz, mny)` | `void` |  | it のローカル座標系での mesh 頂点 footprint (OBB)。 | OkabeYashiki(ObbWD・PlaceNagayaPiece) |

### 据え付けの技法(2026-09-20)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.IsRoofName(name)` | `bool` |  | 屋根系のメッシュ名か(yane / noki / taruki / mune / keta)。 | Assets(Bochi) |
| `EdoBuild.Body(tr, maxSamples=…, withRoof=…)` | `List<Vector3>` | 地面・面・隅・区域 | 壁体(屋根・軒・垂木・棟・桁を除く、見えているメッシュ)の頂点を世界座標で。 | SannoSha(AbutStairsToWalls・Nozura・Stage2_Kaidan), Typology(BuildParcel・OutsideBy), TypologyBuilder.Jisha(JEnclosureRoofs・JExt), Assets(Bochi), MatsudairaDewa(MeshBody) ほか3 |
| `EdoBuild.EdgeAlong(tr, ax, sgn)` | `float` |  | 駒の壁体の、世界軸 ax 方向の端の座標(sgn ≥ 0 なら最大側)。 | SannoSha(Stage8_Ido) |
| `EdoBuild.FaceSpan(go, dir, yLo, yHi, mn, mx, perpDir=…, origin=…, perpMax=…)` | `void` | 天端 | 高さの帯 [yLo, yHi] にある見えている頂点を、 走り方向 dir(xz)へ投影した min/max。 | MatsudairaDewa(ProjBand) |
| `EdoBuild.ProjSpan(go, dir)` | `float` | 面 | 駒の実メッシュ(見えている物だけ)を走り方向 dir(xz)へ投影した伸び[m]。 | TypologyBuilder.Niwa(Niwa・NiwaUra), MatsudairaDewa(ProjSpan), TypologyBuilder.Keidai(NiwaKeidai) |
| `EdoBuild.LocalSpan(tr, localAxis)` | `float` |  | 駒の壁体を、駒の局所軸 localAxis へ投影した伸び[m](世界の尺度)。 | — |
| `EdoBuild.Face(go, dir, yLo, yHi, maxSide, perpDir=…, origin=…, perpMax=…)` | `float` |  | FaceSpan の片側。maxSide なら dir の正の側の面。 | MatsudairaDewa(Stage5_Mon) |
| `EdoBuild.FaceOut(go, a, n, yLo, yHi, pick=…)` | `float` |  | 線(点 a・外向き法線 n)からの、帯内の頂点の最大の張り出し[m] (= その駒の外面の位置。 | OkabeYashiki(AlignInubashiri・FaceOut) |
| `EdoBuild.AlignFace(go, a, n, target, yLo, yHi, pick=…)` | `float` |  | 外面(FaceOut)が target へ来るよう、法線 n 方向に 平行移動する。 ⟶ 返す: 移動量[m](測れなければ NaN) | MatsudairaDewa(Stage5_Mon) |
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
| `EdoBuild.KeepInsidePoly(go, poly, runDir, maxPull, before, step=…, tol=…)` | `float` | 柔 駒どうし・隅・区域 | 壁体を区画の多角形の内へ収める。置いた駒の実メッシュ(屋根を除く)が poly の外へ出ていたら、走り runDir に沿って 最小量だけ引いて収める。 ⟶ 返す: 動かした量[m](+ は runDir 向き・0 = 元から内側) | OkabeYashiki(PlaceFences・PlaceIshigaki), MatsudairaDewa(Stage3_Ishigaki) |
| `EdoBuild.InsetRunToPoly(run, poly, inward, maxPush, before, step=…, tol=…, bandH=…)` | `float` | 硬 区域 | 硬い(許容0)・区域: 区画線の上に一列で据えた駒(柵・潜り戸など)を、列ごと同じ量だけ inward の向きへ引き、列のどの駒の実メッシュ(EdgeCandidates)も区画の外へ 出ない最小の量に納める。 ⟶ 返す: 引いた量[m](0 = 元から内側)、maxPush で収まらなければ 動かさず NaN | OkabeYashiki(PlaceFences・PlaceOmoteNagaya) |
| `EdoBuild.RetireOutsidePoly(group, poly, note, label, tol=…)` | `int` | 硬 区域 | 硬い(許容0)・区域: 群の直下の駒のうち、壁体(屋根を除く実頂点 BodyExRoof)が 区画の多角形の外へ出た物を退ける(消す)。 | OkabeYashiki(PlaceIshigaki・PlaceKuiretsu・PlaceTakegaki…) |
| `EdoBuild.GroundUnder(c, axisA, halfA, axisB, halfB, n, mn, mx)` | `void` | 地面 | 足あとの下の地形(格子点)の最小と最大。 | MatsudairaDewa(Stage6_Zosaku) |

### 隅の駒と塀の取り合い(2026-09-21)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.BodyAt(prefabPath, pos, yaw, withRoof=…)` | `List<Vector3>` |  | プレハブ資産を pos / yaw に据えたと仮定したときの 世界頂点。 | SannoSha(PanelProfile・SakuProfile・Stage3_Dodome), MatsudairaDewa(YaguraKeepout), TypologyBuilder.Rim(Rim) |
| `EdoBuild.SectionAt(prefabPath, pos, yaw, y, withRoof=…)` | `List<Vector3>` | 天端・床・断面 | 部材を据えたときの、高さ y の水平断面(世界座標・実体化しない)。 | TypologyBuilder.Rim(Rim) |
| `EdoBuild.IsRoofLabel(name)` | `bool` |  | 材やサブメッシュの名で屋根を見分ける。IsRoofName(和名)に 英名の roof / 屋根 を足したもの。 | — |
| `EdoBuild.BodyBelowRoofAt(prefabPath, pos, yaw)` | `List<Vector3>` |  | 一体メッシュの駒の「一層目の躯体」の世界頂点(実体化しない)。 | — |
| `EdoBuild.BodyExRoofAt(prefabPath, pos, yaw, bodyParts=…, roofParts=…)` | `List<Vector3>` | 区域 | 一体メッシュの駒の「躯体」全部(屋根の材を除いたすべての材)の世界頂点(実体化しない)。 | MatsudairaDewa(YaguraSeat) |
| `EdoBuild.BodyExRoof(tr, maxSamples=…)` | `List<Vector3>` |  | Body 相当だが、単一メッシュに焼かれた駒(庫裏・墓地・鐘楼・山門など、 Blender 側で屋根まで join した部材)も材(サブメッシュ)の名で屋根を見分けて落とす (BodyExRoofAt の、実体化済み T… | Typology(OutsideBy), TypologyBuilder.Jisha(JExt), TypologyBuilder.Keidai(NiwaKeidai) |
| `EdoBuild.CorridorSpan(pts, A, B, perpDir, perpLo, perpHi, yLo, yHi, s0, s1)` | `bool` | 地面・断面・隅 | 塀の通り道(回廊)を、その駒がどこからどこまで塞いでいるか。 | MatsudairaDewa(YaguraKeepout) |
| `EdoBuild.CorridorJambs(pts, A, B, perpDir, perpLo, perpHi, yLo, yHi, p0, p1, s0, s1)` | `bool` | 床 | 回廊を塞ぐ駒の「塞ぎ始め・塞ぎ終わりの点」(CorridorSpan の点版)。 | — |
| `EdoBuild.OpeningJambs(prefabPath, pos, yaw, A, B, perpHalf, yLo, yHi, bite, j0, j1, s0, s1, how)` | `bool` | 天端・床・断面 | 口に建つ駒(門)の脇柱へ、囲いの run の終端を取り付ける点を測る。 | SannoSha(ClipRunEndsToGates) |
| `EdoBuild.DobeiProfile(A, B, outward, seat, perpDir, perpLo, perpHi, yLo, yHi, outerAt=…, pad=…)` | `bool` | 断面 | その辺に建てる練塀の断面を、駒を1枚仮に据えて実測する。 | MatsudairaDewa(YaguraKeepout) |

## EdoBuildGamae.cs

══════════════════════════════════════════════════════════════════════

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.GATE_BURY_MAX` | `float` |  | 塀の端を門構えへ埋める量[m](§0a「埋めて隠す」・山王の勝手口の bite と同じ作法)。 | — |
| `EdoBuild.SpecOf(go)` | `EdoPartSpec.Spec` |  | 置いた駒の札(資産の道から引く)。札の無い駒は null。 | Typology(BuildParcel・GamaeJointReport・MichiInsideBy…), TypologyBuilder.Jisha(JishaOmoya), TypologyBuilder.Niwa(SandoAxis) |
| `EdoBuild.GroundOrBed(bed)` | `Func<float, float, float>` | 地面・床 | 床 = 地面と bed(縁と目地は 5cm 跨ぐ・BedIndex.AtNear)の高い方。 | Typology(BuildParcel・IsSueMono) |
| `EdoBuild.GamaeContact(piece)` | `Func<MeshFilter, bool>` | 地面 | 門構えの駒の地面との当たりの部材(札の contact)。 | Typology(BuildParcel・Inspect) |
| `EdoBuild.GamaeBottom(piece)` | `float` |  | 門構えの駒の当たりの下端[世界 y](GamaeContact の部材の最下点・無ければ外形の最下点)。 | — |
| `EdoBuild.SeatGamae(piece, verts)` | `void` | 硬 地面・床・区域 | 門構えの駒を地面へ据える(高さだけ)── 最下点で SeatOnGround した後、札に contact があれば その部材の当たり(RootToBed の最小 = 最も地面に近い所)を地面へ下ろす(外した飾りは根入れ… | Typology(SeatGamae) |
| `EdoBuild.FenceEndPiece(kind)` | `string` |  | 囲いの種別 → 門の脇に来る端の駒の資産(札を引く相手)。 | Typology(GamaeJointReport) |
| `EdoBuild.FenceOuterFace(kind, how)` | `float` | 区域 | 塀の外の面が区画の線からどれだけ外にあるか[m](走りの置き方の約束 × 端の駒の札)。 | Typology(BuildParcel) |
| `EdoBuild.FenceDepth(kind)` | `float` |  | 塀の本体の奥行[m](外の面から内の面まで・端の駒の札)。 | Typology(BuildParcel) |
| `EdoBuild.FenceBite(kind, nagayaTuck, how)` | `float` | 床 | 塀の端を門構えの脇の面からどれだけ門へ食い込ませて口を狭めるか[m]。 | Typology(BuildParcel) |
| `EdoBuild.STATION_END_CLEAR` | `float` | 硬・柔 区域 | 表の辺の上で、門構えの幅の中の道がいちばん平らな所(柔らかい: 狙い)を返す(2026-09-30 EDO-0491)。 | — |
| `EdoBuild.STATION_MOVE_RANGE` | `float` | 床 | 辺の中央で幅の中の道の高さの差がこれ以下なら中央に置く[m]【確度 U】── 差は基壇の布石(GamaeKidan)が受ける。 | — |
| `EdoBuild.FlattestStation(a, b, half, range, rangeMid)` | `Vector2` |  | ⚠ 注釈なし | Typology(BuildParcel) |
| `EdoBuild.HIRABA_BAND` | `float` |  | 平場の連なりを測る高さの幅[m](±)= 棟の系統差の許し(CLAUDE.md 規則3)と同じ。 | — |
| `EdoBuild.HirabaStation(a, b, inward, half, d0, depth, note)` | `Vector2` | 硬・柔 床・区域 | 門を、奥の自然の平場の真ん中の前に置く(柔らかい: 狙い・2026-10-03 EDO-0514 施主裁定 B「樹下の表門を平場の中央の前へ」)。 | Typology(BuildParcel) |
| `EdoBuild.KIDAN_FLOAT_TOL` | `float` | 地面・区域 | 門構えの基壇の布石の浮きの線[m] ── 超えれば布石を敷く。 | — |
| `EdoBuild.KIDAN_EMBED` | `float` | 硬 地面 | 基壇の布石の下端を地面へ入れる深さ[m](硬い)= 段塀の布石と同じ(DAN_STONE_EMBED)。 | — |
| `EdoBuild.KIDAN_BULGE` | `float` | 硬 地面・天端・床・区域 | 門構えの駒の下に布石の基壇を敷く(2026-09-30 EDO-0491・施主「門が浮いてます」)。 | — |
| `EdoBuild.KIDAN_SEAM` | `float` | 駒どうし・天端・床・区域 | 布石の区画どうしの天端の重ね[m] ── 天端の縁と縁を突き付けると、継ぎ目の一点で下の目地を床に読む(2026-09-30 十坊0 0.165m)。 | — |
| `EdoBuild.GamaeKidan(piece, parent, ground, note)` | `List<GameObject>` |  | ⚠ 注釈なし | Typology(BuildParcel) |
| `EdoBuild.BuildingKidan(piece, parent, ground, note)` | `List<GameObject>` | 硬 地面・天端・床・区域 | 棟の下手の浮きを布石の基壇で受ける(EDO-0503・2026-10-02 施主の規則「浮き 許容0」)。 | Typology(BuildParcel) |
| `EdoBuild.KIDAN_BITE` | `float` | 駒どうし・天端 | 棟の基壇の布石の天端を駒の下端より上げる量[m] ── 石の面のふくらみ・継ぎ目で下端の頂点が 0.013m 浮いて測れた (門前2 の shop01 4 棟・2026-10-02)。 | — |
| `EdoBuild.DodomeAlongEdge(a, b, outward, parent, name, minDrop, worst, keepInside=…)` | `List<GameObject>` | 地面・天端・床・区域 | 切土の縁の土留め(EDO-0503・考証【U】「表を道に揃え、背後を切って裏に土留」)。 | Typology(BuildParcel) |
| `Gamae`(class) | — | | 門構えを置いた結果。⭐ `passageC`(通り口の芯)と `gapC/gapHalf`(塀の口)を分けて持つ ── 番所が片方だけの門構えでは二つがずれる(⛔ 2026-09-29 まで一つの gateC が両方を兼… | |
| `EdoBuild.PlaceGamae(mon, bansho, A, B, outward, center, poly, faceOut, bite, fenceDepth)` | `Gamae` | 硬・柔 区域 | 門構えを札で置く(硬い: 札が無ければ例外 ── 呼ぶ側は ⛔ を刷ってその門構えを退ける)。 | Typology(BuildParcel) |
| `EdoBuild.DenseSection(tr, y, step=…)` | `List<Vector3>` | 断面 | 水平断面を線分として取り、step 刻みで点を埋める(世界座標)。 | — |
| `EdoBuild.GamaeFenceGap(fenceEnds, gamae, toward, how)` | `float` | 硬 断面 | 門構えと塀の取り合いの隙[m](検査の列・硬い ── 隙 &gt; 0.01 は ⛔・測れない NaN も ⛔)。 | Typology(GamaeJointReport) |

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
| `AtariBed`(class) | — | | 当たりの床 = 下端が接すると決めた相手の面だけを返す床。 | |
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
| `EdoBuild.SwapToFitted(pieces, fitPathOf, sb)` | `Dictionary<GameObject, GameObject>` | 駒どうし | 相手の石の形に沿わせて焼いた駒へ、据えを変えずに差し替える(2026-09-26・EDO-0437 第11巡)。 ⟶ 返す: 旧 → 新 | — |
| `EdoBuild.SwapWallsBesideStep(step, walls, fitPathOf, sb, reach=…)` | `Dictionary<GameObject, GameObject>` | 天端 | 段石の端に脇から接する土留めの駒を、その段に合わせて焼いた駒へ、据えを変えずに差し替える(2026-09-27・EDO-0437 r14)。 ⟶ 返す: 旧 → 新(呼び手は群の一覧を差し替える) | — |
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
| `EdoBuild.EndGapProfile(piece, dir, mates, yTop, gMin, gMax)` | `void` | 駒どうし・天端 | 駒の端と相手の面の取り合いを高さ方向に測る(EDO-0459)。 | — |
| `EdoBuild.LayFlatSode(old, below, pathOf, depths, up, mates, yBand, maxReach, rep, warn, flushTo=…)` | `GameObject` | 硬 駒どうし・天端 | 石段の袖の最上段の駒を、天端が水平な袖へ差し替えて相手の面まで伸ばす(EDO-0459 施主裁定A 2026-09-26)。 | SannoSha(Stage2_Kaidan・Stage5b_Fumiishi) |
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
| `EdoBuild.KadoGauge(path, armFull, faceDepth)` | `bool` | 隅 | 留め継ぎの隅部材の素の寸法を、焼いた FBX の実メッシュから測る(実体化しない・局所 = 据える前の部材の単位)。 | OkabeYashiki(PlaceKado) |
| `EdoBuild.KadoArms(poly, vertex, isKado, outNormal, scale, armFullLocal, faceDepthLocal, faceIn, bodyIn, stepLocal, minArm, armsLocal, note)` | `bool` | 硬 隅・区域 | 短い辺で隅部材の腕を選ぶ。頂点 vertex の隅の (入りの腕, 出の腕) を局所の長さで返す (`EdoAssets.Own.Kado(part, deg, armIn, armOut, armFull)` へそのま… | OkabeYashiki(PlaceKado) |
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
| `EdoBuild.SegOntoOuterFace(a, b, faceBodies, outward, offset, warn)` | `Vector2[]` | 駒どうし・面 | 区間の線を相手の駒の外の面(鉛直な面)の上へ移す(2026-09-27・EDO-0437 施主裁定「返しの見え面 = 袖の背の面」)。 ⟶ 返す: 区間を法線に沿って平行に移した [a', b'](測れなければ null) | SannoSha(FaceFlushSegs) |
| `EdoBuild.CutKadoArmsToFaces(kados, faces, cutPathOf, sb)` | `Dictionary<GameObject, GameObject>` | 硬 駒どうし・隅 | 隅の駒の腕が鉛直な相手の面の中へ入るなら、腕を相手の面で一辺だけ切った版へ差し替える(2026-09-27・EDO-0437 施主 「端の石は細くしない。 ⟶ 返す: 旧 → 新(差し替えた物だけ) | SannoSha(Nozura) |
| `EdoBuild.LineMeet(p, q, l0, l1)` | `Vector2` |  | 区間 p–q の直線と直線 l0–l1 の交点(平行なら NaN の点)。 | SannoSha(Nozura) |
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

## EdoBuildKatte.cs

勝手まわり(菜園の畝・自然の斜面に据える踏み段)の置き方 — EdoBuild の partial(2026-10-03・EDO-0532 施主裁定A)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `FieldBox`(class) | — | | 菜園の矩形(u・v を軸に、origin からの局所 m)。 | |
| `EdoBuild.FieldRect(origin, u, v, ok, cell, reach)` | `FieldBox` | 地面・区域 | 軸に揃えた最大の矩形を格子 cell で探す(ヒストグラム法)。 | TypologyBuilder.Katte(Katte) |
| `EdoBuild.FieldCorners(b)` | `Vector2[]` |  | 矩形の四隅(世界の XZ)。 | TypologyBuilder.Katte(Katte) |
| `EdoBuild.LayUne(path, parent, b, pitch, sink, maxBury, note)` | `List<GameObject>` | 硬 地面・駒どうし | 畝を並べる。矩形の長手に畝を通し、畝間(芯々)pitch で並べる。 | TypologyBuilder.Katte(Katte) |
| `EdoBuild.SlopeSteps(pathOf, parent, a, b, keri, fumi, mat, proud, blocked, note)` | `List<GameObject>` | 硬 地面・天端 | 自然の斜面に段石を据える(斜面は崩さない・造成しない)。 | TypologyBuilder.Katte(Katte) |
| `EdoBuild.BodyCentreXZ(t)` | `Vector2` |  | 棟の壁体(屋根を外した実メッシュ)の頂点の重心(XZ)。 | TypologyBuilder.Katte(Katte) |
| `EdoBuild.ExitToward(t, from, to, clear)` | `Vector2` |  | 棟の壁体の凸包を from から to の向きへ出た所から、さらに clear 外の点。 | TypologyBuilder.Katte(Katte) |

## EdoBuildMachiya.cs

町屋の表店の run — EdoBuild の一部(規則21「置く・測る・突き付ける・据えるは EdoBuild の関数だけ」)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `ShopModule`(struct) | — | | 表店の駒の寸法(ES 倍・ピボットからの片寄せ込み)。 | |
| `ShopPiece`(struct) | — | | 表店の駒 1 種 = パス+倍率。⭐ 測る倍率と置く倍率を分けて持てない形にした — edogoyomi は ES 倍、 当方で起こした駒は実寸(1 倍)で、片方だけ取り違えると 1.8 倍(または 0.55 倍)の町屋… | |
| `EdoBuild.EdgeDepth(poly, A, B, outward)` | `float` | 硬 区域 | 辺の背後に実際に何 m あるか。辺の上の 9 点から敷地の内へ歩いて、区画の外へ出るまでの 距離の中央値。 | — |
| `EdoBuild.FenceRunFlush(parent, A, B, outward, kind, baseY, prefix, faceDepth, note)` | `List<GameObject>` | 区域 | 柵の外の面を、線から内へ faceDepth の面へ揃えて建てる(EDO-0503)。 | Typology(BuildParcel) |
| `EdoBuild.MACHIYA_MAX_GRADE` | `float` |  | 表店を建ててよい道の縦の勾配の上限【U】(EDO-0503)。 | — |
| `EdoBuild.ShopMeasure(path)` | `ShopModule` |  | 在庫の edogoyomi の駒(ES 倍で使う物)を測る。 | TypologyBuilder.Machiya(Machiya) |
| `EdoBuild.OwnMeasure(path)` | `ShopModule` |  | 当方で起こした駒(実寸で使う物 = 倍率 1)を測る。 | TypologyBuilder.Machiya(UraNagaya) |
| `EdoBuild.ModuleMeasure(path, scale)` | `ShopModule` |  | 駒を scale 倍・無回転で仮置きして軒と躯体の走り・奥行を測る。 | — |
| `MachiyaTally`(struct) | — | | 表店の run が何を建てたか。⛔ 呼び手は必ず全部刷る(規則19)— とくに wantHouses と houses の差は「5間の駒が無い」ことの実測の現れで、 黙って飲むと在庫の宿題(EDO-0318 ④)が見えな… | |
| `EdoBuild.TileWidths(target, widths, joint, res=…)` | `int[]` |  | 列の残り長さを、繰り返し使える棟の実寸の組合せで埋める計画(掲示板 EDO-0362 §1d の型)。 | — |
| `EdoBuild.MachiyaRun(parent, A, B, outward, baseY, maguchiM, maxDepthM, gapC, gapHalf, prefix, leadPath, ours, keepInside, avoid, tally, seed=…, maguchiMix=…)` | `List<GameObject>` | 硬 面・区域 | <summary>表店の列。辺 A→B に、通りへ店先を向けた町屋を軒を接して並べる。 | TypologyBuilder.Machiya(Machiya) |
| `EdoBuild.UraNagayaRun(parent, A, B, outward, baseY, insetM, cap, prefix, keepInside, avoid, dropped, wallGap, gapM, munewari=…)` | `List<GameObject>` | 床 | <summary>裏長屋(裏店)の列。表店の列の背後に、路地を挟んで棟を並べる。 | TypologyBuilder.Machiya(UraNagaya) |
| `EdoBuild.MachiKidoKeisha(a, b, away)` | `float` | 硬 地面・区域 | 道を塞ぐ町木戸を、道の両側の角 a・b の間に据える。 | TypologyBuilder.Machiya(MachiKido) |
| `EdoBuild.MachiKidoAcross(parent, path, a, b, away, name, note, keisha=…)` | `GameObject` |  | ⚠ 注釈なし | Assets(Munamon), TypologyBuilder.Machiya(MachiKido) |
| `EdoBuild.NorenVariants()` | `List<Dictionary<string, object>>` |  | `docs/Sashizu/noren.json` の店の一覧(EdoAssets.Eg.NorenSpec)。 | TypologyBuilder.Machiya(NorenKeysFor) |
| `EdoBuild.HangNoren(houses, keys, seed)` | `string` |  | 表店に軒ごとの暖簾を掛ける。keys は掛けてよい店(noren.json の key・重複は軒数の比)。 | TypologyBuilder.Machiya(Machiya) |

## EdoBuildMichi.cs

EdoBuild — 道の造成(縦断を設計して道の面を均す)。2026-09-30・EDO-0495(施主裁定②「小道を造成する」)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Michi`(class) | — | | 設計した道。s[k] = 芯に沿う距離、y[k] = 設計の高さ(DS 刻み)。 | |
| `EdoBuild.MICHI_DS` | `float` |  | 縦断の刻み[m]。 | — |
| `EdoBuild.MICHI_EDGE_TOL` | `float` | 区域 | 道の面の縁から、道の高さとして読む遊び[m](区画の線の上の点を道として読むため)。 | — |
| `EdoBuild.MichiZosei()` | `List<Michi>` |  | 指図(`docs/Sashizu/*_sashizu.json`)の道の欄のうち `zosei` を持つ物を読み、縦断を設計して返す(json が変われば読み直す)。 | — |
| `EdoBuild.RoadY(x, z)` | `float` | 硬 | 道の高さ(硬い: 門の敷居・門の平場はこれに合わせる)。 | — |
| `EdoBuild.GradeMichiNear(parcel, reach=…)` | `string` | 地面・区域 | 区画に接する設計した道を均す(区画を建てる前に呼ぶ・冪等)。 | Typology(BuildParcel) |
| `EdoBuild.GradeMichi(m)` | `string` |  | 道の面の中の節点を設計の高さへ(横断は水平)。 | — |

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
| `EdoBuild.Seed(s)` | `int` | 区域 | 文字列から版を跨いで同じ乱数の種を作る。 | TypologyBuilder.Yuragi(YuOrig・YuTanaSeed・YuUnit), TypologyBuilder.Machiya(Machiya), TypologyBuilder.Niwa(Niwa) |
| `EdoBuild.PartSize(path)` | `Vector3` |  | 部材の実メッシュの外形(scale=1・yaw=0 の Renderer bounds の大きさ)。 | — |
| `EdoBuild.CrownR(path)` | `float` |  | 樹冠(や駒)の平面の半径[m] — 実メッシュの XZ の大きい方の半分(scale=1 のとき)。 | TypologyBuilder.Niwa(MaxCrown・NiwaIdo・NiwaToro…), TypologyBuilder.Keidai(NiwaKeidai) |
| `NiwaOcc`(class) | — | | 実メッシュの標本を 1m の升へ撒いて、「この点から一番近い実メッシュまで何 m か」を 打ち切り付きで返す。 | |
| `EdoBuild.GateClearance(go, gateC, withRoof=…)` | `float` | 地面 | 門の芯 gateC から駒の実外形までの水平の離れ[m](外形の中なら 0)。 | Typology(Omoya) |
| `NiwaSet`(struct) | — | | 据えるときの作法ひと組。 ⭐ 囲いからの離れは「幹の芯」で、軒からの離れは「樹冠の外接円」で測る(庭方 2026-09-22 の検分⑧)。 | |
| `NiwaKoma`(struct) | — | | 据えた駒ひとつ。⭐ 実メッシュで測り直した樹冠の半径 r(外接円の中心 c)と 地際から測った幹の芯 trunk を両方持つ — 囲いは幹で、軒は樹冠で検めるため(検分⑧)。 | |
| `EdoBuild.NiwaTrunk(go, c, maxSamples=…)` | `bool` |  | 駒の地際(実メッシュの底から「丈の12%か0.30mの厚い方」の帯)に入る頂点の重心 = 幹の芯。 | — |
| `EdoBuild.FootSlope(go, bedAt, footR)` | `float` | 地面 | 幹の足の下の地表の傾き tanθ と、足の半径 footR[m](2026-09-29 EDO-0488)。 | — |
| `NiwaField`(class) | — | | 庭の地 — 「どこに置けるか」を実メッシュから解いて持つ。 | |
| `EdoBuild.NiwaClump(parent, prefix, f, center, palette, n, rnd, o, layer, pick=…)` | `List<GameObject>` |  | 塊をひと組据える。⭐ 本数は必ず奇数・外形は不等辺・乱れは4つ全部(§5-0)。 ⟶ 返す: 据わった駒 | TypologyBuilder.Niwa(Layer・NiwaChisen・NiwaIshigumi…), TypologyBuilder.Keidai(NiwaKeidai) |
| `EdoBuild.NiwaWallBandSites(f, lo, hi, k, rnd, skip, fromWall, blind)` | `List<Vector2>` | 区域 | 散らしではなく帯。周長を k 等分した箇所から内へ歩き、 囲い・長屋の実メッシュからの距離が lo〜hi に入る点を返す。 | TypologyBuilder.Niwa(NiwaChisen・NiwaTsubo), TypologyBuilder.Keidai(NiwaKeidai) |
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
| `EdoBuild.BedTopAt(p, beds, yTop)` | `float` |  | 点 p の真上から下ろした光線が beds の上向きの面に最初に当たる高さ(当たらなければ NaN)。 | SannoSha(AbutStairsToWalls・RetractRunEndsFromWalls) |
| `EdoBuild.SoilSideCrestShort(g, faces, soilAt, at)` | `float` | 地面・天端・面 | 土の側(背)の天端の足りなさ(2026-09-25・EDO-0430)。 | — |
| `EdoBuild.SOIL_SIDE` | `float` | 天端 | 背の帯の奥行[m]。皮は周り 0.5m(CAPR 2 × 0.25)の天端で下げるので、同じだけ見る。 | — |

### 野面の土留めの網(2026-09-26・EDO-0437)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `NozuraSeg`(class) | — | | 野面の土留めの一区間(直線)。指図の run を口(石段の口)で割った一本ずつ。 | |
| `EdoBuild.PlaceNozuraNet(segs, groundAt, faceGroundAt, probe, parent, straight, kado, dan, kiri, mikiriPath, heights, pool, log, kiriEnd=…, noriEnd=…, kadoAbut=…)` | `List<KeyValuePair<GameObject, Vector2>>` | 地面・駒どうし・面・隅 | 野面の土留めの網を据える(2026-09-26・EDO-0437)。 ⟶ 返す: 据えた駒と見え面の向き(駒の名は据わった区間の名) | SannoSha(Nozura), TypologyBuilder.Rim(Rim) |
| `EdoBuild.PlaceNozuraMikiri(pathOfH, edge, toward, face, footY, crestY, partners, parent, name, log, soilAt=…)` | `GameObject` | 天端・床・面 | 口の縁の見切り石を据える(2026-09-26・EDO-0437)。 | — |

## EdoBuildOsameru.cs

寄せて測るを収まるまで回す (EdoBuild の partial・2026-09-26・EDO-0454)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Tori`(class) | — | | 取り合い一つ。「残り」(0 が狙い・単位 m)を測る手と、一手寄せる手の組。 | |
| `Osamari`(class) | — | | Converge の結果。Ok と Reason だけ読めば次の手が決まる。 | |
| `EdoBuild.Converge(toris, maxRounds=…, stall=…)` | `Osamari` | 硬 | 寄せて測るを収まるまで回す。toris を渡した順に寄せ(帯の中の物は動かさない)、 巡ごとに全部を測り直す。 ⟶ 返す: 合否・理由・取り合いごとの前後の残り・最悪値 | — |
| `EdoBuild.AbutAndSeat(mover, other, dir, gap=…, sink=…, maxSamples=…, maxRounds=…)` | `Osamari` | 地面・駒どうし | 一つの駒を「相手へ突き付け → 地面に据える」で納める近道(番所→門・袖塀→番所 の型)。 | — |

## EdoBuildQueue.cs

EdoBuildQueue.cs — 長い建て直しを MCP の 1 回の呼び出しの中で回さず、エディタの中で順に予約して即座に返す(EDO-0503)。

## EdoBuildRim.cs

崖の縁の土留め — 区画の線の上に立つ塀の真下を削って野面の石垣を積み、塀を天端に載せる (EdoBuild の partial・2026-09-28・EDO-0477)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.RIM_MIN` | `float` |  | 背の地盤 − 平場 がこれ以上なら崖の縁と見る[m]。 | — |
| `EdoBuild.RIM_LINE_MIN` | `float` |  | 塀の立つ線の地盤(造成前)− 平場 がこれ以上の所だけ崖の縁と見る[m]。 | — |
| `EdoBuild.RIM_REACH` | `float` |  | 平場がこの距離[m]より遠い縁は崖の縁と見ない(平場の無い所は削らない)。 | — |
| `EdoBuild.RIM_BACK_AT` | `float` | 区域 | 背の地盤を測る離れ[m](区画の線から外へ)。 | — |
| `EdoBuild.RIM_BACK_TOL` | `float` | 硬 天端 | 背の地盤が天端よりこれ以上低い端は石垣を切る[m](背の無い石垣を立てない・硬い)。 | — |
| `EdoBuild.RIM_MIN_LEN` | `float` |  | 石垣の一続きの最短[m]。これより短い区間は積まない。 | — |
| `EdoBuild.RIM_CORNER_BRIDGE` | `float` | 区域 | 区画の角を挟んで崖の縁の標本が抜けた長さ[m]がこれ以下なら、角まで継いで一続きにする(= RIM_MIN_LEN)。 | — |
| `EdoBuild.RIM_BERM` | `float` |  | 法尻の前に平らに取る犬走り[m]。【確度 U】 | — |
| `EdoBuild.RIM_BATTER` | `float` |  | 野面の法(3分)。焼いた駒と同じ(EdoAssets.Own.SannoNozura)。 | — |
| `RimRun`(class) | — | | 崖の縁の石垣の一続き。 | |
| `EdoBuild.RimRetainRuns(A, B, outward, use, pads, padY, report)` | `List<RimRun>` | 天端・区域 | 崖の縁の区間を測る(区画の線を 1m 刻み)。 | TypologyBuilder.Rim(Rim) |
| `EdoBuild.OffsetPolyline(line, off, inward)` | `List<Vector2>` | 区域 | 区画の線の折れ線 line を、区画の内へ off[m] 寄せた折れ線(折れの所は寄せた線どうしの交点)。 | TypologyBuilder.Rim(Rim) |
| `EdoBuild.CutBeforeRim(parcel, r, back=…, cutRun=…)` | `string` | 天端・区域 | 石垣の前(区画の内)を平場まで削る。天端の線 RimRun.crestLine から内への距離 x、走りの外への はみ出し a として、節点の高さを min(今, 限り) に下げる(⛔ 上げない・区画の外は触らない):… | TypologyBuilder.Rim(Rim) |
| `BedIndex`(class) | — | | 受けの駒の上向きの面の索引(実メッシュの三角形・0.5m の升に振る)。 | |
| `EdoBuild.RimFenceInset(bed, a, b, inw, half, crest, maxIn, need, frac)` | `float` | 地面・天端・区域 | 崖の縁の石垣に載せる塀を、区画の線から内へ寄せる量[m]。 | — |

### 区画の角の塀の口(2026-09-28・EDO-0477 P2 隅)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.FenceFaceOffsets(kind, hOut, hIn)` | `void` | 断面・区域 | 囲いの駒の足元の面が区画の線からどれだけ外(hOut)・内(hIn)にあるか[m]。 | Typology(BuildParcel), TypologyBuilder.Rim(CornerReaches) |
| `EdoBuild.CornerReach(dPrev, dThis, outPrev, hOut, hIn)` | `float` | 硬 駒どうし・隅・区域 | 区画の角で塀の run を頂点の先へ延ばす長さ[m]。 | TypologyBuilder.Rim(CornerReaches) |

## EdoBuildRun.cs

囲いの run — 長屋・土塀・板塀を辺に沿って並べる (EdoBuild の partial・2026-09-21)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.CutShoulder(toe, outward, floorY, batter, natural, maxDist=…, step=…)` | `float` | 地面 | 切土の法の法肩までの水平距離(2026-09-26・EDO-0437)。 | SannoSha(ShiftRunToCutShoulder) |
| `EdoBuild.ShoulderLevelEnd(toe0, along, outward, floorY, batter, natural, maxD, eps, profile=…, drawn=…)` | `float` | 駒どうし | 法肩の線が下り始める所(2026-09-26・EDO-0437 第6巡)。 | SannoSha(ShiftRunToCutShoulder) |
| `EdoBuild.NaturalMode` | `bool` | 地面 | 自然地形モード: true なら造成せず、駒は一枚ずつ地面へ据える。 | — |
| `NagModule`(struct) | — | | 部材の壁実寸(走り方向)。edogoyomi knagaya の壁 = n_wall/namako/n_dodai。 | |
| `EdoBuild.NagayaMeasure(path)` | `NagModule` |  | 部材をES倍で仮置きして壁(wall/namako/dodai)のローカルX実寸を測る。 | — |
| `NagayaLeg`(class) | — | | 長屋の鎖の端から隅まで、隣の塀を折って回す足(EDO-0500)。 | |
| `NagayaKado`(class) | — | | 長屋どうしの出隅に据える隅長屋(EDO-0500 2026-10-01 施主指摘「角用の長屋にしないと屋根が変な重なり・窓が途中で途切れる」)。 | |
| `EdoBuild.NAGAYA_KADO_ARM_MIN` | `float` |  | 隅長屋の腕の下限[m](部材方の実測 4.79 ── 2 つ目の窓の先までは詰めない)。 | — |
| `EdoBuild.NagayaKadoPlace(parent, ks, prefix)` | `List<string>` |  | 二辺の腕が揃った隅に隅長屋(EdoAssets.Own.NagayaKado90)を据える。 | Typology(BuildParcel) |
| `EdoBuild.NagayaRun(parent, A, B, outward, baseY, gapC, gapHalf, prefix, keepInside=…, gateTuck=…, closeA=…, closeB=…, legs=…, nagA=…, nagB=…, kados=…, nOutA=…, nOutB=…)` | `List<GameObject>` |  | ⚠ 注釈なし | Sanyashiki(S3_Enclosure), Typology(BuildParcel), Yamato(Y2_Enclosure) |
| `RunModule`(struct) | — | | 部材の走り方向(ローカルX)の実寸。倍率1・回転なしで仮置きして頂点から測る(NagayaMeasure の塀版)。 | |
| `EdoBuild.RunMeasure(path)` | `RunModule` |  | ⚠ 注釈なし | — |
| `RunHeightM`(struct) | — | | 部材のローカル Y の実寸。根入れ(原点より下にある分)と丈の中ほどを取るために測る。 | |
| `EdoBuild.RunMeasureY(path)` | `RunHeightM` |  | 部材のローカル Y の実寸を測る(結果は綴りごとに憶える)。 | SannoSha(SakuRun) |
| `EdoBuild.MidSection(go)` | `List<Vector3>` | 断面 | 据わった駒を、その駒自身の丈の中ほど(継ぎ目の高さ)で切った断面(世界座標)。 | SannoSashizuCheck(Check) |
| `EdoBuild.PolylineParam(poly, p, s, lat, ext=…)` | `void` |  | 折れ線 poly(xz)の上で点 p に最も近い所の 道のり s と符号付きの横のずれ lat(走りの左が +)。 | SannoSashizuCheck(Check) |
| `EdoBuild.GroundPolyline(a, b, span, floatMax, buryMax, smooth=…)` | `List<Vector3>` | 地面 | 地表なりの折れ線へ割る。辺 a→b を、描かれている地表に沿った実長(道のり)で span ごとに割り、継ぎ目の点(世界座標・高さは地表)を返す。 | SannoSha(SakuRun) |
| `EdoBuild.SplitAtBedSteps(a, b, heightAt, jump, res=…, minLen=…)` | `List<Vector2[]>` | 天端・床 | 走りを床の段(鉛直の落ち)で割る(2026-09-26・EDO-0430 山王 `Ita_Keidai` の柵 × 御供所の郭の土留め)。 | SannoSha(SakuRun) |
| `EdoBuild.PlaceOnChord(path, j0, j1, parent, name)` | `GameObject` |  | 弦に沿って駒を据える。継ぎ目 j0→j1 に張るよう、 yaw = 走り・roll = 弦の勾配・走り方向の伸縮 = 弦の実長(斜距離)で置く。 | SannoSha(SakuRun) |
| `EdoBuild.PlaceOnChordMeasured(path, j0, j1, outward, latLine, unitScale, parent, name, ext0=…, ext1=…)` | `GameObject` | 地面 | 弦に張る(実測版)(2026-09-27・EDO-0477 P2)。 | — |
| `EdoBuild.CHORD_ROOT_MAX` | `float` | 地面 | 地形なりの走りの根入れの深さの上限[m](山王の板塀の代 −0.60 と同じ ── 2026-09-27 施主「基本は埋める」)。 | — |
| `EdoBuild.RootChordRun(js, placeSeg, worstFloat, deepest, breaks=…)` | `List<GameObject>` | 地面・天端・区域 | 弦の走りを根入れで収める(2026-09-28・EDO-0477)。 | — |
| `EdoBuild.StraightRunJoints(a, b, span, root, breaks)` | `List<Vector3>` | 地面・天端・区域 | 天端を一続きごとに一直線に取る継ぎ目(2026-09-28・EDO-0477 施主「塀が地形に合わせて滑らかに波打ってる」)。 | — |
| `EdoBuild.KinkOverlap(js, breaks, j, height)` | `float` | 駒どうし | 折れの継ぎ目で隣の駒へ重ねる長さ[m] ── 丈の半分 × 傾きの差 + 0.02(隙間>めり込み・駒どうしの埋め込みは数えない)。 | — |
| `EdoBuild.ChordFacing(j0, j1, outward)` | `bool` |  | 弦 j0→j1 に張った駒の表(ローカル +Z)が outward を向くか。 | — |
| `EdoBuild.DobeiRun(parent, A, B, outward, prefix, followGround, flatBase, gapC, gapHalf)` | `List<GameObject>` |  | ⚠ 注釈なし | SannoSha(Stage1_Keidai・Stage2_Sando), Doi(Stage2_Perimeter), MatsudairaDewa(Stage2_Perimeter), OkabeYashiki(Stage2_Perimeter), Sanyashiki(S3_Enclosure) ほか1 |
| `EdoBuild.NeribeiRun(parent, A, B, outward, prefix, followGround, flatBase, gapC, gapHalf)` | `List<GameObject>` | 隅・区域 | DobeiRun(表裏2枚の板塀)と違い Dobei2m は1駒で厚みを持つ一体物なので、side ループは無い。 | — |
| `EdoBuild.DAN_STEP` | `float` | 硬・柔 地面・床・区域 | ⭐ 屋敷の練塀は傾けない。区間ごとに笠を水平にし、区切りで段を付ける(段塀)。 | — |
| `EdoBuild.DAN_STEP_MIN` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_STEP_MAX` | `float` |  | ⛔ 0.50 にすると 0.50・0.65 の段が残った(観理院の北の角)── 裁定図の段は 0.81・0.83 | — |
| `EdoBuild.DAN_MIN_SEC` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_MAX_SEC` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_BURY` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_BURY_MAX` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_STONE_EMBED` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_GATE_SODE` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_CORNER_CLEAR` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_FLAT_NEAR` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_FLAT_ALONG` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_FLAT_MARGIN` | `float` |  | ⚠ 注釈なし | — |
| `EdoBuild.DAN_FLAT_TOL` | `float` |  | ⚠ 注釈なし | — |
| `DanSec`(struct) | — | | 段塀の一区間(鎖の道のり a〜b・塀の座 W = 塀の下端の高さ)。 | |
| `EdoBuild.DanPlan(chain, note, gates=…)` | `List<DanSec>` | 硬 地面・床・区域 | 折れ線(区画の辺の鎖)に段塀の区切りと座を引く。 | Typology(BuildParcel) |
| `EdoBuild.NeribeiStepRun(parent, A, B, outward, prefix, secs, gapC, gapHalf, note)` | `List<GameObject>` | 地面・天端 | 練塀を段塀で建てる。secs は A からの道のりの区間(座 W)。 | — |
| `EdoBuild.PanelRun(parent, A, B, outward, prefix, assetPath, gapC, gapHalf, pair=…, unitScale=…, beds=…, bedAt=…, splitPost=…, splitBoard=…)` | `List<GameObject>` |  | <remarks>据えは DobeiRun と同じ — 触れている箇所を測る(規則21)。 | — |
| `EdoBuild.PostBoardRun(parent, A, B, outward, prefix, postPath, boardPath, bedAt, root, pair=…)` | `List<GameObject>` | 駒どうし・床・断面 | 柱と板を分けた組で板塀の run を張る(2026-09-26・EDO-0437 第7巡)。 | — |
| `EdoBuild.SCRIBE_MARK` | `float` |  | 光付け(削り合わせ)の印 = 部材の局所 y ≤ これ の頂点(EdoAssets.Own.ItabeiJifuku・EdoAssets.Own.ItabeiHashiraHk の下端の格子)。 | — |
| `EdoBuild.SCRIBE_TOP_STOP` | `float` |  | 削りは部材の上端の手前これだけで止める(面が裏返らない)。 | — |
| `Scribe`(struct) | — | | 光付けの結果(床との隙の実測)。 | |
| `EdoBuild.MemoBed(bedAt, cell)` | `Func<float, float, float>` | 床 | 床の引きを升 cell で覚える(同じ升は一度だけ引く・升の中の点は升の芯の値)。 | — |
| `EdoBuild.SCRIBE_GAP_TARGET` | `float` | 柔 | 光付けの狙い[m]: 削った後の下端と当たりの隙がこれを超える三角形だけ、最も長い辺を割って削り直す(合格線 ±0.01 の手前)。 | — |
| `EdoBuild.SCRIBE_REFINE_PASSES` | `int` |  | ⚠ 注釈なし | — |
| `EdoBuild.SplitEdges(m, want)` | `int` | 面 | 辺を半分に割る(光付けの割り足し・2026-09-27 EDO-0437)。 ⟶ 返す: 割った辺の数 | — |
| `EdoBuild.ScribeToBed(go, bedAt, meshName, step=…)` | `Scribe` | 駒どうし・天端・床 | 部材の下端を床へ光付けする(削り合わせ・2026-09-27 EDO-0437 施主裁定 案A)。 | — |
| `EdoBuild.RecentreInBand(go, s, bedAt, tol, maxSink=…)` | `bool` | 硬 天端・床・区域 | 浮きと根入れの帯の真ん中へ据える(硬い ±tol)。 | Typology(BuildParcel) |
| `EdoBuild.RootToBed(go, bedAt, step=…, only=…)` | `Scribe` | 地面・天端 | 根入れで据える(埋めて隠す・2026-09-27 施主「基本は埋める、違和感が見える所だけ光付け」── docs/oki-kata.md §0a)。 | Typology(BuildParcel・Inspect) |
| `EdoBuild.SinkToBed(go, bedAt, step=…)` | `Scribe` | 硬 地面・区域 | 硬い・地面(浮き 0): 駒の下端の当たり(RootToBed)を相手 bedAt で測り、 最も浮いた当たりが相手に触れる所まで上下に動かす(下端 − 相手 の最大 = 0)。 | OkabeYashiki(PlaceFences) |
| `EdoBuild.VisibleAboveBed(go, bedAt, step=…)` | `float` |  | 駒の見える丈[m] = 全高 − 下端の最も深い根入れ(RootToBed の最小が負の分)。 | OkabeYashiki(PlaceFences) |
| `EdoBuild.WaistOutside(go, poly, bandH=…)` | `float` | 区域 | 駒の腰(壁体の最低点から bandH まで)の全頂点が区画の多角形の外へ出る最大[m](0 = 内)。 | OkabeYashiki(PlaceFences) |
| `EdoBuild.PostBoardRunScribed(parent, A, B, outward, prefix, postPath, boardPath, jifukuPath, bedAt, pair, log, scribe=…)` | `List<GameObject>` | 地面・駒どうし・天端・床・断面 | 柱・板・地覆の組で板塀の run を張り、地覆と柱の下端を床へ光付けする(2026-09-27・EDO-0437 施主裁定 案A「板を石の天端・地面まで下ろす」)。 | SannoSha(Stage4_Kakoi) |
| `EdoBuild.SeatPanelOnBed(go, A, dir, mn, mx, bedAt, root)` | `void` | 地面・床 | 板塀の駒を描かれた地表の弦に張って据える(2026-09-26・EDO-0437 第5巡)。 | — |
| `EdoBuild.RestOnBeds(go, beds)` | `float` | 地面・天端・床 | 駒の足の下に在る受けの駒(土留め・石垣)の天端に載せる(2026-09-26・EDO-0437 第3巡)。 ⟶ 返す: 上げた量(0 = 動かさない) | — |
| `EdoBuild.FenceRun(parent, A, B, outward, kind, baseY, gapC, gapHalf, prefix, note, dan=…)` | `List<GameObject>` |  | 辺 A→B に種別どおりの囲いを建てる。 | Typology(BuildParcel) |
| `EdoBuild.KuiRun(parent, A, B, outward, prefix, gapC, gapHalf, pitchKen, dias, label, note)` | `List<GameObject>` | 地面 | 杭列(傍示杭・杭)。⛔ 連続の塀にしない — 間を空けて立てる。 | — |
| `EdoBuild.PlantAvoid` | `List<Bounds>` |  | 生垣を植えてはならない所(棟・門構えの外接箱)。 | — |
| `EdoBuild.PlantInside` | `Vector2[]` | 硬 区域 | 生垣・林縁帯の株を植えてよい区画の輪郭(世界の x,z)。 | — |
| `IkeKind`(struct) | — | | 生垣の後列(主)の一株の型。⭐ 設計は庭方(2026-09-29 EDO-0475・scratchpad の EDO0475_ikegaki_design)。 | |
| `EdoBuild.TintFoliage(go, tint)` | `void` |  | ⚠ 注釈なし | — |
| `EdoBuild.RootPlant(go, maxRoot)` | `bool` | 硬 地面・天端・区域 | 植えた駒(生垣・林縁帯の低木)を根入れで据える(2026-09-28・EDO-0472)。 | — |

## EdoBuildSeiyaku.cs

制約の二種 — 硬い制約(関門)と柔らかい制約(狙い)を、置く側の共通の層で使い分ける(EDO-0372・施主 2026-09-23)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `Hard`(class) | — | | 硬い制約。ok(駒) が false の置き場は退ける。 | |
| `Soft`(class) | — | | 柔らかい制約。measure(駒) が Target 以上なら満たす(大きいほど良い物だけを書く)。 | |
| `SeiyakuTally`(class) | — | | 制約ごとの勘定。邸ビルダーの log へそのまま刷る(規則19)。 | |
| `EdoBuild.PlaceBest(spots, maxTries, place, hards, softs, tally)` | `GameObject` | 硬・柔 | 置き場の候補を順に試し、硬い制約で退け・柔らかい制約で選ぶ。 | OkabeYashiki(PlaceFences), Typology(Omoya), TypologyBuilder.Jisha(JishaOmoya) |

## EdoBuildSueru.cs

埋め込む駒・差し込む駒・載せる駒を据える (EdoBuild の partial・2026-09-23・EDO-0274)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.BodyOfMat(tr, mat)` | `List<Vector3>` |  | 材(サブメッシュの材質名)で絞った、駒の世界頂点。 | — |
| `EdoBuild.Section(tr, y, mat=…)` | `List<Vector3>` | 断面 | 実体化した駒の水平断面(高さ y で三角形を切った交点・世界座標)。 | SannoSashizuCheck(Check) |
| `EdoBuild.ContactPts(pa, pb, dir, at, count, tol=…, cell=…)` | `float` | 面 | 二つの頂点の集まりが触れている箇所(Contact の中身)。 ⟶ 返す: 最小の隙(負 = めり込み)・NaN = 向き合っていない | — |
| `EdoBuild.RestGap(mover, moverMat, bed, bedMat, at, count, tol=…)` | `float` | 天端・床 | 載る駒と受ける駒が鉛直に触れている箇所(材で絞る・null で全材)。 ⟶ 返す: 最小の隙[m](負 = めり込み・NaN = 上下に重ならない)、 at = その所、count = 最小から tol 以内の点の数 | — |
| `EdoBuild.RestOn(mover, moverMat, bed, bedMat, gap, at, count)` | `float` | 床 | 受けの上に載せる。RestGap が gap(0 = 接触)になる高さへ 鉛直に動かす。 ⟶ 返す: 動かした量[m](上下に重ならなければ NaN で動かさない) | SannoSha(Stage8_Ido) |
| `EdoBuild.FlushGap(go, mat, rise, at, count, cell=…, tol=…)` | `float` | 地面・天端 | 天端を地表に揃えて埋める駒の、天端と地表の差。 ⟶ 返す: 最小(負 = 天端が土に埋まっている)、 rise = 最大(天端が地表から出ている量) | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `EdoBuild.SeatFlush(go, mat, proud, rise, cell=…)` | `float` | 地面・天端 | 天端を地表に揃えて埋める。FlushGap の最小が proud (+ = 地表から出す量・0 = 面一)になる高さへ動かす。 ⟶ 返す: 動かした量[m] | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `EdoBuild.CenterInOpening(plug, plugMat, socket, socketMat, y, margin, clearMin, clearMax)` | `Vector2` | 床・断面 | 差す駒を相手の穴へ芯出しする。高さ y で、差す駒(材 plugMat)の 断面の外周と、受ける駒(材 socketMat)の断面のうち差す駒の外周から margin 以内にある物(= 穴の壁)を取り、両方の外形の中点を… ⟶ 返す: 動かした量(XZ・測れなければ NaN で動かさない) | SannoSha(Stage8_Ido) |
| `EdoBuild.CenterOnBed(mover, moverMat, yMover, bed, bedMat, yBed, reach, worstFoot)` | `Vector2` | 床・断面 | 足(柱)を受け(礎石)へ芯出しする。載る駒(材 moverMat)の高さ yMover の 断面(= 足の実形)と、受ける駒(材 bedMat)の高さ yBed の断面のうち 足の外形から reach 以内の物(= 受け… ⟶ 返す: 動かした量(XZ・測れなければ NaN で動かさない) | SannoSha(Stage8_Ido) |
| `EdoBuild.SeatPlugInBed(bed, bedMat, plug, plugSideMat, plugRestMat, cutBelowTop, clearMin, clearMax, nTouch)` | `string` | 天端・床・断面 | 差して載せる駒を、面一に埋めた受けへ据える(井戸 = 板石敷の穴へ井筒を差し、井桁を縁石へ載せる)。 ⟶ 返す: null(据わった)か、据わらなかった理由 | TypologyBuilder.Niwa(PutIdo) |

### 駒の下の地形(2026-09-23・EDO-0274)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.HullOfMat(tr, mat=…)` | `Vector2[]` |  | 駒(材 mat・null で全材)の実メッシュの平面の外形(XZ の凸包・世界座標)。 | SannoSashizuCheck(Check), SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `EdoBuild.OpeningOf(tr, mat, y, n=…)` | `Vector2[]` | 断面 | 筒の口(輪になった駒の内周)を高さ y の断面から採る。 | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `TerrainCells`(struct) | — | | 地形のセル範囲の報告。 | |
| `EdoBuild.ClearDetailIn(poly, cellOk=…)` | `TerrainCells` |  | 多角形に少しでも掛かる detail のセルを空にする(全層)。 ⟶ 返す: 掛かったセルと値の変わったセル | GardenSurfacePaint(Paint), SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `EdoBuild.CutHole(opening, covers, why, joint=…)` | `TerrainCells` | 地面・駒どうし | 口の下の地形に穴を開ける(TerrainData の holes)。 | SannoSha(Stage8_Ido), TypologyBuilder.Niwa(PutIdo) |
| `EdoBuild.FillHoles(cells)` | `int` |  | CutHole で抜いた範囲を塞ぐ(据え直しの前に)。 ⟶ 返す: 塞いだセルの数 | TypologyBuilder.Niwa(FillIdoHoles) |

### 天端の下の地形(2026-09-23・EDO-0414)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `CrestTuck`(struct) | — | | TuckUnderCrest の報告。 | |
| `EdoBuild.TuckUnderCrest(pieces, mat, depth=…, minGap=…, inset=…, coTol=…, faces=…, measureOnly=…, crestBand=…)` | `CrestTuck` | 硬・柔 地面・天端・面 | 天端を地表と同じ高さに据えた駒の下の地形を納める。 | SannoSha(HifuMeasure・Stage2_Kaidan・Stage3_Dodome) |

## EdoBuildSukima.cs

EdoBuildSukima.cs — 建物と隣の構造物の間の隙のうち、通りから裏手(敷地の内側)へ抜ける物だけを柵で塞ぐ(EDO-0503)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `SukimaGate`(struct) | — | | 塞ぐ口 ── 柵の線 a→b と、通りの側の向き。 | |
| `EdoBuild.SukimaGates(poly, fronts, root, note, cell=…, halfBody=…, yLo=…, yHi=…, maxGate=…, embed=…, maxGrade=…)` | `List<SukimaGate>` | 区域 | 通りから裏手へ抜ける隙だけを見つけて、塞ぐ柵の線を返す(EDO-0503・施主 2026-10-03)。 | Typology(BuildParcel) |

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
| `EdoBuild.TrunkFootLocal(prefabPath)` | `Vector2` |  | 部材の幹の足の中心(部材の局所 xz・scale 1・m)。 | SannoSashizuCheck(Check), SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TrunkFootLocal(prefab)` | `Vector2` |  | ⚠ 注釈なし | SannoSashizuCheck(Check), SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TreePivotForTrunk(point, footLocal, widthScale, rotationRad)` | `Vector2` | 地面 | 地形の木(TreeInstance)のピボットの世界 xz = 点 − R(rotation)·(幹の足 × widthScale)。 | SannoSha(Stage7_Shaso), Trees(Plant) |
| `EdoBuild.TrunkFootWorld(go, foot)` | `bool` |  | 据えた木の幹の足の中心(世界)。傾き・scale は据えたとおり(帯は上向きに 0.3m)。 | Typology(Inspect) |
| `EdoBuild.SeatPlantAt(go, trunkXZ, sink, bury, flt, buryMax=…, floatMax=…)` | `bool` |  | 幹の足の中心を trunkXZ へ寄せてから SeatPlant で据える。 | SannoSha(Stage7_Shaso) |

## EdoBuildZosei.cs

EdoBuild — 造成(平場を採る)。2026-09-27・EDO-0477 P1(山王 Stage1_Grade と松江松平 DesignY の型を、図を持たない区画へ)。

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoBuild.EDGE_BERM` | `float` | 区域 | 区画の縁に沿って地山のまま残す幅[m] = 塀の足元(厚み 0.4〜0.6)+ 犬走り。 | — |
| `EdoBuild.BaseDem()` | `Func<float, float, float>` |  | 造成前の地盤(`docs/Sashizu/base_dem.json`・2m 格子の双一次)。 | Assets, TypologyBuilder.Jisha(JishaOmoya) |
| `Kindai`(class) | — | | 近代の造作の範囲(EdoAssets.Eg.KindaiSpec)。 | |
| `EdoBuild.KindaiList()` | `List<Kindai>` |  | 近代の造作を除く帳を読む(無ければ空)。 | — |
| `EdoBuild.ApplyKindaiNear(parcel, reach=…)` | `string` | 地面・区域 | 区画の外の地形へ、近代の造作を除いた地盤を書く(区画を建てる前に呼ぶ・冪等)。 | Assets, Typology(BuildParcel) |
| `Hiraba`(class) | — | | 平場の結果(棟ごと)。 | |
| `MonPad`(class) | — | | 棟の足あとごとに平場を採り、法面で地山へ擦り付ける。 | |
| `EdoBuild.MonPadWithSode(mon, la, lb, inward, sode, depth)` | `MonPad` | 区域 | 門構えの平場を袖の塀の下まで延ばす(EDO-0514・施主 2026-10-03「敷地・道の造成、整地も選択肢に」)。 | Typology(BuildParcel) |
| `EdoBuild.GradePads(parcel, pads, margin, report, fillRun=…, cutRun=…, mon=…, faced=…)` | `List<Hiraba>` |  | ⚠ 注釈なし | Typology(BuildParcel) |
| `EdoBuild.PadSqueeze(parcel, foot, margin, fillRun=…, cutRun=…)` | `int` | 硬 区域 | この足あとに平場が取れるかを置く前に測る(2026-09-28 EDO-0477)。 | TypologyBuilder.Jisha(JishaOmoya) |
| `EdoBuild.PadSqueeze(parcel, foot, margin, placed, fillRun=…, cutRun=…)` | `int` | 硬 区域 | 置いた棟の平場と束ねても平場が取れるか(2026-09-29 EDO-0472)。 | TypologyBuilder.Jisha(JishaOmoya) |
| `RingNode`(struct) | — | | 縁取りの内の節点。y = 造成前の地盤(無ければ NaN)/ live = 今の地表 / inFoot = 足あとの中 / inP = 区画の中 / e = 区画の縁の法が使える距離(縁から EDGE_BERM を引いた… | |
| `EdoBuild.PAD_SHIFT` | `float` |  | 束ねた平場が、棟ごとの地盤の中央値から動いてよい幅[m] = 規則3 の系統差 ±0.25。 | — |
| `EdoBuild.CLIFF_SLOPE` | `float` |  | 崖とみなす横断勾配(高さ/水平)。1:1.4(約 35°)より急なら崖。 | — |
| `EdoBuild.CLIFF_MIN_RUN` | `float` |  | 崖と数える続きの最短[m]。これより短い急な所は塀の駒(2m)で跨ぐ段差として囲う。 | — |
| `EdoBuild.CliffFreeSpans(a, b, outward, minSpan, cliffLen, alongOnly=…)` | `List<float[]>` | 地面・床・区域 | 辺のうち塀が立てる区間(2026-09-28・EDO-0477。 | Typology(BuildParcel) |

## EdoGeom.cs

純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26)

| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |
|---|---|---|---|---|
| `EdoGeom.PIP(poly, p)` | `bool` |  | point-in-polygon (偶奇則)。 | SannoSha(InUngradedParcel・Nozura・OnFumotomichi…), DoiBuilder.Niwa(EditNiwaHeights・InWater・PondOverlapsCell…), Typology(Edges・Inner・Inspect…), Doi(GradeQA・ParcelOutQA・PointInPoly…), MatsudairaDewa(GradeQA・Stage1_Grade・Stage7_Niwa…) ほか10 |
| `EdoGeom.SignedArea(poly)` | `float` |  | 符号付き面積。CCW で正。 | TypologyBuilder.Jisha(JishaOmoya), TypologyBuilder.Keidai(NiwaKeidai) |
| `EdoGeom.InwardNormal(poly, i)` | `Vector2` |  | 辺 i (poly[i]→poly[i+1]) の、多角形の内側を向く単位法線。 | GotenTypoTest(Build), OkabeYashiki(OutNormal), Typology(Outward), TypologyBuilder.Jisha(JishaOmoya) |
| `EdoGeom.DistToEdge(p, a, b)` | `float` | 区域 | 点 p から線分 ab への最短距離。 ⚠ 長さ0の線分では NaN を返してはいけない。 | SannoSha(KeepClearOfFlushWalls・OnFumotomichi・Stage4_Kakoi), TypologyBuilder.Niwa(NiwaChisen・NiwaTsubo), Typology(FrontEdge), TypologyBuilder.Jisha(JishaOmoya), TypologyBuilder.Keidai(NiwaKeidai) |
| `EdoGeom.LineIntersect(p0, d0, p1, d1, fallback)` | `Vector2` |  | 点 p から多角形の外周(全辺)への最短距離。 | — |
| `EdoGeom.DistToPolyEdge(poly, p)` | `float` |  | ⚠ 注釈なし | Typology(Candidates・Inner・Inspect…), TypologyBuilder.Jisha(JInside・JMinEdge・JishaOmoya), TypologyBuilder.Niwa(NiwaChisen・NiwaUra), SannoSashizuCheck(Check), SannoSha(OnFumotomichi) ほか2 |
| `EdoGeom.HullXZ(pts)` | `int[]` | 区域 | 点集合の凸包の頂点インデックス(反時計回り・共線点は落とす)。 | PartSpec(Measure), Typology(BuildParcel), TypologyBuilder.Katte(Katte) |

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
| `EdoParcels.Get(id)` | `Vector2[]` | 区域 | 区画のポリゴンを引く。無ければ 例外を投げずに null を返し、警告を出す (LoadAssetAtPath と同じ作法。 | SannoSha(InUngradedParcel・Stage1_Grade・Stage7_Shaso…), Typology(BuildParcel・Edges・MichiInsideBy…), Doi(In・KomonIshigakiQA), OkabeYashiki(C), SurfacePaint(Paint・Verify) ほか6 |
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

