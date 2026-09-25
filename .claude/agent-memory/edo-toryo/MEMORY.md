# Memory Index — edo-toryo(棟梁)

実装中に踏んだ非自明な罠だけ。手順はスキル、不変則は CLAUDE.md、指図は docs/Sashizu が正典。

## Unity MCP の罠

- [書き戻しは必ずタイムアウトする](pitfall-writeback-mcp-timeout.md) — 大きい邸のプレハブ。⛔再送せず mtime で判定
- [domain reload 後に bridge が消える](pitfall-bridge-drops-after-domain-reload.md) — 約2分。status ファイルと Logs/Editor.log で見る
- [再生中に建てるとシーンは消える](playmode-discards-scene-edits.md) — isPlaying を先に聞く。資産(プレハブ・地形)への書き込みだけ残る
- [30秒を超える execute_code は6回走る](akasaka-open-resent-six-times.md) — 赤坂・作業場を開く・重い計測。menu の赤坂へ戻すも6回開く・計測は割ってファイルへ
- [execute_code の replay は履歴の番号](execute-code-replay-index-is-history.md) — index=0 で前の Stage が再び走った。⛔replay せず送り直す

- [古い port 登録で「instances なし」が一回おき](pitfall-bridge-drops-after-domain-reload.md) — 6400→6401 退避 + 別プロジェクトの残骸。待たずに再送
- [start --unity が通っても claim が付いていないことがある](pitfall-unity-claim-not-verified.md) — status で「資源: unity」を見るまで MCP を叩かない
- [claim が無い巡は .cs も保存しない](cs-edit-is-not-claim-free.md) — 1行で他人の bridge が2分落ちる。用意は scratchpad の OLD/NEW 指示書へ
- [delayCall は他窓の reload で消える・指図の同時書き](delaycall-lost-and-shared-sashizu.md) — Stage は直に呼ぶ。流す前に指図の sha と impl の src を見る
- [別セッションの赤い .cs で Editor アセンブリが焼けない](editor-dll-blocked-by-other-session.md) — dll の mtime が止まり CPU も静か。⛔refresh を繰り返さず console の error を読む

## 部材の据え方

- [綴りで部材を選ぶ器は似た新部材で倒れる](part-pick-by-spelling-breaks-on-new-sibling.md) — 小鳥居が焼けた途端に一ノ・二ノ鳥居が消えた。名指しの行を先に外す

