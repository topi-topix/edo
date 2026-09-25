---
name: sode-neiri-and-buried-crest
description: 袖の根入れは丈の選択で取る(男坂は 3.20 を焼いて足した)・「隅の駒が天端 25.94 で埋まる」は前の巡の読みで、v19 の実測では天端 28.30・露出 1.33m だった
metadata:
  type: project
---

2026-09-25 山王 EDO-0430 v19(commit 64961800)。

1. 袖(石段の組)の底の根入れは `PlaceIshidanSodeByDepth(footAt, neiri)` が丈で取る。足元は**設計面**(Gr.Bilinear・外は地形)で測る ──
   描かれた地表で測ると皮が袖の底へ寄せて持ち上げた後の値を読み、不足が見えない。男坂 (0.260, 0.650) は 2.20 では下り側の端で
   0.08〜0.20 不足 ⇒ 登録済みの `--depth=3.20` を `--only=男坂` で焼いて 12 駒が深い丈へ。女坂は変わらず 3 駒。
2. 依頼の前提「TW_Romon_KoshiN_kado1 は天端 25.94 で全部埋まる」は**古い巡の読み**で、v19 の実測では天端 28.30・前の地表より 1.33m 上。
   先に測ってから直す(前提を測らずに据えを直さない ── [[batter-toe-read-as-bottom]] と同じ型)。
3. 見え面の前の帯を測るとき、足の光線(RayToBodies)が壁を外すと遠くの駒に当たり足 5m と出る ⇒ 足 > 2.5 の測線は捨てる。
   掘り(digParts)を基準に入れる近似は、袖の外形の頂点までの距離で測ると 0.3m 甘い ⇒ 局所の矩形へ落として測る。

**How to apply:** 袖や土留めの底の浮きを言われたら、描かれた地表でなく設計面で不足を測り、丈を選ぶ側で直す。皮で塞がない。
関連: [[batter-toe-read-as-bottom]] [[wall-foot-ridge-from-nodes-under-hull]] [[new-fbx-without-meta-reads-as-unbaked]]
