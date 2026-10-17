---
name: keta-pokes-through-tile-valley
description: 切妻の瓦屋根を軒桁の線で壁に合わせると、桁・柱・漆喰の天端が瓦の谷から木の楕円として一列に覗く(供待・厩・詰人長屋)
metadata:
  type: project
---

`obi_roof` を「軒桁の線で壁天端に合う」高さに置くと、瓦の谷は桁の線で 4〜5cm 沈むので、桁・柱・漆喰の天端が軒先から 1.3m ほど上に**木の楕円の列**として覗く。遠景のレンダでは見えない。軒の寄りで撮ってはじめて見える(2026-10-03 EDO-0502)。

**Why:** 在庫の Okabe_Tomomachi / Okabe_Umaya / Doi_Umaya / Typ_Umaya(`build_okabe_fuzokuya.frame` の桁は壁の外へ 0.11 出る)と Obi_Nagaya / Doi_Kachu(`build_obi_nagaya.build`)は、どれもこの欠陥を持ったまま焼かれている。

**How to apply:** 新しく焼くときは `frame(keta_out=0.0)`(桁を内へ引いて 6cm 下げ、柱は桁の下で止める)、`build(keta_drop=0.06)` / CLI `--keta-drop 0.06` を渡す。既定値は従来のままなので、在庫の駒を直すなら焼き直しが要る。合否は軒の寄りのレンダで見る([[noji-under-tile-valley]])。
