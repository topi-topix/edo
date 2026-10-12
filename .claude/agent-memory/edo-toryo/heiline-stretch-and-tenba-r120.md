---
name: heiline-stretch-and-tenba-r120
description: 岡部 const.heiLine(芯線の控え d を一続きで一つ・天端の線を段の点だけ)の第120巡の罠 ── d は c の後でしか解けず基壇を二度据える・床へ据えるのを区間の組にしないと線が割れる・Runs の線は同じドメインでしか生きない
metadata:
  type: project
---
2026-10-12 EDO-0502 第120巡(辺19〜24 で試し)。

1. **d は基壇の実測 c の後でしか解けない**(c = PlaceCastleRun が測る・_kidanCe)。一方 基壇の天端は天端の線に従う ⇒ Stage2 は
   PlaceIshigaki → HeiLineFace(d)→ 隅 → HeiLineTenba → PlaceIshigaki をもう一度(c は倍率で決まり二度目も同じ ── 違えば ★ を刷る)。S1+S2 は約 11 秒。
2. **SeatHeiOnBed が駒ごとに床へ据えると、平らに決めた区間の中に天端の段が出る**(SinkGroupToBed は最も浮いた当たりへ組ごと動かす)。
   ⇒ 天端の線の run の駒は区間の番号(lineSec)を鍵に一つの組・頂点で段を切らない隅も同じ組(HeiLineKadoKey)。さらに座に据える(上げも下げもしない)。
3. Runs の lineS/lineSeat は static の struct 配列に載る ⇒ **ドメインが替わると消える**(3d の SeatHeiOnBed が駒ごとへ戻る)。
   S2 から 3d まで compile を挟まず流す。別の巡で 3d だけ流すなら先に S2 を流す。
4. 造成の面は塀の芯の所で横に 1:1.5 ほど内へ上がる(辺23: 線から 0.5m 10.36・2.5m 11.70)── 区間の座を地盤の最小にすると内の側は横の勾配ぶん埋まる(前からの姿)。
   辺23 s17〜22 に 11.47 の平らな出っ張り(5m)があり、天端の線が 0.55 上がって下がる。正体は未確認。
5. **段を頂点の近くの点で切ると隅の腕の中に 0.15 の切り駒だけの区間ができる**(S_Hei_18_5_0 T01)。⇒ 段の点は隅の塊(FitKado が測った腕の実端面の間)の端か、
   塊の端から minLen 以上離れた所だけ(HeiTenbaSteps の armIn/armOut)。そのため天端の線は FitKado の後に解き、基壇はその後に据え直す。
6. **段の点の隅を単独で床へ据えると 3d で溝の脇の低い当たりへ落ちる**(Kado_P24 −1.29)・SeatKadoToRuns は外接の箱で隣の区間の先の駒を拾う(P22 0.5 低い)。
   ⇒ 隅も区間の組で座に据え、SeatKadoToRuns・AlignInubashiri・KeepInsidePoly は天端の線の run を通さない(OnHeiLine)。外面は据える時に NeribeiPanelRun(faceIn)が壁面で合わせる。
7. 流している間に普請奉行が指図をコミットすると S1 の頭で「算出物が今の指図から焼かれていない」で止まる ⇒ bake_impl --write と --graded-bin を焼き直し、Reload() してから流す。
8. **KadoFace は 2cm 未満の寄せを捨てていた**(不感帯 0.02・2026-10-12 第120巡の続き)── P20(折れ 1.48°)の隅が 0.014/0.020 内へ残り、直線(外面 1.050)と横に 2cm ずれた。
   不感帯を 1mm へ(EdoBuildKado.KadoFace)。芯線の頂点の隅は PlaceKado が据える時に面を合わせ、FitKado は腕の実端面だけ測る(OnHeiLineVertex)。
9. **段の点の真上の「浮き」0.5 は台の石垣の石の端の面**(Castle Wall の天端の端は 0.25m で 0.2〜0.5 落ちる)── 段の点で上の区間の石と練塀が同じ s で終わると、
   床の測りが最後の頂点で石の端の斜面を読む。石の天端の起伏(11.29〜11.49)も同じ。足の浮きの数えは段の点の ±0.05 を分けて読む。
10. 天端の線の駒は座ちょうどに据える(NeribeiPanelRun の sink 0)── 既定の −0.10 の根入れで据えてから SeatHeiOnBed で 0.10 上げていた(後合わせ)。
11. **練塀の足は外面より 0.14 外から 0.69**(腰の笠 ishigaki・線から 0.91〜1.60 ── 壁面 1.05 ではない)。足の浮きは足の頂点(最下点 +0.05)の幅で測る(芯 +0.64 で測ると足の外の地表を読む偽の浮き)。
    辺19〜21 は c 0.25・控えの奥行 0.35 ⇒ 台の石垣の天端は線から 0.6 まで ⇒ 足は犬走りの土の上(台の天端に載るのは辺22〜24 だけ)。
12. **台の石垣の段の点の継ぎ目の切り欠き**(天端の端が落ちる V)の底の石の面を FillUnderFoot の「石垣の下は触らない」が拾い、Kado_P24 の足の下に 1.04 の穴が残った
    ⇒ FillUnderFoot に allowUnderFoot(節点, 足の底)── 凸包の中は「石が足の底を支える所(床 ≥ 底 −0.02)」と天端の前の縁 c+0.05 より前だけ除く。
13. FillUnderFoot の縁の上げの上限 0.10 は 0.25 格子で足の内の縁が節点の間に落ちる所で 0.04 浮かせた ⇒ 岡部は 0.30。
14. 辺23 s15.5〜22.5 の 11.47 の平らな出っ張り = TW_Nishi_Kado(mode toe・hi Nishi)の tw_fill_rule が西の平場の盛の法を野面石の天端 11.46〜11.49 へ持ち上げた面(sashizu_lib.tw_fill_rule)。
15. 待ちの見張りは「=== DONE」だけで止める(各段の見出しは**終わった後に**書くので「=== S3d」で止めると書き戻しの済みを 30 分見落とした)。
**How to apply:** 外周の残りへ広げるときは trial の範囲を広げるだけ。段の数は HL_TOL/HL_LAMBDA(棟梁の値・P)で決まる。関連 [[okabe-perimeter-rerun-order-and-neribei-measure]] [[graded-bin-stale-after-sashizu-commit]]
