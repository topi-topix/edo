# Memory Index — edo-toryo(棟梁)

実装中に踏んだ非自明な罠だけ。手順はスキル、不変則は CLAUDE.md、指図は docs/Sashizu が正典。

## Unity MCP の罠

- [書き戻しは必ずタイムアウトする](pitfall-writeback-mcp-timeout.md) — 大きい邸のプレハブ。⛔再送せず mtime で判定
- [domain reload 後に bridge が消える](pitfall-bridge-drops-after-domain-reload.md) — 約2分。status と Editor.log で見る・古い port で「instances なし」が一回おき
- [再生中に建てるとシーンは消える](playmode-discards-scene-edits.md) — isPlaying を先に聞く。資産(プレハブ・地形)への書き込みだけ残る
- [30秒を超える execute_code は6回走る](akasaka-open-resent-six-times.md) — 赤坂・作業場を開く・重い計測。menu の赤坂へ戻すも6回開く・計測は割ってファイルへ
- [execute_code の replay は履歴の番号](execute-code-replay-index-is-history.md) — index=0 で前の Stage が再び走った。⛔replay せず送り直す
- [SkinGapTable の計測は6回走り、その間に claim が移ると空振る](skin-gap-table-reruns-and-lost-scene.md) — 78秒×6。頭で GN の有無を返させる
- [タイムアウト後は read_console で待つ・池の斑は水を消して切り分け](wait-on-timeout-with-cheap-mcp.md) — sleep は門番が止める。軽い MCP は main thread が空くまで返らない
- [長い Stage は印のファイルで再送を止める・狙いだけの Converge は2巡](long-run-guard-and-soft-only-converge.md) — delayCall は発火せず。active scene を先に聞く
- [隅部材の remap の menu は Kado 89 本を再 import して何巡も回る](remap-menu-reimports-all-kado.md) — 新しい FBX が少なければ1本ずつ remap

- [start --unity が通っても claim が付いていないことがある](pitfall-unity-claim-not-verified.md) — status で「資源: unity」を見るまで MCP を叩かない・渡された直後の引き取り(compile_wait 前に読み直す)
- [claim が無い巡は .cs も保存しない](cs-edit-is-not-claim-free.md) — 1行で他人の bridge が2分落ちる。用意は scratchpad の OLD/NEW 指示書へ
- [[MenuItem] の直下に関数を差すとメニューが化ける・子の印は親と動く](menuitem-drift-and-child-mark-moves.md) — 「4 囲い」が柵を建てていなかった。印 _axis が 0.117 ずれた
- [delayCall は他窓の reload で消える・指図の同時書き](delaycall-lost-and-shared-sashizu.md) — Stage は直に呼ぶ。流す前に指図の sha と impl の src を見る・着手前に kansei の reopen を見る
- [別セッションの赤い .cs で Editor アセンブリが焼けない](editor-dll-blocked-by-other-session.md) — dll の mtime が止まり CPU も静か。⛔refresh を繰り返さず console の error を読む

- [外周の石垣の見え面は区画の外・隣の棟の均しが節点を奪う](outer-wall-face-outside-parcel-and-shared-pads.md) — 皮の own が 2m 格子のまま描く。LevelPad は低い順
- [欄の上書きの直後は算出物の指紋で Stage1 が止まる](impl-fingerprint-after-yat-overwrite.md) — 食い違い0なら bake_impl --write。長い流しは印+txt で待つ
- [作業場が前の窓の邸で dirty・旧い退避は前の案の造成前](koba-left-dirty-by-other-window.md) — UnwrittenIn を最初に見る。他邸の書き戻しは分類器が止める→返す

## 部材の据え方

- [欄の書式が変わると Stage が「読めない」で黙って退く](return-lost-when-sashizu-text-format-changes.md) — 腰石垣の返しが returnEnd の書き換えで消えた。★読めない を grep
- [起こし直した指図の欄の形と旧い隅](redrawn-sashizu-shapes-and-stale-joints.md) — poly/pts/place文字列で KeyNotFound・谷底に旧い kado・DanPlan の段上限は柔らかい

- [綴りで部材を選ぶ器は似た新部材で倒れる](part-pick-by-spelling-breaks-on-new-sibling.md) — 小鳥居が焼けた途端に一ノ・二ノ鳥居が消えた。名指しの行を先に外す

