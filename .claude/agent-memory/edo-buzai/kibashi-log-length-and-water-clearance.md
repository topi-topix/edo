---
name: kibashi-log-length-and-water-clearance
description: 木の平橋(岡部 書院の泉水)── 在庫の丸太は最長3.18mで桁4mは長手だけ伸ばす・橋面が水面+0.35なので梁は水面すれすれ(2026-10-08)
metadata:
  type: project
---
在庫の丸太 `wood_log_01..09` は最長 3.18m(05 は 1.33m)。径間 4m の桁は 3.0m を切って**長手だけ**伸ばした(桁は板の下の陰)。`build_maruta.log_piece` は長さ超過で SystemExit。
**Why:** 指図の deckY = waterY+0.35 で、板0.045+桁φ0.16+梁φ0.14 で梁の下端が水面に届く。太くすると梁が沈む。
**How to apply:** 水面に近い橋は桁・梁の径から先に詰める。AssetByKey に "Hashi" の case は無い(棟梁が足す)。[[haisui-modules-holes-and-soil-scale]]
