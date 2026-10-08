---
name: stair-hull-below-face-sawtooth
description: 面の縁の外に立つ石段の外形の中の皮の点が駒の底まで下げられ、段の前に鋸の歯の窪みが出る。直す前に SkinTrace で分岐を名指す(3b は 37 分)
metadata:
  type: project
---
症状(2026-10-08 岡部 K_Dan1 一段目・EDO-0502 第52巡): 段石の下の縁で地面が鋸の歯に食い込む。皮の節点を読むと、外形の中(f<0)は
駒の底 16.33・外(f>0)は面 16.50。0.25 格子と段の向き(10.5°)の差で、縁を跨ぐ三角形が 0〜0.17 の窪みを周期 1.37m で並べた。
原因: 段は面の**外**(設計の地盤)に立つ。CutEdgeSkin「石段の外形」の `fyS が NaN` の枝が外形の中を駒の底まで下げ、外の点は「石段の前」が面へ揃える。
対処: その枝で、近くの面(STAIR_APRON 以内)に足が許容の内で埋まる駒は max(底, 面) まで下げる(EdoBuildHifu.cs)。
⚠ 罠: 最初「面の中で地形が低い点を上げる」と推して 1 巡(Stage3b 37 分)を無駄にした。FaceY が NaN かどうかは見た目で分からない。
How to apply: 皮の直しは**1回目の Stage3b から EdoBuild.SkinTrace に疑いの節点を入れて流す**(TrLog がどの枝で下げたかを刷る)。推して直してから流さない。
関連: [[pad-edge-nodes-outside-face-and-pinned-skin]] [[fumiishi-chamfer-and-floor-cover]] [[sode-check-skinground-and-dropped-run-residue]]
追記 2026-10-08 第53巡: SkinTrace の点は**皮の格子に乗せる**(岡部の皮は x,z が …13/…38/…63/…88)。-437.50 のような丸い値は TrHit(±0.125)を外れて何も刷らず、3b を一回空振りした。先に皮の頂点を読んで座標を写す。
同じ枝(面の外は max(底, 面) まで下げる)が立てた土(hold)の節点まで下げていた ⇒ HoldY より下げない。