- [回した境内では方位も uv も枠の回りを足す](rotated-grid-directions.md) — 山王 5.5°。W() と FaceYaw が落として門が建たず社殿が元の軸に残った
- [正面のローカル軸は部材ごとに違う](front-axis-differs-per-part.md) — 山王 社殿5棟=+X/堂宇10棟=+Z。yaw=front−axis.front(EdoBuild.FaceYaw)
- [partFrom は2書式・フォルダを決め打ちしない](partfrom-two-spellings.md) — Own.呼び名は EdoAssets.OwnPath で解く。鐘楼鼓楼は Models/Jisha
- [partFrom の `4.5f` が 0 に化けた・差し替えは Place の後に旧を消す](ownpath-float-suffix-and-destroy-before-place.md) — OwnF を直した(EDO-0438)
- [接地は格子点でなく描かれている地表で測る](contact-must-use-drawn-surface.md) — 2m格子で斜面に ±(1m×勾配) の嘘。嘘の不合格と嘘の合格が同時に出る
- [幹の足は樹皮の底の輪か 0.02m 上の断面で測る](trunk-foot-band-catches-foliage.md) — 0.3m 帯は紅葉・蔓で 0.39m 外れた。蔓は最も低い茎
- [SeatPlant は斜面の木を浮き上限で沈める](seatplant-float-cap-buries-slope-trees.md)・[既定で格子を引く](seatplant-reads-grid-not-skin.md) — 埋没15〜21m/皮の後は Drawn() を渡す
- [榎・椋は SeatPlant が NaN](seatplant-nan-enoki-mukunoki-noki.md) — LOD の子名の "noki" を IsRoofName が屋根と見る。篩を EdoBuild で直す
- [退けた群の下に建てると子が非活性で測れない](retired-group-makes-children-unmeasurable.md) — SeatPlant 全数 NaN。親を起こす。躯体の寸法は断面で(BodyFootprintLocal)
- [埋没を地形を掘って消す器は連鎖する](dig-to-unbury-cascades.md) — 山王 0.53/0.65 の埋没で3通り試し全部戻した。納めの話
- [急斜面の埋没は据え直しで浮きへ移るだけ](bury-becomes-float-when-relief-exceeds-tolerance.md) — 起伏>許容の和なら据え方の話でない。上げる前に埋没+浮きを測る
- [間引いた接地は沈む側にしか外れず、上限は足元の起伏](seat-sampling-error-bounded-by-relief.md) — だから起伏で選んで細かく据え直せる。平地は無料
- [段の位置は指図の pos でなく実地表から解く](stair-position-is-terrain-dependent.md) — 落ち際は擦り付けで2〜4.5m。許容は段自身の蹴上
- [比は意図でなく据わった数で決まる](ratio-on-intent-vs-seated.md) — 樹冠の大きい層が据わりで負け一方向に外れる。CrownR で先に測る
- [斜面の走りは道のりで割り、丈の中ほどで継ぐ](slope-run-walk-by-arc-not-horizontal.md) — 水平割り+傾けは隙とめり込みを同時に出す。GroundPolyline/PlaceOnChord
- [測って置く。事後に寄せる関数を持たない](measure-dont-nudge.md) — 帯の頂点では門柱が消えて偽の穴。閉じは三角形で測る
- [段を跨ぐ渡廊下は区間に割る](roka-dan-step-joint.md) — 段の柱は低い側。折れ目に 0.19m の口(雨押えの部材が無い)
- [設計面を地形へ写す二つの罠](grade-transfer-cliff-and-dropped-cells.md) — 石垣の見え面を双一次で跨がない・縮めた設計面の外に前の巡の切盛が残る
- [区域外を退ける群の降り方・写し戻しの罠](retire-outside-walk-and-restore.md) — 子1つの入れ物を駒と読み338本消した。写し戻しは ConvertToPrefabInstance で繋ぐ
- [区画を引き直すと焼いていない算出物の欄が線の外に据わる](stale-impl-after-parcel-redraw.md) — 岡部の杭列 484 個が 4〜11m 外。RetireOutsidePoly で退ける
- [区画の線を動かすと前の造成が隣に残る](prev-grade-left-in-neighbor-after-parcel-move.md) — Stage1_Grade(prev) が類型の区画も戻す。隣の塀が浮く恐れ
- [均しの縁の節点・皮の PIN の被り・閉じの検め](pad-edge-nodes-outside-face-and-pinned-skin.md) — PadRim・PIN_TUCK・基壇を数える・積みを地表で測らない
- [LevelPad に区画を渡すと段の土留めを越えて下の面を盛る](levelpad-crosses-terrace-wall.md) — 棟の建つ面の poly を渡す。均した後は heightmap の差を見る
- [造成は変わった段だけ流し直す](regrade-only-the-changed-block.md) — 全面だと築山と池が平らに戻り掘り直せない
- [筋の最小−最大は全筋で浮く・門は皮の前に据わる・返しの外形の中は上げない](strip-min-max-leaves-float-and-gate-seat-before-skin.md) — 柱ごとに測る・SeatGamaeOn・TopLanding 面
- [門長屋の口の芯はローカル +X で len/2−gc](nagaya-mon-gate-offset-axis.md) — 口の s から gc を出すのは据えた後の向き(sSign)で。奥の壁の抜けで測る
- [土井の表門は旧い版・札の front は出格子を拾う](doi-omotemon-old-part-and-front-by-foot.md) — 躯体11.18/番所が右/切り下げ無し。外面は foot で寄せる・新FBXは1本ずつ remap
- [番所はピボットが奥行の芯・部材は片手](bansho-pivot-and-protrude.md) — protrude は躯体の外面の越える量。対に振らないと袖塀へ 0.22 めり込む

