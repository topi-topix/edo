---
name: nagaya-kata-namako-phase-and-window-layout
description: 表長屋の割付の型 --kata ── 海鼠の目地は bay/7・瓦は bay/11 の周期・窓は海鼠の穴と一体。旧版の継ぎ目の段は端の間の δ(2026-10-17 EDO-0502)
metadata:
  type: project
---
- 素の knagaya01c の海鼠(namako)は x に周期 bay/7(素 0.384m)、瓦(n_maru/n_hira/n_noki)は bay/11、垂木は独立 0.341。海鼠は窓の所に穴(縁)があり窓と位相が一体 ⇒ 窓だけ動かせない。n_wall・n_namako(箱)は穴なし。
- 旧版の「なまこがずれる」は駒の中の端の間の δ(9.09 で −0.648 obj = 1.18m の段)と ε 0.04 の段。`--kata φ` は bay を σ=1.0147 で 1.5間へ伸ばし、帯を切り貼りせず、窓は全部塞いで(芯の左右を ±4 目地の無地から写す)選んだ芯へ素の窓まわりを目地の整数倍だけ写す。φ は据える側が外周の道のり u から出す(u≡0 が窓の芯)。
- 検め: 継ぎ目の目地の位相は FBX の浮き彫りの頂点 (u mod p) の集合を突き合わせる(新版 100%・旧版 60〜67%)。既定の出力は頂点の多重集合で不変。
**Why:** 施主 2026-10-17 の写真(辺18)。**How to apply:** 長屋の版を焼くときは --kata と u を必ず渡す。関連 [[nagaya-short-both-ends-extend]] [[dan-seam-low-end-flat-cut]] [[nagaya-body-length-and-goten-root-offset]]
