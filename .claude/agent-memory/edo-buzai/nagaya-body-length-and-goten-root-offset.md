---
name: nagaya-body-length-and-goten-root-offset
description: 表長屋の --body(躯体=呼び寸法・破風 0.322 は外)と、在庫の御殿部材の FBX の根に平行移動が残っていて並べ焼きで柱が 0.09 ずれる罠(2026-10-03 EDO-0502)
metadata:
  type: project
---

- 表長屋の呼び寸法は従来「破風込みの全幅」。躯体の端は **namako2(妻の海鼠の浮き彫り)の外面**で、破風はそこから 0.322(土台の小口からは 0.352)。⇒ `build_nagaya_omote.py --body` で躯体=呼び寸法・名に `_kutai`・札を書く。中の窓割り 1.5間固定・端数は両端の間(0.99〜2.22m)。門口は躯体の端から測ると口の局所位置は旧版と同じ。
- 前の巡の門長屋の引数(測って復元): 17.68_mon12.18 = `--gate 12.18 3.636 3.30 --doorh 3.30 --kabuki 0.42 --ridge 8.5 --floors 2`(番所なし)/ 20.07_mon4.07 = `--gate 4.07 2.727 2.8 --floors 2`。
- ⚠ 在庫の御殿部材(Goten_Column・Goten_Nureen_1ken)は FBX の根に (0.091,0.091,0)/(0.909,0,0) の平行移動を抱える。Unity は Put で上書きするので芯ピボットになるが、Blender で読み直して並べると 0.09 ずれる ⇒ 並べ焼きでは根の平行移動を捨てる(build_goten_tsuka.assemble_and_render)。

- 土井の棟梁の「部材か札が無い Nagaya_Omote_<L>_2f.fbx」は KutaiOf が _kutai 不在で素の名へ落ちた表示。要るのは `_2f_kutai`+札(2026-10-07 16.82/15)。前例どおり素の版も一緒に焼く。

**Why:** 呼び寸法の定義違いで 0.644m の隙・並べ焼きの見かけのずれで誤診しかけた。
**How to apply:** 新しく長屋の駒を並べる邸は --body を使う。御殿の部材を並べて検めるときは根の平行移動を捨てる。関連 [[nagaya-tsuma2-straight]]
