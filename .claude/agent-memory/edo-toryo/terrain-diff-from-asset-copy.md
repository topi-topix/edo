---
name: terrain-diff-from-asset-copy
description: 地形の前後の差は ModernTerrain.asset の写しから後で採れる(.bin を採り忘れても)── 高さは int16 の行優先の塊で、行を探して位置を合わせる
metadata:
  type: project
---
症状: 着手前に heightmap の .bin を採らず、`ModernTerrain.asset` の cp だけ残した(2026-10-06 土井 r14)。資産は binary で、写しと今のファイルは長さが 256 byte 違い同じ offset では比べられない(全面が変わったと出る)。
対処: Unity で `GetHeights` を float32 で .bin へ書き、python で `round(h*32766)` の int16 にして、**遠い行(z=100)の先頭 200 点**を写しの中で `find` → 塊の頭 = off − 100·R·2。そこから R×R の int16 を読んで差を取る(R=2049・高さ 49m)。
結果: 土井の S1→地表の通しは高さの変化 0 節点(造成は冪等)。
**How to apply:** 着手前は .bin を採るのが本筋。採り忘れたらこの手で事後に差を出せる。
