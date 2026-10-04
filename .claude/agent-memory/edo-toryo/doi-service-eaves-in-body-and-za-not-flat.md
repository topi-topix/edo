---
name: doi-service-eaves-in-body-and-za-not-flat
description: 土井の附属屋(一体メッシュ)は Body/Contact(withRoof:false) に軒が残り離れを嘘にする・2m 格子の座(Za_*)は足形の中で 0.3m 起伏し布石で受けると座が欄より最大 0.36m 上がる
metadata:
  type: project
---

2026-10-04 EDO-0533 S5(EdoDoiBuilder.Mune.cs)。

1. 症状: 供待の背を表長屋 E13_N11 から 0.5間 に Abut(withRoof:false) したら壁どうしは 1.55m 離れたまま。家中長屋 K1 が奥の塀から 0.74m も逃げた。
   原因: 部材方の一体メッシュの附属屋(供待・家中長屋)は屋根の名の篩に掛からず、軒先(下端から 1.8〜2.3m)が Body に残る。Contact は軒の 1 筋を当たりに取った。
   対処: 壁体の離れは帯 [下端+0.15, 下端+1.8] の EdoBuild.Face / KeepClearOfLine で測る(2.2 では軒先の垂れが入る)。
2. 症状: 座(Za_*・足形+0.5間)の上でも足形の下の地盤が 0.24〜0.47m 起伏(芯は欄の y)。SeatOnGround → BuildingKidan で受けると棟が欄より +0.1〜0.36m 上がる(蔵2 ⚠)。
   原因: 2m 格子が 0.9m の縁の法を足形の中へ一次で描く。LevelPad で均すと奥の塀の肩(座の縁)まで削るので使わなかった。
3. GotenKit.Mune は梁間の端数(nzFrac)を持てるようにした(長局 8.5間)。床下の足が面の縁の法へ出る所は AshimotoReach で下へ伸ばす。

**How to apply:** 一体メッシュの棟どうしの離れは帯で測る。座の起伏が出たら造成(座を足形+1升に)の話として普請奉行へ。
関連: [[one-mesh-part-split-by-submesh]] [[levelpad-crosses-terrace-wall]] [[wall-toe-mound-is-grid-not-grading]]
