---
name: stair-sode-crest-vs-kasa-and-fence-gap-end
description: 土留めを切って張り出す石段の袖は「入隅で天端を越えない」と「段鼻+0.15」が両立しない(笠 0.003 に潰れる)・天端の垣の口の端は SplitCutsByCrest で 0.1〜0.2 ずれる
metadata:
  type: project
---

2026-10-07 EDO-0502 岡部 K_Kuruwa.sode(EdoBuild.PlaceIshidanSodeRow を新設)。

1. 症状: 笠の上がりの狙い 0.15【柔】が 0.003 に潰れた。原因: 最後の蹴上が土留めの見え面(天端の位置)の真上にあり、
   段鼻の線は面で天端 16.5 に届く ⇒ 正の笠は必ず入隅で天端を越える。幾何の衝突で据え方では解けない(普請方へ)。
   対処: 硬い方(天端を越えない)を守り柔らかい方を最も近く(0.003)で建てて ⚠。
2. 症状: 天端の垣の口の片側だけ親柱が立たず垣が 0.48 手前で切れた。原因: 区間の端が口の s と一致するかを 0.05 で
   見ていたが、SplitCutsByCrest が端を 0.1 刻みで落とすので最大 0.2 ずれる。対処: 許し 0.3(PlaceCrestFence)。
3. 山王の袖の生成器は `sode <蹴上> <踏面> <幅> --depth=X` で任意の丈を焼ける(4.20 も可)。名は蹴上 F3 で丸まる(0.2833→0.283)。
   remap は `EdoSannoShaBuilder.RemapSannoShinzo()`(Kaidan を舐めるが数秒)。

関連: [[new-fbx-without-meta-reads-as-unbaked]] [[hard-vs-soft]]