- [回した境内では方位も uv も枠の回りを足す](rotated-grid-directions.md) — 山王 5.5°。W() と FaceYaw が落として門が建たず社殿が元の軸に残った
- [正面のローカル軸は部材ごとに違う](front-axis-differs-per-part.md) — 山王 社殿5棟=+X/堂宇10棟=+Z。yaw=front−axis.front(EdoBuild.FaceYaw)
- [partFrom は2書式・フォルダを決め打ちしない](partfrom-two-spellings.md) — Own.呼び名は EdoAssets.OwnPath で解く。鐘楼鼓楼は Models/Jisha
- [partFrom の `4.5f` が 0 に化けた・差し替えは Place の後に旧を消す](ownpath-float-suffix-and-destroy-before-place.md) — OwnF を直した(EDO-0438)
- [接地は格子点でなく描かれている地表で測る](contact-must-use-drawn-surface.md) — 2m格子で斜面に ±(1m×勾配) の嘘。嘘の不合格と嘘の合格が同時に出る
- [幹の足は樹皮の底の輪か 0.02m 上の断面で測る](trunk-foot-band-catches-foliage.md) — 0.3m 帯は紅葉・蔓で 0.39m 外れた。蔓は最も低い茎
- [SeatPlant は斜面の木を浮き上限で沈める](seatplant-float-cap-buries-slope-trees.md) — 名指し20本が埋没15〜21m/浮き0.70。社叢の数え合わせは矩形の縁で11本落ちる
- [榎・椋は SeatPlant が NaN](seatplant-nan-enoki-mukunoki-noki.md) — LOD の子名の "noki" を IsRoofName が屋根と見る。篩を EdoBuild で直す
- [埋没を地形を掘って消す器は連鎖する](dig-to-unbury-cascades.md) — 山王 0.53/0.65 の埋没で3通り試し全部戻した。納めの話
- [急斜面の埋没は据え直しで浮きへ移るだけ](bury-becomes-float-when-relief-exceeds-tolerance.md) — 起伏>許容の和なら据え方の話でない。上げる前に埋没+浮きを測る
- [間引いた接地は沈む側にしか外れず、上限は足元の起伏](seat-sampling-error-bounded-by-relief.md) — だから起伏で選んで細かく据え直せる。平地は無料
- [段の位置は指図の pos でなく実地表から解く](stair-position-is-terrain-dependent.md) — 落ち際は擦り付けで2〜4.5m。許容は段自身の蹴上
- [比は意図でなく据わった数で決まる](ratio-on-intent-vs-seated.md) — 樹冠の大きい層が据わりで負け一方向に外れる。CrownR で先に測る
- [斜面の走りは道のりで割り、丈の中ほどで継ぐ](slope-run-walk-by-arc-not-horizontal.md) — 水平割り+傾けは隙とめり込みを同時に出す。GroundPolyline/PlaceOnChord
- [測って置く。事後に寄せる関数を持たない](measure-dont-nudge.md) — 帯の頂点では門柱が消えて偽の穴。閉じは三角形で測る
- [段を跨ぐ渡廊下は区間に割る](roka-dan-step-joint.md) — 段の柱は低い側。折れ目に 0.19m の口(雨押えの部材が無い)
- [設計面を地形へ写す二つの罠](grade-transfer-cliff-and-dropped-cells.md) — 石垣の見え面を双一次で跨がない・縮めた設計面の外に前の巡の切盛が残る
- [区画の線を動かすと前の造成が隣に残る](prev-grade-left-in-neighbor-after-parcel-move.md) — Stage1_Grade(prev) が類型の区画も戻す。隣の塀が浮く恐れ
- [造成は変わった段だけ流し直す](regrade-only-the-changed-block.md) — 全面だと築山と池が平らに戻り掘り直せない
- [番所はピボットが奥行の芯・部材は片手](bansho-pivot-and-protrude.md) — protrude は躯体の外面の越える量。対に振らないと袖塀へ 0.22 めり込む

- [帯割り屋根は床へ据える](banded-roof-sits-at-floor.md) — FBX が軒高を焼き込み済み。寄せ直すと 0.71m 浮く。⚠ 渡廊下と当たる
- [園路の敷きはメッシュ。スプラット不可](gravel-band-mesh-not-splat.md) — alphamap 4.0 m/px。巻きは上から見て時計回り

- [透塀の段の境は両側 c で口 0.18m](sukibei-step-ends-both-c.md) — 一直線の継ぎ目は端 n(ContinuesStraight・1818_nn)。検査は腰の断面で
- [透塀の隅は kadoFrom で引き、run の群に入れない](pitfall-sanno-sukibei-kado.md) — kind は null。群に混ぜると偽の 0.29m 芯ずれ 8 本

- [山王の社叢は「数え方」が入れ物を決める](sanno-shaso-counting-and-bake-gap.md) — 低木はGameObject・名指しは群の外・旧Keidairinは群ごと退避。焼き出し7点は `{size}` のまま

- [一体で焼いた駒は材(サブメッシュ)の名で躯体と屋根を分ける](one-mesh-part-split-by-submesh.md) — BodyBelowRoofAt は一層目だけ。層を問わないのは BodyExRoofAt
- [塀と足元の石垣は同じ従属値で解く](base-and-wall-share-one-dependent-value.md) — 片方だけ実測にすると塀の下が 1.38m 途切れる
- [水が乳白色・汀に白い縁はシェーダの既定値](water-defaults-are-for-deep-ponds.md) — 深さ4m前提の _DepthFade/_ShoreWidth。Depth/Opaque は無実
- [参道の起点を門の実面へ移すと奥の棟が押し出される](jisha-maeniwa-origin-pushes-out-mune.md) — 前庭 1.8→6.6m と引き換えに成満寺が 3/4→2/4。本堂は退かない
- [本堂と山門は Body(withRoof:false) が屋根を落とさない](honden-body-does-not-drop-roof.md) — 軒と壁体を出し分ける分岐が黙って無効になる。頂点数で先に検める
- [庫裏の SmallHouse は 14.5×10.5m で本堂並み](jisha-kuri-smallhouse-is-14m.md) — 狭い境内の「収まらず未建」は離れを緩めても直らない。部材の側の話
- [口の縁は門の実メッシュで測る・端は点で取る](run-end-at-opening.md) — 射影だけだと横のずれが落ちて 0.822m の口。柱物は帯でなく断面(SectionAt)
- [GetDetailLayer/GetHoles は寸法を [w,h] と偽る](terrain-detail-array-dims-lie.md) — 中身は [y,x]。正方でない範囲は DetailBlock で読み直す
- [筋割りの Contact は平らな面どうしを見落とす](contact-cells-miss-flat-faces.md) — 柱と礎石で屋形が 1.93m 沈んだ。鉛直は RestOn(面で測る)
- [斜めの隅の駒は「回廊」で測る](corner-piece-corridor-not-projection.md) — 全頂点の射影だと 1.13m の口が残る。DobeiProfile→BodyAt→CorridorSpan
- [流したら計測より先に書き戻す](writeback-before-measuring.md) — 途中の reload の間に claim が他の窓へ移り書き戻せなくなった
- [留めの継ぎ目は口0でも線に沿ってずれる](miter-joint-slides-along-cut.md) — 弦で据えて解消。焼く一覧は相手の居ない端を切らない(器と規則を揃える)

