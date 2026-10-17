---
name: r156-heiline-continuation-and-inner-wall
description: 岡部 第156巡 — tenba の「<組>_e<辺>」で天端の線を隣の辺へ続ける・長屋の混じる辺の c は塀だけで・塀の下の内向きの石垣は仮の四角で PlaceCastleRun・IshigakiHead が行を捨てる・長屋は座 −0.10 で据える
metadata:
  type: project
---
2026-10-17 EDO-0502 第156巡(S1→S2 だけ)。

1. **天端の線の範囲は trial の文だけでなく tenba の続きの欄でも延びる**(TenbaContinuations)。辺39 を入れると一続きの d は「辺の c の最大」で
   長屋 N39_0 の台 c 0.75 を拾い北の一続き全体を 0.80→1.05 にするところだった ⇒ 塀と長屋が同じ辺に乗る辺は塀の run の c だけ(HeiLineFace の cOf)。
   seatOverGround も塀の run の [s0,s1] の上だけで測る(線は辺の終わりまで延びる)。
2. 塀の下の内向きの石垣(EdoBuild.PlaceUnderWallInner)は、区画の線〜塀の内面+c の仮の四角(辺0 を逆向き)で PlaceCastleRun ⇒ 法は区画の内を向く。2 回据えて c を測り直す。
3. **IshigakiHead は 2・3 回目の PlaceIshigaki の行を「坂なり・出隅」しか残さない** ⇒ 新しい行は見えない。名の語を篩へ足した。測りは scene で(IGU_* の天端・塀の足 on 437/439)。
4. N39_0 の実メッシュの底 16.400 は PlaceNagayaPiece の SeatBottom(座 −0.10) ── 全長屋が同じ(N39_1 14.1/14.2・N18_a 18.4/18.5)。台の天端は 16.500 で 0.10 埋まる作り。欠陥でない。
5. 指図のコミット直後は bake_impl の指紋で S1 が止まり、--write の後も 0.25m の bin が古く 1m で造成した(既知 [[graded-bin-stale-after-sashizu-commit]])── `impl_okabe.py --graded-bin` → `Reload()` → S1。

**How to apply:** 隣の辺へ塀を回す欄が来たら d・seatOverGround が長屋の値を拾っていないかをログの「塀の一続き」の行で見る。
関連 [[r155-off-heiline-dobei-sinks-and-unread-fields]] [[heiline-stretch-and-tenba-r120]]