- [土井の附属屋は Body に軒が残る・座は格子で起伏](doi-service-eaves-in-body-and-za-not-flat.md) — 離れは帯 0.15〜1.8 の Face で。布石で座が +0.36 上がる
- [帯割り屋根は床へ据える](banded-roof-sits-at-floor.md) — FBX が軒高を焼き込み済み。寄せ直すと 0.71m 浮く。⚠ 渡廊下と当たる
- [小段の盛り残りは Stage1 から流せば消える](backbench-residue-cleared-by-stage1.md) — 岡部 S1 は graded へ上書き。返しの前の尾根は壁の下の節点を 2m 格子が描く物
- [土留めに埋まった地形の木が皮の穴を止める](tree-buried-in-wall-blocks-skin-hole.md) — 尾根と背の隙の正体。RetireTreesInParts。穴の升を先に刷る
- [皮を庭の後に流すと池を埋める・印は巡ごとに名を替える](skin-after-garden-fills-pond.md) — CutEdgeSkin faceKeepOut に庭の矩形
- [園路の敷きはメッシュ。スプラット不可](gravel-band-mesh-not-splat.md) — alphamap 4.0 m/px。巻きは上から見て時計回り

- [透塀の段の境は両側 c](sukibei-step-ends-both-c.md)・[隅は kadoFrom で run に入れない](pitfall-sanno-sukibei-kado.md) — 口 0.18m・継ぎ目は端 n・偽の芯ずれ 8 本

- [山王の社叢は「数え方」が入れ物を決める](sanno-shaso-counting-and-bake-gap.md) — 低木はGameObject・名指しは群の外・旧Keidairinは群ごと退避。焼き出し7点は `{size}` のまま

