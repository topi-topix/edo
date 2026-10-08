---
name: pond-bank-skin-and-bench-under-hull
description: 池の縁の浮きは水面の縁を押し出しても直らない(岸を皮で描く)・背の小段は駒の外形の中では皮が地形を残すので「描かれていない」と誤読する(岡部 第60〜61巡)
metadata:
  type: project
---

池: 第60巡で水面の縁を「継ぎの間に点を足して外へ出す」をしたら、瓢箪のくびれで縁が池底を渡り悪化した(1520/3203)。
正しい手は岸を皮で描く: CutEdgeSkin(drawAreas)+ Stage3b で hori.danmen を汀線からの距離で 0.25 格子へ。石組・乱杭は汀から内 0.3m を岸の高さに(石の足の下)── 0/1426。
背の小段: 天端の線から 0.3〜1.2m 後ろは野面の駒の外形(控え+法)の中で、皮は地形を残す(SkinTrace「near 2」)。そこを測ると「盛っていない」と出るが駒の下。測るのは外形の外だけ。
**How to apply:** 縁や背の地表を測る前に、点が部材の外形の中か(SkinTrace の near)を見る。関連 [[pond-outline-and-garden-seat-traps]]
