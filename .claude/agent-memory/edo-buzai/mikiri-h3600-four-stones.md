---
name: mikiri-h3600-four-stones
description: 見切り石を H2400 より高く焼くときは石の数を増やす(3 石だと縦長の板)・検証レンダの G0 の駒は深い駒を天端で沈めて代用
metadata:
  type: project
---
2026-10-10 EDO-0502 で Sanno_Nozura_Mikiri_H3600(4 石・1166 tris)を焼いた。
- `make_mikiri_h` の石の数は H ≤ 2.45 まで旧式(2/3 石)のまま、それより高い見付だけ round(全丈/0.95) ⇒ 既存の駒の乱数列は不変。
- `render_mikiri_h` は同じ見付の G0 が無いと落ちていた(H3000〜4200 は G0 を焼いていない)⇒ より深い G0 を天端で合わせて沈め、staging に無ければ在庫(OUT_WALL_REPO)から読む。
**How to apply:** 既定の正面カメラ(z 4.2)は H3.6 で天端しか写らない ⇒ 引きの絵は z 9.5 の別スクリプトで撮る。meta は H2400 を写し guid だけ替える(remap 済み)。[[nozura-kiri-diagonal-and-tall-mikiri]]