- [袖の groundHi の上げは 1.41m で切れる](sode-groundhi-lift-limit.md) — 女坂5駒が建たず。袖が建っても踏面の端に地表が被る(EDO-0421)
- [.meta の無い新しい FBX は「焼いていない」と出る](new-fbx-without-meta-reads-as-unbaked.md) — 部材方の直後は Refresh→remap→Stage。参照する未追跡 .meta もコミット
- [透塀の t の端は食い込み 0 で中門へ](sukibei-t-end-bite-zero.md) — ClipRunEndsToGates の halfT は bite。0.30 入れて全駒 1725 で倒れた
- [自作の木の FBX は地形の木として無効](own-tree-fbx-invalid-as-terrain-tree.md) — 根に MR も LODGroup も無く1本も描かれない。TreePrototype.Validate で先に検める
- [穴と皮の罠](terrain-holes-and-skin-traps.md) — 穴の升の地形の木は消える・地形のシェーダの材質は黒・艶で白く光る。木の升は開けない
- [Castle Wall の見え面は局所 −X](castlewall-face-is-local-minus-x.md) — 山王の土留め 162/233 駒が法の面を高い側へ。FaceSide/WallFaceRise で測る
- [裏込めの皮は退役・原因は殻の石垣の底の測り違い](backfill-skin-needs-three-limits.md) — 鉛直な見え面で底が天端に化け偽の隙4510。WallBottom で15
- [石垣の隅は区間の端ごとに・T 字の継ぎ目・二段築の下段](run-corners-seams-and-tiers.md) — PlaceRunCorners/PlaceTierBelow。控えは外向きの駒で・基壇の向きは低い地盤で測り直す
- [野面の土留めの罠](nozura-wall-traps.md) — 見え面は局所+Z・殻の石垣は光線で測る・足元の溝は天端の帯(CREST_BAND)で解消・背の帯の溝は据えで消えない(前が0.4〜0.75飛び出す)・Stage7 の順
- [袖の根入れは丈で取る・埋まる隅は先に測る](sode-neiri-and-buried-crest.md) — 足元は設計面で測る(皮は嘘)。男坂も 3.20 を焼いた。25.94 の隅は古い読み

- [法で切った段石・袖の差し替えの罠](batter-cut-parts-measure-and-check.md) — 突き合わせの幅は縮尺を見ない・袖の目地が偽の口・女坂の足は斜交で切れない
- [短い返しは票が割れて裏返る・袖は run の走る段だけ・別 run の出隅を芯で測ると入隅と誤る](short-return-tie-and-sode-extent.md) — RunLowHand/OverlapAlong/ShortSegConvexEnd。段の小口は中ほどで突き付け(跨ぐ段は解けない)

## 測り方・関門

