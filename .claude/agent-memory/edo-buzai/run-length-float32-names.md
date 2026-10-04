---
name: run-length-float32-names
description: 指図の s0/s1 から C# が float で引いた run 長は 5.45/5.46・12.9/12.91 に割れる。名の要る長さは float32 で引いて全部焼く(2026-10-04 土井 EDO-0533)
metadata:
  type: project
---
- 土井の辺13 は s の刻みが 5.45/5.46 交互、辺12 は 12.91/12.90。ビルダーは `Len2(s1−s0)`(float32)で名を作るので、bom の「5.45」だけ焼くと半分が欠ける ⇒ numpy.float32 で引いて Len2 を再現し、出た名を全部焼く。
- 3間(5.45)の表長屋は --body で中の窓割り 0・端の間 1.556×2 で収まる(全幅版は ε+0.354)。坂なりの段違いは _kutai を妻壁で突き付け、上の棟の妻が下の屋根の上に出る形で足りる(破風の重なりは埋まる)。
- 長屋の潜り門は komon に有効高が無いと焼けない(--gate の第3引数)。sill と run の seat の差も確かめる。
関連 [[fbx-name-mm-floor-float]] [[nagaya-body-length-and-goten-root-offset]]