- [一体で焼いた駒は材(サブメッシュ)の名で躯体と屋根を分ける](one-mesh-part-split-by-submesh.md) — BodyBelowRoofAt は一層目だけ。層を問わないのは BodyExRoofAt
- [塀と足元の石垣は同じ従属値で解く](base-and-wall-share-one-dependent-value.md) — 片方だけ実測にすると塀の下が 1.38m 途切れる
- [水が乳白色・汀に白い縁はシェーダの既定値](water-defaults-are-for-deep-ponds.md) — 深さ4m前提の _DepthFade/_ShoreWidth。Depth/Opaque は無実
- [参道の起点を門の実面へ移すと奥の棟が押し出される](jisha-maeniwa-origin-pushes-out-mune.md) — 前庭 1.8→6.6m と引き換えに成満寺が 3/4→2/4。本堂は退かない
- [本堂と山門は Body(withRoof:false) が屋根を落とさない](honden-body-does-not-drop-roof.md) — 軒と壁体を出し分ける分岐が黙って無効になる。頂点数で先に検める
- [庫裏の SmallHouse は 14.5×10.5m で本堂並み](jisha-kuri-smallhouse-is-14m.md) — 狭い境内の「収まらず未建」は離れを緩めても直らない。部材の側の話
- [塀の腰で止まる端・6e が木戸を消す](run-end-at-wall-plinth-and-6e-kido.md) — 段ごとの当たりの最も奥へ。口は壁の法線でヤード側から測る
- [口の奥の土の壁は均していない坂](gap-cheek-is-unbuilt-kiritoshi.md) — profS だけの坂を誰も均さず。返しは地表で測ると裏返る(lowForce)
- [口の縁は門の実メッシュで測る・端は点で取る](run-end-at-opening.md) — 射影だけだと横のずれが落ちて 0.822m の口。柱物は帯でなく断面(SectionAt)
- [GetDetailLayer/GetHoles は寸法を [w,h] と偽る](terrain-detail-array-dims-lie.md) — 中身は [y,x]。正方でない範囲は DetailBlock で読み直す
- [低ポリの駒を頂点の窓で測ると空になる](lowpoly-vertex-window-empty.md) — 階段廊下が回しを誤り塀の端が点なし。材(BodyOfMat)か光線(ReachToBodies)で
- [筋割りの Contact は平らな面どうしを見落とす](contact-cells-miss-flat-faces.md) — 柱と礎石で屋形が 1.93m 沈んだ。鉛直は RestOn(面で測る)
- [斜めの隅の駒は「回廊」で測る](corner-piece-corridor-not-projection.md) — 全頂点の射影だと 1.13m の口が残る。DobeiProfile→BodyAt→CorridorSpan
- [流したら計測より先に書き戻す](writeback-before-measuring.md) — 途中の reload の間に claim が他の窓へ移り書き戻せなくなった
- [留めの継ぎ目は口0でも線に沿ってずれる](miter-joint-slides-along-cut.md) — 弦で据えて解消。焼く一覧は相手の居ない端を切らない(器と規則を揃える)

- [袖の groundHi の上げは 1.41m で切れる](sode-groundhi-lift-limit.md) — 女坂5駒が建たず。袖が建っても踏面の端に地表が被る(EDO-0421)
- [.meta の無い新しい FBX は「焼いていない」と出る](new-fbx-without-meta-reads-as-unbaked.md) — 部材方の直後は Refresh→remap→Stage。参照する未追跡 .meta もコミット
- [透塀の t の端は食い込み 0 で中門へ](sukibei-t-end-bite-zero.md) — ClipRunEndsToGates の halfT は bite。0.30 入れて全駒 1725 で倒れた
- [自作の木の FBX は地形の木として無効](own-tree-fbx-invalid-as-terrain-tree.md) — 根に MR も LODGroup も無く1本も描かれない。TreePrototype.Validate で先に検める
- [穴と皮の罠](terrain-holes-and-skin-traps.md) — 穴の升の地形の木は消える・地形のシェーダの材質は黒・艶で白く光る。木の升は開けない
- [棟の背の城の石垣の3つの罠](back-plinth-slot-cut-and-oblique-aabb.md) — 天端の奥行1.4で長屋の下に0.89の溝(埋めの列)・2m格子は犬走りの切りを描けない・斜めの辺の外接箱は偽のめり込み
- [Castle Wall の見え面は局所 −X](castlewall-face-is-local-minus-x.md) — 山王の土留め 162/233 駒が法の面を高い側へ。FaceSide/WallFaceRise で測る
- [裏込めの皮は退役・原因は殻の石垣の底の測り違い](backfill-skin-needs-three-limits.md) — 鉛直な見え面で底が天端に化け偽の隙4510。WallBottom で15
- [張り出す石段の袖の笠は入隅の天端で潰れる・垣の口の端は 0.2 ずれる](stair-sode-crest-vs-kasa-and-fence-gap-end.md) — K_Kuruwa 笠 0.003。PlaceIshidanSodeRow・PlaceCrestFence の許し 0.3
- [石垣の隅は区間の端ごとに・T 字の継ぎ目・二段築の下段](run-corners-seams-and-tiers.md) — PlaceRunCorners/PlaceTierBelow。控えは外向きの駒で・基壇の向きは低い地盤で測り直す
- [野面の網の罠](nozura-net-face-crest-end.md) — 見え面は設計面と天端の列の控えで・端の行は口の地表・端の光線は前の地表まで・打ち切りは低い端だけ
- [斜めの取り合いは相手の面の法線で測る・法の楔](oblique-contact-and-batter-wedge.md) — 走りの筋では −0.27 の嘘。入隅の鉛直な小口は縮めても法へ入る
- [皮の土の箱は小段の端の法の回り込み・溝の尾根は 1m 格子](bench-end-slope-spills-and-3b-opposite-wall.md) — RaycastAll と BackBenchAt を点で刷る
- [重ねて埋める短い run は突き付けで駒 0](overlap-run-abuts-to-zero.md) — NozuraSeg.noAbut。2b のログの「駒 0」を grep
- [城の石垣の法の帯は 3b の候補に入らない](castle-batter-no-up-tris-skips-3b.md) — 見え面 ny 0.24 で TopRaw NaN。UnderFace で足す・外形の中だけで足すと背を掘る
- [野面の見え面の土の帯は皮の辺](skin-edge-across-nozura-face.md) — 抜けでなく天端下の点と足元の点を結ぶ皮の三角形。光線で駒/皮/地形の先着を数える
- [野面の土留めの罠](nozura-wall-traps.md) — 見え面は局所+Z・殻の石垣は光線で測る・足元の溝は天端の帯(CREST_BAND)で解消・背の帯の溝は据えで消えない(前が0.4〜0.75飛び出す)・Stage7 の順
- [袖の根入れは丈で取る・埋まる隅は先に測る](sode-neiri-and-buried-crest.md) — 足元は設計面で測る(皮は嘘)。男坂も 3.20 を焼いた。25.94 の隅は古い読み

