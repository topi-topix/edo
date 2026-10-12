---
name: neribei-saka-shear-and-tome
description: 練塀の坂なりは縦の剪断で焼くと断面が一致して閉じる・隅は芯の道のりで配る・棟止めは端だけの駒 Tome に分けた(2026-10-12 EDO-0502)
metadata:
  type: project
---
2026-10-12 岡部の const.heiLine.tenba(坂なり ≤1/8)用に build_neribei.py へ `--grade` / `--tome` / `--saka` を足した(Neribei_Saka_U|D<bp>[_Tkk]・Neribei_Kado_*_G..x..・Neribei_Tome_L/R)。

- 縦の剪断 z += g·X は x 一定の断面を形のまま上下させるだけ ⇒ 平ら・別勾配の駒と継ぎ目が自動で閉じる。回転で傾けると断面が合わない。
- 隅は腕ごとの直線の剪断だと留めの面で 2·g·q·sin(Δ/2) 割れる ⇒ 芯の道のり T を留めの線 α_m(q) から腕の先まで一様に配る(留めの上 T=0・腕の先は横に水平)。
- 棟止めを勾配×長さで焼くと数百本 ⇒ s_hei_l の端の柱の内面より外だけを一つの駒にし、どの駒の端にも突き付ける。段は上下の両方に付けて柱の外面を背中合わせ。
- 並べ焼きの光線は継ぎ目ちょうどの格子(縁の上)と、腕に沿う光線が遠い端の下を潜る所で偽の抜けが出る ⇒ 格子を 0.7mm ずらし、平らな隅と同じ光線で比べる。

**How to apply:** 新しい勾配・腕は `--list` で焼き足す(.meta も書くので remap 不要)。並べ焼きは scratchpad の assemble.py の形。[[neribei-closed-section-and-dobei2]] [[magenta-background-finds-holes]]
