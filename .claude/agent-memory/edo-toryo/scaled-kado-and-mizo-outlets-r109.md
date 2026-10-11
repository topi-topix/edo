---
name: scaled-kado-and-mizo-outlets-r109
description: 倍率 s の石垣の隅(S075)を PlaceRunCorners で据える罠・坂の座の天端の刻みで隅が退く・縁石の作り AF の底が欄より下がる・台の前の溝が N40_2/3 の基壇と重なる(岡部 第109巡)
metadata:
  type: project
---

2026-10-11 EDO-0502 第109巡(岡部 PlaceIshigaki / PlaceMizoSections / PlaceSeRojiAnkyo)。

1. **倍率版の隅**: PlaceRunKado の pathOf は**実寸の丈**(0.75 の Castle Wall なら 3.0)を渡す ⇒ `IshigakiKadoS(deg, h/s, s)`。
   armPathOf(腕を詰めた版)は KadoShortArm が**名の腕(素の cm)と実寸の要る長さ**を比べるので倍率版では選び違える ⇒ 渡さない。
   PlaceCastleRun の kadoMinTurn を 40 に戻すと 40° 未満の頂点でも端が重なり PlaceRunCorners が隅を試す ⇒ 端の組を 40° 以上の頂点の近くに絞る。
2. **坂の座の run** は 2m の区間の芯で天端を刻む ⇒ 出隅の両脇で 0.01〜0.02 違い「天端が食い違う」で隅が退く(P24 10.873/10.886)。
   両 run の SeatAt が頂点で続くなら両脇の区間の天端を頂点の座へ揃える。天端か倍率が本当に違う頂点(P0 12.3/11.1)は kadoSkip で頂点へ突き付け。
3. **縁石の作り(AF)の底**: SolveMizoBottom は駒の矩形の最低で地面を引くので、地面に「欄の底」を渡すと 1/100 の線より 0.01 下がり尻が敷きを割る ⇒ 解いた後に欄の線へ max で戻す(下り続けるまま)。
   LayMizo の pathAt は駒の順に一度ずつ呼ばれる ⇒ 閉包の番号で駒の両端の底と道から深さを選べる。狙いが変わる境(吐き口の手前 4m)は駒の境へ寄せないと跨ぐ駒が検めで退く。
4. **N40_2 / N40_3 の基壇は runs.front に「溝の内の縁」が無く区画の線に立つ** ⇒ Mizo_Kita(辺40 s29.35〜)の溝の上に基壇の見え面が来る(s44 で線から −0.07)。暗渠の吐口の嘴が区画の外へ出て退いた。指図の欄の話(差し戻し)。

**How to apply:** 倍率版の隅・溝の吐き口を他の邸へ広げるときはこの3つの罠を先に見る。関連: [[stepjoint-and-kado-return-traps]] [[lowpoly-vertex-window-empty]] [[castle-run-short-group-c-and-tall-foot]]
