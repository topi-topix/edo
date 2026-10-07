---
name: pad-edge-nodes-outside-face-and-pinned-skin
description: 棟の下の均しが面の外の節点を触らず隅が埋まる・皮の縁の点(PIN)の下の節点が天端に被る・閉じの検めが基壇の石垣を数えていない
metadata:
  type: project
---

2026-10-07 EDO-0502 第46巡(岡部)。

1. 厩 −0.053 は「上書き」ではなかった。LevelPad は棟の建つ面(TerracePolyAt)の外の節点を触らない ⇒ 隅が面の縁から一升の内だと、
   隅の升を描く節点(面と面の間の坂)が +0.13〜0.17 のまま残る。直し: `EdoBuild.PadRim`(区画の内・他の平らな面の外で、升が足あとに
   掛かる節点だけ均す)。さらに皮の設計への写しは平らな縁の幅を**地形の升**で取る(dstep だと格子のずれで +0.032 残った)。
2. 天端被り 7 点の正体は皮の縁の点(穴の升と地形の升の境・地形のまま)の下の地形の節点が天端より 0.2〜0.34 高かったこと。
   CloseRimAtHull は PIN を動かさない。直し: CutEdgeSkin の中で PIN の節点を天端−0.003 へ(PIN_TUCK_MAX 0.40)。
3. 閉じ 辺23/24/41 の隙は検めが Kakoi/Mon/Fences だけ数えていたため。Ishigaki(基壇)を入れると 0.00。
4. 裏坂の縁 004f の浮きは下の積み _tsumi0 に載っている(地表で測ると +0.15〜0.48 の嘘)。

**How to apply:** 均した棟の埋没は先に「節点が面の内か」を測る。被りは pin の点が穴の升の境に並んでいないか見る。閉じの検めは基壇の群を入れる。
関連: [[levelpad-crosses-terrace-wall]] [[qa-misreads-stack-and-single-mesh-gate]] [[terrain-holes-and-skin-traps]]

追記: 3b を単独で流し直す(前の 3b の皮が残ったまま)と「古い皮を外して塞いだ升 1299」の道で 2166 秒掛かった(S1 から流すと 3b は 417 秒)。
皮だけ直した巡も S1 から通す方が速い。build_queue_wait の --stall 900 は 3b 単独では偽の「固まった」を出す。
