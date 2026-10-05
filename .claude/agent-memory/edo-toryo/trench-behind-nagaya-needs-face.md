---
name: trench-behind-nagaya-needs-face
description: 段の面の中に掘る細い溝(返しの石垣と長屋の背の間 1間)は、地形を切っても設計の地盤を下げても皮と SkinGround が面の高さで埋め戻す ── 溝を小さい平らな面(SkinFace)として足す(2026-10-05 岡部 第19巡)
metadata:
  type: project
---

2026-10-05 EDO-0502 第19巡 岡部 TW_Kado_Hokuto の返し(N39_1 の背から一間)。
① `EdoBuild.CutAlongBack` で溝を 13.1 へ切ると、② の「描かれた地表で検める」が 2m 格子の升の四隅を下げ、返しの背の門の内の土(16.5)まで 2m 掘った。
   両側が 13.1 に読め、`PlaceCrestWall` の LowSide が返しの低い側を取り違えて、返しと妻の閉じの駒が「全体が埋まる」で退けられた。
② Stage3b で設計の地盤(gh)だけを溝の高さへ下げても、`SkinGround` と皮は **平らな面(FlatFaces = 指図 terraces の poly)を設計の地盤より先に**採るので、溝は門の内の面 16.5 のまま描かれた。

**Why:** 面の中は面の高さが勝つ(面積の小さい面が勝つ入れ子)。2m 格子は 1.8m の溝を描けない。
**How to apply:** 面の中に掘る溝・窪みは、`FlatFaces` に小さい SkinFace として足す(Okabe `BackTrenches` → `FlatFaces`)。
返しの低い側は地表で決めず、溝の向きを lowHint+lowForce で渡す。`_flat` は長屋を据えた後(Stage2b の冒頭)に読み直す。
