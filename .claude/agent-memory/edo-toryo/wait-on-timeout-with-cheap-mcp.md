---
name: wait-on-timeout-with-cheap-mcp
description: 長い execute_code がタイムアウトした後の待ちは sleep 不可(門番が止める)── 軽い MCP(read_console)を一つ投げれば main thread が空くまで返らない。池の灰色の斑は水を消したレンダで切り分ける
metadata:
  type: project
---
2026-10-04 EDO-0533 土井 第7巡。

1. 症状: Stage8 植栽(46秒)・書き戻し(1分超)の execute_code がタイムアウト。結果のファイルを sleep の見張りで待とうとしたら門番が止めた(役は sleep/until を打てない・EDO-0457)。
   対処: 印のファイルで再送を止めておき(long-run-guard)、`read_console` を一つ投げる ── 前の execute_code が main thread を握っている間は返らず、返った時には結果の .txt が書けている。
2. 症状: 庭の池(土井 P_DoiOkuniwa)を斜め上から撮ると、最深の升の所に灰色の楕円と白い輪が出る。
   切り分け: 同じカメラで水面だけ SetActive(false) にして撮る ── 池床は一様な草の塗りで斑は無い ⇒ 地形でなく水の見え方(深さ 1.63m の一升だけが周り 0.3〜0.6m より深い段差を _DepthFade 0.9 が描く)。縁先の目の高さ(書院)からは出ない。カメラは UniversalAdditionalCameraData で depth/color とも ON(PC_RPAsset も ON)。

**How to apply:** 30 秒を超える Stage は印+結果ファイル+read_console で待つ。水の斑を問われたら水面を消した一枚を並べて出す。
関連: [[long-run-guard-and-soft-only-converge]] [[water-defaults-are-for-deep-ponds]] [[pond-carved-but-water-lost]]