- [土留めの端を袖の外面で止める](run-end-at-sode-face.md) — RunEndAtFace は9箇所に当たる。一直線の袖は外す・43°は切った駒・隅の腕が袖へ入る
- [法で切った段石・袖の差し替えの罠](batter-cut-parts-measure-and-check.md) — 突き合わせの幅は縮尺を見ない・袖の目地が偽の口・女坂の足は斜交で切れない
- [積み止めの駒は FaceWallToLine で裏返る・継ぎ手は端の帯で・隅の返しの腕の向きと定尺](tome-piece-facing-and-joint.md) — 天端の差0は隠れた隣と比べた値。faceNear は seg.face を先に・armFixed+W/2
- [二重折れの出隅は一つの駒](double-fold-kado-one-piece.md) — 中の区間の1駒が消え折れ2が黙って飛ぶ。PlaceRunKado2
- [短い返しは票が割れて裏返る・袖は run の走る段だけ・別 run の出隅を芯で測ると入隅と誤る](short-return-tie-and-sode-extent.md) — RunLowHand/OverlapAlong/ShortSegConvexEnd。段の小口は中ほどで突き付け(跨ぐ段は解けない)
- [野面 第3巡の測りの罠](nozura-round3-measure-traps.md) — 最も離れる向きの Contact は段石×隅 0.17 を見落とす・外形の中の面の無い点で皮が溝・法切り駒の見付は足元の面で

- [暗渠の蓋が測れない・足元を笠の裏と読む](ankyo-lid-and-foot-under-overhang.md) — MizoPieceOf は板で ok=偽。足元は LowestFootAt(厚み0.3・底の開いた腰)

- [敷石の面取りの口・門の上向きの面の下の皮・同じ高さの重なり](fumiishi-chamfer-and-floor-cover.md) — 天端の帯で口を閉じる。門の面は深さ 0.15 で拾う。重なりは下の側を 0.01 ずつ

- [板塀を天端・法肩に据える罠](panel-on-crest-and-shoulder-traps.md) — 帯は天端の最高で・法肩の下りは描かれた地表で・Itabei5 は 3m 未満に割れない
- [水平の袖の継ぎ目は面取りの下で・鉛直な端は法の隅で楔](flat-sode-chamfer-and-batter-wedge.md) — 天端の帯では V を 0.015 の口と読む。男坂 052f × kado1 は帯の下で 0.05/0.2m 入る
- [野面の入隅の土の楔・L字の隅の天端・段違いを継がない規則](nozura-concave-wedge-and-kado-crest.md) — 入隅は天端の帯で触れて下は埋める・crestOf は隅で 0.4〜0.6 低く読む・共有の型は前の巡のログと diff
- [法尻の背の小段は切る BackBench・継ぎ目に被りが残る](toe-bench-cut-and-joint-cover.md) — keep は部材ごとの外接で。天端の帯の最大で引くと継ぎ目の低い石に 0.2 被る
- [endRaise は tallEnd に回る・皮へ均しを写しても残る埋没は地形の節点](end-raise-and-pad-in-skin-design.md) — 薪蔵は米蔵が節点を上書き・3b が 58 分
- [段石×野面は全端を包絡で・野面を焼き直したら跨ぐ端の za を測り直す](nozura-envelope-and-rebake-za.md) — 中ほどの中央値は石の出入りを均して d 0。焼いた組が 0.06 外れた
- [隅の腕を袖の実測で選ぶ・足元の溝は cap の掘り・空きの点の塞ぎ](kado-short-arm-and-foot-groove.md) — KadoShortArm は詰めた後の袖で測る。天端の四角い抜けは部材
- [別の駒の天端・段に被る隅石を退ける](crest-of-other-and-step-yield.md) — 法の足が下の天端に載る所で皮が天端に張り付く。YieldWallsToSteps。MeshInside は一つずつ
- [MidSection は世界座標・内外は MeshInside で](post-board-run-and-mesh-inside.md) — 重ねて板が 438m 飛んだ。総当たりの光線は 25 分ふさいだ(二度目)