- [Contact の筋 0.1m は疎な駒で偽の隙](contact-cell-too-fine-on-sparse-meshes.md) — 段石・袖で「測れず/0.015」。0.25m で測る。女坂の曲がりの袖の口は別件
- [段石の浮きは袖に塞がれない端だけで数える](dan-float-read-behind-sode.md) — 底−地表は男坂で 0.43m 出るが袖の裏の空洞
- [当たりは棟の外形線の上で測らない](notch-seat-has-80mm-plate-under.md) — 線上は内と外を拾い分ける。廊下の側へ張り出す三角形だけに絞る
- [実メッシュの当たりは紙より 0.08m 低い](mesh-atari-is-lower-than-paper.md) — 葺き厚と垂れ。5点の中央値で測る
- [C#の検図関門が kansei を見ていなかった](csharp-review-gate-ignored-kansei.md) — python が⭕でも止まる。直した
- [bake_impl は指紋違いで焼ける欄まで書かない](bake-impl-carried-src.md) — 欄を足したら carriedSrc を残す。半分だけ焼かない

- [面の輪郭ぎわの残差は物差しの話](terrace-rim-residual-is-the-ruler.md) — 失敗点が全部1セル以内なら造成の欠陥でない。均すと段が埋まり崖に盛土
- [池が掘れていないの正体は水面の紛失と 2m 格子](pond-carved-but-water-lost.md) — ⛔掘り直さない。CreateNoCarve で水面だけ
- [作業場の書き戻しは台帳0件で黙る](koba-writeback-ledger-empty.md) — 段別の邸は本体が台帳に載らない。Convert(自邸名)で拾う
- [プレハブの grep で名が出ないのは正常](prefab-yaml-has-guids-not-names.md) — 参照は GUID。検めるのは LoadAssetAtPath で childCount

## 検査の読み方

- [退役した Stage が残ると検査が嘘の件数を出す](retired-stage-makes-fake-counts.md) — 449=1278−829 は別の母集団の引き算
- [退ける門と検査は同じ測りで](machiya-clash-gate-weaker-than-check.md) — 門だけ屋根を外すと検査でめり込み。揃えた犠牲は駒1個だけ
- [CheckScene は矩形の芯で測る](checkscene-center-vs-seat.md) — `seat` で据えた部材は永久に鳴る。⛔芯へ動かして0件にしない
- [天端の埋没の数えは法の根入れを拾う](crest-burial-count-picks-batter-face.md) — 4m の偽の埋没。TuckUnderCrest に見え面を渡し天端の帯だけ数える
- [UnderfloorGap は一体の駒で屋根を拾う](underfloorgap-picks-roof-on-one-mesh-parts.md) — 堂・鐘楼で 5〜7m の偽の浮き。底の頂点で測る
- [山王 Stage0 は今の Keidai・Sando を退避する](sanno-stage0-retires-live-groups.md) — 名木20本ごと非活性へ。建て直しは Stage1 から
- [門・柵の浮きは「床」で測る](gate-float-measure-on-bed.md) — 土留めの天端に載る隅は地表で嘘の浮き。座は上限・浮けば床へ。Stage9 の後に S4/5
- [山王 Stage7 は縁の地形の木11本を毎回重ねる](sanno-stage7-edge-trees-duplicate.md) — 矩形の等号が float 往復で外れる。a07d0d1b で解消(取り残し0を確認 2026-09-23)
- [社叢QAのカメラ②は赤坂では宝蔵院の門の中](sanno-shaso-qa-camera2-inside-gate.md) — 撮る間だけ門+十坊の板塀 3_4f/4b ほか計52個を消す。カメラは動かさない
- [山王 Stage6 は Clear の後に指紋を検める](sanno-stage6-clears-before-fingerprint.md) — 落ちると社殿が空。並行の指図書きが済むまで bake を見張る
- [地形の detail/holes の塊は寸法の名札が逆](terrain-detail-array-dims-lie.md) — GetDetailLayer/GetHoles の配列は行優先。非正方の塊は組み直してから触る(EDO-0274)
- [法の足元の土の縁は底の読み違い](batter-toe-read-as-bottom.md) — 駒の底は根入れ済みだった。皮の塞ぎが法の途中を底と読む。段ごとの値で追う
- [見え面の足元の山形は外形の中の節点](wall-foot-ridge-from-nodes-under-hull.md) — 皮が近くの点を地形のまま描いた。CleanAt・差で混ぜる・Stage9 は6回走る
- [盛土の床・基壇の向き・設計面の縁の溝](fill-only-floor-and-base-facing.md) — fillOnly を皮の面にしない・BlockOutward・DesignOut は地形で埋める
