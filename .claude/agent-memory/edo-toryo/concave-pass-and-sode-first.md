---
name: concave-pass-and-sode-first
description: 入隅の通し(_Tooshi)は検めで埋める駒として外す・PlaceKaidanSodes の上端の相手は cuts の長文と == で比べて常に空だった・袖を先に据えると笠の上がりは 0 に詰まる
metadata:
  type: project
---
2026-10-10 EDO-0502 第99巡(岡部 const.abutOrder 10-10o・TW_Kado_Hokuto.cuts 10-10o)。

1. **入隅の通し**(PlaceNozuraNet の passEnds → 通しの駒 `<区間>_Tooshi<端>_NN`)は土に埋める駒。Stage3b は名で design.buried に入れ、
   NozuraSkinPlaneCheck も名で外した。外さないと「見え面の平面より前」が 76→106(最悪 +4.80 は通しの駒の前の後の壁の背の土)と嘘で増える。
   NozuraSeamReport は外していない ── 被り 3 と天端の差 0.092(継ぎ目の局所の帯・最上点は 1mm で揃う)は通しの駒の読み。
2. **PlaceKaidanSodes の上端の相手(walls)は `S(cuts) != nm` で比べていて、cuts が長文なので 10-07 から常に空**だった(log「上端の相手なし」)。
   K_Kuruwa は planRay(本線の計画の見え面の線)へ替えたので効かないが、他の石段に袖を足すときは同じ穴。
3. 袖の上端を計画の線(天端 16.50)で決めると、面の位置の段鼻の線が既に 16.50 で**笠の上がりは 0.000**(狙い 0.30【柔】未達 ⚠)。上限【硬】が勝つ。

How to apply: 埋める駒を新しく足す巡は、検め(平面・継ぎ目・被り)がその駒を見え面として数えないか、名で外れるかを先に grep。関連: [[skin-solve-lo-hi-first-runs]] [[za-hull-and-back-wall-order]]
