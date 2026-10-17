---
name: neribei-saka-T-is-tiles
description: 練塀の坂なりの名の _T<kk> は端数の切りの瓦の枚数(1〜13)・無印は一枚 14 枚。待ちの名の T を落として焼くと辺が丸ごと建たない(2026-10-17 岡部 第157巡)
metadata:
  type: feedback
---
- `EdoAssets.NeribeiSaka(grade, tiles)` は tiles<14 で `_T<kk>` を付ける。T10 = 瓦 10 枚の切り(2.136m)・T12 = 2.563m。据える側は n 枚の一枚 + 切り 1 枚で走りを割るので、一枚(無印)と切り(_Tkk)の両方が要る。
- 第155巡で「Saka_D0882_NK」だけ焼いて T10 を落とし、辺38 の塀が建たなかった。⇒ 待ちの名を一字ずつ写し、`--kiri <kk> --grade <%>` で焼く(一枚は `--choku`)。

- 並べ焼きで駒を Blender で連ねるとき、D(Unity +X へ下がる)は Blender +x へ**上がる**(Unity X = Blender −x)。z −= g·dx で並べると継ぎ目ごとに段が出て偽の欠陥に見える ⇒ z += g·dx(2026-10-17 T07)。継ぎ目の最近点の片側 0.43 は瓦の出の頂点で T10 も同じ・逆向き ≤0.04 を見る。

**How to apply:** 練塀の坂なりの待ちを受けたら名の _T を確かめる。[[neribei-saka-shear-and-tome]] [[neribei-no-koshi-nk]]
