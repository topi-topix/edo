---
name: expose-measured-under-batter
description: 土留めの見付を天端の縁の 0.3m 前で測ると法の駒の下(法の途中の設計の地盤)を読み、丈が 0.5m 足りない駒が足元から浮く。皮がその歯形の底へ盛り上がり「土の歯」が並ぶ
metadata:
  type: project
---

2026-10-04 EDO-0502 第9巡(岡部 TW_Kado_Shumen の口の脇)。近景で城の石垣の足元に土の三角の歯が並んだ。
正体: 皮(CutEdgeSkin の sealFace)が隣の駒の底まで盛る ── 丈 4.0 の Castle Wall(底の石が歯形)が面 16.5 から 0.5m 浮き(底 17.0)、
皮が歯の間の底へ上がった。浮いた原因は PlaceCrestWall の見付の測り: 天端の前の縁から lowN×0.3 の地表 = 法 1:0.25 の駒の**下**
(足元は縁から約 1m 前)で、SkinGround が法の途中の設計の地盤 17.0 を返し、見付 4.0 と読んだ。
対処: 据えた駒の実メッシュで足元の出(lowN 方向の最大)を測り、その 0.3m 前で測り直して丈を選び直す(EdoBuild.PlaceCrestWall・1 回)。

**How to apply:** 土留めの足元に土の歯・楔が出たら、まず駒の底と前の面の差(浮き)を測る。PlaceCrestWall の ★ 浮きが 0 でも、測った地表が駒の下なら嘘。
関連 [[wall-seat-on-skin-ground-not-grid]] [[batter-toe-read-as-bottom]]
