---
name: castle-wall-kiri-and-short-arm
description: Castle Wall を斜めに切る駒と腕の短い隅で踏んだ罠 — 底が開いた素・bisect が頂点の脇に重複を作る・読み直しの .001・切った腕は素の小口を移して塞ぐ
metadata:
  type: project
---

2026-09-26 EDO-0430(`build_ishigaki_kiri.py`・`build_kado.py --arms`・`Own.IshigakiKiri` / `Own.IshigakiKado(deg,h,aZ,aX)`)。

- 素の `Castle Wall` は 38 頂点の箱で**底が開いている**(境界 8 本)。holes_fill は底まで塞ぐ ⇒ 切り口は面の上の頂点を角で並べて凸多角形を張る。
- 切る面が素の頂点の 1e-5 脇を通ると bisect が重複頂点を作り、開いた辺が 7 本残った ⇒ bisect の直後に remove_doubles(1e-4)。
- 一覧を 1 本のプロセスで回すと 2 本目の材が `stone wall.001` ⇒ 行ごとに `V.reset()`。
- 腕を縮めるのは頂点を寄せず、bisect で切って**素の小口の面を複製して切り口へ移す**(断面が走りに一定なので形も UV も一致)。
- 斜めの端は 2 枚組でなく 4.0m の 1 本物 ── 2 枚組は切る位置が割付けの連続値になる。

**Why:** 女坂の口(43.2°)と、隅の腕が袖へ入る所(0.41/0.29)を許容0で塞ぐため。
**How to apply:** 別の角・腕は一覧/引数に足して焼く。関連 [[ishigaki-kado-tall-90]] [[nori-cut-step-and-sode]]
