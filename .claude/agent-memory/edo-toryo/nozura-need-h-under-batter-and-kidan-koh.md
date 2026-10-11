---
name: nozura-need-h-under-batter-and-kidan-koh
description: 野面の見付を線(天端の前の縁)の 0.25/0.7 前で測ると法の下を読み、足元を切り下げた所で底が浮き皮が「土の板」を立てる・外周の基壇を甲の型(根石を線)へ移した時の段取り(2026-10-11 EDO-0502 第107巡)
metadata:
  type: project
---
- 症状: TW_Higashi_Se(背の路地の奥の野面)で底の浮き 15 駒(+0.06〜+0.93)と、見え面の前に垂直の土の板(高さ 2〜3m)が何枚も。
  原因: PlaceNozuraRun の needH・endExpose・積み止めが足元を「線から 0.25/0.7」で測る。線は天端の前の縁で、H4.8 の法尻は 1.4m 前 ⇒ 測り点は
  法の下(路地の切りの帯 [背−0.3, 足元+0.3] の外の高い地形)。皮は浮いた底の下を埋めるので、駒の継ぎ目ごとに土の板になる(同じ原因)。
  切り分け: 皮を消して撮ると、浮いた駒の底と路地の間に空き(板は皮)。
  対処: EdoBuild.FootAhead(法 FaceBatterOf × (天端 − 足元) + off の不動点・最も低い値)。全野面に効く。
- 外周の基壇を EdoBuild.PlaceCastleRun へ移すには CastleSec に scale(岡部の倍率 s)・datumIn(溝の内の縁 0.55)・insetKey(run ごとの控え)が要った。
  囲いの外面は Okabe の FaceIn(e,s) = c + 犬走り。基壇は囲いより先に据える(c が外面を決める)。KadoFace は腕ごとの目標の版を足した。

**How to apply:** 野面の底が浮いて「見付 > 駒の丈」の ★ が出ないとき(丈は足りると読んでいる)は、見付の測り点が法の下に入っていないかを先に疑う。
[[seroji-chain-foot-and-outer-base-inverted]] [[expose-measured-under-batter]]
