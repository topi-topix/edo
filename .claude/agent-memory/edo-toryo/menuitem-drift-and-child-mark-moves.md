---
name: menuitem-drift-and-child-mark-moves
description: 関数を [MenuItem] と本体の間に差し込むとメニューが別の関数を呼ぶ・子の印(_axis)は親の縮尺と位置を戻すと一緒に動く(山王 EDO-0430 2026-09-26)
metadata:
  type: project
---

1. **[MenuItem] の直下へ関数を差し込むと、属性がその関数に付く。** 0c28b9d9 で `AbutStairsToWalls` を
   `[MenuItem("…4 囲い")]` と `Stage4Menu` の間に入れた結果、メニュー「4 囲い」が柵を建てずに石段の突き付けだけを
   流していた(例外も警告も出ない)。**Why:** C# の属性は次の宣言に付く。**How to apply:** Stage を足したら
   `grep -n -A3 MenuItem` で属性の直下が意図した入口か見る。メニューで流した巡の結果が変わらないときはまずこれを疑う。

2. **子の印は親と一緒に動く。** `CutStairEndsToBatter` が段石を `localScale=1; position=芯` に戻すと、子の `_axis` が
   親の縮尺の分だけずれ(郭の階で 0.117)、次の巡の測りが d を 1.57 倍に読んだ。**How to apply:** 親を動かす前に
   子の印の世界座標を取り、動かした後に戻す(直した)。測りが前の巡と急に食い違ったら印の localPosition を見る。

3. 跨ぐ端・d の綴りの駒は相手の法 1:0.25 を仮定して焼く。鉛直の城の石垣に当たる端では蹴上の下端に 0.025 の口。
   `MeasureStepEndOnBatter` が法を測るようにした(鉛直で面一なら切らない)。