- [袖の坂・小口の土の検めは SkinGround で盛りを読まない・3b はメモリで落ちる](sode-check-skinground-and-dropped-run-residue.md) — Drawn で測る・hold・2b の後に書き戻す

- [袖の背に沿う返しの隅は法で袖へ入る](kado-arm-along-sode-back-batter.md) — 見える所は面一でも W0.31/E0.47 入る。解くのは返しの腕を一辺切った Kado90(部材)

- [門の背の突き付けは札で・2m格子の坂の石段・印の名は共有](gate-back-abut-through-passage-and-steps-on-graded-ramp.md) — 光線は門の口を抜けて扉まで伸びた。踏面の坂上の端を地表へ(SlopeStepsAt)
- [城の石垣の口が二つ近いと間に 2m の駒が芯で据わる](castle-run-narrow-pier-between-gaps.md) — 土井の扉口と潜戸の間 0.459m。部材か指図へ差し戻す
- [棟の下の均しを直しても埋没が動かないのは皮・垣の残る浮きは目地](levelpad-rim-and-skin-hides-terrain.md) — Drawn と地形の両方で測る。計測は組み立て1回で全駒
- [光付けは2次元で上げる・remap 済みでも材 null](scribe-2d-and-stale-fbx-material.md) — 列の窓の最大は法肩で浮き目地で食い込む。桃色は ForceUpdate で再 import(長屋12本も 10-03)

- [長屋は全幅で並べると躯体が開く・御殿は縁の下に当たり無し・棟門は札で・描かれた法尻](nagaya-body-vs-gable-and-rendered-toe.md) — FitBodyToSpan/PlaceGamae/toeRender
- [石垣の足元の盛りは2m格子の描き・造成では消えない](wall-toe-mound-is-grid-not-grading.md) — 足〜背 2.15m < 格子。縁の皮が要る
- [袖の背の小段は段の境の脇だけ 0.4 余る](sode-back-bench-cap-conflict.md) — 上限でも格子でもなかった。狙いと描画を同じ点で並べてから名指す
- [皮を足す邸は土留めを皮の地表で据える](wall-seat-on-skin-ground-not-grid.md) — 格子の盛りに載せたまま削ると 0.5m 浮く。岡部 3b は約5分
- [見付を天端の縁の 0.3m 前で測ると法の駒の下を読む](expose-measured-under-batter.md) — 丈不足で浮き、皮が歯形へ盛り土の歯。足元の出の前で測る
- [端を切った練塀の駒は片方の端にしか合わない](dobei-kiri-hand-and-radian.md) — 849_L は SE_Hei の始めで手が逆。Atan2 はラジアン
- [相手の無い端の口は区画の線の楔](free-run-end-at-oblique-parcel-corner.md) — 岡部 辺0/辺24。伸ばすと区域侵犯・斜めの小口の部材
- [壁の口から張り出す石段は浮く・yAt が地盤と違う](stair-out-of-wall-and-yat-mismatch.md) — StackDownToGround・LevelPad で中央値へ
- [面の中の細い溝は小さい面として足す](trench-behind-nagaya-needs-face.md) — 地形を切っても設計の地盤を下げても皮が面の高さで埋め戻す。返しの低い側は lowHint で
- [段の土留めの3つの罠](dan-ishigaki-r3-traps.md) — BedTopAt は 8m まで・指図の文言の上書きで正規表現が 0・語だけの直しでも指紋で止まる
- [野面の端の納めは背の土で退く](nozura-end-rule-blocked-by-back-soil.md) — 端の見付は駒の走りで測る・背>天端の端は延ばしも見切り石も埋没で退く(普請方へ)
- [stepJoint は勾配の上限で解けない・隅の返しの腕は armBlock で](stepjoint-and-kado-return-traps.md) — 袖の run 1.4m に段 0.5。否定文の見切り石・Stage は ~call で予約
- [坂の袖・段石の背の窪み](slope-sode-flat-kado-and-end-specs.md) — 出隅は PAV・踊り場・低い端は face で名指す。皮の窪みは SkinTrace で段ごとに測る
- [腰の端の小段は 1:1 の法で切りが 1.0 を超える・石段の a/b は従属値](koshi-end-cut-exceeds-on-1to1-slope.md) — koshiEnd は5端とも退く。KaidanAB が atS から解く
- [野面の段の境の駒は H1.50 だけ・継ぎ目の下が抜ける](nozura-dan-piece-fixed-height.md) — 直線は H4.8 まで選ぶ。StackDownAtNozuraSteps で積み下ろす

