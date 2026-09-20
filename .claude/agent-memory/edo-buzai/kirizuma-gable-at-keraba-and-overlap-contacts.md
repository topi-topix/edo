---
name: kirizuma-gable-at-keraba-and-overlap-contacts
description: GR.make_kirizuma(tsuma=True) は妻壁をケラバの端に立てる。ケラバのある建物では捨てて壁の通りに立てる。BVHTree.overlap は突き付けの接触面も当たりに数える
metadata:
  type: project
---

2026-09-15 山王の御供所の一棟(`build_sanno_gokusho_ikko.py`)と透塀の口の端 h で踏んだ二つ。
・`GR.make_kirizuma` は渡廊下用で、妻壁を `x0 = −end`(ケラバの端)に立てる。ケラバ 0.45 の建物だと妻壁が軒の外に浮くので、`gable()` の先頭(妻壁)を捨てて、壁の通りに `vstrip` で立て直した。破風・棟は大きさを上げた。
・組み上がりの当たりを `BVHTree.overlap` で数えると、柱が柱の面に突き付いた所や基壇の天端に立った所も「13 面対」と出る。めり込みと接触は区別されない。

**Why:** 生成器の既定値は、元の用途(渡廊下)の寸法のままになっている。overlap は面どうしの交差判定で、同じ平面に触れているだけでも交差になる。
**How to apply:** 切妻の道具を建物に流用するときは、妻壁の位置を立面で先に見る。当たりの数が 0 でないときは、接触の面(柱の面・基壇の天端)を先に除いて読むか、find_nearest の法線でめり込みの深さを測る。関連 [[stale-matrix-world-after-location]]
