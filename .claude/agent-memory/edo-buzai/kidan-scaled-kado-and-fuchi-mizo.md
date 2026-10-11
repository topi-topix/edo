---
name: kidan-scaled-kado-and-fuchi-mizo
description: 外周の基壇(倍率 s の Castle Wall)の出隅は素の隅を s 倍で焼く(_S075・名の H/A は素の寸法)・P0 は天端が違う・縁石の作りの溝は縁石を深くした AF(2026-10-11 EDO-0502)
metadata:
  type: project
---
- PlaceCastleRun の駒は Vector3.one·s で一様に縮めた Castle Wall ⇒ 隅は `build_kado.py --s 0.75` で頂点へ焼き scale 1 で据える(PlaceRunKado は scale 1 前提)。名の H・A は素の寸法、実寸 × s。
- 依頼の「倍率 0.75/0.25 の隅」(岡部 P0)は倍率より**天端が違う**(12.3 / 11.1)のが本題 ── PlaceRunKado は deg≥30 で天端違いを ⛔ で退ける。高い側で焼き、辺0 側の腕を P で切った A200x0/A0x200 を添えた。
- 縁石の作り(道が溝の底より低い)は嵩上げでは足りない(縁石の下が道より上で浮く)⇒ 縁石の下端を天端 −0.55 へ下ろした AF・吐き口は +X の縁石を内法で切る AH/AFH。
**How to apply:** 倍率つきの run の隅・道が底より低い溝。関連 [[ishigaki-kado-tall-90]] [[mizo-a-kasa-stagger]]