- [地形の前後の差は資産の写しから採れる](terrain-diff-from-asset-copy.md)・[検証レンダの構図は残らない](render-camera-poses-not-kept.md) — int16 の塊を行で探す・構図は cams.txt

## 測り方・関門

- [練塀は下絵の seat で置かれ埋まる・天端の垣と S_Hei_20 の浮きは偽](dobei-seat-is-shitae-and-false-floats-r12.md) — 岡部 辺34 で 2.6m 埋没。浮きは光線の先着で確かめる・作業場の取り違え

- [偶奇の多数決の内外判定は野面で偽のめり込み](parity-inside-test-false-intrusion.md) — 袖×SW の隅 0.234 は偽。当たり0の向きが在れば外
- [悪化の申告はまず prefab を git で比べる](regression-claim-diff-prefab-first.md) — EDO-0437 の3件は駒が動いていなかった。郭の階の南の袖は EK の隅の腕の中(腕 −0.04 の隅が要る)

- [Contact の筋 0.1m は疎な駒で偽の隙](contact-cell-too-fine-on-sparse-meshes.md) — 段石・袖で「測れず/0.015」。0.25m で測る。女坂の曲がりの袖の口は別件
- [段石の浮きは袖に塞がれない端だけで数える](dan-float-read-behind-sode.md) — 底−地表は男坂で 0.43m 出るが袖の裏の空洞
- [当たりは棟の外形線の上で測らない](notch-seat-has-80mm-plate-under.md) — 線上は内と外を拾い分ける。廊下の側へ張り出す三角形だけに絞る
- [実メッシュの当たりは紙より 0.08m 低い](mesh-atari-is-lower-than-paper.md) — 葺き厚と垂れ。5点の中央値で測る
- [C#の検図関門が kansei を見ていなかった](csharp-review-gate-ignored-kansei.md) — python が⭕でも止まる。直した
- [bake_impl は指紋違いで焼ける欄まで書かない](bake-impl-carried-src.md) — 欄を足したら carriedSrc を残す。半分だけ焼かない

- [面の輪郭ぎわの残差は物差しの話](terrace-rim-residual-is-the-ruler.md) — 失敗点が全部1セル以内なら造成の欠陥でない。均すと段が埋まり崖に盛土
- [池が掘れていないの正体は水面の紛失と 2m 格子](pond-carved-but-water-lost.md) — ⛔掘り直さない。CreateNoCarve で水面だけ
- [作業場の書き戻しは台帳0件で黙る](koba-writeback-ledger-empty.md) — 段別の邸は本体が台帳に載らない。Convert(自邸名)で拾う
- [類型を何軒も建て直す作業場](typology-multi-parcel-koba.md) — 隣は20m以内だけ・残りは実体を足す。BuildParcel は自分で切り出すので wrote=0 が正常
- [並びの区画のログの浮きは後の造成で古くなる](typology-log-stale-after-neighbor-regrade.md) — 共有辺の地表が動く。建て終えてから数え直す
- [プレハブの grep で名が出ないのは正常](prefab-yaml-has-guids-not-names.md) — 参照は GUID。検めるのは LoadAssetAtPath で childCount

## 検査の読み方

- [検査の浮き・子0は測り方の読み違いのことがある](qa-misreads-stack-and-single-mesh-gate.md) — 積みを地表で測る・一体の門・皮の前の垣。相手を床に入れて測り直す

- [袖の脇の入りは見える地表で割る](sode-side-bite-below-skin.md) — 女坂の北の袖×回廊の出隅は全部 皮の下。MeasureSodeSideBites・裏の面の偽の入り

- [退役した Stage が残ると検査が嘘の件数を出す](retired-stage-makes-fake-counts.md) — 449=1278−829 は別の母集団の引き算
- [退ける門と検査は同じ測りで](machiya-clash-gate-weaker-than-check.md) — 門だけ屋根を外すと検査でめり込み。揃えた犠牲は駒1個だけ
- [CheckScene は矩形の芯で測る](checkscene-center-vs-seat.md) — `seat` で据えた部材は永久に鳴る。⛔芯へ動かして0件にしない
- [天端の埋没の数えは法の根入れを拾う](crest-burial-count-picks-batter-face.md)・[UnderfloorGap は一体の駒で屋根を拾う](underfloorgap-picks-roof-on-one-mesh-parts.md) — 4m・5〜7m の偽。天端の帯だけ数える・底の頂点で測る
- 山王の Stage の罠: [Stage0 は Keidai・Sando を退避](sanno-stage0-retires-live-groups.md)・[Stage7 の縁の木の重ね(解消)](sanno-stage7-edge-trees-duplicate.md)・[Stage6 は Clear の後に指紋](sanno-stage6-clears-before-fingerprint.md) — 建て直しは Stage1 から・bake を見張る
- [門・柵の浮きは「床」で測る](gate-float-measure-on-bed.md) — 土留めの天端に載る隅は地表で嘘の浮き。座は上限・浮けば床へ。Stage9 の後に S4/5
- [社叢QAのカメラ②は赤坂では宝蔵院の門の中](sanno-shaso-qa-camera2-inside-gate.md) — 撮る間だけ門+十坊の板塀 3_4f/4b ほか計52個を消す。カメラは動かさない
- [法の足元の土の縁は底の読み違い](batter-toe-read-as-bottom.md) — 駒の底は根入れ済みだった。皮の塞ぎが法の途中を底と読む。段ごとの値で追う
- [法の途中を底と読む歯・石段の前の土・外周の石垣を皮へ渡す](foot-bottom-batter-and-stair-front.md) — TopIndex.FootBottom。点の Bottom/WallBottom を reflection で刷る
- [見え面の足元の山形は外形の中の節点](wall-foot-ridge-from-nodes-under-hull.md) — 皮が近くの点を地形のまま描いた。CleanAt・差で混ぜる・Stage9 は6回走る
- [盛土の床・基壇の向き・設計面の縁の溝](fill-only-floor-and-base-facing.md) — fillOnly を皮の面にしない・BlockOutward・DesignOut は地形で埋める
- [総当たりの計測は Unity を1時間ふさぐ](brute-force-measure-hangs-unity.md) — 升の索引+印で打つ。RayToBodies は1呼び出し100本まで・mesh.vertices を輪の中で呼ばない(四度目 10-05)
- [落とした後の Stage9 は空の皮を焼く](unity-kill-leaves-holes-without-skin.md) — 穴は地形・皮はシーン。null の皮には最新の資産を差してから流す
- [皮の段プレハブのメッシュが消えると S1 が穴を塞がず 4b が空の皮](skin-mesh-missing-leaves-holes-open.md) — S1 の塞いだ升が前の巡の穴の数と違えば 4b の前に止まる
- [線の上の基壇・柵は区画外に出る](line-sitting-pieces-pivot-out.md) — float 0.25mm・端の控え・芯置き。材 null の一体駒は屋根を躯体と数える
- [区画の辺に沿う城の石垣・長屋の4つの罠](castle-run-along-parcel-edge-traps.md) — s の丸めは VTX_TOL・90°超の出隅は PullAlongInside・駒の実長>送り・疎な駒は筋 1.0
- [隅の腕は短辺を越えて区画外へ出る](kado-arm-overruns-short-edge.md) — 岡部 P2〜P4 が 0.7〜1.3m 外。閉じの検査は見ない・駒の頂点を PIP
- [旧案の一括削除は分類器が止める](bulk-delete-denied-by-auto-mode.md) — 施主の指示でも役経由は不可。一覧まで出して施主の許可を仰ぐ
