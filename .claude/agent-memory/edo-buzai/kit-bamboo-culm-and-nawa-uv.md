---
name: kit-bamboo-culm-and-nawa-uv
description: キットの竹1本の実測(Fences/Bamboo garden fence の stake)と縄の UV 矩形・丸材の v は節間隔ごとに折り返す・結束の径は材の皮から皮で決める・set_origin だけだと FBX ノードに平行移動が残る
metadata:
  type: project
---

2026-09-22・竹矢来(EDO-0363)で実測した。竹の役物を起こすときの拠り所。

## 竹の借り先は **Village Kit `Meshes/Fences/Bamboo garden fence.fbx`**

- 中に **`bamboo garden fence stake` = 実ジオメトリの竹1本**が入っている:
  **八角柱・半径 0.0263(径 0.053)・長さ 0.900m・24頂点**。材は `Bamboo garden fence`
  (`Japanese Village Kit/Materials/Bamboo garden fence.mat` があるので remap の借り先は既定の並びで足りる)。
- UV(実測):**側面 = u 0.123..0.237 を8帯に割り・長手 v 0.005..0.637 が実長 0.900m**/
  **小口 = u 0.960..0.994 × v 0.045..0.079**(切り口の白い環)。
- **縄(結束)**は同じアトラスの竹垣本体にある — **u 0.813..0.899 × v 0.591..0.697**
  (rgb 0.40/0.39/0.33)。隣に 0.861..0.950 と 0.923..0.993 の2枚もある(やや暗い)。
- ⚠ `Japanese Shrine and Temples/Meshes/Fence_Bamboo_A_01_*` も実ジオメトリの竹垣(丈 0.78m)だが、
  材 `Fence_Bamboo_A_01` は **`Japanese Shrine and Temples/Materials`** にあり、
  `EdoRemapMat` の借り先の並びに**入っていない**。足さずに使うと真っ白。

## 丸材(竹・丸太)を自前で起こすときの作法

- **v は節の間隔(0.9m)ごとに折り返す**(輪 k が奇数のとき v0/v1 を入れ替える)。
  引き伸ばさずに済み、折り返しの線が**竹の節に見える**。1本を長く伸ばすと節が間延びする。
- 断面の枠は **`n1 = t × ref` / `n2 = t × n1`**(n1 × n2 = t)。四角 [P_k(a0), P_k(a1),
  P_{k+1}(a1), P_{k+1}(a0)] の順で**外向き**になる。⛔ `n1.cross(t)` は符号が逆。
- 小口は**扇形の四角**で塞ぐ(三角ファンは頂点が 3 倍になる)。奥端は角の昇順、手前端は降順。
- ⛔ **結束(縄)の径を決め打ちしない。**「材の皮から相手の皮まで」で出す
  (例: 斜材の内皮 `DIAG_Z-DIAG_R` から胴縁の外皮 `RAIL_Z+RAIL_R` の中点・半分)。
  はみ出すと立面で**黒い角板**に見える。面数も 4 でなく 6〜8。

## ⛔ `V.set_origin` だけでは FBX ノードに平行移動が残る

原点だけを動かすと `o.location` に差が残り、書き出した FBX の**ノードに平行移動が乗る**
(実測: `set_origin(o, (1.818,0,0))` → node loc (1.818,0,0))。Unity では**子が 1.8m 横へずれた
位置に置かれる**。`ButtOnRun` / `SeatBottom` は実メッシュを測るので run では吸収されるが、
ピボットで据える呼び手では効く。
⭕ **メッシュを原点の上へ寄せてから**(`o.location = -center` → `transform_apply(location=True)`)
`set_origin(o, (0,0,0))`。`build_typ_machiya` と同じ流儀。
関連 [[stale-matrix-world-after-location]] [[see-through-fence-panelrun-and-solidity]]
